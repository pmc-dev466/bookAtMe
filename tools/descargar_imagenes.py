#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga las portadas de Amazon y las convierte a WebP en assets/img/."""
import io, os, sys, urllib.request
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "assets", "img")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126 Safari/537.36"}

IMAGENES = {
 "la-paciente-silenciosa": ["81a4E-iiE6L", "816iyHPJENL"],
 "la-asistenta": ["71UilMg9WPL", "71havglGFnL", "71ETEJ7YXxL"],
 "las-gratitudes": ["91MTGLuKFDL", "51VHLHCLzIL"],
 "el-hombre-en-busca-de-sentido": ["711oUNxxOzL", "61By+AvZOVL"],
 "comeras-flores": ["51vFJp0InYL"],
 "la-biblioteca-de-la-medianoche": ["71uyykCirrL"],
 "llevara-tu-nombre": ["71dpgk7jatL", "61cu5YWOrzL", "613FMJQjYZL"],
 "riete-de-las-bodas": ["61TGimj+PzL"],
 "el-club-de-las-indomables": ["81QLaLTOr0L", "71MkOcmQR3L", "81BOyM4bxxL"],
 # --- primera tanda de ampliacion (capturados el 2026-08-26) ---
 "el-secreto-de-la-asistenta": ["71tFruc1CpL", "5142dZNsORL", "71QPS7OcemL"],
 "la-profesora": ["61V9Oatax8L"],
 "alas-de-hierro": ["71W6mRIMgnL"],
 "proyecto-hail-mary": ["71xMvXNcbOL", "815I+6y5rmL", "81qHbW+4XUL"],
 "alchemised": ["91lGejTwzKL", "91xAWZNjRKL", "71XJFMgplzL"],
 "verity": ["61Uzj0+kW1L"],
 "el-duque-y-yo": ["71odEMjJZsL", "71OT4hhsgAL"],
 "los-siete-maridos-de-evelyn-hugo": ["71WOm2J4LpL"],
 "la-peninsula-de-las-casas-vacias": ["71tizXJrF5L"],
 "el-recluso": ["61PJhQc5koL"],
 # --- pasatiempos: los mas vendidos de Amazon.es en Libros ---
 "murdoku": ["81QzAPcftIL", "81cjAsBrArL"],
 "murdoku-viaje-al-pasado": ["61eHIoW4ZKL"],
 "murdle": ["71o41wV-v1L", "71vcBX50fiL"],
 "sopicidios": ["71mUvKw6WJL"],
 # Alas de sangre: se cambia a la edicion que MAS se vende (tapa dura, n.o 322)
 # en vez de la especial de bolsillo (n.o 1068).
 "alas-de-sangre": ["71M8IoER7JL"],
}

def descargar(code):
    url = "https://m.media-amazon.com/images/I/%s._SL1500_.jpg" % code.replace("+", "%2B")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

def main():
    os.makedirs(OUT, exist_ok=True)
    ok = fail = 0
    for slug, codes in IMAGENES.items():
        for i, code in enumerate(codes, 1):
            destino = os.path.join(OUT, "%s-%d.webp" % (slug, i))
            if os.path.exists(destino):
                ok += 1; continue
            try:
                img = Image.open(io.BytesIO(descargar(code)))
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                img.thumbnail((1200, 1200), Image.LANCZOS)
                img.save(destino, "WEBP", quality=86, method=6)
                print("  [ok] %s  (%dx%d)" % (os.path.basename(destino), *img.size))
                ok += 1
            except Exception as e:
                print("  [!!] %s -> %s" % (os.path.basename(destino), e)); fail += 1
    print("\n%d imagenes listas, %d fallos" % (ok, fail))
    return 1 if fail else 0

if __name__ == "__main__":
    sys.exit(main())
