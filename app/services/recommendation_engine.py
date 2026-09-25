import math
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.player import Player
from app.models.player_score import PlayerScore
from app.models.team_profile import TeamProfile
from app.models.fixture import Fixture

class RecommendationEngine:
    """
    Motor Contextual: Calcula o Expected Score Contextual (ESC) de um jogador
    para uma partida específica (Next Fixture).
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate_esc_for_player(self, player_id: int, next_fixture_id: int) -> Optional[Dict]:
        """
        Calcula o Expected Score Contextual para o jogador X na partida Y.
        Retorna o dicionário de análise.
        """
        player = self.db.query(Player).filter(Player.id == player_id).first()
        fixture = self.db.query(Fixture).filter(Fixture.id == next_fixture_id).first()
        
        if not player or not player.score or not fixture:
            return None

        # Determinar mando de campo
        is_home = (player.team_id == fixture.home_team_id)
        opponent_team_id = fixture.away_team_id if is_home else fixture.home_team_id
        
        opponent = self.db.query(TeamProfile).filter(TeamProfile.id == opponent_team_id).first()
        if not opponent:
            # Fallback seguro se não houver perfil do adversário
            return {
                "player_id": player.id,
                "fixture_id": fixture.id,
                "esc": player.score.smart_score,
                "reasoning": ["Sem dados do adversário. Usando Smart Score padrão."]
            }

        ps: PlayerScore = player.score
        reasoning = []

        # 1. Base Contextual (Mando de Campo)
        if is_home:
            base_score = ps.avg_points_home
            context_matches = ps.home_matches
            reasoning.append(f"Joga em CASA (Média casa: {base_score:.2f})")
        else:
            base_score = ps.avg_points_away
            context_matches = ps.away_matches
            reasoning.append(f"Joga FORA (Média fora: {base_score:.2f})")

        # Blend se amostragem no mando for baixa
        if context_matches < 3:
            weight = context_matches / 3.0
            base_score = (base_score * weight) + (ps.avg_points * (1 - weight))
            reasoning.append("Amostragem de mando baixa, mesclando com média geral.")

        # 2. Ponderação com Momentum (Fator 7)
        weighted_base = (base_score * 0.45) + (ps.last_3_avg * 0.35) + (ps.last_5_avg * 0.20)
        
        if ps.trend == "rising":
            momentum_mod = 1.06
            reasoning.append("Momentum de alta (+6%).")
        elif ps.trend == "falling":
            momentum_mod = 0.94
            reasoning.append("Momentum de queda (-6%).")
        else:
            momentum_mod = 1.0

        # 3. Probabilidade de Clean Sheet (Fator 4) & Força Adversária (Fator 2 e 3)
        # Ajuste de ameaça baseado na média de gols do adversário no mando atual
        if is_home:
            opp_threat = opponent.avg_goals_scored_away if opponent.away_matches > 0 else opponent.avg_goals_scored
            opp_defense_weakness = opponent.avg_goals_conceded_away if opponent.away_matches > 0 else opponent.avg_goals_conceded
        else:
            opp_threat = opponent.avg_goals_scored_home if opponent.home_matches > 0 else opponent.avg_goals_scored
            opp_defense_weakness = opponent.avg_goals_conceded_home if opponent.home_matches > 0 else opponent.avg_goals_conceded

        sg_probability = 0.0
        opponent_factor = 1.0

        if player.position in ("Goalkeeper", "Defender"):
            # Poisson P(X=0)
            if opp_threat == 0.0:
                sg_probability = 0.40 # Padrão conservador se sem dados
            else:
                # Se meu time sofre poucos gols, a ameaça diminui. 
                # (Simplificação: usamos apenas a ameaça adversária pura com ajuste de mando)
                adjusted_threat = opp_threat * (0.85 if is_home else 1.15)
                sg_probability = math.exp(-adjusted_threat)
            
            sg_expected_pts = sg_probability * 5.0
            reasoning.append(f"Adversário marca {opp_threat:.2f} gols no cenário. Probabilidade de SG: {sg_probability*100:.1f}% (+{sg_expected_pts:.2f} pts).")
            
            # Adiciona a expectativa de SG na base
            weighted_base += (sg_expected_pts * 0.4) # Peso parcial pois média já contém SGs passados
            
        else:
            # Atacantes e Meias: adversário com defesa fraca é bom
            if opp_defense_weakness > 1.5:
                opponent_factor = 1.15
                reasoning.append(f"Defesa adversária FRACA ({opp_defense_weakness:.2f} gols/jogo). Bônus ofensivo (+15%).")
            elif opp_defense_weakness < 0.8 and opp_defense_weakness > 0:
                opponent_factor = 0.85
                reasoning.append(f"Defesa adversária FORTE ({opp_defense_weakness:.2f} gols/jogo). Penalidade ofensiva (-15%).")

        # 4. Consistência e Minutos (Fatores 6 e 8)
        consistency_mod = 0.92 + (ps.consistency_index / 100.0) * 0.16
        if consistency_mod > 1.0:
            reasoning.append("Jogador muito consistente (Ajuste de segurança positivo).")

        avg_minutes = ps.total_minutes / max(ps.matches_played, 1)
        if avg_minutes >= 80:
            minutes_mod = 1.0
        elif avg_minutes >= 60:
            minutes_mod = 0.85
            reasoning.append("Risco de substituição antecipada (-15%).")
        elif avg_minutes >= 30:
            minutes_mod = 0.60
            reasoning.append("Risco alto: Reserva de uso frequente (-40%).")
        else:
            minutes_mod = 0.30
            reasoning.append("Risco CRÍTICO: Dificilmente joga o tempo suficiente (-70%).")

        # Cálculo Final
        esc = (
            weighted_base
            * opponent_factor
            * momentum_mod
            * minutes_mod
            * consistency_mod
        )

        # Se o ESC ficar absurdo (muito pequeno ou muito grande), aplicar limite amigável
        esc = max(-2.0, min(esc, 25.0))

        return {
            "player": {
                "id": player.id,
                "name": player.name,
                "position": player.position,
                "team_name": player.team_name,
                "photo_url": player.photo_url
            },
            "smart_score": ps.smart_score,
            "expected_score_contextual": round(esc, 2),
            "is_home": is_home,
            "opponent": opponent.name,
            "sg_probability": round(sg_probability * 100, 1) if player.position in ("Goalkeeper", "Defender") else None,
            "reasoning": reasoning
        }

    def get_recommendations_for_fixture(self, fixture_id: int, limit: int = 11) -> List[Dict]:
        """Gera recomendações de ambos os times para uma partida."""
        fixture = self.db.query(Fixture).filter(Fixture.id == fixture_id).first()
        if not fixture:
            return []
            
        players = self.db.query(Player).filter(
            Player.team_id.in_([fixture.home_team_id, fixture.away_team_id])
        ).all()
        
        recs = []
        for p in players:
            r = self.calculate_esc_for_player(p.id, fixture_id)
            if r:
                recs.append(r)
                
        # Ordena pelo maior ESC
        recs.sort(key=lambda x: x["expected_score_contextual"], reverse=True)
        return recs[:limit]
