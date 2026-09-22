# THE BOUNCER — branding guide

*How to hang your sign on our club.*

The Bouncer's brand works in **two layers**. The house layer is ours — the club
facade, the velvet rope, the red carpet, the doors. It ships in the box and
looks complete with zero customization. The marquee layer is yours — named
slots where your club's identity goes up in lights. This doc is the slot
list: what each one is, where it renders, and the specs.

## The slots

| Slot | Config key | Where it appears | Format |
|---|---|---|---|
| Club name | `CLUB_NAME` | Awning on the gate page, over the doors, both page titles | Plain text, escaped |
| Logo | `CLUB_LOGO` | Above the scene (gate), under the greeting (doors) | Inline `<svg...>` or path to a `.svg` file |
| Accent | `ACCENT` | The rope, the awning border, buttons, the VIP's name | `#rgb` or `#rrggbb` |

All three are set in `bouncer.conf`, by hand, by Club Management
(`python3 bouncer.py --manage`), or by your AI following
`docs/AI-Setup-Directions.md` — same schema, three writers.

## Specs

**Club name** — keep it short; it renders in a letterspaced uppercase awning.
Anything HTML-ish is escaped (`<b>evil</b>` shows up as text, not markup).
If empty, the house default ("The Bouncer") is used.

**Logo** — SVG only, static art, no `<script>` (it gets inlined into the
page as-is). Two ways to supply it:
- Paste the SVG markup directly as the `CLUB_LOGO` value — **one line**.
  `bouncer.conf` is line-oriented, so a multi-line paste would break
  parsing. (Club Management collapses pasted SVG to one line for you
  automatically.)
- Point at a file: `CLUB_LOGO = ./logo.svg` (read at startup; anything that
  isn't an SVG, or any read failure, means no logo — the house art carries it).
  For anything beyond a tiny mark, the file path is the calmer choice.

Display size: max ~14rem wide on the gate, ~12rem on the doors; it scales
down, never up. Transparent background works best — the house is near-black
(`#0d0d0f`). Don't put your club name *in* the logo image; the name already
has its own slot right next to it.

**Accent** — any `#rgb` / `#rrggbb`. It draws the rope, the awning border,
the buttons, and the VIP's name on the doors page. Anything else falls back
to velvet-rope gold (`#c9a227`).

## What not to do

- Don't cover the rope. The house scene (rope, posts, carpet, doors) is
  the Bouncer's signature — your logo hangs *above* it, never over it.
- Don't restyle the gate form into something unrecognizable *unless* you keep
  the contract: the error slot, the `<form method="post">`, the input named
  `phrase`. Strangers must always understand what the page wants.
- Don't point the doors page "step inside" button anywhere but `/`. Off-origin
  is a back door with no bouncer on it.

## The mascot

Poli — the cartoony bouncer with the 🌀 stretched across his t-shirt —
stands on the doors page (`/enter`), not at the gate. Marquee slots don't
change; he just has better company now.
