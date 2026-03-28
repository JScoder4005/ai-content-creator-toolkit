---
tags: [system-design, phase-2, validation, zod, api]
created: 2026-03-28
phase: 2
---
# Phase 2.2 - Request Validation (Zod)

## What is it?
Parsing and type-checking incoming request data at the API boundary before any business logic runs.

## Why does it matter?
TypeScript only protects at compile time. Runtime validation with Zod catches bad data from clients, bots, or bugs — before you waste a Claude API call or corrupt the DB.

## How it works
1. Request arrives at route handler
2. `ZodSchema.safeParse(body)` runs immediately
3. If invalid → return 400 with structured error, stop
4. If valid → `result.data` is typed and safe to use downstream
5. [[request_validation_flow.svg]]

## Applied to ContentPilot
Schema lives in `lib/schemas/generate.ts`:
```ts
export const GenerateSchema = z.object({
  topic: z.string().min(3).max(200),
  platform: z.enum(['twitter', 'linkedin', 'instagram']),
  tone: z.enum(['professional', 'casual', 'witty']).optional().default('professional'),
})
export type GenerateInput = z.infer<typeof GenerateSchema>
```
`safeParse` in the route — never `parse` (throws, harder to handle).

## What to learn vs ignore
Learn: `z.object`, `z.string`, `z.enum`, `z.optional`, `z.default`, `safeParse`, `error.flatten()`
Ignore now: transforms, async refinements, superRefine

## Trade-offs
- Zod: type inference + structured errors, costs ~13kb bundle
- Manual checks: zero deps, verbose, no type inference

## Interview questions

**Q: Why server-side validation even if the client validates?**
Client is untrusted. Anyone can bypass frontend validation with cURL or Postman. Server-side is the actual security boundary — client check is only UX.

**Q: `parse` vs `safeParse` — when to use which?**
`parse` throws a ZodError on failure — use in scripts where exceptions are fine. `safeParse` returns `{ success, data | error }` and never throws — always use in API routes so you control the response.

**Q: Where in the request lifecycle should validation run?**
First, before everything. Before auth, before DB, before external APIs. Fail fast — don't waste compute on an invalid request.

**Q: Why 400 not 422?**
422 is more semantically precise but 400 is the de facto standard in REST APIs. Both are acceptable — what matters is consistency. ContentPilot uses 400.

---
Related: [[Phase 2.1 - REST API Design]] [[Phase 2.3 - Authentication JWT]]