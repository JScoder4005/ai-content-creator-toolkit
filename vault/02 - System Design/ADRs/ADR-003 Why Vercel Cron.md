---
tags: [adr, scheduler, cron]
created: 2026-03-27
status: Accepted
---

# ADR-003: Why Vercel Cron over BullMQ

## Status
Accepted

## Context
Scheduled posts need a background job runner to check the queue
and fire posts at the right time.

## Decision
Use Vercel Cron (runs every 15 minutes via vercel.json).

## Alternatives considered
- BullMQ + Redis — powerful, retry logic, but needs Redis instance (~$10/mo)
- node-cron — only works if server is always running (not serverless)
- GitHub Actions — hacky, not designed for this

## Consequences
- Zero cost on Vercel hobby plan
- 15-minute minimum interval (good enough for scheduling)
- No persistent job state — status tracked in PostgreSQL instead
- Simple to reason about and debug

---
[[01 - Projects/ContentPilot/Architecture v1]]
