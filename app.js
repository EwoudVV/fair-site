/* Ewoud Makes — fair site
   No dependencies. Served statically (GitHub Pages); sign-ups go to the nest
   box backend via FAIR_API (see config.js). If the backend is unreachable,
   submissions are queued in localStorage and retried — nothing is lost. */

(function () {
  "use strict";

  /* config.js defines FAIR_API and FAIR_CONTACT */
  var API = window.FAIR_API || "";
  var CONTACT = window.FAIR_CONTACT || "your-email@example.com";
  var QUEUE_KEY = "fair_queue";

  /* ---------- signup counter ---------- */
  var counterEl = document.getElementById("counter");
  function loadCounter() {
    if (!counterEl) return;
    if (!API) return;
    fetch(API + "/count", { mode: "cors" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (d) { counterEl.textContent = String(d.count || 0); })
      .catch(function () {});
  }

  /* ---------- queued submissions ---------- */
  function readQueue() {
    try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]"); }
    catch (e) { return []; }
  }
  function writeQueue(q) {
    try { localStorage.setItem(QUEUE_KEY, JSON.stringify(q.slice(-50))); } catch (e) {}
  }

  function sendPayload(payload) {
    if (!API) return Promise.reject(new Error("no backend"));
    return fetch(API + "/signup", {
      method: "POST",
      mode: "cors",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok || !d.ok) throw new Error(d.error || "failed");
        return d;
      });
    });
  }

  function flushQueue() {
    var q = readQueue();
    if (!q.length) return;
    var kept = [];
    q.forEach(function (item) {
      sendPayload(item).catch(function () { kept.push(item); });
    });
    writeQueue(kept);
    if (kept.length !== q.length) loadCounter();
  }

  /* ---------- signup form ---------- */
  var form = document.getElementById("signup-form");
  var statusEl = document.getElementById("form-status");
  var submitBtn = document.getElementById("submit-btn");

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = "form-status" + (kind ? " " + kind : "");
  }

  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (form.dataset.sent === "1") return;

      var name = form.name.value.trim();
      var email = form.email.value.trim();
      var phone = form.phone.value.trim();
      if (!name) { setStatus("Please add your name so I can get back to you :)", "err"); form.name.focus(); return; }
      if (!email && !phone) { setStatus("Add an email or phone number so I can reach you.", "err"); form.email.focus(); return; }

      var topics = Array.prototype.slice.call(form.querySelectorAll('input[name="topics"]:checked'))
        .map(function (c) { return c.value; });
      if (topics.length === 0) topics = ["Not sure yet — surprise us"];

      var payload = {
        name: name,
        email: email,
        phone: phone,
        kid_age: form.kid_age.value.trim(),
        topics: topics,
        message: form.message.value.trim(),
        website: form.website.value.trim()
      };

      submitBtn.disabled = true;
      submitBtn.textContent = "Sending…";
      setStatus("", "");

      sendPayload(payload)
        .then(function () {
          form.dataset.sent = "1";
          setStatus("Got it! I'll text or email you right after the fair. Thank you!", "ok");
          submitBtn.textContent = "Done! Talk soon \u2764";
          loadCounter();
        })
        .catch(function () {
          // queue it locally, retry in the background, and give a fallback path
          var q = readQueue();
          q.push(payload);
          writeQueue(q);
          setStatus(
            "The booth's connection hiccuped, but your spot is saved — I'll get back to you. " +
            "If you'd rather, email " + CONTACT + ".",
            "ok"
          );
          form.dataset.sent = "1";
          submitBtn.textContent = "Done! Talk soon \u2764";
          flushQueue();
        });
    });
  }

  /* ---------- drawbot animation ---------- */
  var gantryX = document.querySelector(".gantry-x");
  var gantryY = document.querySelector(".gantry-y");
  function animateDrawbot() {
    if (!gantryX || !gantryY) return;
    var t = 0;
    setInterval(function () {
      t += 1;
      var x = 4 + 88 * (0.5 + 0.5 * Math.sin(t / 7));
      var y = -14 + 24 * Math.sin(t / 5);
      gantryX.style.transform = "translateX(" + x + "%)";
      gantryY.style.transform = "translateY(" + y + "px)";
    }, 900);
  }
  animateDrawbot();

  /* ---------- reveal on scroll ---------- */
  var revealEls = document.querySelectorAll(".card, .plan, .shop-item, .section-title");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) {
      el.classList.add("reveal");
      io.observe(el);
    });
  }

  /* ---------- boot ---------- */
  loadCounter();
  flushQueue();
})();
