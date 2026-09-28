import asyncio
import logging
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.services.sync_service import SyncService
from app.services.player_matcher_service import PlayerMatcherService
from app.models import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("=========================================")
    logger.info("INICIANDO SYNC INTELIGENTE DAS RODADAS FALTANTES")
    logger.info("=========================================")

    # NAO apagamos o banco. Vamos aproveitar os dados existentes!
    db = SessionLocal()
    sync_service = SyncService(db=db)
    
    original_get = sync_service.client._get
    async def rate_limited_get(endpoint, params=None):
        await asyncio.sleep(0.25)
        return await original_get(endpoint, params)
    sync_service.client._get = rate_limited_get

    logger.info("Buscando jogos faltantes de 2026...")
    try:
        # A propria funcao ja pula as partidas que tem estatisticas gravadas!
        result = await sync_service.sync_fixtures_by_range(
            from_date="2026-01-01", 
            to_date="2026-12-31"
        )
        logger.info(f"Sync Inteligente Finalizado! Resultados: {result}")
    except Exception as e:
        logger.error(f"Erro durante o sync: {e}")

    logger.info("Iniciando De-Para dos jogadores novos...")
    matcher = PlayerMatcherService(db)
    match_result = matcher.run_matching_pipeline()
    logger.info(f"Matcher Finalizado! {match_result}")
    
    logger.info("Banco de Dados 2026 totalmente sincronizado sem duplicidade!")

if __name__ == "__main__":
    asyncio.run(main())
