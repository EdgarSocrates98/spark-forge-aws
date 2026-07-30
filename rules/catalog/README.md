# Catálogo de regras — como ler e escrever

Este catálogo é a forma **executável** do conhecimento em `../../knowledge/`. A prosa lá explica *por quê*; aqui define *quando dispara*.

Definido por `docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md` §5.3.

## Por que YAML e não código

1. **Auditável.** Cada regra carrega `sources` com URL e data. Dá para responder "de onde veio esse limiar" meses depois.
2. **Versão-guardada.** `runtime_scope` impede aplicar propriedade Iceberg 1.10 num Glue 4.0.
3. **Portátil.** É o terceiro degrau da escada de degradação: um agente sem MCP e sem Python lê estes arquivos direto e aplica o mesmo limiar, com a mesma fonte. Paridade Devin ↔ Claude não depende do motor existir.
4. **Editável sem tocar Python.** Ajustar limiar é mudar dado.

## Estrutura de uma regra

```yaml
- id: SF-PY-004                    # SF-<AREA>-<NNN>, único no catálogo inteiro
  category: pyspark-code
  title: Action ou write dentro de loop
  requires_facts: [pyspark.loop]   # kinds de Fact necessários
  when:                            # predicado
    all:
      - fact: pyspark.loop
        where: {attrs.contains_action: true}
  status: structural               # structural | confirmed
  severity_default: P1             # P0..P4
  runtime_scope: {glue: "*"}
  explanation: >
    ...
  proposed_change: [...]
  risks: [...]
  tradeoffs: [...]
  validation: [...]
  rollback: [...]
  sources: [{url: ..., retrieved: 2026-07-29}]
```

### Campos

| Campo | Obrigatório | Nota |
|---|---|---|
| `id` | sim | Único. Áreas: `PY` (PySpark), `CFG` (config Spark), `GLUE` (infra/IaC), `UI` (Spark UI), `ICE` (Iceberg), `PQ` (Parquet/S3), `ATH` (Athena), `ENV` (ambiente/versão) |
| `category` | sim | Agrupa no relatório |
| `title` | sim | Uma linha |
| `requires_facts` | sim | Regra não dispara se o kind não foi extraído. Evita falso negativo silencioso |
| `when` | sim | `all` / `any` de condições |
| `status` | sim | `structural` = padrão sem métrica. `confirmed` = há measure |
| `threshold` | se por limiar | Aparece na saída — o operador vê qual limiar foi aplicado |
| `severity_default` ou `severity_by` | sim | `severity_by` avaliado em ordem, primeiro match ganha |
| `runtime_scope` | sim | Fora do range: regra **skipped por versão**, com motivo no relatório |
| `explanation` | sim | Por que custa. Aponta para `knowledge/` quando há profundidade |
| `proposed_change` | sim | Ações concretas |
| `risks`, `tradeoffs` | sim | Sem isso não é recomendação, é opinião |
| `validation` | sim | Como provar que a semântica não mudou |
| `rollback` | sim | Como voltar |
| `sources` | sim | URL + `retrieved`. Heurística de campo declara `{origin: field-heuristic}` |

### Condições em `when`

```yaml
# igualdade de atributo
- fact: pyspark.driver_collect
  where: {attrs.bounded: false, attrs.inside_loop: true}

# expressão sobre measures
- fact: spark.stage.task_duration
  expr: "measures.max_ms / measures.p50_ms >= threshold.ratio"

# ausência de fact
- absent: pyspark.cache_unpersist
```

### Avaliador de `expr`

Whitelist de nós AST: `Compare`, `BinOp`, `BoolOp`, `UnaryOp`, `Constant`, e acesso a atributo restrito a `measures.*`, `attrs.*`, `threshold.*`.

**Proibido:** `Call`, `Import`, `Subscript` arbitrário, qualquer dunder, qualquer nome fora da whitelist. **Não usar `eval`.**

Motivo: o catálogo é dado editável. Um dia alguém cola YAML de terceiro aqui. O avaliador é superfície de execução e é tratado como tal — há teste de segurança dedicado.

## Regras para escrever regra nova

1. **Nenhuma regra sem fonte.** Heurística de campo é permitida, mas declarada: `sources: [{origin: field-heuristic, note: "..."}]`.
2. **Nenhum limiar sem `runtime_scope`.** Se vale para tudo, escreva `"*"` explicitamente.
3. **`status: structural` para análise estática.** Só use `confirmed` quando há `measures` de execução real.
4. **Sem percentual de ganho em `explanation` ou em qualquer campo.** Ganho previsto só existe com benchmark, e vive no `Finding`, não na regra.
5. **`requires_facts` completo.** Regra que depende de um kind não listado gera falso negativo mudo.
6. **Fixture obrigatória.** Toda regra nova precisa de fixture em `fixtures/` com golden output — provando que dispara no caso positivo **e que não dispara** no caso limpo e no near-threshold.
7. **`validation` real.** "Validar o resultado" não é validação. Diga o quê: contagem total, contagem por chave, agregado de controle, contagem de nulos, distinct da PK.

## Arquivos

| Arquivo | Área | Depende de extratores da |
|---|---|---|
| `pyspark.yaml` | `SF-PY-*` | Fase 0 (AST PySpark) |
| `env.yaml` | `SF-ENV-*` | Fase 0 |
| `spark-config.yaml` | `SF-CFG-*` | Fase 0 parcial (`pyspark.conf_set`), Fase 1 (Terraform) |
| `glue-infra.yaml` | `SF-GLUE-*` | Fase 1 (Terraform HCL) |
| `spark-ui.yaml` | `SF-UI-*` | Fase 1 (event log) |
| `iceberg.yaml` | `SF-ICE-*` | Fase 1 (metadata tables) |
| `parquet.yaml` | `SF-PQ-*` | Fase 1 |
| `athena.yaml` | `SF-ATH-*` | Fase 1 |
| `routing.yaml` | `ROUTE-*` | Fase 0 — predicado sobre o case, não sobre facts |

### `routing.yaml` tem schema próprio

Regra de roteamento **não** tem `category`, `sources`, `severity` nem `runtime_scope` — ela não é um juízo sobre o sistema analisado, é uma decisão sobre o que fazer a seguir. Campos:

| Campo | Nota |
|---|---|
| `id` | `ROUTE-NNN` |
| `phase_in` | fases do case em que a regra é considerada |
| `when` | predicado sobre `case:` (estado) ou `finding:` (achado presente/ausente) |
| `recommended_skill` | skill a acionar |
| `reason` | **obrigatório** — aparece na saída e é o que o operador lê para entender a rota |
| `missing_artifacts`, `collect_commands` | o que falta e como coletar |
| `blocked_by` | gate não satisfeito. **Advisory na Fase 0**, não fail-closed |

Avaliação em ordem: primeiro match vira `recommended_skill`, os seguintes entram em `alternatives` com `rank`. Há um `fallback` no fim do arquivo — nenhum estado fica sem rota, e cair no fallback é sinal de que falta uma regra.

O validador de catálogo deve aplicar o schema de `Rule` a todos os arquivos **exceto** `routing.yaml`, que tem o seu.

Regras que dependem de extrator da Fase 1 já podem ser escritas: elas ficam inertes (`requires_facts` não satisfeito) até o extrator existir, e nesse momento passam a valer sem mudança de código. Escrever agora é o caminho — o conhecimento não espera o parser.

## O que este catálogo não é

Não é lista de boas práticas. Não é checklist de revisão — isso é `checklists/`. Não é procedimento — isso é `skills/`. É um conjunto de predicados sobre evidência extraída, com limiar, guarda de versão e proveniência.
