#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de BookAtMe!
Lee datos/libros.json y escribe TODAS las paginas del sitio.
Ningun libro se escribe a mano: anadir un libro = anadir un registro al JSON
y volver a ejecutar este script.

    python tools/build_site.py

Sube VER en cada ejecucion (ya lo hace solo con la fecha de hoy) para que el
navegador no sirva CSS/JS antiguos.
"""
import json, os, re, html, math, datetime, shutil, sys, time, io

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(BASE, "datos", "libros.json")
# Lleva la hora y el minuto a propósito: con solo la fecha, dos reconstrucciones del
# mismo día comparten ?v= y el navegador sigue sirviendo el CSS viejo de la caché.
# Eso hace perder horas persiguiendo fallos que ya estaban arreglados.
VER = datetime.datetime.now().strftime("%Y%m%d-%H%M")
SITIO = "BookAtMe!"
# Cuantos libros salen en la estanteria 3D. El resto del catalogo vive en las
# paginas normales: con mas de 10 la balda va lenta y no se distingue nada.
LIBROS_EN_ESTANTERIA = 10

def _dominio():
    """La direccion publica de la web. Manda, por este orden:
         python tools/build_site.py --dominio https://loquesea.pages.dev
         BOOKATME_DOMINIO=https://loquesea.pages.dev python tools/build_site.py
       y si no, el de aqui abajo.
    CAMBIA ESTA LINEA cuando sepas la URL definitiva que te da Cloudflare: de ella
    salen el sitemap, las URLs canonicas y la miniatura al compartir."""
    for i, a in enumerate(sys.argv):
        if a == "--dominio" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith("--dominio="):
            return a.split("=", 1)[1]
    return os.environ.get("BOOKATME_DOMINIO", "https://bookatme.pages.dev")

DOMINIO = _dominio().rstrip("/")
FECHA_LARGA = "25 de agosto de 2026"

# ---------------------------------------------------------------- utilidades
def e(s):
    return html.escape("" if s is None else str(s), quote=True)

def eur(n):
    if n is None:
        return "—"
    return ("%.2f" % n).replace(".", ",") + " €"

def miles(n):
    if n is None:
        return "—"
    return "{:,}".format(int(n)).replace(",", ".")

def dec(n, suf=""):
    if n is None:
        return "—"
    s = ("%g" % n).replace(".", ",")
    return s + suf

def estrellas(v):
    """Cinco estrellas con relleno parcial exacto (sin glifos exoticos)."""
    if v is None:
        return ""
    pct = max(0.0, min(100.0, float(v) / 5 * 100))
    return '<span class="stars-glyph" aria-hidden="true"><b style="width:%.1f%%"></b></span>' % pct

def plural(n, uno, muchos):
    return "%d %s" % (n, uno if n == 1 else muchos)

def descuento(b):
    if b.get("precio") and b.get("precio_lista") and b["precio_lista"] > b["precio"]:
        return round((b["precio_lista"] - b["precio"]) / b["precio_lista"] * 100)
    return 0

def nota_media(b):
    vals = [b.get(k) for k in EJES_K if isinstance(b.get(k), (int, float))]
    return round(sum(vals) / len(vals), 1) if vals else None

EJES = [("score_ritmo", "Ritmo"), ("score_personajes", "Personajes"),
        ("score_profundidad", "Profundidad"), ("score_originalidad", "Originalidad"),
        ("score_facilidad", "Facilidad"), ("score_calidad_precio", "Calidad-precio")]
EJES_K = [k for k, _ in EJES]

IC = {
 "check": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 10.5l4 4 8-9"/></svg>',
 "cross": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15"/></svg>',
 "amazon": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 16h6M4.5 7h11l-1 7.5h-9L4.5 7zM7.5 7V5a2.5 2.5 0 015 0v2"/></svg>',
 "book": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4.5h7a2 2 0 012 2V16a2 2 0 00-2-2H4V4.5zM16 4.5H9"/></svg>',
 "clock": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l2.5 2"/></svg>',
 "scale": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 4v13M5 17h10M4 8l3-4 3 4M13 10l3-4 3 4"/></svg>',
 "eye": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1.7 10S4.6 5 10 5s8.3 5 8.3 5-2.9 5-8.3 5-8.3-5-8.3-5z"/><circle cx="10" cy="10" r="2.2"/></svg>',
 "spark": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2.5l1.8 4.7 4.7 1.8-4.7 1.8L10 15.5 8.2 10.8 3.5 9l4.7-1.8L10 2.5z"/></svg>',
 "tag": '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3h6.2l7.8 7.8-6.2 6.2L3 9.2V3z"/><circle cx="6.6" cy="6.6" r="1.1"/></svg>',
}

# ---------------------------------------------------------------- plantilla
def pagina(titulo, descripcion, cuerpo, activo="", extra_head="", jsonld=None, clase="", guia=""):
    ld = ""
    if jsonld:
        for bloque in (jsonld if isinstance(jsonld, list) else [jsonld]):
            ld += '<script type="application/ld+json">%s</script>' % json.dumps(bloque, ensure_ascii=False)
    return """<!DOCTYPE html>
<!--
  ==========================================================================
   ARCHIVO GENERADO - NO LO EDITES.

   Este archivo lo escribe tools/build_site.py y se sobrescribe ENTERO cada
   vez que se reconstruye la web. Cualquier cambio que hagas aqui se pierde.

   Lo que buscas esta en:
     datos/libros.json     los libros: pros, contras, descripciones, notas
     styles.css            colores, tamanos, margenes
     tools/build_site.py   los textos que salen en todas las paginas

   Y luego doble clic en actualizar.bat (o deja abierto desarrollo.bat).
  ==========================================================================
-->
<html lang="es"%s>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<meta property="og:type" content="website">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:locale" content="es_ES">
<meta property="og:site_name" content="BookAtMe!">
<meta name="twitter:card" content="summary_large_image">
<!--SEO-->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Las tipografias no bloquean el pintado: se cargan como hoja de impresion
     y pasan a valer para pantalla al terminar. Antes, si fonts.googleapis.com iba
     lento, la web entera se quedaba en blanco esperando a un servidor ajeno.
     Con display=swap el texto se ve desde el primer momento con la del sistema. -->
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,400&display=swap">
<link rel="stylesheet" media="print" onload="this.media=&#39;all&#39;;this.onload=null" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,400&display=swap">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,400&display=swap"></noscript>
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="assets/icono-180.png">
<link rel="manifest" href="site.webmanifest">
<meta name="theme-color" content="#14161C">
<link rel="stylesheet" href="styles.css?v=%s">
<script>document.documentElement.className+=" js";</script>
%s%s
</head>
<body>
<a class="skip-link" href="#main">Ir al contenido</a>
%s
%s
<main id="main"%s>
%s
</main>
%s
%s
%s
<script defer src="lib/db.js?v=%s"></script>
<script defer src="main.js?v=%s"></script>
%s
</body>
</html>
""" % (' class="%s"' % clase if clase else "", e(titulo), e(descripcion), e(titulo), e(descripcion),
       VER, extra_head, ld, barra_afiliados(), cabecera(activo, guia), "", cuerpo, barra_comparador(), pie(),
       guia_json(guia), VER, VER, analitica())


GUIAS_INTERFAZ = {
    # Ojo al orden: los pasos van de arriba abajo de la pagina. Si saltan hacia
    # atras, la guia da tumbos. Y del 2 al 5 apuntan todos DENTRO de la misma
    # tarjeta, para no ir dando saltos entre libros distintos.
    "inicio": [
        (".nav-links",
         "Todo empieza por aquí",
         "Los libros están ordenados por género. En «Estantería» los verás en 3D y podrás "
         "hojearlos, y en «Comparador» puedes enfrentar hasta cuatro a la vez."),
        (".book-card .card-badges",
         "Cada libro, de un vistazo",
         "El género, y si está rebajado o destacado. Nuestra nota propia sobre 10 no está aquí: "
         "está dentro, en la ficha del libro, junto al gráfico de sus seis ejes."),
        (".book-card .stars",
         "Esta nota es de Amazon",
         "La media de los lectores y cuántos han opinado. Es un dato de Amazon, no nuestro: "
         "las dos notas aparecen por separado en la ficha y nunca las mezclamos."),
        (".book-card .price",
         "El precio, con su fecha",
         "Es el que había el día que lo miramos, no el de ahora mismo. Por eso decimos «precio "
         "orientativo»: el que vale es el que veas en Amazon al comprar."),
        (".book-card .cmp-add",
         "Guarda los que dudes",
         "Marca «Comparar» en dos o más libros y podrás verlos enfrentados en una tabla, "
         "con la mejor cifra de cada fila resaltada."),
        (".book-card .btn-buy",
         "Y cuando lo tengas claro",
         "Este botón lleva a Amazon. Es un enlace de afiliado: si compras nos llevamos una "
         "comisión y a ti te cuesta exactamente lo mismo. Por eso también contamos lo malo "
         "de cada libro."),
    ],
    "comparador": [
        ("#buscar",
         "Busca el libro",
         "Escribe el título, el autor o el género. Si no encuentra nada, te lo dirá; "
         "y si ya lo tienes elegido, también."),
        ("[data-cmp-slots]",
         "Hasta cuatro a la vez",
         "Los libros elegidos aparecen aquí. Para quitar uno, pulsa la ✕ de su esquina."),
        ("[data-cmp-out]",
         "La tabla los enfrenta",
         "Con dos o más verás la comparativa fila a fila. La dirección de la barra del navegador "
         "guarda tu selección: cópiala para enseñársela a alguien."),
    ],
    "estanteria": [
        ("#estanteria-canvas",
         "Una estantería de verdad",
         "Gira con la rueda del ratón o con las flechas del teclado. Haz clic en un libro para "
         "cogerlo. Aquí solo están los diez más vendidos de Amazon.es."),
        (".est-acciones",
         "Ábrelo y hojéalo",
         "Al abrir un libro puedes pasar sus páginas: dentro está la sinopsis, lo que nos gusta, "
         "lo que no, la ficha y nuestra nota. Arrastra la tapa para cerrarlo."),
        (".est-indice",
         "Dónde estás",
         "Este contador te dice por qué libro vas. Si prefieres verlos en lista normal, "
         "tienes el resto del catálogo en el menú."),
    ],
}

def guia_json(clave):
    """Los pasos de la guia, para que los lea main.js. Si la clave no existe,
    la pagina simplemente no tiene guia y no pasa nada."""
    pasos = GUIAS_INTERFAZ.get(clave)
    if not pasos:
        return ""
    datos = {"clave": clave,
             "pasos": [{"sel": s, "titulo": t, "texto": x} for s, t, x in pasos]}
    return ('<script type="application/json" id="guia-pasos">%s</script>'
            % json.dumps(datos, ensure_ascii=False))

# El identificador de Cloudflare Web Analytics. Se saca del panel de Cloudflare:
# Analytics & Logs -> Web Analytics -> Add a site. Es una cadena de 32 caracteres.
# Mientras este vacio la web no carga ninguna analitica, y no da ningun error.
#
# Cloudflare Web Analytics NO usa cookies ni guarda datos personales, asi que
# esta web SIGUE sin necesitar banner de consentimiento.
ANALYTICS_TOKEN = ""

def analitica():
    if not ANALYTICS_TOKEN:
        return "<!-- Analitica desactivada: rellena ANALYTICS_TOKEN en tools/build_site.py -->"
    return ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
            'data-cf-beacon=%s></script>' % json.dumps(json.dumps({"token": ANALYTICS_TOKEN})))

def barra_afiliados():
    return ('<div class="aff-bar">Como afiliados de Amazon, ganamos una comisión por las compras que cumplen los requisitos. '
            'Para ti el precio es el mismo. <a href="aviso-afiliados.html">Más información</a>.</div>')

def boton_guia():
    """El circulito con la interrogacion, al lado del Comparador. Solo sale en
    las paginas que tienen guia, y solo con JavaScript: sin el no haria nada."""
    return ('<button class="btn-guia" type="button" data-guia-abrir '
            'aria-label="Ver la guía de la web" title="Ver la guía de la web">'
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<circle cx="10" cy="10" r="7.6"/><path d="M7.9 7.6a2.2 2.2 0 013.9 1.2c0 1.5-2 1.6-2 2.9"/>'
            '<path d="M9.8 14.4h.02"/></svg></button>')

def cabecera(activo="", guia=""):
    def li(href, txt, key):
        cur = ' aria-current="page"' if key == activo else ""
        return '<a href="%s"%s>%s</a>' % (href, cur, txt)
    cats = "".join('<a href="categoria-%s.html">%s</a>' % (c["id"], e(c["nombre"])) for c in CATS)
    return """<header class="site-head" data-head>
  <div class="wrap head-inner">
    <a class="brand" href="index.html">
      <span class="brand-mark">Book<span>At</span>Me<em>!</em></span>
      <span class="brand-tag">Comparativas de libros</span>
    </a>
    <nav class="nav-links" aria-label="Principal">
      %s
      %s
      %s
      %s
      %s
      <a class="nav-cta" href="comparador.html">Comparador<span class="nav-cta-count" data-cmp-count>0</span></a>
    </nav>
    %s
    <button class="nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-controls="nav-drawer" aria-label="Abrir menú"><i></i><i></i><i></i></button>
  </div>
  <div class="nav-drawer" id="nav-drawer" data-nav-drawer>
    <a href="index.html">Inicio</a>
    <a href="estanteria.html">La estantería en 3D</a>
    <a href="comparador.html">Comparador</a>
    <a href="ofertas.html">Ofertas</a>
    <a href="%s">Guías de compra</a>
    <div class="drawer-label">Por género</div>
    %s
    <div class="drawer-label">La casa</div>
    %s<a href="como-elegimos.html">Cómo elegimos</a>
    <a href="aviso-afiliados.html">Aviso de afiliados</a>
  </div>
