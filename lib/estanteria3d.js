/* =========================================================================
   BookAtMe! · La estantería en 3D
   -------------------------------------------------------------------------
   Lee los libros de window.__ESTANTERIA__ (generado por tools/build_site.py)
   y monta una estantería navegable: se elige un libro, se abre, se hojea,
   y desde el panel se va a Amazon con el enlace de afiliado o a la ficha.

   NO se escribe ningún libro aquí. Añadir un libro = añadirlo al JSON.
   ========================================================================= */
import * as THREE from "three";
import { OrbitControls } from "three/addons/OrbitControls.js";
import { RoomEnvironment } from "three/addons/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/RoundedBoxGeometry.js";
import { RectAreaLightUniformsLib } from "three/addons/RectAreaLightUniformsLib.js";

const DATOS = Array.isArray(window.__ESTANTERIA__) ? window.__ESTANTERIA__ : [];

/* --- paleta por género -------------------------------------------------
   Cada categoría tiene su tela y su dorado. Es lo que da variedad al
   estante sin inventarnos nada del libro. */
const PALETAS = {
  amor:      { tela: "#8C2F39", foil: "#E8C07A", luz: "#FFD9C4", relleno: "#E0BFB4", pared: "#F3E6E2", suelo: "#DFCAC4" },
  suspense:  { tela: "#1F2A33", foil: "#C6CBD1", luz: "#DCE6EF", relleno: "#9FB3C9", pared: "#E4E7EB", suelo: "#CDD2D8" },
  drama:     { tela: "#3C3A4B", foil: "#D8CBB0", luz: "#EFE6DA", relleno: "#B9B3C4", pared: "#EAE7E4", suelo: "#D3CFCB" },
  comedia:   { tela: "#C2661C", foil: "#FFE1A8", luz: "#FFE3BC", relleno: "#EBC79A", pared: "#F6EBDD", suelo: "#E3CDB2" },
  filosofia: { tela: "#24503D", foil: "#C9A227", luz: "#EDE7CE", relleno: "#A9BFAF", pared: "#E9EDE7", suelo: "#CFD8CE" },
  fantasia:  { tela: "#3B2E63", foil: "#D9BBEB", luz: "#E6DCF5", relleno: "#B6A8D4", pared: "#EBE7F2", suelo: "#D2CBDF" },
  /* pasatiempos: rojo de novela de detectives, que es de lo que van */
  pasatiempos: { tela: "#7A1F1F", foil: "#E8D9A8", luz: "#FFE8D2", relleno: "#D8B9A8", pared: "#F2E8E0", suelo: "#DCC4B0" }
};
const PALETA_POR_DEFECTO = PALETAS.filosofia;

const paletaDe = (cat) => PALETAS[cat] || PALETA_POR_DEFECTO;

/* --- utilidades --------------------------------------------------------- */
const clamp = THREE.MathUtils.clamp;
const damp = THREE.MathUtils.damp;
const lerp = THREE.MathUtils.lerp;
const suave = (v) => v * v * (3 - 2 * v);
const masSuave = (v) => v * v * v * (v * (v * 6 - 15) + 10);
const mod = (v, n) => ((v % n) + n) % n;
const pad = (v) => String(v).padStart(2, "0");
const romano = (n) => ["I","II","III","IV","V","VI","VII","VIII","IX","X",
  "XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX"][n - 1] || String(n);

function semilla(txt) {
  let h = 2166136261;
  for (let i = 0; i < txt.length; i += 1) {
    h ^= txt.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
function azar(s) {
  let v = s >>> 0;
  return () => {
    v += 0x6d2b79f5;
    let r = v;
    r = Math.imul(r ^ (r >>> 15), r | 1);
    r ^= r + Math.imul(r ^ (r >>> 7), r | 61);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
function eur(n) {
  if (n === null || n === undefined) return null;
  return n.toFixed(2).replace(".", ",") + " €";
}

/* --- referencias del DOM ------------------------------------------------ */
const escena3d = document.querySelector("#estanteria");
const lienzo = document.querySelector("#estanteria-canvas");
const cargando = document.querySelector("#estanteria-cargando");
const respaldo = document.querySelector("#estanteria-respaldo");
const barraUi = document.querySelector("#estanteria-ui");
const panel = document.querySelector("#estanteria-panel");
const tituloSel = document.querySelector("#sel-titulo");
const notaSel = document.querySelector("#sel-nota");
const contador = document.querySelector("#sel-contador");
const marcadores = document.querySelector("#sel-marcadores");
const btnAnterior = document.querySelector("#btn-anterior");
const btnSiguiente = document.querySelector("#btn-siguiente");
const btnAbrir = document.querySelector("#btn-abrir");
const btnCerrarPanel = document.querySelector("#btn-cerrar-panel");
const btnResetVista = document.querySelector("#btn-reset-vista");
const btnHojear = document.querySelector("#btn-hojear");
const btnPagAnterior = document.querySelector("#btn-pag-anterior");
const btnPagSiguiente = document.querySelector("#btn-pag-siguiente");
const etiquetaPag = document.querySelector("#pag-etiqueta");
const contadorPag = document.querySelector("#pag-contador");
const pistaPanel = document.querySelector("#panel-pista");
const pGenero = document.querySelector("#p-genero");
const pTitulo = document.querySelector("#p-titulo");
const pAutor = document.querySelector("#p-autor");
const pSinopsis = document.querySelector("#p-sinopsis");
const pDatos = document.querySelector("#p-datos");
const pPros = document.querySelector("#p-pros");
const pComprar = document.querySelector("#p-comprar");
const pFicha = document.querySelector("#p-ficha");
const pPrecio = document.querySelector("#p-precio");
const avisos = document.querySelector("#estanteria-avisos");
const etiquetaRaton = document.querySelector("#etiqueta-raton");
const etiquetaRatonNum = document.querySelector("#etiqueta-raton-num");
const etiquetaRatonTit = document.querySelector("#etiqueta-raton-tit");
const consultaMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");

/* --- estado ------------------------------------------------------------- */
let movimientoReducido = consultaMovimiento.matches;
let renderer, escena, camara, controles, entorno, tarima;
let libros = [];
let dianas = [];
let raf = 0;
let tUltimo = performance.now();
let modo = "estante";        // estante | abriendo | detalle | cerrando
let tTransicion = 0;
let posicion = 0;
let posicionDestino = 0;
let seleccion = 0;
let sobrevolado = -1;
let ruedaQuieta = 0;
let focoDeVuelta = btnAbrir;
let libroActivo = null;
let hojeando = false;
let libroSobrevolado = false;
let pliegoActual = 0;
let ratonSucio = false;
let suspendido = false;
let anchoVista = window.innerWidth;
let altoVista = window.innerHeight;
let desplazeDetalleX = 0;
let desplazeActualX = 0;
let anchoSeguro = anchoVista * 0.6;
let temaIniciado = false;
let temaEnMovimiento = false;
let cargador = null;

const materialesSala = { suelo: null, pared: null, madera: null, maderaOscura: null, sombra: null };
/* hacia donde se tira la niebla ahora que el fondo es madera, no pared clara */
const NIEBLA_MADERA = new THREE.Color(0x3a2418);
const lucesSala = { hemi: null, clave: null, claveSuave: null, relleno: null, borde: null, trasera: null, lomo: null, canto: null };
const destinoTema = {
  suelo: new THREE.Color(0xd8c8aa), pared: new THREE.Color(0xe9dfcb),
  madera: new THREE.Color(0x4a2b1d), maderaOscura: new THREE.Color(0x2a170f),
  sombra: new THREE.Color(0x2f1d13), niebla: new THREE.Color(0xe9dfcb),
  hemi: new THREE.Color(0xfff8e8), hemiSuelo: new THREE.Color(0x5b4030),
  clave: new THREE.Color(0xffe8c2), relleno: new THREE.Color(0xd8e3e7), borde: new THREE.Color(0xd5a45e)
};

const raton = { ndc: new THREE.Vector2(3, 3), x: 0, y: 0 };
const arrastre = { activo: false, id: null, x0: 0, y0: 0, avance: 0, pico: 0,
  confirmado: false, velocidad: 0, sesgoY: 0, avancePrevio: 0, tPrevio: 0, sentido: 0, tipo: null };
const pulsacion = { activa: false, id: null, x0: 0, y0: 0, movida: false, permiteClic: false };

const lanzador = new THREE.Raycaster();
const camEstante = new THREE.Vector3();
const objEstante = new THREE.Vector3();
const posDetalle = new THREE.Vector3();
const camDetalle = new THREE.Vector3();
const objDetalle = new THREE.Vector3();
const objTransicion = new THREE.Vector3();
const tarimaReposo = new THREE.Vector3();
const tarimaDetalle = new THREE.Vector3(0, -4.2, -3);
const giroDetalle = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.055, -0.14, 0));
const escalaDetalle = new THREE.Vector3();
const movReposoPos = new THREE.Vector3();
const movReposoGiro = new THREE.Quaternion();

/* posiciones congeladas al empezar cada transición */
const aP0 = new THREE.Vector3(), aQ0 = new THREE.Quaternion(), aE0 = new THREE.Vector3();
const aMovP0 = new THREE.Vector3(), aMovQ0 = new THREE.Quaternion();
const aCamP0 = new THREE.Vector3(), aCamO0 = new THREE.Vector3(), aTarima0 = new THREE.Vector3();
const cP1 = new THREE.Vector3(), cQ1 = new THREE.Quaternion(), cE1 = new THREE.Vector3(1.09, 1.09, 1.09);
const cP0 = new THREE.Vector3(), cQ0 = new THREE.Quaternion(), cE0 = new THREE.Vector3();
const cMovP0 = new THREE.Vector3(), cMovQ0 = new THREE.Quaternion();
const cCamP0 = new THREE.Vector3(), cCamO0 = new THREE.Vector3(), cTarima0 = new THREE.Vector3();
let aDesplX0 = 0, cDesplX0 = 0;

const TAPA_ARRIBA = 0.47;
const SEPARACION = 1.5;
const HOJAS = 4;                 // hojas que se pasan → 5 pliegos
const PLIEGOS = HOJAS + 1;
const SEG_H = 18, SEG_V = 8;     // malla de la página flexible
const CONFIRMA_PAGINA = 0.18;
const CONFIRMA_ABRIR = 0.16;
const CONFIRMA_CERRAR = 0.2;
const DUR_DETALLE = 0.92;
const DUR_ESTANTE = 0.92;

/* --- geometrías y materiales compartidos -------------------------------- */
const comun = {
  caja: new THREE.BoxGeometry(1, 1, 1),
  plano: new THREE.PlaneGeometry(1, 1),
  papel: new THREE.MeshPhysicalMaterial({ color: 0xe7dfcf, roughness: 0.95, metalness: 0, sheen: 0.025, sheenRoughness: 1 }),
  hoja: new THREE.MeshPhysicalMaterial({ color: 0xfdfcfa, roughness: 0.955, metalness: 0, sheen: 0.02, sheenRoughness: 1, side: THREE.DoubleSide }),
  cabezada: new THREE.MeshPhysicalMaterial({ color: 0xc6a66d, roughness: 0.58, metalness: 0.16, sheen: 0.14, sheenRoughness: 0.76 }),
  /* el `map` se les enchufa en montarSala(), cuando ya existe el renderer */
  nogal: new THREE.MeshStandardMaterial({ color: 0x4a2b1d, roughness: 0.58, metalness: 0 }),
  nogalOscuro: new THREE.MeshStandardMaterial({ color: 0x2a170f, roughness: 0.7, metalness: 0 })
};

function conFundido(base) {
  const m = base.clone();
  m.transparent = true;
  m.opacity = 1;
  return m;
}

/* --- la madera de la sala ------------------------------------------------
   Estas dos son las unicas texturas que vienen en archivo y no dibujadas al
   vuelo: son lo primero que se ve y no pueden salir distintas de lo aprobado.
   Se generan con `python tools/generar_madera.py`.
   Mientras no cargan -o si fallan- los materiales conservan su color liso de
   nogal: nunca un estante blanco. */
let maderaLista = false;
let ultimoLibroTema = null;
const cargadorTex = new THREE.TextureLoader();
const maderaPendiente = { total: 0, hechas: 0 };

function cargarMadera(archivo, repX, repY) {
  maderaPendiente.total += 1;
  const tex = cargadorTex.load(archivo, () => {
    maderaPendiente.hechas += 1;
    if (maderaPendiente.hechas === maderaPendiente.total) {
      maderaLista = true;
      /* el color de la madera pasa a ser un simple tinte sobre la foto */
      if (ultimoLibroTema) aplicarTema(ultimoLibroTema);
    }
    pedirCuadro();
  }, undefined, () => { /* sin madera: se queda el color liso */ });
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(repX, repY);
  tex.anisotropy = Math.min(16, renderer.capabilities.getMaxAnisotropy());
  return tex;
}

function ajustarTextura(t, { color = true, aniso = 16 } = {}) {
  if (color) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = Math.min(aniso, renderer.capabilities.getMaxAnisotropy());
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}

/* --- texto en canvas ---------------------------------------------------- */
function partirTexto(ctx, txt, ancho) {
  const palabras = String(txt || "").split(/\s+/).filter(Boolean);
  const lineas = [];
  let linea = "";
  palabras.forEach((p) => {
    const prueba = linea ? linea + " " + p : p;
    if (ctx.measureText(prueba).width > ancho && linea) {
      lineas.push(linea);
      linea = p;
    } else linea = prueba;
  });
  if (linea) lineas.push(linea);
  return lineas;
}

function escribirBloque(ctx, txt, x, y, ancho, alto, maxLineas) {
  const lineas = partirTexto(ctx, txt, ancho);
  const n = Math.min(lineas.length, maxLineas);
  for (let i = 0; i < n; i += 1) {
    let l = lineas[i];
    if (i === maxLineas - 1 && lineas.length > maxLineas) l = l.replace(/[.,;:]?$/, "…");
    ctx.fillText(l, x, y + i * alto);
  }
  return y + n * alto;
}

/* --- papel -------------------------------------------------------------- */
function superficiePapel(ctx, w, h, rnd) {
  /* Papel casi blanco. El crema de antes (#e8e1d3) quedaba bonito en foto pero,
     con la luz calida de la escena encima, dejaba el texto en gris sobre beige
     y no se leia. Un libro esta para leerlo. */
  ctx.fillStyle = "#f7f4ed";
  ctx.fillRect(0, 0, w, h);
  /* El bano marron del final ensuciaba la esquina de abajo y le quitaba
     contraste al texto justo donde acaba el parrafo. Se queda en un tercio. */
  const bano = ctx.createLinearGradient(0, 0, w, h);
  bano.addColorStop(0, "rgba(255,255,255,0.26)");
  bano.addColorStop(0.42, "rgba(255,255,255,0.05)");
  bano.addColorStop(1, "rgba(103,87,64,0.028)");
  ctx.fillStyle = bano;
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 1800; i += 1) {
    const x = rnd() * w, y = rnd() * h, l = 5 + rnd() * 30;
    ctx.strokeStyle = rnd() > 0.44
      ? "rgba(255,255,255," + (0.025 + rnd() * 0.045) + ")"
      : "rgba(92,76,55," + (0.018 + rnd() * 0.035) + ")";
    ctx.lineWidth = 0.45 + rnd() * 0.65;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(Math.min(w, x + l), y + (rnd() - 0.5) * 2.2);
    ctx.stroke();
  }
}

let texturaPapelCache = null;
function texturaPapel() {
  if (texturaPapelCache) return texturaPapelCache;
  const c = document.createElement("canvas");
  c.width = 512; c.height = 768;
  superficiePapel(c.getContext("2d"), 512, 768, azar(semilla("papel-leido")));
  texturaPapelCache = ajustarTextura(new THREE.CanvasTexture(c));
  return texturaPapelCache;
}

/* --- tela del encuadernado ---------------------------------------------- */
function mapasTela(libro) {
  const n = 256;
  const alturas = new Float32Array(n * n);
  const cN = document.createElement("canvas"), cR = document.createElement("canvas");
  cN.width = cN.height = cR.width = cR.height = n;
  const gN = cN.getContext("2d"), gR = cR.getContext("2d");
  const iN = gN.createImageData(n, n), iR = gR.createImageData(n, n);
  const fase = (semilla(libro.id) % 19) * 0.23;
  for (let y = 0; y < n; y += 1) {
    for (let x = 0; x < n; x += 1) {
      alturas[y * n + x] = 0.5
        + Math.sin((x + fase) * Math.PI * 0.52) * 0.18
        + Math.sin((y - fase) * Math.PI * 0.41) * 0.15
        + Math.sin((x + y + fase) * Math.PI * 0.19) * 0.045;
    }
  }
  const h = (x, y) => alturas[(((y % n) + n) % n) * n + (((x % n) + n) % n)];
  for (let y = 0; y < n; y += 1) {
    for (let x = 0; x < n; x += 1) {
      const i = y * n + x, p = i * 4;
      const dx = (h(x + 1, y) - h(x - 1, y)) * 1.5;
      const dy = (h(x, y + 1) - h(x, y - 1)) * 1.5;
      const len = Math.hypot(dx, dy, 1);
      iN.data[p] = Math.round(((-dx / len) * 0.5 + 0.5) * 255);
      iN.data[p + 1] = Math.round(((-dy / len) * 0.5 + 0.5) * 255);
      iN.data[p + 2] = Math.round(((1 / len) * 0.5 + 0.5) * 255);
      iN.data[p + 3] = 255;
      const r = Math.round(188 + alturas[i] * 56);
      iR.data[p] = iR.data[p + 1] = iR.data[p + 2] = r;
      iR.data[p + 3] = 255;
    }
  }
  gN.putImageData(iN, 0, 0);
  gR.putImageData(iR, 0, 0);
  const prep = (cv) => {
    const t = new THREE.CanvasTexture(cv);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(5, 8);
    return ajustarTextura(t, { color: false, aniso: 12 });
  };
  return { normal: prep(cN), rugosidad: prep(cR) };
}

/* --- PORTADA: la foto real de Amazon ------------------------------------ */
function texturaPortada(libro, aspecto) {
  const pal = paletaDe(libro.categoria);
  const c = document.createElement("canvas");
  /* El lienzo lleva la proporcion REAL de este libro. Con una medida fija, la
     portada se estiraba hasta un 9% al mapearla sobre libros mas o menos
     gordos, y en la tipografia de una cubierta eso canta enseguida. */
  c.width = 768; c.height = Math.round(768 * (aspecto || 1.5));
  const ctx = c.getContext("2d");

  /* provisional: tela + título, para que nunca haya un libro en blanco */
  ctx.fillStyle = pal.tela;
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.fillStyle = pal.foil;
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.font = '400 62px "Fraunces", Georgia, serif';
  partirTexto(ctx, libro.titulo, c.width - 150).slice(0, 4)
    .forEach((l, i) => ctx.fillText(l, c.width / 2, c.height * 0.373 + i * 74));
  ctx.font = '500 30px "Inter", Arial, sans-serif';
  ctx.fillText(libro.autor || "", c.width / 2, c.height * 0.764);

  const tex = ajustarTextura(new THREE.CanvasTexture(c));

  const src = (libro.imagenes && libro.imagenes[0]) || null;
  if (src) {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      /* encajar la foto llenando la tapa, recortando lo que sobre */
      const escala = Math.max(c.width / img.width, c.height / img.height);
      const w = img.width * escala, h = img.height * escala;
      ctx.fillStyle = pal.tela;
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.drawImage(img, (c.width - w) / 2, (c.height - h) / 2, w, h);
      /* sombreado de canto: da volumen a la tapa */
      const canto = ctx.createLinearGradient(0, 0, c.width, 0);
      /* muy suave a proposito: es volumen, no un filtro sobre la portada */
      canto.addColorStop(0, "rgba(0,0,0,0.06)");
      canto.addColorStop(0.045, "rgba(255,255,255,0.015)");
      canto.addColorStop(0.95, "rgba(255,255,255,0)");
      canto.addColorStop(1, "rgba(0,0,0,0.03)");
      ctx.fillStyle = canto;
      ctx.fillRect(0, 0, c.width, c.height);
      tex.needsUpdate = true;
      pedirCuadro();
    };
    img.onerror = () => { /* se queda la tela con el título: es suficiente */ };
    img.src = src;
  }
  return tex;
}

