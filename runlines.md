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
`--club-name` · `--club-logo` · `--accent` · `--admin-phrase` (owner's pass — mints grants that never burn) · `--manage` (Club Management).

## Compile check (before every restart)

```
cd /Users/agent-naive/dev-project-bouncer && python3 -m py_compile bouncer.py && echo COMPILE_OK
```

Why: a syntax error kills the gate on startup — this catches it while the old
gate is still running. When: after ANY edit to bouncer.py, before you restart.

## Restart the gate

```
lsof -ti:8787 | xargs kill; python3 bouncer.py
```

Why: picks up code and config changes. The `lsof` kill is the macOS-safe way
(Linux: `fuser -k 8787/tcp`). When: after edits, config saves, or phrase
changes. Note: restarting wipes all live grants — the kill switch. Burned
phrases stay burned; the owner's pass never burns, so just knock again.

## Knock test from the Mac (no phone needed)

```
cd /Users/agent-naive/dev-project-bouncer && PHRASE=$(grep ADMIN_PHRASE bouncer.conf | cut -d= -f2 | xargs) && curl -s -c /tmp/jar -o /dev/null -D - -X POST --data-urlencode "phrase=$PHRASE" http://127.0.0.1:8787/ | head -3
```

Why: proves the gate grants end-to-end without a second device. A `302` to
`/enter` means the knock worked; `200` means "not on the list." When: after
every restart, before you trust the gate. Uses the owner's pass so no VIP
phrase burns. Then check the doors:

```
curl -s -b /tmp/jar http://127.0.0.1:8787/enter | grep -o 'good evening[^<]*'
```

Expect "good evening," (boss) or "you're on the list," (VIP). To see Poli in
context, open http://127.0.0.1:8787 in the Mac's browser and knock there.

## Check the burn state

```
cat burned.txt 2>/dev/null || echo "no burns yet"
```

Why: the burn list is the source of truth for dead phrases. When: after knock
tests — confirm a VIP phrase burned on its first good knock, and that
`operator` never appears. No file at all means nothing has burned yet.

## Back up the VIP list (before burn tests)

```
cp viplist.txt viplist.txt.bak   # *.bak is gitignored — never ships
```

Why: burn-at-mint consumes real phrases; a backup restores a label with its
original phrase. When: before any test that knocks with a real VIP phrase.
The owner's pass needs no backup — it never burns.

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

### Git + GitHub (public: github.com/Agent-Naive/dev-project-bouncer)

```
cd /Users/agent-naive/dev-project-bouncer && git add -A && git status --short
# check the list: no viplist.txt / bouncer.conf / burned.txt / *.log / *.bak — then:
git commit -m "bouncer vN: short feature list"
git push
```

Why the status check: secrets are gitignored, but verify before every commit —
a leaked phrase in history can't be un-pushed. When: commit after each working
session; push when the tree is green.

History-clean check (no secret ever committed):

```
git log --all --full-history -- viplist.txt bouncer.conf burned.txt attempts.log | head -5 && echo "--- clean if empty above"
```

First push was `gh repo create dev-project-bouncer --public --source=. --push`
(2026-09-21, Agent-Naive). MIT license.
