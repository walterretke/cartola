from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class PlayerMatchStats(Base):
    """
    Estatísticas COMPLETAS do jogador em uma partida específica.
    Mapeia todos os scouts do Cartola FC + dados extras da API para inteligência avançada.
    """
    __tablename__ = "cartola_player_match_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("cartola_players.id", ondelete="CASCADE"), nullable=False, index=True)
    fixture_id = Column(Integer, nullable=False, index=True)
    round_name = Column(String(100), nullable=True)
    match_date = Column(DateTime, nullable=True)
    
    # Contexto de Mando de Campo
    is_home = Column(Boolean, nullable=False, default=True)
    opponent_team_id = Column(Integer, nullable=True)
    opponent_name = Column(String(150), nullable=True)
    
    # Participação
    minutes_played = Column(Integer, default=0)
    rating = Column(Float, nullable=True)           # Nota Sofascore/API (0.0 a 10.0)
    was_substitute = Column(Boolean, default=False) # Entrou do banco?
    
    # ========== SCOUTS DE ATAQUE (mapeiam direto para pontuação Cartola) ==========
    goals = Column(Integer, default=0)              # G  (+8.0)
    assists = Column(Integer, default=0)            # A  (+5.0)
    shots_on_target = Column(Integer, default=0)    # FD (+1.2) - shots.on - goals.total
    shots_off_target = Column(Integer, default=0)   # FF (+0.8) - shots.total - shots.on
    shots_woodwork = Column(Integer, default=0)     # FT (+3.0) - não disponível direto na API
    fouls_drawn = Column(Integer, default=0)        # FS (+0.5)
    penalties_won = Column(Integer, default=0)      # PS (+1.0)
    penalties_missed = Column(Integer, default=0)   # PP (-4.0)
    offsides = Column(Integer, default=0)           # I  (-0.1)
    
    # ========== SCOUTS DE DEFESA (mapeiam direto para pontuação Cartola) ==========
    tackles = Column(Integer, default=0)            # DS (+1.5)
    clean_sheet = Column(Boolean, default=False)    # SG (+5.0)
    saves = Column(Integer, default=0)              # DE (+1.3) - exclusivo goleiro
    penalties_saved = Column(Integer, default=0)    # DP (+7.0) - exclusivo goleiro
    fouls_committed = Column(Integer, default=0)    # FC (-0.3)
    yellow_cards = Column(Integer, default=0)       # CA (-1.0)
    red_cards = Column(Integer, default=0)          # CV (-3.0)
    goals_conceded = Column(Integer, default=0)     # GS (-1.0)
    penalties_committed = Column(Integer, default=0)# PC (-1.0)
    own_goals = Column(Integer, default=0)          # GC (-3.0)
    
    # ========== DADOS EXTRAS DA API (inteligência avançada, não são scouts Cartola) ==========
    # Passes
    passes_total = Column(Integer, default=0)
    passes_key = Column(Integer, default=0)         # Passes decisivos (quase-assistência)
    passes_accuracy = Column(Integer, default=0)    # % de acerto de passes
    
    # Dribles
    dribbles_attempts = Column(Integer, default=0)
    dribbles_success = Column(Integer, default=0)
    dribbles_past = Column(Integer, default=0)      # Quantas vezes foi driblado
    
    # Duelos
    duels_total = Column(Integer, default=0)
    duels_won = Column(Integer, default=0)
    
    # Bloqueios e Interceptações
    blocks = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    
    # Finalizações totais (para cálculos derivados)
    shots_total = Column(Integer, default=0)
    
    # ========== PONTUAÇÃO CALCULADA ==========
    match_cartola_score = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    player = relationship("Player", back_populates="match_stats")

    __table_args__ = (
        Index("ix_player_fixture", "player_id", "fixture_id", unique=True),
    )
