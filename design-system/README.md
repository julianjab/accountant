# Handoff: Contador — intake de documentos por cliente

## Overview

Diseño de las pantallas que hoy no existen en `apps/web`: bandeja de entrada de documentos agrupada por cliente, ficha de cliente, revisión de datos extraídos por OCR, y hojas de cálculo por cliente. Se apoya en entidades que ya existen en `apps/server` (`Client`, `Document`, `DocumentType`, `ExtractedData`) y en el pipeline de `process_uploaded_document.py`.

Repositorio destino: `julianjab/accountant`, rama `main`, workspace `apps/web` (Nuxt 4 + Nuxt UI 4 + Tailwind 4 + `@nuxtjs/i18n`, locale por defecto `es`).

## About the Design Files

Los archivos de `design/` son **referencias de diseño escritas en HTML/JSX** — prototipos que muestran aspecto y comportamiento previstos, **no código para copiar a producción**. El JSX está escrito con estilos inline y React sin bundler sólo para poder verse en el navegador.

La tarea es **recrear estos diseños en el entorno existente del repo**: componentes `.vue` de Nuxt, envolviendo los componentes de Nuxt UI (`UButton`, `UCard`, `UBadge`, `UTable`) y usando clases de Tailwind 4 con los tokens declarados en `apps/web/app/assets/css/main.css`. No portar los estilos inline tal cual.

## Fidelity

**Alta fidelidad.** Colores, tipografía, espaciado y estados son definitivos; los valores numéricos de esta guía son los que hay que reproducir. Los datos mostrados son ficticios.

Dos excepciones explícitas:
- **Iconos**: los prototipos usan glifos unicode (`◧ ◍ ⚙ ▦ ⌕`) como marcador. Implementar con **Lucide** (`@iconify-json/lucide`, ya en `package.json`): `inbox`, `users`, `settings`, `table`, `search`, `arrow-left`. Stroke 1.5–2px, 16px en navegación.
- **Vista previa del documento**: en el prototipo es una trama diagonal. En producción va el visor real de Drive (`webViewLink` en iframe o render de PDF).

## Screens / Views

Ancho de diseño 1440×900. Todas las vistas comparten el shell: barra lateral 238px + topbar 62px + área de contenido con scroll.

### 1. Shell (`Sidebar` + `Topbar`)

- **Barra lateral**: 238px fijos, `#0C1512`, padding `22px 14px 16px`, columna flex.
  - Marca: cuadro 26×26 `border-radius:8px`, fondo `#00DC82`, letra "C" 13px/800 en `#052E16`; a 10px, el nombre "Contador" 15px/700, `letter-spacing:-0.01em`, color `#E6EDE9`. **No hay logotipo real**: si existe uno, sustituir.
  - Ítems de navegación: `9px 10px`, `border-radius:8px`, 13.5px/500, color `rgba(230,237,233,.72)`; icono 16px a la izquierda, conteo a la derecha en JetBrains Mono 11.5px con opacidad .55. Activo: fondo `rgba(0,220,130,.12)`, texto `#00DC82`. Hover: fondo `rgba(255,255,255,.07)`. Gap vertical 2px.
  - Ítems: Bandeja, Clientes, Tipos de documento, Hojas de cálculo.
  - Pie: borde superior `rgba(255,255,255,.09)`, etiqueta "SESIÓN DE GOOGLE" (11.5px, uppercase, tracking .08em, `rgba(230,237,233,.4)`), avatar circular 26px, correo 12.5px, "Drive · solo lectura" 11px `rgba(230,237,233,.45)`, y botón "Cerrar sesión" a ancho completo con borde `rgba(255,255,255,.12)`. Reutiliza el estado de `useGoogleAuth()` y las claves `auth.signedInAs` / `auth.signOut`.
- **Topbar**: 62px, fondo blanco, borde inferior `#E4E4DF`, padding lateral 30px.
  - Miga de pan a la izquierda en JetBrains Mono 12px `#6B7770`, minúsculas: `inicio / clientes / Ferretería El Tornillo`.
  - Buscador (no funcional en el mock): 270px, fondo `#F2F2EE`, borde `#E4E4DF`, radio 8px, padding `6px 11px`, placeholder 12.5px `#98A29B`, atajo `⌘K` en mono 10px dentro de una cajita con borde `#DEDED8`, radio 4px.
  - Acción principal a la derecha: botón sólido "Registrar cliente".

