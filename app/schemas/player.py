from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, computed_field

from app.core.cartola import normalize_position, status_label, team_logo_url

class PlayerScoreResponse(BaseModel):
    matches_played: int
    home_matches: int
    away_matches: int
    total_minutes: int = 0
    total_points: float
    avg_points: float
    avg_points_home: float
    avg_points_away: float
    std_deviation: float
    consistency_index: float
    min_score: float
    max_score: float
    last_3_avg: float = 0.0
    last_5_avg: float
    ema_points: float = 0.0
    trend: str = "stable"
    # Médias por scout
    avg_goals: float = 0.0
    avg_assists: float = 0.0
    avg_shots_on_target: float = 0.0
    avg_shots_off_target: float = 0.0
    avg_fouls_drawn: float = 0.0
    avg_tackles: float = 0.0
    avg_saves: float = 0.0
    avg_fouls_committed: float = 0.0
    avg_yellow_cards: float = 0.0
    avg_goals_conceded: float = 0.0
    clean_sheet_pct: float = 0.0
    # Indicadores avançados
    avg_rating: float = 0.0
    avg_passes_key: float = 0.0
    avg_dribbles_success: float = 0.0
    avg_duels_won: float = 0.0
    avg_interceptions: float = 0.0
    duel_win_pct: float = 0.0
    pass_accuracy_avg: float = 0.0
    # Potenciais
    offensive_potential: float = 0.0
    defensive_potential: float = 0.0
    discipline_risk: float = 0.0
    smart_score: float
    calculated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PlayerMatchStatsResponse(BaseModel):
    id: int
    fixture_id: int
    round_name: Optional[str] = None
    match_date: Optional[datetime] = None
    is_home: bool
    opponent_name: Optional[str] = None
    minutes_played: int
    rating: Optional[float] = None
    was_substitute: bool = False
    goals: int
    assists: int
    shots_on_target: int
    shots_off_target: int
    shots_woodwork: int = 0
    shots_total: int = 0
    fouls_drawn: int
    tackles: int
    clean_sheet: bool
    saves: int
    penalties_saved: int
    fouls_committed: int
    yellow_cards: int
    red_cards: int
    goals_conceded: int
    penalties_won: int = 0
    penalties_missed: int = 0
    penalties_committed: int = 0
    offsides: int = 0
    own_goals: int = 0
    passes_key: int = 0
    dribbles_success: int = 0
    duels_won: int = 0
    interceptions: int = 0
    match_cartola_score: float

    model_config = ConfigDict(from_attributes=True)

class PlayerListItemResponse(BaseModel):
    id: int
    api_football_id: int
    cartola_id: Optional[int] = None
    name: str
    position: str
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    photo_url: Optional[str] = None
    age: Optional[int] = None
    nationality: Optional[str] = None
    price_cartoletas: Optional[float] = 0.0
    cartola_status_id: Optional[int] = None
    score: Optional[PlayerScoreResponse] = None
    # Pontuações das últimas partidas, da mais antiga para a mais recente
    recent_scores: List[float] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def position_normalized(self) -> str:
        return normalize_position(self.position)

    @computed_field
    @property
    def status_label(self) -> str:
        return status_label(self.cartola_status_id)

    @computed_field
    @property
    def team_logo_url(self) -> Optional[str]:
        return team_logo_url(self.team_id)

class PlayerDetailResponse(PlayerListItemResponse):
    match_stats: List[PlayerMatchStatsResponse] = []
