# THE BOUNCER — handoff log

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
- Jeffrey: run the tunnel test from the phone (gate -> joe's test phrase
  -> green dummy page), then git add -A && git commit.

## 2026-09-21 — Session 3b (tunnel test PASSED on the Mac)

- Tunnel URL served the gate to the open internet (verified from the Linux VM:
  gate page loaded through the trycloudflare URL).
- Jeffrey on his phone: wrong phrase -> "not on the list." (deny path confirmed first,
  phrase unspent), then joe's test phrase -> 302 -> green dummy page.
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

## 2026-09-21 — Session 6 (the night: branding + Club Management)

- Jeffrey, DADO first: "don't lose the branding opportunity by missing the
  doors opening for the VIP to enter." Then: brand the first page too
  ("welcome to Club <project>"), users layer their own sub-branding over the
  house scene with a spec doc. Then: "maybe we write a local web interface
  admin page... it then saves the file as the config... re-runs would
  overwrite the old config... doable?" Then: "the AI could just do it behind
  the scenes." Then: "maybe call it Run Club Management or something lol
  instead of wizard." Then: "do it all :)" — DADO lifted, full build.
- Built in `bouncer.py` (1175 lines, stdlib only):
  - **Three beats**: the line (branded gate `/`) -> the doors (`/enter`:
    "you're on the list, {label}", CSS doors swing open, "step inside"
    button -> `/`) -> the club (app). Grant 302s to `/enter` (was `/`).
  - **Marquee slots**: `CLUB_NAME` / `CLUB_LOGO` (inline SVG or .svg path) /
    `ACCENT` in bouncer.conf + CLI flags. Name/label HTML-escaped, bad accent
    falls back to velvet-rope gold, logo failures -> house art carries it.
  - **House scene**: inline `SCENE_SVG` (rope, posts, red carpet). Mascot later.
  - **Club Management** (`--manage`): local-only (127.0.0.1 forced) web form —
    pre-fills from current config, phrases masked with regenerate checkboxes,
    `gen_phrase()` 5-word generator, writes `bouncer.conf` (unknown keys and
    comments preserved) + `viplist.txt`, new/changed phrases shown once.
    Never tunnel it — says so on the page.
  - **Three writers, one contract**: AI (AI-Setup-Directions.md), Club
    Management, terminal — same schema, same order.
- Docs: `bouncer.conf.example` (marquee section), `docs/BRANDING.md` (new —
  slot list, sizes, formats), `docs/AI-Setup-Directions.md` (three beats,
  three writers, /enter verification, never-tunnel-manage rule),
  `runlines.md` (manage runline), `README.md`, `docs/TODO.md` (Phase 2.5).
- Tested on the Linux VM with the exact files: branded gate render, denied/
  granted, 302 -> /enter, doors greets by label, /enter without grant -> gate,
  step-inside -> app, KILL_IP, one-shot burn, 429, traversal 404, proxy clean,
  manage save + prefill + phrase gen, XSS escaped, accent fallback, logo file
  inlined, manage-written config runs the gate.
- Test notes: pkill -f can match your own shell's command line when the
  pattern appears later in it — `fuser -k PORT/tcp` is bulletproof.
- Shipped to the Mac: bouncer.py + all docs above. Mac needs a bouncer
  restart to pick it up (grants wipe — the kill switch — and one-shot
  phrases become usable again).
- Ship note: bouncer.py went over in 5 chunks (A–E) through the paired-device
  file API, each chunk pulled back and diffed byte-for-byte against the
  VM-tested build before the next went. The diff caught three transcription
  slips (a literal `\U0001f300` written as the emoji, one indent slip, one
  trailing newline) — all fixed. Final Mac bouncer.py is byte-identical
  (55,083 bytes, 1175 lines) to the tested build. Jeffrey to verify:
  `cd /Users/agent-naive/dev-project-bouncer && python3 -m py_compile bouncer.py`.

## 2026-09-21 — Session 7 (release fixes)

