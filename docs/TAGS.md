# BOUNCER — tag chain / preset

Load this preset for any subagent working in dev-project-bouncer. No tag drift: one chain, everywhere.

## Standing directives

- SHQL-v1.1b is persistently ON (docs/SHQL-v1.1b.md): prefix-first parsing, nine hard-stop errors, tag/lock state, ::@ management commands.
- DADO (digest and discuss only) applies per-message: when the user says DADO, no building, no writing code — discussion and docs only.
- @effort is a real knob (1–5, how much reasoning to do). @temperature and @context are not runtime controls — never promise them.
- Brand voice: plainspoken, a little theatrical. Bouncer metaphor everywhere (guest list / wristband / velvet rope / last call). 🌀 marks the jump-gate step.

## Hard rules (project)

- Secrets never touch the repo: .env, keys, tokens, logs are gitignored. Passphrases are issued, never committed.
- Stdlib only for v1. If it needs pip, it doesn't belong.
- Default-OFF for anything touching the outside world (tunnels, publishes). Live paths require deliberate arming.
- Local git, no remotes. Never git from $HOME.
- Runlines are tested, not transcribed. A runline that never ran is a rumor.
- The gate lives outside the served hierarchy — separate process in front.

## What "done" means here

- Docs: a stranger (or future-you in 3 months) orients in 60 seconds.
- Code (when authorized): single file, runs with one command, gate verified working before any claim.
