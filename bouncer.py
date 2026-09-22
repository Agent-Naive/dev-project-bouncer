#!/usr/bin/env python3
"""
BOUNCER 🌀 — put a bouncer on your tunnel.

A tiny passphrase gate: one URL serves a passphrase page to strangers and
your app to VIPs on the list. Per-VIP phrases are one-shot: the first good
knock burns the phrase (durably — a restart can't re-arm it) and binds the
grant to the VIP's IP; the grant dies if the IP changes or the TTL expires.
The operator's own phrase (ADMIN_PHRASE) never burns — Poli knows the boss.
Stdlib only — no pip, no venv.

Two modes — pick ONE in bouncer.conf (comment/uncomment what you need):

  serve — bouncer IS the server. It serves a static folder to authed VIPs.
          One door, one port, one tunnel. Nothing else listens anywhere.
          Best for static apps: a single HTML file, a docs folder, ...

  proxy — bouncer forwards authed VIPs to your dynamic app. Your app must
          bind 127.0.0.1 and never get its own tunnel. One door only.

The night, in three beats:

  1. the line   — strangers get the branded gate page:
                 "welcome to Club __CLUB__", rope, red carpet.
  2. the doors  — a good phrase opens /enter: "you're on the list,
                 __LABEL__", the doors swing open, "step inside".
  3. the club   — the button walks the VIP into your app (/).

Setup (three writers, one contract — bouncer.conf):

    human:   python3 bouncer.py --manage     # Club Management, local only
    AI:      read docs/AI-Setup-Directions.md, then write bouncer.conf
             + viplist.txt directly (the AI is the wizard)
    terminal: cp bouncer.conf.example bouncer.conf   # then edit it
              cp viplist.example.txt viplist.txt     # real phrases here

    python3 bouncer.py                     # run the gate

New here — human or AI? Read docs/AI-Setup-Directions.md. It maps every
SAFE-TO-CHANGE zone and every DO-NOT-TOUCH zone in this file.

viplist.txt format (one per line, keep OUT of git — see .gitignore):

    joe     correct horse battery staple
    frank   28800 another secret phrase here

Label is the first token; the rest of the line is the phrase (spaces allowed).
A positive integer right after the label is that VIP's own grant lifetime in
seconds (frank gets 8 hours); without it, the house TTL from bouncer.conf
applies. Lines starting with # are ignored.
Burned one-shot phrases land in burned.txt (also gitignored) — the forbidden
list. Phrases burn the moment they mint a grant, so a burned label can't
knock again until you hand it a fresh phrase.
You're on the VIP list or you're not. 🌀

Security notes:
- Phrases are verified server-side against PBKDF2-HMAC-SHA256 hashes.
  Only salted hashes live in memory; the plaintext never leaves the login form.
- Session cookies are HMAC-signed with a per-start random secret and bound
  to the guest's IP. Restarting bouncer wipes all grants (the kill switch).
- Client IP is read from the CF-Connecting-IP header, which Cloudflare sets.
  All public traffic arrives via the tunnel, so this header is trustworthy.
  Without a tunnel (local testing), it falls back to the socket peer IP.
  Do NOT put bouncer directly on the open internet without a tunnel — a
  client could spoof the header.
- One door: the gate only works if it's the only public URL. In proxy mode
  never tunnel the backend directly — a second tunnel is a second door with
  no bouncer on it, and crawlers will find it.
- Club Management (--manage) binds 127.0.0.1 and writes your config files.
  NEVER tunnel it: a config-writing endpoint on the public internet is
  game over. It says so on the page, in big letters.
"""

