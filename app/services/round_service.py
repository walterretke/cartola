from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cartola import (
    FINISHED_FIXTURE_STATUSES,
    LIVE_FIXTURE_STATUSES,
    round_name_from_number,
    round_number_from_name,
    team_logo_url,
)
from app.core.config import settings
from app.models.fixture import Fixture
from app.models.player import Player
from app.models.player_match_stats import PlayerMatchStats
from app.models.player_score import PlayerScore
from app.models.team_profile import TeamProfile
from app.models.team_recommendation import TeamRecommendation
from app.services.recommendation_engine import RecommendationEngine


def as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Datas do banco são UTC sem fuso: devolve com fuso explícito."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class RoundService:
    """Rodadas, jogos e status geral dos dados."""

    def __init__(self, db: Session):
        self.db = db
        self._teams: Optional[Dict[int, TeamProfile]] = None

    @property
    def teams(self) -> Dict[int, TeamProfile]:
        if self._teams is None:
            self._teams = {t.id: t for t in self.db.query(TeamProfile).all()}
        return self._teams

    # ================================================================
    # Jogos
    # ================================================================
    def _team_summary(self, team_id: int) -> Dict:
        team = self.teams.get(team_id)
        return {"id": team_id, "name": team.name if team else None, "logo_url": team_logo_url(team_id)}

    def team_profile_dict(self, team: TeamProfile) -> Dict:
        data = {c.name: getattr(team, c.name) for c in TeamProfile.__table__.columns}
        data["logo_url"] = team_logo_url(team.id)
        return data

    def fixture_dict(self, fixture: Fixture, detail: bool = False) -> Dict:
        home = self.teams.get(fixture.home_team_id)
        away = self.teams.get(fixture.away_team_id)
        home_sg = away_sg = None
        if home and away:
            home_sg = round(RecommendationEngine.sg_probability_for(away, is_home=True) * 100, 1)
            away_sg = round(RecommendationEngine.sg_probability_for(home, is_home=False) * 100, 1)

        data = {
            "id": fixture.id,
            "round_number": round_number_from_name(fixture.round_name),
            "round_name": fixture.round_name,
            "match_date": as_utc(fixture.match_date),
            "status": fixture.status,
            "is_finished": fixture.status in FINISHED_FIXTURE_STATUSES,
            "is_live": fixture.status in LIVE_FIXTURE_STATUSES,
            "home_team": self._team_summary(fixture.home_team_id),
            "away_team": self._team_summary(fixture.away_team_id),
            "home_goals": fixture.home_goals,
            "away_goals": fixture.away_goals,
            "home_sg_probability": home_sg,
            "away_sg_probability": away_sg,
        }
        if detail:
            data["home_profile"] = self.team_profile_dict(home) if home else None
            data["away_profile"] = self.team_profile_dict(away) if away else None
        return data

    def fixtures_of_round(self, round_number: int) -> List[Fixture]:
        return (
            self.db.query(Fixture)
            .filter(Fixture.round_name == round_name_from_number(round_number))
            .order_by(Fixture.match_date.asc())
            .all()
        )

    # ================================================================
    # Rodadas
    # ================================================================
    def list_rounds(self) -> List[Dict]:
        grouped: Dict[int, List[Fixture]] = defaultdict(list)
        for f in self.db.query(Fixture).all():
            n = round_number_from_name(f.round_name)
            if n is not None:
                grouped[n].append(f)

        rounds = []
        for n in sorted(grouped):
            fixtures = grouped[n]
            dates = [f.match_date for f in fixtures if f.match_date]
            finished = sum(1 for f in fixtures if f.status in FINISHED_FIXTURE_STATUSES)
            live = any(f.status in LIVE_FIXTURE_STATUSES for f in fixtures)
            if finished == len(fixtures):
                status = "finished"
            elif live or finished > 0:
                status = "live"
            else:
                status = "upcoming"
            rounds.append({
                "round_number": n,
                "fixtures_total": len(fixtures),
                "fixtures_finished": finished,
                "first_match": as_utc(min(dates)) if dates else None,
                "last_match": as_utc(max(dates)) if dates else None,
                "status": status,
            })
        return rounds

    def current_round_number(self) -> Optional[int]:
        """Primeira rodada que ainda não terminou. Se todas terminaram, a última."""
        rounds = self.list_rounds()
        if not rounds:
            return None
        for r in rounds:
            if r["status"] != "finished":
                return r["round_number"]
        return rounds[-1]["round_number"]

    def data_updated_at(self) -> Optional[datetime]:
        return as_utc(self.db.query(func.max(PlayerScore.calculated_at)).scalar())

    def current_round(self) -> Dict:
        rounds = {r["round_number"]: r for r in self.list_rounds()}
        number = self.current_round_number()
        base = {
            "season_year": settings.BRASILEIRAO_SEASON,
            "round_number": number,
            "status": None,
            "market_status": "unknown",
            "market_closes_at": None,
            "first_match": None,
            "last_match": None,
            "data_updated_at": self.data_updated_at(),
            "fixtures": [],
        }
        if number is None:
            return base

        summary = rounds[number]
        fixtures = self.fixtures_of_round(number)
        first_match = summary["first_match"]
        closes_at = first_match - timedelta(minutes=1) if first_match else None

        if summary["status"] == "upcoming" and closes_at and closes_at > datetime.now(timezone.utc):
            market_status = "open"
        elif summary["status"] == "upcoming" and not closes_at:
            market_status = "unknown"
        else:
            market_status = "closed"

        base.update({
            "status": summary["status"],
            "market_status": market_status,
            "market_closes_at": closes_at,
            "first_match": first_match,
            "last_match": summary["last_match"],
            "fixtures": [self.fixture_dict(f) for f in fixtures],
        })
        return base

    # ================================================================
    # Status geral
    # ================================================================
    def system_status(self) -> Dict:
        return {
            "players": self.db.query(func.count(Player.id)).scalar() or 0,
            "players_with_cartola_id": self.db.query(func.count(Player.id)).filter(Player.cartola_id.isnot(None)).scalar() or 0,
            "teams": self.db.query(func.count(TeamProfile.id)).scalar() or 0,
            "fixtures": self.db.query(func.count(Fixture.id)).scalar() or 0,
            "fixtures_finished": self.db.query(func.count(Fixture.id)).filter(Fixture.status.in_(FINISHED_FIXTURE_STATUSES)).scalar() or 0,
            "match_stats": self.db.query(func.count(PlayerMatchStats.id)).scalar() or 0,
            "lineups": self.db.query(func.count(TeamRecommendation.id)).scalar() or 0,
            "data_updated_at": self.data_updated_at(),
        }
