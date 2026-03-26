# 🎬 AI Content Creator Toolkit

> Automate your content workflow — from ride to published post — using Claude AI, Obsidian, and n8n.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Made with Claude](https://img.shields.io/badge/made%20with-Claude%20AI-purple.svg)

---

## 🧭 What is this?

This toolkit helps **content creators who code** automate the boring parts of content creation — writing captions, generating scripts, posting to platforms, and documenting what they learn — so they can focus on actually creating.

Built by a developer who rides a KTM 390 Adventure, shoots with an Insta360 X3, and got tired of spending more time writing captions than riding.

**What's inside:**

| Tool | What it does |
|------|-------------|
| `setup_obsidian_vault.py` | One script that builds your entire Obsidian knowledge base |
| `system-design-learning.skill` | Claude skill for structured system design learning |
| `ContentPilot` *(coming soon)* | Next.js dashboard to generate captions + post to YouTube/Instagram |
| `n8n workflows` *(coming soon)* | Automated TIL notes + social posting |

---

## 🚀 Quick Start

### 1. Set up your Obsidian vault in 30 seconds

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/ai-content-creator-toolkit.git
cd ai-content-creator-toolkit

# Run the setup script (requires Python 3.6+)
python3 setup_obsidian_vault.py

# Custom path
python3 setup_obsidian_vault.py --vault "/Users/yourname/Documents/MyVault"
```

Open Obsidian → Open folder as vault → select the created folder. Done.

### 2. Install the Claude skill

1. Download `system-design-learning.skill`
2. Open Claude.ai → Settings → My Skills → Upload
3. Claude now remembers your entire learning journey across sessions

### 3. Install Obsidian plugins

After opening the vault, install these 5 plugins (Settings → Community plugins → Browse):

| Plugin | Purpose |
|--------|---------|
| `Local REST API` | Lets n8n and scripts write notes automatically |
| `Templater` | Dynamic note templates |
| `Dataview` | Live dashboard queries |
| `Periodic Notes` | Auto-creates daily notes |
| `Excalidraw` | Draw diagrams inside notes |

---

## 📁 What the vault setup script creates

```
MyVault/
├── 00 - Home/
│   ├── Index.md          ← Live dashboard (Dataview queries auto-populate)
│   └── Roadmap.md        ← 8-week learning plan with checkboxes
│
├── 01 - Projects/
│   └── ContentPilot/
│       ├── Architecture v1.md
│       └── Data Model.md
│
├── 02 - System Design/
│   ├── Concepts/         ← One note per concept learned
│   ├── Diagrams/         ← SVG/PNG diagrams embedded in notes
│   └── ADRs/             ← Architecture Decision Records
│       ├── ADR-001 Why PostgreSQL.md
│       ├── ADR-002 Why Cloudinary.md
│       └── ADR-003 Why Vercel Cron.md
│
├── 03 - Daily Notes/     ← Auto-created daily devlog
├── 04 - TIL/             ← Today I Learned notes
├── 05 - Inbox/           ← Quick capture
└── Templates/
    ├── Daily Note.md
    ├── Concept Note.md
    └── ADR.md
```

---

## 🧠 The Claude Skill — what it does

The `system-design-learning.skill` gives Claude full context about:

- Your project (ContentPilot architecture, tech stack, decisions made)
- Your vault structure (exact folder paths, plugin config)
- Your learning progress (which concepts are done, what's next)
- Your teaching preferences (diagrams first, apply to real project)

**Without the skill:** You re-explain context every session.
**With the skill:** Claude picks up exactly where you left off.

### Learning roadmap the skill tracks

| Phase | Topic | Concepts covered |
|-------|-------|-----------------|
| ✓ 1 | Foundations | Client-server, DNS, CDN, HTTP/HTTPS |
| → 2 | API layer | Rate limiting, auth middleware, error handling |
| 3 | Data layer | PostgreSQL, indexing, Prisma optimisation |
| 4 | Async & queues | Cron jobs, retry logic, idempotency |
| 5 | External integrations | OAuth, webhooks, third-party APIs |
| 6 | Scalability | Caching, CDN, horizontal scaling |
| 7 | Resilience & security | Circuit breakers, OWASP, secrets |
| 8 | Interview ready | Trade-offs, estimation, ADRs |

---

## 🔌 Automate notes from n8n (coming soon)

Once you have [n8n](https://n8n.io) running and the Obsidian Local REST API plugin installed:

```javascript
// n8n HTTP Request node
{
  method: "PUT",
  url: "http://localhost:27123/vault/04 - TIL/{{ $now.format('yyyy-MM-dd') }}.md",
  headers: {
    "Authorization": "Bearer YOUR_OBSIDIAN_API_KEY",
    "Content-Type": "text/markdown"
  },
  body: `# TIL — {{ $now.format('yyyy-MM-dd') }}\n\n{{ $json.content }}`
}
```

Your TIL workflow generates content via Groq/Claude → saves to Obsidian automatically.

---

## 🛠️ Tech stack (ContentPilot dashboard)

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 App Router + shadcn/ui + Tailwind |
| Animations | Three.js (R3F + Drei) |
| AI | Claude API (`claude-sonnet-4-5`) |
| Database | Supabase + Prisma (PostgreSQL) |
| Media | Cloudinary (ephemeral — deleted after upload) |
| Scheduler | Vercel Cron |
| Hosting | Vercel (free tier) |
| YouTube | YouTube Data API v3 |
| Instagram | Meta Graph API |

---

## 📖 Architecture decisions (ADRs)

Every major decision is documented in the vault. Here's a summary:

**Why PostgreSQL over MongoDB?**
Strong relational integrity between users/posts. Prisma ORM works excellently.
ACID guarantees matter for scheduled post queuing.

**Why Cloudinary as ephemeral storage?**
Instagram and YouTube require a public URL before posting. Cloudinary provides
that, but we delete immediately after the platform confirms upload — keeping
usage well within free tier. *(Credit: realized during learning session)*

**Why Vercel Cron over BullMQ?**
BullMQ needs Redis (~$10/mo). Vercel Cron is free, checks queue every 15 min,
status tracked in PostgreSQL. Simple, zero infra.

---

## 🗺️ Roadmap

- [x] Obsidian vault setup script
- [x] System design learning skill
- [ ] ContentPilot Next.js dashboard
- [ ] YouTube upload integration
- [ ] Instagram Reels integration
- [ ] n8n workflow templates
- [ ] MCP server for ride content generation
- [ ] Cloudflare Tunnel setup guide
- [ ] GitHub Action → Obsidian note automation

---

## 🤝 Contributing

PRs welcome! If you:
- Use a different stack (Vue, Remix, etc.) — add a variant
- Have a better n8n workflow — share it
- Want to add a new Claude skill — follow the skill format

```bash
git clone https://github.com/YOUR_USERNAME/ai-content-creator-toolkit.git
cd ai-content-creator-toolkit
# make your changes
git checkout -b feature/your-feature
git commit -m "add: your feature"
git push origin feature/your-feature
# open a PR
```

---

## 📄 License

MIT — use it, modify it, build on it.

---

## 👤 Author

Built by **Uday** — full-stack dev

- Learning system design by building ContentPilot
- Documenting everything in Obsidian
- Automating the boring parts with n8n + Claude

---

## ⭐ If this helped you

Star the repo, share it with a developer friend who creates content.
The goal is to make this the go-to toolkit for developers who create.

---


