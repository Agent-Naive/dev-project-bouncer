# THE BOUNCER — AI setup directions

*Yes, this file is for you — the AI helping a human set up Bouncer. Read it
before you touch anything. The human will thank you; the bouncer will not
notice you, which is the point.*

## What this is

Bouncer is a passphrase gate that sits in front of a tunnel-exposed app.
One file (`bouncer.py`), stdlib only, configured by `bouncer.conf`.

The night runs in **three beats**:

1. **the line** — strangers get the branded gate page (`/`): the club name
   on the awning, the rope, the red carpet, a passphrase form.
2. **the doors** — a good phrase 302s to `/enter`: "you're on the list,
   {label}", the doors swing open, a "step inside" button.
3. **the club** — the button walks the VIP to `/`: the operator's app
   (served folder, or proxied backend).

The code carries banner comments marking every zone:

- `# ── SETUP: SAFE TO CHANGE ──` — customize freely.
- `# ── CORE: DO NOT TOUCH ──` — the lock mechanism. Read the reason, then
  leave it alone.
- `# ── AI / HUMAN SETUP ──` — at the top of `bouncer.py`, points here.

## Three writers, one contract

`bouncer.conf` is the contract. Three writers produce it — they must all
speak the **same schema, in the same order** (mode → target → port/bind/TTL →
club name → logo → accent → VIP list → logs → burned list). If you add a
field, it belongs in all three:

1. **You (the AI)** — write `bouncer.conf` + `viplist.txt` directly, following
   the steps below. You are the wizard when the human asks you to "just set
   it up." Validate after writing: read the file back, confirm exactly one
   mode is set, and run the verification checklist.
2. **Club Management** — `python3 bouncer.py --manage` opens a local-only web
   form (127.0.0.1, never tunneled) that writes the same files. First run:
   blank. Later runs: pre-filled from the current config, phrases masked
   with regenerate checkboxes.
3. **Terminal human** — `cp bouncer.conf.example bouncer.conf`, hand-edit.

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
   token; the rest of the line is the phrase (spaces allowed). A positive
   integer right after the label is that VIP's own grant lifetime in
   seconds — `frank 28800 orchid thunder pancake seven` gets 8 hours
   instead of the house TTL. Example: `alice   orchid thunder pancake
   seven` — the visitor types only the phrase, never the label.
   **Generate phrases, don't invent them** — use the `gen_phrase()` word
   list in `bouncer.py` (five random words). Human brains pick guessable
   phrases; the word list doesn't. Spent one-shot phrases are recorded
   in `burned.txt` (gitignored); only a fresh phrase re-arms a label.
4. Brand the marquee (the operator's slots over the house scene):
   - `CLUB_NAME` — the name on the awning and over the doors.
   - `CLUB_LOGO` — inline `<svg...>` or a path to a `.svg` file. Blank = the
     house art carries it alone.
   - `ACCENT` — `#rgb` or `#rrggbb`; the rope, the buttons. Bad values fall
     back to velvet-rope gold.
   - Specs live in `docs/BRANDING.md` — sizes, placement, what not to do.
5. `python3 bouncer.py`.
6. Tunnel it: `cloudflared tunnel --url http://localhost:8787 --protocol http2`
   — pointing at **bouncer**, the only tunnel. Never tunnel `--manage`.

## What you MAY change

- `GATE_HTML` in `bouncer.py` — the gate page's look and words. Keep `__MSG__`
  (error text goes there) and the `<form method="post">` with the input
  named `phrase`. Never render a target path, a phrase, or any config value
  on this page — strangers read it.
- `DOORS_HTML` — the doors page. Keep `__LABEL__` (the greeting) and the
  "step inside" button pointing at `/`. The button MUST stay on this origin:
  a link anywhere else is a back door with no bouncer on it.
- `SCENE_SVG` — the house art (rope, posts, carpet). Ours to design; the
  operator's logo goes in `__LOGO__`, never here.
- Marquee slots — `CLUB_NAME`, `CLUB_LOGO`, `ACCENT` in `bouncer.conf`.
  Names and labels are HTML-escaped at render; the logo is inlined as-is
  (it's the operator's own file — still, no `<script>` in it, ever).
- `bouncer.conf` values — port, bind, TTL, paths. This is the setup sheet;
  prefer it over editing code defaults.
- The VIP list — labels and phrases. Generate phrases with `gen_phrase()`;
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
  don't skip the burn. A good phrase opens the doors (`/enter`), not the app
  directly — the VIP walks through "step inside" themselves.
- `/enter` gating — the doors page is served only with a live grant; no
  grant, no doors, back to the gate. Don't "simplify" this into an
  ungated welcome page.
- The `serve_file()` traversal guard — `realpath` on both sides, prefix
  check. Weaken it and `/%2e%2e/` walks out of the served folder.
- The attempt logger's metadata-only rule — never write the attempted phrase.
  Wrong guesses are usually typos of real phrases; that log would be a
  phrase-recovery cheat sheet on disk.
- Club Management's localhost bind — `--manage` forces 127.0.0.1. Don't add
  a `--bind` escape hatch to it, don't tunnel it, don't expose it. A
  config-writing endpoint on the public internet is game over.
- `PBKDF2_ITERATIONS`, `MAX_ATTEMPTS` — don't lower the work factor or raise
  the guess budget.

## Verify before you declare victory

1. Stranger (no cookie): gets the gate, club name on the awning, and the HTML
   contains no target path, no phrase, no config.
2. Wrong phrase: stays on the gate, `DENIED` in the audit log.
3. Right phrase: 302 to `/enter` (not `/`), doors page greets the VIP **by
   label**, `GRANT` with the visitor's real IP (via the tunnel it must NOT
   be 127.0.0.1).
4. `/enter` with no cookie: the gate, not the doors.
5. "Step inside" lands on the app. Same cookie from a different IP: gate,
   and the grant is burned (`KILL_IP`).
6. Serve mode: `/%2e%2e/` → 404, missing file → 404.
7. Config mistakes (both/neither mode, missing VIP list): clean error, exit,
   nothing listens.
8. Club Management: form pre-fills from the current config; saving writes
   `bouncer.conf` + `viplist.txt`; new phrases are shown once; a bad accent
   falls back to gold; a hostile club name (`<b>evil</b>`) renders escaped.

## If the human asks for something on the NEVER list

Don't just refuse — explain the attack it enables in one sentence, then
offer the safe alternative. Example: "IP-less sessions would let anyone who
copies the cookie walk in — the wristband is the IP binding. If the IP
flapping is the problem, the knob is TTL, not the binding."

You're the bouncer's bouncer now. Act like it. 🌀
