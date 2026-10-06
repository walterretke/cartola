import random
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.cartola import (
    DEFAULT_FORMATION,
    FORMATIONS,
    PLAYABLE_STATUSES,
    round_name_from_number,
)
from app.models.fixture import Fixture
from app.models.player_match_stats import PlayerMatchStats
from app.models.player_score import PlayerScore
from app.models.team_recommendation import TeamRecommendation
from app.services.recommendation_engine import RecommendationEngine

STRATEGIES = ("PRINCIPAL", "ALTERNATIVO", "VALORIZACAO", "APOSTA")


class TeamBuilderService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = RecommendationEngine(db)
        # Formação padrão: 4-3-3 (Posições do Cartola)
        # Ordenado do ataque para a defesa para priorizar escolhas ofensivas e evitar conflitos
        self.formation_name = DEFAULT_FORMATION
        self.formation = dict(FORMATIONS[DEFAULT_FORMATION])

    def _last_scores(self, player_ids: List[int]) -> Dict[int, float]:
        """Pontuação da última partida de cada jogador, em uma única consulta."""
        if not player_ids:
            return {}
        rows = (
            self.db.query(PlayerMatchStats.player_id, PlayerMatchStats.match_cartola_score)
            .filter(PlayerMatchStats.player_id.in_(player_ids))
            .order_by(PlayerMatchStats.player_id, desc(PlayerMatchStats.match_date))
            .all()
        )
        last: Dict[int, float] = {}
        for player_id, score in rows:
            last.setdefault(player_id, score or 0.0)
        return last

    def _std_deviations(self, player_ids: List[int]) -> Dict[int, float]:
        if not player_ids:
            return {}
        rows = (
            self.db.query(PlayerScore.player_id, PlayerScore.std_deviation)
            .filter(PlayerScore.player_id.in_(player_ids))
            .all()
        )
        return {pid: std or 0.0 for pid, std in rows}

    def generate_teams_for_round(
        self,
        season_year: int,
        round_number: int,
        max_cost: Optional[float] = None,
        formation: str = DEFAULT_FORMATION,
    ) -> Dict[str, Any]:
        """
        Gera as 4 estratégias de escalação (Principal, Alternativo, Valorização, Aposta).
        Escalações anteriores da mesma rodada e estratégia são substituídas.
        """
        if formation not in FORMATIONS:
            raise ValueError(f"Formação inválida: {formation}. Use uma de {', '.join(FORMATIONS)}.")
        self.formation_name = formation
        self.formation = dict(FORMATIONS[formation])

        fixtures = self.db.query(Fixture).filter(Fixture.round_name == round_name_from_number(round_number)).all()

        all_recs = []
        for f in fixtures:
            # Projeções de todos os jogadores da partida
            for r in self.engine.get_recommendations_for_fixture(f.id, limit=60):
                # Regra 5: Somente status "Provável" (7) e "Dúvida" (2)
                if r["player"]["status_id"] not in PLAYABLE_STATUSES:
                    continue
                all_recs.append(r)

        player_ids = [r["player"]["id"] for r in all_recs]
        last_scores = self._last_scores(player_ids)
        std_devs = self._std_deviations(player_ids)
        for r in all_recs:
            pid = r["player"]["id"]
            r["last_score"] = last_scores.get(pid, 0.0)
            r["price"] = r["player"]["price"]
            r["std_deviation"] = std_devs.get(pid, 0.0)
            r["team_id"] = r["player"]["team_id"]

        # Separar por posição (o motor já devolve a posição no padrão do Cartola)
        players_by_pos = {pos: [] for pos in self.formation}
        for r in all_recs:
            pos = r["player"]["position"]
            if pos in players_by_pos:
                players_by_pos[pos].append(r)

        teams = {
            "PRINCIPAL": self._build_principal(players_by_pos, max_cost),
            "ALTERNATIVO": self._build_alternativo(players_by_pos, max_cost),
            "VALORIZACAO": self._build_valorizacao(players_by_pos, max_cost),
            "APOSTA": self._build_aposta(players_by_pos, max_cost)
        }

        # Substitui as escalações anteriores desta rodada (evita registros duplicados)
        self.db.query(TeamRecommendation).filter(
            TeamRecommendation.season_year == season_year,
            TeamRecommendation.round_number == round_number,
        ).delete(synchronize_session=False)

        for strategy, squad in teams.items():
            squad["formation"] = formation
            if squad["players"]:
                self.db.add(TeamRecommendation(
                    season_year=season_year,
                    round_number=round_number,
                    strategy=strategy,
                    formation=formation,
                    expected_total_score=squad["expected_score"],
                    expected_total_cost=squad["cost"],
                    squad_data=squad
                ))

        self.db.commit()
        return teams

    def _assemble_433(self, players_by_pos: dict, sort_key, reverse=True, filter_func=None, max_cost=None) -> dict:
        """Helper para montar 4-3-3 genérico com suporte a downgrade de custo"""
        starters = []
        reserves = []
        
        teams_we_are_attacking = set()
        
        # 1. Seleciona titulares ideais (Greedy)
        pos_pools = {}
        for pos, limit in self.formation.items():
            pool = players_by_pos.get(pos, [])
            if filter_func:
                pool = [p for p in pool if filter_func(p)]
            
            if pos in ('Zagueiro', 'Lateral', 'Goleiro', 'Tecnico'):
                pool = [p for p in pool if p['team_id'] not in teams_we_are_attacking]
                
            pool.sort(key=sort_key, reverse=reverse)
            pos_pools[pos] = pool
            
            pos_starters = pool[:limit]
            starters.extend(pos_starters)
            
            if pos in ('Atacante', 'Meia'):
                for s in pos_starters:
                    teams_we_are_attacking.add(s['opponent_id'])

        # 2. Heurística de rebaixamento (Downgrade) para caber no orçamento
        current_cost = sum(s['price'] for s in starters)
        
        if max_cost and current_cost > max_cost:
            # Mantém o índice do próximo reserva disponível para downgrade por posição
            next_idx = {pos: self.formation[pos] for pos in self.formation}
            
            while current_cost > max_cost:
                best_trade = None
                best_efficiency = float('inf')
                
                # Procura a melhor troca (menor perda de pontos por cartoleta salva)
                for i, s in enumerate(starters):
                    pos = s['player']['position']
                    pool = pos_pools[pos]
                    idx = next_idx[pos]
                    
                    # Procura o próximo jogador mais barato que o titular atual
                    while idx < len(pool) and pool[idx]['price'] >= s['price']:
                        idx += 1
                        
                    if idx < len(pool):
                        candidate = pool[idx]
                        price_diff = s['price'] - candidate['price']
                        score_diff = s['expected_score_contextual'] - candidate['expected_score_contextual']
                        
                        # Evitar divisão por zero, e queremos perder o mínimo de pontos
                        efficiency = score_diff / price_diff if price_diff > 0 else float('inf')
                        
                        if efficiency < best_efficiency:
                            best_efficiency = efficiency
                            best_trade = (i, pos, candidate, idx)
                
                if best_trade:
                    i, pos, candidate, idx = best_trade
                    current_cost -= starters[i]['price']
                    current_cost += candidate['price']
                    starters[i] = candidate
                    next_idx[pos] = idx + 1
                else:
                    # Impossível reduzir mais
                    break

        # Recalcula custo total
        final_cost = sum(s['price'] for s in starters)
        expected_score = sum(s['expected_score_contextual'] for s in starters)

        # 3. Monta banco de reservas
        for pos, limit in self.formation.items():
            if pos == 'Tecnico':
                continue
            
            pos_starters = [s for s in starters if s['player']['position'] == pos]
            if not pos_starters:
                continue
                
            cheapest_starter_price = min(s['price'] for s in pos_starters)
            
            # Pega quem não está no time titular e custa menos que o titular mais barato
            starter_ids = {s['player']['id'] for s in starters}
            valid_reserves = [r for r in pos_pools[pos] if r['player']['id'] not in starter_ids and r['price'] <= cheapest_starter_price]
            
            bench_limit = 1
            reserves.extend(valid_reserves[:bench_limit])

        # Regra 1: Capitão deve ser preferencialmente do ataque
        captain = None
        if starters:
            def captain_score(p):
                score = p['expected_score_contextual']
                pos = p['player']['position']
                if pos == 'Atacante': return score * 1.3
                if pos == 'Meia': return score * 1.0
                return score * 0.5

            valid_captains = [p for p in starters if p['player']['position'] != 'Tecnico']
            if valid_captains:
                captain = max(valid_captains, key=captain_score)
                expected_score += captain['expected_score_contextual'] * 0.5 # Bônus do capitão

        reserva_luxo = None
        if reserves:
            def luxury_score(r):
                pos = r['player']['position']
                score = r['expected_score_contextual']
                if pos in ('Zagueiro', 'Lateral', 'Goleiro'):
                    return -999.0 # Nunca escolhe defensor
                elif pos == 'Atacante':
                    return score * 1.4 # Bônus artificial para priorizar atacantes
                elif pos == 'Meia':
                    return score * 1.0
                return -999.0

            valid_luxury = [r for r in reserves if luxury_score(r) > -900]
            if valid_luxury:
                reserva_luxo = max(valid_luxury, key=luxury_score)

        return {
            "players": starters,
            "reserves": reserves,
            "captain_id": captain['player']['id'] if captain else None,
            "luxury_reserve_id": reserva_luxo['player']['id'] if reserva_luxo else None,
            "cost": round(final_cost, 2),
            "expected_score": round(expected_score, 2)
        }

    def _build_principal(self, players_by_pos: dict, max_cost: float = None) -> dict:
        return self._assemble_433(players_by_pos, sort_key=lambda x: x['expected_score_contextual'], max_cost=max_cost)

    def _build_alternativo(self, players_by_pos: dict, max_cost: float = None) -> dict:
        def alt_sort(x):
            return x['expected_score_contextual'] * random.uniform(0.85, 1.0)
        return self._assemble_433(players_by_pos, sort_key=alt_sort, max_cost=max_cost)

    def _build_valorizacao(self, players_by_pos: dict, max_cost: float = None) -> dict:
        def val_filter(x):
            return x['price'] < 12.0 and x['last_score'] < 3.0

        def val_sort(x):
            return (x['expected_score_contextual'] - x['last_score']) / max(1.0, x['price'])

        return self._assemble_433(players_by_pos, sort_key=val_sort, filter_func=val_filter, max_cost=max_cost)

    def _build_aposta(self, players_by_pos: dict, max_cost: float = None) -> dict:
        def aposta_filter(x):
            return x['price'] < 18.0 and x['expected_score_contextual'] < 10.0
            
        def aposta_sort(x):
            return x['std_deviation'] * x['expected_score_contextual']

        return self._assemble_433(players_by_pos, sort_key=aposta_sort, filter_func=aposta_filter, max_cost=max_cost)
