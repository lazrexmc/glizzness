/* The Glizzness — shared site behavior.
   Progressive enhancement only: every page works without JS (the form falls back
   to call/text/email). Reads constants from config.js. */
(function () {
  "use strict";

  var phone = window.GLIZZNESS_PHONE || "";
  var email = window.GLIZZNESS_EMAIL || "";
  var dd    = window.GLIZZNESS_DOORDASH || "";
  var telHref = phone ? "tel:" + phone.replace(/[^0-9+]/g, "") : "";
  var ddSet = dd && dd.indexOf("PASTE_YOUR") === -1;

  /* ---- Mobile nav toggle ---- */
  var toggle = document.querySelector(".nav__toggle");
  var links  = document.querySelector(".nav__links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { links.classList.remove("is-open"); toggle.setAttribute("aria-expanded", "false"); });
    });
  }

  /* ---- Nav shadow on scroll ---- */
  var nav = document.querySelector(".nav");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---- Contact / order buttons (tel, sms, mailto pre-filled, DoorDash) ---- */
  var tmpl = "Hi Glizzness! I'd like to ask about catering / booking.\n\n" +
             "Name:\nEvent date:\nGuests:\nPackage:\nLocation:\nDetails:";
  var enc = encodeURIComponent(tmpl);
  var smsHref  = phone ? "sms:" + phone.replace(/[^0-9+]/g, "") + "?&body=" + enc : "";
  var mailHref = email ? "mailto:" + email + "?subject=" + encodeURIComponent("Catering / booking — The Glizzness") + "&body=" + enc : "";

  function wire(sel, href) {
    document.querySelectorAll(sel).forEach(function (el) {
      if (href) { el.setAttribute("href", href); el.hidden = false; }
      else { el.hidden = true; }
    });
  }
  wire(".js-call", telHref);
  wire(".js-text", smsHref);
  wire(".js-email", mailHref);
  wire(".js-doordash", ddSet ? dd : "");

  /* Plain phone/email text targets */
  document.querySelectorAll(".js-phone-text").forEach(function (el) { if (phone) el.textContent = phone; });
  document.querySelectorAll(".js-phone-link").forEach(function (el) { if (phone) { el.href = telHref; if (!el.textContent.trim()) el.textContent = phone; } });
  document.querySelectorAll(".js-email-text").forEach(function (el) { if (email) el.textContent = email; });
  document.querySelectorAll(".js-email-link").forEach(function (el) { if (email) { el.href = "mailto:" + email; if (!el.textContent.trim()) el.textContent = email; } });

  /* Social links (hide when unset) */
  document.querySelectorAll(".js-fb").forEach(function (el) { var u = window.GLIZZNESS_FACEBOOK; if (u) { el.href = u; } else { el.hidden = true; } });
  document.querySelectorAll(".js-ig").forEach(function (el) { var u = window.GLIZZNESS_INSTAGRAM; if (u) { el.href = u; } else { el.hidden = true; } });

  /* ---- "Request this package" -> preselect + scroll to form ---- */
  var pkgSelect = document.getElementById("f-package");
  document.querySelectorAll(".pkg-btn").forEach(function (b) {
    b.addEventListener("click", function () {
      var p = b.getAttribute("data-package");
      if (pkgSelect) {
        for (var i = 0; i < pkgSelect.options.length; i++) {
          if (pkgSelect.options[i].value === p) { pkgSelect.selectedIndex = i; break; }
        }
      }
      var book = document.getElementById("book");
      if (book) {
        book.scrollIntoView({ behavior: "smooth" });
        setTimeout(function () { var n = document.getElementById("f-name"); if (n) n.focus(); }, 350);
      }
    });
  });

  /* ---- Booking form -> Supabase insert (anon insert-only) ---- */
  var form   = document.getElementById("book-form");
  var status = document.getElementById("book-status");
  var submit = document.getElementById("book-submit");
  if (form && status && submit) {
    var U = window.SUPABASE_URL, K = window.SUPABASE_ANON_KEY;
    var val = function (id) { var el = document.getElementById(id); return el ? (el.value || "").trim() : ""; };

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      status.className = "book__status"; status.textContent = "";

      if (!val("f-name") || !val("f-phone")) {
        status.className = "book__status err";
        status.textContent = "Add at least your name and a phone number so we can reach you.";
        return;
      }
      if (!U || !K || K.indexOf("PASTE_YOUR") !== -1) {
        status.className = "book__status err";
        status.innerHTML = "Booking isn't wired up yet — call or text " + (phone ? "<a href='" + telHref + "'>" + phone + "</a>" : "us") + " and we'll get you on the calendar.";
        return;
      }

      var data = {
        name: val("f-name"), phone: val("f-phone"), email: val("f-email") || null,
        event_date: val("f-date") || null,
        guest_count: val("f-guests") ? Number(val("f-guests")) : null,
        package: pkgSelect ? pkgSelect.value : null,
        location: val("f-location") || null,
        message: val("f-message") || null,
        source: form.getAttribute("data-source") || "site_catering"
      };

      submit.disabled = true; submit.textContent = "Sending…";
      fetch(U + "/rest/v1/catering_leads", {
        method: "POST",
        headers: { "Content-Type": "application/json", apikey: K, Authorization: "Bearer " + K, Prefer: "return=minimal" },
        body: JSON.stringify(data)
      }).then(function (r) {
        if (!r.ok) return r.text().then(function (t) { throw new Error(r.status + " " + t); });
        status.className = "book__status ok";
        status.textContent = "🌭 Got it! We'll reach out shortly to lock in your event. Thanks for choosing The Glizzness.";
        form.reset(); submit.disabled = false; submit.textContent = "Send my request";
      }).catch(function (e) {
        console.error(e);
        status.className = "book__status err";
        var msg = "That didn't go through. Please ";
        if (phone) msg += "call or text <a href='" + telHref + "'>" + phone + "</a>";
        if (phone && email) msg += " or ";
        if (email) msg += "email <a href='mailto:" + email + "'>" + email + "</a>";
        if (!phone && !email) msg += "reach out to us";
        status.innerHTML = msg + " and we'll get you booked.";
        submit.disabled = false; submit.textContent = "Send my request";
      });
    });
  }
})();
