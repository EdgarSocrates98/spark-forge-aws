# SparkForge Fase 4b — gates fail-closed e assinatura: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o case deixa de avançar de fase com gate não satisfeito quando o operador pede rigor, e o relatório passa a carregar prova de que corresponde à evidência e ao catálogo que o produziram.

**Architecture:** o gate vive em `store.set_phase`, único ponto de passagem entre fases. O produtor de cada gate é declarado no `routing.yaml` — sem produtor declarado, o gate segue advisory mesmo sob rigor. A assinatura é hash de correspondência, sem chave e sem segredo.

**Tech Stack:** Python stdlib (`hashlib`), YAML declarativo, pytest.

**Spec:** [`../specs/2026-08-04-sparkforge-fase4b-gates-assinatura-design.md`](../specs/2026-08-04-sparkforge-fase4b-gates-assinatura-design.md) — §6 tem os dez critérios, §8 os dois desvios medidos antes de começar.

---

## Fatos do ambiente verificados antes de escrever este plano

```
store.py:23  PHASES  intake inventory facts diagnosis hypothesis experiment validation report
store.py:34  GATES   baseline_captured dominant_bottleneck_identified
                     functional_validation_defined flows_mapped        <- QUATRO
store.py:71  new_case  "gates": dict.fromkeys(GATES, False)
store.py:121 set_phase  valida contra PHASES, faz deepcopy, seta e devolve
store.py:129 set_gate   valida contra GATES

routing.yaml  blocked_by so em ROUTE-012 [baseline_captured]
                        e ROUTE-015 [functional_validation_defined]
resume.py:213 imprime "bloqueado por (advisory)"
cli.py:386-387 --gate / --gate-value       _core.py:1641 store.set_gate
_core.py:1626  case_update(repo, phase, gate, gate_value, skill, now, outcome)
templates/performance-report.md  54 linhas, secoes numeradas, sem bloco de assinatura
```

**A consequência que decide a Task 1:** as fases do case são as **oito** acima —
`remediation` **não existe**, e o exemplo do D-4 do spec usa esse nome. Onde o
gate morde é na entrada de `experiment` e de `validation`, e a Task 1 mede qual,
em vez de herdar o nome errado.

**A consequência que decide a Task 2:** `case update --gate X --gate-value true`
já permite virar qualquer gate. Sob rigor ele é **ignorado** (desvio D-4b-2 do
spec) — senão virar a flag seria override sem motivo e sem registro.

---

## Task 1: classificar os quatro gates, e medir onde cada um morde

Antes de qualquer código. O critério da §1 do spec — *gate só pode ser
fail-closed se tiver produtor declarado* — precisa ser aplicado aos **quatro**
nomes, e o spec só classificou dois.

**Files:** nenhum ainda. Esta task produz **medição e decisão**, escritas no plano.

- [ ] **Step 1: Para cada gate, responda com evidência**

Para `baseline_captured`, `dominant_bottleneck_identified`,
`functional_validation_defined` e `flows_mapped`:

1. Que fact, se presente, prova que o gate está satisfeito? Procure em
   `EMITTED_KINDS` de todos os extratores — não invente kind.
2. Que comando produz esse fact? Precisa existir hoje na CLI.
3. Se não houver fact que o prove, o gate **fica advisory**, e o motivo vai
   escrito.

Cole a tabela das quatro respostas.

- [ ] **Step 2: Meça em que transição o gate morde**

`PHASES` não tem `remediation`. Rode `python -c "from sparkforge.case.store import PHASES; print(PHASES)"` e decida, para cada gate com produtor, **antes de qual fase** ele é exigido. Justifique pela pergunta que a fase responde, não por ordem alfabética.

Se a resposta for "depende do gate", o mapeamento é dado e mora no `routing.yaml` junto do produtor — não em `if` no Python.

- [ ] **Step 3: Escreva a decisão no plano**

Tabela final: gate → fact produtor → comando → fase que ele guarda → advisory ou fail-closed. É o contrato que as Tasks 2 e 3 implementam.

