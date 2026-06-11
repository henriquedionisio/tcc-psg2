# Apresentação de Andamento — TCC PSG2

**Aluno:** Henrique Costa Dionísio  
**Orientadora:** Profa. Dra. Sarajane Marques Peres  
**Data:** 11/06/2026  
**Disciplina:** ACH2018 — Projeto Supervisionado ou de Graduação II

---

## Introdução

### O problema

Modelos de linguagem (como o ChatGPT) são **imprevisíveis**: a mesma pergunta pode gerar respostas diferentes dependendo de configurações internas (`temperature`, `top-p`) ou de como o sistema é instruído (engenharia de prompt). Em aplicações reais — chatbots, assistentes institucionais, suporte — isso é um risco: uma resposta pode ser precisa e outra, não.

### O que este TCC propõe

Usar o conceito de **Digital Twin** (gêmeo digital): criar **cópias** de uma conversa real e testar variações de forma controlada, **sem afetar** o sistema original. A ideia é responder:

> *"Se eu mudar o prompt ou os parâmetros, a resposta fica melhor, pior ou igual — e quanto custa?"*

### O que já foi feito neste andamento

1. Reconstruí do zero o sistema experimental (o repositório original foi perdido)
2. Executei a **POC completa** com API real da OpenAI
3. Coletei **64 comparações** (twins), exportei dataset e gerei gráficos
4. Iniciei a monografia (`monografia/monografia.md`)

**Resultado principal:** a abordagem **funciona** e é **barata** (US$ 0,09 por 64 twins). Os dados preliminares sugerem que **prompt simples** teve melhor custo-benefício nesta amostra.

---

## Parte 1 — O que é o sistema (em linguagem simples)

Imagine que você tem uma conversa de chatbot e quer testar: *"e se eu mudasse a instrução do assistente?"* ou *"e se eu mudasse a aleatoriedade do modelo?"*

O sistema faz isso automaticamente:

1. **Você escreve** o começo da conversa (3 mensagens)
2. O sistema **copia** essa conversa em 8 versões (gêmeos)
3. Cada gêmeo tem uma **configuração diferente** (prompt ou parâmetro)
4. Um **robô-usuário** (outra IA) continua fazendo perguntas
5. O **assistente** (IA) responde em cada gêmeo
6. Um **robô-avaliador** (IA) dá nota nas respostas
7. Tudo vira **planilha e gráficos**

**Não há pessoa real conversando** após o início — são 3 papéis de IA: usuário simulado, assistente e avaliador.

---

## Parte 2 — Onde está cada coisa (arquivos)

| O quê | Onde | Para que serve |
|---|---|---|
| Conversas iniciais (perguntas que eu escrevi) | `experiments/conversations/*.yaml` | Roteiro fixo de cada teste |
| Configuração do experimento | `experiments/poc_config.yaml` | Quantos forks, limites, quais conversas |
| Instrução do assistente (4 níveis) | `prompts/system_*.txt` | Como o assistente deve responder |
| Instrução do robô-usuário | `prompts/user_simulator.txt` | Como gerar perguntas de acompanhamento |
| Instrução do avaliador | `prompts/judge_*.txt` | Como dar nota (factualidade, robustez...) |
| Código que executa tudo | `src/services/experiment.py` | Motor do experimento |
| Conversas geradas | `data/tcc.db` | Banco SQLite |
| Resultados tabulados | `data/exports/results_exp_3.csv` | Planilha para análise |
| Gráficos | `data/exports/charts/*_exp_3.png` | Visualizações |

**Comando usado:**
```bash
python -m src.cli run-experiment experiments/poc_config.yaml
```

---

## Parte 3 — As 4 conversas de teste

Cada arquivo YAML tem **objetivo + 3 mensagens fixas** (eu escrevi o começo):

| ID | Tipo | Objetivo | 1ª pergunta | 3ª pergunta (antes do fork) |
|---|---|---|---|---|
| C1 | Factual | Explicar ciclo da água | "Pode me explicar o ciclo da água?" | "Quais são as principais etapas?" |
| C2 | Criativa | Conto sci-fi em 3 atos | "Ajude a estruturar um conto em 3 atos" | "Lua saindo da órbita. Comece o Ato 1." |
| C3 | Instrucional | Plano de estudo Python | "Plano de Python para iniciante, 4 semanas" | "Detalhe a Semana 1" |
| C4 | Contextual | Matrícula e bolsas (tom institucional) | "Como funciona matrícula em universidade pública?" | "E bolsas para calouros?" |

