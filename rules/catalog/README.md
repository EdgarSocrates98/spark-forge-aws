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
| `blocked_on` | não | Nome de uma capacidade que ainda não existe (ex.: um extrator, uma etapa de fusão — ver "Facts `.enriched`" abaixo). Diferente de `requires_facts`: skip por `requires_facts` é "os dados podem chegar na próxima execução"; skip por `blocked_on` é "não vai disparar até alguém construir a capacidade". `rules/engine.py::judge` reporta os dois com `reason` distinto em `skipped` |
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

### `same_subject` — correlação dentro de uma entidade

Por default, cada condição de um grupo `all` é satisfeita independentemente, contra a
lista inteira de facts. Isso é correto para a maioria das regras, e **errado** para
regra que correlaciona atributos de uma mesma entidade.

Um arquivo Terraform com dois `aws_glue_job` mostra o problema: sem `same_subject`, uma
regra casa juntando um atributo do job A com outro atributo do job B. Cada job está
correto isoladamente, e a regra acusa. Acusar configuração correta destrói a confiança em
todo o resto do relatório.

```yaml
    when:
      same_subject: true
      all:
        - fact: tf.attribute
          where: {attrs.key: "--enable-auto-scaling", attrs.value: "true"}
        - fact: tf.attribute
          where: {attrs.key: number_of_workers, attrs.present: true}
```

Com `same_subject: true`, todas as condições do grupo precisam ser satisfeitas pela mesma
entidade. Use sempre que a regra fizer afirmação sobre **uma** entidade — um job, um
stage, uma tabela, uma query. Não use quando a afirmação for sobre o conjunto.

A entidade é `subject.symbol` quando ele existe (`aws_glue_job.etl`, `db.eventos`). Sem
`symbol`, um subject `source_location` identifica uma **localização**, e a chave é
`<arquivo>:<linha>` — nunca só o arquivo. Dois `spark.sql(...)` no mesmo módulo são duas
queries independentes: agrupar por arquivo poria as duas no mesmo grupo e a query correta
mascararia a incorreta, que é o falso negativo que `same_subject` existe para evitar. Todos
os facts de uma query compartilham um único subject, construído uma vez por query em
`facts/sql_literal.py::_scan_sql` e propagado intacto pelos facts `.enriched` da fusão, então
a linha é identidade estável, não detalhe de formatação. Sentinela de arquivo
(`sql.analyzed`, `pyspark.module_analyzed`, `tf.module_analyzed`, ancoradas em `line: 0`)
cai no próprio grupo: ela prova que o arquivo foi varrido, não afirma nada sobre um ponto
específico dentro dele.

**Um Finding por subject.** A regra afirma algo sobre uma entidade, então ela emite um
Finding para **cada** entidade que casa — nunca só a primeira. O `subject` de cada Finding
é o daquela entidade, e `evidence` carrega apenas os facts dela: evidência nunca vaza de um
recurso para o achado de outro. Quatro jobs com o mesmo defeito são quatro achados. Reportar
um só faria o operador corrigir aquele, rodar de novo e descobrir o próximo, sem nunca saber
quantos faltam — subcontar engana da mesma forma que um falso negativo. Regra sem
`same_subject` continua produzindo no máximo um Finding: ela fala do conjunto de facts, não
de uma entidade.

**`absent:` sob `same_subject` é avaliado dentro do grupo do subject**, e é isso que torna a
combinação útil para "esta entidade não tem X". `SF-GLUE-002` é o exemplo: ancorada em
`tf.resource` (um por `aws_glue_job`) com `absent: tf.observability.spark_ui`, ela acusa cada
job sem observabilidade. Ancorada no módulo, o fact existiria globalmente assim que **um**
job habilitasse Spark UI, `absent` falharia, e a regra não dispararia para ninguém —
mascarando todos os outros. `SF-ATH-003` (tabela, `catalog.table_partitions`) e `SF-ATH-002`
(query, `sql.projection`) têm a mesma forma.

**Uma regra com `absent:` e sem `same_subject` está afirmando algo sobre o conjunto
inteiro**, e precisa realmente ser essa a pergunta. `SF-ENV-003` é o caso legítimo: o
argumento `--enable-observability-metrics` está no recurso Terraform e `glueContext` está no
código Python — artefatos diferentes, subjects que nunca coincidem. A pergunta é "este
código-base inicializa `glueContext` em algum lugar?", e `same_subject` ali faria a regra
nunca disparar. `tests/test_rules_catalog_reachability.py` obriga qualquer nova regra dessa
forma a se declarar nessa lista, com o motivo escrito.

Escolha a âncora pela entidade sobre a qual a regra fala. Um fact de nível de arquivo
(`symbol: ""`, `line: 0` — as sentinelas `*_analyzed`) agrupa pelo arquivo, e esse grupo
nunca contém o fact de nível de recurso que `absent:` deveria observar: a regra passaria a
acusar todo módulo, inclusive os corretos.

