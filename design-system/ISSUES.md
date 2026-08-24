# Issues listas para pegar en GitHub

No puedo crear issues por ti (sólo leo el repo). El flujo es:

1. Copia la carpeta `design_handoff_contador/` a la raíz del repo y haz commit — así los enlaces de las issues apuntan a archivos que existen en `main`.
2. Crea las issues de abajo copiando cada bloque. Título en la línea `##`, cuerpo lo que sigue.
3. Si usas la CLI: `gh issue create --title "..." --body-file <archivo>`.

Sugerencia de etiquetas: `design`, `frontend`, `backend`, `blocked`.

---

## [Épica] UI de intake de documentos por cliente

Diseño completo en `design_handoff_contador/README.md`. El prototipo navegable se abre con `design_handoff_contador/design/ui_kits/contador/index.html`.

Hoy `apps/web` es la plantilla de Nuxt UI con un `UHeader`, el botón de Google y la tabla de clientes. Todo el pipeline de documentos (`Document`, `DocumentType`, `ExtractedData`) existe en `apps/server` sin interfaz.

**Alcance**

- [x] #A Tokens de diseño y shell (barra lateral + topbar)
- [ ] #B Bandeja de entrada agrupada por cliente
- [x] #C Ficha de cliente
- [ ] #D Revisión de documento y datos extraídos
- [ ] #E Tipos de documento y "Definir tipo"
- [x] #F Hojas de cálculo por cliente
- [ ] #G Endpoints faltantes en `apps/server`

**Fuera de alcance**: responsive por debajo de ~1100px, tiempo real en la bandeja, autenticación distinta a la actual.

**Decisiones que el diseño da por cerradas**

- Los documentos siempre se muestran agrupados bajo su cliente. Nada de listas planas cronológicas.
- La superficie profunda `#0C1512` significa "esto lo generó el modelo, revísalo": sólo navegación y contenido de IA.
- Todo campo extraído muestra su confianza; ámbar por debajo de 0.90.
- Copia en español, reutilizando las claves de `i18n/locales/es.json`.

---

## A. Tokens de diseño y shell de la app — ✅ implementado

Ref: `design-system/README.md` → "Design Tokens" y "Screens / Views § 1".

**Implementado** (branch `feat/design-tokens-app-shell`):

- [x] `apps/web/app/assets/css/main.css` — `@theme static` extendido con los neutros de tinta verdosa (mapeados a una escala estándar `--color-neutral-50..950` para que sirvan como `ui.colors.neutral` de Nuxt UI, más alias exactos `--color-paper-*`/`--color-line-*` para los valores que no caen limpio en esa escala), los 5 estados reales de `Document.status` (`pending | classifying | running_ocr | processed | failed`, no los 4 genéricos que proponía el issue original), la paleta de 6 avatares (no 8), la escala tipográfica nombrada (`--text-label/meta/small/body/section/title/display`) y su alias en convención Tailwind (`--text-xs..3xl`), y `--font-mono: 'JetBrains Mono', ui-monospace, monospace;`. La escala verde no se tocó.
- [x] `apps/web/nuxt.config.ts` — `@nuxt/fonts` registrado en `modules`, con `fonts.families` para `Public Sans` y `JetBrains Mono` (Google provider; no hubo que autoalojar).
- [x] `apps/web/app/app.config.ts` — `ui.colors.neutral` pasó de `'slate'` a `'neutral'` (la escala nueva).
- [x] `apps/web/app/layouts/default.vue` — grid sidebar (238px, `bg-neutral-950` = `#0C1512`) + contenido; `apps/web/app/app.vue` quedó en `UApp` + `NuxtLayout` + `NuxtPage`, sin `UHeader`.
- [x] `apps/web/app/components/AppSidebar.vue` — marca placeholder (cuadro verde "C"), nav de **4 ítems reales del doc de diseño** (Bandeja `/` `i-lucide-inbox`, Clientes `/clients` `i-lucide-users`, Tipos de documento `/document-types` `i-lucide-settings`, Hojas de cálculo `/sheets` `i-lucide-table`), estado activo con `aria-current="page"`, slot `#auth`.
- [x] `apps/web/app/components/AppSidebarAuth.vue` — renderiza el `GoogleSignInButton` real (de la tarea de Google Auth, ya en `main` antes que ésta) sin tocarlo, y añade debajo la leyenda "Drive · solo lectura" cuando hay sesión. No hizo falta un placeholder tipado nuevo — el componente real ya existía. Se descartó una reimplementación propia del bloque logueado (avatar + correo + botón) porque duplicaba lógica y rompía los `data-testid` que ya usa `tests/e2e/google-sign-in.spec.ts`.
- [x] `apps/web/app/components/AppTopbar.vue` + `AppBreadcrumb.vue` — 62px, breadcrumb mono minúscula formato `inicio / <sección>` (igual al prototipo `Sidebar.jsx`/`Topbar.jsx`, no el `segmento · segmento` que proponía el issue original), buscador no funcional (`i-lucide-search`, atajo `⌘K`), slot de acciones con `UColorModeButton`.
- [x] Iconos: sólo `@iconify-json/lucide` (`inbox`, `users`, `settings`, `table`, `search` usados; `arrow-left` queda reservado para la tarea D — revisión de documento). Sin glifos unicode.
- [x] i18n: claves nuevas `nav.*`, `breadcrumb.home`, `topbar.search`, `auth.driveReadOnly` en `es.json`/`en.json`.
- [x] `document-types` y `sheets` se muestran deshabilitados (sin `NuxtLink`, texto atenuado) en vez de como enlaces "muertos" — no tienen página todavía.

