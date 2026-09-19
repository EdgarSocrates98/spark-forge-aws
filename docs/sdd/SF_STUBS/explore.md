---
sdd: 1
feature: SF_STUBS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Apagar o oco. Saem os 19 agentes sf-* cujas rule_areas sao todas areas de coordenacao, os 35 rules/catalog/agentic-sf-*.yaml e as 45 rotas de routing.yaml que apontam para esses agentes ou para essas areas. Os 11 sf-* que declaram area executavel ficam, sem as areas ocas. As 10 tools e as skills com conteudo que so os ocos alcancam sao realocadas num coordenador que fica; skill sem artefato coletavel sai junto."
    tradeoffs:
      - "o catalogo passa a ter so regra que julga: 192 viram 157, e o numero publicado para de contar area que nunca dispara"
      - "nenhuma area executavel fica sem coordenador: os ocos nao declaram nenhuma"
      - "move muitos registros de uma vez: espelhos .agents/.codex/.github, routing, surface lock, referencia gerada, STATUS e README"
      - "dominio apagado (Airflow, DynamoDB, Kinesis, Lambda, Step Functions) volta so por artefato, e isso e a feature CRITERIO_DE_DOMINIO"
  - id: B
    summary: "Religar. Cada agente oco cujo dominio ja tem regra executavel em outra area passa a declarar essa area (athena->SF-ATH, iceberg->SF-ICE, parquet->SF-PQ, functional-rules->SF-FVAL, cost-reviewer->SF-WASTE); so os sem artefato nenhum sao apagados, e as 35 areas ocas saem do catalogo."
    tradeoffs:
      - "preserva os pontos de entrada __agentic_*__ de quem ja os usa"
      - "cria dois coordenadores por area (sf-athena-specialist e athena-query-optimizer para SF-ATH, e assim por diante): duplicacao que o roteador resolve escolhendo um, e o outro vira nome sem uso"
      - "o agente religado continua com 40 a 55 palavras de corpo generico: religar nao o preenche"
  - id: C
    summary: "Preencher. Os 30 agentes ficam; os 19 ocos ganham corpo com procedimento que cita tools reais, e as 35 areas ficam como executable: false com um campo novo dizendo que coleta as destravaria."
    tradeoffs:
      - "nao apaga nada, e registra no catalogo o backlog de dominios"
      - "a camada continua sem julgar: area que nao dispara segue contada no catalogo"
      - "o campo de destrave e o criterio de dominio, e escreve-lo aqui adianta a feature CRITERIO_DE_DOMINIO sem o gate dela"
chosen: A
---

# SF_STUBS — exploração

## Origem

Quarta frente da avaliação de `prompt_evo_debate_gpt_possivel_futuro.md` (fora do
git), de 2026-09-17: a camada `sf-*`/`agentic-sf-*` nasceu no commit `308fa4dd`
("agentic platform v2") como nomes de domínio sem artefato. Pedido do operador em
2026-09-19: "preencher ou apagar".

## Perfil

`dev`.

## Medidas (2026-09-19, `main` em `91643841`)

- `rules/catalog/agentic-sf-*.yaml`: 35 arquivos, **1 regra cada, 0 executáveis, 0 com
  `sources`**. Todas `executable: false`, `when: {all: []}`. `sparkforge/rules/loader.py`
  chama isso de "área de coordenação": ela nunca produz finding.
- `agents/sf-*.md`: 30 coordenadores. **11** declaram ao menos uma área executável
  (`sf-orchestrator`, `sf-pyspark-specialist`, `sf-runtime-specialist`,
  `sf-storage-specialist`, `sf-lake-formation-specialist`, `sf-security-reviewer`,
  `sf-terraform-specialist`, `sf-graph-specialist`, `sf-neptune-specialist`,
  `sf-analytics-specialist`, `sf-token-verifier`). **19** só declaram áreas ocas, e 16
  desses têm corpo de 39 a 57 palavras, o mesmo texto genérico.
- `rules/catalog/routing.yaml`: **45** rotas recomendam um dos 19. As que disparam por
  `findings_area` de área oca (AGENT-031 a AGENT-065) nunca casam, porque a área não
  produz finding. As `__agentic_*__` só casam se alguém puser a string em
  `scope.entrypoints`; nenhum código do pacote a põe.
- Apagar os 19 hoje deixaria órfãs, pelo `tests/test_agent_coverage.py`: as 9 tools
  `sparkforge_code_*` (só `sf-context-engineer` as cita) e
  `sparkforge_iceberg_assess_upgrade` (só `sf-iceberg-specialist`). E 12 skills só são
  declaradas por ocos: `analyze-functional-rules`, `design-agent-systems`,
  `design-airflow-pipelines`, `design-dynamodb-model`, `design-lambda-serverless`,
  `design-step-functions-orchestration`, `engineer-agent-context`,
  `engineer-agent-memory`, `iceberg-v3-readiness`, `optimize-athena-queries`,
  `optimize-iceberg-tables`, `verify-agent-evidence`.
- Nenhuma área executável deixa de ter coordenador se os 19 saírem: eles não declaram
  nenhuma.

## Perguntas feitas

1. Preencher ou apagar? O operador pediu que as duas saídas fossem avaliadas e que as
   duas frentes restantes corressem em sequência.
2. Qual abordagem? Resposta (2026-09-19): A, apagar o oco.

## Abordagens

A (recomendada) apaga o que não julga nada e realoca o que tem conteúdo. B mantém nomes
que duplicam coordenadores clássicos e não os preenche. C conserva a camada inteira e
adianta, sem gate, o critério que é a próxima feature.

## Escolha

A, escolhida pelo operador. Ela é a única das três em que o catálogo passa a conter
só regra que julga, e a que não duplica coordenador. O que tem conteúdo (tools, skills
de Athena, Iceberg e funcval) muda de dono em vez de sair. Os domínios que saem sem
artefato voltam pela feature CRITERIO_DE_DOMINIO, que vem em seguida.
