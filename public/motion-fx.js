/* jargal.me motion layer — uses the free Motion library (motion.dev, MIT), vendored at vendor/motion-14.10.1.min.js.
   Progressive enhancement: if Motion is missing or the user prefers reduced motion, the site works as before. */
(function () {
  "use strict";
  var M = window.Motion;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var small = window.matchMedia && window.matchMedia("(max-width: 760px)").matches;
  var coarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
  var root = document.documentElement;

  /* ---------- Background: orbs, aurora, rings (CSS-driven loops, cheap transforms) ---------- */
  function buildBackground() {
    var bg = document.createElement("div");
    bg.className = "fx-bg";
    bg.setAttribute("aria-hidden", "true");
    bg.innerHTML =
      '<div class="fx-parallax" data-depth="18"><span class="fx-orb fx-orb-a"></span><span class="fx-orb fx-orb-b"></span>' +
      (small ? "" : '<span class="fx-orb fx-orb-c"></span>') + "</div>" +
      '<div class="fx-parallax" data-depth="8"><span class="fx-aurora fx-aurora-a"></span>' +
      (small ? "" : '<span class="fx-aurora fx-aurora-b"></span>') + "</div>" +
      '<div class="fx-parallax" data-depth="28"><span class="fx-ring fx-ring-a"></span>' +
      (small ? "" : '<span class="fx-ring fx-ring-b"></span>') + "</div>" +
      '<canvas class="fx-particles"></canvas><div class="fx-scrim"></div>';
    document.body.insertBefore(bg, document.body.firstChild);
    return bg;
  }

  /* ---------- Pointer-reactive network particles (restrained) ---------- */
  function startParticles(canvas) {
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var dpr = Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2);
    var count = small ? 34 : 90;
    var linkDist = small ? 90 : 130;
    var pts = [], w = 0, h = 0, mouse = { x: -9999, y: -9999 }, running = true, raf = 0;

    function resize() {
      w = window.innerWidth; h = window.innerHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = w + "px"; canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    for (var i = 0; i < count; i++) {
      pts.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25, r: Math.random() * 1.4 + 0.6 });
    }
    function frame() {
      if (!running) return;
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < pts.length; i++) {
        var p = pts[i];
        var dx = p.x - mouse.x, dy = p.y - mouse.y, d2 = dx * dx + dy * dy;
        if (d2 < 22500 && d2 > 1) { var f = 0.6 / Math.sqrt(d2); p.vx += dx * f * 0.02; p.vy += dy * f * 0.02; }
        p.vx *= 0.985; p.vy *= 0.985;
        p.vx += (Math.random() - 0.5) * 0.01; p.vy += (Math.random() - 0.5) * 0.01;
        p.x += p.vx; p.y += p.vy;
        if (p.x < -10) p.x = w + 10; else if (p.x > w + 10) p.x = -10;
        if (p.y < -10) p.y = h + 10; else if (p.y > h + 10) p.y = -10;
      }
      ctx.lineWidth = 0.6;
      for (var a = 0; a < pts.length; a++) {
        for (var b = a + 1; b < pts.length; b++) {
          var ex = pts[a].x - pts[b].x, ey = pts[a].y - pts[b].y, dd = ex * ex + ey * ey;
          if (dd < linkDist * linkDist) {
            ctx.strokeStyle = "rgba(0,230,118," + (0.16 * (1 - Math.sqrt(dd) / linkDist)).toFixed(3) + ")";
            ctx.beginPath(); ctx.moveTo(pts[a].x, pts[a].y); ctx.lineTo(pts[b].x, pts[b].y); ctx.stroke();
          }
        }
      }
      ctx.fillStyle = "rgba(160,255,200,0.55)";
      for (var k = 0; k < pts.length; k++) { ctx.beginPath(); ctx.arc(pts[k].x, pts[k].y, pts[k].r, 0, 6.283); ctx.fill(); }
      raf = requestAnimationFrame(frame);
    }
    window.addEventListener("resize", resize, { passive: true });
    if (!coarse) {
      window.addEventListener("pointermove", function (e) { mouse.x = e.clientX; mouse.y = e.clientY; }, { passive: true });
      document.addEventListener("pointerleave", function () { mouse.x = mouse.y = -9999; });
    }
    document.addEventListener("visibilitychange", function () {
      running = !document.hidden;
      if (running) { cancelAnimationFrame(raf); raf = requestAnimationFrame(frame); }
    });
    raf = requestAnimationFrame(frame);
  }

  /* ---------- Pointer + scroll parallax on background layers ---------- */
  function startParallax(bg) {
    var layers = bg.querySelectorAll(".fx-parallax");
    var tx = 0, ty = 0, cx = 0, cy = 0, sy = 0, ticking = false;
    function apply() {
      cx += (tx - cx) * 0.06; cy += (ty - cy) * 0.06;
      for (var i = 0; i < layers.length; i++) {
        var d = +layers[i].getAttribute("data-depth");
        layers[i].style.transform = "translate3d(" + (cx * d).toFixed(1) + "px," + (cy * d - sy * d * 0.01).toFixed(1) + "px,0)";
      }
      if (Math.abs(tx - cx) > 0.001 || Math.abs(ty - cy) > 0.001) requestAnimationFrame(apply); else ticking = false;
    }
    function kick() { if (!ticking) { ticking = true; requestAnimationFrame(apply); } }
    if (!coarse) window.addEventListener("pointermove", function (e) { tx = e.clientX / window.innerWidth - 0.5; ty = e.clientY / window.innerHeight - 0.5; kick(); }, { passive: true });
    window.addEventListener("scroll", function () { sy = window.scrollY; tx += 0.0001; kick(); }, { passive: true });
  }

  /* ---------- Motion-powered entrances, reveals, hovers ---------- */
  function heroEntrance() {
    var hero = document.querySelector(".hero-copy, .page-hero-copy");
    if (!hero) return [];
    var items = hero.querySelectorAll(".eyebrow, h1, .hero-lead, .hero-detail, .hero-actions > *, .stat-card, .page-hero-copy > p");
    var list = Array.prototype.slice.call(items);
    if (!list.length) return [];
    hero.classList.add("visible"); hero.style.opacity = "1"; hero.style.transform = "none";
    list.forEach(function (n) { n.style.opacity = "0"; });
    M.animate(list, { opacity: [0, 1], y: [24, 0], filter: ["blur(6px)", "blur(0px)"] },
      { duration: 0.8, delay: M.stagger(0.07, { startDelay: 0.15 }), ease: [0.22, 1, 0.36, 1] });
    var visual = document.querySelector(".hero-visual");
    if (visual) {
      visual.classList.add("visible");
      M.animate(visual, { opacity: [0, 1], scale: [0.94, 1] }, { duration: 1, delay: 0.35, ease: [0.22, 1, 0.36, 1] });
      var notes = visual.querySelectorAll(".floating-note");
      if (notes.length) M.animate(notes, { y: [0, -8, 0] }, { duration: 5, repeat: Infinity, ease: "easeInOut", delay: M.stagger(1.2) });
    }
    return [hero, visual];
  }

  function scrollReveals(skip) {
    document.querySelectorAll(".reveal").forEach(function (node) {
      if (skip.indexOf(node) !== -1) return;
      node.style.opacity = "0";
      node.style.transform = "translateY(32px)";
    });
    M.inView(".reveal", function (el) {
      if (skip.indexOf(el) !== -1) return;
      el.classList.add("visible");
      var sibs = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
      M.animate(el, { opacity: 1, y: [32, 0] }, { duration: 0.7, delay: Math.min(sibs, 4) * 0.08, ease: [0.22, 1, 0.36, 1] });
    }, { amount: 0.15 });
  }

  function cardHovers() {
    if (coarse) return;
    document.querySelectorAll(".project-card, .feature-card, .stat-card, .timeline-card").forEach(function (card) {
      card.classList.add("fx-card");
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        card.style.setProperty("--mx", ((e.clientX - r.left) / r.width * 100).toFixed(1) + "%");
        card.style.setProperty("--my", ((e.clientY - r.top) / r.height * 100).toFixed(1) + "%");
      });
      M.hover(card, function () {
        M.animate(card, { y: -6, scale: 1.015 }, { type: "spring", stiffness: 300, damping: 22 });
        return function () { M.animate(card, { y: 0, scale: 1 }, { type: "spring", stiffness: 300, damping: 24 }); };
      });
    });
  }

  /* ---------- Animated entry into /3d ---------- */
  function threeDEntry() {
    var links = document.querySelectorAll('a[href="3d/"], a[href="./3d/"], a[href="/3d/"], a[href="3d/index.html"]');
    if (!links.length) return;
    var veil = document.createElement("div");
    veil.className = "fx-veil"; veil.setAttribute("aria-hidden", "true");
    veil.innerHTML = '<span class="fx-veil-ring"></span><span class="fx-veil-label">Entering 3D</span>';
    document.body.appendChild(veil);
    links.forEach(function (a) {
      if (a.classList.contains("button")) a.classList.add("fx-3d-link");
      a.addEventListener("click", function (e) {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target === "_blank") return;
        e.preventDefault();
        var href = a.href, done = false;
        function go() { if (!done) { done = true; window.location.href = href; } }
        veil.classList.add("active");
        M.animate(veil, { opacity: [0, 1] }, { duration: 0.35 });
        M.animate(veil.querySelector(".fx-veil-ring"), { scale: [0.2, 1.6], opacity: [0, 1, 0.6] }, { duration: 0.55, ease: [0.22, 1, 0.36, 1] }).then(go);
        setTimeout(go, 900); /* safety net */
      });
    });
    window.addEventListener("pageshow", function (e) { if (e.persisted) { veil.classList.remove("active"); veil.style.opacity = "0"; } });
  }

  if (reduce || !M || !M.animate) {
    root.classList.add("fx-static");
    return; /* scripts.js keeps its simple reveal; no continuous motion */
  }
  root.classList.add("fx-on");
  document.addEventListener("DOMContentLoaded", function () {
    try {
      var bg = buildBackground();
      startParticles(bg.querySelector(".fx-particles"));
      startParallax(bg);
      var skip = heroEntrance();
      scrollReveals(skip);
      cardHovers();
      threeDEntry();
    } catch (err) {
      root.classList.remove("fx-on");
      document.querySelectorAll(".reveal").forEach(function (n) { n.style.opacity = ""; n.style.transform = ""; n.classList.add("visible"); });
      if (window.console) console.warn("motion-fx disabled:", err);
    }
  });
})();
