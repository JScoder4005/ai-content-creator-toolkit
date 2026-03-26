---
tags: [concept]
created: 2026-03-27
---

# DNS Resolution

## What is it?
DNS is the phone book of the internet. It translates 
domain names like contentpilot.com into IP addresses 
like 76.223.44.12 that servers understand.

## Why does it matter?
Without DNS you'd have to remember IP addresses for 
every website. DNS makes the internet human-friendly.

## How it works
1. Browser asks DNS Resolver (your ISP / Google 8.8.8.8)
2. Resolver asks Root DNS — who handles .com?
3. Root sends to TLD Nameserver — who owns contentpilot?
4. TLD sends to Vercel's Authoritative DNS
5. Vercel returns IP address 76.223.44.12
6. Browser connects to that IP
7. Result cached — next visit is instant
   ![[dns_resolution_flow.svg]]

## Applied to ContentPilot
- contentpilot.com is registered on a domain registrar
- DNS A record points to Vercel's IP
- Vercel handles the rest automatically
- First visit ~20ms DNS lookup, repeat visits ~0ms (cached)

## Trade-offs
| Approach | Pro | Con |
|---|---|---|
| Vercel DNS | Auto-managed, zero config | Less control |
| Cloudflare DNS | Faster, DDoS protection | Extra setup |
| Custom DNS | Full control | Complex to manage |

## Interview angle
"DNS translates contentpilot.com to an IP. First visit 
takes ~20ms to resolve, subsequent visits use the cache 
so it's instant. We use Vercel's DNS — zero config needed."

## Interview questions:-
- Q: How does DNS work?
  A: Browser asks resolver → root → TLD → authoritative → gets IP → caches it

- Q: What happens if DNS is down?
  A: No one can reach your site by domain name — IP still works directly

- Q: How would you reduce DNS lookup time?
  A: Use a CDN like Cloudflare, enable DNS prefetching in the browser

---
Related: [[01 - Projects/ContentPilot/Architecture v1]]
[[02 - System Design/Concepts/Client-Server Model]]
[[02 - System Design/Concepts/CDN and Edge Networks]]