from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.fixture import CurrentRoundResponse, RoundSummary
from app.services.round_service import RoundService

router = APIRouter()


@router.get("/", response_model=List[RoundSummary])
def list_rounds(db: Session = Depends(get_db)):
    """Todas as rodadas com jogos cadastrados, com contagem de jogos encerrados."""
    return RoundService(db).list_rounds()


@router.get("/current", response_model=CurrentRoundResponse)
def get_current_round(db: Session = Depends(get_db)):
    """
    Rodada atual (a primeira que ainda não terminou), status do mercado,
    horário de fechamento e os jogos da rodada.
    """
    return RoundService(db).current_round()
