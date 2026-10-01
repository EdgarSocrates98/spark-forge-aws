---
sdd: 1
feature: DATABRICKS_SPARK
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Declarar a plataforma databricks a partir do event log, com matriz Databricks Runtime -> Spark com fonte, auditoria das regras sem runtime_scope e recusa nomeada quando o plano tem operadores Photon."
    tradeoffs:
      - "prova o criterio de entrada por artefato com o menor codigo novo: o extrator de event log ja e Spark generico"
      - "troca julgamento errado silencioso por recusa nomeada onde o significado muda (Photon, defaults do runtime)"
      - "auditar as regras sem runtime_scope e trabalho manual e move goldens"
  - id: B
    summary: "So rotular: env.platform = databricks e matriz de runtime, sem auditoria de regra nem guarda para Photon."
    tradeoffs:
      - "o mais barato"
      - "remediacao escrita para Glue (worker type, DPU) chega a quem roda Databricks"
      - "a regra 18 fica cega para spark.sql.shuffle.partitions=auto e demais defaults do runtime"
  - id: C
    summary: "Adaptador completo: A mais coletores collect_databricks_* pela REST API (cluster, run, download do event log)."
    tradeoffs:
      - "fluxo ponta a ponta, igual ao do Glue"
      - "credencial, SDK e superficie nova (regra 26), com acesso a workspace ainda incerto"
      - "melhor como incremento seguinte, depois de A provar o reuso"
chosen: A
---

# DATABRICKS_SPARK — exploração

## Origem

A avaliação crítica de `prompt_evo_debate_gpt_possivel_futuro.md` (arquivo fora do
git) concluiu que a expansão do SparkForge para além de Glue/EMR deve entrar por
**artefato coletável**, não por nome de agente. A camada de amplitude que existe hoje
está oca: agentes `sf-*` de ~640 bytes e `rules/catalog/agentic-sf-*.yaml` com
`executable: false`, `when: all: []` e `sources: []`. Databricks é o domínio novo
mais barato porque roda Spark e reaproveita os extratores atuais.

O pedido original tinha quatro subsistemas independentes, decompostos em features
próprias: `DATABRICKS_SPARK` (esta), `CRITERIO_DE_DOMINIO`, `SF_STUBS` e `TOOLS_OK`.

## Perfil

`dev`: a mudança é no próprio SparkForge.

## Medidas lidas antes de propor

- Não existe código Databricks nem Delta em `sparkforge/` (busca por `databricks`,
  `_delta_log`, `delta lake`: zero arquivos `.py`).
- `sparkforge/facts/event_log.py::extract_event_log` lê o formato de listener do
  Spark e não depende de Glue.
- `sparkforge/facts/runtime_detect.py::_PLATFORM_KEYS` conhece `emr` e `glue`;
  `env.platform` conta plataformas observadas.
- No catálogo, 176 regras declaram `runtime_scope: {}`; 20 estão presas a `glue`
  e 7 a `spark`/`iceberg`.

## Perguntas feitas, uma por vez

1. Qual pedaço explorar primeiro? Resposta: Databricks.
2. Qual artefato é o primeiro incremento? Resposta: event log mais runtime
   (`_delta_log`, definição de job/cluster e billing em DBU ficam para depois).
3. Há workspace Databricks para gerar event log real? Resposta: talvez
   (Community/trial). Consequência: a base de teste são fixtures sintéticas
   montadas a partir de documentação com fonte; o log real, se vier, é validação
   local e nunca entra em arquivo.

## Abordagens

A (recomendada) declara a plataforma e protege a fronteira onde o significado
muda. B é A sem a fronteira. C é A mais coleta pela API.

Diferenças do Databricks que motivam a fronteira de A:

- **Photon**: operadores nativos no plano (`Photon*`) e métricas de task próprias;
  regra de plano pensada para a JVM pode julgar mal.
- **Defaults do runtime**, como `spark.sql.shuffle.partitions=auto`: pela regra 18,
  a versão muda o significado do número.
- **Remediação específica de AWS** nas regras sem `runtime_scope`.

## Escolha

A. Atende o critério de artefato com o menor código novo, e onde o SparkForge não
sabe julgar, recusa com nome em vez de julgar errado. C fica registrada como
incremento seguinte, condicionada a acesso a workspace.

## Em aberto para o define

- Qual propriedade do event log identifica a versão do Databricks Runtime; confirmar
  com fonte, não de memória.
- Qual fonte T1 sustenta a matriz Databricks Runtime -> Spark.
- Como sinalizar Photon a partir do event log (nome de operador no plano SQL ou
  propriedade de ambiente), com fonte.
- Critério da auditoria: o que torna uma remediação "específica de AWS".
