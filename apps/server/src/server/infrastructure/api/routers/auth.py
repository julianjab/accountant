import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse

from server.application.use_cases import (
    CompleteGoogleSignIn,
    GetGoogleSession,
    MissingRefreshToken,
    SignOutGoogle,
    StartGoogleSignIn,
)
from server.domain.ports import OAuthTransportError
from server.infrastructure.api.deps import (
    get_complete_google_sign_in_use_case,
    get_google_session_use_case,
    get_settings,
    get_sign_out_google_use_case,
    get_start_google_sign_in_use_case,
)
from server.infrastructure.api.schemas import GoogleUserResponse
from server.infrastructure.config.settings import Settings

router = APIRouter(prefix="/auth/google", tags=["auth"])

SESSION_COOKIE = "accountant_session"
STATE_COOKIE = "accountant_oauth_state"

# The session lives as long as the refresh token stays valid; the cookie is what
# makes the login survive a browser restart.
SESSION_MAX_AGE = 60 * 60 * 24 * 30
STATE_MAX_AGE = 60 * 10


def _set_cookie(response: Response, key: str, value: str, max_age: int, settings: Settings) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/login")
def login(
    use_case: StartGoogleSignIn = Depends(get_start_google_sign_in_use_case),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    redirect = use_case.execute()
    response = RedirectResponse(redirect.authorization_url, status_code=307)
    # Echoed back by Google and compared in the callback, so a forged callback
    # cannot establish a session.
    _set_cookie(response, STATE_COOKIE, redirect.state, STATE_MAX_AGE, settings)
    return response


@router.get("/callback")
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    accountant_oauth_state: str | None = Cookie(default=None),
    use_case: CompleteGoogleSignIn = Depends(get_complete_google_sign_in_use_case),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if error is not None or code is None:
        return RedirectResponse(f"{settings.web_app_url}?auth_error=denied", status_code=307)

    if (
        not state
        or not accountant_oauth_state
        or not secrets.compare_digest(state, accountant_oauth_state)
    ):
        return RedirectResponse(f"{settings.web_app_url}?auth_error=state", status_code=307)

    try:
        session = use_case.execute(code)
    except MissingRefreshToken:
        return RedirectResponse(f"{settings.web_app_url}?auth_error=no_refresh", status_code=307)
    except OAuthTransportError:
        return RedirectResponse(f"{settings.web_app_url}?auth_error=exchange", status_code=307)

    response = RedirectResponse(settings.web_app_url, status_code=307)
    _set_cookie(response, SESSION_COOKIE, session.id, SESSION_MAX_AGE, settings)
    response.delete_cookie(STATE_COOKIE, path="/")
    return response


@router.get("/me", response_model=GoogleUserResponse)
def me(
    accountant_session: str | None = Cookie(default=None),
    use_case: GetGoogleSession = Depends(get_google_session_use_case),
) -> GoogleUserResponse:
    if accountant_session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = use_case.execute(accountant_session)
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return GoogleUserResponse.model_validate(session.user, from_attributes=True)


@router.post("/logout", status_code=204)
def logout(
    accountant_session: str | None = Cookie(default=None),
    use_case: SignOutGoogle = Depends(get_sign_out_google_use_case),
) -> Response:
    if accountant_session is not None:
        use_case.execute(accountant_session)

    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
