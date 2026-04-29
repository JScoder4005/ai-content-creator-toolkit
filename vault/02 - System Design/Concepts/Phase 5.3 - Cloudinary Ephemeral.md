---
tags:
  - system-design
  - phase-5
  - cloudinary
  - storage
  - ephemeral
created: 2026-04-26
phase: 5
---

# Phase 5.3 - Cloudinary Ephemeral

## What is it?

Using Cloudinary as a temporary staging area for user-uploaded media. Files are uploaded to Cloudinary to get a publicly accessible URL, passed to YouTube/Instagram for publishing, then immediately deleted. Cloudinary is never permanent storage.

## Why does it matter?

YouTube and Instagram APIs require a publicly accessible URL to pull media from — you can't upload directly from the browser in one step. Cloudinary provides that URL instantly. Deleting after publish keeps storage costs near zero and avoids keeping duplicate copies of content the platforms already own.

## How it works

![[cloudinary_ephemeral_contentpilot.svg]]

1. User uploads file → goes to Cloudinary → get `publicId` + `secure_url`
2. Store `publicId` in DB temporarily (needed for deletion)
3. Pass `secure_url` to YouTube/Instagram API
4. On publish success → delete from Cloudinary immediately
5. On publish failure → keep file for retry

## Applied to ContentPilot

### Install

```bash
npm install cloudinary
```

### Cloudinary config

```typescript
// lib/cloudinary.ts
import { v2 as cloudinary } from 'cloudinary'

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
})

export { cloudinary }
```

### Upload — signed upload from server

```typescript
// app/api/v1/upload/route.ts
import { cloudinary } from '@/lib/cloudinary'
import { prisma } from '@/lib/prisma'

export async function POST(req: Request) {
  const formData = await req.formData()
  const file = formData.get('file') as File
  const contentId = formData.get('contentId') as string

  const arrayBuffer = await file.arrayBuffer()
  const buffer = Buffer.from(arrayBuffer)

  // Upload to Cloudinary
  const result = await new Promise<any>((resolve, reject) => {
    cloudinary.uploader.upload_stream(
      {
        folder: 'contentpilot/staging',
        resource_type: 'auto',       // auto-detect video or image
        overwrite: false,
      },
      (error, result) => error ? reject(error) : resolve(result)
    ).end(buffer)
  })

  // Store publicId temporarily — needed to delete after publish
  await prisma.content.update({
    where: { id: contentId },
    data: { cloudinaryPublicId: result.public_id },
  })

  return Response.json({
    publicId: result.public_id,
    secureUrl: result.secure_url,
  })
}
```

### Delete after successful publish

```typescript
// lib/cloudinary.ts
export async function deleteFromCloudinary(publicId: string): Promise<void> {
  await cloudinary.uploader.destroy(publicId, { resource_type: 'video' })

  // Clear publicId from DB — no longer needed
  await prisma.content.updateMany({
    where: { cloudinaryPublicId: publicId },
    data: { cloudinaryPublicId: null },
  })
}
```

### Full publish + delete flow in Cron

```typescript
// app/api/cron/publish/route.ts (relevant section)
for (const post of scheduledPosts) {
  try {
    const externalId = await publishToYouTube(
      post.content,
      post.platform,
      post.content.cloudinaryUrl  // Cloudinary secure_url
    )

    await prisma.$transaction([
      prisma.publishedPost.update({
        where: { id: post.id },
        data: { status: 'PUBLISHED', externalId, publishedAt: new Date() },
      }),
      prisma.content.update({
        where: { id: post.content.id },
        data: { status: 'PUBLISHED' },
      }),
    ])

    // Delete from Cloudinary AFTER successful DB transaction
    if (post.content.cloudinaryPublicId) {
      await deleteFromCloudinary(post.content.cloudinaryPublicId)
    }

  } catch (error) {
    // Don't delete — keep file for retry
    await prisma.publishedPost.update({
      where: { id: post.id },
      data: { status: 'FAILED' },
    })
  }
}
```

### Signed uploads — security

Never expose your Cloudinary API secret to the client. Always upload via your server or use signed upload presets:

```typescript
// Generate a signed upload signature for direct client upload
export async function GET(req: Request) {
  const timestamp = Math.round(Date.now() / 1000)
  const signature = cloudinary.utils.api_sign_request(
    { timestamp, folder: 'contentpilot/staging' },
    process.env.CLOUDINARY_API_SECRET!
  )
  return Response.json({ timestamp, signature })
}
```

### Environment variables

```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### Add cloudinaryPublicId to Prisma schema

```prisma
model Content {
  // ... existing fields
  cloudinaryPublicId String?   // null after deletion
  cloudinaryUrl      String?   // secure_url for platform API
}
```

## Trade-offs

| | Cloudinary ephemeral | S3 permanent | Direct upload to platform |
|---|---|---|---|
| Cost | ✅ Near zero (delete after use) | Storage + transfer cost | ✅ Zero |
| Public URL | ✅ Instant | ✅ with presigned URL | ❌ not supported |
| Transform on upload | ✅ resize, compress | ❌ | ❌ |
| Complexity | Medium | Medium | Low |
| ContentPilot choice | ✅ | — | — |

## Interview Q&A

**Q: Why use Cloudinary as a staging area instead of uploading directly to YouTube?**
YouTube and Instagram APIs require a publicly accessible URL to pull media from — they don't accept direct file uploads from browsers in one step. Cloudinary provides an instant public URL. It also handles transcoding, compression, and format validation before the file reaches the platform.

**Q: Why delete from Cloudinary after publishing instead of keeping files there?**
Cloudinary charges by storage and bandwidth. Keeping files permanently means paying for storage that serves no purpose — the platform already has the final copy. Ephemeral use keeps costs near zero at any scale.

**Q: Why delete AFTER the DB transaction, not before?**
If you delete from Cloudinary before updating the DB and the DB update fails, the file is gone but the post is never marked published. On retry, there's nothing to publish. Delete only after the DB is in a consistent PUBLISHED state — if the delete fails, the file persists temporarily but data is correct.

**Q: How do you handle the case where deletion fails?**
Log the failed deletion with the `publicId`. A separate cleanup Cron can query content rows where `status = PUBLISHED` and `cloudinaryPublicId IS NOT NULL` — these are files that should have been deleted but weren't. Retry deletion for those.

**Q: Why use signed uploads instead of exposing the API key to the client?**
The Cloudinary API secret lets anyone upload unlimited files to your account, consume your quota, and rack up charges. Signed uploads let the client upload directly to Cloudinary using a time-limited signature generated by your server — the secret never leaves the server.

---

Related: [[Phase 5.2 - YouTube and Meta APIs]] [[Phase 6.1 - Caching Strategy]]