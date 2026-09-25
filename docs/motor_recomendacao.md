# Motor de Recomendação Contextual — CartolaAI

> **Objetivo:** Dado que o mercado abriu para a Rodada X, recomendar os 11 melhores jogadores
> levando em conta **o contexto da partida que ele vai jogar**, e não apenas seu desempenho histórico geral.

---

## O Problema Central

O `smart_score` responde: **"Quão bom é esse jogador no geral?"**

Mas o que o cartoleiro precisa saber é:

> **"Quanto esse jogador vai pontuar NA PRÓXIMA PARTIDA, contra ESSE adversário, jogando EM CASA ou FORA?"**

Exemplo real: Um zagueiro do Palmeiras tem `smart_score = 7.5`. Mas na próxima rodada:
- Ele joga **FORA** (e historicamente pontua 3.2 fora vs 9.8 em casa)
- Contra o **Flamengo** (que marca 2.1 gols/jogo fora → baixa probabilidade de SG)
- Ele tomou **cartão amarelo** no último jogo (risco de suspensão com 2º amarelo)

Nesse cenário, recomendar esse jogador seria um **erro grave**. O `smart_score` não captura isso.

---

## Os 12 Fatores Científicos do Motor Contextual

### Fator 1: Mando de Campo (Home/Away Split)
**Impacto: ⭐⭐⭐⭐⭐ (Crítico)**

O futebol brasileiro tem uma das maiores vantagens de mando de campo do mundo.
Estudos mostram que times da Série A ganham ~60% dos jogos em casa.

**Métricas que já temos:**
- `avg_points_home` vs `avg_points_away`
- `home_matches` / `away_matches` (amostragem)

**Como usar:**
- Se o jogador joga EM CASA → usar `avg_points_home` como base
- Se o jogador joga FORA → usar `avg_points_away` como base
- Calcular o `home_away_factor`: razão entre a média contextual e a média geral

```python
# Exemplo
if proxima_partida.is_home:
    base_esperada = player.avg_points_home
else:
    base_esperada = player.avg_points_away

home_away_factor = base_esperada / player.avg_points  # >1.0 = bônus, <1.0 = penalidade
```

**Regra de segurança:** Se o jogador tem < 3 jogos naquele mando, usar a média geral com desconto.

---

### Fator 2: Força do Adversário — Perfil Ofensivo
**Impacto: ⭐⭐⭐⭐⭐ (Crítico para defensores/goleiros)**

O adversário define a probabilidade de **Saldo de Gols (SG)**, que vale +5.0 pontos.
Para goleiros e zagueiros, o SG é frequentemente o scout que MAIS pesa na pontuação.

**Métrica necessária (por time adversário):**
- `opponent_avg_goals_scored` — média de gols que o adversário marca por jogo
- `opponent_avg_goals_scored_home` / `opponent_avg_goals_scored_away` — contextualizado
- `opponent_shots_per_game` — pressão ofensiva do adversário

**Como usar:**
```
sg_probability = f(meu_time_gols_sofridos_por_jogo, adversario_gols_marcados_por_jogo, mando)

# Adversário marca pouco + meu time sofre pouco + jogo em casa = SG provável
# Adversário marca muito + jogo fora = SG improvável
```

**Impacto real:** Um goleiro que faz 4.0 pts/jogo SEM SG pode fazer 9.0 pts COM SG.
A diferença de 5.0 pontos é maior que a maioria dos gols.

---

### Fator 3: Força do Adversário — Perfil Defensivo
**Impacto: ⭐⭐⭐⭐⭐ (Crítico para atacantes/meias)**

Contra uma defesa fraca, atacantes tendem a finalizar mais e marcar mais.

**Métrica necessária (por time adversário):**
- `opponent_avg_goals_conceded` — média de gols que o adversário SOFRE por jogo
- `opponent_avg_goals_conceded_home` / `_away` — contextualizado
- `opponent_fouls_per_game` — adversários "faltosos" geram mais FS (+0.5 cada)

**Como usar:**
```python
# Atacante jogando contra time que sofre 2+ gols/jogo → bônus ofensivo
if opponent.avg_goals_conceded > 1.5:
    attack_bonus = 1.15  # +15%
elif opponent.avg_goals_conceded < 0.8:
    attack_bonus = 0.85  # -15%
```

