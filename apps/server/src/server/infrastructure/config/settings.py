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

    # Cookies are only marked Secure over HTTPS; local dev runs on plain http.
    session_cookie_secure: bool = False

    # Firestore project holding clients, documents, document types, extracted
    # data and sessions. Left empty, the server falls back to in-memory
    # repositories, which lose everything on restart.
    firestore_project: str = ""
    firestore_database: str = "(default)"
