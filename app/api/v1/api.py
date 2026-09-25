from fastapi import APIRouter
from app.api.v1.endpoints import users, scout_actions, players, sync

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(scout_actions.router, prefix="/scout-actions", tags=["Dados Mestre - Scouts"])
api_router.include_router(players.router, prefix="/players", tags=["Jogadores e Scores"])
api_router.include_router(sync.router, prefix="/sync", tags=["Sincronização"])
