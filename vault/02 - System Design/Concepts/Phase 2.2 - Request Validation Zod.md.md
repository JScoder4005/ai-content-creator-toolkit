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
1. Why server-side validation even if client validates?
2. `parse` vs `safeParse` — when to use which?
3. Where in the request lifecycle should validation run?
4. Why 400 not 422 for validation errors?

---
Related: [[Phase 2.1 - REST API Design]] [[Phase 2.3 - Authentication JWT]]