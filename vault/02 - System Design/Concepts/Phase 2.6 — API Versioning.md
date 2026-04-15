---
tags: [system-design, phase-2, api-versioning]
created: 2026-03-28
phase: 2
---
# Phase 2.6 - API Versioning

## What is it?
Maintaining multiple versions of an API simultaneously so breaking changes don't force all clients to update at once.

## Why does it matter?
Once an API has consumers (mobile apps, frontend, third parties), you can't change the contract without breaking them. Versioning lets you evolve the API while keeping old clients working.

## How it works

![[api_versioning_contentpilot.svg|619]]

Old clients → `/api/v1/` → v1 handler (unchanged forever)
New clients → `/api/v2/` → v2 handler (new shape, new features)
Both live in parallel until v1 is sunset.

## Three strategies

| Strategy | Example | ContentPilot |
|---|---|---|
| URL versioning | `/api/v1/generate` | ✅ |
| Header versioning | `Accept: application/vnd.cp.v2+json` | ❌ |
| Query param | `/api/generate?version=1` | ❌ |

URL versioning: explicit, CDN-cacheable, easy to test.

## Applied to ContentPilot

Folder structure IS the versioning:
```
app/api/v1/generate/route.ts   ← stable, topic + single platform
app/api/v2/generate/route.ts   ← future, topic + platforms[] + scheduledAt
```

**Breaking changes** (need new version): rename field, change type, remove field, change status code

**Non-breaking** (same version): add optional field, add new endpoint, add response data

**Deprecation headers on v1:**
```typescript
res.headers.set('Deprecation', 'true')
res.headers.set('Sunset', 'Sat, 01 Jan 2027 00:00:00 GMT')
res.headers.set('Link', '</api/v2/generate>; rel="successor-version"')
```

## What to learn vs ignore
Learn: URL versioning, breaking vs non-breaking changes, Deprecation + Sunset headers, Next.js folder-based routing
Ignore: HATEOAS, semantic versioning for APIs — over-engineering at this scale

## Trade-offs
- URL: visible, cacheable, testable ✅
- Header: hidden, cache issues, harder to test ❌
- Query param: cache issues, pollutes params ❌

## Interview questions

**Q: What is API versioning and when do you need it?**
Lets you introduce breaking changes without forcing all clients to update simultaneously. Need it the moment your API has external consumers you don't fully control.

**Q: What counts as a breaking change?**
Renaming/removing a field, changing a field's type, changing a status code, removing an endpoint. Adding new optional fields or endpoints is non-breaking — existing clients are unaffected.

**Q: Why URL versioning over header versioning?**
URL is explicit, visible, pasteable, CDN-cacheable without extra config. Header versioning hides the version and complicates caching and testing.

**Q: How long should you maintain old versions?**
Until traffic drops below threshold or a committed sunset date passes. Always announce via `Deprecation` + `Sunset` headers so clients have time to migrate.

**Q: How does Next.js handle versioning?**
Purely folder structure — `app/api/v1/` and `app/api/v2/` are independent route trees. No config or middleware routing needed.

---
Related: [[Phase 2.5 - Error Handling]] [[Phase 3.1 - Database Design]]