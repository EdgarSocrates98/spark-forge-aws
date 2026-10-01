# Plano de aplicação na resposta do `judge` — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer a ordem de aplicação, o lastro por achado, as restrições de sequenciamento e as lacunas nomeadas chegarem a quem chama `sparkforge_judge`, sem que o `judge` deixe de ser read-only.

**Architecture:** Um módulo novo `digest.py` monta o bloco a partir dos módulos do executor que já existem, sem criar entidade e sem tocar o disco. `run.py` passa a usá-lo em vez de repetir a sequência, para que `judge` e `arbitrate` nunca divirjam. `judge_findings` só chama e anexa.

**Tech Stack:** Python 3.11+, dataclasses frozen, JSON, pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-plano-de-aplicacao-no-judge-design.md`

---

## Antes da Tarefa 1 — a confirmação que precede o código

A §7 do spec afirma que **os goldens de fixture não mudam**, porque guardam
`expected/findings.json` produzido por `run_judge`, e não a resposta do adapter.
Se isso estiver errado, o custo da entrega triplica e o desenho volta à mesa.

**Confirme antes de escrever qualquer linha:**

```bash
TOKENSAVE_DISABLE_GREP_HOOK=1 grep -rn "judge_findings" tests/test_fixtures_golden*.py | head
python -c "
import inspect, sparkforge.rules.engine as e
print('run_judge devolve Finding, nao dict:', inspect.signature(e.judge))
"
```

Se algum `test_fixtures_golden*` chamar `judge_findings` (o adapter) em vez de
`run_judge` (o motor), **pare e reporte** — o desenho pressupõe que não chamam.

---

## Estrutura de arquivos

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/agentic/executor/digest.py` | monta o bloco `plan` e o mapa de lastro, sem gravar |
| `tests/test_agentic_executor_digest.py` | testes do digest |
| `tests/test_adapters_judge_plan.py` | testes do bloco na resposta do adapter |

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/agentic/executor/claims.py` | expõe `standing_for_finding`; `claims_from_findings` passa a usá-la |
| `sparkforge/agentic/executor/run.py` | passa a usar `plan_digest` |
| `sparkforge/adapters/_core.py` | `judge_findings` anexa `plan` e `evidence_standing` |
| `sparkforge/adapters/tools.py` | `outputSchema` de `sparkforge_judge` |
| `docs/surface.lock.json` | crescimento do schema |

---

## Task 1: `standing_for_finding` — os três insumos, num lugar só

**Files:**
- Modify: `sparkforge/agentic/executor/claims.py`
- Test: `tests/test_agentic_executor_claims.py`

Hoje `claims_from_findings` computa `tier`, `dentro` e `medidas_presentes`
dentro do laço e os passa a `confidence_for`. O bloco de lastro precisa dos três
**por finding**. Recomputá-los em `digest.py` duplicaria a regra, e as duas
cópias divergiriam — que é o defeito que este spec evita entre `digest` e `run`.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_agentic_executor_claims.py`:

