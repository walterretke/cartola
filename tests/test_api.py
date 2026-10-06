from app.core.cartola import (
    LATERAL,
    MEIA,
    ZAGUEIRO,
    GOLEIRO,
    merge_position,
    normalize_position,
    round_number_from_name,
)
from app.db.seed import normalize_stored_positions
from app.models.player import Player
from app.models.team_recommendation import TeamRecommendation

API = "/api/v1"


# ================================================================
# Posições
# ================================================================
def test_normalize_position_accepts_both_languages():
    assert normalize_position("Defender") == ZAGUEIRO
    assert normalize_position("G") == GOLEIRO
    assert normalize_position("Midfielder") == MEIA
    assert normalize_position("Lateral") == LATERAL
    assert normalize_position("técnico") == "Tecnico"


def test_merge_position_keeps_lateral_from_cartola():
    assert merge_position(LATERAL, "D") == LATERAL
    assert merge_position(ZAGUEIRO, "M") == MEIA
    assert merge_position(None, "F") == "Atacante"


def test_round_number_from_name():
    assert round_number_from_name("Regular Season - 12") == 12
    assert round_number_from_name(None) is None


def test_normalize_stored_positions(db):
    player = db.query(Player).filter(Player.position == ZAGUEIRO).first()
    player.position = "Defender"
    db.commit()
    assert normalize_stored_positions(db) >= 1
    db.commit()
    db.refresh(player)
    assert player.position == ZAGUEIRO


# ================================================================
# Projeção
# ================================================================
def test_defenders_receive_clean_sheet_factor(client, db):
    """Bug corrigido: posições em português (Zagueiro/Lateral/Goleiro) perdiam o bônus de SG."""
    for position in (GOLEIRO, LATERAL, ZAGUEIRO):
        player = db.query(Player).filter(Player.position == position).first()
        res = client.get(f"{API}/recommendations/player/{player.id}/next")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["sg_probability"] is not None
        assert any(f["key"] == "sg" for f in data["factors"])


def test_factors_add_up_to_projection(client):
    res = client.get(f"{API}/recommendations/round", params={"limit": 200})
    assert res.status_code == 200
    projections = res.json()
    assert projections, "a rodada atual deveria ter projeções"
    for p in projections:
        total = sum(f["impact_pts"] for f in p["factors"])
        assert abs(total - p["expected_score_contextual"]) < 0.06, p["player"]["name"]
        assert "IA" not in " ".join(p["reasoning"])


def test_round_recommendations_filter_by_position(client):
    res = client.get(f"{API}/recommendations/round", params={"position": "Attacker"})
    assert res.status_code == 200
    assert {p["player"]["position"] for p in res.json()} == {"Atacante"}


def test_fixture_recommendations(client):
    res = client.get(f"{API}/recommendations/fixture/2001", params={"limit": 5})
    assert res.status_code == 200
    assert len(res.json()) == 5


# ================================================================
# Rodadas, jogos e clubes
# ================================================================
def test_current_round_is_first_unfinished(client):
    res = client.get(f"{API}/rounds/current")
    assert res.status_code == 200
    data = res.json()
    assert data["round_number"] == 2
    assert data["market_status"] == "open"
    assert data["market_closes_at"] is not None
    assert len(data["fixtures"]) == 2
    assert data["data_updated_at"] is not None


def test_list_rounds(client):
    res = client.get(f"{API}/rounds")
    assert [r["status"] for r in res.json()] == ["finished", "upcoming"]


def test_fixtures_of_round(client):
    res = client.get(f"{API}/fixtures", params={"round": 1})
    assert res.status_code == 200
    fixtures = res.json()
    assert len(fixtures) == 2
    assert all(f["is_finished"] for f in fixtures)
    assert all(0 < f["home_sg_probability"] <= 100 for f in fixtures)
    assert fixtures[0]["home_team"]["logo_url"].startswith("https://")