### 2. Bandeja de entrada (`QueueScreen`) — vista por defecto

Padding `30px 30px 44px`, ancho máximo 1180px.

- **Encabezado**: h1 27px/700 `letter-spacing:-0.02em` "Bandeja de entrada"; a 14px, alineado a la línea base inferior (+5px), la bajada 13px `#6B7770`: "Documentos que llegan por Drive, agrupados por cliente."
- **Cuatro tarjetas de cifra**: grid 4 columnas, gap 12px, margen inferior 26px. Cada una: fondo blanco, borde `#E4E4DF`, radio 11px, padding `15px 16px`. Etiqueta 11.5px uppercase tracking .08em `#8A948C`; cifra JetBrains Mono 30px/600 `letter-spacing:-0.03em`; nota 12px `#8A948C` alineada a la línea base. Colores de cifra: por defecto `#0F1A14`, "Procesados hoy" `#00A155`, "Fallidos" `#B03A2B`.
  - Contenido: Sin procesar / Procesados hoy / Fallidos / Tiempo medio.
- **Tabla agrupada**: tarjeta blanca, borde `#E4E4DF`, radio 12px, `overflow:hidden`.
  - Barra de filtros: padding `12px 16px`, borde inferior `#EDEDE8`, chips en fila con gap 8px. Chip: `5px 11px`, radio pastilla, 12.5px/500, borde `#DEDED8` sobre blanco; activo invierte a fondo `#0C1512`, texto blanco. Orden: Todos, Pendiente, Clasificando, OCR, Procesado, Fallido. A la derecha, conteo 12px `#8A948C`.
  - **Cabecera de grupo (cliente)**: fondo `#FAFAF8`, borde inferior `#EDEDE8`, padding `10px 16px`. Avatar 22×22 radio 5px con iniciales 10px/600 (paleta por cliente, ver Design Tokens); nombre 13px/600 como botón que navega a la ficha (hover `#00A155`); a la derecha el conteo en mono 11.5px `#98A29B`.
  - **Fila de documento**: grid `minmax(0,1.9fr) minmax(0,1.1fr) auto 90px`, padding `9px 16px 9px 48px` (sangrado bajo el grupo), borde inferior `#F1F1EC`, hover `#FAFAF8`, cursor pointer.
    - Miniatura de archivo: 22×26, borde `#DEDED8`, radio 3px, fondo `#F6F6F2`, extensión en mono 8px/600 `#8A948C`.
    - Nombre 13.5px/500 con elipsis; tipo 13px `#6B7770` con elipsis; estado (badge); hora en mono 12px `#8A948C` alineada a la derecha.
  - No hay fila de cabecera de columnas: el grupo de cliente hace de separador.

### 3. Ficha de cliente (`ClientScreen`)

Padding `30px 30px 44px`, máximo 1180px.

- **Encabezado**: avatar 52×52 radio 13px, fondo `#0C1512`, iniciales 18px/600 `#00DC82`. A 16px: h1 26px/700 tracking -0.02em; debajo, fila de metadatos a 16px de gap, 13px `#6B7770` — NIT en JetBrains Mono, correo (o "sin correo"), y "Carpeta Drive · Clientes/{nombre}" con el nombre como enlace. A la derecha, botón de contorno "Exportar a hoja de cálculo".
- **Cuerpo**: grid `1fr 296px`, gap 20px, `align-items:start`.
  - Izquierda: tarjeta con pestañas (Documentos / Datos extraídos / Hojas de cálculo) — pestaña activa 13px/600 con subrayado 2px `#00A155`, inactivas `#8A948C`. Debajo, filas de documento en **layout de dos líneas** (la columna es estrecha): miniatura, nombre 13.5px/500, segunda línea "tipo · hora" 12px `#8A948C`, badge de estado a la derecha.
  - Derecha, dos tarjetas apiladas con gap 14px:
    - "Resumen del mes": etiqueta uppercase; filas etiqueta/valor separadas por `#F3F3EE`, valor en mono 13px/500.
    - Panel profundo `#0C1512`, radio 12px: "Tipos configurados", etiquetas verdes `rgba(0,220,130,.13)` sobre texto `#75EDAE`, y botón de ancho completo con borde `rgba(255,255,255,.14)` → "Configurar extracción".

