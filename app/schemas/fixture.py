from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class TeamProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cartola_id: Optional[int] = None
    name: str
    logo_url: Optional[str] = None
    matches_played: int = 0
    home_matches: int = 0
    away_matches: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    avg_goals_scored: float = 0.0
    avg_goals_scored_home: float = 0.0
    avg_goals_scored_away: float = 0.0
    avg_goals_conceded: float = 0.0
    avg_goals_conceded_home: float = 0.0
    avg_goals_conceded_away: float = 0.0
    clean_sheets: int = 0
    clean_sheet_rate: float = 0.0


class TeamSummary(BaseModel):
    id: int
    name: Optional[str] = None
    logo_url: Optional[str] = None


class FixtureResponse(BaseModel):
    id: int
    round_number: Optional[int] = None
    round_name: Optional[str] = None
    match_date: Optional[datetime] = None
    status: str
    is_finished: bool
    is_live: bool
    home_team: TeamSummary
    away_team: TeamSummary
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    # Chance (0-100) de cada time terminar sem sofrer gol
    home_sg_probability: Optional[float] = None
    away_sg_probability: Optional[float] = None


class FixtureDetailResponse(FixtureResponse):
    home_profile: Optional[TeamProfileResponse] = None
    away_profile: Optional[TeamProfileResponse] = None


class RoundSummary(BaseModel):
    round_number: int
    fixtures_total: int
    fixtures_finished: int
    first_match: Optional[datetime] = None
    last_match: Optional[datetime] = None
    status: str  # "upcoming" | "live" | "finished"


class CurrentRoundResponse(BaseModel):
    season_year: int
    round_number: Optional[int] = None
    status: Optional[str] = None
    market_status: str  # "open" | "closed" | "unknown"
    market_closes_at: Optional[datetime] = None
    first_match: Optional[datetime] = None
    last_match: Optional[datetime] = None
    data_updated_at: Optional[datetime] = None
    fixtures: List[FixtureResponse] = []


class SystemStatusResponse(BaseModel):
    players: int
    players_with_cartola_id: int
    teams: int
    fixtures: int
    fixtures_finished: int
    match_stats: int
    lineups: int
    data_updated_at: Optional[datetime] = None