**Desvíos respecto al enunciado original**: el issue se redactó antes de que `design-system/` llegara al repo (commit `b03b96e`), así que sus "Open questions" (hex de neutros/estados/avatares, nav de 3 ítems con un "Ajustes" inventado, separador de miga de pan) se descartaron a favor de los valores reales y definitivos del doc. `document-types` y `sheets` son enlaces "muertos" hasta las tareas E/F, igual que `/inbox` (redirige a `/clients` vía `pages/index.vue`, sin cambios en esta tarea).

**Tests**: no se agregaron tests nuevos (componentes de presentación puros, sin lógica de negocio propia — reutilizan `useGoogleAuth`/`GoogleSignInButton`, ya cubiertos). `bun run lint && bun run typecheck && bun run test` en verde (11 tests). Verificado manualmente con `bun run dev`: `/clients` renderiza dentro del shell nuevo, sidebar+breadcrumb correctos, sin errores en consola del server.

**Deuda técnica / fuera de alcance**: sin colapso de sidebar en viewports angostos (`< 1280px`, explícitamente fuera de alcance); escala tipográfica genérica `xl/2xl/3xl` interpolada (el doc de diseño no define esos tamaños, sólo `display`/`title` y hacia abajo — quedan como aproximación razonable hasta que una vista futura la necesite con precisión).

---

## B. Bandeja de entrada agrupada por cliente

Ref: README → "§ 2 Bandeja de entrada". Depende de A y de G.

Ruta `/` (hoy redirige a `/clients`; pasa a ser la bandeja).

**Tareas**

- [ ] Cuatro tarjetas de cifra: sin procesar, procesados hoy, fallidos, tiempo medio.
- [ ] Filtros por `DocumentStatus` (selección única, en query param), con el conteo "N de M documentos".
- [ ] Lista agrupada: cabecera por cliente (avatar de color estable + nombre navegable + conteo) y filas de documento sangradas 48px.
- [ ] Fila: miniatura de extensión, nombre, tipo clasificado, badge de estado, hora.
- [ ] Estado vacío y estado "sin resultados para este filtro".

**Criterio de aceptación**: los grupos sin documentos que pasen el filtro desaparecen por completo; clic en la fila abre la revisión; clic en el nombre del cliente abre su ficha.

---

## C. Ficha de cliente — ✅ implementado

Ref: README → "§ 3 Ficha de cliente". Depende de A y G.

Ruta `/clients/[id]`. La tabla actual de `/clients` se mantiene como índice.

**Implementado** (branch `feat/client-detail-page`):

