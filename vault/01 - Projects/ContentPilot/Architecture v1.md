---
tags: [contentpilot, architecture, system-design]
created: 2026-03-27
version: v1
---

# ContentPilot — Architecture v1

## Overview
Content automation dashboard built with Next.js 14, Claude API,
YouTube Data API, Meta Graph API, Cloudinary, Supabase, and Vercel Cron.

## Current architecture diagram
![[Diagrams/contentpilot-v1.png]]

## Components

### Frontend
- Next.js 14 App Router
- shadcn/ui + Tailwind CSS
- Three.js animations

### API layer
- /api/generate — calls Claude API
- /api/publish/youtube — YouTube Data API v3
- /api/publish/instagram — Meta Graph API
- /api/schedule — writes to DB queue

### Data layer
- Supabase (PostgreSQL)
- Prisma ORM
- Posts table: id, content, platform, scheduled_at, status

### External services
- Cloudinary — media storage
- Vercel Cron — job scheduler

## Trade-offs
[[02 - System Design/ADRs/ADR-001 Why PostgreSQL]]
[[02 - System Design/ADRs/ADR-002 Why Cloudinary]]
[[02 - System Design/ADRs/ADR-003 Why Vercel Cron]]
