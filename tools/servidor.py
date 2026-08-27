# -*- coding: utf-8 -*-
"""Servidor de desarrollo: sirve la web, la reconstruye sola y recarga el navegador.

    python tools/servidor.py [puerto]
    (o doble clic en  desarrollo.bat )

Que hace, y por que existe cada cosa:

1. SIRVE LA WEB como lo hara Cloudflare Pages. `python -m http.server` devuelve
   SU pagina de error ante una direccion que no existe; esto devuelve el
   404.html del proyecto, con codigo 404 de verdad.

2. VIGILA LOS ARCHIVOS FUENTE y reconstruye solo. Guardas datos/libros.json o
   styles.css y, un segundo despues, las paginas ya estan hechas. No hay que
   ejecutar nada a mano.

3. RECARGA EL NAVEGADOR SOLO al terminar la reconstruccion. La pagina lleva un
   trocito de codigo que pregunta cada segundo "ha cambiado algo?" y se recarga
   cuando la respuesta es que si. Eso es lo que se llama "editar en caliente":
   guardas, miras la pantalla, ya esta.

Ese trocito de codigo lo INYECTA ESTE SERVIDOR al vuelo, solo en local. En los
archivos no queda nada, asi que lo que se publica esta limpio.
"""
import os
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8777

# Lo que se vigila. Si cambia algo de aqui, se reconstruye.
VIGILADOS = [
    ("datos", (".json",)),
    ("tools", (".py",)),
    ("lib", (".js",)),
    (".", (".css", ".js")),
]
# lib/three/ es la libreria 3D: 1 MB que nunca se toca, no hace falta mirarla.
IGNORAR = (os.path.join("lib", "three"), os.path.join("lib", "db.js"),
           os.path.join("lib", "estanteria-db.js"), "preview", "assets", "scripts")

version = {"n": 0, "estado": "listo"}
candado = threading.Lock()

RECARGA = """
<script>
/* Solo en local: lo inyecta tools/servidor.py, no esta en los archivos. */
(function () {
  var mia = null;
  setInterval(function () {
    fetch("/__version", { cache: "no-store" }).then(function (r) { return r.text(); })
      .then(function (v) {
        if (mia === null) { mia = v; return; }
        if (v !== mia) location.reload();
      }).catch(function () {});
  }, 1000);
})();
</script>
"""


def firma():
    """Un numero que cambia si cambia cualquier archivo vigilado."""
    total = 0
    for carpeta, exts in VIGILADOS:
        base = os.path.join(RAIZ, carpeta)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, nombres in os.walk(base):
            rel = os.path.relpath(dirpath, RAIZ)
            if any(rel == i or rel.startswith(i + os.sep) for i in IGNORAR):
                dirnames[:] = []
                continue
            for n in nombres:
                if n.endswith(exts):
                    r = os.path.join(dirpath, n)
                    if any(os.path.relpath(r, RAIZ).startswith(i) for i in IGNORAR):
                        continue
                    try:
                        total += int(os.path.getmtime(r))
                    except OSError:
                        pass
            if carpeta == ".":
                dirnames[:] = []      # la raiz, sin bajar a las subcarpetas
    return total


def reconstruir():
    with candado:
        version["estado"] = "construyendo"
    print("  ~ algo ha cambiado, reconstruyendo...")
    r = subprocess.run([sys.executable, os.path.join("tools", "build_site.py")],
                       cwd=RAIZ, capture_output=True, text=True)
    if r.returncode == 0:
        print("  + listo, el navegador se recarga solo")
    else:
        print("  ! ERROR al construir:")
        for linea in (r.stdout + r.stderr).strip().split("\n")[-12:]:
            print("      " + linea)
    with candado:
        version["n"] += 1
        version["estado"] = "listo"


def vigilar():
    anterior = firma()
    while True:
        time.sleep(0.7)
        try:
            ahora = firma()
        except OSError:
            continue
        if ahora != anterior:
            anterior = ahora
            time.sleep(0.25)        # que termine de guardarse el archivo
            anterior = firma()
            reconstruir()


class Manejador(SimpleHTTPRequestHandler):
    extensions_map = dict(SimpleHTTPRequestHandler.extensions_map)
    extensions_map.update({
        ".webp": "image/webp", ".webmanifest": "application/manifest+json",
        ".mjs": "text/javascript", ".js": "text/javascript",
        ".json": "application/json", ".svg": "image/svg+xml",
    })

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=RAIZ, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/__version"):
            with candado:
                cuerpo = ("%d-%s" % (version["n"], version["estado"])).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        super().do_GET()

    def send_head(self):
        """Se cuela aqui para meter el codigo de recarga en las paginas HTML."""
        ruta = self.translate_path(self.path)
        if os.path.isdir(ruta):
            indice = os.path.join(ruta, "index.html")
            if os.path.exists(indice):
                ruta = indice
        if ruta.endswith(".html") and os.path.exists(ruta):
            with open(ruta, "rb") as f:
                doc = f.read()
            if b"</body>" in doc:
                doc = doc.replace(b"</body>", RECARGA.encode() + b"</body>", 1)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(doc)))
            self.end_headers()
            import io as _io
            return _io.BytesIO(doc)
        return super().send_head()

    def send_error(self, code, message=None, explain=None):
        """Ante una direccion que no existe, la 404 del sitio (como Cloudflare)."""
        if code == 404:
            ruta = os.path.join(RAIZ, "404.html")
            if os.path.exists(ruta):
                with open(ruta, "rb") as f:
                    cuerpo = f.read()
                if b"</body>" in cuerpo:
                    cuerpo = cuerpo.replace(b"</body>", RECARGA.encode() + b"</body>", 1)
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(cuerpo)
                return
        super().send_error(code, message, explain)

    def log_message(self, formato, *args):
        if args and str(args[1]).startswith(("4", "5")) and "__version" not in str(args[0]):
            sys.stderr.write("  %s %s\n" % (args[1], args[0]))


def main():
    hilo = threading.Thread(target=vigilar, daemon=True)
    hilo.start()
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    except OSError:
        print("\n[ERROR] El puerto %d ya esta ocupado." % PUERTO)
        print("        Seguramente hay otro servidor abierto de antes.")
        print("        Cierra esa ventana, o abre esta en otro puerto:")
        print("            python tools/servidor.py 8778\n")
        return 1
    with servidor:
        print("=" * 58)
        print(" Servidor de desarrollo")
        print("=" * 58)
        print("  http://localhost:%d" % PUERTO)
        print()
        print("  Guarda cualquier archivo y la web se reconstruye y")
        print("  se recarga sola. No hace falta actualizar.bat.")
        print()
        print("  La pagina de error: http://localhost:%d/loquesea" % PUERTO)
        print("  Ctrl+C para parar")
        print("=" * 58)
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print("\nparado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
