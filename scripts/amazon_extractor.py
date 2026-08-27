#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
================================================================================
 Amazon Product Extractor  ·  Scrapling / StealthyFetcher
================================================================================

Extrae de un producto de Amazon usando SOLO el enlace:
    · Enlace de afiliados original + tag + ASIN + URL canónica
    · Título, marca, precio, moneda, valoración y nº de reseñas
    · TODAS las imágenes en máxima resolución (hiRes)
    · Viñetas de características (feature bullets)
    · Descripción del producto y contenido A+
    · Ficha técnica y detalles del producto (tablas + detail bullets)
    · Reseñas de clientes con TEXTO COMPLETO (autor, título, estrellas, fecha,
      compra verificada y votos útiles) — solo las que muestra la propia página
      del producto (la "primera página"), sin recorrer la lista completa.

--------------------------------------------------------------------------------
CONTRATO DE ENTRADA  (IMPORTANTE)
--------------------------------------------------------------------------------
El enlace que recibe este script SIEMPRE es un ENLACE DE AFILIADOS. Puede llegar
en dos formas y ambas se aceptan:

    1) Enlace corto de afiliado:   https://amzn.to/XXXXXXX
    2) URL completa con el tag:    https://www.amazon.es/dp/ASIN?...&tag=mi-tag-21&...

