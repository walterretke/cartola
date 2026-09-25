from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Player(Base):
    """
    Jogador de futebol cadastrado a partir da API.
    """
    __tablename__ = "cartola_players"

    id = Column(Integer, primary_key=True, index=True)
    api_football_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False, index=True)
    firstname = Column(String(100), nullable=True)
    lastname = Column(String(100), nullable=True)
    position = Column(String(50), nullable=False, index=True) # Goalkeeper, Defender, Midfielder, Attacker
    team_id = Column(Integer, nullable=True, index=True)
    team_name = Column(String(150), nullable=True, index=True)
    photo_url = Column(String(255), nullable=True)
    age = Column(Integer, nullable=True)
    nationality = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    match_stats = relationship("PlayerMatchStats", back_populates="player", cascade="all, delete-orphan")
    score = relationship("PlayerScore", back_populates="player", uselist=False, cascade="all, delete-orphan")