/* --- LOMO: título y autor de verdad ------------------------------------- */
function texturaLomo(libro) {
  const pal = paletaDe(libro.categoria);
  const c = document.createElement("canvas");
  c.width = 384; c.height = 1536;
  const ctx = c.getContext("2d");
  const rnd = azar(semilla(libro.id + "-lomo"));

  ctx.fillStyle = pal.tela;
  ctx.fillRect(0, 0, c.width, c.height);
  const sombra = ctx.createLinearGradient(0, 0, c.width, 0);
  sombra.addColorStop(0, "rgba(0,0,0,0.2)");
  sombra.addColorStop(0.14, "rgba(255,255,255,0.055)");
  sombra.addColorStop(0.62, "rgba(255,255,255,0.012)");
  sombra.addColorStop(1, "rgba(0,0,0,0.16)");
  ctx.fillStyle = sombra;
  ctx.fillRect(0, 0, c.width, c.height);
  for (let i = 0; i < 1400; i += 1) {
    const x = rnd() * c.width, y = rnd() * c.height, vert = rnd() > 0.42;
    ctx.strokeStyle = rnd() > 0.5
      ? "rgba(255,255,255," + (0.018 + rnd() * 0.038) + ")"
      : "rgba(0,0,0," + (0.018 + rnd() * 0.032) + ")";
    ctx.lineWidth = 0.45 + rnd() * 0.7;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(vert ? x + (rnd() - 0.5) * 1.2 : x + 8 + rnd() * 28,
               vert ? y + 8 + rnd() * 34 : y + (rnd() - 0.5) * 1.2);
    ctx.stroke();
  }

  ctx.fillStyle = pal.foil;
  ctx.strokeStyle = pal.foil;
  ctx.lineWidth = 2.4;
  ctx.strokeRect(34, 38, c.width - 68, c.height - 76);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  ctx.save();
  ctx.translate(c.width * 0.5, c.height * 0.46);
  ctx.rotate(Math.PI / 2);
  const t = libro.titulo || "";
  const cuerpo = t.length > 34 ? 40 : t.length > 22 ? 50 : 62;
  ctx.font = "400 " + cuerpo + 'px "Fraunces", Georgia, serif';
  const lineas = partirTexto(ctx, t, c.height - 320).slice(0, 2);
  lineas.forEach((l, i) => ctx.fillText(l, 0, (i - (lineas.length - 1) / 2) * (cuerpo + 8)));
  ctx.restore();

  ctx.save();
  ctx.translate(c.width * 0.5, c.height - 250);
  ctx.rotate(Math.PI / 2);
  ctx.font = '500 26px "Inter", Arial, sans-serif';
  ctx.fillText((libro.autor || "").split(",")[0], 0, 0);
  ctx.restore();

  ctx.beginPath();
  ctx.arc(c.width * 0.5, 132, 22, 0, Math.PI * 2);
  ctx.stroke();
  ctx.font = '500 22px "Inter", Arial, sans-serif';
  ctx.fillText(romano(libro.indice + 1), c.width * 0.5, 133);
  return ajustarTextura(new THREE.CanvasTexture(c), { aniso: 16 });
}

/* --- CONTRAPORTADA ------------------------------------------------------ */
function texturaContra(libro, aspecto) {
  const pal = paletaDe(libro.categoria);
  const c = document.createElement("canvas");
  c.width = 768; c.height = Math.round(768 * (aspecto || 1.5));
  const ctx = c.getContext("2d");
  const rnd = azar(semilla(libro.id + "-contra"));

  ctx.fillStyle = pal.tela;
  ctx.fillRect(0, 0, c.width, c.height);
  for (let i = 0; i < 2000; i += 1) {
    const x = rnd() * c.width, y = rnd() * c.height, l = 5 + rnd() * 30;
    ctx.strokeStyle = rnd() > 0.5
      ? "rgba(255,255,255," + (0.018 + rnd() * 0.03) + ")"
      : "rgba(0,0,0," + (0.016 + rnd() * 0.028) + ")";
    ctx.lineWidth = 0.45 + rnd() * 0.65;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + l, y + (rnd() - 0.5) * 1.5);
    ctx.stroke();
  }
  const vineta = ctx.createRadialGradient(c.width * 0.62, c.height * 0.38, 20,
                                          c.width * 0.62, c.height * 0.38, c.width * 0.75);
  vineta.addColorStop(0, "rgba(255,255,255,0.03)");
  vineta.addColorStop(1, "rgba(0,0,0,0.09)");
  ctx.fillStyle = vineta;
  ctx.fillRect(0, 0, c.width, c.height);

  ctx.fillStyle = pal.foil;
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.font = '500 16px "Inter", Arial, sans-serif';
  ctx.fillText("BOOKATME · " + (libro.generoNombre || "").toUpperCase(), 68, 88);
  ctx.globalAlpha = 0.7;
  ctx.fillRect(68, 110, 176, 2);
  ctx.globalAlpha = 0.62;
  ctx.font = '300 25px "Newsreader", Georgia, serif';
  escribirBloque(ctx, libro.descripcion, 68, 210, c.width - 140, 40, 12);
  ctx.globalAlpha = 1;

  ctx.font = '400 46px "Fraunces", Georgia, serif';
  /* anclado abajo, no a un 1152 fijo: el alto del lienzo cambia con el libro */
  partirTexto(ctx, libro.titulo, c.width - 140).slice(0, 2)
    .forEach((l, i) => ctx.fillText(l, 68, c.height - 222 + i * 54));
  ctx.font = '500 17px "Inter", Arial, sans-serif';
  ctx.globalAlpha = 0.8;
  ctx.fillText((libro.autor || "").toUpperCase(), 70, c.height - 128);
  ctx.globalAlpha = 0.62;
  ctx.fillRect(68, c.height - 94, c.width - 136, 1.5);
  ctx.font = '500 14px "Inter", Arial, sans-serif';
  ctx.fillText("COMPARATIVAS DE LIBROS", 68, c.height - 56);

  const tex = ajustarTextura(new THREE.CanvasTexture(c));

  /* Si Amazon publica la contraportada de verdad, esa manda; lo de arriba se
     queda de respaldo para los libros que solo tienen portada. */
  if (libro.contraportada) {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      const escala = Math.max(c.width / img.width, c.height / img.height);
      const w = img.width * escala, h = img.height * escala;
      ctx.globalAlpha = 1;
      ctx.fillStyle = pal.tela;
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.drawImage(img, (c.width - w) / 2, (c.height - h) / 2, w, h);
      const canto = ctx.createLinearGradient(0, 0, c.width, 0);
      canto.addColorStop(0, "rgba(0,0,0,0.07)");
      canto.addColorStop(0.07, "rgba(255,255,255,0)");
      canto.addColorStop(0.945, "rgba(255,255,255,0.02)");
      canto.addColorStop(1, "rgba(0,0,0,0.13)");
      ctx.fillStyle = canto;
      ctx.fillRect(0, 0, c.width, c.height);
      tex.needsUpdate = true;
      pedirCuadro();
    };
    img.onerror = () => { /* se queda la contraportada dibujada */ };
    img.src = libro.contraportada;
  }
  return tex;
}

/* --- GUARDAS ------------------------------------------------------------ */
function texturaGuardas(libro) {
  const pal = paletaDe(libro.categoria);
  const c = document.createElement("canvas");
  c.width = 512; c.height = 768;
  const ctx = c.getContext("2d");
  superficiePapel(ctx, c.width, c.height, azar(semilla(libro.id + "-guardas")));
  ctx.save();
  ctx.fillStyle = pal.tela;
  ctx.globalAlpha = 0.13;
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.globalAlpha = 0.16;
  ctx.strokeStyle = pal.foil;
  ctx.lineWidth = 1;
  for (let x = 28; x < c.width; x += 48) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, c.height); ctx.stroke();
  }
  for (let y = 24; y < c.height; y += 48) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(c.width, y); ctx.stroke();
  }
  ctx.restore();
  return ajustarTextura(new THREE.CanvasTexture(c));
}

/* --- CANTOS del bloque de páginas --------------------------------------- */
let cantosCache = null;
function texturasCanto() {
  if (cantosCache) return cantosCache;
  const hacer = (w, h, clave) => {
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d");
    const rnd = azar(semilla(clave));
    ctx.fillStyle = "#dcd5c7";
    ctx.fillRect(0, 0, w, h);
    const paso = clave === "canto-largo" ? 2 : 1.35;
    for (let y = 0; y < h; y += paso) {
      const tono = Math.round(106 + rnd() * 74);
      const cuadernillo = rnd() > 0.965;
      ctx.strokeStyle = "rgba(" + tono + "," + (tono - 3) + "," + (tono - 9) + ","
        + (cuadernillo ? 0.34 : 0.13 + rnd() * 0.13) + ")";
      ctx.lineWidth = cuadernillo ? 1.05 : 0.42 + rnd() * 0.42;
      ctx.beginPath();
      ctx.moveTo(0, y + (rnd() - 0.5) * 0.5);
      ctx.bezierCurveTo(w * 0.3, y + (rnd() - 0.5) * 0.9,
                        w * 0.72, y + (rnd() - 0.5) * 0.9,
                        w, y + (rnd() - 0.5) * 0.5);
      ctx.stroke();
    }
    const sombra = ctx.createLinearGradient(0, 0, w, 0);
    sombra.addColorStop(0, "rgba(58,48,35,0.18)");
    sombra.addColorStop(0.035, "rgba(255,255,255,0.04)");
    sombra.addColorStop(0.86, "rgba(255,255,255,0)");
    sombra.addColorStop(1, "rgba(58,48,35,0.12)");
    ctx.fillStyle = sombra;
    ctx.fillRect(0, 0, w, h);
    return ajustarTextura(new THREE.CanvasTexture(c));
  };
  cantosCache = { largo: hacer(512, 2048, "canto-largo"), corto: hacer(2048, 384, "canto-corto") };
  return cantosCache;
}

