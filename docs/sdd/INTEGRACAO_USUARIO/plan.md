---
sdd: 1
feature: INTEGRACAO_USUARIO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/INTEGRACAO_USUARIO/design.md
  sha256: "40cebfd5feb8e14d1a51a00e0d679c9473facc5a23d5d7ad3aec7352c4bacb23"
tasks:
  - id: T1
    files: [tests/test_integrate.py, sparkforge/integrate/__init__.py, sparkforge/integrate/sources.py, pyproject.toml]
    covers: [AC1]
    test: {path: tests/test_integrate.py, name: test_wheel_embute_skills_e_agents}
  - id: T2
    files: [tests/test_integrate.py, sparkforge/integrate/render.py, scripts/sync_skills.py, tests/test_arvore_versionada.py]
    covers: [AC6]
    test: {path: tests/test_integrate.py, name: test_conteudo_e_o_da_renderizacao_do_sync_skills}
  - id: T3
    files: [tests/test_integrate.py, sparkforge/integrate/hosts.py, sparkforge/integrate/writer.py, sparkforge/integrate/__init__.py]
    covers: [AC7]
    test: {path: tests/test_integrate.py, name: test_manifesto_dry_run_e_idempotencia}
  - id: T4
    files: [tests/test_integrate.py, sparkforge/integrate/writer.py, sparkforge/integrate/__init__.py]
    covers: [AC3, AC5]
    test: {path: tests/test_integrate.py, name: test_integrate_devin_grava_global_e_preserva_mcp_existente}
  - id: T5
    files: [tests/test_integrate.py, sparkforge/integrate/writer.py, sparkforge/integrate/__init__.py]
    covers: [AC4]
    test: {path: tests/test_integrate.py, name: test_integrate_codex_grava_toml_e_preserva_config}
  - id: T6
    files: [tests/test_integrate.py, sparkforge/integrate/writer.py, sparkforge/integrate/__init__.py]
    covers: [AC8]
    test: {path: tests/test_integrate.py, name: test_detach_remove_so_o_proprio_e_recusa_o_editado}
  - id: T7
    files: [tests/test_integrate.py, sparkforge/integrate/claude.py, sparkforge/integrate/__init__.py]
    covers: [AC2]
    test: {path: tests/test_integrate.py, name: test_integrate_claude_monta_plugin_e_recusa_sem_cli}
  - id: T8
    files: [tests/test_integrate.py, sparkforge/integrate/conflict.py, sparkforge/integrate/__init__.py]
    covers: [AC9, AC10]
    test: {path: tests/test_integrate.py, name: test_conflito_com_copia_vendorizada_tres_escolhas}
  - id: T9
    files: [tests/test_integrate.py, sparkforge/integrate/__init__.py, sparkforge/doctor.py, sparkforge/adapters/_core.py, sparkforge/adapters/tools.py, sparkforge/adapters/cli.py, tests/test_doctor.py, tests/test_adapters_tools.py, tests/test_capability_parity.py, docs/guia/referencia/README.md, docs/guia/referencia/cli/README.md, docs/guia/referencia/cli/integrate.md, docs/guia/referencia/cli/detach.md, docs/guia/referencia/cli/doctor.md, docs/guia/referencia/tools/README.md, docs/guia/referencia/tools/sparkforge_doctor.md]
    covers: [AC11]
    test: {path: tests/test_integrate.py, name: test_doctor_informa_integracao_por_host}
  - id: T10
    files: [docs/guia/02-instalacao.md, docs/guia/03-cli.md, README.md, docs/superpowers/STATUS.md, docs/surface.lock.json, docs/claims.lock.json, docs/harness/CODEINTEL-GAP.md]
    covers: [AC12]
    test: {path: tests/test_surface_lock.py, name: TestOLockBateComAMedida::test_the_tool_catalogue_matches}
---

# INTEGRACAO_USUARIO — plano

Dez tarefas, na ordem de dependência. Todo o código abaixo foi executado numa cópia do
repositório, tarefa por tarefa: cada teste deu o vermelho descrito antes do código e o
verde depois, e o `ruff` passou em todas.

## Premissas do design

- **D1:** o renderizador sai de `scripts/sync_skills.py` e vai para
  `sparkforge/integrate/render.py`, junto com as tabelas de despacho. As funções que
  leem perfis passam a receber `agents_src`. A fachada carrega `render.py` **pelo
  caminho** (`importlib.util.spec_from_file_location`), e não por
  `import sparkforge...`. A razão: com instalação editável, o import pelo pacote acharia
  o `render.py` do disco dentro da visão `git archive` de
  `tests/test_arvore_versionada.py`, e o gate deixaria de conferir o renderizador
  commitado. Por isso `render.py` importa só a biblioteca padrão. O carregamento pelo
  caminho substitui o "põe ROOT no sys.path" do D1: não sobra nada no pacote que
  precise do `sys.path`.
- **D2:** a plataforma `codex` gera o TOML com `name`, `description` e
  `developer_instructions` por `json.dumps`, sem biblioteca de TOML. Os executores não
  vão para o Codex, porque não têm `description` e o TOML exige esse campo.
- **D3:** o bundle mora em `sparkforge/integrate/bundle/{skills,agents}`.
- **D4:** `hosts.host(nome, home=, windows=, appdata=)`. No Windows o diretório de
  config do Devin inteiro vai para `%APPDATA%\devin`, com os agents e o
  `mcp_config.json`. `~/.agents/skills` é compartilhado e recebe a renderização
  `devin`, a mesma do espelho `.agents/skills` do repositório.
- **D5:** o manifesto guarda caminhos relativos ao HOME em POSIX (absolutos quando
  ficam fora dele) e o sha256 de cada arquivo. Os donos de um arquivo compartilhado
  são os hosts que o listam.
- **D6–D7:** para JSON, só `mcpServers.sparkforge`. Para TOML, um bloco entre
  `# >>> sparkforge (gerenciado)` e `# <<< sparkforge`. Um `detach` devolve a config
  anterior.
- **D8:** o executor do `claude` é injetável (`runner`, `which`). A primeira vez faz
  `marketplace add` e `install`. Uma atualização com arquivo mudado faz
  `marketplace update` e `plugin update`. O `detach` faz `uninstall` e
  `marketplace remove`. Todos os flags foram conferidos no `--help` do Claude Code
  2.1.283.
- **D9:** `repositorio_fonte` quando o repositório tem `scripts/sync_skills.py`.
- **D10:** `integrate` e `detach` são só CLI, e entram em `ALLOWED_CLI_ONLY`.

## Arquivos que o plano toca fora do manifesto do design

A **T9** precisa de sete arquivos que o design não lista. Sem eles, o AC11 não
fecha:

- `sparkforge/adapters/_core.py`: é onde o `doctor` sonda o ambiente, e ele é também a
  tool MCP `sparkforge_doctor`.
- `sparkforge/adapters/tools.py`: a descrição da tool diz "nove checagens".
- `tests/test_doctor.py`: a lista `IDS` exata.
- `tests/test_adapters_tools.py`: faz `len(checks) == 9`.
- as páginas geradas `docs/guia/referencia/cli/doctor.md`,
  `docs/guia/referencia/tools/README.md` e
  `docs/guia/referencia/tools/sparkforge_doctor.md`.

O design precisa dessa emenda antes de o plano ir a `ready`.

## Comandos

- Teste de uma tarefa (a suíte inteira não roda num processo só):
  `python -m pytest tests/test_integrate.py::<nome> -q -p no:cacheprovider --basetemp=E:/sfpt_iu`.
- Lint de uma tarefa: `python -m ruff check <arquivos da tarefa>`.
- Por decisão do operador, cada tarefa roda **só o próprio teste e o ruff**. Os gates
  vizinhos de `docs/gates-por-mudanca.md` (`agent_or_skill`, `tool_or_verb`,
  `disk_read`, `dependency`, `status_numbers`, `claims`) rodam uma vez, na T10. Cada
  tarefa diz qual deles ela move.
- Todo teste aponta `HOME`, `USERPROFILE` e `APPDATA` para `tmp_path`, com uma fixture
  `autouse`, e injeta o `claude`. Nenhum toca o HOME real, e nenhum chama o binário.
- Arquivo `.py` novo precisa de `git add` antes de qualquer lote de teste. Ele também
  move alegações de tamanho de corpus do gate de lastro. A T10 as relê **à mão**, pela
  lista de ids do gate, e nunca com `--seed`.
- Todo arquivo é LF, com linhas de até 100 colunas. O código roda em Python >= 3.10:
  nada de `tomllib` em produção, e nada de `datetime.UTC`.

## T1 — o wheel embute `skills/` e `agents/`, e o pacote os acha

### 1. Escrever o teste que falha

`tests/test_integrate.py`, primeira versão:

```python
"""`sparkforge integrate` e `sparkforge detach`: a integracao por usuario.

Todo teste aponta HOME, USERPROFILE e APPDATA para `tmp_path` e injeta o executor
do `claude`: nenhum teste toca o HOME real nem chama o binario `claude` de verdade.
Spec: docs/sdd/INTEGRACAO_USUARIO/define.md.
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from sparkforge.integrate import sources

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _home_isolado(tmp_path, monkeypatch):
    casa = tmp_path / "home_padrao"
    casa.mkdir()
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.setenv("APPDATA", str(casa / "AppData" / "Roaming"))


def _relativos(base: Path) -> list[str]:
    return sorted(
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )


def test_wheel_embute_skills_e_agents(tmp_path):
    out = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.skip(f"`python -m build` indisponivel ou falhou: {build.stderr[-400:]}")
    (roda,) = sorted(out.glob("*.whl"))
    prefixo = "sparkforge/integrate/bundle/"
    with zipfile.ZipFile(roda) as wheel:
        nomes = wheel.namelist()
        assert f"{prefixo}skills/sdd-plan/SKILL.md" in nomes
        assert f"{prefixo}agents/sf-runtime-specialist.md" in nomes
        assert f"{prefixo}agents/executors/sf-judge.md" in nomes
        # `sparkforge/agents/` e pacote Python: o bundle nao pode cair nele.
        assert not [n for n in nomes if n.startswith("sparkforge/agents/") and n.endswith(".md")]
        destino = tmp_path / "instalado"
        wheel.extractall(destino, members=[n for n in nomes if n.startswith(prefixo)])

    # Sem repositorio: a raiz candidata nao tem pyproject.toml, e o pacote vence.
    sem_repo = tmp_path / "sem_repo"
    (sem_repo / "skills").mkdir(parents=True)
    (sem_repo / "agents").mkdir()
    bundle = destino / "sparkforge" / "integrate" / "bundle"
    raiz = sources.content_root(repo_root=sem_repo, bundle=bundle)
    assert raiz == bundle
    assert _relativos(sources.skills_dir(raiz)) == _relativos(ROOT / "skills")
    assert _relativos(sources.agents_dir(raiz)) == _relativos(ROOT / "agents")
    assert sources.skill_names(raiz) == sources.skill_names(ROOT)

    # Em desenvolvimento a raiz do repositorio vence; sem nenhuma das duas, recusa.
    assert sources.content_root() == ROOT
    with pytest.raises(sources.SourcesError):
        sources.content_root(repo_root=sem_repo, bundle=tmp_path / "vazio")
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_wheel_embute_skills_e_agents -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: erro de coleta com `ModuleNotFoundError: No module named
'sparkforge.integrate'`. O pacote ausente é a unidade sob teste.

### 3. Código mínimo

`sparkforge/integrate/__init__.py`:

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
```

`sparkforge/integrate/sources.py`:

```python
"""Onde moram `skills/` e `agents/` que a integracao grava (D3).

Duas origens, nesta ordem:

1. a raiz do repositorio, em desenvolvimento -- so vence com `pyproject.toml` e
   `skills/` presentes, para que um `site-packages/agents` de outro pacote nunca
   seja lido por engano;
2. `sparkforge/integrate/bundle/`, onde o `force-include` do wheel poe as duas
   pastas. Nao e `sparkforge/agents/`: esse nome ja e pacote Python.

Os parametros `repo_root` e `bundle` existem para o teste apontar as duas raizes
para `tmp_path`; o codigo de producao nunca os passa.
"""
from __future__ import annotations

from pathlib import Path

_AQUI = Path(__file__).resolve().parent
BUNDLE = _AQUI / "bundle"
REPO_ROOT = _AQUI.parents[1]


class SourcesError(RuntimeError):
    """`skills/` e `agents/` nao estao nem no repositorio nem no pacote."""


def _tem_conteudo(raiz: Path) -> bool:
    return (raiz / "skills").is_dir() and (raiz / "agents").is_dir()


def content_root(*, repo_root: Path | None = None, bundle: Path | None = None) -> Path:
    """A raiz que contem `skills/` e `agents/`."""
    repo = REPO_ROOT if repo_root is None else Path(repo_root)
    if (repo / "pyproject.toml").is_file() and _tem_conteudo(repo):
        return repo
    pacote = BUNDLE if bundle is None else Path(bundle)
    if _tem_conteudo(pacote):
        return pacote
    raise SourcesError(
        f"skills/ e agents/ nao encontrados em {repo} nem em {pacote}; "
        "reinstale o pacote: pip install --force-reinstall sparkforge-aws"
    )


def _raiz(root: Path | None) -> Path:
    return content_root() if root is None else Path(root)


def skills_dir(root: Path | None = None) -> Path:
    return _raiz(root) / "skills"


def agents_dir(root: Path | None = None) -> Path:
    return _raiz(root) / "agents"


def executors_dir(root: Path | None = None) -> Path:
    return agents_dir(root) / "executors"


def skill_names(root: Path | None = None) -> list[str]:
    return sorted(p.parent.name for p in skills_dir(root).glob("*/SKILL.md"))


def skill_files(root: Path | None = None) -> list[Path]:
    """Todo arquivo de toda skill, em qualquer profundidade."""
    base = skills_dir(root)
    return sorted(
        p for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.relative_to(base).parts
    )


def agent_files(root: Path | None = None) -> list[Path]:
    return sorted(p for p in agents_dir(root).glob("*.md") if p.is_file())


def executor_files(root: Path | None = None) -> list[Path]:
    return sorted(p for p in executors_dir(root).glob("*.md") if p.is_file())


__all__ = [
    "BUNDLE",
    "REPO_ROOT",
    "SourcesError",
    "agent_files",
    "agents_dir",
    "content_root",
    "executor_files",
    "executors_dir",
    "skill_files",
    "skill_names",
    "skills_dir",
]
```

Em `pyproject.toml`, troque

```toml
"knowledge" = "sparkforge/knowledge"
```

por

```toml
"knowledge" = "sparkforge/knowledge"
# `skills/` e `agents/` vao para `sparkforge/integrate/bundle/`, e nao para
# `sparkforge/agents/`, que ja e pacote Python. `sparkforge integrate` os le de la
# quando nao ha repositorio (docs/sdd/INTEGRACAO_USUARIO/design.md, D3).
"skills" = "sparkforge/integrate/bundle/skills"
"agents" = "sparkforge/integrate/bundle/agents"
```

e, no `include` do `[tool.hatch.build.targets.sdist]`, troque

```toml
    "knowledge",
    "README.md",
```

por

```toml
    "knowledge",
    "skills",
    "agents",
    "README.md",
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`. O teste constrói o wheel de verdade e leva uns 15 s.
Sem `python -m build` disponível ele sai `skipped`, e `skipped` não vale como verde.
Nesse caso rode `python -m pip install build` e repita.

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate tests/test_integrate.py`. Esta tarefa move
`disk_read` e `dependency` (`python scripts/verify_wheel.py` e
`python scripts/gen_requirements.py --check`), que rodam na T10. O `pyproject.toml`
não ganha dependência, só `force-include`.

### 6. Commit

`git add sparkforge/integrate tests/test_integrate.py pyproject.toml` e
`feat(integrate): ship skills and agents inside the wheel, and find them without the repo`

## T2 — um renderizador só, com a plataforma `codex`

### 1. Escrever o teste que falha

Em `tests/test_integrate.py`, o bloco de imports (do `from __future__` até a linha
antes de `ROOT = ...`) passa a ser:

```python
from __future__ import annotations

import ast
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from sparkforge.integrate import render, sources
```

e acrescente ao fim do arquivo:

```python
def _corpo_do_markdown(texto: str) -> str:
    fim = texto.index("\n---", 3)
    return texto[fim + len("\n---"):].lstrip("\r\n").replace("\r\n", "\n")


def test_conteudo_e_o_da_renderizacao_do_sync_skills():
    from scripts import sync_skills

    # Nao existe quinto renderizador: a fachada executa o MESMO arquivo, e nao
    # define mais nenhuma das duas funcoes.
    assert Path(sync_skills._render.__file__).resolve() == Path(render.__file__).resolve()
    fonte = (ROOT / "scripts" / "sync_skills.py").read_text(encoding="utf-8")
    definidas = {
        no.name for no in ast.walk(ast.parse(fonte)) if isinstance(no, ast.FunctionDef)
    }
    assert not {"render_agent", "_codex_toml", "_split_frontmatter"} & definidas

    agents_src = sources.agents_dir(ROOT)
    skills_root = sources.skills_dir(ROOT)
    espelhos_de_agent = {"claude": ".claude/agents", "devin": ".agents/agents"}
    for plataforma, espelho in espelhos_de_agent.items():
        for src in sources.agent_files(ROOT):
            esperado = (ROOT / espelho / src.name).read_bytes()
            assert render.render_agent_file(src, plataforma) == esperado, src
            assert sync_skills.render_agent(src.read_text(encoding="utf-8"), plataforma).encode(
                "utf-8"
            ) == render.render_agent_file(src, plataforma)
    for src in sources.agent_files(ROOT):
        copilot = ROOT / ".github" / "agents" / f"{src.stem}.agent.md"
        assert render.render_agent_file(src, "github") == copilot.read_bytes(), src
    for plataforma, espelho in {"claude": ".claude/skills", "devin": ".agents/skills"}.items():
        for src in sources.skill_files(ROOT):
            destino = ROOT / espelho / src.relative_to(skills_root)
            gravado = render.render_skill_file(
                src, skills_root, plataforma, agents_src=agents_src
            )
            assert gravado == sync_skills.rendered_skill_bytes(src, destino), src
            assert gravado == destino.read_bytes(), src

    # Codex: TOML com os tres campos, e o corpo e o markdown depois do frontmatter.
    tomllib = pytest.importorskip("tomllib")
    for src in sources.agent_files(ROOT):
        texto = src.read_text(encoding="utf-8")
        dados = tomllib.loads(render.render_agent_file(src, "codex").decode("utf-8"))
        assert set(dados) == {"name", "description", "developer_instructions"}
        assert dados["name"] == src.stem
        assert dados["description"] in texto
        assert dados["developer_instructions"] == _corpo_do_markdown(texto)
    exemplo = sources.skill_files(ROOT)[0]
    assert render.render_skill_file(
        exemplo, skills_root, "codex", agents_src=agents_src
    ) == exemplo.read_bytes()
    with pytest.raises(ValueError, match="description"):
        render.render_agent("---\nname: x\n---\ncorpo\n", "codex")
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_conteudo_e_o_da_renderizacao_do_sync_skills -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: erro de coleta com `ImportError: cannot import name 'render' from
'sparkforge.integrate'`.

### 3. Código mínimo

`sparkforge/integrate/render.py`, inteiro. Da linha 22 até o fim de
`_frontmatter_scalar`, o texto é o de `scripts/sync_skills.py`, da linha 70 à 484,
**sem mudança**, exceto por dois trechos: a constante `PLATFORMS` (com o comentário
acima dela) e o desvio `codex` em `render_agent`. O que vem depois de
`_frontmatter_scalar` é novo.