---

## Parte 4 — O fluxo completo (passo a passo)

```
PASSO 1 — Carregar conversa do YAML → gravar no banco

PASSO 2 — FORK no turno 3 ou 6
          Copiar mensagens até aquele ponto
          Criar 8 gêmeos:

          ┌─ Controle (prompt baseline, temp=0.7)
          ├─ Prompt simples  (1 linha de instrução)
          ├─ Prompt médio    (instrução estruturada)
          ├─ Prompt complexo (rubrica longa)
          ├─ Param temp=0.0  (determinístico)
          ├─ Param temp=0.7  (baseline)
          ├─ Param temp=1.0, top_p=0.4
          └─ Param temp=1.0, top_p=1.0

PASSO 3 — Para cada gêmeo, repetir até 5 vezes:
          Robô-usuário pergunta → Assistente responde

PASSO 4 — Avaliador dá nota em cada gêmeo

PASSO 5 — Repetir para 4 conversas × 2 forks = 64 gêmeos
```

### Os 3 papéis de IA

| Papel | Arquivo | Enviado para |
|---|---|---|
| Assistente | `prompts/system_*.txt` | OpenAI (gera respostas) |
| Robô-usuário | `prompts/user_simulator.txt` | OpenAI (gera perguntas) |
| Avaliador | `prompts/judge_*.txt` | OpenAI (gera notas) |

O prompt baseline **não vai para uma pessoa** — é a instrução que a OpenAI usa para gerar respostas do assistente.

---

## Parte 5 — Números do experimento #3

| Métrica | Valor |
|---|---|
| Modelo | gpt-4o-mini (OpenAI) |
| Conversas | 4 |
| Forks por conversa | 2 (turnos 3 e 6) |
| Gêmeos por fork | 8 |
| **Total de gêmeos** | **64** |
| Chamadas à API | 730 |
| Tokens consumidos | 411.458 |
| **Custo** | **US$ 0,09** |
| Tempo | ~25 minutos |

---

## Parte 6 — Análise dos resultados (gráfico por gráfico)

### Gráfico 1 — Tokens médios por tipo de gêmeo

![Tokens](../data/exports/charts/tokens_by_type_exp_3.png)

**O que o gráfico mostra:** quanto cada tipo de gêmeo gastou de tokens (proxy de custo).

| Tipo | Tokens médios | O que significa |
|---|---|---|
| Controle | 2.302 | Referência — comportamento "normal" |
| Parâmetros | 1.934 | Levemente mais econômico que o controle |
| **Prompt** | **3.882** | **Quase 2× mais caro** que o controle |

**Análise:** mudar só os parâmetros (`temperature`/`top-p`) **não aumentou** o custo. Quem aumentou foi a **engenharia de prompt** — especialmente o prompt complexo (média de 4.797 tokens em alguns gêmeos, pico de 6.352).

**Exemplo concreto (C1, ciclo da água, mesmo fork):**
- Prompt simples: **525 tokens**, resolveu em 3 turnos
- Prompt complexo: **6.352 tokens**, não resolveu em 5 turnos
- Controle: 1.623 tokens, resolveu em 5 turnos

**Conclusão deste gráfico:** prompt complexo ≠ melhor; pode ser **muito mais caro** sem benefício claro.

---

### Gráfico 2 — Factualidade por nível de prompt

![Factualidade](../data/exports/charts/factualidade_by_prompt_exp_3.png)

**O que o gráfico mostra:** nota de factualidade (1–5) dada pelo avaliador (LLM-as-a-Judge), por nível de prompt.

| Prompt | Score médio | Amostras avaliadas |
|---|---|---|
| **Simples** | **5,0** | 1 |
| Médio | 4,5 | 4 |
| Complexo | 4,3 | 3 |

**Análise:** nesta amostra, o prompt **mais simples** teve a melhor factualidade. O prompt complexo, apesar de ter mais regras ("evite alucinações", "cite fontes"), **não superou** o simples.

