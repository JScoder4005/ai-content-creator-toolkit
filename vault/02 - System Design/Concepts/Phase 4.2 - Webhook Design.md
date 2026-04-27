---
tags: [system-design, phase-4, webhooks, youtube, instagram]
created: 2026-04-26
phase: 4
---

# Phase 4.2 - Webhook Design

## What is it?

A webhook is an HTTP POST that an external platform sends to your server when an event occurs — video processed, post published, payment completed. Push-based, not poll-based. You register a URL, they call it.

## Why does it matter?

Without webhooks, ContentPilot would have to poll YouTube every few minutes to check if a video finished processing. That wastes API quota, adds latency, and hits rate limits. YouTube pushes the event the moment it's ready — no polling needed.

## How it works

![[webhook_design_contentpilot.svg|605]]

1. External platform fires a POST to your registered webhook URL
2. Your route verifies the HMAC signature — rejects if invalid
3. **Return 200 immediately** — before any processing
4. Process the event asynchronously after responding
5. Platform retries with exponential backoff if it gets 5xx or times out

The critical rule: **always return 200 first**. Platforms have short timeout windows (5–10s). If your processing takes longer, they assume delivery failed and retry — causing duplicate processing.

## Applied to ContentPilot

### Register webhook URL with YouTube

```
https://contentpilot.dev/api/webhooks/youtube
```

YouTube sends `X-Hub-Signature-256: sha256=<hmac>` on every request.

### Webhook route — YouTube

```typescript
// app/api/webhooks/youtube/route.ts
import { prisma } from '@/lib/prisma'
import crypto from 'crypto'

export async function POST(req: Request) {
  const rawBody = await req.text()  // must read as text for signature verification

  // Step 1: verify signature BEFORE parsing body
  const signature = req.headers.get('x-hub-signature-256')
  const expected = `sha256=${crypto
    .createHmac('sha256', process.env.YOUTUBE_WEBHOOK_SECRET!)
    .update(rawBody)
    .digest('hex')}`

  if (!signature || signature !== expected) {
    return Response.json({ error: 'Invalid signature' }, { status: 401 })
  }

  // Step 2: return 200 immediately
  const response = Response.json({ received: true }, { status: 200 })

  // Step 3: process asynchronously after responding
  const event = JSON.parse(rawBody)
  processYouTubeEvent(event).catch(console.error)  // fire and forget

  return response
}

async function processYouTubeEvent(event: any) {
  if (event.type === 'video.processed') {
    const post = await prisma.publishedPost.findFirst({
      where: { externalId: event.videoId },
    })

    if (post) {
      await prisma.publishedPost.update({
        where: { id: post.id },
        data: { status: 'PUBLISHED', publishedAt: new Date() },
      })
    }
  }
}
```

### Webhook route — Instagram

```typescript
// app/api/webhooks/instagram/route.ts

// Instagram sends a GET first to verify the endpoint
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const mode = searchParams.get('hub.mode')
  const token = searchParams.get('hub.verify_token')
  const challenge = searchParams.get('hub.challenge')

  if (mode === 'subscribe' && token === process.env.INSTAGRAM_VERIFY_TOKEN) {
    return new Response(challenge, { status: 200 })  // echo back challenge
  }

  return Response.json({ error: 'Forbidden' }, { status: 403 })
}

export async function POST(req: Request) {
  const rawBody = await req.text()

  // Instagram uses x-hub-signature (SHA1) or x-hub-signature-256 (SHA256)
  const signature = req.headers.get('x-hub-signature-256')
  const expected = `sha256=${crypto
    .createHmac('sha256', process.env.INSTAGRAM_APP_SECRET!)
    .update(rawBody)
    .digest('hex')}`

  if (!signature || signature !== expected) {
    return Response.json({ error: 'Invalid signature' }, { status: 401 })
  }

  const response = Response.json({ received: true }, { status: 200 })

  const event = JSON.parse(rawBody)
  processInstagramEvent(event).catch(console.error)

  return response
}
```

### Idempotency — handle duplicate deliveries

Platforms retry on failure. Your handler must be idempotent — processing the same event twice produces the same result:

```typescript
async function processYouTubeEvent(event: any) {
  if (event.type === 'video.processed') {
    await prisma.publishedPost.updateMany({
      where: {
        externalId: event.videoId,
        status: { not: 'PUBLISHED' },  // skip if already processed
      },
      data: { status: 'PUBLISHED', publishedAt: new Date() },
    })
  }
}
```

`updateMany` with `status: { not: 'PUBLISHED' }` — second delivery is a no-op.

### Environment variables

```bash
YOUTUBE_WEBHOOK_SECRET=your-youtube-secret
INSTAGRAM_APP_SECRET=your-instagram-app-secret
INSTAGRAM_VERIFY_TOKEN=your-verify-token
```

## Trade-offs

| | Webhooks | Polling |
|---|---|---|
| Latency | ✅ Real-time push | ❌ Up to poll interval |
| API quota | ✅ One call per event | ❌ Constant requests |
| Complexity | Medium (signature verify, idempotency) | Low |
| Reliability | Platform must support webhooks | ✅ Always works |
| ContentPilot choice | ✅ YouTube + Instagram | Fallback only |

## Interview Q&A

**Q: What is a webhook and how does it differ from polling?**
A webhook is an HTTP POST from an external system to your server when an event occurs — push-based. Polling is your server repeatedly asking "did anything change?" — pull-based. Webhooks are more efficient: no wasted requests, real-time delivery, no API quota burn.

**Q: Why must you verify the webhook signature?**
Your webhook URL is public — anyone can POST to it. Without signature verification, an attacker can send fake events: fake "video published" events to mark content as published when it isn't, or fake payment events. HMAC signature verification proves the request came from the legitimate platform using a shared secret.

**Q: Why return 200 before processing the event?**
Platforms have short timeout windows (typically 5–10 seconds). If your processing takes longer, they assume delivery failed and retry — causing the same event to be processed multiple times. Return 200 immediately to acknowledge receipt, then process asynchronously.

**Q: What is idempotency and why does it matter for webhooks?**
Idempotency means processing the same operation multiple times produces the same result. Platforms retry failed deliveries — your handler will receive duplicates. An idempotent handler checks if the event was already processed and skips it, preventing double-publishing or duplicate DB rows.

**Q: What is the Instagram webhook verification handshake?**
When you register a webhook URL, Instagram sends a GET request with `hub.mode=subscribe`, `hub.verify_token`, and `hub.challenge`. Your endpoint must verify the token matches your secret and echo back the `hub.challenge` value. This proves you own and control the endpoint before Instagram starts sending events.

---

Related: [[Phase 4.1 - Vercel Cron Jobs]] [[Phase 4.3 - Background Jobs]]