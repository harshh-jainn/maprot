/* maprot runtime. All geometry is precomputed in Python; this just draws and
   handles interaction. BOARD is injected above. */
(function () {
  "use strict";
  var B = window.BOARD, VB = B.vb, IMG = B.img;
  var NS = "http://www.w3.org/2000/svg";
  function el(t, a) {
    var n = document.createElementNS(NS, t);
    for (var k in (a || {})) n.setAttribute(k, a[k]);
    return n;
  }
  function $(id) { return document.getElementById(id); }

  /* ---- graticule ---- */
  (function () {
    var g = $("grat"), L = $("grat-lbl"), i;
    for (i = 0; i < B.graticule.lon.length; i++) {
      var v = B.graticule.lon[i];
      g.appendChild(el("line", { x1: v.x, y1: VB.y + 12, x2: v.x, y2: VB.y + VB.h - 12 }));
      var t = el("text", { x: v.x + 4, y: VB.y + 18, "class": "grat-txt" });
      t.textContent = v.label; L.appendChild(t);
    }
    for (i = 0; i < B.graticule.lat.length; i++) {
      var w = B.graticule.lat[i];
      g.appendChild(el("line", { x1: VB.x + 12, y1: w.y, x2: VB.x + VB.w - 12, y2: w.y }));
      var u = el("text", { x: VB.x + 3, y: w.y - 4, "class": "grat-txt", "text-anchor": "start" });
      u.textContent = w.label; L.appendChild(u);
    }
  })();

  /* ---- reference towns ---- */
  (function () {
    var g = $("towns");
    B.towns.forEach(function (t) {
      var grp = el("g", { "class": "town" });
      grp.appendChild(el("circle", { cx: t.x, cy: t.y, r: 3.6 }));
      var tx = el("text", {
        x: t.side === "r" ? t.x + 9 : t.x - 9, y: t.y + 5,
        "text-anchor": t.side === "r" ? "start" : "end"
      });
      tx.textContent = t.name; grp.appendChild(tx); g.appendChild(grp);
    });
  })();

  /* ---- route ---- */
  if (B.route && B.route.length > 1) {
    $("route").setAttribute("d", "M" + B.route.map(function (p) {
      return p.x.toFixed(1) + "," + p.y.toFixed(1);
    }).join(" L"));
  }

  /* ---- pins ---- */
  var pinEls = {}, ixEls = {};
  (function () {
    var gp = $("pins"), gl = $("leaders");
    B.places.forEach(function (p, i) {
      if (p.fanned) {
        gl.appendChild(el("line", { "class": "leader", x1: p.ax, y1: p.ay, x2: p.x, y2: p.y }));
        gl.appendChild(el("circle", { "class": "anchor", cx: p.ax, cy: p.ay, r: 2.6 }));
      }
      var grp = el("g", {
        "class": "pin pin-in", transform: "translate(" + p.x + " " + p.y + ")",
        role: "button", tabindex: "0",
        "aria-label": p.name + (p.city ? ", " + p.city : ""),
        style: "animation-delay:" + (0.2 + i * 0.08) + "s"
      });
      var sc = el("g", { "class": "pin-s" });
      sc.appendChild(el("circle", { "class": "pin-hit", cx: 0, cy: -17, r: 32 }));
      sc.appendChild(el("circle", { "class": "halo", cx: 0, cy: -21, r: 19 }));
      sc.appendChild(el("path", {
        "class": "drop",
        d: "M0 0 C-4.5-9 -14.5-13 -14.5-21 A14.5 14.5 0 1 1 14.5-21 C14.5-13 4.5-9 0 0 Z"
      }));
      var n = el("text", { "class": "num", x: 0, y: -21 });
      n.textContent = p.n; sc.appendChild(n);
      grp.appendChild(sc);
      grp.addEventListener("click", function (e) { e.stopPropagation(); showPop(p.n); });
      grp.addEventListener("mouseenter", function () {
        if (matchMedia("(hover:hover)").matches) showPop(p.n);
      });
      grp.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showPop(p.n); }
      });
      grp.addEventListener("focus", function () { showPop(p.n); });
      gp.appendChild(grp); pinEls[p.n] = grp;
    });
  })();

  /* pins render ~15px wide on a phone, so scale them up from the tip */
  function pinScale() { return window.matchMedia("(max-width:900px)").matches ? 1.45 : 1; }
  function applyPinScale() {
    var s = pinScale(), list = document.querySelectorAll(".pin-s"), i;
    for (i = 0; i < list.length; i++) list[i].setAttribute("transform", "scale(" + s + ")");
  }
  applyPinScale();
  window.addEventListener("resize", function () { applyPinScale(); hidePop(); });
  window.addEventListener("orientationchange", function () { applyPinScale(); hidePop(); });

  /* ---- pin callout: one photo, one line, then go deeper ---- */
  var pop = $("pop");
  function showPop(n) {
    var p = byN(n);
    for (var k in pinEls) pinEls[k].classList.toggle("is-active", +k === n);
    pop.innerHTML =
      '<button class="pop-x" type="button" aria-label="Close">&times;</button>' +
      '<img src="' + IMG[p.photos[0].file] + '" alt="' + esc(p.photos[0].alt) + '">' +
      '<div><p class="pop-n">' + p.name + '</p><p class="pop-one">' + p.one + "</p>" +
      '<button class="pop-go" type="button">Full write-up &rarr;</button></div>';
    pop.hidden = false;

    var rawLeft = (p.x - VB.x) / VB.w * 100;
    var rawTop = (p.y - 36 * pinScale() - VB.y) / VB.h * 100;
    var below = rawTop < 16;
    pop.classList.toggle("below", below);
    pop.style.top = (below ? (p.y - VB.y) / VB.h * 100 : rawTop) + "%";
    var cw = pop.parentElement.clientWidth, pw = pop.offsetWidth;
    var half = (pw / 2) / cw * 100;
    var left = Math.min(100 - half - 0.5, Math.max(half + 0.5, rawLeft));
    pop.style.left = left + "%";
    var arrow = ((rawLeft - (left - half)) / (pw / cw * 100)) * 100;
    pop.style.setProperty("--arrow", Math.min(92, Math.max(8, arrow)) + "%");

    pop.querySelector(".pop-x").addEventListener("click", function (e) {
      e.stopPropagation(); hidePop();
    });
    pop.querySelector(".pop-go").addEventListener("click", function (e) {
      e.stopPropagation(); select(n, true);
    });
  }
  function hidePop() { pop.hidden = true; }
  pop.addEventListener("click", function (e) { e.stopPropagation(); });
  document.addEventListener("click", hidePop);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") hidePop(); });

  /* ---- index ---- */
  (function () {
    var ul = $("index");
    B.places.forEach(function (p) {
      var li = document.createElement("li"), b = document.createElement("button");
      b.type = "button";
      b.innerHTML = '<span class="ix-n">' + pad(p.n) + "</span>" +
        '<img src="' + IMG[p.photos[0].file] + '" alt="">' +
        '<span class="ix-name">' + p.name + "</span>" +
        '<span class="ix-loc">' + (p.loc || "") + "</span>";
      b.addEventListener("click", function () { select(p.n); });
      li.appendChild(b); ul.appendChild(li); ixEls[p.n] = b;
    });
    $("m-count").textContent = pad(B.places.length);
    var seen = [], i;
    for (i = 0; i < B.places.length; i++) {
      var r = B.places[i].region;
      if (r && seen.indexOf(r) < 0) seen.push(r);
    }
    $("m-regions").textContent = seen.join(" · ") || "—";
  })();

  /* ---- planning notes ---- */
  if (B.notes && B.notes.items && B.notes.items.length) {
    var ol = $("notes-list");
    B.notes.items.forEach(function (it) {
      var li = document.createElement("li");
      li.innerHTML = '<span class="dont">' + it[0] + '</span><span class="do">' + it[1] + "</span>";
      ol.appendChild(li);
    });
    if (B.notes.source) {
      $("notes-src").innerHTML = 'From <a href="' + B.notes.source.url +
        '" target="_blank" rel="noopener">this reel</a> by ' + B.notes.source.by +
        " &mdash; one creator&rsquo;s opinions, not gospel.";
    }
  } else {
    var sec = document.querySelector(".notes");
    if (sec) sec.remove();
  }

  /* ---- lightbox ---- */
  var lb = $("lb"), lbImg = $("lb-img");
  function openLb(src, alt) { lbImg.src = src; lbImg.alt = alt; lb.classList.add("on"); }
  function closeLb() { lb.classList.remove("on"); lbImg.src = ""; }
  lb.addEventListener("click", closeLb);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeLb(); });

  /* ---- dossier ---- */
  function select(n, scroll) {
    var p = byN(n);
    hidePop();
    for (var k in pinEls) pinEls[k].classList.toggle("is-active", +k === n);
    for (var j in ixEls) ixEls[j].setAttribute("aria-current", +j === n ? "true" : "false");
    var gmap = p.maps_query
      ? "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(p.maps_query)
      : "https://www.google.com/maps/search/?api=1&query=" + p.lat + "," + p.lon;
    var amap = p.maps_query
      ? "https://maps.apple.com/?q=" + encodeURIComponent(p.maps_query)
      : "https://maps.apple.com/?ll=" + p.lat + "," + p.lon + "&q=" + encodeURIComponent(p.name);
    var multi = p.sources.length > 1;
    var d = $("dossier");
    d.innerHTML =
      '<button class="back" type="button">&uarr;&nbsp; Back to map</button>' +
      "<div>" + (p.type ? '<span class="chip">' + p.type + "</span>" : "") +
        "<h2>" + p.name + "</h2>" +
        '<div class="where">' + (p.city ? p.city + " &middot; " : "") +
          '<span class="coord">' + p.lat.toFixed(4) + "&deg;, " + p.lon.toFixed(4) + "&deg;</span>" +
          (p.approx ? '<span class="approx" title="Venue not in OpenStreetMap — pinned to its locality">approx.</span>' : "") +
        "</div></div>" +
      '<div class="gallery">' + p.photos.map(function (ph, i) {
        return '<button type="button" data-i="' + i + '" aria-label="Enlarge: ' + esc(ph.alt) + '">' +
               '<img src="' + IMG[ph.file] + '" alt="' + esc(ph.alt) + '"></button>';
      }).join("") + "</div>" +
      (p.unique ? '<section><h3 class="sec">Why it’s unique</h3><p class="lede">' + p.unique + "</p></section>" : "") +
      (p.desc ? '<section class="body"><h3 class="sec">What it’s like</h3><p>' + p.desc + "</p></section>" : "") +
      (p.facts && p.facts.length ? '<section><h3 class="sec">Know before you go</h3><dl class="facts">' +
        p.facts.map(function (f) { return "<dt>" + f[0] + "</dt><dd>" + f[1] + "</dd>"; }).join("") +
        "</dl></section>" : "") +
      (p.near && p.near.length ? '<section><h3 class="sec">Nearby</h3><ul class="near">' +
        p.near.map(function (f) { return "<li><span>" + f[0] + '</span><span class="d">' + f[1] + "</span></li>"; }).join("") +
        "</ul></section>" : "") +
      '<section><h3 class="sec">Links</h3><div class="links">' +
        p.sources.map(function (s) {
          return '<a class="watch" href="' + s.url + '" target="_blank" rel="noopener">&#9654; Reel' +
                 (multi ? " &middot; " + s.by : "") + "</a>";
        }).join("") +
        '<a href="' + gmap + '" target="_blank" rel="noopener">Google Maps</a>' +
        '<a href="' + amap + '" target="_blank" rel="noopener">Apple Maps</a>' +
      "</div></section>" +
      '<p class="src">Photos are frames from ' + (multi ? "reels" : "the reel") + " by " +
        p.sources.map(function (s) { return s.by; }).join(" and ") + "</p>";

    d.querySelector(".back").addEventListener("click", function () {
      document.querySelector(".plate").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    var gb = d.querySelectorAll(".gallery button"), i;
    for (i = 0; i < gb.length; i++) {
      (function (b) {
        b.addEventListener("click", function () {
          var ph = p.photos[+b.dataset.i];
          openLb(IMG[ph.file], ph.alt);
        });
      })(gb[i]);
    }
    if (scroll && window.matchMedia("(max-width:900px)").matches) {
      d.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function byN(n) {
    for (var i = 0; i < B.places.length; i++) if (B.places[i].n === n) return B.places[i];
    return null;
  }
  function pad(n) { return String(n).length < 2 ? "0" + n : String(n); }
  function esc(s) { return String(s || "").replace(/"/g, "&quot;"); }

  if (B.places.length) select(B.places[0].n);
})();
