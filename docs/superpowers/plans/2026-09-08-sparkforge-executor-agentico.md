# Executor agêntico determinístico — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer um case real produzir `Claim`/`Evidence`/`Contradiction`/`Unknown`/`Decision` no blackboard, decidindo conflito, lastro, medida faltante e ordem — sem chamar provider nenhum.

**Architecture:** Verbo novo que roda depois de `judge`. Cada regra executável ganha um bloco `action:` legível por máquina; o executor cruza as ações dos findings entre si e contra os facts, arbitra com as primitivas que já existem em `sparkforge/agentic/`, e grava. O que não fecha determinísticamente vira `DebatePlan` emitido e uma recusa nomeada.

**Tech Stack:** Python 3.11+, dataclasses frozen, YAML (catálogo e conhecimento), JSONL (blackboard), argparse (CLI), pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-sparkforge-executor-agentico-design.md`

---

## Desvios do spec, declarados antes de começar

**D-1 — as fixtures não viram domínio novo em `fixtures/`.** A §8.1 do spec pede
`fixtures/arbitration/`. Medido: toda fixture do corpus tem a forma
`input/facts.json → expected/facts.json + expected/findings.json`, e o executor
não produz nem fact nem finding — produz blackboard. Um domínio novo com
`expected/blackboard.json` seria a segunda forma divergente do corpus (hoje só
`glue_job_run` diverge). Os testes do executor moram em
`tests/test_agentic_executor_*.py` e **consomem as fixtures existentes**
(`fixtures/waste/`, `fixtures/timeout/`) como entrada — corpus já ancorado, sem
forma nova.

**D-2 — são 112 regras executáveis, não 111.** `_executable_rules()` devolve 112
hoje; o STATUS publica 111 e está defasado em um desde `SF-BRIDGE-001`. O plano
usa 112, e a Tarefa 22 remedia o STATUS.

**D-4 — decidido na Tarefa 1, e vale para os lotes 4-10.** A leitura das 112
produziu **76 `kind` em 20 `axis`**, acima da faixa de 25-50 que este plano
estimava. A faixa era estimativa; o critério publicado — dois `kind` diferem
quando as ações tocam coisas diferentes ou vão em direções diferentes — foi
aplicado contra as 112 reais, e a fusão seguinte juntaria alavancas que
conflitam entre si (`capacity.reduce_workers` com
`capacity.change_worker_type`), que é exatamente o cruzamento que o executor
existe para fazer. Fica em 76.

**D-5 — `action:` é UM bloco, e descreve a ação DOMINANTE.** A leitura achou
regras cujo `proposed_change` oferece alternativas mutuamente excludentes:
`SF-LF-001` e `SF-LF-002` (o texto delas diz que não existe meio-termo),
`SF-ATH-003` (três alternativas em eixos diferentes) e `SF-UI-004` (a
classificação da causa decide entre duas ações opostas). Elas declaram a
dominante, e a alternativa fica **fora desta entrega**, como limite declarado.
Razão: contradição e ordem operam sobre a ação que a regra propõe aplicar;
alternativa dentro de uma regra é escolha do operador, e a arbitragem deste
executor escolhe entre CLAIMS, nunca dentro de uma.

**D-6 — não existe `direction: hold`.** `SF-EMRS-004` e `SF-EMRK-003` admitem
por escrito que **não** mudar pode ser a decisão certa. Isso é `investigate`: a
regra pede que a política seja declarada antes de mexer, e `investigate` já
significa medir ou decidir antes de mudar. Criar `hold` faria o executor
ordenar uma não-ação, e ordenar o nada não é ordem. `SF-UI-004`,
`SF-BENCH-001` e `SF-BENCH-004` também são `investigate` — a ação delas é
medida ou escopo de afirmação, não mudança no job.

**D-7 — `moves` tambem precisa de vocabulario fechado, e o plano nao previa.**
Os exemplos deste plano escrevem `cost.dpu_seconds`, `runtime.wall_clock`,
`scan.bytes_read` sem nada que os feche. Sete lotes escrevendo eixo por conta
propria produziriam `runtime.wall_clock` num e `wall_clock` noutro, e a
restricao da §5.4 — duas acoes que compartilham eixo nao entram no mesmo run —
**nunca dispararia**, sem que nada acusasse. E o mesmo modo de falha que o
literal repetido de `routing.yaml` teve no gate de area.

`rules/catalog/action_kinds.yaml` ganha uma chave `axes:` no mesmo molde de
`kinds:`, e o gate de `tests/test_rules_action_field.py` cobra as duas direcoes:
todo eixo citado em `moves` esta no vocabulario, e todo eixo do vocabulario e
citado por alguma regra. A Tarefa 4 abre a chave; os lotes seguintes acrescentam
o que faltar.

**D-8 — a Tarefa 3 deixou 96 goldens vermelhos, e a verificacao dela nao olhou.**
Medido em 2026-09-08, depois do lote A: o corpus tem **125** goldens com
findings; **29** carregam a chave `action` (os que o lote A regenerou) e **96**
nao. Eles sao anteriores a Tarefa 3, que pos `action` em `Finding.to_dict()`, e
falham com ou sem lote nenhum.

A causa nao foi o implementador: a verificacao que este plano mandou rodar na
Tarefa 3 nomeava quatro arquivos de teste, e **nenhum deles era
`test_fixtures_golden_*`**. E o modo de falha que o proprio STATUS deste
repositorio ja registra por escrito -- fase que fecha verde nao prova que esta
certa, prova que a suite olhou para onde alguem mandou olhar.

**Tarefa 3b, inserida entre o lote A e o lote B:** saneamento unico dos 96. Ela
acrescenta a chave `action` que `to_dict()` hoje produz, e **nada mais** -- o
criterio de aceite e que o diff de cada golden toque **so** essa chave. Golden
que mudar qualquer outra coisa na regeneracao e achado, e para a tarefa.

Depois dela, cada lote regenera apenas os goldens das areas que ele preencheu.

---

## Estrutura de arquivos

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `rules/catalog/action_kinds.yaml` | vocabulário fechado de `action.kind` |
| `knowledge/source_authority.yaml` | host da URL → tier T1/T2/T4 |
| `sparkforge/agentic/executor/__init__.py` | reexporta `run_executor` |
| `sparkforge/agentic/executor/authority.py` | tier por host, vigência e escopo de versão |
| `sparkforge/agentic/executor/claims.py` | findings → `Claim` + `Evidence` |
| `sparkforge/agentic/executor/conflict.py` | contradição direta e condicional |
| `sparkforge/agentic/executor/ordering.py` | ordem topológica e restrições derivadas |
| `sparkforge/agentic/executor/unknowns.py` | `unresolved` e lastro reprovado → `Unknown` → `Experiment` |
| `sparkforge/agentic/executor/plan.py` | `DebatePlan` e a recusa nomeada |
| `sparkforge/agentic/executor/run.py` | orquestra, decide e grava |
| `tests/test_rules_action_field.py` | gate do campo `action` |
| `tests/test_agentic_executor_authority.py` | testes de tier e escopo |
| `tests/test_agentic_executor_claims.py` | testes de claims e evidence |
| `tests/test_agentic_executor_conflict.py` | testes de contradição |
| `tests/test_agentic_executor_ordering.py` | testes de ordem |
| `tests/test_agentic_executor_run.py` | ponta a ponta sobre fixture existente |

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/rules/loader.py` | validação do bloco `action` |
| `sparkforge/rules/engine.py:202` | propaga `action` para o `Finding` |
| `sparkforge/findings/models.py:69` | campo `action` no `Finding` |
| `sparkforge/agentic/models.py:181` | campo `measurement_ref` na `Evidence` |
| `sparkforge/adapters/cli.py` | verbo `arbitrate` |
| `sparkforge/adapters/tools.py` | tool `sparkforge_arbitrate` |
| os 26 arquivos de catálogo com regra executável | bloco `action:` |

---

## Fase 1 — vocabulário e schema

### Task 1: Levantar o vocabulário candidato lendo os 112 `proposed_change`

**Files:**
- Create: `scripts/derive_action_kinds.py`
- Create: `rules/catalog/action_kinds.yaml`

- [ ] **Step 1: Escrever o script de leitura**

O script **não decide** o vocabulário. Ele imprime, por regra executável, a
área, o id, o título e o `proposed_change`, para que a lista seja escrita à mão
a partir da leitura. Automatizar o agrupamento produziria `kind` derivado de
palavra, não de eixo.

```python
"""Imprime area, id, titulo e proposed_change de cada regra executavel.

Ferramenta de LEITURA. O vocabulario de `action.kind` e escrito a mao a partir
desta saida -- agrupar por palavra produziria kind derivado de texto, e o eixo
de uma acao nao esta no verbo que a descreve.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sparkforge.rules.loader import load_catalog  # noqa: E402


def main() -> int:
    rules = [r for r in load_catalog() if r.get("executable", True)]
    for rule in sorted(rules, key=lambda r: r["id"]):
        print(f"## {rule['id']} -- {rule['title']}")
        for line in rule.get("proposed_change") or []:
            print(f"  - {line}")
        print()
    print(f"total: {len(rules)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Rodar e ler a saída inteira**

Run: `python scripts/derive_action_kinds.py > /tmp/proposed.txt; wc -l /tmp/proposed.txt`
Expected: `total: 112` no stderr, e o arquivo com as 112 regras.

- [ ] **Step 3: Escrever o vocabulário à mão**

Cria `rules/catalog/action_kinds.yaml` com a forma abaixo. Os `kind` saem da
leitura do passo 2 — os exemplos aqui são os três que a leitura de
`waste.yaml` e `timeout.yaml` já garante, e o resto entra conforme lido.

```yaml
# Vocabulario fechado de `action.kind`. Derivado da leitura dos 112
# `proposed_change`, nao inventado: ver `scripts/derive_action_kinds.py`.
#
# `direction: investigate` existe para a regra que propoe MEDIDA e nao mudanca.
# Forcar SF-WASTE-001 a declarar `decrease` inventaria uma recomendacao que o
# proprio `proposed_change` dela recusa por escrito.
schema_version: 1
directions:
  - increase
  - decrease
  - replace
  - remove
  - add
  - investigate
kinds:
  capacity.investigate_sizing:
    axis: capacidade
    description: Rodar o verbo de capacidade contra o SLA declarado, sem propor numero.
  capacity.reduce_workers:
    axis: capacidade
    description: Reduzir contagem de worker para capacidade ja observada.
  timeout.increase_limit:
    axis: timeout
    description: Aumentar limite de timeout de rede, broadcast ou heartbeat.
```

- [ ] **Step 4: Commit**

```bash
git add scripts/derive_action_kinds.py rules/catalog/action_kinds.yaml
git commit -m "feat(rules): vocabulario de action.kind, derivado da leitura das 112 executaveis"
```

---

### Task 2: Validar `action` no loader, com allowlist que encolhe

**Files:**
- Modify: `sparkforge/rules/loader.py`
- Test: `tests/test_rules_action_field.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Gate do campo `action`.

Duas direcoes, e as duas importam: toda regra executavel declara `action`, e
todo `kind` do vocabulario tem ao menos uma regra que o usa. Sem a segunda, o
vocabulario incha com entrada morta e ninguem percebe.

