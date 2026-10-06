from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.team_profile import TeamProfile
from app.schemas.fixture import TeamProfileResponse
from app.services.round_service import RoundService

router = APIRouter()


@router.get("/", response_model=List[TeamProfileResponse])
def list_team_profiles(db: Session = Depends(get_db)):
    """Perfil de ataque e defesa de todos os clubes, em ordem alfabética."""
    service = RoundService(db)
    teams = db.query(TeamProfile).order_by(TeamProfile.name.asc()).all()
    return [service.team_profile_dict(t) for t in teams]


@router.get("/{team_id}", response_model=TeamProfileResponse)
def get_team_profile(team_id: int, db: Session = Depends(get_db)):
    team = db.query(TeamProfile).filter(TeamProfile.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Clube não encontrado")
    return RoundService(db).team_profile_dict(team)