```python
"""O renderizador por plataforma de skills e agents -- um so, para os espelhos do
repositorio (`scripts/sync_skills.py`) e para a integracao por usuario
(`sparkforge integrate`).

Movido de `scripts/sync_skills.py` pela feature INTEGRACAO_USUARIO (D1): o texto
das decisoes abaixo e o de la, sem mudanca. O que mudou e so a assinatura das
funcoes que leem perfis -- recebem o diretorio de agents por parametro, porque o
pacote instalado nao tem `agents/` na raiz do repositorio -- e a plataforma
`codex` (D2).

Este modulo importa so a biblioteca padrao. `scripts/sync_skills.py` o carrega
PELO CAMINHO do arquivo, e nao pelo pacote instalado, para que
`tests/test_arvore_versionada.py` confira o espelho commitado contra o renderizador
commitado; um import de `sparkforge.*` aqui quebraria esse carregamento.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# --------------------------------------------------------------------------
# Renderizacao por plataforma
# --------------------------------------------------------------------------
# Fundamento medido: knowledge/devin/agents-and-subagents.md (retrieved
# 2026-08-04). Desenho: D-1, D-2 e D-3 de
# docs/superpowers/specs/2026-08-04-sparkforge-devin-subagentes-design.md.

# `claude` e `github` recebem o arquivo INALTERADO. Nao ha round-trip de YAML
# em caminho nenhum: parsear e re-serializar reordenaria as chaves e produziria
# diff onde nao houve mudanca, e o gate viraria ruido.
PASSTHROUGH_PLATFORMS = frozenset({"claude", "github"})
# `codex` (D2): o perfil vira o TOML de `~/.codex/agents/` -- `name`, `description`
# e `developer_instructions` (learn.chatgpt.com/docs/agent-configuration/subagents,
# lido em 2026-09-25). A skill do Codex e a mesma `SKILL.md`, sem campo a mais.
PLATFORMS = PASSTHROUGH_PLATFORMS | {"devin", "codex"}

# Campos que o espelho do Devin NAO leva.
#
# `tools:` -- o Devin aceita o campo ("Claude Code agent files use `tools`
# instead of `allowed-tools`[...] Both formats are supported automatically"),
# mas o MAPEAMENTO DE VALORES nao esta documentado em lugar nenhum: `Bash` ->
# `exec`? `Write` -> `write`? Os nomes de tool do Devin sao `read`, `edit`,
# `grep`, `glob`, `exec` (cli/reference/permissions.md). Chute em campo de
# PERMISSAO concede ou nega errado, e nos dois sentidos o erro e caro. Omitido,
# o subagente herda o que o harness da -- que e o comportamento que a propria
# documentacao descreve como default ("all tools"). Veto V-DV-8.
DEVIN_DROPPED_KEYS = frozenset({"tools"})

# NENHUM caminho aqui ACRESCENTA `model:`, e isso e deliberado (D-3):
#   1. o default do subagente "is not a fixed model name -- it resolves through
#      a router at spawn time";
#   2. o admin da organizacao sobrescreve pela setting "Default subagent
#      model", inclusive com a opcao *None*, que desliga o despacho por
#      completo;
#   3. o identificador literal e `swe-1-7`, com HIFEN -- a doc interna que
#      motivou esta fase errava com ponto, e nenhuma pagina do CLI documenta
#      esse literal como valor aceito de frontmatter (vetos V-DV-2 e V-DV-3).
# Escrever `model:` seria fingir controle sobre o que o harness decide. Quem
# vier depois vai querer "completar" o frontmatter: nao complete sem medir.

# Nomes que o Devin ja usa para os seus dois perfis embutidos. A tabela de
# frontmatter da fonte diz, sobre `name`: "Identifier for the profile (must not
# conflict with built-in profiles)", e a tabela de perfis nomeia os dois --
# knowledge/devin/agents-and-subagents.md, secao 1 (retrieved 2026-08-04).
#
# A fonte PROIBE a colisao e NAO diz o que acontece quando ela ocorre. Pular com
# aviso, sobrescrever o built-in e recusar a sessao sao todos plausiveis, e
# nenhum esta escrito. Por isso o gate recusa o nome em vez de supor qual vale:
# supor comportamento nao documentado e a mesma familia de chute que o V-DV-8
# recusou em `tools:`, agora num campo de IDENTIDADE -- e um perfil que o Devin
# ignore em silencio e pior que um que ele recuse, porque o metodo some sem
# alarme e o built-in `subagent_general` (acesso total, nenhum `## Nao faz`)
# atende no lugar dele.
DEVIN_BUILTIN_PROFILE_NAMES = frozenset({"subagent_explore", "subagent_general"})

_FRONTMATTER_FENCE = "---"
_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:")


def _split_frontmatter(text: str) -> tuple[list[str], list[str], list[str]] | None:
    """Fatia o texto em (abertura, corpo do frontmatter, resto).

    Trabalha em linhas com o fim de linha preservado (`keepends=True`): o gate
    compara byte a byte, entao normalizar CRLF para LF produziria DIVERGENTE em
    toda regeneracao numa arvore com `autocrlf`.

    Devolve `None` quando nao ha frontmatter delimitado -- ai o arquivo sai
    inalterado, em vez de o renderizador adivinhar onde o cabecalho termina.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != _FRONTMATTER_FENCE:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == _FRONTMATTER_FENCE:
            return lines[:1], lines[1:index], lines[index:]
    return None


def _drop_frontmatter_keys(front: list[str], keys: frozenset[str]) -> list[str]:
    """Remove chaves de topo do frontmatter, com as continuacoes delas.

    A continuacao importa porque o campo tem duas formas possiveis:

        tools: Read, Grep, Glob        # inline -- e a forma dos treze perfis hoje
        tools:                         # bloco
          - Read
          - Grep

    Apagar so a linha `tools:` na forma de bloco deixaria `  - Read` orfao e
    quebraria o YAML do espelho. A remocao para na proxima linha nao indentada,
    para nao engolir a chave seguinte -- `skills:` vem logo depois e tambem e
    lista indentada.
    """
    kept: list[str] = []
    dropping = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if not dropping:
                kept.append(line)
            continue
        match = _TOP_LEVEL_KEY.match(content)
        dropping = bool(match) and match.group(1) in keys
        if not dropping:
            kept.append(line)
    return kept


def render_agent(text: str, platform: str) -> str:
    """Devolve o conteudo do perfil no formato que `platform` le.

    `claude` e `github` recebem o texto identico -- o espelho deles nao mudou
    nesta fase, e um renderizador que mexesse em todos os alvos quebraria o
    Copilot sem ninguem pedir.
    """
    if platform not in PLATFORMS:
        raise ValueError(
            f"plataforma desconhecida: {platform!r}; conhecidas: {sorted(PLATFORMS)}"
        )
    if platform in PASSTHROUGH_PLATFORMS:
        return text
    if platform == "codex":
        return _codex_toml(text)

    parsed = _split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed

    kept = _drop_frontmatter_keys(front, DEVIN_DROPPED_KEYS)
    if kept == front:
        return text
    return "".join(opening + kept + rest)


# --------------------------------------------------------------------------
# Skills que despacham
# --------------------------------------------------------------------------
# `.agents/skills/<name>/SKILL.md` e caminho de descoberta NATIVO do Devin, nao
# convencao deste repositorio, e o frontmatter de skill aceita `subagent`
# (boolean, default `false`) e `agent` (string, default nenhum) -- tabela de
# knowledge/devin/agents-and-subagents.md secao 8. Desenho: D-5 e D-6.
#
# So o espelho do Devin recebe os campos. `.claude/skills/` continua passthrough
# byte a byte: o Claude Code nao le `subagent:`, e escrever la seria publicar
# campo que ninguem consome.

SKILL_FILENAME = "SKILL.md"

# Campos que a renderizacao do Devin CONTROLA numa skill. Sao removidos antes de
# reinseridos, e nao so acrescentados: assim uma skill que deixou de despachar
# perde o campo no espelho, e um `subagent: true` posto a mao num espelho volta
# a divergir do que o tradutor produz. Acrescentar sem remover deixaria os dois
# casos passarem calados.
DEVIN_SKILL_DISPATCH_KEYS = frozenset({"subagent", "agent"})

# D-6: despacha quem e investigacao fechada -- o subagente le artefato, julga
# contra o catalogo, e devolve texto que o pai resume. Nao despacha quem dirige
# o loop, quem orquestra outras skills, ou quem precisa de uma decisao que so
# uma pessoa tem.
#
# A assimetria que decide os casos duvidosos: uma skill despachavel a mais que
# precisasse perguntar falha MUDA -- `ask_user_question` e sempre negado a
# subagente (veto V-DV-10), entao ela inventa a resposta ou para sem dizer por
# que. Uma skill despachavel a menos custa contexto do pai, e mais nada. Na
# duvida, nao despacha.
DISPATCHABLE_SKILLS = {
    "analyze-batch-loop": "extrai o loop do codigo e julga; a saida e relatorio",
    "analyze-library-call-graph": "varre a biblioteca e devolve o grafo; leitura fechada",
    "analyze-spark-plan": "interpreta um plano fisico ja salvo; nao pede nada a ninguem",
    "analyze-spark-ui": "coleta e julga o event log de um run identificado no pedido",
    "diagnose-data-skew": "cruza SF-UI-001 com SF-UI-002 sobre o event log que ela mesma coleta",
    "diagnose-oom": "classifica o OOM por `heap_oom_in_log`; discriminador esta no artefato",
    "optimize-parquet-layout": "junta listagem, plano e catalogo, todos coletaveis so lendo",
    "optimize-pyspark-code": "mesma forma de `review-pyspark-pr`: extrai, julga, propoe diff",
    "review-data-validation": "revisa a validacao declarada no codigo e devolve achados",
    "review-emr-cluster": "revisa a definicao do cluster que ja esta em disco",
    "review-emr-eks": "revisa o job run do emr-containers que ja esta em disco",
    "review-glue-terraform": "revisa o .tf que ja esta em disco",
    "review-pyspark-pr": "revisa um diff fechado e classifica risco",
    "analyze-functional-rules": "Especialista de dominio; despacho por coordenador",
    # As tres de Glue 6 que LEEM e julgam, sem decisao de terceiro no caminho:
    # os artefatos (codigo, .tf, requirements, .jar) ja estao em disco, e o
    # veredito sai do catalogo e da matriz.
    "migrate-glue-6": "extrai a arvore do job e julga degrau a degrau; leitura fechada",
    "spark4-compatibility": "julga o codigo e os pins contra a fronteira do Spark 4",
    "lakeformation-fgac-guard": "correlaciona FGAC e classpath no .tf que ja esta em disco",
    # Le as quatro matrizes de `knowledge/` e devolve numero com fonte. Nao ha
    # artefato do operador para faltar, nao ha decisao de terceiro no caminho, e
    # nenhum Finding nasce dela -- a leitura e fechada por construcao.
    "compare-releases": (
        "le as quatro matrizes de versao e devolve o diff com o eixo declarado; "
        "nao le artefato do operador e nao julga"
    ),
}

NON_DISPATCHABLE_SKILLS = {
    # Ela COLETA da AWS ao vivo, e as quatro coletas do procedimento pedem
    # credencial e permissao de leitura sobre governanca de terceiro
    # (`ListPermissions`, `GetDataLakeSettings`, `SimulatePrincipalPolicy`).
    # Alem disso, TODA recomendacao dela e mudanca de postura de seguranca, e
    # tres delas -- boundary, service control policy, desregistrar localizacao --
    # tem raio maior que o do job. Despachar quem nao pode perguntar seria
    # exatamente o caso que este registro existe para barrar.
    "diagnose-lakeformation-access": (
        "coleta da AWS ao vivo e recomenda mudanca de permissao; a decisao sobe "
        "a quem responde pela governanca, e um subagente nao pode perguntar"
    ),
    # Ela e o DRIVER do debate: conduz o laco next -> submit e, idealmente,
    # despacha um subagente POR LADO. Despacha-la inteira para um subagente
    # juntaria os dois lados num contexto so -- o lado A leria o raciocinio
    # privado do B --, e o `submit` grava no blackboard do case (mutacao local).
    "run-debate": (
        "conduz o laco do debate no agente pai e despacha os lados; despachada "
        "inteira, os dois lados dividiriam um contexto e gravariam no case"
    ),
    # O lado do host do L3 do §15: roda git na arvore do operador e para antes
    # de `git push` e de `gh pr create`. As duas paradas pedem confirmacao
    # humana, e um subagente despachado nao tem a quem perguntar.
    "propose-change-pr": (
        "roda git/gh na arvore do operador e para para confirmacao humana antes de "
        "push e de abrir o PR; despachada, ninguem estaria la para confirmar"
    ),
    "tool-specialist-routing": "valida roteamento no agente atual",
    # As duas que dirigem o loop. Um subagente nao herda o historico do pai e,
    # por default, nao gera subagente proprio (`max-nesting`): despachar quem
    # orquestra e perder justamente a orquestracao.
    "sparkforge-diagnose": (
        "abre o case e roteia. Despachar joga o ciclo de vida do case para um "
        "contexto que nao volta -- e o case e o que faz a investigacao atravessar "
        "sessoes e ferramentas"
    ),
    "glue-incremental-performance-architect": (
        "orquestra as skills especializadas por `next-step` e le "
        "PROMPT_INICIAL_MESTRE.md; subagente nao gera subagente por default"
    ),
    # As que precisam de uma decisao que nao esta no repositorio.
    "iceberg-v3-readiness": (
        "subir `format-version` e decisao de IDA, e a skill exige o inventario de "
        "consumidores -- que e conhecimento da organizacao, escrito por uma pessoa, "
        "nao derivavel de artefato. Dentro de subagente a pergunta 'quem mais le "
        "esta tabela?' e inalcancavel, e a resposta errada quebra o consumidor dias "
        "depois"
    ),
    "optimize-iceberg-table": (
        "`expire_snapshots` e `remove_orphan_files` nao tem desfazer, e a propria "
        "skill exige que a retencao venha do dono dos dados. Dentro de subagente "
        "essa confirmacao e inalcancavel"
    ),
    "optimize-latest-per-key": (
        "a secao `Perguntas que o extrator nao faz por voce` sao quatro perguntas "
        "de semantica de negocio -- desempate, timezone, correcao retroativa"
    ),
    "design-incremental-processing": (
        "o contrato de saida tem dezesseis campos de desenho que nenhum extrator "
        "preenche; a propria skill os chama de perguntas"
    ),
    # As que dependem de evidencia que o pai ja acumulou, ou de uma execucao nova.
    "benchmark-pyspark-job": (
        "o passo 2 e `aplique a mudanca` entre as duas coletas: exige um run novo "
        "e o id dele, que so aparece depois de alguem publicar a mudanca"
    ),
    "optimize-variable-volume-job": (
        "classificar execucoes por perfil parte do volume observado no workload, "
        "e compara N runs que o operador escolhe"
    ),
    "tune-glue-job": (
        "o passo 1 exige baseline ja provado por `analyze-spark-ui`, `diagnose-oom` "
        "e `diagnose-data-skew`; subagente nao herda o historico do pai e teria de "
        "reconstruir a evidencia que motivou a chamada"
    ),
    "design-data-architecture": "Especialista de dominio; despacho por coordenador",
    "design-s3-data-lake": "Especialista de dominio; despacho por coordenador",
    "review-terraform-data-platform": "Especialista de dominio; despacho por coordenador",
    # As duas que mutam infraestrutura AWS ao vivo: procedimento operacional,
    # nao gatilho do motor. Rodam `aws s3tables create-*` e `aws s3api put-*`,
    # e a fronteira `## Nao faz` exige confirmacao explicita do operador para
    # cada comando de escrita -- inalcancavel dentro de subagente (V-DV-10).
    "provision-s3-tables-table": (
        "cria table bucket, namespace, tabela e catalog integration S3 Tables "
        "via `aws s3tables`/`aws glue` ao vivo; a fronteira `## Nao faz` exige "
        "confirmacao do operador por comando de escrita, inalcancavel em subagente"
    ),
    "harden-s3-bucket": (
        "executa `put-bucket-policy`, `put-bucket-encryption`, `create-detector` "
        "ao vivo; a fronteira `## Nao faz` exige confirmacao do operador por "
        "comando de escrita, inalcancavel em subagente"
    ),
    # As nove skills oficiais AWS adaptadas (aws/agent-toolkit-for-aws, commit
    # 10b28af8): procedimento operacional AWS, nao gatilho do motor SparkForge.
    # Sao referencia de servico (storage, database, serverless, IAM, observability,
    # billing, messaging, security, SDK Python) e podem mutar infra ao vivo.
    # A fronteira `## Nao faz` de cada uma exige confirmacao do operador por
    # comando de escrita -- inalcancavel em subagente (V-DV-10).
    "aws-storage": (
        "referencia de storage AWS (S3, EFS, FSx, EBS); pode mutar configuracao "
        "de bucket e lifecycle ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-database": (
        "roteia para skill de database AWS (Aurora, RDS, DynamoDB, etc); pode "
        "mutar configuracao de instancia ao vivo, fronteira exige confirmacao"
    ),
    "aws-serverless": (
        "procedimento de Lambda, Step Functions, EventBridge; pode mutar funcao "
        "e state machine ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-iam": (
        "referencia de IAM (policies, roles, trust); pode mutar policy e role "
        "ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-observability": (
        "procedimento de CloudWatch, X-Ray, CloudTrail; pode mutar alarme, "
        "dashboard e trail ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-billing-and-cost-management": (
        "analise de custo AWS (CUR, Savings Plans); pode mutar budget e alerta "
        "ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-messaging-and-streaming": (
        "referencia de SQS, SNS, EventBridge, Kinesis, MSK; pode mutar fila, "
        "topico e stream ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-security": (
        "procedimento de Security Hub, GuardDuty, Inspector; pode mutar finding "
        "e detector ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-sdk-python-usage": (
        "padroes de boto3/botocore; e referencia de uso de SDK, nao muta infra "
        "por si, mas pode executar chamadas AWS se o operador pedir"
    ),
    # As seis fases do SDD proprio (feature SDD_SKILLS, 2026-09-16). Dirigem a
    # sessao e o operador, nao investigam artefato fechado (D-6): explore,
    # define, design e plan fazem uma pergunta por vez e esperam a aprovacao;
    # build despacha um subagente por tarefa e dois revisores, e subagente nao
    # gera subagente por default; ship para antes de push e de PR.
    "sdd-explore": (
        "pergunta uma coisa por vez e espera o operador escolher a abordagem; "
        "despachada, ninguem estaria la para responder"
    ),
    "sdd-define": (
        "fecha criterios e hipotese com o operador, uma pergunta por vez; "
        "subagente nao pode perguntar (V-DV-10)"
    ),
    "sdd-design": (
        "apresenta o desenho por partes e espera aprovacao de cada uma; "
        "subagente nao pode perguntar"
    ),
    "sdd-plan": (
        "o plano passa pela leitura do operador antes de ficar ready; "
        "subagente nao pode perguntar"
    ),
    "sdd-build": (
        "despacha um subagente por tarefa e dois revisores; despachada inteira, "
        "perderia a orquestracao, porque subagente nao gera subagente por default"
    ),
    "sdd-ship": (
        "para antes de git push, merge e gh pr create para a escolha do operador; "
        "despachada, ninguem estaria la para escolher"
    ),
}

SKILL_DISPATCH_REASON = {**DISPATCHABLE_SKILLS, **NON_DISPATCHABLE_SKILLS}

_LIST_ITEM = re.compile(r"^\s*-\s+(.*)$")


def _frontmatter_list(front: list[str], key: str) -> list[str]:
    """Le uma lista do frontmatter, nas duas formas que o corpus usa.

        skills:          |  rule_areas: [SF-EMR, SF-PY]
          - review-x     |
          - review-y     |

    A forma inline existe hoje em `rule_areas:` e `executors:`; se alguem
    escrever `skills:` assim, um leitor que so entendesse blocos devolveria
    lista vazia -- e lista vazia aqui vira "nenhum coordenador declara esta
    skill", que e silencio, nao erro.
    """
    values: list[str] = []
    collecting = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if collecting:
                item = _LIST_ITEM.match(content)
                if item:
                    values.append(item.group(1).strip().strip("'\""))
            continue
        match = _TOP_LEVEL_KEY.match(content)
        collecting = False
        if match and match.group(1) == key:
            inline = content.split(":", 1)[1].strip()
            if not inline:
                collecting = True
            elif inline.startswith("[") and inline.endswith("]"):
                values.extend(
                    part.strip().strip("'\"")
                    for part in inline[1:-1].split(",")
                    if part.strip()
                )
            else:
                values.append(inline.strip("'\""))
    return values


def _frontmatter_scalar(front: list[str], key: str) -> str | None:
    """Le um escalar de topo do frontmatter, ou `None` se ele nao estiver la.

    Irmao de `_frontmatter_list`, e pela mesma razao: nao ha round-trip de YAML
    em caminho nenhum deste arquivo, entao a leitura tambem e por linha.
    """
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            continue
        match = _TOP_LEVEL_KEY.match(content)
        if match and match.group(1) == key:
            return content.split(":", 1)[1].strip().strip("'\"") or None
    return None


def _toml_string(valor: str) -> str:
    """String basica de TOML.

    O escape do JSON e um subconjunto do escape de string basica do TOML, entao
    `json.dumps` serve sem depender de biblioteca de TOML -- que o Python 3.10 nao
    tem, e que o projeto nao traz como dependencia.
    """
    return json.dumps(valor, ensure_ascii=False)


def _codex_toml(text: str) -> str:
    """O perfil no formato de `~/.codex/agents/<nome>.toml`.

    `developer_instructions` e o corpo do markdown depois do frontmatter, com LF.
    Perfil sem `name` ou sem `description` levanta: o Codex exige os dois, e
    inventar a descricao publicaria um papel que ninguem escreveu.
    """
    parsed = _split_frontmatter(text)
    if parsed is None:
        raise ValueError("perfil sem frontmatter nao vira agent do Codex")
    _, front, rest = parsed
    name = _frontmatter_scalar(front, "name")
    description = _frontmatter_scalar(front, "description")
    if not name or not description:
        raise ValueError(
            f"perfil sem `name` ou sem `description` nao vira agent do Codex: {name!r}"
        )
    corpo = "".join(rest[1:]).replace("\r\n", "\n").lstrip("\n")
    return (
        f"name = {_toml_string(name)}\n"
        f"description = {_toml_string(description)}\n"
        f"developer_instructions = {_toml_string(corpo)}\n"
    )


def _agent_files(agents_src: Path) -> list[Path]:
    return sorted(p for p in Path(agents_src).glob("*.md") if p.is_file())


def coordinators_by_skill(agents_src: Path) -> dict[str, tuple[str, ...]]:
    """A relacao skill -> coordenadores, DERIVADA do `skills:` de cada perfil.

    D-5: nao existe segunda lista. Cada coordenador ja declara as skills que
    coordena, e essa declaracao ja e testada por `test_agent_coverage`. Manter
    uma tabela paralela `skill -> agente` seria a familia de defeito que a Fase
    5c achou nos dois `EXTRACTORS` mantidos a mao: uma cresce, a outra nao, e o
    desacordo e mudo.
    """
    relation: dict[str, list[str]] = {}
    for path in _agent_files(agents_src):
        parsed = _split_frontmatter(path.read_bytes().decode("utf-8"))
        if parsed is None:
            continue
        for skill in _frontmatter_list(parsed[1], "skills"):
            relation.setdefault(skill, []).append(path.stem)
    return {skill: tuple(sorted(names)) for skill, names in sorted(relation.items())}


def orchestrator_profiles(agents_src: Path) -> frozenset[str]:
    """Perfis que NAO sao destino de despacho de investigacao fechada.

    Derivado, nao mantido a mao: e o conjunto dos perfis de `agents/*.md` cuja
    skill HOMONIMA este modulo ja declara nao-despachavel. Hoje ele tem
    exatamente um elemento -- `glue-incremental-performance-architect` --, e a
    razao escrita ao lado dela e a mesma que vale para o perfil: ela "orquestra
    as skills especializadas por `next-step`", e subagente nao gera subagente por
    default. Se um dia a skill virar despachavel, a exclusao some sozinha.
    """
    return frozenset(
        name
        for name in NON_DISPATCHABLE_SKILLS
        if (Path(agents_src) / f"{name}.md").is_file()
    )


def agent_for_skill(name: str, agents_src: Path) -> str | None:
    """O perfil que a skill `name` nomeia em `agent:`, ou `None`.

    Skill declarada por mais de um coordenador NAO declara `agent:`, e o Devin
    escolhe o perfil: ordem alfabetica nao e criterio de competencia. Declarante
    unico que e o orquestrador tambem nao: publicar aquilo seria propriedade
    mecanica com cara de decisao (`diagnose-oom`, 2026-08-04). A historia inteira
    esta no `git log` de `scripts/sync_skills.py`.
    """
    coordinators = coordinators_by_skill(agents_src).get(name, ())
    if len(coordinators) != 1:
        return None
    if coordinators[0] in orchestrator_profiles(agents_src):
        return None
    return coordinators[0]


def _newline_of(lines: list[str]) -> str:
    """O fim de linha que o arquivo usa, para a linha inserida usar o mesmo.

    Misturar LF e CRLF dentro do mesmo frontmatter faria o espelho divergir a
    cada regeneracao numa arvore com `autocrlf`.
    """
    for line in reversed(lines):
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def render_skill(text: str, platform: str, *, name: str, agents_src: Path) -> str:
    """Devolve a skill `name` no formato que `platform` le.

    So o Devin recebe `subagent:`/`agent:`. Os campos entram no FIM do
    frontmatter, imediatamente antes da cerca de fechamento: e a unica posicao
    que nao depende de onde as chaves existentes estao, e a que nao pode cair
    dentro de uma lista indentada. O Codex le a `SKILL.md` como ela e.
    """
    if platform not in PLATFORMS:
        raise ValueError(
            f"plataforma desconhecida: {platform!r}; conhecidas: {sorted(PLATFORMS)}"
        )
    if name not in SKILL_DISPATCH_REASON:
        raise ValueError(
            f"skill sem decisao de despacho registrada: {name!r}. Declare em "
            "DISPATCHABLE_SKILLS ou em NON_DISPATCHABLE_SKILLS, com a razao ao "
            "lado -- o default silencioso seria publicar a skill sem ninguem ter "
            "decidido se ela pode rodar sem poder perguntar."
        )
    if platform in PASSTHROUGH_PLATFORMS or platform == "codex":
        return text

    parsed = _split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed

    kept = _drop_frontmatter_keys(front, DEVIN_SKILL_DISPATCH_KEYS)
    added: list[str] = []
    if name in DISPATCHABLE_SKILLS:
        newline = _newline_of(kept or opening)
        added.append(f"subagent: true{newline}")
        agent = agent_for_skill(name, agents_src)
        if agent is not None:
            added.append(f"agent: {agent}{newline}")

    if kept == front and not added:
        return text
    return "".join(opening + kept + added + rest)


def render_skill_file(
    src: Path, skills_root: Path, platform: str, *, agents_src: Path
) -> bytes:
    """Os bytes de um arquivo de skill para `platform`.

    O nome da skill e o NOME DO DIRETORIO sob `skills_root`, o mesmo identificador
    que o Devin usa e que os coordenadores escrevem em `skills:`. Arquivo que nao
    e `SKILL.md` sai como esta, sem passar por `decode`.
    """
    data = Path(src).read_bytes()
    if Path(src).name != SKILL_FILENAME:
        return data
    name = Path(src).relative_to(skills_root).parts[0]
    rendered = render_skill(data.decode("utf-8"), platform, name=name, agents_src=agents_src)
    return rendered.encode("utf-8")


def render_agent_file(src: Path, platform: str) -> bytes:
    """Os bytes de um perfil para `platform`.

    Le e escreve em bytes de proposito: `read_text` aplicaria newline universal e
    um espelho com CRLF passaria a comparar igual a uma fonte LF.
    """
    text = Path(src).read_bytes().decode("utf-8")
    return render_agent(text, platform).encode("utf-8")


__all__ = [
    "DEVIN_BUILTIN_PROFILE_NAMES",
    "DEVIN_DROPPED_KEYS",
    "DEVIN_SKILL_DISPATCH_KEYS",
    "DISPATCHABLE_SKILLS",
    "NON_DISPATCHABLE_SKILLS",
    "PASSTHROUGH_PLATFORMS",
    "PLATFORMS",
    "SKILL_DISPATCH_REASON",
    "SKILL_FILENAME",
    "agent_for_skill",
    "coordinators_by_skill",
    "orchestrator_profiles",
    "render_agent",
    "render_agent_file",
    "render_skill",
    "render_skill_file",
]
```

`scripts/sync_skills.py` vira fachada. Primeiro troque os imports

```python
import argparse
import re
from pathlib import Path
```

por

```python
import argparse
import importlib.util
import sys
from pathlib import Path
```

Depois apague, **inclusive**, da linha 70 (`# ----...` logo acima de
`# Renderizacao por plataforma`) até a linha 657
(`    return "".join(opening + kept + added + rest)`, a última de `render_skill`). O
trecho apagado contém `profile_name_problem` e `check_profile_names`, que voltam no
bloco abaixo sem mudança. No lugar, ponha:

```python
# --------------------------------------------------------------------------
# Renderizacao por plataforma: mora em sparkforge/integrate/render.py
# --------------------------------------------------------------------------
# Um renderizador so para os espelhos deste repositorio e para a integracao por
# usuario (`sparkforge integrate`), feature INTEGRACAO_USUARIO, D1. Este arquivo e
# a fachada: reexporta os nomes que os testes e o `--check` usam e passa o proprio
# `AGENTS_SRC` as funcoes que leem perfis.
#
# O modulo e carregado PELO CAMINHO, a partir de `ROOT`, e nao por
# `import sparkforge...`. `tests/test_arvore_versionada.py` roda este script sobre
# uma copia de `git archive HEAD`; um import pelo pacote acharia o `render.py` do
# disco (instalacao editavel), e o gate deixaria de conferir o renderizador
# commitado. `render.py` so importa a biblioteca padrao, e por isso carrega sozinho.
_RENDER_PATH = ROOT / "sparkforge" / "integrate" / "render.py"
_RENDER_SPEC = importlib.util.spec_from_file_location("_sparkforge_render", _RENDER_PATH)
if _RENDER_SPEC is None or _RENDER_SPEC.loader is None:
    raise ImportError(f"renderizador nao encontrado: {_RENDER_PATH}")
_render = importlib.util.module_from_spec(_RENDER_SPEC)
sys.modules[_RENDER_SPEC.name] = _render
_RENDER_SPEC.loader.exec_module(_render)

PASSTHROUGH_PLATFORMS = _render.PASSTHROUGH_PLATFORMS
PLATFORMS = _render.PLATFORMS
DEVIN_DROPPED_KEYS = _render.DEVIN_DROPPED_KEYS
DEVIN_BUILTIN_PROFILE_NAMES = _render.DEVIN_BUILTIN_PROFILE_NAMES
DEVIN_SKILL_DISPATCH_KEYS = _render.DEVIN_SKILL_DISPATCH_KEYS
DISPATCHABLE_SKILLS = _render.DISPATCHABLE_SKILLS
NON_DISPATCHABLE_SKILLS = _render.NON_DISPATCHABLE_SKILLS
SKILL_DISPATCH_REASON = _render.SKILL_DISPATCH_REASON
SKILL_FILENAME = _render.SKILL_FILENAME
render_agent = _render.render_agent
_split_frontmatter = _render._split_frontmatter
_drop_frontmatter_keys = _render._drop_frontmatter_keys
_frontmatter_list = _render._frontmatter_list
_frontmatter_scalar = _render._frontmatter_scalar


def coordinators_by_skill() -> dict[str, tuple[str, ...]]:
    return _render.coordinators_by_skill(AGENTS_SRC)


def orchestrator_profiles() -> frozenset[str]:
    return _render.orchestrator_profiles(AGENTS_SRC)


def agent_for_skill(name: str) -> str | None:
    return _render.agent_for_skill(name, AGENTS_SRC)


def render_skill(text: str, platform: str, *, name: str) -> str:
    return _render.render_skill(text, platform, name=name, agents_src=AGENTS_SRC)


def profile_name_problem(path: Path) -> str | None:
    """O identificador que `path` publica colide com um built-in do Devin?

    Confere as **duas** fontes de identidade, porque elas podem discordar: o nome
    do arquivo, que a fonte declara ser o default do campo, e o `name:` do
    frontmatter, que vence quando existe. Um gate que so olhasse o caminho
    deixaria passar `revisor.md` com `name: subagent_general`.
    """
    parsed = _split_frontmatter(path.read_bytes().decode("utf-8"))
    declared = _frontmatter_scalar(parsed[1], "name") if parsed else None
    for identifier in (path.stem, declared):
        if identifier in DEVIN_BUILTIN_PROFILE_NAMES:
            return (
                f"NOME RESERVADO {path}: `{identifier}` e perfil embutido do Devin "
                "(knowledge/devin/agents-and-subagents.md, secao 1). A fonte proibe "
                "a colisao e nao diz o que acontece nela -- escolha outro nome"
            )
    return None


def check_profile_names() -> list[str]:
    """Confere as FONTES, nunca os espelhos.

    O espelho e derivado: um nome reservado que chegasse ao `.agents/agents/`
    teria vindo de `agents/`, e acusar nos dois lugares so multiplicaria a mesma
    linha por tres.
    """
    return [
        problem
        for path in iter_agent_files() + iter_executor_files()
        if (problem := profile_name_problem(path)) is not None
    ]
```

`skill_name_for`, `rendered_skill_bytes`, `platform_for`, `rendered_bytes` e o resto
do arquivo ficam como estão. Eles chamam `render_skill` e `render_agent` da fachada.

Em `tests/test_arvore_versionada.py`, troque

```python
    mudanca no tradutor sem regenerar os espelhos tambem cai aqui.
    """
    alvos = ["scripts/sync_skills.py", *_raizes_governadas()]