`PENDENTES` encolhe a cada lote da Fase 2 e chega a conjunto vazio na Tarefa 11.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.rules.loader import catalog_dir, load_catalog

# Arquivos ainda sem `action`. Encolhe a cada lote; vazio ao fim da Fase 2.
PENDENTES = {
    "pyspark.yaml",
    "emr-infra.yaml",
    "controlm.yaml",
    "emr-serverless.yaml",
    "glue-infra.yaml",
    "graph.yaml",
    "spark-ui.yaml",
    "athena.yaml",
    "env.yaml",
    "funcval.yaml",
    "iceberg.yaml",
    "parquet.yaml",
    "benchmark.yaml",
    "data-quality.yaml",
    "emr-eks.yaml",
    "glue-migration.yaml",
    "spark-plan.yaml",
    "spark4.yaml",
    "glue-kms.yaml",
    "lakeformation.yaml",
    "timeout.yaml",
    "waste.yaml",
    "bridge.yaml",
    "callgraph.yaml",
    "glue-cross-account.yaml",
    "glue-network.yaml",
}


def _vocabulary() -> dict:
    path = catalog_dir() / "action_kinds.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _rule_files() -> dict[str, str]:
    """rule_id -> nome do arquivo que o declara."""
    origem: dict[str, str] = {}
    for path in sorted(Path(catalog_dir()).glob("*.yaml")):
        if path.name in {"routing.yaml", "action_kinds.yaml"}:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rule in data.get("rules") or []:
            origem[rule["id"]] = path.name
    return origem


class TestActionField:
    def test_toda_executavel_declara_action(self):
        origem = _rule_files()
        faltando = [
            r["id"]
            for r in load_catalog()
            if r.get("executable", True)
            and origem.get(r["id"]) not in PENDENTES
            and "action" not in r
        ]
        assert faltando == [], f"regras executaveis sem `action`: {faltando}"

    def test_kind_esta_no_vocabulario(self):
        vocab = set(_vocabulary()["kinds"])
        fora = [
            (r["id"], r["action"]["kind"])
            for r in load_catalog()
            if "action" in r and r["action"]["kind"] not in vocab
        ]
        assert fora == [], f"kind fora do vocabulario: {fora}"

    def test_todo_kind_do_vocabulario_tem_regra(self):
        if PENDENTES:
            return  # so vale com o catalogo inteiro preenchido
        vocab = set(_vocabulary()["kinds"])
        usados = {r["action"]["kind"] for r in load_catalog() if "action" in r}
        mortos = sorted(vocab - usados)
        assert mortos == [], f"kind no vocabulario sem regra que o use: {mortos}"
```

- [ ] **Step 2: Rodar o teste**

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS nos três (com `PENDENTES` cheio, o primeiro e o terceiro não cobram nada ainda; o segundo já vale).

- [ ] **Step 3: Validar a forma de `action` no loader**

Em `sparkforge/rules/loader.py`, acrescentar a função e chamá-la dentro do laço
que já valida cada regra (junto de `_validate_executability`):

```python
_ACTION_DIRECTIONS = (
    "increase",
    "decrease",
    "replace",
    "remove",
    "add",
    "investigate",
)
_ACTION_KEYS = {"kind", "target", "direction", "requires_absent", "moves", "depends_on"}


def _validate_action(rule_id: str, rule: dict[str, Any]) -> None:
    """Valida a FORMA do bloco `action`. O vocabulario de `kind` e conferido
    por `tests/test_rules_action_field.py`, contra `action_kinds.yaml` --
    aqui carregar o vocabulario a cada regra custaria uma leitura por regra."""
    action = rule.get("action")
    if action is None:
        return
    if not isinstance(action, dict):
        raise CatalogError(f"{rule_id}: `action` precisa ser um mapa")
    desconhecidas = sorted(set(action) - _ACTION_KEYS)
    if desconhecidas:
        raise CatalogError(f"{rule_id}: chaves desconhecidas em `action`: {desconhecidas}")
    for obrigatoria in ("kind", "target", "direction"):
        if not str(action.get(obrigatoria) or "").strip():
            raise CatalogError(f"{rule_id}: `action.{obrigatoria}` ausente ou vazio")
    if action["direction"] not in _ACTION_DIRECTIONS:
        raise CatalogError(
            f"{rule_id}: `action.direction` {action['direction']!r} invalido "
            f"(esperado: {', '.join(_ACTION_DIRECTIONS)})"
        )
    for lista in ("requires_absent", "moves", "depends_on"):
        valor = action.get(lista, [])
        if not isinstance(valor, list):
            raise CatalogError(f"{rule_id}: `action.{lista}` precisa ser lista")
    if not rule.get("executable", True) and action:
        raise CatalogError(
            f"{rule_id}: regra nao executavel nao pode declarar `action` -- "
            "ela nao produz finding, e acao sem finding e afirmacao sobre nada"
        )
```

- [ ] **Step 4: Escrever o teste da validação**

Acrescentar a `tests/test_rules_action_field.py`:

```python
import pytest

from sparkforge.rules.loader import CatalogError, _validate_action


class TestActionShape:
    def test_direction_invalida_recusa(self):
        with pytest.raises(CatalogError, match="direction"):
            _validate_action(
                "SF-X-001",
                {"action": {"kind": "k", "target": "t", "direction": "aumentar"}},
            )

    def test_chave_desconhecida_recusa(self):
        with pytest.raises(CatalogError, match="desconhecidas"):
            _validate_action(
                "SF-X-001",
                {
                    "action": {
                        "kind": "k",
                        "target": "t",
                        "direction": "increase",
                        "expected_gain": "-31%",
                    }
                },
            )

    def test_nao_executavel_com_action_recusa(self):
        with pytest.raises(CatalogError, match="nao executavel"):
            _validate_action(
                "SF-ARCH-001",
                {
                    "executable": False,
                    "action": {"kind": "k", "target": "t", "direction": "increase"},
                },
            )

    def test_ausencia_de_action_passa(self):
        _validate_action("SF-X-001", {})
```

`expected_gain` no segundo teste não é decorativo: é exatamente o campo que a
regra 13 proíbe, e o gate de chave desconhecida é o que impede que ele entre
pela porta dos fundos.

- [ ] **Step 5: Rodar**

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS nos sete.

- [ ] **Step 6: Commit**

```bash
git add sparkforge/rules/loader.py tests/test_rules_action_field.py
git commit -m "feat(rules): validacao de forma do bloco action, e o gate que recusa expected_gain"
```

---

### Task 3: Propagar `action` para o `Finding`

**Files:**
- Modify: `sparkforge/findings/models.py:69`
- Modify: `sparkforge/rules/engine.py:202`
- Test: `tests/test_rules_action_field.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_rules_action_field.py`:

```python
from sparkforge.findings.models import Finding


class TestFindingCarregaAction:
    def test_finding_tem_campo_action(self):
        f = Finding(
            rule_id="SF-WASTE-001",
            title="t",
            severity="P2",
            confidence="medium",
            status="confirmed",
            subject={"job": "x"},
            evidence=["f_abc123"],
            action={"kind": "capacity.investigate_sizing", "target": "glue.number_of_workers", "direction": "investigate"},
        )
        assert f.to_dict()["action"]["direction"] == "investigate"

    def test_action_ausente_e_dict_vazio(self):
        f = Finding(
            rule_id="SF-X-001",
            title="t",
            severity="P2",
            confidence="medium",
            status="confirmed",
            subject={},
            evidence=["f_abc123"],
        )
        assert f.to_dict()["action"] == {}
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_rules_action_field.py::TestFindingCarregaAction -v`
Expected: FAIL com `unexpected keyword argument 'action'`.

- [ ] **Step 3: Acrescentar o campo**

Em `sparkforge/findings/models.py`, dentro de `class Finding`, depois de
`sources`:

```python
    action: dict[str, Any] = field(default_factory=dict)
```

E em `to_dict`, depois de `"sources"`:

```python
            "action": dict(self.action),
```

Em `sparkforge/rules/engine.py`, na linha 202, ao lado de `proposed_change`:

```python
        action=dict(rule.get("action") or {}),
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS nos nove.

- [ ] **Step 5: Rodar o lote de findings inteiro, para provar que o campo é aditivo**

Run: `python -m pytest tests/test_findings_models.py tests/test_rules_engine.py -q`
Expected: PASS, zero falha. Se algum golden compara `to_dict()` inteiro, ele
precisa do `"action": {}` — acrescentar ao golden, não remover o campo.

- [ ] **Step 6: Commit**

```bash
git add sparkforge/findings/models.py sparkforge/rules/engine.py tests/test_rules_action_field.py
git commit -m "feat(findings): Finding carrega o action da regra que o produziu"
```

---

## Fase 2 — preencher `action` nas 112

Sete lotes, agrupados por eixo. Cada lote segue os mesmos cinco passos; o que
muda é o conjunto de arquivos e o texto de cada `action`. **Regra que vale para
todos:** o `action` tem que descrever o que o `proposed_change` daquela regra já
diz. Se o `proposed_change` manda medir, `direction` é `investigate` — nunca
`decrease`.

### Task 4: Lote A — capacidade e infraestrutura (27 regras)

**Files:**
- Modify: `rules/catalog/glue-infra.yaml` (6), `rules/catalog/emr-infra.yaml` (9), `rules/catalog/emr-serverless.yaml` (6), `rules/catalog/emr-eks.yaml` (4), `rules/catalog/waste.yaml` (2)
- Modify: `tests/test_rules_action_field.py` (`PENDENTES`)

- [ ] **Step 1: Ler o `proposed_change` das 27**

Run: `python scripts/derive_action_kinds.py | grep -A6 -E "^## SF-(GLUE|EMR|EMRS|EMRK|WASTE)-"`

- [ ] **Step 2: Escrever o bloco `action` em cada regra**

Exemplo completo, em `rules/catalog/waste.yaml`, dentro de `SF-WASTE-001`,
depois de `proposed_change`:

```yaml
    action:
      kind: capacity.investigate_sizing
      target: glue.number_of_workers
      direction: investigate
      requires_absent:
        - glue.utilization.skew_high
      moves:
        - cost.dpu_seconds
      depends_on: []
```

`direction: investigate` e não `decrease`: o `proposed_change` desta regra manda
rodar `sparkforge capacity`, e diz por escrito que reduzir sem capacidade
observada é experimento e não escolha.

- [ ] **Step 3: Acrescentar ao vocabulário o que faltar**

Todo `kind` novo entra em `rules/catalog/action_kinds.yaml` com `axis` e
`description`, na mesma forma da Tarefa 1.

- [ ] **Step 4: Encolher a allowlist e rodar**