</header>""" % (li("index.html", "Inicio", "inicio"),
                li("estanteria.html", "Estantería", "estanteria"),
                li(GUIAS[0]["slug"] + ".html", "Guías", "guias"),
                li("ofertas.html", "Ofertas", "ofertas"),
                li("como-elegimos.html", "Cómo elegimos", "como"),
                boton_guia() if guia else "",
                GUIAS[0]["slug"] + ".html",
                '<a href="#" data-guia-abrir>Ver la guía de la web</a>' if guia else "",
                cats)

def barra_comparador():
    return """<div class="cmp-bar" data-cmp-bar role="status">
  <span class="cmp-bar-text" data-cmp-bar-text></span>
  <button class="btn-clear" type="button" data-cmp-clear>Vaciar</button>
  <a class="btn btn-buy" href="comparador.html">Comparar</a>
</div>"""

def pie():
    cats = "".join('<li><a href="categoria-%s.html">%s</a></li>' % (c["id"], e(c["nombre"])) for c in CATS)
    guias = "".join('<li><a href="%s.html">%s</a></li>' % (g["slug"], e(g["nav"])) for g in GUIAS)
    return """<footer class="site-foot">
  <div class="wrap">
    <div class="foot-grid">
      <div class="foot-brand">
        <span class="brand-mark">Book<span style="color:#A87C2E">At</span>Me<em>!</em></span>
        <p>Comparativas de libros hechas con datos reales de Amazon.es y una opinión propia. Sin listas patrocinadas y sin puestos a la venta.</p>
      </div>
      <div><h4>Por género</h4><ul>%s</ul></div>
      <div><h4>Guías</h4><ul>%s<li><a href="ofertas.html">Ofertas</a></li><li><a href="comparador.html">Comparador</a></li></ul></div>
      <div><h4>La casa</h4><ul><li><a href="#" data-guia-abrir>Ver la guía de la web</a></li>
        <li><a href="como-elegimos.html">Cómo elegimos</a></li>
        <li><a href="aviso-afiliados.html">Aviso de afiliados</a></li>
        <li><a href="privacidad.html">Privacidad y cookies</a></li>
      </ul></div>
    </div>
    <div class="foot-legal">
      <p><strong>Aviso de afiliados:</strong> %s participa en el Programa de Afiliados de Amazon EU, un programa de publicidad
      que permite a los sitios web obtener comisiones por publicitar e incluir enlaces a Amazon.es. Como Afiliado de Amazon,
      obtenemos ingresos por las compras adscritas que cumplen los requisitos aplicables. El precio que pagas es el mismo.
      Amazon y el logotipo de Amazon son marcas comerciales de Amazon.com, Inc. o sus filiales.<br>
      Los precios y la disponibilidad mostrados son los del %s y pueden haber cambiado. El precio válido es el que aparece en Amazon en el momento de la compra.</p>
      <p>© 2026 %s</p>
    </div>
  </div>
</footer>""" % (cats, guias, SITIO, FECHA_LARGA, SITIO)

# ---------------------------------------------------------------- fragmentos
def boton_compra(b, grande=False, texto=None):
    if texto is None:
        texto = "Ver en Amazon" if b.get("precio") is not None else "Ver precio en Amazon"
    return ('<a class="btn btn-buy%s" href="%s" target="_blank" rel="sponsored nofollow noopener">%s%s</a>'
            % (" btn-buy-lg" if grande else "", e(b["affiliate_url"]), IC["amazon"], e(texto)))

def precio_html(b):
    if b.get("precio") is None:
        return '<span class="price-none">Consultar en Amazon</span>'
    was = ""
    if b.get("precio_lista") and b["precio_lista"] > b["precio"]:
        was = '<span class="price-was">%s</span>' % eur(b["precio_lista"])
    return '<span class="price"><span class="price-now">%s</span>%s</span>' % (eur(b["precio"]), was)

def estrellas_html(b):
    if b.get("valoracion_media") is None:
        return '<span class="stars"><span class="stars-count">Sin valoraciones aún</span></span>'
    return ('<span class="stars">%s'
            '<span>%s</span><span class="stars-count">(%s)</span></span>'
            % (estrellas(b["valoracion_media"]), dec(b["valoracion_media"]), miles(b.get("resenas_cantidad"))))

def boton_comparar(b):
    return ('<button class="cmp-add" type="button" data-cmp-add="%s" aria-pressed="false">'
            '<span class="box"></span><span data-cmp-label>Comparar</span></button>' % e(b["id"]))

def tarjeta(b, mostrar_cat=True, con_boton=True):
    off = descuento(b)
    badges = []
    if mostrar_cat:
        badges.append('<span class="badge badge-cat">%s</span>' % e(cat_nombre(b["categoria"])))
    if off >= 5:
        badges.append('<span class="badge badge-off">−%d %%</span>' % off)
    if b.get("isFeatured"):
        badges.append('<span class="badge badge-top">Destacado</span>')
    return """<article class="book-card" data-book="%s" data-formato="%s" data-reveal>
  <a href="libro-%s.html" aria-label="Ver la ficha de %s"><span class="cover"><img src="%s" alt="Portada de %s, de %s" loading="lazy" decoding="async" width="400" height="600"></span></a>
  <div class="card-badges">%s</div>
  <h3><a href="libro-%s.html">%s</a></h3>
  <p class="author">%s</p>
  %s
  <div class="card-foot">%s<span class="badge badge-cat">%s p.</span></div>
  %s
  %s
</article>""" % (e(b["id"]), e(b.get("formato")), e(b["id"]), e(b["titulo"]), e(b["imagenes"][0]),
                 e(b["titulo"]), e(b["autor"]), "".join(badges), e(b["id"]), e(b["titulo"]), e(b["autor"]),
                 estrellas_html(b), precio_html(b), miles(b.get("num_paginas")),
                 boton_compra(b) if con_boton else "", boton_comparar(b))

def cat_nombre(cid):
    for c in CATS:
        if c["id"] == cid:
            return c["nombre"]
    return cid

def cat_obj(cid):
    for c in CATS:
        if c["id"] == cid:
            return c
    return {"id": cid, "nombre": cid, "titulo": cid, "intro": ""}

# ---------------------------------------------------------------- radar SVG
def punto(c, r, i, n):
    a = (math.pi * 2 * i) / n - math.pi / 2
    return (round((c + r * math.cos(a)) * 10) / 10, round((c + r * math.sin(a)) * 10) / 10)

def radar_svg(b, size=300, color="#24503D"):
    C, R, N = size / 2, size * 0.36, len(EJES)
    # Las etiquetas se dibujan FUERA del hexagono, asi que la caja tiene que ser
    # mas ancha que el grafico. Con viewBox="0 0 300 300" se cortaban por los
    # lados: "Calidad-precio" empezaba en x=-39 y "Personajes" acababa en 339.
    PAD = size * 0.18
    out = ['<svg class="radar-svg" viewBox="%g 0 %g %g" role="img" aria-label="Valoración del editor de %s en seis ejes">'
           % (-PAD, size + 2 * PAD, size, e(b["titulo"]))]
    for j in range(1, 6):
        pts = " ".join("%g,%g" % punto(C, R * j / 5, i, N) for i in range(N))
        out.append('<polygon class="radar-ring" points="%s"/>' % pts)
    for i in range(N):
        x, y = punto(C, R, i, N)
        out.append('<line class="radar-axis" x1="%g" y1="%g" x2="%g" y2="%g"/>' % (C, C, x, y))
    pts, dots = [], []
    for i, (k, _) in enumerate(EJES):
        v = b.get(k) or 0
        x, y = punto(C, R * v / 10, i, N)
        pts.append("%g,%g" % (x, y))
        dots.append('<circle class="radar-dot" cx="%g" cy="%g" fill="%s"/>' % (x, y, color))
    out.append('<polygon class="radar-shape" points="%s" fill="%s" fill-opacity="0.17" stroke="%s"/>%s'
               % (" ".join(pts), color, color, "".join(dots)))
    for i, (k, lab) in enumerate(EJES):
        x, y = punto(C, R + 21, i, N)
        anchor = "start" if x > C + 4 else ("end" if x < C - 4 else "middle")
        out.append('<text class="radar-label" x="%g" y="%g" text-anchor="%s">%s</text>' % (x, y + 3, anchor, e(lab)))
    out.append("</svg>")
    return "".join(out)

def panel_radar(b):
    filas = "".join(
        '<div class="score-row"><span class="lbl">%s</span><span class="track"><span class="fill" style="width:%d%%"></span></span><span class="num">%s</span></div>'
        % (e(lab), (b.get(k) or 0) * 10, dec(b.get(k))) for k, lab in EJES)
    return """<div class="radar-panel" data-reveal>
  <div class="radar-head"><h3>El perfil del libro</h3><span class="badge badge-cat">Nota %s/10</span></div>
  <p class="radar-note">Valoración del editor sobre 10, no es un dato de Amazon. Explicamos el método en <a href="como-elegimos.html" style="color:var(--accent)">Cómo elegimos</a>.</p>
  <div style="max-width:340px;margin-inline:auto">%s</div>
  <div class="score-list">%s</div>
