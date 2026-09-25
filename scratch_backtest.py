from app.db.session import SessionLocal
from app.models.fixture import Fixture
from app.models.player_match_stats import PlayerMatchStats
from app.services.recommendation_engine import RecommendationEngine

def run_backtest():
    db = SessionLocal()

    # Pega a partida mais recente real que tem STATS reais
    stat_with_score = db.query(PlayerMatchStats).filter(PlayerMatchStats.match_cartola_score != 0).order_by(PlayerMatchStats.match_date.desc()).first()
    fixture = db.query(Fixture).filter(Fixture.id == stat_with_score.fixture_id).first()
    print(f'Partida Real: {fixture.home_team.name} vs {fixture.away_team.name} (Data: {fixture.match_date})')

    # Roda o motor
    engine = RecommendationEngine(db)
    recs = engine.get_recommendations_for_fixture(fixture.id, limit=11)

    print('-'*75)
    print(f'{"JOGADOR":<20} | {"POSIÇÃO":<10} | {"PREVISTO (ESC)":<15} | {"SCORE REAL":<10} | {"ERRO":<10}')
    print('-'*75)

    total_esc = 0
    total_real = 0

    for r in recs:
        p_id = r['player']['id']
        name = r['player']['name']
        pos = r['player']['position']
        esc = r['expected_score_contextual']
        
        # Busca o que ele realmente pontuou
        stat = db.query(PlayerMatchStats).filter(
            PlayerMatchStats.player_id == p_id, 
            PlayerMatchStats.fixture_id == fixture.id
        ).first()
        
        real_score = stat.match_cartola_score if stat else 0.0
        diff = real_score - esc
        
        total_esc += esc
        total_real += real_score
        
        print(f'{name[:19]:<20} | {pos[:10]:<10} | {esc:<15.2f} | {real_score:<10.2f} | {diff:<10.2f}')

    print('-'*75)
    print(f'{"TOTAL DO TIME":<33} | {total_esc:<15.2f} | {total_real:<10.2f} | {total_real - total_esc:<10.2f}')

if __name__ == "__main__":
    run_backtest()
