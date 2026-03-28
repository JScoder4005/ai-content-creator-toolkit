---
tags: [system-design, phase-2, error-handling, api]
created: 2026-03-28
phase: 2
---
# Phase 2.5 - Error Handling

## What is it?
Classifying, logging, and responding to errors consistently — giving the server full detail and the client only safe, predictable information.

## Why does it matter?
Inconsistent error handling leaks internal system details to attackers, breaks frontend error parsing, and makes debugging harder. One central pattern fixes all three.

## How it works

![[error_handling_contentpilot.svg]]

1. Error thrown anywhere in the route handler
2. Central `handleError` catches and classifies it
3. Operational error → specific message + correct status code
4. Unknown error → generic 500, full detail only in server logs
5. Client always gets `{ error, code }` — never a stack trace

## Error categories

| Type | Status | Client message |
|---|---|---|
| Validation | 400 | Specific — "Invalid request body" |
| Unauthorized | 401 | Generic — "Unauthorized" |
| Not found | 404 | Specific — "Post not found" |
| Rate limit | 429 | "Rate limit exceeded" + Retry-After |
| Claude API fail | 502 | "Something went wrong" |
| DB error | 500 | "Something went wrong" |
| Unknown bug | 500 | "Something went wrong" |

## Applied to ContentPilot

**Custom error classes:**
```typescript
// lib/errors.ts
export class AppError extends Error {
  constructor(
    public message: string,
    public statusCode: number,
    public code: string,
    public isOperational = true
  ) {
    super(message)
    this.name = 'AppError'
  }
}

export class ValidationError extends AppError {
  constructor(message: string) {
    super(message, 400, 'VALIDATION_ERROR')
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string) {
    super(`${resource} not found`, 404, 'NOT_FOUND')
  }
}

export class UnauthorizedError extends AppError {
  constructor() {
    super('Unauthorized', 401, 'UNAUTHORIZED')
  }
}
```

**Central error handler:**
```typescript
// lib/errorHandler.ts
import { AppError } from './errors'
import { NextResponse } from 'next/server'

export function handleError(error: unknown): NextResponse {
  if (error instanceof AppError && error.isOperational) {
    console.error({
      code: error.code,
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
    })
    return NextResponse.json(
      { error: error.message, code: error.code },
      { status: error.statusCode }
    )
  }

  console.error({
    message: 'Unexpected error',
    error,
    stack: error instanceof Error ? error.stack : null,
    timestamp: new Date().toISOString(),
  })

  return NextResponse.json(
    { error: 'Something went wrong', code: 'INTERNAL_ERROR' },
    { status: 500 }
  )
}
```

**Usage in every route:**
```typescript
export async function POST(req: Request) {
  try {
    // ... route logic ...
  } catch (error) {
    return handleError(error)
  }
}
```

## What to learn vs ignore
Learn: `AppError` pattern, `isOperational` flag, `{ error, code }` response shape, central handler, try/catch in every route
Ignore now: Sentry/Datadog error monitoring — production concern, covered in Phase 7

## Trade-offs
- Custom error classes: consistent, typed, flexible — medium boilerplate
- Generic try/catch: low boilerplate — inconsistent across routes
- ContentPilot uses custom error classes

## Interview questions

**Q: Why never send stack traces to the client?**
Stack traces expose file paths, library versions, DB schema details — all useful for an attacker. Client only needs a safe message and a code.

**Q: Operational error vs programmer error?**
Operational = expected (bad input, not found, rate limit). Give client specific message. Programmer = unexpected bug (null reference, DB crash). Always return generic 500, full detail in server logs only.

**Q: What should the error response shape look like?**
Always `{ error: string, code: string }`. `error` is human-readable, `code` is machine-readable for the frontend to switch on. Never include stack, internal IDs, or raw DB messages.

**Q: Where should error handling logic live in Next.js?**
Central `handleError` function called from the `catch` block of every route. Never handle errors ad-hoc inline — inconsistent shapes and missed logging.

**Q: What status code for unexpected server errors?**
500 Internal Server Error. Body: `{ error: 'Something went wrong', code: 'INTERNAL_ERROR' }` — nothing more.

---
Related: [[Phase 2.4 - Authentication JWT]] [[Phase 2.6 - API Versioning]]