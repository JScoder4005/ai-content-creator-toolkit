---
tags: [system-design, phase-3, database, schema, prisma]
created: 2026-04-26
phase: 3
---

# Phase 3.1 - DB Schema Design

## What is it?

Designing the tables, columns, relationships, and constraints that define how ContentPilot stores its data in PostgreSQL.

## Why does it matter?

A bad schema is expensive to fix later — migrations on a live DB with real data are painful. Getting the shape right before writing any code means you never have to untangle a mess of orphaned rows, missing foreign keys, or status fields stored as raw strings.

## How it works

![[contentpilot_db_schema.svg|610]]

Five tables, three relationship types:

- **Users → Content** (1:N) — one user owns many pieces of content
- **Users → Platforms** (1:N) — one user can connect multiple platforms
- **Content → PublishedPosts** (1:N) — one content item can be published to many platforms
- **Platforms → PublishedPosts** (1:N) — one platform receives many published posts
- **PublishedPosts → Analytics** (1:1) — one analytics row per published post

## Applied to ContentPilot

### Prisma schema

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

enum Plan {
  FREE
  PRO
}

enum Tone {
  PROFESSIONAL
  CASUAL
  WITTY
}

enum ContentStatus {
  DRAFT
  GENERATING
  READY
  PUBLISHED
  FAILED
}

enum PlatformType {
  YOUTUBE
  INSTAGRAM
}

enum PostStatus {
  SCHEDULED
  PUBLISHED
  FAILED
}

model User {
  id           String     @id @default(uuid())
  email        String     @unique
  passwordHash String
  plan         Plan       @default(FREE)
  createdAt    DateTime   @default(now())
  content      Content[]
  platforms    Platform[]
}

model Content {
  id        String        @id @default(uuid())
  userId    String
  user      User          @relation(fields: [userId], references: [id], onDelete: Cascade)
  topic     String
  caption   String
  tone      Tone          @default(PROFESSIONAL)
  status    ContentStatus @default(DRAFT)
  createdAt DateTime      @default(now())
  posts     PublishedPost[]
}

model Platform {
  id          String       @id @default(uuid())
  userId      String
  user        User         @relation(fields: [userId], references: [id], onDelete: Cascade)
  type        PlatformType
  accessToken String
  posts       PublishedPost[]
}

model PublishedPost {
  id          String     @id @default(uuid())
  contentId   String
  content     Content    @relation(fields: [contentId], references: [id], onDelete: Cascade)
  platformId  String
  platform    Platform   @relation(fields: [platformId], references: [id], onDelete: Cascade)
  externalId  String?
  status      PostStatus @default(SCHEDULED)
  scheduledAt DateTime?
  publishedAt DateTime?
  analytics   Analytics?
}

model Analytics {
  id        String        @id @default(uuid())
  postId    String        @unique
  post      PublishedPost @relation(fields: [postId], references: [id], onDelete: Cascade)
  views     Int           @default(0)
  likes     Int           @default(0)
  shares    Int           @default(0)
  fetchedAt DateTime      @default(now())
}
```

### Key design decisions

**UUIDs not integers for PKs** — UUIDs can be generated at the edge without a DB round-trip. Integers require a DB sequence call. Also prevents sequential ID enumeration attacks.

**`status` enum on Content** — `DRAFT | GENERATING | READY | PUBLISHED | FAILED`. Vercel Cron picks up `READY` items to publish. Enums are enforced at the DB level — raw strings allow silent typo bugs.

**`externalId` on PublishedPost** — the ID YouTube/Instagram returns after publishing. Required to fetch analytics later via their APIs.

**Platforms table per user** — one user can connect multiple platforms. `accessToken` encrypted at rest (Phase 7). Supports multi-account per user.

**Analytics as a separate table** — fetched periodically by Vercel Cron, not real time. 1:1 with PublishedPost enforced by `@unique` on `postId`. Easier to index and extend than JSON columns.

**`onDelete: Cascade`** — delete a user, all their data goes with it. No orphaned rows.

## Trade-offs

| Decision | Choice | Alternative | Why |
|---|---|---|---|
| PK type | UUID | Auto-increment int | Edge-safe, no enumeration attacks |
| Status tracking | Enum | Boolean flags | Single source of truth, DB-enforced |
| Analytics storage | Separate table | JSON column on PublishedPost | Queryable, indexable, extensible |
| Token storage | Platform table | Env variable | Supports multi-account per user |

## Interview Q&A

**Q: Why use UUIDs over auto-increment integers for primary keys?**
UUIDs can be generated anywhere — client, edge function, app server — without a DB round-trip. Auto-increment integers require a DB sequence call. UUIDs also prevent sequential enumeration attacks where an attacker guesses IDs by incrementing.

**Q: What is a foreign key and what does `onDelete: Cascade` do?**
A foreign key is a column that references the primary key of another table, enforcing referential integrity — you can't have a `Content` row pointing to a `userId` that doesn't exist. `onDelete: Cascade` means when the referenced row is deleted, all rows referencing it are automatically deleted too. Prevents orphaned data.

**Q: Why use enums for status fields instead of strings?**
Enums are enforced at the DB level — you can't insert an invalid value. Strings allow bugs like `"publisehd"` to silently enter the DB and break conditional logic. Enums also make valid states explicit and self-documenting.

**Q: What is a junction table and when do you need one?**
A table that sits between two others to represent a many-to-many relationship. `PublishedPost` is a junction between `Content` and `Platform` — one content item can be published to many platforms, one platform receives many content items. It also carries relationship-specific data: status, scheduledAt, externalId.

**Q: Why store analytics in a separate table instead of columns on PublishedPost?**
Separation of concerns — publishing and analytics fetching are independent operations run at different times. A separate table is easier to index, query, and extend. Adding new metrics (comments, saves) means adding columns to Analytics without touching PublishedPost.

---

Related: [[Phase 2.6 - API Versioning]] [[Phase 3.2 - Prisma ORM]]