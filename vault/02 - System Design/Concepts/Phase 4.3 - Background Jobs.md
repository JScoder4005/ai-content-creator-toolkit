---
tags: [system-design, phase-4, background-jobs, async, queue]
created: 2026-04-26
phase: 4
---

# Phase 4.3 - Background Jobs

## What is it?

A background job is work that runs outside the request/response cycle — decoupled from the user's request so they're not blocked waiting for a slow operation to complete.

## Why does it matter?

Generating a caption with the Claude API can take 3–10 seconds. Uploading to YouTube can take minutes. Blocking the HTTP response until these finish means the user stares at a spinner — and if the connection drops, the work is lost. Background jobs decouple the trigger from the work.

## How it works

![[background_jobs_contentpilot.svg]]

1. Request arrives — route enqueues the job and returns 202 immediately
2. User is unblocked — they can close the tab, it doesn't matter
3. Vercel Cron picks up PENDING jobs from the DB queue
4. Worker processes: calls Claude API, writes result to DB
5. Status updated — user polls or gets notified when done

**202 Accepted** means "I received your request and it's being processed" — different from 200 which means "here's your result".

## Applied to ContentPilot

### DB as job queue — no BullMQ at MVP

ContentPilot uses the `Content` table itself as a lightweight job queue via the `status` enum. No Redis, no BullMQ, no extra infrastructure.

```
DRAFT → GENERATING → READY → PUBLISHED
                   ↘ FAILED
```

### Enqueue — route handler

```typescript
// app/api/v1/generate/route.ts
export async function POST(req: Request) {
  try {
    const body = await req.json()
    const result = GenerateSchema.safeParse(body)
    if (!result.success) throw new ValidationError('Invalid request body')

    const { topic, platform, tone } = result.data
    const userId = req.headers.get('x-user-id')!

    // Enqueue — create content with GENERATING status
    const content = await prisma.content.create({
      data: { userId, topic, tone, status: 'GENERATING', caption: '' },
    })

    // Return 202 immediately — don't wait for Claude
    return Response.json(
      { contentId: content.id, status: 'generating' },
      { status: 202 }
    )
  } catch (error) {
    return handleError(error)
  }
}
```

### Worker — Cron picks up GENERATING jobs

```typescript
// app/api/cron/generate/route.ts
import { prisma } from '@/lib/prisma'
import { generateCaption } from '@/lib/claude'

export async function POST(req: Request) {
  const authHeader = req.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Pick up jobs stuck in GENERATING for more than 1 min (retry stale)
  const jobs = await prisma.content.findMany({
    where: {
      status: 'GENERATING',
      updatedAt: { lt: new Date(Date.now() - 60_000) },
    },
    take: 10,  // process in batches
  })

  for (const job of jobs) {
    try {
      const caption = await generateCaption(job.topic, job.tone)

      await prisma.content.update({
        where: { id: job.id },
        data: { caption, status: 'READY' },
      })
    } catch {
      await prisma.content.update({
        where: { id: job.id },
        data: { status: 'FAILED' },
      })
    }
  }

  return Response.json({ processed: jobs.length })
}
```

### Poll for status — client side

```typescript
// Client polls until status is READY or FAILED
async function pollContentStatus(contentId: string) {
  const interval = setInterval(async () => {
    const res = await fetch(`/api/v1/content/${contentId}/status`)
    const { status } = await res.json()

    if (status === 'READY') {
      clearInterval(interval)
      // show caption to user
    } else if (status === 'FAILED') {
      clearInterval(interval)
      // show error to user
    }
  }, 2000)  // poll every 2 seconds
}
```

### Status endpoint

```typescript
// app/api/v1/content/[id]/status/route.ts
export async function GET(req: Request, { params }: { params: { id: string } }) {
  const content = await prisma.content.findUnique({
    where: { id: params.id },
    select: { status: true, caption: true },
  })

  if (!content) throw new NotFoundError('Content')

  return Response.json(content)
}
```

## Trade-offs

| | DB as queue | BullMQ + Redis | Vercel Background |
|---|---|---|---|
| Setup | ✅ Zero extra infra | Redis required | ✅ Zero |
| Retry logic | Manual | ✅ Built-in | ✅ Built-in |
| Job visibility | ✅ Query DB | Dashboard | Limited |
| Scale | ⚠️ DB load at scale | ✅ | ✅ |
| Cost | ✅ Free | Redis cost | Pro plan |
| ContentPilot choice | ✅ MVP | Phase 2 scale | — |

## Interview Q&A

**Q: What is a background job and when do you need one?**
A background job runs outside the request/response cycle — the user gets a response immediately while the work continues. You need one when an operation is slow (Claude API, video upload), unreliable (external API), or long-running (batch processing). Blocking the HTTP response on these is bad UX and wastes server resources.

**Q: What does HTTP 202 Accepted mean vs 200 OK?**
200 means "I completed your request, here's the result." 202 means "I received your request and it's being processed — check back later." Use 202 when work is deferred to a background job. Include a `contentId` or job ID in the response so the client can poll for status.

**Q: Why use the DB as a job queue instead of BullMQ?**
At MVP scale, a DB queue is simpler — no Redis to provision, no BullMQ to configure, and the job state is visible via normal DB queries. The tradeoff is DB load at scale and no built-in retry. Switch to BullMQ when job volume is high enough to stress the DB.

**Q: How do you prevent a job from being processed twice by concurrent workers?**
Use atomic status updates — only process jobs in a specific state and update the state atomically. With Prisma: `updateMany` with `where: { status: 'GENERATING' }` — only one worker claims it. At scale, use `SELECT FOR UPDATE SKIP LOCKED` in raw SQL.

**Q: What is the difference between a job queue and a message queue?**
A job queue holds discrete tasks to be processed once by one worker — publish this post, generate this caption. A message queue (Kafka, RabbitMQ) holds events that can be consumed by multiple subscribers in order. ContentPilot needs a job queue, not a message queue.

---

Related: [[Phase 4.2 - Webhook Design]] [[Phase 5.1 - Claude API Patterns]]