from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./local.db"
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    # service_role (legacy JWT) or sb_secret_ key: backend-only access to Supabase Storage
    supabase_service_key: str = ""
    storage_bucket: str = "achievement-files"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_timeout_s: float = 8.0
    llm_mentor_timeout_s: float = 25.0  # a mentor turn may chain several tool calls
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