- [ ] **Step 4: Commit**

---

## Task 2: o gate em `set_phase`

**Files:**
- Modify: `sparkforge/case/store.py`, `rules/catalog/routing.yaml`, `tests/test_case_store.py`

- [ ] **Step 1: O produtor no `routing.yaml`**

Bloco novo, no topo, ao lado das rotas — a decisão vira dado, como o roteamento de coordenador virou na Fase 4:

```yaml
gates:
  baseline_captured:
    satisfied_by: bench.run_delta
    produced_by: "sparkforge benchmark --before <facts_antes> --after <facts_depois> --out .sparkforge/facts_bench.json"
    guards_phase: <o que a Task 1 mediu>
  functional_validation_defined:
    # SEM satisfied_by: nenhum extrator emite fact que prove isto ate a Fase 4c.
    # Endurece-lo agora e o impasse que a secao 5.5 da Fase 0 recusou.
    advisory_reason: "sem produtor ate a Fase 4c"
```

Os quatro gates aparecem, inclusive os que ficam advisory — gate ausente do bloco é ambíguo entre "esqueceram" e "é advisory de propósito".

- [ ] **Step 2: O teste que falha**

```python
def test_gate_com_produtor_bloqueia_a_transicao_sob_rigor():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    with pytest.raises(store.CaseError) as exc:
        store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())
    assert "baseline_captured" in str(exc.value)
    assert "sparkforge benchmark" in str(exc.value)


def test_sem_rigor_a_transicao_passa_como_hoje():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    assert store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())["phase"] == PHASE_GUARDADA


def test_o_fact_produtor_satisfaz_o_gate():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    novo = store.set_phase(case, PHASE_GUARDADA, fact_kinds={"bench.run_delta"})
    assert novo["phase"] == PHASE_GUARDADA


def test_gate_sem_produtor_declarado_nunca_bloqueia():
    """O criterio da secao 1 do spec, travado: functional_validation_defined nao
    tem `satisfied_by`, entao nem sob rigor ele impede a transicao."""
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    novo = store.set_phase(case, PHASE_DO_GATE_SEM_PRODUTOR, fact_kinds=set())
    assert novo["phase"] == PHASE_DO_GATE_SEM_PRODUTOR


def test_o_booleano_manual_nao_destrava_sob_rigor():
    """Desvio D-4b-2: `case update --gate X --gate-value true` seria override sem
    motivo e sem registro."""
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    case = store.set_gate(case, "baseline_captured", True)
    with pytest.raises(store.CaseError):
        store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())
```

Substitua `PHASE_GUARDADA` e `PHASE_DO_GATE_SEM_PRODUTOR` pelo que a Task 1 mediu.

- [ ] **Step 3: Rode e veja falhar**

Run: `python -m pytest tests/test_case_store.py -k gate -v`
Expected: FAIL — `set_phase() got an unexpected keyword argument 'fact_kinds'`

- [ ] **Step 4: Implemente**

`set_phase(case, phase, fact_kinds=None)`. Parâmetro **opcional**: `set_phase` é chamado de dentro do `_core` e de testes, e a assinatura antiga precisa continuar valendo — sem `fact_kinds`, o comportamento é o de hoje.

A checagem só acontece quando `case.get("strict_gates")` é verdadeiro **e** o gate tem `satisfied_by` no `routing.yaml`. A mensagem nomeia a fase pedida, o gate, o fact que faltou e o comando de `produced_by` — o D-5 do spec, e o teste assere **conteúdo**, porque a Fase 4a mediu que mensagem inacionável passa no CI.

- [ ] **Step 5: Rode e commite**

---

## Task 3: rigor na abertura, e override com motivo