```python
from sparkforge.agentic.executor.authority import load_authority_map
from sparkforge.agentic.executor.claims import standing_for_finding

_MAPA = load_authority_map()


class TestStandingForFinding:
    def test_devolve_os_tres_insumos_mais_o_valor(self):
        finding = {
            "rule_id": "SF-WASTE-001",
            "evidence": ["f_aaa111"],
            "runtime_scope": {},
            "sources": [{"url": "https://docs.aws.amazon.com/glue/x.html"}],
        }
        s = standing_for_finding(finding, {"f_aaa111"}, _MAPA, {"glue": "5.0"})
        assert s == {
            "value": "high",
            "source_tier": "T1_OFFICIAL_DOCS",
            "in_version_scope": True,
            "measures_present": True,
        }

    def test_fora_do_escopo_de_versao_e_medium(self):
        finding = {
            "rule_id": "SF-X-001",
            "evidence": ["f_aaa111"],
            "runtime_scope": {"glue": ["4.0"]},
            "sources": [{"url": "https://docs.aws.amazon.com/glue/x.html"}],
        }
        s = standing_for_finding(finding, {"f_aaa111"}, _MAPA, {"glue": "6.0"})
        assert s["value"] == "medium"
        assert s["in_version_scope"] is False
        assert s["source_tier"] == "T1_OFFICIAL_DOCS"

    def test_medida_ausente_e_low_mesmo_com_t1(self):
        finding = {
            "rule_id": "SF-X-001",
            "evidence": ["f_ausente"],
            "runtime_scope": {},
            "sources": [{"url": "https://docs.aws.amazon.com/glue/x.html"}],
        }
        s = standing_for_finding(finding, set(), _MAPA, {"glue": "5.0"})
        assert s["value"] == "low"
        assert s["measures_present"] is False

    def test_o_valor_bate_com_o_confidence_da_claim(self):
        """A funcao nova e a que `claims_from_findings` usa -- se as duas
        divergirem, o `judge` diz uma coisa e o `arbitrate` outra."""
        from sparkforge.agentic.executor.claims import claims_from_findings

        finding = {
            "rule_id": "SF-WASTE-001",
            "title": "t",
            "evidence": ["f_aaa111"],
            "runtime_scope": {},
            "sources": [{"url": "https://docs.aws.amazon.com/glue/x.html"}],
        }
        facts = [{"id": "f_aaa111", "kind": "glue.utilization.summary"}]
        claims, _ = claims_from_findings([finding], facts, _MAPA, {"glue": "5.0"})
        s = standing_for_finding(finding, {"f_aaa111"}, _MAPA, {"glue": "5.0"})
        assert claims[0].confidence == s["value"]
```

- [ ] **Step 2: Rodar e ver falhar pelo motivo certo**

Run: `python -m pytest tests/test_agentic_executor_claims.py::TestStandingForFinding -v`
Expected: FAIL com `ImportError: cannot import name 'standing_for_finding'`

- [ ] **Step 3: Extrair a função**

Em `sparkforge/agentic/executor/claims.py`, acrescentar (e **fazer
`claims_from_findings` usá-la**, substituindo o cálculo inline das três
variáveis):

```python
def standing_for_finding(
    finding: dict[str, Any],
    ids_presentes: set[str],
    authority_map: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    """Os tres insumos do lastro, e o valor que eles produzem.

    Existe como funcao propria porque DOIS consumidores precisam do mesmo
    calculo: `claims_from_findings`, que o usa para o `confidence` da Claim, e
    `digest.plan_digest`, que o publica na resposta do `judge`. Recomputa-lo no
    segundo faria as duas leituras divergirem com o tempo -- e o operador veria
    o `judge` afirmar um lastro e o `arbitrate` afirmar outro sobre o mesmo
    achado.

    O valor NUNCA viaja sozinho: rotulo de confianca sem os insumos que o
    produziram e o que a §5.1 do spec do executor proibiu ao recusar publicar o
    score de `assess_claim`.
    """
    refs = _fact_ids_declarados(finding)
    medidas_presentes = bool(refs) and all(ref in ids_presentes for ref in refs)
    escopo = dict(finding.get("runtime_scope") or {})
    dentro = in_scope(escopo, runtime or {})
    tier = _melhor_tier(list(finding.get("sources") or []), authority_map)
    return {
        "value": confidence_for(tier, dentro, medidas_presentes),
        "source_tier": tier.name,
        "in_version_scope": dentro,
        "measures_present": medidas_presentes,
    }
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_claims.py -v`
Expected: PASS em todos, inclusive os que já existiam — a refatoração não pode
mudar o `confidence` de claim nenhuma.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/claims.py tests/test_agentic_executor_claims.py
git commit -m "refactor(executor): os tres insumos do lastro viram funcao propria, para nao serem recomputados"
```

---

## Task 2: `digest.py` — o bloco, sem gravar

**Files:**
- Create: `sparkforge/agentic/executor/digest.py`
- Test: `tests/test_agentic_executor_digest.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""O bloco de plano que o `judge` publica.

