---
tags: [system-design, phase-3, database, transactions, postgresql]
created: 2026-04-26
phase: 3
---

# Phase 3.4 - DB Transactions

## What is it?

A transaction groups multiple DB operations into a single atomic unit. Either all operations succeed and are committed, or any failure triggers a rollback that undoes everything. No partial state.

## Why does it matter?

ContentPilot's publish flow does two things: update `content.status` to `PUBLISHED` and create a `PublishedPost` row. If the second operation fails after the first succeeds, content is marked published but no post record exists. The data is corrupt. A transaction prevents this.

## How it works

![[db_transactions_contentpilot.svg|636]]

**ACID properties:**
- **Atomic** — all or nothing, no partial writes
- **Consistent** — DB moves from one valid state to another
- **Isolated** — concurrent transactions don't see each other's uncommitted changes
- **Durable** — committed data survives crashes

## Applied to ContentPilot

### Prisma `$transaction` — interactive

```typescript
// lib/publishing.ts
import { prisma } from '@/lib/prisma'

export async function publishContent(contentId: string, platformId: string, externalId: string) {
  return await prisma.$transaction(async (tx) => {
    // Op 1: mark content as published
    const content = await tx.content.update({
      where: { id: contentId },
      data: { status: 'PUBLISHED' },
    })

    // Op 2: create the published post record
    const post = await tx.publishedPost.create({
      data: {
        contentId,
        platformId,
        externalId,
        status: 'PUBLISHED',
        publishedAt: new Date(),
      },
    })

    // Op 3: create initial analytics row
    await tx.analytics.create({
      data: { postId: post.id },
    })

    return { content, post }
    // If any op throws → automatic ROLLBACK, none of the above persists
  })
}
```

### Prisma `$transaction` — batch (simpler, non-interactive)

```typescript
// When operations don't depend on each other's results
await prisma.$transaction([
  prisma.content.update({
    where: { id: contentId },
    data: { status: 'FAILED' },
  }),
  prisma.publishedPost.update({
    where: { id: postId },
    data: { status: 'FAILED' },
  }),
])
```

### When to use interactive vs batch

```typescript
// Use INTERACTIVE when: op2 needs result of op1
const post = await tx.publishedPost.create({ data: { contentId } })
await tx.analytics.create({ data: { postId: post.id } })  // needs post.id

// Use BATCH when: operations are independent
await prisma.$transaction([
  prisma.content.update(...),
  prisma.publishedPost.update(...),
])
```

### Timeout configuration

```typescript
// Default timeout is 5s — increase for slow operations
await prisma.$transaction(async (tx) => {
  // ... operations
}, {
  maxWait: 5000,   // max time to acquire a connection (ms)
  timeout: 10000,  // max transaction duration (ms)
})
```

## Trade-offs

| | With transaction | Without transaction |
|---|---|---|
| Data consistency | ✅ guaranteed | ❌ partial writes possible |
| Performance | Slightly slower (lock overhead) | Faster |
| Complexity | Medium | Low |
| Use when | Multiple related writes | Single write operations |

## Interview Q&A

**Q: What is a database transaction and why do you need one?**
A transaction groups multiple operations into a single atomic unit — all succeed or all fail. Without it, a crash or error between two related writes leaves the DB in a corrupt partial state. Example: ContentPilot marking content PUBLISHED and creating the PublishedPost record must both succeed or both fail.

**Q: What does ACID stand for?**
Atomic (all or nothing), Consistent (valid state to valid state), Isolated (concurrent transactions don't interfere), Durable (committed data survives crashes). All four are guaranteed by PostgreSQL transactions.

**Q: What is the difference between interactive and batch transactions in Prisma?**
Interactive (`$transaction(async tx => {...})`) runs operations sequentially where each can use results from the previous — necessary when op2 depends on op1's output. Batch (`$transaction([op1, op2])`) runs independent operations as a single atomic unit without needing intermediate results.

**Q: What happens if an error is thrown inside a Prisma transaction?**
Prisma automatically rolls back all operations in that transaction. Nothing is written to the DB. The error propagates up to the calling code for handling.

**Q: When should you NOT use a transaction?**
Single write operations — no atomicity needed. Read-only operations — no writes to protect. Very long-running operations — transactions hold locks, blocking other queries. In those cases, use idempotent operations with retry logic instead.

---

Related: [[Phase 3.3 - Indexing and Queries]] [[Phase 4.1 - Vercel Cron Jobs]]