</div>""" % (dec(nota_media(b)), radar_svg(b), filas)

# ---------------------------------------------------------------- ficha
def tabla_specs(b):
    def fila(lab, val):
        nil = ' class="nil"' if val in (None, "", "—") else ""
        return "<tr><th>%s</th><td%s>%s</td></tr>" % (e(lab), nil, val if val not in (None, "") else "—")

    edicion = [
        fila("Formato", e(b.get("formato")).capitalize() if b.get("formato") else "—"),
        fila("Páginas", miles(b.get("num_paginas"))),
        fila("Editorial", e(b.get("editorial"))),
        fila("Fecha de publicación", e(b.get("fecha_publicacion"))),
        fila("Idioma", e(b.get("idioma"))),
        fila("Idioma original", e(b.get("idioma_original"))),
        fila("Traducción", e(b.get("traductor")) if b.get("traductor") else "—"),
    ]
    fisico = [
        fila("Dimensiones", (e(b.get("dimensiones_cm")) + " cm") if b.get("dimensiones_cm") else "—"),
        fila("Peso", (miles(b.get("peso_g")) + " g") if b.get("peso_g") else "—"),
        fila("ISBN-10", e(b.get("isbn_10"))),
        fila("ISBN-13", e(b.get("isbn_13"))),
        fila("Edad recomendada", e(b.get("edad_recomendada")) if b.get("edad_recomendada") else "—"),
    ]
    lectura = [
        fila("Tiempo de lectura estimado", ("≈ %s horas" % dec(b["horas_lectura"])) if b.get("horas_lectura") else "—"),
        fila("Precio por 100 páginas", eur(round(b["precio"] / b["num_paginas"] * 100, 2)) if (b.get("precio") and b.get("num_paginas")) else "—"),
        fila("Saga", (e(b["saga"]) + (" · n.º %d" % b["num_en_saga"] if b.get("num_en_saga") else "")) if b.get("saga") else "No pertenece a una saga"),
        fila("También en Kindle", "Sí" if b.get("disponible_kindle") else ("No" if b.get("disponible_kindle") is False else "—")),
        fila("También en audiolibro", "Sí" if b.get("disponible_audiolibro") else ("No" if b.get("disponible_audiolibro") is False else "—")),
    ]
    extra = ""
    if b.get("specs_extra"):
        filas = "".join(fila(k, e(v)) for k, v in b["specs_extra"].items())
        extra = '<table class="spec-table"><caption>Otros datos</caption><tbody>%s</tbody></table>' % filas

    return """<div class="spec-wrap">
<table class="spec-table"><caption>La edición</caption><tbody>%s</tbody></table>
<table class="spec-table"><caption>Formato y medidas</caption><tbody>%s</tbody></table>
<table class="spec-table"><caption>Lectura y disponibilidad</caption><tbody>%s</tbody></table>
%s
</div>""" % ("".join(edicion), "".join(fisico), "".join(lectura), extra)

def galeria(b):
    imgs = b.get("imagenes") or []
    if not imgs:
        return ""
    thumbs = ""
    if len(imgs) > 1:
        thumbs = '<div class="gallery-thumbs">%s</div>' % "".join(
            '<button type="button" data-gallery-thumb data-src="%s" data-alt="%s" aria-current="%s" aria-label="Ver imagen %d"><img src="%s" alt="" loading="lazy" decoding="async" width="120" height="180"></button>'
            % (e(src), "Imagen %d de %s" % (i + 1, e(b["titulo"])), "true" if i == 0 else "false", i + 1, e(src))
            for i, src in enumerate(imgs))
    else:
        thumbs = '<p class="gallery-single">Amazon solo publica una imagen de este título.</p>'
    return """<div data-gallery>
  <div class="gallery-main"><img data-gallery-main src="%s" alt="Portada de %s, de %s" fetchpriority="high" width="600" height="900"></div>
  %s
</div>""" % (e(imgs[0]), e(b["titulo"]), e(b["autor"]), thumbs)

def pros_contras(b):
    pros = "".join("<li>%s<span>%s</span></li>" % (IC["check"], e(p)) for p in b.get("pros", []))
    cons = "".join("<li>%s<span>%s</span></li>" % (IC["cross"], e(p)) for p in b.get("contras", []))
    return """<div class="pc" data-reveal>
  <div class="pc-col pc-pros"><h3>%s A favor</h3><ul>%s</ul></div>
  <div class="pc-col pc-cons"><h3>%s En contra</h3><ul>%s</ul></div>
</div>
<div class="ideal" data-reveal><b>Ideal para</b>%s</div>""" % (IC["check"], pros, IC["cross"], cons, e(b.get("ideal_para", "")))

def resenas_html(b):
    items = "".join("""<article class="review">
  <div class="review-head"><span class="who">%s</span><span aria-label="%s de 5 estrellas">%s</span><span class="when">%s</span></div>
  <h4>%s</h4><p>%s</p>
  <p class="review-meta">Reseña publicada en Amazon.es · %s</p>
</article>""" % (e(r.get("autor")), e(r.get("estrellas")), estrellas(r.get("estrellas")), e(r.get("fecha")),
                 e(r.get("titulo")), e(r.get("texto")), e(r.get("formato", "Compra verificada")))
        for r in b.get("resenas", []))
    return """<div class="reviews-summary">%s</div><div class="reviews">%s</div>
<p class="aff-note">Reseñas recogidas de la ficha pública del libro en Amazon.es el %s. Se reproducen tal cual, sin editar el sentido.</p>""" % (
        e(b.get("resenas_resumen", "")), items, FECHA_LARGA)

def similares(b):
    otros = [x for x in LIBROS if x["id"] != b["id"]]
    mismos = [x for x in otros if x["categoria"] == b["categoria"]]
    resto = sorted([x for x in otros if x["categoria"] != b["categoria"]],
                   key=lambda x: abs((x.get("precio") or 0) - (b.get("precio") or 0)))
    sel = (mismos + resto)[:3]
    items = "".join("""<a class="similar-item" href="libro-%s.html">
  <span class="cover"><img src="%s" alt="" loading="lazy" decoding="async" width="120" height="180"></span>
  <span><h4>%s</h4><span>%s · %s</span></span></a>""" % (e(x["id"]), e(x["imagenes"][0]), e(x["titulo"]),
                                                          e(x["autor"]), eur(x.get("precio"))) for x in sel)
    return '<div class="radar-panel"><div class="radar-head"><h3>Parecidos</h3></div><div class="similar-strip">%s</div></div>' % items

def pagina_libro(b):
    cat = cat_obj(b["categoria"])
    off = descuento(b)
    ld = {
        "@context": "https://schema.org", "@type": "Book",
        "name": b["titulo"], "author": {"@type": "Person", "name": b["autor"]},
        "bookFormat": {"tapa dura": "https://schema.org/Hardcover", "tapa blanda": "https://schema.org/Paperback",
                       "bolsillo": "https://schema.org/Paperback"}.get(b.get("formato"), "https://schema.org/Paperback"),
        "numberOfPages": b.get("num_paginas"), "inLanguage": "es",
        "publisher": b.get("editorial"), "isbn": b.get("isbn_13"),
    }
    if b.get("precio") is not None:
        ld["offers"] = {"@type": "Offer", "price": "%.2f" % b["precio"], "priceCurrency": "EUR",
                        "url": b["canonical_url"], "availability": "https://schema.org/InStock"}
    if b.get("valoracion_media") is not None:
        ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": b["valoracion_media"],
                                 "reviewCount": b.get("resenas_cantidad"), "bestRating": 5}

    chips = []
    if b.get("num_paginas"):
        chips.append('<span class="chip">%s%s páginas</span>' % (IC["book"], miles(b["num_paginas"])))
    if b.get("horas_lectura"):
        chips.append('<span class="chip">%s≈ %s h de lectura</span>' % (IC["clock"], dec(b["horas_lectura"])))
    if b.get("formato"):
        chips.append('<span class="chip">%s%s</span>' % (IC["scale"], e(b["formato"].capitalize())))
    if off >= 5:
        chips.append('<span class="chip">%s−%d %% sobre PVP</span>' % (IC["tag"], off))

    cuerpo = """<section class="book-hero">
  <div class="wrap">
    <nav class="crumbs" aria-label="Migas de pan">
      <a href="index.html">Inicio</a><span>›</span><a href="categoria-%s.html">%s</a><span>›</span><span>%s</span>
    </nav>
    <div class="book-hero-grid">
      <div>%s</div>
      <div>
        <span class="eyebrow">%s</span>
        <h1 class="book-title">%s</h1>
        %s
        <p class="book-author">de <b>%s</b>%s</p>
        <div class="book-meta-row">%s</div>
        <div class="buybox">
          %s
          <span class="price-date">Precio orientativo recogido el %s. Consúltalo en Amazon antes de comprar.</span>
          %s
          %s
          <div class="buybox-facts">%s</div>
        </div>
        <p class="pull">%s</p>
      </div>
    </div>
  </div>
</section>

<section class="section" style="padding-top:clamp(2rem,5vw,3.2rem)">
  <div class="wrap">
    <div class="book-body">
      <div>
        <h2 style="margin-bottom:1rem">Nuestra opinión</h2>
        <div class="prose" style="max-width:none">%s</div>
        %s
        <div style="margin-top:2rem">%s</div>

        <h2 id="ficha" style="margin:2.6rem 0 .4rem">Ficha técnica completa</h2>
        <p style="color:var(--ink-mute);font-size:.9rem;margin-bottom:.4rem">Datos tomados de la ficha del libro en Amazon.es. Los huecos marcados con “—” son datos que Amazon no publica; no los rellenamos a ojo.</p>
        %s

        <h2 id="resenas" style="margin:2.6rem 0 1rem">Qué dicen quienes lo han leído</h2>
        %s

        <div style="margin-top:2.4rem">%s</div>
      </div>
      <aside class="book-aside">
        %s
        %s
      </aside>
    </div>
  </div>
