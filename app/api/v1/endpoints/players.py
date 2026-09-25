from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_db
from app.models.player import Player
from app.models.player_score import PlayerScore
from app.schemas.player import PlayerListItemResponse, PlayerDetailResponse

router = APIRouter()

@router.get("/", response_model=List[PlayerListItemResponse])
def list_players(
    position: Optional[str] = Query(None, description="Filtrar por posição: Goalkeeper, Defender, Midfielder, Attacker"),
    team: Optional[str] = Query(None, description="Filtrar por nome do clube"),
    sort_by: str = Query("smart_score", description="Ordenar por: smart_score, avg_points, avg_points_home, avg_points_away, consistency_index"),
    search: Optional[str] = Query(None, description="Buscar por nome do atleta"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Lista os atletas do Brasileirão com seus scores calculados,
    médias em casa/fora e índices de oscilação e regularidade.
    """
    query = db.query(Player).join(Player.score, isouter=True)

    if position:
        query = query.filter(Player.position.ilike(f"%{position}%"))
    if team:
        query = query.filter(Player.team_name.ilike(f"%{team}%"))
    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))

    # Ordenação
    sort_col = getattr(PlayerScore, sort_by, PlayerScore.smart_score)
    query = query.order_by(desc(sort_col).nullslast())

    return query.limit(limit).all()

@router.get("/{player_id}", response_model=PlayerDetailResponse)
def get_player_details(
    player_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna a ficha detalhada de um atleta com o histórico completo de partidas,
    destacando o desempenho em jogos em casa vs fora e scouts de cada partida.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")
    return player