/* --- sombra de contacto ------------------------------------------------- */
let sombraCache = null;
function texturaSombra() {
  if (sombraCache) return sombraCache;
  const c = document.createElement("canvas");
  c.width = 512; c.height = 128;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(256, 64, 10, 256, 64, 254);
  g.addColorStop(0, "rgba(255,255,255,0.95)");
  g.addColorStop(0.38, "rgba(255,255,255,0.62)");
  g.addColorStop(0.72, "rgba(255,255,255,0.18)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, c.width, c.height);
  sombraCache = ajustarTextura(new THREE.CanvasTexture(c), { color: false, aniso: 8 });
  return sombraCache;
}

/* =========================================================================
   LAS PÁGINAS DE DENTRO — aquí va el contenido real de la ficha
   ========================================================================= */
const TITULOS_PLIEGO = ["Portadilla", "De qué va", "Lo que nos gusta",
                        "Lo que no tanto", "Ficha y nota"];

function texturasInteriores(libro) {
  const pal = paletaDe(libro.categoria);
  /* La tinta tira mucho mas hacia el negro que antes (0.62). Con el tono del
     genero tan presente, sobre papel crema y con la luz calida de la escena,
     el texto salia lavado y no habia quien lo leyera. Sigue teniendo el matiz
     del genero, pero ya es tinta. */
  /* Tinta practicamente negra: solo se deja un 6% del color del genero, lo justo
     para que un libro de amor no tenga la misma tinta que uno de suspense. Antes
     pesaba mucho mas el tono del genero y el texto salia gris. */
  const tintaColor = new THREE.Color(pal.tela).lerp(new THREE.Color(0x100c09), 0.94);
  const tinta = "#" + tintaColor.getHexString();

  /* 8 caras = 4 hojas. Cada una recibe su pintor. */
  const pintores = [
    /* 0 · portadilla */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText((libro.generoNombre || "").toUpperCase(), 54, 178);
      ctx.font = '400 ' + (libro.titulo.length > 26 ? 56 : 72) + 'px "Fraunces", Georgia, serif';
      const fin = escribirBloque(ctx, libro.titulo, 52, 272, w - 104, 78, 3);
      ctx.globalAlpha = 0.78;
      ctx.font = '500 28px "Inter", Arial, sans-serif';
      ctx.fillText(libro.autor || "", 54, fin + 40);
      if (libro.traductor) {
        ctx.globalAlpha = 0.6;
        ctx.font = '400 20px "Inter", Arial, sans-serif';
        ctx.fillText("Traducción de " + libro.traductor, 54, fin + 76);
      }
      ctx.globalAlpha = 0.72;
      ctx.font = '400 28px "Newsreader", Georgia, serif';
      escribirBloque(ctx, libro.destacado_editorial || "", 54, 570, w - 108, 38, 4);
      ctx.globalAlpha = 1;
    },
    /* 1 · de qué va (primera mitad) */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText("DE QUÉ VA", 54, 152);
      ctx.globalAlpha = 1;
      ctx.font = '500 36px "Newsreader", Georgia, serif';
      escribirBloque(ctx, libro.descripcion, 54, 220, w - 108, 48, 10);
      ctx.globalAlpha = 1;
    },
    /* 2 · por qué lo recomendamos */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText("POR QUÉ LO RECOMENDAMOS", 54, 152);
      ctx.globalAlpha = 1;
      ctx.font = '500 36px "Newsreader", Georgia, serif';
      escribirBloque(ctx, libro.editorialTexto || libro.destacado_editorial || libro.descripcion,
                     54, 220, w - 108, 48, 10);
      ctx.globalAlpha = 1;
    },
    /* 3 · lo que nos gusta */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText("LO QUE NOS GUSTA", 54, 152);
      /* 4 en vez de 5: con la letra ya legible no caben mas de cuatro */
      let y = 228;
      (libro.pros || []).slice(0, 4).forEach((p) => {
        ctx.globalAlpha = 0.85;
        ctx.font = '600 34px "Inter", Arial, sans-serif';
        ctx.fillText("+", 54, y);
        ctx.globalAlpha = 1;
        ctx.font = '500 32px "Newsreader", Georgia, serif';
        y = escribirBloque(ctx, p, 94, y, w - 150, 42, 2) + 36;
      });
      ctx.globalAlpha = 1;
    },
    /* 4 · lo que no tanto */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText("LO QUE NO TANTO", 54, 152);
      /* 4 en vez de 5: con la letra ya legible no caben mas de cuatro */
      let y = 228;
      (libro.contras || []).slice(0, 4).forEach((p) => {
        ctx.globalAlpha = 0.85;
        ctx.font = '600 34px "Inter", Arial, sans-serif';
        ctx.fillText("−", 54, y);
        ctx.globalAlpha = 1;
        ctx.font = '500 32px "Newsreader", Georgia, serif';
        y = escribirBloque(ctx, p, 94, y, w - 150, 42, 2) + 36;
      });
      ctx.globalAlpha = 1;
    },
    /* 5 · es para ti si */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText("ES PARA TI SI…", 54, 152);
      ctx.globalAlpha = 1;
      ctx.font = '500 36px "Newsreader", Georgia, serif';
      escribirBloque(ctx, libro.ideal_para, 54, 228, w - 108, 48, 9);
      ctx.globalAlpha = 1;
    },
    /* 6 · la ficha */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText("LA FICHA", 54, 152);
      const filas = [
        ["Editorial", libro.editorial],
        ["Formato", libro.formato],
        ["Páginas", libro.num_paginas ? libro.num_paginas + " págs." : null],
        ["Publicado", libro.anio],
        ["Se lee en", libro.horas_lectura ? "~" + libro.horas_lectura + " h" : null],
        ["Kindle", libro.disponible_kindle === null ? null : (libro.disponible_kindle ? "Sí" : "No")],
        ["Audiolibro", libro.disponible_audiolibro === null ? null : (libro.disponible_audiolibro ? "Sí" : "No")]
      ];
      let y = 206;
      filas.forEach(([k, v]) => {
        ctx.globalAlpha = 0.6;
        ctx.font = '600 16px "Inter", Arial, sans-serif';
        ctx.fillText(k.toUpperCase(), 54, y);
        ctx.globalAlpha = 0.92;
        ctx.font = '500 30px "Newsreader", Georgia, serif';
        ctx.fillText(v === null || v === undefined || v === "" ? "—" : String(v), 54, y + 36);
        ctx.globalAlpha = 0.22;
        ctx.fillRect(54, y + 54, w - 108, 1);
        y += 74;
      });
      ctx.globalAlpha = 1;
    },
    /* 7 · colofón: nota, precio y el aviso legal */
    (ctx, w, h) => {
      ctx.font = '600 18px "Inter", Arial, sans-serif';
      ctx.fillText("NUESTRA NOTA", 54, 152);
      ctx.font = '400 118px "Fraunces", Georgia, serif';
      ctx.fillText(libro.notaMedia === null ? "—" : String(libro.notaMedia).replace(".", ","), 52, 292);
      ctx.globalAlpha = 0.6;
      ctx.font = '600 20px "Inter", Arial, sans-serif';
      ctx.fillText("sobre 10", 54, 330);
      if (libro.valoracion_media) {
        ctx.globalAlpha = 0.85;
        ctx.font = '500 28px "Newsreader", Georgia, serif';
        ctx.fillText(String(libro.valoracion_media).replace(".", ",") + " ★ en Amazon"
          + (libro.resenas_cantidad ? " · " + libro.resenas_cantidad.toLocaleString("es-ES") + " reseñas" : ""),
          54, 392);
      }
      ctx.globalAlpha = 0.22;
      ctx.fillRect(54, 428, w - 108, 1);
      if (libro.precio !== null && libro.precio !== undefined) {
        ctx.globalAlpha = 0.6;
        ctx.font = '600 16px "Inter", Arial, sans-serif';
        ctx.fillText("PRECIO ORIENTATIVO", 54, 478);
        ctx.globalAlpha = 0.92;
        ctx.font = '400 60px "Fraunces", Georgia, serif';
        ctx.fillText(eur(libro.precio), 52, 546);
        ctx.globalAlpha = 0.62;
        ctx.font = '400 20px "Newsreader", Georgia, serif';
        ctx.fillText("Tomado el " + (libro.precio_fecha || "") + ". Consúltalo en Amazon.", 54, 584);
      }
      ctx.globalAlpha = 0.58;
      ctx.font = '400 20px "Newsreader", Georgia, serif';
      escribirBloque(ctx, "Como afiliados de Amazon, ganamos una comisión por las compras que "
        + "cumplen los requisitos. Para ti el precio es el mismo.", 54, 638, w - 108, 27, 3);
      ctx.globalAlpha = 1;
    }
  ];

  return pintores.map((pintar, i) => {
    const c = document.createElement("canvas");
    const W = 512, H = 768;
    /* AQUI estaba el problema de que no se leyera nada. El lienzo media
       384x576 y encima se dibujaba a escala 0.75, o sea que un texto de
       "21px" acababa midiendo 15,75 pixeles DE VERDAD... y luego esa textura
       se estiraba sobre unos 600 pixeles de pantalla. Al ampliar casi el
       doble, las letras se convertian en un borron gris por muy negra que
       fuese la tinta. No era un problema de color: era de resolucion.
       Ahora se dibuja al triple: el mismo texto ocupa 63 pixeles reales.
       Las coordenadas siguen en el espacio 512x768, no hay que tocar nada mas. */
    /* En movil se baja a x2: x3 son ~113 MB de textura solo para el libro
       abierto y un telefono no lo aguanta. Con x2 el texto sigue saliendo a 44
       pixeles reales, de sobra para la pantalla, y baja a ~50 MB. */
    const ESCALA = anchoVista < 820 ? 2 : 3;
    c.width = W * ESCALA; c.height = H * ESCALA;
    const ctx = c.getContext("2d");
    ctx.scale(ESCALA, ESCALA);
    superficiePapel(ctx, W, H, azar(semilla(libro.id + "-hoja-" + i)));
    ctx.fillStyle = tinta;
    ctx.strokeStyle = tinta;
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";

    /* cabecera y pie iguales en todas: da unidad al libro */
    ctx.globalAlpha = 0.5;
    ctx.font = '600 15px "Inter", Arial, sans-serif';
    ctx.fillText("BOOKATME", 48, 50);
    ctx.textAlign = "right";
    ctx.fillText(pad(i + 1), W - 48, 48);
    ctx.textAlign = "left";
    ctx.fillRect(48, 62, W - 96, 1);
    ctx.globalAlpha = 1;

    pintar(ctx, W, H);

    ctx.globalAlpha = 0.5;
    ctx.fillRect(48, H - 48, W - 96, 1);
    ctx.font = '500 15px "Inter", Arial, sans-serif';
    ctx.fillText("bookatme · comparativas de libros", 48, H - 26);
    ctx.globalAlpha = 1;

    const t = ajustarTextura(new THREE.CanvasTexture(c));
    t.name = libro.id + "-hoja-" + (i + 1);
    return t;
  });
}

/* --- geometrías a medida ------------------------------------------------ */
function planoRedondeado(w, h, r) {
  const hw = w * 0.5, hh = h * 0.5;
  const q = Math.min(r, hw, hh);
  const forma = new THREE.Shape();
  forma.moveTo(-hw + q, -hh);
  forma.lineTo(hw - q, -hh);
  forma.quadraticCurveTo(hw, -hh, hw, -hh + q);
  forma.lineTo(hw, hh - q);
  forma.quadraticCurveTo(hw, hh, hw - q, hh);
  forma.lineTo(-hw + q, hh);
  forma.quadraticCurveTo(-hw, hh, -hw, hh - q);
  forma.lineTo(-hw, -hh + q);
  forma.quadraticCurveTo(-hw, -hh, -hw + q, -hh);
  const g = new THREE.ShapeGeometry(forma, 8);
  const pos = g.getAttribute("position");
  const uv = new Float32Array(pos.count * 2);
  for (let i = 0; i < pos.count; i += 1) {
    uv[i * 2] = (pos.getX(i) + hw) / w;
    uv[i * 2 + 1] = (pos.getY(i) + hh) / h;
  }
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  g.computeVertexNormals();
  return g;
}

