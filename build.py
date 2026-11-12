#!/usr/bin/env python3
"""
Statischer Seiten-Generator für die Praxis Vogel GmbH.

  python3 build.py

Liest _src/layout.html (Head, Header, Footer) und _src/pages/*.html (Inhalte)
und schreibt fertige Seiten mit sauberen URLs:
  _src/pages/index.html    -> /index.html          (https://praxis-vogel.net/)
  _src/pages/angebot.html  -> /angebot/index.html  (https://praxis-vogel.net/angebot/)
  _src/pages/404.html      -> /404.html
Zusätzlich: sitemap.xml und robots.txt. Keine Abhängigkeiten.

Kopfzeilen einer Seite (bis zur ersten Leerzeile):
  title:       <title>, max. ~60 Zeichen
  description: Meta-Description, max. ~155 Zeichen
  nav:         aktiver Menüpunkt (Slug) oder leer
  crumb:       Name in der Breadcrumb (strukturierte Daten)
  robots:      z. B. "noindex, follow" (Standard: index, follow)
  priority:    Sitemap-Priorität (Standard 0.7)
  preload:     Bildname, der als LCP-Bild vorgeladen wird (optional)
  contact_end: "no" blendet den Kontakt-Abschluss (_src/partials/contact-end.html) aus

Platzhalter im Inhalt:
  {{icon:name}}
  {{picture:basis|Alt-Text|CSS-Klasse|sizes|eager}}   (eager optional)
"""
from datetime import date
from pathlib import Path
import hashlib
import html as htmllib
import json
import re

ROOT = Path(__file__).parent
SRC = ROOT / "_src"
SITE = "https://praxis-vogel.net"

NAV = [
    ("angebot", "Angebot"),
    ("vorgehen", "Vorgehen &amp; Kosten"),
    ("ueber-uns", "Über uns"),
    ("partner", "Partner"),
    ("kontakt", "Kontakt"),
]

# Verfügbare Bildgrössen (WebP) + JPG-Fallback, Seitenverhältnis 4:5 bzw. 1200x630
IMAGES = {
    "luca-vogel-beratung": {"widths": [480, 720, 960, 1280], "fallback": 720, "ratio": (4, 5)},
    "luca-vogel-gespraech": {"widths": [720, 1200], "fallback": 1200, "ratio": (40, 21)},
    "luca-vogel-portrait": {"widths": [480, 720, 960], "fallback": 720, "ratio": (4, 5)},
}

_S = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"'
ICONS = {
    "phone": f'<svg {_S}><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>',
    "mail": f'<svg {_S}><rect x="2.5" y="4.5" width="19" height="15" rx="2.5"/><path d="M3 7l9 6 9-6"/></svg>',
    "pin": f'<svg {_S}><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "arrow": f'<svg {_S}><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "family": f'<svg {_S}><circle cx="8" cy="6.5" r="2.5"/><circle cx="16.5" cy="8" r="2"/><path d="M3.5 20v-3.5A4.5 4.5 0 0 1 8 12a4.5 4.5 0 0 1 4.5 4.5V20"/><path d="M14 20v-3a3 3 0 0 1 6 0v3"/></svg>',
    "compass": f'<svg {_S}><circle cx="12" cy="12" r="9.5"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/></svg>',
    "heart": f'<svg {_S}><path d="M19.5 13.6L12 21l-7.5-7.4A5 5 0 0 1 12 6.6a5 5 0 0 1 7.5 7z"/></svg>',
    "shield": f'<svg {_S}><path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>',
    "award": f'<svg {_S}><circle cx="12" cy="9" r="6"/><path d="M8.5 14L7 22l5-3 5 3-1.5-8"/></svg>',
    "calendar": f'<svg {_S}><rect x="3" y="4.5" width="18" height="17" rx="2.5"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/></svg>',
    "info": f'<svg {_S}><circle cx="12" cy="12" r="9.5"/><path d="M12 11v6M12 7.5v.01"/></svg>',
    "plus": f'<svg {_S}><path d="M12 5v14M5 12h14"/></svg>',
    "quote": '<svg viewBox="0 0 40 40" fill="currentColor" aria-hidden="true" focusable="false"><path d="M7 30c-2-2-3-4.5-3-7.6 0-5.3 3.7-10.1 9.2-12.6l1.3 2c-5.1 2.8-6.1 6.4-6.5 8.6.8-.4 1.9-.6 3-.5 2.9.3 5.1 2.7 5.1 5.6a5.6 5.6 0 0 1-9.1 4.5zm17 0c-2-2-3-4.5-3-7.6 0-5.3 3.7-10.1 9.2-12.6l1.3 2c-5.1 2.8-6.1 6.4-6.5 8.6.8-.4 1.9-.6 3-.5 2.9.3 5.1 2.7 5.1 5.6A5.6 5.6 0 0 1 24 30z"/></svg>',
    "users": f'<svg {_S}><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20.5a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14.2a6.5 6.5 0 0 1 3 6.3"/></svg>',
    "external": f'<svg {_S}><path d="M14 4h6v6M20 4l-9 9M18 14v5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 19V7.5A1.5 1.5 0 0 1 5.5 6H10"/></svg>',
}