</section>""" % (e(cat["id"]), e(cat["nombre"]), e(b["titulo"]),
                 galeria(b), e(cat["nombre"]), e(b["titulo"]),
                 ('<p class="book-sub">%s</p>' % e(b["subtitulo"])) if b.get("subtitulo") else "",
                 e(b["autor"]), (" · traducción de %s" % e(b["traductor"])) if b.get("traductor") else "",
                 estrellas_html(b),
                 precio_html(b), FECHA_LARGA, boton_compra(b, grande=True), boton_comparar(b),
                 "".join(chips),
                 e(b.get("destacado_editorial", "")),
                 b.get("cuerpo_editorial", ""), pros_contras(b), boton_compra(b, grande=True),
                 tabla_specs(b), resenas_html(b), boton_compra(b, grande=True),
                 panel_radar(b), similares(b))

    desc = b.get("descripcion", "")[:158]
    return pagina("%s, de %s · análisis y ficha completa | %s" % (b["titulo"], b["autor"], SITIO),
                  desc, cuerpo, activo="", jsonld=ld)

# ---------------------------------------------------------------- home
def pagina_home():
    dest = [b for b in LIBROS if b.get("isFeatured")]
    if len(dest) < 4:
        dest = (dest + [b for b in LIBROS if not b.get("isFeatured")])[:5]
    dest = dest[:5]
    shelf = "".join('<a href="libro-%s.html" aria-label="%s"><span class="cover"><img src="%s" alt="Portada de %s" %s width="300" height="450"></span></a>'
                    % (e(b["id"]), e(b["titulo"]), e(b["imagenes"][0]), e(b["titulo"]),
                       'fetchpriority="high"' if i == 0 else 'loading="lazy"')
                    for i, b in enumerate(dest[:5]))

    top = sorted(LIBROS, key=lambda b: (nota_media(b) or 0), reverse=True)[:5]
    nuevos = sorted(LIBROS, key=lambda b: (b.get("anio") or 0), reverse=True)[:5]

    cat_cards = "".join("""<a class="cat-card" href="categoria-%s.html" data-reveal>
      <h3>%s</h3><p>%s</p><span class="n">%s →</span></a>"""
      % (e(c["id"]), e(c["nombre"]), e(c["intro"][:96].rsplit(" ", 1)[0] + "…"),
         plural(len([b for b in LIBROS if b["categoria"] == c["id"]]), "libro comparado", "libros comparados")) for c in CATS)

    guia_cards = "".join("""<a class="cat-card" href="%s.html" data-reveal><h3>%s</h3><p>%s</p><span class="n">Leer la guía →</span></a>"""
      % (g["slug"], e(g["h1"]), e(g["resumen"][:110].rsplit(" ", 1)[0] + "…")) for g in GUIAS)

    cuerpo = """<section class="hero">
  <div class="wrap hero-grid">
    <div>
      <span class="eyebrow">Los %d libros más vendidos ahora en Amazon.es</span>
      <h1>No te decimos qué leer.<br>Te enseñamos <em>en qué se diferencian</em>.</h1>
      <p class="lead hero-lead">Cada libro con su ficha técnica completa, su gráfico de valoración, sus pros y sus contras. Y un comparador para ponerlos cara a cara y decidir tú.</p>
      <div class="hero-actions">
        <a class="btn btn-buy" href="comparador.html">Abrir el comparador</a>
        <a class="btn btn-ghost" href="#destacados">Ver los libros</a>
      </div>
      <div class="hero-facts">
        <div class="hero-fact"><strong>%d</strong><span>libros analizados</span></div>
        <div class="hero-fact"><strong>%d</strong><span>géneros</span></div>
        <div class="hero-fact"><strong>%s</strong><span>reseñas de compradores</span></div>
      </div>
    </div>
    <div class="shelf" data-reveal>
      <div class="shelf-books">%s</div>
      <div class="shelf-plank"></div>
    </div>
  </div>
</section>

<section class="trust section" style="padding-block:clamp(2.2rem,5vw,3.4rem)" aria-labelledby="por-que-fiarte">
  <div class="wrap">
    <!-- Encabezado solo para lectores de pantalla: el diseno no lo pide, pero sin
         el la portada saltaba de h1 a h3 y el indice de la pagina quedaba roto. -->
    <h2 id="por-que-fiarte" class="sr-only">Por que fiarte de esta comparativa</h2>
  </div>
  <div class="wrap trust-grid">
    <div class="trust-item"><h3>%sDatos reales, no copiados</h3><p>Precio, valoración, páginas, editorial, ISBN y medidas salen de la ficha del libro en Amazon.es. Si Amazon no publica un dato, aquí verás “—”: no lo inventamos.</p></div>
    <div class="trust-item"><h3>%sSeis ejes, siempre los mismos</h3><p>Ritmo, personajes, profundidad, originalidad, facilidad y calidad-precio. Es opinión nuestra y va etiquetada como tal, pero se aplica igual a todos.</p></div>
    <div class="trust-item"><h3>%sTambién decimos lo malo</h3><p>Cada ficha lleva sus contras. Ganamos comisión si compras, y por eso mismo nos interesa que no devuelvas el libro.</p></div>
  </div>
</section>

<section class="section" id="destacados">
  <div class="wrap">
    <div class="section-head">
      <span class="eyebrow">La selección</span>
      <h2>Los destacados de este mes</h2>
      <p>Los que mejor nota sacan en nuestro análisis entre los más vendidos ahora mismo.</p>
    </div>
    <div class="book-grid">%s</div>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap">
    <div class="section-head"><span class="eyebrow">Por género</span><h2>¿Qué te apetece leer?</h2></div>
    <div class="cat-grid">%s</div>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap">
    <div class="section-head"><span class="eyebrow">Ranking</span><h2>Mejor valorados por nosotros</h2>
    <p>Ordenados por la nota media de los seis ejes. Es nuestra opinión, no la de Amazon.</p></div>
    <div class="book-grid">%s</div>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap">
    <div class="section-head"><span class="eyebrow">Guías de compra</span><h2>¿No sabes por dónde empezar?</h2></div>
    <div class="cat-grid">%s</div>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap">
    <div class="section-head"><span class="eyebrow">Novedades</span><h2>Lo más reciente</h2></div>
    <div class="book-grid">%s</div>
  </div>
</section>""" % (len(LIBROS), len(LIBROS), len(CATS),
                 miles(sum(b.get("resenas_cantidad") or 0 for b in LIBROS)), shelf,
                 IC["eye"], IC["spark"], IC["scale"],
                 "".join(tarjeta(b) for b in dest), cat_cards,
                 "".join(tarjeta(b) for b in top), guia_cards,
                 "".join(tarjeta(b) for b in nuevos))

    return pagina("%s · Comparativa de los libros más vendidos en Amazon España 2026" % SITIO,
                  "Comparamos los %d libros más vendidos en Amazon.es: ficha técnica completa, gráfico de valoración, pros y contras y un comparador para verlos lado a lado." % len(LIBROS),
                  cuerpo, activo="inicio", guia="inicio")

# ---------------------------------------------------------------- categoría
def pagina_categoria(c):
    libros = [b for b in LIBROS if b["categoria"] == c["id"]]
    libros.sort(key=lambda b: (nota_media(b) or 0), reverse=True)
    formatos = sorted(set(b.get("formato") for b in LIBROS if b.get("formato")))
    chips = "".join('<button class="chip-toggle" type="button" data-filter-format="%s" aria-pressed="false">%s</button>'
                    % (e(f), e(f.capitalize())) for f in formatos)
    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "name": "%s: los mejores libros" % c["titulo"],
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": b["titulo"]}
                              for i, b in enumerate(libros)]}
    cuerpo = """<section class="section" style="padding-bottom:0">
  <div class="wrap">
    <nav class="crumbs"><a href="index.html">Inicio</a><span>›</span><span>%s</span></nav>
    <div class="section-head">
      <span class="eyebrow">%s</span>
      <h1>%s</h1>
      <p class="lead">%s</p>
    </div>
  </div>
</section>
<section class="section" style="padding-top:2rem">
  <div class="wrap">
    <div class="filters">
      <label for="orden">Ordenar por</label>
      <select id="orden" data-sort>
        <option value="nota">Nuestra nota</option>
        <option value="valoracion">Valoración en Amazon</option>
        <option value="resenas">Número de reseñas</option>
        <option value="precio-asc">Precio: de menor a mayor</option>
        <option value="precio-desc">Precio: de mayor a menor</option>
        <option value="paginas">Más páginas</option>
      </select>
      %s
    </div>
    <div class="book-grid" data-filter-grid>%s</div>
    <p class="cmp-empty" data-filter-empty hidden>Ningún libro de esta categoría encaja con los filtros elegidos.</p>
    <p class="aff-note">Precios recogidos el %s. Los enlaces a Amazon son enlaces de afiliado.</p>
  </div>
</section>""" % (e(c["nombre"]), plural(len(libros), "libro comparado", "libros comparados"),
                 e(c["titulo"]), e(c["intro"]), chips,
                 "".join(tarjeta(b, mostrar_cat=False) for b in libros), FECHA_LARGA)
    tit = ("%s: %s comparado (2026)" % (c["titulo"], "1 libro")) if len(libros) == 1 else \
          ("%s: los %d mejores comparados (2026)" % (c["titulo"], len(libros)))
    return pagina("%s | %s" % (tit, SITIO),
                  c["intro"][:158], cuerpo, activo="", jsonld=ld)

# ---------------------------------------------------------------- comparador
def pagina_comparador():
    cuerpo = """<section class="section" data-cmp-page style="padding-bottom:2rem">
  <div class="wrap">
    <div class="section-head">
      <span class="eyebrow">La herramienta</span>
      <h1>Comparador de libros</h1>
      <p class="lead">Elige hasta cuatro y míralos enfrentados: precio, páginas, precio por cada 100 páginas, valoración, peso y nuestros seis ejes superpuestos en un mismo gráfico.</p>
    </div>
    <div class="cmp-picker">
      <div class="cmp-slots" data-cmp-slots></div>
      <div class="cmp-search">
        <label class="sr-only" for="buscar">Buscar un libro para añadir</label>
        <input id="buscar" type="search" placeholder="Busca por título, autor o género…" autocomplete="off" data-cmp-search>
        <ul class="cmp-results" data-cmp-results aria-live="polite" aria-atomic="false"></ul>
      </div>
    </div>
    <div data-cmp-out><p class="cmp-empty">Elige al menos <b>dos libros</b> para verlos enfrentados.</p></div>
    <p class="aff-note">La fila resaltada como “mejor” marca el valor más favorable de esa característica entre los libros elegidos (precio más bajo, más reseñas, menos peso…). Los seis ejes finales son valoración del editor, no datos de Amazon. Precios del %s.</p>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap">
    <div class="section-head"><h2>Todos los libros del catálogo</h2><p>Pulsa “Comparar” en cualquiera para añadirlo arriba.</p></div>
    <div class="book-grid">%s</div>
  </div>