function bloquePaginas(w, h, d, r) {
  const g = new RoundedBoxGeometry(w, h, d, 4, r);
  const pos = g.getAttribute("position");
  const hw = w * 0.5;
  for (let i = 0; i < pos.count; i += 1) {
    const x = pos.getX(i), z = pos.getZ(i);
    const nx = clamp((x + hw) / w, 0, 1);
    const t = clamp(nx / 0.16, 0, 1);
    const suavizado = t * t * (3 - 2 * t);
    const compresion = (1 - suavizado) * 0.012;
    const canto = Math.pow(nx, 8) * Math.sin(pos.getY(i) * 31) * 0.00055;
    pos.setZ(i, Math.sign(z || 1) * Math.max(0, Math.abs(z) - compresion + canto));
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  g.computeBoundingBox();
  g.computeBoundingSphere();
  return g;
}

/* =========================================================================
   CONSTRUCCIÓN DE UN LIBRO
   ========================================================================= */
function malla(geo, mat, nombre, proyecta = true, recibe = true) {
  const m = new THREE.Mesh(geo, mat);
  m.name = nombre;
  m.castShadow = proyecta;
  m.receiveShadow = recibe;
  return m;
}

function cantoneras(pivote, libro, lado, w, h, z, mat) {
  const grosor = 0.002, borde = 0.018;
  const largoH = w - borde * 0.7, largoV = h - borde * 2.2;
  [["cabeza", w * 0.5, h * 0.5 - borde * 0.56, largoH, borde],
   ["pie", w * 0.5, -h * 0.5 + borde * 0.56, largoH, borde],
   ["lomo", borde * 0.56, 0, borde, largoV],
   ["canto", w - borde * 0.56, 0, borde, largoV]].forEach(([n, x, y, sw, sh]) => {
    const tira = malla(comun.caja, mat, libro.id + "-" + lado + "-cantonera-" + n, false, true);
    tira.scale.set(sw, sh, grosor);
    tira.position.set(x, y, z);
    pivote.add(tira);
  });
}

function crearLibro(libro, indice) {
  const pal = paletaDe(libro.categoria);
  const raiz = new THREE.Group();
  raiz.name = "libro-" + libro.id;
  raiz.userData.indice = indice;

  const mov = new THREE.Group();
  mov.name = libro.id + "-mov";
  raiz.add(mov);

  /* proporciones: cada libro un poco distinto, según sus páginas reales */
  const paginas = libro.num_paginas || 320;
  const w = 1.02;
  const h = 1.5 + clamp((paginas - 200) / 900, -0.06, 0.16);
  const d = clamp(0.14 + paginas / 2600, 0.16, 0.34);

  const tabla = 0.032, rTapa = 0.0045, rPag = 0.0025, rLomo = 0.0015;
  const grosorLomo = 0.014, anchoLomo = 0.082;
  const wPag = w - 0.074, hPag = h - 0.068, dPag = d - 0.026;

  const aspectoCara = (h - 0.007) / (w - 0.007);
  const texPortada = texturaPortada(libro, aspectoCara);
  const texLomo = texturaLomo(libro);
  const texContra = texturaContra(libro, aspectoCara);
  const texGuardas = texturaGuardas(libro);
  const texPapel = texturaPapel();
  const cantos = texturasCanto();
  const tela = mapasTela(libro);

  const matTela = new THREE.MeshPhysicalMaterial({
    color: pal.tela, normalMap: tela.normal, normalScale: new THREE.Vector2(0.34, 0.34),
    roughnessMap: tela.rugosidad, roughness: 0.98, metalness: 0.02,
    sheen: 0.34, sheenRoughness: 0.76, sheenColor: new THREE.Color(pal.foil), transparent: true
  });
  /* Una sobrecubierta impresa, no tela: menos difusa y con un barniz de verdad.
     El emissiveMap es lo que mas se nota: sostiene el color de la portada
     cuando el libro cae en la parte oscura de la balda, que era justo donde se
     veian lavadas. `transparent` no sobra, es lo que permite el fundido de
     entrada (ver `fundibles`); quitarlo lo rompe en silencio. */
  /* La portada tiene que parecerse a la foto real, no a un plastico.
     El `clearcoat` de antes era una capa de barniz que reflejaba las luces de la
     sala y dejaba un brillo cruzando la imagen: ESE era el "filtro" raro. Y con
     `envMapIntensity` a 1 le entraban ademas los reflejos del entorno.
     Ahora: papel impreso mate, casi sin barniz, con pocos reflejos y con el
     `emissiveMap` alto para que mande el color propio de la portada por encima
     de la iluminacion de la escena. */
  const matPortada = new THREE.MeshPhysicalMaterial({
    map: texPortada,
    /* 0.5 la dejaba demasiado clara: sumada a la luz de la sala, la portada
       salia por encima de su color real y se lavaba. Con el mapeo neutro ya no
       hace falta forzarla, basta un empujon pequeno para que no se apague en la
       parte oscura de la balda. */
    emissive: 0xffffff, emissiveMap: texPortada, emissiveIntensity: 0.16,
    roughness: 0.92, metalness: 0,
    clearcoat: 0.03, clearcoatRoughness: 0.9,
    envMapIntensity: 0.22,
    transparent: true
  });
  const matLomo = new THREE.MeshPhysicalMaterial({
    map: texLomo, normalMap: tela.normal, normalScale: new THREE.Vector2(0.3, 0.3),
    roughnessMap: tela.rugosidad, roughness: 0.95, metalness: 0.025,
    sheen: 0.27, sheenRoughness: 0.78, transparent: true, side: THREE.DoubleSide
  });
  /* Con contraportada real se comporta como la tapa; sin ella, sigue siendo tela. */
  const contraReal = !!libro.contraportada;
  const matContra = new THREE.MeshPhysicalMaterial({
    map: texContra,
    normalMap: contraReal ? null : tela.normal, normalScale: new THREE.Vector2(0.28, 0.28),
    roughnessMap: contraReal ? null : tela.rugosidad,
    emissive: 0xffffff, emissiveMap: contraReal ? texContra : null,
    emissiveIntensity: contraReal ? 0.16 : 0,
    roughness: contraReal ? 0.92 : 0.96, metalness: contraReal ? 0 : 0.025,
    clearcoat: contraReal ? 0.03 : 0, clearcoatRoughness: 0.9,
    envMapIntensity: contraReal ? 0.22 : 1,
    sheen: contraReal ? 0 : 0.25, sheenRoughness: 0.8,
    transparent: true, side: THREE.DoubleSide
  });
  const matGuardas = new THREE.MeshPhysicalMaterial({
    color: 0xffffff, map: texGuardas, bumpMap: texPapel, bumpScale: 0.0018,
    roughness: 0.94, metalness: 0, sheen: 0.025, sheenRoughness: 1,
    side: THREE.DoubleSide, transparent: true
  });
  const matCantoLargo = new THREE.MeshPhysicalMaterial({
    color: 0xffffff, map: cantos.largo, bumpMap: cantos.largo, bumpScale: 0.0022,
    roughness: 0.93, metalness: 0, side: THREE.DoubleSide, transparent: true
  });
  const matCantoCorto = new THREE.MeshPhysicalMaterial({
    color: 0xffffff, map: cantos.corto, bumpMap: cantos.corto, bumpScale: 0.0015,
    roughness: 0.94, metalness: 0, side: THREE.DoubleSide, transparent: true
  });
  const matRanura = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(pal.tela).multiplyScalar(0.42), roughness: 0.9, metalness: 0,
    side: THREE.DoubleSide, transparent: true
  });
  const matPapel = conFundido(comun.papel);
  matPapel.map = texPapel; matPapel.bumpMap = texPapel; matPapel.bumpScale = 0.0014;
  matPapel.needsUpdate = true;
  const matCabezada = conFundido(comun.cabezada);
  /* Los interiores ya NO se dibujan al arrancar. A triple resolucion, 8 hojas
     por libro y 10 libros serian 80 lienzos enormes en memoria de golpe (medio
     giga largo) y un arranque lentisimo. Como solo se puede tener un libro
     abierto a la vez, se dibujan al abrirlo y se sueltan al pasar a otro.
     Ver asegurarInteriores() / soltarInteriores(). */
  const matsInteriores = [];
  for (let i = 0; i < HOJAS * 2; i += 1) {
    const m = conFundido(comun.hoja);
    m.map = texPapel; m.bumpMap = texPapel; m.bumpScale = 0.0012;
    m.roughness = 0.96; m.side = THREE.FrontSide;
    /* La pieza que faltaba para que se leyera. Sin esto, la pagina solo se ve
       con la luz que le llega, y en una escena calida y a media luz el papel
       blanco se queda gris; la tinta negra baja con el, y el contraste se
       come. Con el emissiveMap, el papel tira hacia su blanco de verdad y la
       tinta sigue negra, porque los dos salen del mismo dibujo. */
    m.emissive = new THREE.Color(0xffffff);
    m.emissiveMap = texPapel;
    m.emissiveIntensity = 0.5;
    m.envMapIntensity = 0.25;
    m.needsUpdate = true;
    matsInteriores.push(m);
  }
  const matHojaLisa = conFundido(comun.hoja);
  matHojaLisa.map = texPapel; matHojaLisa.bumpMap = texPapel; matHojaLisa.bumpScale = 0.0012;
  matHojaLisa.roughness = 0.96; matHojaLisa.side = THREE.FrontSide;
  /* mismo brillo propio que las paginas con texto, o se nota el salto */
  matHojaLisa.emissive = new THREE.Color(0xffffff);
  matHojaLisa.emissiveMap = texPapel;
  matHojaLisa.emissiveIntensity = 0.5;
  matHojaLisa.envMapIntensity = 0.25;
  matHojaLisa.needsUpdate = true;
  const matCuadernillo = new THREE.MeshPhysicalMaterial({
    color: 0x8d816f, roughness: 0.98, metalness: 0, transparent: true
  });
  const matCinta = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(pal.foil).lerp(new THREE.Color(pal.tela), 0.28),
    roughness: 0.62, metalness: 0.08, sheen: 0.36, sheenRoughness: 0.68,
    side: THREE.DoubleSide, transparent: true
  });

  const geoTapa = new RoundedBoxGeometry(w, h, tabla, 2, rTapa);
  const geoBloque = bloquePaginas(wPag, hPag, dPag, rPag);
  const geoCara = planoRedondeado(w - 0.007, h - 0.007, 0.0035);
  const geoGuardas = planoRedondeado(w - 0.045, h - 0.045, 0.003);

  const bloque = malla(geoBloque, matPapel, libro.id + "-bloque");
  bloque.position.x = 0.018;
  mov.add(bloque);

  /* --- contratapa --- */
  const pivContra = new THREE.Group();
  pivContra.name = libro.id + "-piv-contra";
  pivContra.position.set(-w * 0.5, 0, -d * 0.5 - tabla * 0.5);
  const tapaAtras = malla(geoTapa, matTela, libro.id + "-contratapa");
  tapaAtras.position.x = w * 0.5;
  pivContra.add(tapaAtras);
  const caraContra = malla(geoCara, matContra, libro.id + "-contra-arte", false, false);
  caraContra.position.set(w * 0.5, 0, -tabla * 0.55);
  caraContra.rotation.y = Math.PI;
  pivContra.add(caraContra);
  const guardaAtras = malla(geoGuardas, matGuardas, libro.id + "-guarda-atras", false, true);
  guardaAtras.position.set(w * 0.5, 0, tabla * 0.515);
  pivContra.add(guardaAtras);
  cantoneras(pivContra, libro, "contra", w, h, tabla * 0.53, matTela);
  const ranuraAtras = malla(comun.plano, matRanura, libro.id + "-ranura-atras", false, false);
  ranuraAtras.scale.set(0.012, h * 0.94, 1);
  ranuraAtras.position.set(0.038, 0, -tabla * 0.535);
  ranuraAtras.rotation.y = Math.PI;
  pivContra.add(ranuraAtras);
  mov.add(pivContra);

  /* --- tapa delantera (la que se abre) --- */
  const pivTapa = new THREE.Group();
  pivTapa.name = libro.id + "-piv-tapa";
  pivTapa.position.set(-w * 0.5, 0, d * 0.5 + tabla * 0.5);
  const tapa = malla(geoTapa, matTela, libro.id + "-tapa");
  tapa.position.x = w * 0.5;
  pivTapa.add(tapa);
  const caraPortada = malla(geoCara, matPortada, libro.id + "-portada", false, false);
  caraPortada.position.set(w * 0.5, 0, tabla * 0.55);
  pivTapa.add(caraPortada);
  const guardaDelante = malla(geoGuardas, matGuardas, libro.id + "-guarda-delante", false, true);
  guardaDelante.position.set(w * 0.5, 0, -tabla * 0.515);
  guardaDelante.rotation.y = Math.PI;
  pivTapa.add(guardaDelante);
  cantoneras(pivTapa, libro, "tapa", w, h, -tabla * 0.53, matTela);
  const ranuraDelante = malla(comun.plano, matRanura, libro.id + "-ranura-delante", false, false);
  ranuraDelante.scale.set(0.012, h * 0.94, 1);
  ranuraDelante.position.set(0.038, 0, tabla * 0.655);
  pivTapa.add(ranuraDelante);
  mov.add(pivTapa);

  /* --- las hojas que se pasan --- */
  const pivotes = [];
  const superficies = [];
  const anchoVisible = wPag - anchoLomo * 0.42;
  for (let i = 0; i < 6; i += 1) {
    const orden = 5 - i;
    const matA = orden < HOJAS ? matsInteriores[orden * 2] : matHojaLisa;
    const matB = orden < HOJAS ? matsInteriores[orden * 2 + 1] : matHojaLisa;
    const piv = new THREE.Group();
    piv.name = libro.id + "-hoja-" + i;
    piv.position.set(-w * 0.5 + anchoLomo * 0.65, 0, dPag * 0.5 + 0.0015 + i * 0.0015);
    piv.userData.zReposo = piv.position.z;
    piv.userData.zPasada = d * 0.5 + tabla + 0.004 + orden * 0.0015;

    const geoA = new THREE.PlaneGeometry(1, 1, SEG_H, SEG_V);
    const geoB = new THREE.PlaneGeometry(1, 1, SEG_H, SEG_V);
    const caraA = malla(geoA, matA, libro.id + "-hoja-" + i + "-a", false, true);
    caraA.scale.set(anchoVisible, hPag - 0.014, 1);
    caraA.position.set(anchoVisible * 0.5, 0, 0.00022);
    piv.add(caraA);
    superficies.push(caraA);
    const caraB = malla(geoB, matB, libro.id + "-hoja-" + i + "-b", false, true);
    caraB.scale.set(anchoVisible, hPag - 0.014, 1);
    caraB.position.set(anchoVisible * 0.5, 0, -0.00022);
    caraB.rotation.y = Math.PI;
    piv.add(caraB);
    superficies.push(caraB);

    piv.userData.flex = {
      curva: 0, vCurva: 0, torsion: 0, vTorsion: 0,
      caras: [
        { geo: geoA, pos: geoA.attributes.position, base: Float32Array.from(geoA.attributes.position.array), sentido: 1 },
        { geo: geoB, pos: geoB.attributes.position, base: Float32Array.from(geoB.attributes.position.array), sentido: -1 }
      ]
    };
    mov.add(piv);
    pivotes.push(piv);
  }

  /* --- lomo --- */
  const lomo = malla(new RoundedBoxGeometry(grosorLomo, h - 0.012, d + tabla * 1.88, 1, rLomo),
                     matLomo, libro.id + "-lomo");
  lomo.position.x = -w * 0.5 - grosorLomo * 0.35;
  mov.add(lomo);

  const forro = malla(new RoundedBoxGeometry(anchoLomo * 0.68, h - 0.056,
                        Math.max(0.045, dPag - 0.008), 1, 0.0015),
                      matGuardas, libro.id + "-forro-lomo");
  forro.position.set(-w * 0.5 + anchoLomo * 0.38, 0, 0);
  mov.add(forro);

  [-1, 1].forEach((s) => {
    const cab = malla(new THREE.CylinderGeometry(0.012, 0.012, dPag * 0.88, 12, 1, false),
                      matCabezada, libro.id + "-cabezada-" + s);
    cab.rotation.x = Math.PI * 0.5;
    cab.position.set(-wPag * 0.5 + 0.046, s * (hPag * 0.5 - 0.004), 0);
    mov.add(cab);
  });

  /* --- cinta de leer --- */
  const cinta = malla(planoRedondeado(0.034, hPag * 0.76, 0.002), matCinta,
                      libro.id + "-cinta", false, true);
  cinta.position.set(-wPag * 0.5 + 0.09 + (semilla(libro.id) % 3) * 0.018, -hPag * 0.17, dPag * 0.5 + 0.003);
  cinta.rotation.z = (semilla(libro.id) % 2 ? -1 : 1) * 0.014;
  mov.add(cinta);

  /* --- cuadernillos y cantos --- */
  for (let i = 0; i < 6; i += 1) {
    const c = malla(comun.caja, matCuadernillo, libro.id + "-cuadernillo-" + i, false, true);
    c.scale.set(0.0035, 0.00135, dPag * 0.91);
    c.position.set(0.018 + wPag * 0.5 + 0.001, -hPag * 0.5 + ((i + 1) / 7) * hPag, 0);
    mov.add(c);
  }
  const cantoLargo = malla(comun.plano, matCantoLargo, libro.id + "-canto", false, true);
  cantoLargo.scale.set(dPag * 0.94, hPag - 0.028, 1);
  cantoLargo.rotation.y = Math.PI * 0.5;
  cantoLargo.position.set(0.018 + wPag * 0.5 + 0.002, 0, 0);
  mov.add(cantoLargo);
  [-1, 1].forEach((s) => {
    const c = malla(comun.plano, matCantoCorto, libro.id + "-canto-" + s, false, true);
    c.scale.set(wPag - 0.035, dPag * 0.94, 1);
    c.rotation.x = s > 0 ? -Math.PI * 0.5 : Math.PI * 0.5;
    c.position.set(0.018, s * (hPag * 0.5 + 0.002), 0);
    mov.add(c);
  });

  /* --- diana invisible para el ratón --- */
  const matDiana = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
  const diana = malla(comun.caja, matDiana, libro.id + "-diana", false, false);
  diana.scale.set(w * 1.34, h * 1.2, Math.max(d * 4, 1));
  diana.position.set(-anchoLomo * 0.18, 0, 0.12);
  diana.userData.indice = indice;
  mov.add(diana);
  dianas.push(diana);

  /* --- sombra bajo el libro --- */
  const matSombra = new THREE.MeshBasicMaterial({
    color: new THREE.Color(0x2a170f), alphaMap: texturaSombra(),
    transparent: true, opacity: 0.24, depthWrite: false, side: THREE.DoubleSide
  });
  const sombra = malla(comun.plano, matSombra, libro.id + "-sombra", false, false);
  sombra.scale.set(w * 1.22, d * 2.05, 1);
  sombra.rotation.x = -Math.PI * 0.5;
  sombra.position.set(0, -h * 0.5 - 0.022, 0.025);
  raiz.add(sombra);

  const conFundidoTodos = [matTela, matPortada, matLomo, matContra, matGuardas,
    matCantoLargo, matCantoCorto, matRanura, matPapel, ...matsInteriores,
    matHojaLisa, matCabezada, matCuadernillo, matCinta];

  return {
    datos: libro, raiz, mov, pivTapa, tapa, bloque, pivotes, superficies,
    gestos: [...superficies, bloque], diana, sombra,
    opacidad: 1, desfasePrevio: null,
    /* el estado de los interiores dibujados a demanda */
    interiores: { hechas: false, texturas: [], mats: matsInteriores },
    fundibles: conFundidoTodos,
    materiales: [...conFundidoTodos, matSombra, matDiana],
    base: { w, h, d }
  };
}