---

### Fator 4: Clean Sheet Probability (Probabilidade de SG)
**Impacto: ⭐⭐⭐⭐⭐ (O scout mais decisivo do Cartola)**

SG (+5.0) é, estatisticamente, o scout que mais separa uma rodada BOA de uma rodada RUIM
para jogadores defensivos. É um "swing" de 5.0 pontos que acontece ou não.

**Cálculo proposto:**
```python
# Dados do meu time
team_clean_sheet_rate = team.clean_sheets / team.matches  # Ex: 40%
team_goals_conceded_per_game = team.goals_conceded / team.matches  # Ex: 0.9

# Dados do adversário
opp_goals_scored_per_game = opponent.goals_scored / opponent.matches  # Ex: 1.2

# Contextualizar por mando
if is_home:
    # Em casa, times sofrem menos gols
    context_modifier = 0.80  # reduz a ameaça do adversário em 20%
else:
    context_modifier = 1.20  # fora, adversário é mais perigoso

adjusted_opp_threat = opp_goals_scored_per_game * context_modifier

# Probabilidade de SG usando distribuição de Poisson
import math
sg_probability = math.exp(-adjusted_opp_threat)  # P(X=0) na Poisson
# Ex: Se adjusted_threat = 0.8 → sg_prob = 0.449 (44.9%)
# Ex: Se adjusted_threat = 2.0 → sg_prob = 0.135 (13.5%)

# Contribuição esperada do SG para a pontuação
expected_sg_points = sg_probability * 5.0
```

---

### Fator 5: Volume de Ações (Shot Volume, Tackle Volume)
**Impacto: ⭐⭐⭐⭐ (Alto)**

Jogadores que acumulam MUITAS ações por jogo tendem a pontuar mais de forma consistente,
independente de marcarem gol ou não. É o "piso de pontuação".

**Métricas que já temos:**
- `avg_shots_on_target` (FD: +1.2 cada)
- `avg_shots_off_target` (FF: +0.8 cada)
- `avg_fouls_drawn` (FS: +0.5 cada)
- `avg_tackles` (DS: +1.5 cada)
- `avg_saves` (DE: +1.3 cada)

**Como usar:**
```python
# "Piso de pontuação" = quanto o jogador tende a marcar SEM gol
floor_score = (
    avg_shots_on_target * 1.2 +
    avg_shots_off_target * 0.8 +
    avg_fouls_drawn * 0.5 +
    avg_tackles * 1.5 -
    avg_fouls_committed * 0.3 -
    avg_yellow_cards * 1.0
)

# Jogador com floor_score alto é "seguro" — pontua bem mesmo sem gol
# Jogador com floor_score baixo depende de eventos raros (gols) para pontuar
```

**Exemplo real:**
- Raphael Veiga (meia/Palmeiras): floor ~4.0 (muita finalização, falta sofrida)
- Pedro (atacante/Flamengo): floor ~2.0 (menos ações, mas MUITOS gols)

Pedro tem ceiling mais alto, mas Veiga é mais "seguro" rodada a rodada.

---

### Fator 6: Consistência vs Explosão (Perfil de Risco)
**Impacto: ⭐⭐⭐⭐ (Alto)**

Dois jogadores com `avg_points = 6.0` podem ser completamente diferentes:

| Jogador A (Consistente) | Jogador B (Explosivo) |
|---|---|
| Rodada 1: 5.5 | Rodada 1: 15.0 |
| Rodada 2: 6.2 | Rodada 2: -2.0 |
| Rodada 3: 6.8 | Rodada 3: 12.0 |
| Rodada 4: 5.5 | Rodada 4: -1.0 |
| Média: 6.0 | Média: 6.0 |
| Desvio: 0.56 | Desvio: 7.87 |

**Métricas que já temos:**
- `std_deviation`
- `consistency_index` (0 a 100)
- `min_score` / `max_score`

