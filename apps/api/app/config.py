from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/food_advisor"
    REDIS_URL: str = "redis://localhost:6379"
    OPENAI_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    NEXTAUTH_SECRET: str = "your-secret-key-change-in-production"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "places"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    OLLAMA_URL: str = ""
    OLLAMA_MODEL: str = "qwen2.5:7b"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    class Config:
        env_file = ".env"


settings = Settings()
