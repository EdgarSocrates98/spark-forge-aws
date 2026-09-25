"""`sparkforge integrate` e `sparkforge detach`: a integracao por usuario.

Todo teste aponta HOME, USERPROFILE e APPDATA para `tmp_path` e injeta o executor
do `claude`: nenhum teste toca o HOME real nem chama o binario `claude` de verdade.
Spec: docs/sdd/INTEGRACAO_USUARIO/define.md.
"""
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


def _frontmatter_yaml(texto: str) -> dict:
    """O frontmatter pelo leitor de YAML de verdade: o valor que o Codex deve receber."""
    import yaml

    texto = texto.replace("\r\n", "\n")
    return yaml.safe_load(texto[len("---\n"): texto.index("\n---", 3)])


def test_codex_toml_escapa_controle_que_o_json_deixa():
    tomllib = pytest.importorskip("tomllib")
    texto = "---\nname: x\ndescription: d\x7fe\n---\ncorpo \x7f fim\x1f\ttab\n"
    saida = render.render_agent(texto, "codex")
    assert "\x7f" not in saida
    dados = tomllib.loads(saida)
    assert dados["description"] == "d\x7fe"
    assert dados["developer_instructions"] == "corpo \x7f fim\x1f\ttab\n"


@pytest.mark.parametrize(
    "linhas",
    [
        "description: >-\n  dobrado\n  em duas",
        "description: |\n  literal",
        "description: >\n  dobrado",
        'description: "com \\"escape\\""',
        "description: plano que\n  continua na linha de baixo",
    ],
)
def test_codex_recusa_escalar_yaml_que_nao_le(linhas):
    texto = f"---\nname: x\n{linhas}\ntools: Read\n---\ncorpo\n"
    with pytest.raises(ValueError, match="escalar_yaml_nao_suportado"):
        render.render_agent(texto, "codex")


def test_codex_le_as_aspas_que_sabe_ler():
    tomllib = pytest.importorskip("tomllib")
    for linha, esperado in [
        ("description: 'it''s'", "it's"),
        ('description: "sem escape"', "sem escape"),
        ("description: plano - com hifen", "plano - com hifen"),
    ]:
        texto = f"---\nname: x\n{linha}\n---\ncorpo\n"
        dados = tomllib.loads(render.render_agent(texto, "codex"))
        assert dados["description"] == esperado, linha


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
        assert dados["description"] == _frontmatter_yaml(texto)["description"], src
        assert dados["developer_instructions"] == _corpo_do_markdown(texto)
    exemplo = sources.skill_files(ROOT)[0]
    assert render.render_skill_file(
        exemplo, skills_root, "codex", agents_src=agents_src
    ) == exemplo.read_bytes()
    with pytest.raises(ValueError, match="description"):
        render.render_agent("---\nname: x\n---\ncorpo\n", "codex")


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
