---
sdd: 1
feature: CRITERIO_DE_DOMINIO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/CRITERIO_DE_DOMINIO/design.md
  sha256: "a3dffb1296db0d515e7496b2846dd86d635bb904837439203ab8891135f4f387"
tasks:
  - id: T1
    files: [tests/test_criterio_de_dominio.py, agents/sf-orchestrator.md, skills/agentic-orchestration/SKILL.md, agents/spark-performance-architect.md, rules/catalog/routing.yaml, config/agents.yaml, tests/test_canonical_registry.py, knowledge/tool-specialization-matrix.md, knowledge/offline-manifest.json, fixtures/knowledge_drift/filtro_por_url/expected/result.json, scripts/sync_skills.py, tests/test_sync_render.py, manifest.json, docs/surface.lock.json, docs/guia/referencia/agents/README.md, docs/claims.lock.json]
    covers: [AC1, AC2, AC3, AC4, AC5, AC7]
    test: {path: tests/test_criterio_de_dominio.py, name: test_todo_coordenador_tem_rota_por_artefato}
  - id: T2
    files: [tests/test_criterio_de_dominio.py, docs/gates-por-mudanca.md, CLAUDE.md, AGENTS.md, docs/guia/05-agents-e-skills.md, docs/guia/usos/iceberg-e-parquet.md, docs/operations-guide.md, docs/teams-catalog.md, docs/vnext/AGENT-CATALOG.md, docs/agentic-evolution.md, knowledge/domain-tool-matrix.md, docs/superpowers/STATUS.md, README.md, docs/guia/12-espelhos-e-dependencias.md, .devin/README.md, docs/claims.lock.json]
    covers: [AC6, AC8, AC9]
    test: {path: tests/test_criterio_de_dominio.py, name: test_criterio_escrito_e_apontado}
---

# CRITERIO_DE_DOMINIO — plano

Regras: as de `C:\Users\edgar\AppData\Local\Temp\claude\E--projetos-spark-forge-aws\aecdc55f-7550-4610-801b-0b1e6d24fd0a\scratchpad\contexto_sfstubs.md`
(valem iguais aqui: edição por ferramenta, LF, backup do `.claude/agents/README.md`
antes de `sync_skills.py`, commit por `git commit -F`, gate de lastro, um comando por
vez), branch `sdd/criterio-de-dominio`.

Duas tarefas: o gate e a remoção no mesmo commit (o teste de rota fica vermelho até os
sete saírem, e `test_there_is_at_least_one_route_per_coordinator` fica vermelho se as
rotas saem antes deles), depois o texto.

## T1 — o gate, e o que só o nome alcançava

1. Teste, em `tests/test_criterio_de_dominio.py` (arquivo novo):

