from sqlalchemy import Column, Integer, Float, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class PlayerSeasonHistory(Base):
    """
    Guarda o histórico consolidado de um jogador em uma temporada fechada.
    Usado como 'Priori Bayesiana' (Peso Histórico) no início da temporada seguinte.
    """
    __tablename__ = "cartola_player_season_history"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("cartola_players.id", ondelete="CASCADE"), nullable=False, index=True)
    season_year = Column(Integer, nullable=False) # Ex: 2024
    league_id = Column(Integer, default=71) # 71 = Serie A, 72 = Serie B
    league_difficulty_weight = Column(Float, default=1.0) # LDC (ex: 0.7 para Serie B)
    
    # Amostragem
    matches_played = Column(Integer, default=0)
    
    # Pontuação Geral
    avg_points = Column(Float, default=0.0)
    consistency_index = Column(Float, default=0.0)
    
    # Médias Vitais por Scout (para plugar no motor)
    avg_goals = Column(Float, default=0.0)
    avg_assists = Column(Float, default=0.0)
    avg_shots_on_target = Column(Float, default=0.0)
    avg_tackles = Column(Float, default=0.0)
    avg_saves = Column(Float, default=0.0)
    clean_sheet_pct = Column(Float, default=0.0)
    
    # Potenciais calculados do ano
    offensive_potential = Column(Float, default=0.0)
    defensive_potential = Column(Float, default=0.0)

    player = relationship("Player", back_populates="history_records")

    __table_args__ = (
        UniqueConstraint("player_id", "season_year", name="uix_player_season"),
    )