Remover de `PENDENTES` em `tests/test_rules_action_field.py`:
`glue-infra.yaml`, `emr-infra.yaml`, `emr-serverless.yaml`, `emr-eks.yaml`, `waste.yaml`.

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS. Se `test_toda_executavel_declara_action` falhar, ele nomeia os ids que faltam.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/ tests/test_rules_action_field.py
git commit -m "feat(rules): action nas 27 regras de capacidade e infraestrutura"
```

---

### Task 5: Lote B — execução Spark (16 regras)

**Files:**
- Modify: `rules/catalog/spark-ui.yaml` (6), `rules/catalog/spark-plan.yaml` (4), `rules/catalog/timeout.yaml` (2), `rules/catalog/benchmark.yaml` (4)
- Modify: `tests/test_rules_action_field.py` (`PENDENTES`)

- [ ] **Step 1: Ler o `proposed_change` das 16**

Run: `python scripts/derive_action_kinds.py | grep -A6 -E "^## SF-(UI|PLAN|TIMEOUT|BENCH)-"`

- [ ] **Step 2: Escrever o bloco `action` em cada regra**

**Este passo estava errado no plano original, e a correção é o achado.** Ele
mandava dar a `SF-TIMEOUT-001` a ação `timeout.increase_limit` com
`requires_absent: [spark.stage.skew, spark.stage.spill, ...]`.

Medido em `rules/catalog/timeout.yaml`: `SF-TIMEOUT-001` **não propõe aumentar
limite nenhum**. O título dela é *"Timeout com sintoma medido ao lado — aumentar
o limite mascara a causa"*, o `when` dispara **só** com skew, spill, GC ou
executor perdido acima do limiar, e o `proposed_change` manda ler
`attrs.category`, investigar o sintoma, e **só depois** avaliar o limite. A
guarda que o plano queria mover para `requires_absent` já está no `when`.

Ela é `direction: investigate`, com `kind` do eixo de timeout que descreva
*investigar o sintoma medido ao lado* — não `increase`.

`SF-TIMEOUT-002` julga a relação entre duas propriedades
(`heartbeatInterval >= network.timeout`, que é errado sempre) e é a que tem
ação de mudança de verdade neste par.

Vale para o lote inteiro: **o `proposed_change` manda, e o plano não.** Onde
este documento e a regra discordarem, a regra vence e o desvio vai no relatório.

Run para conferir: `python -c "from sparkforge.facts.event_log import EMITTED_KINDS; print(sorted(EMITTED_KINDS))"`

- [ ] **Step 3: Acrescentar ao vocabulário o que faltar**

- [ ] **Step 4: Encolher a allowlist e rodar**

Remover de `PENDENTES`: `spark-ui.yaml`, `spark-plan.yaml`, `timeout.yaml`, `benchmark.yaml`.

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/ tests/test_rules_action_field.py
git commit -m "feat(rules): action nas 16 regras de execucao Spark, com o requires_absent de timeout"
```

---

### Task 6: Lote C — código (20 regras)

**Files:**
- Modify: `rules/catalog/pyspark.yaml` (12), `rules/catalog/graph.yaml` (6), `rules/catalog/callgraph.yaml` (1), `rules/catalog/bridge.yaml` (1)
- Modify: `tests/test_rules_action_field.py` (`PENDENTES`)

- [ ] **Step 1: Ler o `proposed_change` das 20**

Run: `python scripts/derive_action_kinds.py | grep -A6 -E "^## SF-(PY|GRAPH|CG|BRIDGE)-"`

- [ ] **Step 2: Escrever o bloco `action` em cada regra**

Exemplo, em `rules/catalog/pyspark.yaml`, numa regra que propõe trocar UDF
Python por função nativa:

```yaml
    action:
      kind: code.replace_python_udf
      target: pyspark.udf
      direction: replace
      requires_absent: []
      moves:
        - runtime.wall_clock
        - cpu.python_worker
      depends_on: []
```

- [ ] **Step 3: Acrescentar ao vocabulário o que faltar**

- [ ] **Step 4: Encolher a allowlist e rodar**

Remover de `PENDENTES`: `pyspark.yaml`, `graph.yaml`, `callgraph.yaml`, `bridge.yaml`.

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/ tests/test_rules_action_field.py
git commit -m "feat(rules): action nas 20 regras de codigo"
```

---

### Task 7: Lote D — armazenamento (15 regras)

**Files:**
- Modify: `rules/catalog/iceberg.yaml` (5), `rules/catalog/parquet.yaml` (5), `rules/catalog/athena.yaml` (5)
- Modify: `tests/test_rules_action_field.py` (`PENDENTES`)

- [ ] **Step 1: Ler o `proposed_change` das 15**

Run: `python scripts/derive_action_kinds.py | grep -A6 -E "^## SF-(ICE|PQ|ATH)-"`

- [ ] **Step 2: Escrever o bloco `action` em cada regra**

Atenção ao risco desta área: manutenção de Iceberg é destrutiva, e a regra 10 do
`CLAUDE.md` proíbe executá-la sem confirmação de escopo. O `action` **descreve** a
mudança; ele não a autoriza. Exemplo:

```yaml
    action:
      kind: storage.compact_data_files
      target: iceberg.table.data_files
      direction: replace
      requires_absent: []
      moves:
        - scan.bytes_read
        - metadata.planning_time
      depends_on: []
```

- [ ] **Step 3: Acrescentar ao vocabulário o que faltar**

- [ ] **Step 4: Encolher a allowlist e rodar**

Remover de `PENDENTES`: `iceberg.yaml`, `parquet.yaml`, `athena.yaml`.

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/ tests/test_rules_action_field.py
git commit -m "feat(rules): action nas 15 regras de armazenamento"
```

---

### Task 8: Lote E — dados e validação (9 regras)

**Files:**
- Modify: `rules/catalog/data-quality.yaml` (4), `rules/catalog/funcval.yaml` (5)
- Modify: `tests/test_rules_action_field.py` (`PENDENTES`)

- [ ] **Step 1: Ler o `proposed_change` das 9**

Run: `python scripts/derive_action_kinds.py | grep -A6 -E "^## SF-(DQ|FVAL)-"`

- [ ] **Step 2: Escrever o bloco `action` em cada regra**

```yaml
    action:
      kind: validation.declare_business_key
      target: funcval.business_key
      direction: add
      requires_absent: []
      moves: []
      depends_on: []
```

`moves: []` aqui é declaração, não esquecimento: declarar a chave de negócio não
move eixo de performance nenhum — ela torna a comparação possível.

- [ ] **Step 3: Acrescentar ao vocabulário o que faltar**

- [ ] **Step 4: Encolher a allowlist e rodar**

Remover de `PENDENTES`: `data-quality.yaml`, `funcval.yaml`.

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/ tests/test_rules_action_field.py
git commit -m "feat(rules): action nas 9 regras de dados e validacao"
```

---

### Task 9: Lote F — segurança e ambiente (11 regras)

**Files:**
- Modify: `rules/catalog/env.yaml` (5), `rules/catalog/glue-kms.yaml` (2), `rules/catalog/lakeformation.yaml` (2), `rules/catalog/glue-cross-account.yaml` (1), `rules/catalog/glue-network.yaml` (1)
- Modify: `tests/test_rules_action_field.py` (`PENDENTES`)

- [ ] **Step 1: Ler o `proposed_change` das 11**

Run: `python scripts/derive_action_kinds.py | grep -A6 -E "^## SF-(ENV|KMS|LF|XACC|NET)-"`

- [ ] **Step 2: Escrever o bloco `action` em cada regra**

```yaml
    action:
      kind: security.remove_literal_credential
      target: job.arguments
      direction: remove
      requires_absent: []
      moves: []
      depends_on: []
```

- [ ] **Step 3: Acrescentar ao vocabulário o que faltar**

- [ ] **Step 4: Encolher a allowlist e rodar**

Remover de `PENDENTES`: `env.yaml`, `glue-kms.yaml`, `lakeformation.yaml`, `glue-cross-account.yaml`, `glue-network.yaml`.

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/ tests/test_rules_action_field.py
git commit -m "feat(rules): action nas 11 regras de seguranca e ambiente"
```

---

### Task 10: Lote G — versão e orquestração (14 regras)

**Files:**
- Modify: `rules/catalog/glue-migration.yaml` (4), `rules/catalog/spark4.yaml` (4), `rules/catalog/controlm.yaml` (6)
- Modify: `tests/test_rules_action_field.py` (`PENDENTES`)

- [ ] **Step 1: Ler o `proposed_change` das 14**

Run: `python scripts/derive_action_kinds.py | grep -A6 -E "^## SF-(MIG|SPARK4|CTM)-"`

- [ ] **Step 2: Escrever o bloco `action` em cada regra**

```yaml
    action:
      kind: version.replace_removed_api
      target: pyspark.api
      direction: replace
      requires_absent: []
      moves: []
      depends_on: []
```

- [ ] **Step 3: Acrescentar ao vocabulário o que faltar**

- [ ] **Step 4: Esvaziar a allowlist e rodar**

`PENDENTES` vira `set()`. Isso liga `test_todo_kind_do_vocabulario_tem_regra`,
que estava dormente.

Run: `python -m pytest tests/test_rules_action_field.py -v`
Expected: PASS nos nove. Se `test_todo_kind_do_vocabulario_tem_regra` falhar,
ele nomeia os `kind` mortos — apagar do vocabulário, não inventar regra que os use.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/ tests/test_rules_action_field.py
git commit -m "feat(rules): action nas 14 regras de versao e orquestracao; allowlist zerada"
```

---

### Task 11: Rodar o catálogo inteiro e os lotes que ele toca

**Files:**
- nenhum arquivo novo

- [ ] **Step 1: Conferir a contagem**

Run:
```bash
python -c "
from sparkforge.rules.loader import load_catalog
r=[x for x in load_catalog() if x.get('executable',True)]
print(len(r), sum(1 for x in r if 'action' in x))
"
```
Expected: `112 112`

- [ ] **Step 2: Rodar os lotes de teste que tocam catálogo**

Run: `python -m pytest tests/test_rules_loader.py tests/test_fixtures_kind_coverage.py tests/test_rules_action_field.py -q`
Expected: PASS. Se um golden de finding comparar `to_dict()` inteiro, ele agora
tem `action` preenchido — atualizar o golden, que é a mudança correta.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "test(rules): goldens atualizados com o action propagado"
```

---

## Fase 3 — o motor

### Task 12: `source_authority.yaml` e o módulo de autoridade

**Files:**
- Create: `knowledge/source_authority.yaml`
- Create: `sparkforge/agentic/executor/__init__.py`
- Create: `sparkforge/agentic/executor/authority.py`
- Test: `tests/test_agentic_executor_authority.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Tier por host, vigencia e escopo de versao.

O par que importa: uma T1 FORA da versao alvo tem autoridade e nao sustenta a
claim. Foi essa diferenca que a auditoria de 2026-09-03 separou, quando
`has_sufficient_authority` e `has_fresh_in_scope` eram a mesma expressao.
"""

from __future__ import annotations

from sparkforge.agentic.models import EvidenceAuthority
from sparkforge.agentic.executor.authority import in_scope, load_authority_map, tier_for_url


class TestTierPorHost:
    def test_docs_aws_e_t1(self):
        m = load_authority_map()
        assert tier_for_url("https://docs.aws.amazon.com/glue/latest/dg/x.html", m) is (
            EvidenceAuthority.T1_OFFICIAL_DOCS
        )

    def test_github_releases_e_t2(self):
        m = load_authority_map()
        assert tier_for_url("https://github.com/apache/iceberg/releases/tag/v1.11.0", m) is (
            EvidenceAuthority.T2_SOURCE_CODE
        )

    def test_host_desconhecido_e_t4(self):
        m = load_authority_map()
        assert tier_for_url("https://blog.exemplo.com/spark-tuning", m) is (
            EvidenceAuthority.T4_RECOGNIZED_AUTHORITY
        )


class TestEscopoDeVersao:
    def test_regra_sem_runtime_scope_vale_em_qualquer_versao(self):
        assert in_scope({}, {"glue": "5.0", "spark": "3.5.4"}) is True

    def test_t1_fora_da_versao_alvo_nao_sustenta(self):
        assert in_scope({"glue": ["4.0"]}, {"glue": "6.0"}) is False

    def test_t1_dentro_da_versao_alvo_sustenta(self):
        assert in_scope({"glue": ["4.0", "5.0"]}, {"glue": "5.0"}) is True

    def test_runtime_sem_a_chave_do_escopo_nao_sustenta(self):
        # Escopo pede Glue e o case nao diz qual Glue: nao da para afirmar
        # que esta dentro, e afirmar que esta fora seria inventar.
        assert in_scope({"glue": ["5.0"]}, {"spark": "3.5.4"}) is False
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_authority.py -v`
Expected: FAIL com `ModuleNotFoundError: sparkforge.agentic.executor`.

