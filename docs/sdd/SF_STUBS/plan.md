---
sdd: 1
feature: SF_STUBS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SF_STUBS/design.md
  sha256: "b7fbc3837368426f28d89ce589daa7f25af6ef920f273ac738f74753a64941a9"
tasks:
  - id: T1
    files: [tests/test_sf_stubs.py, agents/pyspark-code-reviewer.md, agents/iceberg-performance-engineer.md, agents/data-quality-reviewer.md, sparkforge/findings/schemas/business_rule.schema.json, tests/test_sync_render.py, docs/guia/referencia/agents/README.md, docs/surface.lock.json, docs/claims.lock.json]
    covers: [AC4]
    test: {path: tests/test_sf_stubs.py, name: test_conteudo_real_muda_de_dono}
  - id: T2
    files: [tests/test_sf_stubs.py, rules/catalog/agentic-sf-agents.yaml, rules/catalog/routing.yaml, agents/sf-airflow-specialist.md, agents/sf-analytics-specialist.md, skills/design-airflow-pipelines/SKILL.md, sparkforge/economy/router.py, scripts/sync_skills.py, tests/test_sync_render.py, manifest.json, docs/surface.lock.json, docs/guia/referencia/agents/README.md, fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, evals/holdout/config_por_caminho_indireto/expected/assessment.json, docs/superpowers/STATUS.md, README.md, docs/guia/07-conhecimento-e-catalogo.md, docs/claims.lock.json]
    covers: [AC1, AC2, AC3, AC5, AC6, AC7]
    test: {path: tests/test_sf_stubs.py, name: test_todo_sf_declara_area_que_julga}
  - id: T3
    files: [tests/test_sf_stubs.py, AGENTS.md, docs/guia/05-agents-e-skills.md, docs/guia/usos/athena-e-sql.md, docs/guia/usos/iceberg-e-parquet.md, docs/teams-catalog.md, docs/operations-guide.md, docs/vnext/AGENT-CATALOG.md, docs/vnext/DEMOS.md, knowledge/domain-tool-matrix.md, knowledge/offline-manifest.json, docs/delivery-report.md, docs/agentic-expansion.md, docs/harness/MIGRATIONS-GLUE-GAP.md, docs/claims.lock.json]
    covers: [AC8]
    test: {path: tests/test_sf_stubs.py, name: test_documento_vivo_nao_cita_o_que_saiu}
---

# SF_STUBS — plano

Regras: as de `C:\Users\edgar\AppData\Local\Temp\claude\E--projetos-spark-forge-aws\aecdc55f-7550-4610-801b-0b1e6d24fd0a\scratchpad\contexto.md`
(edição por ferramenta, LF, commit por `git commit -F` com as duas linhas de
atribuição, gate de lastro antes de commit com `.py` novo), branch `sdd/sf-stubs`,
pouca memória: um comando por vez, nunca os lotes.

**Agente se edita na fonte `agents/<nome>.md` e skill em `skills/<nome>/`**; os espelhos
saem de `python scripts/sync_skills.py`. Esse script APAGA o
`.claude/agents/README.md` não rastreado: antes de rodá-lo,
`cp .claude/agents/README.md "$TEMP/claude_agents_README.bak.md"`, e depois
`cp "$TEMP/claude_agents_README.bak.md" .claude/agents/README.md`. O mesmo vale
depois de `tests/test_agents_parity.py`. O README nunca entra no `git add`.

Por que três tarefas e não seis: `tests/test_router_agents.py::test_there_is_at_least_one_route_per_coordinator`
fica vermelho se as rotas saem antes dos agentes, `tests/test_agent_coverage.py::test_no_area_is_orphan`
se os agentes saem antes das áreas, `test_every_declared_area_exists_in_the_catalog`
se as áreas saem antes dos agentes, e `tests/test_docs_coverage.py` (o `rule_count` do
`manifest.json`) e os goldens de assessment se o catálogo muda sem eles. Rotas, agentes,
áreas, skills e registros saem no mesmo commit (T2).

## T1 — o conteúdo real muda de dono

1. Teste, em `tests/test_sf_stubs.py` (arquivo novo):