Ele e CALCULADO e nao gravado: nenhuma entidade e criada, nenhum arquivo e
escrito. O registro auditavel continua sendo `sparkforge arbitrate`.
"""

from __future__ import annotations

import json
import pathlib

from sparkforge.agentic.executor.digest import plan_digest
from sparkforge.findings.models import Fact

_RUNTIME = {"glue": "5.0", "spark": "3.5.4"}


def _uniao(nome: str) -> tuple[list[dict], list[dict]]:
    """Facts do case = entrada (com id computado) + derivados. Ver §12.9 do
    spec do executor: alimentar com o subconjunto fabrica claim desancorada."""
    base = pathlib.Path("fixtures") / nome
    entrada = json.loads((base / "input" / "facts.json").read_text(encoding="utf-8"))
    entrada = entrada if isinstance(entrada, list) else entrada.get("facts", [])
    facts = []
    vistos = set()
    for f in entrada:
        obj = Fact(
            kind=f["kind"],
            subject=f.get("subject", {}),
            measures=f.get("measures", {}),
            attrs=f.get("attrs", {}),
        )
        if obj.id not in vistos:
            vistos.add(obj.id)
            facts.append(dict(f, id=obj.id))
    derivados = json.loads((base / "expected" / "facts.json").read_text(encoding="utf-8"))
    derivados = derivados if isinstance(derivados, list) else derivados.get("facts", [])
    for f in derivados:
        if f.get("id") not in vistos:
            vistos.add(f.get("id"))
            facts.append(f)
    findings = json.loads((base / "expected" / "findings.json").read_text(encoding="utf-8"))
    findings = findings if isinstance(findings, list) else findings.get("findings", [])
    return findings, facts


class TestFormaDoBloco:
    def test_bloco_tem_as_chaves_declaradas(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, standing = plan_digest(findings, facts, _RUNTIME)
        assert set(bloco) == {
            "scope",
            "order",
            "order_unresolved",
            "constraints",
            "contradictions",
            "objections",
            "unresolved",
            "persisted",
            "note",
        }

    def test_persisted_e_sempre_falso(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, _ = plan_digest(findings, facts, _RUNTIME)
        assert bloco["persisted"] is False
        assert "arbitrate" in bloco["note"]

    def test_caso_sem_nada_produz_listas_vazias_e_nao_bloco_ausente(self):
        bloco, standing = plan_digest([], [], _RUNTIME)
        assert bloco["order"] == []
        assert bloco["constraints"] == []
        assert bloco["contradictions"] == []
        assert bloco["objections"] == []
        assert bloco["unresolved"] == []
        assert standing == {}

    def test_scope_nomeia_o_conjunto_e_a_contagem(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, _ = plan_digest(findings, facts, _RUNTIME)
        assert str(len(findings)) in bloco["scope"]


class TestLastro:
    def test_standing_tem_uma_entrada_por_finding_com_rule_id(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        _, standing = plan_digest(findings, facts, _RUNTIME)
        assert set(standing) == {f["rule_id"] for f in findings}
        for valor in standing.values():
            assert set(valor) == {
                "value",
                "source_tier",
                "in_version_scope",
                "measures_present",
            }


class TestNaoGrava:
    def test_nenhum_arquivo_e_criado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        antes = set(tmp_path.rglob("*"))
        plan_digest(
            [{"rule_id": "SF-X-001", "evidence": [], "sources": [], "runtime_scope": {}}],
            [],
            _RUNTIME,
        )
        assert set(tmp_path.rglob("*")) == antes


class TestNaoPublicaScore:
    def test_bloco_nao_carrega_score(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, standing = plan_digest(findings, facts, _RUNTIME)
        texto = json.dumps([bloco, standing])
        assert "score" not in texto
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_agentic_executor_digest.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.agentic.executor.digest'`

- [ ] **Step 3: Escrever o módulo**

```python
"""O plano de aplicacao, calculado e nao gravado.

