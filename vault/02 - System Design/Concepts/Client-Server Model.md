---
tags: [concept]
created: 2026-03-27
---

# Client-Server Model

## What is it?
A client sends a request, a server processes it and sends back a response. The browser is the client, Vercel is the server.

## Why does it matter?
Every web app works this way. Understanding this is the foundation of all system design.

## How it works
Browser types URL → sends HTTP request → server processes → sends back HTML → browser renders it.
![[contentpilot_request_journ.svg]]

## Applied to ContentPilot
- Client = your browser opening contentpilot.com
- Server = Next.js running on Vercel
- Request = GET /dashboard
- Response = your posts, queue, history

## Trade-offs
| Approach | Pro | Con |
|---|---|---|
| Server-side render | Fast first load, SEO | Server does more work |
| Client-side render | Interactive, dynamic | Slower first load |

## Interview angle
"Every system has clients and servers. In ContentPilot, the browser is the client, Vercel edge is the server, and they communicate over HTTP."

---
Related: [[01 - Projects/ContentPilot/Architecture v1]]