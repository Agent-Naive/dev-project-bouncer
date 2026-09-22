# BOUNCER — handoff log

## 2026-09-21 — Session 1 (scaffold)

Done:
- Project created by Jeffrey at /Users/agent-naive/dev-project-bouncer with docs/ + docs/SHQL-v1.1b.md + New-Project.md.
- Scaffold docs created: README.md, docs/BRAND.md, docs/DESIGN.md, docs/TAGS.md, docs/TODO.md, runlines.md, HANDOFF-LOG.md (this file), .gitignore.
- Brand locked: BOUNCER 🌀, "Put a bouncer on your tunnel." Jump gate = the pattern name. Mascot planned: cartoony bouncer, 🌀 on t-shirt.
- Technical design discussed under DADO (gate flow, per-guest IP-bound TTL phrases, CF-Connecting-IP gotcha, threat model). Design lives in docs/DESIGN.md.

Not done (deliberately):
- bouncer.py v1 build — designed, not authorized. Waiting for Jeffrey's go.
- Mascot art, public repo, release — Phase 3.

Next:
- Jeffrey says go → Phase 1 build per docs/TODO.md.

## 2026-09-21 — Session 2 (v1 build + test)

Done:
- Jeffrey said go. Built bouncer.py (~330 lines, stdlib only) on the Linux VM, then
  shipped it to /Users/agent-naive/dev-project-bouncer/bouncer.py.
- Added guests.example.txt (committed example; real guests.txt stays gitignored).
- Full test battery on the VM, all passing:
  T1 stranger gets gate page, no leak of target/secret in HTML
  T2 wrong phrase -> "not on the list."
  T3 correct phrase -> 302 + HttpOnly/Secure cookie -> /secret.txt proxied through
  T4 same cookie from different IP -> gate; KILL_IP audited; grant dead for original IP too
  T5 spent phrase re-entered -> "not on the list." (one-shot burn)
  T6 TTL=3s: immediate fetch proxied, fetch after 4s -> gate; EXPIRED audited
  T7 7 rapid bad attempts from one IP -> 200 x5 then 429 x2; RATELIMITED audited
- Bug caught by testing: first implementation verified the cookie HMAC against the
  *request* IP, which made the KILL_IP and EXPIRED branches unreachable (wrong-IP
  cookies died at signature check before the grant was ever consulted). Fixed by
  verifying against the grant's bound values, then comparing IPs — now a wrong-IP
  cookie both fails and burns the grant with a KILL_IP line.
- Updated runlines.md (app runlines tested on Linux; tunnel runline marked NEEDS MAC
  VERIFICATION), docs/TODO.md (Phase 1 + local Phase 2 checked), docs/DESIGN.md
  (one-shot decision recorded).

Not done:
- Tunnel test via trycloudflare on the Mac (CF-Connecting-IP end-to-end) — needs Jeffrey.
- git add/commit of v1 — needs Jeffrey (no shell on the device side).
- Phase 3 (release) and Phase 4 (adopt on SHQL stack).

Next:
- Jeffrey: run the tunnel test, then git add -A && git commit -m "bouncer v1".

## 2026-09-21 — Session 3 (one door: serve mode, bouncer.conf, VIP list)

The insight (Jeffrey): the gate only works if it's the only public URL. A second
tunnel pointed at the backend walks right around the bouncer — crawlers would find
it. So the local script itself must be the thing that allows/disallows, with one
door: one port, one tunnel, nothing else listening.

Done:
- Serve mode: `--serve DIR` / `SERVE_DIR` — bouncer serves static files to authed
  VIPs directly. No backend process, no second port. Covers static apps; proxy
  mode stays for dynamic ones.
- `bouncer.conf`: KEY = value setup file, comment/uncomment per need (SERVE_DIR vs
  TARGET). CLI flags override it. Ships as bouncer.conf.example; live file gitignored.
- Rename: guest list -> VIP list (`viplist.txt`, `--viplist`, `VIPLIST` key).
  "The bouncer lets you in 'cause you're the shit." — Jeffrey's words, now in the
  example file header.
