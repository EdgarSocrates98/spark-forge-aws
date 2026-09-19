<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_root_cause`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Ordena os achados de `judge` por consequencia DECLARADA e nomeia a LACUNA. Use quando houver mais de um achado e a pergunta for 'por onde comeco'. O que ele publica de novo nao sao os achados: e `missing_evidence` -- as regras que ficaram MUDAS por falta de artefato, com o kind que falta e o modulo que o emite. Sem isso, silencio por falta de coleta e indistinguivel de silencio por ausencia de defeito. NAO calcula confianca: `confidence_declared` e o campo da REGRA repassado como declarado, nunca combinado com severidade para produzir score novo. NAO estima ganho. NAO avalia impacto de seguranca -- `security_posture` classifica pelo NAMESPACE do `action.kind` e repassa o `risks` da regra verbatim. As tres recusas saem em `refused` com o que destravaria cada uma. A saida e uma ORDEM por consequencia, e `ordering.is_not` diz que ela nao e ranking por probabilidade.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | qualquer | sim | Arquivo de facts, ou a LISTA deles. A repeticao e o contrato: a lacuna publicada e sobre a UNIAO. |
| `all_missing` | boolean | não | Lista as regras nao avaliadas de todas as areas. O TOTAL sai nos dois casos. |
| `athena` | string | não |  |
| `databricks` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não |  |
| `emr` | string | não |  |
| `glue` | string | não |  |
| `iceberg` | string | não |  |
| `photon` | string: `on`, `off` | não | Photon ligado ou desligado no Databricks. Com 'on', regra de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (plan.photon) faz o mesmo sem declaracao e vence 'off', que vira divergencia 'photon:'. Sem databricks, vira divergencia 'photon:'. |
| `python` | string | não |  |
| `spark` | string | não |  |

## Na CLI

[`sparkforge root-cause`](../cli/root-cause.md)

## Capacidade

order the findings by declared consequence and name the gap

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
