# BOUNCER — TODO / project needs

## Phase 0 — Scaffold (docs) [in progress]

- [x] Project dir + docs/SHQL-v1.1b.md + New-Project.md (Jeffrey)
- [x] docs/TODO.md (this file)
- [ ] README.md — what/why, what-it-is-not, hard rules, runlines pointer
- [ ] docs/BRAND.md — brand lockup
- [ ] docs/DESIGN.md — technical design from the DADO sessions
- [ ] docs/TAGS.md — subagent tag chain / preset
- [ ] runlines.md — setup/run/tunnel/kill
- [ ] HANDOFF-LOG.md — session continuity
- [ ] .gitignore — secrets never touch the repo
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
- One-shot phrases: after a grant dies (IP mismatch or TTL), the phrase is burned
  until the operator restarts bouncer. (Matches "poof the access dies".)
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
- [ ] Runlines: app runlines tested on Linux; tunnel runline needs Mac verification

## Phase 3 — Release (public, free)

- [ ] README polished for strangers (60-second orient)
- [ ] LICENSE — MIT
- [ ] Mascot: cartoony bouncer with the 🌀 on his t-shirt (earpiece, clipboard, strong eyebrows — non-negotiable)
- [ ] Public repo; announce where appropriate

## Phase 4 — Adopt

- [ ] Apply to the SHQL stack (after the public release)

## Future ideas

(none yet — the attempt logger was here, now it's built. see Phase 1.5.)

## Project needs

- Python 3.x (stdlib only)
- cloudflared (for tunnel testing and real use)
- Any machine to expose — any OS. Nothing here is Mac-specific.