**Como usar (inspirado no Sharpe Ratio das finanças):**
```python
# Risk-Adjusted Score = retorno esperado / risco
if std_deviation > 0:
    sharpe_like = avg_points / std_deviation  # Quanto maior, melhor relação retorno/risco
else:
    sharpe_like = avg_points * 2  # Sem risco = excelente

# Jogador A: 6.0 / 0.56 = 10.7 (ótimo!)
# Jogador B: 6.0 / 7.87 = 0.76 (péssimo ajustado ao risco)
```

**Estratégia contextual:**
- Se você está em uma liga MATA-MATA e precisa arriscar → prefira explosivos
- Se você está em liga de PONTOS CORRIDOS e precisa regularidade → prefira consistentes

---

### Fator 7: Momentum / Tendência Recente
**Impacto: ⭐⭐⭐⭐ (Alto)**

Um jogador em ascensão tende a manter a performance (confiança, forma física, entrosamento).
Um jogador em queda pode estar com problema físico, perdendo posição, ou desmotivado.

**Métricas que já temos:**
- `last_3_avg` / `last_5_avg`
- `trend` (rising, falling, stable)

**Como usar:**
```python
# Peso do momentum no score contextual
if trend == "rising":
    momentum_modifier = 1.08  # +8%
elif trend == "falling":
    momentum_modifier = 0.92  # -8%
else:
    momentum_modifier = 1.00

# Ponderar mais o momento recente
contextual_base = (avg_points * 0.35) + (last_3_avg * 0.40) + (last_5_avg * 0.25)
```

---

### Fator 8: Garantia de Minutos (Titular vs Reserva)
**Impacto: ⭐⭐⭐⭐ (Alto — Risco binário)**

Um jogador que entra no 2º tempo tem METADE do tempo para acumular scouts.
Pior: se ele não entrar em campo, a pontuação é ZERO.

**Métricas que já temos:**
- `was_substitute` (em cada partida)
- `minutes_played` (em cada partida)
- `total_minutes` / `matches_played` = `avg_minutes`

**Como usar:**
```python
avg_minutes = total_minutes / matches_played

# Penalidade progressiva:
if avg_minutes >= 80:
    minutes_modifier = 1.00  # Titular absoluto
elif avg_minutes >= 60:
    minutes_modifier = 0.85  # Titular com risco de sair cedo
elif avg_minutes >= 30:
    minutes_modifier = 0.60  # Reserva que entra frequentemente
else:
    minutes_modifier = 0.30  # Risco altíssimo de não jogar

# Percentual de jogos como titular
starter_rate = jogos_como_titular / matches_played
if starter_rate < 0.5:
    minutes_modifier *= 0.80  # Penalidade extra para reserva frequente
```

---

### Fator 9: Desempenho Histórico contra o Adversário Específico
**Impacto: ⭐⭐⭐ (Médio — depende da amostragem)**

Alguns jogadores têm "desempenhos fetiche" contra determinados times.

**Métrica necessária (consultar PlayerMatchStats):**
```python
# Filtrar stats do jogador contra o adversário da próxima rodada
historico_vs_opp = db.query(PlayerMatchStats).filter(
    PlayerMatchStats.player_id == player.id,
    PlayerMatchStats.opponent_team_id == next_opponent_id
).all()

if len(historico_vs_opp) >= 2:
    avg_vs_opponent = mean([m.match_cartola_score for m in historico_vs_opp])
    # Se avg_vs_opponent é muito diferente da média geral, ajustar
```

**Regra:** Só usar se houver pelo menos 2 confrontos anteriores (amostragem mínima).

---

### Fator 10: Disciplina e Risco de Cartão/Expulsão
**Impacto: ⭐⭐⭐ (Médio — mas devastador quando acontece)**

- Cartão amarelo: -1.0
- Cartão vermelho: -3.0 + perde tempo de jogo restante + perde SG
- Pênalti cometido: -1.0

**Métricas que já temos:**
- `avg_yellow_cards`
- `avg_fouls_committed`
- `discipline_risk`

**Como usar:**
```python
# Risco de cartão por jogo (baseado no histórico)
card_risk = avg_yellow_cards + (avg_red_cards * 3)  # Vermelho pesa 3x mais

# Penalidade no score contextual
discipline_penalty = card_risk * 0.5  # Cada 0.5 de risco = -0.25 no score esperado
```

---

### Fator 11: Dados Avançados (Inteligência Extra da API)
**Impacto: ⭐⭐⭐ (Médio — diferencial competitivo)**

