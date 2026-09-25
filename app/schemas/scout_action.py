from typing import Optional
from pydantic import BaseModel, ConfigDict

class ScoutActionResponse(BaseModel):
    id: int
    code: str
    name: str
    category: str
    points: float
    description: Optional[str] = None
    is_goalkeeper_only: bool

    model_config = ConfigDict(from_attributes=True)