`plan_digest` monta o bloco que o `judge` publica: ordem, restricoes de
sequenciamento, contradicoes, objecoes e lacunas, mais o lastro por achado.

Ele NAO cria entidade e NAO toca o disco. `sparkforge_judge` e `READ_ONLY` e
continua sendo -- faze-lo gravar mudaria a cadeia de autorizacao de uma tool que
muitas skills chamam, e faria um verbo de leitura escrever no repositorio do
operador. O registro auditavel (blackboard, ADR, decisoes, `DebatePlan`
completo) continua sendo `sparkforge arbitrate`.

`run.py` usa este modulo em vez de repetir a sequencia: se os dois montassem o
plano por conta propria, divergiriam, e o operador veria o `judge` afirmar uma
ordem e o `arbitrate` outra sobre o mesmo case.
"""

from __future__ import annotations

from typing import Any

from sparkforge.agentic.executor.authority import load_authority_map
from sparkforge.agentic.executor.claims import standing_for_finding
from sparkforge.agentic.executor.conflict import conditional_conflicts, direct_conflicts
from sparkforge.agentic.executor.ordering import order_actions
from sparkforge.agentic.executor.unknowns import unknowns_from

_NOTA = (
    "calculado, nao gravado. O registro auditavel e `sparkforge arbitrate`."
)


def plan_digest(
    findings: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    runtime: dict[str, Any],
    authority_map: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Devolve `(bloco, lastro_por_rule_id)`.

    `bloco["scope"]` nomeia o conjunto e a contagem de proposito: a ordem e
    propriedade do CASO, e um consumidor que recebeu uma pagina leria a ordem
    como completa se nada dissesse o contrario.

    Chave ausente e pior que lista vazia: forma estavel e o que permite ao
    consumidor confiar na chave em vez de testar se ela existe. Por isso o bloco
    sai com as mesmas nove chaves sempre, mesmo num case sem achado nenhum.
    """
    mapa = authority_map if authority_map is not None else load_authority_map()
    findings = list(findings or [])
    facts = list(facts or [])

    ids_presentes = {
        str(f.get("id")) for f in facts if isinstance(f, dict) and f.get("id")
    }

    acao_por_regra = {
        str(f.get("rule_id")): (f.get("action") or {})
        for f in findings
        if f.get("rule_id")
    }

    ordem, restricoes, ordem_unresolved = order_actions(findings)

    contradicoes = [
        {
            "rules": [a, b],
            "target": str(acao_por_regra.get(a, {}).get("target") or ""),
            "directions": [
                str(acao_por_regra.get(a, {}).get("direction") or ""),
                str(acao_por_regra.get(b, {}).get("direction") or ""),
            ],
        }
        for a, b in direct_conflicts(findings)
    ]

    objecoes = [
        {"rule": rule_id, "blocked_by_kind": kind, "fact_id": fact_id}
        for rule_id, kind, fact_id in conditional_conflicts(findings, facts)
    ]

    lacunas = [
        {"question": u.question, "evidence_needed": list(u.evidence_needed)}
        for u in unknowns_from(findings, facts)
    ]

    lastro = {
        str(f["rule_id"]): standing_for_finding(f, ids_presentes, mapa, runtime)
        for f in findings
        if f.get("rule_id")
    }

    bloco = {
        "scope": (
            f"todos os {len(findings)} achados deste case, nao a pagina"
        ),
        "order": ordem,
        "order_unresolved": ordem_unresolved,
        "constraints": restricoes,
        "contradictions": contradicoes,
        "objections": objecoes,
        "unresolved": lacunas,
        "persisted": False,
        "note": _NOTA,
    }
    return bloco, lastro
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_digest.py -v`
Expected: PASS nos oito.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/digest.py tests/test_agentic_executor_digest.py
git commit -m "feat(executor): o plano de aplicacao calculado, sem entidade e sem disco"
```

---

