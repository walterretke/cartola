import httpx
import logging
from typing import Any, Dict, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ApiFootballClient:
    """
    Cliente assíncrono para comunicação com a API-Football v3 (api-sports.io).
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        league_id: Optional[int] = None,
        season: Optional[int] = None
    ):
        self.api_key = api_key or settings.API_FOOTBALL_KEY
        self.base_url = (base_url or settings.API_FOOTBALL_BASE_URL).rstrip("/")
        self.league_id = league_id or settings.BRASILEIRAO_LEAGUE_ID
        self.season = season or settings.BRASILEIRAO_SEASON
        
        self.headers = {
            "x-apisports-key": self.api_key,
            "User-Agent": "CartolaAI-Backend/1.0"
        }

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "sua_chave_api_football_aqui")

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"Erro na API (HTTP {response.status_code}): {response.text}")
                
            data = response.json()
            
            # API-Football retorna erros em 'errors' (pode ser dict ou lista)
            if "errors" in data and data["errors"]:
                # Se for dict (ex: {"access": "Your account is suspended..."})
                if isinstance(data["errors"], dict):
                    error_msgs = [f"{k}: {v}" for k, v in data["errors"].items()]
                    error_msg = ", ".join(error_msgs)
                else:
                    error_msg = str(data["errors"])
                raise Exception(f"Erro retornado pela API-Football: {error_msg}")
                
            return data.get("response", [])

    async def get_fixtures(
        self,
        from_date: str,
        to_date: str
    ) -> List[Dict[str, Any]]:
        """
        Retorna partidas do Brasileirão num intervalo de datas.
        """
        params = {
            "league": self.league_id,
            "season": self.season,
            "from": from_date,
            "to": to_date
        }
        return await self._get("fixtures", params=params)

    async def get_fixture_player_stats(self, fixture_id: int) -> List[Dict[str, Any]]:
        """
        Retorna as estatísticas (scouts) completas de todos os jogadores
        para uma partida específica. Fundamental para o motor do Cartola!
        """
        params = {
            "fixture": fixture_id
        }
        # A rota correta na API-Football para pegar os stats da partida é /fixtures/players
        return await self._get("fixtures/players", params=params)