**Trecho real do judge (twin controle, C1):**
```json
{"score": 5, "justification": "Descreve corretamente condensação e nuvens, sem erros factuais."}
```

**Conclusão deste gráfico:** mais instrução no prompt **não garantiu** mais factualidade nesta POC. Resultado preliminar — amostra pequena.

---

### Gráfico 3 — Robustez por combinação de parâmetros

![Robustez params](../data/exports/charts/robustez_by_params_exp_3.png)

**O que o gráfico mostra:** o quanto a resposta do gêmeo foi **parecida** com a do controle (escala 1–5; 5 = idêntica, 1 = muito diferente).

| Parâmetros | Score | Interpretação |
|---|---|---|
| Baseline (temp=0.7) | 2,0 | Resposta moderadamente diferente do controle |
| Determinístico (temp=0.0) | **3,5** | Mais parecida com o controle |
| Alta temp / Máxima variabilidade | *(sem dados)* | Judge não avaliou esses na amostra de 50% |

**Análise:** `temperature=0.0` (determinístico) produziu respostas **mais consistentes** com o baseline. Isso é esperado: menos aleatoriedade → menos variação.

**Trecho real do judge (robustez baixa, score 1/5):**
```json
{"score": 1, "justification": "Respostas substancialmente diferentes em conteúdo e conclusão."}
```

**Conclusão deste gráfico:** parâmetros importam para **consistência**. Determinístico = mais previsível. Amostra limitada para temp=1.0.

---

### Gráfico 4 — Robustez por turno do fork

![Robustez fork](../data/exports/charts/robustez_by_fork_turn_exp_3.png)

**O que o gráfico mostra:** robustez média conforme o **momento** em que o fork foi feito.

| Turno do fork | Score | Contexto acumulado |
|---|---|---|
| Turno 3 (início) | 2,0 | Pouco histórico (3 mensagens) |
| Turno 6 (meio) | **3,5** | Mais histórico (6 mensagens) |

**Análise:** forks mais tardios geraram respostas **mais parecidas** com o controle. Com mais contexto acumulado, os gêmeos tendem a convergir — a conversa já tem direção definida.

**Conclusão deste gráfico:** o **momento do fork importa**. Fork cedo = mais variabilidade. Fork tarde = mais estabilidade.

---

### Gráfico 5 — Taxa de resolução por tipo de gêmeo

![Resolução](../data/exports/charts/resolution_by_type_exp_3.png)

**O que o gráfico mostra:** percentual de gêmeos em que a conversa foi **encerrada** pelo robô-usuário dizendo *"Obrigado, isso resolve minha dúvida"* (heurística automática).

| Tipo | Taxa de resolução |
|---|---|
| Controle | **37,5%** (3 de 8) |
| Parâmetros | 25% (2 de 8) |
| Prompt | 16,7% (2 de 12) |

**Nota:** o avaliador (judge) foi mais otimista — deu taxa de resolução de 75% para controle, 67% para os demais. A diferença existe porque:
- **Heurística** = detecta a frase "obrigado, resolve minha dúvida" na mensagem
- **Judge** = avalia semanticamente se o objetivo foi atingido

**Análise:** o controle resolveu mais conversas dentro do limite de 5 turnos. Gêmeos com prompt complexo frequentemente **estouraram o limite** sem o robô-usuário encerrar — porque as respostas eram longas e a conversa demorou mais.

**Conclusão deste gráfico:** configuração afeta se a conversa **chega ao fim** dentro do limite. Prompts que geram respostas longas podem impedir resolução no tempo.

---

### Síntese da análise

| Pergunta do TCC | Resposta preliminar | Evidência |
|---|---|---|
| Prompt complexo melhora qualidade? | **Não nesta amostra** — simples teve factualidade 5,0 e custou menos | Gráficos 1 e 2 |
| Parâmetros mudam comportamento? | **Sim** — temp=0.0 mais consistente | Gráfico 3 |
| Momento do fork importa? | **Sim** — turno 6 mais robusto que turno 3 | Gráfico 4 |
| O sistema é viável? | **Sim** — 64 gêmeos por US$ 0,09 | Tabela de números |
| Digital Twin funciona? | **Sim** — pipeline completo executado | Todo o experimento |

