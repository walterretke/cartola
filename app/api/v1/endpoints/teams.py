from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.team_builder_service import TeamBuilderService

router = APIRouter()

@router.post("/generate")
def generate_teams(
    season_year: int = Query(..., description="Ano da temporada (ex: 2024)"),
    round_number: int = Query(..., description="Número da rodada (ex: 5)"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Gatilha a inteligência artificial para montar as 4 estratégias de times 
    da rodada (Principal, Alternativo, Valorização e Aposta).
    Os times gerados são salvos no banco de dados e retornados na resposta.
    """
    builder = TeamBuilderService(db)
    try:
        teams = builder.generate_teams_for_round(season_year, round_number)
        return {
            "status": "success",
            "message": f"Times gerados para a rodada {round_number} de {season_year}",
            "data": teams
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
