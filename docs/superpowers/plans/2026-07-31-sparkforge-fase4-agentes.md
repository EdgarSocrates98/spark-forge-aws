# SparkForge Fase 4 — Coordenadores, Executores e Espelho: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** toda capacidade do toolkit alcançável a partir de um coordenador, em toda plataforma suportada — verificado por invariante de CI, não prometido em prosa. Hoje 21 das 29 tools MCP não são citadas em agente nenhum nem em skill nenhuma.

**Architecture:** três camadas sobre um estado só. Coordenadores (agentes Claude) decidem o QUE investigar por domínio; executores (subagentes Claude) fazem UMA função do loop de fase, com fronteira negativa explícita; `sparkforge playbook` emite a mesma decomposição em sequência para plataforma sem despacho de subagente. As três leem e escrevem `.sparkforge/case.yaml` — nenhuma guarda contexto próprio.

**Tech Stack:** markdown com frontmatter YAML (agentes), YAML declarativo (`routing.yaml`, `parity.yaml`), Python stdlib + PyYAML, pytest.

**Spec:** [`../specs/2026-07-31-sparkforge-fase4-agentes-design.md`](../specs/2026-07-31-sparkforge-fase4-agentes-design.md)

---

## Fatos do ambiente verificados antes de escrever este plano

Medidos, não copiados:

```
agentes           3        skills 18, todas declaradas por algum agente (0 orfas)
tools MCP        29        citadas em agente ou skill: 8   -> 21 ORFAS
areas de regra    9        SF-ATH CG ENV GLUE ICE PLAN PQ PY UI
skills/agente    17 / 10 / 3   (distribuicao torta)
rotas            16        em rules/catalog/routing.yaml
plataformas       4        claude_code, devin_desktop, devin_cli, copilot_ci
mecanismos        3        mcp, cli, files
testes         1883        5 skipped (procedencia, so sob o gate)
```

- Frontmatter de agente: `name`, `description`, `tools`, `skills` (lista). Corpo em markdown, sempre abrindo com **"Siga `AGENT_PROTOCOL.md`."**
- `tests/test_agents_parity.py` tem `NAMES` com os 3 nomes **fixos** — acrescentar agente sem tocar ali quebra `test_agents_dir_holds_all_three`.
- `scripts/sync_skills.py` espelha `agents/` para `.claude/agents/`, `.agents/agents/` e `.github/agents/*.agent.md`. Não injeta nada.
- `next_step(case, finding_ids, directory=None)` em `sparkforge/case/router.py:194` é puro e devolve `recommended_skill`. Rotas têm `id`, `phase_in`, `title`, `when`, `recommended_skill`, `reason`, e opcionais `missing_artifacts`/`collect_commands`.
- `routing.yaml` usa operadores declarativos: `absent`, `count_gt`, `equals`, `contains`, `any_where`. **Não** `expr` — a whitelist do avaliador proíbe `Call` e `In`.
- CLI: `_print` (linha 57) é o emissor único; handlers `_cmd_*`; `_DISPATCH` mapeia `(comando, subcomando)`; `_dispatch` monta `sub_action` de uma cadeia de `getattr(args, "<x>_action", None)`.

---

## File Structure

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `agents/glue-infra-reviewer.md` | Coordenador SF-GLUE + SF-ENV |
| `agents/athena-query-optimizer.md` | Coordenador SF-ATH + SF-PQ |
| `agents/pyspark-code-reviewer.md` | Coordenador SF-PY + SF-PLAN + SF-CG |
| `agents/executors/sf-inventory.md` | Mapeia artefatos; não extrai |
| `agents/executors/sf-extractor.md` | Roda `analyze`; não julga |
| `agents/executors/sf-judge.md` | Roda `judge`; não propõe mudança |
| `agents/executors/sf-verifier.md` | Tenta refutar P0/P1; não conserta |
| `agents/executors/sf-synthesizer.md` | Relatório e próximo passo |
| `sparkforge/case/playbook.py` | Decomposição de um coordenador em passos |
| `tests/test_agent_coverage.py` | Os três invariantes de cobertura |
| `tests/test_playbook.py` | Determinismo e fidelidade aos executores |

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `agents/*.md` (3 existentes) | Ganham bloco `executors:` no frontmatter |
| `rules/catalog/routing.yaml` | Rotas de coordenador |
| `sparkforge/adapters/_core.py`, `cli.py`, `tools.py` | Verbo e tool `playbook` |
| `parity.yaml` | Plataforma `codex`, mecanismo `playbook`, capacidade de coordenação |
| `manifest.json` | Tool nova |
| `tests/test_agents_parity.py` | `NAMES` derivado do disco, não literal |
| `scripts/sync_skills.py` | Espelhar `agents/executors/` |
| `README.md`, `AGENTS.md`, `AGENT_PROTOCOL.md`, `GUIA_DE_USO.md`, `PROMPT_INICIAL_MESTRE.md`, `STATUS.md` | Referenciar o que é novo |

---

## Task 1: O invariante de cobertura, antes de qualquer conteúdo

Primeiro de propósito. O teste tem que **falhar hoje**, listando as 21 tools órfãs — é ele que define o que as tasks seguintes precisam fechar, e sem ele a fase vira exercício de escrever markdown sem alvo.

**Files:**
- Create: `tests/test_agent_coverage.py`

- [ ] **Step 1: Escreva o teste**

> **Atenção ao `ids=`.** Use lista pré-computada, **nunca** `ids=lambda p: p.stem`.
> Com `parametrize` sobre lista vazia — o estado desta task, antes de `agents/executors/`
> existir — o pytest 8.x chama o callable sobre um sentinela interno e estoura
> `ValueError` **dentro do coletor**, abortando a coleta da suíte inteira em vez de
> pular o teste. Verificado em repro isolado: com `ids` como lista, o pytest apenas
> pula. `pyproject.toml` fixa `pytest>=8.0` sem teto, então o CI pega a mesma versão.