Code review before release found three real bugs; all fixed, re-tested on
the VM (22-check battery, all passing), and shipped to the Mac as targeted
edits — Mac bouncer.py is byte-identical (55,900 bytes, 1188 lines) to the
fixed, tested build:
- **Mode switch left a stale key.** Saving in serve mode kept the old
  `TARGET` line (and vice versa), so the gate fail-closed on restart with
  "pick ONE mode". Club Management now writes every managed key on each
  save; the unchosen mode's key goes blank, and a blank attempt-log field
  means off (a stale path can't re-enable logging).
- **Multi-line pasted logo broke the conf file.** `bouncer.conf` is
  line-oriented; a multi-line SVG paste would kill parsing. The save handler
  now collapses the logo field to one line (SVG doesn't care), and the docs
  say: inline SVG must be one line, or use a `.svg` path.
  (`docs/BRANDING.md`, `bouncer.conf.example` updated.)
- **Authed VIPs couldn't POST to their own app.** Any POST — even with a
  live grant — ran the knock ceremony: denied, rate-limited, logged as a
  knock. Now an authed POST goes behind the rope to the app; only strangers
  knock. (PUT/PATCH/DELETE already forwarded; verified with bodies.)
- Also verified: phrase preserve vs regenerate vs custom on save, duplicate
  labels -> 400, comments and unknown config keys survive a Management save,
  shown-once page lists only new/changed phrases.
- `runlines.md`: commit message updated to the v3 release line; Tested
  section notes the fix battery.

Still needs Jeffrey: `python3 -m py_compile bouncer.py`, then the git
ignore/status checks, then commit. Restarting the gate wipes grants (kill
switch) — one-shot phrases become usable again.

## 2026-09-21 — Session 8 (durable burns, per-VIP TTL, wristband announcement)

- Jeffrey, after the DADO on burn mechanics: "go on all three in that order" —
  (1) persistent burned list, (2) per-VIP TTL on the viplist line, (3) grant-time
  announcement on /enter. Built and tested on the Linux VM, shipped as chunks.
- Feature 1 — **burned.txt (the forbidden list)**. The `st.burned` set was
  in-memory only: a restart silently re-armed dead phrases. Now every burn
  (EXPIRED, KILL_IP) is appended to `burned.txt` via `persist_burn()`, loaded at
  startup with `load_burned()`. New `--burned` flag / `BURNED` config key (a
  managed key, written every Club Management save — a path, never blanked).
  Gitignored; `burned.example.txt` tracked. Club Management shows the burned-out
  labels and the burned-file path. **Re-issue rule: a fresh phrase is the only
  way back in** — regenerating (or hand-setting a new phrase) for a burned label
  drops it from burned.txt via `unburn_labels()` on save. Never automatic.
- Feature 2 — **per-VIP TTL**. viplist lines are now `label phrase` (house TTL)
  or `label ttl phrase` (that VIP's own grant lifetime, seconds). One parser
  (`split_viplist_line`) serves the gate and Club Management; a positive integer
  right after the label is always a TTL, so a phrase beginning with a number
  needs an explicit TTL in front of it (documented — generated phrases never
  start with digits, so Club Management output is unambiguous). load_viplist
  fail-closes on malformed lines. Club Management: per-row TTL field
  (blank = house TTL, and blanking drops an explicit TTL — "blank means house
  rules"); untouched rows keep phrase AND TTL; invalid row TTL -> 400. Confirm
  page shows each new phrase with its wristband length ("2 hours" / "house
  grant lifetime").
- Feature 3 — **/enter announces the grant**. The doors page now renders
  "this wristband is good for 8 hours — last call 6:04 PM." under the greeting,
  from the grant's stored TTL and expiry (server-local time).
- Design note: the TTL was never the phrase's lifetime — the phrase dies on
  first use regardless. The TTL is the *wristband's* lifetime. Per-VIP TTL makes
  that visible and tunable per guest (contractor: 8 hours; friend: a week).
- Tested on the Linux VM, 23/23 + 11/11:
  - per-VIP TTL honored at grant time (cookie expiry delta 5s / 7200s / 86400s);
    2-token lines used the house TTL; old-format lines with multi-word phrases
    still parse.
  - EXPIRED burn persisted to burned.txt; after restart the burned phrase was
    denied ("not on the list") while the live label still knocked clean.
  - KILL_IP burn persisted; denied after restart.
  - Club Management: negative/non-numeric row TTL -> 400; regen + TTL 7200 saved
    `vipA 7200 <phrase>`, confirm showed "2 hours", burned.txt dropped vipA;
    after gate restart the new phrase granted with a 7200s wristband and /enter
    announced "good for 2 hours"; the old phrase stayed dead.
  - Prefill showed per-row TTLs and the burned-out list; unchanged save preserved
    explicit TTLs, comments, and unknown config keys; BURNED written; duplicate
    labels still 400.
- Shipped to the Mac: bouncer.py chunks (byte-identical) + burned.example.txt +
  PATCHES.md (7 small doc/config edits). Mac needs: apply patches, concatenate
  chunks -> bouncer.py, `python3 -m py_compile bouncer.py`, restart the gate to
  pick it up (grants wipe — the kill switch; burned phrases stay burned).

## 2026-09-21 — Session 9 (Poli on the doors)

- **Poli, the mascot.** Original cartoon bouncer, explicitly not a Pokemon:
  hugely fat belly, shirt barely fits with one button holding the line, spiral
  stretched across the belly, bushy eyebrows, gold jewelry, stogie, clipboard —
  funny, rough, street-tough. Named Poli as a nod to Poliwhirl's spiral belly
  (Jeffrey: not "Paulie").
- **Placement: the doors page /enter, not the gate.** Gate stays a clean
  knock; on /enter Poli greets the VIP by name, unclips the rope, and presents
  the wristband. Future spots later — v1 lives at the doors.
- Technical: public `/poli.webp` asset route (no grant needed — a cartoon, not
  a secret) + `serve_poli()` reading a fixed filename alongside bouncer.py
  (missing file -> 404 "poli is off duty", never a crash); `.poli` CSS;
  `<img class="poli">` on DOORS_HTML. The gate page carries no Poli reference.
- Art: Jeffrey placed the original full-size sketch as `poli.webp` (673,026
  bytes, 1280x1920). The doors-page CSS caps it at 12rem high / 75% wide, so
  it renders the same as the planned optimized version — just served heavier
  (cached 1h by the asset route).
- Mac: the 4 code edits are applied this session (mirrored from the tested VM
  build); `poli.webp` is in place. Still needed: `python3 -m py_compile
  bouncer.py`, one restart, one knock, visual confirm of Poli on /enter.

## 2026-09-21 — Session 10 (retitled: The Bouncer)

- Jeffrey: "should this project actually be titled and known as The
  Bouncer?" Yes — it joins The Judge in the cast of characters, and with
  Poli as the face the project reads as one persona, not a utility.
- Changed: display title across README, all docs, `bouncer.conf.example`,
  and the `--help` description; default marquee `DEFAULT_CLUB_NAME =
  "The Bouncer"` (the live gate's awning picks it up on next restart —
  `bouncer.conf` doesn't set CLUB_NAME). Unchanged: folder name, 🌀,
  tagline ("Put a bouncer on your tunnel"), `server_version` tokens.

## 2026-09-21 — Session 11 (burn at mint + the owner's pass)

- Jeffrey closed the burn-semantics question with logic, not preference:
  trycloudflare pipes are ephemeral by design and coders restart servers
  constantly — so burns that only fired when a wristband came back to the
  door left every tester's phrase quietly re-arming all day. The fix:
  **burn at mint**. The phrase dies the moment it mints a grant — durably,
  in burned.txt, on the first good knock. Wristband stays valid for its TTL;
  a restart can't re-arm the phrase. The burn list finally keeps the
  one-shot promise it always advertised.
- **The owner's pass**: `ADMIN_PHRASE` (bouncer.conf / `--admin-phrase` / Club
  Management "owner" section) mints grants that never burn — knock as often
  as you like, across restarts. The wristband still fades at TTL and stays
  IP-bound; only the phrase is immortal. Recognition, not a bypass: the
  doors page greets the operator "good evening, boss — no knock needed,
  Poli knows the face." Fail-closed: gate refuses to start if ADMIN_PHRASE
  matches a VIP phrase; `operator` is a reserved label.
- Tested on the Linux VM (burn-at-mint, restart survival, admin re-knock,
  expiry idempotency, both fail-closed guards, blank-admin start, VIP
  greeting intact), mirrored to the Mac as targeted edits.
- Mac still needs: `python3 -m py_compile bouncer.py`, one restart, set
  ADMIN_PHRASE (Club Management or bouncer.conf), one knock to see Poli
  tip his hat.
- Verified on the Mac, same night: clean compile; gate restarted
  (127.0.0.1:8787, serve mode, 2 VIPs); ADMIN_PHRASE set via Club
  Management; owner knock -> 302; /enter greets "good evening, boss";
  second knock -> 302 again; burned.txt never created — zero burns, both
  shipped VIPs untouched. The owner's pass is human-verified.
- Release hygiene: `*.bak` added to .gitignore (a `viplist.txt.bak` would
  otherwise NOT be ignored); `viplist.txt.bak` created as a local backup.
  `viplist.example.txt` already ships 2 starters — enough.
- Committed: `da9115e` "bouncer v4: Poli, burn-at-mint, owner's pass"
  (16 files, secrets all correctly unstaged). Repo is local-only, no
  remotes — GitHub push is a future release step.
- Released: MIT LICENSE added (`d64d06a`); history verified clean (no
  secret ever committed); pushed public via `gh repo create` as
  **Agent-Naive/dev-project-bouncer** — https://github.com/Agent-Naive/dev-project-bouncer
  Phase 3 (public release) is done.
- Follow-up, same night: Jeffrey noticed the boss's doors page still showed
  "this wristband is good for 1 day" — the boss shouldn't get wristband
  talk. `serve_doors` now blanks the wristband line for the operator
  (one line; the grant underneath stays a real TTL/IP-bound session) plus
  `.wristband:empty{display:none}` so no gap renders. Verified live.
- README gained "Who it's for" (trycloudflare, ngrok, Railway/Render/Fly,
  raw VPS, demos/webhooks — with the honest limits: shared passphrase, not
  identity; not a replacement for real auth). runlines.md gained compile
  check, restart, Mac knock test, burn-state check, viplist backup, and the
  public GitHub section.
- Poli X promo cards: four 1200x675 cards (composited from the original art,
  zero drift, zero halos), four catchphrase variants for rotating across
  replies. Gitignored as poli-x-*.png; original webp untouched; build script
  kept at ~/workspace/poli-promo/build_cards.py. For the "Try this..." reply
  campaign on trycloudflare complaint threads.
- Jump Gate, the tip agent: the gate page now carries the spiral (2.5rem, shirt-print
  scale) with a chat bubble across the bottom explaining in plain terms what The
  Bouncer is and why it exists. All tips live in GATE_TIPS (3 written, tip 1 active);
  swap on demand with ACTIVE_TIP. Named Jump Gate — the original name coming home.
- Option 3 built (demo funnel): static "free and open-source" GitHub footer on both
  the gate and doors pages; Jump Gate tip #4 with a copy-paste curl one-liner
  (raw.githubusercontent download — never a curl-pipe-to-shell). Tips are now
  (text, html) tuples: plain text escaped, html trusted house-only so tip 4 can
  carry a <code> block (one-click select). ACTIVE_TIP stays 0.
- Invisible hit counter: every gate impression logs result="visit" in the attempt
  log (same file, same metadata-only rule) — poor-man's traffic stats, hidden
  from the visitor. No new flags; works with the existing ATTEMPT_LOG.
