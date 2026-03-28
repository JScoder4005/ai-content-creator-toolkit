---
tags: [system-design, phase-2, rate-limiting, redis, api]
created: 2026-03-28
phase: 2
---
# Phase 2.3 - Rate Limiting

## What is it?
Capping the number of requests a client can make to an endpoint within a time window.

## Why does it matter?
`/api/v1/generate` calls the Claude API — every request costs money. Without rate limiting, one user (or bot) can exhaust the budget, slow other users, or crash the service.

## How it works

![[rate_limiting_contentpilot.svg]]

1. Request arrives with userId (from JWT)
2. Check Redis counter for that userId
3. Limit exceeded → 429 with `Retry-After` header, stop
4. Under limit → increment counter, proceed to Claude API

## Algorithms

**Fixed window** — counter resets at clock boundaries (every hour on the hour).
Problem: burst exploit — 10 req at 11:59 + 10 at 12:00 = 20 in 2 minutes.

**Sliding window** — tracks last 60 minutes from *now*, not clock boundary.
No burst exploit. ContentPilot uses this.

## Applied to ContentPilot
- Library: `@upstash/ratelimit` + `@upstash/redis`
- Limit: 10 requests / user / hour on `/api/v1/generate`
- Key: `userId` (not IP — shared IPs break per-IP limiting)
- Store: Upstash Redis (serverless-compatible, works on Vercel Edge)
```typescript
// lib/ratelimit.ts
import { Ratelimit } from '@upstash/ratelimit'
import { Redis } from '@upstash/redis'

export const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(10, '1 h'),
  prefix: 'ratelimit',
})
```
```typescript
// middleware.ts — after JWT verification
if (req.nextUrl.pathname.startsWith('/api/v1/generate')) {
  const { success, limit, remaining, reset } = await ratelimit.limit(userId)

  if (!success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Try again later.' },
      {
        status: 429,
        headers: {
          'X-RateLimit-Limit': limit.toString(),
          'X-RateLimit-Remaining': '0',
          'Retry-After': Math.ceil((reset - Date.now()) / 1000).toString(),
        }
      }
    )
  }
}
```

## What to learn vs ignore
Learn: sliding window, `limit()` return values, `Retry-After`, Redis TTL, userId as key
Ignore now: token bucket, leaky bucket, distributed cross-region limiting (Phase 6)

## Trade-offs
- Upstash Redis: exact, serverless-compatible, ~5ms latency, free tier 10k/day
- In-memory Map: zero latency, breaks on Vercel (resets per invocation)
- DB counter: exact, ~20ms latency, adds DB load

ContentPilot uses Upstash Redis.

## Interview questions

**Q: What is rate limiting and why does it matter?**
Caps requests per client per time window. Without it, one user can exhaust your API budget, slow other users, or take down the service.

**Q: Fixed window vs sliding window?**
Fixed resets at clock boundaries — allows burst abuse at the boundary (20 req in 2 min). Sliding window tracks last N minutes from now — no burst exploit, always enforces a true rolling limit.

**Q: Why userId as key, not IP?**
Multiple users share IPs (office NAT, shared WiFi). IP limiting punishes innocent users for someone else's abuse. userId isolates per authenticated user precisely.

**Q: What status code and headers for rate limit response?**
429 Too Many Requests. Include `Retry-After` (seconds until reset), `X-RateLimit-Limit`, `X-RateLimit-Remaining`. Lets clients back off gracefully.

**Q: Why not in-memory rate limiting on Vercel?**
Vercel functions are stateless — each invocation can run on a different instance. In-memory counter only tracks one instance's requests. Redis is shared across all instances — the only accurate option.

---
Related: [[Phase 2.2 - Request Validation Zod]] [[Phase 2.4 - Authentication JWT]]