from dotenv import load_dotenv
from fastapi import FastAPI

from server.infrastructure.api.routers import clients, document_types, documents, drive_webhook

load_dotenv()

app = FastAPI(title="Accountant OCR Server")

app.include_router(clients.router)
app.include_router(document_types.router)
app.include_router(documents.router)
app.include_router(drive_webhook.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
