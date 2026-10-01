---
sdd: 1
feature: TOOLS_OK
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/TOOLS_OK/design.md
  sha256: "094822c067da39071b5ed951455f82a2e778de41d0fb5d153e87a134593e89f1"
tasks:
  - id: T1
    files: [tests/test_tools_ok_rule.py, CLAUDE.md, AGENTS.md, docs/claims.lock.json]
    covers: [AC1, AC2, AC3, AC4]
    test: {path: tests/test_tools_ok_rule.py, name: test_claude_md_abre_com_a_regra_de_prova}
  - id: T2
    files: [tests/test_tools_ok_rule.py, evals/agentic/fase0/baselines]
    covers: [AC5]
    test: {path: tests/test_tools_ok_rule.py, name: test_baseline_tools_ok_gravado}
---

# TOOLS_OK — plano

Regras: as de `C:\Users\edgar\AppData\Local\Temp\claude\E--projetos-spark-forge-aws\aecdc55f-7550-4610-801b-0b1e6d24fd0a\scratchpad\contexto.md`
(edição por ferramenta, LF, commit por `git commit -F` com as duas linhas de
atribuição, gate de lastro antes de commit com `.py` novo, NUNCA
`tests/test_agents_parity.py`), branch `sdd/tools-ok`, pouca memória: um comando por
vez, nunca os lotes.

## T1 — a regra e a trava

1. Teste, em `tests/test_tools_ok_rule.py` (arquivo novo):

```python
"""A regra de prova no que o host injeta, e os verbos que ela cita."""
import json
import re
from pathlib import Path

import yaml

from sparkforge.adapters.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]
MARCA_PT = "## Antes de responder sobre artefato, rode o verbo"
MARCA_EN = "## Before answering about an artifact, run the verb"


def _bloco(arquivo: str, marca: str) -> tuple[str, int, str]:
    texto = (ROOT / arquivo).read_text(encoding="utf-8")
    assert marca in texto, f"{arquivo} sem o bloco {marca!r}"
    inicio = texto.index(marca)
    fim = texto.find("\n## ", inicio + 1)
    return texto, inicio, texto[inicio : fim if fim != -1 else len(texto)]


def _tools(bloco: str) -> set[str]:
    return set(re.findall(r"`(sparkforge_[a-z_]+)`", bloco))


def test_claude_md_abre_com_a_regra_de_prova():
    texto, inicio, bloco = _bloco("CLAUDE.md", MARCA_PT)
    assert inicio < texto.index("Ao trabalhar em código PySpark")
    assert "fact_id" in bloco and "rule_id" in bloco
    assert _tools(bloco)


def test_agents_md_carrega_a_mesma_regra():
    _, _, pt = _bloco("CLAUDE.md", MARCA_PT)
    texto, inicio, en = _bloco("AGENTS.md", MARCA_EN)
    assert inicio < texto.index("This repository contains")
    assert "fact_id" in en and "rule_id" in en
    assert _tools(en) == _tools(pt)


def test_verbos_da_regra_existem_e_cobrem_a_suite():
    _, _, bloco = _bloco("CLAUDE.md", MARCA_PT)
    citadas = _tools(bloco)
    assert citadas <= set(TOOLS), sorted(citadas - set(TOOLS))
    suite = yaml.safe_load(
        (ROOT / "evals" / "agentic" / "fase0" / "suite.yaml").read_text(encoding="utf-8")
    )
    for pergunta in suite["questions"]:
        for item in pergunta["required_tools"]:
            alternativas = item if isinstance(item, list) else [item]
            assert any(f"sparkforge_{a}" in citadas for a in alternativas), (
                pergunta["id"],
                alternativas,
            )
```

2. Vermelho: `python -m pytest tests/test_tools_ok_rule.py::test_claude_md_abre_com_a_regra_de_prova -q`
   — `AssertionError: CLAUDE.md sem o bloco ...`.

3. Texto. No `CLAUDE.md`, entre a linha 1 (`# SparkForge AWS — Instruções do
   repositório`) e a linha `Ao trabalhar em código PySpark destinado ao AWS Glue:`,
   entra (com uma linha em branco antes e depois):

