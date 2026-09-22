# BOUNCER 🌀

*Put a bouncer on your tunnel.*

Bouncer is a tiny passphrase gate that stands in front of anything you expose to the internet — the "jump gate" (🌀) you drop into your runline. One Python file, stdlib only, free forever.

## What it is

- A single-file passphrase gate with two modes. One URL serves a passphrase page to strangers and the real app to VIPs holding a valid session — serve mode for static apps (bouncer IS the server, one door), proxy mode for dynamic apps.
- Per-VIP passphrases: each phrase binds to the first IP that uses it, then dies on a timer. (*"Is your name on the list?"*)
- Built for the trycloudflare era: automated crawlers sweep public tunnels looking for IP and ideas. The bouncer keeps the riffraff outside the velvet rope.

## What it is not

- Not a VPN, not identity management, not SSO.
- Not obscurity as security: the gate page announces "something is here." It just never shows the goods without the phrase.
- IP binding is a speed bump, not a wall — NAT sharing and roaming phones. See docs/DESIGN.md for the honest weaknesses.

## Hard rules

- Secrets never touch the repo. Passphrases are issued to VIPs, never committed, never pasted into docs.
- Stdlib only. If it needs pip, it doesn't belong in v1.
- Default-OFF: nothing is exposed unless a human deliberately arms the tunnel.
- One door: the gate only works if it's the only public URL. Never give the backend its own tunnel.

## Status

v1 built + tested (Linux VM, 2026-09-21); v2 adds serve mode, bouncer.conf, VIP-list rename. Mac tunnel test pending.

## Runlines

See runlines.md. Project runlines are live; app runlines land with the v1 build.