- [ ] **Step 3: Escrever o mapa de conhecimento**

`knowledge/source_authority.yaml`:

```yaml
# Host da URL -> tier de autoridade. DADO versionado, nao codigo: pela mesma
# razao que a matriz de runtime e YAML e nao literal em Python.
#
# O tier gradua FONTE DE CONHECIMENTO. Ele nao gradua a medida do artefato do
# cliente, e nao existe tier para isso -- ver a §3.4 do spec.
schema_version: 1
default: T4_RECOGNIZED_AUTHORITY
hosts:
  docs.aws.amazon.com: T1_OFFICIAL_DOCS
  spark.apache.org: T1_OFFICIAL_DOCS
  iceberg.apache.org: T1_OFFICIAL_DOCS
  parquet.apache.org: T1_OFFICIAL_DOCS
  avro.apache.org: T1_OFFICIAL_DOCS
  aws.amazon.com: T1_OFFICIAL_DOCS
  docs.bmc.com: T1_OFFICIAL_DOCS
  github.com: T2_SOURCE_CODE
  issues.apache.org: T2_SOURCE_CODE
```

- [ ] **Step 4: Escrever o módulo**

`sparkforge/agentic/executor/__init__.py`:

```python
"""Executor agentico deterministico.

Roda depois de `judge`, sobre findings ja julgados. Nao chama provider nenhum.
"""

from sparkforge.agentic.executor.run import run_executor

__all__ = ["run_executor"]
```

`sparkforge/agentic/executor/authority.py`:

```python
"""Tier da fonte, vigencia e escopo de versao.

`tier_for_url` responde QUAL a autoridade da fonte. `in_scope` responde se ela
VALE para o runtime deste case. As duas juntas sao `has_fresh_in_scope`; nenhuma
delas sozinha e.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml

from sparkforge.agentic.models import EvidenceAuthority


def _knowledge_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "knowledge"


def load_authority_map(path: Path | None = None) -> dict[str, object]:
    src = path or (_knowledge_dir() / "source_authority.yaml")
    return yaml.safe_load(src.read_text(encoding="utf-8"))


def tier_for_url(url: str, mapping: dict[str, object]) -> EvidenceAuthority:
    host = (urlparse(url).hostname or "").lower()
    hosts = mapping.get("hosts") or {}
    nome = hosts.get(host) or mapping.get("default") or "T4_RECOGNIZED_AUTHORITY"
    return EvidenceAuthority[str(nome)]


def in_scope(runtime_scope: dict[str, object], runtime: dict[str, object]) -> bool:
    """Escopo vazio vale em qualquer versao. Escopo que nomeia uma chave que o
    case nao declara devolve False -- nao da para afirmar que esta dentro, e
    afirmar que esta fora seria inventar o contrario. As duas saidas erradas
    sao possiveis; esta e a que recusa em vez de aprovar."""
    if not runtime_scope:
        return True
    for chave, aceitos in runtime_scope.items():
        atual = runtime.get(chave)
        if atual is None:
            return False
        if str(atual) not in [str(v) for v in aceitos]:
            return False
    return True
```

- [ ] **Step 5: Rodar**

Run: `python -m pytest tests/test_agentic_executor_authority.py -v`
Expected: PASS nos sete.

- [ ] **Step 6: Commit**

```bash
git add knowledge/source_authority.yaml sparkforge/agentic/executor/ tests/test_agentic_executor_authority.py
git commit -m "feat(agentic): tier por host e escopo de versao, com a recusa quando o case nao declara a chave"
```

---

### Task 13: `measurement_ref` na `Evidence`

**Files:**
- Modify: `sparkforge/agentic/models.py:181`
- Test: `tests/test_agentic_models.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_agentic_models.py`:

```python
class TestEvidenceMeasurementRef:
    def test_measurement_ref_entra_no_id(self):
        from sparkforge.agentic.models import Evidence, EvidenceAuthority

        a = Evidence(
            source="https://docs.aws.amazon.com/glue/x.html",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            measurement_ref="f_aaa111",
        )
        b = Evidence(
            source="https://docs.aws.amazon.com/glue/x.html",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            measurement_ref="f_bbb222",
        )
        assert a.id != b.id

    def test_measurement_ref_sai_separado_do_authority(self):
        from sparkforge.agentic.models import Evidence, EvidenceAuthority

        e = Evidence(
            source="https://docs.aws.amazon.com/glue/x.html",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            measurement_ref="f_aaa111",
        )
        d = e.to_dict()
        assert d["authority"] == "T1_OFFICIAL_DOCS"
        assert d["measurement_ref"] == "f_aaa111"
```

O primeiro teste é o que impede a colisão: a mesma fonte oficial sustentando
medidas diferentes são evidências diferentes.

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_models.py::TestEvidenceMeasurementRef -v`
Expected: FAIL com `unexpected keyword argument 'measurement_ref'`.

- [ ] **Step 3: Acrescentar o campo**

Em `sparkforge/agentic/models.py`, dentro de `class Evidence`, depois de `scope`:

```python
    # `fact.id` da medida que casou com o `when` da regra. NUNCA se funde com
    # `authority`: o tier gradua a FONTE do limiar, e nao existe tier para
    # medida do artefato do cliente. Fundir os dois produziria um numero que
    # nao mede nada -- mesma familia da regra 22 (byte e token nao se somam).
    measurement_ref: str = ""
```

No `id`, acrescentar ao payload:

```python
            "measurement_ref": self.measurement_ref,
```

No `to_dict`, acrescentar:

```python
            "measurement_ref": self.measurement_ref,
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_models.py -v`
Expected: PASS. Nenhum teste fixa hash literal de `ev_` (medido: só prefixo e
igualdade entre dois iguais), então o payload novo não quebra nada.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/models.py tests/test_agentic_models.py
git commit -m "feat(agentic): Evidence carrega measurement_ref ao lado do authority, sem fundir os dois"
```

---

### Task 14: findings → `Claim` + `Evidence`

**Files:**
- Create: `sparkforge/agentic/executor/claims.py`
- Test: `tests/test_agentic_executor_claims.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Findings viram Claim, e os facts que os ancoram viram Evidence."""

from __future__ import annotations

from sparkforge.agentic.executor.authority import load_authority_map
from sparkforge.agentic.executor.claims import claims_from_findings

FINDING = {
    "rule_id": "SF-WASTE-001",
    "title": "Folga medida em worker, memoria e disco, sem skew que a explique",
    "severity": "P2",
    "confidence": "medium",
    "status": "confirmed",
    "subject": {"job": "etl_diario"},
    "evidence": ["f_aaa111"],
    "runtime_scope": {},
    "sources": [{"url": "https://docs.aws.amazon.com/glue/latest/dg/auto-scaling.html"}],
    "action": {
        "kind": "capacity.investigate_sizing",
        "target": "glue.number_of_workers",
        "direction": "investigate",
        "requires_absent": [],
        "moves": ["cost.dpu_seconds"],
        "depends_on": [],
    },
}
FACTS = [{"id": "f_aaa111", "kind": "glue.utilization.summary", "measures": {}}]
RUNTIME = {"glue": "5.0", "spark": "3.5.4"}


class TestClaimsFromFindings:
    def test_um_finding_vira_uma_claim(self):
        claims, _ = claims_from_findings([FINDING], FACTS, load_authority_map(), RUNTIME)
        assert len(claims) == 1
        assert claims[0].claimant == "SF-WASTE-001"
        assert "SF-WASTE-001" in claims[0].statement

    def test_evidence_liga_fonte_e_medida(self):
        _, evidences = claims_from_findings([FINDING], FACTS, load_authority_map(), RUNTIME)
        assert len(evidences) == 1
        assert evidences[0].authority.name == "T1_OFFICIAL_DOCS"
        assert evidences[0].measurement_ref == "f_aaa111"

    def test_evidence_suporta_a_claim_que_a_produziu(self):
        claims, evidences = claims_from_findings(
            [FINDING], FACTS, load_authority_map(), RUNTIME
        )
        assert evidences[0].supports == [claims[0].id]

    def test_confidence_high_com_t1_no_escopo_e_medida_presente(self):
        claims, _ = claims_from_findings([FINDING], FACTS, load_authority_map(), RUNTIME)
        assert claims[0].confidence == "high"

    def test_confidence_low_quando_a_medida_citada_nao_esta_nos_facts(self):
        claims, _ = claims_from_findings([FINDING], [], load_authority_map(), RUNTIME)
        assert claims[0].confidence == "low"

    def test_confidence_medium_com_t1_fora_do_escopo_de_versao(self):
        f = dict(FINDING, runtime_scope={"glue": ["4.0"]})
        claims, _ = claims_from_findings([f], FACTS, load_authority_map(), RUNTIME)
        assert claims[0].confidence == "medium"
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_claims.py -v`
Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Escrever o módulo**

