# MCP pagination audit — superficies de enumeracao

Auditoria da superficie MCP para o final-hardening: quais ferramentas
paginam, quais sao estruturalmente limitadas e quais podem devolver
payload sem teto. Classificacao resultante: um item de BACKLOG com
gatilho; todo o resto ja tem teto ou pagina.

- Auditado em: 2026-10-06
- Mecanismo existente: `paginate_items` / `next_cursor` / `page_size` em
  `sparkforge/adapters/_core.py` (call sites ~1016, 1078, 1385, 1443,
  3935, 5436, 6075) — usado pelos verbos `analyze_*` e fatias de facts.

## Pagina (cursor real)

- `analyze_*` — fatias de facts via `_facts_page` + `paginate_items`:
  devolvem `items`, `next_cursor` e `total` observado.
- `memory_recall` — `limit=5` fixo por chamada (teto duro, nao cursor).

## Limitado por construcao (teto estrutural ou cap explicito)

| superficie | teto |
|---|---|
| `code_search` | `CODE_SEARCH_MAX_LIMIT` |
| `code_symbol`, `code_export`, `code_path`, `code_context`, `code_shape` | estruturas de grafo/detalhe limitadas pelo proprio tamanho do indice |
| scores, budgets, decisoes | objeto unico por run/decision_id — nao enumeram |
| tool catalog / capability matrix | lista fechada por versao |

## Sem teto — BACKLOG

- `agentops_timeline` — devolve **todos os spans do run** sem cap nem
  cursor. O payload cresce com o numero de spans de um unico run; um run
  patologico (loop, fan-out grande) pode devolver milhares de spans.

**Classificacao:** BACKLOG. Nao vira paginacao nesta onda porque o
payload vai pela janela MCP inteira e um cursor exigiria estado do lado
do adapter ou fatiamento por offset — trabalho real, nao hardening.

**Gatilho:** quando um consumidor real paginar um timeline (um run com
milhares de spans em producao, ou um cliente MCP que precise de streams
parciais), adicionar `offset`/`limit` + `next_cursor` sobre a mesma
convencao de `paginate_items` ja existente.

## Nota sobre criterio

"Pagina ou tem teto" nao significa "pequeno". A classificacao aqui mede
a ausencia de limite estrutural — um payload que cresce sem bound com o
dado do usuario e o risco; um objeto grande mas fechado por versao nao e.
