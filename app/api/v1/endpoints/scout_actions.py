from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.scout_action import ScoutAction
from app.schemas.scout_action import ScoutActionResponse

router = APIRouter()

@router.get("/", response_model=List[ScoutActionResponse])
def get_scout_actions(db: Session = Depends(get_db)):
    """
    Retorna os dados mestre com as pontuações oficiais de cada scout do Cartola FC.
    """
    return db.query(ScoutAction).order_by(ScoutAction.category, ScoutAction.points.desc()).all()