</section>""" % (FECHA_LARGA, "".join(tarjeta(b) for b in LIBROS))
    return pagina("Comparador de libros · enfréntalos lado a lado | %s" % SITIO,
                  "Elige hasta cuatro libros y compáralos: precio, páginas, precio por cada 100 páginas, valoración de Amazon y seis ejes de valoración superpuestos.",
                  cuerpo, activo="comparador", guia="comparador")

# ---------------------------------------------------------------- ofertas
def pagina_ofertas():
    ofertas = [b for b in LIBROS if descuento(b) >= 5]
    ofertas.sort(key=descuento, reverse=True)
    if ofertas:
        cards = "".join(tarjeta(b) for b in ofertas)
        ahorro = sum((b["precio_lista"] - b["precio"]) for b in ofertas)
        intro = ("Ahora mismo hay <b>%d libros</b> por debajo de su precio de portada, con un ahorro conjunto de %s. "
                 "En España el descuento sobre el PVP de un libro está limitado por ley al 5 %%, así que estos son "
                 "los máximos que vas a ver salvo en ediciones especiales.") % (len(ofertas), eur(round(ahorro, 2)))
    else:
        cards = '<p class="cmp-empty">Ahora mismo ningún libro del catálogo está por debajo de su precio de portada.</p>'
        intro = "Ahora mismo no hay descuentos en el catálogo."
    cuerpo = """<section class="section">
  <div class="wrap">
    <nav class="crumbs"><a href="index.html">Inicio</a><span>›</span><span>Ofertas</span></nav>
    <div class="section-head">
      <span class="eyebrow">Precios por debajo del PVP</span>
      <h1>Ofertas de hoy</h1>
      <p class="lead">%s</p>
    </div>
    <div class="book-grid">%s</div>
    <p class="aff-note">Precios recogidos el %s. Un precio puede cambiar en cualquier momento: el que manda es el que ves en Amazon al pagar.</p>
  </div>
</section>""" % (intro, cards, FECHA_LARGA)
    return pagina("Ofertas en libros · %s" % SITIO,
                  "Los libros de nuestra comparativa que ahora mismo están por debajo de su precio de portada en Amazon.es.",
                  cuerpo, activo="ofertas")

# ---------------------------------------------------------------- guías
def pagina_guia(g):
    picks = [byid(i) for i in g["ids"]]
    picks = [p for p in picks if p]
    bloques = ""
    for i, b in enumerate(picks):
        bloques += """<article class="guide-pick" id="p%d" data-reveal>
  <a href="libro-%s.html" aria-label="Ver la ficha de %s"><span class="cover"><img src="%s" alt="Portada de %s" loading="lazy" decoding="async" width="300" height="450"></span></a>
  <div>
    <div class="guide-rank">%02d</div>
    <span class="eyebrow">%s</span>
    <h3><a href="libro-%s.html">%s</a></h3>
    <p class="author" style="color:var(--ink-mute);font-size:.88rem">%s · %s páginas · %s</p>
    <p class="why">%s</p>
    <div class="book-meta-row">%s%s</div>
    <div style="display:flex;gap:.6rem;flex-wrap:wrap;align-items:center">%s<a class="btn btn-ghost" href="libro-%s.html">Ver la ficha</a>%s</div>
  </div>
</article>""" % (i + 1, e(b["id"]), e(b["titulo"]), e(b["imagenes"][0]), e(b["titulo"]), i + 1, e(g["motes"][i]),
                 e(b["id"]), e(b["titulo"]), e(b["autor"]), miles(b.get("num_paginas")), e(b.get("formato")),
                 e(g["porques"][i]), estrellas_html(b), precio_html(b),
                 boton_compra(b), e(b["id"]), boton_comparar(b))

    toc = "".join('<li><a href="#p%d">%s — <em>%s</em></a></li>' % (i + 1, e(g["motes"][i]), e(b["titulo"]))
                  for i, b in enumerate(picks))
    faqs = "".join("<details><summary>%s</summary><p>%s</p></details>" % (e(q), e(a)) for q, a in g["faq"])

    ld = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": g["h1"],
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": b["titulo"],
                              "url": "libro-%s.html" % b["id"]} for i, b in enumerate(picks)]},
        {"@context": "https://schema.org", "@type": "FAQPage",
         "mainEntity": [{"@type": "Question", "name": q,
                         "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in g["faq"]]}
    ]

    cuerpo = """<section class="guide-hero">
  <div class="wrap-narrow">
    <nav class="crumbs"><a href="index.html">Inicio</a><span>›</span><span>Guías</span></nav>
    <span class="eyebrow">Guía de compra · actualizada el %s</span>
    <h1>%s</h1>
    <p class="lead" style="margin-top:1rem">%s</p>
  </div>
</section>
<section class="section" style="padding-top:2rem">
  <div class="wrap-narrow">
    <div class="guide-toc"><h2>En esta guía</h2><ol>%s</ol></div>
    <div class="prose" style="max-width:none">%s</div>
    <div style="margin-top:2.2rem">%s</div>
    <h2 style="margin:2.8rem 0 1rem">Cómo elegir sin equivocarte</h2>
    <div class="prose" style="max-width:none">%s</div>
    <h2 style="margin:2.8rem 0 1rem">Preguntas frecuentes</h2>
    <div class="faq">%s</div>
    <p class="aff-note">Esta guía contiene enlaces de afiliado de Amazon: si compras a través de ellos ganamos una comisión sin coste para ti. Precios del %s.</p>
  </div>
</section>""" % (FECHA_LARGA, e(g["h1"]), e(g["resumen"]), toc, g["intro"], bloques, g["criterios"], faqs, FECHA_LARGA)

    return pagina("%s | %s" % (g["h1"], SITIO), g["resumen"][:158], cuerpo, activo="guias", jsonld=ld)

def byid(i):
    for b in LIBROS:
        if b["id"] == i:
            return b
    return None

# ---------------------------------------------------------------- estáticas
def pagina_como_elegimos():
    ejes = "".join("<tr><th>%s</th><td>%s</td></tr>" % (e(l), e(d)) for l, d in [
        ("Ritmo", "Cuánto engancha y a qué velocidad avanza. Nos apoyamos en la estructura del libro y en lo que repiten las reseñas."),
        ("Personajes", "Profundidad y memorabilidad de quienes habitan la novela."),
        ("Profundidad", "Carga emocional o intelectual: el poso que deja al terminarlo."),
        ("Originalidad", "Cuánto se aparta de lo que ya has leído dentro de su género."),
        ("Facilidad", "Accesibilidad de la prosa. Un 10 se lee solo; un 3 exige esfuerzo."),
        ("Calidad-precio", "Este sí es un cálculo: 60 % el precio por cada 100 páginas (invertido y normalizado al catálogo) y 40 % la valoración media de Amazon normalizada entre 4,0 y 5,0 estrellas."),
    ])
    cuerpo = """<section class="section">
  <div class="wrap-narrow">
    <nav class="crumbs"><a href="index.html">Inicio</a><span>›</span><span>Cómo elegimos</span></nav>
    <span class="eyebrow">Método</span>
    <h1>Cómo elegimos y cómo puntuamos</h1>
    <div class="prose" style="margin-top:1.6rem;max-width:none">
      <p>Esta web hace dos cosas distintas y conviene no mezclarlas: <strong>recoge datos</strong> y <strong>opina</strong>. Los separamos siempre.</p>
      <h2>1. Los datos</h2>
      <p>Precio, precio de portada, valoración media, número de reseñas, páginas, editorial, fecha, ISBN, dimensiones y peso salen de la ficha pública del libro en Amazon.es, capturada el %s. No los retocamos. Si Amazon no publica un dato, en la ficha verás un guion “—”: preferimos un hueco a una cifra inventada.</p>
      <p>Los precios son una foto de ese día. Cambian. El precio que vale es el que ves en Amazon al pagar, y por eso lo etiquetamos siempre con su fecha.</p>
      <h2>2. Qué libros entran</h2>
      <p>Partimos de las listas de los más vendidos de Amazon.es —la general y la de cada género— y nos quedamos con títulos que tengan edición física y suficientes valoraciones como para que la media signifique algo. Nadie paga por aparecer aquí, y no aceptamos ejemplares a cambio de una nota.</p>
      <h2>3. La valoración del editor</h2>
      <p>Cinco de los seis ejes son un juicio nuestro, formado leyendo la sinopsis, el material de la editorial y las reseñas reales de cada libro. Van etiquetados como “valoración del editor” en todas las fichas y en el comparador. El sexto es un cálculo.</p>
      <table class="spec-table" style="margin-top:1.4rem"><tbody>%s</tbody></table>
      <p style="margin-top:1.4rem">Las notas son <strong>relativas a este catálogo</strong>, no absolutas: un 10 en calidad-precio significa “el mejor de los que comparamos aquí”. Cuando entran libros nuevos, recalculamos las notas de todos para que sigan siendo comparables entre sí.</p>
      <h2>4. Cómo ganamos dinero</h2>
      <p>Con comisiones de afiliado de Amazon. Si compras a través de nuestros enlaces, nos llevamos un porcentaje y tú pagas exactamente lo mismo. Eso condiciona lo que hacemos de una forma concreta: nos interesa que aciertes, porque una devolución no nos deja comisión. Por eso cada ficha lleva su sección de contras y por eso decimos abiertamente cuándo un libro no vale su precio.</p>
    </div>
  </div>
</section>""" % (FECHA_LARGA, ejes)
    return pagina("Cómo elegimos y puntuamos los libros | %s" % SITIO,
                  "El método: qué datos vienen de Amazon, qué es opinión nuestra y cómo se calculan las notas de los seis ejes.",
                  cuerpo, activo="como")

def pagina_404():
    """Cloudflare la sirve en cualquier direccion que no exista. No es un callejon
    sin salida: lleva a las categorias, al comparador y a los libros."""
    cats = "".join(
        '<a class="btn btn-ghost" href="categoria-%s.html">%s</a>' % (e(c["id"]), e(c["nombre"]))
        for c in CATS)
    sugeridos = sorted(LIBROS, key=lambda b: -(b.get("valoracion_media") or 0))[:3]
    tarjetas = "".join(tarjeta(b) for b in sugeridos)
    cuerpo = """<section class="section">
  <div class="wrap-narrow" style="text-align:center">
    <span class="eyebrow">Error 404</span>
    <h1>Esta página no existe</h1>
    <br>
    <p class="lede" style="margin-inline:auto">Puede que el enlace esté mal escrito, o que la página se
    haya movido. Lo que buscas casi seguro está a un clic de aquí.</p>
    <div style="display:flex;gap:.6rem;flex-wrap:wrap;justify-content:center;margin-top:1.8rem">
      <a class="btn btn-primary" href="index.html">Volver al inicio</a>
      <a class="btn btn-ghost" href="comparador.html">Comparar libros</a>
      <a class="btn btn-ghost" href="estanteria.html">La estantería en 3D</a>
    </div>
  </div>
</section>

<section class="section section-alt">
  <div class="wrap">
    <div class="section-head"><h2>Busca por género</h2></div>
    <div style="display:flex;gap:.6rem;flex-wrap:wrap;justify-content:center">%s</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>O empieza por los mejor valorados</h2>
      <p class="section-sub">Los tres libros con mejor nota de lectores de toda la comparativa.</p>
    </div>
    <div class="book-grid">%s</div>
  </div>
