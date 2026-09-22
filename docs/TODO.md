# THE BOUNCER — TODO / project needs

## Phase 0 — Scaffold (docs) [done]

- [x] Project dir + docs/SHQL-v1.1b.md + New-Project.md (Jeffrey)
- [x] docs/TODO.md (this file)
- [x] README.md — what/why, what-it-is-not, hard rules, runlines pointer
- [x] docs/BRAND.md — brand lockup
- [x] docs/DESIGN.md — technical design from the DADO sessions
- [x] docs/TAGS.md — subagent tag chain / preset
- [x] runlines.md — setup/run/tunnel/kill
- [x] HANDOFF-LOG.md — session continuity
- [x] .gitignore — secrets never touch the repo
- [x] git init (local only, no remotes) + scaffold commit (5d416b5, 2026-09-21)

## Phase 1 — v1 build (bouncer.py) [BUILT + TESTED 2026-09-21]

Single stdlib-only Python file. No dependencies, no pip, no venv.

- [x] Gate: one URL serves the passphrase page until a valid signed session cookie exists
- [x] Passphrase verification, server-side only: PBKDF2 (hashlib) + hmac.compare_digest
- [x] Signed session cookies: HMAC with a per-start random secret, IP-bound
- [x] Reverse-proxy to the target over localhost (target path never client-visible; streamed, not buffered)
- [x] Per-guest phrases: table of phrase_hash -> {bound_ip, expires_at}; one-shot (burned after use)
- [x] Client IP read from CF-Connecting-IP — NOT the socket peer (the critical gotcha)
- [x] TTL per grant; IP mismatch kills the grant; restart wipes all grants (kill switch)
- [x] Rate-limit passphrase attempts per IP (5/min, then 429)
- [x] Audit log: phrase label, first-seen IP, grant/expiry/kill events
- [x] Nothing sensitive in served HTML/JS; no second path ever client-visible

Decisions locked during build:
- One-shot phrases: after a grant dies (IP mismatch or TTL), the phrase is
  burned into burned.txt (the forbidden list) and stays burned across
  restarts — only a fresh phrase (Club Management regenerate) re-arms the
  label. (Matches "poof the access dies", now durable.)
- Cookie HMAC is verified against the grant's bound values (not the request IP),
  so a wrong-IP cookie both fails AND burns the grant with a KILL_IP audit line.
  (First implementation verified against the request IP, which made KILL_IP/EXPIRED
  unreachable — caught by testing, fixed before shipping.)

## Phase 1.5 — One door (2026-09-21) [BUILT + TESTED on Linux VM]

The gate only works if it's the only public URL — a second tunnel to the
backend walks right around the bouncer. So:

- [x] Serve mode: `--serve DIR` / `SERVE_DIR` serves static files to authed VIPs;
      bouncer is the only server listening (one door, one port, one tunnel)