- [x] `apps/server/src/server/domain/entities/client.py` — `drive_folder_url: str | None = None`; propagado en `ClientCreateRequest`/`ClientResponse` (`infrastructure/api/schemas.py`) y en `RegisterClient.execute` (`application/use_cases/register_client.py`).
- [x] `apps/server/src/server/infrastructure/api/routers/clients.py` — `GET /clients/{id}` con 404. `GET /clients/{id}/documents` y `GET /document-types?active_only=` **ya existían** (tarea G, mergeada antes que ésta) — se reutilizaron sin cambios.
- [x] Web dominio: `Client.driveFolderUrl`, `DocumentType` nuevo (`{ id, name, active }`); `ClientDocument`/`DocumentStatus` reutilizados sin redefinir.
- [x] Web puertos/use cases: `ClientRepository.get`, `DocumentRepository`/`DocumentTypeRepository` nuevos; `GetClient`, `ListClientDocuments`, `ListActiveDocumentTypes` (con test hermano cada uno, patrón `list-clients.test.ts`).
- [x] Web adapters: `HttpClientRepository.get` (404 → `null` vía `statusCode` de `FetchError`), `HttpDocumentRepository`, `HttpDocumentTypeRepository`; DI en `useDi.ts`.
- [x] `apps/web/app/infrastructure/components/clients/` — `ClientHeader`, `ClientDocumentList`, `MonthlySummaryCard`, `ConfiguredTypesCard`, `ExportSpreadsheetButton` (directorio nuevo).
- [x] `apps/web/app/pages/clients/[id].vue` — tres `useAsyncData` independientes (`client:{id}`, `documents:{id}`, `document-types`), estado "no encontrado" traducido para 404, `UTabs` (sólo "Documentos" con contenido) y layout `grid` con panel lateral que colapsa bajo `lg`.
- [x] `apps/web/app/pages/clients/index.vue` — filas de `UTable` navegables: `onSelect` para clic + un listener `@keydown` en la tabla (Nuxt UI 4 marca la fila seleccionable como `role="button" tabindex="0"` pero **no** conecta Enter/Space a una activación real; se captura el `keydown` que burbujea desde la `<tr>` enfocada y se resuelve el cliente por índice de fila, restando la cantidad real de filas de `<thead>`). **Corregido después** (ver abajo): esto divergía del "List row pattern" que las tareas B/C consolidaron para las demás listas.
- [x] i18n: `clients.detail.*` y `documents.status.*` en `es.json`/`en.json`.