```python
"""A camada sf-* sem area oca: o catalogo so julga, e o conteudo real mudou de dono."""
import re
from pathlib import Path

import yaml

from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"

OCOS = (
    "sf-agent-builder",
    "sf-agent-evaluation-specialist",
    "sf-airflow-specialist",
    "sf-athena-specialist",
    "sf-context-engineer",
    "sf-cost-reviewer",
    "sf-data-architect",
    "sf-dynamodb-specialist",
    "sf-evidence-verifier",
    "sf-functional-rules-specialist",
    "sf-iceberg-specialist",
    "sf-kinesis-specialist",
    "sf-lambda-serverless-specialist",
    "sf-lineage-specialist",
    "sf-memory-engineer",
    "sf-parquet-specialist",
    "sf-s3-specialist",
    "sf-schema-registry-specialist",
    "sf-step-functions-specialist",
)
SKILLS_QUE_SAIRAM = (
    "design-agent-systems",
    "design-airflow-pipelines",
    "design-dynamodb-model",
    "design-lambda-serverless",
    "design-step-functions-orchestration",
    "engineer-agent-context",
    "engineer-agent-memory",
    "optimize-athena-queries",
    "optimize-iceberg-tables",
    "verify-agent-evidence",
)
CODE_TOOLS = (
    "sparkforge_code_status",
    "sparkforge_code_sync",
    "sparkforge_code_search",
    "sparkforge_code_symbol",
    "sparkforge_code_export",
    "sparkforge_code_shape",
    "sparkforge_code_path",
    "sparkforge_code_context",
    "sparkforge_code_read",
)


def _front(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1]) or {}


def test_conteudo_real_muda_de_dono():
    revisor = (AGENTS / "pyspark-code-reviewer.md").read_text(encoding="utf-8")
    faltam = [t for t in CODE_TOOLS if t not in revisor]
    assert not faltam, faltam
    iceberg = AGENTS / "iceberg-performance-engineer.md"
    assert "sparkforge_iceberg_assess_upgrade" in iceberg.read_text(encoding="utf-8")
    assert "iceberg-v3-readiness" in (_front(iceberg).get("skills") or [])
    dq = _front(AGENTS / "data-quality-reviewer.md")
    assert "analyze-functional-rules" in (dq.get("skills") or [])
```

2. Vermelho: `python -m pytest tests/test_sf_stubs.py::test_conteudo_real_muda_de_dono -q`
   — `AssertionError` listando as nove `sparkforge_code_*`.

3. Código.
   - `agents/pyspark-code-reviewer.md`: copie a seção `## Índice de código` inteira de
     `agents/sf-context-engineer.md` (do título até a linha antes de `## Não faz`) e
     cole-a logo antes da seção `## Não faz` do revisor.
   - `agents/iceberg-performance-engineer.md`: acrescente `  - iceberg-v3-readiness` ao
     fim da lista `skills:` do frontmatter, e copie a seção
     `## Subir o format version da tabela` de `agents/sf-iceberg-specialist.md` para logo
     antes da seção `## Não faz`.
   - `agents/data-quality-reviewer.md`: acrescente `  - analyze-functional-rules` ao fim
     da lista `skills:`.
   - `sparkforge/findings/schemas/business_rule.schema.json`: na `description` da raiz,
     troque `sf-functional-rules-specialist` por `data-quality-reviewer`.
   - Espelhos: backup do README, `python scripts/sync_skills.py`, devolva o README.
   - `tests/test_sync_render.py::RELACAO_MEDIDA`: `iceberg-v3-readiness` passa a
     `("iceberg-performance-engineer", "sf-iceberg-specialist")` e
     `analyze-functional-rules` ganha `"data-quality-reviewer"` na tupla, em ordem
     alfabética. Confira contra `python -c "import sys;sys.path.insert(0,'scripts');import sync_skills;print(sync_skills.coordinators_by_skill())"`.
   - `python scripts/gen_reference_docs.py` e `python scripts/check_surface_lock.py --update`.

4. Verde: o comando do passo 2, e
   `python -m pytest tests/test_sync_render.py tests/test_agent_coverage.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_findings_validate.py -q`.
5. `python scripts/sync_skills.py --check`, `python scripts/check_vnext_claims.py`
   (`.py` novo: remedie por id), `python -m ruff check sparkforge scripts tests`.
6. Commit: `refactor(agents): move the code index, Iceberg upgrade and functional rules to their owners`,
   com os bytes da superfície no corpo.

## T2 — a camada oca sai

1. Teste, em `tests/test_sf_stubs.py`:

