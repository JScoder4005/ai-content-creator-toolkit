---
tags: [contentpilot, database, schema]
created: 2026-03-27
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
