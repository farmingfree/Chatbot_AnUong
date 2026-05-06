from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/food_advisor"
    REDIS_URL: str = "redis://localhost:6379"
    OPENAI_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    NEXTAUTH_SECRET: str = "your-secret-key-change-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
