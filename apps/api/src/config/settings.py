from __future__ import annotations
from pydantic_settings import BaseSettings
from typing import Literal, List, Optional
from pydantic import BaseModel, Field, SecretStr
from functools import lru_cache
from typing import Any, Tuple
from pydantic import field_validator, computed_field

try:
    from pydantic_settings import SettingsConfigDict
except Exception:
    from pydantic import BaseSettings  # type: ignore
    class SettingsConfigDict(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # print a warning if pydantic_settings is not found
            print("Warning: pydantic_settings not found, using pydantic.BaseSettings instead")

class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json: bool = False
    include_request_id: bool = False

class HTTPXConfig(BaseModel):
    timeout: float = 15.0
    max_keepalive: int = 50
    max_connections: int = 100
    user_agent: str = "QuantumX-API/v1.0"

class RedisConfig(BaseModel):
    enabled: bool = False
    url: Optional[str] = None
    pool_size: int = 10

class PostgreConfig(BaseModel):
    enabled: bool = False
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: Optional[SecretStr] = None
    db: str = "quantumx"
    dsn: Optional[str] = None
    pool_size: int = 10

class FeatureFlags(BaseModel):
    enable_rag: bool = True
    enable_search_cache: bool = True
    enable_smart_buyer: bool = True
    enable_multi_agent: bool = False
    enable_yaml_workflow: bool = False

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="QX_",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "QuantumX API"
    APP_VERSION: str = "v1.0"

    ENV: Literal["dev", "staging", "prod"] = "dev"
    DEBUG: bool = False

    LOGGING: LoggingConfig = LoggingConfig()

    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    HTTPX: HTTPXConfig = HTTPXConfig()

    RATE_LIMIT_GLOBAL: int = 120
    RATE_LIMIT_PER_IP: int = 30
    REQUEST_BODY_LIMIT_MD: int = 8

    SENTRY_DSN: Optional[str] = None

    REDIS: RedisConfig = RedisConfig()
    POSTGRES: PostgreConfig = PostgreConfig()

    LLM_PROVIDER: Literal["openai", "anthropic", "gemini", "ollama", "local"] = "openai"
    OPENAI_API_KEY: Optional[SecretStr] = None
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    GEMINI_API_KEY: Optional[SecretStr] = None
    OLLAMA_API_KEY: Optional[SecretStr] = None
    LOCAL_LLM_PATH: Optional[str] = None

    OPEN_SEARCH_URL: Optional[str] = None
    OPEN_SEARCH_USERNAME: Optional[str] = None
    OPEN_SEARCH_PASSWORD: Optional[SecretStr] = None

    FEATURES: FeatureFlags = FeatureFlags()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, value: Any) -> List[str]:
        if value is None:
            return ["*"]
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str):
            s = value.strip()
        if not s:
            return ["*"]
            # Handle wildcard
            if s == "*":
                return ["*"]
            # Handle JSON array string
        if s.startswith("["):
            try:
                import json
                arr = json.loads(s)
                return [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                pass
            # Handle comma-separated values
        return [x.strip() for x in s.split(",") if x.strip()]
        return ["*"]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _derive_debug(cls, v: Any, info) -> bool:
        if isinstance(v, bool):
            return v
        env = (info.data.get("ENV") or "dev").lower()
        return env == "dev"

    @computed_field
    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    @computed_field
    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"

    @computed_field
    @property
    def HTTPX_LIMITS(self) -> Tuple[int, int]:
        return int(self.HTTPX.max_keepalive), int(self.HTTPX.max_connections)

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.POSTGRES.dsn:
            return self.POSTGRES.dsn
        pw = self.POSTGRES.password.get_secret_value() if isinstance(self.POSTGRES.password, SecretStr) else (self.POSTGRES.password or "")
        return f"postgresql+psycopg://{self.POSTGRES.user}:{pw}@{self.POSTGRES.host}:{self.POSTGRES.port}/{self.POSTGRES.db}"

    @computed_field
    @property
    def ANY_CORS(self) -> bool:
        return self.CORS_ORIGINS == ["*"]

    @computed_field
    @property
    def OPENAI_ENABLED(self) -> bool:
        return self.LLM_PROVIDER == "openai" and bool(self.OPENAI_API_KEY)

    @computed_field
    @property
    def ANTHROPIC_ENABLED(self) -> bool:
        return self.LLM_PROVIDER == "anthropic" and bool(self.ANTHROPIC_API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()