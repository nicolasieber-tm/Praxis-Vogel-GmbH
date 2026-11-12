/* Praxis Vogel GmbH – kleine Helfer (Navigation, Header, Reveal, Kontaktformular) */
(function () {

  // Mobile Navigation
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("hauptnavigation");
  if (toggle && nav) {
    var setOpen = function (open) {
      toggle.setAttribute("aria-expanded", String(open));
      toggle.querySelector(".visually-hidden").textContent = open ? "Menü schliessen" : "Menü öffnen";
      nav.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
    };
    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) setOpen(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) { setOpen(false); toggle.focus(); }
    });
    window.matchMedia("(min-width: 1000px)").addEventListener("change", function (mq) {
      if (mq.matches) setOpen(false);
    });
  }

  // Header-Linie beim Scrollen
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () { header.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Google Maps erst nach Klick laden (Zwei-Klick-Lösung)
  document.querySelectorAll("[data-map]").forEach(function (map) {
    var btn = map.querySelector("[data-map-load]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var iframe = document.createElement("iframe");
      iframe.src = map.getAttribute("data-src");
      iframe.title = "Karte: Praxis Vogel GmbH, Kastelweg 6, 2544 Bettlach";
      iframe.loading = "lazy";
      iframe.referrerPolicy = "no-referrer-when-downgrade";
      iframe.setAttribute("allowfullscreen", "");
      map.innerHTML = "";
      map.appendChild(iframe);
      iframe.focus();
    });
  });

  // Jahr im Footer
  document.querySelectorAll("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  // Kontaktformular
  // Ist data-endpoint gesetzt (z. B. Formspree / Web3Forms / eigenes PHP), wird per fetch gesendet.
  // Ohne Endpoint öffnet sich das E-Mail-Programm mit vorausgefüllter Nachricht (Fallback).
  var form = document.querySelector("[data-contact-form]");
  if (form) {
    var status = form.querySelector(".form__status");
    var show = function (msg, ok) {
      status.textContent = msg;
      status.className = "form__status " + (ok ? "form__status--ok" : "form__status--err");
      status.hidden = false;
    };

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }

      var data = new FormData(form);
      if (data.get("website")) return; // Honeypot

      var endpoint = form.getAttribute("data-endpoint");
      var btn = form.querySelector("button[type=submit]");

      if (!endpoint) {
        var to = form.getAttribute("data-mailto");
        var subject = "Anfrage über die Webseite: " + (data.get("anliegen") || "Allgemein");
        var body =
          "Name: " + data.get("name") + "\n" +
          "E-Mail: " + data.get("email") + "\n" +
          "Telefon: " + (data.get("telefon") || "–") + "\n" +
          "Ich bin: " + (data.get("rolle") || "–") + "\n" +
          "Anliegen: " + (data.get("anliegen") || "–") + "\n\n" +
          data.get("nachricht");
        window.location.href = "mailto:" + to + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
        show("Ihr E-Mail-Programm wurde geöffnet. Bitte senden Sie die vorbereitete Nachricht ab.", true);
        return;
      }

      btn.disabled = true;
      fetch(endpoint, { method: "POST", body: data, headers: { Accept: "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error();
          form.reset();
          show("Vielen Dank für Ihre Nachricht. Wir melden uns so schnell wie möglich bei Ihnen.", true);
        })
        .catch(function () {
          show("Leider ist etwas schiefgelaufen. Bitte rufen Sie uns an: 078 731 76 78.", false);
        })
        .finally(function () { btn.disabled = false; });
    });
  }
})();
