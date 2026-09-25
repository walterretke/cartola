from app.db.session import SessionLocal
from app.models.player import Player
from app.models.fixture import Fixture
from app.models.player_match_stats import PlayerMatchStats
from app.services.recommendation_engine import RecommendationEngine

def simulate_round():
    db = SessionLocal()

    # Rodada 4 ocorreu por volta do dia 27 e 28 de Abril de 2024
    fixtures = db.query(Fixture).filter(Fixture.match_date >= '2024-04-27', Fixture.match_date <= '2024-04-29', Fixture.status == 'FT').all()

    print(f'Simulando a Rodada 4 (Avaliando {len(fixtures)} partidas e todos os seus jogadores)')

    engine = RecommendationEngine(db)

    all_recs = []
    for f in fixtures:
        recs = engine.get_recommendations_for_fixture(f.id, limit=80) 
        for r in recs:
            # Filtro ABSOLUTO do Novo Motor: Só escala se for "Provável" (status 7)
            # Obs: Como estamos usando status de HOJE para jogo de ABRIL, alguns times podem sumir
            player_obj = db.query(Player).filter(Player.id == r['player']['id']).first()
            if not player_obj or player_obj.cartola_status_id != 7:
                continue

            # Pega a pontuacao real
            stat = db.query(PlayerMatchStats).filter(PlayerMatchStats.player_id == r['player']['id'], PlayerMatchStats.fixture_id == f.id).first()
            r['real_score'] = stat.match_cartola_score if stat else 0.0
            all_recs.append(r)

    # Ordenar por ESC (Expected Score Contextual)
    all_recs.sort(key=lambda x: x['expected_score_contextual'], reverse=True)

    # Montar o time ideal (4-3-3 clássico)
    team = {'Goalkeeper': [], 'Defender': [], 'Midfielder': [], 'Attacker': []}
    limits = {'Goalkeeper': 1, 'Defender': 4, 'Midfielder': 3, 'Attacker': 3}

    final_team = []
    for r in all_recs:
        pos = r['player']['position']
        if len(team[pos]) < limits[pos]:
            team[pos].append(r)
            final_team.append(r)
        
        if len(final_team) == 11:
            break

    print('-'*85)
    print(f'{"JOGADOR":<20} | {"TIME":<15} | {"POSIÇÃO":<10} | {"PREV (ESC)":<10} | {"REAL":<10}')
    print('-'*85)

    tot_esc = 0
    tot_real = 0

    order = ['Goalkeeper', 'Defender', 'Midfielder', 'Attacker']
    for pos in order:
        for r in team[pos]:
            tot_esc += r['expected_score_contextual']
            tot_real += r['real_score']
            print(f"{r['player']['name'][:19]:<20} | {r['player']['team_name'][:14]:<15} | {pos[:10]:<10} | {r['expected_score_contextual']:<10.2f} | {r['real_score']:<10.2f}")

    print('-'*85)
    print(f'{"TOTAL DA SELEÇÃO ALGORÍTMICA":<50} | {tot_esc:<10.2f} | {tot_real:<10.2f}')

if __name__ == "__main__":
    simulate_round()
