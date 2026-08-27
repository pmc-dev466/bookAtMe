# Leído — web de afiliados de Amazon.es sobre libros

Web de comparativas de libros para Amazon España. **Ningún libro está escrito a mano**:
todos viven en `datos/libros.json` y las 25 páginas se generan desde ahí.

## Añadir libros (lo habitual)

1. Pásame tus enlaces de afiliado, uno por línea.
2. Yo saco los datos, escribo la ficha y añado el registro a `datos/libros.json`.
3. Se regenera todo:

```bash
python tools/build_site.py
```

Al añadir libros hay que **recalcular las notas de calidad-precio de todos**, porque
son relativas al catálogo. Está explicado en `datos/libros.schema.json`.

Y hay que **mirar las imágenes una a una**: Amazon no las sirve en orden, a veces la
primera es la contraportada. Todo el sitio da por hecho que la primera de la lista es
la portada, así que si no lo es, se reordena la lista a mano. La contraportada de
verdad va en su propio campo y es la que se ve por detrás en la estantería 3D.

Un libro nuevo aparece solo en: la portada, su categoría, el comparador, las ofertas
si tiene descuento, **y la estantería en 3D**. No hay que tocar nada más.

### Reconstruir la web: un solo archivo

Doble clic en **`BookAtMe.bat`** y elige una opcion del menu. O desde la terminal:

```bash
.ctualizar.bat
```

Hace las tres cosas en orden (miniaturas → páginas → comprobación) y se para si algo
falla. Tarda menos de dos segundos. Si acaba diciendo `LISTO`, se puede publicar.

**No encadenes los comandos con `&&`**: PowerShell 5 de Windows no lo admite y da un
error de sintaxis. Por eso existe el `.bat`. Si aun así los quieres sueltos, van de
uno en uno:

```bash
python tools/generar_og.py
```
```bash
python tools/build_site.py
```
```bash
python tools/comprobar_sitio.py
```

## Los archivos

| Ruta | Qué es |
|---|---|
| `datos/libros.json` | **La fuente de la verdad.** Los libros con todos sus campos. |
| `datos/libros.schema.json` | El contrato: qué campo significa qué y cómo se calculan las notas. |
| `tools/build_site.py` | El generador. Lee el JSON y escribe todas las páginas + `lib/*.js`. |
| `tools/descargar_imagenes.py` | Baja las portadas de Amazon y las convierte a WebP. |
| `tools/empaquetar_preview.py` | Empaqueta el sitio en **un solo archivo** para enseñarlo con un enlace. |
| `tools/generar_madera.py` | Dibuja las dos texturas de madera de la estantería 3D. Solo hay que ejecutarlo si se quiere otra madera. |
| `tools/generar_og.py` | Dibuja los iconos y las miniaturas que se ven al compartir la web. **Ejecutar al añadir libros.** |
| `tools/comprobar_sitio.py` | Revisa el sitio ya generado: enlaces rotos, SEO, accesibilidad, peso de imágenes. |
| `tools/servidor.py` | Servidor de desarrollo: sirve, vigila los archivos, reconstruye y recarga el navegador. Sirve el 404 de verdad. |
| `GUIA.md` | Guía para tocar cosas a mano, sin tecnicismos. Inventario de qué hace cada archivo. |
| `404.html`, `robots.txt`, `sitemap.xml`, `site.webmanifest` | Generados. No editar a mano. |
| `styles.css` | Todo el diseño, en 11 secciones numeradas. |
| `main.js` | Solo enriquece: galería, comparador, filtros. El contenido ya está en el HTML. |
| `lib/db.js` | Generado. Lo lee el comparador. No editar a mano. |
| `lib/estanteria-db.js` | Generado. Los datos que necesita la estantería 3D. No editar a mano. |
| `lib/estanteria3d.js` | La estantería en 3D. Escrito a mano, **este sí se edita**. |
| `lib/three/` | Three.js r165 y sus 4 complementos, guardados aquí a propósito. |
| `_headers` | Cabeceras de caché y seguridad para Cloudflare Pages. **Debe subirse.** |
| `.gitignore` | Lo que no va a GitHub. |
| `tools/preparar_publicacion.py` | Deja en `publicar/` solo lo que debe ser público. |
| `scripts/` | Herramientas de la skill (extractor de Amazon, verificador). |
| `preview/` | Solo la vista previa de un archivo. **No hace falta subirla.** |
| `*.html`, `assets/`, `lib/` | Generados (salvo `estanteria3d.js`). Esto es lo que se publica. |

