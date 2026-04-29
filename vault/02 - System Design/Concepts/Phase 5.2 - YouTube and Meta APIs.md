---
tags: [system-design, phase-5, youtube, instagram, oauth, api]
created: 2026-04-26
phase: 5
---

# Phase 5.2 - YouTube and Meta APIs

## What is it?

Integration with YouTube Data API v3 and Instagram Graph API to publish content on behalf of ContentPilot users using OAuth 2.0 access tokens with publish permissions.

## Why does it matter?

ContentPilot's entire value prop is automated publishing. Without proper OAuth flow, token storage, and refresh logic, publishing breaks the moment a token expires — which happens every hour for YouTube and every 60 days for Instagram.

## How it works

![[youtube_meta_apis_contentpilot.svg|589]]

**OAuth flow (one time per user):**
1. User clicks Connect — redirect to Google/Meta consent screen
2. User grants permissions — platform redirects back with auth code
3. Exchange code for access + refresh tokens
4. Encrypt and store tokens in `Platform` table

**Publish flow (every post):**
1. Fetch token from DB and decrypt
2. Check expiry — refresh if expired
3. Call YouTube/Instagram API with fresh token
4. Store `externalId` (videoId/postId) on success

## Applied to ContentPilot

### Install

```bash
npm install googleapis axios
```

### OAuth callback — YouTube

```typescript
// app/api/auth/youtube/callback/route.ts
import { google } from 'googleapis'
import { prisma } from '@/lib/prisma'
import { encrypt } from '@/lib/crypto'

const oauth2Client = new google.auth.OAuth2(
  process.env.YOUTUBE_CLIENT_ID,
  process.env.YOUTUBE_CLIENT_SECRET,
  `${process.env.NEXT_PUBLIC_APP_URL}/api/auth/youtube/callback`
)

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const code = searchParams.get('code')
  const userId = searchParams.get('state')  // passed during redirect

  const { tokens } = await oauth2Client.getToken(code!)

  await prisma.platform.upsert({
    where: { userId_type: { userId: userId!, type: 'YOUTUBE' } },
    update: {
      accessToken: encrypt(tokens.access_token!),
      refreshToken: encrypt(tokens.refresh_token!),
      expiresAt: new Date(tokens.expiry_date!),
    },
    create: {
      userId: userId!,
      type: 'YOUTUBE',
      accessToken: encrypt(tokens.access_token!),
      refreshToken: encrypt(tokens.refresh_token!),
      expiresAt: new Date(tokens.expiry_date!),
    },
  })

  return Response.redirect(`${process.env.NEXT_PUBLIC_APP_URL}/dashboard`)
}
```

### Token refresh utility

```typescript
// lib/tokens.ts
import { google } from 'googleapis'
import { prisma } from '@/lib/prisma'
import { encrypt, decrypt } from '@/lib/crypto'

export async function getValidYouTubeToken(platformId: string): Promise<string> {
  const platform = await prisma.platform.findUnique({ where: { id: platformId } })
  if (!platform) throw new Error('Platform not found')

  // Refresh if expired or expiring within 5 minutes
  if (platform.expiresAt && platform.expiresAt < new Date(Date.now() + 5 * 60 * 1000)) {
    const oauth2Client = new google.auth.OAuth2(
      process.env.YOUTUBE_CLIENT_ID,
      process.env.YOUTUBE_CLIENT_SECRET,
    )
    oauth2Client.setCredentials({ refresh_token: decrypt(platform.refreshToken!) })

    const { credentials } = await oauth2Client.refreshAccessToken()

    await prisma.platform.update({
      where: { id: platformId },
      data: {
        accessToken: encrypt(credentials.access_token!),
        expiresAt: new Date(credentials.expiry_date!),
      },
    })

    return credentials.access_token!
  }

  return decrypt(platform.accessToken)
}
```

### Publish to YouTube

```typescript
// lib/publishers/youtube.ts
import { google } from 'googleapis'
import { getValidYouTubeToken } from '@/lib/tokens'

export async function publishToYouTube(
  content: { topic: string; caption: string },
  platform: { id: string },
  videoUrl: string
): Promise<string> {
  const accessToken = await getValidYouTubeToken(platform.id)

  const auth = new google.auth.OAuth2()
  auth.setCredentials({ access_token: accessToken })

  const youtube = google.youtube({ version: 'v3', auth })

  // YouTube requires video file — fetch from Cloudinary URL
  const videoResponse = await fetch(videoUrl)
  const videoBuffer = await videoResponse.arrayBuffer()

  const response = await youtube.videos.insert({
    part: ['snippet', 'status'],
    requestBody: {
      snippet: {
        title: content.topic,
        description: content.caption,
        categoryId: '22',  // People & Blogs
      },
      status: { privacyStatus: 'public' },
    },
    media: {
      body: Buffer.from(videoBuffer),
      mimeType: 'video/mp4',
    },
  })

  return response.data.id!  // YouTube videoId = externalId
}
```

