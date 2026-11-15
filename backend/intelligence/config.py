"""Configuration for the intelligence engine — loaded from environment or .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class IntelligenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    TAVILY_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    LLM_PROVIDER: str = "groq"
    INTELLIGENCE_LLM_MODEL: str = "openai/gpt-oss-120b"
    INTELLIGENCE_LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT_SECONDS: int = 30

    SEARCH_TIMEOUT_SECONDS: int = 15
    SEARCH_MAX_RESULTS: int = 10
    MAX_RETRIES: int = 2

    INTELLIGENCE_FIXTURE_MODE: bool = True  # True until real API keys are configured

    @property
    def LLM_MODEL(self) -> str:
        return self.INTELLIGENCE_LLM_MODEL

    @property
    def LLM_TEMPERATURE(self) -> float:
        return self.INTELLIGENCE_LLM_TEMPERATURE

    @property
    def USE_FIXTURE_MODE(self) -> bool:
        return self.INTELLIGENCE_FIXTURE_MODE


intelligence_settings = IntelligenceSettings()
