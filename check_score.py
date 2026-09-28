from app.db.session import SessionLocal
from app.models.fixture import Fixture
from app.models.player_match_stats import PlayerMatchStats

db = SessionLocal()

starters = [
    {'id': 291, 'pos': 'Goalkeeper', 'is_captain': True},
    {'id': 254, 'pos': 'Defender'},
    {'id': 321, 'pos': 'Defender'},
    {'id': 130, 'pos': 'Defender'},
    {'id': 193, 'pos': 'Defender'},
    {'id': 69, 'pos': 'Midfielder'},
    {'id': 243, 'pos': 'Midfielder'},
    {'id': 14, 'pos': 'Midfielder'},
    {'id': 199, 'pos': 'Attacker'},
    {'id': 88, 'pos': 'Attacker'},
    {'id': 57, 'pos': 'Attacker'},
]

reserves = {
    'Goalkeeper': [17],
    'Defender': [191, 128],
    'Midfielder': [37],
    'Attacker': [10]
}

round_name = 'Regular Season - 4'
final_score = 0.0
players_log = []

for s in starters:
    stat = db.query(PlayerMatchStats).join(Fixture, Fixture.id == PlayerMatchStats.fixture_id).filter(
        PlayerMatchStats.player_id == s['id'],
        Fixture.round_name == round_name
    ).first()
    
    if stat and stat.minutes_played > 0:
        pts = stat.match_cartola_score
        if s.get('is_captain'): pts *= 1.5
        final_score += pts
        cap_str = f" (CAPITAO -> {pts:.2f})" if s.get('is_captain') else ""
        players_log.append(f"Titular ID {s['id']} jogou e fez {stat.match_cartola_score:.2f} pts{cap_str}")
    else:
        subs = reserves[s['pos']]
        if subs:
            sub_id = subs.pop(0)
            sub_stat = db.query(PlayerMatchStats).join(Fixture, Fixture.id == PlayerMatchStats.fixture_id).filter(
                PlayerMatchStats.player_id == sub_id,
                Fixture.round_name == round_name
            ).first()
            if sub_stat and sub_stat.minutes_played > 0:
                pts = sub_stat.match_cartola_score
                if s.get('is_captain'): pts *= 1.5
                final_score += pts
                cap_str = f" (CAPITAO -> {pts:.2f})" if s.get('is_captain') else ""
                players_log.append(f"Subst ({s['pos']}): Entrou Reserva ID {sub_id} e fez {sub_stat.match_cartola_score:.2f} pts{cap_str}")
            else:
                players_log.append(f"Subst falhou ({s['pos']}): Reserva {sub_id} tb nao jogou. 0 pts.")
        else:
            players_log.append(f"Titular {s['id']} nao jogou e s/ reserva de {s['pos']}. 0 pts.")

print("--- RESULTADOS REAIS NA RODADA 4 ---")
for log in players_log: print(log)
print(f"\nPONTUACAO TOTAL DO TIME: {final_score:.2f} pontos")