### Publish to Instagram

```typescript
// lib/publishers/instagram.ts
import axios from 'axios'
import { decrypt } from '@/lib/crypto'

export async function publishToInstagram(
  content: { caption: string },
  platform: { accessToken: string },
  imageUrl: string
): Promise<string> {
  const token = decrypt(platform.accessToken)
  const igUserId = process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID

  // Step 1: create media container
  const containerRes = await axios.post(
    `https://graph.facebook.com/v18.0/${igUserId}/media`,
    {
      image_url: imageUrl,
      caption: content.caption,
      access_token: token,
    }
  )
  const containerId = containerRes.data.id

  // Step 2: publish the container
  const publishRes = await axios.post(
    `https://graph.facebook.com/v18.0/${igUserId}/media_publish`,
    { creation_id: containerId, access_token: token }
  )

  return publishRes.data.id  // Instagram postId = externalId
}
```

### Encryption utility for tokens

```typescript
// lib/crypto.ts
import crypto from 'crypto'

const ALGORITHM = 'aes-256-gcm'
const KEY = Buffer.from(process.env.ENCRYPTION_KEY!, 'hex')  // 32 bytes

export function encrypt(text: string): string {
  const iv = crypto.randomBytes(16)
  const cipher = crypto.createCipheriv(ALGORITHM, KEY, iv)
  const encrypted = Buffer.concat([cipher.update(text, 'utf8'), cipher.final()])
  const tag = cipher.getAuthTag()
  return `${iv.toString('hex')}:${tag.toString('hex')}:${encrypted.toString('hex')}`
}

export function decrypt(data: string): string {
  const [ivHex, tagHex, encryptedHex] = data.split(':')
  const iv = Buffer.from(ivHex, 'hex')
  const tag = Buffer.from(tagHex, 'hex')
  const encrypted = Buffer.from(encryptedHex, 'hex')
  const decipher = crypto.createDecipheriv(ALGORITHM, KEY, iv)
  decipher.setAuthTag(tag)
  return decipher.update(encrypted).toString('utf8') + decipher.final('utf8')
}
```

### Required scopes

```typescript
// YouTube scopes needed
const YOUTUBE_SCOPES = [
  'https://www.googleapis.com/auth/youtube.upload',
  'https://www.googleapis.com/auth/youtube',
]

// Instagram — via Meta App permissions
// instagram_basic, instagram_content_publish, pages_read_engagement
```

## Trade-offs

| | YouTube Data API v3 | Instagram Graph API |
|---|---|---|
| Auth | Google OAuth 2.0 | Meta OAuth 2.0 |
| Token expiry | 1 hour (refresh token: indefinite) | 60 days (long-lived) |
| Video upload | Direct multipart | URL-based (image only direct) |
| Approval needed | ✅ YouTube audit for upload scope | ✅ Meta app review |
| Quota | 10,000 units/day free | Rate limited per endpoint |

## Interview Q&A

**Q: What is OAuth 2.0 and why does ContentPilot use it?**
OAuth 2.0 is an authorization framework that lets users grant third-party apps access to their accounts without sharing passwords. ContentPilot uses it so users can connect their YouTube/Instagram accounts — the platform issues access tokens scoped to specific permissions (upload only, not account management).

**Q: What is the difference between an access token and a refresh token?**
An access token is short-lived (1 hour for YouTube) and used in every API call. A refresh token is long-lived and used only to get a new access token when the current one expires. Store both encrypted — lose the refresh token and the user must re-authenticate.

**Q: Why encrypt access tokens at rest in the DB?**
If the DB is compromised, plain-text tokens give attackers full access to users' YouTube and Instagram accounts. AES-256-GCM encryption means stolen DB rows are useless without the encryption key — stored separately in environment variables.

**Q: Why does Instagram publishing require two API calls?**
Instagram's Graph API separates media creation from publishing. First you create a media container (registers the image/video URL), then you publish it. This lets Instagram validate and process the media before it goes live. One call = not supported.

**Q: What happens when a YouTube API quota is exhausted?**
YouTube returns a 403 with `quotaExceeded` error. ContentPilot catches this, marks the post as FAILED, and surfaces the error to the user. Quota resets at midnight Pacific time. At scale, request a quota increase from Google Cloud Console.

---

Related: [[Phase 5.1 - Claude API Patterns]] [[Phase 5.3 - Cloudinary Ephemeral]]