/* =========================================================================
   LA SALA
   ========================================================================= */
function montarSala() {
  comun.nogal.map = cargarMadera("assets/img/madera-balda.webp", 7, 1);
  comun.nogalOscuro.map = cargarMadera("assets/img/madera-balda.webp", 5, 1);

  const suelo = malla(comun.plano, new THREE.MeshStandardMaterial({
    color: 0xd8c8aa, roughness: 0.92, metalness: 0 }), "suelo", false, true);
  suelo.scale.set(30, 20, 1);
  suelo.rotation.x = -Math.PI * 0.5;
  suelo.position.y = -0.02;
  escena.add(suelo);

  const pared = malla(comun.plano, new THREE.MeshStandardMaterial({
    color: 0xe9dfcb, roughness: 0.78, metalness: 0,
    map: cargarMadera("assets/img/madera-pared.webp", 5, 2.2) }), "pared", false, true);
  pared.scale.set(28, 14, 1);
  pared.position.set(0, 5.5, -3.3);
  escena.add(pared);

  const balda = malla(comun.caja, comun.nogal, "balda");
  balda.scale.set(17, 0.28, 1.08);
  balda.position.set(0, 0.33, -0.03);
  tarima.add(balda);

  const listón = malla(comun.caja, comun.nogalOscuro, "balda-canto");
  listón.scale.set(17.05, 0.075, 1.14);
  listón.position.set(0, 0.205, 0.02);
  tarima.add(listón);

  const trasera = malla(comun.caja, comun.nogal, "balda-trasera");
  trasera.scale.set(17, 0.17, 0.2);
  trasera.position.set(0, 0.68, -0.52);
  tarima.add(trasera);

  [-7.65, 7.65].forEach((x, i) => {
    const montante = malla(comun.caja, comun.nogalOscuro, "montante-" + i);
    montante.scale.set(0.2, 3.8, 0.72);
    montante.position.set(x, 2.05, -0.28);
    tarima.add(montante);
  });

  const franja = malla(comun.plano, new THREE.MeshBasicMaterial({
    color: 0x2f1d13, alphaMap: texturaSombra(), transparent: true,
    opacity: 0.22, depthWrite: false }), "sombra-balda", false, false);
  franja.scale.set(16, 0.85, 1);
  franja.rotation.x = -Math.PI * 0.5;
  franja.position.set(0, 0.49, 0.06);
  tarima.add(franja);

  materialesSala.suelo = suelo.material;
  materialesSala.pared = pared.material;
  materialesSala.madera = comun.nogal;
  materialesSala.maderaOscura = comun.nogalOscuro;
  materialesSala.sombra = franja.material;
}

function montarLuces() {
  lucesSala.hemi = new THREE.HemisphereLight(0xfff8e8, 0x5b4030, 0.56);
  escena.add(lucesSala.hemi);

  const clave = new THREE.DirectionalLight(0xffe8c2, 1.42);
  clave.position.set(-4.6, 7.4, 5.8);
  clave.castShadow = true;
  clave.shadow.mapSize.set(2048, 2048);
  clave.shadow.camera.left = -6; clave.shadow.camera.right = 6;
  clave.shadow.camera.top = 6; clave.shadow.camera.bottom = -1.5;
  clave.shadow.camera.near = 1; clave.shadow.camera.far = 18;
  clave.shadow.bias = -0.00018;
  clave.shadow.normalBias = 0.018;
  clave.shadow.radius = 3.5;
  escena.add(clave);
  lucesSala.clave = clave;

  const claveSuave = new THREE.RectAreaLight(0xffe8c2, 5.4, 4.8, 5.6);
  claveSuave.position.set(-3.2, 5.5, 4.6);
  claveSuave.lookAt(0, 1.45, 0);
  escena.add(claveSuave);
  lucesSala.claveSuave = claveSuave;

  const relleno = new THREE.DirectionalLight(0xd8e3e7, 0.3);
  relleno.position.set(5.5, 3.6, 4.2);
  escena.add(relleno);
  lucesSala.relleno = relleno;

  const borde = new THREE.RectAreaLight(0xd5a45e, 3.45, 1.6, 4.8);
  borde.position.set(3.8, 3.6, -2.1);
  borde.lookAt(-0.2, 1.5, 0);
  escena.add(borde);
  lucesSala.borde = borde;

  const trasera = new THREE.RectAreaLight(0xd8e3e7, 2.7, 3.8, 4.8);
  trasera.position.set(-1.8, 2.9, -4.5);
  trasera.lookAt(-0.1, 1.45, 0);
  escena.add(trasera);
  lucesSala.trasera = trasera;

  const rasanteLomo = new THREE.RectAreaLight(0xffe8c2, 1.9, 0.9, 4.6);
  rasanteLomo.position.set(-4.6, 3.2, 1.1);
  rasanteLomo.lookAt(-0.55, 1.5, 0);
  escena.add(rasanteLomo);
  lucesSala.lomo = rasanteLomo;

  const rasanteCanto = new THREE.RectAreaLight(0xfff7e7, 2.15, 1.15, 3.8);
  rasanteCanto.position.set(4.2, 4.8, 3.1);
  rasanteCanto.lookAt(0.65, 1.55, 0);
  escena.add(rasanteCanto);
  lucesSala.canto = rasanteCanto;
}