**Desvíos respecto al enunciado original**: ninguno funcional. La única ambigüedad resuelta por el builder: el botón "Exportar a hoja de cálculo" se ubicó en el encabezado (`ClientHeader`), no en la pestaña "Hojas de cálculo", porque el diseño de referencia (`ClientScreen.jsx`) lo pone ahí. El botón "Configurar extracción" queda deshabilitado con tooltip (mismo patrón que "Exportar") en vez de enlazar a `/document-types`, porque esa ruta todavía no existe (#12).

**Seguridad**: el hook de pre-push de este repo detectó que `drive_folder_url` se renderiza como `<a href>` sin sanear — un valor `javascript:...` habría sido un XSS activable con un clic. Se corrigió en dos capas: `ClientCreateRequest` en el servidor rechaza (422) cualquier valor que no empiece con `https://` (`field_validator`, con test), y `ClientHeader.vue` repite el chequeo en el cliente antes de bindear el `href`, por si algún dato viejo/editado a mano llegara sin pasar por el validador.

**Tests**: `apps/web` → `bun run lint && bun run typecheck && bun run test` en verde (8 archivos, 15 tests). `apps/server` → `uv run ruff format . && uv run ruff check . && uv run pytest` en verde (36 tests, incluye `GET /clients/{id}` happy-path + 404 y el rechazo de `drive_folder_url` no-https). Verificado manualmente en un browser real (Playwright, ver detalle abajo): fila → ficha por clic, fila → ficha por teclado (`Enter`), estado "no encontrado" para un id inexistente sin excepción sin capturar, tabs, resumen del mes y tarjeta de tipos con datos reales del server.

**Deuda técnica / fuera de alcance**: el servidor no tiene `CORSMiddleware` (pre-existente, no introducido por esta tarea) — cualquier navegación *client-side* que dispare un `$fetch` desde el browser hacia un `serverApiBase` en otro origen falla por CORS en dev con puertos separados; el primer render SSR no se ve afectado porque corre en el servidor de Nuxt, no en el browser. No se tocó porque escapa al alcance de "Ficha de cliente" y afecta a toda la app por igual. Contenido real de "Datos extraídos" y "Hojas de cálculo", funcionalidad de "Exportar" (#11) y paginación de la lista de documentos quedan fuera de esta issue, como estaba previsto.

**Corrección posterior — `clients/index.vue` alineado al "List row pattern"**: la `UTable` de arriba nunca estuvo en el doc de diseño (`/clients` no es una de las pantallas del handoff) y quedó sin el tratamiento que sí llevan `InboxGroup`/`ClientDocumentList` — sin avatar, sin `divide-y`/hover/tipografía del patrón de fila, y con un workaround de teclado propio para suplir lo que `UTable` no resuelve. Se reemplazó por el mismo patrón de `<ul>/<li>/<NuxtLink>` que usan las demás listas (una sola implementación para todos los anchos, sin variante mobile aparte), documentado ahora en README.md → "List row pattern". La iniciales compartidas (antes duplicadas en `InboxGroup.vue`) se extrajeron a `initialsForClientName` en `app/utils/client-color.ts`.

---

## D. Revisión de documento y datos extraídos

Ref: README → "§ 4 Revisión de documento". Depende de A.

Ruta `/documents/[id]`. Consume `GET /documents/{id}` y `GET /documents/{id}/extracted-data`, que ya existen.

**Tareas**

- [ ] Vista a dos columnas: documento original a la izquierda, extracción a la derecha.
- [ ] Visor real del archivo de Drive (el prototipo usa una trama diagonal como marcador).
- [ ] Filas de campo con clave en mono, valor, y barra de confianza de 34px. **Regla**: > 0.90 verde con valor en tinta; ≤ 0.90 ámbar con el valor también en ámbar.
- [ ] Confianza promedio en la cabecera de la tarjeta.
- [ ] Documento `failed` o sin tipo: mostrar `Document.error` en lugar de los campos.
- [ ] Trazabilidad con las transiciones reales de `process_uploaded_document.py` (detectado → clasificado → OCR → listo).
- [ ] Botón "Aprobar y enviar a hoja" (deshabilitado hasta F).

---

## E. Tipos de documento y "Definir tipo"

Ref: README → "§ 5". Depende de A y G.

Rutas `/document-types` y `/document-types/new`.

**Tareas**

- [ ] Lista en dos columnas: nombre, estado activo/borrador, conteo, descripción y las claves de `extraction_schema` como etiquetas mono.
- [ ] Formulario de definición: nombre, descripción y documento de muestra → `POST /document-types` (multipart).
- [ ] Panel profundo con la propuesta de la IA: `extraction_prompt` y `extraction_schema`, con acciones "Guardar tipo" y "Editar".
- [ ] Estado de carga honesto: la llamada a Claude es lenta y bloqueante.

---

## F. Hojas de cálculo por cliente — ✅ implementado

Ref: README → "§ 6". Depende de G (ya cerrada).

**Implementado** (branch `feat/cliente-hoja-calculo-consolidacion`):

- [x] `apps/server/src/server/domain/entities/sheet_row.py` — `SheetRow{source_document_id, source_document_file_name, date, description, amount, tax}` (todos `str`).
- [x] `Client.spreadsheet_url: str | None = None` — destino de "Abrir en Google Sheets", pegado fuera de banda al registrar el cliente (opción i del PRD: URL persistida, sin credenciales de Sheets nuevas; Drive sigue en `drive.readonly`).
- [x] `application/use_cases/list_client_sheet_rows.py` — `ListClientSheetRows` agrega los documentos `DocumentStatus.APPROVED` de un cliente con su `ExtractedData` (lectura por clave exacta `date`/`description`/`amount`/`tax`, `""` si falta). No se tocaron los ports: la agregación vive enteramente en el use case, no en `ExtractedDataRepository`.
- [x] `GET /clients/{client_id}/spreadsheet-rows` (404 si el cliente no existe) — `infrastructure/api/routers/clients.py`.
- [x] `apps/web/app/pages/sheets.vue` — tarjetas horizontales de cliente (grid, no scroll horizontal), la seleccionada invierte a `bg-neutral-950`/`text-invert` (tokens ya declarados en tarea A); tabla de filas vía `UTable`; botón "Abrir en Google Sheets" (enlaza a `spreadsheetUrl`, deshabilitado si no hay).
- [x] `apps/web/app/components/AppSidebar.vue` — `/sheets` deja de ser un link "muerto".
- [x] i18n: `sheets.*` en `es.json`/`en.json` (no `clients.spreadsheet.*`, siguiendo la convención de este README).

**Desvíos respecto al enunciado original, documentados en el issue de ia-flow**:
- **Sin filtro de periodo** en el endpoint ni en la UI: `ExtractedData.fields` no tiene un campo de fecha confiable todavía (depende del `extraction_schema` de cada `DocumentType`, tarea E, no implementada). Las tarjetas muestran conteo de filas + estado de sincronización, no "periodo".
- **Forma de fila con fallback a `""`**: no hay mapeo formal entre las claves de un `extraction_schema` y `date`/`description`/`amount`/`tax`. Si un tipo de documento usa otros nombres, esas columnas salen vacías — deuda técnica para cuando la tarea E permita declarar ese mapeo.

**Tests**: `apps/server/tests/application/test_list_client_sheet_rows.py`, casos nuevos en `test_clients.py`/`test_register_client.py`; `apps/web/app/application/use-cases/list-client-sheet-rows.test.ts`. `uv run ruff check . && uv run pytest` (38 tests) y `bun run lint && bun run typecheck && bun run test` (13 tests) en verde. Verificado manualmente con `bun run dev` + `uv run uvicorn` apuntando a un puerto de prueba: selección de tarjeta, cambio de tabla, y estado deshabilitado del botón cuando `spreadsheetUrl` es `null` — confirmado por captura de accesibilidad (Playwright), sin errores de consola. No se pudo probar el camino con filas aprobadas reales de punta a punta (requiere credenciales de Anthropic para correr el pipeline de OCR, no disponibles en este entorno); ese camino queda cubierto por los tests de `ListClientSheetRows`.

**Deuda técnica / fuera de alcance**: sin paginación en `GET /clients/{id}/spreadsheet-rows`; sin mapeo declarado entre `extraction_schema` y las claves canónicas de `SheetRow`; sin filtro de periodo.

---

## G. Endpoints faltantes en apps/server — ✅ implementado

La UI diseñada necesita lecturas que hoy no existen.

**Implementado** (branch `feat/add-missing-server-endpoints`):

- [x] `DocumentRepository.list_all(status: DocumentStatus | None = None)` y `DocumentTypeRepository.list_all()` en `domain/ports/repositories.py`, implementados en `InMemoryDocumentRepository`/`InMemoryDocumentTypeRepository` (`infrastructure/adapters/in_memory_repositories.py`). `list_by_client` ya existía.
- [x] `GET /documents?status=&client_id=` — filtra por `DocumentStatus` (422 si el valor es inválido, comportamiento nativo de FastAPI/Pydantic) y por `client_id`. Alimenta la bandeja.
- [x] `GET /clients/{id}/documents` — 404 si el cliente no existe. Alimenta la ficha de cliente.
- [x] `GET /document-types?active_only=true|false` (default `true`). `active_only=false` requirió `DocumentTypeRepository.list_all()`.
- [x] `GET /documents/metrics` → `DocumentMetricsResponse { unprocessed, processed_today, failed, avg_processing_seconds }`. Declarado antes de `/{document_id}` para que FastAPI no matchee `metrics` como id.
  - `processed_today` compara `processed_at` (nuevo campo en `Document`, poblado en `process_uploaded_document.py` al llegar a `PROCESSED`) contra la fecha actual **en UTC**.
  - `avg_processing_seconds` promedia `processed_at - created_at` sólo sobre documentos con `status = processed`; `null` si no hay ninguno.
- [x] Modelo de aprobación — **opción A** del PRD (estado nuevo, no un campo ortogonal): `DocumentStatus.APPROVED` + `Document.reviewed_at`/`approved_by` (ambos `None` por defecto, no rompen datos existentes). Caso de uso `ApproveDocument` (`application/use_cases/approve_document.py`) valida que el documento esté en `PROCESSED`, si no lanza `DocumentNotApprovable`; `DocumentNotFound` si no existe. Endpoint `POST /documents/{id}/approve` (404 / 409). Habilita a F/#11 a consultar `status = approved` como precondición de exportar.

**Desvíos respecto al enunciado original**: ninguno relevante — se implementó tal como está descrito arriba, incluida la opción A de aprobación.

**Tests**: `apps/server/tests/application/test_approve_document.py`, `apps/server/tests/infrastructure/api/{test_documents,test_clients,test_document_types}.py` (vía `TestClient`). `uv run ruff format . && uv run ruff check --fix . && uv run pytest` en verde (29 tests).

**Deuda técnica / fuera de alcance**: sin paginación en los listados; sin auth para `approved_by` (string libre); persistencia sigue in-memory.
