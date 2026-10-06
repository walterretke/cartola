import math
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.scout_action import ScoutAction
from app.models.player import Player
from app.models.player_match_stats import PlayerMatchStats
from app.models.player_score import PlayerScore
from app.core.cartola import GOLEIRO, LATERAL, ZAGUEIRO, MEIA, ATACANTE, normalize_position

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Motor de inteligência COMPLETO do CartolaAI.
    
    Responsabilidades:
    1. Calcular a pontuação oficial do Cartola para cada partida (match_cartola_score)
    2. Agregar médias por scout, casa/fora, oscilação, momentum
    3. Calcular indicadores avançados (potencial ofensivo/defensivo, risco disciplinar)
    4. Gerar o Smart Score final ponderado por posição
    """

    # ========== PESOS POR POSIÇÃO PARA O SMART SCORE ==========
    # Cada posição tem pesos diferentes que refletem o que REALMENTE importa
    # para gerar pontuação consistente no Cartola
    POSITION_WEIGHTS = {
        GOLEIRO: {
            # Goleiro pontua MUITO com SG (+5.0 por jogo!) e DE (+1.3 cada defesa).
            # DP (+7.0) é raro mas devastador. Gols sofridos (-1.0 cada) destroem.
            "offensive_weight": 0.05,   # Goleiro quase nunca pontua no ataque
            "defensive_weight": 0.70,   # SG, DE, DP são tudo
            "discipline_weight": 0.25,  # CA/CV destroem goleiro (perde SG também)
        },
        ZAGUEIRO: {
            # Zagueiro/Lateral: SG (+5.0) é o scout mais valioso.
            # DS (+1.5 cada) é consistente. Gols/Assistências são bônus raros.
            # FC (-0.3) e CA (-1.0) são frequentes e perigosos.
            "offensive_weight": 0.20,   # Gols de zagueiro são raros mas valem muito
            "defensive_weight": 0.55,   # SG + DS são o pão de cada dia
            "discipline_weight": 0.25,  # Zagueiros levam muita falta e cartão
        },
        MEIA: {
            # Meia: posição mais equilibrada. A (+5.0), FS (+0.5 cada, acumula),
            # FD (+1.2 cada). DS (+1.5) também conta.
            # É a posição que mais se beneficia de VOLUME de ações.
            "offensive_weight": 0.50,   # G, A, FD, FS, FF
            "defensive_weight": 0.30,   # DS, SG (se no esquema defensivo)
            "discipline_weight": 0.20,  # Cartões são menos frequentes
        },
        ATACANTE: {
            # Atacante: G (+8.0) é TUDO. A (+5.0) complementa.
            # FD (+1.2) e FF (+0.8) mostram volume de finalização.
            # FS (+0.5) acumula bem para atacantes que sofrem muita falta.
            "offensive_weight": 0.75,   # G, A, FD, FF, FT, FS
            "defensive_weight": 0.05,   # Atacante quase não faz scout defensivo
            "discipline_weight": 0.20,  # PP (-4.0) é devastador
        },
    }
    # Lateral pontua como zagueiro (SG + DS)
    POSITION_WEIGHTS[LATERAL] = POSITION_WEIGHTS[ZAGUEIRO]

    def __init__(self, db: Session):
        self.db = db
        self.scouts_map: Dict[str, float] = self._load_scouts_map()

    def _load_scouts_map(self) -> Dict[str, float]:
        """Carrega a tabela mestre de pontuações do Cartola."""
        actions = self.db.query(ScoutAction).all()
        return {action.code: action.points for action in actions}

    # ================================================================
    # 1. PONTUAÇÃO OFICIAL DO CARTOLA POR PARTIDA
    # ================================================================
    def calculate_match_cartola_score(self, stats: PlayerMatchStats, position: str = "") -> float:
        """
        Calcula a pontuação OFICIAL do Cartola para uma partida específica.
        Usa exatamente os mesmos valores da tabela mestre de scouts.
        """
        pts = self.scouts_map
        score = 0.0

        # --- ATAQUE ---
        score += stats.goals * pts.get("G", 8.0)
        score += stats.assists * pts.get("A", 5.0)
        score += stats.shots_woodwork * pts.get("FT", 3.0)
        score += stats.shots_on_target * pts.get("FD", 1.2)
        score += stats.shots_off_target * pts.get("FF", 0.8)
        score += stats.penalties_won * pts.get("PS", 1.0)
        score += stats.fouls_drawn * pts.get("FS", 0.5)
        score += stats.offsides * pts.get("I", -0.1)
        score += stats.penalties_missed * pts.get("PP", -4.0)

        # --- DEFESA ---
        score += stats.tackles * pts.get("DS", 1.5)
        if stats.clean_sheet:
            score += pts.get("SG", 5.0)
        score += stats.saves * pts.get("DE", 1.3)
        score += stats.penalties_saved * pts.get("DP", 7.0)
        score += stats.fouls_committed * pts.get("FC", -0.3)
        score += stats.yellow_cards * pts.get("CA", -1.0)
        score += stats.red_cards * pts.get("CV", -3.0)
        score += stats.goals_conceded * pts.get("GS", -1.0)
        score += stats.penalties_committed * pts.get("PC", -1.0)
        score += stats.own_goals * pts.get("GC", -3.0)

        return round(score, 2)

    # ================================================================
    # 2. CÁLCULO COMPLETO DO PLAYER SCORE (INTELIGÊNCIA TOTAL)
    # ================================================================
    def calculate_player_score(self, player: Player) -> PlayerScore:
        """
        Análise COMPLETA do atleta:
        - Pontuação Cartola por partida
        - Médias gerais, casa e fora
        - Média individual de cada scout
        - Indicadores avançados (duelos, passes decisivos, dribles)
        - Potencial ofensivo, defensivo e risco disciplinar
        - Oscilação, consistência e momentum
        - Smart Score final ponderado por posição
        """
        matches: List[PlayerMatchStats] = (
            self.db.query(PlayerMatchStats)
            .filter(PlayerMatchStats.player_id == player.id)
            .order_by(PlayerMatchStats.match_date.asc())
            .all()
        )

        # Buscar ou instanciar o PlayerScore
        player_score = (
            self.db.query(PlayerScore)
            .filter(PlayerScore.player_id == player.id)
            .first()
        )
        if not player_score:
            player_score = PlayerScore(player_id=player.id)
            self.db.add(player_score)

        if not matches:
            self._reset_score(player_score)
            return player_score

        # ========== FASE 1: Pontuar cada partida e coletar dados ==========
        scores: List[float] = []
        home_scores: List[float] = []
        away_scores: List[float] = []

        # Acumuladores de scouts
        total_goals = 0
        total_assists = 0
        total_shots_on = 0
        total_shots_off = 0
        total_fouls_drawn = 0
        total_tackles = 0
        total_saves = 0
        total_fouls_committed = 0
        total_yellow = 0
        total_red = 0
        total_goals_conceded = 0
        total_clean_sheets = 0
        total_penalties_missed = 0
        total_penalties_won = 0

        # Acumuladores de dados extras
        total_rating = 0.0
        rating_count = 0
        total_passes_key = 0
        total_dribbles_success = 0
        total_duels_total = 0
        total_duels_won = 0
        total_interceptions = 0
        total_passes_accuracy = 0
        total_minutes = 0

        for m in matches:
            pts = self.calculate_match_cartola_score(m, player.position)
            m.match_cartola_score = pts
            scores.append(pts)

            if m.is_home:
                home_scores.append(pts)
            else:
                away_scores.append(pts)

            # Acumular scouts
            total_goals += m.goals or 0
            total_assists += m.assists or 0
            total_shots_on += m.shots_on_target or 0
            total_shots_off += m.shots_off_target or 0
            total_fouls_drawn += m.fouls_drawn or 0
            total_tackles += m.tackles or 0
            total_saves += m.saves or 0
            total_fouls_committed += m.fouls_committed or 0
            total_yellow += m.yellow_cards or 0
            total_red += m.red_cards or 0
            total_goals_conceded += m.goals_conceded or 0
            total_penalties_missed += m.penalties_missed or 0
            total_penalties_won += m.penalties_won or 0
            if m.clean_sheet:
                total_clean_sheets += 1

            # Acumular dados extras
            if m.rating:
                total_rating += m.rating
                rating_count += 1
            total_passes_key += m.passes_key or 0
            total_dribbles_success += m.dribbles_success or 0
            total_duels_total += m.duels_total or 0
            total_duels_won += m.duels_won or 0
            total_interceptions += m.interceptions or 0
            total_passes_accuracy += m.passes_accuracy or 0
            total_minutes += m.minutes_played or 0

        n = len(scores)
        total_pts = sum(scores)
        current_avg_pts = (total_pts / n) if n > 0 else 0.0

        avg_home = (sum(home_scores) / len(home_scores)) if home_scores else current_avg_pts
        avg_away = (sum(away_scores) / len(away_scores)) if away_scores else current_avg_pts

        # ========== PRIORI BAYESIANA (Usando Histórico da Temporada Passada e LDC) ==========
        from app.models.player_season_history import PlayerSeasonHistory
        from datetime import datetime
        current_year = datetime.now().year
        
        # Buscar histórico do ano passado (ou o mais recente disponível)
        historical_profile = self.db.query(PlayerSeasonHistory).filter(
            PlayerSeasonHistory.player_id == player.id,
            PlayerSeasonHistory.season_year < current_year
        ).order_by(PlayerSeasonHistory.season_year.desc()).first()

        # A "Regra Viveros" (Decaimento Rápido para LDC < 1.0)
        # Se veio da Série B, a paciência da IA dura só 3 jogos. Se veio da Série A, dura 6.
        if historical_profile:
            ldc = historical_profile.league_difficulty_weight
            historical_pts = historical_profile.avg_points * ldc
            patience_matches = 3 if ldc < 1.0 else 6
            prior_weight = max(0, patience_matches - n)
        else:
            historical_pts = 0.0
            prior_weight = 0
        
        if prior_weight > 0 and historical_profile:
            # Fórmula de Bayes: Mescla a pontuação real atual com o peso do histórico penalizado
            avg_pts = ((current_avg_pts * n) + (historical_pts * prior_weight)) / (n + prior_weight)
        else:
            avg_pts = current_avg_pts

        # ========== FASE 2: Oscilação e Consistência ==========
        if n > 1:
            variance = sum((s - avg_pts) ** 2 for s in scores) / n
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        if std_dev == 0:
            consistency = 80.0 if n > 0 else 0.0
        else:
            ratio = std_dev / (abs(avg_pts) + 1.0)
            consistency = max(0.0, min(100.0, round(100.0 - (ratio * 35.0), 1)))

        # ========== FASE 3: Momentum e EMA (Exponential Moving Average) ==========
        last_3 = scores[-3:] if len(scores) >= 3 else scores
        last_5 = scores[-5:] if len(scores) >= 5 else scores
        last_3_avg = sum(last_3) / len(last_3) if last_3 else 0.0
        last_5_avg = sum(last_5) / len(last_5) if last_5 else 0.0

        # Calcular Média Móvel Exponencial (EMA)
        # alpha = 0.35 (Peso do jogo atual é 35%, peso do histórico é 65%)
        alpha = 0.35
        
        # O EMA começa sendo o histórico penalizado do ano passado ou o primeiro jogo do ano atual.
        if historical_profile and historical_profile.avg_points != 0:
            ema = historical_profile.avg_points * historical_profile.league_difficulty_weight
        else:
            ema = scores[0] if scores else 0.0
            
        for i, s in enumerate(scores):
            if i == 0 and not historical_profile:
                # Já inicializado
                continue
            ema = (s * alpha) + (ema * (1 - alpha))

        # Tendência: comparar últimos 5 com média geral
        if n >= 5:
            if last_5_avg > avg_pts * 1.10:
                trend = "rising"
            elif last_5_avg < avg_pts * 0.90:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # ========== FASE 4: Médias por scout ==========
        avg_goals = total_goals / n
        avg_assists = total_assists / n
        avg_shots_on = total_shots_on / n
        avg_shots_off = total_shots_off / n
        avg_fouls_drawn = total_fouls_drawn / n
        avg_tackles = total_tackles / n
        avg_saves_val = total_saves / n
        avg_fouls_committed = total_fouls_committed / n
        avg_yellow = total_yellow / n
        avg_goals_conc = total_goals_conceded / n
        clean_sheet_pct = (total_clean_sheets / n) * 100

        # ========== FASE 5: Indicadores Avançados ==========
        avg_rating = (total_rating / rating_count) if rating_count > 0 else 0.0
        avg_passes_key = total_passes_key / n
        avg_dribbles_success = total_dribbles_success / n
        avg_duels_won = total_duels_won / n
        avg_interceptions = total_interceptions / n
        duel_win_pct = (total_duels_won / total_duels_total * 100) if total_duels_total > 0 else 0.0
        pass_accuracy_avg = total_passes_accuracy / n if n > 0 else 0.0

        # ========== FASE 6: Potenciais ==========
        pts_map = self.scouts_map

        # Potencial Ofensivo: quanto o jogador tende a marcar de ataque por jogo
        offensive_potential = (
            avg_goals * pts_map.get("G", 8.0) +
            avg_assists * pts_map.get("A", 5.0) +
            avg_shots_on * pts_map.get("FD", 1.2) +
            avg_shots_off * pts_map.get("FF", 0.8) +
            avg_fouls_drawn * pts_map.get("FS", 0.5) +
            (total_penalties_won / n) * pts_map.get("PS", 1.0)
        )

        # Potencial Defensivo: quanto o jogador tende a marcar de defesa por jogo
        defensive_potential = (
            avg_tackles * pts_map.get("DS", 1.5) +
            (clean_sheet_pct / 100) * pts_map.get("SG", 5.0) +
            avg_saves_val * pts_map.get("DE", 1.3) +
            avg_interceptions * 0.5  # Bônus de inteligência: interceptações não dão scout mas indicam qualidade
        )

        # Risco Disciplinar: quanto o jogador tende a PERDER por jogo com indisciplina
        discipline_risk = abs(
            avg_fouls_committed * pts_map.get("FC", -0.3) +
            avg_yellow * pts_map.get("CA", -1.0) +
            (total_red / n) * pts_map.get("CV", -3.0) +
            (total_penalties_missed / n) * pts_map.get("PP", -4.0)
        )

        # ========== FASE 7: SMART SCORE FINAL ==========
        position = normalize_position(player.position)
        weights = self.POSITION_WEIGHTS.get(position, self.POSITION_WEIGHTS[MEIA])

        # Base ponderada por posição
        weighted_score = (
            offensive_potential * weights["offensive_weight"] +
            defensive_potential * weights["defensive_weight"] -
            discipline_risk * weights["discipline_weight"]
        )

        # Componente de forma e histórico:
        # 40% média histórica + 35% momentum recente + 25% base ponderada por posição
        form_score = (avg_pts * 0.40) + (last_5_avg * 0.35) + (weighted_score * 0.25)

        # Modificador de regularidade: jogadores consistentes ganham bônus de segurança
        regularity_multiplier = 0.88 + (consistency / 100.0) * 0.24  # 0.88 a 1.12

        # Modificador de mando: bônus sutil para quem joga muito bem em casa
        home_away_spread = avg_home - avg_away
        if home_away_spread > 3.0:
            # Jogador muito dependente de jogar em casa — leve penalidade
            mando_modifier = 0.97
        elif home_away_spread < -1.0:
            # Jogador joga BEM fora de casa — bônus
            mando_modifier = 1.03
        else:
            mando_modifier = 1.0

        # Penalidade de pequena amostragem
        sample_penalty = min(1.0, n / 5.0)

        # Bônus de nota alta (rating da API > 7.0 indica jogador dominante)
        rating_bonus = 1.0
        if avg_rating >= 7.5:
            rating_bonus = 1.05
        elif avg_rating >= 7.0:
            rating_bonus = 1.02
        elif avg_rating > 0 and avg_rating < 6.0:
            rating_bonus = 0.97

        smart_score = round(
            form_score * regularity_multiplier * mando_modifier * sample_penalty * rating_bonus,
            2
        )

        # ========== SALVAR TUDO ==========
        player_score.matches_played = n
        player_score.home_matches = len(home_scores)
        player_score.away_matches = len(away_scores)
        player_score.total_minutes = total_minutes
        player_score.total_points = round(total_pts, 2)
        player_score.avg_points = round(avg_pts, 2)
        player_score.avg_points_home = round(avg_home, 2)
        player_score.avg_points_away = round(avg_away, 2)
        player_score.std_deviation = round(std_dev, 2)
        player_score.consistency_index = consistency
        player_score.min_score = round(min(scores), 2)
        player_score.max_score = round(max(scores), 2)
        player_score.last_3_avg = round(last_3_avg, 2)
        player_score.last_5_avg = round(last_5_avg, 2)
        player_score.ema_points = round(ema, 2)
        player_score.trend = trend

        # Médias por scout
        player_score.avg_goals = round(avg_goals, 3)
        player_score.avg_assists = round(avg_assists, 3)
        player_score.avg_shots_on_target = round(avg_shots_on, 3)
        player_score.avg_shots_off_target = round(avg_shots_off, 3)
        player_score.avg_fouls_drawn = round(avg_fouls_drawn, 3)
        player_score.avg_tackles = round(avg_tackles, 3)
        player_score.avg_saves = round(avg_saves_val, 3)
        player_score.avg_fouls_committed = round(avg_fouls_committed, 3)
        player_score.avg_yellow_cards = round(avg_yellow, 3)
        player_score.avg_goals_conceded = round(avg_goals_conc, 3)
        player_score.clean_sheet_pct = round(clean_sheet_pct, 1)

        # Indicadores avançados
        player_score.avg_rating = round(avg_rating, 2)
        player_score.avg_passes_key = round(avg_passes_key, 3)
        player_score.avg_dribbles_success = round(avg_dribbles_success, 3)
        player_score.avg_duels_won = round(avg_duels_won, 3)
        player_score.avg_interceptions = round(avg_interceptions, 3)
        player_score.duel_win_pct = round(duel_win_pct, 1)
        player_score.pass_accuracy_avg = round(pass_accuracy_avg, 1)

        # Potenciais
        player_score.offensive_potential = round(offensive_potential, 2)
        player_score.defensive_potential = round(defensive_potential, 2)
        player_score.discipline_risk = round(discipline_risk, 2)

        player_score.smart_score = smart_score

        return player_score

    def _reset_score(self, ps: PlayerScore):
        """Zera todos os campos de um PlayerScore (jogador sem partidas)."""
        ps.matches_played = 0
        ps.home_matches = 0
        ps.away_matches = 0
        ps.total_minutes = 0
        ps.total_points = 0.0
        ps.avg_points = 0.0
        ps.avg_points_home = 0.0
        ps.avg_points_away = 0.0
        ps.std_deviation = 0.0
        ps.consistency_index = 0.0
        ps.min_score = 0.0
        ps.max_score = 0.0
        ps.last_3_avg = 0.0
        ps.last_5_avg = 0.0
        ps.ema_points = 0.0
        ps.trend = "stable"
        ps.avg_goals = 0.0
        ps.avg_assists = 0.0
        ps.avg_shots_on_target = 0.0
        ps.avg_shots_off_target = 0.0
        ps.avg_fouls_drawn = 0.0
        ps.avg_tackles = 0.0
        ps.avg_saves = 0.0
        ps.avg_fouls_committed = 0.0
        ps.avg_yellow_cards = 0.0
        ps.avg_goals_conceded = 0.0
        ps.clean_sheet_pct = 0.0
        ps.avg_rating = 0.0
        ps.avg_passes_key = 0.0
        ps.avg_dribbles_success = 0.0
        ps.avg_duels_won = 0.0
        ps.avg_interceptions = 0.0
        ps.duel_win_pct = 0.0
        ps.pass_accuracy_avg = 0.0
        ps.offensive_potential = 0.0
        ps.defensive_potential = 0.0
        ps.discipline_risk = 0.0
        ps.smart_score = 0.0

    def calculate_all_scores(self) -> int:
        """Recalcula os scores de todos os jogadores cadastrados no banco."""
        players = self.db.query(Player).all()
        count = 0
        for p in players:
            self.calculate_player_score(p)
            count += 1
        self.db.commit()
        return count
