from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.recommendation_engine import RecommendationEngine

router = APIRouter()

@router.get("/fixture/{fixture_id}")
def get_recommendations_for_fixture(
    fixture_id: int,
    limit: int = Query(11, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Retorna a recomendação contextual de jogadores para uma partida específica.
    """
    engine = RecommendationEngine(db=db)
    recs = engine.get_recommendations_for_fixture(fixture_id, limit=limit)
    if not recs:
        raise HTTPException(status_code=404, detail="Partida não encontrada ou sem jogadores sincronizados.")
    return recs

@router.get("/player/{player_id}/fixture/{fixture_id}")
def get_player_contextual_score(
    player_id: int,
    fixture_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna a análise detalhada e o Expected Score Contextual (ESC) 
    para um jogador em uma partida futura.
    """
    engine = RecommendationEngine(db=db)
    rec = engine.calculate_esc_for_player(player_id, fixture_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Jogador ou partida não encontrados.")
    return rec
