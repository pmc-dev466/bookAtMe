# -*- coding: utf-8 -*-
"""Comprueba el sitio ya generado, sin abrir el navegador.

    python tools/comprobar_sitio.py

Revisa, sobre los .html de verdad:
  1. Que TODOS los enlaces internos apunten a algo que existe (menu, submenus,
     migas, pies, tarjetas, botones...). Un enlace roto no se ve hasta que
     alguien lo pulsa.
  2. Que todos los src de imagenes existan y lleven medidas (width/height): sin
     ellas la pagina pega saltos mientras carga.
  3. Que cada pagina tenga un solo <h1>, titulo unico, meta description,
     canonical y miniatura para compartir.
  4. Que ninguna imagen pase de 8 MB.
  5. Que los enlaces de afiliado conserven su etiqueta.
  6. Accesibilidad basica: alt en imagenes, idioma, enlace para saltar al
     contenido, y que todo boton/enlace sin texto lleve aria-label.

Devuelve 1 si hay algo roto, para poder encadenarlo antes de publicar.
"""
import io
import os
import re
import sys
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_IMAGEN_MB = 8

fallos = []
avisos = []


def fallo(pagina, txt):
    fallos.append("%s: %s" % (pagina, txt))


def aviso(pagina, txt):
    avisos.append("%s: %s" % (pagina, txt))


def existe(ruta_rel):
    return os.path.exists(os.path.join(RAIZ, ruta_rel.replace("/", os.sep)))


def main():
    paginas = sorted(f for f in os.listdir(RAIZ) if f.endswith(".html"))
    if not paginas:
        print("[!] No hay paginas generadas. Ejecuta antes tools/build_site.py")
        return 1

    titulos = defaultdict(list)
    destinos = set()

    for p in paginas:
        doc = io.open(os.path.join(RAIZ, p), encoding="utf-8").read()
        absoluta = (p == "404.html")   # la 404 se sirve desde cualquier ruta

        # --- enlaces internos ---
        for m in re.finditer(r'href="([^"]+)"', doc):
            h = m.group(1)
            if h.startswith(("http://", "https://", "//", "#", "mailto:", "tel:", "data:")):
                continue
            destino = h.split("#")[0].split("?")[0]
            if not destino:
                continue
            destino = destino[1:] if destino.startswith("/") else destino
            destinos.add(destino)
            if not existe(destino):
                fallo(p, "enlace roto -> %s" % h)

        # --- imagenes ---
        for m in re.finditer(r"<img\b[^>]*>", doc):
            tag = m.group(0)
            src = re.search(r'src="([^"]+)"', tag)
            if not src:
                fallo(p, "hay un <img> sin src")
                continue
            s = src.group(1)
            if s.startswith(("http", "data:")):
                continue
            s = s[1:] if s.startswith("/") else s
            if not existe(s):
                fallo(p, "imagen que no existe -> %s" % s)
                continue
            mb = os.path.getsize(os.path.join(RAIZ, s.replace("/", os.sep))) / 1048576.0
            if mb > MAX_IMAGEN_MB:
                fallo(p, "imagen de %.1f MB (maximo %d) -> %s" % (mb, MAX_IMAGEN_MB, s))
            if 'width=' not in tag or 'height=' not in tag:
                aviso(p, "imagen sin medidas (da saltos al cargar) -> %s" % s)
            if 'alt=' not in tag:
                fallo(p, "imagen sin alt -> %s" % s)

        # --- cabecera y SEO ---
        h1 = len(re.findall(r"<h1\b", doc))
        if h1 != 1:
            fallo(p, "tiene %d <h1> (debe haber exactamente 1)" % h1)

        t = re.search(r"<title>(.*?)</title>", doc, re.S)
        if not t or not t.group(1).strip():
            fallo(p, "sin <title>")
        else:
            titulos[t.group(1).strip()].append(p)

        d = re.search(r'<meta name="description" content="([^"]*)"', doc)
        if not d or len(d.group(1)) < 50:
            fallo(p, "meta description ausente o demasiado corta")
        elif len(d.group(1)) > 165:
            aviso(p, "meta description de %d caracteres (Google corta sobre 160)" % len(d.group(1)))

        if not absoluta and '<link rel="canonical"' not in doc:
            fallo(p, "sin URL canonica")
        if not absoluta and 'property="og:image"' not in doc:
            fallo(p, "sin miniatura para compartir (og:image)")
        if 'name="robots"' not in doc:
            fallo(p, "sin meta robots")
        if absoluta and "noindex" not in doc:
            fallo(p, "la pagina de error deberia ser noindex")

        # --- orden de encabezados ---
        # Saltarse un nivel (de h1 a h3) rompe el indice que usan los lectores
        # de pantalla para moverse por la pagina.
        niveles = [int(m.group(1)) for m in re.finditer(r"<h([1-6])", doc)]
        for i in range(1, len(niveles)):
            if niveles[i] - niveles[i - 1] > 1:
                fallo(p, "salta de h%d a h%d (no se puede saltar un nivel)"
                      % (niveles[i - 1], niveles[i]))
                break

        # --- la miniatura de compartir existe de verdad ---
        og = re.search(r'property="og:image" content="([^"]+)"', doc)
        if og:
            local = og.group(1).split("/", 3)[-1] if og.group(1).startswith("http") else og.group(1)
            if not existe(local):
                fallo(p, "la miniatura para compartir no existe -> %s" % local)

        # --- accesibilidad basica ---
        if '<html lang="es"' not in doc:
            fallo(p, "al <html> le falta lang=\"es\"")
        if 'class="skip-link"' not in doc:
            fallo(p, "sin enlace para saltar al contenido")
        for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", doc, re.S):
            tag, dentro = m.group(0), re.sub(r"<[^>]+>", "", m.group(1)).strip()
            # una imagen con alt tambien da nombre al enlace: cuenta como texto
            con_alt = re.search(r'<img[^>]*alt="[^"]+"', m.group(1))
            if not dentro and not con_alt and "aria-label" not in tag and "aria-hidden" not in tag:
                fallo(p, "enlace sin texto ni aria-label: %s" % tag[:70])
        for m in re.finditer(r"<button\b[^>]*>(.*?)</button>", doc, re.S):
            tag, dentro = m.group(0), re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if not dentro and "aria-label" not in tag:
                fallo(p, "boton sin texto ni aria-label: %s" % tag[:70])

        # --- afiliados ---
        for m in re.finditer(r'href="(https://www\.amazon\.[^"]+)"', doc):
            if "tag=" not in m.group(1):
                fallo(p, "enlace a Amazon SIN etiqueta de afiliado")

    for titulo, ps in titulos.items():
        if len(ps) > 1:
            fallo(", ".join(ps), "comparten el mismo <title>: %s" % titulo)

    # paginas que existen pero a las que no llega ningun enlace
    for p in paginas:
        if p not in destinos and p not in ("index.html", "404.html"):
            aviso(p, "ninguna pagina enlaza aqui (huerfana)")

    print("=" * 62)
    print("Comprobacion del sitio: %d paginas" % len(paginas))
    print("=" * 62)
    if fallos:
        print("\n[X] %d FALLOS" % len(fallos))
        for f in fallos:
            print("   -", f)
    if avisos:
        print("\n[!] %d avisos" % len(avisos))
        for a in avisos:
            print("   -", a)
    if not fallos and not avisos:
        print("\n[OK] Todo correcto.")
    elif not fallos:
        print("\n[OK] Sin fallos.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
