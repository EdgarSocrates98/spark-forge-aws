"""`sparkforge integrate` e `sparkforge detach`: a integracao por usuario.

Todo teste aponta HOME, USERPROFILE e APPDATA para `tmp_path` e injeta o executor
do `claude`: nenhum teste toca o HOME real nem chama o binario `claude` de verdade.
Spec: docs/sdd/INTEGRACAO_USUARIO/define.md.
"""
from __future__ import annotations

import ast
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from sparkforge.integrate import render, sources

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
