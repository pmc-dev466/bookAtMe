/* =============================================================
   BookAtMe! · main.js
   Script clásico + IIFE. Un solo global de lectura: window.__DB__
   El HTML ya trae el contenido; esto solo enriquece.
   ============================================================= */
(function () {
  "use strict";

  var DB = window.__DB__ || { libros: [], meta: {} };
  var LIBROS = DB.libros || [];
  var EJES = [
    { k: "score_ritmo",          l: "Ritmo" },
    { k: "score_personajes",     l: "Personajes" },
    { k: "score_profundidad",    l: "Profundidad" },
    { k: "score_originalidad",   l: "Originalidad" },
    { k: "score_facilidad",      l: "Facilidad" },
    { k: "score_calidad_precio", l: "Calidad-precio" }
  ];
  var COLORES = ["#24503D", "#8C2F39", "#A87C2E", "#3E6B8A"];
  var MAX_CMP = 4;
  var STORE = "leido:comparar";

  /* ---------- helpers ---------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function safe(fn, name) { try { fn(); } catch (e) { console.warn("[" + name + "]", e); } }
  function byId(id) {
    for (var i = 0; i < LIBROS.length; i++) if (LIBROS[i].id === id) return LIBROS[i];
    return null;
  }
  function eur(n) {
    if (n == null) return "—";
    return n.toFixed(2).replace(".", ",") + " €";
  }
  function num(n, suf) {
    if (n == null || n === "") return "—";
    return String(n).replace(".", ",") + (suf || "");
  }
  function miles(n) {
    if (n == null) return "—";
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }
  var reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- cabecera ---------- */
  function initHeader() {
    var head = $("[data-head]");
    if (!head || head.dataset.ligado) return;
    head.dataset.ligado = "1";
    var onScroll = function () { head.classList.toggle("is-stuck", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    var toggle = $("[data-nav-toggle]");
    var drawer = $("[data-nav-drawer]");
    if (toggle && drawer) {
      toggle.addEventListener("click", function () {
        var open = drawer.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
      drawer.addEventListener("click", function (e) {
        if (e.target.closest("a")) {
          drawer.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    }
  }

  /* ---------- apariciones al hacer scroll ---------- */
  function initReveals() {
    var els = $$("[data-reveal]");
    if (!els.length) return;
    if (!("IntersectionObserver" in window) || reduced) {
      els.forEach(function (el) { el.classList.add("is-revealed"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-revealed"); io.unobserve(e.target); }
      });
    }, { threshold: 0.02, rootMargin: "0px 0px -3% 0px" });
    els.forEach(function (el) { io.observe(el); });

    // red de seguridad: si el observador nunca dispara, mostramos igualmente
    setTimeout(function () {
      $$("[data-reveal]:not(.is-revealed)").forEach(function (el) {
        if (el.getBoundingClientRect().top < window.innerHeight * 1.4) el.classList.add("is-revealed");
      });
    }, 2500);
    setTimeout(function () {
      $$("[data-reveal]:not(.is-revealed)").forEach(function (el) { el.classList.add("is-revealed"); });
    }, 6000);
  }

  /* ---------- anclas suaves ---------- */
  function initAnchors() {
    document.addEventListener("click", function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      var id = a.getAttribute("href");
      // "#/..." son rutas de la versión de un solo archivo, no anclas
      if (!id || id === "#" || id.indexOf("#/") === 0) return;
      var el = document.querySelector(id);
      if (!el) return;
      e.preventDefault();
      window.scrollTo({
        top: el.getBoundingClientRect().top + window.scrollY - 92,
        behavior: reduced ? "auto" : "smooth"
      });
    });
  }

  /* ---------- galería de la ficha ---------- */
  function initGallery() {
    var g = $("[data-gallery]");
    if (!g) return;
    var main = $("[data-gallery-main]", g);
    var thumbs = $$("[data-gallery-thumb]", g);
    if (!main || thumbs.length < 2) return;
    thumbs.forEach(function (b) {
      b.addEventListener("click", function () {
        main.src = b.getAttribute("data-src");
        main.alt = b.getAttribute("data-alt") || main.alt;
        thumbs.forEach(function (o) { o.setAttribute("aria-current", o === b ? "true" : "false"); });
      });
    });
  }

  /* ---------- selección para comparar ---------- */
  function getSel() {
    var raw;
    /* El enlace compartible (#c=...) es una ENTRADA, no la fuente de la verdad.
       Antes se leia SIEMPRE de aqui y setSel() no lo actualizaba nunca: en cuanto
       aparecia el #c= (al llegar al segundo libro) la seleccion se congelaba, la
       cuarta casilla no se llenaba y la X no quitaba nada. Ahora se lee una sola
       vez al entrar, se vuelca al almacen, y a partir de ahi manda el almacen. */
    if (hashPendiente && location.hash.indexOf("#c=") === 0) {
      hashPendiente = false;
      raw = decodeURIComponent(location.hash.slice(3)).split(",");
      try { localStorage.setItem(STORE, JSON.stringify(raw.slice(0, MAX_CMP))); } catch (e) {}
    } else {
      hashPendiente = false;
      try { raw = JSON.parse(localStorage.getItem(STORE) || "[]"); } catch (e) { raw = []; }
    }
    if (!Array.isArray(raw)) raw = [];
    return raw.filter(function (id) { return !!byId(id); }).slice(0, MAX_CMP);
  }
  function setSel(ids) {
    ids = ids.slice(0, MAX_CMP);
    try { localStorage.setItem(STORE, JSON.stringify(ids)); } catch (e) {}
    /* El enlace compartible se reescribe AQUI, con cada cambio, para que no se
       quede obsoleto. Antes se escribia al pintar la tabla y solo cuando habia
       dos libros o mas, que es lo que provocaba el desfase. */
    if (history.replaceState && document.querySelector("[data-cmp-page]") &&
        location.hash.indexOf("#/") !== 0) {
      history.replaceState(null, "",
        ids.length ? "#c=" + encodeURIComponent(ids.join(",")) : location.pathname);
    }
    document.dispatchEvent(new CustomEvent("leido:cmp", { detail: ids }));
  }
  function toggleSel(id) {
    var ids = getSel();
    var i = ids.indexOf(id);
    if (i >= 0) ids.splice(i, 1);
    else {
      if (ids.length >= MAX_CMP) return false;
      ids.push(id);
    }
    setSel(ids);
    return true;
  }

  /* El #c= de la URL solo se hace caso la primera vez, al entrar por un enlace
     compartido. Ver getSel(). */
  var hashPendiente = true;
  var globalesLigados = false;   // los oyentes a nivel de documento se enganchan una sola vez
  var paintActual = function () {};

  function initCompareButtons() {
    function paint() {
      var ids = getSel();
      $$("[data-cmp-add]").forEach(function (b) {
        var on = ids.indexOf(b.getAttribute("data-cmp-add")) >= 0;
        b.setAttribute("aria-pressed", on ? "true" : "false");
        var t = $("[data-cmp-label]", b);
        if (t) t.textContent = on ? "En el comparador" : "Comparar";
      });
      $$("[data-cmp-count]").forEach(function (el) {
        el.textContent = ids.length;
        el.classList.toggle("is-on", ids.length > 0);
      });
      var bar = $("[data-cmp-bar]");
      if (bar) {
        bar.classList.toggle("is-on", ids.length > 0 && !$("[data-cmp-page]"));
        var txt = $("[data-cmp-bar-text]", bar);
        if (txt) {
          txt.innerHTML = "<b>" + ids.length + " " + (ids.length === 1 ? "libro" : "libros") +
            "</b> en el comparador<small>" +
            (ids.length === 1 ? "Añade al menos uno más para enfrentarlos" : "Puedes comparar hasta " + MAX_CMP) +
            "</small>";
        }
      }
    }
    if (!globalesLigados) {
      globalesLigados = true;
      document.addEventListener("click", function (e) {
        var b = e.target.closest("[data-cmp-add]");
        if (!b) return;
        e.preventDefault();
        if (!toggleSel(b.getAttribute("data-cmp-add"))) {
          b.setAttribute("title", "Ya tienes " + MAX_CMP + " libros seleccionados");
        }
      });
      document.addEventListener("leido:cmp", function () { safe(paintActual, "paint"); });
      safe(initAnchors, "initAnchors");
    }
    paintActual = paint;

    var clear = $("[data-cmp-clear]");
    if (clear && !clear.dataset.ligado) {
      clear.dataset.ligado = "1";
      clear.addEventListener("click", function () { setSel([]); });
    }
    paint();
  }

  /* ---------- radar ---------- */
  function radarSVG(libros, size) {
    var S = size || 300, C = S / 2, R = S * 0.36, N = EJES.length;
    /* Igual que en las fichas: las etiquetas caen fuera del hexagono y con la
       caja justa se cortaban por los lados. */
    var PAD = S * 0.18;
    var svg = ['<svg class="radar-svg" viewBox="' + (-PAD) + ' 0 ' + (S + 2 * PAD) + ' ' + S +
      '" role="img" aria-label="Gráfico de valoraciones del editor">'];
    var i, j;
    for (j = 1; j <= 5; j++) {
      var pts = [];
      for (i = 0; i < N; i++) pts.push(point(C, R * (j / 5), i, N).join(","));
      svg.push('<polygon class="radar-ring" points="' + pts.join(" ") + '"/>');
    }
    for (i = 0; i < N; i++) {
      var p = point(C, R, i, N);
      svg.push('<line class="radar-axis" x1="' + C + '" y1="' + C + '" x2="' + p[0] + '" y2="' + p[1] + '"/>');
    }
    libros.forEach(function (lb, k) {
      var col = COLORES[k % COLORES.length], pts = [], dots = "";
      for (i = 0; i < N; i++) {
        var v = lb[EJES[i].k];
        v = (typeof v === "number") ? v : 0;
        var q = point(C, R * (v / 10), i, N);
        pts.push(q.join(","));
        dots += '<circle class="radar-dot" cx="' + q[0] + '" cy="' + q[1] + '" fill="' + col + '"/>';
      }
      svg.push('<polygon class="radar-shape" points="' + pts.join(" ") + '" fill="' + col +
        '" fill-opacity="' + (libros.length > 1 ? 0.13 : 0.17) + '" stroke="' + col + '"/>' + dots);
    });
    for (i = 0; i < N; i++) {
      var lp = point(C, R + 21, i, N);
      var anchor = lp[0] > C + 4 ? "start" : (lp[0] < C - 4 ? "end" : "middle");
      svg.push('<text class="radar-label" x="' + lp[0] + '" y="' + (lp[1] + 3) + '" text-anchor="' + anchor + '">' +
        esc(EJES[i].l) + "</text>");
    }
    svg.push("</svg>");
    return svg.join("");
  }
  function point(c, r, i, n) {
    var a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [Math.round((c + r * Math.cos(a)) * 10) / 10, Math.round((c + r * Math.sin(a)) * 10) / 10];
  }

  /* ---------- página del comparador ---------- */
  var FILAS = [
    { l: "Categoría",        f: function (b) { return catName(b.categoria); } },
    { l: "Precio",           f: function (b) { return eur(b.precio); }, v: function (b) { return b.precio; }, mejor: "min" },
    { l: "Precio de lista",  f: function (b) { return eur(b.precio_lista); } },
    { l: "Valoración media", f: function (b) { return b.valoracion_media != null ? num(b.valoracion_media) + " / 5" : "—"; }, v: function (b) { return b.valoracion_media; }, mejor: "max" },
    { l: "Nº de reseñas",    f: function (b) { return miles(b.resenas_cantidad); }, v: function (b) { return b.resenas_cantidad; }, mejor: "max" },
    { l: "Formato",          f: function (b) { return b.formato ? b.formato.charAt(0).toUpperCase() + b.formato.slice(1) : "—"; } },
    { l: "Páginas",          f: function (b) { return miles(b.num_paginas); } },
    { l: "Horas de lectura", f: function (b) { return b.horas_lectura != null ? "≈ " + num(b.horas_lectura) + " h" : "—"; } },
    { l: "€ por 100 páginas", f: function (b) { var x = ratio(b); return x == null ? "—" : eur(x); }, v: ratio, mejor: "min" },
    { l: "Editorial",        f: function (b) { return b.editorial || "—"; } },
    { l: "Año",              f: function (b) { return b.anio || "—"; } },
    { l: "Idioma original",  f: function (b) { return b.idioma_original || "—"; } },
    { l: "Peso",             f: function (b) { return b.peso_g != null ? miles(b.peso_g) + " g" : "—"; }, v: function (b) { return b.peso_g; }, mejor: "min" },
    { l: "Dimensiones",      f: function (b) { return b.dimensiones_cm ? b.dimensiones_cm + " cm" : "—"; } },
    { l: "Saga",             f: function (b) { return b.saga ? b.saga + (b.num_en_saga ? " (n.º " + b.num_en_saga + ")" : "") : "No"; } },
    { l: "Kindle",           f: function (b) { return b.disponible_kindle == null ? "—" : (b.disponible_kindle ? "Sí" : "No"); } },
    { l: "Audiolibro",       f: function (b) { return b.disponible_audiolibro == null ? "—" : (b.disponible_audiolibro ? "Sí" : "No"); } },
    { l: "ISBN-13",          f: function (b) { return b.isbn_13 || "—"; } }
  ];
  function ratio(b) {
    if (b.precio == null || !b.num_paginas) return null;
    return Math.round((b.precio / b.num_paginas) * 10000) / 100;
  }
  function catName(id) {
    var cats = (DB.meta && DB.meta.categorias) || [];
    for (var i = 0; i < cats.length; i++) if (cats[i].id === id) return cats[i].nombre;
    return id || "—";
  }
  function media(b) {
    var s = 0, n = 0;
    EJES.forEach(function (e) { if (typeof b[e.k] === "number") { s += b[e.k]; n++; } });
    return n ? Math.round((s / n) * 10) / 10 : null;
  }

  function initComparador() {
    var page = $("[data-cmp-page]");
    if (!page) return;

    /* Si lib/db.js no llego (red caida, bloqueador, archivo mal subido), el
       comparador se quedaba mudo y en blanco para siempre. Mejor decirlo. */
    if (!LIBROS.length) {
      var aviso = $("[data-cmp-out]");
      if (aviso) {
        aviso.innerHTML = '<p class="cmp-empty">No hemos podido cargar la lista de libros. ' +
          'Recarga la p\u00e1gina; si sigue igual, puedes ver las fichas una a una desde ' +
          '<a href="index.html">la portada</a>.</p>';
      }
      return;
    }

    var slots = $("[data-cmp-slots]");
    var input = $("[data-cmp-search]");
    var results = $("[data-cmp-results]");
    var out = $("[data-cmp-out]");

    function render() {
      var ids = getSel();
      var sel = ids.map(byId).filter(Boolean);

      if (slots) {
        var h = sel.map(function (b) {
          return '<div class="slot-wrap"><span class="cover"><img src="' + esc(b.imagenes[0]) +
            '" alt="Portada de ' + esc(b.titulo) + '" loading="lazy"></span>' +
            '<button class="remove-badge" data-cmp-add="' + esc(b.id) + '" aria-label="Quitar ' + esc(b.titulo) + '">×</button></div>';
        }).join("");
        for (var k = sel.length; k < MAX_CMP; k++) h += '<div class="slot-empty" aria-hidden="true">+</div>';
        slots.innerHTML = h;
      }

      if (!out) return;
      if (sel.length < 2) {
        out.innerHTML = '<p class="cmp-empty">Elige al menos <b>dos libros</b> para verlos enfrentados.' +
          (sel.length === 1 ? " Ya tienes uno: añade otro." : "") + "</p>";
        return;
      }

      // mejor valor por fila
      var html = ['<div class="cmp-table-wrap"><table class="cmp-table"><caption class="sr-only">Comparativa de libros</caption><thead><tr><th scope="col"><span class="sr-only">Característica</span></th>'];
      sel.forEach(function (b) {
        html.push('<th scope="col" class="cmp-col-head"><a href="libro-' + esc(b.id) + '.html">' +
          '<span class="cover"><img src="' + esc(b.imagenes[0]) + '" alt="Portada de ' + esc(b.titulo) + '" loading="lazy"></span>' +
          "<h3>" + esc(b.titulo) + "</h3></a><span class=\"author\">" + esc(b.autor) + "</span></th>");
      });
      html.push("</tr></thead><tbody>");

      FILAS.forEach(function (row) {
        var best = null;
        if (row.mejor && row.v) {
          var vals = sel.map(row.v).filter(function (x) { return typeof x === "number"; });
          if (vals.length > 1) best = row.mejor === "min" ? Math.min.apply(null, vals) : Math.max.apply(null, vals);
        }
        html.push("<tr><th scope=\"row\">" + esc(row.l) + "</th>");
        sel.forEach(function (b) {
          var isBest = best != null && row.v && row.v(b) === best;
          html.push("<td" + (isBest ? ' class="is-best"' : "") + ">" + row.f(b) + "</td>");
        });
        html.push("</tr>");
      });

      // ejes del editor
      html.push('<tr><th scope="row" colspan="' + (sel.length + 1) + '" style="padding-top:1.3rem;color:var(--wine);font-weight:600;letter-spacing:.1em;font-size:.7rem;text-transform:uppercase">Valoración del editor (0-10)</th></tr>');
      EJES.concat([{ k: "__media", l: "Nota media" }]).forEach(function (e) {
        var get = function (b) { return e.k === "__media" ? media(b) : b[e.k]; };
        var vals = sel.map(get).filter(function (x) { return typeof x === "number"; });
        var best = vals.length > 1 ? Math.max.apply(null, vals) : null;
        html.push('<tr><th scope="row">' + esc(e.l) + "</th>");
        sel.forEach(function (b) {
          var v = get(b);
          html.push("<td" + (best != null && v === best ? ' class="is-best"' : "") + ">" +
            (typeof v === "number" ? num(v) + " / 10" : "—") + "</td>");
        });
        html.push("</tr>");
      });

      html.push("</tbody><tfoot><tr><td></td>");
      sel.forEach(function (b) {
        html.push('<td><a class="btn btn-buy" href="' + esc(b.affiliate_url) +
          '" target="_blank" rel="sponsored nofollow noopener">Ver en Amazon</a></td>');
      });
      html.push("</tr></tfoot></table></div>");

      // radar superpuesto
      html.push('<div class="radar-panel" style="margin-top:1.8rem"><div class="radar-head"><h3>Perfiles superpuestos</h3></div>' +
        '<p class="radar-note">Valoración del editor sobre 10 en seis ejes. No son datos de Amazon.</p>' +
        '<div style="max-width:420px;margin-inline:auto">' + radarSVG(sel, 330) + "</div>" +
        '<div class="radar-legend">' + sel.map(function (b, i) {
          return '<span><i style="background:' + COLORES[i % COLORES.length] + '"></i>' + esc(b.titulo) + "</span>";
        }).join("") + "</div></div>");

      out.innerHTML = html.join("");

    }

    if (input && results) {
      input.addEventListener("input", function () {
        var q = input.value.trim().toLowerCase();
        if (q.length < 2) { results.innerHTML = ""; return; }
        var ids = getSel();
        function coincide(b) {
          return (b.titulo + " " + b.autor + " " + catName(b.categoria)).toLowerCase().indexOf(q) >= 0;
        }
        var todos = LIBROS.filter(coincide);
        var hits = todos.filter(function (b) { return ids.indexOf(b.id) < 0; }).slice(0, 6);

        /* Antes, si no habia resultados se vaciaba la lista y no se decia nada:
           el usuario escribia y no pasaba absolutamente nada en pantalla. Ahora
           siempre hay respuesta, y se distingue "no existe" de "ya lo tienes". */
        if (!hits.length) {
          var motivo = todos.length
            ? "Ya lo tienes en la comparativa."
            : "No hemos encontrado ning\u00fan libro que encaje. Prueba con el t\u00edtulo, el autor o el " +
              "g\u00e9nero (amor, suspense, drama, comedia, filosof\u00eda, fantas\u00eda).";
          results.innerHTML = '<li class="cmp-sin-resultados">' + motivo + "</li>";
          return;
        }
        results.innerHTML = hits.map(function (b) {
          return '<li><button type="button" data-cmp-add="' + esc(b.id) + '">' +
            '<img src="' + esc(b.imagenes[0]) + '" alt="" loading="lazy" decoding="async" width="30" height="45">' +
            "<span><strong>" + esc(b.titulo) + "</strong><span>" + esc(b.autor) + " · " + catName(b.categoria) + "</span></span></button></li>";
        }).join("");
      });
      results.addEventListener("click", function () {
        input.value = ""; results.innerHTML = "";
      });
    }

    if (!page.dataset.ligado) {
      page.dataset.ligado = "1";
      document.addEventListener("leido:cmp", function () { if (document.body.contains(page)) safe(render, "render"); });
      window.addEventListener("hashchange", function () {
        /* esto solo salta en una navegacion de verdad (atras/adelante o enlace
           pegado a mano): ahi si hay que volver a hacer caso a la URL */
        hashPendiente = true;
        if (document.body.contains(page)) safe(render, "render");
      });
    }
    render();
  }

  /* ---------- filtros de categoría / listados ---------- */
  function initFilters() {
    var grid = $("[data-filter-grid]");
    if (!grid) return;
    var sort = $("[data-sort]");
    var chips = $$("[data-filter-format]");
    var cards = $$("[data-book]", grid);
    var empty = $("[data-filter-empty]");

    function apply() {
      var fmt = chips.filter(function (c) { return c.getAttribute("aria-pressed") === "true"; })
        .map(function (c) { return c.getAttribute("data-filter-format"); });
      var visibles = 0;
      cards.forEach(function (c) {
        var ok = !fmt.length || fmt.indexOf(c.getAttribute("data-formato")) >= 0;
        c.hidden = !ok;
        if (ok) visibles++;
      });
      if (empty) empty.hidden = visibles > 0;

      if (sort) {
        var key = sort.value;
        var arr = cards.slice().sort(function (a, b) {
          var x = byId(a.getAttribute("data-book")), y = byId(b.getAttribute("data-book"));
          if (!x || !y) return 0;
          switch (key) {
            case "precio-asc":  return (x.precio || 1e9) - (y.precio || 1e9);
            case "precio-desc": return (y.precio || -1) - (x.precio || -1);
            case "valoracion":  return (y.valoracion_media || 0) - (x.valoracion_media || 0);
            case "paginas":     return (y.num_paginas || 0) - (x.num_paginas || 0);
            case "nota":        return (media(y) || 0) - (media(x) || 0);
            default:            return (y.resenas_cantidad || 0) - (x.resenas_cantidad || 0);
          }
        });
        arr.forEach(function (c) { grid.appendChild(c); });
      }
    }
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        c.setAttribute("aria-pressed", c.getAttribute("aria-pressed") === "true" ? "false" : "true");
        apply();
      });
    });
    if (sort) sort.addEventListener("change", apply);
    apply();
  }


  /* ---------- guía por la interfaz ----------
     Los pasos vienen del HTML, en un <script type="application/json">, para
     que el texto lo escriba el generador y no viva aquí. Cada paso apunta a un
     selector; los que no encuentran su elemento se saltan solos, así la guía
     nunca se queda señalando al vacío. */
  function initGuia() {
    var fuente = $("#guia-pasos");
    if (!fuente) return;
    var datos;
    try { datos = JSON.parse(fuente.textContent); } catch (e) { return; }
    if (!datos || !datos.pasos || !datos.pasos.length) return;

    var CLAVE = "leido:guia:" + (datos.clave || "general");
    var pasos = [], i = 0, capa = null, foco = null, globo = null, previo = null;

    function visible(el) {
      if (!el) return false;
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    }
    function recoger() {
      pasos = datos.pasos.filter(function (p) { return visible($(p.sel)); });
      return pasos.length;
    }

    function cerrar(completada) {
      if (!capa) return;
      document.removeEventListener("keydown", teclas, true);
      window.removeEventListener("resize", situar);
      window.removeEventListener("scroll", situar, true);
      capa.remove();
      capa = foco = globo = null;
      document.documentElement.classList.remove("guia-abierta");
      if (completada) { try { localStorage.setItem(CLAVE, "1"); } catch (e) {} }
      if (previo && document.body.contains(previo)) previo.focus();
    }

    function situar() {
      if (!capa) return;
      var p = pasos[i], el = $(p.sel);
      if (!el) return;
      var r = el.getBoundingClientRect(), m = 8;
      foco.style.top = (r.top - m) + "px";
      foco.style.left = (r.left - m) + "px";
      foco.style.width = (r.width + m * 2) + "px";
      foco.style.height = (r.height + m * 2) + "px";

      // el globo va debajo del elemento; si no cabe, encima
      var gh = globo.offsetHeight || 190, gw = globo.offsetWidth || 320;
      var abajo = r.bottom + 14 + gh <= window.innerHeight;
      globo.style.top = (abajo ? r.bottom + 14 : Math.max(12, r.top - gh - 14)) + "px";
      var x = r.left + r.width / 2 - gw / 2;
      globo.style.left = Math.min(Math.max(12, x), window.innerWidth - gw - 12) + "px";
      globo.classList.toggle("guia-globo-arriba", !abajo);
    }

    /* Llevar la página hasta el elemento del paso. No se usa scrollIntoView con
       "smooth" a secas porque hay situaciones en las que ese desplazamiento no
       llega a ejecutarse, y entonces el recuadro se queda señalando algo que no
       está en pantalla. Aquí se calcula el destino, se intenta suave, y a los
       700 ms se comprueba: si no ha llegado, se coloca de golpe. */
    function irA(el) {
      if (!el) return;
      var r = el.getBoundingClientRect();
      var destino = Math.max(0, Math.round(
        window.scrollY + r.top + r.height / 2 - window.innerHeight / 2));
      var quieto = window.matchMedia &&
                   window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      /* Ojo: "auto" NO significa instantaneo, significa "lo que diga el CSS", y
         el CSS de esta web pide scroll-behavior: smooth. Para colocar de golpe
         hay que decir "instant" a las claras, tanto aqui como en la red de
         seguridad, o el respaldo sale suave tambien y no sirve de nada. */
      try {
        window.scrollTo({ top: destino, behavior: quieto ? "instant" : "smooth" });
      } catch (e) { window.scrollTo(0, destino); }
      setTimeout(function () {
        if (!capa) return;
        if (Math.abs(window.scrollY - destino) > 4) {
          try { window.scrollTo({ top: destino, behavior: "instant" }); }
          catch (e) { window.scrollTo(0, destino); }
        }
        situar();
      }, 700);
    }

    function pintar() {
      var p = pasos[i], el = $(p.sel);
      irA(el);
      $("[data-guia-titulo]", globo).textContent = p.titulo;
      $("[data-guia-texto]", globo).textContent = p.texto;
      $("[data-guia-cuenta]", globo).textContent = (i + 1) + " de " + pasos.length;
      $("[data-guia-atras]", globo).disabled = (i === 0);
      $("[data-guia-siguiente]", globo).textContent =
        (i === pasos.length - 1) ? "Entendido" : "Siguiente";
      /* El desplazamiento suave dura mas de lo que tarda un setTimeout corto, y
         el recuadro se quedaba donde estaba antes de moverse. Se recoloca en
         cada fotograma hasta que el scroll para. */
      situar();
      var t0 = performance.now();
      (function seguir() {
        if (!capa) return;
        situar();
        if (performance.now() - t0 < 900) requestAnimationFrame(seguir);
      })();
    }

    function mover(d) {
      var j = i + d;
      if (j < 0) return;
      if (j >= pasos.length) { cerrar(true); return; }
      i = j;
      pintar();
    }

    function teclas(ev) {
      if (!capa) return;
      if (ev.key === "Escape") { ev.preventDefault(); cerrar(true); }
      else if (ev.key === "ArrowRight") { ev.preventDefault(); mover(1); }
      else if (ev.key === "ArrowLeft") { ev.preventDefault(); mover(-1); }
      else if (ev.key === "Tab") {
        // el foco no se escapa del globo mientras la guía está abierta
        var f = $$("button:not([disabled])", globo);
        if (!f.length) return;
        var pri = f[0], ult = f[f.length - 1];
        if (ev.shiftKey && document.activeElement === pri) { ev.preventDefault(); ult.focus(); }
        else if (!ev.shiftKey && document.activeElement === ult) { ev.preventDefault(); pri.focus(); }
      }
    }

    function abrir() {
      if (capa || !recoger()) return;
      previo = document.activeElement;
      i = 0;
      capa = document.createElement("div");
      capa.className = "guia-capa";
      capa.innerHTML =
        '<div class="guia-foco"></div>' +
        '<div class="guia-globo" role="dialog" aria-modal="true" aria-labelledby="guia-t">' +
          '<p class="guia-cuenta" data-guia-cuenta></p>' +
          '<h2 id="guia-t" data-guia-titulo></h2>' +
          '<p data-guia-texto></p>' +
          '<div class="guia-botones">' +
            '<button type="button" class="btn btn-ghost" data-guia-saltar>Saltar</button>' +
            '<span class="guia-nav">' +
              '<button type="button" class="btn btn-ghost" data-guia-atras>Atrás</button>' +
              '<button type="button" class="btn btn-primary" data-guia-siguiente>Siguiente</button>' +
            '</span>' +
          '</div>' +
        '</div>';
      document.body.appendChild(capa);
      document.documentElement.classList.add("guia-abierta");
      foco = $(".guia-foco", capa);
      globo = $(".guia-globo", capa);
      $("[data-guia-saltar]", globo).addEventListener("click", function () { cerrar(true); });
      $("[data-guia-atras]", globo).addEventListener("click", function () { mover(-1); });
      $("[data-guia-siguiente]", globo).addEventListener("click", function () { mover(1); });
      capa.addEventListener("click", function (ev) { if (ev.target === capa) cerrar(true); });
      document.addEventListener("keydown", teclas, true);
      window.addEventListener("resize", situar);
      window.addEventListener("scroll", situar, true);
      pintar();
      $("[data-guia-siguiente]", globo).focus();
    }

    $$("[data-guia-abrir]").forEach(function (b) {
      b.addEventListener("click", function (ev) { ev.preventDefault(); abrir(); });
    });

    var vista = "1";
    try { vista = localStorage.getItem(CLAVE); } catch (e) { vista = "1"; }
    if (!vista) setTimeout(abrir, 900);   // solo la primera vez
  }

  /* ---------- arranque ---------- */
  function boot() {
    safe(initHeader, "initHeader");
    safe(initGallery, "initGallery");
    safe(initCompareButtons, "initCompareButtons");
    safe(initComparador, "initComparador");
    safe(initFilters, "initFilters");
    safe(initReveals, "initReveals");
    safe(initGuia, "initGuia");
    document.documentElement.classList.add("is-ready");
  }

  // La versión de un solo archivo (vista previa) reutiliza este arranque tras cambiar de página.
  window.__LEIDO_BOOT__ = boot;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