```python
"""Findings julgados viram Claim; os facts que os ancoram viram Evidence.

O `confidence` da Claim NAO vem do score de `assess_claim` -- os pesos daquele
score sao convencao sem calibracao, e o `CLAUDE.md` diz isso por escrito. Ele
vem da tabela da §5.1 do spec, que e conferivel campo a campo.
"""

from __future__ import annotations

from typing import Any

from sparkforge.agentic.executor.authority import in_scope, tier_for_url
from sparkforge.agentic.models import Claim, ClaimType, Evidence, EvidenceAuthority

_COM_AUTORIDADE = (
    EvidenceAuthority.T1_OFFICIAL_DOCS,
    EvidenceAuthority.T2_SOURCE_CODE,
)

# `INFERENCE` e nao `RECOMMENDATION`: a claim afirma o DIAGNOSTICO derivado da
# medida. A mudanca proposta mora em `action`, que e dado da regra e nao
# afirmacao do executor. Os quatro membros de ClaimType sao OBSERVATION,
# INFERENCE, HYPOTHESIS e RECOMMENDATION -- medido, nao suposto.
_TIPO_DE_CLAIM = ClaimType.INFERENCE


def _melhor_tier(
    sources: list[dict[str, Any]], mapping: dict[str, Any]
) -> EvidenceAuthority:
    tiers = [tier_for_url(str(s.get("url") or ""), mapping) for s in sources]
    if not tiers:
        return EvidenceAuthority.T6_CONJECTURE
    return min(tiers, key=lambda t: t.name)


def confidence_for(
    tier: EvidenceAuthority, dentro_do_escopo: bool, medidas_presentes: bool
) -> str:
    """Tabela da §5.1 do spec. `high` exige as tres condicoes juntas."""
    if not medidas_presentes:
        return "low"
    if tier not in _COM_AUTORIDADE:
        return "low"
    if not dentro_do_escopo:
        return "medium"
    return "high"


def claims_from_findings(
    findings: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    authority_map: dict[str, Any],
    runtime: dict[str, Any],
    created_at: str = "",
) -> tuple[list[Claim], list[Evidence]]:
    ids_de_fact = {str(f.get("id")) for f in facts}
    claims: list[Claim] = []
    evidences: list[Evidence] = []

    for finding in findings:
        sources = list(finding.get("sources") or [])
        tier = _melhor_tier(sources, authority_map)
        dentro = in_scope(dict(finding.get("runtime_scope") or {}), runtime)
        refs = [str(e) for e in finding.get("evidence") or []]
        presentes = bool(refs) and all(r in ids_de_fact for r in refs)

        claim = Claim(
            claimant=str(finding["rule_id"]),
            claim_type=_TIPO_DE_CLAIM,
            statement=f"{finding['rule_id']}: {finding.get('title', '')}",
            evidence_refs=refs,
            confidence=confidence_for(tier, dentro, presentes),
            created_at=created_at,
        )
        claims.append(claim)

        for source in sources or [{}]:
            url = str(source.get("url") or "")
            evidences.append(
                Evidence(
                    source=url or str(finding["rule_id"]),
                    authority=tier_for_url(url, authority_map)
                    if url
                    else EvidenceAuthority.T6_CONJECTURE,
                    scope=str(finding.get("runtime_scope") or ""),
                    measurement_ref=refs[0] if refs else "",
                    supports=[claim.id],
                )
            )

    return claims, evidences
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_claims.py -v`
Expected: PASS nos seis.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/claims.py tests/test_agentic_executor_claims.py
git commit -m "feat(agentic): findings viram Claim, e o confidence vem de tabela conferivel e nao do score"
```

---

### Task 15: contradição direta e condicional

**Files:**
- Create: `sparkforge/agentic/executor/conflict.py`
- Test: `tests/test_agentic_executor_conflict.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Contradicao direta (mesmo target, direcoes opostas) e condicional
(`requires_absent` medido no mesmo case)."""

from __future__ import annotations

from sparkforge.agentic.executor.conflict import conditional_conflicts, direct_conflicts

SOBE_TIMEOUT = {
    "rule_id": "SF-TIMEOUT-001",
    "action": {
        "kind": "timeout.increase_limit",
        "target": "spark.network.timeout",
        "direction": "increase",
        "requires_absent": ["spark.stage.skew"],
    },
}
DESCE_TIMEOUT = {
    "rule_id": "SF-TIMEOUT-002",
    "action": {
        "kind": "timeout.decrease_limit",
        "target": "spark.network.timeout",
        "direction": "decrease",
        "requires_absent": [],
    },
}
OUTRO_ALVO = {
    "rule_id": "SF-PY-001",
    "action": {
        "kind": "code.replace_python_udf",
        "target": "pyspark.udf",
        "direction": "replace",
        "requires_absent": [],
    },
}


class TestContradicaoDireta:
    def test_mesmo_target_direcoes_opostas(self):
        pares = direct_conflicts([SOBE_TIMEOUT, DESCE_TIMEOUT])
        assert pares == [("SF-TIMEOUT-001", "SF-TIMEOUT-002")]

    def test_alvos_diferentes_nao_sao_contradicao(self):
        assert direct_conflicts([SOBE_TIMEOUT, OUTRO_ALVO]) == []

    def test_mesma_direcao_no_mesmo_alvo_nao_e_contradicao(self):
        gemeo = dict(SOBE_TIMEOUT, rule_id="SF-TIMEOUT-009")
        assert direct_conflicts([SOBE_TIMEOUT, gemeo]) == []


class TestContradicaoCondicional:
    def test_requires_absent_medido_dispara(self):
        facts = [{"id": "f_1", "kind": "spark.stage.skew"}]
        assert conditional_conflicts([SOBE_TIMEOUT], facts) == [
            ("SF-TIMEOUT-001", "spark.stage.skew", "f_1")
        ]

    def test_requires_absent_nao_medido_cala(self):
        facts = [{"id": "f_1", "kind": "spark.stage.spill"}]
        assert conditional_conflicts([SOBE_TIMEOUT], facts) == []

    def test_finding_sem_action_nao_participa(self):
        facts = [{"id": "f_1", "kind": "spark.stage.skew"}]
        assert conditional_conflicts([{"rule_id": "SF-X-001"}], facts) == []
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_conflict.py -v`
Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Escrever o módulo**

```python
"""Contradicao entre acoes propostas.

Direta: mesmo `target`, direcoes opostas. Condicional: o `requires_absent` de
uma acao esta MEDIDO no mesmo case -- subir timeout com skew ao lado troca uma
falha rapida por uma falha cara, que e a regra 15 do CLAUDE.md tornada
verificavel.

Alvos diferentes nao sao contradicao. Sao ordem, e caem em `ordering.py`.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

_OPOSTAS = {
    frozenset({"increase", "decrease"}),
    frozenset({"add", "remove"}),
}


def direct_conflicts(findings: list[dict[str, Any]]) -> list[tuple[str, str]]:
    pares: list[tuple[str, str]] = []
    com_acao = [f for f in findings if f.get("action")]
    for a, b in combinations(com_acao, 2):
        aa, ab = a["action"], b["action"]
        if aa.get("target") != ab.get("target"):
            continue
        if frozenset({aa.get("direction"), ab.get("direction")}) in _OPOSTAS:
            pares.append((str(a["rule_id"]), str(b["rule_id"])))
    return sorted(pares)


def conditional_conflicts(
    findings: list[dict[str, Any]], facts: list[dict[str, Any]]
) -> list[tuple[str, str, str]]:
    """Devolve (rule_id, kind_proibido, fact_id) -- o fact_id entra porque a
    contradicao precisa apontar a MEDIDA, nao so o nome do kind."""
    por_kind: dict[str, str] = {}
    for fact in facts:
        por_kind.setdefault(str(fact.get("kind")), str(fact.get("id")))

    achados: list[tuple[str, str, str]] = []
    for finding in findings:
        action = finding.get("action") or {}
        for proibido in action.get("requires_absent") or []:
            if proibido in por_kind:
                achados.append((str(finding["rule_id"]), str(proibido), por_kind[proibido]))
    return sorted(achados)
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_conflict.py -v`
Expected: PASS nos seis.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/conflict.py tests/test_agentic_executor_conflict.py
git commit -m "feat(agentic): contradicao direta e condicional, com o fact_id da medida que a sustenta"
```

---

### Task 16: ordem de aplicação

**Files:**
- Create: `sparkforge/agentic/executor/ordering.py`
- Test: `tests/test_agentic_executor_ordering.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Ordem topologica sobre `depends_on`, mais as duas restricoes derivadas."""

from __future__ import annotations

from sparkforge.agentic.executor.ordering import order_actions

INVESTIGA = {
    "rule_id": "SF-WASTE-001",
    "action": {
        "kind": "capacity.investigate_sizing",
        "target": "glue.number_of_workers",
        "direction": "investigate",
        "moves": ["cost.dpu_seconds"],
        "depends_on": [],
    },
}
REDUZ = {
    "rule_id": "SF-GLUE-003",
    "action": {
        "kind": "capacity.reduce_workers",
        "target": "glue.number_of_workers",
        "direction": "decrease",
        "moves": ["cost.dpu_seconds"],
        "depends_on": [],
    },
}
TROCA_UDF = {
    "rule_id": "SF-PY-001",
    "action": {
        "kind": "code.replace_python_udf",
        "target": "pyspark.udf",
        "direction": "replace",
        "moves": ["runtime.wall_clock"],
        "depends_on": [],
    },
}


class TestOrdem:
    def test_investigate_vem_antes_de_mudar_o_mesmo_alvo(self):
        ordem, _, _ = order_actions([REDUZ, INVESTIGA])
        assert ordem.index("SF-WASTE-001") < ordem.index("SF-GLUE-003")

    def test_depends_on_declarado_e_respeitado(self):
        a = dict(TROCA_UDF)
        b = {
            "rule_id": "SF-PY-002",
            "action": {
                "kind": "code.replace_python_udf",
                "target": "pyspark.udf_2",
                "direction": "replace",
                "moves": [],
                "depends_on": ["SF-PY-001"],
            },
        }
        ordem, _, _ = order_actions([b, a])
        assert ordem.index("SF-PY-001") < ordem.index("SF-PY-002")

    def test_ciclo_sai_unresolved_e_nao_ordem_arbitraria(self):
        a = {
            "rule_id": "SF-A-001",
            "action": {"kind": "k", "target": "t1", "direction": "add", "moves": [], "depends_on": ["SF-B-001"]},
        }
        b = {
            "rule_id": "SF-B-001",
            "action": {"kind": "k", "target": "t2", "direction": "add", "moves": [], "depends_on": ["SF-A-001"]},
        }
        ordem, _, unresolved = order_actions([a, b])
        assert ordem == []
        assert unresolved["reason"] == "order.unresolved"
        assert sorted(unresolved["cycle"]) == ["SF-A-001", "SF-B-001"]


class TestEixoCompartilhado:
    def test_duas_acoes_no_mesmo_eixo_nao_entram_no_mesmo_run(self):
        _, restricoes, _ = order_actions([INVESTIGA, REDUZ])
        assert {
            "axis": "cost.dpu_seconds",
            "rules": ["SF-GLUE-003", "SF-WASTE-001"],
            "reason": "aplicar juntas torna o antes/depois inatribuivel",
        } in restricoes

    def test_eixos_diferentes_nao_geram_restricao(self):
        _, restricoes, _ = order_actions([REDUZ, TROCA_UDF])
        assert restricoes == []
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_ordering.py -v`
Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Escrever o módulo**

