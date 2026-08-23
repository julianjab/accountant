import os


def _run(*, reload: bool) -> None:
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=os.getenv("ACCOUNTANT_HOST", "127.0.0.1"),
        port=int(os.getenv("ACCOUNTANT_PORT", "8000")),
        reload=reload,
    )


def main() -> None:
    _run(reload=True)


def serve() -> None:
    """Run without autoreload.

    Reload restarts the process on every file change, which drops the in-memory
    repositories mid-flow — an OAuth callback can land on a server that no longer
    remembers the state it issued. Use this while exercising the login.
    """
    _run(reload=False)
