#!/usr/bin/env python3
"""Serve the Let's Drive Go page and save waitlist sign-ups to waitlist.csv.

Only the page and the images folder are served. waitlist.csv, this script and
everything else in the folder stay private.

Run:  python3 server.py          (listens on http://127.0.0.1:8765)
Share: cloudflared tunnel --url http://127.0.0.1:8765
"""
import csv
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "lets-drive-go.html")
IMAGES = os.path.join(HERE, "images")
CSV_PATH = os.path.join(HERE, "waitlist.csv")
PORT = int(os.environ.get("PORT", "8765"))

ROLES = {"learner", "instructor", "driver", "client"}
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
IMAGE_RE = re.compile(r"^/images/([A-Za-z0-9_-]+\.(jpg|jpeg|png|webp|svg))$")
TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "svg": "image/svg+xml"}
HEAD = (
    b'<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
    b'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    b"</head><body>\n"
)

lock = threading.Lock()
recent = {}  # ip -> list of submit times, for a simple rate limit


def clean(value, limit):
    value = str(value or "").strip()[:limit]
    # Stop spreadsheet apps treating a value as a formula.
    if value[:1] in ("=", "+", "-", "@"):
        value = "'" + value
    return value


class Handler(BaseHTTPRequestHandler):
    server_version = "LetsDriveGo"

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def send(self, code, body, ctype="text/plain; charset=utf-8", cache=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "public, max-age=3600" if cache else "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/lets-drive-go.html"):
            with open(PAGE, "rb") as f:
                return self.send(200, HEAD + f.read() + b"\n</body></html>", "text/html; charset=utf-8")
        m = IMAGE_RE.match(path)
        if m:
            file_path = os.path.join(IMAGES, m.group(1))
            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    return self.send(200, f.read(), TYPES[m.group(2).lower()], cache=True)
        self.send(404, b"Not found")

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/waitlist":
            return self.send(404, b"Not found")
        ip = self.headers.get("CF-Connecting-IP") or self.client_address[0]
        now = time.time()
        with lock:
            hits = [t for t in recent.get(ip, []) if now - t < 600]
            if len(hits) >= 10:
                return self.send(429, b'{"error":"too_many"}', "application/json")
            hits.append(now)
            recent[ip] = hits
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 4096:
                raise ValueError("size")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self.send(400, b'{"error":"bad_request"}', "application/json")

        role = str(data.get("role") or "")
        name = clean(data.get("name"), 60)
        email = str(data.get("email") or "").strip()[:120]
        postcode = clean(data.get("postcode"), 10).upper()
        if role not in ROLES or not name or not postcode or not EMAIL_RE.match(email):
            return self.send(400, b'{"error":"invalid"}', "application/json")

        row = [datetime.now(timezone.utc).isoformat(timespec="seconds"), role, name, clean(email, 120), postcode]
        with lock:
            new_file = not os.path.exists(CSV_PATH)
            with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow(["joined_utc", "role", "name", "email", "postcode"])
                w.writerow(row)
        print("New sign-up saved (%s)" % role, flush=True)
        self.send(200, b'{"ok":true}', "application/json")


if __name__ == "__main__":
    print("Serving on http://127.0.0.1:%d — sign-ups go to %s" % (PORT, CSV_PATH), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