- Dummy target moved out of the project to /tmp/bouncer-dummy-target (test only).
- Test battery on the Linux VM (exact Mac file, pulled via files.upload), all passing:
  S1 stranger gets gate, zero bytes of the static app leak
  S2 correct phrase -> 302 -> / serves index.html, /sub/deep.txt serves
  S3 /%2e%2e/ traversal -> 404 "nothing here." (realpath pinned under SERVE_DIR)
  S4 missing file -> 404; S5 both/neither mode in config -> clean fail-closed error;
      missing VIPLIST -> clean fail-closed error
  S6 CLI --port overrides config; S7 proxy mode via config TARGET still proxies
- Docs updated: README, runlines.md, docs/BRAND.md, docs/DESIGN.md (one-door threat
  model + v2 scope), docs/TAGS.md, docs/TODO.md (Phase 1.5).
- Live bouncer.conf on the Mac: serve mode -> /tmp/bouncer-dummy-target, port 8787.
- Bug caught on the Mac tunnel test: granted VIPs got "nothing here." (404) instead of
  the static app. Cause: macOS /tmp is a symlink to /private/tmp; serve_dir was
  normalized with abspath (symlink kept) but request paths with realpath (symlink
  resolved), so the traversal guard's prefix check failed on every file. Fixed with
  realpath for serve_dir too; verified on the VM with a symlinked SERVE_DIR (200).

Not done:
- Tunnel test via trycloudflare on the Mac — needs Jeffrey. Now simpler: two
  terminals (python3 bouncer.py, then cloudflared tunnel --url http://localhost:8787).
  No dummy server needed in serve mode.
- git add/commit — needs Jeffrey (no shell on the device side).
- Phase 3 (release) and Phase 4 (adopt on SHQL stack).

Next:
- Jeffrey: run the tunnel test from the phone (gate -> phrase "velvet rope test one"
  -> green dummy page), then git add -A && git commit.

## 2026-09-21 — Session 3b (tunnel test PASSED on the Mac)

- Tunnel URL served the gate to the open internet (verified from the Linux VM:
  gate page loaded through the trycloudflare URL).
- Jeffrey on his phone: wrong phrase -> "not on the list." (deny path confirmed first,
  phrase unspent), then "velvet rope test one" -> 302 -> green dummy page.
- First grant attempt 404'd ("nothing here.") — the macOS /tmp symlink bug, fixed
  and re-verified (see Session 3). After restarting bouncer, the grant worked.
- One-door serve mode verified live end-to-end: single tunnel, single port,
  bouncer is the only server. The wristband works. 🟢
- Audit confirmation: the GRANT line carried the phone's real public IPv6 via
  CF-Connecting-IP (not 127.0.0.1, not the tunnel daemon) — the IP binding is
  real, not theater. The critical gotcha from DESIGN.md holds up live.

## 2026-09-21 — Session 4 (attempt logger)

- Jeffrey: "we need an attempt logger" — first said not mid-test, then "can do now."
- Built: `--attempt-log` / `ATTEMPT_LOG` — one JSON line per knock on the gate:
  ts, ip, result (denied/granted/ratelimited), label, user-agent. Metadata only,
  never the attempted phrase (wrong guesses are often typos of real phrases).
- Logging never breaks the gate: write failures are swallowed (OSError -> pass).
- Enabled in the Mac's live bouncer.conf (`ATTEMPT_LOG = ./attempts.log`, gitignored
  via `*.log`). Needs a bouncer restart to take effect.
- Tested on the VM with the exact Mac file: denied/granted/ratelimited all logged,
  all lines valid JSON, no phrase text in the file.
- Docs: DESIGN.md (v2 scope), TODO.md (Phase 1.5 + Future ideas retired), runlines.md.

## 2026-09-21 — Session 5 (AI setup directions)

- Jeffrey's idea: since users will have AI do their setup anyway, be the first
  project to ship AI setup directions. Built:
- `docs/AI-Setup-Directions.md` — written directly to the AI doing the setup:
  step-by-step, MAY-change vs NEVER-change (each never with the attack it
  would enable), a 6-point verification checklist, and how to handle a human
  asking for something on the never list (explain the attack, offer the safe
  alternative).
- Banner comments in `bouncer.py` at every zone: `# ── SETUP: SAFE TO CHANGE ──`,
  `# ── CORE: DO NOT TOUCH ──` (client_ip, grant ceremony, traversal guard,
  constants), plus a top-of-file pointer to the doc.
- Verified on the VM with the exact Mac file: compiles, gate/grants/traversal
  all behave.
