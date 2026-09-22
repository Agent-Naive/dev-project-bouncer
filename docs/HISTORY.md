# THE BOUNCER — the story so far

*A living history. Everything here happened on 2026-09-21, start to finish —
the spiral, the gate, the burns, and finally Poli. Written so the future
story (and future builds) have somewhere to stand.*

## The problem: the jump gate

Jeffrey's projects live behind Cloudflare tunnels — a public URL pointing at
something on his Mac. The SHQL stack needed to be reachable by other people
with no downloads, but wide open wasn't an option. The answer was a pattern,
not just a program: **the jump gate** — one URL that serves a passphrase page
until you've proven you're on the list, and nothing else. Like a stargate
with a bouncer standing in front of it: you don't get through the ring
unless he knows your name.

## The brand: 🌀 gets its first job

THE BOUNCER — "Put a bouncer on your tunnel." (retitled from BOUNCER the
same day Poli arrived — the cast needed its proper name). The whole thing runs on a
nightclub metaphor: the **guest list** (viplist), the **wristband** (a signed,
IP-bound, TTL'd session cookie), the **velvet rope** (the gate page), **last
call** (expiry). And the mark: 🌀, the cyclone — the swirl of the jump gate
itself. That emoji's first-ever use was right here, in the runline, as this
project's sigil. It would be a while before anyone realized where the
spiral was really headed.

## Session 1 — scaffold

Jeffrey creates `/Users/agent-naive/dev-project-bouncer`. Docs, brand,
design, tags, runlines, handoff log. The mascot is planned from day one —
the brief, verbatim: *"cartoony bouncer, 🌀 on t-shirt."* The spiral already
has a body waiting for it; nobody knows that yet.

## Session 2 — v1: the gate opens (for the right people)

Built on the Linux VM, shipped to the Mac: a stdlib-only Python gate.
Per-guest passphrases bound to first-use IP — read from the
`CF-Connecting-IP` header, not the socket peer, because behind a tunnel the
peer is just the tunnel daemon (the gotcha that would have broken
everything). Signed HttpOnly cookies, an audit log of grants, one-shot
phrases. A full T1–T7 test battery, and testing caught a real bug: the first
cut verified the cookie HMAC against the *request* IP, which made the
KILL_IP and EXPIRED branches unreachable. Fixed by verifying against the
grant's bound values first, then comparing IPs.

## Session 3 — the one-door insight (Jeffrey's)

The architectural moment: **the gate only works if it's the only public
door.** A second tunnel pointed at the backend walks right around the
bouncer — crawlers would find it. So the local script itself became the
thing that allows or denies: *serve mode*. One port, one tunnel, nothing
else listening. The bouncer doesn't guard the app's door — he *is* the door.

## Sessions 4–7 — the back office and the quiet logger

Club Management: a local-only web form for running the club (phrases,
TTLs, config) — with a hard rule that it binds 127.0.0.1 and must NEVER be
tunneled. A config-writing endpoint on the public internet is game over.

Then the attempt logger Jeffrey asked for: one JSON line per knock on the
gate — timestamp, IP, result, label, user agent. Metadata only, **never the
attempted phrase text**, because wrong guesses are usually typos of real
phrases and storing them would build a phrase-typo oracle on disk.

## Session 8 — burns that survive a restart

Three upgrades, in Jeffrey's chosen order: (1) a persistent **burned list**
— EXPIRED and KILL_IP burns are appended to `burned.txt`, so a restart
can't silently re-arm a dead phrase (restarting still wipes *live* grants —
that's the kill switch); (2) **per-VIP TTL** on the viplist line
(`label ttl phrase`), so a contractor gets 8 hours and a friend gets a week;
(3) the doors page announces the wristband: *"this wristband is good for 8
hours — last call 6:04 PM."* The TTL was never the phrase's lifetime — the
phrase is one-shot. The TTL is the wristband's.

## Session 9 — Poli arrives, and the spiral comes home

The 🌀 needed a body, and it got one: **Poli**. An original cartoon bouncer
— explicitly not a Pokémon, and not "Paulie." Hugely fat belly, shirt barely
fitting with one button holding the line, the spiral stretched into an oval
across the gut, bushy eyebrows, gold jewelry, a stogie, a clipboard. Funny,
rough, street-tough. Named as a nod to Poliwhirl's spiral belly — the
project's mark, finally worn the way it was always meant to be. Jeffrey
was on the floor laughing.

Placement was a real decision: Poli does **not** stand at the gate. The gate
stays a clean knock — no distractions. Poli lives on the **doors page**
(`/enter`): he recognizes the VIP by name, unclips the rope, and presents
the wristband. Served as a public asset (`/poli.webp` — a cartoon, not a
secret), with a graceful 404 ("poli is off duty") if the file ever goes
missing. The doors still open.

## Session 10 — burn at mint, and the owner walks in

Jeffrey closed the burn-semantics question with logic, not preference:
trycloudflare pipes are ephemeral by design, and coders restart their
servers constantly — so a burn that only fires when a wristband comes back
to the door leaves every tester's phrase quietly re-arming all day. The
fix: **burn at mint**. The phrase dies the moment it mints a grant — durably,
in `burned.txt`, on the first good knock. The wristband stays valid for its
TTL; a restart can't re-arm the phrase. The burn list finally keeps the
one-shot promise it always advertised.

And because the operator would otherwise burn a phrase every time he tested
his own gate: **the owner's pass**. `ADMIN_PHRASE` (bouncer.conf, `--admin-
phrase`, or Club Management) mints grants that never burn — knock as often
as you like, across restarts. The wristband still fades at TTL and stays
IP-bound; only the phrase is immortal. It's recognition, not a bypass: Poli
sees the face, unclips the rope himself — *"good evening, boss."* The doors
page greets the operator by his true title.

Fail-closed around the master key: the gate refuses to start if
`ADMIN_PHRASE` matches a VIP phrase, and `operator` is a reserved label.
Club Management gets an "owner" section — masked, never shown, blank keeps
the current one.

## Session 11 — the public release, and Poli goes to work

The Bouncer went public under MIT: `github.com/Agent-Naive/dev-project-bouncer`.
v4 shipped with Poli, burn-at-mint, and the owner's pass — the whole arc from
a single day's work, start to finish.

Small refinements after the release, Jeffrey's eye: the boss's doors page was
still showing wristband talk ("this wristband is good for 1 day") — the owner
doesn't get a wristband, he gets recognized. One line blanks it for the
operator (the grant underneath stays a real TTL/IP-bound session), plus a CSS
rule so no gap renders. The README gained "Who it's for" — trycloudflare,
ngrok, Railway/Render/Fly, raw VPS, demos and webhooks — with the honest
limits stated plainly: shared passphrase, not identity; never trying to be
something it's not.

Then Poli got his first job outside the doors: **X promo cards**. Four
1200x675 landscape cards (X's native size — no feed cropping), each a
composite of the original Poli art — never regenerated, so zero drift — with
a comic speech bubble ("Name on the list?", "No phrase, no entry.", "Hold it.
Phrase first.", "The rope stays up."), THE BOUNCER in gold, a cyan spiral
echoing his belly, and the GitHub URL as a credit strip. Built for Jeffrey's
reply-guy campaign: "Try this…" on trycloudflare complaint threads. The
cards stay local (gitignored, `poli-x-*.png`); the original webp was never
touched. Build script kept at `~/workspace/poli-promo/build_cards.py` for
future variants.

## Open threads — to be continued

- **Cloudflare end-to-end**: the `CF-Connecting-IP` binding, proven live
  through a real tunnel. Local-first, then tunnel — the standing order.
- **Poli's future**: promo cards shipped; the gate and the denied page still
  waiting. The spiral has range.
- **The SHQL stack**: the jump gate guarding the thing it was built for —
  Jeffrey will put the Bouncer on his own stack next.

*Free and open-source. Jeffrey will put it on his own SHQL stack after the
public release — the jump gate guarding the thing it was built for.*
