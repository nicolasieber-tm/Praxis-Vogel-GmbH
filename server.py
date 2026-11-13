#!/usr/bin/env python3
"""
Webserver der Praxis Vogel GmbH (Railway). Keine Abhängigkeiten, nur Python-Standardbibliothek.

  python3 server.py            -> http://localhost:8000

Aufgaben:
  - liefert die mit build.py erzeugten Seiten aus (Caching, gzip, Sicherheits-Header, 404-Seite)
  - leitet alte URLs der bisherigen Webseite per 301 weiter
  - nimmt das Kontaktformular entgegen (POST /anfrage) und sendet die Anfrage über Resend per E-Mail

Umgebungsvariablen (in Railway unter "Variables"):
  RESEND_API_KEY      API-Schlüssel von resend.com (ohne ihn wird nichts versendet)
  KONTAKT_EMPFAENGER  Empfänger der Anfragen, mehrere mit Komma getrennt (Standard: praxis-vogel@gmx.ch)
  KONTAKT_ABSENDER    Absender, Domain muss bei Resend bestätigt sein
                      (Standard: Webseite Praxis Vogel <webseite@praxis-vogel.net>)
  PORT                wird von Railway gesetzt
"""
import gzip
import json
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent.resolve()
SITE_HOST = "praxis-vogel.net"

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
EMPFAENGER = [a.strip() for a in os.environ.get("KONTAKT_EMPFAENGER", "praxis-vogel@gmx.ch").split(",") if a.strip()]
ABSENDER = os.environ.get("KONTAKT_ABSENDER", "Webseite Praxis Vogel <webseite@praxis-vogel.net>").strip()

ROLLEN = ["Elternteil / Angehörige:r", "Jugendliche:r", "Behörde / Fachstelle", "Andere"]
ANLIEGEN = ["Familienbegleitung", "Coaching für Jugendliche", "Ich bin noch unsicher"]

# Nur diese Dateitypen werden ausgeliefert (Quellen, Skripte, Konfiguration bleiben privat)
ERLAUBT = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".pdf": "application/pdf",
    ".webmanifest": "application/manifest+json",
}
KOMPRIMIEREN = {".html", ".css", ".js", ".xml", ".txt", ".svg"}
CACHE = {
    ".html": "no-cache",
    ".css": "public, max-age=2592000",
    ".js": "public, max-age=2592000",
}
CACHE_LANG = "public, max-age=31536000"

SICHERHEIT = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=31536000",
}

# Alte URLs der bisherigen Webseite -> neue URLs (Rankings erhalten)
ALT_UEBER_MICH = re.compile(r"^/(über-mich|ueber-mich)(/|\.html)?$", re.I)
SEITE_HTML = re.compile(r"^/([a-z0-9-]+)\.html$")

# Einfaches Limit gegen Formular-Spam: max. 5 Anfragen pro IP in 10 Minuten
_limit = {}
_limit_lock = threading.Lock()


def zu_viele(ip):
    jetzt = time.time()
    with _limit_lock:
        liste = [t for t in _limit.get(ip, []) if jetzt - t < 600]
        liste.append(jetzt)
        _limit[ip] = liste
        if len(_limit) > 5000:
            _limit.clear()
        return len(liste) > 5


def log(*teile):
    print(*teile, file=sys.stderr, flush=True)


def bereinigen(wert, max_len, einzeilig=True):
    wert = (wert or "").strip()
    wert = "".join(c for c in wert if c in "\n\t" or (ord(c) >= 32 and ord(c) != 127))
    if einzeilig:
        wert = re.sub(r"\s+", " ", wert)
    return wert[:max_len]


EMAIL_RE = re.compile(r"^[^@\s<>,;\"]+@[^@\s<>,;\"]+\.[a-zA-Z]{2,}$")


