# fredcrumb — dev-project-bouncer

**SHQL (ShorthandQL)** — the command language and agent ruleset for this project.
- If the task involves SHQL: read the ACTIVE binder first — `shql-binder-v1.3b/SHQL-v1.3b.md`. The binder is the authority, not memory or these notes.
- Per-command how-tos live in `shql-binder-v1.3b/help-files/`.
- Binders are versioned directories; the ACTIVE one is named in the tree below. Upgrades add a new versioned dir — never edit a binder in place.

The Bouncer (Poli): a tiny open-source passphrase gate. No phrase, no entry —
wrong answers get the rickroll. Viplist names get past the rope.

```
dev-project-bouncer/
├── bouncer.py                   ← the gate: passphrase check + attempt logging
├── bouncer.conf                 ← live config (bouncer.conf.example = template)
├── viplist.txt                  ← the VIP list (viplist.txt.bak = safety copy)
├── rickroll.html                ← the trap: Never Gonna Give You Up
├── attempts.log                 ← attempt log (attempts-dropwire.log = dropwire flavor)
├── CT-issuance-rate-counter.py  ← cert-transparency issuance counter
├── CT-polling-utility-script.sh ← CT log polling helper
├── runlines.md                  ← runlines
├── HANDOFF-LOG.md               ← session continuity
├── README.md                    ← project readme
├── LICENSE                      ← MIT
├── docs/                        ← docs
├── x-bouncer-ads/               ← X ad creatives (2026-09-22): 4 Poli promo PNGs + ad copy in .md and .pdf (same content)
├── poli*.png · poli.webp         ← brand assets: Poli working the rope
├── shql-binder-v1.3b/          ← ACTIVE SHQL binder (v1.3b). Versioned dirs: upgrades add new, never edit in place.
└── fredcrumb.md                 ← this file: what lives here and why
```

Fred was here.