**Files:**
- Modify: `sparkforge/case/store.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `sparkforge/case/resume.py`, `tests/`

- [ ] **Step 1: `strict_gates` no case**

`new_case` ganha o parâmetro, default `False`, e a chave entra no dicionário. Case gravado por versão anterior não tem a chave — `case.get("strict_gates")` responde `None`, que é falsy, e o comportamento antigo se preserva sem migração. **Confira se `SCHEMA_VERSION` precisa subir**: se houver teste que valide o conjunto exato de chaves do case, ele decide, e a resposta vai no relatório.

- [ ] **Step 2: `case open --strict-gates`**

CLI, `_core.case_open` e a tool MCP, na mesma passada — deixar o MCP para trás recria a assimetria que a Fase 5b corrigiu na flag `--emr`.

- [ ] **Step 3: O override, e o teste primeiro**

```python
def test_override_sem_motivo_e_recusado():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    with pytest.raises(store.CaseError) as exc:
        store.override_gate(case, "baseline_captured", reason="")
    assert "motivo" in str(exc.value).lower()


def test_override_com_motivo_fica_gravado_e_destrava():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    case = store.override_gate(case, "baseline_captured", reason="job descontinuado")
    registro = case["gate_overrides"][0]
    assert registro["gate"] == "baseline_captured"
    assert registro["reason"] == "job descontinuado"
    assert store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())["phase"] == PHASE_GUARDADA
```

`gate_overrides` é lista, não dicionário: dois overrides do mesmo gate em momentos diferentes são dois fatos, e sobrescrever apagaria o primeiro motivo.

- [ ] **Step 4: `case update --override-gate --reason`**

Nos três adaptadores. `--override-gate` sem `--reason` sai com `exit_code=2` e mensagem que diz o que falta.

- [ ] **Step 5: `resume` mostra o override**

`resume.py:213` hoje imprime `bloqueado por (advisory)`. Quando o case tem `strict_gates`, a palavra `advisory` está **errada** — e quando há override, a retomada precisa mostrar gate, motivo e quando. Quem retoma numa outra máquina tem que saber que alguém passou por cima, sem abrir o YAML.

- [ ] **Step 6: Rode a suíte inteira e commite**

Nenhum case existente pode quebrar: é o critério 5 do spec.

---

## Task 4: a assinatura de correspondência

**Files:**
- Create: `sparkforge/findings/signature.py`, `tests/test_findings_signature.py`
- Modify: `sparkforge/adapters/{_core,cli,tools}.py`, `templates/performance-report.md`

- [ ] **Step 1: O teste que falha**

```python
from sparkforge.findings.signature import compute_signature, normalize_body


