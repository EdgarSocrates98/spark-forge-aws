<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_proof`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Change Proof: para cada recomendacao APLICADA (`applied`: RULE_ID ou RULE_ID:simbolo), as obrigacoes de prova e o desfecho de cada uma. RESOLUCAO: a regra deixou de disparar na mesma chave estavel do subject, julgada sobre os facts do depois? Se ela ficou muda por falta de artefato, o desfecho e `unproven` com os kinds que faltam. EIXOS: um por item de `action.moves`, pela politica `rules/catalog/proof_axes.yaml` -- correcao pelos veredictos SF-FVAL, melhoria pelo benchmark e SF-BENCH, e eixo sem comparador sai `unproven` com a medida que o destravaria. Desfechos: refuted, not_refuted, inconclusive, unproven. O QUE ELA NAO FAZ, e isto e contrato: nunca diz `proven` (proxy de funcval e delta de benchmark nao provam equivalencia nem melhoria atribuivel) e nunca estima ganho. Com mais de uma mudanca aplicada, a melhoria sai `inconclusive` (`attribution_shared`).

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `after_facts_path` | string ou array de string | sim | Facts extraidos dos artefatos do depois. |
| `applied` | array de string | sim | RULE_ID ou RULE_ID:simbolo de cada recomendacao aplicada. |
| `facts_path` | string ou array de string | sim | A UNIAO de facts do case, com os de funcval e benchmark. |
| `findings_path` | string | sim | Findings do antes, gerados por `sparkforge judge --out`. |
| `athena` | string | não |  |
| `databricks` | string | não |  |
| `emr` | string | não |  |
| `glue` | string | não |  |
| `iceberg` | string | não |  |
| `photon` | string: `on`, `off` | não | Photon ligado ou desligado no Databricks. Com 'on', regra de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf. Sem databricks, vira divergencia 'photon:'. |
| `python` | string | não |  |
| `spark` | string | não |  |

## Na CLI

[`sparkforge proof`](../cli/proof.md)

## Capacidade

prove what an applied change did and did not break

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