```python
# tests/test_agent_coverage.py
"""Cobertura de capacidade por coordenador, como invariante.

21 das 29 tools MCP nao eram citadas em agente nenhum nem em skill nenhuma
quando esta fase abriu. A causa nao foi descuido pontual: cada fase alargou a
superficie do toolkit sem alargar a orientacao, e NADA reprovava. Este arquivo
e o que reprova.

E a versao de orientacao do `pyspark.unresolved`: capacidade que existe e nao e
alcancavel nao e capacidade, e a diferenca entre "nao ha o que usar ali" e
"ninguem documentou" tem que aparecer.
"""
import re
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters.tools import TOOLS
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
EXECUTORS = AGENTS / "executors"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path.name} sem frontmatter"
    block = text.split("---", 2)[1]
    return yaml.safe_load(block) or {}


def coordinators() -> list[Path]:
    return sorted(p for p in AGENTS.glob("*.md"))


def executors() -> list[Path]:
    return sorted(p for p in EXECUTORS.glob("*.md"))


def _corpus_of(path: Path) -> str:
    """Texto do coordenador MAIS o das skills e executores que ele declara.

    Alcancavel A PARTIR de um coordenador, nao apenas escrito nele: e assim que
    um agente real chega a capacidade -- lendo o coordenador e seguindo o que
    ele manda abrir.
    """
    front = _frontmatter(path)
    text = path.read_text(encoding="utf-8")
    for skill in front.get("skills") or []:
        skill_file = ROOT / "skills" / skill / "SKILL.md"
        if skill_file.is_file():
            text += skill_file.read_text(encoding="utf-8")
    for executor in front.get("executors") or []:
        executor_file = EXECUTORS / f"{executor}.md"
        if executor_file.is_file():
            text += executor_file.read_text(encoding="utf-8")
    return text


class TestEveryToolIsReachable:
    def test_no_tool_is_orphan(self):
        """Falha listando as orfas -- mensagem acionavel, nao contagem."""
        reachable = "".join(_corpus_of(p) for p in coordinators())
        orphans = sorted(name for name in TOOLS if name not in reachable)
        assert not orphans, (
            f"{len(orphans)} de {len(TOOLS)} tools nao sao alcancaveis a partir de "
            f"nenhum coordenador: {orphans}. Cite a tool no coordenador, numa skill "
            f"que ele declare, ou num executor que ele despache."
        )


class TestEveryRuleAreaHasACoordinator:
    def test_no_area_is_orphan(self):
        areas = sorted({r["id"].rsplit("-", 1)[0] for r in load_catalog()})
        declared: set[str] = set()
        for path in coordinators():
            declared |= set(_frontmatter(path).get("rule_areas") or [])
        missing = sorted(set(areas) - declared)
        assert not missing, (
            f"areas de regra sem coordenador: {missing}. Toda area precisa de alguem "
            f"que saiba quando investiga-la."
        )

    def test_every_declared_area_exists_in_the_catalog(self):
        """Area declarada que nao existe e ponteiro para o nada."""
        areas = {r["id"].rsplit("-", 1)[0] for r in load_catalog()}
        for path in coordinators():
            for area in _frontmatter(path).get("rule_areas") or []:
                assert area in areas, f"{path.name} declara {area}, que nao existe"


class TestCoordinatorExecutorWiring:
    def test_every_declared_executor_exists(self):
        available = {p.stem for p in executors()}
        for path in coordinators():
            for executor in _frontmatter(path).get("executors") or []:
                assert executor in available, f"{path.name} declara {executor}, ausente"

    def test_every_executor_is_declared_by_someone(self):
        """Executor que ninguem despacha e codigo morto com cara de capacidade."""
        declared: set[str] = set()
        for path in coordinators():
            declared |= set(_frontmatter(path).get("executors") or [])
        orphans = sorted({p.stem for p in executors()} - declared)
        assert not orphans, f"executores que nenhum coordenador despacha: {orphans}"

    @pytest.mark.parametrize("path", executors(), ids=[p.stem for p in executors()])
    def test_every_executor_declares_its_negative_boundary(self, path):
        """A secao 4.2 da Fase 0 diz que a fronteira NEGATIVA e o mecanismo que
        garante o determinismo. Executor sem ela vira coordenador disfarcado."""
        text = path.read_text(encoding="utf-8")
        assert "## Não faz" in text, f"{path.name} sem secao `## Não faz`"


class TestHandoffContract:
    """Executor isolado nao e time; e cinco agentes repetindo trabalho.

    O que faz os executores trabalharem EM CONJUNTO nao e a ordem em que o
    coordenador os despacha -- e o estado que cada um deixa para o seguinte.
    Sem contrato de entrega, cada executor reconstroi o que o anterior ja sabia,
    e a decomposicao vira cinco investigacoes paralelas com o mesmo custo de uma
    sozinha, so que divergindo entre si.

    O estado compartilhado e `.sparkforge/case.yaml`: nenhum executor guarda
    contexto proprio, pela mesma razao que a Fase 0 pos o roteamento em dado --
    estado que sobrevive a troca de sessao, de modelo e de ferramenta.
    """

    @pytest.mark.parametrize("path", executors(), ids=[p.stem for p in executors()])
    def test_every_executor_declares_what_it_hands_over(self, path):
        text = path.read_text(encoding="utf-8")
        assert "## Entrega" in text, (
            f"{path.name} sem secao `## Entrega`. Sem dizer o que escreve no case, "
            f"o executor seguinte nao sabe o que pode assumir -- e reconstroi."
        )

    @pytest.mark.parametrize("path", executors(), ids=[p.stem for p in executors()])
    def test_every_executor_declares_what_it_expects(self, path):
        """A outra ponta do contrato: o que ele PRESSUPOE ja no case.

        `sf-inventory` e o unico que pode comecar do zero. Os demais dependem do
        anterior, e declarar isso e o que permite o coordenador saber que pulou
        um passo em vez de descobrir por resultado estranho.
        """
        text = path.read_text(encoding="utf-8")
        assert "## Pressupõe" in text, f"{path.name} sem secao `## Pressupõe`"

    def test_the_chain_closes(self):
        """O que um entrega, o seguinte pressupoe -- nenhum elo solto.

        Compara as chaves de case declaradas por cada executor na ordem do loop
        de fase. Uma chave pressuposta que ninguem entrega e um elo quebrado: o
        executor vai procurar no case algo que nunca foi escrito.
        """
        order = ["sf-inventory", "sf-extractor", "sf-judge", "sf-verifier", "sf-synthesizer"]
        delivered: set[str] = set()
        for name in order:
            text = (EXECUTORS / f"{name}.md").read_text(encoding="utf-8")
            expects = set(re.findall(r"`case\.([a-z_.]+)`", _section(text, "Pressupõe")))
            missing = expects - delivered
            assert not missing, (
                f"{name} pressupoe {sorted(missing)}, que nenhum executor anterior "
                f"entrega. Elo quebrado na cadeia."
            )
            delivered |= set(re.findall(r"`case\.([a-z_.]+)`", _section(text, "Entrega")))


