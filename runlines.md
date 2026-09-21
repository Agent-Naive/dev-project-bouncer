# BOUNCER — runlines

Project runlines (live). App runlines land with the v1 build — anything marked PLANNED is untested, not a rumor I'm selling as fact.

## Project

### Scaffold check

```
ls /Users/agent-naive/dev-project-bouncer
ls /Users/agent-naive/dev-project-bouncer/docs
```

### Git (local only, no remotes)

```
cd /Users/agent-naive/dev-project-bouncer && git init
cd /Users/agent-naive/dev-project-bouncer && git add -A && git commit -m "scaffold"
```

### Kill everything (project-level)

```
# Nothing persistent runs for the scaffold. When bouncer.py exists:
# pkill -f bouncer.py
```

## PLANNED (v1 build — untested until built)

### Run the gate (planned)

```
# python3 bouncer.py --target http://localhost:11435 --port 8787
```

### Tunnel with the jump gate (planned)

```
# cloudflared tunnel --url http://localhost:8787 --protocol http2
# The 🌀 step: bouncer runs first, tunnel points at bouncer, never at the app.
```

### Kill the tunnel + gate (planned)

```
# pkill -f "cloudflared tunnel"; pkill -f bouncer.py
# Restarting bouncer wipes all grants — the kill switch.
```
