# SparkForge AWS — estado por fase

**Atualizado em:** 2026-07-31
**Commit de referência:** `bc53865` (merge da PR #1, `feat/fase2-desbloqueios`)
**Versão do pacote:** `0.4.0` — consistente em `pyproject.toml`, `manifest.json`,
`.claude-plugin/plugin.json` e `sparkforge.__version__`, e fixada por
`tests/test_docs_coverage.py::TestManifest::test_version_is_0_4_0`.

Este arquivo é a fonte da verdade sobre **onde o projeto está**. Os specs e plans
em `specs/` e `plans/` são registro histórico de decisão: descrevem o que se
pretendia numa data, não o repositório de hoje. Quando um número divergir, este
arquivo ganha.

---

## Números correntes

| Dimensão | Valor | Onde conferir |
|---|---|---|
| Testes | **1726** passando | `python -m pytest -q` |
| Extratores de facts | **13** | `sparkforge/facts/*.py` |
| Fact kinds distintos emitidos | **80** | união de `EMITTED_KINDS` |
| Regras de diagnóstico | **43** | `load_catalog()` |
| Regras bloqueadas (`blocked_on`) | **0** | `rules/catalog/*.yaml` |
| Regras com golden que dispara | **43 de 43** | `tests/test_fixtures_kind_coverage.py` |
| Rotas determinísticas | **16** (`ROUTE-001`…`ROUTE-016`) | `rules/catalog/routing.yaml` |
| Tools MCP | **28** | `sparkforge.adapters.tools.TOOLS` |
| Fixtures golden | **73** em 15 domínios | `fixtures/` |
| Pares de eval | 10 | `evals/fase0.xml` |

Regras por área: SF-PY 12, SF-UI 6, SF-GLUE 6, SF-ATH 5, SF-ICE 5, SF-PQ 5, SF-ENV 4.

Fixtures por domínio: `pyspark` 17, `iceberg` 8, `terraform` 7, `plan` 6,
`fusion` 5, `runtime` 5, `s3` 5, `sql` 4, `athena` 3, `catalog` 3, `consumers` 3,
`callgraph` 2, `infra_code` 2, `tfdiff` 2, `eventlog` 1.

---

## Fases

### Fase 0 — contratos, extração determinística e paridade — **CONCLUÍDA** (2026-07-30)

Documentos: [spec](specs/2026-07-29-sparkforge-fase0-design.md) ·
[plan](plans/2026-07-29-sparkforge-fase0.md) · errata na §18 do spec.

Entregou as seis camadas com fronteiras negativas (`facts/`, `rules/`,
`findings/`, `case/`, `collect/`, `adapters/`), o avaliador `expr` com whitelist
de nós AST, os contratos `Fact`/`Finding`/`RuntimeContext` com ordenação
determinística, o `case.yaml` com roteamento por dado, CLI + MCP, o plugin do
Claude Code, `AGENT_PROTOCOL.md`, `parity.yaml` e a suíte de eval.

Faixa de commits: `66fcb6f` … `7d51664`, fechada pelo merge `7cc739e`.

### Fase 1 — extratores restantes e coletores AWS — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-30-sparkforge-fase1-design.md) ·
[plan](plans/2026-07-30-sparkforge-fase1.md).

Doze extratores novos além de `pyspark_ast`, os coletores AWS, a etapa de fusão
de facts, e a superfície de CLI e MCP para cada um. Fecha com uma auditoria
(`bb72f9f`) que corrigiu seis defeitos, incluindo o transporte HTTP do MCP, que
era paridade afirmada e não testada.

Faixa de commits: `97b0818` … `bb72f9f`.

### Fase 2 (executada) — desbloqueio do catálogo — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-31-sparkforge-fase2-design.md) ·
[plan](plans/2026-07-31-sparkforge-fase2.md).

> **Atenção ao nome.** A "Fase 2" que o repositório executou (branch
> `feat/fase2-desbloqueios`) **não** é a Fase 2 do roadmap da §16 do spec da
> Fase 0. O roadmap chama de Fase 2 a expansão do knowledge e o
> `refresh_knowledge`. O que foi executado é o oposto: nenhuma regra nova, e sim
> a construção dos extratores que faltavam para que as regras já committadas
> parem de ser inertes.

Levou o catálogo de 5 regras com `blocked_on` e 3 sem golden positivo para
**0 bloqueadas e 43 de 43 provadas por fixture**, e travou os dois invariantes
que impedem a regressão.

Faixa de commits: `dc80efd` … `b44edd0`, merge `bc53865`.

### Fase 3 — integração profunda — **NÃO INICIADA**

Escopo da §16: export de Playbook/Knowledge para conta Devin, MCP HTTP
hospedado, marketplace de plugin, distribuição pip.

Parcial existente: o transporte HTTP funciona localmente
(`python -m sparkforge.adapters.mcp --transport http`) e é testado. Falta
hospedagem, export Devin e publicação em PyPI/marketplace.

### Fase 4 — rigor — **NÃO INICIADA**

Escopo da §16: gates fail-closed opcionais, benchmark automatizado antes/depois,
validação funcional automatizada (contagem, schema, chaves, agregados),
assinatura de relatório. `blocked_by` segue advisory, como a §5.5 da Fase 0
decidiu conscientemente.

---

## Dívidas abertas

| Dívida | Origem | Impacto |
|---|---|---|
| `refresh_knowledge` não existe | §16 Fase 2 do spec da Fase 0 | Atualização do knowledge é manual; nada garante que uma fonte com `retrieved: 2026-07-29` seja reconferida |
| Matriz de compatibilidade não é automatizada | §16 Fase 2 | `knowledge/glue/runtime-matrix.md` é parseada e comparada com `GLUE_MATRIX` (guarda de drift), mas ninguém a atualiza sozinha |
| Três eixos de versionamento parados em 1/1/0.4.0 | §12.2 do spec da Fase 0 | Fases 1 e 2 adicionaram 12 extratores e 18 tools sem bump. A próxima mudança de contrato ou de limiar tem que mexer nos três |
| Catálogo cobre 7 áreas, não as 18 skills | §16 Fase 2 | Skills sem regra correspondente continuam dependendo de prosa |
| Glue 3.0 na `GLUE_MATRIX` sem cobertura de fixture própria | Fase 1 | Usado só como lado negativo da fronteira do AQE |

## Como manter este arquivo honesto

Ao fechar uma fase:

1. Atualize a tabela **Números correntes** rodando os comandos da coluna direita.
2. Marque a fase e cole a faixa de commits.
3. Escreva o par spec + plan em `specs/` e `plans/` com a data do merge.
4. Se um número de um spec antigo ficou obsoleto, **não edite o spec** — acrescente
   a linha na seção de desvios dele (§18 no caso da Fase 0) e aponte para cá.
