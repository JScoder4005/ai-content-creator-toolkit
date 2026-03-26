---
tags: [concept, automation, git]
created: 2026-03-27
---

# Git Workflow and Automation

## What is it?
A shell script that automatically syncs your Obsidian vault
notes to a public GitHub repository with one command.

## Why does it matter?
Manually copying files and running git commands is tedious.
A sync script turns a 5-step process into one command —
reducing friction means you actually do it consistently.

## How it works
1. Copies updated .md and .svg files from Obsidian vault
2. Stages all changes with git add
3. Commits with a custom message
4. Pushes to GitHub

## The script
Located at:
`~/Documents/UdayPersonalProjects/ai-content-creator-toolkit/sync-vault.sh`

Run it:
```bash
cd ~/Documents/UdayPersonalProjects/ai-content-creator-toolkit
./sync-vault.sh "add: Phase 2 — Rate Limiting"
```

## How ${1:-"default"} works
`$1` = first argument you pass to the script
`:-` = "if empty, use this default"
So `${1:-"update: vault notes"}` means:
- If you pass a message → use it
- If you don't → use "update: vault notes"

## Applied to ContentPilot
Every time we complete a Phase of system design learning:
1. New concept notes are in Obsidian
2. Run sync script with phase name as message
3. GitHub repo updates automatically
4. Anyone can follow the learning journey in real time

## Trade-offs
| Approach | Pro | Con |
|---|---|---|
| Manual copy + push | Full control | Easy to forget |
| Sync script | One command, consistent | Copies everything, no cherry-pick |
| Git submodule | Cleaner separation | Complex setup |
| Obsidian Git plugin | Auto-push on timer | Pushes personal notes too |

## Interview questions
- Q: What is a shell script?
  A: A text file containing terminal commands that run in sequence.
  The #!/bin/bash line tells the OS which interpreter to use.

- Q: What does git add . do vs git add filename?
  A: git add . stages ALL changed files. git add filename stages
  only that specific file. Use . for broad commits, filename for
  precise ones.

- Q: What is the difference between git commit and git push?
  A: commit saves changes to your LOCAL repository. push sends
  those commits to the REMOTE repository (GitHub). You can have
  many commits before pushing.

---
Related: [[01 - Projects/ContentPilot/Architecture v1]]
[[02 - System Design/Concepts/HTTP Request and Response]]