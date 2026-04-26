---
tags: [system-design, phase-3, prisma, orm, database]
created: 2026-04-26
phase: 3
---

# Phase 3.2 - Prisma ORM

## What is it?

Prisma is three tools in one: a schema language to define your data models, a migration system to version your DB changes, and an auto-generated type-safe query client. The schema is the single source of truth — everything else is generated from it.

## Why does it matter?

Raw SQL returns `any`. A typo in a column name only fails at runtime. Prisma generates a client from your exact schema — `prisma.user.findUnique()` returns `User | null`, TypeScript knows the shape, and wrong field names fail at compile time before they ever hit production.

## How it works

![[prisma_orm_workflow.svg]]

1. Define models in `schema.prisma`
2. `prisma migrate dev` creates a SQL migration file and applies it
3. `prisma generate` generates the typed client
4. Import client in route handlers — fully typed queries
5. `prisma db seed` inserts test data via `prisma/seed.ts`

## Applied to ContentPilot

### Setup

```bash
npm install prisma @prisma/client
npx prisma init
```

### Singleton client

```typescript
// lib/prisma.ts
import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: ['query', 'error', 'warn'],
  })

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma
}
```

Singleton prevents connection pool exhaustion on Vercel hot reloads. Without it, every hot reload opens a new pool — Supabase connection limit hit fast.

### Common queries

```typescript
// Create content after Claude generates caption
const content = await prisma.content.create({
  data: { userId, topic, caption, tone, status: 'READY' },
})

// Fetch ready content with posts + analytics
const readyContent = await prisma.content.findMany({
  where: { userId, status: 'READY' },
  include: {
    posts: {
      include: { platform: true, analytics: true },
    },
  },
  orderBy: { createdAt: 'desc' },
})

// Update status after publishing
await prisma.content.update({
  where: { id: contentId },
  data: { status: 'PUBLISHED' },
})

// Upsert analytics on every Cron fetch
await prisma.analytics.upsert({
  where: { postId },
  update: { views, likes, shares, fetchedAt: new Date() },
  create: { postId, views, likes, shares },
})
```

### Migrations

```bash
# Dev: create migration file + apply + regenerate client
npx prisma migrate dev --name add_content_table

# Production: apply pending migrations only
npx prisma migrate deploy

# After pulling schema changes from git
npx prisma generate
```

### Seed script

```typescript
// prisma/seed.ts
import { PrismaClient } from '@prisma/client'
import bcrypt from 'bcryptjs'

const prisma = new PrismaClient()

async function main() {
  const user = await prisma.user.upsert({
    where: { email: 'uday@contentpilot.dev' },
    update: {},
    create: {
      email: 'uday@contentpilot.dev',
      passwordHash: await bcrypt.hash('password123', 10),
      plan: 'PRO',
    },
  })

  await prisma.content.create({
    data: {
      userId: user.id,
      topic: 'KTM 390 Adventure review',
      caption: 'The best ADV bike under 5 lakhs.',
      tone: 'CASUAL',
      status: 'READY',
    },
  })

  console.log('Seeded:', user.email)
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
```

```json
// package.json
{
  "prisma": {
    "seed": "ts-node prisma/seed.ts"
  }
}
```

```bash
npx prisma db seed
```

## Trade-offs

| | Prisma | Raw SQL | Drizzle ORM |
|---|---|---|---|
| Type safety | ✅ fully generated | ❌ manual | ✅ schema-first |
| Migration management | ✅ built-in | ❌ manual | ⚠️ separate tool |
| Query flexibility | ⚠️ complex needs `$queryRaw` | ✅ full control | ✅ |
| Bundle size | ~500kb | 0 | ~30kb |
| ContentPilot choice | ✅ | — | — |

## Interview Q&A

**Q: What is an ORM and why use one over raw SQL?**
An ORM maps DB tables to code objects so you query using your language instead of SQL strings. Benefits: type safety, auto-completion, migration management, SQL injection protection by default. Downside: complex queries sometimes need `prisma.$queryRaw` fallback.

**Q: What does `prisma generate` do?**
Reads `schema.prisma` and generates the Prisma Client — a fully typed query builder tailored to your exact schema. Must run after every schema change. On Vercel it runs automatically via `postinstall`.

**Q: Why singleton Prisma Client in Next.js?**
Next.js hot-reloads in development, creating a new module instance each time. Without a singleton, each reload creates a new `PrismaClient` and opens a new connection pool. Supabase has a connection limit — exhausted quickly without the singleton stored on `globalThis`.

**Q: `prisma migrate dev` vs `prisma migrate deploy`?**
`migrate dev` creates a migration file from schema changes, applies it, regenerates client — development only. `migrate deploy` applies pending migrations without creating new ones — production CI/CD. Never run `migrate dev` in production as it can prompt destructive action confirmation.

**Q: What does `upsert` do and when do you use it?**
Update if exists, create if not — in a single atomic operation. ContentPilot uses it for analytics: Vercel Cron fetches fresh stats without knowing if a row already exists. `upsert` handles both cases without a separate read.

**Q: What is seeding and why does it matter?**
Populates the DB with initial or test data via a script. In development it gives realistic data without manual inserts. In staging it creates known test accounts. Never run in production unless for explicit initial setup like admin accounts.

---

Related: [[Phase 3.1 - DB Schema Design]] [[Phase 3.3 - Indexing and Queries]]