### 4. Revisión de documento (`DocumentScreen`)

Padding `22px 30px 40px`.

- **Barra de acción**: botón de contorno "← Volver", nombre del archivo 14px/600, badge de estado, y a la derecha el botón sólido "Aprobar y enviar a hoja".
- **Cuerpo**: grid `1fr 1fr`, gap 18px, `align-items:start`.
  - Izquierda — tarjeta con etiqueta "DOCUMENTO ORIGINAL" y, a la derecha, "Drive · 1 de 3" en mono 11.5px. Debajo, el visor: alto 470–520px, borde discontinuo `#D8D8D2`, radio 8px. En el prototipo es `repeating-linear-gradient(135deg,#FAFAF8,#FAFAF8 9px,#F4F4F0 9px,#F4F4F0 18px)`; **en producción va el documento real**.
  - Derecha — dos tarjetas:
    - "Datos extraídos" + etiqueta verde con el nombre del `DocumentType`; a la derecha "confianza {promedio}" en mono. Filas de campo: grid `170px 1fr 62px`, padding `10px 16px`, borde `#F1F1EC`. Clave en mono 12px `#8A948C`; valor 13.5px/500; a la derecha barra de 34×4px radio 3px sobre `#EDEDE8` con relleno proporcional y el valor con 2 decimales en mono 10.5px.
      - **Regla de confianza**: > 0.90 relleno `#00C16A` y valor en `#0F1A14`; ≤ 0.90 relleno `#D9A420` y valor en `#8A7A2E`.
      - Si el documento es `failed` / sin tipo: mensaje "No se identificó el tipo de documento, así que no hay campos extraídos." en 13px `#6B7770`.
    - "Trazabilidad": lista con punto de 7px por evento — detectado en Drive (`#98A29B`), clasificado (`#2C5FA8`), OCR completado (`#6A45A8`), listo para aprobación (`#00C16A`). Cada evento: etiqueta 13px + meta en mono 11.5px `#98A29B` (`09:11:49 · claude-classifier`). Se corresponde con las transiciones de estado de `process_uploaded_document.py`.

### 5. Tipos de documento y "Definir tipo"

(En el prototipo `Contador.dc.html`; ver `design/` — el UI kit no los incluye.)

- **Lista**: grid de 2 columnas, gap 14px. Cada tarjeta: nombre 15px/600, badge Activo/Borrador, conteo de documentos en mono; descripción 13px `#6B7770`; y un bloque hundido `#FAFAF8` borde `#EDEDE8` radio 8px con la etiqueta `extraction_schema` en mono 10.5px y las claves como etiquetas mono 11.5px sobre blanco, radio 5px.
- **Definir tipo** (`/document-types/new`): dos pasos, una sola columna.
  1. Formulario (Nombre, Descripción, documento de muestra) → `POST /document-types/proposals`
     (multipart: `name`, `sample_file`, `kind_id?`). No guarda nada, y la pantalla lo dice
     bajo el título. Estado de carga honesto: la llamada a Claude tarda ~1 min.
  2. **Selección de lo que se extrae**, en tarjetas: identificación de quien reporta (el
     control más ruidoso, ver abajo), campos por sección, y años gravables. Guardar →
     `POST /document-types` (JSON con el esquema ya podado, `field_mappings`, `fields`,
     `tax_years`, `kind_id`, `sample_document_id`).
  - **Convención**: la propuesta cruda de la IA (`extraction_prompt`, `extraction_schema`)
    **ya no se muestra**. El lector es un contador con un certificado en la mano, no un
    desarrollador: se le muestran los campos en las palabras del documento y el path como
    texto secundario. El panel profundo `#0C1512` del prototipo queda sin uso en esta
    pantalla; si vuelve a hacer falta, sigue significando "esto lo generó el modelo".
  - **Bloqueo de guardado**: sin campo de NIT de quien reporta (o si el campo elegido se
    destilda) no se puede guardar — el servidor descartaría todas las asignaciones y el tipo
    reportaría como faltante cada cifra que debería respaldar. Mismo guard que el
    configurador (`/document-types/[id]`), con las mismas cadenas i18n.

#### Patrón: selección de campos por sección

Se usa en el paso 2 de "Definir tipo" y está disponible para cualquier pantalla que haga
elegir campos de un documento.