</section>""" % (cats, tarjetas)
    return pagina("Página no encontrada | " + SITIO,
                  "La página que buscas no existe. Vuelve al inicio, compara libros por género "
                  "o consulta las fichas de los más vendidos en Amazon.es.",
                  cuerpo)

def pagina_aviso():
    cuerpo = """<section class="section">
  <div class="wrap-narrow">
    <nav class="crumbs"><a href="index.html">Inicio</a><span>›</span><span>Aviso de afiliados</span></nav>
    <span class="eyebrow">Legal</span>
    <h1>Aviso de afiliados</h1>
    <div class="prose" style="margin-top:1.6rem;max-width:none">
      <p><strong>%s participa en el Programa de Afiliados de Amazon EU</strong>, un programa de publicidad para afiliados
      diseñado para ofrecer a sitios web un modo de obtener comisiones por publicidad, publicitando e incluyendo enlaces a Amazon.es.</p>
      <p>En la práctica: todos los botones «Ver en Amazon» de esta web son enlaces de afiliado. Si compras después de
      pulsarlos, Amazon nos paga una comisión. <strong>El precio que pagas tú es exactamente el mismo</strong>, con o sin
      nuestro enlace.</p>
      <h2>Qué no hacemos</h2>
      <ul>
        <li>No cobramos por aparecer en las comparativas ni por salir mejor puntuado.</li>
        <li>No ocultamos los defectos de un libro: cada ficha lleva su lista de contras.</li>
        <li>No inventamos datos técnicos ni reseñas. Lo que no sabemos aparece como “—”.</li>
      </ul>
      <h2>Precios y disponibilidad</h2>
      <p>Los precios y la disponibilidad que ves aquí son los recogidos el <strong>%s</strong> y pueden haber cambiado desde
      entonces. El precio y la disponibilidad aplicables a la compra son los que aparecen en Amazon.es en el momento de
      realizarla. Amazon no se hace responsable de la exactitud de los precios mostrados en esta web.</p>
      <h2>Marcas</h2>
      <p>Amazon, Amazon.es y el logotipo de Amazon son marcas comerciales de Amazon.com, Inc. o de sus filiales. Los títulos,
      portadas y textos de los libros pertenecen a sus respectivos autores y editoriales, y se reproducen aquí a efectos
      informativos y de reseña.</p>
      <h2>Reseñas de terceros</h2>
      <p>Las opiniones de lectores que aparecen en las fichas están recogidas de la página pública del producto en Amazon.es
      y se reproducen de forma literal, con su autor y su fecha, sin alterar su sentido. No son opiniones de esta web.</p>
      <h2>Contacto</h2>
      <p>Para cualquier corrección, reclamación de derechos o retirada de contenido, escríbenos y lo resolvemos:
      <a href="mailto:hola@bookatme.example">hola@bookatme.example</a>.</p>
    </div>
  </div>
</section>""" % (SITIO, FECHA_LARGA)
    return pagina("Aviso de afiliados | %s" % SITIO,
                  "Esta web contiene enlaces de afiliado de Amazon y gana una comisión por las compras que cumplen los requisitos. El precio para ti no cambia.",
                  cuerpo)

def pagina_privacidad():
    cuerpo = """<section class="section">
  <div class="wrap-narrow">
    <nav class="crumbs"><a href="index.html">Inicio</a><span>›</span><span>Privacidad</span></nav>
    <span class="eyebrow">Legal</span>
    <h1>Privacidad y cookies</h1>
    <div class="prose" style="margin-top:1.6rem;max-width:none">
      <h2>Qué guardamos</h2>
      <p>Esta web es un sitio estático. No tiene formularios, no tiene registro y <strong>no recoge datos personales</strong>.
      No usamos cookies de seguimiento ni analítica de terceros.</p>
      <h2>Almacenamiento local</h2>
      <p>Lo único que se guarda en tu navegador es la lista de libros que añades al comparador, mediante
      <em>localStorage</em>. Es información técnica que no sale de tu dispositivo, no se envía a ningún servidor y puedes
      borrarla vaciando el comparador o limpiando los datos del navegador.</p>
      <h2>Enlaces a Amazon</h2>
      <p>Cuando pulsas un botón «Ver en Amazon» sales de esta web. A partir de ahí se aplican el aviso de privacidad y la
      política de cookies de Amazon.es, sobre los que no tenemos control. Amazon utiliza cookies para asociar tu visita a
      nuestro identificador de afiliado durante un tiempo limitado.</p>
      <h2>Tipografías</h2>
      <p>Las tipografías se cargan desde Google Fonts, lo que implica una conexión a servidores de Google que puede registrar
      tu dirección IP. Si prefieres evitarlo, puedes bloquear ese dominio en tu navegador; la web sigue funcionando.</p>
      <h2>Tus derechos</h2>
      <p>Al no tratar datos personales no hay ningún fichero que consultar, rectificar o suprimir. Si aun así tienes cualquier
      duda, escríbenos a <a href="mailto:hola@bookatme.example">hola@bookatme.example</a>.</p>
    </div>
  </div>
</section>"""
    return pagina("Privacidad y cookies | %s" % SITIO,
                  "Esta web no recoge datos personales ni usa cookies de seguimiento. Solo guarda tu selección del comparador en el propio navegador.",
                  cuerpo)

def favicon():
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<rect width="32" height="32" rx="6" fill="#14161C"/>'
            '<path d="M9 8h9a4 4 0 014 4v13a4 4 0 00-4-4H9V8z" fill="none" stroke="#24503D" stroke-width="2.2" stroke-linejoin="round"/>'
            '<path d="M23 8h-4" stroke="#A87C2E" stroke-width="2.2" stroke-linecap="round"/></svg>')

def db_js():
    campos = ("id asin titulo subtitulo autor categoria affiliate_url imagenes precio precio_lista "
              "valoracion_media resenas_cantidad formato num_paginas editorial anio idioma_original "
              "peso_g dimensiones_cm isbn_13 horas_lectura saga num_en_saga disponible_kindle "
              "disponible_audiolibro").split() + EJES_K
    ligero = [{k: b.get(k) for k in campos} for b in LIBROS]
    return ("(function(){\n  \"use strict\";\n  window.__DB__ = {\n    meta: %s,\n    libros: %s\n  };\n})();\n"
            % (json.dumps({"categorias": CATS, "actualizado": META.get("actualizado"),
                           "ejes": [l for _, l in EJES]}, ensure_ascii=False),
               json.dumps(ligero, ensure_ascii=False)))

def og_imagen_de(nombre):
    """La miniatura al compartir: la propia del libro si existe, si no la de la marca."""
    suya = "assets/og/%s.jpg" % nombre[:-5]
    if os.path.exists(os.path.join(BASE, suya.replace("/", os.sep))):
        return suya
    return "assets/og/bookatme.jpg"

def seo_de(nombre):
    """Rellena el hueco <!--SEO--> con lo que depende de EN QUE pagina estamos.
    Se hace aqui, en escribir(), porque es el unico sitio que conoce el nombre
    del archivo; asi no hay que pasarle la URL a las 25 llamadas a pagina()."""
    if not nombre.endswith(".html"):
        return ""
    # La pagina de error no se indexa, pero sus enlaces si se siguen.
    if nombre == "404.html":
        return '<meta name="robots" content="noindex, follow">'
    p = ['<meta name="robots" content="index, follow">']
    if DOMINIO:
        url = DOMINIO + "/" if nombre == "index.html" else "%s/%s" % (DOMINIO, nombre)
        img = "%s/%s" % (DOMINIO, og_imagen_de(nombre))
        p += ['<link rel="canonical" href="%s">' % e(url),
              '<meta property="og:url" content="%s">' % e(url),
              '<meta property="og:image" content="%s">' % e(img),
              '<meta property="og:image:width" content="1200">',
              '<meta property="og:image:height" content="630">',
              '<meta name="twitter:image" content="%s">' % e(img)]
    return "\n".join(p)

def absolutizar(doc):
    """Convierte las rutas relativas en absolutas.
    Solo para 404.html: Cloudflare la sirve en CUALQUIER direccion que no exista
    (/loquesea/otracosa incluida), y desde ahi 'styles.css' apuntaria a
    /loquesea/styles.css. Sin esto la pagina de error saldria sin estilos."""
    return re.sub(r'(href|src)="(?!https?:|//|/|#|mailto:|data:)', r'\1="/', doc)

def robots_txt():
    lineas = ["User-agent: *", "Allow: /", ""]
    if DOMINIO:
        lineas.append("Sitemap: %s/sitemap.xml" % DOMINIO)
    return "\n".join(lineas) + "\n"

def webmanifest():
    return json.dumps({
        "name": "BookAtMe! · comparativas de libros",
        "short_name": "BookAtMe!",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#F5F4F0",
        "theme_color": "#14161C",
        "icons": [
            {"src": "/assets/icono-180.png", "sizes": "180x180", "type": "image/png"},
            {"src": "/assets/icono-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/assets/favicon.svg", "sizes": "any", "type": "image/svg+xml"}
        ]
    }, ensure_ascii=False, indent=2)

def sitemap(paginas):
    if not DOMINIO:
        return None
    hoy = datetime.date.today().isoformat()
    # La 404 nunca va al sitemap: se le pide a Google justo lo contrario.
    utiles = [p for p in paginas if p != "404.html"]
    urls = "".join(
        "\n  <url><loc>%s/%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>"
        % (DOMINIO, "" if p == "index.html" else p, hoy,
           "1.0" if p == "index.html" else ("0.8" if p.startswith(("categoria-", "libro-")) else "0.6"))
        for p in utiles)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s\n</urlset>\n' % urls)

# ---------------------------------------------------------------- guías (contenido)
def definir_guias():
    return [
        {
            "slug": "guia-mejor-libro-para-desconectar-2026",
            "nav": "Mejor libro para desconectar",
            "h1": "El mejor libro para desconectar en 2026",
            "resumen": "Cinco libros elegidos por una única cosa: que te saquen de tu cabeza. Los ordenamos de más ligero a más hondo, con lo que cuesta cada uno y cuántas horas te va a durar.",
            "ids": ["la-asistenta", "riete-de-las-bodas", "alas-de-sangre", "la-biblioteca-de-la-medianoche", "las-gratitudes"],
            "motes": ["El que no vas a poder soltar", "El que te va a hacer reír", "El que te saca del mundo",
                      "El que te deja mejor", "El que te deja tocado (en el buen sentido)"],
            "porques": [
                "Capítulos de tres páginas y un giro en la mitad exacta. Si llevas meses sin terminar un libro, este rompe la racha: la mayoría de sus lectores lo despachan en dos o tres tardes. Es lo más parecido a una serie que se ve de un tirón.",
                "624 páginas de comedia romántica con dos historias cruzadas, madre e hija. No pretende nada más que hacerte pasar un buen rato, y lo consigue con un 4,5 de media. Es el que más horas de buen humor da por euro de toda la selección.",
                "Si desconectar para ti significa irse literalmente a otro mundo, aquí tienes 800 páginas de dragones, academia militar y tensión romántica por 15,15 €. Tiene la mejor nota de todo nuestro catálogo (4,7) y dos libros más esperando.",
                "Desconectar no siempre es huir: a veces es reordenar. La novela de Matt Haig plantea qué vidas podrías haber vivido y termina, sin sermonear demasiado, convenciéndote de la que tienes. Tapa dura por menos de 12 €, el mejor regalo de la lista.",
                "Ojo con este: son 176 páginas y se leen en una tarde, pero no es una lectura ligera. Si lo que necesitas es que un libro te pare en seco y te haga llamar a alguien a quien tenías que dar las gracias, es este."
            ],
            "intro": """<p>«Desconectar» quiere decir cosas distintas según el día. Hay tardes en que necesitas que un libro te arrastre y no te deje pensar, y hay tardes en que lo que quieres es exactamente lo contrario: parar, respirar y que alguien te cuente algo que importe.</p>
