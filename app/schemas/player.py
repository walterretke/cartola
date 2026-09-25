from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

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
    trend: str = "stable"
    # Médias por scout
    avg_goals: float = 0.0
    avg_assists: float = 0.0
    avg_shots_on_target: float = 0.0
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
    name: str
    position: str
    team_name: Optional[str] = None
    photo_url: Optional[str] = None
    score: Optional[PlayerScoreResponse] = None

    model_config = ConfigDict(from_attributes=True)

class PlayerDetailResponse(PlayerListItemResponse):
    match_stats: List[PlayerMatchStatsResponse] = []