```python
def _areas_que_julgam() -> set[str]:
    return {r["id"].rsplit("-", 1)[0] for r in load_catalog() if r.get("executable", True)}


def _findings_areas(no) -> list[str]:
    if isinstance(no, dict):
        achadas = [no["findings_area"]] if "findings_area" in no else []
        return achadas + [a for v in no.values() for a in _findings_areas(v)]
    if isinstance(no, list):
        return [a for v in no for a in _findings_areas(v)]
    return []


def test_catalogo_so_tem_regra_que_julga():
    catalogo = load_catalog()
    assert not list((ROOT / "rules" / "catalog").glob("agentic-sf-*.yaml"))
    assert [r["id"] for r in catalogo if r.get("executable", True) is False] == []
    assert len(catalogo) == 157


def test_todo_sf_declara_area_que_julga():
    presentes = {p.stem for p in AGENTS.glob("sf-*.md")}
    assert presentes.isdisjoint(OCOS), sorted(presentes & set(OCOS))
    julgam = _areas_que_julgam()
    for path in sorted(AGENTS.glob("sf-*.md")):
        areas = set(_front(path).get("rule_areas") or [])
        assert areas & julgam, path.name
        assert areas <= julgam, (path.name, sorted(areas - julgam))


def test_rota_aponta_para_agente_e_area_que_existem():
    rotas = yaml.safe_load(
        (ROOT / "rules" / "catalog" / "routing.yaml").read_text(encoding="utf-8")
    )["rules"]
    agentes = {p.stem for p in AGENTS.glob("*.md")}
    julgam = _areas_que_julgam()
    for rota in rotas:
        agente = rota.get("recommended_agent")
        if agente is not None:
            assert agente in agentes, (rota["id"], agente)
        fora = [a for a in _findings_areas(rota.get("when")) if a not in julgam]
        assert not fora, (rota["id"], fora)
```

2. Vermelho: `python -m pytest tests/test_sf_stubs.py -k "catalogo or todo_sf or rota" -q`
   — três `AssertionError`: os `agentic-sf-*.yaml` existem, os 19 existem, e a rota
   `AGENT-017` (primeira da lista) dispara por área oca.

3. Código, nesta ordem.
   - `git rm -q rules/catalog/agentic-sf-*.yaml` (35 arquivos).
   - `rules/catalog/routing.yaml`: apague as 54 rotas de D3 do design — AGENT-017 a 025,
     029 a 070, 072, 073 e 074. Cada rota é o bloco que começa na
     linha `  - id: AGENT-0NN` e termina antes da próxima `  - id:` ou do próximo
     comentário de coluna 0. Apague só o bloco; comentários de seção ficam.
     Confira depois: `python -c "import yaml;r=yaml.safe_load(open('rules/catalog/routing.yaml',encoding='utf-8'));print(sorted(x['id'] for x in r['rules'] if x['id'].startswith('AGENT')))"`
     não lista nenhum dos 54.
   - `git rm -q` dos 19 `agents/<nome>.md` da constante `OCOS`.
   - Nos 11 `agents/sf-*.md` que ficam, reescreva a linha `rule_areas: [...]` sem as
     áreas que não estão em `_areas_que_julgam()`. Resultado esperado:
     `sf-analytics-specialist` `[SF-DQ]`; `sf-graph-specialist` `[SF-GRAPH]`;
     `sf-lake-formation-specialist` `[SF-LF, SF-XACC]`; `sf-neptune-specialist`
     `[SF-GRAPH]`; `sf-security-reviewer` `[SF-KMS, SF-IAM]`; `sf-storage-specialist`
     `[SF-ICE, SF-PQ]`; `sf-terraform-specialist` `[SF-NET]`; `sf-token-verifier`
     `[SF-DQ]`; `sf-orchestrator`, `sf-pyspark-specialist` e `sf-runtime-specialist`
     ficam como estão.
   - `git rm -rq` das 10 `skills/<nome>` de `SKILLS_QUE_SAIRAM`.
   - `scripts/sync_skills.py::DISPATCHABLE_SKILLS`: apague as 10 chaves de
     `SKILLS_QUE_SAIRAM`.
   - `sparkforge/economy/router.py::specialist_keywords`: apague as entradas
     `"athena"`, `"dynamodb"`, `"step functions"` e `"kinesis"`.
   - `manifest.json`: tire as 10 skills da lista `skills`, e `knowledge_base.rule_count`
     passa a `157`.
   - Espelhos: backup do README, `python scripts/sync_skills.py`, devolva o README.
   - `tests/test_sync_render.py::RELACAO_MEDIDA`: apague as chaves das 10 skills e tire os
     19 agentes de toda tupla, até a constante igualar
     `sync_skills.coordinators_by_skill()` (mesmo comando de T1).
   - `python scripts/gen_reference_docs.py` e `python scripts/check_surface_lock.py --update`.
   - Goldens de assessment: `python scripts/regen_fixtures.py glue_40_para_60_salto_longo glue_51_para_60_iceberg_ansi glue_60_fgac_com_jar config_por_caminho_indireto lote_misto_iceberg_parquet`.
     Confira com `git diff --stat -- fixtures/scenarios evals/holdout` e
     `git diff -- fixtures/scenarios evals/holdout | grep '^[-+] '`: só `catalog_rules`
     (192 para 157), a contagem de regras sem guarda (166 para 131) e a frase
     `statement` que as repete. Qualquer outra linha é achado que mudou: pare e relate.
   - Números: `README.md` linha 46 e `docs/guia/07-conhecimento-e-catalogo.md` linha 38
     passam a dizer 157 regras, todas executáveis. Em `docs/superpowers/STATUS.md`, as
     linhas das tabelas que publicam 192 e 157 de 192 (linhas 52 e 56 hoje) ganham a
     leitura nova na frente, no padrão das leituras anteriores: "**157**, todas
     executáveis — as 35 áreas de coordenação da expansão agêntica saíram em 2026-09-19
     (feature `docs/sdd/SF_STUBS/`). Leitura anterior de **192**, ...". Agents e skills
     na tabela *Números correntes*, se houver linha: a medida nova.
   - `python scripts/check_status_numbers.py --strict` e
     `python scripts/check_vnext_claims.py`: remedie pela lista de ids da saída.

