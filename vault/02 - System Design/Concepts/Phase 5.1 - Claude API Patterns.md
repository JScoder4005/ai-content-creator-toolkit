---
tags: [system-design, phase-5, claude-api, ai, integrations]
created: 2026-04-26
phase: 5
---

# Phase 5.1 - Claude API Patterns

## What is it?

Patterns for calling the Claude API reliably in ContentPilot — structured prompts, timeout handling, retry with exponential backoff, response validation, and cost control.

## Why does it matter?

The Claude API is an external dependency — it can time out, rate limit, return malformed responses, or go down. Every call costs money. Without proper patterns, a single bad response corrupts content data, a timeout crashes the job, and runaway retries burn your budget.

## How it works

![[claude_api_patterns_contentpilot.svg]]

1. Build a structured prompt (system + user + output format instruction)
2. Call Claude API with a timeout
3. On error → retry up to 3 times with exponential backoff
4. On success → parse and validate response with Zod
5. Valid → save to DB with status READY
6. Exhausted retries → status FAILED, log error

## Applied to ContentPilot

### Install

```bash
npm install @anthropic-ai/sdk
```

### Claude client — singleton

```typescript
// lib/claude.ts
import Anthropic from '@anthropic-ai/sdk'

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
  timeout: 30_000,   // 30 second timeout
  maxRetries: 0,     // handle retries manually for full control
})

export { client }
```

### Structured prompt — output format enforced

```typescript
// lib/claude.ts
import { z } from 'zod'

const CaptionResponseSchema = z.object({
  caption: z.string().min(10).max(2200),
  hashtags: z.array(z.string()).max(30),
  hook: z.string().max(150),
})

type CaptionResponse = z.infer<typeof CaptionResponseSchema>

export async function generateCaption(
  topic: string,
  platform: string,
  tone: string
): Promise<CaptionResponse> {
  const systemPrompt = `You are a social media content expert specialising in ${platform} captions.
Always respond with valid JSON only — no markdown, no explanation.
Response format:
{
  "caption": "full caption text",
  "hashtags": ["tag1", "tag2"],
  "hook": "first line to grab attention"
}`

  const userPrompt = `Create a ${tone} ${platform} caption about: ${topic}`

  return await withRetry(() => callClaude(systemPrompt, userPrompt), 3)
}

async function callClaude(
  systemPrompt: string,
  userPrompt: string
): Promise<CaptionResponse> {
  const message = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1024,
    system: systemPrompt,
    messages: [{ role: 'user', content: userPrompt }],
  })

  const raw = message.content[0].type === 'text' ? message.content[0].text : ''

  // Strip any accidental markdown fences
  const cleaned = raw.replace(/```json|```/g, '').trim()

  // Parse + validate with Zod
  const parsed = JSON.parse(cleaned)
  return CaptionResponseSchema.parse(parsed)
}
```

### Retry with exponential backoff

```typescript
// lib/retry.ts
export async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts: number
): Promise<T> {
  let lastError: unknown

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error

      // Don't retry on validation errors — bad prompt, not transient
      if (error instanceof SyntaxError || error instanceof z.ZodError) {
        throw error
      }

      if (attempt < maxAttempts) {
        const delay = Math.pow(2, attempt) * 1000  // 2s, 4s, 8s
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
  }

  throw lastError
}
```

### Cost control — token budgeting

```typescript
// Cap tokens to control cost per request
const message = await client.messages.create({
  model: 'claude-sonnet-4-20250514',
  max_tokens: 1024,   // hard cap — never exceed this
  system: systemPrompt,
  messages: [{ role: 'user', content: userPrompt }],
})

// Log token usage per request
console.log({
  inputTokens: message.usage.input_tokens,
  outputTokens: message.usage.output_tokens,
  estimatedCost: (message.usage.input_tokens * 0.000003) +
                 (message.usage.output_tokens * 0.000015),
})
```

### Platform-specific prompt variations

```typescript
const PLATFORM_INSTRUCTIONS: Record<string, string> = {
  instagram: 'Max 2200 characters. Use line breaks for readability. Include 5–10 hashtags.',
  youtube: 'Max 5000 characters. Front-load keywords. Include timestamps if relevant.',
  twitter: 'Max 280 characters. No hashtags unless essential. Punchy and direct.',
}

const systemPrompt = `You are a social media content expert.
Platform: ${platform}
Instructions: ${PLATFORM_INSTRUCTIONS[platform]}
Always respond with valid JSON only.`
```

## Trade-offs

| | Anthropic SDK | Raw fetch | Groq (alternative) |
|---|---|---|---|
| Type safety | ✅ | ❌ | ✅ |
| Built-in retry | ✅ (disabled here intentionally) | ❌ | ✅ |
| Model quality | ✅ Claude Sonnet | Depends | Llama 3 |
| Cost | Medium | Same | ✅ Cheaper |
| ContentPilot choice | ✅ | — | Fallback option |

## Interview Q&A

**Q: Why disable the SDK's built-in retry and handle it manually?**
The SDK retries on all errors including Zod validation failures — you'd waste retries on a broken prompt that will never succeed. Manual retry lets you distinguish transient errors (timeout, 429) from permanent ones (invalid JSON, schema mismatch) and only retry what's worth retrying.

**Q: Why validate the Claude API response with Zod?**
Claude is a language model — it can return well-formed text that doesn't match your expected JSON structure, has missing fields, or exceeds length limits. Zod catches this at the boundary before corrupt data reaches your DB. Treat Claude's output the same as any untrusted external input.

**Q: What is exponential backoff and why use it?**
Exponential backoff increases the wait time between retries exponentially — 2s, 4s, 8s. If you retry immediately, you hammer an already-overloaded API. Exponential backoff gives the upstream service time to recover and avoids thundering herd when many clients retry simultaneously.

**Q: How do you control Claude API costs in production?**
Set `max_tokens` as a hard cap — Claude stops generating at that limit. Log `usage.input_tokens` and `usage.output_tokens` per request to track spend. Rate limit users (Phase 2.3) so no single user can trigger unlimited API calls. Use cheaper models (Haiku) for lower-value tasks.

**Q: Why instruct Claude to return JSON only in the system prompt?**
Claude sometimes wraps JSON in markdown code fences or adds explanation text. The system prompt instruction eliminates this — but you still strip fences defensively. A Zod parse failure on unexpected formatting is caught and triggers a retry with the same prompt.

---

Related: [[Phase 4.3 - Background Jobs]] [[Phase 5.2 - YouTube and Meta APIs]]