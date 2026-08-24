# Accountant

Monorepo for an OCR-driven document intake tool for accountants: a preparer uploads client
documents to Google Drive; the server auto-detects the document type and extracts structured
data from it via a multimodal AI.

## Domain

- **Client** — a person/company whose tax documents are being processed. Clients are
  imported from Drive: each subfolder of `ACCOUNTANT_GOOGLE_DRIVE_CLIENTS_FOLDER_ID` is one
  (`POST /clients/import`). Matching is by Drive folder id, so renaming a folder updates the
  client rather than forking it, and a folder disappearing never deletes one. `tax_id` is
  therefore optional — a folder carries a name, not a tax id.
- **Document** — a file uploaded for a client (linked to a Drive file).
- **Extracted data** — the structured fields an OCR run produced for a document.

## Config

- **Document type** — defines how a kind of document (e.g. "Bancolombia statement") is
  recognized and extracted. Created by showing an AI a sample document; it proposes the
  extraction prompt + JSON schema, which are stored and reused for every future document of
  that type.

## How processing works

1. A document lands in Drive → the server's webhook fires.
2. A fast/cheap AI call classifies the document against the active document types.
3. The OCR engine (a multimodal AI call) extracts fields using that type's prompt + schema.
4. The result is persisted as the document's extracted data.

## Stack

- `apps/server` — Python 3.12 + FastAPI + `uv`. OCR/classification via Anthropic (Claude vision).
  Drive access via `google-api-python-client`.
- `apps/web` — Nuxt (Vue) + Nuxt UI + `bun`. Talks to the server's HTTP API; will also handle
  Drive/Sheets integration (uploading documents, exporting extracted data).
- Root: `bun` workspaces (JS side only — `apps/server` is managed independently via `uv`).

### Logging

`infrastructure/config/logging.py` is the single place logging is set up, called from
`main.py` before anything else. `ACCOUNTANT_LOG_LEVEL` sets the application's level (the
`server.*` loggers); uvicorn's access log deliberately stays at INFO so DEBUG does not drown
in it. `ACCOUNTANT_LOG_FILE` switches from stderr to a rotating file, and
`ACCOUNTANT_LOG_FORMAT=json` emits one JSON object per line. Use module-level
`logging.getLogger(__name__)` in infrastructure; keep domain and application free of it.

### Running the server during a login

`uv run server` autoreloads, which restarts the process on every file change and
therefore drops the in-memory repositories mid-flow — an OAuth callback can land on a
server that no longer remembers the `state` it issued, or the session it just stored.
Use `uv run server-noreload` (`bun run server:serve`) while exercising the login, or
configure `ACCOUNTANT_FIRESTORE_PROJECT` so sessions outlive a restart.

## Architecture — hexagonal, in both apps

Both `apps/server` and `apps/web` follow ports & adapters, SOLID-first:

- **domain/** — entities and value objects. No framework imports, no I/O.
- **application/** — use cases (one class per use case, single responsibility) and **ports**
  (interfaces/Protocols) that use cases depend on. Depends only on `domain/`.
- **infrastructure/** — adapters implementing the ports (Claude clients, Google Drive, HTTP
  repositories, in-memory/DB repositories) and the driving side (FastAPI routers, Nuxt
  pages/composables). This is the only layer allowed to import frameworks/SDKs.

Dependency rule: `infrastructure` → `application` → `domain`, never the other way. New
integrations (a DB, a different OCR/LLM provider, a different storage) are new adapters behind
an existing port — the use cases don't change.

Persistence is **Firestore**
(`apps/server/src/server/infrastructure/adapters/firestore_repositories.py`) for clients,
documents, document types, extracted data and login sessions. Document *files* themselves stay
in Google Drive (`GoogleDriveStorage`); Firestore holds only their metadata and extracted
fields. With `ACCOUNTANT_FIRESTORE_PROJECT` unset the server falls back to the in-memory
adapters (`in_memory_repositories.py`), which is what the tests use — both sit behind the same
`domain/ports`, so use cases never change.

### Google login

Users sign in with Google via the **authorization-code** flow, owned entirely by `apps/server`
(`infrastructure/api/routers/auth.py` + `adapters/google_oauth_client.py`). The browser never
sees an access token: the server holds the access *and* refresh tokens, keyed by an opaque
session id delivered as an httpOnly cookie, and renews the access token on demand
(`GetGoogleSession`). This is what makes a login survive reloads, and it is the same grant the
server will use to read a user's Drive on their behalf.

Authentication is not authorization: `ACCOUNTANT_ALLOWED_SIGN_INS` (emails and/or `@domains`)
gates who may establish a session at all, and it is empty by default so a misconfigured deploy
locks everyone out rather than letting any Google account read the clients' tax data. Every
business router carries `require_session`; only `/health` and the Drive webhook (guarded by its
own shared secret) are open.

The `state` nonce is stored in its own short-lived cookie and compared in the callback, so a
forged callback cannot establish a session. Sessions live in the `sessions` Firestore
collection and hold refresh tokens — never expose it through an API, and deny all client access
in its security rules.

### Talking to Anthropic

`infrastructure/providers/` is a second, lower-level abstraction that sits *inside*
infrastructure (not `domain/ports` — it's a transport detail, not a business capability):

- `ai_provider.py` — the `AIProvider` `Protocol` (`create_message(...)`) that the three
  Claude-backed adapters (`ClaudeDocumentClassifier`, `ClaudeOcrEngine`,
  `ClaudeDocumentTypeConfigurator`) depend on.
- `anthropic_http_client.py` — the one place that calls `httpx` against the Messages API:
  URL/version/beta-header constants and header/auth builders. No SDK, no error classification.
- `anthropic_provider.py` — `AnthropicProvider`, the `AIProvider` implementation built on the
  above. Auth (`get_auth_mode()`) is read directly from the process env, not an
  `ACCOUNTANT_`-prefixed setting: `ANTHROPIC_API_KEY` (a standard, billed key — the right
  choice for a server, and preferred when both are set) or, only as a local-dev fallback when
  no key is configured, `CLAUDE_CODE_OAUTH_TOKEN` (reuses Claude Code/subscription auth; the
  request then requires the Claude Code identifying system block to be accepted).

All prompt text (system prompts + instruction templates) lives in
`apps/server/src/server/infrastructure/config/prompts.yaml`, loaded via
`infrastructure/config/prompts.py::get_prompts()` via `importlib.resources` (it ships inside the
package on purpose) — edit the YAML to iterate on prompts without touching adapter code. Per-document-type `extraction_prompt`/`extraction_schema`
(the Config UI output) stay on the `DocumentType` entity itself; the YAML only holds the
system-level prompts these adapters always send.

## Conventions

- **All code (identifiers, comments, commit messages) is in English.** User-facing text is
  never hardcoded — it goes through i18n.
  - `apps/web`: `@nuxtjs/i18n`, locale files in `apps/web/i18n/locales/*.json` (`es` is the
    default locale, `en` is the fallback). Use `useI18n().t(...)` in components, never inline
    Spanish/English strings in templates.
  - `apps/server`: API payload keys are snake_case (see `infrastructure/api/schemas.py`); the
    server has no UI-facing strings today.
- Python identifiers/payload keys: snake_case. TypeScript: camelCase, `PascalCase` for
  types/classes.
- **Every breadcrumb crumb should be navigable.** `AppBreadcrumb.vue` builds its trail from
  the URL alone, so a segment with no page of its own (e.g. `/documents` has no index) reads
  as dead text unless the page that *does* have the context sets a `linkTo` override via
  `useBreadcrumbLabels().setLabel(path, label, linkTo)` — see `documents/[id].vue`, which
  points its "documents" crumb at the document's owning client page. Only fall back to a
  non-clickable crumb when there is truly nowhere sensible to send the reader.

## Commands

```bash
# web (apps/web)
bun run dev / build / lint / typecheck / test

# server (apps/server)
uv run server                              # dev server (uvicorn --reload)
uv run server-noreload                     # same, without autoreload (see below)
uv run ruff format . && uv run ruff check --fix .
uv run pytest

# from repo root
bun run web:dev / web:lint / web:test
bun run server:dev / server:serve / server:lint / server:test
bun run lint   # both apps
bun run test   # both apps
```

Follow the global pre-push checklist (lint + tests for every changed package) before any
`git push` — see `~/.claude/CLAUDE.md`.
