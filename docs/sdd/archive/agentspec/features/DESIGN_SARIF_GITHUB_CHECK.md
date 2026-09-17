# DESIGN: SARIF + GitHub Check

> Technical design for implementing SARIF + GitHub Check

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SARIF_GITHUB_CHECK |
| **Date** | 2026-09-11 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_SARIF_GITHUB_CHECK.md](./DEFINE_SARIF_GITHUB_CHECK.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                     sparkforge report github                               │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  findings.json ─┐                                                          │
│  facts.json (N) ┼─► adapters/_core.report_github ─► reporting/locate.py    │
│  --repo         │     (so valida e le JSON)          resolve(finding,      │
│  --source-root* ┘                                     facts_by_id, roots,  │
│                                                       existe)              │
│                                                          │                 │
│                          ┌───────────────────────────────┴──────┐          │
│                          ▼                                      ▼          │
│                  Localizado(uri, line, col?)        Recusa(motivo)         │
│                          │                                      │          │
│                          └──────────────┬───────────────────────┘          │
│                                         ▼                                  │
│                         reporting/github.py (puro, sem I/O)                │
│             ┌───────────────┬───────────┴─────────┬──────────────┐         │
│             ▼               ▼                     ▼              ▼         │
│        sarif(dict)    summary(str)        annotations(list)   gate(bool)   │
│             │               │                     │              │         │
│  CLI ───────┼── .sparkforge/report/sparkforge.sarif (nome fixo)  │         │
│             │   .sparkforge/report/summary.md     (nome fixo)    │         │
│             │   stdout: ::error file=..,line=..::msg              │         │
│             │   exit: 1 se o gate disparar; 0 senao; 2 uso ───────┘         │
│  MCP ───────┴── sparkforge_report_github (READ_ONLY): devolve tudo,        │
│                 nao grava                                                  │
└───────────────────────────────────────────────────────────────────────────┘

WORKFLOW (fora do pacote, examples/github/sparkforge.yml)
  analyze pyspark --path jobs  → facts
  analyze terraform --path infra → facts
  judge --facts ... → findings
  report github --source-root jobs --source-root infra --fail-on P0
  github/codeql-action/upload-sarif  ← .sparkforge/report/sparkforge.sarif
  cat .sparkforge/report/summary.md >> $GITHUB_STEP_SUMMARY
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/reporting/__init__.py` | Pacote novo; nao importa `adapters` | Python |
| `sparkforge/reporting/locate.py` | Resolve cada finding em `Localizado` ou `Recusa`, com a existencia do arquivo injetada (`existe: Callable[[str], bool]`) | Python puro |
| `sparkforge/reporting/github.py` | `projetar(findings, facts, locais, *, category, fail_on, versao)` → `Projecao(sarif, summary, annotations, recusas, gate)`; escape de workflow command; limites do GitHub | Python puro, sem I/O |
| `adapters/_core.py::report_github` | Le e valida `findings.json` e os `facts.json`, monta `existe` confinado a `--repo`, chama a projecao | Python |
| `adapters/cli.py` | `report github`: grava os dois arquivos com nome fixo, imprime as anotacoes, devolve o exit code | argparse |
| `adapters/tools.py` | `sparkforge_report_github`, `READ_ONLY` | TOOLS |
| `fixtures/sarif/` | 4 casos + `_schema/sarif-schema-2.1.0.json` (OASIS, com `SOURCE.md`: URL e sha256) | JSON, golden |
| `tests/test_fixtures_golden_sarif.py` | Golden, validacao de schema, gate | pytest |
| `tests/test_reporting_github.py` | Unidade: localizacao, escape, limites; invariante sobre os 222 findings de `fixtures/` | pytest |
| `docs/github-code-scanning.md`, `examples/github/sparkforge.yml` | Como ligar no repositorio de dados | Markdown, YAML |
| `.github/workflows/ci.yml` | Job `sarif-upload`, so `workflow_dispatch` | GitHub Actions |

---

## Key Decisions

### Decision 1: projecao pura, com I/O so na borda

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o mesmo resultado sai por duas portas: a CLI grava e imprime, a tool MCP so devolve. Os goldens precisam ser byte a byte.

**Choice:** `reporting/github.py` e `reporting/locate.py` nao fazem I/O. A existencia de arquivo entra como `existe(caminho_relativo) -> bool`, construida pelo `_core` sobre `--repo`. A CLI e a tool chamam a mesma `projetar`.

**Rationale:** duas portas sobre uma unica funcao nao divergem, e a funcao e testavel sem disco.

**Alternatives Rejected:**
1. Emitir dentro do `_core`: a tool e a CLI ficariam com logica duplicada.
2. `os.path.exists` dentro do `locate`: o teste precisaria de arvore em disco, e o confinamento a `--repo` ficaria espalhado.

**Consequences:**
- Um parametro a mais (`existe`).
- A garantia "nada fora de `--repo`" mora num lugar so.

---

### Decision 2: `--source-root` repetivel, e ambiguidade vira recusa

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** medido em `adapters/_core.py`, `analyze <verbo> --path <dir>` chama `extract_*_tree(target, repo_root=target)`. O `subject.file` e relativo ao diretorio analisado, e nao a raiz do git. Um finding de `analyze pyspark --path jobs` diz `lib/job.py`; o GitHub precisa de `jobs/lib/job.py` (A-006).

**Choice:** `--source-root <dir>` repetivel (default `.`), relativo a `--repo`. Para cada `file`, a resolucao percorre as raizes na ordem dada:
- se existir em exatamente uma, a `uri` e `<raiz>/<file>` normalizado com `/`;
- se existir em mais de uma, e recusa `caminho_ambiguo`;
- se nao existir em nenhuma, e recusa `arquivo_fora_do_repo`.

Raiz absoluta, com `..`, ou que resolva fora de `--repo`: erro de uso (exit 2).

**Rationale:** a raiz e declarada pelo operador, que e quem sabe de onde rodou cada `analyze`. Chutar a raiz localizaria o alerta no arquivo errado.

**Alternatives Rejected:**
1. Exigir `analyze --path .`: forcaria analisar o repositorio inteiro, fixtures e testes incluidos.
2. Gravar a raiz nos facts: mudaria o contrato de `Fact` e todos os goldens.

**Consequences:**
- O workflow de exemplo repete no `report` os mesmos diretorios que passou aos `analyze`.

---

### Decision 3: evidencia so conta com `subject` de codigo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** A-005. Um fact de evidencia pode ter `file` e `line` de um artefato que nao e codigo (`plan.txt`, dump JSON).

**Choice:** a ordem de localizacao e:
1. `finding.subject`, com `type` em {`source_location`, `tf_resource`, `plan_node`}, `file` e `line`;
2. senao, o **primeiro** `fact_id` de `evidence`, na ordem do finding, cujo fact esteja na uniao e tenha `subject.type` em {`source_location`, `tf_resource`}, `file` e `line`;
3. a `uri` resolvida pela Decision 2.

Motivos de recusa, na ordem de teste:
- `evidencia_ausente` (fact de evidencia fora da uniao, e nenhum outro caminho localiza);
- `runtime` (`subject.type` em {`job_run`, `stage`, `table`} e nenhuma evidencia de codigo);
- `sem_linha`;
- `arquivo_fora_do_repo`;
- `caminho_ambiguo`.

`plan_node` entra pelo `subject` e, sem o arquivo no repositorio, cai em `arquivo_fora_do_repo`.

**Rationale:** a evidencia so empresta localizacao quando ela aponta codigo que o revisor ve no diff.

**Alternatives Rejected:**
1. Aceitar qualquer evidencia com linha: poria alerta em dump de catalogo.

**Consequences:**
- Um finding de `stage` so sai do SARIF se o fact de evidencia for de codigo. A ponte `spark.stage.callsite` fica fora do escopo.

---

### Decision 4: saidas com nome fixo, anotacoes no stdout, contagem no stderr

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** no eval harness, o scanner de seguranca recusou escrita em caminho vindo do argv. O workflow le a saida de lugar conhecido, e o GitHub so transforma em anotacao a linha `::cmd...::` inteira no stdout.

**Choice:**
- escrita em `<repo>/.sparkforge/report/sparkforge.sarif` e `<repo>/.sparkforge/report/summary.md`, ambos com `newline="\n"`;
- stdout: so as linhas de anotacao, uma por finding localizado, na ordem do SARIF;
- stderr: uma linha `sparkforge report github: <n> no SARIF, <m> sem localizacao, gate <P0|P1|off>: <ok|disparou>`;
- exit code: 1 so pelo gate, 2 para erro de uso ou de entrada, 0 nos outros casos.

**Rationale:** o workflow le caminhos fixos, e o stdout fica limpo para o parser de comandos do GitHub.

**Alternatives Rejected:**
1. `--out`: caminho do argv para escrita.
2. JSON no stdout como os outros verbos: misturaria JSON com linhas de anotacao.

**Consequences:**
- O `report github` e o primeiro verbo cujo stdout nao e JSON. A decisao fica registrada na docstring do handler.

---

### Decision 5: mapeamento SARIF deterministico e sem o que o GitHub calcula

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:**
- `version: "2.1.0"` e `$schema` apontando a URL OASIS do schema versionado;
- um unico run, com `tool.driver`:
  - `name: "SparkForge"`, `semanticVersion` do pacote, `informationUri` do repositorio;
  - `rules` ordenadas por `id`, uma por `rule_id` presente nos findings: `name` (id sem hifen), `shortDescription.text` (titulo), `fullDescription.text` (explicacao), `help.text` e `help.markdown` (proposed_change, validation e rollback em listas), `helpUri` (primeira `sources[].url`, se houver), `defaultConfiguration.level` pela severidade, e `properties.precision` (`high`/`medium`/`low` direto do `confidence`);
- `results` ordenados por (`uri`, `startLine`, `ruleId`), cada um com:
  - `ruleId`, `ruleIndex` e `level`;
  - `message.text` = titulo, mais ` (medido: k=v, ...)` quando houver `measured`;
  - `locations[0].physicalLocation` com `artifactLocation.uri` e `uriBaseId: "%SRCROOT%"`;
  - `region.startLine`, e `startColumn` so quando o subject traz `col`;
  - `properties`: `evidence` (lista de `fact_id`), `status` e `severity` (P0..P4);
- `runAutomationDetails.id` = `"<category>/"` quando houver `--category`;
- sem `partialFingerprints`, sem `security-severity`, sem horario e sem caminho absoluto.

**Rationale:** mesma entrada, mesmos bytes. O `upload-sarif` calcula o fingerprint a partir do fonte, e o GitHub so usa o `primaryLocationLineHash` (T1).

**Consequences:**
- Um finding repetido em linhas diferentes gera resultados diferentes; na mesma linha, a deduplicacao e do GitHub.

---

### Decision 6: limites do GitHub viram recusa, nunca truncamento calado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:**
- mais de **5 000** resultados: os primeiros 5 000 na ordem da Decision 5 ficam, e o resto vira recusa `limite_do_github` no resumo;
- resumo acima de **1 MiB** (`1_048_576` bytes em UTF-8): a tabela de recusas e cortada no ultimo item que cabe, com uma linha final que diz quantos ficaram de fora.

Os dois limites sao constantes nomeadas, com a URL T1 no comentario.

**Rationale:** regra 20, e os limites sao publicados (T1).

---

### Decision 7: tool MCP `READ_ONLY`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `sparkforge_report_github(findings_path, facts_path: string | string[], repo, source_roots?, category?, fail_on?)` devolve:
- `sarif` (objeto), `summary_markdown` e `annotations`;
- `counts` {`findings`, `located`, `refused`};
- `refused` [{`rule_id`, `reason`, `subject_type`}];
- `gate` {`fail_on`, `tripped`}.

Nao grava. Declara caminho (`findings_path`, `facts_path`, `repo`), entao **nao** entra no conjunto `SEM_CAMINHO` de `tests/test_harness_authorization.py`.

**Consequences:**
- Move os 7 registros manuais (`test_adapters_tools`, `test_harness_authorization`, `parity.yaml`, agent coverage, `manifest.json`, `surface.lock`, `claims.lock`).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `fixtures/sarif/_schema/sarif-schema-2.1.0.json` + `SOURCE.md` | Create | Schema OASIS versionado (URL, sha256, data) | (general) | None |
| 2 | `sparkforge/reporting/__init__.py` | Create | Pacote | @agentspec:python:python-developer | None |
| 3 | `sparkforge/reporting/locate.py` | Create | Resolucao e recusas (Decisions 2 e 3) | @agentspec:python:python-developer | 2 |
| 4 | `sparkforge/reporting/github.py` | Create | Projecao SARIF, resumo, anotacoes, gate e limites | @agentspec:python:python-developer | 3 |
| 5 | `tests/test_reporting_github.py` | Create | Unidade + invariante sobre os 222 findings | @agentspec:test:test-generator | 3, 4 |
| 6 | `sparkforge/adapters/_core.py` | Modify | `report_github`: leitura, validacao, `existe` confinado | (general) | 4 |
| 7 | `sparkforge/adapters/cli.py` | Modify | Subcomando `report github`, escrita com nome fixo, exit code | (general) | 6 |
| 8 | `sparkforge/adapters/tools.py` | Modify | `sparkforge_report_github` + schema de entrada e saida | (general) | 6 |
| 9 | `fixtures/sarif/{pyspark_com_linha,terraform,so_runtime,misto}/` | Create | `input/` (findings, facts, arvore minima), `meta.yaml` (source_roots, fail_on, category), `expected/` (sarif, summary, annotations, exit_code) | (general) | 7 |
| 10 | `tests/test_fixtures_golden_sarif.py` | Create | Golden byte a byte, schema OASIS, gate | @agentspec:test:test-generator | 1, 9 |
| 11 | `scripts/regen_fixtures.py` | Modify | `regen_sarif` | (general) | 9 |
| 12 | Registros manuais (`tests/test_adapters_tools.py`, `tests/test_harness_authorization.py`, `parity.yaml`, agent coverage, `manifest.json`) | Modify | Tool nova | (general) | 8 |
| 13 | `docs/github-code-scanning.md` + `examples/github/sparkforge.yml` | Create | Guia e workflow de exemplo | @agentspec:cloud:ci-cd-specialist | 7 |
| 14 | `.github/workflows/ci.yml` | Modify | Job `sarif-upload` (`workflow_dispatch`, `security-events: write`) | @agentspec:cloud:ci-cd-specialist | 7 |
| 15 | `README.md`, `docs/superpowers/STATUS.md`, `CLAUDE.md` (tabela de verbos, contagem de tools) | Modify | Documentacao com numeros medidos | (general) | all |
| 16 | `docs/surface.lock.json`, `docs/claims.lock.json` + docs auditados | Modify | Gates (`--update`; remediacao por lista de ids) | (general) | all |
| 17 | `.claude/sdd/reports/BUILD_REPORT_SARIF_GITHUB_CHECK.md` | Create | Relatorio | (general) | all |

**Total Files:** 17 entradas (cerca de 30 arquivos fisicos).

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 2, 3, 4 | Funcoes puras, dataclasses, type hints |
| @agentspec:test:test-generator | 5, 10 | pytest, golden, casos de borda |
| @agentspec:cloud:ci-cd-specialist | 13, 14 | GitHub Actions, `upload-sarif`, permissoes |
| (general) | 1, 6–9, 11, 12, 15–17 | Integracao com o adapter e os registros manuais que so este repositorio conhece |

**Agent Discovery:**
- Scanned: agentes do plugin agentspec e os da sessao.
- Matched by: tipo de arquivo, palavra-chave (python, test, CI), caminho.
- Nota de execucao: um escritor por vez na arvore. O briefing de cada agente leva as armadilhas do repositorio: lotes por arquivo, `git add` de `.py` novo, sem `.glob` em `sparkforge/`, sem `def` duplicado no mesmo escopo, os 7 registros manuais, e arquivo vazio na raiz.

---

## Code Patterns

### Pattern 1: localizacao pura (`sparkforge/reporting/locate.py`)

```python
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

SUBJECTS_COM_CODIGO = frozenset({"source_location", "tf_resource"})
SUBJECTS_LOCALIZAVEIS = SUBJECTS_COM_CODIGO | {"plan_node"}
SUBJECTS_DE_RUNTIME = frozenset({"job_run", "stage", "table"})


@dataclass(frozen=True)
class Localizado:
    uri: str
    line: int
    col: int | None


@dataclass(frozen=True)
class Recusa:
    motivo: str


def _uri(file: str, raizes: Sequence[str], existe: Callable[[str], bool]) -> str | Recusa:
    candidatos = [
        str(PurePosixPath(raiz) / file) if raiz != "." else str(PurePosixPath(file))
        for raiz in raizes
    ]
    achados = [c for c in candidatos if existe(c)]
    if not achados:
        return Recusa("arquivo_fora_do_repo")
    if len(achados) > 1:
        return Recusa("caminho_ambiguo")
    return achados[0]


def _de_subject(subject: Mapping[str, Any], tipos: frozenset[str]) -> tuple[str, int, int | None] | None:
    if subject.get("type") in tipos and subject.get("file") and subject.get("line"):
        return str(subject["file"]), int(subject["line"]), subject.get("col")
    return None


def localizar(
    finding: Mapping[str, Any],
    facts_por_id: Mapping[str, Mapping[str, Any]],
    raizes: Sequence[str],
    existe: Callable[[str], bool],
) -> Localizado | Recusa:
    subject = finding.get("subject") or {}
    alvo = _de_subject(subject, SUBJECTS_LOCALIZAVEIS)
    faltou_evidencia = False
    if alvo is None:
        for fact_id in finding.get("evidence") or []:
            fact = facts_por_id.get(fact_id)
            if fact is None:
                faltou_evidencia = True
                continue
            alvo = _de_subject(fact.get("subject") or {}, SUBJECTS_COM_CODIGO)
            if alvo is not None:
                break
    if alvo is None:
        if faltou_evidencia:
            return Recusa("evidencia_ausente")
        if subject.get("type") in SUBJECTS_DE_RUNTIME:
            return Recusa("runtime")
        return Recusa("sem_linha")
    file, line, col = alvo
    uri = _uri(file, raizes, existe)
    if isinstance(uri, Recusa):
        return uri
    return Localizado(uri=uri, line=line, col=int(col) if col else None)
```

### Pattern 2: escape de workflow command (fonte T2: `actions/toolkit`, `packages/core/src/command.ts`)

```python
def _escape_dado(valor: str) -> str:
    return valor.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_propriedade(valor: str) -> str:
    return _escape_dado(valor).replace(":", "%3A").replace(",", "%2C")


_COMANDO_POR_LEVEL = {"error": "error", "warning": "warning", "note": "notice"}


def anotacao(level: str, uri: str, line: int, titulo: str, mensagem: str) -> str:
    propriedades = ",".join(
        f"{k}={_escape_propriedade(v)}"
        for k, v in (("file", uri), ("line", str(line)), ("title", titulo))
    )
    return f"::{_COMANDO_POR_LEVEL[level]} {propriedades}::{_escape_dado(mensagem)}"
```

### Pattern 3: severidade e gate

```python
LEVEL_POR_SEVERIDADE = {"P0": "error", "P1": "error", "P2": "warning", "P3": "note", "P4": "note"}
ORDEM = ("P0", "P1", "P2", "P3", "P4")


def gate_disparou(severidades: Sequence[str], fail_on: str | None) -> bool:
    if fail_on is None:
        return False
    limite = ORDEM.index(fail_on)
    return any(ORDEM.index(s) <= limite for s in severidades)
```

### Pattern 4: `existe` confinado a `--repo` (no `_core`)

```python
def _existe_sob(repo: Path) -> Callable[[str], bool]:
    raiz = repo.resolve()

    def existe(relativo: str) -> bool:
        alvo = (raiz / relativo).resolve()
        return alvo.is_relative_to(raiz) and alvo.is_file()

    return existe
```

---

## Data Flow

```text
1. report github recebe findings.json, facts.json (N), --repo e --source-root
   │
   ▼
2. _core valida a entrada: arquivos existem, JSON legivel, raizes relativas e dentro de --repo
   (senao exit 2), e monta facts_por_id a partir da uniao
   │
   ▼
3. locate.localizar para cada finding → Localizado | Recusa(motivo)
   │
   ▼
4. github.projetar → sarif, summary, annotations, gate (limites aplicados e nomeados)
   │
   ▼
5a. CLI: grava .sparkforge/report/{sparkforge.sarif, summary.md}; anotacoes no stdout;
    contagem no stderr; exit 0|1
5b. MCP: devolve o mesmo, sem gravar
   │
   ▼
6. Workflow: upload-sarif (Code Scanning) + summary.md >> $GITHUB_STEP_SUMMARY
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| GitHub Code Scanning | `github/codeql-action/upload-sarif`, no workflow e nao no pacote | `GITHUB_TOKEN` com `security-events: write` |
| GitHub Actions | Workflow commands no stdout; `$GITHUB_STEP_SUMMARY` | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | `localizar` (cada motivo de recusa, subject contra evidencia, ambiguidade), escape (os 5 caracteres), gate (fronteiras), limites (5 000 e 1 MiB com entrada sintetica), ordem deterministica | `tests/test_reporting_github.py` | pytest | Todos os ramos de `locate.py` e `github.py` |
| Invariant | Os 222 findings de `fixtures/**/expected/findings.json`: SARIF + recusa = total, e nenhum resultado sem arquivo existente e linha | `tests/test_reporting_github.py` | pytest | Corpus inteiro |
| Golden | 4 casos byte a byte (SARIF, resumo, anotacoes, exit code) | `tests/test_fixtures_golden_sarif.py` | pytest | AT-001 a AT-008 |
| Schema | Todo SARIF dos testes contra o schema OASIS versionado | `tests/test_fixtures_golden_sarif.py` | `jsonschema` | 100% dos SARIF |
| Adapter | CLI (exit 0/1/2, nomes fixos, stdout so com anotacoes) e tool (mesmo resultado, nada gravado) | `tests/test_adapters_tools.py`, testes da CLI | pytest | AT-011, AT-012 |
| E2E | Upload real por `workflow_dispatch`; `gh api .../code-scanning/sarifs/{id}` com `processing_status: complete` e `results_count` | `ci.yml` job `sarif-upload` | GitHub | AT-013 |

**Cobertura dos AT:**

| AT | Onde |
|----|------|
| AT-001, 002, 004 | golden `pyspark_com_linha`, `terraform`, `so_runtime` |
| AT-003, 005, 006 | golden `misto` + unidade |
| AT-007, 008 | unidade + golden (`exit_code`) |
| AT-009 | unidade |
| AT-010 | invariante |
| AT-011, 012 | adapter |
| AT-013 | E2E |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `--findings` ou `--facts` ausente ou com JSON invalido | Exit 2, mensagem acionavel (envelope `{error, exit_code}` na tool) | No |
| `--source-root` absoluto, com `..` ou fora de `--repo` | Exit 2 | No |
| Fact de evidencia ausente da uniao | Recusa `evidencia_ausente`, sem excecao | No |
| Mais de 5 000 resultados | Recusa `limite_do_github` para o excedente | No |
| Resumo acima de 1 MiB | Corte nomeado da tabela de recusas | No |
| Falha ao gravar `.sparkforge/report/` | Exit 2 com a causa; nada parcial fica gravado (escrita em temporario e depois `replace`) | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--source-root` | str (repetivel) | `.` | Raizes relativas a `--repo`, na ordem dos `analyze` |
| `--fail-on` | `P0` \| `P1` | ausente | Gate de severidade |
| `--category` | str | ausente | `runAutomationDetails.id = "<category>/"` |
| `LIMITE_RESULTADOS` | int | `5000` | T1: resultados exibidos por run |
| `LIMITE_SUMARIO_BYTES` | int | `1_048_576` | T1: tamanho do step summary |

---

## Security Considerations

- Nenhuma rede no pacote: o upload e do workflow (`offline-strict` intacto).
- Nenhum caminho do argv usado para escrita. A leitura do argv (`--findings`, `--facts`) segue o padrao dos outros verbos, e `--source-root` e confinado a `--repo` por `resolve()` + `is_relative_to`.
- Texto de finding vai para o stdout como anotacao, e ele pode conter `::` ou quebra de linha. O escape T2 impede que o finding injete outro workflow command.
- O resumo Markdown inclui texto das regras (do catalogo, controlado pelo repositorio) e caminhos. Sem HTML cru: `|` e quebras de linha escapados nas celulas.
- O Snyk Code roda sobre `sparkforge/reporting` e o handler da CLI antes do commit.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Uma linha de contagem no stderr (Decision 4) |
| Metrics | Os spans de `call_tool` gravam a chamada da tool como qualquer outra (regra 27) |
| Tracing | N/A |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Item 1 (schema) + conferir sha256 | Schema carregado pelo `jsonschema` |
| B2 | Itens 2–5 | Unidade verde e invariante sobre os 222 |
| B3 | Itens 6–8 e 12 | CLI e tool verdes; 7 registros atualizados |
| B4 | Itens 9–11 | Golden e schema verdes |
| B5 | Itens 13–14 | Workflow valido (`actionlint`, se disponivel) |
| B6 | Itens 15–16; ruff, suite por lotes, gates, Snyk | Tudo verde |
| B7 | Commit, push, PR; `workflow_dispatch` do `sarif-upload` | SC6: analise aceita |
| B8 | Item 17 e statuses | — |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | design-agent | Versao inicial |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_SARIF_GITHUB_CHECK.md`
