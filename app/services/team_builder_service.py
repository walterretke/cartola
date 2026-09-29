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
        self.formation = {'Atacante': 3, 'Meia': 3, 'Lateral': 2, 'Zagueiro': 2, 'Goleiro': 1}

    def generate_teams_for_round(self, season_year: int, round_number: int) -> Dict[str, Any]:
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
        players_by_pos = {'Goleiro': [], 'Lateral': [], 'Zagueiro': [], 'Meia': [], 'Atacante': []}
        for r in all_recs:
            pos = r['player']['position']
            if pos in players_by_pos:
                players_by_pos[pos].append(r)

        teams = {
            "PRINCIPAL": self._build_principal(players_by_pos),
            "ALTERNATIVO": self._build_alternativo(players_by_pos),
            "VALORIZACAO": self._build_valorizacao(players_by_pos),
            "APOSTA": self._build_aposta(players_by_pos)
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

    def _assemble_433(self, players_by_pos: dict, sort_key, reverse=True, filter_func=None) -> dict:
        """Helper para montar 4-3-3 genérico"""
        starters = []
        reserves = []
        cost = 0.0
        expected_score = 0.0
        
        # Regra 6: Evitar zagueiro do time que o atacante vai enfrentar
        teams_we_are_attacking = set()

        for pos, limit in self.formation.items():
            pool = players_by_pos.get(pos, [])
            if filter_func:
                pool = [p for p in pool if filter_func(p)]
            
            if pos in ('Zagueiro', 'Lateral', 'Goleiro'):
                pool = [p for p in pool if p['team_id'] not in teams_we_are_attacking]
            
            pool.sort(key=sort_key, reverse=reverse)
            
            pos_starters = pool[:limit]
            starters.extend(pos_starters)
            
            for s in pos_starters:
                cost += s['price']
                expected_score += s['expected_score_contextual']
                if pos == 'Atacante':
                    teams_we_are_attacking.add(s['opponent_id'])
            
            if pos_starters:
                cheapest_starter_price = min(s['price'] for s in pos_starters)
                valid_reserves = [r for r in pool[limit:] if r['price'] <= cheapest_starter_price]
                bench_limit = 1
                if pos in ('Zagueiro', 'Lateral'):
                    bench_limit = 1
                reserves.extend(valid_reserves[:bench_limit])

        # Regra 1: Capitão deve ser preferencialmente do ataque e talvez meio-campistas se muita vantagem estatística
        captain = None
        if starters:
            def captain_score(p):
                score = p['expected_score_contextual']
                if p['player']['position'] == 'Atacante':
                    return score * 1.3 # Bônus artificial para priorizar atacante
                elif p['player']['position'] == 'Meia':
                    return score * 1.0
                return score * 0.5 # Desprioriza fortemente defesa para capitão

            captain = max(starters, key=captain_score)
            expected_score += captain['expected_score_contextual'] * 0.5 # Bônus do capitão real

        return {
            "players": starters,
            "reserves": reserves,
            "captain_id": captain['player']['id'] if captain else None,
            "cost": round(cost, 2),
            "expected_score": round(expected_score, 2)
        }

    def _build_principal(self, players_by_pos: dict) -> dict:
        return self._assemble_433(players_by_pos, sort_key=lambda x: x['expected_score_contextual'])

    def _build_alternativo(self, players_by_pos: dict) -> dict:
        def alt_sort(x):
            return x['expected_score_contextual'] * random.uniform(0.85, 1.0)
        return self._assemble_433(players_by_pos, sort_key=alt_sort)

    def _build_valorizacao(self, players_by_pos: dict) -> dict:
        def val_filter(x):
            return x['price'] < 12.0 and x['last_score'] < 3.0

        def val_sort(x):
            return (x['expected_score_contextual'] - x['last_score']) / max(1.0, x['price'])

        return self._assemble_433(players_by_pos, sort_key=val_sort, filter_func=val_filter)

    def _build_aposta(self, players_by_pos: dict) -> dict:
        def aposta_filter(x):
            return x['price'] < 18.0 and x['expected_score_contextual'] < 10.0
            
        def aposta_sort(x):
            return x['std_deviation'] * x['expected_score_contextual']

        return self._assemble_433(players_by_pos, sort_key=aposta_sort, filter_func=aposta_filter)
