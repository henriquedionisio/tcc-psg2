# Avaliação de Variabilidade em Large Language Models por meio de Digital Twins Conversacionais

**Autor:** Henrique Costa Dionísio  
**Orientadora:** Profa. Dra. Sarajane Marques Peres  
**Instituição:** EACH-USP — Graduação em Sistemas de Informação  
**Disciplina:** ACH2018 — Projeto Supervisionado ou de Graduação II  
**Ano:** 2026

---

## Resumo

Grandes modelos de linguagem (LLMs) apresentam natureza estocástica: pequenas mudanças nos parâmetros de decodificação ou na engenharia de prompt podem alterar significativamente as respostas geradas. Este trabalho propõe e valida uma prova de conceito (POC) de Digital Twins conversacionais com fork controlado para avaliar sistematicamente essa variabilidade. O sistema duplica diálogos em pontos específicos da conversa, aplica perturbações controladas (variação de `temperature`/`top-p` e níveis de engenharia de prompt) e compara os resultados por meio de métricas modulares, incluindo contagem de tokens, turnos, resolução e LLM-as-a-Judge. Os experimentos foram conduzidos com OpenAI GPT-4o-mini sobre quatro conversas multi-turno categorizadas (factual, criativa, instrucional e contextual). Os resultados da POC real (experimento #3, 64 twins, US$ 0,09) indicam que prompts simples obtiveram maior factualidade (5,0 vs. 4,33 do complexo), porém consomem menos tokens; forks tardios (turno 6) apresentaram maior robustez (3,5 vs. 2,0 no turno 3). A abordagem de Digital Twin mostrou-se viável como mecanismo de avaliação observacional, embora limitada pela ausência de usuários reais e pela escala reduzida imposta pelo orçamento experimental.

**Palavras-chave:** Large Language Models, Digital Twins, Avaliação de IA Generativa, Experimentação Controlada, Engenharia de Prompt.

---

## 1. Introdução

A adoção de LLMs em aplicações produtivas — chatbots, assistentes de código, análise de documentos — amplia a necessidade de mecanismos robustos de monitoramento e avaliação. Um desafio central é a natureza estocástica desses modelos: a mesma pergunta pode gerar respostas diferentes dependendo dos parâmetros de decodificação (`temperature`, `top-p`) e do contexto acumulado da conversa.

Os métodos de avaliação predominantes utilizam benchmarks estáticos, insuficientes para capturar riscos que emergem em uso real, como erros factuais, inconsistências e desvios de diretrizes institucionais.

Este trabalho investiga o paradigma de **Digital Twins** aplicado a conversas com LLMs: a criação de cópias computacionais de diálogos que permitem aplicar perturbações controladas sem interferir no sistema original. O objetivo é fornecer evidências empíricas preliminares sobre o impacto de parâmetros de decodificação e engenharia de prompt na variabilidade das respostas.

### 1.1 Objetivos

**Objetivo geral:** Avaliar sistematicamente o impacto dos parâmetros `temperature`, `top-p`, turno do fork e engenharia de prompt na variabilidade das respostas de LLMs utilizando Digital Twins conversacionais.

**Objetivos específicos:**
- Definir métricas qualitativas e quantitativas para análise comparativa
- Conduzir experimentação controlada com subset de Grid Search e variação de prompts
- Analisar padrões de variabilidade e identificar configurações mais adequadas por contexto
- Validar a viabilidade metodológica da abordagem de Digital Twin

---

## 2. Fundamentação Teórica

### 2.1 Large Language Models e Estocasticidade

LLMs baseados em arquitetura Transformer geram texto de forma autoregressiva, selecionando tokens a partir de distribuições de probabilidade. Os parâmetros `temperature` e `top-p` (nucleus sampling) controlam a aleatoriedade dessa seleção: valores baixos produzem respostas mais determinísticas; valores altos aumentam criatividade e variabilidade (Brown et al., 2020; Zhao et al., 2023).

### 2.2 Avaliação de LLMs

A literatura de avaliação de LLMs (Chang et al., 2024) distingue benchmarks automáticos, avaliação humana e LLM-as-a-Judge. Este trabalho combina métricas automáticas (tokens, turnos) com avaliação por judge para factualidade, robustez e adequação institucional.

### 2.3 Digital Twins

Originalmente desenvolvido para sistemas ciberfísicos (Grieves, 2019; Fuller et al., 2020), o conceito de Digital Twin consiste em uma réplica computacional de um sistema real para monitoramento e simulação. Aplicações recentes exploram LLMs como componentes internos de twins (Xia et al., 2024; Yang et al., 2025), mas o uso do twin como observador de interações reais com LLMs permanece incipiente.

---

## 3. Metodologia

### 3.1 Arquitetura do Sistema

O sistema foi implementado em Python com FastAPI, SQLModel/SQLite, LangChain e OpenAI. Os componentes principais são:

1. **Fork Engine** — Duplica o histórico conversacional até um turno N
2. **Twin Runner** — Cria branches com perturbações distintas
3. **User Simulator** — LLM que simula o usuário humano pós-fork
4. **Metrics Module** — Avaliação modular e plugável
5. **Experiment Runner** — Orquestração da POC via CLI

### 3.2 Protocolo Experimental

| Dimensão | Configuração |
|---|---|
| Conversas | 4 (factual, criativa, instrucional, contextual) |
| Turnos seed | 3 mensagens iniciais fixas por conversa |
| Pontos de fork | Turnos 3 e 6 |
| Twins por fork | 8 (1 controle + 3 prompt + 4 parâmetros) |
| Turnos pós-fork | Máximo 5 |
| Modelo | gpt-4o-mini |
| Orçamento | ~US$ 10 |

**Twins de prompt** (temperature=0.7, top_p=1.0):
- Simples: instrução mínima
- Médio: diretrizes estruturadas
- Complexo: rubrica detalhada com restrições

**Twins de parâmetros** (prompt baseline):
- (0.0, 1.0) determinístico
- (0.7, 1.0) baseline
- (1.0, 0.4) alta temperatura, nucleus restrito
- (1.0, 1.0) máxima variabilidade

### 3.3 Simulador de Usuário

Dado que twins digitais não possuem interlocutor humano, um LLM simula o usuário com persona e objetivo fixos por conversa. Esta é uma limitação metodológica reconhecida: o simulador é um proxy, não um substituto de comportamento humano real.

### 3.4 Métricas

| Métrica | Tipo | Descrição |
|---|---|---|
| Tokens | Automática | Consumo total de tokens por twin |
| Turnos | Automática | Turnos pós-fork até resolução ou limite |
| Resolução | Judge | Conversa atingiu o objetivo? |
| Factualidade | Judge (1-5) | Precisão e ausência de alucinações |
| Robustez | Judge (1-5) | Consistência vs. twin controle |
| Adequação institucional | Judge (1-5) | Conformidade com diretrizes (contextual/instrucional) |

Todas as rubricas de judge estão publicadas em `prompts/judge_*.txt`.

---

## 4. Implementação

### 4.1 Tecnologias

- Python 3.9+, FastAPI, SQLModel, SQLite
- LangChain + langchain-openai
- Rich + Typer (CLI)
- pandas + matplotlib (análise)

### 4.2 Estrutura de Dados

- **Conversation** — Metadados e objetivo do diálogo
- **Message** — Mensagens com turno, role e contagem de tokens
- **Twin** — Branch com tipo, parâmetros e prompt
- **ExperimentRun** — Execução com custo e status
- **MetricResult** — Resultado de cada métrica por twin

### 4.3 Controle de Custos

O runner impõe limites de turnos (5), tokens por resposta (500) e orçamento total (US$ 10), registrando custo estimado em `data/cost_log.json`.

---

## 5. Resultados

### 5.1 Volume Experimental (Experimento #3 — POC real)

A POC completa foi executada em 11/06/2026 com OpenAI `gpt-4o-mini`. Configuração: 4 conversas × 2 forks (turnos 3 e 6) × 8 twins = **64 twins**, cada um com até 5 turnos pós-fork.

| Métrica | Valor |
|---|---|
| Chamadas à API | 730 |
| Tokens consumidos | 411.458 |
| Custo estimado | US$ 0,09 |
| Tempo de execução | ~25 minutos |
| Twins por tipo | 8 controle, 24 prompt, 32 parâmetros |

Dataset exportado em `data/exports/results_exp_3.csv`. Gráficos em `data/exports/charts/*_exp_3.png`.

### 5.2 Análise dos Resultados

#### Consumo de tokens

| Tipo de twin | Tokens médios |
|---|---|
| Controle | 2.302 |
| Parâmetros | 1.934 |
| Prompt | 3.882 |

Twins com engenharia de prompt consomem mais tokens. Dentro desse grupo, prompt **complexo** (4.797) e **médio** (4.390) gastam quase o dobro do **simples** (2.460), indicando trade-off entre detalhamento e custo.

#### Factualidade (LLM-as-a-Judge, escala 1–5)

| Nível de prompt | Score médio |
|---|---|
| Simples | 5,00 |
| Médio | 4,50 |
| Complexo | 4,33 |
| **Geral** | **4,72** |

Por categoria de conversa: contextual (4,88), factual (4,75), criativa (4,67), instrucional (4,57).

#### Robustez vs. baseline (escala 1–5)

| Turno do fork | Score médio |
|---|---|
| Turno 3 | 2,00 |
| Turno 6 | 3,50 |
| **Geral** | **3,00** |

Forks mais tardios apresentam maior robustez na amostra avaliada, possivelmente por contexto mais acumulado estabilizar respostas. Parâmetros `temp=0.0` (determinístico) obtiveram robustez 3,5; `temp=0.7` (baseline) obteve 2,0 na amostra com judge.

#### Resolução da conversa (judge)

| Tipo de twin | Taxa de resolução |
|---|---|
| Controle | 75% |
| Prompt | 67% |
| Parâmetros | 67% |

Apenas 23% dos twins encerraram por heurística de mensagem do simulador ("obrigado, resolveu"); o judge avaliou resolução de forma mais otimista.

#### Gráficos gerados

1. `tokens_by_type_exp_3.png` — consumo por tipo de twin
2. `factualidade_by_prompt_exp_3.png` — factualidade por nível de prompt
3. `robustez_by_params_exp_3.png` — robustez por combinação de parâmetros
4. `robustez_by_fork_turn_exp_3.png` — efeito do momento do fork
5. `resolution_by_type_exp_3.png` — taxa de resolução por tipo

### 5.3 Recomendações Preliminares (baseadas nos dados)

| Contexto | Configuração sugerida | Evidência |
|---|---|---|
| Diálogos factuais | Prompt simples ou médio + temp≤0.7 | Maior factualidade com prompt simples (5,0) |
| Diálogos criativos | Prompt médio + temp=0.7–1.0 | Equilíbrio custo/qualidade |
| Diálogos instrucionais | Prompt médio + temp=0.7 | Factualidade 4,57; evitar prompt complexo pelo custo |
| Diálogos institucionais | Prompt médio + temp≤0.7 | Maior factualidade na categoria contextual (4,88) |
| Controle de custo | Prompt simples | 2.460 tokens vs. 4.797 do complexo |

> **Nota:** Recomendações são preliminares. O judge foi aplicado em ~50% dos twins (amostragem para economia). Avaliação humana complementar é necessária.

---

## 6. Discussão

### 6.1 Validação da Abordagem

A POC demonstra que Digital Twins com fork controlado são viáveis para avaliação observacional de LLMs. O sistema permite comparar configurações de forma reproduzível e auditável, com prompts e rubricas publicáveis.

### 6.2 Limitações

1. **Ausência de usuário real** — O User Simulator introduz viés; resultados não refletem comportamento humano autêntico
2. **Escala reduzida** — 4 conversas e orçamento de US$ 10 limitam generalização
3. **Modelo único** — Apenas gpt-4o-mini foi testado; resultados podem diferir em outros modelos
4. **LLM-as-a-Judge** — O judge compartilha limitações dos LLMs (viés, inconsistência)
5. **Simulador, não produção** — O sistema é um ambiente experimental, não validação em uso real
6. **Estocasticidade residual** — Mesmo o twin controle pode variar entre execuções

### 6.3 Ameaças à Validade

- **Validade interna:** Perturbações são controladas, mas o simulador de usuário adiciona variável não controlada
- **Validade externa:** Conjunto de 4 conversas não representa diversidade de uso real
- **Validade de constructo:** Métricas de judge são proxies; avaliação humana seria necessária para confirmação

---

## 7. Conclusão

Este trabalho apresentou uma POC funcional de Digital Twins conversacionais para avaliação de variabilidade em LLMs. O sistema implementa fork controlado, múltiplos tipos de twins, simulador de usuário, métricas modulares e pipeline de análise reproduzível.

Os resultados preliminares sugerem que engenharia de prompt tem impacto comparável ou superior aos parâmetros de decodificação na qualidade das respostas, especialmente em diálogos factuais e institucionais. A abordagem mostrou-se promissora como base metodológica para avaliação não intrusiva de sistemas generativos.

### 7.1 Trabalhos Futuros

- Integração como módulo do sistema HarpIA
- Escala com conversas reais de usuários (com anonimização)
- Experimentação com múltiplos modelos (GPT, LLaMA, Gemini)
- Avaliação humana complementar ao LLM-as-a-Judge
- Simulação longitudinal com conversas estendidas
- Análise de logits em modelos abertos

---

## Referências

- BOMMASANI, R. et al. On the opportunities and risks of foundation models. arXiv:2108.07258, 2021.
- BROWN, T. B. et al. Language models are few-shot learners. NeurIPS, 2020.
- CHANG, Y. et al. A survey on evaluation of large language models. ACM TIST, 2024.
- FULLER, A. et al. Digital twin: Enabling technologies, challenges and open research. IEEE Access, 2020.
- GRIEVES, M. Virtually intelligent product systems: Digital and physical twins. Wiley, 2019.
- XIA, Y. et al. LLM experiments with simulation in digital twins. IEEE ETFA, 2024.
- YANG, L. et al. Leveraging LLMs for enhanced digital twin modeling. arXiv:2503.02167, 2025.
- ZHAO, W. X. et al. A survey of large language models. arXiv:2303.18223, 2023.

---

## Apêndice A — Reprodução do Experimento

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # adicionar OPENAI_API_KEY

# Experimento
python -m src.cli run-experiment experiments/poc_config.yaml --dry-run
python -m src.cli run-experiment experiments/poc_config.yaml

# Análise
python -m src.cli export-results
python analysis/generate_report.py
```

## Apêndice B — Prompts Publicáveis

Todos os prompts estão em `prompts/`:
- `system_baseline.txt`, `system_simple.txt`, `system_medium.txt`, `system_complex.txt`
- `user_simulator.txt`
- `judge_factualidade.txt`, `judge_robustez.txt`, `judge_resolucao.txt`, `judge_adequacao.txt`
