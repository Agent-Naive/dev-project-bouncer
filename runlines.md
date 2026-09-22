# BOUNCER — runlines

## Setup (once)

```
cp bouncer.conf.example bouncer.conf   # uncomment ONE mode: SERVE_DIR or TARGET
cp viplist.example.txt viplist.txt     # then put real phrases in viplist.txt
```

`bouncer.conf` is the setup sheet — comment/uncomment what you need. CLI flags override it.

## Run the gate

```
# serve mode (static app — bouncer IS the server, one door):
python3 bouncer.py

# proxy mode (dynamic app): uncomment TARGET in bouncer.conf first,
# bind your app to 127.0.0.1, and NEVER give it its own tunnel.
```

Flags: `--serve DIR` · `--target URL` · `--viplist` · `--port` (8787) ·
`--bind` (127.0.0.1) · `--ttl` seconds (86400) · `--audit-log` path (stdout) ·
`--attempt-log` path (JSON-lines knock log, off by default).

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
# Restarting bouncer wipes all grants — the kill switch.
```

## Tested (Linux VM, 2026-09-21)

Full battery passed: gate blocks strangers; correct phrase grants (302 + cookie);
wrong phrase denied; IP change kills grant (KILL_IP); TTL expiry (EXPIRED);
burned phrase rejected; 6th rapid attempt -> 429; serve mode traversal blocked;
config errors fail closed. See HANDOFF-LOG.md.

## Project

### Git (local only, no remotes)

```
cd /Users/agent-naive/dev-project-bouncer && git add -A && git commit -m "bouncer v2: serve mode, bouncer.conf, VIP list"
```