4. Verde: o comando do passo 2, e
   `python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py tests/test_sync_render.py tests/test_skill_content.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_rules_loader.py tests/test_fixtures_kind_coverage.py tests/test_rule_scope_by_nature.py tests/test_status_numbers_gate.py tests/test_vnext_claims.py -q`,
   depois `python -m pytest tests/test_fixtures_scenarios.py tests/test_evals_holdout.py -q`
  . Teste com
   lista literal de área ou de agente que cair: tire dela os nomes que saíram e registre no
   relatório como desvio.
5. `python scripts/sync_skills.py --check`, `python -m ruff check sparkforge scripts tests`.
6. Commit: `refactor(agents): remove the hollow sf-* layer`, com no corpo 35 áreas, 19
   agentes, 54 rotas e 10 skills a menos, 192 para 157 regras, e os bytes da superfície.

## T3 — documentos

1. Teste, em `tests/test_sf_stubs.py`:

```python
VIVOS = (
    "AGENTS.md",
    "docs/guia/05-agents-e-skills.md",
    "docs/guia/usos/athena-e-sql.md",
    "docs/guia/usos/iceberg-e-parquet.md",
    "docs/teams-catalog.md",
    "docs/operations-guide.md",
    "docs/vnext/AGENT-CATALOG.md",
    "docs/vnext/DEMOS.md",
    "knowledge/domain-tool-matrix.md",
)


def test_documento_vivo_nao_cita_o_que_saiu():
    for rel in VIVOS:
        texto = (ROOT / rel).read_text(encoding="utf-8")
        citados = [
            nome
            for nome in OCOS + SKILLS_QUE_SAIRAM
            if re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", texto)
        ]
        assert not citados, (rel, citados)
```

2. Vermelho: `python -m pytest tests/test_sf_stubs.py::test_documento_vivo_nao_cita_o_que_saiu -q`
   — `AssertionError` em `AGENTS.md`.
3. Texto. Em cada documento de `VIVOS`, onde ele cita um nome que saiu: se a frase é
   sobre um domínio que ficou com outro dono (Athena, Iceberg, Parquet, S3, índice de
   código, regras funcionais), troque pelo dono novo (`athena-query-optimizer`,
   `iceberg-performance-engineer`, `sf-storage-specialist`, `pyspark-code-reviewer`,
   `data-quality-reviewer`); se é sobre domínio sem artefato (Airflow, DynamoDB, Kinesis,
   Lambda, Step Functions, arquitetura de dados, agentes, memória, contexto, evidência),
   tire a menção. `knowledge/domain-tool-matrix.md`: reescreva a frase única para citar só
   coordenadores que existem; depois `python scripts/refresh_knowledge.py --offline --update`
   para o `knowledge/offline-manifest.json`.
   Nos três históricos (`docs/delivery-report.md`, `docs/agentic-expansion.md`,
   `docs/harness/MIGRATIONS-GLUE-GAP.md`), acrescente logo abaixo do título:

```markdown
> **Desvio (2026-09-19, feature `docs/sdd/SF_STUBS/`):** as 35 áreas `agentic-sf-*`, os
> 19 agentes `sf-*` que só as declaravam e 10 skills sem artefato saíram do repositório.
> Este documento é registro histórico e cita nomes que não existem mais.
```

4. Verde: o comando do passo 2, e
   `python -m pytest tests/test_bootstrap_budget.py tests/test_offline_expansion.py tests/test_reference_docs.py -q`.
5. `python scripts/check_vnext_claims.py` (AGENT-CATALOG e DEMOS são auditados, e o
   MIGRATIONS-GLUE-GAP também: remedie por id, preservando a contagem de linhas), e
   `python scripts/check_status_numbers.py --strict`.
6. Commit: `docs: stop citing the removed sf-* agents and skills`.
