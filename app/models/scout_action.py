from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class ScoutAction(Base):
    """
    Dados mestre de pontuação do Cartola FC.
    Cada registro define um tipo de ação e quantos pontos ela vale no jogo.
    """
    __tablename__ = "cartola_scout_actions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False) # Ex: G, A, DS, SG, DE, DP, etc.
    name = Column(String(100), nullable=False)                         # Ex: "Gol", "Assistência", "Desarme"
    category = Column(String(50), nullable=False)                     # "ATAQUE", "DEFESA", "TECNICO"
    points = Column(Float, nullable=False)                            # Ex: 8.0, 5.0, 1.5, -0.3
    description = Column(String(255), nullable=True)
    is_goalkeeper_only = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