El script NO necesita que se lo resuelvan antes: expande él mismo el enlace
corto siguiendo las redirecciones (sin llegar a cargar la página pesada de
Amazon, para ir rápido y no toparse con bloqueos). Del enlace de afiliados se
derivan y se guardan como campos de la ficha:

    · affiliate_url   -> el enlace de afiliados TAL CUAL se recibió (se conserva
                         siempre, es el que hay que reutilizar para monetizar).
    · affiliate_tag   -> el identificador de afiliado extraído (p. ej. mi-tag-21).
    · resolved_url    -> la URL de Amazon ya expandida (con sus parámetros).
    · canonical_url   -> URL limpia del producto (https://dominio/dp/ASIN).
    · asin            -> identificador único del producto en Amazon.

--------------------------------------------------------------------------------
POR QUÉ NO FALLA  (mecanismos anti-fallo, por si Amazon cambia algo)
--------------------------------------------------------------------------------
· Descarga con navegador STEALTH (Camoufox vía StealthyFetcher): pasa el
  anti-bot de Amazon sin APIs ni solvers. En las pruebas devuelve HTTP 200 y
  sin captcha.
· Espera al selector #productTitle antes de leer, para asegurar que la página
  ha cargado del todo (network_idle=True).
· Cada campo se intenta con VARIOS selectores de respaldo encadenados: si Amazon
  renombra un contenedor, el siguiente selector lo cubre.
· Las imágenes se recogen de 4 fuentes distintas (JSON hiRes incrustado, JSON
  'large', atributo data-a-dynamic-image y selectores directos del visor) y se
  normalizan a la resolución original más grande.
· Se filtran pósters de vídeo, sprites e iconos para quedarnos solo con fotos
  reales del producto.
· Se detecta explícitamente si Amazon devuelve un captcha/bloqueo y se avisa.

--------------------------------------------------------------------------------
USO
--------------------------------------------------------------------------------
    python amazon_extractor.py "<enlace_de_afiliados>" [--download] [--out carpeta]

    <enlace_de_afiliados>   amzn.to/... corto  o  amazon.*/...?tag=...  (afiliado)
    --download              descarga también las imágenes a <carpeta>/imagenes/
    --out carpeta           carpeta de salida (por defecto la actual)

SALIDA
    · <carpeta>/producto.json   -> todos los datos estructurados
    · <carpeta>/imagenes/*.jpg   -> imágenes (si se pasa --download)

Requiere: pip install "scrapling[all]>=0.4.7"  +  scrapling install
================================================================================
"""

import sys
import re
import os
import json
import argparse
import urllib.request
import urllib.error
from urllib.parse import urlparse, urljoin, parse_qs

from scrapling.fetchers import StealthyFetcher


# User-Agent realista para la fase de resolución del enlace (no para el scraping,
# que lo hace el navegador stealth).
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def clean(text):
    """Colapsa espacios en blanco y devuelve None si queda vacío."""
    if text is None:
        return None
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text or None


def first(selector_result):
    """Devuelve el primer texto limpio de un resultado de selección de Scrapling."""
    try:
        val = selector_result.get()
    except Exception:
        val = None
    return clean(val)


def normalize_asin(url_or_text):
    """Extrae el ASIN (10 caracteres alfanuméricos) de una URL o texto de Amazon."""
    if not url_or_text:
        return None
    m = re.search(r"/(?:dp|gp/product|product|gp/aw/d)/([A-Z0-9]{10})", url_or_text)
    if m:
        return m.group(1)
    m = re.search(r"[/?&](?:asin|ASIN)=([A-Z0-9]{10})", url_or_text)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z0-9]{10})\b", url_or_text)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# Resolución del ENLACE DE AFILIADOS
# --------------------------------------------------------------------------- #

def resolve_affiliate_link(link, max_hops=6):
    """
    Expande un enlace de afiliados (amzn.to/... o URL completa) siguiendo las
    redirecciones HTTP UNA A UNA, y se detiene en cuanto llega a un dominio
    amazon.* — así obtenemos la URL final con el parámetro `tag` SIN cargar la
    página pesada de Amazon (más rápido y sin riesgo de bloqueo en este paso).

    Devuelve la URL de Amazon ya expandida (o el propio enlace si no se pudo
    resolver, para que el flujo continúe igualmente).
    """
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        # Anulamos el auto-seguimiento: gestionamos cada salto a mano.
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    current = link

    for _ in range(max_hops):
        netloc = urlparse(current).netloc.lower()
        # Ya estamos en Amazon: esta es la URL buena, no seguimos cargando.
        if "amazon." in netloc:
            return current
        req = urllib.request.Request(current, headers={"User-Agent": _UA})
        try:
            resp = opener.open(req, timeout=20)
            code = resp.getcode()
            if code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location")
                if not loc:
                    return current
                current = urljoin(current, loc)
                continue
            return resp.geturl() or current          # 2xx: es la final
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location")
                if not loc:
                    return current
                current = urljoin(current, loc)
                continue
            return current
        except Exception:
            return current
    return current


def affiliate_tag_from(url):
    """Extrae el identificador de afiliado (parámetro `tag`) de una URL de Amazon."""
    try:
        q = parse_qs(urlparse(url).query)
        val = q.get("tag", [None])[0]
        return clean(val)
    except Exception:
        return None


def build_canonical(resolved_url, asin):
    """Construye la URL limpia del producto: https://<dominio>/dp/<ASIN>."""
    if not asin:
        return None
    netloc = urlparse(resolved_url).netloc if resolved_url else ""
    if "amazon." not in netloc:
        netloc = "www.amazon.es"        # respaldo razonable para enlaces .es
    return f"https://{netloc}/dp/{asin}"


# --------------------------------------------------------------------------- #
# Extracción de imágenes (varias fuentes para no fallar)
# --------------------------------------------------------------------------- #

def extract_images(page, html):
    urls = []

    # Fuente 1: JSON incrustado 'colorImages' -> hiRes (máxima calidad)
    for m in re.finditer(r'"hiRes":"(https:[^"]+?)"', html):
        urls.append(m.group(1).replace("\\/", "/"))

    # Fuente 2: 'large' como respaldo cuando hiRes es null
    for m in re.finditer(r'"large":"(https:[^"]+?)"', html):
        urls.append(m.group(1).replace("\\/", "/"))

    # Fuente 3: atributo data-a-dynamic-image (las claves son URLs)
    for attr in re.finditer(r'data-a-dynamic-image=(?:\'|")(\{.*?\})(?:\'|")', html):
        try:
            data = json.loads(attr.group(1).replace("&quot;", '"'))
            urls.extend(data.keys())
        except Exception:
            pass

    # Fuente 4: selectores directos del visor, por si todo lo anterior cambia
    for sel in ["#landingImage::attr(src)", "#imgTagWrapperId img::attr(src)",
                "#altImages img::attr(src)"]:
        try:
            urls.extend([u for u in page.css(sel).getall() if u])
        except Exception:
            pass

    # Marcadores de imágenes que NO son fotos de producto (pósters de vídeo,
    # sprites, iconos, píxeles transparentes).
    NON_PRODUCT = re.compile(
        r'(play-button|play-icon|mb-image-grid|PKplay|PKmb|360_icon|sprite|overlay|'
        r'hqdefault|transparent-pixel|grey-pixel|-thumb)', re.I)

    cleaned, seen = [], set()
    for u in urls:
        if not u or "media-amazon.com/images/I/" not in u:
            continue
        # Descartar ANTES de normalizar (los marcadores viven en el sufijo).
        if NON_PRODUCT.search(u):
            continue
        # Normaliza a máxima resolución: reduce ".../I/<id><.modificadores>.jpg"
        # a ".../I/<id>.jpg". Sin token de tamaño, Amazon sirve la resolución
        # original (la más grande disponible).
        full = re.sub(r'(/images/I/[A-Za-z0-9@%+\-]+)\.[^/]*$', r'\1.jpg', u)
        if full not in seen:
            seen.add(full)
            cleaned.append(full)
    return cleaned


# --------------------------------------------------------------------------- #
# Extracción de detalles / ficha técnica
# --------------------------------------------------------------------------- #

def extract_availability(page):
    """
    Devuelve el mensaje de disponibilidad legible (p. ej. 'In stock' o
    'Currently unavailable.'), descartando el código de <script> que Amazon
    incrusta dentro del contenedor #availability.
    """
    parts = [clean(t) for t in page.css("#availability ::text").getall() if clean(t)]
    good = [p for p in parts
            if p and "{" not in p and "function" not in p and "P.when" not in p
            and ";" not in p and len(p) < 120]
    return " ".join(good[:2]) if good else None


def extract_price(page, html):
    """
    Precio con varios selectores de respaldo + reconstrucción whole/fraction +
    regex sobre el JSON incrustado. Amazon cambia el markup del precio a menudo;
    con esta cadena de fallbacks el precio se obtiene en la gran mayoría de casos
    (siempre que el producto esté EN STOCK y se acceda desde el país correcto).
    """
    sels = [
        "#corePriceDisplay_desktop_feature_div span.a-offscreen::text",
        "#corePrice_feature_div span.a-offscreen::text",
        "#apex_desktop span.a-offscreen::text",
        "span.priceToPay span.a-offscreen::text",
        "span.apexPriceToPay span.a-offscreen::text",
        "#price_inside_buybox::text",
        "#newBuyBoxPrice::text",
        "#corePrice_desktop span.a-offscreen::text",
        ".a-price span.a-offscreen::text",
        "#priceblock_ourprice::text",
        "#priceblock_dealprice::text",
    ]
    for s in sels:
        v = first(page.css(s))
        if v and re.search(r"\d", v):
            return v
    whole = first(page.css("span.a-price-whole::text"))
    if whole and re.search(r"\d", whole):
        frac = first(page.css("span.a-price-fraction::text")) or "00"
        sym = first(page.css("span.a-price-symbol::text")) or "€"
        return "%s,%s %s" % (whole.strip().rstrip(",."), frac, sym)
    for pat in [r'"priceAmount":\s*([0-9]+(?:\.[0-9]+)?)',
                r'"displayPrice":"([^"]+)"',
                r'"buyingPrice":\s*([0-9]+(?:\.[0-9]+)?)',
                r'"price":"([0-9.,]+\s*€?)"']:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def extract_details(page):
    details = {}

    # Tablas técnicas (productDetails_techSpec_section_1, ..._detailBullets_...)
    for row in page.css("table.prodDetTable tr"):
        key = first(row.css("th::text"))
        val = first(row.css("td::text"))
        if key and val:
            details[key] = val

    # Tablas de atributos (a-keyvalue en la sección de detalles)
    for row in page.css("#productDetails_db_sections tr, .a-keyvalue tr"):
        key = first(row.css("th::text"))
        val = first(row.css("td::text"))
        if key and val and key not in details:
            details[key] = val

    # detailBullets (lista con "Clave : Valor")
    for li in page.css("#detailBullets_feature_div li"):
        spans = [clean(s) for s in li.css("span::text").getall() if clean(s)]
        spans = [s for s in spans if s and s not in ("‎", "‏", ":")]
        if len(spans) >= 2:
            key = spans[0].rstrip(":").strip()
            val = " ".join(spans[1:]).strip()
            if key and val and key not in details:
                details[key] = val

    return details


# --------------------------------------------------------------------------- #
# Extracción de RESEÑAS (texto completo, solo la primera página)
# --------------------------------------------------------------------------- #

def extract_reviews(page):
    """
    Extrae las reseñas que la propia página del producto muestra (las "top
    reviews" = primera página). NO recorre la lista completa de opiniones.

    De cada reseña saca: autor, título, estrellas, fecha, texto completo,
    si es compra verificada y el nº de votos útiles.
    """
    _STARS = re.compile(r'(de 5 estrellas|out of 5 stars|estrellas|stars)', re.I)
    reviews = []

    for r in page.css('[data-hook="review"]'):
        # Estrellas de la reseña
        rating = (first(r.css('[data-hook="review-star-rating"] span.a-icon-alt::text'))
                  or first(r.css('[data-hook="cmps-review-star-rating"] span.a-icon-alt::text')))

        # Título — Amazon usa dos markups según el diseño:
        #   nuevo: data-hook="reviewTitle" (un <h5>)   ·   antiguo: data-hook="review-title"
        title = first(r.css('[data-hook="reviewTitle"]::text'))
        if not title:
            title_spans = [clean(t) for t in r.css('[data-hook="review-title"] span::text').getall()
                           if clean(t)]
            title_spans = [t for t in title_spans if not _STARS.search(t)]
            title = " ".join(title_spans) if title_spans else first(r.css('[data-hook="review-title"]::text'))

        # Texto completo del cuerpo — nuevo (reviewRichContentContainer / reviewText)
        # con respaldo al antiguo (review-body).
        body_parts = [clean(t) for t in r.css('[data-hook="reviewRichContentContainer"] ::text').getall()
                      if clean(t)]
        if not body_parts:
            body_parts = [clean(t) for t in r.css('[data-hook="reviewText"] span::text').getall()
                          if clean(t)]
        if not body_parts:
            body_parts = [clean(t) for t in r.css('[data-hook="review-body"] span::text').getall()
                          if clean(t)]
        # Dedupe conservando el orden (por si el markup duplica texto colapsado/expandido).
        body = " ".join(dict.fromkeys(body_parts)) if body_parts else None

        author = first(r.css('.a-profile-name::text'))
        date = first(r.css('[data-hook="review-date"]::text'))
        verified = bool(r.css('[data-hook="avp-badge"]'))
        helpful = first(r.css('[data-hook="helpful-vote-statement"]::text'))

        if body or title:
            reviews.append({
                "author": author,
                "rating": rating,
                "title": title,
                "date": date,
                "verified_purchase": verified,
                "helpful": helpful,
                "text": body,
            })
    return reviews


# --------------------------------------------------------------------------- #
# Núcleo
# --------------------------------------------------------------------------- #

def extract(affiliate_url):
    # 1) Resolver el ENLACE DE AFILIADOS -> URL de Amazon expandida + tag + ASIN.
    resolved_url = resolve_affiliate_link(affiliate_url)
    affiliate_tag = affiliate_tag_from(resolved_url) or affiliate_tag_from(affiliate_url)
    asin = normalize_asin(resolved_url) or normalize_asin(affiliate_url)
    canonical_url = build_canonical(resolved_url, asin)

    # URL que abriremos en el navegador: la canónica limpia si tenemos ASIN;
    # si no, la resuelta; y si tampoco, el propio enlace (el navegador seguirá
    # la redirección igualmente).
    fetch_url = canonical_url or resolved_url or affiliate_url

    print(f"[+] Enlace afiliado : {affiliate_url}", file=sys.stderr)
    print(f"[+] Resuelto a      : {resolved_url}", file=sys.stderr)
    print(f"[+] Tag afiliado    : {affiliate_tag}", file=sys.stderr)
    print(f"[+] ASIN            : {asin}", file=sys.stderr)
    print(f"[+] Descargando (stealth): {fetch_url}", file=sys.stderr)

    # 2) Descargar la página con el navegador stealth.
    # IMPORTANTE: google_search=True (referer google) es lo que evita el bloqueo
    # anti-bot de Amazon. Con google_search=False, Amazon devuelve muchas veces una
    # página de bloqueo sin #productTitle. Este flag fue clave para que el scraper
    # funcione de forma fiable. (Aun así conviene reintentar 1-2 veces ante bloqueos
    # puntuales — ver 06-populate-pipeline.md.)
    page = StealthyFetcher.fetch(
        fetch_url,
        headless=True,
        network_idle=True,
        google_search=True,
        wait_selector="#productTitle",
        timeout=60000,
        block_webrtc=True,
    )

    html = page.html_content
    if page.status:
        print(f"[+] HTTP {page.status}", file=sys.stderr)

    # Enlace caído: /dp/ASIN devuelve 404 cuando el producto ha sido retirado o el
    # ASIN es solo una variación no direccionable. Se avisa para que NO se invente
    # un producto: hay que pedir al usuario un enlace actualizado.
    if page.status == 404 or re.search(r'(Documento no encontrado|Page Not Found|Buscá|no encontrada)', html or "", re.I):
        print("[!] ENLACE CAÍDO (HTTP 404 / producto no encontrado). "
              "Este ASIN ya no existe en Amazon: pide al usuario un enlace actualizado.",
              file=sys.stderr)

    title = first(page.css("#productTitle::text"))

    # Si no hay título, comprobar bloqueo/captcha para avisar con claridad.
    if not title and re.search(
            r'(captcha|Introduce los caracteres|Type the characters|Robot Check|'
            r'automated access)', html, re.I):
        print("[!] Amazon mostró un captcha/bloqueo. Reintenta o usa --proxy.",
              file=sys.stderr)

    # ASIN de respaldo desde la propia página (link canónico) si aún no lo tenemos.
    if not asin:
        asin = normalize_asin(first(page.css("link[rel='canonical']::attr(href)")))
        canonical_url = canonical_url or build_canonical(resolved_url, asin)

    data = {
        # --- Enlace de afiliados y localización del producto ---
        "affiliate_url": affiliate_url,        # el enlace de afiliados TAL CUAL se recibió
        "affiliate_tag": affiliate_tag,        # identificador de afiliado (tag)
        "resolved_url": resolved_url,          # URL de Amazon expandida
        "canonical_url": canonical_url,        # URL limpia del producto
        "asin": asin,
        # --- Datos del producto ---
        "title": title,
        "brand": first(page.css("#bylineInfo::text")) or first(page.css("a#bylineInfo::text")),
        "price": extract_price(page, html),
        "rating": (first(page.css("#acrPopover span.a-icon-alt::text"))
                   or first(page.css("i.a-icon-star span::text"))),
        "reviews_count": first(page.css("#acrCustomerReviewText::text")),
        "availability": extract_availability(page),
        "feature_bullets": [
            clean(t) for t in page.css("#feature-bullets li span.a-list-item::text").getall()
            if clean(t)
        ],
        "description": (first(page.css("#productDescription span::text"))
                        or first(page.css("#productDescription p::text"))
                        or first(page.css("#productDescription::text"))),
        "aplus_text": [
            clean(t) for t in page.css("#aplus p::text, #aplus_feature_div p::text").getall()
            if clean(t)
        ][:40],
        "details": extract_details(page),
        "reviews": extract_reviews(page),
        "images": extract_images(page, html),
    }
    return data


def download_images(urls, folder):
    os.makedirs(folder, exist_ok=True)
    saved = []
    for i, u in enumerate(urls, 1):
        ext = os.path.splitext(urlparse(u).path)[1] or ".jpg"
        dest = os.path.join(folder, f"img_{i:02d}{ext}")
        try:
            req = urllib.request.Request(u, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
                f.write(r.read())
            saved.append(dest)
            print(f"    - guardada {dest}", file=sys.stderr)
        except Exception as e:
            print(f"    ! error con {u}: {e}", file=sys.stderr)
    return saved


def main():
    ap = argparse.ArgumentParser(
        description="Extractor de productos de Amazon a partir de un ENLACE DE AFILIADOS (Scrapling)")
    ap.add_argument("url", help="Enlace de afiliados: amzn.to/... o amazon.*/...?tag=...")
    ap.add_argument("--download", action="store_true", help="Descargar las imágenes")
    ap.add_argument("--out", default=".", help="Carpeta de salida")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    data = extract(args.url)

    if args.download and data["images"]:
        data["images_local"] = download_images(data["images"], os.path.join(args.out, "imagenes"))

    out_json = os.path.join(args.out, "producto.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Resumen legible
    print("\n" + "=" * 70)
    print(f"AFILIADO    : {data['affiliate_url']}")
    print(f"TAG         : {data['affiliate_tag']}   ·   ASIN: {data['asin']}")
    print(f"TÍTULO      : {data['title']}")
    print(f"MARCA       : {data['brand']}")
    print(f"PRECIO      : {data['price']}")
    print(f"VALORACIÓN  : {data['rating']}  ({data['reviews_count']})")
    print(f"IMÁGENES    : {len(data['images'])}")
    print(f"CARACT.     : {len(data['feature_bullets'])} viñetas")
    print(f"DETALLES    : {len(data['details'])} campos")
    print(f"RESEÑAS     : {len(data['reviews'])} (texto completo, 1ª página)")
    print(f"JSON        : {out_json}")
    print("=" * 70)


if __name__ == "__main__":
    main()