function montarPolvo() {
  const n = 110;
  const pos = new Float32Array(n * 3);
  const rnd = azar(20260825);
  for (let i = 0; i < n; i += 1) {
    pos[i * 3] = (rnd() - 0.5) * 14;
    pos[i * 3 + 1] = 0.7 + rnd() * 4.7;
    pos[i * 3 + 2] = -1.7 + rnd() * 4;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const polvo = new THREE.Points(g, new THREE.PointsMaterial({
    color: 0xc3a97b, size: 0.014, transparent: true, opacity: 0.3, depthWrite: false }));
  polvo.name = "polvo";
  escena.add(polvo);
}

/* =========================================================================
   INTERFAZ
   ========================================================================= */
function ajustesResponsive() {
  /* El panel tiene que quedar por debajo de la cabecera del sitio, que es
     pegajosa y va por encima de la escena. Se mide en vez de fijar un numero:
     si algun dia crece el menu, esto sigue valiendo. */
  /* Se mide el BORDE INFERIOR, no la altura: encima de la cabecera va la barra
     de aviso de afiliados, asi que empieza mas abajo de 0. */
  const cab = document.querySelector(".site-head");
  escena3d.style.setProperty("--est-cabecera",
    (cab ? Math.max(0, Math.round(cab.getBoundingClientRect().bottom)) : 104) + "px");

  const estrecho = anchoVista < 820;
  camEstante.set(0, estrecho ? 2.02 : 1.92, estrecho ? 8.7 : 8.1);
  objEstante.set(0, estrecho ? 1.57 : 1.55, 0);
  posDetalle.set(estrecho ? 0 : -2.25, estrecho ? 2.3 : 1.56, estrecho ? 0.15 : 0);
  camDetalle.set(estrecho ? 0 : -0.52, estrecho ? 2.46 : 1.78, estrecho ? 5.7 : 5.25);
  objDetalle.copy(posDetalle);

  if (estrecho) {
    desplazeDetalleX = 0;
    anchoSeguro = anchoVista;
    return;
  }
  const caja = panel.getBoundingClientRect();
  const izq = caja.left > 0 ? caja.left : anchoVista * 0.64;
  const margen = clamp(anchoVista * 0.035, 32, 56);
  anchoSeguro = Math.max(anchoVista * 0.42, izq - margen);
  const ancho = clamp((anchoVista - 820) / 620, 0, 1);
  const centro = anchoSeguro * lerp(0.55, 0.615, ancho);
  desplazeDetalleX = Math.max(0, anchoVista * 0.5 - centro);
}

function factorEscala() {
  if (!libroActivo || anchoVista < 820) return 0.82;
  const dist = Math.abs(camDetalle.z - posDetalle.z);
  const altoMundo = 2 * dist * Math.tan(THREE.MathUtils.degToRad(camara.fov * 0.5));
  const pxPorUnidad = altoVista / Math.max(altoMundo, 0.001);
  const anchoLibro = libroActivo.base.w * pxPorUnidad * 1.16;
  return clamp((anchoSeguro * 0.72) / Math.max(anchoLibro, 1), 0.9, 1.32);
}

function aplicarDesplazamiento() {
  if (Math.abs(desplazeActualX) < 0.5) { camara.clearViewOffset(); return; }
  camara.setViewOffset(anchoVista, altoVista, desplazeActualX, 0, anchoVista, altoVista);
}

/* --- tema por género ---------------------------------------------------- */
function fijarTemaYa() {
  materialesSala.suelo?.color.copy(destinoTema.suelo);
  materialesSala.pared?.color.copy(destinoTema.pared);
  materialesSala.madera?.color.copy(destinoTema.madera);
  materialesSala.maderaOscura?.color.copy(destinoTema.maderaOscura);
  materialesSala.sombra?.color.copy(destinoTema.sombra);
  escena?.fog?.color.copy(destinoTema.niebla);
  lucesSala.hemi?.color.copy(destinoTema.hemi);
  lucesSala.hemi?.groundColor.copy(destinoTema.hemiSuelo);
  lucesSala.clave?.color.copy(destinoTema.clave);
  lucesSala.claveSuave?.color.copy(destinoTema.clave);
  lucesSala.relleno?.color.copy(destinoTema.relleno);
  lucesSala.borde?.color.copy(destinoTema.borde);
  lucesSala.trasera?.color.copy(destinoTema.relleno);
  lucesSala.lomo?.color.copy(destinoTema.clave);
  lucesSala.canto?.color.copy(destinoTema.hemi);
  temaEnMovimiento = false;
}

function aplicarTema(libro) {
  const pal = paletaDe(libro.categoria);
  ultimoLibroTema = libro;
  destinoTema.suelo.set(pal.suelo);
  destinoTema.pared.set(pal.pared);
  /* La niebla ya no puede ser del color de la pared: contra madera oscura, una
     niebla palida la lava y parece un halo. Se tira hacia el marron del fondo
     conservando algo del tinte del genero. */
  destinoTema.niebla.set(pal.pared);
  destinoTema.niebla.lerp(NIEBLA_MADERA, 0.55);
  /* Con la foto de madera puesta, el color del material solo tine: blanco deja
     la madera tal cual, el gris la oscurece. Sin foto, el nogal liso de antes. */
  destinoTema.madera.set(maderaLista ? 0xffffff : 0x4a2b1d);
  destinoTema.maderaOscura.set(maderaLista ? 0x8a8a8a : 0x2a170f);
  destinoTema.sombra.set(0x2f1d13);
  destinoTema.hemi.set(pal.luz);
  destinoTema.hemiSuelo.set(0x5b4030);
  destinoTema.clave.set(pal.luz);
  destinoTema.relleno.set(pal.relleno);
  destinoTema.borde.set(pal.foil);
  escena3d.style.setProperty("--gen-tela", pal.tela);
  escena3d.style.setProperty("--gen-foil", pal.foil);
  if (!temaIniciado || movimientoReducido) { temaIniciado = true; fijarTemaYa(); }
  else { temaEnMovimiento = true; pedirCuadro(); }
}

function actualizarTema(dt) {
  if (!temaEnMovimiento) return false;
  const k = 1 - Math.exp(-dt * 5.5);
  let mayor = 0;
  const mover = (c, d) => {
    if (!c) return;
    const dr = c.r - d.r, dg = c.g - d.g, db = c.b - d.b;
    mayor = Math.max(mayor, dr * dr + dg * dg + db * db);
    c.lerp(d, k);
  };
  mover(materialesSala.suelo?.color, destinoTema.suelo);
  mover(materialesSala.pared?.color, destinoTema.pared);
  mover(materialesSala.madera?.color, destinoTema.madera);
  mover(materialesSala.maderaOscura?.color, destinoTema.maderaOscura);
  mover(materialesSala.sombra?.color, destinoTema.sombra);
  mover(escena?.fog?.color, destinoTema.niebla);
  mover(lucesSala.hemi?.color, destinoTema.hemi);
  mover(lucesSala.hemi?.groundColor, destinoTema.hemiSuelo);
  mover(lucesSala.clave?.color, destinoTema.clave);
  mover(lucesSala.claveSuave?.color, destinoTema.clave);
  mover(lucesSala.relleno?.color, destinoTema.relleno);
  mover(lucesSala.borde?.color, destinoTema.borde);
  mover(lucesSala.trasera?.color, destinoTema.relleno);
  mover(lucesSala.lomo?.color, destinoTema.clave);
  mover(lucesSala.canto?.color, destinoTema.hemi);
  if (mayor < 0.0000025) fijarTemaYa();
  return temaEnMovimiento;
}

/* --- marcadores --------------------------------------------------------- */
function construirMarcadores() {
  DATOS.forEach((libro, i) => {
    const b = document.createElement("button");
    b.className = "est-marcador";
    b.type = "button";
    b.setAttribute("role", "tab");
    b.setAttribute("aria-label", "Ver " + libro.titulo);
    b.setAttribute("aria-current", i === 0 ? "true" : "false");
    b.setAttribute("aria-selected", i === 0 ? "true" : "false");
    b.tabIndex = i === 0 ? 0 : -1;
    b.addEventListener("click", () => elegirMarcador(i, b));
    marcadores.append(b);
  });
}

function actualizarSeleccion(i, anunciar = false) {
  const n = mod(i, DATOS.length);
  if (n === seleccion && !anunciar) return;
  seleccion = n;
  const libro = DATOS[seleccion];
  tituloSel.textContent = libro.titulo;
  notaSel.textContent = libro.autor + " · " + libro.generoNombre;
  contador.textContent = pad(seleccion + 1) + " / " + pad(DATOS.length);
  btnAbrir.setAttribute("aria-label", "Abrir " + libro.titulo);
  aplicarTema(libro);
  [...marcadores.children].forEach((m, j) => {
    const act = j === seleccion;
    m.setAttribute("aria-current", act ? "true" : "false");
    m.setAttribute("aria-selected", act ? "true" : "false");
    m.tabIndex = act ? 0 : -1;
  });
  if (anunciar) {
    avisos.textContent = "Libro " + (seleccion + 1) + " de " + DATOS.length + ": "
      + libro.titulo + ", de " + libro.autor + ".";
  }
}

/* --- panel lateral ------------------------------------------------------ */
function rellenarPanel(libro) {
  pGenero.textContent = libro.generoNombre + " · nota " +
    (libro.notaMedia === null ? "—" : String(libro.notaMedia).replace(".", ","));
  pTitulo.textContent = libro.titulo;
  pAutor.textContent = libro.autor || "";
  pSinopsis.textContent = libro.destacado_editorial || libro.descripcion || "";

  pDatos.innerHTML = "";
  [["Género", libro.generoNombre],
   ["Páginas", libro.num_paginas ? libro.num_paginas + " págs." : null],
   ["Se lee en", libro.horas_lectura ? "~" + libro.horas_lectura + " h" : null],
   ["En Amazon", libro.valoracion_media ? String(libro.valoracion_media).replace(".", ",") + " ★" : null]
  ].forEach(([k, v]) => {
    const d = document.createElement("div");
    const dt = document.createElement("dt");
    dt.textContent = k;
    const dd = document.createElement("dd");
    dd.textContent = v === null || v === undefined ? "—" : v;
    d.append(dt, dd);
    pDatos.append(d);
  });

  pPros.innerHTML = "";
  (libro.pros || []).slice(0, 3).forEach((p) => {
    const li = document.createElement("li");
    li.textContent = p;
    pPros.append(li);
  });

  pComprar.href = libro.affiliate_url;
  pFicha.href = libro.ficha_url;
  pPrecio.textContent = libro.precio === null || libro.precio === undefined
    ? "Ver precio en Amazon"
    : eur(libro.precio) + " · precio orientativo";
}

const etiquetasPliego = () => TITULOS_PLIEGO;

function actualizarControlesPagina(anunciar = false) {
  const et = etiquetasPliego();
  const bloqueado = modo !== "detalle" || !hojeando;
  const sinAnterior = bloqueado || pliegoActual === 0;
  const sinSiguiente = bloqueado || pliegoActual === PLIEGOS - 1;
  btnPagAnterior.disabled = sinAnterior;
  btnPagSiguiente.disabled = sinSiguiente;
  etiquetaPag.textContent = hojeando ? et[pliegoActual] : "Cerrado";
  contadorPag.textContent = hojeando ? pad(pliegoActual + 1) + " / " + pad(PLIEGOS) : "Ábrelo para hojear";
  btnHojear.textContent = hojeando ? "Cerrar el libro" : "Hojear el libro";
  btnHojear.setAttribute("aria-pressed", String(hojeando));
  pistaPanel.textContent = hojeando
    ? "Arrastra las páginas. La tapa, para cerrar."
    : "Toca el libro o arrastra la tapa para abrirlo";
  if (anunciar && libroActivo && hojeando) {
    avisos.textContent = "Página " + (pliegoActual + 1) + " de " + PLIEGOS + ": " + et[pliegoActual] + ".";
  }
}

function ponerHojeando(abierto, anunciar = true) {
  if (modo !== "detalle" || hojeando === abierto) return;
  cancelarArrastre();
  hojeando = abierto;
  if (!hojeando) pliegoActual = 0;
  lienzo.classList.remove("sobre-pagina", "sobre-libro");
  actualizarControlesPagina(false);
  ratonSucio = true;
  if (anunciar && libroActivo) {
    avisos.textContent = hojeando
      ? libroActivo.datos.titulo + " abierto por la portadilla. Arrastra una página para leer."
      : libroActivo.datos.titulo + " cerrado.";
  }
  pedirCuadro();
}

function pasarPagina(sentido) {
  if (modo !== "detalle" || !hojeando) return;
  const n = clamp(pliegoActual + sentido, 0, PLIEGOS - 1);
  if (n === pliegoActual) return;
  pliegoActual = n;
  actualizarControlesPagina(true);
  pedirCuadro();
}

function elegirMarcador(i, origen) {
  if (modo !== "estante") return;
  const r = Math.round(posicionDestino);
  const actual = mod(r, DATOS.length);
  let d = i - actual;
  if (d > DATOS.length / 2) d -= DATOS.length;
  if (d < -DATOS.length / 2) d += DATOS.length;
  posicionDestino = r + d;
  focoDeVuelta = origen;
  actualizarSeleccion(i, true);
  pedirCuadro();
}

function navegar(sentido, origen) {
  if (modo !== "estante") return;
  posicionDestino = Math.round(posicionDestino) + sentido;
  focoDeVuelta = origen;
  actualizarSeleccion(mod(Math.round(posicionDestino), DATOS.length), true);
  pedirCuadro();
}

function alinearEstante() {
  const r = Math.round(posicionDestino);
  const actual = mod(r, DATOS.length);
  let d = seleccion - actual;
  if (d > DATOS.length / 2) d -= DATOS.length;
  if (d < -DATOS.length / 2) d += DATOS.length;
  posicionDestino = r + d;
  posicion = posicionDestino;
}

function colocarEnBalda(l, i) {
  let desf = i - posicion;
  desf -= Math.round(desf / DATOS.length) * DATOS.length;
  const dist = Math.abs(desf);
  const foco = 1 - clamp(dist, 0, 1);
  const op = 1 - suave(clamp((dist - 2.55) / 0.7, 0, 1));
  l.raiz.position.set(desf * SEPARACION, TAPA_ARRIBA + l.base.h * 0.5 + foco * 0.15,
                      0.13 + foco * 0.24 - Math.min(dist, 2.8) * 0.07);
  l.raiz.rotation.set(0, -desf * 0.105, -desf * 0.018);
  l.raiz.scale.setScalar(1 + foco * 0.09);
  l.mov.position.y = 0;
  l.mov.rotation.set(0, 0, 0);
  l.pivTapa.rotation.y = 0;
  l.pivotes.forEach((p) => {
    p.rotation.y = 0; p.rotation.z = 0;
    p.position.z = p.userData.zReposo;
    flexionar(p, 0, 0, true);
  });
  l.opacidad = op;
  l.fundibles.forEach((m) => { m.opacity = op; });
  l.sombra.visible = true;
  l.sombra.material.opacity = op * 0.24;
  l.diana.visible = op > 0.12;
  l.desfasePrevio = desf;
}

/* =========================================================================
   FÍSICA DE LA PÁGINA — lo que hace que parezca papel y no cartón
   ========================================================================= */
function flexionar(piv, curvaObj, dt, inmediato = false, torsionObj = 0) {
  const f = piv.userData.flex;
  if (!f) return;
  const yaMismo = inmediato || movimientoReducido;
  const paso = Math.min(dt, 0.033);
  let curva = curvaObj, torsion = torsionObj;

  if (yaMismo) { f.vCurva = 0; f.vTorsion = 0; }
  else {
    f.vCurva = clamp(f.vCurva + ((curvaObj - f.curva) * 178 - f.vCurva * 19) * paso, -1.8, 1.8);
    f.vTorsion = clamp(f.vTorsion + ((torsionObj - f.torsion) * 210 - f.vTorsion * 21) * paso, -1.6, 1.6);
    curva = clamp(f.curva + f.vCurva * paso, -0.025, 0.19);
    torsion = clamp(f.torsion + f.vTorsion * paso, -0.12, 0.12);
    if (Math.abs(curvaObj - curva) < 0.00002 && Math.abs(f.vCurva) < 0.0008) { curva = curvaObj; f.vCurva = 0; }
    if (Math.abs(torsionObj - torsion) < 0.00002 && Math.abs(f.vTorsion) < 0.0008) { torsion = torsionObj; f.vTorsion = 0; }
    if (Math.abs(curva - f.curva) < 0.00001 && Math.abs(curvaObj - curva) < 0.00001
      && Math.abs(torsion - f.torsion) < 0.00001 && Math.abs(torsionObj - torsion) < 0.00001) return;
  }

  f.curva = curva;
  f.torsion = torsion;
  f.caras.forEach((c) => {
    const { pos, base, sentido, geo } = c;
    for (let v = 0; v < pos.count; v += 1) {
      const o = v * 3;
      const x = base[o], y = base[o + 1];
      const u = x + 0.5;
      const uu = sentido > 0 ? u : 1 - u;
      const arco = Math.sin(Math.PI * uu);
      const levante = uu * uu * 0.16;
      const forma = arco * 0.84 + levante;
      const diagonal = torsion * y * Math.pow(uu, 1.35);
      const onda = torsion * Math.sin(uu * Math.PI * 2) * (1 - Math.min(1, Math.abs(y) * 1.65)) * 0.09;
      pos.setXYZ(v, x, y, (curva * forma * (1 + y * 0.14) + diagonal + onda) * sentido);
    }
    pos.needsUpdate = true;
    geo.computeVertexNormals();
  });
}

function animarLibroAbierto(l, dt, apertura = 1) {
  const a = clamp(apertura, 0, 1);
  const vel = movimientoReducido ? 1000 : 10.5;
  const rendija = (modo === "detalle" && !hojeando && libroSobrevolado && !movimientoReducido) ? -0.16 : 0;
  const objTapa = a > 0 ? (-Math.PI + 0.055) * a : rendija;
  l.pivTapa.rotation.y = damp(l.pivTapa.rotation.y, objTapa, vel, dt);

  l.pivotes.forEach((piv, i) => {
    const orden = l.pivotes.length - 1 - i;
    let objPag = 0, objZ = piv.userData.zReposo, objTorsion = 0, extraCurva = 0, objFlexTorsion = 0;

    if (orden < HOJAS) {
      const pasada = orden < pliegoActual;
      const sinPasar = -0.038 + orden * 0.008;
      const yaPasada = -Math.PI + 0.085 + orden * 0.014;
      objPag = pasada ? yaPasada : sinPasar;
      objZ = pasada ? piv.userData.zPasada : piv.userData.zReposo;

      if (arrastre.activo && arrastre.sentido !== 0) {
        const ordenArrastrado = arrastre.sentido > 0 ? pliegoActual : pliegoActual - 1;
        if (orden === ordenArrastrado) {
          const av = suave(arrastre.avance);
          const envolvente = Math.sin(Math.PI * av);
          const rapidez = clamp(Math.abs(arrastre.velocidad) / 5.5, 0, 1);
          const rapidezFirmada = clamp(arrastre.velocidad / 5.5, -1, 1);
          objPag = arrastre.sentido > 0 ? lerp(sinPasar, yaPasada, av) : lerp(yaPasada, sinPasar, av);
          objZ = arrastre.sentido > 0
            ? lerp(piv.userData.zReposo, piv.userData.zPasada, av)
            : lerp(piv.userData.zPasada, piv.userData.zReposo, av);
          objTorsion = arrastre.sentido * envolvente * (0.014 + arrastre.sesgoY * 0.026);
          extraCurva = envolvente * (0.032 + rapidez * 0.064);
          objFlexTorsion = envolvente * (arrastre.sesgoY * 0.08 + rapidezFirmada * arrastre.sentido * 0.03);
        }
      }
      piv.position.z = damp(piv.position.z,
        piv.userData.zReposo + (objZ - piv.userData.zReposo) * a, vel, dt);
    } else {
      objPag = -0.006 + (orden - HOJAS) * 0.003;
      piv.position.z = damp(piv.position.z, piv.userData.zReposo, vel, dt);
    }

    piv.rotation.y = damp(piv.rotation.y, objPag * a, vel, dt);
    piv.rotation.z = damp(piv.rotation.z, objTorsion * a, vel, dt);
    const avanceGiro = clamp(Math.abs(piv.rotation.y) / Math.PI, 0, 1);
    const objCurva = a > 0 ? a * (0.004 + Math.sin(Math.PI * avanceGiro) * 0.082 + extraCurva) : 0;
    flexionar(piv, objCurva, dt, false, objFlexTorsion * a);
  });
}

/* =========================================================================
   RATÓN Y GESTOS
   ========================================================================= */
function ponerRaton(ev) {
  const r = lienzo.getBoundingClientRect();
  raton.x = ev.clientX; raton.y = ev.clientY;
  raton.ndc.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
  raton.ndc.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
  ratonSucio = true;
}
function libroBajoRaton() {
  lanzador.setFromCamera(raton.ndc, camara);
  const h = lanzador.intersectObjects(dianas, false);
  return h.length ? h[0].object.userData.indice : -1;
}
function activoBajoRaton() {
  if (modo !== "detalle" || !libroActivo) return false;
  libroActivo.raiz.updateWorldMatrix(true, true);
  lanzador.setFromCamera(raton.ndc, camara);
  return lanzador.intersectObject(libroActivo.diana, false).length > 0;
}
function paginaBajoRaton() {
  if (modo !== "detalle" || !libroActivo || !hojeando) return null;
  libroActivo.raiz.updateWorldMatrix(true, true);
  lanzador.setFromCamera(raton.ndc, camara);
  const h = lanzador.intersectObjects(libroActivo.gestos, false);
  return h.length ? h[0].object : null;
}
function tapaBajoRaton() {
  if (modo !== "detalle" || !libroActivo || pliegoActual !== 0) return null;
  libroActivo.raiz.updateWorldMatrix(true, true);
  lanzador.setFromCamera(raton.ndc, camara);
  const h = lanzador.intersectObject(libroActivo.tapa, false);
  return h.length ? h[0].object : null;
}
function setSobrevolado(i) {
  if (sobrevolado === i) return;
  sobrevolado = i;
  lienzo.classList.toggle("sobre-lomo", i >= 0);
  if (i >= 0) {
    etiquetaRatonNum.textContent = DATOS[i].generoNombre;
    etiquetaRatonTit.textContent = DATOS[i].titulo;
    etiquetaRaton.setAttribute("aria-hidden", "false");
  } else etiquetaRaton.setAttribute("aria-hidden", "true");
  pedirCuadro();
}
function actualizarSobrevuelo() {
  ratonSucio = false;
  if (modo === "detalle" && libroActivo) {
    setSobrevolado(-1);
    if (hojeando) {
      libroSobrevolado = false;
      lienzo.classList.remove("sobre-libro");
      lienzo.classList.toggle("sobre-pagina",
        arrastre.activo || Boolean(paginaBajoRaton()) || Boolean(tapaBajoRaton()));
    } else {
      libroSobrevolado = Boolean(tapaBajoRaton());
      lienzo.classList.remove("sobre-pagina");
      lienzo.classList.toggle("sobre-libro", libroSobrevolado);
    }
    return;
  }
  libroSobrevolado = false;
  lienzo.classList.remove("sobre-pagina", "sobre-libro");
  setSobrevolado(modo === "estante" ? libroBajoRaton() : -1);
}

function reiniciarArrastre() {
  const id = arrastre.id;
  arrastre.activo = false; arrastre.id = null; arrastre.avance = 0; arrastre.pico = 0;
  arrastre.confirmado = false; arrastre.velocidad = 0; arrastre.sesgoY = 0;
  arrastre.avancePrevio = 0; arrastre.tPrevio = 0; arrastre.sentido = 0; arrastre.tipo = null;
  lienzo.classList.remove("arrastrando");
  controles.enabled = modo === "detalle";
  if (id !== null && lienzo.hasPointerCapture?.(id)) lienzo.releasePointerCapture(id);
}
function impulsoAlSoltar(sentido) {
  if (!libroActivo || sentido === 0) return;
  const orden = sentido > 0 ? pliegoActual : pliegoActual - 1;
  const piv = libroActivo.pivotes[libroActivo.pivotes.length - 1 - orden];
  const f = piv?.userData.flex;
  if (!f) return;
  const rapidez = clamp(Math.abs(arrastre.velocidad) / 5.5, 0.12, 1);
  f.vCurva = clamp(f.vCurva + rapidez * 0.46, -1.8, 1.8);
  f.vTorsion = clamp(f.vTorsion + arrastre.sesgoY * 0.38
    + clamp(arrastre.velocidad / 5.5, -1, 1) * sentido * 0.14, -1.6, 1.6);
}
function resolverArrastre(confirmar = false) {
  if (!arrastre.activo) return false;
  const sentido = arrastre.sentido;
  const cerrar = confirmar && arrastre.tipo === "cerrar-tapa" && arrastre.confirmado;
  const abrir = confirmar && arrastre.tipo === "abrir-tapa" && arrastre.confirmado;
  const pasar = confirmar && arrastre.tipo === "pagina" && arrastre.confirmado && sentido !== 0;
  if (pasar) impulsoAlSoltar(sentido);
  reiniciarArrastre();
  if (cerrar) ponerHojeando(false);
  else if (abrir) ponerHojeando(true);
  else if (pasar) pasarPagina(sentido);
  else pedirCuadro();
  return cerrar || abrir || pasar;
}
const cancelarArrastre = () => resolverArrastre(false);

function reiniciarPulsacion() {
  pulsacion.activa = false; pulsacion.id = null;
  pulsacion.movida = false; pulsacion.permiteClic = false;
}

function onLibroAbajo(ev) {
  if (modo !== "detalle" || hojeando || ev.button !== 0 || ev.isPrimary === false) return;
  ponerRaton(ev);
  pulsacion.permiteClic = false;
  if (!activoBajoRaton()) return;
  pulsacion.activa = true; pulsacion.id = ev.pointerId;
  pulsacion.x0 = ev.clientX; pulsacion.y0 = ev.clientY; pulsacion.movida = false;
}
function onLibroMover(ev) {
  if (!pulsacion.activa || ev.pointerId !== pulsacion.id) return;
  if (Math.hypot(ev.clientX - pulsacion.x0, ev.clientY - pulsacion.y0) > 16) pulsacion.movida = true;
}
function onLibroArriba(ev) {
  if (!pulsacion.activa || ev.pointerId !== pulsacion.id) return;
  pulsacion.permiteClic = ev.type === "pointerup" && !pulsacion.movida;
  pulsacion.activa = false; pulsacion.id = null;
}

function onPaginaAbajo(ev) {
  if (modo !== "detalle" || !libroActivo || ev.button !== 0 || ev.isPrimary === false) return;
  ponerRaton(ev);
  const tapa = tapaBajoRaton();
  const pag = hojeando ? paginaBajoRaton() : null;
  if (!tapa && !pag) return;
  ev.preventDefault();
  ev.stopImmediatePropagation();
  arrastre.activo = true; arrastre.id = ev.pointerId;
  arrastre.x0 = ev.clientX; arrastre.y0 = ev.clientY;
  arrastre.avance = 0; arrastre.pico = 0; arrastre.confirmado = false;
  arrastre.velocidad = 0; arrastre.sesgoY = 0; arrastre.avancePrevio = 0;
  arrastre.tPrevio = ev.timeStamp || performance.now();
  arrastre.sentido = 0;
  arrastre.tipo = tapa ? (hojeando ? "cerrar-tapa" : "abrir-tapa") : "pagina";
  controles.enabled = false;
  lienzo.classList.add("sobre-pagina", "arrastrando");
  lienzo.setPointerCapture?.(ev.pointerId);
  pedirCuadro();
}
function medirArrastre(ev, dy) {
  const t = ev.timeStamp || performance.now();
  const trans = clamp((t - arrastre.tPrevio) / 1000, 0.008, 0.08);
  const vInst = clamp((arrastre.avance - arrastre.avancePrevio) / trans, -8, 8);
  arrastre.velocidad = lerp(arrastre.velocidad, vInst, 0.42);
  arrastre.sesgoY = lerp(arrastre.sesgoY, clamp(dy / 180, -1, 1), 0.36);
  arrastre.avancePrevio = arrastre.avance;
  arrastre.tPrevio = t;
}
function actualizarArrastre(ev) {
  ponerRaton(ev);
  const dx = ev.clientX - arrastre.x0, dy = ev.clientY - arrastre.y0;
  const dist = Math.abs(dx);
  if (arrastre.tipo === "abrir-tapa" || arrastre.tipo === "cerrar-tapa") {
    const abriendo = arrastre.tipo === "abrir-tapa";
    const firmado = abriendo ? -dx : dx;
    const umbral = abriendo ? CONFIRMA_ABRIR : CONFIRMA_CERRAR;
    arrastre.sentido = 0;
    arrastre.avance = (dist >= 3 && dist >= Math.abs(dy) * 0.72)
      ? clamp(Math.max(0, firmado) / 140, 0, 1) : 0;
    arrastre.pico = Math.max(arrastre.pico, arrastre.avance);
    if (arrastre.pico >= umbral) arrastre.confirmado = true;
    medirArrastre(ev, dy);
    return;
  }
  if (dist < 3 || dist < Math.abs(dy) * 0.72) arrastre.avance = 0;
  else {
    if (arrastre.sentido === 0 && dist >= 6) {
      const s = dx < 0 ? 1 : -1;
      const hay = s > 0 ? pliegoActual < PLIEGOS - 1 : pliegoActual > 0;
      arrastre.sentido = hay ? s : 0;
    }
    const firmado = arrastre.sentido > 0 ? -dx : dx;
    arrastre.avance = arrastre.sentido !== 0 ? clamp(Math.max(0, firmado) / 150, 0, 1) : 0;
    arrastre.pico = Math.max(arrastre.pico, arrastre.avance);
    if (arrastre.pico >= CONFIRMA_PAGINA) arrastre.confirmado = true;
  }
  medirArrastre(ev, dy);
}
function onPaginaMover(ev) {
  if (!arrastre.activo || ev.pointerId !== arrastre.id) return;
  ev.preventDefault();
  ev.stopImmediatePropagation();
  actualizarArrastre(ev);
  pedirCuadro();
}
function onPaginaArriba(ev) {
  if (!arrastre.activo || ev.pointerId !== arrastre.id) return;
  if (ev.cancelable) ev.preventDefault();
  ev.stopImmediatePropagation();
  if (ev.type === "pointerup") actualizarArrastre(ev);
  const tipo = arrastre.tipo;
  const recorrido = Math.hypot(ev.clientX - arrastre.x0, ev.clientY - arrastre.y0);
  const clicAbrir = ev.type === "pointerup" && tipo === "abrir-tapa"
    && !arrastre.confirmado && recorrido <= 12;
  if (arrastre.confirmado) resolverArrastre(true);
  else if (clicAbrir) { reiniciarArrastre(); pulsacion.permiteClic = false; ponerHojeando(true); }
  else { if (tipo === "abrir-tapa") pulsacion.permiteClic = false; cancelarArrastre(); }
}
function onPaginaArribaVentana(ev) {
  if (!arrastre.activo || ev.pointerId !== arrastre.id) return;
  if (ev.type === "pointerup") actualizarArrastre(ev);
  resolverArrastre(true);
}

function onRatonMover(ev) {
  ponerRaton(ev);
  etiquetaRaton.style.left = raton.x + "px";
  etiquetaRaton.style.top = raton.y + "px";
  pedirCuadro();
}
function onRatonSalir() {
  raton.ndc.set(3, 3);
  ratonSucio = false;
  libroSobrevolado = false;
  setSobrevolado(-1);
  if (!arrastre.activo) lienzo.classList.remove("sobre-pagina", "sobre-libro");
}
function onClic(ev) {
  if (modo === "detalle" && !hojeando && ev.button === 0) {
    if (!pulsacion.permiteClic) return;
    pulsacion.permiteClic = false;
    ponerRaton(ev);
    if (!activoBajoRaton()) return;
    ev.preventDefault();
    ponerHojeando(true);
    return;
  }
  if (modo !== "estante" || ev.button !== 0) return;
  ponerRaton(ev);
  const i = libroBajoRaton();
  if (i < 0) return;
  ev.preventDefault();
  elegirMarcador(i, lienzo);
  abrirDetalle(lienzo);
}
function onRueda(ev) {
  if (modo !== "estante") return;
  ev.preventDefault();
  const d = Math.abs(ev.deltaX) > Math.abs(ev.deltaY) ? ev.deltaX : ev.deltaY;
  posicionDestino += clamp(d * 0.0022, -0.72, 0.72);
  ruedaQuieta = 0.14;
  pedirCuadro();
}

/* =========================================================================
   ABRIR Y CERRAR
   ========================================================================= */
/* --- interiores a demanda -----------------------------------------------
   Dibujar 8 hojas a triple resolucion cuesta memoria, asi que solo existe el
   del libro abierto. Se dibuja al abrir y se suelta al abrir otro. */
function asegurarInteriores(l) {
  if (!l || !l.interiores || l.interiores.hechas) return;
  const texs = texturasInteriores(l.datos);
  texs.forEach((tex, i) => {
    const m = l.interiores.mats[i];
    if (!m) return;
    m.map = tex;
    m.emissiveMap = tex;      /* el mismo dibujo, o el texto perderia contraste */
    m.needsUpdate = true;
  });
  l.interiores.texturas = texs;
  l.interiores.hechas = true;
  pedirCuadro();
}

function soltarInteriores(l) {
  if (!l || !l.interiores || !l.interiores.hechas) return;
  l.interiores.texturas.forEach((tex) => { try { tex.dispose(); } catch (e) { /* ya suelta */ } });
  l.interiores.texturas = [];
  const papel = texturaPapel();
  l.interiores.mats.forEach((m) => {
    m.map = papel;
    m.emissiveMap = papel;
    m.needsUpdate = true;
  });
  l.interiores.hechas = false;
}

function abrirDetalle(origen = btnAbrir) {
  if (modo !== "estante") return;
  modo = "abriendo";
  tTransicion = 0;
  hojeando = false;
  libroSobrevolado = false;
  pliegoActual = 0;
  reiniciarPulsacion();
  focoDeVuelta = origen === lienzo
    ? (marcadores.children[seleccion] || btnAbrir)
    : (origen instanceof HTMLElement ? origen : btnAbrir);
  libroActivo = libros[seleccion];
  /* solo el libro abierto conserva sus paginas dibujadas */
  libros.forEach((l) => { if (l !== libroActivo) soltarInteriores(l); });
  asegurarInteriores(libroActivo);
  libroActivo.sombra.visible = false;
  rellenarPanel(libroActivo.datos);
  actualizarControlesPagina(false);
  panel.inert = false;
  panel.setAttribute("aria-hidden", "false");
  barraUi.inert = true;
  escena3d.classList.add("modo-detalle", "abriendo");
  etiquetaRaton.setAttribute("aria-hidden", "true");
  setSobrevolado(-1);

  libroActivo.raiz.updateWorldMatrix(true, true);
  libroActivo.raiz.matrixWorld.decompose(aP0, aQ0, aE0);
  aCamP0.copy(camara.position);
  aCamO0.copy(objTransicion);
  aTarima0.copy(tarima.position);
  aMovP0.copy(libroActivo.mov.position);
  aMovQ0.copy(libroActivo.mov.quaternion);
  aDesplX0 = desplazeActualX;
  escena.add(libroActivo.raiz);
  libroActivo.raiz.position.copy(aP0);
  libroActivo.raiz.quaternion.copy(aQ0);
  libroActivo.raiz.scale.copy(aE0);
  aplicarDesplazamiento();
  controles.enabled = false;
  avisos.textContent = "Abriendo " + libroActivo.datos.titulo + ".";
  if (movimientoReducido) terminarApertura();
  pedirCuadro();
}
function poseApertura(p) {
  const k = masSuave(clamp(p, 0, 1));
  const kTarima = masSuave(clamp(p / 0.68, 0, 1));
  escalaDetalle.setScalar(factorEscala());
  tarima.position.lerpVectors(aTarima0, tarimaDetalle, kTarima);
  libroActivo.raiz.position.lerpVectors(aP0, posDetalle, k);
  libroActivo.raiz.quaternion.slerpQuaternions(aQ0, giroDetalle, k);
  libroActivo.raiz.scale.lerpVectors(aE0, escalaDetalle, k);
  libroActivo.mov.position.lerpVectors(aMovP0, movReposoPos, k);
  libroActivo.mov.quaternion.slerpQuaternions(aMovQ0, movReposoGiro, k);
  camara.position.lerpVectors(aCamP0, camDetalle, k);
  objTransicion.lerpVectors(aCamO0, objDetalle, k);
  desplazeActualX = lerp(aDesplX0, desplazeDetalleX, k);
  aplicarDesplazamiento();
  camara.lookAt(objTransicion);
}
function terminarApertura() {
  if (!libroActivo) return;
  poseApertura(1);
  modo = "detalle";
  tTransicion = 1;
  controles.target.copy(objDetalle);
  controles.enabled = true;
  controles.enableDamping = !movimientoReducido;
  controles.update();
  actualizarControlesPagina(false);
  escena3d.classList.remove("abriendo");
  btnCerrarPanel.focus({ preventScroll: true });
}

function cerrarDetalle() {
  if (modo !== "detalle") return;
  cancelarArrastre();
  reiniciarPulsacion();
  modo = "cerrando";
  tTransicion = 0;
  hojeando = false;
  libroSobrevolado = false;
  pliegoActual = 0;
  lienzo.classList.remove("sobre-pagina", "sobre-libro");
  actualizarControlesPagina(false);
  controles.enabled = false;
  cP0.copy(libroActivo.raiz.position);
  cQ0.copy(libroActivo.raiz.quaternion);
  cE0.copy(libroActivo.raiz.scale);
  cMovP0.copy(libroActivo.mov.position);
  cMovQ0.copy(libroActivo.mov.quaternion);
  cCamP0.copy(camara.position);
  cCamO0.copy(controles.target);
  cTarima0.copy(tarima.position);
  cDesplX0 = desplazeActualX;
  objTransicion.copy(cCamO0);
  escena3d.classList.remove("abriendo");
  alinearEstante();
  cP1.set(0, TAPA_ARRIBA + libroActivo.base.h * 0.5 + 0.15, 0.37);
  cQ1.identity();
  libros.forEach((l, i) => { if (l !== libroActivo && l.raiz.parent === tarima) colocarEnBalda(l, i); });
  escena3d.classList.remove("modo-detalle");
  panel.setAttribute("aria-hidden", "true");
  panel.inert = true;
  avisos.textContent = "Devolviendo " + libroActivo.datos.titulo + " a la estantería.";
  if (movimientoReducido) terminarCierre();
  pedirCuadro();
}
function poseCierre(p) {
  const k = masSuave(clamp(p, 0, 1));
  const kTarima = masSuave(clamp((p - 0.24) / 0.76, 0, 1));
  tarima.position.lerpVectors(cTarima0, tarimaReposo, kTarima);
  libroActivo.raiz.position.lerpVectors(cP0, cP1, k);
  libroActivo.raiz.quaternion.slerpQuaternions(cQ0, cQ1, k);
  libroActivo.raiz.scale.lerpVectors(cE0, cE1, k);
  libroActivo.mov.position.lerpVectors(cMovP0, movReposoPos, k);
  libroActivo.mov.quaternion.slerpQuaternions(cMovQ0, movReposoGiro, k);
  camara.position.lerpVectors(cCamP0, camEstante, k);
  objTransicion.lerpVectors(cCamO0, objEstante, k);
  desplazeActualX = lerp(cDesplX0, 0, k);
  aplicarDesplazamiento();
  camara.lookAt(objTransicion);
}
function terminarCierre() {
  if (!libroActivo) return;
  poseCierre(1);
  tarima.attach(libroActivo.raiz);
  colocarEnBalda(libroActivo, seleccion);
  libroActivo.sombra.visible = true;
  controles.target.copy(objEstante);
  barraUi.inert = false;
  modo = "estante";
  tTransicion = 0;
  avisos.textContent = DATOS[seleccion].titulo + " de vuelta en la estantería.";
  libroActivo = null;
  requestAnimationFrame(() => focoDeVuelta?.focus?.({ preventScroll: true }));
}
function resetVista() {
  if (modo !== "detalle") return;
  camara.position.copy(camDetalle);
  controles.target.copy(objDetalle);
  controles.update();
  pedirCuadro();
}

/* =========================================================================
   BUCLE
   ========================================================================= */
function actualizarEstante(dt, t) {
  if (modo === "estante") {
    posicion = movimientoReducido ? posicionDestino : damp(posicion, posicionDestino, 9.5, dt);
    if (Math.abs(posicion - posicionDestino) < 0.0005) posicion = posicionDestino;
    if (ruedaQuieta > 0) {
      ruedaQuieta -= dt;
      if (ruedaQuieta <= 0) posicionDestino = Math.round(posicionDestino);
    }
    const cerca = mod(Math.round(posicion), DATOS.length);
    if (cerca !== seleccion) actualizarSeleccion(cerca, false);
  }

  libros.forEach((l, i) => {
    if (l.raiz.parent !== tarima) return;
    let desf = i - posicion;
    desf -= Math.round(desf / DATOS.length) * DATOS.length;
    const dist = Math.abs(desf);
    const salto = l.desfasePrevio !== null && Math.abs(desf - l.desfasePrevio) > DATOS.length * 0.5;
    const foco = 1 - clamp(dist, 0, 1);
    const vel = movimientoReducido ? 1000 : 12;
    const objX = desf * SEPARACION;
    if (salto) { l.raiz.position.x = objX; l.opacidad = 0; }
    l.desfasePrevio = desf;

    l.raiz.position.x = damp(l.raiz.position.x, objX, vel, dt);
    l.raiz.position.y = damp(l.raiz.position.y, TAPA_ARRIBA + l.base.h * 0.5 + foco * 0.15, vel, dt);
    l.raiz.position.z = damp(l.raiz.position.z, 0.13 + foco * 0.24 - Math.min(dist, 2.8) * 0.07, vel, dt);
    l.raiz.rotation.y = damp(l.raiz.rotation.y, -desf * 0.105, vel, dt);
    l.raiz.rotation.z = damp(l.raiz.rotation.z, -desf * 0.018, vel, dt);
    l.raiz.scale.setScalar(damp(l.raiz.scale.x, 1 + foco * 0.09, vel, dt));

    const objOp = 1 - suave(clamp((dist - 2.55) / 0.7, 0, 1));
    l.opacidad = movimientoReducido ? objOp : damp(l.opacidad, objOp, 18, dt);
    l.fundibles.forEach((m) => { m.opacity = l.opacidad; });
    l.sombra.visible = true;
    l.sombra.material.opacity = l.opacidad * 0.24;
    l.diana.visible = l.opacidad > 0.12;

    const encima = sobrevolado === i && modo === "estante";
    const anticipo = encima && !movimientoReducido;
    l.pivTapa.rotation.y = damp(l.pivTapa.rotation.y, anticipo ? -0.085 : 0,
      movimientoReducido ? 1000 : 13, dt);
    l.pivotes.forEach((p) => {
      p.rotation.y = damp(p.rotation.y, 0, movimientoReducido ? 1000 : 13, dt);
      p.rotation.z = damp(p.rotation.z, 0, movimientoReducido ? 1000 : 13, dt);
      flexionar(p, 0, dt);
    });

    const vaiven = movimientoReducido ? 0 : Math.sin(t * 0.72 + i * 0.8) * 0.012 * foco;
    l.mov.position.y = damp(l.mov.position.y, vaiven + (anticipo ? 0.035 : 0), 9, dt);
    l.mov.rotation.x = damp(l.mov.rotation.x, anticipo ? raton.ndc.y * 0.035 : 0, 10, dt);
    l.mov.rotation.y = damp(l.mov.rotation.y, anticipo ? -raton.ndc.x * 0.035 : 0, 10, dt);
  });
}

function actualizarTransicion(dt) {
  if (modo === "abriendo") {
    tTransicion = Math.min(1, tTransicion + dt / DUR_DETALLE);
    poseApertura(tTransicion);
    animarLibroAbierto(libroActivo, dt, 0);
    if (tTransicion >= 1) terminarApertura();
  } else if (modo === "cerrando") {
    tTransicion = Math.min(1, tTransicion + dt / DUR_ESTANTE);
    poseCierre(tTransicion);
    animarLibroAbierto(libroActivo, dt, 0);
    if (tTransicion >= 1) terminarCierre();
  } else if (modo === "estante") {
    tarima.position.y = damp(tarima.position.y, 0, 10, dt);
    tarima.position.z = damp(tarima.position.z, 0, 10, dt);
    camara.position.x = damp(camara.position.x, camEstante.x, 8, dt);
    camara.position.y = damp(camara.position.y, camEstante.y, 8, dt);
    camara.position.z = damp(camara.position.z, camEstante.z, 8, dt);
    objTransicion.copy(objEstante);
    desplazeActualX = 0;
    aplicarDesplazamiento();
    camara.lookAt(objEstante);
  }
}

function aperturaActual() {
  if (arrastre.activo && arrastre.tipo === "abrir-tapa") return suave(arrastre.avance);
  if (!hojeando) return 0;
  if (arrastre.activo && arrastre.tipo === "cerrar-tapa") return 1 - suave(arrastre.avance);
  return 1;
}

function pedirCuadro() {
  if (!raf && !suspendido) raf = requestAnimationFrame(cuadro);
}

function cuadro(ahora) {
  raf = 0;
  const dt = Math.min((ahora - tUltimo) / 1000, 0.05);
  const t = ahora / 1000;
  tUltimo = ahora;

  if (ratonSucio) actualizarSobrevuelo();
  actualizarEstante(dt, t);
  actualizarTransicion(dt);
  if (!movimientoReducido) {
    const polvo = escena.getObjectByName("polvo");
    if (polvo) { polvo.rotation.y = t * 0.012; polvo.position.y = Math.sin(t * 0.17) * 0.025; }
  }
  const temaMueve = actualizarTema(dt);

  if (modo === "detalle") {
    if (arrastre.activo) arrastre.velocidad = damp(arrastre.velocidad, 0, 9, dt);
    controles.update();
    animarLibroAbierto(libroActivo, dt, aperturaActual());
  }

  renderer.render(escena, camara);

  const estanteMueve = Math.abs(posicion - posicionDestino) > 0.0005 || ruedaQuieta > 0;
  if ((!movimientoReducido || modo === "abriendo" || modo === "cerrando"
       || estanteMueve || temaMueve) && !suspendido) pedirCuadro();
}

function redimensionar() {
  anchoVista = window.innerWidth;
  altoVista = window.innerHeight;
  ajustesResponsive();
  renderer.setSize(anchoVista, altoVista, false);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, anchoVista < 820 ? 1.5 : 2));
  camara.aspect = anchoVista / altoVista;
  camara.updateProjectionMatrix();
  if (modo === "estante") {
    camara.position.copy(camEstante);
    objTransicion.copy(objEstante);
    desplazeActualX = 0;
    aplicarDesplazamiento();
    camara.lookAt(objEstante);
  } else if (modo === "detalle" && libroActivo) {
    libroActivo.raiz.position.copy(posDetalle);
    libroActivo.raiz.scale.setScalar(factorEscala());
    objTransicion.copy(objDetalle);
    desplazeActualX = desplazeDetalleX;
    aplicarDesplazamiento();
    resetVista();
  }
  pedirCuadro();
}

