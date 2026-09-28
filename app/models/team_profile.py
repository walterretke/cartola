from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class TeamProfile(Base):
    """
    Perfil do Time: usado para calcular a força do adversário
    e as probabilidades de Saldo de Gols (SG) e Gols Marcados.
    """
    __tablename__ = "cartola_team_profiles"

    id = Column(Integer, primary_key=True, index=True) # ID da API-Football
    cartola_id = Column(Integer, unique=True, index=True, nullable=True)
    name = Column(String(150), nullable=False, index=True)
    
    # Amostragem
    matches_played = Column(Integer, default=0)
    home_matches = Column(Integer, default=0)
    away_matches = Column(Integer, default=0)
    
    # Ataque
    goals_scored = Column(Integer, default=0)
    goals_scored_home = Column(Integer, default=0)
    goals_scored_away = Column(Integer, default=0)
    
    avg_goals_scored = Column(Float, default=0.0)
    avg_goals_scored_home = Column(Float, default=0.0)
    avg_goals_scored_away = Column(Float, default=0.0)
    
    # Defesa
    goals_conceded = Column(Integer, default=0)
    goals_conceded_home = Column(Integer, default=0)
    goals_conceded_away = Column(Integer, default=0)
    
    avg_goals_conceded = Column(Float, default=0.0)
    avg_goals_conceded_home = Column(Float, default=0.0)
    avg_goals_conceded_away = Column(Float, default=0.0)
    
    # Clean Sheets (SG)
    clean_sheets = Column(Integer, default=0)
    clean_sheet_rate = Column(Float, default=0.0) # % de jogos sem sofrer gols
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
