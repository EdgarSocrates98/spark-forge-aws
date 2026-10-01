<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_economy_report`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

O que a execucao poe na janela de contexto: bytes MEDIDOS por tool, o efeito medido do `detail_level`, o peso do catalogo em repouso e -- quando houver transcript do host -- o token de provider AO LADO, nunca somado ao byte. Verbo de topo, nao um `analyze`: compoe sobre o ledger que `call_tool` alimenta e nao le artefato nenhum. O QUE ELE RECUSA: (1) custo em dolar -- chamada de tool local nao tem tabela de preco publicada; (2) estimativa de token por divisao de bytes -- `len//4` e heuristica interna e nao pode sair com o nome de token, entao sem transcript sai `tokens_unresolved`; (3) somar byte com token, que sao unidades diferentes. `payload_bytes` e a serializacao canonica da resposta do despacho, e NAO 'o que o modelo viu': o host reserializa com espacamento proprio.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `run_id` | string | sim | O run cujos spans agregar. Sem spans correlacionados sai `run_unresolved` -- agregar spans de outra investigacao seria pior que numero nenhum. |
| `host_transcript` | string | não | Caminho do transcript JSONL do host, quando houver. E a unica fonte de token de provider que existe aqui. |

## Na CLI

[`sparkforge economy report`](../cli/economy.md)

## Capacidade

measure what the run puts in the context window

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