```markdown
## Antes de responder sobre artefato, rode o verbo

Pergunta sobre um artefato do repositório — código, plano, event log, custo, versão
ou regra — se responde pelo verbo do SparkForge, não pela leitura do arquivo. Chame a
tool MCP e cite na resposta o `fact_id` ou o `rule_id` que a sustenta. Ler o artefato
no olho vem depois do verbo, para conferir, nunca no lugar dele.

| Pergunta sobre | Tool MCP |
|---|---|
| código PySpark | `sparkforge_analyze_pyspark`, depois `sparkforge_judge` |
| plano físico (`explain`) | `sparkforge_analyze_plan`, depois `sparkforge_judge` |
| event log do Spark | `sparkforge_analyze_event_log`, depois `sparkforge_judge` |
| regra do catálogo | `sparkforge_rules_lookup` |
| versão e runtime | `sparkforge_runtime_detect` ou `sparkforge_release_describe` |
| custo de um run | `sparkforge_finops` |
| antes e depois entre dois runs | `sparkforge_benchmark` |
```

   No `AGENTS.md`, entre a linha 1 (`# Agent Instructions — SparkForge AWS`) e a linha
   que começa com `This repository contains`, entra:

```markdown
## Before answering about an artifact, run the verb

A question about a repository artifact — code, plan, event log, cost, version or rule
— is answered through the SparkForge verb, not by reading the file. Call the MCP tool
and cite in the answer the `fact_id` or `rule_id` that supports it. Reading the
artifact directly comes after the verb, to double-check, never instead of it.

| Question about | MCP tool |
|---|---|
| PySpark code | `sparkforge_analyze_pyspark`, then `sparkforge_judge` |
| physical plan (`explain`) | `sparkforge_analyze_plan`, then `sparkforge_judge` |
| Spark event log | `sparkforge_analyze_event_log`, then `sparkforge_judge` |
| catalog rule | `sparkforge_rules_lookup` |
| version and runtime | `sparkforge_runtime_detect` or `sparkforge_release_describe` |
| cost of a run | `sparkforge_finops` |
| before and after between two runs | `sparkforge_benchmark` |
```

4. Verde: `python -m pytest tests/test_tools_ok_rule.py -k "not baseline" -q`, depois
   `python -m pytest tests/test_bootstrap_budget.py tests/test_docs_coverage.py -q`
   (AC4; se o teto estourar, pare e relate — não encurte outras regras sem decisão).
5. `python scripts/check_vnext_claims.py` (arquivo `.py` novo; remedie por id).
   `python scripts/check_status_numbers.py --strict`. `python -m ruff check sparkforge scripts tests`.
6. Commit: `docs(agents): answer artifact questions through the verb first`.

## T2 — a medida

Só com o OK do operador para o custo (U1) e a máquina livre (U2).

1. Teste, em `tests/test_tools_ok_rule.py`:

```python
def test_baseline_tools_ok_gravado():
    base = ROOT / "evals" / "agentic" / "fase0" / "baselines"
    novos = sorted(p for p in base.iterdir() if p.name.endswith("-tools-ok"))
    assert novos, "baseline -tools-ok ausente"
    rodadas = sorted(novos[-1].glob("r*.json"))
    assert len(rodadas) >= 3
    for rodada in rodadas:
        totais = json.loads(rodada.read_text(encoding="utf-8"))["totals"]
        assert {"tools_ok", "correct", "questions"} <= set(totais)
```

2. Vermelho: `python -m pytest tests/test_tools_ok_rule.py::test_baseline_tools_ok_gravado -q`
   — `AssertionError: baseline -tools-ok ausente`.
3. Rodada: `python scripts/run_agentic_eval.py --suite fase0 --model haiku --runs 3`.
   O runner grava em `~/.sparkforge/agentic-evals/fase0-<data>/r1.json..r3.json`
   (`OUT_BASE` em `scripts/run_agentic_eval.py`). Copie os três `r*.json` para
   `evals/agentic/fase0/baselines/<AAAA-MM-DD>-haiku-4-5-tools-ok/`, no formato dos
   baselines vizinhos (confira se eles carregam mais algum arquivo além de `r*.json`,
   e siga igual).
4. Verde: o comando do passo 2.
5. Commit: `evals(agentic): fase0 baseline with the proof rule`, com, no corpo, a
   mediana de `tools_ok` e o acerto por repetição contra 2026-09-16 (3, 3, 1 e 9, 9, 10),
   sem afirmar causa além do experimento.
