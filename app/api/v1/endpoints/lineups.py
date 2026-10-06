from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.cartola import DEFAULT_FORMATION, FORMATIONS
from app.core.config import settings
from app.models.team_recommendation import TeamRecommendation
from app.schemas.lineup import LineupBuildResponse, LineupResponse
from app.services.round_service import RoundService
from app.services.team_builder_service import STRATEGIES, TeamBuilderService

router = APIRouter()


def lineup_to_dict(rec: TeamRecommendation) -> dict:
    squad = dict(rec.squad_data or {})
    squad.setdefault("formation", rec.formation)
    return {
        "id": rec.id,
        "season_year": rec.season_year,
        "round_number": rec.round_number,
        "strategy": rec.strategy,
        "formation": rec.formation,
        "expected_total_score": rec.expected_total_score,
        "expected_total_cost": rec.expected_total_cost,
        "created_at": rec.created_at,
        "squad": squad,
    }


def _resolve_round(db: Session, round_number: Optional[int]) -> int:
    if round_number:
        return round_number
    current = RoundService(db).current_round_number()
    if current is None:
        raise HTTPException(status_code=404, detail="Nenhuma rodada cadastrada. Atualize os dados primeiro.")
    return current


@router.get("/formations", response_model=List[str])
def list_formations():
    """Esquemas táticos aceitos."""
    return list(FORMATIONS.keys())


@router.get("/", response_model=List[LineupResponse])
def list_lineups(
    season: int = Query(settings.BRASILEIRAO_SEASON, description="Ano da temporada"),
    round: Optional[int] = Query(None, ge=1, le=38, description="Rodada. Se vazio, usa a rodada atual."),
    db: Session = Depends(get_db),
):
    """Escalações já montadas da rodada: a mais recente de cada estratégia."""
    round_number = _resolve_round(db, round)
    rows = (
        db.query(TeamRecommendation)
        .filter(TeamRecommendation.season_year == season, TeamRecommendation.round_number == round_number)
        .order_by(TeamRecommendation.created_at.desc(), TeamRecommendation.id.desc())
        .all()
    )
    latest = {}
    for row in rows:
        latest.setdefault(row.strategy, row)
    return [lineup_to_dict(latest[s]) for s in STRATEGIES if s in latest]


@router.post("/build", response_model=LineupBuildResponse)
def build_lineups(
    season: int = Query(settings.BRASILEIRAO_SEASON, description="Ano da temporada"),
    round: Optional[int] = Query(None, ge=1, le=38, description="Rodada. Se vazio, usa a rodada atual."),
    budget: Optional[float] = Query(None, gt=0, description="Limite de cartoletas para os titulares"),
    formation: str = Query(DEFAULT_FORMATION, description="Esquema tático, ex: 4-3-3"),
    db: Session = Depends(get_db),
):
    """
    Monta as 4 escalações da rodada (Principal, Alternativo, Valorização e Aposta).
    Substitui as escalações anteriores da mesma rodada.
    """
    if formation not in FORMATIONS:
        raise HTTPException(status_code=422, detail=f"Formação inválida. Use uma de: {', '.join(FORMATIONS)}")
    round_number = _resolve_round(db, round)

    TeamBuilderService(db).generate_teams_for_round(season, round_number, max_cost=budget, formation=formation)

    saved = (
        db.query(TeamRecommendation)
        .filter(TeamRecommendation.season_year == season, TeamRecommendation.round_number == round_number)
        .all()
    )
    by_strategy = {r.strategy: r for r in saved}
    return {
        "season_year": season,
        "round_number": round_number,
        "formation": formation,
        "budget": budget,
        "lineups": [lineup_to_dict(by_strategy[s]) for s in STRATEGIES if s in by_strategy],
    }
