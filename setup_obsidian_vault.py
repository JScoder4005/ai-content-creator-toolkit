"""
Obsidian Vault Auto-Setup Script
Run this once → your entire vault structure + templates are created automatically.

Usage:
  python setup_obsidian_vault.py
  python setup_obsidian_vault.py --vault "/custom/path/to/MyVault"
"""

import os
import argparse
from pathlib import Path
from datetime import datetime

TODAY = datetime.now().strftime("%Y-%m-%d")
YEAR  = datetime.now().strftime("%Y")

# ── Folder structure ──────────────────────────────────────────────────────────
FOLDERS = [
    "00 - Home",
    "01 - Projects/ContentPilot",
    "02 - System Design/Concepts",
    "02 - System Design/Diagrams",
    "02 - System Design/ADRs",
    "03 - Daily Notes",
    "04 - TIL",
    "05 - Inbox",
    "Templates",
    ".obsidian",          # Obsidian config lives here
]

# ── Note templates ────────────────────────────────────────────────────────────
TEMPLATES = {

    "00 - Home/Index.md": f"""\
---
tags: [home, index]
created: {TODAY}
---

# My Learning Vault

## Active projects
- [[01 - Projects/ContentPilot/Architecture v1|ContentPilot Architecture]]

## System design progress
```dataview
TABLE file.ctime AS "Created", tags
FROM "02 - System Design/Concepts"
SORT file.ctime DESC
```

## Recent TILs
```dataview
LIST
FROM "04 - TIL"
SORT file.ctime DESC
LIMIT 7
```

## Recent ADRs
```dataview
TABLE file.ctime AS "Date"
FROM "02 - System Design/ADRs"
SORT file.ctime DESC
```
""",

    "00 - Home/Roadmap.md": f"""\
---
tags: [roadmap, system-design]
created: {TODAY}
---

# System Design Roadmap — {YEAR}

## 8-week plan

- [ ] Week 1 — Foundations (client-server, REST, HTTP, DNS)
- [ ] Week 2 — API layer (rate limiting, auth, error handling)
- [ ] Week 3 — Data layer (PostgreSQL, indexing, Prisma)
- [ ] Week 4 — Async & queues (cron, retry, idempotency)
- [ ] Week 5 — External integrations (OAuth, webhooks)
- [ ] Week 6 — Scalability (caching, CDN, replication)
- [ ] Week 7 — Resilience & security (circuit breakers, OWASP)
- [ ] Week 8 — Interview ready (trade-offs, estimation, ADRs)

## Applied project
[[01 - Projects/ContentPilot/Architecture v1|ContentPilot]]
""",

    "01 - Projects/ContentPilot/Architecture v1.md": f"""\
---
tags: [contentpilot, architecture, system-design]
created: {TODAY}
version: v1
---

# ContentPilot — Architecture v1

## Overview
Content automation dashboard built with Next.js 14, Claude API,
YouTube Data API, Meta Graph API, Cloudinary, Supabase, and Vercel Cron.

## Current architecture diagram
![[Diagrams/contentpilot-v1.png]]

## Components

### Frontend
- Next.js 14 App Router
- shadcn/ui + Tailwind CSS
- Three.js animations

### API layer
- /api/generate — calls Claude API
- /api/publish/youtube — YouTube Data API v3
- /api/publish/instagram — Meta Graph API
- /api/schedule — writes to DB queue

### Data layer
- Supabase (PostgreSQL)
- Prisma ORM
- Posts table: id, content, platform, scheduled_at, status

### External services
- Cloudinary — media storage
- Vercel Cron — job scheduler

## Trade-offs
[[02 - System Design/ADRs/ADR-001 Why PostgreSQL]]
[[02 - System Design/ADRs/ADR-002 Why Cloudinary]]
[[02 - System Design/ADRs/ADR-003 Why Vercel Cron]]
""",

    "01 - Projects/ContentPilot/Data Model.md": f"""\
---
tags: [contentpilot, database, schema]
created: {TODAY}
---

# ContentPilot — Data Model

## Posts table
| Column       | Type        | Notes                        |
|-------------|-------------|------------------------------|
| id          | uuid        | Primary key                  |
| user_id     | uuid        | FK → users                   |
| content     | text        | Generated caption/script     |
| platform    | enum        | youtube, instagram           |
| media_url   | text        | Cloudinary URL               |
| scheduled_at| timestamptz | null = post immediately      |
| status      | enum        | draft, queued, published, failed |
| created_at  | timestamptz | auto                         |

## Related
[[01 - Projects/ContentPilot/Architecture v1]]
[[02 - System Design/Concepts/Database Indexing]]
""",

    "Templates/Daily Note.md": """\
---
tags: [daily]
created: {{date:YYYY-MM-DD}}
---

# {{date:YYYY-MM-DD}}

## What I built today
- 

## What I learned
- 

## Blockers
- 

## Decisions made
- 

## Links & references
- 

---
[[00 - Home/Index|Home]]
""",

    "Templates/Concept Note.md": """\
---
tags: [concept]
created: {{date:YYYY-MM-DD}}
---

# {Concept Name}

## What is it?


## Why does it matter?


## How it works


## Applied to ContentPilot


## Trade-offs
| Approach | Pro | Con |
|----------|-----|-----|
|          |     |     |

## Interview angle


---
Related: 
""",

    "Templates/ADR.md": """\
---
tags: [adr]
created: {{date:YYYY-MM-DD}}
status: Accepted
---

# ADR-{number}: {Decision Title}

## Status
Accepted

## Context


## Decision


## Alternatives considered


## Consequences


---
[[00 - Home/Index|Home]]
""",

    "02 - System Design/ADRs/ADR-001 Why PostgreSQL.md": f"""\
---
tags: [adr, database]
created: {TODAY}
status: Accepted
---

# ADR-001: Why PostgreSQL over MongoDB

## Status
Accepted

## Context
ContentPilot needs to store posts, schedules, and user data.
Considered MongoDB (flexible schema) vs PostgreSQL (relational).

## Decision
Use PostgreSQL via Supabase.

## Alternatives considered
- MongoDB — flexible but no strong relations, no ACID guarantees
- SQLite — too limited for multi-user eventually
- PlanetScale — MySQL-based, good but less Prisma support

## Consequences
- Strong relational integrity between users/posts
- Prisma ORM works excellently with PostgreSQL
- Supabase free tier covers our needs
- Harder to change schema later but Prisma migrations handle this

---
[[01 - Projects/ContentPilot/Architecture v1]]
""",

    "02 - System Design/ADRs/ADR-002 Why Cloudinary.md": f"""\
---
tags: [adr, storage, media]
created: {TODAY}
status: Accepted
---

# ADR-002: Why Cloudinary for media storage

## Status
Accepted

## Context
Instagram and YouTube APIs require a publicly accessible media URL
before posting. We need somewhere to temporarily host video/image files.

## Decision
Use Cloudinary free tier.

## Alternatives considered
- AWS S3 — powerful but requires AWS account setup + IAM
- Supabase Storage — simpler but less CDN optimisation
- Self-hosted — too much infra overhead

## Consequences
- Free tier: 25GB storage, 25GB bandwidth/month
- Built-in image/video transformations
- Public URLs available immediately after upload

---
[[01 - Projects/ContentPilot/Architecture v1]]
""",

    "02 - System Design/ADRs/ADR-003 Why Vercel Cron.md": f"""\
---
tags: [adr, scheduler, cron]
created: {TODAY}
status: Accepted
---

# ADR-003: Why Vercel Cron over BullMQ

## Status
Accepted

## Context
Scheduled posts need a background job runner to check the queue
and fire posts at the right time.

## Decision
Use Vercel Cron (runs every 15 minutes via vercel.json).

## Alternatives considered
- BullMQ + Redis — powerful, retry logic, but needs Redis instance (~$10/mo)
- node-cron — only works if server is always running (not serverless)
- GitHub Actions — hacky, not designed for this

## Consequences
- Zero cost on Vercel hobby plan
- 15-minute minimum interval (good enough for scheduling)
- No persistent job state — status tracked in PostgreSQL instead
- Simple to reason about and debug

---
[[01 - Projects/ContentPilot/Architecture v1]]
""",

    "04 - TIL/.gitkeep": "",
    "03 - Daily Notes/.gitkeep": "",
    "02 - System Design/Diagrams/.gitkeep": "",
    "05 - Inbox/.gitkeep": "",
}