## Task 3: `run.py` passa a usar `digest.py`

**Files:**
- Modify: `sparkforge/agentic/executor/run.py`
- Test: `tests/test_agentic_executor_run.py`

**Este é o passo que impede as duas leituras de divergirem.** Hoje `run.py`
chama `direct_conflicts`, `conditional_conflicts`, `order_actions` e
`unknowns_from` por conta própria. Depois desta tarefa ele obtém os mesmos
resultados de `plan_digest`, e segue fazendo o que só ele faz: criar entidades,
arbitrar, decidir, gerar ADR e gravar.

- [ ] **Step 1: Escrever o teste que trava a igualdade**

Acrescentar a `tests/test_agentic_executor_run.py`:

```python
class TestJudgeEArbitrateNaoDivergem:
    def test_ordem_e_contradicoes_batem_com_o_digest(self, tmp_path):
        """O `judge` publica o que `plan_digest` monta; o `arbitrate` grava a
        partir do MESMO calculo. Se estes dois numeros divergirem, o operador
        ve o `judge` afirmar uma ordem e o `arbitrate` outra sobre o mesmo case.
        """
        from sparkforge.agentic.executor.digest import plan_digest
        from sparkforge.agentic.executor import run_executor

        findings, facts = _fixture_uniao("timeout/timeout_com_spill_e_skew")
        runtime = {"glue": "5.0", "spark": "3.5.4"}

        bloco, _ = plan_digest(findings, facts, runtime)
        saida = run_executor(findings, facts, root=tmp_path, runtime=runtime)

        assert saida["order"] == bloco["order"]
        assert saida["order_constraints"] == bloco["constraints"]
        assert len(saida["contradictions"]) == len(bloco["contradictions"])
        assert len(saida["unknowns"]) == len(bloco["unresolved"])
```

`_fixture_uniao` é o helper de união que já existe naquele arquivo desde a
Tarefa 19 do plano anterior — reuse-o; se o nome divergir, use o que estiver lá.

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_run.py::TestJudgeEArbitrateNaoDivergem -v`
Expected: PASS já — as duas implementações concordam **hoje**. O teste existe
para pegar a divergência que uma mudança futura introduziria.

- [ ] **Step 3: Refatorar `run.py` para consumir o digest**

Em `run_executor`, substituir as chamadas diretas por:

```python
    from sparkforge.agentic.executor.digest import plan_digest

    bloco, _lastro = plan_digest(findings, facts, runtime, authority_map=mapa)
    ordem = bloco["order"]
    restricoes = bloco["constraints"]
    ordem_unresolved = bloco["order_unresolved"]
```

As contradições e objeções continuam vindo de `direct_conflicts` e
`conditional_conflicts` **em forma de tupla**, porque `run.py` precisa dos ids
crus para montar `Contradiction` e `Objection` — o bloco os traz já
serializados, e reparsear dicionário para reconstruir tupla seria pior que
chamar a função duas vezes. Deixe isso escrito em comentário no código.

- [ ] **Step 4: Rodar o executor inteiro**

Run: `python -m pytest tests/test_agentic_executor_*.py -q`
Expected: PASS, sem regressão nos 163 mais os novos.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/run.py tests/test_agentic_executor_run.py
git commit -m "refactor(executor): run.py consome o digest, e um teste trava a igualdade das duas leituras"
```

---

## Task 4: `judge_findings` anexa o bloco e o lastro

