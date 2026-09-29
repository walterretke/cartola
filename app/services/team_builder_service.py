import random
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.fixture import Fixture
from app.models.player import Player
from app.models.player_match_stats import PlayerMatchStats
from app.models.team_recommendation import TeamRecommendation
from app.services.recommendation_engine import RecommendationEngine

class TeamBuilderService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = RecommendationEngine(db)
        # Formação padrão solicitada: 4-3-3 (Posições do Cartola)
        # Ordenado do ataque para a defesa para priorizar escolhas ofensivas e evitar conflitos
        self.formation = {'Atacante': 3, 'Meia': 3, 'Lateral': 2, 'Zagueiro': 2, 'Goleiro': 1, 'Tecnico': 1}

    def generate_teams_for_round(self, season_year: int, round_number: int, max_cost: float = None) -> Dict[str, Any]:
        """
        Gera as 4 estratégias de escalação (Principal, Alternativo, Valorização, Aposta)
        """
        fixtures = self.db.query(Fixture).filter(Fixture.round_name == f'Regular Season - {round_number}').all()
        
        all_recs = []
        for f in fixtures:
            # Obter recomendações com o ESC
            recs = self.engine.get_recommendations_for_fixture(f.id, limit=60)
            for r in recs:
                player_obj = self.db.query(Player).filter(Player.id == r['player']['id']).first()
                if not player_obj:
                    continue
                
                # Regra 5: Somente status "Provável" (7) e "Dúvida" (2)
                if player_obj.cartola_status_id not in (2, 7):
                    continue
                
                # Adicionar dados extras como last_score, price, std_deviation
                last_stat = self.db.query(PlayerMatchStats).filter(
                    PlayerMatchStats.player_id == player_obj.id
                ).order_by(desc(PlayerMatchStats.match_date)).first()
                
                r['last_score'] = last_stat.match_cartola_score if last_stat else 0.0
                r['price'] = player_obj.price_cartoletas
                r['std_deviation'] = player_obj.score.std_deviation if player_obj.score else 0.0
                r['team_id'] = player_obj.team_id
                r['opponent_id'] = f.away_team_id if player_obj.team_id == f.home_team_id else f.home_team_id
                
                # Ajuste de posição caso a sincronização ainda tenha posições em inglês
                pos = player_obj.position
                if pos == 'Goalkeeper': pos = 'Goleiro'
                elif pos == 'Defender': pos = 'Zagueiro'
                elif pos == 'Midfielder': pos = 'Meia'
                elif pos == 'Attacker': pos = 'Atacante'
                r['player']['position'] = pos
                
                all_recs.append(r)

        # Separar por posição
        players_by_pos = {'Goleiro': [], 'Lateral': [], 'Zagueiro': [], 'Meia': [], 'Atacante': [], 'Tecnico': []}
        for r in all_recs:
            pos = r['player']['position']
            if pos in players_by_pos:
                players_by_pos[pos].append(r)

        teams = {
            "PRINCIPAL": self._build_principal(players_by_pos, max_cost),
            "ALTERNATIVO": self._build_alternativo(players_by_pos, max_cost),
            "VALORIZACAO": self._build_valorizacao(players_by_pos, max_cost),
            "APOSTA": self._build_aposta(players_by_pos, max_cost)
        }

        # Salvar no banco
        for strategy, squad in teams.items():
            if squad["players"]:
                rec = TeamRecommendation(
                    season_year=season_year,
                    round_number=round_number,
                    strategy=strategy,
                    formation="4-3-3",
                    expected_total_score=squad["expected_score"],
                    expected_total_cost=squad["cost"],
                    squad_data=squad
                )
                self.db.add(rec)
        
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
