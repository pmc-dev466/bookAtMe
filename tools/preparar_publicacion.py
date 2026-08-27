# -*- coding: utf-8 -*-
"""Deja en publicar/ SOLO lo que debe ver el mundo.

    python tools/preparar_publicacion.py

Por que hace falta: Cloudflare Pages publica la carpeta que le digas, entera.
Si le das la carpeta del proyecto, subirias tambien datos/libros.json (tu base
de datos completa), tools/ (todas las herramientas) y preview/ (10 MB que no
pintan nada). La solucion es darle una carpeta que ya venga limpia.

Lo que SI se publica:
    los .html, styles.css, main.js, lib/, assets/,
    _headers, robots.txt, sitemap.xml, site.webmanifest

Lo que NO:
    datos/, tools/, scripts/, preview/, .claude/, los .bat, .md, .htaccess,
"""
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "publicar")

CARPETAS = ["lib", "assets"]
EXTENSIONES_RAIZ = (".html", ".css", ".js", ".xml", ".txt", ".webmanifest")
SUELTOS = ["_headers", "_redirects"]

# Ni la libreria de desarrollo ni los archivos de trabajo.
FUERA = ("__pycache__", ".DS_Store", "Thumbs.db")


def limpiar_destino():
    if os.path.isdir(DESTINO):
        shutil.rmtree(DESTINO)
    os.makedirs(DESTINO)


def copiar_archivo(rel):
    origen = os.path.join(RAIZ, rel)
    destino = os.path.join(DESTINO, rel)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.copy2(origen, destino)
    return os.path.getsize(origen)


def main():
    if not os.path.exists(os.path.join(RAIZ, "index.html")):
        print("[!] No hay web generada. Ejecuta antes actualizar.bat")
        return 1

    limpiar_destino()
    n, peso = 0, 0

    # raiz: solo las extensiones publicas, y nada que empiece por punto
    for nombre in sorted(os.listdir(RAIZ)):
        ruta = os.path.join(RAIZ, nombre)
        if not os.path.isfile(ruta) or nombre.startswith("."):
            continue
        if nombre.endswith(EXTENSIONES_RAIZ):
            peso += copiar_archivo(nombre)
            n += 1

    # los sueltos sin extension (_headers), que el filtro de arriba se salta
    for nombre in SUELTOS:
        if os.path.isfile(os.path.join(RAIZ, nombre)):
            peso += copiar_archivo(nombre)
            n += 1

    # carpetas enteras
    for carpeta in CARPETAS:
        base = os.path.join(RAIZ, carpeta)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, nombres in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in FUERA]
            for nom in nombres:
                if nom in FUERA or nom.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, nom), RAIZ)
                peso += copiar_archivo(rel)
                n += 1

    # comprobacion final: que no se haya colado nada privado
    colados = []
    for dirpath, dirnames, nombres in os.walk(DESTINO):
        for nom in nombres:
            rel = os.path.relpath(os.path.join(dirpath, nom), DESTINO)
            if rel.split(os.sep)[0] in ("datos", "tools", "scripts", "preview"):
                colados.append(rel)
            if nom.endswith((".py", ".bat", ".md")):
                colados.append(rel)

    print("=" * 58)
    print(" publicar/  ·  %d archivos  ·  %.1f MB" % (n, peso / 1048576.0))
    print("=" * 58)
    if colados:
        print("\n[X] Se han colado archivos que NO deben publicarse:")
        for c in colados[:10]:
            print("   -", c)
        return 1
    print("\n  Nada privado dentro. Listo para subir:")
    print("      npx wrangler pages deploy publicar --project-name=bookatme")
    return 0


if __name__ == "__main__":
    sys.exit(main())
