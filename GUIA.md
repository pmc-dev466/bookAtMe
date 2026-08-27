# Guía para tocar cosas a mano

Para Pedro. Sin tecnicismos. Si algo aquí no se entiende, es culpa de la guía.

---

## Lo primero: dos tipos de dato

Esta es la distinción que hay que tener clara, y todo lo demás sale de ella.

### Datos de Amazon — **no se tocan a mano**

Precio, valoración, número de opiniones, páginas, editorial, ISBN, dimensiones,
peso y puesto de ventas. Se **capturan** de la ficha del producto.

Si los escribes a mano pasan dos cosas malas: te lo estarías inventando (y la
web promete que no inventa nada), y además tu cambio se perdería en la
siguiente captura. Cuando quieras precios frescos, **pídemelo**: se recapturan
todos de una vez y se actualiza `precio_fecha` sola.

### Texto editorial — **es tuyo, edítalo cuando quieras**

Los pros, los contras, «es para ti si…», la descripción, el texto de «por qué
lo recomendamos» y las seis notas del gráfico. Eso es **opinión**, no dato. No
sale de Amazon: lo escribimos nosotros, y la web lo etiqueta como opinión.

Ahí puedes entrar y cambiar lo que quieras.

---

## La regla de oro

> **Los archivos `.html` de la carpeta principal no se tocan nunca.**

Se borran y se vuelven a escribir enteros en cada reconstrucción. Un cambio a
mano ahí se pierde.

| Quiero cambiar… | Se toca… |
|---|---|
| Pros, contras, descripción, notas de un libro | `datos/libros.json` |
| Colores, tamaños, márgenes | `styles.css` |
| Un texto que sale en todas las páginas | `tools/build_site.py` |
| Precio, valoración, páginas de un libro | **nada: se recaptura de Amazon** |

---

## Editar en caliente

Doble clic en **`desarrollo.bat`** y deja la ventana abierta. Mientras esté:

- la web se ve en `http://localhost:8777`
- al guardar cualquier archivo **se reconstruye sola**
- **el navegador se recarga solo**

Guardas, miras la pantalla, ya está. No hace falta ejecutar nada más.

`actualizar.bat` sigue existiendo para cuando solo quieras reconstruir y
comprobar de una pasada, sin dejar nada abierto.

> **Si ves la página de error fea de Python** («Error response / Error code:
> 404»), es que tienes abierto un servidor viejo de antes. Cierra todas las
> ventanas negras y vuelve a abrir `desarrollo.bat`.

---

## Cómo se fabrica la web

Como una combinación de correspondencia de Word: una lista de datos más una
plantilla producen muchas cartas. Tú editas la lista, nunca las cartas.

```
datos/libros.json  ──►  tools/build_site.py  ──►  41 archivos .html
   (los 24 libros)      (la máquina + plantilla)      (la web)
```

**Python no está en tu web.** Cloudflare no ejecuta Python. Python vive en tu
ordenador y sirve para *fabricar* los HTML. Lo que se publica es HTML, CSS,
JavaScript e imágenes, y nada más.

---

## Recetas

### Cambiar un pro o un contra

1. Abre `datos/libros.json` con el Bloc de notas.
2. Ctrl+F, escribe el título del libro.
3. Edita las listas `"pros"` o `"contras"`. Cada frase entre comillas, separadas
   por comas:

```json
"pros": ["Se lee en dos tardes", "El giro final sorprende de verdad"],
```

4. Guarda. Si tienes `desarrollo.bat` abierto, ya está.

### Cambiar las notas de los seis ejes

Mismo archivo, mismo libro. Son números del 0 al 10:

```json
"score_ritmo": 9,
"score_personajes": 7,
```

**Ojo con `score_calidad_precio`**: esa no se pone a mano, se calcula sola a
partir del precio por página y la valoración, y es relativa a todo el catálogo.
Si la tocas, se sobrescribe en la siguiente reconstrucción.

### Cambiar los colores de toda la web

En `styles.css`, arriba del todo:

```css
--ink:        #15181A;   /* el texto */
--accent:     #24503D;   /* el verde de los botones */
--brass:      #A87C2E;   /* el dorado de los detalles */
--paper:      #F5F4F0;   /* el fondo */
```

Cambia ahí y cambia la web entera. No busques colores sueltos por el archivo.

### Cambiar un texto que sale en todas las páginas

En `tools/build_site.py`, búscalos con Ctrl+F:

| Texto | Búscalo por |
|---|---|
| El nombre de la web | `SITIO =` |
| La frase del pie | `Comparativas de libros hechas con` |
| El aviso de afiliados de arriba | `def barra_afiliados` |
| Los textos de la guía de bienvenida | `GUIAS_INTERFAZ` |
| El menú de navegación | `def cabecera` |
| El identificador de la analítica | `ANALYTICS_TOKEN` |

### Cambiar el texto de la página de error (404)

`404.html` **es un archivo generado**: si lo editas, el cambio se pierde. Su texto
está en `tools/build_site.py`, en la función `pagina_404()` — búscala con Ctrl+F
por `def pagina_404`. Ahí puedes cambiar el título, la frase de debajo y los tres
botones de salida.

