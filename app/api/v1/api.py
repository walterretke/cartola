from fastapi import APIRouter
from app.api.v1.endpoints import users, scout_actions, players, sync, recommendations

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(scout_actions.router, prefix="/scout-actions", tags=["Dados Mestre - Scouts"])
api_router.include_router(players.router, prefix="/players", tags=["Jogadores e Scores"])
api_router.include_router(sync.router, prefix="/sync", tags=["Sincronização"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recomendações e Motor Contextual"])
from app.api.v1.endpoints import teams, rounds, fixtures, team_profiles, lineups
api_router.include_router(teams.router, prefix='/teams', tags=['Estrategias e Escalacoes'])
api_router.include_router(rounds.router, prefix='/rounds', tags=['Rodadas'])
api_router.include_router(fixtures.router, prefix='/fixtures', tags=['Jogos'])
api_router.include_router(team_profiles.router, prefix='/team-profiles', tags=['Clubes'])
api_router.include_router(lineups.router, prefix='/lineups', tags=['Escalacoes'])