<p>Por eso esta guía no es un ranking de mejor a peor. Es una escala: <strong>de más evasión a más poso</strong>. Los cinco están entre los más vendidos de Amazon.es ahora mismo, los cinco tienen su ficha completa aquí y de los cinco te decimos también lo que no nos gusta.</p>""",
            "criterios": """<p>Tres cosas antes de decidir:</p>
<p><strong>Cuánto tiempo tienes de verdad.</strong> No es lo mismo un libro de 176 páginas que uno de 800. En cada ficha calculamos las horas de lectura estimadas (a razón de unas 55 páginas por hora) para que no te engañes: <em>Alas de sangre</em> son unas catorce horas y media de tu vida.</p>
<p><strong>Cuánto cuesta cada hora.</strong> Es el dato que más se olvida. En España el descuento sobre el precio de portada está limitado por ley al 5 %, así que un libro caro va a seguir siendo caro; lo que cambia es cuánto te dura. Nuestro comparador tiene una fila de «€ por 100 páginas» precisamente para esto.</p>
<p><strong>Si quieres continuidad o punto final.</strong> Empezar una saga de tres libros no es lo mismo que leer una novela cerrada. <em>La asistenta</em> y <em>Alas de sangre</em> son primeras entregas; los otros tres se acaban y se acabó.</p>
<p>Si dudas entre dos, mételos en el <a href="comparador.html">comparador</a> y míralos enfrentados: verás en la misma pantalla el precio, las páginas, la valoración real de Amazon y nuestros seis ejes superpuestos.</p>""",
            "faq": [
                ("¿Cuál elijo si hace años que no leo nada?",
                 "La asistenta, sin dudarlo. Sus capítulos son de tres o cuatro páginas y siempre terminan con un anzuelo, así que el libro tira de ti en lugar de al revés. Sus lectores lo suelen terminar en dos o tres tardes."),
                ("¿Merece la pena pagar la tapa dura?",
                 "Solo si es para regalar o si el libro te va a acompañar mucho tiempo. Para leer y pasar página, la edición de bolsillo de La paciente silenciosa (11,35 € por 400 páginas) o la de Alas de sangre (15,15 € por 800) dan mucho más por el mismo dinero."),
                ("¿Los precios que aparecen son los de hoy?",
                 "No necesariamente. Son los que recogimos el 25 de agosto de 2026, y los etiquetamos con esa fecha en todas las fichas. Los precios de Amazon cambian; el que vale es el que ves al pagar."),
                ("¿Un libro largo aburre más?",
                 "No tiene por qué, pero conviene saber en qué te metes. El club de las indomables son 896 páginas y 1,13 kg: es fantástico en casa y bastante incómodo en la maleta. Ese tipo de detalle está en la ficha técnica de cada libro."),
            ],
        },
        {
            "slug": "guia-mejores-thrillers-2026",
            "nav": "Mejores thrillers",
            "h1": "Los mejores thrillers y libros de suspense de 2026",
            "resumen": "Qué thriller comprar según lo que busques: el del mejor giro final, el que más engancha y el que mejor está escrito. Con precio por hora de lectura y lo que dicen sus miles de reseñas.",
            "ids": ["la-paciente-silenciosa", "la-asistenta", "comeras-flores"],
            "motes": ["El del mejor final", "El más adictivo", "La alternativa con literatura"],
            "porques": [
                "Alicia Berenson mata a su marido y deja de hablar para siempre. Las 23.617 reseñas de Amazon repiten la misma palabra sobre su desenlace: asombroso. Es además la compra más razonable del género: 400 páginas en bolsillo por 11,35 €, unos 2,84 € por cada cien páginas.",
                "Si lo que buscas es no poder parar y te da igual el estilo, este gana por goleada. Capítulos cortísimos, giro en la mitad y un ritmo que sus lectores describen como imposible de soltar. La contrapartida es que la prosa es puramente funcional.",
                "No es un thriller, pero funciona parecido y está mucho mejor escrito: Comerás flores se lee con la misma velocidad y va cerrando el cerco alrededor de su protagonista hasta que duele. Doble premio en 2025. Si te cansa el thriller de fórmula, empieza por aquí."
            ],
            "intro": """<p>El thriller es el género donde más fácil es equivocarse de compra, porque casi todos prometen lo mismo: adictivo, impredecible, no podrás soltarlo. La contraportada nunca te dice lo único que importa, que es <strong>qué clase de lector eres</strong>.</p>
<p>Hay dos formas de disfrutar un thriller y son casi incompatibles. Una es el juego: adivinar antes que el autor y llevarte una sorpresa en la última página. La otra es la inmersión: que la novela esté tan bien escrita que dé igual quién lo hizo. Casi ningún libro hace las dos cosas bien. Aquí te decimos cuál hace cada una.</p>""",
            "criterios": """<p><strong>Mira el número de reseñas, no solo la nota.</strong> Un 4,7 con 40 valoraciones no dice nada; un 4,2 con 23.617 sí. En nuestras fichas verás siempre los dos números juntos, y en el comparador hay una fila específica para el recuento.</p>
<p><strong>Desconfía de «adictivo» y busca el número de páginas por capítulo.</strong> Lo que engancha no es el argumento, es la estructura. Los thrillers que más atrapan tienen capítulos cortos: es lo que hace que sigas «solo uno más».</p>
<p><strong>El giro final es lo único que no se puede arreglar.</strong> Un thriller con un ritmo irregular pero un final memorable se recuerda con cariño; uno con buen ritmo y un final tramposo, no. Por eso, si solo te llevas uno, llévate el que tenga fama por el desenlace.</p>
<p><strong>Y mira el formato.</strong> El thriller es literatura de viaje: pesa lo que pesa. Un bolsillo de 279 g cabe en cualquier bolso; una tapa dura de 1,13 kg no. Está en la ficha técnica de cada libro.</p>""",
            "faq": [
                ("¿Cuál tiene el mejor giro final?",
                 "La paciente silenciosa, de Alex Michaelides. Es el elemento que aparece en prácticamente todas sus reseñas de cinco estrellas, y el motivo por el que el libro sigue en el top 10 de Amazon.es años después de publicarse."),
                ("¿La asistenta o La paciente silenciosa?",
                 "La asistenta si lo que quieres es velocidad pura y te da igual el estilo; La paciente silenciosa si quieres un thriller algo mejor escrito y con un final más redondo. La segunda además cuesta 7,55 € menos."),
                ("¿Hace falta leer la saga entera de La asistenta?",
                 "No. El primer libro se cierra por completo y se entiende solo. Las continuaciones existen para quien se quede con ganas, no porque falte nada."),
                ("¿Los thrillers de esta lista tienen escenas duras?",
                 "Los tres tratan temas de violencia o de relaciones tóxicas, pero ninguno es explícito en lo gráfico. Comerás flores es el más incómodo de los tres, y lo es por lo reconocible de lo que cuenta, no por lo que enseña."),
            ],
        },
    ]

# ---------------------------------------------------------------- estantería 3D
def sin_html(s):
    """El cuerpo editorial lleva <p>; dentro del libro 3D se pinta en un canvas."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def mas_vendidos(cuantos=None):
    """Los libros ordenados del mas vendido al menos, segun el puesto que publica
    Amazon. Los que no lo tienen van detras, ordenados por valoracion: asi el
    orden es estable aunque falte el dato, en vez de quedar al azar."""
    def clave(b):
        p = b.get("puesto_ventas")
        return (0, p) if isinstance(p, int) else (1, -(b.get("valoracion_media") or 0))
    orden = sorted(LIBROS, key=clave)
    return orden[:cuantos] if cuantos else orden

def estanteria_db():
    """Los datos que necesita la estantería. Solo los carga estanteria.html.
    Va limitada a los mas vendidos: no es el catalogo entero."""
    fila = []
    for i, b in enumerate(mas_vendidos(LIBROS_EN_ESTANTERIA)):
        fila.append({
            "indice": i,
            "id": b["id"],
            "titulo": b["titulo"],
            "autor": b.get("autor"),
            "traductor": b.get("traductor"),
            "categoria": b["categoria"],
            "generoNombre": cat_nombre(b["categoria"]),
            "imagenes": b.get("imagenes", []),
            "contraportada": b.get("contraportada"),
            "affiliate_url": b["affiliate_url"],
            "ficha_url": "libro-%s.html" % b["id"],
            "precio": b.get("precio"),
            "precio_fecha": b.get("precio_fecha"),
            "valoracion_media": b.get("valoracion_media"),
            "resenas_cantidad": b.get("resenas_cantidad"),
            "num_paginas": b.get("num_paginas"),
            "editorial": b.get("editorial"),
            "anio": b.get("anio"),
            "formato": b.get("formato"),
            "horas_lectura": b.get("horas_lectura"),
            "disponible_kindle": b.get("disponible_kindle"),
            "disponible_audiolibro": b.get("disponible_audiolibro"),
            "notaMedia": nota_media(b),
            "descripcion": b.get("descripcion"),
            "destacado_editorial": b.get("destacado_editorial"),
            "editorialTexto": sin_html(b.get("cuerpo_editorial")),
            "pros": b.get("pros", []),
            "contras": b.get("contras", []),
            "ideal_para": b.get("ideal_para"),
        })
    return ('(function(){\n  "use strict";\n  window.__ESTANTERIA__ = %s;\n})();\n'
            % json.dumps(fila, ensure_ascii=False))