**`absent:` exige um fact sentinela.** `absent: X` é verdadeiro quando nenhum fact do kind `X` existe — inclusive quando o extrator que produziria `X` nunca rodou. Uma regra que usa `absent:` sem exigir também o sentinela do extrator relevante (`pyspark.module_analyzed` para PySpark) dispara falso positivo numa análise parcial. Sempre inclua o sentinela em `requires_facts`.

### Facts `.enriched` — correlação de fontes fora do motor

`where`/`expr` avaliam SEMPRE contra o contexto de um único fact (`rules/engine.py::_fact_context`). Isso é suficiente enquanto a evidência de uma regra vem inteira de um extrator. Não é suficiente quando a resposta é literalmente metade de uma fonte, metade de outra — por exemplo, "esta query faz `SELECT *`" (do texto SQL) **e** "esta tabela é colunar" (do schema do catálogo) precisam estar no MESMO fact para uma condição `where` casar as duas ao mesmo tempo.

O motor não resolve isso combinando facts dentro de uma condição — não é essa a mudança que se faz (ver "Regras para escrever regra nova" acima: o motor fica simples de propósito). A correlação acontece **antes** de `judge`, numa etapa de fusão que lê os facts das duas fontes e produz um fact novo, de um kind próprio (`<kind original>.enriched`), carregando os attrs das duas fontes juntos. `sparkforge/facts/fusion.py` é a implementação de referência: correlaciona `sql.projection`/`sql.predicate` (`sparkforge/facts/sql_literal.py`) com `catalog.table_schema` (`sparkforge/facts/catalog_schema.py`) pelo nome da tabela e produz `sql.projection.enriched` / `sql.predicate.enriched`.

Uma regra que depende de fusão:

- Referencia o fact `.enriched` em `when`, nunca o fact original das duas fontes numa condição só.
- Lista o fact `.enriched` (ou o fact da fonte que falta) em `requires_facts`, para não disparar numa análise que nunca rodou a fusão — mesma disciplina do sentinela em `absent:`.
- Fica marcada `blocked_on: <nome-da-capacidade>` no catálogo até a etapa de fusão que ela precisa existir (ver campo `blocked_on` abaixo), documentando no comentário da regra **o que especificamente falta** — não "falta dado", mas "falta a capacidade de correlacionar X com Y".

`SF-ATH-001`, `SF-ATH-002` e `SF-ATH-005` (`athena.yaml`) são o exemplo: ficaram `blocked_on: fusao-sql-catalogo-schema` até `fusion.py` existir, e o comentário em cada regra explica exatamente qual correlação faltava.

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

### Operadores declarativos de roteamento

Predicado de roteamento é **declarativo**, nunca expressão livre. Expressão exigiria
`Call`/`In`, que a whitelist do avaliador proíbe — e o catálogo é dado editável,
portanto superfície de execução.

| Operador | Semântica |
|---|---|
| `equals: <v>` | valor no caminho é igual a `<v>` |
| `absent: true` | caminho ausente, vazio ou `null` |
| `present: true` | caminho existe e é truthy |
| `count_gt: <n>` | comprimento (lista/dict/str) ou valor numérico maior que `<n>` |
| `count_eq: <n>` | comprimento ou valor numérico igual a `<n>` |
| `contains: <v>` | `<v>` está na lista do caminho |
| `any_where: {k: v}` | algum item da lista tem `k == v` |

`case: <caminho.pontuado>` resolve dentro do case. `finding: <rule_id>` com
`present: true`/`false` testa a presença de um achado.

O validador de catálogo deve aplicar o schema de `Rule` a todos os arquivos **exceto** `routing.yaml`, que tem o seu.

Nenhuma regra do catálogo carrega `blocked_on` hoje: as cinco últimas que
dependiam de capacidade inexistente — `SF-PQ-001/003/005` (listagem S3),
`SF-GLUE-005` (diff de Terraform) e `SF-ENV-002` (inventário de consumidores)
— foram desbloqueadas com os extratores correspondentes. O que falta para uma
regra disparar é sempre **coleta**, nunca código.

Regra nova que dependa de extrator que ainda não existe pode ser escrita assim
mesmo: marque `blocked_on: <capacidade>` e ela fica inerte até o extrator
nascer. `tests/test_rules_catalog_reachability.py` garante as duas pontas —
kind sem extrator exige `blocked_on`, e `blocked_on` que sobrevive ao extrator
falha o teste.

## O que este catálogo não é

Não é lista de boas práticas. Não é checklist de revisão — isso é `checklists/`. Não é procedimento — isso é `skills/`. É um conjunto de predicados sobre evidência extraída, com limiar, guarda de versão e proveniência.