---

## Parte 7 — Exemplo passo a passo (C1: ciclo da água)

Para fixar o entendimento, um exemplo completo:

### O que eu escrevi (YAML)

```
Turno 1 — Usuário:    "Pode me explicar o ciclo da água?"
Turno 2 — Assistente: "Envolve evaporação, condensação, precipitação..."
Turno 3 — Usuário:    "Quais são as principais etapas?"
```

### Fork no turno 3 → 8 gêmeos criados

### Gêmeo CONTROLE (referência)

- **Prompt:** `system_baseline.txt` → *"Seja útil, preciso e objetivo"*
- **Parâmetros:** temp=0.7, top_p=1.0

**O que a IA gerou (real):**
```
Turno 4 — Robô-usuário:  "Como acontece a evaporação na natureza?"
Turno 5 — Assistente:    [explicação sobre evaporação]
Turno 6 — Robô-usuário:  "Como a água se transforma em vapor?"
...
Final   — Robô-usuário:  "Obrigado, isso resolve minha dúvida."
```

**Resultado:** 1.623 tokens · resolvido · factualidade **5/5**

### Gêmeo PROMPT SIMPLES (mesma conversa, prompt diferente)

- **Prompt:** `system_simple.txt` → *"Responda às perguntas do usuário."*

**O que a IA gerou (real):**
```
Turno 4 — Robô-usuário:  "Quais são as etapas do ciclo da água?"
Turno 5 — Assistente:    [lista: evaporação, transpiração, condensação...]
Turno 6 — Robô-usuário:  "Obrigado, isso resolve minha dúvida."
```

**Resultado:** **525 tokens** · resolvido em **3 turnos** (vs. 5 do controle)

### Gêmeo PROMPT COMPLEXO

- **Prompt:** `system_complex.txt` → rubrica de 20+ linhas

**Resultado:** **6.352 tokens** · **não resolvido** (estourou 5 turnos)

---

## Parte 8 — Conclusões para a reunião

### O que está pronto

- [x] Sistema funcional (código + prompts publicáveis)
- [x] POC executada com dados reais (experimento #3)
- [x] Dataset exportado (`results_exp_3.csv`)
- [x] 5 gráficos comparativos
- [x] Monografia em andamento

### O que os dados sugerem (preliminar)

1. **A abordagem Digital Twin é viável** para avaliar variabilidade de LLMs
2. **Prompt simples** teve melhor custo-benefício (menos tokens, factualidade igual ou superior)
3. **Parâmetro determinístico** (temp=0.0) gera respostas mais consistentes
4. **Fork tardio** (turno 6) reduz variabilidade entre gêmeos
5. **Custo é viável** para experimentos maiores (US$ 0,09 por 64 gêmeos)

### Limitações (honestas)

| Limitação | Impacto |
|---|---|
| Robô-usuário, não humano real | Perguntas podem não refletir comportamento real |
| 4 conversas de teste | Não generaliza para todos os cenários |
| Judge avaliou ~50% dos gêmeos | Alguns gráficos têm poucos dados |
| Seeds no banco contaminadas por teste mock anterior | Mensagens pós-fork são reais; início precisa ser re-rodado |
| Evidência preliminar | Requer validação humana complementar |

### Próximos passos

1. Limpar banco e **re-rodar** com seeds corretas dos YAMLs
2. Finalizar monografia com análise crítica
3. Validação humana em amostra dos resultados
4. Integração HarpIA (trabalho futuro, fora do escopo deste TCC)

---

## Parte 9 — Artefatos para consulta

| Arquivo | Conteúdo |
|---|---|
| `experiments/conversations/*.yaml` | Perguntas que eu escrevi |
| `prompts/` | Todos os prompts (publicáveis) |
| `data/exports/results_exp_3.csv` | Dataset com 64 gêmeos e métricas |
| `data/exports/charts/*_exp_3.png` | Gráficos analisados acima |
| `monografia/monografia.md` | Texto do TCC |

---

*Documento consolidado para apresentação de andamento — Experimento #3, 11/06/2026*
