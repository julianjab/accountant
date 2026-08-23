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
- [ ] #C Ficha de cliente
- [ ] #D Revisión de documento y datos extraídos
- [ ] #E Tipos de documento y "Definir tipo"
- [ ] #F Hojas de cálculo por cliente
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

## C. Ficha de cliente

Ref: README → "§ 3 Ficha de cliente". Depende de A y G.

Ruta `/clients/[id]`. La tabla actual de `/clients` se mantiene como índice.

**Tareas**

- [ ] Encabezado: avatar 52px, nombre, NIT en mono, correo (o "sin correo"), enlace a la carpeta de Drive.
- [ ] Pestañas Documentos / Datos extraídos / Hojas de cálculo (sólo la primera con contenido en esta issue).
- [ ] Lista de documentos en **layout de dos líneas** (la columna es estrecha): nombre arriba, "tipo · hora" abajo, badge a la derecha.
- [ ] Panel lateral: "Resumen del mes" y tarjeta profunda de "Tipos configurados" con acceso a la configuración.
- [ ] Botón "Exportar a hoja de cálculo" (deshabilitado hasta F).

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

## F. Hojas de cálculo por cliente

Ref: README → "§ 6". Depende de G. **Bloqueada por backend.**

**Tareas**

- [ ] Selector de cliente en tarjetas (la seleccionada se invierte a fondo profundo).
- [ ] Tabla de filas aprobadas: fecha, descripción, documento origen, valor, iva.
- [ ] Acción "Abrir en Google Sheets".

**Nota**: no existe entidad ni endpoint de hojas de cálculo. Definir primero cómo se agregan los `ExtractedData` aprobados por cliente y periodo, y qué significa "aprobado" en el modelo (hoy `Document` no tiene ese estado).

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
