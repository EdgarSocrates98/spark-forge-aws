<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_debate_referee`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Arbitra o PROTOCOLO de debate do case e diz se o fechamento declarado pode ser publicado. Use depois de `sparkforge_arbitrate`, e antes de apresentar qualquer causa raiz que tenha saido de debate entre agentes. Ele NOMEIA quatro violacoes: hipotese que sobrevive ao fechamento (a frase do protocolo -- `claim_type: hypothesis` nao fecha root cause), claim sem `evidence_refs`, objecao sem replica, e referencia pendurada. `upheld` e BINARIO: recusa graduada nao recusa. ELE NAO EXECUTA DEBATE e nao gera argumento nenhum -- isso exige provider, e nada neste projeto chama provider. `arbitrate` emite `debate_plan` e para; este verbo valida o que o host preencheu. O setimo estagio do protocolo (VERIFICATION) sai `modeled: false`, porque consenso e acordo e nao verificacao. As tres recusas saem em `refused` com o que destravaria.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio com `.sparkforge/blackboard/`. |

## Na CLI

[`sparkforge debate referee`](../cli/debate.md)

## Capacidade

referee the debate protocol and refuse a closure not anchored in evidence

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
