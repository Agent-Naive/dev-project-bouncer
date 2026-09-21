# BOUNCER — technical design

Status: designed under DADO (discuss only). Not yet built.

## The gate

```
visitor → tunnel URL → bouncer (localhost:PORT)
                            │
                   valid session cookie?
                      /            \
                    no              yes
                     │                │
              passphrase page    proxy to the app
              (nothing else       (same URL — the real
               is served)          path never appears
                                   client-side)
```

- One URL, two faces. The app path is never revealed client-side — no second URL in HTML, JS, or redirects. No breadcrumbs.
- Passphrase verified server-side only: PBKDF2 (hashlib, stdlib) + hmac.compare_digest. Only salted hashes are stored.
- Session cookie: HMAC-signed with a per-start random secret.
- The gate is a separate process in front of the app — outside the served folder hierarchy, never a file inside the web root.

## Per-guest phrases

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
- Restarting bouncer wipes all grants — the kill switch.
- Audit log: phrase label, first-seen IP, grant/expiry/kill events.

## The critical gotcha: which IP?

Behind a tunnel, the socket peer is NOT the guest — it's the tunnel daemon (localhost) or the provider's edge. The guest's real IP arrives in the `CF-Connecting-IP` header (Cloudflare). The binding MUST read that header. Bind to the socket IP and every guest shares one address — the feature becomes theater.

## Threat model

Stops: drive-by crawlers, casual snoopers, anyone without a phrase. Phrase-sharing is mostly contained by IP binding + TTL.  
Does not stop: a guest leaking their phrase to someone on the same NAT (shared public IP); the tunnel provider itself seeing traffic (inherent to any tunnel); targeted attackers (out of scope).  
The gate page announces "something is here" — obscurity was never the goal.

## Honest weaknesses

- IP is a weak authenticator. Same-house/office guests share a public IP.
- Strictness cuts both ways: phones hopping WiFi→cellular, rotating home IPs, VPN toggles can lock out legit guests mid-visit. Fix: issue a fresh phrase.
- Roughly one phrase per device: a guest's phone and laptop are different IPs.

## Rate limiting

Slow passphrase attempts per IP (delay + attempt counting). Cheap, effective against guessing.

## v1 scope

Single file, stdlib only: gate, hashing, signed cookies, proxy, per-guest table, TTL, audit log, rate limiting. No pip, no venv.
