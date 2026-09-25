from app.db.session import SessionLocal
from app.models.player import Player
from app.models.fixture import Fixture
from app.models.player_match_stats import PlayerMatchStats
from app.services.recommendation_engine import RecommendationEngine
from collections import defaultdict

def simulate_full_cartola_rules():
    db = SessionLocal()

    fixtures = db.query(Fixture).filter(
        Fixture.match_date >= '2024-04-27', 
        Fixture.match_date <= '2024-04-29', 
        Fixture.status == 'FT'
    ).all()

    engine = RecommendationEngine(db)

    # 1. Obter previsões (ESC) e Notas Reais para todos os jogadores da rodada
    all_recs = []
    for f in fixtures:
        recs = engine.get_recommendations_for_fixture(f.id, limit=60)
        for r in recs:
            stat = db.query(PlayerMatchStats).filter(
                PlayerMatchStats.player_id == r['player']['id'], 
                PlayerMatchStats.fixture_id == f.id
            ).first()
            
            p_obj = db.query(Player).filter(Player.id == r['player']['id']).first()
            r['player_obj'] = p_obj
            
            r['real_score'] = stat.match_cartola_score if stat else 0.0
            r['minutes_played'] = stat.minutes_played if stat else 0
            all_recs.append(r)

    # Ordenar por ESC decrescente
    all_recs.sort(key=lambda x: x['expected_score_contextual'], reverse=True)

    # 2. Separar por posição
    players_by_pos = {'Goalkeeper': [], 'Defender': [], 'Midfielder': [], 'Attacker': []}
    for r in all_recs:
        players_by_pos[r['player']['position']].append(r)

    # 3. Escalar Titulares (4-3-3)
    formation = {'Goalkeeper': 1, 'Defender': 4, 'Midfielder': 3, 'Attacker': 3}
    starters = []
    reserves = []

    for pos, limit in formation.items():
        pos_players = players_by_pos[pos]
        
        # Titulares: os 'limit' melhores por ESC
        pos_starters = pos_players[:limit]
        starters.extend(pos_starters)
        
        # Achar o menor preço entre os titulares desta posição
        if pos_starters:
            cheapest_starter_price = min(s['player_obj'].price_cartoletas for s in pos_starters)
        else:
            cheapest_starter_price = float('inf')
            
        # Reservas: filtrar quem custa MENOS ou IGUAL ao titular mais barato
        # E pegar os melhores ESC restantes
        remaining_players = pos_players[limit:]
        valid_reserves = [r for r in remaining_players if r['player_obj'].price_cartoletas <= cheapest_starter_price]
        
        bench_limit = 2 if pos == 'Defender' else 1
        reserves.extend(valid_reserves[:bench_limit])

    # 4. Definir Capitão e Reserva de Luxo
    captain = max(starters, key=lambda x: x['expected_score_contextual'])
    captain_id = captain['player']['id']

    reserva_luxo = max(reserves, key=lambda x: x['expected_score_contextual'])
    reserva_luxo_id = reserva_luxo['player']['id']

    # 5. Aplicar Regras de Substituição (Ao Vivo)
    logs_substituicoes = []
    
    # 5.1 Substituição Comum (Titular não jogou = minutos 0)
    final_starters = []
    for starter in starters:
        if starter['minutes_played'] == 0:
            # Procura reserva normal da mesma posicao
            sub = next((r for r in reserves if r['player']['position'] == starter['player']['position'] and r['player']['id'] != reserva_luxo_id), None)
            if sub and sub['minutes_played'] > 0:
                final_starters.append(sub)
                reserves.remove(sub)
                logs_substituicoes.append(f"[SUBSTITUICAO] {sub['player']['name']} entrou no lugar de {starter['player']['name']} (Nao jogou)")
            else:
                final_starters.append(starter)
        else:
            final_starters.append(starter)

    # 5.2 Substituição do Reserva de Luxo
    luxo_pos = reserva_luxo['player']['position']
    # Encontra o titular (que jogou) com a PIOR pontuação na mesma posição
    titulares_mesma_pos = [s for s in final_starters if s['player']['position'] == luxo_pos]
    if titulares_mesma_pos and reserva_luxo['minutes_played'] > 0:
        pior_titular = min(titulares_mesma_pos, key=lambda x: x['real_score'])
        
        # Regra do Cartola: Luxo entra se a pontuação dele for MAIOR que a do pior titular
        if reserva_luxo['real_score'] > pior_titular['real_score']:
            final_starters.remove(pior_titular)
            final_starters.append(reserva_luxo)
            logs_substituicoes.append(f"[RESERVA DE LUXO] {reserva_luxo['player']['name']} ({reserva_luxo['real_score']} pts) substituiu {pior_titular['player']['name']} ({pior_titular['real_score']} pts)")

    # 6. Calcular Técnico
    # Achar o time com a maior média de ESC do campeonato na rodada
    team_esc = defaultdict(list)
    for r in all_recs:
        team_esc[r['player']['team_name']].append(r['expected_score_contextual'])
    
    best_team_name = max(team_esc.keys(), key=lambda t: sum(team_esc[t][:11]))
    
    # Calcular pontuação real do técnico: (Soma do time / 11) + 1 se venceu
    team_real_pts = []
    won = False
    for f in fixtures:
        is_home = (f.home_team.name == best_team_name)
        is_away = (f.away_team.name == best_team_name)
        if is_home or is_away:
            # Pegar todos os stats reais do time
            stats = db.query(PlayerMatchStats).filter(PlayerMatchStats.fixture_id == f.id).all()
            for s in stats:
                if (is_home and s.is_home) or (is_away and not s.is_home):
                    team_real_pts.append(s.match_cartola_score)
            
            # Ver se venceu
            if is_home and f.home_goals > f.away_goals: won = True
            if is_away and f.away_goals > f.home_goals: won = True
            break
            
    coach_score = (sum(team_real_pts) / 11) + (1.0 if won else 0.0)

    # 7. Print do Resultado Final
    print('-'*90)
    print(f'{"JOGADOR":<20} | {"POSIÇÃO":<10} | {"ESC":<7} | {"PONTOS REAIS":<15}')
    print('-'*90)

    total_real = 0.0
    for s in final_starters:
        pts = s['real_score']
        label = ""
        if s['player']['id'] == captain_id:
            pts *= 1.5
            label = " (CAPITÃO 1.5x)"
            
        total_real += pts
        print(f"{s['player']['name'][:19]:<20} | {s['player']['position'][:10]:<10} | {s['expected_score_contextual']:<7.2f} | {pts:<7.2f}{label}")

    print('-'*90)
    print(f"{'Técnico (' + best_team_name + ')':<20} | {'Coach':<10} | {'--':<7} | {coach_score:<7.2f} {'(+1 Vitória)' if won else ''}")
    total_real += coach_score
    print('-'*90)
    print(f"PONTUAÇÃO TOTAL DO TIME: {total_real:.2f} pontos")
    print('-'*90)
    
    if logs_substituicoes:
        print("MUDANÇAS DURANTE A RODADA:")
        for log in logs_substituicoes:
            print("  " + log)

if __name__ == "__main__":
    simulate_full_cartola_rules()
