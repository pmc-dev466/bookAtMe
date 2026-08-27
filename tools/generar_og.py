# -*- coding: utf-8 -*-
"""Genera los iconos y las miniaturas de compartir (Open Graph).

    python tools/generar_og.py

Escribe:
    assets/icono-180.png, assets/icono-512.png   (icono de la app)
    assets/og/bookatme.jpg                       (miniatura por defecto)
    assets/og/libro-<id>.jpg                     (una por libro, con su portada)

La miniatura Open Graph es lo que se ve cuando alguien pega un enlace de la web
en WhatsApp, Telegram, X o Facebook. Sin ella sale un recuadro gris y nadie
pincha. Van en JPG a proposito: WebP todavia falla en algunos previsualizadores.

Hay que volver a ejecutarlo al anadir libros nuevos.
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(RAIZ, "assets")
SALIDA_OG = os.path.join(ASSETS, "og")
DATOS = os.path.join(RAIZ, "datos", "libros.json")

ANCHO, ALTO = 1200, 630
TINTA = (245, 244, 240)
FONDO = (20, 22, 28)
VERDE = (36, 80, 61)
LATON = (168, 124, 46)

# Georgia y Arial vienen con Windows; si faltan, se prueban rutas de Linux/Mac
# y en ultimo caso Pillow pone su tipografia de mapa de bits (fea pero funciona).
CANDIDATAS = {
    "serif": ["georgiab.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"],
    "serif_normal": ["georgia.ttf", "DejaVuSerif.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
    "sans": ["arial.ttf", "DejaVuSans.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/System/Library/Fonts/Supplemental/Arial.ttf"],
    "sans_negrita": ["arialbd.ttf", "DejaVuSans-Bold.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}
DIRS = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"), ""]


def fuente(clase, tam):
    for nombre in CANDIDATAS[clase]:
        for d in DIRS:
            ruta = os.path.join(d, nombre) if d else nombre
            try:
                return ImageFont.truetype(ruta, tam)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()


def ancho_de(dib, txt, f):
    caja = dib.textbbox((0, 0), txt, font=f)
    return caja[2] - caja[0]


def partir(dib, txt, f, limite, max_lineas):
    """Parte el texto en lineas que quepan; la ultima se corta con puntos."""
    palabras = str(txt or "").split()
    lineas, actual = [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if ancho_de(dib, prueba, f) <= limite or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
            if len(lineas) == max_lineas:
                break
    if actual and len(lineas) < max_lineas:
        lineas.append(actual)
    if len(lineas) == max_lineas and len(palabras) > sum(len(l.split()) for l in lineas):
        while lineas[-1] and ancho_de(dib, lineas[-1] + "…", f) > limite:
            lineas[-1] = lineas[-1][:-1]
        lineas[-1] += "…"
    return lineas


def lienzo():
    """Fondo comun: oscuro, con un resplandor calido arriba a la izquierda."""
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    brillo = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(brillo)
    for i in range(70, 0, -1):
        k = i / 70.0
        r = int(560 * k)
        col = (int(FONDO[0] + 26 * (1 - k)), int(FONDO[1] + 20 * (1 - k)), int(FONDO[2] + 14 * (1 - k)))
        d.ellipse([-260 - r // 3, -300 - r // 3, r, r], fill=col)
    img = Image.blend(img, brillo, 0.85)
    d = ImageDraw.Draw(img)
    d.rectangle([0, ALTO - 7, ANCHO, ALTO], fill=VERDE)
    d.rectangle([0, ALTO - 7, 360, ALTO], fill=LATON)
    return img


def marca(dib, x, y):
    f1 = fuente("serif", 40)
    f2 = fuente("sans_negrita", 17)
    dib.text((x, y), "BookAtMe!", font=f1, fill=TINTA)
    ancho = ancho_de(dib, "BookAtMe!", f1)
    dib.text((x + ancho + 16, y + 17), "COMPARATIVAS DE LIBROS", font=f2,
             fill=(150, 146, 138))


def og_marca():
    img = lienzo()
    d = ImageDraw.Draw(img)
    marca(d, 84, 74)
    f = fuente("serif", 76)
    fs = fuente("sans", 30)
    lineas = partir(d, "Los libros más vendidos de Amazon.es, comparados de verdad", f, ANCHO - 168, 3)
    y = 214
    for l in lineas:
        d.text((84, y), l, font=f, fill=TINTA)
        y += 92
    d.text((84, y + 22), "Ficha técnica · pros y contras · nota de calidad-precio",
           font=fs, fill=(168, 164, 155))
    return img


def og_libro(libro, ruta_portada):
    img = lienzo()
    d = ImageDraw.Draw(img)
    marca(d, 84, 62)

    # la portada, encajada a la altura disponible
    izq_texto = 84
    if ruta_portada and os.path.exists(ruta_portada):
        try:
            port = Image.open(ruta_portada).convert("RGB")
            alto_max = 396
            k = alto_max / port.height
            port = port.resize((max(1, int(port.width * k)), alto_max), Image.LANCZOS)
            px, py = 84, 168
            sombra = Image.new("RGB", (port.width + 26, port.height + 26), FONDO)
            img.paste(sombra, (px - 13, py - 9))
            img.paste(port, (px, py))
            d.rectangle([px, py, px + port.width, py + port.height], outline=(70, 66, 60), width=1)
            izq_texto = px + port.width + 56
        except Exception:
            pass

    limite = ANCHO - izq_texto - 84
    ft = fuente("serif", 58)
    fa = fuente("sans", 27)
    fn = fuente("sans_negrita", 24)

    lineas = partir(d, libro["titulo"], ft, limite, 3)
    y = 178
    for l in lineas:
        d.text((izq_texto, y), l, font=ft, fill=TINTA)
        y += 72
    d.text((izq_texto, y + 10), libro.get("autor") or "", font=fa, fill=(176, 172, 163))

    etiquetas = []
    if libro.get("valoracion_media"):
        # sin el simbolo de estrella: Arial no lo trae y sale un cuadrado
        etiquetas.append("%s sobre 5 en Amazon" % str(libro["valoracion_media"]).replace(".", ","))
    if libro.get("num_paginas"):
        etiquetas.append("%s páginas" % libro["num_paginas"])
    if etiquetas:
        d.text((izq_texto, y + 62), "   ·   ".join(etiquetas), font=fn, fill=LATON)
    return img


def icono(tam):
    """El mismo dibujo que assets/favicon.svg, en PNG."""
    esc = tam / 32.0
    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, tam - 1, tam - 1], radius=int(6 * esc), fill=FONDO)
    g = max(2, int(2.2 * esc))
    d.line([(9 * esc, 8 * esc), (18 * esc, 8 * esc)], fill=VERDE, width=g)
    d.line([(9 * esc, 8 * esc), (9 * esc, 25 * esc)], fill=VERDE, width=g)
    d.line([(9 * esc, 25 * esc), (18 * esc, 25 * esc)], fill=VERDE, width=g)
    d.arc([14 * esc, 8 * esc, 26 * esc, 25 * esc], -80, 80, fill=VERDE, width=g)
    d.line([(19 * esc, 8 * esc), (23 * esc, 8 * esc)], fill=LATON, width=g)
    return img


def main():
    if not os.path.isdir(SALIDA_OG):
        os.makedirs(SALIDA_OG)

    with io.open(DATOS, encoding="utf-8") as f:
        libros = json.load(f)["libros"]

    hechas = []

    for tam in (180, 512):
        ruta = os.path.join(ASSETS, "icono-%d.png" % tam)
        icono(tam).save(ruta, "PNG", optimize=True)
        hechas.append(("assets/icono-%d.png" % tam, ruta))

    ruta = os.path.join(SALIDA_OG, "bookatme.jpg")
    og_marca().save(ruta, "JPEG", quality=84, optimize=True, progressive=True)
    hechas.append(("assets/og/bookatme.jpg", ruta))

    for b in libros:
        portada = b.get("imagenes") or []
        portada = os.path.join(RAIZ, portada[0].replace("/", os.sep)) if portada else None
        nombre = "libro-%s.jpg" % b["id"]
        ruta = os.path.join(SALIDA_OG, nombre)
        og_libro(b, portada).save(ruta, "JPEG", quality=84, optimize=True, progressive=True)
        hechas.append(("assets/og/" + nombre, ruta))

    total = sum(os.path.getsize(r) for _, r in hechas)
    for nombre, ruta in hechas:
        print("[+] %-34s %5.0f KB" % (nombre, os.path.getsize(ruta) / 1024))
    print("    %d archivos · %.0f KB en total" % (len(hechas), total / 1024))


if __name__ == "__main__":
    main()