```python
"""Dominio entra por artefato coletavel, nunca por nome.

Uma area so existe com regra que julga fact emitido por extrator, e um coordenador so
existe com area que julga e com rota que um finding ou fact dispara. Criterio escrito
em docs/gates-por-mudanca.md, secao "Criterio de dominio: artefato antes de nome".
"""
import re
from pathlib import Path

import yaml

from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"

SAIRAM_AGENTES = (
    "sf-analytics-specialist",
    "sf-graph-specialist",
    "sf-neptune-specialist",
    "sf-orchestrator",
    "sf-pyspark-specialist",
    "sf-storage-specialist",
    "sf-token-verifier",
)
SAIRAM_SKILLS = (
    "agentic-orchestration",
    "analyze-analytics",
    "analyze-graph-data",
    "design-neptune-graph",
    "token-efficient-agent",
)
SDD_TOOLS = ("sparkforge_sdd_check", "sparkforge_sdd_status", "sparkforge_sdd_stamp")


def _front(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1]) or {}


def _coordenadores() -> list[Path]:
    return sorted(AGENTS.glob("*.md"))


def _area(rule_id: str) -> str:
    return rule_id.rsplit("-", 1)[0]


def _areas_que_julgam() -> set[str]:
    return {
        _area(r["id"])
        for r in load_catalog()
        if r.get("executable", True) and not r.get("blocked_on")
    }


def _chaves(no) -> set[str]:
    if isinstance(no, dict):
        return set(no) | {k for v in no.values() for k in _chaves(v)}
    if isinstance(no, list):
        return {k for v in no for k in _chaves(v)}
    return set()


def _valores_de_caso(no) -> list[str]:
    if isinstance(no, dict):
        proprios = [str(no.get("contains", ""))] if "case" in no else []
        return proprios + [v for x in no.values() for v in _valores_de_caso(x)]
    if isinstance(no, list):
        return [v for x in no for v in _valores_de_caso(x)]
    return []


def _por_artefato(rota: dict) -> bool:
    when = rota.get("when")
    if _chaves(when) & {"findings_area", "fact"}:
        return True
    casos = _valores_de_caso(when)
    return bool(casos) and not any(re.fullmatch(r"__\w+__", c) for c in casos)


def _rotas() -> list[dict]:
    texto = (ROOT / "rules" / "catalog" / "routing.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(texto)["rules"]


def test_catalogo_nao_tem_area_de_coordenacao():
    inertes = [r["id"] for r in load_catalog() if r.get("executable", True) is False]
    assert not inertes, inertes


def test_toda_area_tem_regra_que_julga():
    todas = {_area(r["id"]) for r in load_catalog()}
    sem = sorted(todas - _areas_que_julgam())
    assert not sem, sem


def test_todo_coordenador_declara_area_que_julga():
    julgam = _areas_que_julgam()
    todas = {_area(r["id"]) for r in load_catalog()}
    for path in _coordenadores():
        areas = set(_front(path).get("rule_areas") or [])
        assert areas & julgam, path.name
        assert areas <= todas, (path.name, sorted(areas - todas))


def test_todo_coordenador_tem_rota_por_artefato():
    por_artefato = {rota.get("recommended_agent") for rota in _rotas() if _por_artefato(rota)}
    sem = sorted(p.stem for p in _coordenadores() if p.stem not in por_artefato)
    assert not sem, sem


def test_o_que_so_o_nome_alcancava_saiu():
    presentes = {p.stem for p in _coordenadores()}
    assert presentes.isdisjoint(SAIRAM_AGENTES), sorted(presentes & set(SAIRAM_AGENTES))
    skills = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()}
    assert skills.isdisjoint(SAIRAM_SKILLS), sorted(skills & set(SAIRAM_SKILLS))
    arquiteto = (AGENTS / "spark-performance-architect.md").read_text(encoding="utf-8")
    faltam = [t for t in SDD_TOOLS if t not in arquiteto]
    assert not faltam, faltam
```

2. Vermelho: `git add tests/test_criterio_de_dominio.py` e
   `python -m pytest tests/test_criterio_de_dominio.py -q` — dois `AssertionError`:
   `test_todo_coordenador_tem_rota_por_artefato` listando os sete, e
   `test_o_que_so_o_nome_alcancava_saiu`. Os três primeiros passam: o SF_STUBS já deixou
   o catálogo e os coordenadores conformes (anote isso no relato; eles ganham vermelho
   próprio no experimento do ship, sobre a árvore de `91643841`).

