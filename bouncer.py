#!/usr/bin/env python3
"""
BOUNCER 🌀 — put a bouncer on your tunnel.

A tiny passphrase gate: one URL serves a passphrase page to strangers and
your app to VIPs on the list. Per-VIP phrases are one-shot: first use binds
the phrase to the VIP's IP, and the grant dies if the IP changes or the
TTL expires. Stdlib only — no pip, no venv.

Two modes — pick ONE in bouncer.conf (comment/uncomment what you need):

  serve — bouncer IS the server. It serves a static folder to authed VIPs.
          One door, one port, one tunnel. Nothing else listens anywhere.
          Best for static apps: a single HTML file, a docs folder, ...

  proxy — bouncer forwards authed VIPs to your dynamic app. Your app must
          bind 127.0.0.1 and never get its own tunnel. One door only.

Setup:

    cp bouncer.conf.example bouncer.conf   # then uncomment your mode
    cp viplist.example.txt viplist.txt     # then put real phrases in it
    python3 bouncer.py                     # CLI flags override bouncer.conf

New here — human or AI? Read docs/AI-Setup-Directions.md. It maps every
SAFE-TO-CHANGE zone and every DO-NOT-TOUCH zone in this file.

viplist.txt format (one per line, keep OUT of git — see .gitignore):

    joe     correct horse battery staple
    frank   another secret phrase here

Label is the first token; the rest of the line is the phrase (spaces allowed).
Lines starting with # are ignored.
You're on the VIP list or you're not. 🌀

Flow: visitor -> tunnel URL -> bouncer -> (wristband?) -> your app.

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
"""

# ── AI / HUMAN SETUP ─────────────────────────────────────────
# Setting this up? Read docs/AI-Setup-Directions.md first.
# It maps every SAFE-TO-CHANGE zone and every DO-NOT-TOUCH zone below.
# ────────────────────────────────────────────────────────────
import argparse
import base64
import hashlib
import hmac
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
# The gate page. Restyle it, reword it, make it yours — but keep {msg}
# (where errors print) and the <form method="post"> with the input named
# "phrase". Never print the target path, a phrase, or any config value
# here: strangers read this page.
# ────────────────────────────────────────────────────────────
GATE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>bouncer</title>
<style>
body{{background:#0d0d0f;color:#e8e8ea;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}}
.card{{text-align:center;padding:2rem}}.spiral{{font-size:3rem}}
input{{background:#1a1a1e;border:1px solid #333;color:#fff;padding:.7rem 1rem;font-size:1rem;border-radius:8px;width:16rem}}
button{{background:#fff;color:#000;border:0;padding:.7rem 1.2rem;font-size:1rem;border-radius:8px;cursor:pointer;margin-top:.8rem}}
.err{{color:#ff7b7b;min-height:1.4em}}
</style></head>
<body><div class="card"><div class="spiral">🌀</div>
<h2>this tunnel has a bouncer</h2>
<p class="err">{msg}</p>
<form method="post"><input type="password" name="phrase" placeholder="passphrase" autocomplete="off" autofocus><br>
<button type="submit">let me in</button></form></div></body></html>"""


# ---------------------------------------------------------------- state

# ── CORE: DO NOT TOUCH ───────────────────────────────────────
# Grants are one-shot and IP-bound: first use binds the phrase's label to
# the VIP's IP; a different IP burns the grant (KILL_IP). Don't "simplify"
# this into multi-use phrases or IP-less sessions — that's the whole lock.
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
        self.phrases = load_viplist(args.viplist)   # label -> (salt, dk)
        if not self.phrases:
            sys.exit("error: no usable phrases in the VIP list (fail closed)")
        self.grants = {}    # label -> {"ip": str, "expires": int}
        self.burned = set()  # labels whose one-shot phrase is spent
        self.attempts = {}  # ip -> [timestamps]
        self.lock = threading.Lock()
        self.audit_path = args.audit_log
        self.attempt_log = args.attempt_log

    def audit(self, event, label="-", ip="-"):
        line = "[bouncer] %s %-10s label=%s ip=%s" % (
            time.strftime("%Y-%m-%dT%H:%M:%S"), event, label, ip)
        print(line, flush=True)
        if self.audit_path:
            with open(self.audit_path, "a") as f:
                f.write(line + "\n")


# ── SETUP + CORE ─────────────────────────────────────────────
# SETUP: viplist.txt is one "label phrase" per line (# = comment).
# CORE: phrases are hashed with a fresh salt at startup and compared in
# constant time. Never store or compare plaintext, and never echo which
# label was tried — that tells an attacker which labels exist.
# ────────────────────────────────────────────────────────────
def load_viplist(path):
    """Read the VIP list: 'label phrase' per line, # comments ignored."""
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
        parts = line.split(None, 1)
        if len(parts) != 2:
            sys.exit("error: VIP list line %d: need 'label phrase'" % lineno)
        label, phrase = parts
        if label in phrases:
            sys.exit("error: VIP list line %d: duplicate label '%s'" % (lineno, label))
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        phrases[label] = (salt, dk)
    return phrases


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
        html = GATE_HTML.format(msg=msg).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(html)

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
                st.burned.add(label)
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
                st.burned.add(label)
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
        if self.authed_label():
            self.serve_behind_rope()
        else:
            self.serve_gate()

    # ── CORE: DO NOT TOUCH ───────────────────────────────────
    # The grant ceremony: verify the phrase (constant-time), sign a cookie
    # bound to label+IP+expiry, burn the grant on IP mismatch. Don't log the
    # phrase, don't accept it via GET (URLs end up in logs), don't skip the
    # burn. The attempt logger records metadata only — keep it that way.
    # ────────────────────────────────────────────────────────
    def do_POST(self):
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
        with st.lock:
            for label, (salt, dk) in st.phrases.items():
                if label in st.grants or label in st.burned:
                    continue
                test = hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"), salt, PBKDF2_ITERATIONS)
                if hmac.compare_digest(dk, test):
                    matched = label
                    break
            if matched:
                expires = int(time.time()) + st.ttl
                st.grants[matched] = {"ip": ip, "expires": expires}
                cookie = sign_cookie(st, matched, ip, expires)
        if matched:
            st.audit("GRANT", matched, ip)
            self.log_attempt("granted", matched)
            self.send_response(302)
            self.send_header("Set-Cookie",
                             "%s=%s; Path=/; HttpOnly; Secure; SameSite=Lax" % (COOKIE_NAME, cookie))
            self.send_header("Location", "/")
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
    ap = argparse.ArgumentParser(description="BOUNCER — put a bouncer on your tunnel.")
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
    cli = ap.parse_args()

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
    if not args.viplist:
        sys.exit("error: no VIP list — set VIPLIST in bouncer.conf or pass --viplist")

    state = BouncerState(args)
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    server.state = state
    server.daemon_threads = True
    dest = args.serve if state.mode == "serve" else args.target
    print("[bouncer] 🌀 live on %s:%d -> %s | mode=%s ttl=%ds | phrases=%d | one-shot grants"
          % (args.bind, args.port, dest, state.mode, args.ttl, len(state.phrases)), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bouncer] last call. all grants wiped.", flush=True)


if __name__ == "__main__":
    main()
