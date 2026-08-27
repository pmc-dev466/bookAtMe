# -*- coding: utf-8 -*-
"""Genera las dos texturas de madera de la estanteria en 3D.

    python tools/generar_madera.py

Escribe assets/img/madera-balda.webp y assets/img/madera-pared.webp.

Por que un archivo y no dibujarlo al vuelo en el navegador, como el resto de
texturas de la estanteria: la madera es lo primero que se ve y no puede salir
distinta de lo aprobado. Aqui el resultado se mira antes de publicarlo. El
demo original traia su madera en un base64 gigante e irrecuperable; esto es lo
mismo pero reproducible: se vuelve a ejecutar y sale igual (la semilla manda).
"""
import math
import os
from PIL import Image, ImageDraw, ImageFilter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "assets", "img")


def azar(s):
    """El mismo generador determinista que usa lib/estanteria3d.js."""
    st = [s & 0xFFFFFFFF]

    def r():
        st[0] = (st[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = st[0]
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return r


def mezcla(c1, c2, k):
    return tuple(int(round(a + (b - a) * k)) for a, b in zip(c1, c2))


def veta(dc, rnd, x0, x1, y0, y1, base, claro, oscuro, cuantas):
    """Lineas de veta dentro de una franja, corriendo a lo largo de x."""
    ancho = max(x1 - x0, 1)
    for _ in range(cuantas):
        yc = y0 + rnd() * (y1 - y0)
        amp = 1.5 + rnd() * ((y1 - y0) * 0.16)
        fase = rnd() * math.tau
        frec = (0.5 + rnd() * 2.4) / ancho * math.tau
        fuerte = rnd() > 0.66
        col = mezcla(base, oscuro if rnd() > 0.36 else claro, 0.5 if fuerte else 0.24)
        alfa = int((70 if fuerte else 34) + rnd() * 40)
        grosor = (1 + int(rnd() * 2)) if fuerte else 1
        pts, x = [], x0
        while x <= x1:
            pts.append((x, yc + math.sin(x * frec + fase) * amp
                        + math.sin(x * frec * 2.9 + fase * 1.7) * amp * 0.4))
            x += 10
        dc.line(pts, fill=col + (alfa,), width=grosor, joint="curve")


def madera(w, h, base, claro, oscuro, tablas=0, vertical=False, semilla=7, densidad=26):
    """tablas=0 -> tabla continua. vertical -> la veta corre en vertical."""
    rnd = azar(semilla)
    W, H = (h, w) if vertical else (w, h)   # se dibuja en horizontal y se gira al final

    img = Image.new("RGB", (W, H), base)
    d = ImageDraw.Draw(img)

    # Cada tabla con su tono: es lo que hace que parezcan tablas y no papel pintado.
    franjas = []
    if tablas > 0:
        paso = H / tablas
        for i in range(tablas):
            y0, y1 = i * paso, (i + 1) * paso
            tono = mezcla(base, claro if rnd() > 0.5 else oscuro, 0.05 + rnd() * 0.22)
            d.rectangle([0, y0, W, y1], fill=tono)
            franjas.append((y0, y1, tono))
    else:
        y = 0
        while y < H:
            alto = 26 + rnd() * 90
            tono = mezcla(base, claro if rnd() > 0.5 else oscuro, 0.04 + rnd() * 0.14)
            d.rectangle([0, y, W, y + alto], fill=tono)
            franjas.append((y, y + alto, tono))
            y += alto
        img = img.filter(ImageFilter.GaussianBlur(5))

    # La veta, por tandas, para que las lineas se acumulen unas sobre otras.
    for _ in range(7):
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        for (y0, y1, tono) in franjas:
            veta(dc, rnd, 0, W, y0, y1, tono, claro, oscuro, densidad)
        img = Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")

    # Poro fino.
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    for _ in range(3400):
        x, y = rnd() * W, rnd() * H
        largo = 8 + rnd() * 42
        col = oscuro if rnd() > 0.42 else claro
        dc.line([(x, y), (x + largo, y + (rnd() - 0.5) * 1.6)],
                fill=col + (int(16 + rnd() * 30),), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")

    # Juntas: sombra en el canto de una tabla y filo iluminado en la de al lado.
    if tablas > 0:
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        paso = H / tablas
        for i in range(1, tablas):
            y = i * paso
            dc.line([(0, y - 3), (W, y - 3)], fill=oscuro + (70,), width=5)
            dc.line([(0, y), (W, y)], fill=(0, 0, 0, 190), width=3)
            dc.line([(0, y + 3), (W, y + 3)], fill=claro + (60,), width=2)
        img = Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")

    if vertical:
        img = img.rotate(90, expand=True)
    return img


def main():
    if not os.path.isdir(SALIDA):
        raise SystemExit("no encuentro %s" % SALIDA)

    # Nogal de la balda: se ve de cerca y con luz, va mas claro.
    balda = madera(1024, 512, (74, 43, 29), (158, 104, 63), (30, 16, 9), semilla=7)

    # Pared entablada: mas oscura, para que las portadas destaquen contra ella.
    pared = madera(1024, 1024, (56, 32, 21), (128, 82, 48), (22, 11, 6),
                   tablas=8, vertical=True, semilla=21, densidad=22)

    for nombre, img in (("madera-balda", balda), ("madera-pared", pared)):
        ruta = os.path.join(SALIDA, nombre + ".webp")
        img.save(ruta, "WEBP", quality=86, method=6)
        print("[+] assets/img/%s.webp  %s  %.0f KB"
              % (nombre, "x".join(map(str, img.size)), os.path.getsize(ruta) / 1024))


if __name__ == "__main__":
    main()
