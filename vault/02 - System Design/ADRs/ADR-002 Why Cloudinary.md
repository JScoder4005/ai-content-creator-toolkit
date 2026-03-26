---
tags: [adr, storage, media]
created: 2026-03-27
status: Accepted
---

# ADR-002: Why Cloudinary for media storage

## Status
Accepted

## Context
Instagram and YouTube APIs require a publicly accessible media URL
before posting. We need somewhere to temporarily host video/image files.

## Decision
Use Cloudinary free tier.

## Alternatives considered
- AWS S3 — powerful but requires AWS account setup + IAM
- Supabase Storage — simpler but less CDN optimisation
- Self-hosted — too much infra overhead

## Consequences
- Free tier: 25GB storage, 25GB bandwidth/month
- Built-in image/video transformations
- Public URLs available immediately after upload
-  Media deleted immediately after successful platform upload (This is called ephemeral storage in system design)
- Acts as ephemeral staging, not permanent storage
- Keeps usage well within free tier limits

---
[[01 - Projects/ContentPilot/Architecture v1]]
