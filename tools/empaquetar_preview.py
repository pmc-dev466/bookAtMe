#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Empaqueta el sitio generado en UN solo archivo HTML autocontenido, para poder
enseñarlo con un enlace temporal sin necesidad de hosting.

    python tools/empaquetar_preview.py

Sale en  preview/leido-preview.html

Es SOLO una vista previa. La web de verdad son los 26 archivos sueltos que
genera tools/build_site.py: esos son los que se suben al hosting y los que
Google puede leer. Aqui las paginas viven todas dentro del mismo archivo y se
cambian con un router de hash (#/pagina.html).
"""
import base64, glob, io, mimetypes, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(BASE, "preview", "leido-preview.html")
INICIO = "index.html"


def leer(p):
    with io.open(os.path.join(BASE, p), encoding="utf-8") as f:
        return f.read()


def data_uri(ruta):
    tipo = mimetypes.guess_type(ruta)[0] or "application/octet-stream"
    with open(os.path.join(BASE, ruta), "rb") as f:
        return "data:%s;base64,%s" % (tipo, base64.b64encode(f.read()).decode("ascii"))


def trozo(html, etiqueta):
    m = re.search(r"<%s\b[^>]*>(.*)</%s>" % (etiqueta, etiqueta), html, re.S)
    return m.group(1) if m else ""


def main():
    paginas = sorted(os.path.basename(p) for p in glob.glob(os.path.join(BASE, "*.html")))
    if INICIO not in paginas:
        print("[!] Falta index.html: ejecuta antes tools/build_site.py")
        return 1

    # Las imagenes se incrustan UNA sola vez en un mapa ruta -> data URI.
    # En el HTML dejamos data-img="ruta" y un script las resuelve al vuelo;
    # si se incrustaran en cada <img> el archivo pesaria diez veces mas.
    cache = {}
    def sustituir_img(m):
        ruta = m.group(1)
        if ruta not in cache:
            destino = os.path.join(BASE, ruta.replace("/", os.sep))
            if not os.path.exists(destino):
                return m.group(0)
            cache[ruta] = data_uri(ruta)
        return 'data-img="%s"' % ruta

    vistas, titulos = {}, {}
    base_html = leer(INICIO)
    for p in paginas:
        h = leer(p)
        cuerpo = trozo(h, "main")
        cuerpo = re.sub(r'src="(assets/[^"]+)"', sustituir_img, cuerpo)
        # enlaces internos -> rutas del router
        cuerpo = re.sub(r'href="(?!http|mailto|#)([a-z0-9\-]+\.html)(#[^"]*)?"',
                        lambda m: 'href="#/%s%s"' % (m.group(1), m.group(2) or ""), cuerpo)
        vistas[p] = cuerpo
        t = re.search(r"<title>(.*?)</title>", h, re.S)
        titulos[p] = t.group(1).strip() if t else "Leído"

    cabecera = re.sub(r'href="(?!http|mailto|#)([a-z0-9\-]+\.html)"',
                      lambda m: 'href="#/%s"' % m.group(1),
                      re.sub(r'src="(assets/[^"]+)"', sustituir_img, trozo(base_html, "header")))
    pie = re.sub(r'href="(?!http|mailto|#)([a-z0-9\-]+\.html)"',
                 lambda m: 'href="#/%s"' % m.group(1), trozo(base_html, "footer"))
    barra_aff = re.search(r'<div class="aff-bar">.*?</div>', base_html, re.S).group(0)
    barra_aff = re.sub(r'href="(?!http|mailto|#)([a-z0-9\-]+\.html)"',
                       lambda m: 'href="#/%s"' % m.group(1), barra_aff)
    barra_cmp = re.search(r'<div class="cmp-bar".*?</div>\s*(?=<footer)', base_html, re.S).group(0)
    barra_cmp = re.sub(r'href="(?!http|mailto|#)([a-z0-9\-]+\.html)"',
                       lambda m: 'href="#/%s"' % m.group(1), barra_cmp)

    css = leer("styles.css")
    js = leer("main.js")
    db = leer("lib/db.js")
    favicon = data_uri("assets/favicon.svg")

    vistas_js = ",\n".join(
        '%s: {t: %s, h: %s}' % (js_str(p), js_str(titulos[p]), js_str(vistas[p]))
        for p in paginas)

    # En modo --artifact el anfitrion ya pone <!doctype>/<html>/<head>/<body>,
    # asi que solo entregamos el contenido.
    artifact = "--artifact" in sys.argv
    cabeza = """<title>Leído</title>
<link rel="icon" href="%s" type="image/svg+xml">""" % favicon if artifact else """<!DOCTYPE html>
<html lang="es" class="js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<meta name="description" content="Comparativa de los libros más vendidos en Amazon España: ficha completa, gráfico de valoración, pros y contras y comparador lado a lado.">
<link rel="icon" href="%s" type="image/svg+xml">""" % (titulos[INICIO], favicon)
    cierre = "" if artifact else "</body>\n</html>"

    doc = """%s
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;1,6..72,400&display=swap">
<style>
%s
</style>
%s
<a class="skip-link" href="#main">Ir al contenido</a>
%s
%s
<main id="main"></main>
%s
%s
<script>
window.__IMGS__ = %s;
</script>
<script>
%s
</script>
<script>
/* Router de la vista previa de un solo archivo. En el sitio real cada página
   es un .html independiente y esto no existe. */
(function () {
  "use strict";
  var VISTAS = {
%s
  };
  var INICIO = %s;
  var main = document.getElementById("main");

  /* Las portadas viven en window.__IMGS__ (ruta -> data URI). */
  function resolver(raiz) {
    var m = window.__IMGS__ || {};
    (raiz.querySelectorAll ? raiz : document).querySelectorAll("img[data-img]").forEach(function (im) {
      var r = im.getAttribute("data-img");
      if (m[r]) { im.src = m[r]; im.removeAttribute("data-img"); }
    });
    (raiz.querySelectorAll ? raiz : document).querySelectorAll('img[src^="assets/"]').forEach(function (im) {
      var r = im.getAttribute("src");
      if (m[r]) im.src = m[r];
    });
  }
  new MutationObserver(function (muts) {
    muts.forEach(function (mu) {
      mu.addedNodes.forEach(function (n) { if (n.nodeType === 1) resolver(n.matches ? n : document); });
    });
  }).observe(document.body, { childList: true, subtree: true });

  function ruta() {
    var h = location.hash || "";
    if (h.indexOf("#/") !== 0) return INICIO;
    var p = h.slice(2).split("#")[0].split("?")[0];
    return VISTAS[p] ? p : INICIO;
  }
  function pintar(scroll) {
    var p = ruta(), v = VISTAS[p];
    main.innerHTML = v.h;
    resolver(main);
    document.title = v.t;
    document.querySelectorAll(".nav-links a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (href === "#/" + p) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    if (window.__LEIDO_BOOT__) window.__LEIDO_BOOT__();
    if (scroll !== false) window.scrollTo({ top: 0, behavior: "auto" });
    var frag = (location.hash.split("#")[2]);
    if (frag) {
      var el = document.getElementById(frag);
      if (el) el.scrollIntoView();
    }
  }
  window.addEventListener("hashchange", function () { pintar(true); });
  document.documentElement.classList.add("js");
  pintar(false);
})();
</script>
%s
""" % (cabeza, css, ("" if artifact else "</head>\n<body>"), barra_aff, cabecera, barra_cmp, pie,
       js_str_obj(cache), db + "\n" + js, vistas_js, js_str(INICIO), cierre)

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with io.open(SALIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    kb = os.path.getsize(SALIDA) / 1024.0
    print("[+] %s · %d páginas · %.1f MB" % (os.path.relpath(SALIDA, BASE), len(paginas), kb / 1024.0))
    return 0


def js_str(s):
    import json
    return json.dumps(s, ensure_ascii=False)


def js_str_obj(d):
    import json
    return json.dumps(d, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
