from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.infrastructure.api.deps import get_settings
from server.infrastructure.api.routers import (
    auth,
    clients,
    clients_import,
    document_types,
    documents,
    drive_webhook,
)
from server.infrastructure.config.logging import configure_logging
from server.infrastructure.providers.anthropic_http_client import get_auth_mode

load_dotenv()
configure_logging(get_settings())


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_auth_mode()  # fail fast on startup instead of on the first AI call
    yield


app = FastAPI(title="Accountant OCR Server", lifespan=lifespan)

# The web app authenticates with an httpOnly session cookie, which the browser
# only sends cross-origin when the origin is allowlisted and credentials are on.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(clients_import.router)
app.include_router(document_types.router)
app.include_router(documents.router)
app.include_router(drive_webhook.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
