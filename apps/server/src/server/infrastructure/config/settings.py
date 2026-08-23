from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ACCOUNTANT_")

    anthropic_model: str = "claude-sonnet-5"
    google_service_account_file: str = ""
    google_drive_webhook_secret: str = ""
