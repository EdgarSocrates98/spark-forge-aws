---
sdd: 1
feature: CONFIG_OCA
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/CONFIG_OCA/design.md
  sha256: "563805997b5533902098cbd464fb0410351c7a306e36e72b619aff0cc3150310"
tasks:
  - id: T1
    files: [tests/test_config_declarado_existe.py, config/agentic-expansion.yaml]
    covers: [AC1, AC2]
    test: {path: tests/test_config_declarado_existe.py, name: test_todo_nome_declarado_resolve}
  - id: T2
    files: [tests/test_config_declarado_existe.py, config/subagents.yaml, subagents/intake-packager.md, tests/test_sf_stubs.py, docs/agentic-expansion.md, docs/operations-guide.md, docs/claims.lock.json, docs/harness/CODEINTEL-GAP.md]
    covers: [AC3, AC4, AC5]
    test: {path: tests/test_config_declarado_existe.py, name: test_o_registro_de_subagents_saiu_e_ninguem_o_le}
---

# CONFIG_OCA — plano

**Duas tarefas, e a separação é deliberada.** A T1 é a trava mais a remoção de sete nomes
num YAML. A T2 apaga 17 arquivos. Separadas, o `git revert` da T2 devolve os arquivos sem
levar a trava junto — que é exatamente o que o `rollback` do D3 promete para a lacuna U1.

## T1 — a trava, e as sete tools que não existem

> Fecha **AC1** e **AC2**.

### 1. Escrever o teste que falha

Crie `tests/test_config_declarado_existe.py`:

```python
"""Todo nome declarado num registro de `config/` aponta para algo que existe.

O SF_STUBS (`docs/sdd/SF_STUBS/`) apagou 19 agentes `sf-*` ocos, e dois incrementos
depois a mesma doenca foi encontrada uma camada abaixo, em `config/`: sete tools
declaradas que nao existem em `TOOLS`. Ela sobreviveu porque NADA impedia.

Este e o gate que impede. Ele nao afirma que aquelas sete sairam -- afirma que nada
declarado deixa de resolver, e por isso continua valendo para o proximo registro.

O mapa abaixo e declarado de proposito. Varrer todo YAML de `config/` e adivinhar quais
strings sao nomes a resolver produziria falso positivo em campo de politica
(`forbidden_by_default` nao e um agente), e um teste que precisa de lista de excecao
para nao mentir acaba desligado.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.adapters.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]

# As sete que a feature `docs/sdd/CONFIG_OCA/` removeu de `config/agentic-expansion.yaml`:
# nenhuma existia em `TOOLS`, e nenhuma tinha artefato coletavel definido.
TOOLS_QUE_SAIRAM = (
    "sparkforge_context_pack",
    "sparkforge_cost_estimate",
    "sparkforge_eval_golden_case",
    "sparkforge_lineage_extract",
    "sparkforge_offline_knowledge_search",
    "sparkforge_offline_knowledge_verify",
    "sparkforge_schema_compare",
)


def _agente_existe(nome: str) -> bool:
    return (ROOT / "agents" / f"{nome}.md").exists()


def _caminho_existe(rel: str) -> bool:
    return (ROOT / rel).exists()


def _tool_existe(nome: str) -> bool:
    return nome in TOOLS


# (registro, chave, resolvedor, o que o nome deveria apontar)
MAPA = (
    ("config/agentic-expansion.yaml", "agents", _agente_existe, "arquivo em agents/"),
    ("config/agentic-expansion.yaml", "knowledge", _caminho_existe, "caminho no repositorio"),
    (
        "config/agentic-expansion.yaml",
        "tools",
        _tool_existe,
        "entrada em sparkforge.adapters.tools.TOOLS",
    ),
)


def _declarados(registro: str, chave: str) -> list[str]:
    """Os nomes daquela chave, ou lista vazia se a chave nao existe.

    Chave ausente e resposta legitima: o D2 removeu o bloco `tools` inteiro em vez de
    deixar `tools: []`, porque chave vazia e convite a reencher sem criterio.
    """
    dados = yaml.safe_load((ROOT / registro).read_text(encoding="utf-8"))
    valor = (dados or {}).get(chave)
    return list(valor) if isinstance(valor, list) else []


def test_todo_nome_declarado_resolve():
    """AC2: a trava. A falha nomeia registro, chave e nome."""
    quebrados = []
    for registro, chave, resolve, alvo in MAPA:
        for nome in _declarados(registro, chave):
            if not resolve(nome):
                quebrados.append(f"{registro} :: {chave} :: {nome} (deveria ser {alvo})")
    assert not quebrados, (
        "nome declarado em config/ que nao resolve:\n  "
        + "\n  ".join(quebrados)
        + "\n\nColoque o artefato antes do nome, ou tire o nome. Ver "
        "docs/sdd/CONFIG_OCA/define.md."
    )


def test_toda_tool_declarada_existe():
    """AC1: as sete que sairam nao voltam, por nome.

    Esta asercao e o par NAO-VACUO do teste acima: com o bloco `tools` removido, aquele
    passa por ausencia. Este falha se qualquer uma das sete for reintroduzida em
    `config/`, tenha ou nao bloco.
    """
    texto = (ROOT / "config" / "agentic-expansion.yaml").read_text(encoding="utf-8")
    voltaram = [t for t in TOOLS_QUE_SAIRAM if t in texto]
    assert not voltaram, f"tool sem lastro de volta no registro: {voltaram}"
    assert all(t not in TOOLS for t in TOOLS_QUE_SAIRAM), (
        "uma das sete passou a existir de verdade: tire-a de TOOLS_QUE_SAIRAM e deixe o "
        "gate do declarado cuidar dela"
    )
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_config_declarado_existe.py -q
```

