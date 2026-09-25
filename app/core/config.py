from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Mobile API"
    API_V1_STR: str = "/api/v1"
    
    # Adicionar outras configuracoes, como URL de banco de dados, JWT secrets, etc.
    # DATABASE_URI: str = "sqlite:///./test.db"

    class Config:
        case_sensitive = True

settings = Settings()
