"""
Testes rodam contra um SQLite temporário com dados de exemplo:
4 clubes, rodada 1 encerrada e rodada 2 marcada para o futuro.
"""
import os
import tempfile
from datetime import datetime, timedelta, timezone

# Precisa vir antes de importar o app: variáveis de ambiente têm prioridade sobre o .env.local
_TMP_DIR = tempfile.mkdtemp(prefix="cartola-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP_DIR, 'test.db')}"
os.environ["BRASILEIRAO_SEASON"] = "2026"

import pytest
from fastapi.testclient import TestClient

from app.core.cartola import ATACANTE, GOLEIRO, LATERAL, MEIA, TECNICO, ZAGUEIRO, round_name_from_number
from app.db.base import Base
from app.db.seed import init_db
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.fixture import Fixture
from app.models.player import Player
from app.models.player_match_stats import PlayerMatchStats
from app.models.player_score import PlayerScore
from app.models.team_profile import TeamProfile
from app.services.scoring_engine import ScoringEngine
from app.services.sync_service import SyncService

TEAMS = {101: "Alvorada FC", 102: "Botafogo do Sul", 103: "Cruzeiro do Norte", 104: "Dragões EC"}

# (posição, quantidade, preço base)
SQUAD = [
    (GOLEIRO, 2, 8.0),
    (LATERAL, 2, 7.0),
    (ZAGUEIRO, 3, 6.0),
    (MEIA, 3, 10.0),
    (ATACANTE, 3, 12.0),
]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seed(db) -> None:
    for team_id, name in TEAMS.items():
        db.add(TeamProfile(id=team_id, name=name))
    db.flush()

    past = _now() - timedelta(days=10)
    future = _now() + timedelta(days=3)
    # Rodada 1 (encerrada): 101 2x0 102, 103 1x1 104
    r1 = [
        Fixture(id=1001, round_name=round_name_from_number(1), match_date=past, status="FT",
                home_team_id=101, away_team_id=102, home_goals=2, away_goals=0),
        Fixture(id=1002, round_name=round_name_from_number(1), match_date=past + timedelta(hours=2), status="FT",
                home_team_id=103, away_team_id=104, home_goals=1, away_goals=1),
    ]
    # Rodada 2 (futura): 102 x 101, 104 x 103
    r2 = [
        Fixture(id=2001, round_name=round_name_from_number(2), match_date=future, status="NS",
                home_team_id=102, away_team_id=101),
        Fixture(id=2002, round_name=round_name_from_number(2), match_date=future + timedelta(hours=2), status="NS",
                home_team_id=104, away_team_id=103),
    ]
    db.add_all(r1 + r2)
    db.flush()

    next_id = 1
    for team_id in TEAMS:
        fixture = r1[0] if team_id in (101, 102) else r1[1]
        is_home = fixture.home_team_id == team_id
        conceded = fixture.away_goals if is_home else fixture.home_goals
        for position, count, base_price in SQUAD:
            for i in range(count):
                player = Player(
                    api_football_id=team_id * 100 + next_id,
                    name=f"{position} {i + 1} {TEAMS[team_id]}",
                    position=position,
                    team_id=team_id,
                    team_name=TEAMS[team_id],
                    cartola_status_id=7,
                    price_cartoletas=base_price + i * 2,
                )
                next_id += 1
                db.add(player)
                db.flush()
                db.add(PlayerMatchStats(
                    player_id=player.id,
                    fixture_id=fixture.id,
                    round_name=fixture.round_name,
                    match_date=fixture.match_date,
                    is_home=is_home,
                    opponent_team_id=fixture.away_team_id if is_home else fixture.home_team_id,
                    minutes_played=90 - i * 20,
                    goals=1 if position == ATACANTE and i == 0 else 0,
                    tackles=2 if position in (LATERAL, ZAGUEIRO, MEIA) else 0,
                    shots_on_target=1 if position in (MEIA, ATACANTE) else 0,
                    saves=3 if position == GOLEIRO else 0,
                    clean_sheet=conceded == 0 and position in (GOLEIRO, LATERAL, ZAGUEIRO),
                    goals_conceded=conceded if position == GOLEIRO else 0,
                ))
        coach = Player(
            api_football_id=-(team_id * 100 + next_id),
            cartola_id=team_id * 10,
            name=f"Técnico {TEAMS[team_id]}",
            position=TECNICO,
            team_id=team_id,
            team_name=TEAMS[team_id],
            cartola_status_id=7,
            price_cartoletas=9.0,
        )
        next_id += 1
        db.add(coach)
        db.flush()
        db.add(PlayerScore(player_id=coach.id, smart_score=5.0))

    db.commit()
    SyncService(db=db, client=object())._recalculate_team_profiles()
    ScoringEngine(db).calculate_all_scores()
    # O ScoringEngine zera técnicos sem partidas; mantém o score para o motor calcular
    for ps in db.query(PlayerScore).join(Player).filter(Player.position == TECNICO):
        ps.smart_score = 5.0
    db.commit()


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield
    engine.dispose()


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