def pagina_estanteria():
    # La rejilla de respaldo enseña LO MISMO que la balda: si la estantería solo
    # muestra los 10 más vendidos, sin JavaScript no pueden aparecer 50.
    tarjetas = "".join(tarjeta(b) for b in mas_vendidos(LIBROS_EN_ESTANTERIA))
    # Esta es la ÚNICA página con módulos ES, y es a propósito: Three.js moderno solo
    # se publica así. El resto del sitio sigue con <script defer> + IIFE.
    # Los dos riesgos de los módulos están cubiertos:
    #   1. file:// — el sitio se sirve por http, en local y publicado.
    #   2. navegador sin import maps (anterior a 2023) — el módulo no carga, y la red
    #      de seguridad de abajo retira la escena y deja la rejilla de libros.
    cabeza = """<script type="importmap">
{"imports":{"three":"./lib/three/three.module.min.js","three/addons/":"./lib/three/addons/"}}
</script>
<script defer src="lib/estanteria-db.js?v=%s"></script>
<script type="module" src="lib/estanteria3d.js?v=%s"></script>
<script>
/* Red de seguridad: si a los 8 s la estantería no ha dicho que está lista, se retira
   y queda la rejilla de libros. Nunca una ruleta girando para siempre. */
setTimeout(function () {
  var e = document.getElementById("estanteria");
  if (!e || e.classList.contains("listo")) return;
  e.style.display = "none";
  var c = document.getElementById("estanteria-cargando");
  if (c) c.hidden = true;
}, 8000);
</script>""" % (VER, VER)

    cuerpo = """
<section class="est-escena" id="estanteria" aria-label="Estantería en tres dimensiones">
  <canvas id="estanteria-canvas" aria-hidden="true"></canvas>

  <div class="est-cargando" id="estanteria-cargando">
    <div class="est-cargando-marca" aria-hidden="true"></div>
    <p>Montando la estantería</p>
  </div>

  <div class="est-barra" id="estanteria-ui">
    <div class="est-sel">
      <span class="est-contador" id="sel-contador">01 / 01</span>
      <div class="est-sel-txt">
        <p class="est-sel-titulo" id="sel-titulo">&nbsp;</p>
        <p class="est-sel-nota" id="sel-nota">&nbsp;</p>
      </div>
    </div>
    <div class="est-acciones">
      <button class="est-redondo" type="button" id="btn-anterior" aria-label="Libro anterior">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m10.5 3.5-4.5 4.5 4.5 4.5"/></svg>
      </button>
      <button class="est-texto" type="button" id="btn-abrir">Abrir</button>
      <button class="est-redondo" type="button" id="btn-siguiente" aria-label="Libro siguiente">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m5.5 3.5 4.5 4.5-4.5 4.5"/></svg>
      </button>
    </div>
    <nav class="est-indice" aria-label="Índice de la estantería">
      <div class="est-marcadores" id="sel-marcadores" role="tablist" aria-label="Elegir libro"></div>
      <p class="est-pista">Rueda · flechas · clic en el libro</p>
    </nav>
  </div>

  <aside class="est-panel" id="estanteria-panel" role="dialog" aria-modal="true"
         aria-labelledby="p-titulo" aria-hidden="true" inert>
    <button class="est-cerrar" type="button" id="btn-cerrar-panel" aria-label="Devolver el libro a la estantería">
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8"/></svg>
    </button>
    <p class="est-genero" id="p-genero"></p>
    <h2 class="est-titulo" id="p-titulo"></h2>
    <p class="est-autor" id="p-autor"></p>
    <p class="est-sinopsis" id="p-sinopsis"></p>
    <ul class="est-pros" id="p-pros"></ul>
    <dl class="est-datos" id="p-datos"></dl>
    <div class="est-cta">
      <a class="btn btn-buy" id="p-comprar" href="#" target="_blank" rel="sponsored nofollow noopener">%sVer en Amazon</a>
      <a class="btn btn-ghost" id="p-ficha" href="#">Ver ficha completa</a>
    </div>
    <p class="est-precio" id="p-precio"></p>
    <div class="est-hojear" role="group" aria-label="Hojear el libro">
      <button class="est-pag" type="button" id="btn-pag-anterior" aria-label="Página anterior" disabled>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m10.5 3.5-4.5 4.5 4.5 4.5"/></svg>
      </button>
      <p class="est-pag-estado"><strong id="pag-etiqueta">Cerrado</strong><span id="pag-contador">Ábrelo para hojear</span></p>
      <button class="est-pag" type="button" id="btn-pag-siguiente" aria-label="Página siguiente" disabled>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m5.5 3.5 4.5 4.5-4.5 4.5"/></svg>
      </button>
    </div>
    <div class="est-panel-pie">
      <p class="est-pista" id="panel-pista">Toca el libro para abrirlo</p>
      <div class="est-panel-botones">
        <button class="est-enlace" type="button" id="btn-hojear" aria-pressed="false">Hojear el libro</button>
        <button class="est-enlace" type="button" id="btn-reset-vista">Centrar</button>
      </div>
    </div>
  </aside>

  <div class="est-etiqueta" id="etiqueta-raton" aria-hidden="true">
    <span id="etiqueta-raton-num"></span>
    <strong id="etiqueta-raton-tit"></strong>
  </div>
  <p class="sr-only" id="estanteria-avisos" aria-live="polite"></p>
</section>

<div class="est-respaldo" id="estanteria-respaldo">
  <section class="section">
    <div class="wrap">
      <nav class="crumbs"><a href="index.html">Inicio</a><span>›</span><span>La estantería</span></nav>
      <div class="section-head">
        <span class="eyebrow">La estantería</span>
        <h1>Los %s libros, uno a uno</h1>
        <p class="lead" data-motivo>Todos los que comparamos, con su ficha, su nota y su precio.
          Si tu navegador admite gráficos 3D, arriba puedes cogerlos de la balda y hojearlos.</p>
      </div>
      <div class="book-grid">%s</div>
    </div>
  </section>
</div>
""" % (IC["amazon"], len(LIBROS), tarjetas)

    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "La estantería de BookAtMe!",
        "numberOfItems": len(LIBROS),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "item": {"@type": "Book", "name": b["titulo"],
                      "author": {"@type": "Person", "name": b.get("autor") or ""},
                      "url": "libro-%s.html" % b["id"]}}
            for i, b in enumerate(LIBROS)
        ],
    }
    return pagina(
        "La estantería en 3D · BookAtMe!",
        "Coge cualquiera de los %d libros que comparamos, ábrelo y hójealo: sinopsis, pros, "
        "contras y nota, dentro del propio libro." % len(LIBROS),
        cuerpo, activo="estanteria", extra_head=cabeza, jsonld=ld, clase="pagina-estanteria",
        guia="estanteria")

# ---------------------------------------------------------------- main
def main():
    global LIBROS, CATS, META, GUIAS
    with open(DATOS, encoding="utf-8") as f:
        data = json.load(f)
    META = data["meta"]
    CATS = META["categorias"]
    LIBROS = data["libros"]
    GUIAS = definir_guias()

    # comprobaciones que evitan publicar algo roto
    problemas = []
    for b in LIBROS:
        if not b.get("affiliate_url") or "tag=" not in b["affiliate_url"]:
            problemas.append("%s: enlace sin etiqueta de afiliado" % b["id"])
        for img in b.get("imagenes", []):
            if not os.path.exists(os.path.join(BASE, img.replace("/", os.sep))):
                problemas.append("%s: falta la imagen %s" % (b["id"], img))
        if b["categoria"] not in [c["id"] for c in CATS]:
            problemas.append("%s: categoría desconocida %s" % (b["id"], b["categoria"]))
    if problemas:
        print("[!] Problemas encontrados:")
        for p in problemas:
            print("    -", p)
        return 1

    # ---- red de seguridad: detectar ediciones a mano ----
    # Si alguien edito un .html despues de la ultima construccion, es que lo
    # hizo a mano. Antes de machacarlo se guarda una copia y se avisa: perder
    # trabajo en silencio es lo peor que puede hacer una herramienta.
    sello = os.path.join(BASE, ".ultima-construccion")
    ultima = 0.0
    if os.path.exists(sello):
        try:
            ultima = float(io.open(sello, encoding="utf-8").read().strip())
        except (ValueError, OSError):
            ultima = 0.0

    a_mano = []
    if ultima:
        for f in sorted(os.listdir(BASE)):
            if not f.endswith(".html"):
                continue
            try:
                if os.path.getmtime(os.path.join(BASE, f)) > ultima + 2:
                    a_mano.append(f)
            except OSError:
                pass

    if a_mano:
        carpeta = os.path.join(BASE, "copias-a-mano",
                               datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(carpeta, exist_ok=True)
        for f in a_mano:
            shutil.copy2(os.path.join(BASE, f), os.path.join(carpeta, f))
        print("")
        print("  " + "!" * 66)
        print("  !! ATENCION: %d archivo(s) .html editados a mano" % len(a_mano))
        print("  !!")
        for f in a_mano[:6]:
            print("  !!    %s" % f)
        if len(a_mano) > 6:
            print("  !!    ...y %d mas" % (len(a_mano) - 6))
        print("  !!")
        print("  !! Esos archivos SE GENERAN solos y ahora se van a sobrescribir.")
        print("  !! Se ha guardado una copia de cada uno en:")
        print("  !!    copias-a-mano/%s" % os.path.basename(carpeta))
        print("  !!")
        print("  !! Para que el cambio sea permanente hay que hacerlo en el sitio")
        print("  !! correcto: datos/libros.json, styles.css o tools/build_site.py.")
        print("  !! Lo explica GUIA.md.")
        print("  " + "!" * 66)
        print("")

    escritas = []

    def escribir(nombre, contenido):
        # El SEO que depende de la pagina se rellena aqui, que es donde por fin
        # se sabe como se llama el archivo.
        if "<!--SEO-->" in contenido:
            contenido = contenido.replace("<!--SEO-->", seo_de(nombre))
        if nombre == "404.html":
            contenido = absolutizar(contenido)
        ruta = os.path.join(BASE, nombre)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(contenido)
        escritas.append(nombre)

    # borrar fichas antiguas de libros que ya no existen
    for f in os.listdir(BASE):
        if f.startswith("libro-") and f.endswith(".html"):
            if f[6:-5] not in [b["id"] for b in LIBROS]:
                os.remove(os.path.join(BASE, f))
                print("    (eliminada ficha huérfana %s)" % f)

    escribir("lib/db.js", db_js())
    escribir("lib/estanteria-db.js", estanteria_db())
    escribir("assets/favicon.svg", favicon())
    escribir("index.html", pagina_home())
    escribir("estanteria.html", pagina_estanteria())
    escribir("comparador.html", pagina_comparador())
    escribir("ofertas.html", pagina_ofertas())
    escribir("como-elegimos.html", pagina_como_elegimos())
    escribir("aviso-afiliados.html", pagina_aviso())
    escribir("privacidad.html", pagina_privacidad())
    escribir("404.html", pagina_404())
    for c in CATS:
        escribir("categoria-%s.html" % c["id"], pagina_categoria(c))
    for b in LIBROS:
        escribir("libro-%s.html" % b["id"], pagina_libro(b))
    for g in GUIAS:
        escribir("%s.html" % g["slug"], pagina_guia(g))

    escribir("robots.txt", robots_txt())
    escribir("site.webmanifest", webmanifest())
    sm = sitemap([p for p in escritas if p.endswith(".html")])
    if sm:
        escribir("sitemap.xml", sm)
    else:
        print("[!] Sin DOMINIO no hay sitemap.xml ni URLs canonicas.")

    # se apunta cuando se construyo, para detectar ediciones a mano la proxima vez
    io.open(os.path.join(BASE, ".ultima-construccion"), "w",
            encoding="utf-8", newline="\n").write(str(time.time()))

    print("[+] %d archivos generados · %d libros · versión %s" % (len(escritas), len(LIBROS), VER))
    for n in escritas:
        print("    ", n)
    return 0

if __name__ == "__main__":
    sys.exit(main())
