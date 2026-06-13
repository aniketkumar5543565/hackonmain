from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase Postgres (direct or pooler connection)
    DATABASE_URL: str

    # Supabase project URL and JWT secret for token verification
    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: str

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Groq API key for OCR and AI parsing
    GROQ_API_KEY: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
