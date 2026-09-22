# THE BOUNCER — runlines

## Setup (once)

```
cp bouncer.conf.example bouncer.conf   # uncomment ONE mode: SERVE_DIR or TARGET
cp viplist.example.txt viplist.txt     # then put real phrases in viplist.txt
```

`bouncer.conf` is the setup sheet — comment/uncomment what you need. CLI flags override it.

Three writers, one contract (`bouncer.conf`): the AI (see
docs/AI-Setup-Directions.md), Club Management below, or the terminal.

## Club Management (local setup — never tunnel)

```
python3 bouncer.py --manage   # back office on 127.0.0.1:8787
```

Opens a form in your browser that writes `bouncer.conf` + `viplist.txt`.
First run: blank. Later runs: pre-filled from the current config, phrases
masked with regenerate. New phrases are shown once — copy them to your VIPs.
**LOCAL ONLY. Never tunnel this page — it writes your config.**

## Run the gate

```
# serve mode (static app — bouncer IS the server, one door):
python3 bouncer.py

# proxy mode (dynamic app): uncomment TARGET in bouncer.conf first,
# bind your app to 127.0.0.1, and NEVER give it its own tunnel.
```

The night, in three beats: the line (branded gate `/`) → the doors
(`/enter`, "you're on the list, {label}") → the club (your app at `/`).

Flags: `--serve DIR` · `--target URL` · `--viplist` · `--port` (8787) ·
`--bind` (127.0.0.1) · `--ttl` seconds (86400) · `--audit-log` path (stdout) ·
`--attempt-log` path (JSON-lines knock log, off by default) ·
`--burned` path (spent-labels file, ./burned.txt) ·
`--club-name` · `--club-logo` · `--accent` · `--manage` (Club Management).

## Tunnel with the jump gate (verified on Mac, 2026-09-21)

```
# The 🌀 step: bouncer runs first, tunnel points at bouncer — the ONLY tunnel.
cloudflared tunnel --url http://localhost:8787 --protocol http2
```

## Kill the tunnel + gate

```
pkill -f "cloudflared tunnel"; pkill -f "[b]ouncer.py"
# bracket trick: [b] matches "b" in the target's command line but not in pkill's
# own, so pkill doesn't commit suicide. learned the hard way 2026-09-21.
# (careful: your own shell command line can also match — fuser -k PORT/tcp
# is the bulletproof kill on Linux, but macOS fuser has no -k: use
# lsof -ti:8787 | xargs kill instead. learned 2026-09-21.)
# Restarting bouncer wipes all grants — the kill switch.
# Burned phrases stay burned across restarts (burned.txt) — only a fresh
# phrase re-arms a label.
```

## Tested (Linux VM, 2026-09-21)

Full battery passed: gate blocks strangers; correct phrase grants (302 → /enter);
wrong phrase denied; doors page greets VIP by label; /enter without grant → gate;
IP change kills grant (KILL_IP); TTL expiry (EXPIRED); burned phrase rejected;
6th rapid attempt -> 429; serve mode traversal blocked; branded gate (club name,
logo, accent fallback, XSS-escaped); Club Management save + prefill + phrase
generation; proxy mode clean; config errors fail closed. Fix battery (2026-09-21):
mode switch blanks the stale key (no more fail-closed on switch); blank
attempt-log field disables logging; multi-line pasted logo collapses to one
line; authed POST/PUT/PATCH/DELETE reach the backend (not the knock ceremony)
and skip the knock rate limit; phrase preserve/regenerate + duplicate-label
400; comments and unknown config keys survive a Management save.
See HANDOFF-LOG.md.

### v4 battery (Linux VM, 2026-09-21) — 23/23 + 11/11
burned.txt: EXPIRED and KILL_IP burns persisted to disk; burned phrases
denied after restart; live labels unaffected. Per-VIP TTL: `label ttl phrase`
grants honored the VIP's TTL (5s / 7200s) while 2-token lines used the house
TTL; invalid row TTL rejected (400); untouched rows kept their TTL; unknown
config keys and comments survived a manage save; duplicate labels still 400.
/enter announces "this wristband is good for X — last call HH:MM PM".
Club Management: burned-file path field, per-row TTL inputs (blank = house),
burned-out list display, regenerate re-arms a burned label (new phrase grants,
old phrase stays dead). Full battery in HANDOFF-LOG.md (Session 8).

## Project

### Git (local only, no remotes)

```
cd /Users/agent-naive/dev-project-bouncer && git add -A && git commit -m "bouncer v4: Poli, burn-at-mint, owner's pass"
```
