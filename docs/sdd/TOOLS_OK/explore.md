---
sdd: 1
feature: TOOLS_OK
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Regra curta no que o host injeta (CLAUDE.md e AGENTS.md): pergunta sobre artefato vai primeiro ao verbo (analyze_* e judge, ou o verbo de topo), e a resposta cita fact_id ou rule_id; tabela curta de tipo de pergunta para verbo. Medida por uma rodada da eval fase0."
    tradeoffs:
      - "o mais barato, e age no unico canal que se mediu chegando ao agente sem ser pedido"
      - "instrucao, nao garantia: o agente pode ignorar"
      - "CLAUDE.md tem teto de tamanho travado por tests/test_bootstrap_budget.py"
  - id: B
    summary: "A descricao de cada tool (carregada por ToolSearch) e de cada skill diz o que ela substitui, e o judge devolve texto curto com os ids."
    tradeoffs:
      - "age no ponto da escolha, em qualquer host"
      - "mexe em muitas descricoes, move superficie e espelhos"
      - "efeito incerto: no baseline o agente muitas vezes nem procura a tool"
  - id: C
    summary: "Hook PreToolUse (sparkforge.policy.hook) recusa Read de artefato que tem verbo (event log, plano, facts.json) e aponta o verbo."
    tradeoffs:
      - "o unico que garante o uso"
      - "so no Claude Code com o hook ligado; atrapalha quem quer ler de proposito"
      - "falta confirmar se a eval roda com os hooks do repositorio"
chosen: A
---

# TOOLS_OK — exploração

## Origem

Terceira das quatro features em que se decompôs a avaliação de 2026-09-17
(DATABRICKS_SPARK e DATABRICKS_PHOTON_PLAN já na `main`). O propósito escolhido pelo
operador: **resposta com prova** — o agente responde a partir do fact ou do finding,
citando `fact_id` ou `rule_id`, em vez de ler o artefato no olho. O acerto atual não
pode cair.

## Perfil

`dev`.

## Medidas lidas antes de propor

Baseline `evals/agentic/fase0/baselines/2026-09-16-haiku-4-5-lookup-busca`
(Haiku 4.5, 13 perguntas, 3 rodadas):

- Acerto 9 de 13 na primeira rodada, com `tools_ok` 3 de 13.
- Por pergunta, nas três rodadas: só `fase0-04` usa as tools exigidas nas 3;
  `fase0-01`, `02`, `05`, `09` pulam `analyze_pyspark`/`judge`; `fase0-06`, `07`, `10`
  pulam `rules_lookup` na maioria; `fase0-08` nunca chama `runtime_detect` nem
  `release_describe`; `abst-01` nunca chama `finops`; `abst-02` nunca chama
  `benchmark` nem `analyze_event_log`.
- Bytes de resultado de tool na primeira rodada: `Read` 380 039; todas as tools MCP
  do SparkForge juntas, cerca de 18 000.
- Medido antes (memória do projeto, 2026-09-15/16): `AGENT_PROTOCOL.md` aberto em 0
  de 39 sessões; trocar 103 por 9 tools não moveu o uso; o host difere os schemas das
  tools MCP e o agente as carrega por ToolSearch.

## Perguntas feitas, uma por vez

1. O que TOOLS_OK precisa melhorar? Resposta: resposta com prova.
2. Qual abordagem? Resposta: A.

## Escolha

A. Age no canal que as medidas mostram chegar ao agente, custa uma rodada da eval
para medir, e não restringe leitura legítima. Se `tools_ok` não subir, C fica
registrada como a feature seguinte, com a medida de A como baseline; B fica para
quando a descrição da tool for o gargalo medido.

## Em aberto para o define

- Se a regra entra no `CLAUDE.md`, no `AGENTS.md` ou nos dois, e quanto do teto de
  tamanho ela consome (`tests/test_bootstrap_budget.py`).
- Se `scripts/run_agentic_eval.py` copia o `CLAUDE.md`/`AGENTS.md` atuais para o
  workspace da eval (a nota do PR #73 diz que copia; conferir).
- O critério de "resposta com prova": o grader atual confere tools, não a citação
  de `fact_id`/`rule_id` na resposta.
- O limiar de sucesso de `tools_ok`, e como lidar com a variância entre rodadas
  (o baseline variou de 3 a 6 antes).