def _section(text: str, title: str) -> str:
    """Corpo de uma secao `## <title>` ate a proxima `##` ou o fim."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""
```

- [ ] **Step 2: Rode e confirme que falha exatamente como esperado**

Run: `python -m pytest tests/test_agent_coverage.py -v`

Esperado: `test_no_tool_is_orphan` falha listando **21 tools**; os testes de área e de executor falham por `agents/executors/` não existir ainda.

Cole a lista das 21 no relatório — ela é o alvo das tasks 2 a 5.

- [ ] **Step 3: Commit**

```bash
git add tests/test_agent_coverage.py
git commit -m "test: invariante de cobertura de capacidade por coordenador"
```

O teste entra vermelho de propósito, e as tasks seguintes o fecham. Se o repositório exigir CI verde a cada commit, use `pytest.mark.xfail(strict=True)` nos três e remova na Task 6 — mas prefira deixar vermelho e fechar rápido: `xfail` esquecido é como um `blocked_on` que sobrevive ao extrator.

---

## Task 2: Os cinco executores

**Files:**
- Create: `agents/executors/sf-inventory.md`, `sf-extractor.md`, `sf-judge.md`, `sf-verifier.md`, `sf-synthesizer.md`

- [ ] **Step 1: `sf-inventory.md`**

```markdown
---
name: sf-inventory
role: executor
function: inventory
tools: Read, Grep, Glob, Bash
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

Você é executor. Faz **uma** função do loop de fase e devolve ao coordenador.

## Faz

Mapeia o terreno antes de qualquer análise:

1. `sparkforge_runtime_detect` — versão de Glue, Spark, Python, Iceberg, e divergências entre fontes.
2. `sparkforge_case_get` — estado do case, ou `sparkforge_case_open` se não existir.
3. `sparkforge_collect_verify` — quais artefatos já existem e estão íntegros.
4. Lista o que falta, com o comando exato de recoleta: `sparkforge_collect_event_log`,
   `sparkforge_collect_glue_job`, `sparkforge_collect_cloudwatch`,
   `sparkforge_collect_iceberg_metadata`, `sparkforge_collect_athena_workgroup`.

## Pressupõe

Nada. É o único executor que pode começar do zero — se o case não existir, ele o abre.

## Entrega

Escreve no case, com `sparkforge_case_update`:

- `case.runtime` — versões confirmadas e `detected_from`
- `case.runtime.divergences` — vazio, ou o conflito entre fontes
- `case.artifacts` — o que existe, com sha256 e origem
- `case.open_questions` — o que falta coletar, com o comando de recoleta

Sem isso, o extrator não sabe quais `analyze` fazem sentido rodar, e roda todos.

## Não faz

Não extrai fact. Não julga. Não recomenda mudança. Se você se pegar rodando `analyze`,
parou de ser inventário e virou extrator — devolva ao coordenador.

Divergência de runtime **não se resolve escolhendo uma fonte**: reporte, que ela vira
`SF-ENV-001`.
```

- [ ] **Step 2: `sf-extractor.md`**

```markdown
---
name: sf-extractor
role: executor
function: extract
tools: Read, Grep, Glob, Bash
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

Você é executor. Faz **uma** função do loop de fase e devolve ao coordenador.

## Faz

Produz facts ancorados, rodando o extrator certo para cada artefato:

| Artefato | Tool |
|---|---|
| código PySpark | `sparkforge_analyze_pyspark` |
| grafo de chamadas | `sparkforge_analyze_call_graph` |
| plano físico | `sparkforge_analyze_plan` |
| Spark event log | `sparkforge_analyze_event_log` |
| Terraform | `sparkforge_analyze_terraform` |
| diff de Terraform (PR) | `sparkforge_analyze_terraform_diff` |
| metadata Iceberg | `sparkforge_analyze_iceberg` |
| SQL literal | `sparkforge_analyze_sql` |
| schema do Glue Catalog | `sparkforge_analyze_catalog_schema` |
| workgroup Athena | `sparkforge_analyze_athena_workgroup` |
| listagem S3 | `sparkforge_analyze_s3_listing` |
| inventário de consumidores | `sparkforge_analyze_consumers` |

Depois, `sparkforge_fuse` — regras que cruzam SQL com schema do catálogo (SF-ATH) só
disparam sobre facts fundidos.

## Pressupõe

`case.runtime` confirmado e `case.artifacts` mapeado. Sem runtime, a guarda de versão
de qualquer regra falha fechada mais adiante e o julgamento sai vazio sem explicar por quê.

## Entrega

- `case.facts_index` — caminho, contagem e `by_kind`
- `case.open_questions` — atualizado com os pontos cegos que sobraram

**Reporte sempre os `*.unresolved`.** São a maquinaria de ponto cego: quando param de
contar, devolvem zero sem levantar erro, e o relatório finge cobertura total.

## Não faz

Não julga. Não aplica limiar. Não atribui severidade. O extrator não sabe que 41 s de
task é ruim — é a fronteira negativa da §4.2 da Fase 0, e é ela que garante que trocar
de modelo não muda a evidência.
```

- [ ] **Step 3: `sf-judge.md`**

```markdown
---
name: sf-judge
role: executor
function: judge
tools: Read, Bash
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

Você é executor. Faz **uma** função do loop de fase e devolve ao coordenador.

## Faz

1. `sparkforge_judge` sobre os facts, com o runtime confirmado.
2. Agrupa por severidade e por `rule_id`.
3. Para cada achado, consulta `sparkforge_rules_lookup` — limiar, guarda de versão, fonte
   com data, e `knowledge_refs` com o caminho **resolvido** dos arquivos citados. Abra por
   ali, nunca pelo caminho relativo do texto: num pacote instalado por pip o arquivo está
   dentro do `site-packages`. Fora de uma regra, use `sparkforge_knowledge_path`.
4. Registra no case com `sparkforge_case_update`.

## Pressupõe

`case.facts_index` populado. Julgar sem facts produz o vazio que parece
"nada encontrado" e na verdade é "nada foi extraído".

## Entrega

- `case.findings_index` — caminho, contagem e `by_severity`
- `case.skills_used` — a skill aplicada e o resultado

Regra pulada por guarda de versão **é informação**: reporte com o motivo, não omita.

## Não faz

Não propõe mudança de código. Não estima ganho. Não escreve relatório. Um achado que
você não conseguiria sustentar com `rule_id` mais `fact_id` não é achado — é palpite, e
tem que sair rotulado como hipótese.
```

- [ ] **Step 4: `sf-verifier.md`** — o que mais agrega

```markdown
---
name: sf-verifier
role: executor
function: verify
tools: Read, Grep, Glob, Bash
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

Você é executor. Faz **uma** função do loop de fase e devolve ao coordenador.

## Faz

**Tenta REFUTAR cada achado P0 e P1.** O ônus da prova é seu, e está invertido: o achado
só sobrevive ao que você não conseguir derrubar.

Para cada um, procure ativamente:

1. **A evidência sustenta?** Abra os `fact_id` de `evidence`. O `subject` aponta para o
   que a regra diz? O `measure` tem a unidade que o limiar assume?
2. **O runtime é o certo?** `sparkforge_runtime_detect`. Regra fora do `runtime_scope`
   não deveria ter disparado; se disparou, é defeito de guarda.
3. **O caminho é alcançável?** Um achado em função morta, ou em ramo que o Catalyst
   descarta, não custa nada em produção. Cruze com `sparkforge_analyze_call_graph`.
4. **É `structural` ou `confirmed`?** `structural` é "esse padrão costuma custar caro",
   não "medi isso". Achado estrutural apresentado como medição é a forma mais comum de
   inflar confiança.
5. **A ausência é evidência?** Condição `absent:` sobre artefato nunca coletado é
   vacuamente verdadeira. Confira a sentinela `*_analyzed`.

## Pressupõe

`case.findings_index` populado. Não há o que refutar antes de haver achado.

## Entrega

- `case.hypotheses` — um por achado P0/P1, com `status: rejected` quando refutado
  e `open` quando sobreviveu, e o `statement` dizendo o que foi tentado

Devolve, por achado: **refutado** com a razão, ou **sobreviveu** com o que você tentou e
não conseguiu derrubar.

## Não faz

Não conserta. Não escreve relatório. Não suaviza achado que sobreviveu — se você não
refutou, ele passa inteiro.

Por que este executor existe: a §17 da spec da Fase 0 aponta falso positivo como o risco
que **treina o operador a ignorar a saída**. Um achado que ninguém tentou derrubar chega
ao relatório com a mesma força de um que resistiu — e é essa indistinção que corrói a
confiança na ferramenta.
```

- [ ] **Step 5: `sf-synthesizer.md`**

```markdown
---
name: sf-synthesizer
role: executor
function: synthesize
tools: Read, Bash, Write
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

Você é executor. Faz **uma** função do loop de fase e devolve ao coordenador.

## Faz

1. Monta o relatório a partir dos achados que **sobreviveram** ao `sf-verifier`.
2. `sparkforge_validate_output` em cada recomendação, antes de apresentar. Ganho
   quantificado sem `benchmark_ref` é rejeitado pelo schema — não contorne.
3. `sparkforge_next_step` para o próximo passo, com o `reason` citando a rota.
4. `sparkforge_resume` para o briefing de retomada, se a investigação for pausar.
5. Registra no case com `sparkforge_case_update`.

## Pressupõe

`case.findings_index` e `case.hypotheses`. Sintetizar sem a verificação apresenta
achado refutado com a mesma força de um que resistiu — a indistinção que corrói a confiança.

## Entrega

- `case.phase` — avançada
- `case.gates` — o que foi satisfeito
- `case.skills_used` — fechado com o desfecho

Toda afirmação quantitativa cita `rule_id` e `fact_id`. Sem fact, é hipótese, e sai
rotulada como hipótese.

Reporte a cobertura: quantos nós resolvidos, quantos `unresolved`, e onde. Relatório que
omite ponto cego finge cobertura total.

## Não faz

Não inventa número. Não escolhe a próxima rota por julgamento — `next_step` decide, e a
árvore de decisão vive em `rules/catalog/routing.yaml`. Não apresenta achado refutado.
```

- [ ] **Step 6: Confirme que os cinco têm fronteira negativa**

Run: `python -m pytest tests/test_agent_coverage.py::TestCoordinatorExecutorWiring -v`
Esperado: `test_every_executor_declares_its_negative_boundary` passa nos 5; `test_every_executor_is_declared_by_someone` ainda falha (Task 3 resolve).

- [ ] **Step 7: Commit**

```bash
git add agents/executors
git commit -m "feat(agents): cinco executores por funcao, com fronteira negativa"
```

---

## Task 3: Os três coordenadores novos, e os três existentes ganham executores

**Files:**
- Create: `agents/glue-infra-reviewer.md`, `agents/athena-query-optimizer.md`, `agents/pyspark-code-reviewer.md`
- Modify: `agents/spark-performance-architect.md`, `agents/glue-incremental-performance-architect.md`, `agents/iceberg-performance-engineer.md`

- [ ] **Step 1: Acrescente `rule_areas` e `executors` aos 3 existentes**

Em cada um dos três, no frontmatter, depois de `skills:`:

```yaml
rule_areas: [SF-PY, SF-UI, SF-PLAN]      # spark-performance-architect
executors: [sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer]
```

```yaml
rule_areas: [SF-PY, SF-ICE, SF-UI, SF-ENV]   # glue-incremental-performance-architect
executors: [sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer]
```

```yaml
rule_areas: [SF-ICE, SF-PQ]                  # iceberg-performance-engineer
executors: [sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer]
```

Acrescente também, no corpo de cada um, uma seção curta:

```markdown
## Como você trabalha

Você coordena; não executa. Despache os executores na ordem do loop de fase —
`sf-inventory` → `sf-extractor` → `sf-judge` → `sf-verifier` → `sf-synthesizer` — e
decida, entre um e outro, se o achado justifica seguir ou se falta coleta.

Nem toda investigação passa pelos cinco. `sparkforge_next_step` diz onde entrar.

Em plataforma sem despacho de subagente, a mesma decomposição sai por
`sparkforge playbook <seu-nome>`.
```

- [ ] **Step 2: `agents/glue-infra-reviewer.md`**

```markdown
---
name: glue-infra-reviewer
description: Use quando o gargalo ou o risco estiver na definição do job Glue e não no código — worker type e número, auto scaling, bookmark, retries, argumentos de job, observabilidade, e o Terraform que os declara.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - review-glue-terraform
  - tune-glue-job
  - optimize-variable-volume-job
rule_areas: [SF-GLUE, SF-ENV]
executors: [sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer]
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

## O que você olha

Infraestrutura declarada, não código. `sparkforge_analyze_terraform` sobre o HCL, e
`sparkforge_analyze_terraform_diff` quando o alvo é um PR — ele compara dois diretórios e
devolve só o lado DEPOIS, porque acusar o estado antigo é acusar o que ninguém pode mais
consertar.

Cruze com execução: `sparkforge_collect_glue_job` para os argumentos reais do job, e
`sparkforge_collect_cloudwatch` para as métricas do Glue.

## Três armadilhas que a infraestrutura esconde

**Observabilidade ligada sem `GlueContext`.** As métricas do Glue são publicadas pelo
GlueContext. Sem ele, `--enable-observability-metrics` fica ligado, o operador acredita ter
métrica, e o painel fica vazio — falha que só aparece quando alguém precisa dela.

**`max_retries` com escrita `append`.** A retentativa reexecuta o job, e `append` não é
idempotente: cada tentativa soma os mesmos registros, o job é marcado como sucesso, e o
dado sai duplicado sem erro no log.

**Bookmark com `max_concurrent_runs` maior que 1.** Bookmark guarda progresso por JOB,
não por execução: duas execuções concorrentes leem o mesmo ponto de partida e a última a
terminar sobrescreve o marcador da outra.

## Ausência de evidência

Valor interpolado no Terraform não é valor ausente — ele só existe depois do `apply`.
Quando o extrator emite `tf.observability.unknown`, isso significa "não deu para saber",
não "não tem". Acusar ali produz P1 falso num job que está correto.

## Como você trabalha

Você coordena; não executa. Despache os executores na ordem do loop de fase e decida,
entre um e outro, se o achado justifica seguir ou se falta coleta.

Em plataforma sem despacho de subagente: `sparkforge playbook glue-infra-reviewer`.
```

- [ ] **Step 3: `agents/athena-query-optimizer.md`**

```markdown
---
name: athena-query-optimizer
description: Use quando o custo ou a latência estiver na consulta e não no job — bytes escaneados no Athena, pruning de partição, projeção de coluna, versão do engine, workgroup, e o layout de armazenamento que a consulta enxerga.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - optimize-parquet-layout
  - optimize-iceberg-table
  - benchmark-pyspark-job
rule_areas: [SF-ATH, SF-PQ]
executors: [sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer]
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

## O que você olha

Athena cobra por **bytes escaneados**. O caminho da evidência tem três pernas, e nenhuma
responde sozinha:

1. `sparkforge_analyze_sql` — a consulta: projeção, predicado, `LIMIT`.
2. `sparkforge_analyze_catalog_schema` — o schema e as partições declaradas no Glue Catalog.
3. `sparkforge_fuse` — correlaciona as duas. **As regras SF-ATH só disparam sobre facts
   fundidos**, porque "a consulta filtra a coluna de partição?" exige saber quais colunas
   são de partição, e isso está no catálogo, não na query.

Some `sparkforge_analyze_athena_workgroup` (versão do engine, limites) e
`sparkforge_analyze_s3_listing` (o que está de fato no prefixo).

## `LIMIT` não é filtro

`LIMIT` corta o resultado, não o escaneamento. Uma consulta com `LIMIT 10` e sem predicado
de partição varre a tabela inteira e cobra por ela. É o erro mais caro e o mais fácil de
não ver, porque a consulta volta rápido.

## Quem consome também decide

Antes de recomendar mudança de formato ou de versão, leia
`knowledge/cross-service-constraints.md` e rode `sparkforge_analyze_consumers`. Glue 5.1
escreve Iceberg **format V3**, e **Athena não lê V3** — a migração passa no job e quebra
silenciosamente no consumidor dias depois.

## Como você trabalha

Você coordena; não executa. Despache os executores na ordem do loop de fase.

Em plataforma sem despacho de subagente: `sparkforge playbook athena-query-optimizer`.
```

- [ ] **Step 4: `agents/pyspark-code-reviewer.md`**

```markdown
---
name: pyspark-code-reviewer
description: Use para revisar código PySpark — PR, biblioteca ou job — correlacionando o que está escrito no fonte, o que sobreviveu ao Catalyst no plano físico, e onde o trabalho Spark é disparado na estrutura de chamadas.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - review-pyspark-pr
  - optimize-pyspark-code
  - analyze-spark-plan
  - analyze-library-call-graph
  - analyze-batch-loop
rule_areas: [SF-PY, SF-PLAN, SF-CG]
executors: [sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer]
---

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

## Três leituras do mesmo código

**Fonte** — `sparkforge_analyze_pyspark`. AST estático, nunca importa nem executa o código
analisado. Achado aqui é `structural`: o padrão costuma custar caro, mas o Catalyst pode
ter descartado aquele ramo.

**Plano** — `sparkforge_analyze_plan`. O que sobreviveu à otimização. Achado aqui é
`confirmed`: o nó está no caminho que vai executar. Quando as duas leituras concordam, a
segunda é a evidência forte.

**Estrutura** — `sparkforge_analyze_call_graph`. Onde o trabalho é disparado. Uma action
isolada é barata; a mesma action dentro de um ciclo de chamadas é ilimitada — e recursão
mútua é a forma que passa despercebida em revisão, porque nenhuma das funções envolvidas
parece recursiva sozinha.

## O que o plano não te diz

`AdaptiveSparkPlan isFinalPlan=false` significa que este é o plano **inicial**. O AQE ainda
vai reotimizá-lo em runtime — inclusive convertendo sort-merge join em broadcast join.
`EXPLAIN` não executa a query, então o plano exibido é sempre o inicial. Recomendar
broadcast manual contra um SortMergeJoin lido daí é recomendar o que o AQE já faria
sozinho.

## Cobertura honesta

Dispatch dinâmico, `getattr`, SQL montado em string: o extrator emite `pyspark.unresolved`
em vez de fingir que olhou. Reporte esses pontos — "312 nós resolvidos, 7 não resolvidos em
`arquivo:linha`" é revisão honesta; omiti-los é revisão que parece completa.

## Como você trabalha

Você coordena; não executa. Despache os executores na ordem do loop de fase.

Em plataforma sem despacho de subagente: `sparkforge playbook pyspark-code-reviewer`.
```

- [ ] **Step 5: `NAMES` derivado do disco**

`tests/test_agents_parity.py` tem `NAMES` com os 3 nomes literais e
`test_agents_dir_holds_all_three`. Substitua:

```python
NAMES = tuple(sorted(p.stem for p in AGENTS.glob("*.md")))


def test_agents_dir_is_not_empty():
    """Antes este teste fixava os tres nomes literais. Lista fixa obriga a
    editar o teste a cada coordenador novo, e -- pior -- nao pega o caso que
    importa, que e um agente parar de ser espelhado. A byte-identidade dos
    espelhos e o invariante; o nome nao e."""
    assert len(NAMES) >= 3
```

Ajuste os demais testes do arquivo para iterar sobre `NAMES` derivado. Confirme que
`test_platform_dirs_carry_no_thresholds_or_sources` continua varrendo `.claude`, `.agents`
e `.github`.

- [ ] **Step 6: Espelhar os executores**

`scripts/sync_skills.py` espelha `agents/` para os três destinos. Estenda para
`agents/executors/`, preservando o subdiretório. Confirme com:

```bash
python scripts/sync_skills.py
python scripts/sync_skills.py --check
ls .claude/agents/executors .agents/agents/executors
```

- [ ] **Step 7: Rode o invariante**

Run: `python -m pytest tests/test_agent_coverage.py -v`

Se `test_no_tool_is_orphan` ainda falhar, **leia a lista** e distribua as tools restantes
pelos coordenadores e executores onde elas fazem sentido. Não force a menção só para o
teste passar — o limite conhecido deste invariante, registrado na §8 do spec, é que ele
mede menção e não utilidade. Citar sem ensinar quando usar é como passa.

- [ ] **Step 8: Commit**

```bash
git add agents scripts/sync_skills.py tests/test_agents_parity.py .claude .agents .github
git commit -m "feat(agents): tres coordenadores novos e executores declarados"
```

---

## Task 4: Roteamento de coordenador como dado

**Files:**
- Modify: `rules/catalog/routing.yaml`
- Test: `tests/test_router_agents.py`

- [ ] **Step 1: Escreva o teste**

```python
# tests/test_router_agents.py
"""Escolher coordenador e consulta, nao julgamento.

