"""Configuration for the intelligence engine — loaded from environment or .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_dir = Path(__file__).resolve().parent.parent
_root_dir = _backend_dir.parent
_env_files = [
    str(_backend_dir / ".env"),
    str(_root_dir / ".env"),
    ".env",
]


class IntelligenceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files,
        extra="ignore",
        case_sensitive=False,
    )

    # API Keys & Credentials
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    # Centralized LLM Gateway (Bifrost)
    BIFROST_BASE_URL: str = "http://localhost:8088"
    BIFROST_API_KEY: str = ""
    BIFROST_MODEL: str = "gemini/gemini-3.5-flash-lite"

    # Provider & Model Selection
    LLM_PROVIDER: str = "bifrost"  # "bifrost" | "gemini" | "groq" | "openai"
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_MODEL: str = "gpt-4o-mini"
    INTELLIGENCE_LLM_MODEL: str = ""
    INTELLIGENCE_LLM_TEMPERATURE: float = 0.1

    # Network & Retry Policies
    LLM_TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE: float = 1.5
    RETRY_BACKOFF_MAX: float = 10.0

    # Search Configuration
    SEARCH_TIMEOUT_SECONDS: int = 15
    SEARCH_MAX_RESULTS: int = 10

    # Batching Budgets
    MAX_ARTICLES_PER_BATCH: int = 15
    MAX_CLAIMS_PER_BATCH: int = 20
    MAX_CHARS_PER_BATCH: int = 24000

    # Caching Layer
    ENABLE_LLM_CACHE: bool = True
    CACHE_TTL_SECONDS: int = 86400  # 24 hours

    # Mode: Set False for live AI research, True for fast offline testing
    INTELLIGENCE_FIXTURE_MODE: bool = True

    @property
    def LLM_MODEL(self) -> str:
        if self.INTELLIGENCE_LLM_MODEL:
            return self.INTELLIGENCE_LLM_MODEL
        if self.LLM_PROVIDER == "bifrost":
            return self.BIFROST_MODEL or f"gemini/{self.GEMINI_MODEL}"
        if self.LLM_PROVIDER == "gemini":
            return self.GEMINI_MODEL
        elif self.LLM_PROVIDER == "groq":
            return self.GROQ_MODEL
        elif self.LLM_PROVIDER == "openai":
            return self.OPENAI_MODEL
        return self.BIFROST_MODEL

    @property
    def LLM_TEMPERATURE(self) -> float:
        return self.INTELLIGENCE_LLM_TEMPERATURE

    @property
    def USE_FIXTURE_MODE(self) -> bool:
        return self.INTELLIGENCE_FIXTURE_MODE


intelligence_settings = IntelligenceSettings()