```

por

```python
    mudanca no tradutor sem regenerar os espelhos tambem cai aqui.

    Desde INTEGRACAO_USUARIO (D1) o tradutor mora em
    `sparkforge/integrate/render.py`, e `sync_skills.py` o carrega pelo caminho a
    partir da propria raiz -- por isso ele vem do commit junto.
    """
    alvos = [
        "scripts/sync_skills.py",
        "sparkforge/integrate/render.py",
        *_raizes_governadas(),
    ]
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`. Depois, os três arquivos que importam `scripts.sync_skills`:

```bash
python -m pytest tests/test_sync_render.py tests/test_agents_parity.py tests/test_skill_content.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

→ verde, com 686 testes na cópia medida. `python scripts/sync_skills.py --check` → `OK`.
Esta tarefa é do tipo `agent_or_skill` e muda o renderizador, e é por isso que os
testes de espelho entram aqui. `tests/test_arvore_versionada.py` confere o **commit**,
então roda depois do commit desta tarefa, na T10.

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate scripts/sync_skills.py tests/test_integrate.py tests/test_arvore_versionada.py`.

### 6. Commit

`git add sparkforge/integrate/render.py` e
`refactor(sync): move the per-platform renderer into sparkforge.integrate and add codex`

## T3 — hosts, plano de escrita, manifesto, dry-run e idempotência

### 1. Escrever o teste que falha

Imports de `tests/test_integrate.py`:

```python
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from sparkforge import __version__
from sparkforge.integrate import integrate, render, sources
```

Acrescente ao fim:

```python
def _foto(base: Path) -> dict[str, tuple[bytes, int]]:
    """Conteudo e mtime de todo arquivo sob `base`: o que "nao mudou nada" compara."""
    return {
        p.relative_to(base).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


def test_manifesto_dry_run_e_idempotencia(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    ensaio = integrate("devin", home=home, dry_run=True, windows=False)
    assert ensaio["dry_run"] is True
    (devin,) = ensaio["hosts"]
    assert ".config/devin/agents/sf-runtime-specialist.md" in devin["written"]
    assert ".agents/skills/sdd-plan/SKILL.md" in devin["written"]
    assert _foto(home) == {}, "dry-run escreveu no HOME"

    primeira = integrate("devin", home=home, windows=False)
    assert primeira["refused"] == []
    manifesto = json.loads((home / ".sparkforge" / "integrations.json").read_text("utf-8"))
    arquivos = manifesto["hosts"]["devin"]["files"]
    assert manifesto["hosts"]["devin"]["package_version"] == __version__
    assert set(arquivos) == set(primeira["hosts"][0]["written"])
    for relativo, sha in arquivos.items():
        assert hashlib.sha256((home / relativo).read_bytes()).hexdigest() == sha, relativo

    antes = _foto(home)
    segunda = integrate("devin", home=home, windows=False)
    assert segunda["hosts"][0]["written"] == []
    assert set(segunda["hosts"][0]["unchanged"]) == set(arquivos)
    assert _foto(home) == antes, "a segunda execucao mudou o HOME"

    # Arquivo que ja estava no HOME e nenhum host registrou e do usuario: fica.
    outra = tmp_path / "outra_home"
    alheio = outra / ".agents" / "skills" / "sdd-plan" / "SKILL.md"
    alheio.parent.mkdir(parents=True)
    alheio.write_text("minha skill\n", encoding="utf-8")
    recusado = integrate("copilot", home=outra)
    assert {"host": "copilot", "reason": "arquivo_do_usuario",
            "path": ".agents/skills/sdd-plan/SKILL.md"} in recusado["refused"]
    assert alheio.read_text(encoding="utf-8") == "minha skill\n"
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_manifesto_dry_run_e_idempotencia -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: erro de coleta com `ImportError: cannot import name 'integrate' from
'sparkforge.integrate'`.

### 3. Código mínimo

`sparkforge/integrate/hosts.py`:

```python
"""Onde cada host le agents, skills e MCP de USUARIO (D4).

Tabela declarativa, com a fonte oficial de cada caminho (lida em 2026-09-25, T1).
Nenhum caminho sai de variavel de ambiente espalhada: `home`, `windows` e `appdata`
entram por parametro, e o teste aponta os tres para `tmp_path`.

`~/.agents/skills` e lido por Devin, Codex e Copilot CLI; os tres gravam a mesma
renderizacao, a da plataforma `devin` -- a mesma que o espelho `.agents/skills` do
repositorio recebe. Os campos `subagent:`/`agent:` que ela acrescenta sao do Devin,
e os outros dois hosts nao os leem.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

HOSTS = ("claude", "devin", "codex", "copilot")

MARKETPLACE = "sparkforge-local"
PLUGIN = "sparkforge-aws"

FONTES = {
    "claude": "https://code.claude.com/docs/en/plugins",
    "devin": "https://docs.devin.ai/cli/subagents",
    "codex": "https://learn.chatgpt.com/docs/agent-configuration/subagents",
    "copilot": "https://docs.github.com/en/copilot/how-tos/copilot-cli",
}