def anfrage_senden(felder):
    """Prüft die Felder und sendet die E-Mail. Gibt (ok, fehlercode) zurück."""
    if felder.get("website"):
        return True, ""  # Honeypot ausgefüllt: still ignorieren

    name = bereinigen(felder.get("name"), 120)
    email = bereinigen(felder.get("email"), 200)
    telefon = bereinigen(felder.get("telefon"), 40)
    rolle = bereinigen(felder.get("rolle"), 60)
    anliegen = bereinigen(felder.get("anliegen"), 60)
    nachricht = bereinigen(felder.get("nachricht"), 5000, einzeilig=False)

    if rolle not in ROLLEN:
        rolle = "Andere"
    if anliegen not in ANLIEGEN:
        anliegen = "Ich bin noch unsicher"
    if not name or not nachricht or not felder.get("datenschutz") or not EMAIL_RE.match(email):
        return False, "eingabe"

    if not RESEND_API_KEY:
        log("FEHLER: RESEND_API_KEY ist nicht gesetzt, Anfrage nicht versendet.")
        return False, "versand"

    datum = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%d.%m.%Y, %H:%M")
    linie = "-" * 40
    text = (
        "Neue Anfrage über das Kontaktformular auf praxis-vogel.net\n"
        f"Eingegangen am {datum} Uhr\n\n"
        f"Name:          {name}\n"
        f"E-Mail:        {email}\n"
        f"Telefon:       {telefon or '–'}\n"
        f"Ich bin:       {rolle}\n"
        f"Interesse an:  {anliegen}\n\n"
        f"Nachricht:\n{linie}\n{nachricht}\n{linie}\n\n"
        f"Mit «Antworten» geht die E-Mail direkt an {name}.\n"
    )
    payload = {
        "from": ABSENDER,
        "to": EMPFAENGER,
        "reply_to": email,
        "subject": f"Neue Anfrage über die Webseite: {anliegen} ({name})",
        "text": text,
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "praxis-vogel-webseite/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            antwort = json.loads(r.read() or b"{}")
            log("Anfrage versendet, Resend-ID:", antwort.get("id"))
            return True, ""
    except urllib.error.HTTPError as e:
        log("FEHLER Resend", e.code, e.read()[:500].decode("utf-8", "replace"))
    except Exception as e:  # Netzwerkfehler, Timeout
        log("FEHLER Resend", repr(e))
    return False, "versand"


class Handler(BaseHTTPRequestHandler):
    server_version = "PraxisVogel"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # ---- Hilfen -----------------------------------------------------------
    def senden(self, status, body=b"", headers=None, head_only=False):
        self.send_response(status)
        for k, v in SICHERHEIT.items():
            self.send_header(k, v)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body and not head_only:
            self.wfile.write(body)

    def weiterleiten(self, ziel, status=301):
        self.senden(status, headers={"Location": ziel, "Cache-Control": "no-cache" if status != 301 else "public, max-age=86400"})

    def client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() if fwd else self.client_address[0]

    def log_message(self, fmt, *args):
        if self.command == "POST" or not str(args[1] if len(args) > 1 else "").startswith(("2", "3")):
            log(f"{self.client_ip()} {fmt % args}")

    def datei(self, pfad, status=200, head_only=False):
        endung = pfad.suffix.lower()
        body = pfad.read_bytes()
        headers = {
            "Content-Type": ERLAUBT[endung],
            "Cache-Control": CACHE.get(endung, CACHE_LANG),
            "Last-Modified": formatdate(pfad.stat().st_mtime, usegmt=True),
            "Vary": "Accept-Encoding",
        }
        if endung in KOMPRIMIEREN and "gzip" in self.headers.get("Accept-Encoding", "") and len(body) > 1024:
            body = gzip.compress(body, 6)
            headers["Content-Encoding"] = "gzip"
        self.senden(status, body, headers, head_only)

    def nicht_gefunden(self, head_only=False):
        self.datei(ROOT / "404.html", 404, head_only)

    # ---- GET / HEAD -----------------------------------------------------------
    def do_HEAD(self):
        self.do_GET(head_only=True)

    def do_GET(self, head_only=False):
        host = (self.headers.get("Host") or "").lower()
        teile = urllib.parse.urlsplit(self.path)
        query = f"?{teile.query}" if teile.query else ""
        if host.startswith("www."):
            return self.weiterleiten(f"https://{host[4:]}{teile.path}{query}")

        pfad = urllib.parse.unquote(teile.path)
        if pfad == "/healthz":
            return self.senden(200, b"ok", {"Content-Type": "text/plain"}, head_only)
        if ALT_UEBER_MICH.match(pfad):
            return self.weiterleiten("/ueber-uns/")
        if pfad == "/index.html":
            return self.weiterleiten("/" + query)
        m = SEITE_HTML.match(pfad)
        if m and m.group(1) != "404" and (ROOT / m.group(1) / "index.html").is_file():
            return self.weiterleiten(f"/{m.group(1)}/{query}")

        # Keine versteckten oder internen Dateien (.git, _src, …)
        segmente = [s for s in pfad.split("/") if s]
        if any(s.startswith((".", "_")) or s == ".." for s in segmente):
            return self.nicht_gefunden(head_only)

        ziel = (ROOT / "/".join(segmente)).resolve()
        if ROOT not in ziel.parents and ziel != ROOT:
            return self.nicht_gefunden(head_only)
        if ziel.is_dir():
            if not pfad.endswith("/"):
                return self.weiterleiten(f"{pfad}/{query}")
            ziel = ziel / "index.html"
        if ziel.is_file() and ziel.suffix.lower() in ERLAUBT and ziel.name != "404.html":
            return self.datei(ziel, head_only=head_only)
        return self.nicht_gefunden(head_only)

    # ---- POST /anfrage ----------------------------------------------------------
    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/anfrage":
            return self.senden(405, b"", {"Allow": "GET, HEAD"})

        json_gewuenscht = "application/json" in self.headers.get("Accept", "")

        def antwort(ok, fehler=""):
            if json_gewuenscht:
                body = json.dumps({"ok": ok, "fehler": fehler}).encode()
                code = 200 if ok else {"eingabe": 422, "limit": 429}.get(fehler, 502)
                return self.senden(code, body, {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"})
            return self.weiterleiten("/danke/" if ok else "/kontakt/?fehler=1#anfrage", 303)

        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > 64_000:
            return antwort(False, "eingabe")
        roh = self.rfile.read(laenge)

        art = self.headers.get("Content-Type", "")
        if art.startswith("multipart/form-data"):
            felder = multipart_lesen(roh, art)
        else:
            felder = {k: v[0] for k, v in urllib.parse.parse_qs(roh.decode("utf-8", "replace")).items()}

        if zu_viele(self.client_ip()):
            return antwort(False, "limit")
        ok, fehler = anfrage_senden(felder)
        return antwort(ok, fehler)


def multipart_lesen(roh, content_type):
    """Liest einfache Textfelder aus multipart/form-data (so sendet fetch() mit FormData)."""
    from email.parser import BytesParser
    from email.policy import HTTP

    nachricht = BytesParser(policy=HTTP).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\n\r\n" + roh
    )
    felder = {}
    if nachricht.is_multipart():
        for teil in nachricht.iter_parts():
            name = teil.get_param("name", header="content-disposition")
            if name and not teil.get_filename():
                felder[name] = teil.get_payload(decode=True).decode("utf-8", "replace")
    return felder


def main():
    mimetypes.init()
    port = int(os.environ.get("PORT", "8000"))
    if not RESEND_API_KEY:
        log("Hinweis: RESEND_API_KEY fehlt, das Kontaktformular kann keine E-Mails senden.")
    log(f"Praxis Vogel Webseite läuft auf Port {port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