# ── AI / HUMAN SETUP ─────────────────────────────────────────
# Setting this up? Read docs/AI-Setup-Directions.md first.
# It maps every SAFE-TO-CHANGE zone and every DO-NOT-TOUCH zone below.
# ────────────────────────────────────────────────────────────
import argparse
import base64
import hashlib
import hmac
import html
import http.client
import json
import mimetypes
import os
import secrets
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# Security constants. Don't lower PBKDF2_ITERATIONS (slower = safer),
# don't rename the cookie, don't raise MAX_ATTEMPTS. The rate limit is
# the thing standing between the gate and a guessing machine.
# ────────────────────────────────────────────────────────────
PBKDF2_ITERATIONS = 150_000
COOKIE_NAME = "__bouncer"
MAX_ATTEMPTS = 5          # max phrase attempts ...
ATTEMPT_WINDOW = 60       # ... per this many seconds, per IP

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
}

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# House brand defaults. CLUB_NAME is the marquee on the awning —
# "welcome to Club __CLUB__". Operators override these in bouncer.conf
# (or Club Management); the house scene below stays ours.
# ────────────────────────────────────────────────────────────
DEFAULT_CLUB_NAME = "The Bouncer"
DEFAULT_ACCENT = "#c9a227"  # velvet-rope gold
ADMIN_LABEL = "operator"  # reserved: the owner's pass mints under this label

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# House scene: the rope, the posts, the red carpet. Inline SVG, no files.
# This is OUR art direction — the operator's logo goes in __LOGO__,
# their name in __CLUB__. (The mascot moves in here later.)
# ────────────────────────────────────────────────────────────
SCENE_SVG = """<svg width="260" height="96" viewBox="0 0 260 96" role="img" aria-label="velvet rope">
<polygon points="104,96 156,96 176,44 84,44" fill="#7a1f1f"/>
<polygon points="104,96 156,96 150,84 110,84" fill="#8f2626"/>
<rect x="28" y="22" width="7" height="58" rx="3.5" fill="#c9a227"/>
<circle cx="31.5" cy="18" r="7" fill="#c9a227"/>
<rect x="225" y="22" width="7" height="58" rx="3.5" fill="#c9a227"/>
<circle cx="228.5" cy="18" r="7" fill="#c9a227"/>
<path d="M31,26 Q130,76 229,26" stroke="#c9a227" stroke-width="5" fill="none" stroke-linecap="round"/>
<text x="130" y="34" text-anchor="middle" font-size="24">\U0001f300</text>
</svg>"""

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# The gate page (beat 1: the line). Restyle it, reword it, make it yours —
# but keep __MSG__ (where errors print) and the <form method="post">
# with the input named "phrase". __CLUB__ / __LOGO__ / __ACCENT__ are the
# operator's marquee slots; __SCENE__ is the house art. Never print the
# target path, a phrase, or any config value here: strangers read this page.
# ────────────────────────────────────────────────────────────
GATE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__CLUB__ &mdash; the bouncer</title>
<style>
body{background:#0d0d0f;color:#e8e8ea;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.club{text-align:center;padding:2rem;max-width:28rem}
.awning{display:inline-block;border:2px solid __ACCENT__;border-radius:12px;padding:.45rem 1.4rem;letter-spacing:.28em;text-transform:uppercase;font-size:.8rem;color:__ACCENT__}
.logo svg{max-height:4rem;max-width:14rem;margin-top:1rem}
.scene{margin:1.2rem auto .4rem}
h1{font-size:1.9rem;margin:.6rem 0 .2rem}
.tag{color:#999;font-size:.95rem;margin:.2rem 0 0}
.err{color:#ff7b7b;min-height:1.4em;margin:.6rem 0}
input{background:#1a1a1e;border:1px solid #333;color:#fff;padding:.7rem 1rem;font-size:1rem;border-radius:8px;width:16rem}
button{background:__ACCENT__;color:#111;border:0;padding:.7rem 1.5rem;font-size:1rem;font-weight:700;border-radius:8px;cursor:pointer;margin-top:.8rem}
</style></head>
<body><div class="club">
<div class="awning">__CLUB__</div>
<div class="logo">__LOGO__</div>
<div class="scene">__SCENE__</div>
<h1>this tunnel has a bouncer</h1>
<p class="tag">if you're on the list, you're already in.</p>
<p class="err">__MSG__</p>
<form method="post"><input type="password" name="phrase" placeholder="passphrase" autocomplete="off" autofocus><br>
<button type="submit">let me in</button></form></div></body></html>"""

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# The doors page (beat 2: the doors). Served at /enter after a good
# phrase. The doors swing open on load; the VIP gets greeted BY NAME
# (__GREETING__ — the bouncer knows who's on the list; the operator gets
# "good evening, boss") and walks through the "step inside" button to /
# (the app). Same marquee slots as the gate. The button MUST stay on this
# origin — a link anywhere else is a back door with no bouncer on it.
# ────────────────────────────────────────────────────────────
DOORS_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>you're in &mdash; __CLUB__</title>
<style>
body{background:#0d0d0f;color:#e8e8ea;font-family:system-ui,sans-serif;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden}
.door{position:fixed;top:0;bottom:0;width:50vw;background:#17171c;z-index:1;animation:swing 1.8s ease-out forwards}
.door.l{left:0;border-right:3px solid __ACCENT__;transform-origin:left center}
.door.r{right:0;border-left:3px solid __ACCENT__;transform-origin:right center}
@keyframes swing{to{transform:scaleX(.02);opacity:0}}
.stage{position:relative;z-index:2;text-align:center;padding:2rem;max-width:28rem;animation:rise .8s ease-out .9s both}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.spiral{font-size:3rem}
.clubline{letter-spacing:.28em;text-transform:uppercase;font-size:.75rem;color:#999;margin:.6rem 0}
h1{font-size:2.1rem;margin:.4rem 0}
.vip{color:__ACCENT__}
.sub{color:#999}
.wristband{color:__ACCENT__;font-size:.95rem;margin:.6rem 0 0}
.wristband:empty{display:none}
.poli{max-height:12rem;max-width:75%;border-radius:14px;margin:.2rem auto;display:block;box-shadow:0 8px 30px rgba(0,0,0,.5)}
.logo svg{max-height:3.5rem;max-width:12rem;margin:1rem auto 0}
.enter{display:inline-block;margin-top:1.4rem;background:__ACCENT__;color:#111;font-weight:700;padding:.9rem 2.4rem;border-radius:10px;text-decoration:none;font-size:1.15rem}
</style></head>
<body>
<div class="door l"></div><div class="door r"></div>
<div class="stage">
<div class="spiral">\U0001f300</div>
<p class="clubline">__CLUB__</p>
<img class="poli" src="/poli.webp" alt="Poli, the bouncer">
<h1>__GREETING__</h1>
<p class="sub">__SUB__</p>
<p class="wristband">__WRISTBAND__</p>
<div class="logo">__LOGO__</div>
<a class="enter" href="/">step inside</a>
</div></body></html>"""

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# Word list for generated VIP phrases (Club Management + AI setup).
# Five words ≈ 35 bits; the rate limit (5/min/IP) and one-shot burns
# do the rest. Human-picked phrases are weaker than these — generate,
# don't invent.
# ────────────────────────────────────────────────────────────
WORDLIST = (
    "amber apricot atlas bacon banjo basil bayou beacon birch bison blaze "
    "bonfire boulder brass breeze bronze brook cabin cactus canyon cedar "
    "cheddar cherry chestnut cider cinnamon citrus cliff clover cobalt comet "
    "copper coral cougar coyote crater cricket crow cumin dahlia delta donut "
    "drift dune eagle ember falcon fern flint forest foxglove frost garnet "
    "glacier grove gull harp hazel heron honey indigo inlet ivory jaguar "
    "juniper kelp lagoon lark lava lemon lilac llama lunar magnet maple "
    "marble meadow mesa meteor mist mocha moss nickel nova nutmeg oasis "
    "onyx orchid otter oyster pancake papaya pebble pepper pine pistachio "
    "plaza prairie prism pumice quartz quill raven ridge river robin sage "
    "salsa sapphire sequoia shark sienna sierra smoke sparrow spruce storm "
    "summit tahoe talon tangerine teal thunder topaz tulip tundra turtle "
    "umber valley velvet vixen walnut willow xenon yarrow yucca zebra zephyr"
).split()


def gen_phrase(n=5):
    """A typable random VIP phrase: n words from the house list."""
    return " ".join(secrets.choice(WORDLIST) for _ in range(n))


def human_seconds(s):
    """'45 seconds', '8 hours', '7 days' — wristband announcements."""
    s = int(s)
    if s < 60:
        return "%d second%s" % (s, "" if s == 1 else "s")
    if s < 3600:
        m = s // 60
        return "%d minute%s" % (m, "" if m == 1 else "s")
    if s < 86400:
        h = s // 3600
        return "%d hour%s" % (h, "" if h == 1 else "s")
    d = s // 86400
    return "%d day%s" % (d, "" if d == 1 else "s")


def valid_accent(v):
    """Accept #rgb / #rrggbb, else fall back to the house gold."""
    v = (v or "").strip()
    if len(v) in (4, 7) and v.startswith("#") and all(
            c in "0123456789abcdefABCDEF" for c in v[1:]):
        return v
    return DEFAULT_ACCENT


def resolve_logo(value):
    """Operator's marquee logo: inline <svg...> or a path to a .svg file.
    Anything else (or any read failure) -> no logo; the house art carries it."""
    if not value:
        return ""
    v = value.strip()
    if v.startswith("<"):
        return v if "<svg" in v[:500].lower() else ""
    if v.lower().endswith(".svg") and os.path.isfile(v):
        try:
            with open(v, "r", encoding="utf-8") as f:
                data = f.read(65536)
        except OSError:
            return ""
        return data if data.lstrip().lower().startswith("<svg") else ""
    return ""


# ---------------------------------------------------------------- state

# ── CORE: DO NOT TOUCH ───────────────────────────────────────
# Grants are one-shot and IP-bound: the first good knock burns the phrase
# (durably, at mint time — a restart can't re-arm it) and binds the grant
# to the VIP's IP; a different IP kills the grant (KILL_IP). The operator's
# phrase (ADMIN_PHRASE, label "operator") never burns — Poli knows the boss.
# Don't "simplify" this into multi-use phrases or IP-less sessions — that's
# the whole lock.
# ────────────────────────────────────────────────────────────
class BouncerState:
    def __init__(self, args):
        # args (target/serve/ttl/viplist/audit_log) already merged from
        # bouncer.conf + CLI flags by main(). Exactly one mode is set.
        if args.target:
            self.mode = "proxy"
            self.target = urllib.parse.urlparse(args.target)
            if self.target.scheme not in ("http", "https") or not self.target.hostname:
                sys.exit("error: TARGET must be an http(s)://host[:port] URL")
            self.serve_dir = None
        else:
            self.mode = "serve"
            self.target = None
            d = os.path.realpath(args.serve)  # realpath, not abspath: e.g. macOS /tmp is a symlink
            if not os.path.isdir(d):
                sys.exit("error: SERVE_DIR must be an existing directory: %s" % args.serve)
            self.serve_dir = d
        self.ttl = args.ttl
        self.server_secret = secrets.token_bytes(32)
        self.phrases = load_viplist(args.viplist, args.ttl)  # label -> (salt, dk, ttl)
        if not self.phrases:
            sys.exit("error: no usable phrases in the VIP list (fail closed)")
        self.grants = {}    # label -> {"ip": str, "expires": int, "ttl": int}
        self.burned_path = args.burned
        self.burned = load_burned(args.burned)  # spent one-shot labels, survives restarts
        # The owner's pass: ADMIN_PHRASE mints grants that never burn.
        # Hashed like a VIP phrase but kept OUT of self.phrases, so the
        # one-shot VIP loop never sees it. Blank = no owner; every phrase
        # is one-shot.
        self.admin = None
        admin_phrase = (args.admin_phrase or "").strip()
        if admin_phrase:
            if ADMIN_LABEL in self.phrases:
                sys.exit("error: '%s' is a reserved label — rename that VIP" % ADMIN_LABEL)
            asalt = os.urandom(16)
            adk = hashlib.pbkdf2_hmac("sha256", admin_phrase.encode("utf-8"),
                                     asalt, PBKDF2_ITERATIONS)
            # The owner's face must not match a guest's phrase. Fail closed.
            for _label, (salt, dk, _ttl) in self.phrases.items():
                atest = hashlib.pbkdf2_hmac("sha256", admin_phrase.encode("utf-8"),
                                            salt, PBKDF2_ITERATIONS)
                if hmac.compare_digest(dk, atest):
                    sys.exit("error: ADMIN_PHRASE must not match a VIP phrase")
            self.admin = (asalt, adk)
        self.attempts = {}  # ip -> [timestamps]
        self.lock = threading.Lock()
        self.audit_path = args.audit_log
        self.attempt_log = args.attempt_log
        # ── SETUP: SAFE TO CHANGE ──
        # Marquee slots: the operator's branding. Escaped at render time;
        # the logo is operator-supplied SVG inlined as-is (their own file).
        self.club_name = args.club_name or DEFAULT_CLUB_NAME
        self.accent = valid_accent(args.accent)
        self.club_logo = resolve_logo(args.club_logo)

    def burn(self, label):
        """Spend a label's one-shot phrase: burned in memory now, and in
        burned.txt so the one-shot promise survives a restart. Idempotent —
        burn-at-mint means EXPIRED/KILL_IP may re-burn an already-burned
        label. The operator's label never burns: Poli knows the boss."""
        if label == ADMIN_LABEL or label in self.burned:
            return
        self.burned.add(label)
        persist_burn(self.burned_path, label)

    def audit(self, event, label="-", ip="-"):
        line = "[bouncer] %s %-10s label=%s ip=%s" % (
            time.strftime("%Y-%m-%dT%H:%M:%S"), event, label, ip)
        print(line, flush=True)
        if self.audit_path:
            with open(self.audit_path, "a") as f:
                f.write(line + "\n")

    def brand(self, template, label=None):
        """Fill the marquee slots. Club name and label are HTML-escaped —
        they come from the operator's config, but the gate page is read by
        strangers, so we don't trust anything."""
        out = template.replace("__CLUB__", html.escape(self.club_name))
        out = out.replace("__ACCENT__", self.accent)
        out = out.replace("__LOGO__", self.club_logo)
        out = out.replace("__SCENE__", SCENE_SVG)
        if label is not None:
            out = out.replace("__LABEL__", html.escape(label))
        return out


# ── SETUP + CORE ─────────────────────────────────────────────
# SETUP: viplist.txt is one "label phrase" per line (# = comment), with an
# optional per-VIP grant lifetime: "label ttl phrase". A positive integer
# right after the label is always read as a TTL — a phrase that begins with
# a number needs an explicit TTL in front of it, or a reworded phrase.
# CORE: phrases are hashed with a fresh salt at startup and compared in
# constant time. Never store or compare plaintext, and never echo which
# label was tried — that tells an attacker which labels exist.
# ────────────────────────────────────────────────────────────
def split_viplist_line(line):
    """Split one viplist line -> (label, ttl_or_None, phrase), or None if
    malformed. 'label ttl phrase' when the token after the label is a
    positive integer; otherwise 'label phrase' (spaces allowed in phrase)."""
    parts = line.split(None, 2)
    if len(parts) == 3 and parts[1].isdigit() and int(parts[1]) > 0:
        return parts[0], int(parts[1]), parts[2]
    parts = line.split(None, 1)
    if len(parts) == 2:
        return parts[0], None, parts[1]
    return None


def load_viplist(path, default_ttl):
    """Read the VIP list: label -> (salt, dk, ttl). ttl is the VIP's own
    grant lifetime, or default_ttl (the house TTL) when the line has none."""
    phrases = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        sys.exit("error: cannot read VIP list file: %s" % e)
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        split = split_viplist_line(line)
        if split is None:
            sys.exit("error: VIP list line %d: need 'label phrase' or 'label ttl phrase'"
                     % lineno)
        label, ttl, phrase = split
        if label in phrases:
            sys.exit("error: VIP list line %d: duplicate label '%s'" % (lineno, label))
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        phrases[label] = (salt, dk, ttl if ttl else default_ttl)
    return phrases


def read_viplist_raw(path):
    """Club Management only: label -> (plaintext phrase, ttl_or_None), to
    preserve phrases and per-VIP TTLs the operator didn't change.
    Local machine, operator's own file."""
    found = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return found
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        split = split_viplist_line(line)
        if split is None:
            continue
        label, ttl, phrase = split
        if label not in found:
            found[label] = (phrase, ttl)
    return found


# ── CORE: DO NOT WEAKEN ──────────────────────────────────────
# The burned list is the one-shot promise made durable: labels whose phrase
# is spent. It is loaded at startup and appended on every burn, so a restart
# can't re-arm a dead phrase. A fresh phrase (via Club Management regenerate)
# is the only way a burned label knocks again — unburn_labels() drops it
# from the file, and the gate picks that up on its next start.
# ────────────────────────────────────────────────────────────
def load_burned(path):
    """Read burned.txt -> set of spent labels. Missing file = first run."""
    burned = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return burned
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        burned.add(line.split(None, 1)[0])
    return burned


def persist_burn(path, label):
    """Append a spent label to the burned file. The gate must never break
    over bookkeeping — failure just leaves the in-memory burn holding."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("%s\n" % label)
    except OSError:
        pass


def unburn_labels(path, labels):
    """Drop labels from the burned file (they got fresh phrases). Comments
    and blank lines are preserved; only matching label lines go."""
    labels = set(labels)
    if not labels:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return
    out = []
    for raw in lines:
        stripped = raw.strip()
        if (stripped and not stripped.startswith("#")
                and stripped.split(None, 1)[0] in labels):
            continue
        out.append(raw)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
    except OSError:
        pass


# ── CORE: DO NOT TOUCH ───────────────────────────────────────
# Trusts CF-Connecting-IP because ALL public traffic arrives via the tunnel.
# Do NOT "simplify" this to the socket peer: behind the tunnel the peer is
# always the tunnel daemon, so every grant would bind to the same IP — one
# VIP's wristband would fit everyone. And never expose bouncer directly to
# the open internet: out there, clients can spoof this header.
# ────────────────────────────────────────────────────────────
def client_ip(handler):
    """VIP's real IP. Behind the tunnel Cloudflare sets CF-Connecting-IP;
    the socket peer is just the tunnel daemon. Locally (no tunnel), fall back
    to the socket peer."""
    hdr = handler.headers.get("CF-Connecting-IP")
    if hdr and hdr.strip():
        return hdr.strip().split(",")[0].strip()
    return handler.client_address[0]


# ---------------------------------------------------------------- cookies

def sign_cookie(state, label, ip, expires):
    body = "%s.%d.%s" % (label, expires, ip)
    sig = hmac.new(state.server_secret, body.encode("utf-8"), hashlib.sha256).hexdigest()
    return (base64.urlsafe_b64encode(label.encode("utf-8")).decode("ascii")
            + "." + str(expires) + "." + sig)


def parse_cookie(handler):
    header = handler.headers.get("Cookie")
    if not header:
        return None
    for part in header.split(";"):
        part = part.strip()
        if part.startswith(COOKIE_NAME + "="):
            return part[len(COOKIE_NAME) + 1:]
    return None


def parse_token(token):
    """Split a cookie token into (label, sig). Returns (None, None) if malformed."""
    try:
        b64label, _expires_s, sig = token.split(".")
        label = base64.urlsafe_b64decode(b64label + "=" * (-len(b64label) % 4)).decode("utf-8")
    except Exception:
        return None, None
    return label, sig


# ---------------------------------------------------------------- handler

class Handler(BaseHTTPRequestHandler):
    server_version = "Bouncer/1.0"

    @property
    def state(self):
        return self.server.state

    def log_message(self, *args):
        pass  # audit() handles logging; keep the console clean

    # -- responses -------------------------------------------------

    def serve_gate(self, msg=""):
        st = self.state
        page = st.brand(GATE_HTML).replace("__MSG__", html.escape(msg))
        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def serve_poli(self):
        """Poli, the bouncer (beat 2: the doors). Served from alongside
        bouncer.py. Fixed filename — no user input touches the path.
        A missing file is a 404, never a crash; the doors still open."""
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(here, "poli.webp"), "rb") as f:
                data = f.read()
        except OSError:
            self.serve_plain(404, "poli is off duty.")
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/webp")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def serve_doors(self, label):
        """Beat 2: the doors. Only reachable with a live grant — strangers
        get the gate. The button walks the VIP to / (the app)."""
        st = self.state
        grant = st.grants.get(label)
        if grant:
            last_call = time.strftime("%I:%M %p", time.localtime(grant["expires"])).lstrip("0")
            wristband = "this wristband is good for %s \u2014 last call %s." % (
                human_seconds(grant["ttl"]), last_call)
        else:
            wristband = ""
        if label == ADMIN_LABEL:
            greeting = "good evening, <span class=\"vip\">boss</span>"
            sub = "no knock needed &mdash; Poli knows the face."
            # The boss doesn't get wristband talk — Poli just waves him in.
            # (The grant underneath stays a real TTL/IP-bound session.)
            wristband = ""
        else:
            greeting = "you're on the list, <span class=\"vip\">%s</span>" % html.escape(label)
            sub = "the rope unclips. the doors are open."
        data = st.brand(DOORS_HTML).replace(
            "__GREETING__", greeting).replace(
            "__SUB__", sub).replace(
            "__WRISTBAND__", html.escape(wristband)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def serve_plain(self, code, text, retry_after=None):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if retry_after:
            self.send_header("Retry-After", str(retry_after))
        self.end_headers()
        self.wfile.write(body)

    # -- auth ------------------------------------------------------

    def authed_label(self):
        """Full check: parse cookie, find the live grant, verify the HMAC
        against the grant's bound values, then require the request IP to
        match the bound IP. Mismatch or expiry kills the grant (one-shot)."""
        st = self.state
        ip = client_ip(self)
        token = parse_cookie(self)
        if not token:
            return None
        label, sig = parse_token(token)
        if not label:
            return None
        now = int(time.time())
        with st.lock:
            grant = st.grants.get(label)
            if not grant:
                return None
            if grant["expires"] <= now:
                # last call — wristband faded
                del st.grants[label]
                st.burn(label)
                st.audit("EXPIRED", label, grant["ip"])
                return None
            body = "%s.%d.%s" % (label, grant["expires"], grant["ip"])
            want = hmac.new(st.server_secret, body.encode("utf-8"),
                            hashlib.sha256).hexdigest()
            if not hmac.compare_digest(want, sig):
                return None
            if grant["ip"] != ip:
                # wrong wrist, wrong wristband — poof
                del st.grants[label]
                st.burn(label)
                st.audit("KILL_IP", label, ip)
                return None
        return label

    def rate_limited(self, ip):
        st = self.state
        now = time.time()
        with st.lock:
            recent = [t for t in st.attempts.get(ip, []) if now - t < ATTEMPT_WINDOW]
            if len(recent) >= MAX_ATTEMPTS:
                st.attempts[ip] = recent
                return True
            recent.append(now)
            st.attempts[ip] = recent
        return False

    def log_attempt(self, result, label="-"):
        """Attempt logger: one JSON line per knock on the gate. Metadata only —
        never the attempted phrase (wrong guesses are often typos of real ones)."""
        st = self.state
        if not st.attempt_log:
            return
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "ip": client_ip(self),
            "result": result,
            "label": label,
            "ua": (self.headers.get("User-Agent") or "-")[:120],
        }
        try:
            with open(st.attempt_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError:
            pass  # the gate must never break over logging

    # -- HTTP verbs ------------------------------------------------

    def do_GET(self):
        upath = urllib.parse.urlparse(self.path).path
        if upath == "/poli.webp":
            # Poli, the mascot — a public branding asset, like the gate
            # page itself. No grant needed; it's a cartoon, not a secret.
            self.serve_poli()
            return
        if upath == "/enter":
            # Beat 2: the doors. Live grant -> the VIP is greeted by name.
            # No grant -> back to the line.
            label = self.authed_label()
            if label:
                self.serve_doors(label)
            else:
                self.serve_gate()
            return
        if self.authed_label():
            self.serve_behind_rope()
        else:
            self.serve_gate()

    # ── CORE: DO NOT TOUCH ───────────────────────────────────
    # The grant ceremony: verify the phrase (constant-time), sign a cookie
    # bound to label+IP+expiry, burn the grant on IP mismatch. Don't log the
    # phrase, don't accept it via GET (URLs end up in logs), don't skip the
    # burn. The attempt logger records metadata only — keep it that way.
    # A good phrase now opens the doors (/enter), not the app directly —
    # the VIP walks through "step inside" to / themselves.
    # ────────────────────────────────────────────────────────
    def do_POST(self):
        # A VIP with a live grant POSTing is talking to their app, not
        # knocking — forward it behind the rope. Only strangers knock;
        # the grant ceremony below is for them.
        if self.authed_label():
            self.serve_behind_rope()
            return
        st = self.state
        ip = client_ip(self)
        if self.rate_limited(ip):
            st.audit("RATELIMITED", "-", ip)
            self.log_attempt("ratelimited")
            self.serve_plain(429, "slow down.", retry_after=ATTEMPT_WINDOW)
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        phrase = urllib.parse.parse_qs(body.decode("utf-8", "replace")).get("phrase", [""])[0]
        matched = None
        matched_ttl = None
        with st.lock:
            # The owner doesn't knock — he's recognized. The admin phrase
            # mints (or replaces) the operator grant and never burns.
            if st.admin:
                asalt, adk = st.admin
                atest = hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"),
                                            asalt, PBKDF2_ITERATIONS)
                if hmac.compare_digest(adk, atest):
                    matched = ADMIN_LABEL
            if not matched:
                for label, (salt, dk, label_ttl) in st.phrases.items():
                    if label in st.grants or label in st.burned:
                        continue
                    test = hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"), salt, PBKDF2_ITERATIONS)
                    if hmac.compare_digest(dk, test):
                        matched = label
                        matched_ttl = label_ttl
                        break
            if matched:
                ttl = matched_ttl or st.ttl
                expires = int(time.time()) + ttl
                st.grants[matched] = {"ip": ip, "expires": expires, "ttl": ttl}
                # Burn at mint: the phrase dies the moment it works. The
                # wristband stays valid for its TTL; a restart can't re-arm
                # the phrase. (burn() itself exempts the operator.)
                st.burn(matched)
                cookie = sign_cookie(st, matched, ip, expires)
        if matched:
            st.audit("GRANT", matched, ip)
            self.log_attempt("granted", matched)
            self.send_response(302)
            self.send_header("Set-Cookie",
                             "%s=%s; Path=/; HttpOnly; Secure; SameSite=Lax" % (COOKIE_NAME, cookie))
            self.send_header("Location", "/enter")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
        else:
            st.audit("DENIED", "-", ip)
            self.log_attempt("denied")
            self.serve_gate("not on the list.")

    # PUT/DELETE/PATCH to authed sessions are served too
    def do_PUT(self):
        self.do_GET()

    def do_DELETE(self):
        self.do_GET()

    def do_PATCH(self):
        self.do_GET()

    def do_HEAD(self):
        if self.authed_label():
            self.serve_behind_rope()
        else:
            self.serve_gate()

    # -- behind the rope -------------------------------------------

    def serve_behind_rope(self):
        if self.state.mode == "serve":
            self.serve_file()
        else:
            self.proxy()

    # ── CORE: DO NOT TOUCH ───────────────────────────────────
    # realpath on BOTH sides: the served dir is resolved at startup and every
    # request path is resolved before the prefix check. Weaken this and
    # /%2e%2e/ walks out of the folder. (Caught live on macOS: /tmp is a
    # symlink to /private/tmp — resolve it or every file 404s.)
    # ────────────────────────────────────────────────────────
    def serve_file(self):
        """One-door static mode: serve files from serve_dir to VIPs only."""
        st = self.state
        upath = urllib.parse.urlparse(self.path).path
        rel = urllib.parse.unquote(upath).lstrip("/")
        full = os.path.realpath(os.path.join(st.serve_dir, rel))
        if full != st.serve_dir and not full.startswith(st.serve_dir + os.sep):
            self.serve_plain(404, "nothing here.")
            return
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not os.path.isfile(full):
            self.serve_plain(404, "nothing here.")
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        try:
            size = os.path.getsize(full)
        except OSError:
            self.serve_plain(404, "nothing here.")
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command == "HEAD":
            return
        try:
            with open(full, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            self.wfile.flush()
        except OSError:
            pass

    # -- reverse proxy ---------------------------------------------

    def proxy(self):
        st = self.state
        ip = client_ip(self)
        t = st.target
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else None

        headers = {}
        for k, v in self.headers.items():
            kl = k.lower()
            if kl in HOP_BY_HOP or kl == "host":
                continue
            if kl == "cookie":
                kept = [c.strip() for c in v.split(";")
                        if not c.strip().startswith(COOKIE_NAME + "=")]
                if kept:
                    headers[k] = "; ".join(kept)
                continue
            headers[k] = v
        headers["X-Forwarded-For"] = ip
        headers["Host"] = t.netloc
        headers["Connection"] = "close"

        port = t.port or (443 if t.scheme == "https" else 80)
        cls = http.client.HTTPSConnection if t.scheme == "https" else http.client.HTTPConnection
        try:
            conn = cls(t.hostname, port, timeout=30)
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
        except Exception:
            self.serve_plain(502, "the house isn't answering.")
            return

        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            kl = k.lower()
            if kl in HOP_BY_HOP or kl in ("content-length", "connection"):
                continue
            self.send_header(k, v)
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
            self.wfile.flush()
        finally:
            conn.close()


# ---------------------------------------------------------------- Club Management

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# Club Management (--manage): the back office. A local-only web form that
# writes bouncer.conf + viplist.txt — the same contract the AI and the
# terminal use. First run: blank form. Later runs: pre-filled from the
# current config, phrases masked with regenerate checkboxes.
#
# HARD RULE: this binds 127.0.0.1 and must NEVER be tunneled. A
# config-writing endpoint on the public internet is game over.
# ────────────────────────────────────────────────────────────
MANAGE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Club Management &mdash; bouncer</title>
<style>
body{background:#0d0d0f;color:#e8e8ea;font-family:system-ui,sans-serif;margin:0;padding:2rem}
.wrap{max-width:44rem;margin:0 auto}
.warn{background:#3a1414;border:1px solid #7a2626;border-radius:10px;padding:1rem 1.2rem;margin-bottom:1.5rem}
.warn b{color:#ff9b9b}
h1{margin:.2rem 0 1.4rem}
h2{font-size:1.05rem;color:#c9a227;letter-spacing:.12em;text-transform:uppercase;margin:1.8rem 0 .6rem}
label{display:block;font-size:.85rem;color:#999;margin:.7rem 0 .25rem}
input[type=text],input[type=number],textarea{width:100%;box-sizing:border-box;background:#1a1a1e;border:1px solid #333;color:#fff;padding:.6rem .8rem;font-size:.95rem;border-radius:8px}
textarea{font-family:ui-monospace,monospace;min-height:5rem}
.row{display:flex;gap:.6rem;align-items:end}
.row>div{flex:1}
.hint{font-size:.8rem;color:#666;margin:.25rem 0 0}
.vip-row{display:flex;gap:.5rem;margin:.4rem 0;align-items:center}
.vip-row input[type=text]{flex:1}
.vip-row input.ttl{flex:0 0 6.5rem}
.spent{color:#ff9b9b;font-family:ui-monospace,monospace;font-size:.9rem;margin:.25rem 0}
.regen{white-space:nowrap;font-size:.85rem;color:#999}
button,.save{background:#c9a227;color:#111;border:0;padding:.7rem 1.4rem;font-size:1rem;font-weight:700;border-radius:8px;cursor:pointer}
button.ghost{background:#2a2a30;color:#e8e8ea;font-weight:400;padding:.5rem 1rem;font-size:.9rem}
.save{margin-top:1.6rem;width:100%;padding:.9rem}
.radio{display:inline-block;margin-right:1.2rem;color:#e8e8ea;font-size:.95rem}
</style></head>
<body><div class="wrap">
<div class="warn"><b>LOCAL ONLY.</b> This page writes your club's config.
Never tunnel it, never expose it &mdash; it binds 127.0.0.1 for a reason.</div>
<h1>\U0001f300 Club Management</h1>
<p style="color:#999">Editing <code>__CONFIG_PATH__</code>. First run: blank.
Later: pre-filled &mdash; change what you want, leave the rest.</p>
<form method="post" action="/save">
<h2>The marquee</h2>
<label>Club name &mdash; on the awning, over the doors</label>
<input type="text" name="club_name" value="__CLUB__" placeholder="The Bouncer">
<label>Accent color &mdash; the rope, the buttons (#rgb or #rrggbb)</label>
<input type="text" name="accent" value="__ACCENT__" placeholder="#c9a227">
<label>Logo &mdash; paste inline SVG, or a path to a .svg file (blank = house art only)</label>
<textarea name="club_logo" placeholder="<svg ...>...</svg>">__LOGO__</textarea>
<p class="hint">See docs/BRANDING.md for sizes and placement.</p>

<h2>One door</h2>
<label>Mode &mdash; exactly one. Serve a folder, or proxy a local app (never tunnel the app itself)</label>
<div>
<span class="radio"><input type="radio" name="mode" value="serve" __SERVE_CHECKED__> serve a static folder</span>
<span class="radio"><input type="radio" name="mode" value="proxy" __PROXY_CHECKED__> proxy a dynamic app</span>
</div>
<div class="row"><div>
<label>Serve dir (serve mode)</label>
<input type="text" name="serve_dir" value="__SERVE_DIR__" placeholder="./public">
</div><div>
<label>Target (proxy mode, e.g. http://127.0.0.1:11435)</label>
<input type="text" name="target" value="__TARGET__" placeholder="http://127.0.0.1:11435">
</div></div>

<h2>The house rules</h2>
<div class="row">
<div><label>Port</label><input type="number" name="port" value="__PORT__"></div>
<div><label>Bind (leave 127.0.0.1)</label><input type="text" name="bind" value="__BIND__"></div>
<div><label>Grant lifetime (seconds)</label><input type="number" name="ttl" value="__TTL__"></div>
</div>
<label>VIP list file</label>
<input type="text" name="viplist" value="__VIPLIST__" placeholder="./viplist.txt">
<label>Attempt log (blank = off)</label>
<input type="text" name="attempt_log" value="__ATTEMPT_LOG__" placeholder="./attempts.log">
<label>Burned list file</label>
<input type="text" name="burned" value="__BURNED__" placeholder="./burned.txt">
<p class="hint">One-shot phrases burn here the moment they mint a grant. Survives restarts — a burned label can't knock again until it gets a fresh phrase.</p>

<h2>The owner</h2>
<label>Operator phrase &mdash; Poli knows the boss. Never burns, knock as often as you like.</label>
<input type="password" name="admin_phrase" placeholder="(unchanged)" autocomplete="off">
<p class="hint">The master key: blank keeps the current one, and it is never shown.
Anyone holding it walks in forever &mdash; guard it like the keys to the club.
To remove it entirely, delete the ADMIN_PHRASE line from bouncer.conf by hand.</p>

<h2>The VIP list</h2>
<p class="hint">Phrases stay masked. Blank "new phrase" keeps the current one;
tick regenerate (or leave blank on a new row) for a fresh generated phrase.
TTL is that VIP's own grant lifetime in seconds — blank means the house grant
lifetime above. New/changed phrases are shown ONCE after saving &mdash; copy them to your VIPs.</p>
<div id="vips">
__VIP_ROWS__
</div>
<input type="hidden" id="vip_count" name="vip_count" value="__VIP_COUNT__">
<p><button type="button" class="ghost" onclick="addRow()">+ add VIP</button></p>

<h2>Burned out</h2>
<p class="hint">Labels whose one-shot phrase is spent. They can't knock again —
hand one a fresh phrase (regenerate above) to let it back in.</p>
__BURNED_ROWS__

<button class="save" type="submit">save the club</button>
</form></div>
<script>
let n = parseInt(document.getElementById('vip_count').value) || 0;
function addRow(){
  const d = document.createElement('div');
  d.className = 'vip-row';
  d.innerHTML = '<input type="text" name="label_'+n+'" placeholder="label">' +
    '<input type="text" class="ttl" name="ttl_'+n+'" placeholder="ttl secs">' +
    '<input type="text" name="newphrase_'+n+'" placeholder="new phrase (blank = generate)" autocomplete="off">' +
    '<span class="regen"><input type="checkbox" name="regen_'+n+'" value="1"> regenerate</span>';
  document.getElementById('vips').appendChild(d);
  n++;
  document.getElementById('vip_count').value = n;
}
</script>
</body></html>"""

CONFIRM_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>saved &mdash; Club Management</title>
<style>
body{background:#0d0d0f;color:#e8e8ea;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.card{text-align:center;padding:2rem;max-width:34rem}
.spiral{font-size:3rem}
.phrase{background:#1a1a1e;border:1px solid #c9a227;border-radius:8px;padding:.7rem 1rem;margin:.5rem 0;font-family:ui-monospace,monospace;word-break:break-all}
.warn{color:#ff9b9b;font-size:.9rem}
code{background:#1a1a1e;padding:.2rem .5rem;border-radius:6px}
</style></head>
<body><div class="card">
<div class="spiral">\U0001f300</div>
<h2>the club is saved</h2>
<p>__SUMMARY__</p>
__PHRASES__
<p class="warn">Phrases are shown once. Copy them to your VIPs now &mdash; this page won't show them again.</p>
<p>Now run the gate normally:</p>
<p><code>python3 bouncer.py</code></p>
</div></body></html>"""


def write_config(path, new):
    """Write bouncer.conf: replace managed KEYs in place, keep unknown
    keys/comments/blanks verbatim, append managed keys that weren't there."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        lines = []
    out = []
    seen = set()
    for raw in lines:
        s = raw.strip()
        if s and not s.startswith("#") and "=" in s:
            key = s.split("=", 1)[0].strip().upper()
            if key in new:
                out.append("%s = %s\n" % (key, new[key]))
                seen.add(key)
                continue
        out.append(raw if raw.endswith("\n") else raw + "\n")
    for key, value in new.items():
        if key not in seen:
            out.append("%s = %s\n" % (key, value))
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)


def build_manage_page(cfg_path):
    """Render Club Management, pre-filled from the current config (or blank)."""
    try:
        cfg = load_config(cfg_path)
    except SystemExit:
        cfg = {}  # malformed config -> start blank, don't die

    def g(key, default=""):
        return cfg.get(key.upper(), default)

    viplist_path = g("viplist", "./viplist.txt")
    existing = read_viplist_raw(viplist_path) if os.path.exists(viplist_path) else {}
    house_ttl = g("ttl", "86400")

    rows = []
    for i, (label, (_phrase, ttl)) in enumerate(existing.items()):
        rows.append(
            '<div class="vip-row">'
            '<input type="text" name="label_%d" value="%s" placeholder="label">'
            '<input type="text" class="ttl" name="ttl_%d" value="%s" placeholder="house: %ss">'
            '<input type="text" name="newphrase_%d" placeholder="new phrase (blank = keep)" autocomplete="off">'
            '<span class="regen"><input type="checkbox" name="regen_%d" value="1"> regenerate</span>'
            "</div>" % (i, html.escape(label), i,
                        html.escape(str(ttl) if ttl else ""), house_ttl, i, i))
    if not rows:
        rows.append(
            '<div class="vip-row">'
            '<input type="text" name="label_0" placeholder="label">'
            '<input type="text" class="ttl" name="ttl_0" placeholder="house: %ss">'
            '<input type="text" name="newphrase_0" placeholder="new phrase (blank = generate)" autocomplete="off">'
            '<span class="regen"><input type="checkbox" name="regen_0" value="1"> regenerate</span>'
            "</div>" % house_ttl)
    n = max(len(existing), 1)

    burned_path = g("burned", "./burned.txt")
    burned = sorted(load_burned(burned_path))
    if burned:
        burned_rows = "".join(
            '<p class="spent">%s</p>' % html.escape(b) for b in burned)
    else:
        burned_rows = '<p class="hint">none &mdash; every phrase is live.</p>'

    mode = "proxy" if g("target") and not g("serve_dir") else "serve"
    page = MANAGE_HTML
    page = page.replace("__CONFIG_PATH__", html.escape(cfg_path))
    page = page.replace("__CLUB__", html.escape(g("club_name", DEFAULT_CLUB_NAME)))
    page = page.replace("__ACCENT__", html.escape(g("accent", DEFAULT_ACCENT)))
    page = page.replace("__LOGO__", html.escape(g("club_logo", "")))
    page = page.replace("__SERVE_CHECKED__", "checked" if mode == "serve" else "")
    page = page.replace("__PROXY_CHECKED__", "checked" if mode == "proxy" else "")
    page = page.replace("__SERVE_DIR__", html.escape(g("serve_dir", "./public")))
    page = page.replace("__TARGET__", html.escape(g("target", "")))
    page = page.replace("__PORT__", html.escape(g("port", "8787")))
    page = page.replace("__BIND__", html.escape(g("bind", "127.0.0.1")))
    page = page.replace("__TTL__", html.escape(g("ttl", "86400")))
    page = page.replace("__VIPLIST__", html.escape(viplist_path))
    page = page.replace("__ATTEMPT_LOG__", html.escape(g("attempt_log", "")))
    page = page.replace("__BURNED__", html.escape(burned_path))
    page = page.replace("__BURNED_ROWS__", burned_rows)
    page = page.replace("__VIP_ROWS__", "".join(rows))
    page = page.replace("__VIP_COUNT__", str(n))
    return page


class ManageHandler(BaseHTTPRequestHandler):
    server_version = "Bouncer-Manage/1.0"

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path != "/":
            self._send(404, "nothing here.", "text/plain; charset=utf-8")
            return
        self._send(200, build_manage_page(self.server.cfg_path))

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/save":
            self._send(404, "nothing here.", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        form = urllib.parse.parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)

        def fv(name, default=""):
            return form.get(name, [default])[0].strip()

        cfg_path = self.server.cfg_path
        try:
            n = int(fv("vip_count", "0"))
        except ValueError:
            n = 0

        # --- VIP list: keep untouched phrases, generate the rest ---
        viplist_path = fv("viplist", "./viplist.txt") or "./viplist.txt"
        existing = read_viplist_raw(viplist_path) if os.path.exists(viplist_path) else {}
        vips = {}       # label -> (phrase, ttl_or_None) to write
        show_once = {}  # label -> (phrase, ttl_or_None), new/changed: display once
        for i in range(n):
            label = fv("label_%d" % i)
            if not label:
                continue
            if label in vips:
                self._send(400, "duplicate label: %s" % html.escape(label),
                           "text/plain; charset=utf-8")
                return
            if label == ADMIN_LABEL:
                self._send(400, "'%s' is reserved for the operator's pass." % ADMIN_LABEL,
                           "text/plain; charset=utf-8")
                return
            # Per-VIP grant lifetime. Blank = the house TTL (and drops any
            # explicit TTL the label had — blank means "house rules").
            ttl_raw = fv("ttl_%d" % i)
            ttl = None
            if ttl_raw:
                try:
                    ttl = int(ttl_raw)
                    if ttl <= 0:
                        raise ValueError
                except ValueError:
                    self._send(400, "TTL for '%s' must be a positive number of seconds."
                               % html.escape(label), "text/plain; charset=utf-8")
                    return
            new_phrase = fv("newphrase_%d" % i)
            regen = ("regen_%d" % i) in form
            if new_phrase:
                vips[label] = (new_phrase, ttl)
                show_once[label] = (new_phrase, ttl)
            elif regen or label not in existing:
                phrase = gen_phrase()
                vips[label] = (phrase, ttl)
                show_once[label] = (phrase, ttl)
            else:
                vips[label] = existing[label]
        if not vips:
            self._send(400, "the VIP list needs at least one VIP.",
                       "text/plain; charset=utf-8")
            return

        # --- bouncer.conf ---
        # Every managed key is written every save, in place. The mode NOT
        # chosen goes blank so no stale TARGET/SERVE_DIR survives to trip
        # the fail-closed "pick ONE mode" check at startup. Same for the
        # attempt log: blank means off, and a stale path can't re-enable it.
        # The burned list is a path, not a toggle — it always has a value.
        mode = fv("mode", "serve")
        burned_path = fv("burned", "./burned.txt") or "./burned.txt"
        new_cfg = {
            "CLUB_NAME": fv("club_name", DEFAULT_CLUB_NAME) or DEFAULT_CLUB_NAME,
            "ACCENT": fv("accent", DEFAULT_ACCENT) or DEFAULT_ACCENT,
            # bouncer.conf is line-oriented: a pasted multi-line SVG would
            # break parsing, so collapse it to one line (SVG ignores it).
            # A path to a .svg file avoids the question entirely.
            "CLUB_LOGO": " ".join(fv("club_logo", "").split()),
            "PORT": fv("port", "8787") or "8787",
            "BIND": fv("bind", "127.0.0.1") or "127.0.0.1",
            "TTL": fv("ttl", "86400") or "86400",
            "VIPLIST": viplist_path,
            "ATTEMPT_LOG": fv("attempt_log", ""),
            "BURNED": burned_path,
        }
        # --- the owner ---
        # The operator phrase: blank in the form = keep whatever is in the
        # file (it is never displayed). A new one must not match a VIP
        # phrase — the gate also refuses to start on a collision.
        admin_phrase = fv("admin_phrase", "")
        if admin_phrase:
            if admin_phrase in [p for (p, _t) in vips.values()]:
                self._send(400, "the operator phrase must not match a VIP phrase.",
                           "text/plain; charset=utf-8")
                return
            new_cfg["ADMIN_PHRASE"] = admin_phrase
        if mode == "proxy":
            new_cfg["TARGET"] = fv("target", "") or "http://127.0.0.1:11435"
            new_cfg["SERVE_DIR"] = ""
        else:
            new_cfg["SERVE_DIR"] = fv("serve_dir", "./public") or "./public"
            new_cfg["TARGET"] = ""
        try:
            port = int(new_cfg["PORT"])
            ttl = int(new_cfg["TTL"])
            if not (1 <= port <= 65535 and ttl > 0):
                raise ValueError
        except ValueError:
            self._send(400, "port must be 1-65535 and TTL positive.",
                       "text/plain; charset=utf-8")
            return
        if mode == "proxy":
            t = urllib.parse.urlparse(new_cfg["TARGET"])
            if t.scheme not in ("http", "https") or not t.hostname:
                self._send(400, "target must be an http(s)://host[:port] URL.",
                           "text/plain; charset=utf-8")
                return

        try:
            write_config(cfg_path, new_cfg)
            with open(viplist_path, "w", encoding="utf-8") as f:
                f.write("# BOUNCER VIP list — written by Club Management.\n")
                f.write("# NEVER commit this file (gitignored).\n")
                f.write("# 'label phrase' uses the house grant lifetime;\n")
                f.write("# 'label ttl phrase' gives that VIP their own (seconds).\n")
                for label, (phrase, ttl) in vips.items():
                    if ttl:
                        f.write("%s %d %s\n" % (label, ttl, phrase))
                    else:
                        f.write("%s %s\n" % (label, phrase))
            # A fresh phrase re-arms a burned label — the only way back in.
            # The gate loads burned.txt at startup, so this takes effect on
            # its next start (Club Management never restarts the gate).
            unburn_labels(burned_path, show_once)
        except OSError as e:
            self._send(500, "couldn't write the files: %s" % html.escape(str(e)),
                       "text/plain; charset=utf-8")
            return

        summary = "Wrote <code>%s</code> (%s mode) and <code>%s</code> (%d VIP%s)." % (
            html.escape(cfg_path), html.escape(mode), html.escape(viplist_path),
            len(vips), "" if len(vips) == 1 else "s")
        if show_once:
            phrases = "".join(
                '<div class="phrase">%s &nbsp;·&nbsp; %s &nbsp;·&nbsp; %s</div>' % (
                    html.escape(label), html.escape(phrase),
                    html.escape(human_seconds(ttl) if ttl else "house grant lifetime"))
                for label, (phrase, ttl) in show_once.items())
        else:
            phrases = "<p>No new phrases — the list is unchanged.</p>"
        page = CONFIRM_HTML.replace("__SUMMARY__", summary).replace("__PHRASES__", phrases)
        print("[manage] saved %s (%d vips, %d new phrases)" % (
            cfg_path, len(vips), len(show_once)), flush=True)
        self._send(200, page)


def run_manage(cfg_path, port):
    """Club Management: local-only config writer. Never tunneled, ever."""
    server = ThreadingHTTPServer(("127.0.0.1", port), ManageHandler)
    server.cfg_path = cfg_path
    server.daemon_threads = True
    print("[manage] 🛎️  Club Management — LOCAL ONLY on 127.0.0.1:%d" % port, flush=True)
    print("[manage] Open http://127.0.0.1:%d in your browser." % port, flush=True)
    print("[manage] NEVER tunnel this page — it writes your config.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[manage] closed. nothing was restarted — run python3 bouncer.py for the gate.",
              flush=True)


# ---------------------------------------------------------------- main

# ── SETUP: SAFE TO CHANGE ────────────────────────────────────
# Reads bouncer.conf (KEY = value). The format is documented in
# bouncer.conf.example — copy that, don't invent new keys here unless you
# also wire them into main() below.
# ────────────────────────────────────────────────────────────
def load_config(path):
    """Read bouncer.conf: KEY = value lines, # comments, blanks ignored."""
    cfg = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        sys.exit("error: cannot read config file: %s" % e)
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            sys.exit("error: config line %d: need KEY = value" % lineno)
        key, value = line.split("=", 1)
        cfg[key.strip().upper()] = value.strip().strip("\"").strip("'")
    return cfg


def main():
    ap = argparse.ArgumentParser(description="THE BOUNCER — put a bouncer on your tunnel.")
    ap.add_argument("--config", default="bouncer.conf",
                    help="setup file (used when present; CLI flags override it)")
    ap.add_argument("--target", default=None,
                    help="proxy mode: forward authed VIPs here, e.g. http://127.0.0.1:11435")
    ap.add_argument("--serve", default=None,
                    help="serve mode: serve this static folder to authed VIPs (one door)")
    ap.add_argument("--port", type=int, default=None, help="port bouncer listens on")
    ap.add_argument("--bind", default=None, help="interface to bind")
    ap.add_argument("--viplist", default=None,
                    help="VIP phrase file: 'label phrase' per line")
    ap.add_argument("--ttl", type=int, default=None, help="grant lifetime in seconds")
    ap.add_argument("--audit-log", default=None,
                    help="optional audit log file (default: stdout)")
    ap.add_argument("--attempt-log", default=None,
                    help="JSON-lines log of every passphrase attempt "
                         "(metadata only, never the phrase)")
    ap.add_argument("--burned", default=None,
                    help="spent one-shot labels file (the forbidden list)")
    # ── SETUP: SAFE TO CHANGE ──
    # Marquee slots: the operator's branding on the gate + doors pages.
    ap.add_argument("--club-name", default=None,
                    help="club name on the awning (default: The Bouncer)")
    ap.add_argument("--club-logo", default=None,
                    help="inline <svg...> or path to a .svg file (default: none)")
    ap.add_argument("--accent", default=None,
                    help="accent color, #rgb or #rrggbb (default: #c9a227)")
    ap.add_argument("--admin-phrase", default=None,
                    help="operator's phrase: mints grants that never burn (default: none)")
    ap.add_argument("--manage", action="store_true",
                    help="Club Management: local-only web setup (127.0.0.1, never tunnel it)")
    cli = ap.parse_args()

    if cli.manage:
        # The back office: writes bouncer.conf + viplist.txt, then exits.
        # Forced to localhost — this must never face the internet.
        cfg = {}
        if os.path.exists(cli.config):
            try:
                cfg = load_config(cli.config)
            except SystemExit:
                pass
        port = cli.port or int(cfg.get("PORT", 8787))
        run_manage(cli.config, port)
        return

    # bouncer.conf is the setup sheet: comment/uncomment what you need.
    # CLI flags override the file. No file? Flags (or defaults) rule alone.
    cfg = load_config(cli.config) if os.path.exists(cli.config) else {}

    def pick(flag, key, default=None):
        if flag is not None:
            return flag
        return cfg.get(key.upper(), default)

    target = pick(cli.target, "target")
    serve = pick(cli.serve, "serve_dir")
    if (target and serve) or (not target and not serve):
        sys.exit("error: pick ONE mode — uncomment TARGET (proxy a dynamic app) "
                 "or SERVE_DIR (serve a static folder) in bouncer.conf")

    class Opt:
        pass
    args = Opt()
    args.target = target
    args.serve = serve
    # ── SETUP: SAFE TO CHANGE ────────────────────────────────
    # Defaults. Prefer bouncer.conf over editing these — the file is the
    # setup sheet, this is the fallback.
    args.port = int(pick(cli.port, "port", 8787))
    args.bind = pick(cli.bind, "bind", "127.0.0.1")
    args.viplist = pick(cli.viplist, "viplist")
    args.ttl = int(pick(cli.ttl, "ttl", 86400))
    args.audit_log = pick(cli.audit_log, "audit_log")
    args.attempt_log = pick(cli.attempt_log, "attempt_log")
    args.burned = pick(cli.burned, "burned", "./burned.txt")
    args.club_name = pick(cli.club_name, "club_name", DEFAULT_CLUB_NAME)
    args.club_logo = pick(cli.club_logo, "club_logo", "")
    args.accent = pick(cli.accent, "accent", DEFAULT_ACCENT)
    args.admin_phrase = pick(cli.admin_phrase, "admin_phrase", "")
    if not args.viplist:
        sys.exit("error: no VIP list — set VIPLIST in bouncer.conf or pass --viplist")

    state = BouncerState(args)
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    server.state = state
    server.daemon_threads = True
    dest = args.serve if state.mode == "serve" else args.target
    print("[bouncer] 🌀 live on %s:%d -> %s | mode=%s ttl=%ds | phrases=%d | club=%s | one-shot grants"
          % (args.bind, args.port, dest, state.mode, args.ttl, len(state.phrases),
             state.club_name), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bouncer] last call. all grants wiped.", flush=True)


if __name__ == "__main__":
    main()