@dataclass(frozen=True)
class Host:
    name: str
    agents_dir: Path
    agent_pattern: str
    agent_platform: str
    executors: bool
    skills_dir: Path
    skill_platform: str
    mcp_config: Path | None
    mcp_format: str | None
    fonte: str


def claude_marketplace_dir(home: Path) -> Path:
    return Path(home) / ".sparkforge" / "claude"


def claude_plugin_dir(home: Path) -> Path:
    return claude_marketplace_dir(home) / "plugins" / PLUGIN


def devin_config_dir(home: Path, *, windows: bool, appdata: Path | None) -> Path:
    """`~/.config/devin`, ou `%APPDATA%\\devin` no Windows."""
    if not windows:
        return Path(home) / ".config" / "devin"
    base = Path(appdata) if appdata else Path(home) / "AppData" / "Roaming"
    return base / "devin"


def host(
    nome: str,
    *,
    home: Path,
    windows: bool | None = None,
    appdata: Path | None = None,
) -> Host:
    """O `Host` de `nome` sob `home`. `windows=None` e `os.name == "nt"`, e
    `appdata=None` le `APPDATA` -- so o CLI deixa os dois no default."""
    if nome not in HOSTS:
        raise ValueError(f"host desconhecido: {nome!r}; conhecidos: {list(HOSTS)}")
    home = Path(home)
    if windows is None:
        windows = os.name == "nt"
    if appdata is None and os.environ.get("APPDATA"):
        appdata = Path(os.environ["APPDATA"])
    compartilhadas = home / ".agents" / "skills"
    if nome == "claude":
        plugin = claude_plugin_dir(home)
        return Host(
            name="claude",
            agents_dir=plugin / "agents",
            agent_pattern="{stem}.md",
            agent_platform="claude",
            executors=True,
            skills_dir=plugin / "skills",
            skill_platform="claude",
            mcp_config=None,
            mcp_format=None,
            fonte=FONTES["claude"],
        )
    if nome == "devin":
        config = devin_config_dir(home, windows=windows, appdata=appdata)
        return Host(
            name="devin",
            agents_dir=config / "agents",
            agent_pattern="{stem}.md",
            agent_platform="devin",
            executors=True,
            skills_dir=compartilhadas,
            skill_platform="devin",
            mcp_config=config / "mcp_config.json",
            mcp_format="json",
            fonte=FONTES["devin"],
        )
    if nome == "codex":
        # Executores ficam de fora: nao tem `description`, e o TOML do Codex exige.
        return Host(
            name="codex",
            agents_dir=home / ".codex" / "agents",
            agent_pattern="{stem}.toml",
            agent_platform="codex",
            executors=False,
            skills_dir=compartilhadas,
            skill_platform="devin",
            mcp_config=home / ".codex" / "config.toml",
            mcp_format="toml",
            fonte=FONTES["codex"],
        )
    return Host(
        name="copilot",
        agents_dir=home / ".copilot" / "agents",
        agent_pattern="{stem}.agent.md",
        agent_platform="github",
        executors=True,
        skills_dir=compartilhadas,
        skill_platform="devin",
        mcp_config=home / ".copilot" / "mcp-config.json",
        mcp_format="json",
        fonte=FONTES["copilot"],
    )


def mcp_command(python: str | None = None) -> tuple[str, list[str]]:
    """O servidor MCP pelo Python que TEM o sparkforge instalado, sem PYTHONPATH."""
    return (python or sys.executable, ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"])


def mcp_entry(nome: str, python: str | None = None) -> dict:
    """A entrada `mcpServers.sparkforge` de um host de config JSON."""
    comando, args = mcp_command(python)
    entrada: dict = {"command": comando, "args": args}
    if nome == "copilot":
        entrada = {"type": "local", **entrada, "tools": ["*"]}
    return entrada


__all__ = [
    "FONTES",
    "HOSTS",
    "MARKETPLACE",
    "PLUGIN",
    "Host",
    "claude_marketplace_dir",
    "claude_plugin_dir",
    "devin_config_dir",
    "host",
    "mcp_command",
    "mcp_entry",
]
```

`sparkforge/integrate/writer.py`, primeira versão:

```python
"""Plano de escrita no HOME, manifesto, dry-run e idempotencia (D5).

Toda escrita fora do repositorio passa por aqui e fica registrada em
`~/.sparkforge/integrations.json`: por host, cada arquivo gravado (caminho
relativo ao HOME, em POSIX, e sha256), a versao do pacote que o gravou e as
entradas de config inseridas. O manifesto e o que torna `detach` seguro -- sem
ele, apagar pelo nome levaria junto arquivo do usuario com o mesmo nome.

Tres regras para arquivo que ja existe no destino:

- nenhum host o registrou: e do usuario, sai recusa `arquivo_do_usuario` e ele
  fica como esta;
- algum host o registrou e o sha256 em disco ainda e o registrado: e nosso, e
  pode ser regravado;
- algum host o registrou e o sha256 mudou: o usuario editou depois, sai recusa
  `editado_pelo_usuario` e ele fica.

Um arquivo de `~/.agents/skills` pode ser de mais de um host; os donos sao os
hosts que o listam no manifesto, e so o ultimo a sair o apaga.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.integrate import render, sources
from sparkforge.integrate.hosts import Host

MANIFEST_RELATIVE = Path(".sparkforge") / "integrations.json"
SCHEMA = 1


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_path(home: Path) -> Path:
    return Path(home) / MANIFEST_RELATIVE


def load_manifest(home: Path) -> dict[str, Any]:
    caminho = manifest_path(home)
    if not caminho.is_file():
        return {"schema": SCHEMA, "hosts": {}}
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados.setdefault("schema", SCHEMA)
    dados.setdefault("hosts", {})
    return dados


def _texto_do_manifesto(manifesto: dict[str, Any]) -> str:
    return json.dumps(manifesto, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def save_manifest(home: Path, manifesto: dict[str, Any]) -> bool:
    """Grava so se mudou: a segunda execucao identica nao toca nem o mtime."""
    caminho = manifest_path(home)
    texto = _texto_do_manifesto(manifesto)
    if caminho.is_file() and caminho.read_text(encoding="utf-8") == texto:
        return False
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(texto.encode("utf-8"))
    return True


def rel(home: Path, caminho: Path) -> str:
    """Relativo ao HOME, em POSIX; fora dele (um `APPDATA` em outro disco), absoluto.
    `Path(home) / rel(...)` devolve o caminho certo nos dois casos."""
    caminho, home = Path(caminho), Path(home)
    if caminho == home or home in caminho.parents:
        return caminho.relative_to(home).as_posix()
    return caminho.as_posix()


def owners(manifesto: dict[str, Any], relativo: str) -> list[str]:
    return sorted(
        nome
        for nome, entrada in manifesto.get("hosts", {}).items()
        if relativo in (entrada.get("files") or {})
    )


def recorded_sha(manifesto: dict[str, Any], relativo: str) -> str | None:
    for nome in owners(manifesto, relativo):
        return manifesto["hosts"][nome]["files"][relativo]
    return None


def plan_files(h: Host, root: Path) -> list[tuple[Path, bytes]]:
    """Os arquivos que o host `h` recebe, ja renderizados para a plataforma dele."""
    agents_src = sources.agents_dir(root)
    skills_root = sources.skills_dir(root)
    plano: list[tuple[Path, bytes]] = []
    for src in sources.agent_files(root):
        destino = h.agents_dir / h.agent_pattern.format(stem=src.stem)
        plano.append((destino, render.render_agent_file(src, h.agent_platform)))
    if h.executors:
        for src in sources.executor_files(root):
            destino = h.agents_dir / "executors" / src.name
            plano.append((destino, render.render_agent_file(src, h.agent_platform)))
    for src in sources.skill_files(root):
        destino = h.skills_dir / src.relative_to(skills_root)
        dados = render.render_skill_file(
            src, skills_root, h.skill_platform, agents_src=agents_src
        )
        plano.append((destino, dados))
    return plano


def _podar(caminho: Path, home: Path) -> None:
    """Apaga os diretorios que ficaram vazios, subindo ate o HOME, sem ele."""
    pai = caminho.parent
    home = Path(home)
    while pai != home and home in pai.parents and pai.is_dir() and not any(pai.iterdir()):
        pai.rmdir()
        pai = pai.parent


def remove_owned(
    home: Path,
    manifesto: dict[str, Any],
    nome: str,
    relativos: list[str],
    *,
    dry_run: bool,
) -> dict[str, list]:
    """Tira de `nome` os arquivos `relativos`, apagando so o que e so dele e ainda
    tem o sha256 gravado. O manifesto e alterado em memoria; quem chama o salva."""
    removidos: list[str] = []
    mantidos: list[str] = []
    recusas: list[dict[str, str]] = []
    arquivos = manifesto["hosts"][nome].setdefault("files", {})
    for relativo in sorted(relativos):
        gravado = arquivos.get(relativo)
        outros = [o for o in owners(manifesto, relativo) if o != nome]
        caminho = Path(home) / relativo
        if outros:
            mantidos.append(relativo)
        elif caminho.is_file() and sha256_bytes(caminho.read_bytes()) != gravado:
            recusas.append({"reason": "editado_pelo_usuario", "path": relativo})
        else:
            removidos.append(relativo)
            if not dry_run and caminho.is_file():
                caminho.unlink()
                _podar(caminho, home)
        if not dry_run:
            arquivos.pop(relativo, None)
    return {"removed": removidos, "kept_shared": mantidos, "refused": recusas}


def apply_files(
    nome: str,
    plano: list[tuple[Path, bytes]],
    *,
    home: Path,
    manifesto: dict[str, Any],
    version: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Grava o plano de `nome` e atualiza o manifesto em memoria."""
    home = Path(home)
    escritos: list[str] = []
    iguais: list[str] = []
    recusas: list[dict[str, str]] = []
    novos: dict[str, str] = {}
    for destino, dados in plano:
        relativo = rel(home, destino)
        sha = sha256_bytes(dados)
        if destino.is_file():
            atual = sha256_bytes(destino.read_bytes())
            registrado = recorded_sha(manifesto, relativo)
            if registrado is None and atual != sha:
                recusas.append({"reason": "arquivo_do_usuario", "path": relativo})
                continue
            if registrado is not None and atual != registrado and atual != sha:
                recusas.append({"reason": "editado_pelo_usuario", "path": relativo})
                continue
            if atual == sha:
                iguais.append(relativo)
                novos[relativo] = sha
                continue
        escritos.append(relativo)
        novos[relativo] = sha
        if not dry_run:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados)
    entrada = manifesto["hosts"].get(nome) or {}
    anteriores = sorted(set(entrada.get("files") or {}) - set(novos))
    orfaos: dict[str, list] = {"removed": [], "kept_shared": [], "refused": []}
    if anteriores:
        manifesto["hosts"].setdefault(nome, entrada)
        orfaos = remove_owned(home, manifesto, nome, anteriores, dry_run=dry_run)
    if not dry_run:
        entrada = manifesto["hosts"].setdefault(nome, {})
        entrada["package_version"] = version
        entrada["files"] = dict(sorted(novos.items()))
        entrada.setdefault("config", [])
    return {
        "host": nome,
        "dry_run": dry_run,
        "written": escritos,
        "unchanged": iguais,
        "removed": orfaos["removed"],
        "refused": recusas + orfaos["refused"],
    }
```

`sparkforge/integrate/__init__.py`, inteiro:

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import host as _host

# Os hosts que esta versao integra. `claude` entra com o marketplace local (D8).
INTEGRAVEIS = ("devin", "codex", "copilot")


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        relatorios.append(
            writer.apply_files(
                nome, plano, home=home, manifesto=manifesto, version=__version__,
                dry_run=dry_run,
            )
        )
    if not dry_run:
        writer.save_manifest(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "integrate"]
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`.

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate tests/test_integrate.py`. `git add` dos dois
`.py` novos. O gate de lastro roda na T10.

### 6. Commit

`feat(integrate): write the user-scope plan with a manifest, dry-run and idempotence`

## T4 — Devin e Copilot: agents, `~/.agents/skills` e `mcpServers.sparkforge`

### 1. Escrever o teste que falha

Acrescente ao fim de `tests/test_integrate.py` (os imports não mudam):

```python
def _agents_renderizados(plataforma: str, padrao: str, executores: bool) -> dict[str, bytes]:
    """O que `scripts/sync_skills.py` renderiza para os agents de `plataforma`."""
    from scripts import sync_skills

    esperado = {
        padrao.format(stem=src.stem): sync_skills.render_agent(
            src.read_text(encoding="utf-8"), plataforma
        ).encode("utf-8")
        for src in sources.agent_files(ROOT)
    }
    if executores:
        for src in sources.executor_files(ROOT):
            esperado[f"executors/{src.name}"] = sync_skills.render_agent(
                src.read_text(encoding="utf-8"), plataforma
            ).encode("utf-8")
    return esperado


def _skills_do_devin() -> dict[str, bytes]:
    """`~/.agents/skills` recebe o que o espelho `.agents/skills` do repo recebe."""
    from scripts import sync_skills

    base = ROOT / ".agents" / "skills"
    return {
        src.relative_to(ROOT / "skills").as_posix(): sync_skills.rendered_skill_bytes(
            src, base / src.relative_to(ROOT / "skills")
        )
        for src in sources.skill_files(ROOT)
    }


def _conteudo(base: Path) -> dict[str, bytes]:
    return {
        p.relative_to(base).as_posix(): p.read_bytes()
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


def test_integrate_devin_grava_global_e_preserva_mcp_existente(tmp_path):
    home = tmp_path / "home"
    config = home / ".config" / "devin" / "mcp_config.json"
    config.parent.mkdir(parents=True)
    outro = {"command": "node", "args": ["servidor.js"]}
    config.write_text(json.dumps({"mcpServers": {"outro": outro}}), encoding="utf-8")

    resultado = integrate("devin", home=home, windows=False)
    assert resultado["refused"] == []
    assert _conteudo(home / ".config" / "devin" / "agents") == _agents_renderizados(
        "devin", "{stem}.md", executores=True
    )
    assert _conteudo(home / ".agents" / "skills") == _skills_do_devin()
    dados = json.loads(config.read_text(encoding="utf-8"))
    assert dados["mcpServers"]["outro"] == outro
    assert dados["mcpServers"]["sparkforge"] == {
        "command": sys.executable,
        "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"],
    }
    assert "PYTHONPATH" not in json.dumps(dados)

    # Windows: o diretorio de config do Devin e %APPDATA%\devin.
    appdata = tmp_path / "home_win" / "AppData" / "Roaming"
    integrate("devin", home=tmp_path / "home_win", windows=True, appdata=appdata)
    assert (appdata / "devin" / "agents" / "sf-runtime-specialist.md").is_file()
    assert (appdata / "devin" / "mcp_config.json").is_file()

    # `sparkforge` que o SparkForge nao escreveu: recusa, e o arquivo fica igual.
    alheio = tmp_path / "home_alheia" / ".config" / "devin" / "mcp_config.json"
    alheio.parent.mkdir(parents=True)
    texto = json.dumps({"mcpServers": {"sparkforge": {"command": "meu"}}})
    alheio.write_text(texto, encoding="utf-8")
    recusado = integrate("devin", home=tmp_path / "home_alheia", windows=False)
    assert [r["reason"] for r in recusado["refused"]] == ["sparkforge_ja_configurado"]
    assert alheio.read_text(encoding="utf-8") == texto

    quebrado = tmp_path / "home_quebrada" / ".config" / "devin" / "mcp_config.json"
    quebrado.parent.mkdir(parents=True)
    quebrado.write_text("{ nao e json", encoding="utf-8")
    recusado = integrate("devin", home=tmp_path / "home_quebrada", windows=False)
    assert [r["reason"] for r in recusado["refused"]] == ["config_invalida"]
    assert quebrado.read_text(encoding="utf-8") == "{ nao e json"


def test_integrate_copilot_grava_global_e_preserva_mcp_existente(tmp_path):
    home = tmp_path / "home"
    config = home / ".copilot" / "mcp-config.json"
    config.parent.mkdir(parents=True)
    outro = {"type": "local", "command": "uvx", "args": ["x"], "tools": ["*"]}
    config.write_text(json.dumps({"mcpServers": {"outro": outro}}), encoding="utf-8")

    resultado = integrate("copilot", home=home)
    assert resultado["refused"] == []
    assert _conteudo(home / ".copilot" / "agents") == _agents_renderizados(
        "github", "{stem}.agent.md", executores=True
    )
    assert _conteudo(home / ".agents" / "skills") == _skills_do_devin()
    dados = json.loads(config.read_text(encoding="utf-8"))
    assert dados["mcpServers"]["outro"] == outro
    assert dados["mcpServers"]["sparkforge"] == {
        "type": "local",
        "command": sys.executable,
        "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"],
        "tools": ["*"],
    }
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_integrate_devin_grava_global_e_preserva_mcp_existente -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: `KeyError: 'sparkforge'` em `dados["mcpServers"]["sparkforge"]`. Os
agents e as skills já são gravados, mas a config não.

### 3. Código mínimo

Acrescente ao fim de `sparkforge/integrate/writer.py`:

```python
# --------------------------------------------------------------------------
# Config de usuario em JSON (Devin, Copilot): so `mcpServers.sparkforge` (D6)
# --------------------------------------------------------------------------


def _registro_de_config(
    manifesto: dict[str, Any], nome: str, relativo: str
) -> dict[str, Any] | None:
    for registro in manifesto["hosts"].get(nome, {}).get("config") or []:
        if registro["path"] == relativo:
            return registro
    return None


def _guardar_registro(
    manifesto: dict[str, Any], nome: str, registro: dict[str, Any]
) -> None:
    registros = manifesto["hosts"].setdefault(nome, {}).setdefault("config", [])
    if registro not in registros:
        registros.append(registro)


def _json_de_config(caminho: Path) -> tuple[str, dict[str, Any] | None]:
    """(texto, dados), com `dados=None` quando o arquivo nao e JSON de objeto."""
    if not caminho.is_file():
        return "", {}
    texto = caminho.read_text(encoding="utf-8")
    try:
        dados = json.loads(texto) if texto.strip() else {}
    except json.JSONDecodeError:
        return texto, None
    if not isinstance(dados, dict) or not isinstance(dados.get("mcpServers", {}), dict):
        return texto, None
    return texto, dados


def apply_json_config(
    nome: str,
    caminho: Path,
    entrada: dict[str, Any],
    *,
    home: Path,
    manifesto: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    """Poe `mcpServers.sparkforge` no JSON de config do host e nada mais."""
    relativo = rel(home, caminho)
    registro = _registro_de_config(manifesto, nome, relativo)
    texto, dados = _json_de_config(caminho)
    if dados is None:
        return {"path": relativo, "status": "refused", "reason": "config_invalida"}
    servidores = dados.get("mcpServers")
    if isinstance(servidores, dict) and "sparkforge" in servidores and registro is None:
        return {"path": relativo, "status": "refused", "reason": "sparkforge_ja_configurado"}
    novo = dict(dados)
    novo["mcpServers"] = {**(servidores or {}), "sparkforge": entrada}
    novo_texto = json.dumps(novo, indent=2, ensure_ascii=False) + "\n"
    status = "unchanged" if novo_texto == texto else "written"
    if registro is None:
        registro = {
            "path": relativo,
            "format": "json",
            "created": not caminho.is_file(),
            "had_mcp_servers": servidores is not None,
        }
    if not dry_run:
        if status == "written":
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(novo_texto.encode("utf-8"))
        _guardar_registro(manifesto, nome, registro)
    return {"path": relativo, "status": status}
```

