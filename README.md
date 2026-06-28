# TCC PSG2 — Digital Twins Conversacionais para Avaliação de LLMs

Trabalho de Graduação: **Avaliação de Variabilidade em Large Language Models por meio de Digital Twins Conversacionais**.

Sistema experimental que duplica conversas em pontos controlados (fork), aplica perturbações em parâmetros de decodificação e engenharia de prompt, e avalia a variabilidade das respostas.

## Requisitos

- Python 3.9+
- Chave de API OpenAI

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env com sua OPENAI_API_KEY
```

## Uso

### Iniciar API

```bash
uvicorn src.main:app --reload
```

### Testar pipeline sem API (dados mock)

```bash
python -m src.cli seed-mock
python -m src.cli export-results
python analysis/generate_report.py
```

### Rodar experimento real (dry-run)

```bash
python -m src.cli run-experiment experiments/poc_config.yaml --dry-run
```

### Rodar POC completa

```bash
python -m src.cli run-experiment experiments/poc_config.yaml
```

### Rodar POC v2 (controle A/B + divergência atribuível)

```bash
# Recomendado: banco limpo para seeds corretas
rm -f data/tcc.db

# Teste reduzido
python -m src.cli run-experiment experiments/poc_v2_config.yaml --dry-run

# Execução completa — Fase 2 (8 conversas, 5 replicações, fork 3 e 6)
python -m src.cli run-experiment experiments/poc_v2_config.yaml

# Exportar resultados e amostra para revisão humana (~10%)
python -m src.cli export-results
python -m src.cli export-human-review --all-replications --sample-rate 0.10
python analysis/generate_report.py
```

A v2 adiciona **control_b** (réplica idêntica de **control_a**) para estimar ruído
intrínseco e calcula **divergência atribuível** = divergência total − ruído A/B.

**Fase 2:** 8 diálogos (4 simples + 4 com restrições), seeds até turno 6,
12 turnos pós-fork, 5 replicações, export `human_review_sample_*.csv`.

### Exportar resultados e gerar gráficos

```bash
python -m src.cli export-results
python analysis/generate_report.py
```

### Gerar a monografia (.docx)

```bash
# Gráficos usados na monografia + documento final no template EACH
python analysis/generate_monografia_charts.py
python analysis/build_monografia_final.py   # gera docs/monografia/monografia-final.docx
```

## Estrutura

- `src/` — API FastAPI, serviços de fork/LLM, métricas e CLI
- `prompts/` — Prompts publicáveis (system, user simulator, judge)
- `experiments/` — Conversas seed e configuração da POC
- `data/` — Banco SQLite, exports e log de custos
- `analysis/` — Scripts de análise e gráficos
- `docs/` — Documentação do TCC: monografia (`docs/monografia/`), relatórios (`docs/relatorios/`), plano de atividades e relatório de andamento

## Experimento POC

- 4 conversas (factual, criativa, instrucional, contextual)
- 2 pontos de fork por conversa (turnos 3 e 6)
- 9 twins por fork (v2): 1 controle A + 1 réplica B + 3 prompt + 4 parâmetros
- 8 twins por fork (v1): sem réplica B (`include_control_replicate: false`)
- Métricas: tokens, turnos, resolução, LLM-as-Judge

## Orçamento

Limite padrão: US$ 10. O runner registra custo estimado em `data/cost_log.json`.
