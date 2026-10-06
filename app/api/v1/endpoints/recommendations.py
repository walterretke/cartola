from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.projection import ProjectionResponse
from app.services.recommendation_engine import RecommendationEngine
from app.services.round_service import RoundService

router = APIRouter()


def _current_round(db: Session) -> int:
    current = RoundService(db).current_round_number()
    if current is None:
        raise HTTPException(status_code=404, detail="Nenhuma rodada cadastrada. Atualize os dados primeiro.")
    return current


@router.get("/round", response_model=List[ProjectionResponse])
def get_recommendations_for_round(
    round: Optional[int] = Query(None, ge=1, le=38, description="Rodada. Se vazio, usa a rodada atual."),
    position: Optional[str] = Query(None, description="Goleiro, Lateral, Zagueiro, Meia, Atacante ou Tecnico"),
    status: Optional[List[int]] = Query(None, description="Status do Cartola (7=Provável, 2=Dúvida...)"),
    limit: int = Query(50, ge=1, le=800),
    db: Session = Depends(get_db),
):
    """Projeções de todos os jogadores da rodada, da maior para a menor."""
    engine = RecommendationEngine(db=db)
    return engine.get_recommendations_for_round(round or _current_round(db), position=position, statuses=status, limit=limit)


@router.get("/fixture/{fixture_id}", response_model=List[ProjectionResponse])
def get_recommendations_for_fixture(
    fixture_id: int,
    limit: int = Query(11, ge=1, le=80),
    db: Session = Depends(get_db),
):
    """Projeções dos jogadores dos dois times de uma partida."""
    engine = RecommendationEngine(db=db)
    recs = engine.get_recommendations_for_fixture(fixture_id, limit=limit)
    if not recs:
        raise HTTPException(status_code=404, detail="Partida não encontrada ou sem jogadores sincronizados.")
    return recs


@router.get("/player/{player_id}/next", response_model=ProjectionResponse)
def get_player_next_projection(
    player_id: int,
    round: Optional[int] = Query(None, ge=1, le=38, description="Rodada. Se vazio, usa a rodada atual."),
    db: Session = Depends(get_db),
):
    """Projeção do jogador para o próximo jogo do time dele, com os fatores que a compõem."""
    engine = RecommendationEngine(db=db)
    rec = engine.get_next_projection(player_id, round or _current_round(db))
    if not rec:
        raise HTTPException(status_code=404, detail="Jogador sem jogo nessa rodada ou sem dados suficientes.")
    return rec


@router.get("/player/{player_id}/fixture/{fixture_id}", response_model=ProjectionResponse)
def get_player_contextual_score(
    player_id: int,
    fixture_id: int,
    db: Session = Depends(get_db),
):
    """Projeção detalhada de um jogador em uma partida específica."""
    engine = RecommendationEngine(db=db)
    rec = engine.calculate_esc_for_player(player_id, fixture_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Jogador ou partida não encontrados.")
    return rec
