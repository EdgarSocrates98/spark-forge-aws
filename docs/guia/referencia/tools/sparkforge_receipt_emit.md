<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_receipt_emit`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Grava o RECIBO de uma execucao do case em `<repo>/.sparkforge/receipts/<receipt_id>.json`: caminho relativo e sha256 do `case.yaml`, de cada arquivo de facts (a UNIAO do case, o mesmo conjunto que `judge` recebeu), dos findings, do report, do blackboard, dos ADRs e dos debates; os fact_ids de `funcval.*` e `bench.*` como prova, sem comparar nada; os spans de tool do run (sem `run_id`, o do proprio processo); e o host e o modelo que o transcript declara, com o provider DECLARADO. O `receipt_id` e o sha256 do JSON canonico, e `now` entra nele. O QUE ELE NAO PROVA, e isto e contrato: autoria -- nao ha chave, e qualquer um com os mesmos artefatos produz o mesmo recibo (`refused: authorship`); nem o que cada tool recebeu ou devolveu (`refused: tool_io`). Nao carrega conteudo de caso: nenhum valor de `measures`, nenhum `metadata_json`, nenhum caminho absoluto. Toda lacuna sai em `unresolved` com a razao. Autonomia L0: `actions.applied_changes` e sempre `false`. O span desta propria chamada fica fora, em `tools.excluded`, porque e gravado depois que ela devolve.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string ou array de string | sim | A UNIAO dos arquivos de facts do case, dentro do repo. |
| `findings_path` | string | sim | Findings (JSON) gerados por `sparkforge judge --out`. |
| `now` | string | sim | Instante ISO 8601 da emissao. Entra no hash. |
| `repo` | string | sim | Raiz do case. Caminhos relativos resolvem contra ela. |
| `host_transcript_path` | string | não | Transcript JSONL do host. So o sha256 entra no recibo. |
| `provider` | string | não | Provider do host, DECLARADO (anthropic). Nunca deduzido. |
| `report_path` | string | não | Relatorio, se houver. |
| `run_id` | string | não | Run cujos spans entram. Default: o run deste processo. |

## Na CLI

[`sparkforge receipt emit`](../cli/receipt.md), [`sparkforge receipt verify`](../cli/receipt.md)

## Capacidade

prove what an execution used and decided

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