Manter os 3 agentes antigos e acrescentar 3 novos cria dois vocabularios --
risco levantado e aceito ao decidir F4-D2. A tabela e o que o neutraliza:
a mesma coisa que `next_step` fez com a escolha de skill.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "rules" / "catalog" / "routing.yaml"
AGENTS = ROOT / "agents"


def _routing() -> dict:
    return yaml.safe_load(ROUTING.read_text(encoding="utf-8"))


def _agent_routes() -> list[dict]:
    return [r for r in _routing()["rules"] if r.get("recommended_agent")]


class TestAgentRoutes:
    def test_there_is_at_least_one_route_per_coordinator(self):
        coordinators = {p.stem for p in AGENTS.glob("*.md")}
        routed = {r["recommended_agent"] for r in _agent_routes()}
        missing = sorted(coordinators - routed)
        assert not missing, f"coordenadores sem rota: {missing}"

    def test_every_routed_agent_exists(self):
        coordinators = {p.stem for p in AGENTS.glob("*.md")}
        for route in _agent_routes():
            assert route["recommended_agent"] in coordinators, route["id"]

    def test_agent_routes_have_id_and_reason(self):
        for route in _agent_routes():
            assert route["id"].startswith("AGENT-"), route
            assert route.get("reason"), route["id"]

    def test_agent_route_ids_are_unique(self):
        ids = [r["id"] for r in _agent_routes()]
        assert len(ids) == len(set(ids))
