---
tags: [system-design, phase-6, cdn, edge, vercel, performance]
created: 2026-04-26
phase: 6
---

# Phase 6.2 - CDN and Edge Config

## What is it?

A CDN (Content Delivery Network) is a globally distributed network of servers that caches and serves content from the location closest to the user. Edge Config is Vercel's ultra-fast key-value store that runs at the CDN edge before your app code even executes.

## Why does it matter?

A user in Bangalore hitting a server in US East adds ~200ms of network latency on every request. A CDN edge node in Mumbai serves the same content in ~5ms. For static assets and cacheable responses this is a free performance win — no code change required, just correct cache headers.

## How it works

![[cdn_edge_config_contentpilot.svg]]

**CDN cache hit** — request served by the nearest edge node instantly. Origin server never involved.

**CDN cache miss** — edge node fetches from origin, caches the response, serves subsequent requests locally.

**Cache-Control headers** determine what gets cached, for how long, and by whom:
- `max-age=31536000, immutable` — static assets, cache forever
- `no-store` — API routes with user data, never cache
- `no-cache` — revalidate with origin before serving

## Applied to ContentPilot

### Cache-Control headers in Next.js

```typescript
// Static assets — JS, CSS, images (Next.js handles automatically)
// Cache-Control: public, max-age=31536000, immutable

// API routes — never cache user-specific data
export async function GET(req: Request) {
  const data = await prisma.content.findMany({ where: { userId } })

  return new Response(JSON.stringify(data), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',  // never cache API responses
    },
  })
}

// Public pages — revalidate every 60 seconds
// next.config.ts
export default {
  async headers() {
    return [
      {
        source: '/blog/:path*',
        headers: [
          { key: 'Cache-Control', value: 's-maxage=60, stale-while-revalidate=300' }
        ],
      },
    ]
  },
}
```

### Vercel Edge Config — feature flags at the edge

Edge Config is a global key-value store that Vercel edge functions read in ~1ms — before your route handler runs. Use it for feature flags, maintenance mode, and A/B config.

```bash
npm install @vercel/edge-config
```

```typescript
// lib/edgeConfig.ts
import { get } from '@vercel/edge-config'

export async function isFeatureEnabled(flag: string): Promise<boolean> {
  return (await get<boolean>(flag)) ?? false
}

export async function isMaintenanceMode(): Promise<boolean> {
  return (await get<boolean>('maintenance_mode')) ?? false
}
```

```typescript
// middleware.ts — check maintenance mode at edge before any route runs
import { isMaintenanceMode } from '@/lib/edgeConfig'

export async function middleware(req: NextRequest) {
  if (await isMaintenanceMode()) {
    return NextResponse.json(
      { error: 'ContentPilot is under maintenance. Back soon.' },
      { status: 503 }
    )
  }
  // ... rest of middleware (rate limit, JWT verify)
}
```

### next.config.ts — CDN and security headers

```typescript
// next.config.ts
const nextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Security (Phase 7.1)
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          // CDN behaviour
          { key: 'Vary', value: 'Accept-Encoding' },
        ],
      },
      {
        source: '/api/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store' },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ]
  },
}
```

### Vercel's built-in CDN — zero config

Vercel automatically puts all deployments behind their global CDN (Vercel Edge Network). You get:
- Static assets cached at edge globally
- Automatic gzip + Brotli compression
- HTTP/2 push
- TLS termination at edge

You only need to set correct `Cache-Control` headers — Vercel handles the rest.

## Trade-offs

| | Vercel CDN | Cloudflare CDN | No CDN |
|---|---|---|---|
| Setup | ✅ Zero — built in | Manual DNS change | None |
| Global PoPs | 70+ | 300+ | N/A |
| Edge functions | ✅ Next.js middleware | ✅ Workers | N/A |
| Edge Config | ✅ Built in | ❌ | N/A |
| Cost | Included in Vercel | Free tier available | N/A |
| ContentPilot choice | ✅ | — | — |

## Interview Q&A

**Q: What is a CDN and how does it improve performance?**
A CDN is a globally distributed network of servers that cache content at locations close to users. Instead of every request travelling to a single origin server — which adds network latency proportional to distance — the CDN serves cached responses from the nearest edge node. A user in Bangalore gets content from Mumbai in ~5ms instead of from US East in ~200ms.

**Q: What is the difference between `max-age` and `s-maxage` in Cache-Control?**
`max-age` controls how long the browser caches the response. `s-maxage` controls how long shared caches (CDN, proxy) cache it — overrides `max-age` for CDN nodes. Use `s-maxage` when you want CDN to cache longer than the browser, or vice versa. `stale-while-revalidate` allows serving stale content while fetching a fresh copy in the background.

**Q: What does `immutable` mean in a Cache-Control header?**
`immutable` tells the browser the resource will never change for the duration of `max-age` — skip revalidation entirely. Used for content-hashed static assets like `_next/static/abc123.js`. The hash in the filename guarantees a new URL for new content, so the old URL can be cached forever.

**Q: What is an edge function and how does it differ from a serverless function?**
Both run on-demand without a persistent server. The difference is location — serverless functions run in one or a few regions (US East for Vercel), while edge functions run in every CDN PoP globally. Edge functions have lower latency but a restricted runtime — no Node.js APIs, no file system, limited execution time. Next.js middleware runs as an edge function.

**Q: What is Vercel Edge Config and when would you use it?**
Edge Config is a global key-value store readable at CDN edge nodes in ~1ms — before any route handler executes. Use it for data that must be checked on every request but changes rarely: feature flags, maintenance mode switches, A/B test config, IP blocklists. The alternative — fetching from a DB or Redis in middleware — adds 5–20ms to every single request.

---

Related: [[Phase 6.1 - Caching Strategy]] [[Phase 6.3 - Load Balancing]]