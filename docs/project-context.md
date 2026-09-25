# Contexto do Projeto: CartolaAI 🚀

Este documento serve como a **memória principal e o diário de bordo** do projeto CartolaAI. Ele descreve a visão geral, as decisões matemáticas e arquiteturais tomadas até o momento, e o roteiro para o futuro.

---

## 1. A Ideia do Projeto
O **CartolaAI** é um sistema preditivo e um motor de inteligência artificial desenhado para dominar o *Cartola FC*. Ao invés de depender de "achismos" ou de dicas de influenciadores, o sistema consome dados brutos reais (da *API-Football / api-sports.io* e da *API Oficial do Cartola*), traduz essas estatísticas de campo para os *Scouts do Cartola*, e utiliza matemática avançada (Machine Learning, Estatística Bayesiana) para calcular o **Expected Score Contextual (ESC)** de cada jogador. 

O objetivo final é entregar a escalação matematicamente perfeita para cada rodada, superando a média de 80 a 100 pontos consistentemente e vencendo ligas.

---

## 2. O Que Já Fizemos Até Aqui (E o Por Quê)

### 2.1. Arquitetura de Dados e Sincronização
* **Modelagem Completa:** Criamos tabelas para Jogadores, Partidas (Fixtures), Perfis de Times, Scouts e Histórico de Temporada.
* **Mapeamento de Scouts:** Traduzimos as estatísticas da API europeia (chutes, desarmes, defesas) para a linguagem exata do Cartola (G, A, SG, DP, etc).
* **Filtro Anti-Zika (Status Oficial):** Como a API de estatísticas mundiais não sabe quem será poupado no Brasil na sexta-feira, criamos um sincronizador que bate diretamente na **API Oficial da Globo (`/mercado`)**. 
  * *Por quê?* Para mapear quem está "Provável", "Dúvida" ou "Suspenso" e puxar o **Preço (Cartoletas)** real do jogador. Isso blinda o algoritmo de escalar jogadores que não vão jogar.

### 2.2. O Motor de Pontuação (A Ciência de Dados)
Aplicamos teses estatísticas avançadas para fugir das "médias burras":
* **Média Móvel Exponencial (EMA):** Substituímos a média simples pela EMA.
  * *Por quê?* Ela resolve o Paradoxo do Momentum vs Histórico. Dá um peso muito maior aos jogos recentes (fase atual), mas não esquece totalmente o histórico a longo prazo.
* **Priori Bayesiana e o "Cold Start Problem":** Criamos a tabela `PlayerSeasonHistory` para guardar o histórico da temporada anterior. 
  * *Por quê?* Para o algoritmo não ficar "cego" nas rodadas 1 a 5. A IA funde a nota da pré-temporada (Estaduais) com a nota histórica do jogador.
* **Coeficiente de Dificuldade da Liga (LDC):** 
  * *Por quê?* Se um time sobe da Série B, as notas de seus jogadores estão infladas. O sistema aplica um "fator de desconto" (ex: 0.7) nessas notas para refletir a dificuldade da Série A.
* **Decaimento Dinâmico (Regra Viveros):**
  * *Por quê?* Se um jogador veio da Série B (LDC < 1.0), mas amassa nas primeiras rodadas da Série A, a IA descarta a punição histórica dele rapidamente (em apenas 3 jogos), permitindo surfar a onda de jogadores revelação sem que o passado ruim/fraco os prenda.

### 2.3. Simulador de Regras Oficiais
Criamos um Backtest robusto (`scratch_round_sim_v2.py`) que valida a eficácia do motor em rodadas passadas respeitando 100% o regulamento oficial:
* Seleciona os 11 titulares.
* Define o **Capitão** (maior ESC -> 1.5x pontos).
* Escolhe o **Técnico** (Time com maior expectativa coletiva + bônus de vitória).
* Escala **5 Reservas** respeitando a regra financeira (custar menos que o titular mais barato).
* Aplica a lógica do **Reserva de Luxo**.
* **Resultado:** Em testes cravou mais de 119 pontos, mitigando jogadores poupados inteligentemente.

---

## 3. Onde Queremos Chegar
Queremos transformar este motor de Backend em uma plataforma web completa (SaaS ou de uso pessoal avançado) com:
1. Um **Dashboard Visual** mostrando as previsões, scouts e histórico.
2. Um "Auto-Escalador" em um clique.
3. Ferramentas de análise preditiva (mostrar para o usuário *o porquê* a IA escolheu o jogador X sobre o Y de forma compreensível).

---

## 4. O Que Falta Definir / Próximos Passos (To-Do List)

Aqui estão as particularidades e decisões pendentes que precisaremos resolver no futuro:

### ⚙️ Integrações e API
* [ ] **Assinar a API paga (api-sports.io):** Fazer o teste de estresse e verificar se o plano pago supre todas as necessidades reais de velocidade e se os dados granulares (impedimentos, finalizações na trave, desarmes) chegam sem falhas.

### 🔄 Gestão de Temporadas (Season Rollover)
* [ ] **Rotina de Fim de Ano:** Definir como faremos a virada de temporada. Será um gatilho automático via *cronjob* em dezembro ou um painel manual de Admin onde você aperta um botão "Arquivar Temporada e Iniciar Pré-Temporada"?
* [ ] **Peso dos Estaduais:** Mapear os IDs das ligas dos estaduais (Paulista, Carioca) na API e definir o LDC de cada uma (ex: Paulistão = 0.6) para calibrar a IA para a Rodada 1.

### 👥 Geração de Times Específicos e Regras de Risco
* [ ] **Gestão de Risco do Capitão (A Regra do Piso Seguro):** Goleiros e defensores possuem alta variância (perdem 5 pontos de SG em um segundo). O algoritmo não pode escolher o Capitão baseado apenas no maior ESC puro. Precisamos implementar a fórmula de `Max(ESC - Desvio Padrão)` para escolher o Capitão. Isso garante que a braçadeira vá para a "Unanimidade" (atacantes/meias de volume) que possuem o maior "Piso" (menor chance de negativar).
* [ ] **Múltiplos Perfis de Escalação:** Não poderemos escalar sempre o time principal se o caixa (Cartoletas) for baixo. O algoritmo precisará de "Modos de Geração":
  * *Time Principal:* Foco 100% em pontuação máxima (Ignora preço).
  * *Time Valorização:* Foco matemático no "Mínimo para Valorizar" para gerar Cartoletas nas primeiras rodadas.
  * *Time Bom e Barato (Budget):* Otimização linear (Maior ESC dividido pelo Menor Preço) para quando o patrimônio estiver baixo.
  * *Time Alternativo/Ousado:* Foco em jogadores com alta variância e baixo índice de escolha (para tirar diferença em ligas no fim do ano).

### 🖥️ Frontend
* [ ] **Definir a Stack Visual:** Escolher se usaremos React, Vue.js, ou templates (Jinja2) para construir a tela de controle do usuário.
