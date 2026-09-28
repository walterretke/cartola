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
        # Formação padrão solicitada: 4-3-3
        self.formation = {'Goalkeeper': 1, 'Defender': 4, 'Midfielder': 3, 'Attacker': 3}

    def generate_teams_for_round(self, season_year: int, round_number: int) -> Dict[str, Any]:
        """
        Gera as 4 estratégias de escalação (Principal, Alternativo, Valorização, Aposta)
        """
        # Obter jogos da rodada
        # OBS: Aqui assumimos que round_name no fixture contém a rodada, 
        # ou usamos uma lógica customizada dependendo de como os dados estão no banco.
        # Por simplificação, vamos buscar os fixtures que batem com os IDs ou lógica de round.
        
        # Simulando a busca de todos os jogadores pontuados para uma rodada
        # Na vida real, seria:
        # fixtures = self.db.query(Fixture).filter(Fixture.season == season_year, Fixture.round == round_number).all()
        # Aqui, vamos usar a função engine.get_recommendations_for_fixture para cada partida da rodada.
        
        # Como não temos um campo exato de rodada no model de Fixture exposto facilmente agora,
        # vamos usar uma query flexível ou passar os fixture_ids.
        # Para fins de implementação do gatilho, vamos buscar os fixtures:
        # (Ajuste a query de fixtures conforme a modelagem de liga/temporada atual do DB)
        # Vamos assumir que buscaremos as fixtures dessa rodada:
        fixtures = self.db.query(Fixture).filter(Fixture.round_name == f'Regular Season - {round_number}').all()
        
        all_recs = []
        for f in fixtures:
            # Obter recomendações com o ESC
            recs = self.engine.get_recommendations_for_fixture(f.id, limit=60)
            for r in recs:
                # Adicionar dados extras como last_score, price, std_deviation
                player_obj = self.db.query(Player).filter(Player.id == r['player']['id']).first()
                if not player_obj:
                    continue
                
                # Obter last score
                last_stat = self.db.query(PlayerMatchStats).filter(
                    PlayerMatchStats.player_id == player_obj.id
                ).order_by(desc(PlayerMatchStats.match_date)).first()
                
                r['last_score'] = last_stat.match_cartola_score if last_stat else 0.0
                r['price'] = player_obj.price_cartoletas
                r['std_deviation'] = player_obj.score.std_deviation if player_obj.score else 0.0
                
                all_recs.append(r)

        # Separar por posição
        players_by_pos = {'Goalkeeper': [], 'Defender': [], 'Midfielder': [], 'Attacker': []}
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

        for pos, limit in self.formation.items():
            pool = players_by_pos.get(pos, [])
            if filter_func:
                pool = [p for p in pool if filter_func(p)]
            
            pool.sort(key=sort_key, reverse=reverse)
            
            pos_starters = pool[:limit]
            starters.extend(pos_starters)
            
            for s in pos_starters:
                cost += s['price']
                expected_score += s['expected_score_contextual']
            
            if pos_starters:
                cheapest_starter_price = min(s['price'] for s in pos_starters)
                valid_reserves = [r for r in pool[limit:] if r['price'] <= cheapest_starter_price]
                bench_limit = 2 if pos == 'Defender' else 1
                reserves.extend(valid_reserves[:bench_limit])

        captain = None
        if starters:
            captain = max(starters, key=lambda x: x['expected_score_contextual'])
            expected_score += captain['expected_score_contextual'] * 0.5 # Bônus do capitão

        return {
            "players": starters,
            "reserves": reserves,
            "captain_id": captain['player']['id'] if captain else None,
            "cost": round(cost, 2),
            "expected_score": round(expected_score, 2)
        }

    def _build_principal(self, players_by_pos: dict) -> dict:
        # Time com maior ESC possível
        return self._assemble_433(
            players_by_pos, 
            sort_key=lambda x: x['expected_score_contextual']
        )

    def _build_alternativo(self, players_by_pos: dict) -> dict:
        # Mantém a ideia do principal, mas adiciona um pouco de ruído (ou descarta os top 1)
        # Vamos penalizar levemente o ESC dos 2 melhores de cada posição para diversificar
        def alt_sort(x):
            return x['expected_score_contextual'] * random.uniform(0.85, 1.0)
        
        return self._assemble_433(players_by_pos, sort_key=alt_sort)

    def _build_valorizacao(self, players_by_pos: dict) -> dict:
        # Foco em jogadores baratos (ex: < 10) e que foram mal na rodada anterior (last_score baixo), 
        # mas que possuem um bom ESC na rodada atual.
        # Métrica de valorização: (ESC - last_score) / (price + 1)
        def val_filter(x):
            return x['price'] < 12.0 and x['last_score'] < 3.0

        def val_sort(x):
            # Prioriza quem tem maior diferença entre expectativa atual e nota passada, custando pouco
            return (x['expected_score_contextual'] - x['last_score']) / max(1.0, x['price'])

        return self._assemble_433(players_by_pos, sort_key=val_sort, filter_func=val_filter)

    def _build_aposta(self, players_by_pos: dict) -> dict:
        # Alta volatilidade (desvio padrão) + ignorar os favoritos absolutos
        def aposta_filter(x):
            # Tira os "modinhas" muito óbvios (ESC altíssimo ou preço muito alto)
            return x['price'] < 18.0 and x['expected_score_contextual'] < 10.0
            
        def aposta_sort(x):
            # Ordena por desvio padrão (imprevisibilidade) * ESC
            return x['std_deviation'] * x['expected_score_contextual']

        return self._assemble_433(players_by_pos, sort_key=aposta_sort, filter_func=aposta_filter)