`sparkforge/integrate/__init__.py`, inteiro:

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import Host, mcp_entry
from sparkforge.integrate.hosts import host as _host

# Os hosts que esta versao integra. `claude` entra com o marketplace local (D8).
INTEGRAVEIS = ("devin", "codex", "copilot")


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _configurar(
    h: Host, *, home: Path, manifesto: dict[str, Any], dry_run: bool, python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None or h.mcp_format != "json":
        return []
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            home=home, manifesto=manifesto, dry_run=dry_run,
        )
    ]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recusas = [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]
    for r in relatorios:
        for config in r.get("config") or []:
            if config["status"] == "refused":
                recusas.append({"host": r["host"], "reason": config["reason"],
                                "path": config["path"]})
    return recusas


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    python: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        relatorio = writer.apply_files(
            nome, plano, home=home, manifesto=manifesto, version=__version__,
            dry_run=dry_run,
        )
        relatorio["config"] = _configurar(
            h, home=home, manifesto=manifesto, dry_run=dry_run, python=python
        )
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "integrate"]
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`. Depois
`python -m pytest tests/test_integrate.py::test_integrate_copilot_grava_global_e_preserva_mcp_existente -q -p no:cacheprovider --basetemp=E:/sfpt_iu`
→ `1 passed` (AC5).

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate tests/test_integrate.py`.

### 6. Commit

`feat(integrate): devin and copilot, merging mcpServers.sparkforge into user config`

## T5 — Codex: agents em TOML e o bloco marcado em `~/.codex/config.toml`

### 1. Escrever o teste que falha

Acrescente ao fim de `tests/test_integrate.py` (os imports não mudam):

```python
CONFIG_CODEX = '''model = "gpt-5"

[mcp_servers.outro]
command = "node"
args = ["servidor.js"]
'''


def test_integrate_codex_grava_toml_e_preserva_config(tmp_path):
    from scripts import sync_skills

    home = tmp_path / "home"
    config = home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG_CODEX, encoding="utf-8")

    resultado = integrate("codex", home=home)
    assert resultado["refused"] == []
    esperado = {
        f"{src.stem}.toml": sync_skills.render_agent(
            src.read_text(encoding="utf-8"), "codex"
        ).encode("utf-8")
        for src in sources.agent_files(ROOT)
    }
    assert _conteudo(home / ".codex" / "agents") == esperado
    assert _conteudo(home / ".agents" / "skills") == _skills_do_devin()

    texto = config.read_text(encoding="utf-8")
    assert texto.startswith(CONFIG_CODEX), "o que o usuario tinha foi reescrito"
    assert texto.count("# >>> sparkforge (gerenciado)") == 1
    assert texto.count("# <<< sparkforge") == 1

    # A segunda execucao nao duplica o bloco.
    integrate("codex", home=home)
    assert config.read_text(encoding="utf-8") == texto

    tomllib = pytest.importorskip("tomllib")
    dados = tomllib.loads(texto)
    assert dados["model"] == "gpt-5"
    assert dados["mcp_servers"]["outro"] == {"command": "node", "args": ["servidor.js"]}
    assert dados["mcp_servers"]["sparkforge"] == {
        "command": sys.executable,
        "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"],
    }
    for arquivo in (home / ".codex" / "agents").glob("*.toml"):
        agente = tomllib.loads(arquivo.read_text(encoding="utf-8"))
        assert set(agente) == {"name", "description", "developer_instructions"}

    # `[mcp_servers.sparkforge]` escrito a mao: recusa, e o arquivo fica igual.
    alheia = tmp_path / "alheia" / ".codex" / "config.toml"
    alheia.parent.mkdir(parents=True)
    alheia.write_text('[mcp_servers.sparkforge]\ncommand = "meu"\n', encoding="utf-8")
    recusado = integrate("codex", home=tmp_path / "alheia")
    assert [r["reason"] for r in recusado["refused"]] == ["sparkforge_ja_configurado"]
    assert alheia.read_text(encoding="utf-8") == '[mcp_servers.sparkforge]\ncommand = "meu"\n'
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_integrate_codex_grava_toml_e_preserva_config -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: `AssertionError: assert 0 == 1` em
`texto.count("# >>> sparkforge (gerenciado)") == 1`. Os agents TOML já são gravados, e
o `config.toml` segue igual ao do usuário.

### 3. Código mínimo

Em `sparkforge/integrate/writer.py`, troque

```python
import hashlib
import json
from pathlib import Path
```

por

```python
import hashlib
import json
import re
from pathlib import Path
```

e acrescente ao fim do mesmo arquivo:

```python
# --------------------------------------------------------------------------
# Config de usuario em TOML (Codex): um bloco marcado (D6)
# --------------------------------------------------------------------------
# O Python 3.10 que o projeto suporta nao le TOML e o projeto nao tem dependencia
# para isso; por isso o SparkForge nao reescreve o arquivo -- so poe, troca ou tira
# o bloco entre os dois marcadores. `[mcp_servers.sparkforge]` fora do bloco foi
# escrito por outra pessoa e sai recusa. Marcador sem par sai recusa tambem: nao
# da para saber onde o bloco termina.

INICIO_TOML = "# >>> sparkforge (gerenciado)"
FIM_TOML = "# <<< sparkforge"
_TABELA_SPARKFORGE = re.compile(r"^\s*\[mcp_servers\.sparkforge\]", re.MULTILINE)


def toml_block(comando: str, args: list[str]) -> str:
    """O bloco com `[mcp_servers.sparkforge]`. `json.dumps` produz string e array
    validos de TOML (o escape do JSON e subconjunto do escape de string basica)."""
    return (
        f"{INICIO_TOML}\n"
        "[mcp_servers.sparkforge]\n"
        f"command = {json.dumps(comando, ensure_ascii=False)}\n"
        f"args = {json.dumps(args, ensure_ascii=False)}\n"
        f"{FIM_TOML}\n"
    )


def _limites_do_bloco(texto: str) -> tuple[int, int] | None | str:
    """(inicio, fim) do bloco, `None` sem bloco, ou `"quebrado"`."""
    inicio, fim = texto.find(INICIO_TOML), texto.find(FIM_TOML)
    if inicio == -1 and fim == -1:
        return None
    if inicio == -1 or fim == -1 or fim < inicio:
        return "quebrado"
    return inicio, fim + len(FIM_TOML)


def apply_toml_config(
    nome: str,
    caminho: Path,
    bloco: str,
    *,
    home: Path,
    manifesto: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    """Poe (ou troca) o bloco marcado no TOML de config; o resto nao e tocado."""
    relativo = rel(home, caminho)
    existia = caminho.is_file()
    texto = caminho.read_text(encoding="utf-8") if existia else ""
    limites = _limites_do_bloco(texto)
    if limites == "quebrado":
        return {"path": relativo, "status": "refused", "reason": "bloco_toml_quebrado"}
    fora = texto if limites is None else texto[: limites[0]] + texto[limites[1]:]
    if _TABELA_SPARKFORGE.search(fora):
        return {"path": relativo, "status": "refused", "reason": "sparkforge_ja_configurado"}
    if limites is None:
        base = texto.rstrip("\n")
        novo = (base + "\n\n" if base else "") + bloco
    else:
        novo = texto[: limites[0]] + bloco.rstrip("\n") + texto[limites[1]:]
    status = "unchanged" if novo == texto else "written"
    registro = _registro_de_config(manifesto, nome, relativo) or {
        "path": relativo,
        "format": "toml",
        "created": not existia,
    }
    if not dry_run:
        if status == "written":
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(novo.encode("utf-8"))
        _guardar_registro(manifesto, nome, registro)
    return {"path": relativo, "status": status}
```

`sparkforge/integrate/__init__.py`, inteiro:

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import Host, mcp_command, mcp_entry
from sparkforge.integrate.hosts import host as _host

# Os hosts que esta versao integra. `claude` entra com o marketplace local (D8).
INTEGRAVEIS = ("devin", "codex", "copilot")


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _configurar(
    h: Host, *, home: Path, manifesto: dict[str, Any], dry_run: bool, python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None:
        return []
    if h.mcp_format == "toml":
        comando, args = mcp_command(python)
        return [
            writer.apply_toml_config(
                h.name, h.mcp_config, writer.toml_block(comando, args),
                home=home, manifesto=manifesto, dry_run=dry_run,
            )
        ]
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            home=home, manifesto=manifesto, dry_run=dry_run,
        )
    ]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recusas = [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]
    for r in relatorios:
        for config in r.get("config") or []:
            if config["status"] == "refused":
                recusas.append({"host": r["host"], "reason": config["reason"],
                                "path": config["path"]})
    return recusas


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    python: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        relatorio = writer.apply_files(
            nome, plano, home=home, manifesto=manifesto, version=__version__,
            dry_run=dry_run,
        )
        relatorio["config"] = _configurar(
            h, home=home, manifesto=manifesto, dry_run=dry_run, python=python
        )
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "integrate"]
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`. As asserções de `tomllib` só rodam em Python ≥ 3.11
(`importorskip`); no 3.10 o resto do teste roda do mesmo jeito.

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate tests/test_integrate.py`.

### 6. Commit

`feat(integrate): codex agents as TOML and a marked block in config.toml`

## T6 — `detach`

### 1. Escrever o teste que falha

Imports de `tests/test_integrate.py`:

```python
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from sparkforge import __version__
from sparkforge.integrate import detach, integrate, render, sources
```

Acrescente ao fim:

```python
def test_detach_remove_so_o_proprio_e_recusa_o_editado(tmp_path):
    home = tmp_path / "home"
    meu = home / "notas.txt"
    meu.parent.mkdir(parents=True)
    meu.write_text("do usuario\n", encoding="utf-8")
    config_devin = home / ".config" / "devin" / "mcp_config.json"
    config_devin.parent.mkdir(parents=True)
    original_devin = {"mcpServers": {"outro": {"command": "node"}}, "extra": 1}
    config_devin.write_text(json.dumps(original_devin), encoding="utf-8")
    config_codex = home / ".codex" / "config.toml"
    config_codex.parent.mkdir(parents=True)
    config_codex.write_text(CONFIG_CODEX, encoding="utf-8")

    for host in ("devin", "codex", "copilot"):
        assert integrate(host, home=home, windows=False)["refused"] == []
    editado = home / ".copilot" / "agents" / "sf-runtime-specialist.agent.md"
    editado.write_text("meu ajuste\n", encoding="utf-8")
    compartilhada = home / ".agents" / "skills" / "sdd-plan" / "SKILL.md"

    # dry-run lista e nao remove nada.
    antes = _foto(home)
    ensaio = detach("devin", home=home, dry_run=True)
    assert ensaio["hosts"][0]["status"] == "detached"
    assert _foto(home) == antes

    # Devin sai; a skill compartilhada fica, porque Codex e Copilot ainda a usam.
    detach("devin", home=home)
    assert not (home / ".config" / "devin" / "agents").exists()
    assert json.loads(config_devin.read_text(encoding="utf-8")) == original_devin
    assert compartilhada.is_file()

    # Codex sai; o config.toml volta a ser o do usuario, byte a byte.
    detach("codex", home=home)
    assert config_codex.read_text(encoding="utf-8") == CONFIG_CODEX
    assert not (home / ".codex" / "agents").exists()
    assert compartilhada.is_file()

    # Copilot sai por ultimo: a skill compartilhada vai junto; o editado fica.
    resultado = detach("copilot", home=home)
    assert {"host": "copilot", "reason": "editado_pelo_usuario",
            "path": ".copilot/agents/sf-runtime-specialist.agent.md"} in resultado["refused"]
    assert editado.read_text(encoding="utf-8") == "meu ajuste\n"
    assert not compartilhada.exists()
    assert not (home / ".agents").exists()
    # O mcp-config.json do Copilot foi criado pelo integrate e ficou vazio: sai.
    assert not (home / ".copilot" / "mcp-config.json").exists()
    assert meu.read_text(encoding="utf-8") == "do usuario\n"
    assert not (home / ".sparkforge" / "integrations.json").exists()
    assert detach("devin", home=home)["hosts"][0]["status"] == "not_integrated"
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_detach_remove_so_o_proprio_e_recusa_o_editado -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: erro de coleta com `ImportError: cannot import name 'detach' from
'sparkforge.integrate'`.

### 3. Código mínimo

Acrescente ao fim de `sparkforge/integrate/writer.py`:

```python
# --------------------------------------------------------------------------
# detach: devolver a config de usuario ao que era (D7)
# --------------------------------------------------------------------------


def _gravar_ou_apagar(caminho: Path, texto: str, *, apagar: bool, home: Path) -> None:
    if apagar:
        caminho.unlink()
        _podar(caminho, home)
    else:
        caminho.write_bytes(texto.encode("utf-8"))


def revert_json_config(
    registro: dict[str, Any], *, home: Path, dry_run: bool
) -> dict[str, Any]:
    """Tira `mcpServers.sparkforge`; o resto do JSON fica. Se o integrate criou o
    arquivo e ele ficou vazio, o arquivo sai."""
    relativo = registro["path"]
    caminho = Path(home) / relativo
    if not caminho.is_file():
        return {"path": relativo, "status": "absent"}
    _, dados = _json_de_config(caminho)
    if dados is None:
        return {"path": relativo, "status": "refused", "reason": "config_invalida"}
    servidores = dict(dados.get("mcpServers") or {})
    if "sparkforge" not in servidores:
        return {"path": relativo, "status": "absent"}
    del servidores["sparkforge"]
    novo = dict(dados)
    if servidores or registro.get("had_mcp_servers"):
        novo["mcpServers"] = servidores
    else:
        novo.pop("mcpServers", None)
    apagar = bool(registro.get("created")) and not novo
    if not dry_run:
        texto = json.dumps(novo, indent=2, ensure_ascii=False) + "\n"
        _gravar_ou_apagar(caminho, texto, apagar=apagar, home=home)
    return {"path": relativo, "status": "deleted" if apagar else "reverted"}


def revert_toml_config(
    registro: dict[str, Any], *, home: Path, dry_run: bool
) -> dict[str, Any]:
    """Tira o bloco marcado e a linha em branco que o integrate pos antes dele."""
    relativo = registro["path"]
    caminho = Path(home) / relativo
    if not caminho.is_file():
        return {"path": relativo, "status": "absent"}
    texto = caminho.read_text(encoding="utf-8")
    limites = _limites_do_bloco(texto)
    if limites == "quebrado":
        return {"path": relativo, "status": "refused", "reason": "bloco_toml_quebrado"}
    if limites is None:
        return {"path": relativo, "status": "absent"}
    partes = [
        parte
        for parte in (texto[: limites[0]].rstrip("\n"), texto[limites[1]:].lstrip("\n"))
        if parte
    ]
    novo = "\n\n".join(partes) + ("\n" if partes else "")
    apagar = bool(registro.get("created")) and not novo.strip()
    if not dry_run:
        _gravar_ou_apagar(caminho, novo, apagar=apagar, home=home)
    return {"path": relativo, "status": "deleted" if apagar else "reverted"}


def revert_config(registro: dict[str, Any], *, home: Path, dry_run: bool) -> dict[str, Any]:
    if registro.get("format") == "toml":
        return revert_toml_config(registro, home=home, dry_run=dry_run)
    return revert_json_config(registro, home=home, dry_run=dry_run)


def drop_manifest_if_empty(home: Path, manifesto: dict[str, Any]) -> None:
    """Sem host integrado, o manifesto sai do HOME; senao, e regravado."""
    if manifesto.get("hosts"):
        save_manifest(home, manifesto)
        return
    caminho = manifest_path(home)
    if caminho.is_file():
        caminho.unlink()
        _podar(caminho, home)
```

`sparkforge/integrate/__init__.py`, inteiro:

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import Host, mcp_command, mcp_entry
from sparkforge.integrate.hosts import host as _host

# Os hosts que esta versao integra. `claude` entra com o marketplace local (D8).
INTEGRAVEIS = ("devin", "codex", "copilot")


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _configurar(
    h: Host, *, home: Path, manifesto: dict[str, Any], dry_run: bool, python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None:
        return []
    if h.mcp_format == "toml":
        comando, args = mcp_command(python)
        return [
            writer.apply_toml_config(
                h.name, h.mcp_config, writer.toml_block(comando, args),
                home=home, manifesto=manifesto, dry_run=dry_run,
            )
        ]
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            home=home, manifesto=manifesto, dry_run=dry_run,
        )
    ]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recusas = [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]
    for r in relatorios:
        for config in r.get("config") or []:
            if config["status"] == "refused":
                recusas.append({"host": r["host"], "reason": config["reason"],
                                "path": config["path"]})
    return recusas


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    python: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        relatorio = writer.apply_files(
            nome, plano, home=home, manifesto=manifesto, version=__version__,
            dry_run=dry_run,
        )
        relatorio["config"] = _configurar(
            h, home=home, manifesto=manifesto, dry_run=dry_run, python=python
        )
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


def detach(alvo: str, *, home: Path, dry_run: bool = False) -> dict[str, Any]:
    """Remove o que o manifesto registrou para `alvo` (D7).

    So sai arquivo que ainda tem o sha256 gravado e que nenhum outro host usa;
    o editado depois fica, como recusa `editado_pelo_usuario`. Da config de
    usuario sai so a entrada que o integrate pos.
    """
    home = Path(home)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        entrada = manifesto["hosts"].get(nome)
        if entrada is None:
            relatorios.append({"host": nome, "status": "not_integrated", "refused": []})
            continue
        registros = list(entrada.get("config") or [])
        relatorio = writer.remove_owned(
            home, manifesto, nome, list(entrada.get("files") or {}), dry_run=dry_run
        )
        relatorio["host"] = nome
        relatorio["status"] = "detached"
        relatorio["config"] = [
            writer.revert_config(registro, home=home, dry_run=dry_run)
            for registro in registros
        ]
        if not dry_run:
            del manifesto["hosts"][nome]
        relatorios.append(relatorio)
    if not dry_run:
        writer.drop_manifest_if_empty(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "detach", "integrate"]
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`.

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate tests/test_integrate.py`.

### 6. Commit

`feat(integrate): detach removes only what the manifest recorded, and restores user config`

## T7 — Claude Code: marketplace local e o `claude plugin`

### 1. Escrever o teste que falha

Acrescente ao fim de `tests/test_integrate.py` (os imports não mudam):

