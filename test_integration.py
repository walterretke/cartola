from fastapi.testclient import TestClient
from app.main import app

def test_full_flow():
    with TestClient(app) as client:
        # 1. Scout Actions
        res_scouts = client.get('/api/v1/scout-actions')
        assert res_scouts.status_code == 200
        scouts = res_scouts.json()
        print(f"Total de Scouts Mestre cadastrados: {len(scouts)}")
        for s in scouts[:5]:
            print(f"  - {s['code']} ({s['name']}): {s['points']} pts [{s['category']}]")

        # 2. Sync
        res_sync = client.post('/api/v1/sync/run')
        assert res_sync.status_code == 200
        sync_data = res_sync.json()
        print("\nResultado da Sincronização:")
        for k, v in sync_data.items():
            print(f"  {k}: {v}")

        # 3. List Players
        res_players = client.get('/api/v1/players?limit=6')
        assert res_players.status_code == 200
        players = res_players.json()
        print(f"\nTop 6 Atletas Ordenados por Smart Score:")
        for p in players:
            score = p.get('score', {})
            print(
                f"  * {p['name']} ({p['position']} - {p['team_name']}): "
                f"Smart Score: {score.get('smart_score')} | "
                f"Média: {score.get('avg_points')} | "
                f"Casa: {score.get('avg_points_home')} | "
                f"Fora: {score.get('avg_points_away')} | "
                f"Oscilação (DP): {score.get('std_deviation')} | "
                f"Regularidade: {score.get('consistency_index')}%"
            )

        # 4. Detalhes do Primeiro Atleta
        first_id = players[0]['id']
        res_detail = client.get(f'/api/v1/players/{first_id}')
        assert res_detail.status_code == 200
        detail = res_detail.json()
        print(f"\nHistórico Detalhado: {detail['name']} ({detail['team_name']})")
        print(f"Total de partidas avaliadas: {len(detail['match_stats'])}")
        for m in detail['match_stats']:
            mando = "CASA" if m['is_home'] else "FORA"
            print(
                f"  - {m['round_name']} [{mando}]: {m['match_cartola_score']} pts | "
                f"Gols: {m['goals']} | Assists: {m['assists']} | "
                f"FD: {m['shots_on_target']} | DS: {m['tackles']} | "
                f"FS: {m['fouls_drawn']} | SG: {m['clean_sheet']}"
            )

if __name__ == "__main__":
    test_full_flow()
