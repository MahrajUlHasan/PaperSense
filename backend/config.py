"""
Configuration management for the Smart Research Paper Analyzer
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    HF_TOKEN: Optional[str] = Field(None, env="HF_TOKEN")
    
    # Qdrant Configuration
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(default="research_papers", env="QDRANT_COLLECTION_NAME")
    
    # Application Settings
    app_name: str = Field(default="Smart Research Paper Analyzer", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Model Configuration
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    embedding_provider: str = Field(
        default="openai",
        env="EMBEDDING_PROVIDER",
        description="Embedding provider: openai | langchain | gemma"
    )
    gemma_embedding_model: str = Field(
        default="models/text-embedding-004",
        env="GEMMA_EMBEDDING_MODEL",
        description="Google GenAI / LangChain embedding model name"
    )
    embedding_dimension: int = Field(
        default=1536,
        env="EMBEDDING_DIMENSION",
        description="Dimension of embedding vectors (1536 for OpenAI, 768 for Gemma/LangChain)"
    )
    gemini_model: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Vector Search Configuration
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")
    similarity_threshold: float = Field(default=0.3, env="SIMILARITY_THRESHOLD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