Dados que o Cartola oficial NÃO mostra, mas que nós temos:

| Dado | O que revela | Para quem importa |
|---|---|---|
| `passes_key` | Quase-assistências (o "quase gol" do time) | Meias criadores |
| `dribbles_success` | Capacidade de criar jogadas individuais | Atacantes/Pontas |
| `duels_won` | Dominância física | Volantes/Zagueiros |
| `duel_win_pct` | Eficiência nos duelos | Todos |
| `interceptions` | Leitura de jogo defensiva | Zagueiros/Volantes |
| `pass_accuracy` | Qualidade técnica | Meias |
| `rating` (Sofascore) | Avaliação geral da performance | Todos |

**Como usar:**
```python
# Indicador de "dominância" — jogador que controla o jogo
dominance_index = (
    (duel_win_pct / 100) * 0.3 +
    (avg_passes_key / max_passes_key_in_league) * 0.25 +
    (avg_dribbles_success / max_dribbles_in_league) * 0.15 +
    (avg_interceptions / max_interceptions_in_league) * 0.15 +
    (avg_rating / 10.0) * 0.15
)
```

---

### Fator 12: Eficiência por Cartoleta (Custo-Benefício)
**Impacto: ⭐⭐⭐ (Médio — essencial para otimização de escalação)**

Quando implementarmos a otimização de time completo (11 jogadores dentro do orçamento),
o custo-benefício será CRUCIAL.

**Nota:** A API-Football não fornece preço em Cartoletas (isso é exclusivo do app oficial).
Quando integrarmos esses dados (ou estimarmos), usaremos:

```python
cartoleta_efficiency = expected_points / player_price
# Jogador que custa C$5 e pontua 8.0 → efficiency = 1.6
# Jogador que custa C$25 e pontua 10.0 → efficiency = 0.4
# O barato é MUITO mais eficiente!
```

---

## Fórmula do Expected Score Contextual (ESC)

A fórmula final que combina todos os fatores:

```python
def calculate_expected_score(player, next_match):
    """
    Calcula o Expected Score Contextual (ESC) para a próxima partida.
    """
    # 1. Base contextualizada por mando
    if next_match.is_home:
        base = player.avg_points_home
    else:
        base = player.avg_points_away
    
    # Se amostragem insuficiente, fazer blend com média geral
    context_matches = player.home_matches if next_match.is_home else player.away_matches
    if context_matches < 3:
        blend_weight = context_matches / 3.0
        base = (base * blend_weight) + (player.avg_points * (1 - blend_weight))
    
    # 2. Ponderar com momentum recente (últimos 3 jogos pesam muito)
    weighted_base = (base * 0.45) + (player.last_3_avg * 0.35) + (player.last_5_avg * 0.20)
    
    # 3. Ajuste de adversário
    opponent_attack_factor = calculate_opponent_attack_factor(next_match.opponent)
    opponent_defense_factor = calculate_opponent_defense_factor(next_match.opponent)
    
    if player.position in ("Goalkeeper", "Defender"):
        # Para defensores: adversário forte no ataque = ruim (menos chance de SG)
        opponent_factor = 1.0 - (opponent_attack_factor - 1.0) * 0.3
        # Adicionar contribuição esperada do SG
        sg_expected = calculate_sg_probability(player, next_match) * 5.0
        weighted_base += sg_expected * 0.5  # Peso parcial pois já está parcialmente na média
    else:
        # Para atacantes/meias: adversário fraco na defesa = bom
        opponent_factor = opponent_defense_factor
    
    # 4. Modificadores
    momentum_mod = {"rising": 1.06, "falling": 0.94, "stable": 1.0}[player.trend]
    
    avg_minutes = player.total_minutes / max(player.matches_played, 1)
    if avg_minutes >= 80:
        minutes_mod = 1.00
    elif avg_minutes >= 60:
        minutes_mod = 0.85
    elif avg_minutes >= 30:
        minutes_mod = 0.60
    else:
        minutes_mod = 0.30
    
    # Consistência: jogadores regulares ganham leve bônus de confiança
    consistency_mod = 0.92 + (player.consistency_index / 100) * 0.16  # 0.92 a 1.08
    
    # Penalidade de amostragem
    sample_mod = min(1.0, player.matches_played / 5.0)
    
    # 5. Score final
    esc = (
        weighted_base
        * opponent_factor
        * momentum_mod
        * minutes_mod
        * consistency_mod
        * sample_mod
    )
    
    return round(esc, 2)
```