```python
class _ClaudeFalso:
    """O executor do `claude` que o teste injeta: grava cada argv e devolve 0."""

    def __init__(self) -> None:
        self.chamadas: list[list[str]] = []

    def __call__(self, argv: list[str]) -> tuple[int, str]:
        self.chamadas.append(argv)
        return 0, "{}"


def test_integrate_claude_monta_plugin_e_recusa_sem_cli(tmp_path):
    from scripts import sync_skills

    home = tmp_path / "home"
    marketplace = home / ".sparkforge" / "claude"
    plugin = marketplace / "plugins" / "sparkforge-aws"

    # Sem `claude` no PATH: o plugin fica montado e a recusa traz os dois comandos.
    sem_cli = integrate("claude", home=home, which=lambda _nome: None)
    (recusa,) = sem_cli["refused"]
    assert recusa["reason"] == "claude_cli_ausente"
    assert recusa["commands"] == [
        f"claude plugin marketplace add {marketplace} --scope user",
        "claude plugin install sparkforge-aws@sparkforge-local --scope user --json",
    ]
    catalogo = json.loads((marketplace / ".claude-plugin" / "marketplace.json").read_text("utf-8"))
    assert catalogo["name"] == "sparkforge-local"
    assert catalogo["plugins"][0]["name"] == "sparkforge-aws"
    assert catalogo["plugins"][0]["source"] == "./plugins/sparkforge-aws"
    manifesto = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    assert (manifesto["name"], manifesto["version"]) == ("sparkforge-aws", __version__)
    mcp = json.loads((plugin / ".mcp.json").read_text("utf-8"))
    assert mcp == {"mcpServers": {"sparkforge": {
        "command": sys.executable,
        "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"],
    }}}
    assert "PYTHONPATH" not in (plugin / ".mcp.json").read_text("utf-8")
    assert _conteudo(plugin / "agents") == _agents_renderizados(
        "claude", "{stem}.md", executores=True
    )
    esperado_skills = {
        src.relative_to(ROOT / "skills").as_posix(): sync_skills.rendered_skill_bytes(
            src, ROOT / ".claude" / "skills" / src.relative_to(ROOT / "skills")
        )
        for src in sources.skill_files(ROOT)
    }
    assert _conteudo(plugin / "skills") == esperado_skills

    # Com o CLI: marketplace add e install, com o executavel que `which` achou.
    claude = _ClaudeFalso()
    registrado = integrate("claude", home=home, runner=claude, which=lambda _: "/bin/claude")
    assert registrado["refused"] == []
    assert claude.chamadas == [
        ["/bin/claude", "plugin", "marketplace", "add", str(marketplace), "--scope", "user"],
        ["/bin/claude", "plugin", "install", "sparkforge-aws@sparkforge-local",
         "--scope", "user", "--json"],
    ]
    # Registrado e sem mudanca: a segunda execucao nao chama o CLI de novo.
    integrate("claude", home=home, runner=claude, which=lambda _: "/bin/claude")
    assert len(claude.chamadas) == 2

    # detach desinstala pelo CLI e tira os arquivos.
    saiu = detach("claude", home=home, runner=claude, which=lambda _: "/bin/claude")
    assert saiu["refused"] == []
    assert claude.chamadas[2:] == [
        ["/bin/claude", "plugin", "uninstall", "sparkforge-aws@sparkforge-local",
         "--scope", "user"],
        ["/bin/claude", "plugin", "marketplace", "remove", "sparkforge-local",
         "--scope", "user"],
    ]
    assert not marketplace.exists()
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_integrate_claude_monta_plugin_e_recusa_sem_cli -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: `TypeError: integrate() got an unexpected keyword argument 'which'`.

### 3. Código mínimo

`sparkforge/integrate/claude.py`:

```python
"""Claude Code: o plugin por marketplace local (D8).

Monta em `~/.sparkforge/claude/` o marketplace `sparkforge-local`, com o plugin
`sparkforge-aws` em `plugins/sparkforge-aws/` (skills, agents, `.mcp.json` e
`.claude-plugin/plugin.json`), e o registra pelo proprio CLI do Claude:

    claude plugin marketplace add <dir> --scope user
    claude plugin install sparkforge-aws@sparkforge-local --scope user --json

Os flags foram conferidos no `--help` do Claude Code 2.1.283. `~/.claude/settings.json`
nao e editado a mao: e formato interno do Claude, e muda sem aviso.

Sem `claude` no PATH o diretorio fica montado e sai a recusa `claude_cli_ausente`
com os comandos que o operador roda. O executor e injetavel (`runner`, `which`):
nenhum teste chama o binario de verdade.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sparkforge.integrate.hosts import (
    MARKETPLACE,
    PLUGIN,
    claude_marketplace_dir,
    claude_plugin_dir,
    mcp_command,
)

Runner = Callable[[list[str]], tuple[int, str]]
Which = Callable[[str], str | None]

DESCRICAO = (
    "Analise deterministica de jobs PySpark no AWS Glue e no Amazon EMR: facts por AST "
    "e dumps coletados, julgamento contra catalogo de regras versionado, e case que "
    "atravessa sessoes."
)
PLUGIN_ID = f"{PLUGIN}@{MARKETPLACE}"


def _json(dados: dict[str, Any]) -> bytes:
    return (json.dumps(dados, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def plugin_files(home: Path, *, version: str, python: str | None) -> list[tuple[Path, bytes]]:
    """Os tres arquivos do marketplace e do plugin que nao sao skill nem agent."""
    marketplace = claude_marketplace_dir(home)
    plugin = claude_plugin_dir(home)
    comando, args = mcp_command(python)
    catalogo = {
        "name": MARKETPLACE,
        "owner": {"name": "SparkForge AWS"},
        "plugins": [
            {
                "name": PLUGIN,
                "source": f"./plugins/{PLUGIN}",
                "description": DESCRICAO,
                "version": version,
            }
        ],
    }
    manifesto = {
        "name": PLUGIN,
        "version": version,
        "description": DESCRICAO,
        "author": {"name": "SparkForge AWS"},
        "license": "MIT",
    }
    # O Python que TEM o sparkforge instalado, sem PYTHONPATH para repositorio nenhum.
    mcp = {"mcpServers": {"sparkforge": {"command": comando, "args": args}}}
    return [
        (marketplace / ".claude-plugin" / "marketplace.json", _json(catalogo)),
        (plugin / ".claude-plugin" / "plugin.json", _json(manifesto)),
        (plugin / ".mcp.json", _json(mcp)),
    ]


def register_commands(home: Path, *, primeira: bool) -> list[list[str]]:
    """Os argumentos do `claude` (sem o executavel): registrar, ou atualizar."""
    if primeira:
        return [
            ["plugin", "marketplace", "add", str(claude_marketplace_dir(home)),
             "--scope", "user"],
            ["plugin", "install", PLUGIN_ID, "--scope", "user", "--json"],
        ]
    return [
        ["plugin", "marketplace", "update", MARKETPLACE],
        ["plugin", "update", PLUGIN_ID],
    ]


def unregister_commands() -> list[list[str]]:
    return [
        ["plugin", "uninstall", PLUGIN_ID, "--scope", "user"],
        ["plugin", "marketplace", "remove", MARKETPLACE, "--scope", "user"],
    ]


def _mostrar(comandos: list[list[str]]) -> list[str]:
    return [" ".join(["claude", *argv]) for argv in comandos]


def run(argv: list[str]) -> tuple[int, str]:
    """O executor de verdade. `argv[0]` e o caminho absoluto que `which` achou."""
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _executar(
    comandos: list[list[str]], *, runner: Runner | None, which: Which | None
) -> dict[str, Any]:
    executavel = (which or shutil.which)("claude")
    if executavel is None:
        return {
            "status": "refused",
            "reason": "claude_cli_ausente",
            "commands": _mostrar(comandos),
        }
    for argv in comandos:
        codigo, saida = (runner or run)([executavel, *argv])
        if codigo != 0:
            return {
                "status": "refused",
                "reason": "claude_cli_falhou",
                "command": _mostrar([argv])[0],
                "output": saida[-400:],
            }
    return {"status": "ok", "commands": _mostrar(comandos)}


def register(
    home: Path,
    *,
    primeira: bool,
    mudou: bool,
    dry_run: bool,
    runner: Runner | None = None,
    which: Which | None = None,
) -> dict[str, Any]:
    """Registra (ou atualiza) o plugin no Claude Code pelo CLI dele."""
    comandos = register_commands(home, primeira=primeira)
    if dry_run:
        return {"status": "dry_run", "commands": _mostrar(comandos)}
    if not primeira and not mudou:
        return {"status": "unchanged", "commands": []}
    return _executar(comandos, runner=runner, which=which)


def unregister(
    *, dry_run: bool, runner: Runner | None = None, which: Which | None = None
) -> dict[str, Any]:
    comandos = unregister_commands()
    if dry_run:
        return {"status": "dry_run", "commands": _mostrar(comandos)}
    return _executar(comandos, runner=runner, which=which)


__all__ = [
    "DESCRICAO",
    "PLUGIN_ID",
    "plugin_files",
    "register",
    "register_commands",
    "run",
    "unregister",
    "unregister_commands",
]
```

`sparkforge/integrate/__init__.py`, inteiro. `INTEGRAVEIS` passa a ser `HOSTS`, e o
`claude` entra no `integrate` e no `detach`:

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import claude as _claude
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import HOSTS, Host, mcp_command, mcp_entry
from sparkforge.integrate.hosts import host as _host

INTEGRAVEIS = HOSTS


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _configurar(
    h: Host, *, home: Path, manifesto: dict[str, Any], dry_run: bool, python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None:
        return []
    if h.mcp_format == "toml":
        comando, args = mcp_command(python)
        return [
            writer.apply_toml_config(
                h.name, h.mcp_config, writer.toml_block(comando, args),
                home=home, manifesto=manifesto, dry_run=dry_run,
            )
        ]
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            home=home, manifesto=manifesto, dry_run=dry_run,
        )
    ]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recusas = [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]
    for r in relatorios:
        for config in r.get("config") or []:
            if config["status"] == "refused":
                recusas.append({"host": r["host"], "reason": config["reason"],
                                "path": config["path"]})
        cli = r.get("claude_cli") or {}
        if cli.get("status") == "refused":
            recusas.append({"host": r["host"], **{k: v for k, v in cli.items() if k != "status"}})
    return recusas


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    python: str | None = None,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        if nome == "claude":
            plano += _claude.plugin_files(home, version=__version__, python=python)
        primeira = not (manifesto["hosts"].get("claude") or {}).get("registered")
        relatorio = writer.apply_files(
            nome, plano, home=home, manifesto=manifesto, version=__version__,
            dry_run=dry_run,
        )
        relatorio["config"] = _configurar(
            h, home=home, manifesto=manifesto, dry_run=dry_run, python=python
        )
        if nome == "claude":
            cli = _claude.register(
                home, primeira=primeira,
                mudou=bool(relatorio["written"] or relatorio["removed"]),
                dry_run=dry_run, runner=runner, which=which,
            )
            relatorio["claude_cli"] = cli
            if cli["status"] == "ok":
                manifesto["hosts"]["claude"]["registered"] = True
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


def detach(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
) -> dict[str, Any]:
    """Remove o que o manifesto registrou para `alvo` (D7).

    So sai arquivo que ainda tem o sha256 gravado e que nenhum outro host usa;
    o editado depois fica, como recusa `editado_pelo_usuario`. Da config de
    usuario sai so a entrada que o integrate pos.
    """
    home = Path(home)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        entrada = manifesto["hosts"].get(nome)
        if entrada is None:
            relatorios.append({"host": nome, "status": "not_integrated", "refused": []})
            continue
        registros = list(entrada.get("config") or [])
        registrado = bool(entrada.get("registered"))
        relatorio = writer.remove_owned(
            home, manifesto, nome, list(entrada.get("files") or {}), dry_run=dry_run
        )
        relatorio["host"] = nome
        relatorio["status"] = "detached"
        relatorio["config"] = [
            writer.revert_config(registro, home=home, dry_run=dry_run)
            for registro in registros
        ]
        if nome == "claude" and registrado:
            relatorio["claude_cli"] = _claude.unregister(
                dry_run=dry_run, runner=runner, which=which
            )
        if not dry_run:
            del manifesto["hosts"][nome]
        relatorios.append(relatorio)
    if not dry_run:
        writer.drop_manifest_if_empty(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "detach", "integrate"]
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`. Nenhuma chamada ao binário `claude`: o teste injeta
`which` e `runner`.

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate tests/test_integrate.py`. O `# noqa: S603`
em `claude.run` é o único do módulo: o argv é fixo, e `argv[0]` é o caminho que
`shutil.which` achou.

### 6. Commit

`git add sparkforge/integrate/claude.py` e
`feat(integrate): claude code plugin through a local marketplace and the claude CLI`

## T8 — cópia vendorizada em dobro, e a guarda do escopo de usuário

### 1. Escrever o teste que falha

Acrescente ao fim de `tests/test_integrate.py` (os imports não mudam):

```python
def _repo_com_copia(base: Path) -> Path:
    """Um repositorio do operador com a copia do install_skills: `.agents/skills`
    com uma skill identica e uma customizada, e um agent do Claude identico."""
    repo = base / "repo_do_operador"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "job.py").write_text("print('job')\n", encoding="utf-8")
    for nome in ("sdd-plan", "diagnose-oom"):
        origem = ROOT / ".agents" / "skills" / nome
        for arquivo in origem.rglob("*"):
            if arquivo.is_file():
                destino = repo / ".agents" / "skills" / nome / arquivo.relative_to(origem)
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(arquivo.read_bytes())
    customizada = repo / ".agents" / "skills" / "diagnose-oom" / "SKILL.md"
    customizada.write_text(customizada.read_text("utf-8") + "\nregra da casa\n", "utf-8")
    agente = repo / ".claude" / "agents" / "executors" / "sf-judge.md"
    agente.parent.mkdir(parents=True)
    agente.write_bytes((ROOT / ".claude" / "agents" / "executors" / "sf-judge.md").read_bytes())
    return repo


def test_conflito_com_copia_vendorizada_tres_escolhas(tmp_path):
    identica = ".agents/skills/sdd-plan/SKILL.md"
    customizada = ".agents/skills/diagnose-oom/SKILL.md"
    agente = ".claude/agents/executors/sf-judge.md"

    # Sem terminal e sem a flag: IGNORAR, e o repositorio nao muda.
    repo = _repo_com_copia(tmp_path / "a")
    antes = _foto(repo)
    ignorado = integrate("devin", home=tmp_path / "h1", windows=False, repo=repo)
    conflito = ignorado["conflict"]
    assert conflito["choice"] == "ignore"
    assert {(c["location"], c["name"], c["identical"]) for c in conflito["collisions"]} == {
        (".agents/skills", "sdd-plan", True),
        (".agents/skills", "diagnose-oom", False),
        (".claude/agents", "sf-judge", True),
    }
    assert _foto(repo) == antes

    # O prompt recebe os nomes; "m" e MESCLAR: sai so o identico.
    perguntas: list[str] = []

    def responde_m(texto: str) -> str:
        perguntas.append(texto)
        return "m"

    repo = _repo_com_copia(tmp_path / "b")
    mesclado = integrate("devin", home=tmp_path / "h2", windows=False, repo=repo,
                         interactive=True, prompt=responde_m)["conflict"]
    assert "sdd-plan" in perguntas[0] and "diagnose-oom" in perguntas[0]
    assert mesclado["choice"] == "merge"
    assert identica in mesclado["removed"] and agente in mesclado["removed"]
    assert not (repo / identica).exists() and not (repo / agente).exists()
    assert (repo / customizada).is_file()
    assert mesclado["still_duplicated"] == [".agents/skills/diagnose-oom"]

    # --on-conflict overwrite, com dry-run: lista e nao apaga; sem dry-run, apaga os dois.
    repo = _repo_com_copia(tmp_path / "c")
    antes = _foto(repo)
    ensaio = integrate("devin", home=tmp_path / "h3", windows=False, repo=repo,
                       on_conflict="overwrite", dry_run=True)["conflict"]
    assert customizada in ensaio["removed"] and identica in ensaio["removed"]
    assert _foto(repo) == antes
    sobrescrito = integrate("devin", home=tmp_path / "h3", windows=False, repo=repo,
                            on_conflict="overwrite")["conflict"]
    assert sobrescrito["still_duplicated"] == []
    assert not (repo / identica).exists() and not (repo / customizada).exists()
    assert (repo / "src" / "job.py").is_file()

    # O proprio repositorio fonte do SparkForge: recusa por nome, nada e tocado.
    fonte = integrate("devin", home=tmp_path / "h4", windows=False, repo=ROOT,
                      on_conflict="overwrite")["conflict"]
    assert fonte["refused"][0]["reason"] == "repositorio_fonte"
    assert fonte["removed"] == []


def test_scope_user_nao_escreve_no_repo(tmp_path):
    repo = _repo_com_copia(tmp_path)
    antes = _foto(repo)
    resultado = integrate("all", home=tmp_path / "home", windows=False, repo=repo,
                          which=lambda _nome: None)
    assert {h["host"] for h in resultado["hosts"]} == {"claude", "devin", "codex", "copilot"}
    assert _foto(repo) == antes, "integrate --scope user escreveu dentro do repositorio"
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_conflito_com_copia_vendorizada_tres_escolhas -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: `TypeError: integrate() got an unexpected keyword argument 'repo'`.

### 3. Código mínimo

`sparkforge/integrate/conflict.py`:

```python
"""Copia vendorizada em dobro no repositorio atual (D9).

`scripts/install_skills.py` copia skills e agents para dentro do repositorio. Com
a integracao de usuario, o mesmo nome aparece duas vezes nos hosts que nao
separam por namespace. Aqui a copia e achada por NOME e classificada por
CONTEUDO: `identico` quando e byte a byte o que o wheel renderiza para aquele
diretorio, `customizado` quando difere.

Tres escolhas, e nenhuma e tomada sem o operador:

- `overwrite` (SOBRESCREVER): apaga do repositorio as duas classes;
- `merge` (MESCLAR): apaga so os identicos e lista os customizados, que continuam
  em dobro;
- `ignore` (IGNORAR): nao toca no repositorio. E o padrao sem terminal e sem
  `--on-conflict`.

No proprio repositorio fonte do SparkForge (tem `scripts/sync_skills.py`) os
espelhos `.claude/`, `.agents/` e `.github/` sao gerados e versionados: sai a
recusa `repositorio_fonte` e nada e tocado.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sparkforge.integrate import render, sources

ESCOLHAS = ("overwrite", "merge", "ignore")

# (diretorio no repo, tipo, plataforma do renderizador, hosts que o leem)
VENDOR_LOCATIONS = (
    (".claude/skills", "skill", "claude", ("claude",)),
    (".agents/skills", "skill", "devin", ("devin", "codex", "copilot")),
    (".claude/agents", "agent", "claude", ("claude",)),
    (".agents/agents", "agent", "devin", ("devin",)),
    (".github/agents", "agent", "github", ("copilot",)),
)

_RESPOSTAS = {
    "s": "overwrite", "sobrescrever": "overwrite", "overwrite": "overwrite",
    "m": "merge", "mesclar": "merge", "merge": "merge",
    "i": "ignore", "ignorar": "ignore", "ignore": "ignore", "": "ignore",
}


def is_source_repo(repo: Path) -> bool:
    return (Path(repo) / "scripts" / "sync_skills.py").is_file()