function onTecla(ev) {
  if (ev.key === "Escape" && modo === "detalle") { ev.preventDefault(); cerrarDetalle(); return; }
  if (modo === "detalle" && !ev.metaKey && !ev.ctrlKey && !ev.altKey
      && (ev.key === "ArrowLeft" || ev.key === "ArrowRight")) {
    ev.preventDefault();
    pasarPagina(ev.key === "ArrowLeft" ? -1 : 1);
    return;
  }
  if (modo !== "estante" || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (ev.key === "ArrowLeft") { ev.preventDefault(); navegar(-1, document.activeElement); }
  else if (ev.key === "ArrowRight") { ev.preventDefault(); navegar(1, document.activeElement); }
  else if ((ev.key === "Enter" || ev.key === " ") && document.activeElement === btnAbrir) {
    ev.preventDefault();
    abrirDetalle(btnAbrir);
  }
}

function onVisibilidad() {
  suspendido = document.hidden;
  /* Si la pestaña estaba oculta, el cuadro pedido nunca llegó a dispararse pero
     `raf` quedó con su id: sin soltarlo, pedirCuadro() no volvería a arrancar
     jamás y la escena se quedaría congelada al volver. */
  if (raf) { cancelAnimationFrame(raf); raf = 0; }
  if (!suspendido) { tUltimo = performance.now(); pedirCuadro(); }
  else { resolverArrastre(true); reiniciarPulsacion(); }
}

function mostrarRespaldo(msg) {
  cargando.hidden = true;
  escena3d.classList.remove("listo");
  respaldo.hidden = false;
  const p = respaldo.querySelector("[data-motivo]");
  if (p) p.textContent = msg;
}

/* =========================================================================
   ARRANQUE
   ========================================================================= */
async function iniciar() {
  if (!DATOS.length) { mostrarRespaldo("Todavía no hay libros que mostrar."); return; }
  /* Hay que esperar a las TRES familias, no solo a Fraunces: las paginas de
     dentro se dibujan con Newsreader e Inter, y el canvas no espera a nadie.
     Si no han llegado, dibuja en Georgia/Arial y el libro sale con otra letra
     sin dar el menor aviso. */
  try {
    await Promise.all([
      document.fonts.load('600 60px "Fraunces"'),
      document.fonts.load('400 60px "Fraunces"'),
      document.fonts.load('400 21px "Newsreader"'),
      document.fonts.load('500 22px "Newsreader"'),
      document.fonts.load('600 12px "Inter"'),
      document.fonts.load('300 21px "Newsreader"'),
      document.fonts.load('500 16px "Inter"'),
      document.fonts.load('400 16px "Inter"')
    ]);
  } catch (e) { /* la fuente del sistema vale */ }

  try {
    renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true, alpha: true,
                                         powerPreference: "high-performance" });
  } catch (e) {
    mostrarRespaldo("Tu navegador no puede mostrar gráficos 3D. Abajo tienes la estantería completa.");
    return;
  }

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  /* ACESFilmic es el mapeo de tonos del cine: comprime las luces y DESATURA
     todo lo que se acerca al blanco. En una pelicula queda bien; aqui hacia que
     las portadas se vieran lavadas y palidas, sin el color que tienen de verdad,
     y que el papel blanco de las paginas nunca llegara a ser blanco.
     El "Neutral" (PBR Neutral de Khronos) esta hecho justo para lo contrario:
     respeta el color del material. La exposicion baja de 0.9 a 0.8 porque
     Neutral entrega mas luz que ACES y si no, todo saldria mas claro todavia. */
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 0.8;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x000000, 0);

  escena = new THREE.Scene();
  escena.fog = new THREE.FogExp2(0xe9dfcb, 0.027);
  const pmrem = new THREE.PMREMGenerator(renderer);
  entorno = pmrem.fromScene(new RoomEnvironment(), 0.04);
  escena.environment = entorno.texture;
  escena.environmentIntensity = 0.72;
  pmrem.dispose();

  camara = new THREE.PerspectiveCamera(32, 1, 0.1, 60);
  tarima = new THREE.Group();
  tarima.name = "tarima";
  escena.add(tarima);

  ajustesResponsive();
  camara.position.copy(camEstante);
  camara.lookAt(objEstante);

  controles = new OrbitControls(camara, lienzo);
  controles.enabled = false;
  controles.enableDamping = !movimientoReducido;
  controles.dampingFactor = 0.075;
  /* El arrastre con boton derecho movia la camara de sitio (pan) y dejaba el
     libro descuadrado o fuera de pantalla, sin forma de volver. Girar y acercar
     si tienen sentido; desplazar, no. */
  controles.enablePan = false;
  controles.screenSpacePanning = false;
  controles.minDistance = 2.8;
  controles.maxDistance = 7.2;
  controles.minPolarAngle = Math.PI * 0.24;
  controles.maxPolarAngle = Math.PI * 0.76;
  controles.target.copy(objEstante);
  controles.addEventListener("change", pedirCuadro);

  RectAreaLightUniformsLib.init();
  montarSala();
  montarLuces();
  montarPolvo();
  construirMarcadores();

  libros = DATOS.map((libro, i) => {
    const l = crearLibro(libro, i);
    tarima.add(l.raiz);
    return l;
  });

  actualizarSeleccion(0, true);
  redimensionar();

  lienzo.addEventListener("pointermove", onRatonMover);
  lienzo.addEventListener("pointerleave", onRatonSalir);
  lienzo.addEventListener("click", onClic);
  ["pointerdown", "pointermove", "pointerup", "pointercancel", "lostpointercapture"]
    .forEach((t, i) => {
      const libroFns = [onLibroAbajo, onLibroMover, onLibroArriba, onLibroArriba, onLibroArriba];
      const pagFns = [onPaginaAbajo, onPaginaMover, onPaginaArriba, onPaginaArriba, onPaginaArriba];
      lienzo.addEventListener(t, libroFns[i], { capture: true });
      lienzo.addEventListener(t, pagFns[i], { capture: true });
    });
  window.addEventListener("pointerup", onPaginaArribaVentana);
  window.addEventListener("pointercancel", onPaginaArribaVentana);
  escena3d.addEventListener("wheel", onRueda, { passive: false });
  lienzo.addEventListener("webglcontextlost", (ev) => {
    ev.preventDefault();
    suspendido = true;
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    mostrarRespaldo("La vista 3D se ha detenido. Recarga la página para volver a intentarlo.");
  });
  window.addEventListener("resize", redimensionar);
  window.addEventListener("keydown", onTecla);
  window.addEventListener("blur", () => { resolverArrastre(true); reiniciarPulsacion(); });
  document.addEventListener("visibilitychange", onVisibilidad);
  consultaMovimiento.addEventListener("change", (ev) => {
    cancelarArrastre();
    reiniciarPulsacion();
    movimientoReducido = ev.matches;
    controles.enableDamping = !movimientoReducido;
    if (movimientoReducido) posicion = posicionDestino;
    pedirCuadro();
  });

  btnAnterior.addEventListener("click", () => navegar(-1, btnAnterior));
  btnSiguiente.addEventListener("click", () => navegar(1, btnSiguiente));
  btnAbrir.addEventListener("click", () => abrirDetalle(btnAbrir));
  btnCerrarPanel.addEventListener("click", cerrarDetalle);
  btnHojear.addEventListener("click", () => ponerHojeando(!hojeando));
  btnPagAnterior.addEventListener("click", () => pasarPagina(-1));
  btnPagSiguiente.addEventListener("click", () => pasarPagina(1));
  btnResetVista.addEventListener("click", resetVista);

  renderer.render(escena, camara);
  cargando.hidden = true;
  escena3d.classList.add("listo");
  pedirCuadro();
}

iniciar().catch((err) => {
  console.error("[estantería 3D]", err);
  mostrarRespaldo("No se ha podido montar la estantería en 3D. Abajo la tienes completa.");
});
