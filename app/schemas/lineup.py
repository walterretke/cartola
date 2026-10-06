from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.projection import ProjectionResponse


class LineupPlayer(ProjectionResponse):
    """Jogador dentro de uma escalação: projeção + dados usados pelo montador."""
    price: float = 0.0
    last_score: float = 0.0
    std_deviation: float = 0.0
    team_id: Optional[int] = None


class Squad(BaseModel):
    formation: Optional[str] = None
    players: List[LineupPlayer] = []
    reserves: List[LineupPlayer] = []
    captain_id: Optional[int] = None
    luxury_reserve_id: Optional[int] = None
    cost: float = 0.0
    expected_score: float = 0.0


class LineupResponse(BaseModel):
    id: Optional[int] = None
    season_year: int
    round_number: int
    strategy: str
    formation: str
    expected_total_score: float
    expected_total_cost: float
    created_at: Optional[datetime] = None
    squad: Squad


class LineupBuildResponse(BaseModel):
    season_year: int
    round_number: int
    formation: str
    budget: Optional[float] = None
    lineups: List[LineupResponse]
