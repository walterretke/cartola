from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.core.cartola import normalize_position
from app.models.player import Player
from app.models.player_match_stats import PlayerMatchStats
from app.models.player_score import PlayerScore
from app.schemas.player import PlayerDetailResponse, PlayerListItemResponse

router = APIRouter()

SORTABLE = {
    "smart_score": PlayerScore.smart_score,
    "avg_points": PlayerScore.avg_points,
    "avg_points_home": PlayerScore.avg_points_home,
    "avg_points_away": PlayerScore.avg_points_away,
    "consistency_index": PlayerScore.consistency_index,
    "ema_points": PlayerScore.ema_points,
    "last_5_avg": PlayerScore.last_5_avg,
    "matches_played": PlayerScore.matches_played,
    "price_cartoletas": Player.price_cartoletas,
    "name": Player.name,
}

RECENT_MATCHES = 5


def recent_scores_by_player(db: Session, player_ids: List[int], n: int = RECENT_MATCHES) -> Dict[int, List[float]]:
    """Últimas `n` pontuações de cada jogador (da mais antiga para a mais recente), em uma consulta."""
    if not player_ids:
        return {}
    rows = (
        db.query(PlayerMatchStats.player_id, PlayerMatchStats.match_cartola_score)
        .filter(PlayerMatchStats.player_id.in_(player_ids))
        .order_by(PlayerMatchStats.player_id, desc(PlayerMatchStats.match_date))
        .all()
    )
    grouped: Dict[int, List[float]] = defaultdict(list)
    for pid, score in rows:
        if len(grouped[pid]) < n:
            grouped[pid].append(round(score or 0.0, 2))
    return {pid: list(reversed(scores)) for pid, scores in grouped.items()}


@router.get("/", response_model=List[PlayerListItemResponse])
def list_players(
    response: Response,
    position: Optional[str] = Query(None, description="Goleiro, Lateral, Zagueiro, Meia, Atacante ou Tecnico"),
    team: Optional[str] = Query(None, description="Filtrar por nome do clube"),
    team_id: Optional[int] = Query(None, description="Filtrar por id do clube"),
    status: Optional[List[int]] = Query(None, description="Status do Cartola (7=Provável, 2=Dúvida, 3=Suspenso, 5=Contundido, 6=Nulo)"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    ids: Optional[List[int]] = Query(None, description="Buscar jogadores específicos (ex: comparador)"),
    search: Optional[str] = Query(None, description="Buscar por nome do atleta"),
    sort_by: str = Query("smart_score", description=f"Ordenar por: {', '.join(SORTABLE)}"),
    order: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Lista os atletas com nota geral, médias em casa e fora, regularidade,
    preço, status e as últimas pontuações. O total de resultados vai no cabeçalho X-Total-Count.
    """
    query = db.query(Player).outerjoin(PlayerScore, PlayerScore.player_id == Player.id)

    if position:
        query = query.filter(Player.position == normalize_position(position))
    if team:
        query = query.filter(Player.team_name.ilike(f"%{team}%"))
    if team_id:
        query = query.filter(Player.team_id == team_id)
    if status:
        query = query.filter(Player.cartola_status_id.in_(status))
    if min_price is not None:
        query = query.filter(Player.price_cartoletas >= min_price)
    if max_price is not None:
        query = query.filter(Player.price_cartoletas <= max_price)
    if ids:
        query = query.filter(Player.id.in_(ids))
    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))

    total = query.with_entities(func.count(Player.id)).scalar() or 0
    response.headers["X-Total-Count"] = str(total)

    sort_col = SORTABLE.get(sort_by, PlayerScore.smart_score)
    direction = asc if order == "asc" else desc
    players = (
        query.options(joinedload(Player.score))
        .order_by(direction(sort_col).nullslast(), Player.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    recent = recent_scores_by_player(db, [p.id for p in players])
    result = []
    for p in players:
        item = PlayerListItemResponse.model_validate(p)
        item.recent_scores = recent.get(p.id, [])
        result.append(item)
    return result


@router.get("/{player_id}", response_model=PlayerDetailResponse)
def get_player_details(player_id: int, db: Session = Depends(get_db)):
    """
    Ficha do atleta com o histórico completo de partidas (da mais antiga para a mais recente),
    desempenho em casa e fora, e os scouts de cada jogo.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")

    detail = PlayerDetailResponse.model_validate(player)
    detail.match_stats.sort(key=lambda m: m.match_date or datetime.min)
    detail.recent_scores = [round(m.match_cartola_score, 2) for m in detail.match_stats[-RECENT_MATCHES:]]
    return detail
