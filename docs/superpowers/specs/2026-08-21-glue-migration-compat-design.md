# SparkForge AWS — Compatibilidade de migração Glue por par de versões (`SF-MIG`)

**Data:** 2026-08-21
**Status:** **proposto**. Nada implementado nesta data.
**Origem:** `prompt_migrations_glue.md` (fábrica de migração Glue) e
`prompt_evo_harness.md` (camada de harness). Os dois se encontram no contrato de
harness; esta fase entrega o vertical, e a §8 registra o critério para o encontro.
**Base:** o motor existente — artefato → facts → regras → findings — com 21 extratores,
116 regras, 171 fixtures golden e gates fail-closed com produtor declarado.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o fato de versão está em dois lugares e um deles é código

`sparkforge/facts/runtime_detect.py:51` carrega `GLUE_MATRIX`, uma constante Python com
Glue 3.0, 4.0, 5.0 e 5.1. Em paralelo, `knowledge/glue/runtime-matrix.md` descreve a mesma
matéria para leitura humana. Não há mecanismo que force as duas a concordarem, e a §4 do
`prompt_migrations_glue.md` proíbe exatamente esse arranjo: "nunca usar essa tabela
isoladamente".

Glue 6.0 não existe em nenhum dos dois. O prompt de migração afirma uma linha para 6.0
— Spark 4.1.1, Python 3.13, Scala 2.13.17, Java 17 — e manda validá-la antes de cada
trabalho. Este documento **não** adota esses valores: eles precisam de fonte oficial com
data de consulta, e o mecanismo para isso já existe em `knowledge/sources.lock.json`, que
vigia 131 fontes.

O analisador de migração atual, `sparkforge/migration/glue/analyzer.py`, tem 4.8 KB, um
`target_runtime` com default `"5.1"` e checagens da forma
`"python_version" in script_content and "3.10" in script_content`. Isso é busca de
substring em texto, não análise de compatibilidade, e o par de versões está embutido em
condicional.

## 2. Objetivo

Analisar a compatibilidade de um job Glue entre um par de versões arbitrário, acumulando os
breaking changes de cada degrau do caminho, com o fato de versão vindo de dado versionado
com procedência e o julgamento vindo de regras executáveis do catálogo.

O par `4.0 → 6.0` é o primeiro exercitado. Nenhum par é privilegiado no código.

### Não-objetivos, com razão registrada

- **Shadow run, reconciliação de dados, canary, cutover, comparação de custo e performance
  real.** Todos exigem job real e AWS viva, que não existem nesta data. Entram como gate com
  evidência ausente, e gate sem evidência é `BLOCKED`, nunca `PASS`.
- **TaskSpec, Router, ExecutionPlanner, ContextManager, BudgetManager, ModelRouter, fanout
  governor.** São o harness, e o harness precisa de duas instâncias antes de ser extraído —
  ver §8.
- **Os 16 agentes do §6 do prompt de migração.** Agente é despacho; esta fase entrega o
  motor que um agente usaria.
- **Hudi e Delta.** Iceberg primeiro, porque o repositório já o conhece com 5 regras e 9
  fixtures. Os outros dois entram quando houver fixture que os exija.
- **Error Knowledge Base.** Projeto próprio.

## 3. Decisões de desenho

### D-1 — a matriz de versões vira dado, e o código para de guardá-la

Nasce `knowledge/glue/runtime-matrix.yaml`, machine-readable, com uma entrada por versão de
Glue contendo `spark`, `python`, `scala`, `java`, `iceberg`, `hudi`, `delta`, `sdk`,
`status` (suportada, EOS, EOL), `sources` e `retrieved`.

`GLUE_MATRIX` é apagado de `runtime_detect.py`; o carregamento passa pelo dado. Um teste
falha se qualquer versão voltar a aparecer hardcoded em `sparkforge/` fora do loader.