**Files:**
- Modify: `sparkforge/adapters/_core.py` (a montagem do `result`, por volta da linha 2889)
- Test: `tests/test_adapters_judge_plan.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""O bloco de plano na resposta do adapter.

O `judge` continua READ_ONLY: ele CALCULA o plano e nao grava nada.
"""

from __future__ import annotations

import json

from sparkforge.adapters._core import judge_findings

_FACTS = "fixtures/waste/folga_medida_sem_skew/input/facts.json"


class TestBlocoNaResposta:
    def test_resposta_traz_o_bloco_plan(self):
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        assert "plan" in r
        assert r["plan"]["persisted"] is False

    def test_cada_item_traz_evidence_standing_com_os_insumos(self):
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        assert r["items"], "a fixture precisa produzir ao menos um finding"
        for item in r["items"]:
            s = item["evidence_standing"]
            assert set(s) == {
                "value",
                "source_tier",
                "in_version_scope",
                "measures_present",
            }

    def test_evidence_standing_nao_substitui_o_confidence_da_regra(self):
        """Sao dois campos com semantica diferente: `confidence` vem da regra,
        `evidence_standing` e computado a partir de tier, escopo e medida.
        Comparar os dois por valor nao provaria nada -- um e string e o outro
        e mapa, e a desigualdade seria verdadeira por tipo."""
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        item = r["items"][0]
        assert isinstance(item["confidence"], str)
        assert isinstance(item["evidence_standing"], dict)
        assert item["confidence"] in {"high", "medium", "low"}
        assert item["evidence_standing"]["value"] in {"high", "medium", "low"}

    def test_a_ordem_e_do_conjunto_e_nao_da_pagina(self):
        inteiro = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        pagina = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4", limit=1)
        assert pagina["returned_count"] <= 1
        assert pagina["plan"]["order"] == inteiro["plan"]["order"]
        assert str(inteiro["total_count"]) in pagina["plan"]["scope"]

    def test_resposta_nao_carrega_score(self):
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        assert "score" not in json.dumps(r)

    def test_judge_nao_escreve_nada(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        antes = set(tmp_path.rglob("*"))
        judge_findings(
            facts=[{"kind": "glue.utilization.summary", "subject": {}, "measures": {}}],
            glue="5.0",
        )
        assert set(tmp_path.rglob("*")) == antes
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_adapters_judge_plan.py -v`
Expected: FAIL com `KeyError: 'plan'`

- [ ] **Step 3: Anexar em `judge_findings`**

Em `sparkforge/adapters/_core.py`, **depois** do filtro de severidade e
**antes** de `paginate_items`, e depois anexar ao `result`:

```python
    # O plano cobre os findings DEPOIS do filtro de severidade e ANTES da
    # paginacao: ele e do conjunto que o operador pediu, nao da pagina que
    # coube. Ordem parcial apresentada como ordem e a familia de afirmacao que
    # este projeto recusa -- por isso `scope` carrega a contagem.
    from sparkforge.agentic.executor.digest import plan_digest

    plano, lastro = plan_digest(finding_dicts, [f.to_dict() for f in fact_list], runtime)
    for item in finding_dicts:
        standing = lastro.get(item.get("rule_id"))
        if standing is not None:
            item["evidence_standing"] = standing
```

e, na montagem do `result`, acrescentar a chave:

```python
        "plan": plano,
```

**Confirme a forma de `fact_list`** antes de escrever: se ele já for lista de
`dict`, remova o `.to_dict()`; se for lista de `Fact`, mantenha. Rode
`python -c "..."` para ver.

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_adapters_judge_plan.py -v`
Expected: PASS nos seis.

- [ ] **Step 5: Rodar os oito que leem a resposta de `judge`**

Run:
```bash
python -m pytest tests/test_adapters_tools.py tests/test_capability_parity.py \
  tests/test_adapters_detail_level.py tests/test_adapters_code_surface.py \
  tests/test_harness_authorization.py tests/test_runtime_inferred_from_facts.py \
  tests/test_emr_eks_area_boundary.py tests/test_emr_serverless_runtime_boundary.py -q