## La guía por la interfaz

La primera vez que alguien entra en la portada, el comparador o la estantería, le sale
una guía de tres o cuatro pasos que le señala lo importante. Se enseña **una sola vez
por página** (queda apuntado en su navegador) y se puede repetir desde el enlace
**«Ver la guía de la web»** del pie.

Se abre desde el **botón con la interrogación de la cabecera** (en móvil, desde el menú
desplegable), y también desde el enlace del pie. Ese botón solo sale en las páginas que
tienen guía, y solo si hay JavaScript.

Los textos viven en `GUIAS_INTERFAZ`, dentro de `tools/build_site.py`. Cada paso es
`(selector, título, texto)`. Si un selector no existe en la página, ese paso se salta
solo: la guía nunca se queda señalando al vacío.

## La estantería en 3D (`estanteria.html`)

Una balda con todos los libros: se giran con la rueda o las flechas, se abre uno y
**se puede hojear de verdad** — las páginas llevan la sinopsis, los pros, los contras
y la nota, sacados del mismo JSON. El panel lateral lleva el botón a Amazon con tu
enlace de afiliado y el enlace a la ficha completa.

Tres cosas que conviene no romper:

1. **Three.js está guardado en `lib/three/`, no viene de un CDN.** Si la web depende de
   un servidor ajeno, el día que ese servidor falle la estantería deja de existir.
2. **Sin JavaScript la página sigue siendo útil**: se ve la rejilla con los libros,
   sus fichas y sus enlaces. Eso es lo que lee Google.
3. **Las portadas son las de Amazon** (`assets/img/*.webp`). El lomo y las páginas de
   dentro se dibujan al vuelo con los datos del libro.
4. **La madera viene en archivo, no dibujada al vuelo.** Es lo primero que se ve y no
   puede salir distinta de lo aprobado, así que se genera con `tools/generar_madera.py`
   y se guarda en `assets/img/madera-*.webp`. Si esos archivos faltan, la estantería
   no se rompe: la madera vuelve a ser color liso.

**Es la única página del sitio con módulos ES**, y es a propósito: Three.js moderno solo
se publica en ese formato. `scripts/verify_project.py` lo marca como error porque la
regla general del sitio es `<script defer>` + IIFE — es una excepción consciente y
acotada a esta página. Los dos riesgos están cubiertos: la web se sirve por http (nunca
`file://`), y si el navegador es demasiado viejo para *import maps*, una red de
seguridad de 8 segundos retira la escena y deja la rejilla de libros funcionando.

## Publicar en Cloudflare Pages

El plan gratuito de Cloudflare Pages permite **uso comercial** y no limita el
tráfico, que es justo lo que necesita una web de afiliados.

**Desde GitHub, que es lo cómodo a la larga**

1. Sube el proyecto a un repositorio.
2. En Cloudflare: *Workers & Pages* → *Create* → *Pages* → *Connect to Git*.
3. Configura así:

   | Ajuste | Valor |
   |---|---|
   | Framework preset | None |
   | Build command | `python tools/preparar_publicacion.py` |
   | Build output directory | `publicar` |

Cada `git push` republica la web sola.

**O a mano, sin GitHub**

```bash
python tools/preparar_publicacion.py
npx wrangler pages deploy publicar --project-name=bookatme
```

#### Qué trae ya resuelto

Página de error 404 (con salidas útiles, no un callejón), `robots.txt`, `sitemap.xml`
con prioridades, URL canónica y miniatura de compartir propia en cada página, iconos,
HTTPS forzado con HSTS y cabeceras de seguridad en `_headers`, tipografías que no
bloquean el pintado, imágenes con medidas para que la página no dé saltos, y
accesibilidad revisada (contraste, foco, orden de encabezados, textos alternativos).

## Reglas que no se rompen

1. **El enlace de afiliado es sagrado.** Se guarda tal cual llega, con su etiqueta.
   `build_site.py` aborta si algún libro no la lleva.
2. **Los datos mandan.** Añadir un libro = añadir un registro. Nunca tocar un `.html`.
3. **Lo que no se sabe, no se inventa.** Si Amazon no publica un dato, va `null` y
   la ficha muestra “—”.
4. **Precio con fecha.** Los precios son una foto del día de la captura y así se
   etiquetan en todas las páginas.
5. **El aviso de afiliados va en todas las páginas.** Es obligación legal del programa.