```python
"""Ordem de aplicacao.

Topologica sobre `depends_on`, mais duas restricoes derivadas:

1. acao `investigate` sobre um alvo vem ANTES de qualquer acao que mude aquele
   alvo -- medir antes de mexer;
2. duas acoes que compartilham eixo em `moves` nao entram no mesmo run --
   aplicar juntas torna o antes/depois inatribuivel, e atribuir a melhora a uma
   delas exigiria o run que nao aconteceu (regra 13).

Ciclo nao produz ordem arbitraria. Produz recusa nomeada.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def order_actions(
    findings: list[dict[str, Any]],
    eixos_de_medida: set[str] | None = None,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    eixos_de_medida = eixos_de_medida if eixos_de_medida is not None else load_measure_axes()
    com_acao = [f for f in findings if f.get("action")]
    ids = [str(f["rule_id"]) for f in com_acao]
    acao = {str(f["rule_id"]): f["action"] for f in com_acao}

    antes: dict[str, set[str]] = {i: set() for i in ids}
    for rid, a in acao.items():
        for dep in a.get("depends_on") or []:
            if str(dep) in antes:
                antes[rid].add(str(dep))

    for alvo in {a.get("target") for a in acao.values()}:
        investigam = [i for i in ids if acao[i].get("target") == alvo and acao[i].get("direction") == "investigate"]
        mudam = [i for i in ids if acao[i].get("target") == alvo and acao[i].get("direction") != "investigate"]
        for m in mudam:
            antes[m].update(investigam)

    ordem: list[str] = []
    pendentes = dict(antes)
    while pendentes:
        prontos = sorted(i for i, deps in pendentes.items() if not deps)
        if not prontos:
            return [], [], {"reason": "order.unresolved", "cycle": sorted(pendentes)}
        for i in prontos:
            ordem.append(i)
            del pendentes[i]
        for deps in pendentes.values():
            deps.difference_update(prontos)

    por_eixo: dict[str, list[str]] = defaultdict(list)
    for rid, a in acao.items():
        for eixo in a.get("moves") or []:
            # SO eixo de `nature: measure`. Medido em 2026-09-08:
            # `correctness.write_result` e `nature: risk` e aparece em 33 das
            # 112 -- incluindo os de risco, o maior grupo tem 33 regras e a
            # restricao vira ruido; so com os de medida, 15 eixos e o maior
            # grupo tem 10. A razao e principiada: a restricao existe porque
            # duas mudancas que movem a mesma MEDIDA tornam o antes/depois
            # inatribuivel (regra 13). Duas que ambas podem alterar o resultado
            # nao tem esse problema -- o que elas exigem e validacao funcional,
            # que e `funcval` e nao isto.
            if str(eixo) not in eixos_de_medida:
                continue
            por_eixo[str(eixo)].append(rid)

    restricoes = [
        {
            "axis": eixo,
            "rules": sorted(regras),
            "reason": "aplicar juntas torna o antes/depois inatribuivel",
        }
        for eixo, regras in sorted(por_eixo.items())
        if len(regras) > 1
    ]

    return ordem, restricoes, {}
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_ordering.py -v`
Expected: PASS nos cinco.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/ordering.py tests/test_agentic_executor_ordering.py
git commit -m "feat(agentic): ordem de aplicacao, com ciclo saindo unresolved e nao arbitrado"
```

---

### Task 17: `Unknown` e o `Experiment` que o destrava

**Files:**
- Create: `sparkforge/agentic/executor/unknowns.py`
- Test: `tests/test_agentic_executor_run.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_agentic_executor_run.py` com esta classe (as outras entram na Tarefa 19):

```python
"""Unknowns: fact `unresolved`, lastro reprovado, e a arbitragem que pede
experimento. Nenhum deles produz previsao de ganho."""

from __future__ import annotations

from sparkforge.agentic.executor.unknowns import experiments_from, unknowns_from


class TestUnknowns:
    def test_fact_unresolved_vira_unknown(self):
        facts = [
            {
                "id": "f_1",
                "kind": "glue.run_cost.unresolved",
                "attrs": {"reason": "sem DPUSeconds sob Auto Scaling"},
            }
        ]
        us = unknowns_from([], facts)
        assert len(us) == 1
        assert "glue.run_cost" in us[0].question
        assert us[0].evidence_needed == ["sem DPUSeconds sob Auto Scaling"]

    def test_claim_low_vira_unknown_com_a_medida_que_destrava(self):
        finding = {
            "rule_id": "SF-X-001",
            "title": "t",
            "evidence": ["f_ausente"],
            "sources": [],
            "action": {"kind": "k", "target": "t", "direction": "add"},
        }
        us = unknowns_from([finding], [])
        assert any("f_ausente" in " ".join(u.evidence_needed) for u in us)

    def test_nenhum_unknown_carrega_previsao_de_ganho(self):
        facts = [{"id": "f_1", "kind": "glue.run_cost.unresolved", "attrs": {}}]
        for u in unknowns_from([], facts):
            texto = (u.question + " ".join(u.evidence_needed)).lower()
            assert "%" not in texto
            assert "econom" not in texto


class TestExperimentos:
    def test_unknown_bloqueante_vira_experimento(self):
        from sparkforge.agentic.executor.unknowns import experiments_from

        facts = [
            {
                "id": "f_1",
                "kind": "glue.run_cost.unresolved",
                "attrs": {"reason": "sem DPUSeconds sob Auto Scaling"},
            }
        ]
        exps = experiments_from(unknowns_from([], facts))
        assert len(exps) == 1
        assert exps[0].variable == "glue.run_cost"

    def test_custo_e_tempo_saem_unresolved(self):
        from sparkforge.agentic.executor.unknowns import experiments_from

        facts = [{"id": "f_1", "kind": "glue.run_cost.unresolved", "attrs": {}}]
        exp = experiments_from(unknowns_from([], facts))[0]
        assert exp.cost_estimate == "unresolved"
        assert exp.time_estimate == "unresolved"

    def test_expected_results_nao_prediz_ganho(self):
        from sparkforge.agentic.executor.unknowns import experiments_from

        facts = [{"id": "f_1", "kind": "glue.run_cost.unresolved", "attrs": {}}]
        exp = experiments_from(unknowns_from([], facts))[0]
        assert exp.expected_results == ""
        assert exp.success_criteria
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_run.py -v`
Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 4: Escrever o módulo**

```python
"""Lacuna medida vira `Unknown`, e o Unknown nomeia o que a destravaria.

Tres origens: fact `*.unresolved`, claim sem lastro, e arbitragem que devolveu
`experiment`. Nenhum Unknown carrega previsao de ganho -- o experimento diz o
que medir, nunca quanto vai melhorar (regra 13).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sparkforge.agentic.experiment import design_experiment_for_unknown
from sparkforge.agentic.models import Experiment, Unknown


def unknowns_from(
    findings: list[dict[str, Any]], facts: list[dict[str, Any]]
) -> list[Unknown]:
    achados: list[Unknown] = []

    for fact in facts:
        kind = str(fact.get("kind") or "")
        if not kind.endswith(".unresolved"):
            continue
        base = kind[: -len(".unresolved")]
        razao = str((fact.get("attrs") or {}).get("reason") or "razao nao declarada")
        achados.append(
            Unknown(
                question=f"{base}: a medida nao foi resolvida.",
                evidence_needed=[razao],
                blocking=True,
            )
        )

    ids = {str(f.get("id")) for f in facts}
    for finding in findings:
        faltando = [str(e) for e in finding.get("evidence") or [] if str(e) not in ids]
        if faltando:
            achados.append(
                Unknown(
                    question=(
                        f"{finding['rule_id']}: o achado cita medida que nao esta "
                        "no conjunto de facts deste case."
                    ),
                    evidence_needed=sorted(faltando),
                    blocking=True,
                )
            )

    return achados


def experiments_from(unknowns: list[Unknown]) -> list[Experiment]:
    """Cada Unknown bloqueante vira um experimento que diz O QUE MEDIR.

    `expected_results` fica VAZIO de proposito: preve-lo seria estimar ganho, e
    a regra 13 recusa isso. `cost_estimate` e `time_estimate` saem
    `unresolved` -- a entrega original os fixava em texto, e a auditoria de
    2026-09-03 pegou isso como um dos catorze defeitos.
    """
    exps: list[Experiment] = []
    for unknown in unknowns:
        if not unknown.blocking:
            continue
        variavel = unknown.question.split(":", 1)[0].strip()
        exp = design_experiment_for_unknown(
            unknown_question=unknown.question,
            variable=variavel,
            baseline="o estado medido neste case",
            evidence_needed=list(unknown.evidence_needed),
            proposed_by="sparkforge.agentic.executor",
        )
        exps.append(
            replace(
                exp,
                expected_results="",
                cost_estimate="unresolved",
                time_estimate="unresolved",
            )
        )
    return exps
```

Se `design_experiment_for_unknown` já devolver `success_criteria` preenchido, o
`replace` acima não o toca — o que ele zera é só o que a regra 13 proíbe.

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_run.py -v`
Expected: PASS nos seis.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/unknowns.py tests/test_agentic_executor_run.py
git commit -m "feat(agentic): lacuna medida vira Unknown, sem previsao de ganho"
```

---

### Task 18: `DebatePlan` e a recusa nomeada

**Files:**
- Create: `sparkforge/agentic/executor/plan.py`
- Test: `tests/test_agentic_executor_run.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_agentic_executor_run.py`:

```python
from sparkforge.agentic.executor.plan import debate_plan


class TestDebatePlan:
    def test_plano_nomeia_participantes_contexto_e_parada(self):
        plano = debate_plan(
            rule_ids=["SF-TIMEOUT-001", "SF-UI-003"],
            fact_ids_por_regra={"SF-TIMEOUT-001": ["f_1"], "SF-UI-003": ["f_2"]},
            budget=None,
        )
        assert plano["reason"] == "debate.unresolved"
        assert set(plano["participants"]) >= {"SF-TIMEOUT-001", "SF-UI-003"}
        assert plano["context"]["SF-TIMEOUT-001"] == ["f_1"]
        assert plano["stop_criterion"]

    def test_sem_budget_declarado_sai_unresolved_e_nao_o_default_do_codigo(self):
        plano = debate_plan(
            rule_ids=["SF-A-001", "SF-B-001"],
            fact_ids_por_regra={},
            budget=None,
        )
        assert plano["budget"]["status"] == "unresolved"
        assert "case.yaml" in plano["budget"]["blocks"]

    def test_budget_declarado_viaja_no_plano(self):
        plano = debate_plan(
            rule_ids=["SF-A-001", "SF-B-001"],
            fact_ids_por_regra={},
            budget={"max_tokens": 3000, "debate_rounds": 2},
        )
        assert plano["budget"]["status"] == "declared"
        assert plano["budget"]["limits"]["debate_rounds"] == 2

    def test_o_plano_nao_executa_nada(self):
        plano = debate_plan(rule_ids=["SF-A-001"], fact_ids_por_regra={}, budget=None)
        assert plano["executed"] is False
        assert "AgentRuntime" in plano["blocks"]
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_run.py::TestDebatePlan -v`
Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Escrever o módulo**

```python
"""O plano de debate que o executor emite quando a arbitragem nao fecha.

