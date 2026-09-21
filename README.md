# BOUNCER 🌀

*Put a bouncer on your tunnel.*

Bouncer is a tiny passphrase gate that stands in front of anything you expose to the internet — the "jump gate" (🌀) you drop into your runline. One Python file, stdlib only, free forever.

## What it is

- A single-file reverse proxy with a passphrase door. One URL serves a passphrase page to strangers and the real app to guests holding a valid session.
- Per-guest passphrases: each phrase binds to the first IP that uses it, then dies on a timer. (*"Is your name on the list?"*)
- Built for the trycloudflare era: automated crawlers sweep public tunnels looking for IP and ideas. The bouncer keeps the riffraff outside the velvet rope.

## What it is not

- Not a VPN, not identity management, not SSO.
- Not obscurity as security: the gate page announces "something is here." It just never shows the goods without the phrase.
- IP binding is a speed bump, not a wall — NAT sharing and roaming phones. See docs/DESIGN.md for the honest weaknesses.

## Hard rules

- Secrets never touch the repo. Passphrases are issued to guests, never committed, never pasted into docs.
- Stdlib only. If it needs pip, it doesn't belong in v1.
- Default-OFF: nothing is exposed unless a human deliberately arms the tunnel.
- The gate lives outside the served folder hierarchy — a separate process in front, never a file inside the web root.

## Status

v1 is designed (docs/DESIGN.md) and not yet built. Build plan: docs/TODO.md.

## Runlines

See runlines.md. Project runlines are live; app runlines land with the v1 build.
