---
tags: [system-design, phase-2, auth, jwt, cookies]
created: 2026-03-28
phase: 2
---
# Phase 2.3 - Authentication JWT

## What is it?
A stateless mechanism where the server issues a signed token on login. The client sends it back on every request; the server verifies the signature to confirm identity.

## Why does it matter?
HTTP is stateless — the server has no memory of previous requests. JWT gives the server a way to trust "this request is from userId X with role Y" without hitting the DB every time.

## How it works

![[jwt_anatomy.svg|569]]

JWT = Header . Payload . Signature (three base64 segments separated by dots)
- Header: algorithm (HS256), type (JWT)
- Payload: userId, role, iat, exp — readable but NOT encrypted
- Signature: HMAC-SHA256(header + payload + secret) — tamper-proof

![[jwt_auth_flow_contentpilot.svg|641]]

On every protected request:
1. Browser auto-sends cookie
2. Next.js middleware extracts JWT from cookie
3. `jwtVerify` checks signature + expiry
4. Invalid → 401 immediately
5. Valid → userId forwarded to route handler

## Applied to ContentPilot

**Issue token on login:**
```typescript
// app/api/auth/login/route.ts
import { SignJWT } from 'jose'
import { cookies } from 'next/headers'

export async function POST(req: Request) {
  const { email, password } = await req.json()
  const user = await db.user.findUnique({ where: { email } })

  if (!user || !await bcrypt.compare(password, user.passwordHash)) {
    return Response.json({ error: 'Invalid credentials' }, { status: 401 })
  }

  const secret = new TextEncoder().encode(process.env.JWT_SECRET)
  const token = await new SignJWT({ userId: user.id, role: user.role })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('7d')
    .sign(secret)

  cookies().set('token', token, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    maxAge: 60 * 60 * 24 * 7
  })

  return Response.json({ success: true })
}
```

**Verify on every protected route:**
```typescript
// middleware.ts
import { jwtVerify } from 'jose'
import { NextRequest, NextResponse } from 'next/server'

export async function middleware(req: NextRequest) {
  const token = req.cookies.get('token')?.value

  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const secret = new TextEncoder().encode(process.env.JWT_SECRET)
    const { payload } = await jwtVerify(token, secret)

    const res = NextResponse.next()
    res.headers.set('x-user-id', payload.userId as string)
    return res
  } catch {
    return NextResponse.json({ error: 'Invalid token' }, { status: 401 })
  }
}

export const config = {
  matcher: ['/api/v1/:path*']
}
```

## What to learn vs ignore
Learn: `SignJWT`, `jwtVerify`, httpOnly cookie flags, middleware matcher, `x-user-id` header pattern
Ignore now: refresh tokens, token rotation, revocation lists (Phase 7)

## Trade-offs
- JWT (stateless): no server memory, scales easily, hard to revoke
- Sessions (stateful): easy revocation, requires DB/Redis for shared state
- ContentPilot uses JWT — Vercel serverless has no shared memory anyway

## Interview questions

**Q: Difference between authentication and authorization?**
Authentication = "who are you?" (verify identity). Authorization = "what can you do?" (check role/permissions). JWT handles both: payload carries userId (authn) and role (authz).

**Q: Why HttpOnly cookie over localStorage?**
`localStorage` is readable by any JS on the page — XSS steals it in one line. HttpOnly cookies are invisible to JavaScript entirely; browser sends them automatically but no script can read them.

**Q: What happens when a JWT expires?**
`jwtVerify` throws. Middleware catches it, returns 401. Client must re-login. Refresh tokens solve this without forcing re-login — out of scope until Phase 7.

**Q: What goes in the payload? What should never go there?**
Include: userId, role, iat, exp. Never: passwords, sensitive PII. Payload is base64 encoded, not encrypted — anyone can decode it. Only the signature is protected.

**Q: Is JWT secure if intercepted?**
Can't be forged without the secret. But can be replayed until expiry. Mitigations: HTTPS only (`secure: true`), short expiry, and refresh token rotation.

---
Related: [[Phase 2.2 - Request Validation Zod]] [[Phase 2.4 - Rate Limiting]]