- **Cabecera de sección**: `bg-elevated/50 rounded-lg px-3 py-2`, título 13–14px/500, contador
  "{n} de {m} marcados" en `text-muted text-xs`, y a la derecha dos `UButton size="xs"
  variant="ghost"`: "Marcar todo" / "Ninguno". La sección es el bloque del papel (viene del
  documento, no del esquema); los campos sin bloque van al final bajo "Otros campos del
  documento".
- **Fila de campo**: `<label>` con `border border-default rounded-lg p-3`, hover
  `bg-elevated/60`, `UCheckbox` a la izquierda. A la derecha: etiqueta del documento
  (13–14px/500) + `UBadge` de rol (Identificación `success` · Valor `primary` · Contexto
  `neutral`), el valor leído en la muestra en `text-toned text-[13px]`, y el path en
  `font-mono text-xs text-dimmed`. Sin marcar, la fila baja a `opacity-60`.
- **Selección por defecto**: `identifier` y `amount` marcados; `context` sin marcar. Es una
  decisión de dominio (`isKeptByDefault`), no del componente: el contador casi siempre quiere
  la identificación y los valores, así que el trabajo es corregir la selección, no armarla.

### 6. Hojas de cálculo (`SheetsScreen`)

- Cuatro tarjetas de cliente en grid, gap 12px: nombre 13px/600, y en mono 11.5px el periodo y el conteo de filas; estado ("Sincronizada" / "Pendiente de exportar") 11.5px. La seleccionada invierte a fondo `#0C1512`, texto `#E6EDE9`, metadatos `rgba(230,237,233,.55)`.
- Tabla: cabecera "{cliente} · {periodo}", etiqueta verde con "N filas aprobadas", botón de contorno "Abrir en Google Sheets". Columnas `110px 1fr 130px 120px 110px`: fecha (mono `#6B7770`), descripción, documento origen (12px `#8A948C`), valor (mono 13px/500, derecha), iva (mono 13px `#6B7770`, derecha). Nombres de columna en mono 11px uppercase tracking .07em.
- **No existe en el servidor todavía**: no hay entidad ni endpoint de hojas. Requiere trabajo de backend (agregación de `ExtractedData` por cliente/periodo + export a Sheets).

## List row pattern

Toda lista de la app (bandeja agrupada por cliente, documentos de un cliente, la lista de
clientes) comparte una única forma de fila — **no hay una variante de tabla aparte**. Esto
no estaba explícito antes de que `/clients` divergiera de las demás listas usando `UTable`;
queda documentado aquí para que no vuelva a pasar.

- Contenedor: `<ul>` con `divide-y divide-default`, envuelto en `rounded-lg border
  border-default bg-default`. Cada fila es un `<li>` con un `<NuxtLink>` de bloque completo
  como única celda clickeable — así el tap y la activación por teclado (Enter/Espacio) vienen
  gratis del elemento nativo, sin réplicas de `onSelect`/`keydown` como las que necesitaba
  `UTable`.
- Fila: `flex items-center gap-3 px-4 py-3` (o `py-2.5` si la fila es más angosta, como en
  `ClientDocumentList`), `hover:bg-elevated`, `transition-colors duration-[120ms]`.
- Elemento inicial — avatar o miniatura, según lo que agrupa la fila:
  - Cliente: iniciales de color estable, `22×22`, `rounded-[5px]`, `text-[10px] font-semibold`
    — `colorForClient`/`initialsForClientName` en `app/utils/client-color.ts`.
  - Documento: miniatura de extensión, `22×26`, `rounded-[3px]`, `border border-default
    bg-muted`.
- Texto: título `text-[13.5px] font-medium text-highlighted`; metadatos secundarios
  `text-[12px] text-muted`, mono (`font-mono`) para cualquier dato — NIT, hora, extensión —
  nunca para una frase.
- Sin `UTable` para listas de entidades de negocio (clientes, documentos, filas de hoja de
  cálculo): a esta escala de columnas (2–4, ninguna con orden/filtrado por columna) una tabla
  sólo agrega un mecanismo de fila distinto que hay que igualar a mano contra este patrón, y
  en viewports angostos empuja columnas fuera de pantalla sin ninguna señal de que se puede
  hacer scroll. Excepción real: `sheets.vue` sí usa `UTable`, porque ahí sí hay columnas
  numéricas alineadas a la derecha que se leen como una hoja de cálculo, no como una lista de
  entidades.