Falha esperada: **exit 1**, `2 failed`. O `test_todo_nome_declarado_resolve` lista as sete
linhas `config/agentic-expansion.yaml :: tools :: sparkforge_... (deveria ser entrada em
sparkforge.adapters.tools.TOOLS)`, e o `test_toda_tool_declarada_existe` acusa as sete
ainda no texto do registro. **Não é erro de coleta** — as duas falham por asserção.

### 3. Código mínimo

Em `config/agentic-expansion.yaml`, **apague a chave `tools` inteira**, com os sete nomes.
O arquivo é JSON dentro de um `.yaml`; preserve a formatação e as vírgulas do resto.

Não toque em `agents` nem em `knowledge`: medidos íntegros, 2 de 2 e 8 de 8.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_config_declarado_existe.py -q
```

Exit 0, 2 passed.

### 5. Gates vizinhos

```bash
python -m pytest tests/test_sf_stubs.py tests/test_criterio_de_dominio.py -q
python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py -q
python -m ruff check sparkforge scripts tests
```

Faça `git add` do arquivo novo antes de qualquer teste que confira a árvore versionada.

### 6. Commit

Mensagem:

```
test(config): refuse a name in config/ that points at nothing

`config/agentic-expansion.yaml` declared seven tools. None of them existed in
`TOOLS`, and none had a collectable artifact behind it. They are gone.

The gate that comes with them is the point. SF_STUBS removed nineteen hollow
`sf-*` agents, and two increments later the same disease was found one layer
down, because nothing stopped it. This test does not assert that those seven
left — it asserts that nothing declared fails to resolve, so it keeps working
for the next registry.

The map it walks is declared on purpose: sweeping every YAML under `config/` and
guessing which strings are names to resolve would flag policy fields, and a test
that needs an exception list to stay honest ends up switched off.
```

## T2 — os dezesseis subagents, a prosa e os registros

> Fecha **AC3**, **AC4** e **AC5**.

### 1. Escrever o teste que falha

Acrescente ao fim de `tests/test_config_declarado_existe.py`:

```python
SUBAGENTS_QUE_SAIRAM = (
    "benchmark-comparator",
    "cost-estimator",
    "cross-reviewer",
    "evidence-extractor",
    "experiment-designer",
    "handoff-preparer",
    "hypothesis-generator",
    "intake-packager",
    "lineage-impact-analyzer",
    "mutation-risk-checker",
    "regression-judge",
    "release-gate",
    "rollback-planner",
    "schema-compatibility-checker",
    "security-gate",
    "source-verifier",
)


