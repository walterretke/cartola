from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.seed import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa tabelas e semeia dados mestre de pontuação do Cartola
    try:
        init_db()
    except Exception as e:
        print(f"Aviso na inicialização do banco: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend para cálculo de scores inteligentes e escalações do Cartola FC baseado em scouts reais e oscilação casa/fora.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "CartolaAI Backend Operacional",
        "docs_url": "/docs",
        "endpoints": {
            "scout_actions": f"{settings.API_V1_STR}/scout-actions",
            "players": f"{settings.API_V1_STR}/players",
            "sync": f"{settings.API_V1_STR}/sync/run"
        }
    }
