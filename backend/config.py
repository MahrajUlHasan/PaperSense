"""PaperSense backend settings, read from backend/.env (see .env.example)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """All settings, each overridable by an environment variable of the same name.

    Keys in .env that no setting uses (for example from older versions) are ignored.
    `hf_token` is optional and only makes model downloads from Hugging Face faster.

    LLM providers: visitors bring their own keys (Settings → API keys in the UI).
    `allow_server_key` + `server_gemini_api_key` are for LOCAL DEVELOPMENT ONLY: they use
    your own key when a request has none. Never enable them on a public deployment.

    `gemini_thinking_budget`: Gemini 2.5 "thinking" tokens count against the output limit.
    None = model default, 0 = off (Flash only), e.g. 1024 = small budget.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PaperSense"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "papersense_v2_dev"

    data_dir: Path = BACKEND_DIR / "data"

    ocr_mode: Literal["off", "auto", "on"] = "off"
    formula_mode: Literal["off", "local", "gemini"] = "local"
    picture_scale: float = 2.0
    docling_threads: int = 4
    min_page_coverage: float = 0.5

    dense_model: str = "BAAI/bge-base-en-v1.5"
    chunk_max_tokens: int = 400
    top_k: int = 6
    prefetch_limit: int = 40

    default_provider: Literal["gemini", "groq", "openrouter"] = "gemini"
    gemini_model: str = "gemini-3.5-flash"
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_model: str = "google/gemma-4-31b-it:free"
    vision_model: str = "gemini-3.5-flash-lite"
    vision_rpm: int = 8
    rewrite_followups: bool = True
    llm_max_output_tokens: int = 4096
    gemini_thinking_budget: Optional[int] = None

    allow_server_key: bool = False
    server_gemini_api_key: Optional[str] = None

    hf_token: Optional[str] = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
