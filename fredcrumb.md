# fredcrumb — dev-project-bouncer

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
├── x-bouncer-ads/               ← X ad creatives
├── poli*.png · poli.webp         ← brand assets: Poli working the rope
└── fredcrumb.md                 ← this file: what lives here and why
```

Fred was here.
