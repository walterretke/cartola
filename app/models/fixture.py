from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Fixture(Base):
    """
    Partidas do campeonato. Necessário para saber os confrontos 
    futuros e calcular as recomendações contextuais.
    """
    __tablename__ = "cartola_fixtures"

    id = Column(Integer, primary_key=True, index=True) # ID da API-Football
    round_name = Column(String(100), nullable=True, index=True)
    match_date = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), nullable=False) # Ex: "FT", "NS" (Not Started)
    
    home_team_id = Column(Integer, ForeignKey("cartola_team_profiles.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("cartola_team_profiles.id"), nullable=False)
    
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    home_team = relationship("TeamProfile", foreign_keys=[home_team_id])
    away_team = relationship("TeamProfile", foreign_keys=[away_team_id])
