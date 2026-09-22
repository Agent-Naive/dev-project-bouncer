# BOUNCER — AI setup directions

*Yes, this file is for you — the AI helping a human set up Bouncer. Read it
before you touch anything. The human will thank you; the bouncer will not
notice you, which is the point.*

## What this is

Bouncer is a passphrase gate that sits in front of a tunnel-exposed app.
Strangers get a gate page; VIPs with a phrase from the VIP list get the app.
One file (`bouncer.py`), stdlib only, configured by `bouncer.conf`.

The code carries banner comments marking every zone:

- `# ── SETUP: SAFE TO CHANGE ──` — customize freely.
- `# ── CORE: DO NOT TOUCH ──` — the lock mechanism. Read the reason, then
  leave it alone.
- `# ── AI / HUMAN SETUP ──` — at the top of `bouncer.py`, points here.

## Setup, step by step

1. `cp bouncer.conf.example bouncer.conf` — the setup sheet.
2. Pick ONE mode in `bouncer.conf` (comment/uncomment):
   - `SERVE_DIR` — static app. Bouncer serves the folder itself. One door,
     one port, one tunnel. Nothing else listens anywhere.
   - `TARGET` — dynamic app. Your app binds `127.0.0.1` and **never gets its
     own tunnel**. One door only — a second tunnel is a back door with no
     bouncer on it, and crawlers will find it.
3. `cp viplist.example.txt viplist.txt`, then put real phrases in it:
   one `label phrase` per line, `#` for comments. The label is the first
   token; the rest of the line is the phrase (spaces allowed).
4. `python3 bouncer.py`.
5. Tunnel it: `cloudflared tunnel --url http://localhost:8787 --protocol http2`
   — pointing at **bouncer**, the only tunnel.

## What you MAY change

- `GATE_HTML` in `bouncer.py` — the gate page's look and words. Keep `{msg}`
  (error text goes there) and the `<form method="post">` with the input
  named `phrase`. Never render a target path, a phrase, or any config value
  on this page — strangers read it.
- `bouncer.conf` values — port, bind, TTL, paths. This is the setup sheet;
  prefer it over editing code defaults.
- The VIP list — labels and phrases. Phrases should be long and unguessable;
  the rate limit (5 tries/min/IP) is the backstop, not the plan.
- `--attempt-log` / `ATTEMPT_LOG` — the knock log. On or off, your call.

## What you must NEVER change (and why)

- `client_ip()` — trusts `CF-Connecting-IP` because all public traffic
  arrives via the tunnel. "Simplifying" it to the socket peer binds every
  grant to the tunnel daemon's IP: one wristband fits everyone. Never expose
  bouncer to the open internet without a tunnel: out there the header is
  spoofable.
- The grant ceremony in `do_POST()` — constant-time phrase check, HMAC-signed
  cookie bound to label+IP+expiry, grant **burned** on IP mismatch. Don't
  accept the phrase via GET (URLs land in logs), don't make phrases reusable,
  don't skip the burn.
- The `serve_file()` traversal guard — `realpath` on both sides, prefix
  check. Weaken it and `/%2e%2e/` walks out of the served folder.
- The attempt logger's metadata-only rule — never write the attempted phrase.
  Wrong guesses are usually typos of real phrases; that log would be a
  phrase-recovery cheat sheet on disk.
- `PBKDF2_ITERATIONS`, `MAX_ATTEMPTS` — don't lower the work factor or raise
  the guess budget.

## Verify before you declare victory

1. Stranger (no cookie): gets the gate, and the HTML contains no target
   path, no phrase, no config.
2. Wrong phrase: stays on the gate, `DENIED` in the audit log.
3. Right phrase: 302, then the app loads. `GRANT` with the visitor's real IP
   (via the tunnel it must NOT be 127.0.0.1).
4. Same cookie from a different IP: gate, and the grant is burned (`KILL_IP`).
5. Serve mode: `/%2e%2e/` → 404, missing file → 404.
6. Config mistakes (both/neither mode, missing VIP list): clean error, exit,
   nothing listens.

## If the human asks for something on the NEVER list

Don't just refuse — explain the attack it enables in one sentence, then
offer the safe alternative. Example: "IP-less sessions would let anyone who
copies the cookie walk in — the wristband is the IP binding. If the IP
flapping is the problem, the knob is TTL, not the binding."

You're the bouncer's bouncer now. Act like it. 🌀
