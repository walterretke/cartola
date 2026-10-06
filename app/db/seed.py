from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.scout_action import ScoutAction
from app.models.player import Player
from app.core.cartola import normalize_position

LEGACY_POSITIONS = ("Goalkeeper", "Defender", "Midfielder", "Attacker")


def normalize_stored_positions(db) -> int:
    """Converte posições gravadas em inglês (API-Football) para o padrão do Cartola."""
    updated = 0
    for legacy in LEGACY_POSITIONS:
        updated += (
            db.query(Player)
            .filter(Player.position == legacy)
            .update({Player.position: normalize_position(legacy)}, synchronize_session=False)
        )
    return updated

# 20 Scouts Oficiais do Cartola FC (Dados Mestre)
CARTOLA_SCOUT_ACTIONS = [
    # --- ATAQUE ---
    {
        "code": "G",
        "name": "Gol",
        "category": "ATAQUE",
        "points": 8.0,
        "description": "Gol marcado pelo atleta",
        "is_goalkeeper_only": False,
    },
    {
        "code": "A",
        "name": "Assistência",
        "category": "ATAQUE",
        "points": 5.0,
        "description": "Passe que resulta diretamente em gol",
        "is_goalkeeper_only": False,
    },
    {
        "code": "FT",
        "name": "Finalização na trave",
        "category": "ATAQUE",
        "points": 3.0,
        "description": "Chute ou cabeceio que acerta a trave ou travessão",
        "is_goalkeeper_only": False,
    },
    {
        "code": "FD",
        "name": "Finalização defendida",
        "category": "ATAQUE",
        "points": 1.2,
        "description": "Chute no alvo defendido pelo goleiro ou zagueiro em cima da linha",
        "is_goalkeeper_only": False,
    },
    {
        "code": "PS",
        "name": "Pênalti sofrido",
        "category": "ATAQUE",
        "points": 1.0,
        "description": "Falta sofrida dentro da área resultando em pênalti",
        "is_goalkeeper_only": False,
    },
    {
        "code": "FF",
        "name": "Finalização pra fora",
        "category": "ATAQUE",
        "points": 0.8,
        "description": "Finalização em direção ao gol que vai para fora",
        "is_goalkeeper_only": False,
    },
    {
        "code": "FS",
        "name": "Falta sofrida",
        "category": "ATAQUE",
        "points": 0.5,
        "description": "Falta sofrida pelo jogador durante o jogo",
        "is_goalkeeper_only": False,
    },
    {
        "code": "I",
        "name": "Impedimento",
        "category": "ATAQUE",
        "points": -0.1,
        "description": "Flagrado em posição de impedimento",
        "is_goalkeeper_only": False,
    },
    {
        "code": "PP",
        "name": "Pênalti perdido",
        "category": "ATAQUE",
        "points": -4.0,
        "description": "Cobrança de pênalti desperdiçada (fora, trave ou defendida)",
        "is_goalkeeper_only": False,
    },
    
    # --- DEFESA ---
    {
        "code": "DP",
        "name": "Defesa de pênalti",
        "category": "DEFESA",
        "points": 7.0,
        "description": "Pênalti defendido pelo goleiro",
        "is_goalkeeper_only": True,
    },
    {
        "code": "SG",
        "name": "Jogo sem sofrer gols",
        "category": "DEFESA",
        "points": 5.0,
        "description": "Manter a baliza invicta (exclusivo goleiros, zagueiros e laterais)",
        "is_goalkeeper_only": False,
    },
    {
        "code": "DS",
        "name": "Desarme",
        "category": "DEFESA",
        "points": 1.5,
        "description": "Recuperação ou desarme limpo de posse de bola",
        "is_goalkeeper_only": False,
    },
    {
        "code": "DE",
        "name": "Defesa",
        "category": "DEFESA",
        "points": 1.3,
        "description": "Defesa realizada pelo goleiro",
        "is_goalkeeper_only": True,
    },
    {
        "code": "FC",
        "name": "Falta cometida",
        "category": "DEFESA",
        "points": -0.3,
        "description": "Falta cometida contra o adversário",
        "is_goalkeeper_only": False,
    },
    {
        "code": "CA",
        "name": "Cartão amarelo",
        "category": "DEFESA",
        "points": -1.0,
        "description": "Recebimento de advertência com cartão amarelo",
        "is_goalkeeper_only": False,
    },
    {
        "code": "GS",
        "name": "Gol sofrido",
        "category": "DEFESA",
        "points": -1.0,
        "description": "Gol sofrido pelo goleiro em campo",
        "is_goalkeeper_only": True,
    },
    {
        "code": "PC",
        "name": "Pênalti cometido",
        "category": "DEFESA",
        "points": -1.0,
        "description": "Falta cometida dentro da área que resulta em pênalti",
        "is_goalkeeper_only": False,
    },
    {
        "code": "CV",
        "name": "Cartão vermelho",
        "category": "DEFESA",
        "points": -3.0,
        "description": "Expulsão direta ou por segundo amarelo",
        "is_goalkeeper_only": False,
    },
    {
        "code": "GC",
        "name": "Gol contra",
        "category": "DEFESA",
        "points": -3.0,
        "description": "Gol marcado contra as próprias redes",
        "is_goalkeeper_only": False,
    },

    # --- TÉCNICO ---
    {
        "code": "V",
        "name": "Vitória",
        "category": "TECNICO",
        "points": 1.0,
        "description": "Vitória da equipe no jogo (scout exclusivo do técnico)",
        "is_goalkeeper_only": False,
    }
]

def init_db():
    print("Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Semeando dados mestre de pontuação do Cartola...")
        count_created = 0
        count_updated = 0
        
        for item in CARTOLA_SCOUT_ACTIONS:
            action = db.query(ScoutAction).filter(ScoutAction.code == item["code"]).first()
            if not action:
                action = ScoutAction(**item)
                db.add(action)
                count_created += 1
            else:
                action.name = item["name"]
                action.category = item["category"]
                action.points = item["points"]
                action.description = item["description"]
                action.is_goalkeeper_only = item["is_goalkeeper_only"]
                count_updated += 1
        
        normalized = normalize_stored_positions(db)
        if normalized:
            print(f"Posições normalizadas para o padrão do Cartola: {normalized} jogadores.")

        db.commit()
        print(f"Sucesso: {count_created} scouts criados, {count_updated} atualizados. Total: {len(CARTOLA_SCOUT_ACTIONS)} scouts cadastrados.")
    except Exception as e:
        db.rollback()
        print(f"Erro ao semear dados: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
