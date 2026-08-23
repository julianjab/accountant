from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from server.infrastructure.api.routers import clients, document_types, documents, drive_webhook
from server.infrastructure.providers.anthropic_http_client import get_auth_mode

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_auth_mode()  # fail fast on startup instead of on the first AI call
    yield


app = FastAPI(title="Accountant OCR Server", lifespan=lifespan)

app.include_router(clients.router)
app.include_router(document_types.router)
app.include_router(documents.router)
app.include_router(drive_webhook.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