```

- [ ] **Step 2: Veja falhar**

Run: `python -m pytest tests/test_router_agents.py -v`
Esperado: falha — nenhuma rota tem `recommended_agent`.

- [ ] **Step 3: Acrescente as rotas ao `routing.yaml`**

Ao final da lista `rules`, com o mesmo vocabulário declarativo das 16 existentes
(`absent`, `count_gt`, `equals`, `contains`, `any_where` — **nunca `expr`**, que a
whitelist do avaliador proíbe):

```yaml
  # Rotas de COORDENADOR. Escolher agente deixa de ser julgamento e vira consulta,
  # pelo mesmo motivo que a escolha de skill virou: prosa dizendo "use o agente certo"
  # multiplica vocabulario quando ha seis deles.
  - id: AGENT-001
    phase_in: [intake, inventory]
    title: Sem runtime nem inventário
    when:
      any:
        - {case: runtime.glue, absent: true}
    recommended_agent: spark-performance-architect
    reason: >
      Coordenador geral enquanto o terreno não está mapeado. Sem runtime confirmado,
      nenhuma especialização se justifica — a guarda de versão de qualquer área falha
      fechada.

  - id: AGENT-002
    phase_in: [diagnosis, hypothesis]
    title: Achado dominante em infraestrutura Glue
    when:
      all:
        - {findings_area: SF-GLUE, count_gt: 0}
    recommended_agent: glue-infra-reviewer
    reason: >
      O gargalo está na definição do job, não no código: worker, bookmark, retries,
      observabilidade. Tuning de código não move nenhum deles.

  - id: AGENT-003
    phase_in: [diagnosis, hypothesis]
    title: Achado dominante em consulta Athena
    when:
      all:
        - {findings_area: SF-ATH, count_gt: 0}
    recommended_agent: athena-query-optimizer
    reason: >
      Athena cobra por bytes escaneados. O caminho passa por consulta, schema do catálogo
      e a fusão dos dois — nenhuma das três responde sozinha.

  - id: AGENT-004
    phase_in: [diagnosis, hypothesis]
    title: Achado dominante em código PySpark
    when:
      any:
        - {findings_area: SF-PY, count_gt: 0}
        - {findings_area: SF-PLAN, count_gt: 0}
        - {findings_area: SF-CG, count_gt: 0}
    recommended_agent: pyspark-code-reviewer
    reason: >
      Fonte, plano físico e grafo de chamadas são três leituras do mesmo código, e o
      achado só é forte quando elas concordam.

  - id: AGENT-005
    phase_in: [diagnosis, hypothesis]
    title: Achado dominante em Iceberg ou layout
    when:
      any:
        - {findings_area: SF-ICE, count_gt: 0}
        - {findings_area: SF-PQ, count_gt: 0}
    recommended_agent: iceberg-performance-engineer
    reason: >
      Distinguir data files, delete files, manifests, snapshots e metadata files decide
      qual manutenção resolve — e compactar a camada errada gasta DPU sem efeito.

  - id: AGENT-006
    phase_in: [diagnosis, hypothesis, experiment]
    title: Fluxo incremental com latest-per-key
    when:
      any:
        - {case: scope.entrypoints, contains: incremental}
    recommended_agent: glue-incremental-performance-architect
    reason: >
      Fluxo full e incremental no mesmo job, latest-per-key em tabela bilionária e
      batching exigem mapear a biblioteca inteira antes de qualquer tuning localizado.
