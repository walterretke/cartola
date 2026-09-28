import asyncio
import logging
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.db.base_class import Base
from app.services.sync_service import SyncService
from app.services.player_matcher_service import PlayerMatcherService
from app.models import *  # Ensure all models are loaded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("=========================================")
    logger.info("INICIANDO RESET TOTAL E SINCRONIZACAO 2026")
    logger.info("=========================================")

    # 1. Dropar e recriar o banco de dados
    logger.info("Limpando banco de dados...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Recriando tabelas...")
    Base.metadata.create_all(bind=engine)

    # 2. Inicializar Master Data (Scouts)
    # Aqui voce pode importar sua funcao init_db() se quiser
    from app.db.seed import seed_scouts
    db = SessionLocal()
    seed_scouts(db)
    
    # 3. Executar o SyncService para o periodo desejado
    sync_service = SyncService(db=db)
    
    # Monkey-patch temporario no cliente da API para garantir o limite de burst se o SyncService nao tiver
    original_get = sync_service.client._get
    async def rate_limited_get(endpoint, params=None):
        await asyncio.sleep(0.25) # Garante que nao ultrapasse 4 req/sec
        return await original_get(endpoint, params)
    sync_service.client._get = rate_limited_get

    logger.info("Iniciando download dos jogos do Brasileirao 2026...")
    # Vamos colocar de Abril de 2026 ate hoje
    try:
        # ATENCAO: Ajuste a data final para a data atual da sua execucao
        result = await sync_service.sync_fixtures_by_range(
            from_date="2026-04-10", 
            to_date="2026-10-01"
        )
        logger.info(f"Sync Finalizado! Resultados: {result}")
    except Exception as e:
        logger.error(f"Erro durante o sync das partidas: {e}")

    # 4. Rodar o Algoritmo de Matcher para buscar os IDs do Cartola
    logger.info("Iniciando De-Para dos jogadores com o Cartola Oficial...")
    matcher = PlayerMatcherService(db)
    match_result = matcher.run_matching_pipeline()
    logger.info(f"Matcher Finalizado! {match_result}")
    
    logger.info("Banco de Dados 2026 pronto para uso!")

if __name__ == "__main__":
    asyncio.run(main())