3. Código.
   - `agents/spark-performance-architect.md`, seção `## Mudança no job pede spec`: troque
     "`sparkforge sdd check` confere cada fase." por "`sparkforge sdd check`
     (`sparkforge_sdd_check`) confere cada fase, `sparkforge_sdd_status` diz onde cada
     feature está, e `sparkforge_sdd_stamp` recarimba a fase cujo upstream mudou."
   - `git rm -q` dos sete `agents/<nome>.md` de `SAIRAM_AGENTES` e dos sete
     `.codex/agents/<nome>.toml`.
   - `git rm -rq` das cinco `skills/<nome>` de `SAIRAM_SKILLS`.
   - `rules/catalog/routing.yaml`: apague os blocos AGENT-011, 012, 014, 015, 016, 027 e
     028 (script por linhas, sem re-serializar; o bloco começa em `  - id: AGENT-0NN` e
     termina antes da próxima `  - id:` ou de comentário de coluna 0).
   - `config/agents.yaml`: apague as entradas `- name: sf-orchestrator`,
     `sf-pyspark-specialist`, `sf-storage-specialist` e `sf-token-verifier` (cada uma vai
     do `- name:` até antes do próximo `- name:` ou da chave de coluna 0).
   - `tests/test_canonical_registry.py::test_registry_loading`: `sf-pyspark-specialist`
     passa a `sf-runtime-specialist`.
   - `knowledge/tool-specialization-matrix.md`: `sf-pyspark-specialist` passa a
     `pyspark-code-reviewer`, `sf-storage-specialist` a `iceberg-performance-engineer`;
     depois `python scripts/refresh_knowledge.py --offline --update`.
   - `scripts/sync_skills.py`: tire as cinco chaves de `SAIRAM_SKILLS` das tabelas em que
     estiverem (`DISPATCHABLE_SKILLS`, `NON_DISPATCHABLE_SKILLS`).
   - `manifest.json`: tire as cinco da lista `skills`.
   - Espelhos: backup do README, `python scripts/sync_skills.py`, devolva o README.
   - `tests/test_sync_render.py`: `RELACAO_MEDIDA` igual a
     `sync_skills.coordinators_by_skill()` (tire as cinco chaves e os sete das tuplas), e a
     tabela de `test_agent_so_aparece_onde_ha_um_coordenador_so` igual ao que o sync mediu.
   - `python scripts/gen_reference_docs.py`, `python scripts/check_surface_lock.py --update`
     (anote os bytes).
   - `python scripts/regen_fixtures.py filtro_por_url` e confira com
     `git diff -- fixtures/knowledge_drift`: só saem linhas `agents/<um dos sete>.md`.
     Qualquer outra mudança: pare e relate.

4. Verde: `python -m pytest tests/test_criterio_de_dominio.py -q`, depois, um de cada vez:
   `python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py tests/test_sync_render.py tests/test_skill_content.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_canonical_registry.py tests/test_sf_stubs.py -q`
   e `python -m pytest tests/test_harness_authorization.py tests/test_platform_compilers.py tests/test_knowledge_drift.py tests/test_offline_expansion.py -q`
   (confira os nomes com `ls tests | grep -iE "drift|harness_auth|platform_comp"`). Teste
   com lista literal que cair por nome removido: tire só o nome e relate como desvio.
5. `python scripts/check_vnext_claims.py` (arquivo `.py` novo; remedie por id), backup do
   README e `python scripts/sync_skills.py --check` e devolva,
   `python -m ruff check sparkforge scripts tests`.
6. Commit: `refactor(agents): gate domains on artifacts; drop coordinators only a name reached`,
   com 7 agentes, 5 skills e 7 rotas a menos, e os bytes da superfície.

## T2 — o critério escrito, documentos e números

1. Teste, em `tests/test_criterio_de_dominio.py` (o `import re` já está lá desde a T1):

```python
SECAO = "## Critério de domínio: artefato antes de nome"
VIVOS = (
    "AGENTS.md",
    "docs/guia/05-agents-e-skills.md",
    "docs/guia/usos/iceberg-e-parquet.md",
    "docs/operations-guide.md",
    "docs/teams-catalog.md",
    "docs/vnext/AGENT-CATALOG.md",
    "docs/agentic-evolution.md",
    "knowledge/domain-tool-matrix.md",
    "knowledge/tool-specialization-matrix.md",
    "config/agents.yaml",
)


def test_criterio_escrito_e_apontado():
    gates = (ROOT / "docs" / "gates-por-mudanca.md").read_text(encoding="utf-8")
    assert SECAO in gates
    inicio = gates.index(SECAO)
    fim = gates.find("\n## ", inicio + 1)
    secao = gates[inicio:fim]
    assert "tests/test_criterio_de_dominio.py" in secao
    for arquivo in ("CLAUDE.md", "AGENTS.md"):
        texto = (ROOT / arquivo).read_text(encoding="utf-8")
        assert "docs/gates-por-mudanca.md" in texto and "artefato" in texto.lower(), arquivo


def test_documento_vivo_nao_cita_o_que_saiu():
    for rel in VIVOS:
        texto = (ROOT / rel).read_text(encoding="utf-8")
        citados = [
            nome
            for nome in SAIRAM_AGENTES + SAIRAM_SKILLS
            if re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", texto)
        ]
        assert not citados, (rel, citados)
```

