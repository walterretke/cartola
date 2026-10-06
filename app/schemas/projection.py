from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class PlayerRef(BaseModel):
    id: int
    name: str
    position: str
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    team_logo_url: Optional[str] = None
    photo_url: Optional[str] = None
    price: float = 0.0
    status_id: Optional[int] = None
    status_label: Optional[str] = None


class ProjectionFactor(BaseModel):
    """Um degrau da projeção. A soma de `impact_pts` de todos os fatores é a projeção final."""
    key: str
    label: str
    detail: str
    multiplier: Optional[float] = None
    impact_pts: float


class ProjectionContext(BaseModel):
    matches_played: int = 0
    home_matches: int = 0
    away_matches: int = 0
    avg_points: float = 0.0
    avg_points_home: float = 0.0
    avg_points_away: float = 0.0
    avg_minutes: float = 0.0
    ema_points: float = 0.0
    trend: str = "stable"
    consistency_index: float = 0.0


class ProjectionResponse(BaseModel):
    """Projeção de pontos de um atleta para uma partida."""
    model_config = ConfigDict(extra="ignore")

    player: PlayerRef
    fixture_id: Optional[int] = None
    match_date: Optional[datetime] = None
    is_home: bool
    opponent_id: Optional[int] = None
    opponent: Optional[str] = None
    opponent_logo_url: Optional[str] = None
    smart_score: float = 0.0
    expected_score_contextual: float
    sg_probability: Optional[float] = None
    reasoning: List[str] = []
    factors: List[ProjectionFactor] = []
    context: Optional[ProjectionContext] = None
