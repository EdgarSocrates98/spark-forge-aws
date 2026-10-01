<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_controlm_jobs`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC) -- o JSON de definicao de job versionado no repositorio, o mesmo que `ctm build` valida e `ctm deploy` publica. Emite o folder e os sub-folders (`ctm.folder`), os jobs com `Type`/`Name`/`RunAs`/`Application`/`SubApplication` (`ctm.job`), o bloco `When` (`ctm.schedule`), as dependencias por evento e por `Flow.Sequence` (`ctm.dependency`), as acoes condicionais `Type: If` (`ctm.action`) e as variaveis de job (`ctm.variable`, com o valor REDIGIDO quando ele tem forma de credencial). LE CODIGO-FONTE, NUNCA EXECUCAO. Nada aqui diz se o job rodou, em quanto tempo, ou se a dependencia foi satisfeita -- isso e `run jobs:status`, outra API, e exige a instancia do Control-M. Nao chama a BMC. A VERSAO E DECLARADA, NUNCA INFERIDA. O JSON nao carrega a versao do Control-M que vai executa-lo -- os 44 blocos de *Job Properties* descrevem tipo, agendamento, dependencia, acao, recurso e identidade, e nenhum a nomeia. Com `version`, o extrator CRUZA as capacidades observadas com a matriz de `knowledge/controlm/` e emite o veredito ja decidido: `ctm.capability_supported`, `ctm.capability_incompatible` ou `ctm.capability_unresolved`. `ctm.version_declared` marca `source: operator_declaration` -- se a declaracao estiver errada, o veredito esta errado junto. SEM `version` O CRUZAMENTO NAO ACONTECE, e isso NAO e erro: os facts de inventario saem do mesmo jeito, e cada capacidade observada sai em `ctm.capability_unresolved` com `reason: version_not_declared` e `unblocked_by`. A regra `SF-CTM-001` fica pulada por `requires_facts`. O SILENCIO DA MATRIZ NUNCA E APROVACAO: capacidade que a matriz nao nomeia, versao acima do teto da faixa e versao que a fonte nao publica saem em `ctm.capability_unresolved` com a razao e a medida que a destrava -- nunca como compativel por omissao. Ausencia de achado `SF-CTM` significa que nada do que a matriz sustenta afirmar foi contrariado, e o que ficou sem resposta e contado em `capability_unresolved_count`. NAO VALIDA O JSON CONTRA O SCHEMA COMPLETO: `ctm build` faz isso e e da BMC. O que vira `ctm.unresolved` aqui e o que nao deu para LER.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo .json ou diretorio com definicoes Jobs-as-Code. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |
| `version` | string | não | A versao do Control-M AUTOMATION API do ambiente ALVO (`9.0.21.300`). DECLARACAO do operador, nao leitura do artefato. Opcional: sem ela o cruzamento com a matriz nao acontece e as capacidades observadas saem como recusa nomeada, em vez de silencio. Fora da faixa que a matriz sustenta, ou dentro dela sem a fonte publicar, tambem sai recusa nomeada -- nunca a resposta da versao vizinha. |

## Na CLI

[`sparkforge analyze controlm-jobs`](../cli/analyze.md)

## Capacidade

extract facts from a Control-M Jobs-as-Code definition

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