`knowledge/glue/runtime-matrix.md` permanece para leitura humana e passa a ser conferido
contra o YAML, no mesmo padrão de `scripts/sync_skills.py --check`: o espelho é exatamente o
que o tradutor produz.

### D-2 — Glue 6.0 entra por pesquisa com data, e até lá as regras nascem `blocked_on`

Nenhuma linha de 6.0 é escrita de memória. Enquanto a entrada não existir no YAML com
`sources` conferidas contra o lock e `retrieved` preenchido, toda regra que dependa de 6.0
declara `blocked_on` — mecanismo que o catálogo suporta e que hoje tem zero uso.

A regra existe, declara o que falta e não julga. É o oposto de assumir a versão e produzir
finding sem lastro.

### D-3 — `runtime_scope` é versão, `requires_facts` é natureza do artefato

O `rules/catalog/athena.yaml` registra, com a razão escrita, que usar `runtime_scope` para
etiquetar serviço foi erro de camada e teria apagado a área inteira em silêncio. Esta fase
respeita a mesma divisão: `runtime_scope` declara a faixa de versões em que o breaking change
vale; o que gateia por tipo de artefato analisado é `requires_facts`.

É essa separação que torna o motor genérico sobre pares: a regra não sabe qual é o par, sabe
em que faixa ela vale.

### D-4 — análise cumulativa, plano de execução possivelmente direto

O §6.2 do prompt de migração distingue migração direta operacional de análise cumulativa
obrigatória. O resolvedor de caminho expande `origem → alvo` em todos os degraus intermediários
que a matriz conhece, e a seleção de regras é a união sobre o caminho. Cada finding registra em
qual salto nasce.

O plano de execução que sai disso pode ser um salto único. A análise nunca é.

### D-5 — o extrator observa, a regra julga

`sparkforge/facts/migration.py` emite fato, nunca veredito. Um import `com.amazonaws.*` é
observação; que ele seja bloqueante para um alvo específico é julgamento de regra, com faixa
de versão declarada. Essa divisão é o que permite reavaliar facts antigos com catálogo novo
sem reparsear artefato.

## 4. Facts

Extrator novo, `sparkforge/facts/migration.py`, com `EMITTED_KINDS` fechado como os outros 20:

| kind | observa |
|---|---|
| `mig.sdk_import` | import `com.amazonaws.*` e `software.amazon.awssdk.*` |
| `mig.emrfs_config` | `fs.s3.consistent.*`, `EmrFileSystem`, configuração exclusiva de EMRFS |
| `mig.ansi_risk` | cast sem `try_cast`, divisão sem guarda, parsing de data com formato legado |
| `mig.jar_binary` | JAR declarado com versão de Scala e alvo de bytecode |
| `mig.python_dep` | dependência com extensão nativa em `requirements` ou `--additional-python-modules` |
| `mig.table_format` | versão de FORMATO de tabela, distinta da versão de biblioteca |
| `mig.legacy_conf` | `spark.sql.legacy.*` e configuração removida |
| `mig.deprecated_api` | `SQLContext` e API removida entre as versões do caminho |

## 5. Regras `SF-MIG`

Arquivo `rules/catalog/glue-migration.yaml`, formato idêntico ao das 116 existentes:
`id`, `category`, `title`, `requires_facts`, `when`, `status`, `severity_default`,
`runtime_scope`, `explanation`, `proposed_change`, `risks`, `tradeoffs`, `validation`,
`rollback`, `sources`.

Áreas cobertas na primeira fatia: AWS SDK v1 para v2, EMRFS para S3A, ANSI mode, Java 8 para
17, Scala 2.12 para 2.13, Python com extensão nativa, versão de formato de tabela contra
consumidores, configuração legada removida.

A quantidade de regras não é fixada aqui de propósito: ela sai do que os fixtures exigirem,
e uma regra sem golden que a dispare não fecha a fase.

## 6. `MigrationAssessment` e gates

