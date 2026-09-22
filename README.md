# The Bouncer 🌀

*Put a bouncer on your tunnel.*

The Bouncer is a tiny passphrase gate that stands in front of anything you expose to the internet — the "jump gate" (🌀) you drop into your runline. One Python file, stdlib only, free forever.

## What it is

- A single-file passphrase gate with two modes. One URL serves a passphrase page to strangers and the real app to VIPs holding a valid session — serve mode for static apps (bouncer IS the server, one door), proxy mode for dynamic apps.
- Per-VIP passphrases: each phrase binds to the first IP that uses it, then dies on a timer. (*"Is your name on the list?"*)
- The night runs in three beats: **the line** (branded gate page) → **the doors** (`/enter` — "you're on the list, {label}", the doors swing open) → **the club** (your app). Your club name, logo, and colors hang over the house scene — see `docs/BRANDING.md`.
- Setup three ways, one contract (`bouncer.conf`): your AI (see `docs/AI-Setup-Directions.md`), **Club Management** (`python3 bouncer.py --manage` — a local-only web form, never tunneled), or the terminal.
- Built for the trycloudflare era: automated crawlers sweep public tunnels looking for IP and ideas. The bouncer keeps the riffraff outside the velvet rope.

## What it is not

- Not a VPN, not identity management, not SSO.
- Not obscurity as security: the gate page announces "something is here." It just never shows the goods without the phrase.
- IP binding is a speed bump, not a wall — NAT sharing and roaming phones. See docs/DESIGN.md for the honest weaknesses.

## Who it's for

Anyone whose app has a public URL and no auth — which is more people than admit it.

The trycloudflare story was just the first instance. The general shape: **any public URL with no auth is findable; the only question is what the finder meets.** Random-word tunnel URLs are obscurity, not security — four common words is a tiny space for a script to walk, and frontier crawlers sweep public tunnels looking for IP and ideas.

- **trycloudflare / Cloudflare quick tunnels** — the origin story. Word-combo hostnames, enumerable, zero auth. Bouncer in front, done.
- **ngrok (free tier)** — random hex subdomain, harder to guess but still unauthenticated. ngrok's own auth is paywalled; The Bouncer is the free, self-hosted answer.
- **Railway / Render / Fly preview deploys** — `*.up.railway.app` and friends are public by default with no built-in gate. Sweet spot: Bouncer listens on the platform's `$PORT`, your app binds `127.0.0.1` behind it in proxy mode. One door, same as the tunnel setup.
- **A raw VPS with a public IP** — same shape. Bouncer as the front door, app behind it.
- **Demos, webhook receivers, personal projects, friends-and-family** — anywhere the alternative today is "hope nobody finds the URL."

The honest version, because we're never trying to be something we're not: this is a *shared passphrase* gate, not identity. One phrase per VIP label; revocation means burn-and-rotate. It's the right tool for demos, previews, and personal projects — it is not a replacement for real auth (OAuth, SSO) on a production multi-user app. And the one-door rule still applies everywhere: if the backend is directly reachable, the bouncer is decoration.

## Hard rules

- Secrets never touch the repo. Passphrases are issued to VIPs, never committed, never pasted into docs.
- Stdlib only. If it needs pip, it doesn't belong in v1.
- Default-OFF: nothing is exposed unless a human deliberately arms the tunnel.
- One door: the gate only works if it's the only public URL. Never give the backend its own tunnel. Never tunnel Club Management.

## Status

v1 built + tested (Linux VM, 2026-09-21); v2 adds serve mode, bouncer.conf, VIP-list rename. Mac tunnel test passed (2026-09-21). v3 adds the three-beat night (branded gate, `/enter` doors page), marquee slots (`CLUB_NAME`/`CLUB_LOGO`/`ACCENT`), and Club Management — built + tested on the VM 2026-09-21.

## Runlines

See runlines.md.
