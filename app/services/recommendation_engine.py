import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Iterable

from sqlalchemy.orm import Session, joinedload

from app.core.cartola import (
    DEFENSIVE_POSITIONS,
    TECNICO,
    normalize_position,
    round_name_from_number,
    status_label,
    team_logo_url,
)
from app.models.player import Player
from app.models.player_score import PlayerScore
from app.models.team_profile import TeamProfile
from app.models.fixture import Fixture


def _num(value: float, decimals: int = 2) -> str:
    """Formata número no padrão brasileiro (vírgula decimal)."""
    return f"{value:.{decimals}f}".replace(".", ",")


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """As datas do banco são UTC sem fuso. Devolve ISO com fuso explícito (seguro para JSON)."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class RecommendationEngine:
    """
    Motor Contextual: calcula a projeção de pontos (Expected Score Contextual, ESC)
    de um atleta para uma partida específica.

    Além do número final, devolve `factors`: a decomposição aditiva da projeção,
    em que a soma de `impact_pts` é igual a `expected_score_contextual`.
    """

    def __init__(self, db: Session):
        self.db = db
        self._teams: Optional[Dict[int, TeamProfile]] = None

    # ================================================================
    # Helpers
    # ================================================================
    @property
    def teams(self) -> Dict[int, TeamProfile]:
        if self._teams is None:
            self._teams = {t.id: t for t in self.db.query(TeamProfile).all()}
        return self._teams

    @staticmethod
    def opponent_threat(opponent: TeamProfile, is_home: bool) -> float:
        """Média de gols marcados pelo adversário no mando em que ele vai jogar."""
        if is_home:  # adversário joga fora
            return opponent.avg_goals_scored_away if opponent.away_matches > 0 else opponent.avg_goals_scored
        return opponent.avg_goals_scored_home if opponent.home_matches > 0 else opponent.avg_goals_scored

    @staticmethod
    def opponent_defense_weakness(opponent: TeamProfile, is_home: bool) -> float:
        """Média de gols sofridos pelo adversário no mando em que ele vai jogar."""
        if is_home:
            return opponent.avg_goals_conceded_away if opponent.away_matches > 0 else opponent.avg_goals_conceded
        return opponent.avg_goals_conceded_home if opponent.home_matches > 0 else opponent.avg_goals_conceded

    @classmethod
    def sg_probability_for(cls, opponent: TeamProfile, is_home: bool) -> float:
        """Probabilidade de não sofrer gol (Poisson P(X=0)), ajustada pelo mando."""
        threat = cls.opponent_threat(opponent, is_home)
        if threat == 0.0:
            return 0.40  # Padrão conservador sem dados
        adjusted_threat = threat * (0.85 if is_home else 1.15)
        return math.exp(-adjusted_threat)

    @staticmethod
    def _player_ref(player: Player) -> Dict:
        return {
            "id": player.id,
            "name": player.name,
            "position": normalize_position(player.position),
            "team_id": player.team_id,
            "team_name": player.team_name,
            "team_logo_url": team_logo_url(player.team_id),
            "photo_url": player.photo_url,
            "price": player.price_cartoletas or 0.0,
            "status_id": player.cartola_status_id,
            "status_label": status_label(player.cartola_status_id),
        }

    def _base_result(self, player: Player, fixture: Fixture, is_home: bool, opponent_id: int) -> Dict:
        opponent = self.teams.get(opponent_id)
        return {
            "player": self._player_ref(player),
            "fixture_id": fixture.id,
            "match_date": iso_utc(fixture.match_date),
            "is_home": is_home,
            "opponent_id": opponent_id,
            "opponent": opponent.name if opponent else None,
            "opponent_logo_url": team_logo_url(opponent_id),
            "smart_score": player.score.smart_score if player.score else 0.0,
        }

    # ================================================================
    # Cálculo
    # ================================================================
    def calculate_esc_for_player(self, player_id: int, next_fixture_id: int) -> Optional[Dict]:
        """Calcula a projeção do jogador X na partida Y."""
        player = (
            self.db.query(Player)
            .options(joinedload(Player.score))
            .filter(Player.id == player_id)
            .first()
        )
        fixture = self.db.query(Fixture).filter(Fixture.id == next_fixture_id).first()
        if not player or not fixture:
            return None
        return self.calculate(player, fixture)

    def calculate(self, player: Player, fixture: Fixture) -> Optional[Dict]:
        if not player.score:
            return None
        if player.team_id not in (fixture.home_team_id, fixture.away_team_id):
            return None

        is_home = player.team_id == fixture.home_team_id
        opponent_id = fixture.away_team_id if is_home else fixture.home_team_id
        opponent = self.teams.get(opponent_id)
        result = self._base_result(player, fixture, is_home, opponent_id)
        position = normalize_position(player.position)

        if not opponent:
            esc = player.score.smart_score
            result.update({
                "expected_score_contextual": round(esc, 2),
                "sg_probability": None,
                "reasoning": ["Ainda não temos dados do adversário. A projeção usa a nota geral do jogador."],
                "factors": [self._factor("base", "Nota geral", esc, "Sem dados do adversário")],
                "context": self._context(player.score),
            })
            return result

        if position == TECNICO:
            return self._calculate_coach(player, is_home, opponent, result)
        return self._calculate_player(player, position, is_home, opponent, result)

    @staticmethod
    def _factor(key: str, label: str, impact: float, detail: str, multiplier: Optional[float] = None) -> Dict:
        return {
            "key": key,
            "label": label,
            "detail": detail,
            "multiplier": round(multiplier, 3) if multiplier is not None else None,
            "impact_pts": round(impact, 2),
        }

    @staticmethod
    def _context(ps: PlayerScore) -> Dict:
        return {
            "matches_played": ps.matches_played,
            "home_matches": ps.home_matches,
            "away_matches": ps.away_matches,
            "avg_points": ps.avg_points,
            "avg_points_home": ps.avg_points_home,
            "avg_points_away": ps.avg_points_away,
            "avg_minutes": round(ps.total_minutes / max(ps.matches_played, 1), 1),
            "ema_points": ps.ema_points,
            "trend": ps.trend,
            "consistency_index": ps.consistency_index,
        }

    def _calculate_coach(self, player: Player, is_home: bool, opponent: TeamProfile, result: Dict) -> Optional[Dict]:
        team_profile = self.teams.get(player.team_id)
        if not team_profile:
            return None

        if is_home:
            my_threat = team_profile.avg_goals_scored_home if team_profile.home_matches > 0 else team_profile.avg_goals_scored
            my_defense = team_profile.avg_goals_conceded_home if team_profile.home_matches > 0 else team_profile.avg_goals_conceded
        else:
            my_threat = team_profile.avg_goals_scored_away if team_profile.away_matches > 0 else team_profile.avg_goals_scored
            my_defense = team_profile.avg_goals_conceded_away if team_profile.away_matches > 0 else team_profile.avg_goals_conceded
        opp_threat = self.opponent_threat(opponent, is_home)
        opp_defense = self.opponent_defense_weakness(opponent, is_home)

        xg_for = (my_threat + opp_defense) / 2.0
        xg_against = (my_defense + opp_threat) / 2.0
        win_prob = min(max(0.20 + ((xg_for - xg_against) * 0.25), 0.0), 0.95)
        sg_probability = math.exp(-xg_against) if xg_against > 0 else 0.4

        factors = [
            self._factor("base", "Base do técnico", 3.0, "Pontuação de referência de um técnico"),
            self._factor("win", "Chance de vitória", win_prob * 1.0, f"{_pct(win_prob)} de chance de vencer"),
            self._factor("goals_for", "Gols a favor", xg_for * 1.18, f"{_num(xg_for)} gols esperados a favor"),
            self._factor("sg", "Chance de SG", sg_probability * 2.27, f"{_pct(sg_probability)} de chance de não sofrer gol"),
            self._factor("goals_against", "Gols contra", -(xg_against * 0.22), f"{_num(xg_against)} gols esperados contra"),
        ]
        expected_score = 3.0 + (win_prob * 1.0) + (xg_for * 1.18) + (sg_probability * 2.27) - (xg_against * 0.22)

        mando = "em casa" if is_home else "fora de casa"
        result.update({
            "expected_score_contextual": round(expected_score, 2),
            "sg_probability": round(sg_probability * 100, 1),
            "reasoning": [
                f"Joga {mando} contra o {opponent.name}: {_num(xg_for)} gols esperados a favor e {_num(xg_against)} contra.",
                f"Chance de vitória de {_pct(win_prob)}.",
                f"Chance de não sofrer gol de {_pct(sg_probability)}.",
            ],
            "factors": factors,
            "context": self._context(player.score),
        })
        return result

    def _calculate_player(self, player: Player, position: str, is_home: bool, opponent: TeamProfile, result: Dict) -> Dict:
        ps: PlayerScore = player.score
        reasoning: List[str] = []
        factors: List[Dict] = []

        # 1. Contexto de mando (informativo: a projeção parte da forma recente)
        if is_home:
            reasoning.append(f"Joga em casa, onde faz {_num(ps.avg_points_home)} pts de média em {ps.home_matches} jogos.")
        else:
            reasoning.append(f"Joga fora, onde faz {_num(ps.avg_points_away)} pts de média em {ps.away_matches} jogos.")

        # 2. Forma recente (Média Móvel Exponencial)
        running = ps.ema_points
        factors.append(self._factor("form", "Forma recente", running, "Média ponderada que valoriza os últimos jogos"))

        if ps.trend == "rising":
            momentum_mod = 1.06
            reasoning.append("Está em alta: as últimas 5 rodadas estão acima da média dele.")
        elif ps.trend == "falling":
            momentum_mod = 0.94
            reasoning.append("Está em queda: as últimas 5 rodadas estão abaixo da média dele.")
        else:
            momentum_mod = 1.0

        # 3. Adversário: chance de SG (defensores) ou fragilidade da defesa (meias/atacantes)
        sg_probability: Optional[float] = None
        opponent_factor = 1.0
        opp_threat = self.opponent_threat(opponent, is_home)
        opp_defense_weakness = self.opponent_defense_weakness(opponent, is_home)

        if position in DEFENSIVE_POSITIONS:
            sg_probability = self.sg_probability_for(opponent, is_home)
            sg_expected_pts = sg_probability * 5.0
            sg_contribution = sg_expected_pts * 0.4  # Peso parcial: a média já contém SGs passados
            running += sg_contribution
            factors.append(self._factor(
                "sg", "Chance de SG", sg_contribution,
                f"{_pct(sg_probability)} de chance de não sofrer gol",
            ))
            reasoning.append(
                f"O {opponent.name} marca {_num(opp_threat)} gols por jogo nesse mando. "
                f"Chance de SG de {_pct(sg_probability)}."
            )
        else:
            if opp_defense_weakness > 1.5:
                opponent_factor = 1.15
                reasoning.append(f"A defesa do {opponent.name} é frágil: sofre {_num(opp_defense_weakness)} gols por jogo nesse mando.")
            elif 0 < opp_defense_weakness < 0.8:
                opponent_factor = 0.85
                reasoning.append(f"A defesa do {opponent.name} é sólida: sofre só {_num(opp_defense_weakness)} gols por jogo nesse mando.")

        def apply(key: str, label: str, mod: float, detail: str):
            nonlocal running
            delta = running * (mod - 1.0)
            running *= mod
            factors.append(self._factor(key, label, delta, detail, multiplier=mod))

        if opponent_factor != 1.0:
            apply("opponent", "Defesa adversária", opponent_factor,
                  f"{opponent.name} sofre {_num(opp_defense_weakness)} gols por jogo")

        if momentum_mod != 1.0:
            apply("momentum", "Fase", momentum_mod, "Em alta" if momentum_mod > 1 else "Em queda")

        # 4. Minutagem
        avg_minutes = ps.total_minutes / max(ps.matches_played, 1)
        if avg_minutes >= 80:
            minutes_mod = 1.0
        elif avg_minutes >= 60:
            minutes_mod = 0.85
            reasoning.append(f"Costuma ser substituído: joga {avg_minutes:.0f} minutos em média.")
        elif avg_minutes >= 30:
            minutes_mod = 0.60
            reasoning.append(f"Entra muito do banco: joga {avg_minutes:.0f} minutos em média.")
        else:
            minutes_mod = 0.30
            reasoning.append(f"Joga pouco: {avg_minutes:.0f} minutos em média por partida.")
        if minutes_mod != 1.0:
            apply("minutes", "Minutagem", minutes_mod, f"{avg_minutes:.0f} minutos por jogo")

        # 5. Regularidade
        consistency_mod = 0.92 + (ps.consistency_index / 100.0) * 0.16
        if consistency_mod > 1.0:
            reasoning.append(f"É regular: índice de regularidade {ps.consistency_index:.0f} de 100.")
        apply("consistency", "Regularidade", consistency_mod, f"Índice {ps.consistency_index:.0f} de 100")

        # 6. Limite de segurança para valores extremos
        esc = max(-2.0, min(running, 25.0))
        if esc != running:
            factors.append(self._factor("cap", "Limite", esc - running, "Projeção limitada entre -2 e 25 pontos"))

        result.update({
            "expected_score_contextual": round(esc, 2),
            "sg_probability": round(sg_probability * 100, 1) if sg_probability is not None else None,
            "reasoning": reasoning,
            "factors": factors,
            "context": self._context(ps),
        })
        return result

    # ================================================================
    # Consultas em lote
    # ================================================================
    def _players_of_teams(self, team_ids: Iterable[int]) -> List[Player]:
        return (
            self.db.query(Player)
            .options(joinedload(Player.score))
            .filter(Player.team_id.in_(list(team_ids)))
            .all()
        )

    def get_recommendations_for_fixture(self, fixture_id: int, limit: int = 11) -> List[Dict]:
        """Projeções dos jogadores dos dois times de uma partida, da maior para a menor."""
        fixture = self.db.query(Fixture).filter(Fixture.id == fixture_id).first()
        if not fixture:
            return []
        recs = [
            r for p in self._players_of_teams([fixture.home_team_id, fixture.away_team_id])
            if (r := self.calculate(p, fixture))
        ]
        recs.sort(key=lambda x: x["expected_score_contextual"], reverse=True)
        return recs[:limit]

    def get_recommendations_for_round(
        self,
        round_number: int,
        position: Optional[str] = None,
        statuses: Optional[Iterable[int]] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Projeções de todos os jogadores da rodada, da maior para a menor."""
        fixtures = self.db.query(Fixture).filter(Fixture.round_name == round_name_from_number(round_number)).all()
        by_team: Dict[int, Fixture] = {}
        for f in fixtures:
            by_team[f.home_team_id] = f
            by_team[f.away_team_id] = f
        if not by_team:
            return []

        wanted_position = normalize_position(position) if position else None
        wanted_status = set(statuses) if statuses else None
        recs = []
        for p in self._players_of_teams(by_team.keys()):
            if wanted_position and normalize_position(p.position) != wanted_position:
                continue
            if wanted_status and p.cartola_status_id not in wanted_status:
                continue
            r = self.calculate(p, by_team[p.team_id])
            if r:
                recs.append(r)
        recs.sort(key=lambda x: x["expected_score_contextual"], reverse=True)
        return recs[:limit]

    def get_next_projection(self, player_id: int, round_number: int) -> Optional[Dict]:
        """Projeção do jogador para o jogo do time dele na rodada informada."""
        player = (
            self.db.query(Player)
            .options(joinedload(Player.score))
            .filter(Player.id == player_id)
            .first()
        )
        if not player or not player.team_id:
            return None
        fixture = (
            self.db.query(Fixture)
            .filter(Fixture.round_name == round_name_from_number(round_number))
            .filter((Fixture.home_team_id == player.team_id) | (Fixture.away_team_id == player.team_id))
            .first()
        )
        if not fixture:
            return None
        return self.calculate(player, fixture)