```

O operador `findings_area` não existe ainda. Implemente-o em
`sparkforge/case/router.py`, junto dos outros operadores declarativos: ele conta quantos
`finding_ids` pertencem à área dada (prefixo do `rule_id` até o último hífen). Se preferir
não estender o motor, use um operador existente sobre o mesmo dado e **justifique a
escolha** — mas não use `expr`.

- [ ] **Step 4: Veja passar e confirme que as 16 rotas de skill seguem intactas**

```bash
python -m pytest tests/test_router_agents.py tests/test_case_router.py -v
python -c "import sys;sys.path.insert(0,'.');import yaml;from pathlib import Path;r=yaml.safe_load(Path('rules/catalog/routing.yaml').read_text(encoding='utf-8'));print('rotas total:',len(r['rules']))"
```

Esperado: 22 rotas (16 de skill + 6 de agente), e nenhuma regressão em `test_case_router.py`.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/routing.yaml sparkforge/case/router.py tests/test_router_agents.py
git commit -m "feat(routing): escolha de coordenador vira dado, nao julgamento"
```

---

## Task 5: `sparkforge playbook`

**Files:**
- Create: `sparkforge/case/playbook.py`, `tests/test_playbook.py`
- Modify: `sparkforge/adapters/_core.py`, `cli.py`, `tools.py`, `manifest.json`

- [ ] **Step 1: Escreva o teste**