def test_o_registro_de_subagents_saiu_e_ninguem_o_le():
    """AC3: os 16 stubs sairam, e a medida que autorizou continua valendo.

    Os contratos existiam -- 16 de 16 -- e eram BYTE-IDENTICOS abaixo de `## Contract`;
    a descricao de cada um era o proprio nome com o hifen trocado por espaco. Nenhum
    modulo de `sparkforge/`, `scripts/` ou `tests/` os lia, ao contrario de `skills/` e
    `agents/`, que varios leem. A lacuna U1 do define -- um consumidor FORA do
    repositorio -- nao e alcancavel daqui, e o rollback do D3 e a rede dela.
    """
    assert not (ROOT / "config" / "subagents.yaml").exists()
    assert not (ROOT / "subagents").exists()

    # E nenhum modulo passou a citar o que saiu.
    for diretorio in ("sparkforge", "scripts", "tests"):
        for arquivo in sorted((ROOT / diretorio).rglob("*.py")):
            if arquivo.name == "test_config_declarado_existe.py":
                continue
            texto = arquivo.read_text(encoding="utf-8")
            assert "config/subagents.yaml" not in texto, arquivo
            assert "subagents/" not in texto, arquivo
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_config_declarado_existe.py::test_o_registro_de_subagents_saiu_e_ninguem_o_le -q
```

Falha esperada: **exit 1**, `AssertionError` na primeira asserção — `config/subagents.yaml`
ainda existe.

### 3. Código mínimo

```bash
git rm config/subagents.yaml
git rm -r subagents/
```

E em `config/agentic-expansion.yaml`, apague a chave `subagents` inteira, com os dezesseis
nomes.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_config_declarado_existe.py -q
```

Exit 0, 3 passed.

### 5. A prosa (AC4)

Dois documentos prometem o que não há, e **os dois têm mais números errados do que os
desta feature**:

- `docs/agentic-expansion.md`, linha 21: *"A expansao adiciona dez agents permanentes,
  dezesseis subagents efemeros, seis ferramentas locais deterministicas, seis knowledge
  bases novas..."*. Medido hoje: **2** agentes (o SF_STUBS deixou dois), **0** subagents,
  **0** ferramentas, **8** documentos de knowledge. A linha está defasada desde o SF_STUBS,
  não só por esta feature. Reescreva-a com o que você **medir**, e cite os registros que
  continuam existindo (`config/agentic-expansion.yaml` e `config/teams-expansion.yaml`;
  `config/subagents.yaml` sai da frase).
- `docs/operations-guide.md`, linha 274: tire os *"16 subagents efemeros"* e os *"6 modulos
  de ferramentas locais"*, e tire `config/subagents.yaml` da lista de registros
  declarativos. O resto da frase, que já registra a recontagem do SF_STUBS, fica.

Depois, em `tests/test_sf_stubs.py`, acrescente `TOOLS_QUE_SAIRAM` e
`SUBAGENTS_QUE_SAIRAM` ao mecanismo que o `test_documento_vivo_nao_cita_o_que_saiu` já
percorre — **importe as duas tuplas de `tests/test_config_declarado_existe.py`** em vez de
recopiá-las, para não criar uma segunda fonte que diverge.

Rode:

```bash
python -m pytest tests/test_sf_stubs.py -q
```

Se ele acusar outro documento vivo citando um nome que saiu, **corrija o documento**, não a
lista.

### 6. Registros (AC5)

```bash
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

O segundo passa dos 2 minutos: segundo plano. Remedie **pela lista de ids que a saída
listar**, um por vez, nunca `--seed`, nunca por varredura. **Atenção, e é o caso desta
tarefa:** a remoção de 17 arquivos faz alegações de contagem e de bytes **caírem**, não
subirem. Cada valor vem de rodar a própria `proof.cmd` por `shlex.split`, nunca
`shell=True`. Regrave `docs/claims.lock.json` com
`json.dumps(..., ensure_ascii=False, indent=2) + "\n"` e **sem** `sort_keys`. Se a saída
vier vazia, não toque no lock.

Rode o gate com a árvore **no estado final**, depois de tudo apagado — rodá-lo antes dá o
número de um estado que já não existe.

### 7. Commit

Mensagem:

```
refactor(config): remove sixteen subagent contracts that nothing dispatched

The sixteen files existed, and that was all. Below `## Contract` they were
byte-identical, and each one's description was its own name with the hyphen
turned into a space. Nothing in `sparkforge/`, `scripts/` or `tests/` read the
registry or the contracts, while `skills/` and `agents/` are read by several
modules each.

`docs/agentic-expansion.md` promised ten permanent agents, sixteen ephemeral
subagents, six local tools and six knowledge bases. Measured today: two, zero,
zero and eight. The line had been stale since SF_STUBS, not only since this
change, and it now says what was counted.

A consumer outside this repository is the one thing the sweep cannot reach; it
is gap U1 in the define, and `git revert` of this commit is its net.
```

Acrescente os arquivos de registro ao `git add` se o gate de lastro tiver listado ids, e um
parágrafo à mensagem dizendo quais e com que valor medido.
