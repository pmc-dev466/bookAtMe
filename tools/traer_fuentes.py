# -*- coding: utf-8 -*-
"""Descarga las tipografias de Google y las deja dentro del proyecto.

POR QUE existe esto en vez de enlazar a fonts.googleapis.com:

  1. El salto al cargar. Pidiendolas a Google, el texto aparecia primero con la
     letra del sistema y luego cambiaba a la buena. No ocupan lo mismo (los
     titulares son un 9% mas estrechos, los parrafos un 9%, el menu un 7% mas
     ancho), asi que al cambiar se recolocaban las lineas y la pagina entera
     pegaba un salto. Google mide eso (lo llama CLS) y lo usa para posicionar.

  2. Privacidad. Cada visitante enviaba su IP a un servidor de Google sin
     enterarse. En Europa eso es delicado.

CUANDO EJECUTARLO: solo si quieres cambiar de tipografia o de grosores.
El resto del tiempo no hace falta; los archivos ya estan en assets/fonts/.

    python tools/traer_fuentes.py

Genera assets/fonts/*.woff2 y fuentes.css. No edites fuentes.css a mano: este
script lo sobrescribe entero.
"""
import io
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Los rangos (300..600) en vez de valores sueltos (300;400;500;600) son la
# diferencia entre 8 archivos y 24: Google devuelve UNA tipografia variable por
# familia en vez de una por grosor. 704 KB frente a 1756 KB.
URL = ("https://fonts.googleapis.com/css2"
       "?family=Fraunces:opsz,wght@9..144,300..600"
       "&family=Inter:wght@400..700"
       "&family=Newsreader:ital,opsz,wght@0,6..72,300..500;1,6..72,300..500"
       "&display=swap")

# Solo alfabeto latino. El vietnamita, el griego y el cirilico sobran en una web
# en espanol y eran mas de la mitad del peso.
ALFABETOS = ("latin", "latin-ext")

# Sin un User-Agent moderno, Google devuelve .ttf en vez de .woff2, que pesa el doble.
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

CABECERA = """/* =========================================================================
   TIPOGRAFIAS PROPIAS  ·  lo genera tools/traer_fuentes.py  ·  NO EDITAR A MANO
   -------------------------------------------------------------------------
   Los archivos estan en assets/fonts/ y se sirven desde tu propio dominio, no
   desde Google. Asi no hay salto al cargar la pagina y la IP de tus visitantes
   no sale de tu web. El detalle completo, en tools/traer_fuentes.py.
   ========================================================================= */"""


# ---------------------------------------------------------------------------
# LETRAS DE REPUESTO A MEDIDA
#
# Aunque las tipografias esten en nuestro dominio, en la primera visita todavia
# pueden tardar un poco y el navegador pinta el texto con la letra del sistema.
# Al llegar la buena cambiaba, y como no ocupan lo mismo la pagina daba un
# salto. Medido en la web real: Georgia es un 14,8% mas ancha que Fraunces.
#
# Aqui se declaran las de repuesto ESTIRADAS o ENCOGIDAS para que ocupen
# exactamente lo mismo que la buena. Asi, aunque el navegador use la de
# repuesto un instante, al cambiar no se mueve nada.
#
# Los numeros salen de MEDIR las dos letras en el navegador, no de estimarlos.
# Si algun dia cambias de tipografia hay que volver a medirlos.
# ---------------------------------------------------------------------------
REPUESTOS = [
    # (nombre, letras del sistema que valen, size-adjust, ascent, descent)
    ("Inter Repuesto",      ["Arial", "Helvetica Neue", "Roboto"],
     "105.51%", "91.94%", "22.75%"),
    ("Fraunces Repuesto",   ["Georgia", "Times New Roman", "Noto Serif"],
     "85.24%", "114.98%", "30.50%"),
    ("Newsreader Repuesto", ["Georgia", "Times New Roman", "Noto Serif"],
     "100.13%", "73.91%", "26.97%"),
]


def reglas_repuesto():
    """Las letras de repuesto ajustadas. No descargan nada."""
    out = []
    for nombre, locales, tam, asc, desc in REPUESTOS:
        # local() usa una letra que el visitante YA tiene instalada. Si no tiene
        # ninguna de la lista, la regla simplemente no se aplica y se pasa a la
        # siguiente del stack en styles.css, que es lo que queremos.
        src = ", ".join("local('%s')" % x for x in locales)
        out.append("""@font-face {
  font-family: '%s';
  src: %s;
  size-adjust: %s;
  ascent-override: %s;
  descent-override: %s;
  line-gap-override: 0%%;
}""" % (nombre, src, tam, asc, desc))
    return out


def bajar(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def main():
    print("Pidiendo la hoja de tipografias a Google...")
    css = bajar(URL).decode("utf-8")
    if "woff2" not in css:
        print("[ERROR] Google no ha devuelto woff2. Revisa el User-Agent.")
        return 1

    bloques = [(s, b) for s, b in
               re.findall(r"/\*\s*([a-z0-9-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", css, re.S)
               if s in ALFABETOS]
    if not bloques:
        print("[ERROR] No he encontrado ninguna tipografia latina en la respuesta.")
        return 1

    destino = os.path.join(BASE, "assets", "fonts")
    if not os.path.isdir(destino):
        os.makedirs(destino)

    reglas = [CABECERA]
    peso = 0
    for sub, b in bloques:
        fam = re.search(r"font-family: '([^']+)'", b).group(1)
        grosor = re.search(r"font-weight: ([0-9 ]+);", b).group(1).strip()
        estilo = re.search(r"font-style: (\w+);", b).group(1)
        rango = re.search(r"unicode-range: ([^;]+);", b).group(1).strip()
        url = re.search(r"url\((https://[^)]+\.woff2)\)", b).group(1)

        nombre = "%s-%s%s.woff2" % (fam.lower(), sub, "-italica" if estilo == "italic" else "")
        ruta = os.path.join(destino, nombre)
        datos = bajar(url)
        with open(ruta, "wb") as f:
            f.write(datos)
        peso += len(datos)
        print("   %-34s %6.0f KB" % (nombre, len(datos) / 1024.0))

        # unicode-range es lo que hace que latin-ext solo se descargue si alguna
        # letra lo necesita. Si se quita, todo el mundo se baja el doble.
        reglas.append("""@font-face {
  font-family: '%s';
  font-style: %s;
  font-weight: %s;
  font-display: swap;
  src: url(assets/fonts/%s) format('woff2');
  unicode-range: %s;
}""" % (fam, estilo, grosor, nombre, rango))

    reglas.extend(reglas_repuesto())

    with io.open(os.path.join(BASE, "fuentes.css"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(reglas) + "\n")

    print("")
    print("Listo: %d tipografias, %.0f KB, y fuentes.css regenerado." % (len(bloques), peso / 1024.0))
    print("Acuerdate de reconstruir la web despues (BookAtMe.bat -> 3).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
