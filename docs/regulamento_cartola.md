# Regulamento Completo — Cartola FC 2026

> **Fonte oficial:** [ge.globo.com/cartola](https://ge.globo.com/cartola)
> Este documento serve como base de conhecimento para o motor de pontuação e o otimizador de escalações do CartolaAI.

---

## 1. O que é o Cartola

O Cartola é o fantasy game oficial da Globo onde o jogador monta seu próprio time com atletas reais da **Série A do Campeonato Brasileiro**. A cada rodada do Brasileirão, o time pontua com base nas ações dos jogadores nas partidas. O objetivo é competir contra amigos e outros cartoleiros para provar quem entende mais de futebol.

### Resumo do Jogo

- Escale **11 jogadores** e **1 técnico** usando **Cartoletas** (a moeda do game).
- A cada rodada, o time pontua com base nos **scouts** (ações em campo).
- Participe de **ligas** e dispute rankings com amigos.
- Existe a versão **FREE** e a versão **PRO** (com benefícios exclusivos).

---

## 2. Mercado e Rodadas

### 2.1 Mercado de Jogadores

O mercado é onde se visualizam todos os atletas da Série A e se monta o time para a rodada.

| Estado do Mercado | Descrição |
|---|---|
| **Aberto** | Escalação permitida. Fecha **1 minuto antes** do primeiro jogo da rodada. |
| **Fechado** | Escalação bloqueada. Parciais de pontuação em tempo real disponíveis. |
| **Reabertura** | Algumas horas após o fim do último jogo da rodada. |

### 2.2 Rodadas

- O Brasileirão possui **38 rodadas**.
- **20 times** se enfrentam em **10 jogos** por rodada (turno e returno).
- As rodadas do Cartola seguem as do Campeonato Brasileiro.

---

## 3. Meu Time

### 3.1 Criação do Time

Para jogar, o cartoleiro cria um perfil informando:
- Nome do presidente (o jogador).
- Nome do time.
- Escudo e uniforme.
- 2 patrocinadores (participação automática na liga do patrocinador escolhido).

### 3.2 Escalação

O time é composto por:
- **11 jogadores** de campo (de acordo com o esquema tático).
- **1 técnico**.
- **1 capitão** (escolhido entre os 11 jogadores — o técnico **não** pode ser capitão).

#### Fatores a considerar na escalação:
- Esquema tático escolhido.
- Status do atleta.
- Preço em Cartoletas (C$).
- Performance nas últimas rodadas.
- Scouts e estatísticas.

### 3.3 Esquemas Táticos

Existem **7 formações** disponíveis:

| Formação | Zagueiros | Laterais | Meias | Atacantes | Observação |
|---|---|---|---|---|---|
| **3-4-3** | 3 | 0 | 4 | 3 | Equilibrado entre ataque e defesa |
| **3-5-2** | 3 | 0 | 5 | 2 | Forte no meio de campo |
| **4-3-3** | 2 | 2 | 3 | 3 | Mais popular entre cartoleiros |
| **4-4-2** | 2 | 2 | 4 | 2 | Esquema padrão, mais defensivo |
| **4-5-1** | 2 | 2 | 5 | 1 | Apoiado na defesa |
| **5-3-2** | 3 | 2 | 3 | 2 | Maior linha de defesa |
| **5-4-1** | 3 | 2 | 4 | 1 | Extremamente defensivo |

> **Importante:** Formações sem laterais (3-x-x) possuem no máximo **4 reservas** (1 por posição disponível). As demais possuem **5 reservas**.

### 3.4 Status dos Atletas

| Status | Ícone | Significado |
|---|---|---|
| **Provável** | 🟢 | Altas chances de ser escalado no próximo jogo |
| **Suspenso** | 🔴 | Não entrará em campo |
| **Machucado** | 🏥 | Provavelmente não jogará por lesão recente |
| **Dúvida** | 🟡 | Participação incerta (mistério do técnico, retorno de lesão, poupa) |
| **Nulo** | ⚫ | Sem status vinculado; muito provável que não jogue |

> ⚠️ Os status são apenas **estimativas** e podem não refletir a decisão final do técnico do clube.

### 3.5 Capitão

- O capitão tem sua pontuação **multiplicada por 1,5×** (tanto positiva quanto negativa).
- **Apenas jogadores** podem ser capitão (técnico não pode).
- Se o capitão não jogar, a braçadeira é passada para o reserva que o substituir.

**Exemplo:**
| Pontuação do jogador | Pontuação como capitão |
|---|---|
| +10.0 pts | +15.0 pts |
| -10.0 pts | -15.0 pts |

### 3.6 Técnico

A pontuação do técnico é calculada assim:

```
pontuação_técnico = (soma_pontuação_todos_atletas_do_clube / 11) + bônus_vitória
```

- **Bônus de vitória:** +1.0 ponto extra se o clube do técnico vencer na rodada.

### 3.7 Escalação Automática

- O sistema gera uma escalação **aleatória** respeitando o patrimônio e o status dos atletas.
- **Não é uma recomendação** — não se baseia em estatísticas nem modelos probabilísticos.
- O capitão e o banco de reservas continuam sendo definidos pelo cartoleiro.

---

## 4. Banco de Reservas

### 4.1 Regras Gerais

| Regra | Detalhe |
|---|---|
| **Opcional** | Só escala quando e como quiser |
| **Até 5 reservas** | 1 por posição do esquema tático |
| **Mudança automática** | Troca ocorre se titular não entrar em campo (nem como titular, nem como substituto) |
| **Condição** | A substituição **não acontece** se o reserva fizer pontuação **nula ou negativa** |
| **Valor do reserva** | Deve ter valor ≤ ao titular mais barato da posição |
| **Patrimônio** | Só é alterado na hora da troca (devolve a diferença) |
| **Pós-rodada** | Reservas que entraram viram titulares; banco é esvaziado |

### 4.2 Substituições Durante as Rodadas

| Indicador | Significado |
|---|---|
| 🟢 ↑ | Substituto que entrou em campo |
| 🔴 ↓ | Titular substituído |
| --- | Ainda não jogou |
| -2.30 | Substituição do titular não efetuada (reserva fez pontuação negativa) |

### 4.3 Ordem de Prioridade (quando vários titulares da mesma posição não jogam)

1. Horário da partida
2. Se o atleta é capitão
3. Atleta de maior valor
4. Ordem alfabética

### 4.4 Reserva de Luxo

Funcionalidade que permite escolher um jogador do banco para **substituir automaticamente o titular com a pior pontuação** na posição (positiva ou negativa), **desde que** o Reserva de Luxo tenha pontuado mais.

**Regras:**
- Seleção opcional no momento da escalação.
- **Todos os titulares da posição precisam ter jogado** para que a substituição ocorra.
- Se algum titular não entrou em campo, aplicam-se as regras normais do banco.
- O Reserva de Luxo pode substituir titular com pontuação negativa.
- A substituição só acontece ao **final das partidas** dos titulares da posição.

**Desempate na pior pontuação:**
1. Se um dos jogadores é capitão → substituído primeiro.
2. Caso contrário → regras normais do banco de reservas.

---

## 5. Pontuação — Scouts

### 5.1 Tabela Completa de Scouts

As ações dos jogadores em campo são chamadas de **Scouts**. São elas que geram a pontuação do time.

#### ⚽ Scouts de Ataque

| Scout | Código | Pontuação | Descrição |
|---|---|---|---|
| **Gol** | `G` | **+8.0** | Gol marcado pelo jogador |
| **Assistência** | `A` | **+5.0** | Último evento antes da finalização que resulta em gol (passe, cruzamento, lançamento). Válida mesmo com leve desvio no adversário. Não conta desvios involuntários, erro de domínio ou bola que "sobra". |
| **Finalização na trave** | `FT` | **+3.0** | Finalização que toca na trave, mesmo com desvio de adversário ou defesa anterior do goleiro |
| **Finalização defendida** | `FD` | **+1.2** | Finalização que o goleiro defende (e a bola segue em jogo ou sai para escanteio). Também conta quando jogador de linha, como último homem, salva finalização na direção do gol. **Não conta** bolas que chegam quase parando ao goleiro ou que ele apenas evita escanteio/saída pela linha de fundo longe da meta. |
| **Pênalti sofrido** | `PS` | **+1.0** | Jogador sofre pênalti |
| **Finalização pra fora** | `FF` | **+0.8** | Finalização que sai pela linha de fundo (mesmo com desvio de adversário de linha para escanteio). Se o goleiro tocar antes do escanteio → conta como FD. Finalizações erradas que saem diretamente pela linha lateral sem tocar em outro jogador também contam. |
| **Falta sofrida** | `FS` | **+0.5** | Jogador sofre falta |
| **Impedimento** | `I` | **-0.1** | Jogador flagrado em impedimento |
| **Pênalti perdido** | `PP` | **-4.0** | Jogador erra cobrança de pênalti |

#### 🛡️ Scouts de Defesa

| Scout | Código | Pontuação | Descrição |
|---|---|---|---|
| **Defesa de pênalti** | `DP` | **+7.0** | *Exclusivo do goleiro.* Goleiro efetivamente defende cobrança de pênalti. Cobranças na trave ou para fora **não** configuram defesa de pênalti. |
| **Jogo sem sofrer gols** | `SG` | **+5.0** | Time do jogador não sofre gols na partida |
| **Desarme** | `DS` | **+1.5** | Jogador interrompe jogada adversária com ação clara (tomando a bola, interceptando passe, evitando drible), mesmo que na sequência a bola saia de campo. **Não conta** se a bola volta imediatamente para o time adversário. **Bloqueios** de cruzamento e finalizações **não** são desarmes. |
| **Defesa (goleiro)** | `DE` | **+1.3** | *Exclusivo do goleiro.* Defesa após finalização. Inclui evitar gol contra de companheiro. **Não conta** se o goleiro apenas pega sobra de finalização bloqueada quase parando, apenas evita escanteio, ou apenas evita saída pela linha de fundo longe da meta. |
| **Falta cometida** | `FC` | **-0.3** | Jogador comete falta |
| **Cartão amarelo** | `CA` | **-1.0** | Jogador recebe cartão amarelo |
| **Gol sofrido** | `GS` | **-1.0** | Time do jogador sofre gol (aplica-se a todos os jogadores em campo) |
| **Pênalti cometido** | `PC` | **-1.0** | Jogador comete pênalti |
| **Cartão vermelho** | `CV` | **-3.0** | Jogador recebe cartão vermelho |
| **Gol contra** | `GC` | **-3.0** | Jogador faz gol contra |

#### 👔 Scout Exclusivo do Técnico

| Scout | Código | Pontuação | Descrição |
|---|---|---|---|
| **Vitória** | `V` | **+1.0** | Clube do técnico vence a partida |

### 5.2 Regras Importantes sobre Scouts

- Scouts de **ataque** valem para a **frente ofensiva** do time (atacantes, meias).
- Scouts de **defesa** valem para a **frente defensiva** do time (goleiro, zagueiros, laterais).
- Os scouts marcados com `*` (DE e DP) são **exclusivos dos goleiros**.
- O scout **SG** (Jogo sem sofrer gols) aplica-se a todos os jogadores defensivos.

### 5.3 Pontuação do Capitão

```
pontuação_capitão = pontuação_scouts × 1.5
```

Aplica-se a pontuações positivas **e negativas**.

### 5.4 Pontuação do Técnico

```
pontuação_técnico = (soma_pontuação_todos_jogadores_do_clube / 11) + (1.0 se vitória)
```

---

## 6. Patrimônio, Cartoletas e Valorização

### 6.1 Patrimônio

- Todo cartoleiro começa com **C$ 100** (cem cartoletas).
- **Patrimônio total** = valor do time escalado + cartoletas em caixa.
- O patrimônio é o recurso usado para competir na liga do patrimônio.

### 6.2 Cartoletas (C$)

- Moeda oficial do Cartola.
- Ganhas ou perdidas a cada rodada através da **valorização/desvalorização** dos jogadores escalados.

### 6.3 Doação de Cartoletas

- Disponível **1 vez por temporada** para cartoleiros com patrimônio entre **C$ 0** e **C$ 99.99**.
- Restaura o patrimônio para **C$ 100**.
- Pode ser usada em qualquer rodada enquanto o mercado estiver aberto.

### 6.4 Valorização

A valorização de um jogador considera:
- Pontuação da rodada.
- Média de pontuação ao longo do campeonato.
- Média de preços ao longo do campeonato.
- Performance relativa aos outros jogadores do mercado.
- Quantidade de cartoletas em circulação.

> **PRO:** Durante mercado fechado, acompanha valorização/desvalorização dos atletas nas parciais em tempo real.

### 6.5 Mínimo para Valorizar

- Estimativa gerada pelo **Gato Mestre** da pontuação mínima que o atleta precisa para começar a valorizar.
- Margem de precisão: **±0.5 pontos**.
- Disponível **exclusivamente para PRO** durante mercado aberto.

---

## 7. Performance dos Atletas

No mercado, para cada atleta estão disponíveis:

### Dados Básicos
- Clube atual
- Nome do jogador
- Posição
- Status
- Preço em Cartoletas
- Variação do preço na última rodada (valorização)
- Última pontuação
- Média de pontos no campeonato
- Quantidade de jogos disputados
- Próximo confronto

### Dados Detalhados
- Scouts detalhados por estratégia (ataque/defesa)
- Posição do clube na classificação
- Próximo jogo do clube
- Gráfico de desempenho em pontos nas últimas rodadas
- Histórico de valorização/desvalorização

---

## 8. Ligas

### 8.1 Tipos de Ligas

| Tipo | Duração | Participantes | Formato |
|---|---|---|---|
| **Clássica** | 1 a 38 rodadas | Sem limite | Ranking por pontuação |
| **Mata-Mata** | 2 a 5 rodadas | 4, 8, 16 ou 32 | Confrontos eliminatórios |
| **Pontos Corridos** | 3 a 38 rodadas | 4 a 38 | Confronto direto (ida e volta) |
| **Patrocinadas** | Todo o campeonato | Variável | Regras do patrocinador |
| **Oficiais do Cartola** | Todo o campeonato | Todos | Automáticas |

### 8.2 Modos de Acesso

| Modo | Descrição |
|---|---|
| **Aberta** | Todos podem entrar |
| **Moderada** | Todos pedem para participar; presidente aceita |
| **Fechada** | Somente por convite |

### 8.3 Ligas Clássicas

- Ranking ordenável por: posição na rodada, mês, turno, campeonato e patrimônio.
- Opção de **desabilitar pontuação 1,5× do capitão** (definido na criação, imutável depois).
- Parciais disponíveis apenas para ligas com até **100 cartoleiros**.
- Pontuação contabilizada **a partir da rodada de criação** da liga.

### 8.4 Ligas Mata-Mata

| Participantes | Chaves | Rodadas |
|---|---|---|
| 4 | 2 | 2 |
| 8 | 4 | 3 |
| 16 | 8 | 4 |
| 32 | 16 | 5 |

- A cada rodada, o time com menor pontuação é **eliminado**.
- Se a liga não atingir o número pré-definido, ajusta para o número mais próximo de 4/8/16 (excedentes removidos por ordem de entrada — últimos a aceitar saem).
- Mínimo de **4 participantes**.

### 8.5 Ligas de Pontos Corridos

**Pontuação por confronto direto:**

| Resultado | Pontos na classificação |
|---|---|
| Vitória | +3 pontos |
| Empate (mesma pontuação exata) | +1 ponto |
| Derrota | 0 pontos |

**Critérios de desempate no ranking:**
1. Número de vitórias nas disputas diretas
2. Melhor pontuação total de escalação nas rodadas da liga
3. Saldo de pontos de classificação
4. Antiguidade no Cartola

- Sempre contabiliza pontuação 1,5× do capitão.
- Requer número **par** de participantes (se ímpar, o time oficial do Cartola é incluído).
- Liga excluída se não atingir mínimo de **3 participantes** no fechamento do mercado.
- **Não é possível** sair, excluir membros ou encerrar a liga após o sorteio.

### 8.6 Ligas Oficiais do Cartola

| Liga | Descrição |
|---|---|
| **Liga Nacional** | Todos os cartoleiros ordenados por pontos |
| **Liga do Patrimônio** | Classificação por riqueza (patrimônio total) |
| **Liga do Capitão** | Apenas pontuação do capitão ao longo das rodadas |
| **Liga PRO** | Exclusiva para assinantes PRO |
| **Ligas de Patrocinadores** | Automáticas com base nos patrocinadores do time |

Ligas oficiais **não contam** para o limite de ligas do cartoleiro.

### 8.7 Limites de Ligas

| Tipo | FREE | PRO |
|---|---|---|
| Clássicas | 1 | 10 |
| Pontos Corridos | 3 | 10 |
| Mata-Mata | 5 | 10 |
| Atletas favoritos | 5 | 20 |

---

## 9. Níveis Mensais

### 9.1 Classificação

Os cartoleiros são classificados em **11 níveis** com base na performance mensal:

| Nível | Faixa | % dos cartoleiros ativos |
|---|---|---|
| **Inicial** | Pontuação ≤ 0 | — |
| **Bronze I** | Faixa inferior | 45% (divididos entre I, II e III) |
| **Bronze II** | Faixa média | ↑ |
| **Bronze III** | Faixa superior | ↑ |
| **Prata I** | Faixa inferior | 35% (divididos entre I, II e III) |
| **Prata II** | Faixa média | ↑ |
| **Prata III** | Faixa superior | ↑ |
| **Ouro I** | Faixa inferior | 19% (divididos entre I, II e III) |
| **Ouro II** | Faixa média | ↑ |
| **Ouro III** | Faixa superior | ↑ |
| **Diamante** | Top | 1% |

### 9.2 Regras dos Níveis

- **Início:** Todos começam no nível Inicial.
- **Rodada → Mês:** O mês da rodada é determinado pela data da **primeira partida**.
- **Resultados:** Divulgados ao fim da última rodada do mês (na abertura do mercado seguinte).
- **Classificação exibida:** Durante todo o mês, exibe-se o nível do **mês anterior**.
- **Progressão não linear:** A variação entre meses não é progressiva (pode pular de Bronze para Ouro).
- **Sem restrições:** Não há limitação de interação entre cartoleiros de níveis diferentes.

---

## 10. Premiação — Temporada 2026

### 10.1 Liga Premiada Mensal 2026

Premiação mensal para o **1º lugar** de cada nível:

#### Prêmios FREE

| Nível | Prêmio |
|---|---|
| 1º Diamante FREE | R$ 6.000 |
| 1º Ouro FREE | R$ 4.000 |
| 1º Prata FREE | R$ 2.000 |
| 1º Bronze FREE | R$ 1.000 |

#### Prêmios PRO

| Nível | Prêmio |
|---|---|
| 1º Diamante PRO | R$ 6.000 |
| 1º Ouro PRO | R$ 4.000 |
| 1º Prata PRO | R$ 2.000 |
| 1º Bronze PRO | R$ 1.000 |

> Cartoleiros PRO **também podem** participar das ligas FREE.

**Elegibilidade:**
- Maior de 18 anos e residente no Brasil.
- Aceitar o Regulamento da Liga Premiada.
- Fornecer CPF e celular na Conta Globo.
- Inscrição até **28 de outubro de 2026**.

**Meses sem premiação:** Janeiro, Junho (Copa do Mundo) e Dezembro.

### 10.2 Campeonato Brasileiro de Cartola 2026

**Prêmio:** R$ 500.000 para o campeão.

#### Fases

| Fase | Formato | Rodadas | Classificação |
|---|---|---|---|
| **Fase 1** | Pontos Corridos (grupos de 10) | 2ª a 19ª | Top 2 de cada grupo avançam |
| **Fase 2** | Liga Clássica | 20ª a 34ª | Top 16 no ranking avançam |
| **Fase 3** | Mata-Mata (16 jogadores) | 35ª a 38ª | Eliminatória até a final |

**Elegibilidade:** mesma da Liga Premiada Mensal. Inscrição até **03/02/2026**.

---

## 11. Cartola FREE vs PRO

| Funcionalidade | FREE | PRO |
|---|---|---|
| Premiação mensal (ligas FREE) | ✅ | ✅ |
| Premiação mensal (ligas PRO exclusivas) | ❌ | ✅ |
| Ligas Clássicas | 1 | 10 |
| Ligas Pontos Corridos | 3 | 10 |
| Ligas Mata-Mata | 5 | 10 |
| Atletas Favoritos | 5 | 20 |
| Mínimo p/ valorizar + valorização nas parciais | ❌ | ✅ |
| Central do PRO (dados exclusivos) | ❌ | ✅ |
| Painel de Dados (Gato Mestre) | ❌ | ✅ |
| Análises exclusivas do Gato Mestre | ❌ | ✅ |
| Análises do assistente de escalação | 2 créditos/temporada | Ilimitado |
| Super Cards de desempenho | ❌ | ✅ |
| Customização exclusiva (escudos/ligas) | ❌ | ✅ |
| Sem publicidade | ❌ | ✅ |

---

## 12. Assistente de Escalação — Gato Mestre

### 12.1 Estratégias

| Estratégia | Objetivo | Fatores Considerados |
|---|---|---|
| **Quero Pontuar** | Maximizar pontuação | Média de scouts, pontos cedidos/conquistados do time, análise do confronto |
| **Quero Valorizar** | Acumular patrimônio | Média de pontos, potencial de pontos, mínimo para valorizar |

- O assistente **avalia** os atletas individualmente — **não recomenda** escalação nem sugere time ideal.
- Para dados atualizados, é necessário gerar uma nova análise a cada rodada.

### 12.2 Reação do Gato Mestre para Valorização

Indicador que sugere a **tendência de valorização** do atleta com base em performance e comportamento do mercado.

### 12.3 Previsão de Pontos

Estimativa de pontuação para a próxima rodada, considerando estatísticas e contexto do jogo.

---

## 13. Mapeamento API-Football → Scouts do Cartola

> Referência técnica para o motor de pontuação do CartolaAI.

| Scout Cartola | Código | Pts | Campo API-Football (api-sports.io) | Cálculo |
|---|---|---|---|---|
| Gol | `G` | +8.0 | `goals.total` | Direto |
| Assistência | `A` | +5.0 | `goals.assists` | Direto |
| Finalização na trave | `FT` | +3.0 | — | ⚠️ Não disponível diretamente. Pode ser inferido parcialmente. |
| Finalização defendida | `FD` | +1.2 | `shots.on` - `goals.total` | Calculado: finalizações no gol que não resultaram em gol |
| Pênalti sofrido | `PS` | +1.0 | `penalty.won` | Direto |
| Finalização pra fora | `FF` | +0.8 | `shots.total` - `shots.on` | Calculado: total de finalizações menos as no gol |
| Falta sofrida | `FS` | +0.5 | `fouls.drawn` | Direto |
| Impedimento | `I` | -0.1 | `offsides` | Direto |
| Pênalti perdido | `PP` | -4.0 | `penalty.missed` | Direto |
| Defesa de pênalti | `DP` | +7.0 | `penalty.saved` | Direto (goleiros) |
| Jogo sem sofrer gols | `SG` | +5.0 | `goals.conceded == 0` | Calculado a partir do placar da partida |
| Desarme | `DS` | +1.5 | `tackles.total` | Direto |
| Defesa (goleiro) | `DE` | +1.3 | `goals.saves` | Direto (goleiros) |
| Falta cometida | `FC` | -0.3 | `fouls.committed` | Direto |
| Cartão amarelo | `CA` | -1.0 | `cards.yellow` | Direto |
| Gol sofrido | `GS` | -1.0 | Placar da partida (goals against) | Calculado a partir do placar |
| Pênalti cometido | `PC` | -1.0 | `penalty.commited` | Direto |
| Cartão vermelho | `CV` | -3.0 | `cards.red` | Direto |
| Gol contra | `GC` | -3.0 | — | ⚠️ Não disponível diretamente na API. Requer cruzamento com eventos da partida. |

### Cobertura

- ✅ **15 de 20 scouts** disponíveis diretamente ou por cálculo simples.
- ⚠️ **2 scouts** (`FT` — Finalização na trave, `GC` — Gol contra) requerem dados de eventos da partida ou não estão disponíveis de forma granular.
- 📊 **Dados extras** disponíveis na API (não usados no Cartola, mas úteis para inteligência avançada): `passes.total`, `passes.key`, `passes.accuracy`, `dribbles.success`, `duels.won`, `games.rating`.

---

## 14. Glossário

| Termo | Definição |
|---|---|
| **Cartoleta (C$)** | Moeda virtual do Cartola |
| **Scout** | Ação de um jogador em campo que gera pontuação |
| **Patrimônio** | Valor total do time + cartoletas em caixa |
| **Valorização** | Aumento no preço de um jogador após a rodada |
| **Desvalorização** | Diminuição no preço de um jogador após a rodada |
| **Mínimo para valorizar** | Estimativa da pontuação necessária para o jogador começar a valorizar |
| **Gato Mestre** | Assistente de inteligência do Cartola (dicas e estatísticas) |
| **Parcial** | Pontuação em tempo real durante a rodada |
| **Mercado** | Período em que é possível escalar o time |
| **WO (Walkover)** | Vitória automática quando o adversário está inativo |
