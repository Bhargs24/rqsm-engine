"""
Application Configuration
Loads settings from environment variables
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # LLM Provider Configuration
    llm_provider: str = Field(default="huggingface", alias="LLM_PROVIDER")
    
    # Hugging Face (FREE)
    huggingface_api_key: Optional[str] = Field(default=None, alias="HUGGINGFACE_API_KEY")
    huggingface_model: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.2",
        alias="HUGGINGFACE_MODEL"
    )
    
    # Ollama (FREE - local)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama2", alias="OLLAMA_MODEL")
    
    # Google Gemini (FREE tier)
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-pro", alias="GEMINI_MODEL")
    
    # OpenAI (PAID - optional)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", alias="OPENAI_MODEL")
    
    # LLM Settings
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=500, alias="LLM_MAX_TOKENS")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./data/rqsm_engine.db",
        alias="DATABASE_URL"
    )
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # Role Assignment Parameters
    role_score_alpha: float = Field(default=0.4, alias="ROLE_SCORE_ALPHA")
    role_score_beta: float = Field(default=0.3, alias="ROLE_SCORE_BETA")
    role_score_gamma: float = Field(default=0.3, alias="ROLE_SCORE_GAMMA")
    
    # State Machine Configuration
    transition_delay_turns: int = Field(default=3, alias="TRANSITION_DELAY_TURNS")
    hysteresis_window_turns: int = Field(default=7, alias="HYSTERESIS_WINDOW_TURNS")
    reallocation_threshold: float = Field(default=0.7, alias="REALLOCATION_THRESHOLD")
    
    # Session Configuration
    max_context_window: int = Field(default=10, alias="MAX_CONTEXT_WINDOW")
    session_timeout_minutes: int = Field(default=30, alias="SESSION_TIMEOUT_MINUTES")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
