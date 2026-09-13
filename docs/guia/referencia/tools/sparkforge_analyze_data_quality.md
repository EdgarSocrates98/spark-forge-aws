<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_data_quality`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de VALIDACAO DE DADO do proprio codigo PySpark (`.py` do repositorio, nunca API da AWS): onde cada check roda, o que ele custa e se ele tem consequencia. Reconhece tres formas pela FORMA do codigo, nunca por lista de nomes -- o check artesanal (`df.filter(...).count()`), a `VerificationSuite` do PyDeequ e a validacao do Great Expectations. `dq.check` carrega framework, tipo, alvo, `position_vs_write` (a validacao roda antes ou depois de o dado ser publicado), `target_persisted`, `action_after_check` e quantos checks incidem sobre o mesmo alvo; `dq.enforcement` so aparece quando a consequencia esta PROVADA (`raise`, `sys.exit`, `assert`) -- no escopo do check, ou UM salto adiante no corpo de um helper do mesmo modulo, e ai `attrs.via` nomeia o helper --, e a AUSENCIA dele e o sinal de validacao sem dente; `dq.module_analyzed` prova que o modulo foi lido, para que 'nenhum check' nao se confunda com 'nao analisei'. NAO JULGA O DADO: nao diz se a tabela esta correta, se um check reprovaria, nem quantas linhas violam a regra -- isso e trabalho da ferramenta de DQ em execucao. Diz apenas ONDE a validacao esta no codigo, o que ela alcanca e o que ela deixa passar. Nao aplica limiar, nao atribui severidade e nao adivinha alvo: alvo que a AST nao resolve (DataFrame anonimo, helper que monta a cadeia a partir do nome da tabela) e cadeia de consequencia mais longa que um salto viram `dq.unresolved` com `reason`, contados como ponto cego em vez de presumidos resolvidos.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo .py ou diretorio com codigo PySpark. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze data-quality`](../cli/analyze.md)

## Capacidade

extract facts about data validation in PySpark code

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