def _arquivos(base: Path) -> dict[str, bytes]:
    return {
        p.relative_to(base).as_posix(): p.read_bytes()
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


def _colisoes_de_skill(
    repo: Path, local: str, plataforma: str, hosts: tuple[str, ...], root: Path
) -> list[dict[str, Any]]:
    skills_root = sources.skills_dir(root)
    agents_src = sources.agents_dir(root)
    achadas = []
    for nome in sources.skill_names(root):
        pasta = repo / local / nome
        if not pasta.is_dir():
            continue
        esperado = {
            src.relative_to(skills_root / nome).as_posix(): render.render_skill_file(
                src, skills_root, plataforma, agents_src=agents_src
            )
            for src in sources.skill_files(root)
            if src.relative_to(skills_root).parts[0] == nome
        }
        encontrado = _arquivos(pasta)
        achadas.append({
            "name": nome,
            "kind": "skill",
            "location": local,
            "hosts": list(hosts),
            "identical": encontrado == esperado,
            "files": [f"{local}/{nome}/{r}" for r in sorted(encontrado)],
        })
    return achadas


def _colisoes_de_agent(
    repo: Path, local: str, plataforma: str, hosts: tuple[str, ...], root: Path
) -> list[dict[str, Any]]:
    sufixo = ".agent.md" if plataforma == "github" else ".md"
    candidatos = [(src, f"{src.stem}{sufixo}") for src in sources.agent_files(root)]
    candidatos += [(src, f"executors/{src.name}") for src in sources.executor_files(root)]
    achadas = []
    for src, relativo in candidatos:
        arquivo = repo / local / relativo
        if not arquivo.is_file():
            continue
        achadas.append({
            "name": src.stem,
            "kind": "agent",
            "location": local,
            "hosts": list(hosts),
            "identical": arquivo.read_bytes() == render.render_agent_file(src, plataforma),
            "files": [f"{local}/{relativo}"],
        })
    return achadas


def detect(repo: Path, *, root: Path | None = None) -> dict[str, Any]:
    """As colisoes entre a copia do repositorio e o que o wheel integra."""
    repo = Path(repo)
    if is_source_repo(repo):
        return {"collisions": [], "refused": [{
            "reason": "repositorio_fonte",
            "detail": "os espelhos deste repositorio sao gerados por scripts/sync_skills.py",
        }]}
    raiz = sources.content_root() if root is None else Path(root)
    colisoes: list[dict[str, Any]] = []
    for local, tipo, plataforma, hosts in VENDOR_LOCATIONS:
        if not (repo / local).is_dir():
            continue
        busca = _colisoes_de_skill if tipo == "skill" else _colisoes_de_agent
        colisoes.extend(busca(repo, local, plataforma, hosts, raiz))
    return {"collisions": colisoes, "refused": []}


def _pergunta(colisoes: list[dict[str, Any]]) -> str:
    nomes = ", ".join(sorted({f"{c['location']}/{c['name']}" for c in colisoes}))
    return (
        f"Copia vendorizada em dobro no repositorio: {nomes}.\n"
        "[s] sobrescrever (apaga do repo)  [m] mesclar (apaga so o identico)  "
        "[i] ignorar (nao toca no repo): "
    )


def choose(
    colisoes: list[dict[str, Any]],
    *,
    on_conflict: str | None,
    interactive: bool,
    prompt: Callable[[str], str] | None,
) -> str:
    """A escolha: a flag vence; sem flag e com terminal, pergunta; senao, `ignore`."""
    if on_conflict is not None:
        if on_conflict not in ESCOLHAS:
            raise ValueError(f"--on-conflict invalido: {on_conflict!r}; use {list(ESCOLHAS)}")
        return on_conflict
    if not colisoes or not interactive or prompt is None:
        return "ignore"
    return _RESPOSTAS.get(prompt(_pergunta(colisoes)).strip().lower(), "ignore")


def _podar(caminho: Path, base: Path) -> None:
    pai = caminho.parent
    while pai != base and base in pai.parents and pai.is_dir() and not any(pai.iterdir()):
        pai.rmdir()
        pai = pai.parent


def resolve(
    repo: Path, colisoes: list[dict[str, Any]], escolha: str, *, dry_run: bool
) -> dict[str, Any]:
    """Aplica a escolha. A lista do que sai vem no relatorio, com ou sem dry-run."""
    repo = Path(repo)
    if escolha == "overwrite":
        saem = colisoes
    elif escolha == "merge":
        saem = [c for c in colisoes if c["identical"]]
    else:
        saem = []
    ficam = [c for c in colisoes if c not in saem]
    removidos = sorted(arquivo for c in saem for arquivo in c["files"])
    if not dry_run:
        for relativo in removidos:
            caminho = repo / relativo
            if caminho.is_file():
                caminho.unlink()
                _podar(caminho, repo / relativo.split("/")[0])
    return {
        "choice": escolha,
        "dry_run": dry_run,
        "removed": removidos,
        "still_duplicated": sorted(f"{c['location']}/{c['name']}" for c in ficam),
    }


__all__ = ["ESCOLHAS", "VENDOR_LOCATIONS", "choose", "detect", "is_source_repo", "resolve"]
```

`sparkforge/integrate/__init__.py`, inteiro:

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import claude as _claude
from sparkforge.integrate import conflict as _conflict
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import HOSTS, Host, mcp_command, mcp_entry
from sparkforge.integrate.hosts import host as _host

INTEGRAVEIS = HOSTS


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _configurar(
    h: Host, *, home: Path, manifesto: dict[str, Any], dry_run: bool, python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None:
        return []
    if h.mcp_format == "toml":
        comando, args = mcp_command(python)
        return [
            writer.apply_toml_config(
                h.name, h.mcp_config, writer.toml_block(comando, args),
                home=home, manifesto=manifesto, dry_run=dry_run,
            )
        ]
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            home=home, manifesto=manifesto, dry_run=dry_run,
        )
    ]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recusas = [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]
    for r in relatorios:
        for config in r.get("config") or []:
            if config["status"] == "refused":
                recusas.append({"host": r["host"], "reason": config["reason"],
                                "path": config["path"]})
        cli = r.get("claude_cli") or {}
        if cli.get("status") == "refused":
            recusas.append({"host": r["host"], **{k: v for k, v in cli.items() if k != "status"}})
    return recusas


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    python: str | None = None,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
    root: Path | None = None,
    repo: Path | None = None,
    on_conflict: str | None = None,
    interactive: bool = False,
    prompt: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`.

    Com `repo`, confere a copia vendorizada em dobro nele e aplica a escolha do
    operador (D9); e a unica escrita possivel dentro de um repositorio."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        if nome == "claude":
            plano += _claude.plugin_files(home, version=__version__, python=python)
        primeira = not (manifesto["hosts"].get("claude") or {}).get("registered")
        relatorio = writer.apply_files(
            nome, plano, home=home, manifesto=manifesto, version=__version__,
            dry_run=dry_run,
        )
        relatorio["config"] = _configurar(
            h, home=home, manifesto=manifesto, dry_run=dry_run, python=python
        )
        if nome == "claude":
            cli = _claude.register(
                home, primeira=primeira,
                mudou=bool(relatorio["written"] or relatorio["removed"]),
                dry_run=dry_run, runner=runner, which=which,
            )
            relatorio["claude_cli"] = cli
            if cli["status"] == "ok":
                manifesto["hosts"]["claude"]["registered"] = True
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(home, manifesto)
    resultado: dict[str, Any] = {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }
    if repo is not None:
        resultado["conflict"] = _conferir_copia(
            Path(repo), raiz, dry_run=dry_run, on_conflict=on_conflict,
            interactive=interactive, prompt=prompt,
        )
    return resultado


def _conferir_copia(
    repo: Path,
    raiz: Path,
    *,
    dry_run: bool,
    on_conflict: str | None,
    interactive: bool,
    prompt: Callable[[str], str] | None,
) -> dict[str, Any]:
    achado = _conflict.detect(repo, root=raiz)
    colisoes = achado["collisions"]
    if achado["refused"]:
        escolha = "ignore"
    else:
        escolha = _conflict.choose(
            colisoes, on_conflict=on_conflict, interactive=interactive, prompt=prompt
        )
    resolucao = _conflict.resolve(repo, colisoes, escolha, dry_run=dry_run)
    return {
        "collisions": [
            {k: c[k] for k in ("name", "kind", "location", "identical")} for c in colisoes
        ],
        **resolucao,
        "refused": achado["refused"],
    }


def detach(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
) -> dict[str, Any]:
    """Remove o que o manifesto registrou para `alvo` (D7).

    So sai arquivo que ainda tem o sha256 gravado e que nenhum outro host usa;
    o editado depois fica, como recusa `editado_pelo_usuario`. Da config de
    usuario sai so a entrada que o integrate pos.
    """
    home = Path(home)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        entrada = manifesto["hosts"].get(nome)
        if entrada is None:
            relatorios.append({"host": nome, "status": "not_integrated", "refused": []})
            continue
        registros = list(entrada.get("config") or [])
        registrado = bool(entrada.get("registered"))
        relatorio = writer.remove_owned(
            home, manifesto, nome, list(entrada.get("files") or {}), dry_run=dry_run
        )
        relatorio["host"] = nome
        relatorio["status"] = "detached"
        relatorio["config"] = [
            writer.revert_config(registro, home=home, dry_run=dry_run)
            for registro in registros
        ]
        if nome == "claude" and registrado:
            relatorio["claude_cli"] = _claude.unregister(
                dry_run=dry_run, runner=runner, which=which
            )
        if not dry_run:
            del manifesto["hosts"][nome]
        relatorios.append(relatorio)
    if not dry_run:
        writer.drop_manifest_if_empty(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "detach", "integrate"]
```

### 4. Rodar e ver passar

O mesmo comando → `1 passed`. Depois a guarda do AC10:
`python -m pytest tests/test_integrate.py::test_scope_user_nao_escreve_no_repo -q -p no:cacheprovider --basetemp=E:/sfpt_iu`
→ `1 passed`. Ela é guarda de regressão: nasce verde por desenho, porque o `integrate`
só escreve no HOME, e morde se uma tarefa futura voltar a copiar para o repositório.
Para ver que ela morde, troque por um instante
`home=tmp_path / "home"` por `home=repo` na chamada do teste: o teste fica vermelho.
Desfaça antes do commit.

### 5. Gates vizinhos

`python -m ruff check sparkforge/integrate tests/test_integrate.py`.

### 6. Commit

`git add sparkforge/integrate/conflict.py` e
`feat(integrate): ask before touching a vendored copy in the repo; never write there otherwise`

## T9 — `sparkforge integrate`/`detach` na CLI, e o `doctor` por host

### 1. Escrever o teste que falha

Imports de `tests/test_integrate.py`:

```python
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from sparkforge import __version__
from sparkforge import doctor as dr
from sparkforge.adapters import _core
from sparkforge.adapters.cli import main as cli_main
from sparkforge.integrate import detach, integrate, render, sources, status
```

Acrescente ao fim:

```python
def test_doctor_informa_integracao_por_host(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    repo = _repo_com_copia(tmp_path)

    # Pela CLI: integrate com o HOME e o cwd do teste, sem terminal -> IGNORAR.
    monkeypatch.chdir(repo)
    assert cli_main(["integrate", "devin", "--scope", "user"]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert saida["conflict"]["choice"] == "ignore"
    assert (Path.home() / ".agents" / "skills" / "sdd-plan" / "SKILL.md").is_file()

    estado = status(home=home, repo=repo)
    por_id = {c.id: c for c in dr.avaliar_integracoes(
        estado["manifest"], None, estado["duplicated"]
    )}
    assert set(por_id) == {
        "integracao_claude", "integracao_devin", "integracao_codex", "integracao_copilot"
    }
    devin = por_id["integracao_devin"]
    assert devin.status == dr.WARN
    assert f"sparkforge {__version__}" in devin.detail
    assert ".agents/skills/sdd-plan" in devin.detail
    assert devin.unlock == "sparkforge integrate devin --scope user --on-conflict merge"
    assert por_id["integracao_claude"].status == dr.SKIP
    assert por_id["integracao_claude"].unlock == "sparkforge integrate claude --scope user"
    # Codex e Copilot nao estao integrados, mas leem `.agents/skills`: o dobro so
    # aparece quando o host esta integrado.
    assert por_id["integracao_codex"].status == dr.SKIP

    # O doctor de verdade traz as quatro checagens, e so le.
    ids = [c["id"] for c in _core.doctor(str(repo))["checks"]]
    assert ids[-4:] == [
        "integracao_claude", "integracao_devin", "integracao_codex", "integracao_copilot"
    ]

    # detach pela CLI tira a integracao; o doctor volta a dizer ausente.
    assert cli_main(["detach", "devin"]) == 0
    capsys.readouterr()
    depois = dr.avaliar_integracoes(status(home=home)["manifest"], None, None)
    assert {c.status for c in depois} == {dr.SKIP}
    assert dr.avaliar_integracoes(None, "JSONDecodeError: x", None)[0].status == dr.WARN
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_integrate.py::test_doctor_informa_integracao_por_host -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: erro de coleta com `ImportError: cannot import name 'status' from
'sparkforge.integrate'`.

### 3. Código mínimo

`sparkforge/integrate/__init__.py`, inteiro (acrescenta `status`):

```python
"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import claude as _claude
from sparkforge.integrate import conflict as _conflict
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import HOSTS, Host, mcp_command, mcp_entry
from sparkforge.integrate.hosts import host as _host

INTEGRAVEIS = HOSTS


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _configurar(
    h: Host, *, home: Path, manifesto: dict[str, Any], dry_run: bool, python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None:
        return []
    if h.mcp_format == "toml":
        comando, args = mcp_command(python)
        return [
            writer.apply_toml_config(
                h.name, h.mcp_config, writer.toml_block(comando, args),
                home=home, manifesto=manifesto, dry_run=dry_run,
            )
        ]
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            home=home, manifesto=manifesto, dry_run=dry_run,
        )
    ]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recusas = [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]
    for r in relatorios:
        for config in r.get("config") or []:
            if config["status"] == "refused":
                recusas.append({"host": r["host"], "reason": config["reason"],
                                "path": config["path"]})
        cli = r.get("claude_cli") or {}
        if cli.get("status") == "refused":
            recusas.append({"host": r["host"], **{k: v for k, v in cli.items() if k != "status"}})
    return recusas


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    python: str | None = None,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
    root: Path | None = None,
    repo: Path | None = None,
    on_conflict: str | None = None,
    interactive: bool = False,
    prompt: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`.

    Com `repo`, confere a copia vendorizada em dobro nele e aplica a escolha do
    operador (D9); e a unica escrita possivel dentro de um repositorio."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        if nome == "claude":
            plano += _claude.plugin_files(home, version=__version__, python=python)
        primeira = not (manifesto["hosts"].get("claude") or {}).get("registered")
        relatorio = writer.apply_files(
            nome, plano, home=home, manifesto=manifesto, version=__version__,
            dry_run=dry_run,
        )
        relatorio["config"] = _configurar(
            h, home=home, manifesto=manifesto, dry_run=dry_run, python=python
        )
        if nome == "claude":
            cli = _claude.register(
                home, primeira=primeira,
                mudou=bool(relatorio["written"] or relatorio["removed"]),
                dry_run=dry_run, runner=runner, which=which,
            )
            relatorio["claude_cli"] = cli
            if cli["status"] == "ok":
                manifesto["hosts"]["claude"]["registered"] = True
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(home, manifesto)
    resultado: dict[str, Any] = {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }
    if repo is not None:
        resultado["conflict"] = _conferir_copia(
            Path(repo), raiz, dry_run=dry_run, on_conflict=on_conflict,
            interactive=interactive, prompt=prompt,
        )
    return resultado


def _conferir_copia(
    repo: Path,
    raiz: Path,
    *,
    dry_run: bool,
    on_conflict: str | None,
    interactive: bool,
    prompt: Callable[[str], str] | None,
) -> dict[str, Any]:
    achado = _conflict.detect(repo, root=raiz)
    colisoes = achado["collisions"]
    if achado["refused"]:
        escolha = "ignore"
    else:
        escolha = _conflict.choose(
            colisoes, on_conflict=on_conflict, interactive=interactive, prompt=prompt
        )
    resolucao = _conflict.resolve(repo, colisoes, escolha, dry_run=dry_run)
    return {
        "collisions": [
            {k: c[k] for k in ("name", "kind", "location", "identical")} for c in colisoes
        ],
        **resolucao,
        "refused": achado["refused"],
    }


def detach(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
) -> dict[str, Any]:
    """Remove o que o manifesto registrou para `alvo` (D7).

    So sai arquivo que ainda tem o sha256 gravado e que nenhum outro host usa;
    o editado depois fica, como recusa `editado_pelo_usuario`. Da config de
    usuario sai so a entrada que o integrate pos.
    """
    home = Path(home)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        entrada = manifesto["hosts"].get(nome)
        if entrada is None:
            relatorios.append({"host": nome, "status": "not_integrated", "refused": []})
            continue
        registros = list(entrada.get("config") or [])
        registrado = bool(entrada.get("registered"))
        relatorio = writer.remove_owned(
            home, manifesto, nome, list(entrada.get("files") or {}), dry_run=dry_run
        )
        relatorio["host"] = nome
        relatorio["status"] = "detached"
        relatorio["config"] = [
            writer.revert_config(registro, home=home, dry_run=dry_run)
            for registro in registros
        ]
        if nome == "claude" and registrado:
            relatorio["claude_cli"] = _claude.unregister(
                dry_run=dry_run, runner=runner, which=which
            )
        if not dry_run:
            del manifesto["hosts"][nome]
        relatorios.append(relatorio)
    if not dry_run:
        writer.drop_manifest_if_empty(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


def status(*, home: Path, repo: Path | None = None) -> dict[str, Any]:
    """O que o `doctor` le: o manifesto e, por host, a copia em dobro no `repo`."""
    manifesto = writer.load_manifest(Path(home))
    em_dobro: dict[str, list[str]] = {nome: [] for nome in HOSTS}
    if repo is not None:
        for colisao in _conflict.detect(Path(repo))["collisions"]:
            for nome in colisao["hosts"]:
                em_dobro[nome].append(f"{colisao['location']}/{colisao['name']}")
    return {"manifest": manifesto, "duplicated": em_dobro}


__all__ = ["INTEGRAVEIS", "detach", "integrate", "status"]
```

Em `sparkforge/doctor.py`, troque

```python
from typing import Any

OK, WARN
```

por

```python
from typing import Any

from sparkforge.integrate.hosts import HOSTS

OK, WARN
```

No mesmo arquivo, a função nova entra logo antes de `resumo`:

Em `sparkforge/doctor.py`, troque

```python
def resumo(checagens: list[Checagem], online: bool) -> dict[str, Any]:
```

por

```python
def avaliar_integracoes(
    manifesto: Mapping[str, Any] | None,
    erro: str | None,
    em_dobro: Mapping[str, list[str]] | None,
) -> list[Checagem]:
    """Uma checagem por host: integrado ou nao, em que versao do pacote, e a copia
    vendorizada em dobro no repositorio atual (INTEGRACAO_USUARIO, AC11)."""
    if erro:
        return [Checagem("integracao", WARN, f"manifesto de integracao nao lido: {erro}",
                         "sparkforge integrate all --scope user --dry-run")]
    hosts = (manifesto or {}).get("hosts") or {}
    checagens = []
    for host in HOSTS:
        ident = f"integracao_{host}"
        entrada = hosts.get(host)
        if entrada is None:
            checagens.append(Checagem(ident, SKIP, "integracao de usuario ausente",
                                      f"sparkforge integrate {host} --scope user"))
            continue
        versao = entrada.get("package_version") or "?"
        detalhe = (
            f"integrado pelo sparkforge {versao}, "
            f"{len(entrada.get('files') or {})} arquivo(s)"
        )
        dobro = sorted((em_dobro or {}).get(host) or [])
        if dobro:
            checagens.append(Checagem(
                ident, WARN,
                f"{detalhe}; copia vendorizada em dobro no repositorio: {', '.join(dobro)}",
                f"sparkforge integrate {host} --scope user --on-conflict merge",
            ))
            continue
        checagens.append(Checagem(ident, OK, detalhe))
    return checagens


def resumo(checagens: list[Checagem], online: bool) -> dict[str, Any]:
```

`sparkforge/adapters/_core.py`, no fim de `doctor()`. Esta é a porta da CLI **e** da
tool MCP `sparkforge_doctor`:

Em `sparkforge/adapters/_core.py`, troque

```python
    checagens.append(dr.avaliar_credencial(extras["boto3"], metodo, conta, erro, online))
    return dr.resumo(checagens, online=online)
```

por

```python
    checagens.append(dr.avaliar_credencial(extras["boto3"], metodo, conta, erro, online))

    def integracao() -> dict[str, Any]:
        from sparkforge.integrate import status as estado_da_integracao

        return estado_da_integracao(home=Path.home(), repo=Path(repo))

    estado, erro = sondar(integracao)
    checagens.extend(dr.avaliar_integracoes(
        (estado or {}).get("manifest"), erro, (estado or {}).get("duplicated")
    ))
    return dr.resumo(checagens, online=online)
```

`sparkforge/adapters/tools.py`, na descrição de `sparkforge_doctor`:

Em `sparkforge/adapters/tools.py`, troque

```python
            "Confere se o ambiente esta pronto, em nove checagens com status ok, warn, fail "
            "ou skip e o comando que resolve: pacote, extras, mcp, catalogo, packs, knowledge, "
            "indice_de_codigo, artefatos e credencial_aws. A credencial e conferida so "
```

por

```python
            "Confere se o ambiente esta pronto, em treze checagens com status ok, warn, fail "
            "ou skip e o comando que resolve: pacote, extras, mcp, catalogo, packs, knowledge, "
            "indice_de_codigo, artefatos, credencial_aws e uma por host da integracao de "
            "usuario (integracao_claude, integracao_devin, integracao_codex, "
            "integracao_copilot: presente, versao do pacote gravada e copia vendorizada em "
            "dobro no repositorio). A credencial e conferida so "
```

`sparkforge/adapters/cli.py`, quatro trocas. A ajuda do `doctor`:

Em `sparkforge/adapters/cli.py`, troque

```python
            "Confere se o ambiente esta pronto: pacote, extras, MCP, catalogo, packs, "
            "knowledge, indice de codigo, artefatos e credencial AWS. Sai 1 com alguma falha."
```

por

```python
            "Confere se o ambiente esta pronto: pacote, extras, MCP, catalogo, packs, "
            "knowledge, indice de codigo, artefatos, credencial AWS e a integracao de "
            "usuario de cada host. Sai 1 com alguma falha."
```

Os dois parsers novos, logo depois do `--online` do `doctor`:

Em `sparkforge/adapters/cli.py`, troque

```python
        help="Confirma a credencial na AWS (STS get_caller_identity). Unico modo com rede.",
    )
```

por

```python
        help="Confirma a credencial na AWS (STS get_caller_identity). Unico modo com rede.",
    )

    # integrate / detach --------------------------------------------------------
    # INTEGRACAO_USUARIO (D10): so CLI. Escrever no HOME e decisao do operador, e
    # um agente nao deve dispara-la sozinho -- por isso nao ha tool MCP.
    hosts_integraveis = ("claude", "devin", "codex", "copilot", "all")
    integrate_p = sub.add_parser(
        "integrate",
        help=(
            "Instala skills, agents e o MCP do SparkForge nos diretorios de USUARIO do host "
            "(Claude Code por marketplace local; Devin, Codex e Copilot CLI), a partir do "
            "pacote instalado. Nada e escrito no repositorio, exceto a remocao da copia "
            "vendorizada que o operador escolher."
        ),
    )
    integrate_p.add_argument("host", choices=hosts_integraveis, help="Host, ou all.")
    integrate_p.add_argument(
        "--scope", choices=("user",), required=True,
        help="Escopo da integracao; so user nesta versao.",
    )
    integrate_p.add_argument(
        "--dry-run", action="store_true", help="Lista o que seria escrito, sem escrever."
    )
    integrate_p.add_argument(
        "--on-conflict", choices=("overwrite", "merge", "ignore"), default=None,
        help=(
            "Copia vendorizada em dobro no repositorio atual: overwrite apaga do repo, "
            "merge apaga so o identico, ignore nao toca. Sem a flag e sem terminal: ignore."
        ),
    )
    detach_p = sub.add_parser(
        "detach",
        help=(
            "Remove a integracao de usuario do host: so o que o manifesto "
            "~/.sparkforge/integrations.json registrou e ainda tem o sha256 gravado."
        ),
    )
    detach_p.add_argument("host", choices=hosts_integraveis, help="Host, ou all.")
    detach_p.add_argument(
        "--scope", choices=("user",), default="user",
        help="Escopo da integracao; so user nesta versao.",
    )
    detach_p.add_argument(
        "--dry-run", action="store_true", help="Lista o que seria removido, sem remover."
    )
```

Os handlers, logo depois de `_cmd_doctor`:

Em `sparkforge/adapters/cli.py`, troque

```python
def _cmd_doctor(args: argparse.Namespace) -> int:
    resultado = _core.doctor(args.repo, online=args.online)
    _print(resultado)
    return 0 if resultado["healthy"] else 1
```

por

```python
def _cmd_doctor(args: argparse.Namespace) -> int:
    resultado = _core.doctor(args.repo, online=args.online)
    _print(resultado)
    return 0 if resultado["healthy"] else 1


def _perguntar(texto: str) -> str:
    """O prompt vai para o stderr: o stdout e o JSON do resultado."""
    print(texto, end="", file=sys.stderr, flush=True)
    return input()


def _cmd_integrate(args: argparse.Namespace) -> int:
    from sparkforge.integrate import integrate

    resultado = integrate(
        args.host,
        home=Path.home(),
        repo=Path.cwd(),
        dry_run=args.dry_run,
        on_conflict=args.on_conflict,
        interactive=sys.stdin.isatty() and sys.stderr.isatty(),
        prompt=_perguntar,
    )
    _print(resultado)
    return 1 if resultado["refused"] else 0


def _cmd_detach(args: argparse.Namespace) -> int:
    from sparkforge.integrate import detach

    resultado = detach(args.host, home=Path.home(), dry_run=args.dry_run)
    _print(resultado)
    return 1 if resultado["refused"] else 0
```

E a tabela `_DISPATCH`:

Em `sparkforge/adapters/cli.py`, troque

```python
    ("doctor", None): _cmd_doctor,
```

por

```python
    ("doctor", None): _cmd_doctor,
    ("integrate", None): _cmd_integrate,
    ("detach", None): _cmd_detach,
```

Os três testes que contam as checagens do `doctor` ou os verbos sem tool:

Em `tests/test_doctor.py`, troque

```python
    "indice_de_codigo", "artefatos", "credencial_aws",
]
```

por

```python
    "indice_de_codigo", "artefatos", "credencial_aws",
    "integracao_claude", "integracao_devin", "integracao_codex", "integracao_copilot",
]
```

Em `tests/test_adapters_tools.py`, troque

```python
        assert len(result["checks"]) == 9 and result["online"] is False, result