Ele nomeia quem participaria, com que contexto e sob que parada. E PARA. Este
pacote nao tem executor de debate, e dizer isso e a diferenca entre "nao sei" e
"nao perguntei" (regra 20).
"""

from __future__ import annotations

from typing import Any


def debate_plan(
    rule_ids: list[str],
    fact_ids_por_regra: dict[str, list[str]],
    budget: dict[str, Any] | None,
) -> dict[str, Any]:
    if budget:
        bloco = {"status": "declared", "limits": dict(budget)}
    else:
        bloco = {
            "status": "unresolved",
            "blocks": (
                "o case.yaml nao declara bloco `budget:`. O default do codigo "
                "so aparece sob `sparkforge budget show --template`, e nao e o "
                "estado deste case."
            ),
        }

    return {
        "reason": "debate.unresolved",
        "participants": sorted(rule_ids),
        "context": {r: sorted(fact_ids_por_regra.get(r, [])) for r in sorted(rule_ids)},
        "stop_criterion": (
            "uma das claims passa a citar medida que a outra nao cita, ou o "
            "budget declarado se esgota"
        ),
        "budget": bloco,
        "executed": False,
        "blocks": (
            "nao ha executor de debate neste pacote. Destrava com um "
            "AgentRuntime concreto, implementado fora do pacote pelo host."
        ),
    }
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_run.py -v`
Expected: PASS nos dez.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/plan.py tests/test_agentic_executor_run.py
git commit -m "feat(agentic): DebatePlan emitido e nao executado, com a recusa nomeada"
```

---

### Task 19: orquestrar, decidir e gravar

**Files:**
- Create: `sparkforge/agentic/executor/run.py`
- Test: `tests/test_agentic_executor_run.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_agentic_executor_run.py`:

```python
import json
from pathlib import Path

from sparkforge.agentic.blackboard import read_claims, read_decisions
from sparkforge.agentic.executor import run_executor


def _fixture(nome: str) -> tuple[list, list]:
    base = Path("fixtures/waste") / nome
    facts = json.loads((base / "expected" / "facts.json").read_text(encoding="utf-8"))
    findings = json.loads((base / "expected" / "findings.json").read_text(encoding="utf-8"))
    return facts if isinstance(facts, list) else facts["facts"], (
        findings if isinstance(findings, list) else findings["findings"]
    )


class TestRunPontaAPonta:
    def test_case_real_produz_claim_no_blackboard(self, tmp_path):
        facts, findings = _fixture("folga_medida_sem_skew")
        run_executor(findings, facts, root=tmp_path, runtime={"glue": "5.0"})
        assert len(read_claims(tmp_path)) == len(findings)

    def test_decisao_carrega_rollback(self, tmp_path):
        facts, findings = _fixture("folga_medida_sem_skew")
        run_executor(findings, facts, root=tmp_path, runtime={"glue": "5.0"})
        for d in read_decisions(tmp_path):
            assert d["rollback"].strip()

    def test_resposta_nao_publica_score(self, tmp_path):
        facts, findings = _fixture("folga_medida_sem_skew")
        out = run_executor(findings, facts, root=tmp_path, runtime={"glue": "5.0"})
        assert "score" not in json.dumps(out)

    def test_contradicao_condicional_sai_como_objection(self, tmp_path):
        # `SF-TIMEOUT-001` com skew medido ao lado: a objecao aponta o fact
        # que a sustenta, e nao so o nome do kind.
        findings = [
            {
                "rule_id": "SF-TIMEOUT-001",
                "title": "t",
                "evidence": ["f_1"],
                "sources": [{"url": "https://spark.apache.org/docs/latest/x.html"}],
                "runtime_scope": {},
                "action": {
                    "kind": "timeout.increase_limit",
                    "target": "spark.network.timeout",
                    "direction": "increase",
                    "requires_absent": ["spark.stage.skew"],
                    "moves": ["runtime.wall_clock"],
                    "depends_on": [],
                },
            }
        ]
        facts = [
            {"id": "f_1", "kind": "spark.timeout.diagnosis"},
            {"id": "f_2", "kind": "spark.stage.skew"},
        ]
        out = run_executor(findings, facts, root=tmp_path, runtime={"spark": "3.5.4"})
        assert len(out["objections"]) == 1
        assert out["objections"][0]["evidence_refs"] == ["f_2"]
        assert out["contradictions"] == []

    def test_blackboard_indisponivel_nao_derruba_a_chamada(self, tmp_path):
        facts, findings = _fixture("folga_medida_sem_skew")
        arquivo = tmp_path / "bloqueado"
        arquivo.write_text("nao sou diretorio", encoding="utf-8")
        out = run_executor(findings, facts, root=arquivo, runtime={"glue": "5.0"})
        assert out["persisted"] is False
        assert out["claims"]
```

O último teste é a regra 27: medição nunca derruba a chamada.

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_executor_run.py::TestRunPontaAPonta -v`
Expected: FAIL com `ImportError: cannot import name 'run_executor'`.

- [ ] **Step 3: Escrever o módulo**

```python
"""Orquestra o executor: claims, contradicoes, unknowns, ordem, decisoes.

Nao chama provider nenhum. Grava no blackboard do repo, e se a gravacao falhar
devolve o resultado do mesmo jeito -- instrumentacao que quebra o produto e
defeito, nao observabilidade (regra 27).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.agentic.arbitration import arbitrate
from sparkforge.agentic.blackboard import (
    append_claim,
    append_contradiction,
    append_decision,
    append_evidence,
    append_experiment,
    append_objection,
    append_unknown,
    init_blackboard,
)
from sparkforge.agentic.decision import DecisionContext, make_decision
from sparkforge.agentic.executor.authority import load_authority_map
from sparkforge.agentic.executor.claims import claims_from_findings
from sparkforge.agentic.executor.conflict import conditional_conflicts, direct_conflicts
from sparkforge.agentic.executor.ordering import order_actions
from sparkforge.agentic.executor.plan import debate_plan
from sparkforge.agentic.executor.unknowns import experiments_from, unknowns_from
from sparkforge.agentic.models import Contradiction, Objection