```python
# tests/test_playbook.py
"""O espelho de orquestracao para plataforma sem despacho de subagente.

Devin, Codex e Copilot nao despacham subagente -- isso e capacidade de harness,
nao conteudo deste repositorio. O playbook emite a MESMA decomposicao em
sequencia. Perde o paralelismo; mantem o metodo, as fronteiras negativas e a
ordem.

O teste que importa e o de FIDELIDADE: se o playbook divergir dos executores
que o coordenador declara, ele vira prosa que envelhece -- exatamente o que a
decisao F4-D4 rejeitou ao escolher verbo em vez de documento.
"""
from pathlib import Path

import pytest
import yaml

from sparkforge.case.playbook import build_playbook

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"


def _coordinators() -> list[str]:
    return sorted(p.stem for p in AGENTS.glob("*.md"))


def _declared_executors(name: str) -> list[str]:
    block = (AGENTS / f"{name}.md").read_text(encoding="utf-8").split("---", 2)[1]
    return (yaml.safe_load(block) or {}).get("executors") or []


class TestFidelity:
    @pytest.mark.parametrize("name", _coordinators())
    def test_steps_match_the_declared_executors(self, name):
        """O invariante que impede o espelho de virar prosa."""
        playbook = build_playbook(name, case={})
        assert [s["executor"] for s in playbook["steps"]] == _declared_executors(name)

    @pytest.mark.parametrize("name", _coordinators())
    def test_every_step_carries_the_negative_boundary(self, name):
        """Sem a fronteira negativa, quem seguir o playbook vira coordenador
        disfarcado e a decomposicao perde o sentido."""
        for step in build_playbook(name, case={})["steps"]:
            assert step["does_not"], step["executor"]


class TestDeterminism:
    def test_same_input_twice_yields_identical_output(self):
        first = build_playbook("spark-performance-architect", case={"phase": "diagnosis"})
        second = build_playbook("spark-performance-architect", case={"phase": "diagnosis"})
        assert first == second


class TestErrors:
    def test_unknown_coordinator_is_an_actionable_error(self):
        with pytest.raises(ValueError) as excinfo:
            build_playbook("nao-existe", case={})
        message = str(excinfo.value)
        assert "nao-existe" in message
        assert "spark-performance-architect" in message, "erro deve listar os validos"
```

- [ ] **Step 2: Veja falhar**

Run: `python -m pytest tests/test_playbook.py -v`
Esperado: `ModuleNotFoundError: No module named 'sparkforge.case.playbook'`

- [ ] **Step 3: Implemente `sparkforge/case/playbook.py`**

```python
"""Decomposicao de um coordenador em passos sequenciais.

Existe porque despacho de subagente e capacidade de HARNESS, nao conteudo deste
repositorio: Devin, Codex e Copilot nao tem equivalente. O playbook emite a
mesma decomposicao em ordem, para um agente so seguir.

Le os arquivos de `agents/` em vez de repetir a lista de executores: uma copia
aqui divergiria do coordenador na primeira mudanca, e o espelho viraria prosa
que envelhece -- o motivo de a decisao F4-D4 ter escolhido verbo em vez de
documento.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "agents"
EXECUTORS = AGENTS / "executors"


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name} sem frontmatter")
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def _section(text: str, title: str) -> str:
    """Corpo de uma secao `## <title>` ate a proxima `##` ou o fim."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


def available_coordinators() -> list[str]:
    return sorted(p.stem for p in AGENTS.glob("*.md"))


def build_playbook(coordinator: str, case: dict[str, Any]) -> dict[str, Any]:
    """Passos ordenados de um coordenador, com o estado do case.

    `does_not` vem da secao `## Não faz` do executor -- nao e reescrito aqui.
    Duas fontes para a mesma fronteira divergiriam, e a que ninguem le seria a
    errada.
    """
    path = AGENTS / f"{coordinator}.md"
    if not path.is_file():
        raise ValueError(
            f"coordenador desconhecido: {coordinator}. "
            f"Disponiveis: {', '.join(available_coordinators())}"
        )

    front = _frontmatter(path)
    steps: list[dict[str, Any]] = []
    for order, name in enumerate(front.get("executors") or [], start=1):
        executor_path = EXECUTORS / f"{name}.md"
        if not executor_path.is_file():
            raise ValueError(
                f"{coordinator} declara o executor {name}, que nao existe em "
                f"{EXECUTORS.relative_to(ROOT)}"
            )
        text = executor_path.read_text(encoding="utf-8")
        steps.append(
            {
                "order": order,
                "executor": name,
                "function": _frontmatter(executor_path).get("function", ""),
                "does": _section(text, "Faz"),
                "does_not": _section(text, "Não faz"),
            }
        )

    return {
        "coordinator": coordinator,
        "description": front.get("description", ""),
        "rule_areas": front.get("rule_areas") or [],
        "skills": front.get("skills") or [],
        "phase": case.get("phase"),
        "steps": steps,
        "note": (
            "Decomposicao sequencial. Em Claude Code os mesmos passos sao "
            "despachados como subagentes; aqui um agente so os segue em ordem, "
            "escrevendo o resultado de cada um no case antes do proximo."
        ),
    }
```

- [ ] **Step 4: Veja passar**

Run: `python -m pytest tests/test_playbook.py -v`
Esperado: PASS.

- [ ] **Step 5: Verbo na CLI e tool no MCP**

Em `_core.py`, junto dos outros verbos:

```python
def playbook(coordinator: str, repo: str = ".") -> dict[str, Any]:
    """Decomposicao do coordenador, com o estado do case quando existir."""
    case: dict[str, Any] = {}
    try:
        case = store.load_case(root=repo)
    except Exception:  # case ausente e caso normal, nao erro
        case = {}
    try:
        return build_playbook(coordinator, case)
    except ValueError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc
```

Confirme a API real de `store` antes de escrever — leia `sparkforge/case/store.py` e use a
função que existe, não a que este plano imaginou. Se a exceção de case ausente tiver tipo
próprio, capture-o em vez de `Exception`.

Na CLI, seguindo o padrão do arquivo:

```python
    playbook_p = sub.add_parser(
        "playbook", help="Decomposicao de um coordenador em passos sequenciais."
    )
    playbook_p.add_argument("coordinator")
    playbook_p.add_argument("--repo", default=".")
```

```python
def _cmd_playbook(args: argparse.Namespace) -> int:
    _print(_core.playbook(args.coordinator, repo=args.repo))
    return 0