```

por

```python
        assert len(result["checks"]) == 13 and result["online"] is False, result
```

Em `tests/test_capability_parity.py`, troque

```python
        "autonomy show": (
            "mostra perfil de nível de autonomia L0-L5 — leitura de config, "
            "sem extração de facts nem julgamento."
        ),
    }
```

por

```python
        "autonomy show": (
            "mostra perfil de nível de autonomia L0-L5 — leitura de config, "
            "sem extração de facts nem julgamento."
        ),
        # INTEGRACAO_USUARIO (D10): escrever no HOME do usuario e decisao do
        # operador, e um agente nao deve dispara-la sozinho.
        "integrate": (
            "grava skills, agents e MCP no HOME do usuario; decisao do operador, "
            "que um agente nao deve disparar sozinho."
        ),
        "detach": (
            "remove a integracao do HOME do usuario; mesma razao de 'integrate'."
        ),
    }
```

Referência gerada. Ela é registro da tarefa que cria o verbo, e por isso roda aqui:

```bash
python scripts/gen_reference_docs.py
```

Isso regrava `docs/guia/referencia/README.md`, `cli/README.md`, `cli/doctor.md`,
`tools/README.md` e `tools/sparkforge_doctor.md`, e cria `cli/integrate.md` e
`cli/detach.md` (7 páginas na cópia medida).

### 4. Rodar e ver passar

O mesmo comando → `1 passed`. Depois os testes que esta tarefa editou:

```bash
python -m pytest tests/test_doctor.py tests/test_capability_parity.py tests/test_reference_docs.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

→ verde. Depois `python -m pytest tests/test_adapters_tools.py -k doctor -q -p no:cacheprovider --basetemp=E:/sfpt_iu` → verde.

### 5. Gates vizinhos

`python -m ruff check sparkforge tests/test_integrate.py tests/test_doctor.py tests/test_adapters_tools.py tests/test_capability_parity.py`.
Esta tarefa move `tool_or_verb`. A referência gerada entra aqui. O surface lock fica
**vermelho até a T10**, porque a descrição de `sparkforge_doctor` cresceu, e o
build_report registra isso. `tests/test_surface_lock.py` é o teste da T10.

### 6. Commit

`feat(cli): integrate and detach verbs, and a doctor check per integrated host`

## T10 — guias, README, STATUS e os gates de registro

### 1. O teste que falha

`tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_tool_catalogue_matches`
está vermelho desde a T9: `tools.total_bytes` do lock é menor que o medido, porque a
descrição de `sparkforge_doctor` cresceu. Tarefa sem teste próprio nomeia o gate que
falha antes.

```bash
python -m pytest tests/test_surface_lock.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

Falha esperada: `AssertionError` em `medida["tools"]["total_bytes"] == lock["tools"]["total_bytes"]`,
e em `test_the_by_name_composition_matches`.

### 2. Documentos

Em `docs/guia/02-instalacao.md`, troque

````markdown
## Instalar as skills e os agents em outro repositório

O pacote Python dá a CLI e o servidor MCP. As skills e os perfis de agent chegam a
outro repositório por `scripts/install_skills.py`, que escreve os diretórios de cada
plataforma.
````

por

````markdown
## Integrar uma vez por máquina: `sparkforge integrate`

Com o pacote instalado, um comando por host deixa skills, agents e o servidor MCP
disponíveis em **qualquer** repositório da máquina, sem copiar nada para dentro dele. O
conteúdo sai do próprio wheel (`sparkforge/integrate/bundle/`), com ou sem acesso ao
GitHub.

```bash
sparkforge integrate all --scope user --dry-run    # lista o que seria escrito
sparkforge integrate all --scope user              # claude, devin, codex e copilot
sparkforge integrate devin --scope user            # um host só
sparkforge doctor                                  # integracao_<host>: presente, versão, cópia em dobro
sparkforge detach all                              # remove só o que o SparkForge escreveu
```

| Host | Agents | Skills | MCP |
|---|---|---|---|
| Claude Code | plugin `sparkforge-aws` do marketplace local `sparkforge-local`, em `~/.sparkforge/claude/` | no plugin | `.mcp.json` do plugin |
| Devin CLI | `~/.config/devin/agents/` (`%APPDATA%\devin\agents\` no Windows) | `~/.agents/skills/` | `~/.config/devin/mcp_config.json`, chave `mcpServers.sparkforge` |
| Codex CLI | `~/.codex/agents/*.toml` | `~/.agents/skills/` | bloco marcado `[mcp_servers.sparkforge]` em `~/.codex/config.toml` |
| Copilot CLI | `~/.copilot/agents/*.agent.md` | `~/.agents/skills/` | `~/.copilot/mcp-config.json`, chave `mcpServers.sparkforge` |

O Claude Code é registrado pelo próprio CLI dele (`claude plugin marketplace add` e
`claude plugin install`). Sem o binário `claude` no PATH, o plugin fica montado e o
comando sai 1 com a recusa `claude_cli_ausente` e os dois comandos para você rodar.

O servidor MCP é chamado pelo Python que tem o `sparkforge` instalado, sem
`PYTHONPATH` para repositório nenhum. Config de usuário que já existia é mesclada, nunca
sobrescrita: só a entrada `sparkforge` entra, e um `sparkforge` que você mesmo escreveu
sai como recusa `sparkforge_ja_configurado`, sem tocar no arquivo.

Tudo o que é gravado fica em `~/.sparkforge/integrations.json`, com o sha256 de cada
arquivo. Rodar de novo não muda nada. `detach` remove só o que o manifesto registrou e
ainda tem o sha256 gravado: arquivo que você editou depois fica, e sai como recusa
`editado_pelo_usuario`.

**Cópia em dobro no repositório.** Se o repositório de onde você chama o comando tem a
cópia do `install_skills.py` (`.claude/skills`, `.agents/skills`, `.claude/agents`,
`.agents/agents`, `.github/agents`), o `integrate` lista os nomes repetidos e pergunta:
sobrescrever (apaga a cópia do repo), mesclar (apaga só o que é idêntico ao que o pacote
instala e lista o customizado) ou ignorar (não toca no repo). `--on-conflict
overwrite|merge|ignore` responde sem prompt; sem terminal e sem a flag, a resposta é
ignorar. Toda remoção respeita `--dry-run`.

Fora desta versão: Copilot no VS Code (o caminho do MCP de usuário não foi confirmado na
documentação oficial) e o Copilot coding agent na nuvem, que não tem escopo de usuário e
continua lendo `.github/agents` do repositório.

## Instalar as skills e os agents em outro repositório

O caminho de cima (`sparkforge integrate`) instala uma vez por máquina. A cópia por
repositório continua existindo para quando os arquivos precisam estar versionados
dentro do projeto -- o Copilot coding agent na nuvem, por exemplo, só lê
`.github/agents` do repositório. As skills e os perfis de agent chegam a outro
repositório por `scripts/install_skills.py`, que escreve os diretórios de cada
plataforma.
````

Em `docs/guia/03-cli.md`, troque

```markdown
### Inteligência de código
```

por

```markdown
### Integração por usuário

| Comando | O que faz | Referência |
|---|---|---|
| `integrate` | Instala skills, agents e o MCP nos diretórios de usuário do host (`claude`, `devin`, `codex`, `copilot` ou `all`), a partir do pacote instalado; `--scope user`, `--dry-run`, `--on-conflict`. | [integrate](referencia/cli/integrate.md) |
| `detach` | Remove a integração de usuário: só o que `~/.sparkforge/integrations.json` registrou e ainda tem o sha256 gravado. | [detach](referencia/cli/detach.md) |

Sem tool MCP de propósito: escrever no HOME é decisão do operador. O detalhe está em [Instalação](02-instalacao.md#integrar-uma-vez-por-máquina-sparkforge-integrate).

### Inteligência de código
```

Em `README.md`, troque

````markdown
a anatomia de cada comando e um fluxo rodado de verdade em [CLI](docs/guia/03-cli.md).
````

por

````markdown
a anatomia de cada comando e um fluxo rodado de verdade em [CLI](docs/guia/03-cli.md).

Para usar o SparkForge em qualquer repositório da máquina sem copiar nada para ele, integre uma vez por host:

```bash
sparkforge integrate all --scope user   # Claude Code, Devin, Codex e Copilot CLI
sparkforge detach all                   # desfaz, removendo só o que foi escrito
```

Os caminhos de cada host e a cópia em dobro no repositório estão em [Instalação](docs/guia/02-instalacao.md#integrar-uma-vez-por-máquina-sparkforge-integrate).
````

Em `docs/superpowers/STATUS.md`, acrescente ao fim do arquivo, depois da seção de
`LF_GRANTS`:

````markdown

## INTEGRACAO_USUARIO — instalar uma vez por máquina, usar em qualquer repositório — **BUILD CONCLUÍDO** (T1–T10; ship pendente)

O SparkForge chegava a um repositório por cópia (`scripts/install_skills.py`). Agora
`sparkforge integrate <claude|devin|codex|copilot|all> --scope user` instala skills,
agents e o MCP nos diretórios de usuário de cada host, a partir do wheel, e
`sparkforge detach` desfaz. O ciclo SDD está em `docs/sdd/INTEGRACAO_USUARIO/`.

**O que foi entregue.** O wheel embute `skills/` e `agents/` em
`sparkforge/integrate/bundle/`. O renderizador por plataforma saiu de
`scripts/sync_skills.py` para `sparkforge/integrate/render.py`, com a plataforma
`codex`, e é um só para os espelhos do repositório e para a integração. Claude Code
entra por marketplace local em `~/.sparkforge/claude/`, registrado pelo `claude
plugin`. Devin, Codex e Copilot CLI recebem os agents nos diretórios globais, as skills
em `~/.agents/skills` e o MCP mesclado na config de usuário. Tudo o que é escrito fica
em `~/.sparkforge/integrations.json`, com sha256. A cópia vendorizada em dobro no
repositório é detectada e resolvida por escolha do operador. O `doctor` ganhou uma
checagem por host.

**Limites declarados.** Copilot no VS Code e o Copilot coding agent na nuvem ficam de
fora. O espelho `.codex/agents/*.toml` do repositório continua mantido à mão. Os
executores não vão para o Codex, porque não têm `description`. A validade do TOML do
usuário não é conferida no Python 3.10: só o par de marcadores é conferido.
````

Na tabela *Números correntes* nada muda: nenhuma tool, regra, extrator, skill ou agent
novo. `python scripts/check_status_numbers.py --strict` confere isso. Se ele acusar
uma dimensão, troque o número em negrito da linha dela pelo valor medido que o gate
imprime.

### 3. Registros de número

Rode na ordem, a partir da árvore limpa (`git status --ignored` sem diretório ignorado
com `.py`):

1. `python scripts/check_surface_lock.py --update` e declare o crescimento de
   `tools.total_bytes` na mensagem do commit (regra 26).
2. `python scripts/check_vnext_claims.py`. Para cada id que o gate listar, as
   alegações de tamanho de corpus que os sete `.py` novos e o `tests/test_integrate.py`
   moveram:
   - rode o `proof.cmd` da entrada em `docs/claims.lock.json`;
   - troque o número na linha `line` de `doc`, que hoje é
     `docs/harness/CODEINTEL-GAP.md`;
   - atualize `context` e `line` da entrada com o texto novo daquela linha;
   - acrescente à `note` uma frase no molde das que já estão lá: "Relida na T10 de
     INTEGRACAO_USUARIO", a data do dia e os dois números medidos, o anterior e o novo,
     separados por `->`.

   Remedie pela lista de ids, nunca por varredura, e **nunca** com `--seed`. Rode o
   gate de novo até `0 divergencia(s)`.
3. `python scripts/check_status_numbers.py --strict` → `0 divergencia(s)`.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_surface_lock.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
```

→ verde. Depois, um por vez, os gates que as tarefas anteriores moveram:

```bash
python scripts/sync_skills.py --check
python -m pytest tests/test_sync_render.py tests/test_agents_parity.py tests/test_skill_content.py tests/test_agent_coverage.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
python -m pytest tests/test_arvore_versionada.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
python -m pytest tests/test_capability_parity.py tests/test_doctor.py tests/test_journal.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
python -m pytest tests/test_adapters_tools.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
python scripts/gen_reference_docs.py --check
python -m pytest tests/test_reference_docs.py tests/test_docs_coverage.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
python -m pytest tests/test_artifact_contents.py tests/test_verify_wheel.py tests/test_suite_batches.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
python -m pytest tests/test_integrate.py -q -p no:cacheprovider --basetemp=E:/sfpt_iu
python scripts/gen_requirements.py --check
python -m ruff check sparkforge scripts tests
```

E o comando do AC12, que é `verified_by` do define:

```bash
python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py --strict && python scripts/verify_wheel.py
```

→ os quatro saem 0. O `verify_wheel` leva minutos: constrói wheel e sdist duas vezes
e roda os goldens num venv limpo. Anote o tamanho do `.whl` que ele constrói. Esse é
o SC2, e o do `main` sai de `python -m build --wheel` num checkout de `main`.
`tests/test_arvore_versionada.py` confere o **commit**, então rode depois do commit
da T2 em diante.

### 5. Gates vizinhos

Os de cima são os gates de `tool_or_verb`, `agent_or_skill`, `disk_read`,
`dependency`, `status_numbers` e `claims` (`docs/gates-por-mudanca.md`). A suíte
inteira roda em lotes, um por vez (`tests/test_suite_batches.py::LOTES`), no `sdd-build`.

### 6. Commit

`docs(integrate): install once per machine; registries and surface growth`, com o
crescimento de `tools.total_bytes` declarado no corpo.
