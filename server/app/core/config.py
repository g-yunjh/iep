from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys / model settings
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_CHAT_MODEL")
    llm_cache_ttl_sec: int = Field(default=600, alias="LLM_CACHE_TTL_SEC")
    local_embedding_model: str = Field(
        default="jhgan/ko-sroberta-multitask",
        alias="LOCAL_EMBEDDING_MODEL",
    )

    # NEIS settings
    neis_api_key: str | None = Field(default=None, alias="NEIS_API_KEY")
    neis_atpt_code: str | None = Field(default=None, alias="NEIS_ATPT_CODE")
    neis_school_code: str | None = Field(default=None, alias="NEIS_SCHOOL_CODE")
    neis_base_url: str = Field(default="https://open.neis.go.kr/hub", alias="NEIS_BASE_URL")
    neis_http_timeout_sec: float = Field(default=10.0, alias="NEIS_HTTP_TIMEOUT_SEC")
    neis_dismissal_7_plus: str = Field(default="16:15", alias="NEIS_DISMISSAL_7_PLUS")
    neis_dismissal_6: str = Field(default="15:20", alias="NEIS_DISMISSAL_6")
    neis_dismissal_default: str = Field(default="14:30", alias="NEIS_DISMISSAL_DEFAULT")

    # API behavior defaults
    career_search_default_current_skills: str = Field(
        default="",
        alias="CAREER_SEARCH_DEFAULT_CURRENT_SKILLS",
    )

    # DB settings
    sqlalchemy_database_url: str = Field(
        default="sqlite:///./iep.db",
        alias="SQLALCHEMY_DATABASE_URL",
    )

    @property
    def resolved_google_api_key(self) -> str | None:
        return self.google_api_key or self.gemini_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
