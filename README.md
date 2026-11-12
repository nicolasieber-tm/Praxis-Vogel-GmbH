# Praxis Vogel GmbH – Webseite

Statische Webseite (HTML/CSS/JS, keine Abhängigkeiten) für die Praxis Luca Vogel, Bettlach.
Design gemäss Kickoff-Briefing: Palette «Terracotta», Inter (lokal eingebunden), warm-hell, Ansprache «Sie».
Mobile First, SEO-optimiert (Lighthouse Mobile: 99–100 in Performance, SEO, Barrierefreiheit, Best Practices).

## Struktur
- `_src/layout.html` – `<head>` (Meta, Open Graph, LocalBusiness-Schema), Header, Footer
- `_src/pages/*.html` – Seiteninhalte (Kopfzeilen: `title`, `description`, `nav`, `crumb`, `robots`, `priority`, `preload`)
- `build.py` – erzeugt die Seiten mit sauberen URLs (`/angebot/index.html`), `sitemap.xml`, `robots.txt`
- `assets/css/style.css` – Design-System, Mobile First (Farb-Tokens oben in `:root`)
- `assets/js/main.js` – Mobile-Menü, Einblend-Animation, Kontaktformular
- `.htaccess` – HTTPS, 301-Weiterleitungen der alten URLs, Caching, Komprimierung (Apache)

**Inhalte immer in `_src/` ändern und danach `python3 build.py` ausführen.** Die generierten Dateien werden überschrieben.

## Lokal ansehen
```
python3 -m http.server 8000
```
→ http://localhost:8000 (die Seite nutzt Root-Pfade wie `/assets/…`, daher über einen Server öffnen, nicht per Doppelklick)

## SEO-Massnahmen
- Saubere URLs, identisch zur alten Seite (`/angebot/`, `/kontakt/` …); `/über-mich` → 301 auf `/ueber-mich/`
- Individuelle Titles (≤ 60 Zeichen) und Meta-Descriptions (≤ 156 Zeichen) mit lokalen Keywords
- Strukturierte Daten: LocalBusiness/ProfessionalService, Service (mit Preisen), FAQPage, ProfilePage/Person, BreadcrumbList, ContactPage
- Sitemap, robots.txt, Canonicals, Open Graph inkl. 1200×630-Bild
- Impressum/Datenschutz/404 auf `noindex, follow`
- Responsive WebP-Bilder mit `srcset`, LCP-Bild vorgeladen, Fonts lokal + metrisch angepasster Fallback (CLS 0)

## Vor dem Livegang
- [ ] Kontaktformular: Endpoint in `_src/pages/kontakt.html` bei `data-endpoint` eintragen (z. B. Formspree/Web3Forms/PHP). Ohne Endpoint öffnet sich das E-Mail-Programm.
- [ ] Impressum: UID-Nummer ergänzen
- [ ] Datenschutzerklärung rechtlich prüfen
- [ ] Einzugsgebiet bestätigen (aktuell: Bettlach, Grenchen, Solothurn, Kanton Solothurn – im Schema und in Texten)
- [ ] Adresse bestätigen: alte Seite schreibt teils «Kastelweg», teils «Kastelsweg»
- [ ] Dave Vogel: Foto, Ausbildung/Abschluss, Werdegang und Schwerpunkte ergänzen (`_src/pages/ueber-uns.html` und Team-Karte in `_src/pages/index.html`, mit `TODO` markiert)
- [ ] Logo lautet «Praxis Luca Vogel» – mit zwei Fachpersonen ggf. auf «Praxis Vogel» anpassen lassen
- [ ] Weitere eigene Fotos einbauen; Logo als SVG anfragen
- [ ] Nach dem Livegang: Google Search Console einrichten, Sitemap einreichen, Google-Unternehmensprofil (Maps) anlegen bzw. aktualisieren