def asset_version(path: str) -> str:
    """Kurzer Hash des Dateiinhalts – ändert sich bei jeder Änderung (Cache-Busting)."""
    return hashlib.md5((ROOT / path.lstrip("/")).read_bytes()).hexdigest()[:8]


def url_for(slug: str) -> str:
    return "/" if slug == "index" else f"/{slug}/"


def picture(base, alt, cls="", sizes="100vw", eager=""):
    img = IMAGES[base]
    rw, rh = img["ratio"]
    fb = img["fallback"]
    srcset = ", ".join(f"/assets/img/{base}-{w}.webp {w}w" for w in img["widths"])
    loading = 'fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
    return (
        f'<picture><source type="image/webp" srcset="{srcset}" sizes="{sizes}">'
        f'<img class="{cls}" src="/assets/img/{base}-{fb}.jpg" width="{fb}" height="{round(fb * rh / rw)}" '
        f'alt="{alt}" {loading}></picture>'
    )


def render_placeholders(text: str) -> str:
    # Letztes Wort + Icon in Text-Links zusammenhalten (kein einsamer Pfeil auf neuer Zeile)
    text = re.sub(
        r'(class="text-link"[^>]*>[^<]*?)(\S+)((?: <span class="visually-hidden">[^<]*</span>)?) ?(\{\{icon:(?:arrow|external)\}\})',
        r'\1<span class="nowrap">\2\3\4</span>',
        text,
    )
    text = re.sub(r"\{\{icon:([a-z-]+)\}\}", lambda m: ICONS[m.group(1)], text)
    text = re.sub(r"\{\{picture:([^}]+)\}\}", lambda m: picture(*m.group(1).split("|")), text)
    return text


def parse(page: Path):
    raw = page.read_text(encoding="utf-8")
    head, _, body = raw.partition("\n\n")
    meta = {}
    for line in head.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def breadcrumb(slug, crumb):
    if slug in ("index", "404"):
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Startseite", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": crumb, "item": SITE + url_for(slug)},
        ],
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def preload_tag(base):
    if not base:
        return ""
    img = IMAGES[base]
    srcset = ", ".join(f"/assets/img/{base}-{w}.webp {w}w" for w in img["widths"])
    return (
        f'<link rel="preload" as="image" type="image/webp" imagesrcset="{srcset}" '
        f'imagesizes="(min-width: 900px) 50vw, 100vw" fetchpriority="high">'
    )


def build():
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    for asset in ("/assets/css/style.css", "/assets/js/main.js"):
        layout = layout.replace(f'"{asset}"', f'"{asset}?v={asset_version(asset)}"')
    contact_end = (SRC / "partials" / "contact-end.html").read_text(encoding="utf-8").rstrip()
    sitemap = []
    today = date.today().isoformat()

    for page in sorted((SRC / "pages").glob("*.html")):
        meta, body = parse(page)
        slug = page.stem
        active = meta.get("nav", "")
        robots = meta.get("robots", "index, follow, max-image-preview:large")
        canonical = SITE + url_for(slug)

        nav = "\n          ".join(
            f'<li><a class="nav__link" href="{url_for(key)}"'
            + (' aria-current="page"' if key == active else "")
            + f">{label}</a></li>"
            for key, label in NAV
        )
        html = (
            layout.replace("{{title}}", htmllib.escape(meta["title"]))
            .replace("{{description}}", htmllib.escape(meta["description"]))
            .replace("{{canonical}}", canonical)
            .replace("{{robots}}", robots)
            .replace("{{preload}}", preload_tag(meta.get("preload", "")))
            .replace("{{breadcrumb}}", breadcrumb(slug, meta.get("crumb", "")))
            .replace("{{body_class}}", f"page-{slug}")
            .replace("{{nav}}", nav)
            .replace("{{content}}", body.rstrip())
            .replace("{{contact_end}}", "" if meta.get("contact_end") == "no" else contact_end)
        )
        html = render_placeholders(html)

        if slug in ("index", "404"):
            out = ROOT / f"{slug}.html"
        else:
            (ROOT / slug).mkdir(exist_ok=True)
            out = ROOT / slug / "index.html"
        out.write_text(html, encoding="utf-8")
        print("✓", out.relative_to(ROOT))

        if slug != "404" and "noindex" not in robots:
            sitemap.append((canonical, meta.get("priority", "0.7")))

    # Alte Dateien aus der ersten Version entfernen (angebot.html usw.)
    for key in [k for k, _ in NAV] + ["impressum", "datenschutz"]:
        old = ROOT / f"{key}.html"
        if old.exists():
            old.unlink()

    urls = "\n".join(
        f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod><priority>{prio}</priority></url>"
        for loc, prio in sitemap
    )
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n",
        encoding="utf-8",
    )
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nDisallow: /_src/\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8"
    )
    print("✓ sitemap.xml, robots.txt")


if __name__ == "__main__":
    build()