---

## Hierarquia dos Fatores por Posição

### ⚽ Goleiro
| Prioridade | Fator | Justificativa |
|---|---|---|
| 1º | SG Probability | SG vale +5.0, é o scout de maior impacto absoluto |
| 2º | Saves Volume (DE) | Goleiros com muitas defesas acumulam pontos consistentes |
| 3º | Mando de Campo | Times sofrem menos gols em casa |
| 4º | Adversário (Ataque) | Adversário que chuta pouco = mais chance de SG |
| 5º | Minutos Garantidos | Goleiro reserva = ZERO pontos |

### 🛡️ Zagueiro / Lateral
| Prioridade | Fator | Justificativa |
|---|---|---|
| 1º | SG Probability | Assim como goleiro, SG é devastador |
| 2º | Desarmes (DS) | Volume de DS define o piso de pontuação |
| 3º | Mando de Campo | Zagueiros pontuam MUITO mais em casa |
| 4º | Disciplina | Zagueiros levam muitos cartões |
| 5º | Adversário (Ataque) | Define probabilidade de SG |

### 🎯 Meia
| Prioridade | Fator | Justificativa |
|---|---|---|
| 1º | Volume de Ações | Meias acumulam FD, FS, DS — é o piso |
| 2º | Momentum | Meias em boa fase fazem MUITOS scouts |
| 3º | Adversário (Defesa) | Defesa fraca = mais chances de G e A |
| 4º | Passes Decisivos | Key passes indicam potencial de assistência |
| 5º | Consistência | Meias são a posição mais consistente |

### ⚡ Atacante
| Prioridade | Fator | Justificativa |
|---|---|---|
| 1º | Adversário (Defesa) | Defesa fraca = GOLS (G vale +8.0!) |
| 2º | Volume de Finalizações | Quem chuta mais, marca mais |
| 3º | Momentum | Atacante "em fase" é imparável |
| 4º | Mando de Campo | Atacantes marcam mais em casa |
| 5º | Faltas Sofridas | FS acumula bem para dribladores |

---

## Dados que Precisamos Construir (Próximos Passos)

### 1. Perfil de Time (TeamProfile)
Para calcular SG Probability e ajuste de adversário, precisamos de um modelo de TIME:

```python
class TeamProfile:
    team_id: int
    team_name: str
    matches_played: int
    # Ataque
    avg_goals_scored: float
    avg_goals_scored_home: float
    avg_goals_scored_away: float
    avg_shots_per_game: float
    # Defesa
    avg_goals_conceded: float
    avg_goals_conceded_home: float
    avg_goals_conceded_away: float
    clean_sheet_rate: float
    # Disciplina
    avg_fouls_per_game: float
    avg_cards_per_game: float
```

### 2. Tabela de Confrontos (FixtureCalendar)
Para saber QUAL é a próxima partida de cada time:

```python
class NextFixture:
    fixture_id: int
    round_name: str
    home_team_id: int
    away_team_id: int
    match_date: datetime
```

### 3. Endpoint de Recomendação
```
GET /api/v1/recommendations?
    round=35
    position=Attacker
    budget=50.0
    strategy=balanced  # balanced | aggressive | safe
```

Retorna os jogadores rankeados por **Expected Score Contextual (ESC)** para aquela rodada.

---

## Resumo: Smart Score vs Expected Score Contextual

| Aspecto | Smart Score (atual) | Expected Score Contextual (novo) |
|---|---|---|
| **Pergunta** | "Quão bom é esse jogador?" | "Quanto ele vai pontuar NESTA partida?" |
| **Contexto** | Nenhum | Mando, adversário, momento |
| **Frequência** | Recalculado a cada sync | Calculado sob demanda por rodada |
| **Uso** | Ranking geral de jogadores | Recomendação de escalação |
| **Depende de** | Histórico do jogador | Histórico + Adversário + Calendário |
