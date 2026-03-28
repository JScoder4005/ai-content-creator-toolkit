---
tags:
  - concept
created: 2026-03-27
---

# CDN and Edge Networks

## What is it?
A network of servers spread across the world that serve 
content from the location nearest to the user.

## Why does it matter?
Reduces latency dramatically. Instead of Bangalore to US 
(200ms), you get Bangalore to Mumbai (20ms).

## How it works
1. You deploy your app to Vercel
2. Vercel replicates it to 30+ edge locations globally
3. When you visit from Bangalore, Mumbai edge serves you
4. Static files (HTML, JS, CSS) are cached at the edge

![[cdn_edge_network.svg|644]]

## Applied to ContentPilot
- Vercel CDN serves Next.js app from Mumbai edge
- Three.js library cached at edge after first load
- Dynamic data (posts, schedule) still hits Supabase origin
- Result: dashboard loads in ~170ms from Bangalore

## Trade-offs
| Approach | Pro | Con |
|---|---|---|
| Vercel CDN | Free, global, zero config | Less control |
| Self-hosted CDN | Full control | Expensive, complex |
| No CDN | Simple | Slow for global users |

## Interview angle
"ContentPilot uses Vercel's edge network so users globally 
get fast load times. Static assets are cached at the nearest 
edge, dynamic data fetches happen after the shell loads."

---
Related: [[01 - Projects/ContentPilot/Architecture v1]]
[[02 - System Design/Concepts/Client-Server Model]]