```
Expected: PASS. Se algum comparar a resposta inteira, ele precisa da chave nova
— acrescente ao esperado, **não** remova o bloco.

- [ ] **Step 6: Rodar os goldens, para confirmar a premissa do spec**

Run: `python -m pytest tests/test_fixtures_golden.py -q`
Expected: 90 passando, **sem nenhuma mudança em golden**. Se algum quebrar, a
premissa da §7 do spec estava errada — **pare e reporte**.

- [ ] **Step 7: Commit**

```bash
git add sparkforge/adapters/_core.py tests/test_adapters_judge_plan.py
git commit -m "feat(judge): a resposta traz o plano de aplicacao e o lastro por achado"
```

---

## Task 5: `outputSchema` da tool e o lock de superfície

**Files:**
- Modify: `sparkforge/adapters/tools.py`
- Modify: `docs/surface.lock.json`
- Test: `tests/test_adapters_tools.py`

- [ ] **Step 1: Medir a superfície antes**

Run: `python scripts/check_surface_lock.py`
Anote os bytes de tools — o crescimento vai declarado no commit (regra 26).

- [ ] **Step 2: Escrever o teste que falha**

Acrescentar a `tests/test_adapters_tools.py`:

```python
class TestJudgeDeclaraOPlano:
    def test_outputschema_declara_plan_e_evidence_standing(self):
        from sparkforge.adapters.tools import TOOLS

        schema = json.dumps(TOOLS["sparkforge_judge"])
        assert "plan" in schema
        assert "evidence_standing" in schema

    def test_a_descricao_diz_que_nao_grava(self):
        from sparkforge.adapters.tools import TOOLS

        desc = TOOLS["sparkforge_judge"]["description"].lower()
        assert "nao grava" in desc or "não grava" in desc
        assert "arbitrate" in desc

    def test_judge_continua_read_only(self):
        from sparkforge.adapters.tools import TOOLS
        from sparkforge.harness.authorization import ToolClass, classify

        assert classify("sparkforge_judge", TOOLS["sparkforge_judge"]) is ToolClass.READ_ONLY
```

**Confirme o nome real** do módulo e da função de classificação lendo
`tests/test_harness_authorization.py` antes de escrever o terceiro teste; se a
API for outra, use a que estiver lá. O que o teste precisa garantir é que
`sparkforge_judge` **não** mudou de classe.

- [ ] **Step 3: Declarar no schema**

Em `sparkforge/adapters/tools.py`, acrescentar ao `outputSchema` de
`sparkforge_judge` a chave `plan` (com as nove subchaves) e `evidence_standing`
dentro do item, e acrescentar à `description`:

```
Devolve tambem `plan`: ordem de aplicacao, restricoes de sequenciamento,
contradicoes e lacunas nomeadas, sobre o CONJUNTO de achados e nao a pagina.
Cada item traz `evidence_standing` com o lastro e os tres insumos que o
produziram. O `judge` CALCULA e NAO GRAVA -- o registro auditavel e
`sparkforge_arbitrate`.
```

- [ ] **Step 4: Rodar e atualizar o lock**

Run: `python -m pytest tests/test_adapters_tools.py -q`
Expected: PASS.

Run: `python scripts/check_surface_lock.py --update`
Anote o crescimento em bytes.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/adapters/tools.py docs/surface.lock.json tests/test_adapters_tools.py
git commit -m "feat(mcp): sparkforge_judge declara o plano no schema, e segue READ_ONLY"
```

---

## Task 6: medir o custo e publicar

**Files:**
- Modify: `docs/superpowers/specs/2026-09-08-plano-de-aplicacao-no-judge-design.md`
- Modify: `docs/superpowers/STATUS.md`
- Modify: `docs/claims.lock.json` (se o gate cobrar)

Você escolheu "sempre, e o custo vai medido". **Medir é entrega, não
observação.**

- [ ] **Step 1: Medir antes e depois**

```bash
python - <<'EOF'
import json, subprocess
from sparkforge.adapters._core import judge_findings
alvo = "fixtures/waste/folga_medida_sem_skew/input/facts.json"
r = judge_findings(facts_path=alvo, glue="5.0", spark="3.5.4")
depois = len(json.dumps(r, ensure_ascii=False))
sem = {k: v for k, v in r.items() if k != "plan"}
sem["items"] = [{k: v for k, v in i.items() if k != "evidence_standing"} for i in sem["items"]]
antes = len(json.dumps(sem, ensure_ascii=False))
print("antes", antes, "depois", depois, "delta", depois - antes,
      "pct", round((depois - antes) / antes * 100, 1))
EOF
```