## Interactions & Behavior

- **Navegación**: barra lateral cambia de vista. Clic en fila de documento → revisión. Clic en el nombre del cliente (cabecera de grupo o tabla) → ficha de cliente. "← Volver" regresa a la bandeja.
- **Filtros de bandeja**: selección única; filtra por `DocumentStatus`. El conteo "N de M documentos" se actualiza. Los grupos de cliente sin documentos que pasen el filtro se ocultan por completo.
- **Transiciones**: 120ms sobre `background`, `border-color`, `color`. No hay desplazamiento, escala ni rebote en ningún estado.
- **Hover**: filas y celdas → `#FAFAF8`; sobre superficie profunda → `rgba(255,255,255,.07)`; botón sólido `#00A155` → `#00C16A`; botón de contorno → borde y texto `#00A155`.
- **Focus**: anillo `0 0 0 3px rgba(0,193,106,.25)`.
- **Estados de carga**: los documentos en `classifying` / `running_ocr` son estados reales del pipeline, no spinners. La bandeja debería refrescar (poll o SSE) para que el badge avance solo; hoy no hay canal de tiempo real en el servidor.
- **Vacío**: usar la clave existente `clients.empty` ("Aún no hay clientes registrados.") en 13px `#6B7770`. Para la bandeja filtrada sin resultados, mismo tratamiento.
- **Errores**: un documento `failed` muestra badge rojo y, en la revisión, el mensaje de `Document.error` en lugar de los campos.
- **Responsive**: no diseñado. La herramienta es de escritorio; por debajo de ~1100px habría que colapsar la barra lateral a iconos y pasar la revisión de documento a una columna.

## State Management

- `screen`: `'queue' | 'clients' | 'client' | 'doc' | 'types' | 'define' | 'sheets'` — en producción, rutas de Nuxt: `/clients`, `/clients/[id]`, `/documents/[id]`, `/document-types`, `/document-types/new`, `/sheets`.
- `filter`: estado activo de la bandeja (query param).
- `clientIx` / `docIx`: en producción son ids de ruta.
- `sheetIx`: cliente seleccionado en Hojas de cálculo.

Datos que hacen falta (endpoints existentes en `apps/server`):
- `GET /clients` — existe (`routers/clients.py`), ya consumido por `list-clients.ts`.
- `GET /documents/{id}` y `GET /documents/{id}/extracted-data` — existen.
- **Falta**: listar documentos por cliente y listar la cola completa. Hoy `DocumentRepository` sólo expone `get`/`save`; hay que añadir `list_by_client` y un `GET /clients/{id}/documents` + `GET /documents`.
- **Falta**: listar `DocumentType` (sólo existe `POST /document-types`).
- **Falta**: todo lo de hojas de cálculo.

## Design Tokens

Todos los valores están en `design/tokens/*.css` como custom properties. Al portar a Tailwind 4, declararlos en `@theme` dentro de `apps/web/app/assets/css/main.css`, junto a la escala verde que ya está allí.

**Verde de marca** — idéntico al de `main.css`, no cambiar: `50 #EFFDF5`, `100 #D9FBE8`, `200 #B3F5D1`, `300 #75EDAE`, `400 #00DC82`, `500 #00C16A`, `600 #00A155`, `700 #007F45`, `800 #016538`, `900 #0A5331`, `950 #052E16`. Acción = 600; hover = 500; sobre tinta oscura = 400.

**Neutros (tinta verdosa, nunca gris puro)**: `#0C1512` superficie profunda, `#0F1A14` texto principal, `#3E4A43` secundario, `#6B7770` terciario, `#8A948C` atenuado, `#98A29B` mono atenuado; líneas `#C9D2CC`, `#D8D8D2`, `#DEDED8`, `#E4E4DF`, `#EDEDE8`, `#F1F1EC`; papel `#F7F7F5` (fondo app), `#FAFAF8` (hundido/hover), `#FCFCFA` (campos), `#FFFFFF` (tarjeta); invertido `#E6EDE9`.

**Estados de documento** (fondo / texto):
- `pending` `#F4F1E6` / `#8A7A2E` — "Pendiente"
- `classifying` `#EAF1FB` / `#2C5FA8` — "Clasificando"
- `running_ocr` `#F1EBFA` / `#6A45A8` — "OCR"
- `processed` `#EFFDF5` / `#00784A` — "Procesado"
- `failed` `#FDEEEC` / `#B03A2B` — "Fallido"