```

E no `_DISPATCH`: `("playbook", None): _cmd_playbook`.

No `tools.py`, tool `sparkforge_playbook` com `outputSchema` fechado descrevendo
`coordinator`, `steps` (com `order`, `executor`, `function`, `does`, `does_not`) e os
demais campos. Acrescente a tool ao `manifest.json` — `test_docs_coverage` compara com
`TOOLS.keys()`.

- [ ] **Step 6: Verifique**

```bash
python -m pytest tests/test_playbook.py tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_docs_coverage.py -v
python -m sparkforge.adapters.cli playbook glue-infra-reviewer | head -30
python -m pytest -q
```

Acrescente também um teste em `TestCliMcpEquivalence` (`tests/test_adapters_cli.py`)
comparando a saída da CLI com a da tool — é a garantia central deste repositório para
capacidade nova, e omiti-la já custou uma rodada de revisão na Fase 3a.

- [ ] **Step 7: Commit**

```bash
git add sparkforge manifest.json tests/
git commit -m "feat(playbook): espelho de orquestracao para plataforma sem subagente"
```

---

## Task 6: Paridade — `codex` e `playbook`

**Files:**
- Modify: `parity.yaml`, `tests/test_capability_parity.py`

- [ ] **Step 1: Escreva o teste**

Acrescente a `tests/test_capability_parity.py`:

```python
class TestOrchestrationParity:
    """A capacidade que faltava no manifesto.

    Os 3 agentes eram espelhados com byte-identidade travada, mas nada
    verificava que "coordenar investigacao" tinha caminho por plataforma --
    exatamente o que o gate da secao 8.4 da Fase 0 existe para pegar. Agentes
    escaparam dele porque agente nao era mecanismo declarado.
    """

    def test_codex_is_a_declared_platform(self):
        assert "codex" in manifest()["platforms"]

    def test_playbook_is_a_declared_mechanism(self):
        assert "playbook" in manifest()["mechanisms"]

    def test_coordination_capability_exists(self):
        names = [c["name"] for c in manifest()["capabilities"]]
        assert any("coorden" in n.lower() for n in names), names

    def test_coordination_reaches_every_platform(self):
        capability = next(
            c for c in manifest()["capabilities"] if "coorden" in c["name"].lower()
        )
        for platform in manifest()["platforms"]:
            assert capability["platforms"].get(platform), platform

    def test_only_claude_code_claims_subagent_dispatch(self):
        """Despacho de subagente e capacidade de HARNESS. Declarar para outra
        plataforma seria afirmar paridade que nao existe -- o defeito exato do
        transporte HTTP na Fase 1, que `parity.yaml` afirmava e nenhum teste
        tocava."""
        capability = next(
            c for c in manifest()["capabilities"] if "coorden" in c["name"].lower()
        )
        for platform, mechanisms in capability["platforms"].items():
            if platform != "claude_code":
                assert "subagent" not in mechanisms, platform
```

- [ ] **Step 2: Veja falhar**

Run: `python -m pytest tests/test_capability_parity.py -v`

- [ ] **Step 3: Atualize o `parity.yaml`**

```yaml
platforms: [claude_code, devin_desktop, devin_cli, codex, copilot_ci]
mechanisms: [mcp, cli, files, playbook]
```

E a capacidade:

```yaml
  - name: coordenar investigacao por agente especializado
    tools: [sparkforge_playbook]
    cli: [playbook]
    knowledge: [AGENT_PROTOCOL.md]
    platforms:
      claude_code: [mcp, cli, files, playbook]
      devin_desktop: [mcp, cli, files, playbook]
      devin_cli: [mcp, cli, files, playbook]
      codex: [cli, files, playbook]
      copilot_ci: [cli, files, playbook]
```

Acrescente à seção `notes` do arquivo por que `subagent` não é mecanismo declarado:
despacho de subagente é capacidade de harness do Claude Code, não conteúdo deste
repositório, e declará-lo como mecanismo faria o manifesto afirmar paridade que não
existe. O `playbook` é a tradução honesta.

- [ ] **Step 4: Veja passar e confirme que as capacidades antigas seguem íntegras**

Run: `python -m pytest tests/test_capability_parity.py -v`
Esperado: PASS, incluindo os testes que já existiam — `test_no_capability_is_missing_a_platform` agora exige `codex` em **todas** as capacidades. Se alguma ficar de fora, decida: ou `codex` a alcança, ou o manifesto precisa dizer por que não. Não afrouxe o teste.

- [ ] **Step 5: Commit**

```bash
git add parity.yaml tests/test_capability_parity.py
git commit -m "feat(parity): codex como plataforma e playbook como mecanismo"
```

---

## Task 7: Documentação e varredura de aceitação

**Files:**
- Modify: `README.md`, `AGENTS.md`, `AGENT_PROTOCOL.md`, `GUIA_DE_USO.md`, `PROMPT_INICIAL_MESTRE.md`, `docs/superpowers/STATUS.md`
- Modify: `docs/superpowers/specs/2026-07-31-sparkforge-fase4-agentes-design.md` (status)

- [ ] **Step 1: Teste primeiro**

Acrescente a `tests/test_docs_coverage.py`:

```python
    def test_readme_documents_the_playbook(self):
        assert "sparkforge playbook" in self.README

    def test_readme_documents_the_two_agent_layers(self):
        lowered = self.README.lower()
        assert "coordenador" in lowered
        assert "executor" in lowered
```

E em `TestAgentsMd`:

```python
    def test_agents_md_lists_every_coordinator(self):
        from pathlib import Path

        for path in Path(ROOT / "agents").glob("*.md"):
            assert path.stem in self.AGENTS, path.stem
```

- [ ] **Step 2: Documente**

`README.md` — seção sobre as duas camadas, os 6 coordenadores, os 5 executores, e
`sparkforge playbook` como o que dá a mesma decomposição a quem não despacha subagente.

`AGENTS.md` — tabela dos 6 coordenadores com quando usar cada um, e o ponteiro para o
roteamento em `routing.yaml`.

`AGENT_PROTOCOL.md` — uma regra nova, ou extensão da regra 6, dizendo que o coordenador
registra no case qual executor rodou e com que resultado.

`GUIA_DE_USO.md` e `PROMPT_INICIAL_MESTRE.md` — como entrar: `next_step` indica a rota, e
`playbook` dá os passos.

`STATUS.md` — números medidos, Fase 4 concluída, e **remover a dívida "Agente não é
mecanismo de paridade declarado"**, que esta fase fecha.

Spec da Fase 4 — trocar `**Status:** aprovado para planejamento` por `implementado`, com a
faixa de commits, no mesmo padrão dos specs anteriores.

- [ ] **Step 3: Varredura dos 10 critérios de aceitação do spec**

Confira **um a um, com comando**. Não marque nenhum sem executar:

```bash
python -m pytest tests/test_agent_coverage.py -v          # 1,2,3,4
python -m sparkforge.adapters.cli playbook athena-query-optimizer   # 5
python -m pytest tests/test_router_agents.py -v           # 6
python -m pytest tests/test_capability_parity.py -v       # 7
python scripts/sync_skills.py --check                     # 8
python -m pytest -q && python -m ruff check sparkforge scripts tests
python scripts/gen_requirements.py --check && python scripts/check_evals.py   # 9
```

Critério 10 é a doc: confirme que cada arquivo da lista referencia o que é novo.

Se algum falhar, **não conserte às cegas** — relate com diagnóstico.

- [ ] **Step 4: Commit**

```bash
git add README.md AGENTS.md AGENT_PROTOCOL.md GUIA_DE_USO.md PROMPT_INICIAL_MESTRE.md docs/superpowers tests/test_docs_coverage.py
git commit -m "docs: documenta coordenadores, executores e playbook, e fecha a Fase 4"
```

---

## Resultado esperado

| | Antes | Depois |
|---|---|---|
| Coordenadores | 3 | 6 |
| Executores | 0 | 5 |
| Tools alcançáveis a partir de um coordenador | 8 de 29 | **29 de 29** |
| Áreas de regra com coordenador | — | 9 de 9 |
| Rotas em `routing.yaml` | 16 | 22 |
| Plataformas no manifesto | 4 | 5 |
| Mecanismos | 3 | 4 |
| Verificação adversarial de finding | nenhuma | `sf-verifier` |
