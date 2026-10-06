from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cartola Analytics API"
    API_V1_STR: str = "/api/v1"

    # Origens liberadas no CORS (JSON no .env, ex: ["https://meusite.com"])
    FRONTEND_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # Banco de Dados
    DATABASE_URL: str = "sqlite:///./cartola.db"
    
    # API-Football
    API_FOOTBALL_KEY: str = ""
    API_FOOTBALL_BASE_URL: str = "https://v3.football.api-sports.io"
    
    # Brasileirão
    BRASILEIRAO_LEAGUE_ID: int = 71
    BRASILEIRAO_SEASON: int = 2024

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