def test_fixture_detail_includes_profiles(client):
    res = client.get(f"{API}/fixtures/2001")
    assert res.status_code == 200
    data = res.json()
    assert data["home_profile"]["name"] == "Botafogo do Sul"
    assert data["away_profile"]["matches_played"] == 1
    assert client.get(f"{API}/fixtures/999999").status_code == 404


def test_team_profiles(client):
    res = client.get(f"{API}/team-profiles")
    assert res.status_code == 200
    assert len(res.json()) == 4


# ================================================================
# Jogadores
# ================================================================
def test_players_list_has_price_status_and_recent_scores(client):
    res = client.get(f"{API}/players", params={"limit": 5, "position": "Atacante"})
    assert res.status_code == 200
    assert int(res.headers["X-Total-Count"]) == 12
    first = res.json()[0]
    assert first["price_cartoletas"] > 0
    assert first["status_label"] == "Provável"
    assert len(first["recent_scores"]) == 1
    assert first["score"]["ema_points"] is not None


def test_players_filters(client):
    res = client.get(f"{API}/players", params={"position": "Defender", "max_price": 7, "sort_by": "price_cartoletas", "order": "asc"})
    assert res.status_code == 200
    players = res.json()
    assert players
    assert all(p["position"] == ZAGUEIRO and p["price_cartoletas"] <= 7 for p in players)
    prices = [p["price_cartoletas"] for p in players]
    assert prices == sorted(prices)


def test_player_detail(client, db):
    player = db.query(Player).filter(Player.position == MEIA).first()
    res = client.get(f"{API}/players/{player.id}")
    assert res.status_code == 200
    data = res.json()
    assert len(data["match_stats"]) == 1
    assert data["recent_scores"] == [data["match_stats"][0]["match_cartola_score"]]


# ================================================================
# Escalações
# ================================================================
def test_build_lineups_is_idempotent(client, db):
    res = client.post(f"{API}/lineups/build", params={"formation": "4-3-3"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["round_number"] == 2
    strategies = {l["strategy"] for l in body["lineups"]}
    assert "PRINCIPAL" in strategies

    principal = next(l for l in body["lineups"] if l["strategy"] == "PRINCIPAL")
    positions = [p["player"]["position"] for p in principal["squad"]["players"]]
    assert positions.count("Atacante") == 3
    assert positions.count("Lateral") == 2
    assert positions.count("Tecnico") == 1
    assert principal["squad"]["captain_id"] is not None

    count_before = db.query(TeamRecommendation).count()
    assert client.post(f"{API}/lineups/build").status_code == 200
    db.expire_all()
    assert db.query(TeamRecommendation).count() == count_before

    listed = client.get(f"{API}/lineups")
    assert listed.status_code == 200
    assert {l["strategy"] for l in listed.json()} == strategies


def test_build_lineups_other_formation_and_budget(client):
    res = client.post(f"{API}/lineups/build", params={"formation": "3-5-2", "budget": 90})
    assert res.status_code == 200, res.text
    principal = next(l for l in res.json()["lineups"] if l["strategy"] == "PRINCIPAL")
    positions = [p["player"]["position"] for p in principal["squad"]["players"]]
    assert positions.count("Meia") == 5
    assert positions.count("Lateral") == 0


def test_build_lineups_rejects_invalid_formation(client):
    assert client.post(f"{API}/lineups/build", params={"formation": "2-2-6"}).status_code == 422


def test_formations(client):
    assert "4-3-3" in client.get(f"{API}/lineups/formations").json()


# ================================================================
# Infra
# ================================================================
def test_cors_allows_frontend(client):
    res = client.get(f"{API}/scout-actions", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_sync_status(client):
    data = client.get(f"{API}/sync/status").json()
    assert data["players"] > 0
    assert data["fixtures"] == 4


def test_root_does_not_mention_ai(client):
    assert "AI" not in client.get("/").json()["message"]
    assert "AI" not in client.get(f"{API}/openapi.json").json()["info"]["title"]
