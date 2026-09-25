import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.player_match_stats import PlayerMatchStats
from app.services.api_football_client import ApiFootballClient
from app.services.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class SyncService:
    """
    Serviço que sincroniza jogadores e estatísticas REAIS da API-Football (api-sports.io)
    e alimenta o banco com TODOS os scouts granulares + dados extras para inteligência.
    """

    def __init__(self, db: Session, client: Optional[ApiFootballClient] = None):
        self.db = db
        self.client = client or ApiFootballClient()
        self.scoring_engine = ScoringEngine(db=db)

    async def sync_fixtures_by_range(
        self,
        from_date: str,
        to_date: str
    ) -> Dict[str, Any]:
        """
        Sincroniza partidas num intervalo de datas.
        Para cada partida finalizada, busca os stats de cada jogador.
        """
        logger.info(f"Sincronizando partidas de {from_date} a {to_date}...")

        try:
            fixtures = await self.client.get_fixtures(from_date=from_date, to_date=to_date)
        except Exception as e:
            logger.error(f"Falha ao buscar fixtures: {e}")
            raise e

        # Filtrar apenas partidas finalizadas (status FT, AET, PEN)
        finished = [f for f in fixtures if f.get("fixture", {}).get("status", {}).get("short") in ("FT", "AET", "PEN")]
        logger.info(f"Total de partidas encontradas: {len(fixtures)}, finalizadas: {len(finished)}")

        synced_players = 0
        synced_stats = 0
        skipped_fixtures = 0

        for f_data in finished:
            fixture_info = f_data.get("fixture", {})
            league_info = f_data.get("league", {})
            teams_info = f_data.get("teams", {})
            goals_info = f_data.get("goals", {})

            fixture_id = fixture_info.get("id")
            if not fixture_id:
                continue

            # Verificar se já processamos esta partida
            existing = self.db.query(PlayerMatchStats).filter(
                PlayerMatchStats.fixture_id == fixture_id
            ).first()
            if existing:
                skipped_fixtures += 1
                continue

            match_date_str = fixture_info.get("date")
            match_date = None
            if match_date_str:
                try:
                    match_date = datetime.fromisoformat(
                        match_date_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except (ValueError, TypeError):
                    pass

            round_name = league_info.get("round", "")

            home_team_id = teams_info.get("home", {}).get("id")
            home_team_name = teams_info.get("home", {}).get("name")
            away_team_id = teams_info.get("away", {}).get("id")
            away_team_name = teams_info.get("away", {}).get("name")

            # Placar (para calcular SG e GS)
            home_goals_scored = goals_info.get("home") or 0
            away_goals_scored = goals_info.get("away") or 0

            # Buscar stats granulares dos jogadores para esta partida
            try:
                teams_players_stats = await self.client.get_fixture_player_stats(fixture_id)
            except Exception as e:
                logger.warning(f"Falha ao buscar stats da partida {fixture_id}: {e}")
                continue

            for team_data in teams_players_stats:
                team_info = team_data.get("team", {})
                current_team_id = team_info.get("id")
                current_team_name = team_info.get("name")

                is_home = (current_team_id == home_team_id)
                opp_id = away_team_id if is_home else home_team_id
                opp_name = away_team_name if is_home else home_team_name

                # Calcular SG (clean sheet) e GS (gols sofridos)
                goals_suffered = away_goals_scored if is_home else home_goals_scored
                is_clean_sheet = (goals_suffered == 0)

                players_list = team_data.get("players", [])
                for p_data in players_list:
                    p_info = p_data.get("player", {})
                    p_id = p_info.get("id")
                    p_name = p_info.get("name")
                    p_photo = p_info.get("photo")

                    if not p_id or not p_name:
                        continue

                    # Primeiro bloco de statistics (a API sempre retorna uma lista com 1 item)
                    p_stats = p_data.get("statistics", [{}])[0]
                    games_data = p_stats.get("games", {})

                    minutes = games_data.get("minutes") or 0
                    if minutes == 0:
                        continue  # Não jogou

                    position_raw = games_data.get("position", "Midfielder")
                    # Normalizar posição: G -> Goalkeeper, D -> Defender, M -> Midfielder, F -> Attacker
                    POSITION_MAP = {"G": "Goalkeeper", "D": "Defender", "M": "Midfielder", "F": "Attacker"}
                    position = POSITION_MAP.get(position_raw, position_raw)

                    rating_str = games_data.get("rating")
                    rating = float(rating_str) if rating_str else None
                    was_sub = games_data.get("substitute", False)

                    # ===== Extrair TODOS os scouts da API =====
                    goals_data = p_stats.get("goals", {})
                    shots_data = p_stats.get("shots", {})
                    passes_data = p_stats.get("passes", {})
                    tackles_data = p_stats.get("tackles", {})
                    duels_data = p_stats.get("duels", {})
                    dribbles_data = p_stats.get("dribbles", {})
                    fouls_data = p_stats.get("fouls", {})
                    cards_data = p_stats.get("cards", {})
                    penalty_data = p_stats.get("penalty", {})
                    offsides_val = p_stats.get("offsides")

                    player_goals = goals_data.get("total") or 0
                    player_assists = goals_data.get("assists") or 0
                    player_saves = goals_data.get("saves") or 0
                    player_conceded = goals_data.get("conceded") or 0

                    shots_total = shots_data.get("total") or 0
                    shots_on = shots_data.get("on") or 0

                    # FD = finalizações no gol que não viraram gol
                    shots_on_target = max(0, shots_on - player_goals)
                    # FF = finalizações que não foram no gol
                    shots_off_target = max(0, shots_total - shots_on)

                    passes_total = passes_data.get("total") or 0
                    passes_key = passes_data.get("key") or 0
                    passes_acc_str = passes_data.get("accuracy")
                    passes_accuracy = int(passes_acc_str) if passes_acc_str else 0

                    tackles_total = tackles_data.get("total") or 0
                    blocks = tackles_data.get("blocks") or 0
                    interceptions = tackles_data.get("interceptions") or 0

                    duels_total = duels_data.get("total") or 0
                    duels_won = duels_data.get("won") or 0

                    dribbles_attempts = dribbles_data.get("attempts") or 0
                    dribbles_success = dribbles_data.get("success") or 0
                    dribbles_past = dribbles_data.get("past") or 0

                    fouls_drawn = fouls_data.get("drawn") or 0
                    fouls_committed = fouls_data.get("committed") or 0

                    yellow_cards = cards_data.get("yellow") or 0
                    red_cards = cards_data.get("red") or 0

                    pen_won = penalty_data.get("won") or 0
                    pen_committed = penalty_data.get("commited") or 0  # typo na API
                    pen_scored = penalty_data.get("scored") or 0
                    pen_missed = penalty_data.get("missed") or 0
                    pen_saved = penalty_data.get("saved") or 0

                    offsides_count = offsides_val or 0

                    # SG: clean sheet aplica-se a Goleiros e Defensores
                    apply_clean_sheet = is_clean_sheet and position in ("Goalkeeper", "Defender")
                    # GS: gols sofridos aplicam-se ao Goleiro
                    apply_goals_conceded = player_conceded if position == "Goalkeeper" else 0

                    # ===== Upsert Player =====
                    player = self.db.query(Player).filter(
                        Player.api_football_id == p_id
                    ).first()
                    if not player:
                        player = Player(
                            api_football_id=p_id,
                            name=p_name,
                            position=position,
                            team_id=current_team_id,
                            team_name=current_team_name,
                            photo_url=p_photo,
                        )
                        self.db.add(player)
                        self.db.flush()
                        synced_players += 1
                    else:
                        # Atualizar time e posição (jogador pode ter sido transferido)
                        player.team_id = current_team_id
                        player.team_name = current_team_name
                        player.position = position
                        if p_photo:
                            player.photo_url = p_photo

                    # ===== Criar PlayerMatchStats com TODOS os campos =====
                    match_stat = PlayerMatchStats(
                        player_id=player.id,
                        fixture_id=fixture_id,
                        round_name=round_name,
                        match_date=match_date,
                        is_home=is_home,
                        opponent_team_id=opp_id,
                        opponent_name=opp_name,
                        minutes_played=minutes,
                        rating=rating,
                        was_substitute=was_sub,
                        # Scouts de Ataque
                        goals=player_goals,
                        assists=player_assists,
                        shots_on_target=shots_on_target,
                        shots_off_target=shots_off_target,
                        shots_woodwork=0,  # API não fornece diretamente
                        fouls_drawn=fouls_drawn,
                        penalties_won=pen_won,
                        penalties_missed=pen_missed,
                        offsides=offsides_count,
                        # Scouts de Defesa
                        tackles=tackles_total,
                        clean_sheet=apply_clean_sheet,
                        saves=player_saves,
                        penalties_saved=pen_saved,
                        fouls_committed=fouls_committed,
                        yellow_cards=yellow_cards,
                        red_cards=red_cards,
                        goals_conceded=apply_goals_conceded,
                        penalties_committed=pen_committed,
                        own_goals=0,  # Requer cruzamento com eventos
                        # Dados extras para inteligência
                        passes_total=passes_total,
                        passes_key=passes_key,
                        passes_accuracy=passes_accuracy,
                        dribbles_attempts=dribbles_attempts,
                        dribbles_success=dribbles_success,
                        dribbles_past=dribbles_past,
                        duels_total=duels_total,
                        duels_won=duels_won,
                        blocks=blocks,
                        interceptions=interceptions,
                        shots_total=shots_total,
                    )
                    self.db.add(match_stat)
                    synced_stats += 1

        self.db.commit()

        # Calcular pontuação Cartola e Smart Score de todos os jogadores
        recalculated = self.scoring_engine.calculate_all_scores()

        return {
            "status": "success",
            "message": "Sincronização completa com api-sports.io.",
            "fixtures_found": len(fixtures),
            "fixtures_finished": len(finished),
            "fixtures_skipped": skipped_fixtures,
            "new_players": synced_players,
            "new_match_stats": synced_stats,
            "scores_calculated": recalculated,
        }

    async def sync_season(
        self,
        chunk_days: int = 30
    ) -> Dict[str, Any]:
        """
        Sincroniza a temporada inteira em blocos de chunk_days dias.
        Brasileirão geralmente vai de abril a dezembro.
        """
        season = self.client.season
        start = datetime(season, 4, 1)
        end = min(datetime(season, 12, 31), datetime.now())

        total_result = {
            "status": "success",
            "chunks_processed": 0,
            "total_new_players": 0,
            "total_new_match_stats": 0,
            "total_scores_calculated": 0,
        }

        current = start
        while current < end:
            chunk_end = min(current + timedelta(days=chunk_days), end)
            from_str = current.strftime("%Y-%m-%d")
            to_str = chunk_end.strftime("%Y-%m-%d")

            try:
                result = await self.sync_fixtures_by_range(from_str, to_str)
                total_result["chunks_processed"] += 1
                total_result["total_new_players"] += result.get("new_players", 0)
                total_result["total_new_match_stats"] += result.get("new_match_stats", 0)
                total_result["total_scores_calculated"] = result.get("scores_calculated", 0)
            except Exception as e:
                logger.error(f"Erro no chunk {from_str} a {to_str}: {e}")

            current = chunk_end + timedelta(days=1)

        return total_result
