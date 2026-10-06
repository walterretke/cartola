from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.fixture import Fixture
from app.schemas.fixture import FixtureDetailResponse, FixtureResponse
from app.services.round_service import RoundService

router = APIRouter()


@router.get("/", response_model=List[FixtureResponse])
def list_fixtures(
    round: Optional[int] = Query(None, ge=1, le=38, description="Número da rodada. Se vazio, usa a rodada atual."),
    db: Session = Depends(get_db),
):
    """Jogos de uma rodada, com a chance de cada time não sofrer gol."""
    service = RoundService(db)
    round_number = round or service.current_round_number()
    if round_number is None:
        return []
    return [service.fixture_dict(f) for f in service.fixtures_of_round(round_number)]


@router.get("/{fixture_id}", response_model=FixtureDetailResponse)
def get_fixture(fixture_id: int, db: Session = Depends(get_db)):
    """Um jogo com o perfil de ataque e defesa dos dois times."""
    fixture = db.query(Fixture).filter(Fixture.id == fixture_id).first()
    if not fixture:
        raise HTTPException(status_code=404, detail="Partida não encontrada")
    return RoundService(db).fixture_dict(fixture, detail=True)