Agregação dos `Finding` num assessment com os campos do §50 do prompt de migração: runtimes de
origem e alvo, classe do job, compatibilidade por eixo, breaking changes, mudanças requeridas e
opcionais, risco de dado, performance, segurança e custo, testes exigidos, rollback, não
resolvidos, e recomendação `GO` / `CONDITIONAL_GO` / `NO_GO`.

Gates nos cinco estados do §12: `PASS`, `PASS_WITH_RISK`, `FAIL`, `BLOCKED`, `NOT_APPLICABLE`,
estendendo o mecanismo de gates fail-closed que o repositório já tem.

**Invariante desta fase:** gate sem evidência é `BLOCKED`. Sem job real e sem AWS, os gates de
dado, performance, custo e canary nascem `BLOCKED` nomeando a evidência ausente. Um assessment
`NO_GO` por falta de evidência é resultado legítimo e desejável.

## 7. Testes

- Golden fixture por caso, em domínio `migration`: Parquet simples, Iceberg leitura e escrita,
  JAR Scala 2.12, `com.amazonaws.*`, configuração EMRFS, cast sem guarda, dependência Python
  nativa.
- Todo kind emitido é alcançado por alguma regra.
- Todo ramo de severidade tem golden que o produz.
- Nenhuma regra inalcançável sem `blocked_on` declarado.
- **Par genérico:** um segundo par de versões seleciona conjunto diferente de regras sem
  alteração em Python. Este é o teste que prova ou derruba a generalidade.
- **Sem versão hardcoded:** nenhuma versão de Glue aparece em `sparkforge/` fora do loader da
  matriz.
- Paridade entre `runtime-matrix.yaml` e `runtime-matrix.md`.

## 8. O encontro com o harness, e o critério para ele acontecer

Esta fase produz, por necessidade e não por antecipação, as três peças que o
`prompt_evo_harness.md` pede: um contrato com inputs, capacidades permitidas, critério de
sucesso, critério de falha e evidência exigida; um conjunto de gates com estados; e um pacote de
evidência com procedência e data.

O `HarnessContract` genérico só se justifica quando existir uma **segunda** instância — Lake
Formation ou Iceberg — e o que for comum entre as duas for medido, não imaginado. Extrair
abstração de um caso só é a arquitetura prematura que a §100 do próprio prompt do harness manda
evitar.

Critério registrado: duas instâncias, estrutura comum medida, e só então o contrato.

## 9. Em aberto para a implementação decidir

- Onde vive o resolvedor de caminho de versão: módulo próprio em `sparkforge/migration/` ou
  função no loader da matriz. Depende de quem mais precisar dele.
- Se `mig.ansi_risk` é um kind só com subtipo no payload, ou kinds separados por classe de
  risco. A escolha afeta quantas regras precisam existir e deve sair do primeiro corpus de
  fixtures, não da intuição.
- Se o `analyzer.py` atual é apagado na mesma fase ou marcado como substituído. Depende de haver
  ou não consumidor dele hoje — a implementação mede antes de apagar.

## 10. Critérios de conclusão

1. `knowledge/glue/runtime-matrix.yaml` existe, com `sources` conferidas contra
   `knowledge/sources.lock.json` e `retrieved` preenchido em toda entrada.
2. `GLUE_MATRIX` não existe mais em `sparkforge/`, e o teste que proíbe versão hardcoded passa.
3. Área `SF-MIG` no catálogo, com toda regra alcançável ou com `blocked_on` declarado.
4. Extrator `migration.py` com `EMITTED_KINDS` fechado, e todo kind alcançado por regra.
5. O par `4.0 → 6.0` produz um `MigrationAssessment` completo contra fixture, com os gates que
   dependem de AWS em `BLOCKED` e a evidência ausente nomeada.
6. Um segundo par de versões roda e seleciona regras diferentes, sem alteração em Python.
7. Se a linha de Glue 6.0 não tiver fonte com data até o fim da fase, as regras que dependem
   dela permanecem `blocked_on` e a fase fecha assim mesmo, declarando isso.
8. A suíte completa continua passando.
