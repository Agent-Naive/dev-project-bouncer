# THE BOUNCER — technical design

Status: v1 built + tested (Linux VM, 2026-09-21, proxy mode). v2 adds serve mode
(one-door static), bouncer.conf setup file, VIP-list rename — built + tested
2026-09-21. Mac tunnel test pending.

## The gate

```
visitor → tunnel URL → bouncer (localhost:PORT)
                            │
                   valid session cookie?
                      /            \
                    no              yes
                     │                │
              passphrase page    behind the rope:
              (nothing else       serve mode → static files
               is served)         proxy mode → forward to the app
                                  (same URL — the real
                                   path never appears
                                   client-side)
```

- One URL, two faces. The app path is never revealed client-side — no second URL in HTML, JS, or redirects. No breadcrumbs.
- Two modes, one door: serve mode (bouncer IS the server — nothing else listens)
  or proxy mode (bouncer forwards to a localhost backend). Pick ONE in bouncer.conf.
- Passphrase verified server-side only: PBKDF2 (hashlib, stdlib) + hmac.compare_digest. Only salted hashes are stored.
- Session cookie: HMAC-signed with a per-start random secret.
- The gate is a separate process in front of the app — outside the served folder hierarchy, never a file inside the web root.

## Per-VIP phrases

```
phrase X (fresh) ── Joe enters ──► bound to Joe's IP, TTL starts
                                        │
                        each request ──► IP still matches? ── no ──► gate (dead)
                                        │ yes
                                        ▼
                                   TTL alive? ── no ──► gate (dead)
                                        │ yes
                                        ▼
                                      proxied ✓
```

- Each phrase is an independent row: phrase_hash -> {bound_ip, expires_at}.
- First use binds the phrase to the client IP; the grant dies if the IP changes or the TTL expires.
- One-shot (decided 2026-09-21): after a grant dies, the phrase is burned — it can
  never grant again until the operator restarts bouncer. Matches "poof the access dies".
- Restarting bouncer wipes all grants — the kill switch.
- Audit log: phrase label, first-seen IP, grant/expiry/kill events.

## The critical gotcha: which IP?

Behind a tunnel, the socket peer is NOT the guest — it's the tunnel daemon (localhost) or the provider's edge. The guest's real IP arrives in the `CF-Connecting-IP` header (Cloudflare). The binding MUST read that header. Bind to the socket IP and every guest shares one address — the feature becomes theater.

## Threat model

Stops: drive-by crawlers, casual snoopers, anyone without a phrase. Phrase-sharing is mostly contained by IP binding + TTL.  
Does not stop: a guest leaking their phrase to someone on the same NAT (shared public IP); the tunnel provider itself seeing traffic (inherent to any tunnel); targeted attackers (out of scope).  
The gate page announces "something is here" — obscurity was never the goal.

## One door (2026-09-21)

The gate only works if it's the only public URL. In proxy mode the backend
must bind 127.0.0.1 and must never get its own tunnel — a second tunnel is a
second door with no bouncer on it, and crawlers will find it. Serve mode
removes the class entirely: bouncer is the only server listening, one port,
one tunnel, nothing else to walk around.

## Honest weaknesses

- IP is a weak authenticator. Same-house/office guests share a public IP.
- Strictness cuts both ways: phones hopping WiFi→cellular, rotating home IPs, VPN toggles can lock out legit guests mid-visit. Fix: issue a fresh phrase.
- Roughly one phrase per device: a guest's phone and laptop are different IPs.

## Rate limiting

Slow passphrase attempts per IP (delay + attempt counting). Cheap, effective against guessing.

## v1 scope

Single file, stdlib only: gate, hashing, signed cookies, proxy, per-guest table, TTL, audit log, rate limiting. No pip, no venv.

## v2 scope (2026-09-21)

- Serve mode (`--serve DIR` / `SERVE_DIR`): static files to authed VIPs. Bouncer
  is the only server listening — one door, one port, one tunnel.
- `bouncer.conf`: KEY = value setup file, comment/uncomment per need. CLI flags
  override it. Ships as `bouncer.conf.example`; the live file is gitignored.
- Rename: guest list → VIP list (`viplist.txt`, `--viplist`, `VIPLIST` key).
- Path-traversal guard: realpath of the requested file must stay under SERVE_DIR.
- Config validation fails closed: both/neither mode set → error; no VIPLIST → error.
- Attempt logger (`--attempt-log` / `ATTEMPT_LOG`): one JSON line per knock on the
  gate (ts, ip, result, label, user-agent). Metadata only — never the attempted
  phrase, since wrong guesses are often typos of real ones.
