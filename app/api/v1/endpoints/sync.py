from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.sync_service import SyncService
from app.services.scoring_engine import ScoringEngine
from app.services.round_service import RoundService
from app.schemas.fixture import SystemStatusResponse

router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse)
def sync_status(db: Session = Depends(get_db)):
    """Contagem dos dados no banco e horário do último recálculo das notas."""
    return RoundService(db).system_status()


@router.post("/run")
async def run_sync(
    from_date: str = Query(None, description="Data inicial (YYYY-MM-DD). Se vazio, usa últimos 7 dias."),
    to_date: str = Query(None, description="Data final (YYYY-MM-DD). Se vazio, usa hoje."),
    db: Session = Depends(get_db),
):
    """
    Sincroniza partidas do Brasileirão num intervalo de datas.
    Busca todos os scouts granulares e dados extras de cada jogador.
    """
    from datetime import datetime, timedelta

    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    sync_service = SyncService(db=db)
    result = await sync_service.sync_fixtures_by_range(from_date, to_date)
    return result


@router.post("/sync-season")
async def sync_season(db: Session = Depends(get_db)):
    """
    Sincroniza a temporada inteira do Brasileirão (de abril até hoje).
    Processa em blocos de 30 dias para respeitar limites da API.
    CUIDADO: Consome muitas requisições! Use com moderação no plano Free.
    """
    sync_service = SyncService(db=db)
    result = await sync_service.sync_season()
    return result


@router.post("/recalculate-scores")
def recalculate_scores(db: Session = Depends(get_db)):
    """
    Recalcula o Smart Score de todos os jogadores no banco.
    """
    scoring_engine = ScoringEngine(db=db)
    count = scoring_engine.calculate_all_scores()
    return {
        "status": "success",
        "message": f"Scores recalculados para {count} jogadores.",
    }

@router.post("/cartola-status")
async def sync_cartola_status(db: Session = Depends(get_db)):
    """
    Bate na API oficial do Cartola para sincronizar status (Provável, Dúvida, etc).
    """
    sync_service = SyncService(db=db)
    result = await sync_service.sync_cartola_status()
    return result

@router.post("/match-cartola-ids")
def match_cartola_ids(db: Session = Depends(get_db)):
    """
    Roda o vínculo por similaridade de nomes ('Fuzzy String Matching') para mapear os 
    IDs do Cartola FC com os IDs dos jogadores já existentes da API-Football.
    """
    from app.services.player_matcher_service import PlayerMatcherService
    matcher = PlayerMatcherService(db)
    result = matcher.run_matching_pipeline()
    return result
