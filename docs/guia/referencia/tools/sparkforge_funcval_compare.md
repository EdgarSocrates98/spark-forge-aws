<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_funcval_compare`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Compara os DOIS resultados que VOCE mediu contra o plano de `sparkforge_funcval_plan`, e emite `funcval.check_delta`, a sentinela `funcval.analyzed` e `funcval.unresolved`. Funcao pura sobre valores ja medidos: nao executa consulta e nao mede nada. Com `out_path`, GRAVA a comparacao COMPLETA no arquivo que `sparkforge_judge` le -- sem ele o passo seguinte exige extrair `items` do envelope a mao, e o envelope PAGINA. O QUE ELE RECUSA AFIRMAR: (1) Os quatro eixos sao PROXIES -- contagem, schema, chaves e agregados iguais NAO provam que o dado e o mesmo. A sentinela carrega esse limite em `attrs`, e nao so nesta descricao. (2) A comparacao e SEMPRE antes contra depois, NUNCA resultado contra catalogo: o schema declarado serviu para saber quais colunas existem, e conferir o observado contra ele seria asserção absoluta sobre o dado -- pergunta de SF-DQ, nao desta fase. (3) COMPARACAO RELATIVA NAO DECIDE `diverged`. Para ponto flutuante o fact sai com `measures.relative_delta` e SEM `diverged`, com `diverged_omitted_reason` dizendo por que: o numero que separa reassociacao de divergencia real e heuristica de campo, e heuristica de campo mora no catalogo (SF-FVAL-004, `threshold.relative_tolerance`), nunca em Python -- um Fact nunca contem limiar. Quem julga e a regra. A comparacao exata mantem o `diverged` no fact, porque 'os dois valores nao sao identicos' e observacao e nao limiar. (4) O MODO DE COMPARACAO VEM DO PLANO, nunca do resultado: senao o operador escolheria se o proprio numero dele e julgado exato ou com tolerancia. O `type` do resultado so e lido para check que o plano NAO pediu. (5) Tres estados de cobertura continuam DISTINTOS: check com valor entra na comparacao; `value: null` com `unavailable_reason` vira `unresolved` e NAO conta como reportado; chave ausente de `checks` e cobertura faltante. 'Nao medi' nunca vira zero. (6) Divergencia dentro da tolerancia nao e prova de igualdade: e ausencia de prova de diferenca.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `after_path` | string | sim | Resultado medido DEPOIS, no mesmo contrato. |
| `before_path` | string | sim | Resultado medido ANTES: JSON `{"target", "checks"}`, cada check um objeto `{"value": <numero\|mapa\|null>}`. `value: null` exige `unavailable_reason`; check nao medido fica AUSENTE de `checks`, nunca zero. |
| `plan_path` | string | sim | Arquivo gravado por `sparkforge_funcval_plan`. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |
| `out_path` | string | não | Onde gravar a comparacao (JSON de facts), que e o que `sparkforge_judge` le como `facts`. OPCIONAL, ao contrario do `out_path` do plano: o plano e a entrada do proximo verbo, esta e uma saida terminal. O arquivo traz a lista COMPLETA e nunca a pagina -- `limit` corta o `structuredContent`, nao o arquivo, e julgar a primeira pagina como se fosse a comparacao e o defeito que a SF-FVAL-005 acusa no dado do operador. |

## Na CLI

[`sparkforge funcval compare`](../cli/funcval.md)

## Capacidade

compare the before and after measurements against the plan

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