Repita sobre **três** fixtures de tamanhos diferentes (uma com 1 finding, uma
com ~5, uma com ~20) — um número só sobre um case pequeno diria mais sobre o
envelope fixo que sobre o bloco, que é a armadilha que a regra 28 do
`CLAUDE.md` já documenta para `detail_level` (1,3% num corpus pequeno).

- [ ] **Step 2: Publicar com o comando ao lado**

Acrescentar seção ao spec e ao STATUS com os três números e o comando que os
produz. **Nenhuma afirmação de que o plano compensa o custo** — não há os dois
lados medidos, e a regra 30 vale aqui igual.

Se o crescimento for grande o bastante para mudar a conclusão do desenho,
**escreva isso e pare** — a decisão volta ao operador.

- [ ] **Step 3: Rodar os gates de documento**

Run: `python scripts/check_vnext_claims.py`
Expected: `0 divergencia(s)`. Se cair, remedie **relendo o número pela própria
prova**, nunca à mão, acrescentando nota sem reescrever as anteriores.

Run: `python scripts/check_status_numbers.py --strict`
Expected: `0 divergencia(s)`

- [ ] **Step 4: Commit**

```bash
git add docs/
git commit -m "docs: o custo em bytes do plano na resposta do judge, medido em tres cases"
```

---

## Task 7: lotes da suíte e fechamento

**Files:**
- Modify: `tests/test_suite_batches.py` (se preciso)

- [ ] **Step 1: Encaixar os arquivos novos**

Run: `python -m pytest tests/test_suite_batches.py -q`
Expected: PASS. Se falhar, acrescente `test_agentic_executor_digest.py` e
`test_adapters_judge_plan.py` à constante `LOTES`.

- [ ] **Step 2: Rodar os lotes afetados**

Rode o lote que contém os arquivos novos e o que contém os oito leitores da
resposta de `judge`, **um por vez**. A suíte inteira num processo não sobrevive
na workstation (o CI a roda inteira e passa — ver `.github/workflows/ci.yml`).

- [ ] **Step 3: Lint**

Run: `python -m ruff check sparkforge scripts tests`
Expected: limpo. **Não** rode `ruff format --check` — reprova 396 arquivos
intocados por drift de versão.

- [ ] **Step 4: Commit**

```bash
git add tests/test_suite_batches.py
git commit -m "test: os dois arquivos do plano encaixados nos lotes"
```

---

## Auto-revisão do plano contra o spec

| Seção do spec | Tarefa |
|---|---|
| §2 `judge` calcula e não grava | 2 (`persisted`, teste de disco), 4 (teste de disco), 5 (segue READ_ONLY) |
| §2 registro continua no `arbitrate` | 2 (`note`), 5 (descrição da tool) |
| §2 bloco sempre, custo medido | 4 (sem parâmetro opt-in), 6 (medição) |
| §3 `digest.py`, `run.py` usa | 2, 3 |
| §4 forma da resposta | 2, 4 |
| §4.1 `scope` e `persisted` | 2 (`scope` com contagem), 4 (ordem do conjunto sob paginação) |
| §4.2 `objections` vazio hoje | 2 (chave sempre presente, lista vazia) |
| §5 `evidence_standing` com os três insumos | 1, 4 |
| §5 campo na serialização, não no dataclass | 4 (anexa em `finding_dicts`) |
| §6 custo publicado | 6 |
| §7 gates | 4 (os oito), 5 (surface lock), 6 (lastro), 7 (lotes) |
| §7 goldens não mudam | confirmação antes da Tarefa 1, e Step 6 da Tarefa 4 |
| §8 testes | 1, 2, 3, 4 |
| §9 o que fica de fora | nenhuma tarefa faz `judge` gravar, mexe em `next_step` ou publica ganho |
