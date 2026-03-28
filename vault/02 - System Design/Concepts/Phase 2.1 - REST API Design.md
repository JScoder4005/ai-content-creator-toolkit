---
tags:
  - concept
  - phase-2
created: 2026-03-28
phase: 2
---

# Phase 2.1 - REST API Design

## What is it?
REST (Representational State Transfer) is a set of rules for
designing clean, predictable API routes. Every route represents
a resource (noun), and HTTP methods define what to do with it (verb).

## Why does it matter?
Bad API design makes your codebase hard to maintain and confusing
for other developers. Good REST design means anyone can look at
your routes and instantly understand what they do.

## The 4 rules

### Rule 1 — Routes are nouns, not verbs
❌ /api/v1/getUser  
✓ /api/v1/users

### Rule 2 — HTTP methods are the verbs
| Method | Action | Example |
|--------|--------|---------|
| GET | Fetch | GET /api/v1/posts |
| POST | Create | POST /api/v1/posts |
| PUT | Update | PUT /api/v1/posts/:id |
| DELETE | Remove | DELETE /api/v1/posts/:id |

### Rule 3 — Correct status codes
| Code | Meaning | When to use |
|------|---------|-------------|
| 200 | OK | successful GET |
| 201 | Created | successful POST |
| 400 | Bad request | wrong input |
| 401 | Unauthorized | not logged in |
| 403 | Forbidden | no permission |
| 404 | Not found | resource missing |
| 429 | Too many requests | rate limit hit |
| 500 | Server error | something crashed |

### Rule 4 — Nest routes logically
/api/v1/posts/:id/comments → comments of a post
/api/v1/users/:id/posts → posts of a user

## Applied to ContentPilot
```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/generate
POST   /api/v1/publish/youtube
POST   /api/v1/publish/instagram
GET    /api/v1/posts
POST   /api/v1/posts
PUT    /api/v1/posts/:id
DELETE /api/v1/posts/:id
```

## What to learn vs ignore
| Learn | Ignore for now |
|-------|---------------|
| REST conventions | GraphQL |
| HTTP methods | gRPC |
| Status codes | WebSockets |
| Route naming | HATEOAS |

## Trade-offs
| Approach | Pro | Con |
|----------|-----|-----|
| REST | Simple, universal | Over-fetching data |
| GraphQL | Flexible queries | Complex setup |
| tRPC | Type-safe | Next.js only |

## Interview questions
- Q: What is REST?
  A: A set of conventions for designing APIs using HTTP methods
  and resource-based URLs. Routes are nouns, methods are verbs.

- Q: What is the difference between PUT and PATCH?
  A: PUT replaces the entire resource. PATCH updates only specific
  fields. ContentPilot uses PUT for simplicity.

- Q: Why use /api/v1/ prefix?
  A: Versioning allows breaking changes without breaking existing
  clients. v1 stays stable while v2 can have new logic.

- Q: What status code should POST /api/v1/posts return?
  A: 201 Created — not 200. 201 specifically means a new resource
  was created successfully.

---
Related: [[01 - Projects/ContentPilot/Architecture v1]]
[[02 - System Design/Concepts/HTTP Request and Response]]