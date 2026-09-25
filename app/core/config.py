from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "CartolaAI Backend"
    API_V1_STR: str = "/api/v1"
    
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
