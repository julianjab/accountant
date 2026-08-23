from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ACCOUNTANT_",
        # The .env also carries unprefixed Anthropic auth vars, read straight
        # from the process env by anthropic_http_client; they are not settings.
        extra="ignore",
    )

    anthropic_model: str = "claude-sonnet-5"
    google_service_account_file: str = ""
    google_drive_webhook_secret: str = ""

    # Google login (authorization-code flow). The client id/secret come from the
    # same "Web application" OAuth client; the redirect URI must be registered on
    # it verbatim.
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Where to send the browser once the callback has established the session,
    # and the origin allowed to call this API with credentials.
    web_app_url: str = "http://localhost:3000"

    # Who may sign in. Comma-separated emails and/or @domains; empty means
    # nobody, so a misconfigured deploy locks everyone out instead of letting
    # any Google account read the clients' tax data.
    allowed_sign_ins: str = ""

    # Cookies are only marked Secure over HTTPS; local dev runs on plain http.
    session_cookie_secure: bool = False

    # Cross-site deploys (web and API on different registrable domains) need
    # SameSite=None, which browsers only accept together with Secure. "strict"
    # is deliberately not offered: the browser would withhold the state cookie
    # on the way back from accounts.google.com, so the callback could never
    # succeed.
    session_cookie_samesite: Literal["lax", "none"] = "lax"

    # Sessions stop being valid this long after sign-in regardless of how alive
    # the refresh token is, so a stolen one cannot be used forever.
    session_max_age_days: int = 30

    def allows(self, email: str) -> bool:
        entries = [e.strip().lower() for e in self.allowed_sign_ins.split(",") if e.strip()]
        candidate = email.lower()
        return any(
            candidate == entry or (entry.startswith("@") and candidate.endswith(entry))
            for entry in entries
        )

    # Firestore project holding clients, documents, document types, extracted
    # data and sessions. Left empty, the server falls back to in-memory
    # repositories, which lose everything on restart.
    firestore_project: str = ""
    firestore_database: str = "(default)"

    # This server's own publicly reachable base URL, needed because Drive push
    # notifications require an HTTPS address to call back into; in dev it points
    # at an ngrok/cloudflared tunnel in front of localhost:8000.
    server_public_url: str = "http://localhost:8000"
