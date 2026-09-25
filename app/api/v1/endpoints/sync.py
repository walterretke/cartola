from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.sync_service import SyncService
from app.services.scoring_engine import ScoringEngine

router = APIRouter()


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
