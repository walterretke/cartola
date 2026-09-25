from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class PlayerScore(Base):
    """
    Score inteligente consolidado do jogador.
    Avalia média geral, desempenho casa/fora, oscilação,
    momentum, médias por scout individual, e indicadores avançados.
    """
    __tablename__ = "cartola_player_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("cartola_players.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # ========== AMOSTRAGEM ==========
    matches_played = Column(Integer, default=0)
    home_matches = Column(Integer, default=0)
    away_matches = Column(Integer, default=0)
    total_minutes = Column(Integer, default=0)
    
    # ========== MÉDIAS DE PONTUAÇÃO CARTOLA ==========
    total_points = Column(Float, default=0.0)
    avg_points = Column(Float, default=0.0)
    avg_points_home = Column(Float, default=0.0)
    avg_points_away = Column(Float, default=0.0)
    
    # ========== OSCILAÇÃO E REGULARIDADE ==========
    std_deviation = Column(Float, default=0.0)
    consistency_index = Column(Float, default=0.0)      # 0 a 100
    min_score = Column(Float, default=0.0)
    max_score = Column(Float, default=0.0)
    
    # ========== MOMENTUM ==========
    last_3_avg = Column(Float, default=0.0)
    last_5_avg = Column(Float, default=0.0)
    ema_points = Column(Float, default=0.0)             # Média Móvel Exponencial (EMA)
    trend = Column(String(20), default="stable")        # rising, falling, stable
    
    # ========== MÉDIAS POR SCOUT (por jogo) ==========
    avg_goals = Column(Float, default=0.0)
    avg_assists = Column(Float, default=0.0)
    avg_shots_on_target = Column(Float, default=0.0)    # FD
    avg_shots_off_target = Column(Float, default=0.0)   # FF
    avg_fouls_drawn = Column(Float, default=0.0)        # FS
    avg_tackles = Column(Float, default=0.0)            # DS
    avg_saves = Column(Float, default=0.0)              # DE (goleiros)
    avg_fouls_committed = Column(Float, default=0.0)    # FC
    avg_yellow_cards = Column(Float, default=0.0)       # CA
    avg_goals_conceded = Column(Float, default=0.0)     # GS
    clean_sheet_pct = Column(Float, default=0.0)        # % de jogos com SG
    
    # ========== INDICADORES AVANÇADOS (dados extras da API) ==========
    avg_rating = Column(Float, default=0.0)             # Nota média Sofascore
    avg_passes_key = Column(Float, default=0.0)         # Passes decisivos/jogo
    avg_dribbles_success = Column(Float, default=0.0)   # Dribles certos/jogo
    avg_duels_won = Column(Float, default=0.0)          # Duelos ganhos/jogo
    avg_interceptions = Column(Float, default=0.0)      # Interceptações/jogo
    duel_win_pct = Column(Float, default=0.0)           # % de duelos ganhos
    pass_accuracy_avg = Column(Float, default=0.0)      # % média de passes certos
    
    # ========== PROJEÇÃO E POTENCIAL ==========
    # Potencial ofensivo: média ponderada dos scouts de ataque por jogo
    offensive_potential = Column(Float, default=0.0)
    # Potencial defensivo: média ponderada dos scouts de defesa por jogo
    defensive_potential = Column(Float, default=0.0)
    # Risco disciplinar: média de cartões + faltas por jogo (quanto maior, pior)
    discipline_risk = Column(Float, default=0.0)
    
    # ========== SCORE INTELIGENTE FINAL ==========
    smart_score = Column(Float, default=0.0, index=True)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    player = relationship("Player", back_populates="score")