def run_executor(
    findings: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    root: Path | str,
    runtime: dict[str, Any] | None = None,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or {}
    claims, evidences = claims_from_findings(
        findings, facts, load_authority_map(), runtime
    )
    por_id = {c.claimant: c for c in claims}

    diretas = direct_conflicts(findings)
    condicionais = conditional_conflicts(findings, facts)
    ordem, restricoes, ordem_unresolved = order_actions(findings)
    unknowns = unknowns_from(findings, facts)
    experimentos = experiments_from(unknowns)

    contradicoes: list[Contradiction] = []
    objecoes: list[Objection] = []
    decisoes = []
    planos = []

    for a, b in diretas:
        contradicoes.append(
            Contradiction(
                claim_a=por_id[a].id,
                claim_b=por_id[b].id,
                description=f"{a} e {b} propoem direcoes opostas sobre o mesmo alvo.",
                detected_by="sparkforge.agentic.executor",
            )
        )
        resultado = arbitrate([por_id[a], por_id[b]], evidences, runtime)
        if resultado.recommendation in {"escalate", "experiment"} or resultado.winning_claim_id is None:
            planos.append(
                debate_plan(
                    rule_ids=[a, b],
                    fact_ids_por_regra={
                        a: list(por_id[a].evidence_refs),
                        b: list(por_id[b].evidence_refs),
                    },
                    budget=budget,
                )
            )
            continue
        vencedora = a if resultado.winning_claim_id == por_id[a].id else b
        decisoes.append(
            make_decision(
                DecisionContext(
                    problem=f"{a} e {b} propoem direcoes opostas sobre o mesmo alvo.",
                    options=[a, b],
                    evidence_by_option={
                        a: list(por_id[a].evidence_refs),
                        b: list(por_id[b].evidence_refs),
                    },
                    runtime=dict(runtime),
                    decided_by="sparkforge.agentic.executor",
                ),
                selected_option=vencedora,
                confidence=por_id[vencedora].confidence,
                validation=f"conferir os eixos declarados em `moves` de {vencedora}",
                rollback=f"reverter a mudanca proposta por {vencedora}",
            )
        )

    # Contradicao CONDICIONAL sai como `Objection`, e nao como `Contradiction`.
    # `Contradiction` liga duas claims (`claim_a`/`claim_b`); a condicional liga
    # uma claim a uma MEDIDA, e enfia-la naquele modelo mentiria sobre o tipo.
    # `Objection(target_claim, objector, statement, evidence_refs)` e a forma
    # que ja existe para exatamente isso.
    for rule_id, kind_proibido, fact_id in condicionais:
        objecoes.append(
            Objection(
                target_claim=por_id[rule_id].id,
                objector="sparkforge.agentic.executor",
                statement=(
                    f"{rule_id} propoe uma mudanca desaconselhada por {kind_proibido}, "
                    f"que esta medido neste case."
                ),
                evidence_refs=[fact_id],
            )
        )

    resposta: dict[str, Any] = {
        "claims": [c.to_dict() for c in claims],
        "evidence": [e.to_dict() for e in evidences],
        "contradictions": [c.to_dict() for c in contradicoes],
        "objections": [o.to_dict() for o in objecoes],
        "unknowns": [u.to_dict() for u in unknowns],
        "experiments": [e.to_dict() for e in experimentos],
        "decisions": [d.to_dict() for d in decisoes],
        "debate_plans": planos,
        "order": ordem,
        "order_constraints": restricoes,
        "order_unresolved": ordem_unresolved,
        "persisted": False,
    }

    try:
        init_blackboard(root)
        for c in claims:
            append_claim(c, root)
        for e in evidences:
            append_evidence(e, root)
        for c in contradicoes:
            append_contradiction(c, root)
        for o in objecoes:
            append_objection(o, root)
        for u in unknowns:
            append_unknown(u, root)
        for e in experimentos:
            append_experiment(e, root)
        for d in decisoes:
            append_decision(d, root)
        resposta["persisted"] = True
    except OSError as exc:
        resposta["persist_error"] = str(exc)

    return resposta
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_executor_run.py -v`
Expected: PASS nos quinze.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/agentic/executor/run.py tests/test_agentic_executor_run.py
git commit -m "feat(agentic): executor ponta a ponta, e a gravacao que falha sem derrubar a chamada"
```

---

## Fase 4 — superfície

### Task 20: verbo de CLI `arbitrate`

**Files:**
- Modify: `sparkforge/adapters/cli.py`
- Test: `tests/test_agentic_cli.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_agentic_cli.py`:

```python
class TestArbitrateCLI:
    def test_arbitrate_grava_e_imprime_json(self, tmp_path, capsys):
        import json

        from sparkforge.adapters.cli import main

        findings = tmp_path / "findings.json"
        facts = tmp_path / "facts.json"
        findings.write_text(
            json.dumps(
                [
                    {
                        "rule_id": "SF-WASTE-001",
                        "title": "t",
                        "evidence": ["f_1"],
                        "sources": [{"url": "https://docs.aws.amazon.com/glue/x.html"}],
                        "runtime_scope": {},
                        "action": {
                            "kind": "capacity.investigate_sizing",
                            "target": "glue.number_of_workers",
                            "direction": "investigate",
                            "requires_absent": [],
                            "moves": [],
                            "depends_on": [],
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        facts.write_text(
            json.dumps([{"id": "f_1", "kind": "glue.utilization.summary"}]), encoding="utf-8"
        )

        code = main(
            [
                "arbitrate",
                "--findings",
                str(findings),
                "--facts",
                str(facts),
                "--repo",
                str(tmp_path),
            ]
        )
        assert code == 0
        saida = json.loads(capsys.readouterr().out)
        assert saida["persisted"] is True
        assert len(saida["claims"]) == 1
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_agentic_cli.py::TestArbitrateCLI -v`
Expected: FAIL com erro de argumento desconhecido `arbitrate`.

- [ ] **Step 3: Acrescentar o parser**

Em `sparkforge/adapters/cli.py`, depois do bloco `# agentic: autonomy`:

```python
    # agentic: arbitrate ----------------------------------------------------
    arb_p = sub.add_parser(
        "arbitrate",
        help=(
            "Roda o executor deterministico sobre findings ja julgados: "
            "claims, contradicoes, unknowns, ordem e decisoes."
        ),
    )
    arb_p.add_argument("--findings", required=True, help="JSON com a lista de findings.")
    arb_p.add_argument("--facts", required=True, help="JSON com a lista de facts.")
    arb_p.add_argument("--repo", default=".", help="Raiz onde fica o blackboard.")
```

E o handler, junto dos outros `_cmd_*`:

```python
def _cmd_arbitrate(args: argparse.Namespace) -> int:
    from sparkforge.agentic.executor import run_executor

    findings = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    facts = json.loads(Path(args.facts).read_text(encoding="utf-8"))
    if isinstance(findings, dict):
        findings = findings.get("findings", [])
    if isinstance(facts, dict):
        facts = facts.get("facts", [])
    saida = run_executor(findings, facts, root=args.repo)
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    return 0
```

E o despacho, no mesmo lugar onde `blackboard_action` é despachado (linha ~3132):

```python
    if args.command == "arbitrate":
        return _cmd_arbitrate(args)
```

- [ ] **Step 4: Rodar**

Run: `python -m pytest tests/test_agentic_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/adapters/cli.py tests/test_agentic_cli.py
git commit -m "feat(cli): verbo arbitrate, e os decisions list/explain passam a ler algo"
```

---

### Task 21: tool MCP `sparkforge_arbitrate` e o lock de superfície

**Files:**
- Modify: `sparkforge/adapters/tools.py`
- Modify: `docs/surface.lock.json`
- Test: `tests/test_agent_coverage.py`

- [ ] **Step 1: Medir a superfície antes**

Run: `python scripts/check_surface_lock.py`
Expected: `0`. Anotar os bytes de tools que ele imprime — o crescimento vai
declarado no commit.

- [ ] **Step 2: Escrever o teste que falha**

Acrescentar a `tests/test_agent_coverage.py`:

```python
class TestArbitrateAlcancavel:
    def test_tool_existe(self):
        from sparkforge.adapters.tools import TOOLS

        assert "sparkforge_arbitrate" in TOOLS

    def test_algum_coordenador_a_alcanca(self):
        from pathlib import Path

        textos = [
            p.read_text(encoding="utf-8")
            for p in Path("agents").glob("*.md")
        ]
        assert any("sparkforge_arbitrate" in t for t in textos), (
            "tool inalcancavel: nenhum coordenador a cita"
        )
```

- [ ] **Step 3: Rodar**

Run: `python -m pytest tests/test_agent_coverage.py::TestArbitrateAlcancavel -v`
Expected: FAIL nos dois.

- [ ] **Step 4: Declarar a tool**

Em `sparkforge/adapters/tools.py`, ao lado de `"sparkforge_judge"`:

```python
    "sparkforge_arbitrate": {
        "description": (
            "Executor deterministico sobre findings ja julgados. Produz claims, "
            "contradicoes (direta e condicional), unknowns, ordem de aplicacao e "
            "decisoes com rollback, gravados no blackboard.\n\n"
            "NAO estima ganho, NAO publica score de arbitragem como confianca "
            "medida, e NAO executa debate -- quando a arbitragem nao fecha, "
            "devolve um plano de debate com `debate.unresolved`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Findings, como `sparkforge_judge` os devolve.",
                },
                "facts": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Facts que ancoram os findings.",
                },
                "repo": {"type": "string", "description": "Raiz do blackboard."},
                "runtime": {
                    "type": "object",
                    "description": "RuntimeContext do case, para o escopo de versao.",
                },
            },
            "required": ["findings", "facts"],
        },
    },
```

Acrescentar `sparkforge_arbitrate` ao coordenador que já despacha decisão
agêntica — `agents/sf-orchestrator.md` —, na lista de tools que ele cita.

- [ ] **Step 5: Rodar e atualizar o lock**

Run: `python -m pytest tests/test_agent_coverage.py -v`
Expected: PASS.

Run: `python scripts/check_surface_lock.py --update`
Expected: escreve o `docs/surface.lock.json` novo e imprime o crescimento.

Run: `python -c "from sparkforge.adapters.tools import TOOLS; print(len(TOOLS))"`
Expected: `69`

- [ ] **Step 6: Commit**

```bash
git add sparkforge/adapters/tools.py agents/sf-orchestrator.md docs/surface.lock.json tests/test_agent_coverage.py
git commit -m "feat(mcp): sparkforge_arbitrate -- tools 68 para 69, superficie declarada no lock"
```

---

## Fase 5 — fechamento

### Task 22: docs, números e a regra 29 reescrita

**Files:**
- Modify: `docs/superpowers/STATUS.md`
- Modify: `docs/agentic-evolution-report.md`
- Modify: `CLAUDE.md`
- Modify: `README.md`, `AGENTS.md`

- [ ] **Step 1: Medir tudo antes de escrever**

Run:
```bash
python -c "from sparkforge.adapters.tools import TOOLS; print('tools', len(TOOLS))"
python -c "
from sparkforge.rules.loader import load_catalog
r=[x for x in load_catalog() if x.get('executable',True)]
print('executaveis', len(r), 'com action', sum(1 for x in r if 'action' in x))
"
python -m pytest tests/ --collect-only -q 2>&1 | tail -1
```

Nenhum número entra na doc sem sair de um destes comandos.

- [ ] **Step 2: Reescrever a regra 29 do `CLAUDE.md`**

Substituir o texto atual da regra 29 por:

```markdown
29. **A camada agêntica tem executor determinístico, e não tem executor de
    debate.** `sparkforge arbitrate` roda depois de `judge` e produz
    `Claim`/`Evidence`/`Contradiction`/`Unknown`/`Decision` no blackboard do
    case — num case rodado, `blackboard summary` deixa de devolver zero. O que
    continua não existindo é o executor de **debate**: quando a arbitragem não
    fecha, o verbo emite um `DebatePlan` e para, com `debate.unresolved`.
    Nenhum `AgentRuntime` concreto mora neste pacote, e nada aqui chama
    provider. Status por componente em `docs/agentic-evolution-report.md`.
```

A regra 30 **não muda**: continua não havendo benchmark da arquitetura nova
contra a antiga, e por isso nenhuma afirmação de ganho.

- [ ] **Step 3: Acrescentar a seção ao STATUS**

Seção nova no fim de `docs/superpowers/STATUS.md`, no molde das anteriores:
o que foi entregue, o que ela não é, os números medidos no passo 1, e a
correção do "111 de 111 executáveis" para 112 (desvio D-2 deste plano).

- [ ] **Step 4: Atualizar `docs/agentic-evolution-report.md`, `README.md` e `AGENTS.md`**

O executor sai de inexistente para determinístico; a superfície de tools vai a
69; o `action:` entra na descrição do catálogo.

- [ ] **Step 5: Rodar os gates de documento**

Run: `python scripts/check_status_numbers.py --strict`
Expected: `0 divergencia(s).`

Run: `python scripts/check_vnext_claims.py`
Expected: `0 divergencia(s).`

Run: `python scripts/check_surface_lock.py`
Expected: `0`

- [ ] **Step 6: Commit**

```bash
git add docs/ CLAUDE.md README.md AGENTS.md
git commit -m "docs: executor deterministico entregue, regra 29 reescrita e o 111 corrigido para 112"
```

---

### Task 23: lotes da suíte e fechamento

**Files:**
- Modify: `tests/test_suite_batches.py`

- [ ] **Step 1: Encaixar os arquivos de teste novos nos lotes**

Os seis arquivos criados (`test_rules_action_field.py`,
`test_agentic_executor_authority.py`, `test_agentic_executor_claims.py`,
`test_agentic_executor_conflict.py`, `test_agentic_executor_ordering.py`,
`test_agentic_executor_run.py`) precisam cair em exatamente um lote da
constante `LOTES`.

Run: `python -m pytest tests/test_suite_batches.py -v`
Expected: FAIL nos invariantes de "todo arquivo cai em um lote" e "a soma fecha
com a coleta" — e é isso que o gate existe para pegar.

- [ ] **Step 2: Acrescentar aos lotes**

Os `test_agentic_executor_*` vão para o mesmo lote dos `test_agentic_*`
existentes; `test_rules_action_field.py` vai para o lote das regras.

- [ ] **Step 3: Rodar o gate dos lotes**

Run: `python -m pytest tests/test_suite_batches.py -v`
Expected: PASS nos três invariantes.

- [ ] **Step 4: Rodar a suíte em lotes, um por vez**

Run cada lote separadamente, conforme `LOTES`. Nunca a suíte inteira num
processo só — ela não sobrevive.

Expected: todos verdes. Anotar a soma e conferir com
`python -m pytest tests/ --collect-only -q 2>&1 | tail -1`.

- [ ] **Step 5: Rodar lint**

Run: `python -m ruff check sparkforge scripts tests`
Expected: sem apontamento.

**Este e o comando que o CI roda** (`.github/workflows/ci.yml:63`), e e o unico
criterio de lint desta entrega. `ruff format --check` **nao** entra: medido em
2026-09-08, ele reprova **396 arquivos que esta branch nao tocou** --
`sparkforge/facts/event_log.py` e `sparkforge/rules/engine.py` entre eles. A
causa e o pin sem teto (`ruff>=0.6` em `requirements.txt:21` e
`pyproject.toml:61`): o repositorio foi formatado com uma versao anterior, e a
0.16.0 formata diferente. Exigi-lo aqui reprovaria a entrega por mudanca de
ambiente, e roda-lo reformataria 396 arquivos alheios ao escopo.

**Achado registrado, e nao consertado aqui:** o STATUS publica que
`ruff format --check` fechou limpo em 2026-09-03. Isso deixou de valer com a
versao instalada hoje, e o pin sem teto e a razao. Fechar isso e por o teto no
pin ou reformatar o repositorio inteiro -- as duas coisas sao entrega propria.

- [ ] **Step 6: Commit**

```bash
git add tests/test_suite_batches.py
git commit -m "test: os seis arquivos do executor encaixados nos lotes, soma refeita"
```

---

## Auto-revisão do plano contra o spec

| Seção do spec | Tarefa que a implementa |
|---|---|
| §3 campo `action:` | 2, 3, e os lotes 4-10 |
| §3.2 vocabulário fechado, derivado | 1, e o gate na 2 |
| §3.3 `schema_version` em 1 | 2 (nenhuma tarefa sobe versão) |
| §3.4 `measurement_ref` separado de `authority` | 13 |
| §4 contradição direta e condicional | 15 detecta, 19 grava (`Contradiction` para a direta, `Objection` para a condicional) |
| §5.1 conflito, `confidence` por tabela, score não publicado | 14, 19 |
| §5.2 lastro, tier por host, escopo de versão | 12, 14 |
| §5.3 `Unknown` → `Experiment`, sem previsão de ganho, custo/tempo `unresolved` | 17, 19 |
| §5.4 ordem, restrição de eixo, ciclo `unresolved` | 16 |
| §6 `DebatePlan` e recusa nomeada | 18 |
| §7 CLI, MCP, L0, gravação, regra 27 | 19, 20, 21 |
| §8.1 fixtures | 19 — com o desvio D-1 declarado no topo |
| §8.2 gates | 2, 21, 22, 23 |
| §9 docs e regra 29 | 22 |
| §10 o que fica de fora | nenhuma tarefa cria `AgentRuntime`; o gate de chave desconhecida na 2 recusa `expected_gain` |
