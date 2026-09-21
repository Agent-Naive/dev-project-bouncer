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
- [ ] git init (local only, no remotes) + scaffold commit

## Phase 1 — v1 build (bouncer.py) [designed, NOT yet authorized]

Single stdlib-only Python file. No dependencies, no pip, no venv.

- [ ] Gate: one URL serves the passphrase page until a valid signed session cookie exists
- [ ] Passphrase verification, server-side only: PBKDF2 (hashlib) + hmac.compare_digest
- [ ] Signed session cookies: HMAC with a per-start random secret
- [ ] Reverse-proxy to the target over localhost (target path never client-visible)
- [ ] Per-guest phrases: table of phrase_hash -> {bound_ip, expires_at}
- [ ] Client IP read from CF-Connecting-IP — NOT the socket peer (the critical gotcha;
      the socket peer is the tunnel daemon, binding to it makes the feature theater)
- [ ] TTL per grant; IP mismatch kills the grant; restart wipes all grants (kill switch)
- [ ] Rate-limit passphrase attempts per IP
- [ ] Audit log: phrase label, first-seen IP, grant/expiry/kill events
- [ ] Nothing sensitive in served HTML/JS; no second path ever client-visible

## Phase 2 — Test

- [ ] Local: gate blocks unauthenticated; correct phrase grants; wrong phrase rejected
- [ ] IP change mid-session kills the grant; TTL expiry kills the grant
- [ ] Hash/secret never appear in responses or logs
- [ ] Tunnel test via trycloudflare: CF-Connecting-IP binding verified end-to-end
- [ ] Runlines tested, not transcribed — a runline that never ran is a rumor

## Phase 3 — Release (public, free)

- [ ] README polished for strangers (60-second orient)
- [ ] LICENSE — MIT
- [ ] Mascot: cartoony bouncer with the 🌀 on his t-shirt (earpiece, clipboard, strong eyebrows — non-negotiable)
- [ ] Public repo; announce where appropriate

## Phase 4 — Adopt

- [ ] Apply to the SHQL stack (after the public release)

## Project needs

- Python 3.x (stdlib only)
- cloudflared (for tunnel testing and real use)
- Any machine to expose — any OS. Nothing here is Mac-specific.