2. Vermelho: `python -m pytest tests/test_criterio_de_dominio.py -k "escrito or vivo" -q`
   — `AssertionError` na seção ausente e em `AGENTS.md`.
3. Texto.
   - `docs/gates-por-mudanca.md`: seção nova logo antes de
     `## Acrescentar uma ÁREA nova`:

```markdown
## Critério de domínio: artefato antes de nome

Domínio novo entra por **artefato coletável**, nunca por nome de agente. Três portas,
todas travadas por `tests/test_criterio_de_dominio.py`:

| nível | exige | teste |
|---|---|---|
| área | ao menos uma regra executável e sem `blocked_on`; nenhuma regra `executable: false` no catálogo commitado | `test_toda_area_tem_regra_que_julga`, `test_catalogo_nao_tem_area_de_coordenacao` |
| coordenador | ao menos uma área de `rule_areas` com regra que julga | `test_todo_coordenador_declara_area_que_julga` |
| rota | ao menos uma rota em `routing.yaml` que dispara por `findings_area` ou `fact`; rota que só lê `scope.entrypoints` (`__agentic_*__`) não conta | `test_todo_coordenador_tem_rota_por_artefato` |

A ordem é a do artefato: primeiro o extrator que emite o fact, depois a regra que o julga,
depois o coordenador que sabe quando investigá-la. Domínio que ainda não tem artefato
(Airflow, DynamoDB, Kinesis, Lambda, Step Functions) não ganha agente nem área: ganha
`unresolved` nomeando o artefato que falta. Foi por essa porta que 35 áreas e 26
coordenadores entraram sem julgar nada, e saíram em 2026-09-19 (`docs/sdd/SF_STUBS/`,
`docs/sdd/CRITERIO_DE_DOMINIO/`).
```

   - `CLAUDE.md`, seção `## Verificação antes de fechar`, logo depois da linha que começa
     com `- Área de regra nova precisa de rota`: acrescente
     `- Domínio novo entra por artefato, nunca por nome de agente: critério e gate em
     \`docs/gates-por-mudanca.md\`, seção *Critério de domínio*.`
     `AGENTS.md`: a mesma linha em inglês na seção equivalente (procure a linha sobre
     rota de área nova; se não houver, no fim da seção de verificação):
     `- A new domain enters through a collectable artifact, never through an agent name:
     criterion and gate in \`docs/gates-por-mudanca.md\` (section *Critério de domínio*).`
   - Documentos de `VIVOS`: nome que saiu vira o dono novo (PySpark e grafos:
     `pyspark-code-reviewer`; Iceberg e Parquet: `iceberg-performance-engineer`; qualidade
     e analytics: `data-quality-reviewer`; orquestração e SDD: `spark-performance-architect`)
     ou sai, mantendo o texto coerente. Em `AGENTS.md`, a lista de coordenadores `sf-*`
     fica com os quatro que existem.
   - Números: `docs/superpowers/STATUS.md` ganha leitura nova na frente, no padrão das
     anteriores, nas linhas de coordenadores (19 para 12), skills (56 para 51), rotas
     (47 para 40) e skills que declaram despacho (remeça); `README.md`,
     `docs/guia/05-agents-e-skills.md`, `docs/guia/12-espelhos-e-dependencias.md` e
     `.devin/README.md` acompanham. `python scripts/refresh_knowledge.py --offline --update`
     se tocou knowledge.
4. Verde: o comando do passo 2, e
   `python -m pytest tests/test_criterio_de_dominio.py tests/test_bootstrap_budget.py tests/test_reference_docs.py tests/test_offline_expansion.py tests/test_docs_coverage.py tests/test_status_numbers_gate.py -q`.
5. `python scripts/check_status_numbers.py --strict`, `python scripts/check_vnext_claims.py`
   (remedie por id), `python -m ruff check sparkforge scripts tests`.
6. Commit: `docs: write the domain criterion and point to it`.