def test_reformatar_o_corpo_nao_muda_a_assinatura():
    a = compute_signature(body="## Titulo\n\ntexto\n", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    b = compute_signature(body="## Titulo\n\n\ntexto  \n\n", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    assert a == b


def test_editar_o_conteudo_muda_a_assinatura():
    a = compute_signature(body="ganho de 40%", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    b = compute_signature(body="ganho de 60%", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    assert a != b


def test_a_ordem_da_evidencia_nao_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=["f_aaa111", "f_bbb222"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=["f_bbb222", "f_aaa111"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    assert a == b


def test_trocar_a_evidencia_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=["f_aaa111"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=["f_ccc333"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    assert a != b


def test_catalogo_diferente_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=[], rule_ids=[], catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=[], rule_ids=[], catalog_version=2, schema_version=1)
    assert a != b
```

- [ ] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_findings_signature.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implemente**

```python
"""Assinatura de CORRESPONDENCIA de um relatorio.

Prova que o texto foi derivado daquela evidencia com aquele catalogo. NAO prova
autoria: nao ha chave, nao ha segredo, e qualquer um com os mesmos facts produz
a mesma assinatura. O bloco escrito no relatorio diz isso, porque bloco que
sugere autoridade mente por omissao.

O corpo entra no hash de proposito (D-7 do spec): sem ele alguem reescreve o
texto inteiro mantendo a assinatura valida, e ela garantiria menos do que o
leitor supoe.
"""
from __future__ import annotations

import hashlib
import json
import re

SIGNATURE_VERSION = 1

_WS = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n{3,}")


def normalize_body(body: str) -> str:
    """Absorve reformatacao, e SO ela.

    Espaco horizontal repetido, espaco no fim da linha, CRLF, e mais de uma
    linha em branco seguida. Nao absorve pontuacao, ordem, numero nem palavra --
    o que ela absorve esta escrito aqui e tem teste dos dois lados.
    """
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(_WS.sub(" ", line).rstrip() for line in text.split("\n"))
    return _BLANKS.sub("\n\n", text).strip()


def compute_signature(
    body: str,
    fact_ids: list[str],
    rule_ids: list[str],
    catalog_version: int,
    schema_version: int,
) -> str:
    payload = {
        "signature_version": SIGNATURE_VERSION,
        "body": normalize_body(body),
        "fact_ids": sorted(set(fact_ids)),
        "rule_ids": sorted(set(rule_ids)),
        "catalog_version": catalog_version,
        "schema_version": schema_version,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sig_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

`SIGNATURE_VERSION` entra no hash: mudar a normalização no futuro sem mudar a versão faria assinaturas antigas parecerem inválidas sem que nada tivesse sido adulterado.

- [ ] **Step 4: Rode e commite**

---

## Task 5: `report sign` e `report verify`

**Files:**
- Modify: `sparkforge/adapters/{_core,cli,tools}.py`, `templates/performance-report.md`, `tests/`

- [ ] **Step 1: O bloco no relatório**

No fim, delimitado, e **fora** do que a própria assinatura cobre — ele não pode entrar no hash que ele mesmo carrega. O corpo assinado é tudo que vem antes do delimitador.

```markdown
<!-- sparkforge:signature -->
- assinatura: sig_a1b2c3d4e5f60718
- evidência: 12 facts, 4 regras
- catálogo: catalog_version 1, schema_version 1
- verifique com: `sparkforge report verify --report <este arquivo> --facts <facts.json>`

Esta assinatura prova **correspondência**, não autoria: que este texto foi
derivado desta evidência com este catálogo. Ela não diz quem o emitiu, e qualquer
pessoa com os mesmos facts produz a mesma assinatura.
<!-- /sparkforge:signature -->
```

- [ ] **Step 2: `report verify` diz o que divergiu**

Não "inválido". Recompute as três partes separadamente e diga qual não bate:
evidência, catálogo ou corpo. É o critério 8 do spec, e o teste cobre os três
casos, mais o de bloco ausente e o de bloco malformado.

- [ ] **Step 3: Os dois verbos nos três adaptadores**

`report sign --report <md> --facts <json>` e `report verify --report <md> --facts <json>`, na CLI, no `_core` e como tool MCP. Mais `parity.yaml` e `manifest.json`, e as **três** listas manuais de `tests/test_adapters_tools.py` que a Fase 5c mediu.

- [ ] **Step 4: Rode e commite**

---

## Task 6: fechamento

**Files:**
- Modify: `docs/superpowers/STATUS.md`, `README.md`, `AGENTS.md`, `AGENT_PROTOCOL.md`

- [ ] **Step 1: Meça**

```bash
python -m pytest -q 2>&1 | tail -2
python -c "from sparkforge.adapters.tools import TOOLS; print('tools', len(TOOLS))"
ruff check .
```

- [ ] **Step 2: `AGENT_PROTOCOL.md`**

A regra que fala de gates precisa dizer que sob `--strict-gates` o booleano manual não destrava, e que override exige motivo. É o documento que o executor lê antes de agir — a Fase 4a mediu que a quebra de contrato do `benchmark_ref` não tinha chegado nele.

- [ ] **Step 3: `STATUS.md`, `README.md`, `AGENTS.md`**

Números medidos. Seção "Fase 4b" no formato das anteriores: o defeito de partida (a razão da Fase 0 deixando de valer para gate com produtor), o que entrou, e o que **não** entrou — a validação funcional, que é a 4c. Na §16, marcar dois dos três itens de rigor como fechados.

- [ ] **Step 4: Suíte verde, ruff limpo, commit**
