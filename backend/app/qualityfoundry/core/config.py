from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QF_", env_file=".env", extra="ignore")

    ENV: str = Field(default="dev")
    DB_URL: str = Field(default="sqlite:///./qualityfoundry.db")
    ARTIFACT_DIR: str = Field(default="./artifacts")

    # Optional integrations
    QDRANT_URL: str | None = Field(default=None)

settings = Settings()
