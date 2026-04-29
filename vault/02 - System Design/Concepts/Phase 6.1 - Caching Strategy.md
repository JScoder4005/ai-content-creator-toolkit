---
tags: [system-design, phase-6, caching, redis, performance]
created: 2026-04-26
phase: 6
---

# Phase 6.1 - Caching Strategy

## What is it?

Caching stores the result of an expensive operation — a DB query, an API call, a computed value — in fast memory so subsequent requests get the result instantly without repeating the work.

## Why does it matter?

A database query takes 20–100ms. A Redis cache lookup takes ~1ms. For data that doesn't change every second — like a user's content list — hitting the DB on every request wastes time and money. Caching sits in front of the DB and absorbs repeated reads.

## How it works

![[caching_strategy_contentpilot.svg|608]]

**Cache hit** — key exists in Redis → return immediately, DB never touched.

**Cache miss** — key not in Redis → query DB → write result to Redis with TTL → return to client.

**Cache invalidation** — when data changes (new content created, post published) → delete the relevant cache key immediately so the next request gets fresh data.

TTL (Time To Live) is the safety net — even if invalidation is missed, stale data expires automatically.

## Applied to ContentPilot

### Cache layer utility

```typescript
// lib/cache.ts
import { Redis } from '@upstash/redis'

const redis = Redis.fromEnv()

export async function getCached<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl = 60  // seconds
): Promise<T> {
  // Check cache first
  const cached = await redis.get<T>(key)
  if (cached !== null) return cached

  // Miss — fetch from DB
  const data = await fetcher()

  // Write to cache with TTL
  await redis.setex(key, ttl, JSON.stringify(data))

  return data
}

export async function invalidateCache(key: string): Promise<void> {
  await redis.del(key)
}

export async function invalidateCachePattern(pattern: string): Promise<void> {
  const keys = await redis.keys(pattern)
  if (keys.length > 0) await redis.del(...keys)
}
```

### Cache keys — consistent naming convention

```typescript
// lib/cacheKeys.ts
export const CacheKeys = {
  userContent: (userId: string) => `content:${userId}`,
  contentDetail: (contentId: string) => `content:detail:${contentId}`,
  userAnalytics: (userId: string) => `analytics:${userId}`,
  userPlatforms: (userId: string) => `platforms:${userId}`,
}
```

### Usage in route handler

```typescript
// app/api/v1/content/route.ts
import { getCached, CacheKeys } from '@/lib'

export async function GET(req: Request) {
  const userId = req.headers.get('x-user-id')!

  const content = await getCached(
    CacheKeys.userContent(userId),
    () => prisma.content.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      take: 20,
    }),
    60  // 60 second TTL
  )

  return Response.json({ content })
}
```

### Cache invalidation on write

```typescript
// app/api/v1/content/route.ts
export async function POST(req: Request) {
  const userId = req.headers.get('x-user-id')!

  // Create new content
  const content = await prisma.content.create({ data: { userId, ...body } })

  // Invalidate cache — next GET will fetch fresh from DB
  await invalidateCache(CacheKeys.userContent(userId))

  return Response.json({ content }, { status: 201 })
}
```

### What to cache vs not cache

```typescript
// ✅ Cache these — read-heavy, changes infrequently
// - user content list (TTL: 60s)
// - analytics summary (TTL: 300s — fetched by Cron anyway)
// - connected platforms list (TTL: 300s)

// ❌ Never cache these
// - auth/JWT verification — security critical, always fresh
// - payment/subscription status — must be real-time
// - content status during generation — changes rapidly
```

## Trade-offs

| | Redis cache | No cache | Next.js fetch cache |
|---|---|---|---|
| Latency | ✅ ~1ms | ❌ 20–100ms DB | ✅ ~0ms (in-memory) |
| Shared across instances | ✅ | N/A | ❌ per-instance |
| Invalidation control | ✅ explicit | N/A | ⚠️ limited |
| Cost | Upstash free tier | None | None |
| ContentPilot choice | ✅ | — | Static pages only |

## Interview Q&A

**Q: What is caching and why is it used?**
Caching stores the result of an expensive operation in fast memory so subsequent requests skip the work entirely. It is used because memory reads are orders of magnitude faster than disk reads or network calls — a Redis lookup takes ~1ms vs 20–100ms for a DB query. Any system with repeated reads of the same data benefits from caching.

**Q: What is a cache TTL and why do you need it?**
TTL (Time To Live) is the duration after which a cached value automatically expires and is removed. It acts as a safety net — even if cache invalidation logic fails or is missed, stale data eventually purges itself. Without TTL, a bug in invalidation logic means users see outdated data forever.

**Q: What is cache invalidation and why is it considered hard?**
Cache invalidation is the process of removing or updating cached data when the underlying source changes. It is hard because you must identify every cache key affected by a write — in a complex system a single DB update can affect many cached views. The two strategies are: delete on write (simple, causes one cache miss) and write-through (update cache and DB together, more complex but no miss).

**Q: What is a cache stampede and how do you prevent it?**
A cache stampede happens when many requests arrive simultaneously for the same expired key — they all miss the cache and simultaneously hit the DB, causing a spike. Prevention: use a mutex lock so only one request fetches from DB while others wait, or use probabilistic early expiration to refresh the cache before it expires.

**Q: What data should never be cached?**
Security-critical data like auth tokens and session state — must always be verified fresh. Rapidly changing data like real-time stock prices or live scores — cache is always stale. Payment and subscription status — stale data here has financial consequences. The rule is: cache data where a brief window of staleness is acceptable.

---

Related: [[Phase 5.3 - Cloudinary Ephemeral]] [[Phase 6.2 - CDN and Edge Config]]