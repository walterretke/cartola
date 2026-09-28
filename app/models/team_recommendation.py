from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base_class import Base

class TeamRecommendation(Base):
    """
    Registra os times recomendados pelo CartolaAI em uma determinada rodada,
    categorizados por estratégia (Principal, Alternativo, Valorização, Aposta).
    """
    __tablename__ = "cartola_team_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    season_year = Column(Integer, nullable=False, index=True)
    round_number = Column(Integer, nullable=False, index=True)
    
    # PRINCIPAL, ALTERNATIVO, VALORIZACAO, APOSTA
    strategy = Column(String(50), nullable=False, index=True)
    
    # Ex: "4-3-3"
    formation = Column(String(20), nullable=False, default="4-3-3")
    
    expected_total_score = Column(Float, default=0.0)
    expected_total_cost = Column(Float, default=0.0)
    
    # JSON contendo as informações completas dos titulares, reservas e capitão
    squad_data = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
