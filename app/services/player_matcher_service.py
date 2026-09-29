import json
import requests
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from thefuzz import fuzz

from app.models.player import Player
from app.models.team_profile import TeamProfile

class PlayerMatcherService:
    def __init__(self, db: Session):
        self.db = db
        # Mapeamento manual dos 20 times da SǸrie A (Cartola ID -> API-Football ID)
        # Obs: VocǦ deve atualizar esse de-para anualmente com os clubes corretos
        self.team_mapping = {
            262: 127,  # Flamengo
            275: 121,  # Palmeiras
            264: 131,  # Corinthians
            277: 128,  # Santos (Se na Serie A)
            276: 126,  # So Paulo
            266: 124,  # Fluminense
            282: 106,  # Atletico Mineiro
            265: 147,  # Bahia
            284: 130,  # Gremio
            285: 119,  # Internacional
            263: 120,  # Botafogo
            293: 134,  # Athletico PR
            # ... adicione os demais ...
        }

    def fetch_cartola_players(self):
        """Busca o mercado oficial do Cartola"""
        url = "https://api.cartola.globo.com/atletas/mercado"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("atletas", [])
        return []

    def run_matching_pipeline(self) -> Dict[str, Any]:
        """
        Rotina principal que busca os dados do Cartola e vincula (De-Para)
        com os jogadores da base atual que vieram da API-Football.
        """
        cartola_players = self.fetch_cartola_players()
        if not cartola_players:
            return {"status": "error", "message": "No foi possvel buscar o mercado do Cartola"}

        matched_count = 0
        unmatched = []

        all_db_players = self.db.query(Player).all()
        # Para todos os jogadores listados no Cartola
        for c_player in cartola_players:
            cartola_id = c_player.get("atleta_id")
            c_team_id = c_player.get("clube_id")
            c_nickname = c_player.get("apelido", "").strip()
            c_fullname = c_player.get("nome", "").strip()

            api_team_id = self.team_mapping.get(c_team_id)
            
            # Se no temos o time mapeado, pula
            if not api_team_id:
                continue

            # Substituido: Busca todos os jogadores globalmente no inicio
            pass
            # a query global
            
            best_match = None
            best_score = 0

            # 1. Tenta achar se o jogador ja foi vinculado antes (mesmo que tenha mudado de time)
            for db_p in all_db_players:
                if db_p.cartola_id == cartola_id:
                    best_match = db_p
                    best_score = 100
                    break
            
            # 2. Se nao achou pelo ID, tenta pelo nome MAS SO ENTRE JOGADORES DO MESMO TIME
            if not best_match:
                db_players = [p for p in all_db_players if p.team_id == api_team_id]
                for db_p in db_players:
                    score1 = fuzz.token_set_ratio(c_nickname.lower(), db_p.name.lower())
                    score2 = fuzz.token_set_ratio(c_fullname.lower(), db_p.name.lower())
                    api_full = f"{db_p.firstname or ''} {db_p.lastname or ''}".strip().lower()
                    score3 = fuzz.token_set_ratio(c_fullname.lower(), api_full) if api_full else 0
                    max_score = max(score1, score2, score3)
                    if max_score > best_score:
                        best_score = max_score
                        best_match = db_p
            # Se encontrou alguǸm com boa similaridade
            if best_match and best_score >= 80:
                # Vincula!
                posicoes_map = {1: "Goleiro", 2: "Lateral", 3: "Zagueiro", 4: "Meia", 5: "Atacante", 6: "Tecnico"}
                best_match.cartola_id = cartola_id
                # Aproveitamos para atualizar o preo e o status!
                best_match.price_cartoletas = c_player.get("preco_num", 0.0)
                best_match.cartola_status_id = c_player.get("status_id", 6)
                pos_id = c_player.get("posicao_id")
                if pos_id in posicoes_map:
                    best_match.position = posicoes_map[pos_id]
                matched_count += 1
            else:
                unmatched.append({
                    "cartola_id": cartola_id,
                    "nickname": c_nickname,
                    "fullname": c_fullname,
                    "team_id": c_team_id
                })

        self.db.commit()

        return {
            "status": "success",
            "matched_count": matched_count,
            "unmatched_count": len(unmatched),
            "unmatched_samples": unmatched[:10]  # Retorna alguns rfos para vocǦ analisar
        }
