---
name: spark4-compatibility
description: Use quando o código PySpark ou o `.jar` precisa rodar sob Apache Spark 4 e alguém pergunta "o que quebra no Spark 4?", "essa config mudou de nome?", "ANSI mode vai estourar meu cast?" ou "meu JAR de Scala 2.12 funciona?". Use também quando o job falha com `NoSuchMethodError`, `ClassNotFoundException` ou uma exceção de overflow que antes devolvia NULL. Se você está prestes a comparar o código com o guia de migração do Apache no olho, rode `sparkforge migrate glue <dir> --from 5.1 --to 6.0` e `sparkforge glue dependency-audit <dir> --glue 6.0` — a área `SF-SPARK4` guarda cada regra pela versão de **Spark**, não de Glue, e por isso vale igual num EMR.
subagent: true
agent: sf-runtime-specialist
---

# Spark 4 Compatibility

A fronteira do Apache Spark 4 é diferente da fronteira do empacotamento da AWS, e confundir as duas produz recomendação errada nos dois sentidos. Uma config renomeada no Spark 4.0 quebra em qualquer motor que rode Spark 4 — Glue 6.0, EMR, um cluster próprio. Já a remoção do EMRFS é do empacotamento do Glue e não existe fora dele. Por isso `SF-SPARK4` declara `runtime_scope` por `spark:` e `SF-MIG` por `glue:`.

## Procedimento

1. `sparkforge migrate glue <dir> --from 5.1 --to 6.0` — as regras de `SF-SPARK4` aparecem no mesmo assessment, guardadas pela versão de Spark do alvo de cada degrau.
2. `sparkforge glue dependency-audit <dir> --glue 6.0` — pins de `requirements*.txt` com `major` e binários `.jar` com `scala_minor`, cada um ao lado do achado que produziu.
3. Para um motor que não é Glue, informe a versão de Spark direto: `sparkforge judge --facts <arquivo> --spark 4.1.1`. A guarda é por Spark, então a regra avalia sem chave `glue` nenhuma.

   Leia o campo `runtime` da saída antes de acreditar em qualquer achado — ou na ausência dele. `detected_from` diz de onde cada versão saiu (`terraform`, `event_log`, `cli`), e `divergences` denuncia fontes que discordam entre si, o que é achado próprio (`SF-ENV-001`) e não detalhe de implementação. Uma flag que contradiz o que o event log declara não é preferência: é sinal de que alguém está julgando o job errado.

## As quatro fronteiras que o catálogo julga

**Config renomeada.** Nome antigo continua aceito pelo parser e ignorado em silêncio — o pior modo de falha, porque o job roda e o comportamento muda. `mig.renamed_conf` observa o nome antigo no código.

**API removida.** Principalmente pandas-on-Spark e `SQLContext`. `mig.removed_api` observa a chamada.

**Piso de dependência.** Spark 4.1 exige versões mínimas de PyArrow e Pandas. `mig.python_dep` já separa o `major` do pin; a regra compara contra o piso. Versão que não começa por dígito (`pacote==@git+https://...`) fica **sem** a chave `major` de propósito: a regra fica muda sobre o que não conseguiu ler, em vez de julgar um número inventado.

**Binário de Scala.** Glue 6.0 roda Scala 2.13.17; versões minor de Scala não são binariamente compatíveis. `mig.jar_binary.scala_minor` é o segundo segmento do que foi observado no nome do artefato — quando não há versão de Scala legível, a chave não existe, pelo mesmo motivo acima.

## ANSI mode é comportamento, não sintaxe

Spark 4.1 liga ANSI por padrão: overflow de inteiro, cast inválido e índice fora do array passam a lançar exceção onde antes devolviam `NULL`. Nenhum extrator consegue decidir se um cast do seu código vai estourar — isso depende do dado. O que o catálogo faz é observar `cast(` sem guarda (`mig.ansi_risk`) e acusar **só no degrau que cruza Glue 6.0**, porque é ali que a fronteira está.

`spark.sql.ansi.enabled=false` restaura o comportamento anterior. É mitigação legítima e precisa ser registrada como decisão: ela desliga uma proteção, não corrige o cast.

## Erros conhecidos, com texto exato

| Erro | Causa observada em fonte oficial |
|---|---|
| `NoSuchMethodError` / `ClassNotFoundException` | `--extra-jars` compilado com Scala 2.12 sob runtime 2.13 (`ERR-GLUE-002`) |
| `NoSuchFieldError` | JAR com AWS SDK v2 anterior a 2.44.6 usado com `--user-jars-first` (`ERR-GLUE-003`) |

## Referência rápida

Conhecimento de fundo, sob demanda: [`knowledge/spark/spark4-migration.md`](../../knowledge/spark/spark4-migration.md) traz o que a fonte declara e marca como *a verificar* o que ela não declara. [`docs/aws/glue/6.0/spark4.md`](../../docs/aws/glue/6.0/spark4.md) é a leitura pelo lado do Glue.

Severidade e limiar de cada regra: `sparkforge rules lookup --id SF-SPARK4-001` (e seguintes).

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime.
Recompilar e republicar artefato, ou desligar ANSI mode num job de produção, é manutenção
destrutiva e você **não executa** — recomende, e a confirmação de escopo e rollback
**sobe a quem pode ser perguntado**: o agente pai que despachou, ou o operador na sessão.

Desligar `spark.sql.ansi.enabled` remove uma proteção. Isso é decisão declarada, com dono,
nunca um ajuste que a skill aplica para fazer o job passar.

## Quando NÃO usar

- A pergunta é sobre a **migração inteira** de um job Glue, com gates e recomendação: use `migrate-glue-6`.
- A pergunta é sobre **performance** do código no Spark 4: isto aqui é compatibilidade. Performance exige execução comparada nos dois runtimes.
- A pergunta é sobre **Iceberg v3** ou **FGAC**: são outras fronteiras, com outras skills.

## Red flags

- **"Renomeei a config, então está resolvido."** Confirme que o nome novo é o que o Spark 4.1 lê, e não um terceiro nome intermediário de uma versão anterior.
- **"O JAR é nosso, foi compilado aqui."** Compilado contra qual Scala? `scala_minor` é o que decide, não a origem do artefato.
- **"Desliguei o ANSI e passou."** Passou a rodar; não passou a estar correto. O cast que estouraria continua produzindo o valor que o ANSI recusava.
- **"A regra não disparou, logo não há risco."** Guarda por versão: fora da faixa, a regra é **pulada**, e `sparkforge judge --show-skipped` mostra a razão. Silêncio da ferramenta nunca é atestado de ausência de risco.
