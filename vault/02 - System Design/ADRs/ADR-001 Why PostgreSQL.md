---
tags: [adr, database]
created: 2026-03-27
status: Accepted
---

# ADR-001: Why PostgreSQL over MongoDB

## Status
Accepted

## Context
ContentPilot needs to store posts, schedules, and user data.
Considered MongoDB (flexible schema) vs PostgreSQL (relational).

## Decision
Use PostgreSQL via Supabase.

## Alternatives considered
- MongoDB — flexible but no strong relations, no ACID guarantees
- SQLite — too limited for multi-user eventually
- PlanetScale — MySQL-based, good but less Prisma support

## Consequences
- Strong relational integrity between users/posts
- Prisma ORM works excellently with PostgreSQL
- Supabase free tier covers our needs
- Harder to change schema later but Prisma migrations handle this

---
[[01 - Projects/ContentPilot/Architecture v1]]
