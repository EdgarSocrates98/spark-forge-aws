# Receita — explorar o Graph Studio

**O quê:** `code init` indexa a árvore; `graph status/view/ui` projeta o
`ForgeGraphView/v1` e abre o Graph Studio local (read-only, 127.0.0.1).
**Por que:** navegar a estrutura real do código — símbolos, chamadas,
comunidades — em vez de adivinhar impacto por leitura linear.
**Quando:** entender um repo desconhecido, medir blast radius antes de mudar,
ou conferir quem chama um símbolo.
**Quando não:** sem `code init` antes, o grafo responde `unavailable` com a
razão — não é bug, é o índice que ainda não existe.

## Problema

"Quem chama `run_job`? O que quebra se eu mudar esta função? Como é a forma
deste repositório?"

## Pré-requisitos

`sparkforge-aws` instalado; o índice construído uma vez:

```bash
sparkforge-aws code init --root .
sparkforge-aws code status --root .
```

`code sync` é a única escrita posterior — põe o índice em dia com a árvore.

## Passo a passo

```bash
# estado honesto do grafo (contagens e origem do índice)
sparkforge-aws graph status

# documento ForgeGraphView/v1 (o contrato que o Studio consome)
sparkforge-aws graph view --root .

# abre o Graph Studio local — read-only, 127.0.0.1
sparkforge-aws graph ui
```

No Studio ou pela CLI de code-intel:

```bash
sparkforge-aws code search run_job          # símbolo por nome parcial
sparkforge-aws code shape                   # comunidades e nós de maior grau
sparkforge-aws code path --from A --to B    # menor caminho de chamadas
```

## Saída esperada / interpretação

`graph status` devolve `provider`, contagens e a origem do índice — ou
`"graph": "unavailable"` com `reason` e o comando que destrava (`code
init`). O `ForgeGraphView/v1` é a projeção consumível: nodes com kind e
origem, edges tipadas, nunca o índice bruto.

## Verificação

`graph status` reporta frescor do índice contra a árvore; depois de editar
código, `code sync` e o `status` volta a refletir a árvore real.

## Limitações

`code shape` descreve comunidades e grau — **não é julgamento** (não aplica
regra nem limiar). O Studio é read-only: nenhuma exploração de grafo escreve
no repo.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `"graph": "unavailable"` | sem índice code-intel | `sparkforge-aws code init --root .` |
| grafo stale | árvore mudou depois do init | `sparkforge-aws code sync` |
| símbolo não achado | índice sem o arquivo (exclude/linguagem) | `code status` mostra o que entrou |

## Uso por agentes

Tools MCP `sparkforge_aws_graph_view` / `sparkforge_aws_graph_status` —
citadas pelo coordenador `pyspark-code-reviewer` junto de `code_search`,
`code_symbol` e `analyze_call_graph` para correlação estrutural.
