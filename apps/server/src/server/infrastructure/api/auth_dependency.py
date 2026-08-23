from fastapi import Cookie, Depends, HTTPException

from server.application.use_cases import GetGoogleSession
from server.domain.entities import GoogleSession
from server.domain.ports import OAuthTransportError
from server.infrastructure.api.deps import get_google_session_use_case

SESSION_COOKIE = "accountant_session"


def require_session(
    accountant_session: str | None = Cookie(default=None),
    use_case: GetGoogleSession = Depends(get_google_session_use_case),
) -> GoogleSession:
    """Rejects a request that carries no live session.

    Applied to every business router: the documents these endpoints expose carry
    tax data, so an open API would make the login decorative.
    """
    if accountant_session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        session = use_case.execute(accountant_session)
    except OAuthTransportError:
        # Google is unreachable; the session may well still be good.
        raise HTTPException(status_code=503, detail="Could not verify the session") from None

    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return session
