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

### Exportar resultados e gerar gráficos

```bash
python -m src.cli export-results
python analysis/generate_report.py
```

## Estrutura

- `src/` — API FastAPI, serviços de fork/LLM, métricas e CLI
- `prompts/` — Prompts publicáveis (system, user simulator, judge)
- `experiments/` — Conversas seed e configuração da POC
- `data/` — Banco SQLite, exports e log de custos
- `analysis/` — Scripts de análise e gráficos
- `monografia/` — Texto do TCC

## Experimento POC

- 4 conversas (factual, criativa, instrucional, contextual)
- 2 pontos de fork por conversa (turnos 3 e 6)
- 8 twins por fork: 1 controle + 3 prompt + 4 parâmetros
- Métricas: tokens, turnos, resolução, LLM-as-Judge

## Orçamento

Limite padrão: US$ 10. O runner registra custo estimado em `data/cost_log.json`.
