# Contador — Design System

Sistema de diseño para **Contador** (`Accountant`), la app de intake contable del repositorio [`julianjab/accountant`](https://github.com/julianjab/accountant) (rama `main`, workspace `apps/web` + `apps/server`).

## Qué es el producto

Un contador conecta su cuenta de Google (Drive, solo lectura) y cada cliente tiene una carpeta vigilada. Cuando llega un documento, un webhook de Drive dispara el pipeline del servidor: se clasifica contra los **tipos de documento** configurados, se le corre la extracción OCR de ese tipo con Claude, y los campos resultantes se guardan como `ExtractedData`. El contador revisa y los datos aprobados se acumulan en una hoja de cálculo por cliente.

Estructura del dominio (fuente: `apps/server/src/server/domain/entities/`):

- `Client` — `name`, `tax_id`, `email`
- `Document` — pertenece a un cliente; `status` ∈ `pending | classifying | running_ocr | processed | failed`
- `DocumentType` — config: `extraction_prompt` + `extraction_schema` propuestos por IA a partir de un documento de muestra
- `ExtractedData` — `fields` + `confidence`

**Estado real del front hoy:** `apps/web` es la plantilla de Nuxt UI con un `UHeader`, el botón de Google y una tabla de clientes (`app/pages/clients/index.vue`). Todo lo demás de este sistema es propuesta construida sobre entidades que ya existen en el servidor. La pantalla de hojas de cálculo no tiene contraparte en el código todavía.

## Fuentes usadas

- Repo GitHub `julianjab/accountant@main` — `apps/web/app/**`, `apps/server/src/server/**`, `apps/web/i18n/locales/es.json`
- No se entregaron Figma, logos ni binarios de fuentes.

## Content fundamentals

- **Idioma: español.** El locale por defecto en `nuxt.config.ts` es `es`; las cadenas salen de `i18n/locales/es.json` y se usan verbatim cuando existen ("Registrar cliente", "Aún no hay clientes registrados", "Cerrar sesión").
- **Tono:** enunciativo y sin adornos. Se describe lo que el sistema hizo, no lo que el usuario debería sentir. "Documentos que llegan por Drive, agrupados por cliente." Nada de "¡Listo!", ni exclamaciones, ni segunda persona imperativa salvo en botones.
- **Botones:** verbo en infinitivo — "Registrar cliente", "Definir tipo", "Exportar a hoja de cálculo", "Aprobar y enviar a hoja".
- **Mayúsculas:** sentence case en títulos y botones. Sólo las etiquetas de sección van en versalitas (uppercase + tracking 0.08em).
- **Términos técnicos sin traducir:** `OCR`, `Drive`, `extraction_prompt`, `extraction_schema`, y las claves de campos (`saldo_final`) se muestran tal cual, en monoespaciada. No se traducen ni se "humanizan".
- **Cifras:** formato colombiano — `$ 15.607.755`, NIT `900.412.883-1`, fechas ISO `2026-03-18` en tablas y `18 mar 09:11:42` en trazas.
- **Errores:** describen la causa, no culpan. "No se otorgaron permisos de lectura sobre Google Drive", "Could not identify the document type" → "Sin identificar".
- **Sin emoji.** Nunca.

## Visual foundations

- **Papel y tinta.** Fondo de app `#F7F7F5` (papel cálido), tarjetas blancas, texto `#0F1A14` (tinta verdosa, no negro). Los grises tienen todos un sesgo verde: `#6B7770`, `#8A948C`. Nunca gris puro.
- **Verde de marca** exactamente el de `app/assets/css/main.css` (Nuxt green). `green-600 #00A155` es la acción; `green-500` el hover; `green-400 #00DC82` sólo sobre tinta oscura. El verde es escaso: un botón sólido por vista, el ítem de navegación activo, y los estados "procesado".
- **Superficie profunda `#0C1512`** para dos cosas y nada más: la navegación y todo lo que genera la IA (propuesta de prompt/esquema, tipos configurados). Es la señal de "esto lo escribió el modelo, revísalo".
- **Tipografía:** Public Sans para todo el texto; JetBrains Mono para lo que es un dato y no una frase — NIT, importes, horas, migas de pan, claves de esquema, cifras de tarjeta. La mono es lo que hace que la app se lea como una herramienta contable.
- **Fondos:** planos. Cero gradientes, cero imágenes decorativas, cero texturas salvo la trama diagonal de `--pattern-placeholder`, que marca dónde iría un documento real.
- **Bordes:** hairline de 1px en `#E4E4DF`; separadores de fila más claros (`#F1F1EC`). El borde es el recurso de separación por defecto, no la sombra.
- **Sombras:** prácticamente ausentes. `--shadow-raised` (0 1px 3px al 6%) sólo si algo debe flotar; `--shadow-overlay` para diálogos. Las tarjetas de la app no llevan sombra.
- **Radios:** 12px en tarjetas y contenedores, 11px en tarjetas de cifra, 8px en botones y campos, 5px en etiquetas mono, 3px en la miniatura de archivo, pastilla en estados y filtros.
- **Hover:** filas y celdas se tiñen a `#FAFAF8`; sobre superficie profunda, blanco al 7%. Botones sólidos aclaran (600 → 500); los de contorno cambian borde y texto a verde. Nada se mueve ni escala.
- **Press / focus:** sin desplazamiento. Foco con anillo verde al 25% (`--focus-ring`).
- **Animación:** transiciones de 120ms sobre color y borde. No hay entradas, rebotes ni parallax. El único movimiento legítimo sería el avance de un estado del pipeline.
- **Transparencia y blur:** sólo dentro de la superficie profunda (blanco al 6–14%). Sin blur de fondo en ningún lado.
- **Layout:** barra lateral fija de 238px, topbar de 62px con miga de pan a la izquierda y acción principal a la derecha, contenido con gutter de 30px y ancho máximo 1180px. Las tablas van a sangre dentro de su tarjeta.
- **Densidad:** filas compactas de 9px por defecto — el contador escanea decenas de documentos. 14px es la variante cómoda.
- **Agrupación:** los documentos siempre se muestran bajo su cliente. Las listas planas cronológicas están descartadas a propósito.
- **Confianza:** todo campo extraído muestra su confianza (barra de 34px + valor). Verde sobre 0.90, ámbar debajo, y el valor se atenúa a ámbar para que el ojo caiga ahí primero.

## Iconography

No hay set de iconos en el repositorio. `apps/web/package.json` declara `@iconify-json/lucide` y `@iconify-json/simple-icons`, así que **Lucide es el set oficial del proyecto**, pero los binarios no están versionados y ninguna vista los usa todavía.

En este sistema, los pocos iconos necesarios se resuelven con glifos unicode (`◧ ◍ ⚙ ▦ ⌕ ←`) como marcador honesto. **No se dibujaron SVGs propios.** Al implementar en producción, sustituir por Lucide (`inbox`, `users`, `settings`, `table`, `search`, `arrow-left`) con stroke 1.5–2px. No se usa emoji. Tampoco hay logo: la marca se representa como el cuadro verde con la letra "C" y el nombre en Public Sans 700 — **no existe un logotipo real y no se inventó uno**.

## Índice

- `styles.css` — punto de entrada; sólo `@import`s
- `tokens/` — `fonts.css`, `colors.css`, `typography.css`, `spacing.css`, `surfaces.css`
- `guidelines/` — 12 fichas de fundamentos (color, tipografía, espacio, superficies, confianza, marcador de documento)
- `components/core/` — `Button`, `StatusBadge`, `Tag`, `Card`, `StatCard`
- `components/data/` — `DocumentRow`, `ClientGroupHeader`, `FieldRow`
- `components/navigation/` — `SidebarNavItem`, `FilterChip`
- `ui_kits/contador/` — app navegable: bandeja, ficha de cliente, revisión de documento, hojas de cálculo
- `Contador.dc.html` (raíz) — el prototipo original del que salió este sistema
- `github.md` — asociación con el repositorio de origen

### Intentional additions

El repositorio no define una librería de componentes propia (usa Nuxt UI sin envolver). Los componentes de aquí son la destilación de las pantallas propuestas, no una recreación de un inventario existente:

- `StatusBadge`, `DocumentRow`, `ClientGroupHeader`, `FieldRow` — necesarios para el pipeline de documentos, que no tiene UI en el repo.
- `Button`, `Card`, `Tag` — equivalentes propios de `UButton`, `UCard`, `UBadge` de Nuxt UI, con los valores de este sistema.

### Substituciones a confirmar

- **Fuentes:** no se entregaron binarios. Public Sans (la declarada en `main.css`) y JetBrains Mono se cargan desde Google Fonts.
- **Iconos:** glifos unicode en lugar de Lucide, que es lo declarado en `package.json`.
