---
tags: [system-design, phase-3, database, indexing, postgresql]
created: 2026-04-26
phase: 3
---

# Phase 3.3 - Indexing and Queries

## What is it?

Indexes are auxiliary data structures PostgreSQL maintains alongside your tables to speed up lookups. Without them, every query scans every row. With them, PostgreSQL jumps directly to the matching rows via a B-tree.

## Why does it matter?

ContentPilot's Vercel Cron queries `content` where `status = READY` on every run. Without an index on `status`, Postgres reads every row in the table. At 10k rows that's fine. At 1M rows that's a timeout.

## How it works

![[indexing_queries_contentpilot.svg|667]]

PostgreSQL uses a B-tree by default. A B-tree is a balanced tree where each node holds sorted values — lookup is O(log n) instead of O(n) full scan. The index stores a sorted copy of the column plus a pointer to the actual row.

**When NOT to index:**
- Low cardinality columns with few unique values (boolean, small enums) — index overhead exceeds benefit
- Columns rarely used in `WHERE`, `JOIN`, or `ORDER BY`
- Write-heavy tables — every insert/update must also update the index

## Applied to ContentPilot

### Indexes in Prisma schema

```prisma
model Content {
  id        String        @id @default(uuid())
  userId    String
  status    ContentStatus @default(DRAFT)
  createdAt DateTime      @default(now())

  @@index([userId])           // filter all content by user
  @@index([status])           // Cron: WHERE status = 'READY'
  @@index([userId, status])   // composite: user's ready content
  @@index([createdAt])        // ORDER BY createdAt DESC
}

model PublishedPost {
  id         String @id @default(uuid())
  contentId  String
  platformId String

  @@index([contentId])    // join: content → posts
  @@index([platformId])   // join: platform → posts
}

model Analytics {
  id     String @id @default(uuid())
  postId String @unique   // @unique auto-creates index
}
```

### Query patterns in ContentPilot

```typescript
// Cron: fetch all READY content — uses @@index([status])
const readyItems = await prisma.content.findMany({
  where: { status: 'READY' },
})

// Dashboard: user's content newest first — uses @@index([userId, createdAt])
const userContent = await prisma.content.findMany({
  where: { userId },
  orderBy: { createdAt: 'desc' },
  take: 20,
  skip: page * 20,  // pagination
})

// Avoid N+1: fetch content with posts in one query
const contentWithPosts = await prisma.content.findMany({
  where: { userId },
  include: { posts: true },  // single JOIN query, not N queries
})

// Raw SQL for complex aggregation Prisma can't express
const stats = await prisma.$queryRaw`
  SELECT
    platform_id,
    COUNT(*) as total_posts,
    SUM(a.views) as total_views
  FROM published_posts pp
  LEFT JOIN analytics a ON a.post_id = pp.id
  WHERE pp.content_id = ${contentId}
  GROUP BY platform_id
`
```

### EXPLAIN ANALYZE — check if index is used

```sql
EXPLAIN ANALYZE
SELECT * FROM content
WHERE user_id = 'abc' AND status = 'READY';

-- Look for: "Index Scan" = good, "Seq Scan" = needs index
```

### N+1 problem — the most common query mistake

```typescript
// BAD — N+1: 1 query for content + N queries for posts
const content = await prisma.content.findMany({ where: { userId } })
for (const item of content) {
  const posts = await prisma.publishedPost.findMany({
    where: { contentId: item.id },  // N separate queries
  })
}

// GOOD — single JOIN via include
const content = await prisma.content.findMany({
  where: { userId },
  include: { posts: true },  // 1 query total
})
```

## Trade-offs

| | Indexed column | Non-indexed column |
|---|---|---|
| Read speed | O(log n) | O(n) |
| Write speed | Slower (index update) | Faster |
| Storage | Extra disk space | None |
| Best for | High cardinality, frequent reads | Rarely queried columns |

## Interview Q&A

**Q: What is a database index and how does it work?**
An index is an auxiliary data structure — usually a B-tree — that stores a sorted copy of a column's values alongside pointers to the actual rows. Instead of scanning every row (O(n)), PostgreSQL traverses the tree to find matching rows in O(log n).

**Q: When should you NOT add an index?**
Low cardinality columns (boolean, tiny enums) — the index doesn't help much because PostgreSQL still needs to fetch many rows. Write-heavy tables — every insert and update must also update the index, adding overhead. Columns never used in WHERE, JOIN, or ORDER BY — dead weight.

**Q: What is a composite index and when do you use one?**
An index on multiple columns — `@@index([userId, status])`. Used when queries frequently filter on both columns together. Column order matters — the index is useful for queries on `userId` alone or `userId + status` together, but not `status` alone.

**Q: What is the N+1 query problem?**
Fetching a list of N records then making N additional queries to fetch related data — one per record. Results in N+1 total queries instead of 1. Fix: use `include` in Prisma to fetch related data in a single JOIN query.

**Q: When do you use `prisma.$queryRaw`?**
When Prisma's query builder can't express what you need — complex aggregations, window functions, CTEs, or multi-table GROUP BY. Use sparingly and always parameterise values (no string interpolation — SQL injection risk).

---

Related: [[Phase 3.2 - Prisma ORM]] [[Phase 3.4 - DB Transactions]]