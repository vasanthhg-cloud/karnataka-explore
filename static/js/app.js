/* Karnataka Explore - small progressive enhancements, no dependencies. */
(function () {
  "use strict";

  /* ---------- theme ---------- */
  var root = document.documentElement;
  function applyTheme(mode) {
    root.setAttribute("data-theme", mode);
    var sun = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>';
    var moon = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8z"/></svg>';
    document.querySelectorAll("[data-theme-icon]").forEach(function (el) {
      el.innerHTML = mode === "dark" ? sun : moon;
    });
  }
  window.toggleTheme = function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try { localStorage.setItem("kx-theme", next); } catch (e) {}
    applyTheme(next);
  };

  /* ---------- mobile nav + dropdowns ---------- */
  document.addEventListener("click", function (e) {
    var t = e.target;
    var navBtn = t.closest("[data-nav-toggle]");
    if (navBtn) { document.getElementById("nav").classList.toggle("open"); return; }
    var dropBtn = t.closest("[data-dropdown]");
    document.querySelectorAll(".dropdown.open").forEach(function (d) {
      if (!dropBtn || d !== dropBtn.closest(".dropdown")) d.classList.remove("open");
    });
    if (dropBtn) dropBtn.closest(".dropdown").classList.toggle("open");
    var pw = t.closest("[data-pw-toggle]");
    if (pw) {
      var input = pw.parentElement.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
      pw.textContent = input.type === "password" ? "Show" : "Hide";
    }
    var lb = t.closest("[data-lightbox]");
    if (lb) openLightbox(lb.getAttribute("data-lightbox"));
  });

  /* ---------- flash messages ---------- */
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity .4s, transform .4s";
      el.style.opacity = "0"; el.style.transform = "translateX(16px)";
      setTimeout(function () { el.remove(); }, 420);
    }, 5200);
  });

  /* ---------- lightbox ---------- */
  function openLightbox(src) {
    var box = document.createElement("div");
    box.style.cssText = "position:fixed;inset:0;background:rgba(4,16,12,.92);z-index:200;display:grid;place-items:center;padding:24px;cursor:zoom-out";
    var img = document.createElement("img");
    img.src = src;
    img.style.cssText = "max-width:96vw;max-height:92vh;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.6)";
    box.appendChild(img);
    box.addEventListener("click", function () { box.remove(); });
    document.addEventListener("keydown", function esc(ev) {
      if (ev.key === "Escape") { box.remove(); document.removeEventListener("keydown", esc); }
    });
    document.body.appendChild(box);
  }

  /* ---------- date guards ---------- */
  document.querySelectorAll("[data-min-today]").forEach(function (el) {
    el.min = new Date().toISOString().slice(0, 10);
  });
  var ci = document.querySelector("[name=checkin]"), co = document.querySelector("[name=checkout]");
  if (ci && co) {
    ci.addEventListener("change", function () {
      if (!ci.value) return;
      var d = new Date(ci.value); d.setDate(d.getDate() + 1);
      co.min = d.toISOString().slice(0, 10);
      if (co.value && co.value <= ci.value) co.value = co.min;
      updateNights();
    });
    co.addEventListener("change", updateNights);
    updateNights();
  }
  function updateNights() {
    var out = document.querySelector("[data-nights]");
    if (!out || !ci || !co || !ci.value || !co.value) return;
    var n = Math.round((new Date(co.value) - new Date(ci.value)) / 86400000);
    out.textContent = n > 0 ? n : 0;
  }

  /* ---------- booking quantity × price ---------- */
  document.querySelectorAll("[data-calc]").forEach(function (form) {
    var price = parseFloat(form.getAttribute("data-price")) || 0;
    var qty = form.querySelector("[data-qty]");
    var out = form.querySelector("[data-total-out]");
    if (!qty || !out) return;
    function calc() {
      var n = parseInt(qty.value, 10) || 1;
      out.textContent = "₹" + (price * n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
    }
    qty.addEventListener("input", calc); calc();
  });

  /* ---------- itinerary counter ---------- */
  var counter = document.querySelector("[data-count-selected]");
  if (counter) {
    function count() {
      counter.textContent = document.querySelectorAll("[data-place-check]:checked").length;
    }
    document.querySelectorAll("[data-place-check]").forEach(function (c) {
      c.addEventListener("change", count);
    });
    count();
  }

  /* ---------- delete confirmations ---------- */
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!confirm(f.getAttribute("data-confirm"))) e.preventDefault();
    });
  });
})();
