# Receita — avaliar performance de um job

**O quê:** o event log da execução vira facts de stage, task, spill e GC;
o `judge` aplica os limiares versionados (SF-UI) e o `benchmark` compara
dois runs — medição, nunca estimativa.
**Por que:** performance é alegação quantificada: o schema recusa
`expected_gain`/`expected_effect` sem `benchmark_ref`. O caminho do Forge
existe para que nenhum número saia inventado.
**Quando:** "o job ficou lento", "essa mudança ajudou?", stage dominante,
skew, spill, executor perdido.
**Quando não:** custo sem medição de run — `finops` pede `dpu_seconds`
reais, não projeção.

## Problema

"Este job está lento — qual o gargalo dominante, com evidência?"

## Pré-requisitos

Event log do Spark (JSONL) ou um `job_run_id`; para before/after, dois
runs medidos da mesma mudança.

## Passo a passo

```bash
# 1) facts da execução
sparkforge-aws analyze event-log --path logs/run1.jsonl \
  --out .sparkforge_aws/facts_eventlog.json

# 2) julgamento determinístico
sparkforge-aws judge --facts .sparkforge_aws/facts_eventlog.json \
  --out .sparkforge_aws/findings.json

# 3) rota do case
sparkforge-aws case update --repo . \
  --facts .sparkforge_aws/facts_eventlog.json \
  --findings .sparkforge_aws/findings.json
sparkforge-aws next-step --repo . --findings .sparkforge_aws/findings.json
```

Para comprovar ganho de uma mudança:

```bash
sparkforge-aws benchmark --before <run A> --after <run B>
```

## Saída esperada / interpretação

Findings com `rule_id` (ex.: SF-UI-001 skew de duração de task, SF-UI-006
subparalelismo) cada um citando os `fact_id` que o sustentam. `next-step`
aponta o coordenador da área dominante (ex.: skew →
`diagnose-data-skew`).

## Verificação

Cada finding carrega `evidence` não-vazio — `Finding` com evidence vazio é
inválido por construção. Re-rodar `analyze` no mesmo log reproduz os
mesmos facts (sha256 estável).

## Limitações

- `analyze event-log` mede o que aconteceu naquele run — não extrapola.
  Volume diferente é outro run, outra análise.
- `benchmark` isola uma variável por vez — comparar dois runs com três
  mudanças misturadas não prova nenhuma delas.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| findings vazios | facts de outro extrator | `judge` recebe o arquivo do `analyze event-log`, não do `analyze pyspark` |
| `next-step` em intake | `facts_index` não gravado | `case update --facts <arquivo>` antes de rotear |

## Uso por agentes

Skills: `analyze-spark-ui`, `diagnose-data-skew`, `diagnose-oom`,
`benchmark-pyspark-job`, `optimize-variable-volume-job`. O host chama as
mesmas tools — o humano e o agente veem o mesmo número.

## Leitura seguinte

- [job-lento](../../guia/usos/job-lento.md)
- [custo-e-capacidade](../../guia/usos/custo-e-capacidade.md)
- [mudancas-com-prova](../../guia/usos/mudancas-com-prova.md)
