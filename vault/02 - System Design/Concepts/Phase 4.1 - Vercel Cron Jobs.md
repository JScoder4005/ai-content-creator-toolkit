---
tags: [system-design, phase-4, cron, vercel, scheduling]
created: 2026-04-26
phase: 4
---

# Phase 4.1 - Vercel Cron Jobs

## What is it?

Vercel Cron Jobs trigger a Next.js API route on a schedule defined in `vercel.json`. No separate server, no GitHub Actions, no BullMQ — just a route that Vercel calls automatically.

## Why does it matter?

ContentPilot needs to publish scheduled content without a user triggering it. Vercel Cron is the simplest solution — it runs inside your existing deployment, costs nothing on Pro plan, and requires zero infrastructure.

## How it works

![[vercel_cron_contentpilot.svg|627]]

1. Vercel Scheduler fires at the configured cron expression
2. Calls your API route with a `Authorization: Bearer CRON_SECRET` header
3. Route verifies the secret — rejects anything without it
4. Queries DB for `READY` content
5. Publishes to platform → updates status to `PUBLISHED`

## Applied to ContentPilot

### vercel.json — define the schedule

```json
{
  "crons": [
    {
      "path": "/api/cron/publish",
      "schedule": "0 * * * *"
    },
    {
      "path": "/api/cron/fetch-analytics",
      "schedule": "0 2 * * *"
    }
  ]
}
```

`0 * * * *` = top of every hour. `0 2 * * *` = 2am daily.
Vercel free plan: 2 crons max, 1/day each. Pro plan: unlimited, any frequency.

### Cron route — publish scheduled content

```typescript
// app/api/cron/publish/route.ts
import { prisma } from '@/lib/prisma'
import { publishToYouTube, publishToInstagram } from '@/lib/publishers'
import { NextRequest } from 'next/server'

export async function POST(req: NextRequest) {
  // Verify this is actually Vercel calling — not a random POST
  const authHeader = req.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Fetch all content ready to publish
  const readyContent = await prisma.content.findMany({
    where: { status: 'READY' },
    include: {
      posts: {
        where: { status: 'SCHEDULED' },
        include: { platform: true },
      },
    },
  })

  const results = []

  for (const content of readyContent) {
    for (const post of content.posts) {
      try {
        let externalId: string

        if (post.platform.type === 'YOUTUBE') {
          externalId = await publishToYouTube(content, post.platform)
        } else {
          externalId = await publishToInstagram(content, post.platform)
        }

        // Transaction: update both content + post atomically
        await prisma.$transaction([
          prisma.publishedPost.update({
            where: { id: post.id },
            data: { status: 'PUBLISHED', externalId, publishedAt: new Date() },
          }),
          prisma.content.update({
            where: { id: content.id },
            data: { status: 'PUBLISHED' },
          }),
        ])

        results.push({ postId: post.id, status: 'published' })
      } catch (error) {
        // Mark failed — don't throw, continue processing other posts
        await prisma.publishedPost.update({
          where: { id: post.id },
          data: { status: 'FAILED' },
        })
        results.push({ postId: post.id, status: 'failed' })
      }
    }
  }

  return Response.json({ processed: results.length, results })
}
```

### Analytics cron — fetch stats daily

```typescript
// app/api/cron/fetch-analytics/route.ts
export async function POST(req: NextRequest) {
  const authHeader = req.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const posts = await prisma.publishedPost.findMany({
    where: { status: 'PUBLISHED', externalId: { not: null } },
    include: { platform: true },
  })

  for (const post of posts) {
    const stats = await fetchPlatformStats(post.externalId!, post.platform.type)

    await prisma.analytics.upsert({
      where: { postId: post.id },
      update: { ...stats, fetchedAt: new Date() },
      create: { postId: post.id, ...stats },
    })
  }

  return Response.json({ updated: posts.length })
}
```

### Environment variable

```bash
# .env.local
CRON_SECRET=your-random-secret-here

# Generate one:
openssl rand -base64 32
```

### Test locally with curl

```bash
curl -X POST http://localhost:3000/api/cron/publish \
  -H "Authorization: Bearer your-random-secret-here"
```

## Trade-offs

| | Vercel Cron | GitHub Actions | BullMQ + Redis |
|---|---|---|---|
| Setup complexity | ✅ Zero — just vercel.json | Medium | High |
| Infra needed | ✅ None | None | Redis server |
| Retry on failure | ❌ No built-in retry | ✅ | ✅ |
| Job queuing | ❌ No | ❌ No | ✅ |
| Cost | Free (Pro plan) | Free | Redis cost |
| ContentPilot choice | ✅ MVP | — | Phase 2 scale |

## Interview Q&A

**Q: What is a cron job and what does the expression `0 * * * *` mean?**
A cron job is a scheduled task that runs automatically at defined intervals. `0 * * * *` means "at minute 0 of every hour" — five fields: minute, hour, day of month, month, day of week. `*` means "every".

**Q: Why do you need to verify the `CRON_SECRET` header?**
The cron route is a public HTTP endpoint — anyone can POST to it. Without secret verification, an attacker can trigger mass publishing or analytics fetches at will. The secret ensures only Vercel's scheduler (and you, in development) can invoke it.

**Q: Why not use GitHub Actions for scheduling instead of Vercel Cron?**
GitHub Actions works but adds a separate system to manage — separate secrets, separate logs, separate failure alerts. Vercel Cron lives inside your deployment — same environment, same logs, zero additional infrastructure for an MVP.

**Q: What happens if a cron job fails midway through processing multiple items?**
Without retry logic, failed items stay in READY or SCHEDULED status and get picked up on the next run. Vercel Cron has no built-in retry — you handle failures per-item with try/catch and mark them FAILED. For guaranteed delivery you'd move to BullMQ at scale.

**Q: Why is Vercel Cron limited on the free plan?**
Free plan: max 2 crons, minimum 1-day interval. Pro plan: unlimited crons, minimum 1-minute interval. ContentPilot needs Pro for hourly publishing.

---

Related: [[Phase 3.4 - DB Transactions]] [[Phase 4.2 - Webhook Design]]