**Avatares de cliente** (índice estable por cliente, mismo color en toda la app): `#EFFDF5/#00784A`, `#F1EBFA/#6A45A8`, `#EAF1FB/#2C5FA8`, `#F4F1E6/#8A7A2E`, `#FDEEEC/#B03A2B`, `#ECF3F0/#3E4A43`.

**Tipografía**: `Public Sans` (ya declarada como `--font-sans` en `main.css`) y `JetBrains Mono` (nueva). Escala: display 27/1.15/700 tracking -.02em · title 26/1.2/700 · section 15/1.3/600 · body 13.5/1.5/400 · body-strong 13.5/500 · small 13/1.45 · meta 12 · label 11.5 uppercase tracking .08em. Mono: figure 30/600 tracking -.03em · value 13/500 · meta 12/400 · micro 11.5/400.

- **Regla**: la monoespaciada se usa para datos, no para frases — NIT, importes, horas, migas de pan, claves de esquema, conteos, cifras.

**Espacio**: 4 · 6 · 9 · 12 · 14 · 16 · 20 · 22 · 30 · 44. Fila compacta 9px (por defecto), cómoda 14px. Gutter de página 30px, gutter de tarjeta 16px, barra lateral 238px, topbar 62px, contenido máx. 1180px. **No redondear a una escala de 4/8px.**

**Radios**: 3 (miniatura de archivo) · 5 (etiqueta mono, avatar pequeño) · 8 (botón, campo, bloque hundido) · 11 (tarjeta de cifra) · 12 (tarjeta) · pastilla (estado, filtro).

**Bordes y sombras**: hairline 1px `#E4E4DF`; separador de fila 1px `#F1F1EC`; discontinuo 1px `#D8D8D2`. Las tarjetas **no llevan sombra**; `0 1px 3px rgba(15,26,20,.06)` sólo si algo debe flotar y `0 12px 32px rgba(15,26,20,.14)` para diálogos.

## Assets

- **No hay logo.** La marca se representa como un cuadro verde con la letra "C". Si existe un logotipo, sustituirlo; no se inventó ninguno.
- **No hay iconos** en el bundle. Usar Lucide vía `@iconify-json/lucide`, ya declarado en `apps/web/package.json`.
- **Fuentes**: no se entregaron binarios. Los prototipos cargan Public Sans y JetBrains Mono desde Google Fonts. En producción, autoalojar o usar `@nuxt/fonts`.
- **Sin imágenes ni ilustraciones.** El único "asset" gráfico es la trama diagonal del marcador de documento, que se reemplaza por el visor real.
- **Sin emoji**, en ningún caso.

## Copy

El locale por defecto es `es`. Reutilizar las claves existentes de `i18n/locales/es.json` (`app.name`, `clients.*`, `auth.*`) y añadir las nuevas bajo `documents.*`, `documentTypes.*`, `sheets.*`. Toda la copia de esta guía está en español y es la definitiva; el archivo `en.json` necesita las traducciones equivalentes.

Tono: enunciativo, sin exclamaciones, sentence case, verbos en infinitivo en los botones. Términos técnicos (`OCR`, `Drive`, `extraction_schema`, claves de campos) no se traducen ni se humanizan.

## Files

En `design/`:

- `readme.md` — la guía completa del sistema (fundamentos de contenido, visuales e iconografía).
- `styles.css` + `tokens/` — todos los tokens como custom properties.
- `components/core/` — `Button`, `StatusBadge`, `Tag`, `Card`, `StatCard`.
- `components/data/` — `DocumentRow` (variantes `columns` y `stacked`), `ClientGroupHeader`, `FieldRow`.
- `components/navigation/` — `SidebarNavItem`, `FilterChip`.
- `ui_kits/contador/index.html` — **ábrelo en un navegador**: es la app navegable (bandeja → cliente → documento → hojas).
- `ui_kits/contador/*.jsx` — las pantallas; `data.js` son los datos ficticios.

Las pantallas de tipos de documento y "Definir tipo" están en el prototipo original `Contador.dc.html` del proyecto de diseño, descrito en la sección 5 de este documento.