def create_vault(vault_path: Path):
    print(f"\n Creating vault at: {vault_path}\n")

    # Create folders
    for folder in FOLDERS:
        target = vault_path / folder
        target.mkdir(parents=True, exist_ok=True)
        print(f"  [folder] {folder}")

    print()

    # Create notes and templates
    for rel_path, content in TEMPLATES.items():
        target = vault_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(content, encoding="utf-8")
            print(f"  [note]   {rel_path}")
        else:
            print(f"  [skip]   {rel_path} (already exists)")

    # Create Obsidian app.json so it opens cleanly
    app_json = vault_path / ".obsidian" / "app.json"
    if not app_json.exists():
        app_json.write_text('{\n  "legacyEditor": false,\n  "livePreview": true\n}',
                            encoding="utf-8")
        print(f"  [config] .obsidian/app.json")

    print(f"""
 Done! Your vault is ready at:
  {vault_path}

 Next steps:
  1. Open Obsidian → Open folder as vault → select: {vault_path}
  2. Settings → Community plugins → turn off Safe mode
  3. Install: Local REST API, Templater, Dataview, Periodic Notes, Excalidraw
  4. Settings → Templater → set template folder to: Templates
  5. Open "00 - Home/Index.md" as your dashboard

 Happy note-taking!
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-setup Obsidian vault")
    parser.add_argument(
        "--vault",
        type=str,
        default=str(Path.home() / "MyVault"),
        help="Path where vault will be created (default: ~/MyVault)"
    )
    args = parser.parse_args()
    vault_path = Path(args.vault).expanduser().resolve()
    create_vault(vault_path)