Lo mismo vale para cualquier otra página: si es un `.html` de la raíz, el texto está
en `tools/build_site.py`, no en el archivo.

> **Desde ahora, si editas un `.html` por error, no pierdes nada.** La siguiente
> reconstrucción lo detecta, guarda una copia en `copias-a-mano/` y te avisa con un
> aviso grande antes de sobrescribirlo. Además cada archivo generado lleva el aviso
> en su línea 2.

### Añadir un libro nuevo

No lo hagas a mano. Hay que capturar unos 35 datos de Amazon, bajar la portada,
escribir la ficha editorial y **recalcular las notas de calidad-precio de todos
los libros**. Pídemelo.

---

## Publicar en Cloudflare Pages

El plan gratuito de Cloudflare Pages permite uso comercial y no limita el tráfico,
que es justo lo que necesita una web de afiliados.

```
python tools/preparar_publicacion.py
npx wrangler pages deploy publicar --project-name=bookatme
```

El primero deja en `publicar/` **solo lo público**: sin `datos/`, sin `tools/`,
sin `preview/`. El segundo lo sube. Si prefieres conectarlo a GitHub, en
Cloudflare hay que poner *Build output directory* = `publicar`.

Cuando publiques:

1. Regenera con tu dirección real:
   `python tools/build_site.py --dominio https://bookatme.pages.dev`
2. Activa la analítica: panel de Cloudflare → *Web Analytics* → *Add a site*.
   Copia el identificador y pégalo en `ANALYTICS_TOKEN`, en
   `tools/build_site.py`. **No usa cookies, así que no necesitas banner.**
3. Da de alta `sitemap.xml` en Google Search Console.

---

## Inventario de archivos

### Se edita a mano

| Archivo | Qué es |
|---|---|
| `datos/libros.json` | **La fuente de la verdad.** Los 24 libros. Todo sale de aquí. |
| `datos/libros.schema.json` | El contrato: qué significa cada campo. Documentación, no se ejecuta. |
| `styles.css` | Todo el diseño, en 12 secciones numeradas. La 1 son los colores. |
| `main.js` | Galería, comparador, filtros y la guía de bienvenida. |
| `lib/estanteria3d.js` | La estantería en 3D. El único archivo de `lib/` hecho a mano. |
| `GUIA.md` | Esto. |

### La maquinaria · `tools/`

| Archivo | Qué hace |
|---|---|
| `build_site.py` | **El generador.** Lee el JSON y escribe las 41 páginas. Aquí viven los textos fijos. |
| `servidor.py` | El servidor de desarrollo: sirve, vigila, reconstruye y recarga. |
| `comprobar_sitio.py` | El revisor: enlaces rotos, SEO, accesibilidad, peso de imágenes. |
| `preparar_publicacion.py` | Deja en `publicar/` solo lo que debe ser público. |
| `generar_og.py` | Iconos y miniaturas de compartir en WhatsApp. |
| `descargar_imagenes.py` | Baja las portadas de Amazon y las convierte. |
| `generar_madera.py` | Las texturas de madera de la estantería 3D. |
| `empaquetar_preview.py` | La web entera en un solo archivo, para enseñarla. |

### Los dos botones

| Archivo | Para qué |
|---|---|
| `desarrollo.bat` | **El del día a día.** Editar en caliente. Deja la ventana abierta. |
| `actualizar.bat` | Reconstruir y comprobar de una pasada, sin dejar nada abierto. |

### Generado · no se toca

| Qué | Cuántos |
|---|---|
| `libro-*.html` | 24 |
| `categoria-*.html` | 7 |
| Portada y secciones | 7 |
| `guia-*.html` | 2 |
| `404.html` | 1 |
| `sitemap.xml`, `robots.txt`, `site.webmanifest` | 3 |
| `assets/img/` (portadas) | 44 |
| `assets/og/` (miniaturas) | 25 |
| `publicar/` | 127 archivos · 8,2 MB |

### Infraestructura

| Archivo | Para qué |
|---|---|
| `_headers` | Caché, HTTPS y seguridad **en Cloudflare**. Debe subirse. |
| `lib/three/` | La librería 3D, guardada aquí para no depender de nadie. |
| `preview/` | La web en un archivo. No se publica. |

---

## Si algo se rompe

1. Mira la ventana de `desarrollo.bat`: si algo falló al construir, lo dice ahí.
2. O ejecuta `actualizar.bat`. Si acaba en **LISTO**, la web está bien.
3. Si editaste el JSON y ahora falla, casi seguro es una **coma de más o de
   menos**. Cada dato lleva coma detrás, menos el último de cada bloque.
4. Si ves la página de error de Python: tienes un servidor viejo abierto.
   Cierra las ventanas negras y vuelve a abrir `desarrollo.bat`.

---

## Lo que nunca se hace

- **Quitar la etiqueta de afiliado de un enlace de Amazon.** Es de lo que cobras.
  El generador se niega a construir si falta.
- **Inventar un dato.** Si Amazon no lo publica, va `null` y la web muestra «—».
- **Escribir a mano un precio o una valoración.** Se capturan. Ver arriba.
- **Quitar el aviso de afiliados.** Es obligación legal del programa de Amazon.