- [x] `bouncer.conf`: KEY = value setup file, comment/uncomment per need; CLI overrides
- [x] Rename: guest list -> VIP list (`viplist.txt`, `--viplist`, `VIPLIST` key)
- [x] Path-traversal guard on serve mode (realpath must stay under SERVE_DIR)
- [x] Config validation fails closed: both/neither mode set -> error; no VIPLIST -> error
- [x] Threat model updated: one-door requirement in docs/DESIGN.md
- [x] Attempt logger (2026-09-21, Jeffrey's call): `--attempt-log` / `ATTEMPT_LOG`,
      one JSON line per gate knock (ts, ip, result, label, user-agent); metadata only,
      never the phrase text. Tested on the VM: denied/granted/ratelimited logged,
      valid JSON, no phrase leakage.

## Phase 2 — Test

- [x] Local (Linux VM, 2026-09-21): gate blocks unauthenticated; correct phrase grants;
      wrong phrase rejected; IP change kills grant (KILL_IP); TTL expiry kills grant
      (EXPIRED); burned phrase rejected; 6th rapid attempt -> 429; no hash/secret in
      responses or logs. Full battery in HANDOFF-LOG.md.
- [x] Tunnel test via trycloudflare on the Mac (2026-09-21): gate -> wrong phrase denied
      ("not on the list.") -> correct phrase granted -> green dummy page, end-to-end
      through the tunnel in serve mode. One-door architecture verified live.
- [x] Runlines: app runlines tested on Linux; tunnel runline verified on the Mac

## Phase 2.5 — The night: branding + Club Management [BUILT + TESTED 2026-09-21]

Jeffrey: don't lose the branding opportunity — the VIP should *feel* the doors
opening, and the operator's club name should hang over Bouncer's house scene.

- [x] Three beats: the line (branded gate `/`) -> the doors (`/enter`,
      "you're on the list, {label}", doors swing open) -> the club (app at `/`)
- [x] Grant 302s to `/enter` (was `/`); `/enter` gated on a live grant
      (no grant -> back to the gate); "step inside" button stays on-origin
- [x] Marquee slots: `CLUB_NAME` / `CLUB_LOGO` / `ACCENT` in bouncer.conf
      (+ `--club-name` / `--club-logo` / `--accent` flags); name+label
      HTML-escaped, bad accent falls back to house gold
- [x] House scene: inline SVG rope + posts + red carpet (`SCENE_SVG`);
      mascot moves in later
- [x] Club Management (`--manage`): local-only web form (127.0.0.1 forced,
      never tunnel it) — pre-fills from current config, phrases masked with
      regenerate checkboxes, `gen_phrase()` 5-word generator, writes `bouncer.conf`
      (unknown keys and comments preserved) + `viplist.txt`, new phrases shown once
- [x] Three writers, one contract: AI (AI-Setup-Directions.md), Club
      Management, terminal — same schema, same order
- [x] `docs/BRANDING.md`: slot list, sizes, formats, what-not-to-do
- [x] VM battery: branding render, doors flow, manage save/prefill/phrases,
      XSS escaping, accent fallback, proxy still clean, one-shot + KILL_IP
      + 429 + traversal all still green

## Phase 2.6 — Per-VIP TTL, durable burns, wristband announcement (2026-09-21) [BUILT + TESTED on Linux VM]

- [x] `burned.txt`: every burn (EXPIRED/KILL_IP) appended to disk, loaded at
      startup — a restart can't re-arm a dead phrase. `--burned` / `BURNED` key;
      gitignored. Club Management shows the burned-out list and the burned-file
      path; regenerating a phrase re-arms the label (dropped from burned.txt
      on save — the only way back in).
- [x] Per-VIP grant lifetime: `label ttl phrase` lines in viplist.txt; blank =
      the house TTL from bouncer.conf. Backward compatible (`label phrase`
      still works). Club Management has a per-row TTL field (blank = house);
      the confirm page shows each new phrase's wristband length.
- [x] `/enter` announces the wristband: "this wristband is good for 8 hours —
      last call 6:04 PM."

## Phase 3 — Release (public, free)

- [ ] README polished for strangers (60-second orient)
- [ ] LICENSE — MIT
- [ ] Mascot: cartoony bouncer with the 🌀 on his t-shirt (earpiece, clipboard, strong eyebrows — non-negotiable)
- [ ] Public repo; announce where appropriate

## Phase 4 — Adopt

- [ ] Apply to the SHQL stack (after the public release)

## Future ideas

- Club Management: one-time token in the URL as a second local-only control
- Doors page: per-VIP "welcome back" when the label already holds a grant
- Poli X promo cards, more catchphrase variants on deck (build with
  ~/workspace/poli-promo/build_cards.py): "The list. Let's see it.",
  "Talk to the clipboard.", "Poli knows the face.",
  "Put a bouncer on your tunnel."

## Project needs

- Python 3.x (stdlib only)
- cloudflared (for tunnel testing and real use)
- Any machine to expose — any OS. Nothing here is Mac-specific.
