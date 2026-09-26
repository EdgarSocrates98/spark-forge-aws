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
from sparkforge import doctor as dr
from sparkforge.adapters import _core
from sparkforge.adapters.cli import main as cli_main
from sparkforge.integrate import detach, integrate, render, sources, status

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _home_isolado(tmp_path, monkeypatch):
    casa = tmp_path / "home_padrao"
    casa.mkdir()
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.setenv("APPDATA", str(casa / "AppData" / "Roaming"))
    # Sem `which`/`runner` injetados, o `claude` e sempre "ausente": nenhum teste
    # chega ao binario de verdade, nem pelo `all`.
    from sparkforge.integrate import claude as _claude

    def _nunca(argv):
        raise AssertionError(f"teste chamou o binario claude: {argv}")

    monkeypatch.setattr(_claude, "WHICH_PADRAO", lambda _nome: None)
    monkeypatch.setattr(_claude, "RUNNER_PADRAO", _nunca)


def _relativos(base: Path) -> list[str]:
    return sorted(
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )


def test_wheel_embute_skills_e_agents(tmp_path):
    # So a AUSENCIA do modulo `build` pula; com ele instalado, build que falha e
    # vermelho -- um skip aqui esconderia justamente o empacotamento quebrado.
    pytest.importorskip("build")
    out = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, f"`python -m build` falhou: {build.stderr[-800:]}"
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


def test_o_gravado_por_integrate_e_o_espelho_do_repo(tmp_path):
    """AC6 pelo que chega ao disco: um erro na tabela de `hosts.py` (plataforma,
    padrao de nome ou diretorio trocado) fica vermelho aqui."""
    home = tmp_path / "home"
    for nome in ("devin", "copilot", "codex"):
        assert integrate(nome, home=home, windows=False)["refused"] == []

    espelho = _conteudo(ROOT / ".agents" / "skills")
    assert _conteudo(home / ".agents" / "skills") == espelho
    assert _conteudo(home / ".config" / "devin" / "agents") == _conteudo(
        ROOT / ".agents" / "agents"
    )
    assert _conteudo(home / ".copilot" / "agents") == _conteudo(ROOT / ".github" / "agents")

    tomllib = pytest.importorskip("tomllib")
    gravados = sorted((home / ".codex" / "agents").glob("*.toml"))
    assert [p.stem for p in gravados] == [p.stem for p in sources.agent_files(ROOT)]
    for arquivo in gravados:
        texto = (ROOT / "agents" / f"{arquivo.stem}.md").read_text(encoding="utf-8")
        dados = tomllib.loads(arquivo.read_text(encoding="utf-8"))
        frente = _frontmatter_yaml(texto)
        assert dados == {
            "name": frente["name"],
            "description": frente["description"],
            "developer_instructions": _corpo_do_markdown(texto),
        }, arquivo.name


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
    arquivos = {
        relativo: registro["sha256"]
        for relativo, registro in manifesto["files"].items()
        if "devin" in registro["owners"]
    }
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


# `sparkforge` escrito a mao, em cada forma que o TOML aceita para a mesma chave.
FORMAS_TOML = {
    "tabela": '[mcp_servers.sparkforge]\ncommand = "meu"\n',
    "aspas_duplas": '[mcp_servers."sparkforge"]\ncommand = "meu"\n',
    "aspas_simples": "[mcp_servers.'sparkforge']\ncommand = \"meu\"\n",
    "espacos": '[ mcp_servers . sparkforge ]\ncommand = "meu"\n',
    "inline_sob_mcp_servers": '[mcp_servers]\nsparkforge = { command = "meu" }\n',
    "pontuada_sob_mcp_servers": '[mcp_servers]\nsparkforge.command = "meu"\n',
    "pontuada_na_raiz": 'mcp_servers.sparkforge.command = "meu"\n',
    "subtabela_env": '[mcp_servers.sparkforge.env]\nX = "1"\n',
}


def _home_codex(base: Path, texto: str) -> tuple[Path, Path]:
    config = base / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_bytes(texto.encode("utf-8"))
    return base, config


@pytest.mark.parametrize("forma", sorted(FORMAS_TOML))
def test_codex_recusa_sparkforge_a_mao_em_qualquer_forma(tmp_path, forma):
    from sparkforge.integrate import writer

    texto = FORMAS_TOML[forma]
    home, config = _home_codex(tmp_path / "home", texto)
    recusado = integrate("codex", home=home, root=_raiz_minima(tmp_path))
    assert [r["reason"] for r in recusado["refused"]] == ["sparkforge_ja_configurado"]
    assert config.read_bytes() == texto.encode("utf-8")
    # O caminho do Python 3.10 (sem tomllib) reconhece a mesma forma pelo texto.
    assert writer._sparkforge_por_texto(texto), forma


@pytest.mark.parametrize("texto", [
    '[mcp_servers.outro]\nnota = "sparkforge"\n',
    '# [mcp_servers.sparkforge]\nmodel = "x"\n',
    '[mcp_servers.sparkforge_x]\ncommand = "y"\n',
    '[outra]\nsparkforge = 1\n',
])
def test_regex_do_310_nao_acusa_o_que_nao_e_sparkforge(texto):
    from sparkforge.integrate import writer

    assert not writer._sparkforge_por_texto(texto)


def test_marcador_so_conta_no_inicio_da_linha(tmp_path):
    texto = 'nota = "# >>> sparkforge (gerenciado)"\n'
    home, config = _home_codex(tmp_path / "home", texto)
    assert integrate("codex", home=home, root=_raiz_minima(tmp_path))["refused"] == []
    assert config.read_text(encoding="utf-8").startswith(texto)
    assert detach("codex", home=home)["refused"] == []
    assert config.read_bytes() == texto.encode("utf-8")


@pytest.mark.parametrize("caso", ["dois_blocos", "sem_fim", "fim_antes"])
def test_bloco_toml_quebrado_recusa_sem_tocar(tmp_path, caso):
    from sparkforge.integrate import writer

    bloco = writer.toml_block("py", ["-m", "x"])
    inicio, resto = bloco.split("\n", 1)
    texto = {
        "dois_blocos": bloco + "\n" + bloco,
        "sem_fim": inicio + "\n",
        "fim_antes": resto + inicio + "\n",
    }[caso]
    home, config = _home_codex(tmp_path / "home", texto)
    recusado = integrate("codex", home=home, root=_raiz_minima(tmp_path))
    assert [r["reason"] for r in recusado["refused"]] == ["bloco_toml_quebrado"]
    assert config.read_bytes() == texto.encode("utf-8")


@pytest.mark.parametrize("texto", [
    "model = \n",
    'mcp_servers = { outro = { command = "x" } }\n',
])
def test_toml_invalido_antes_ou_depois_recusa_config_invalida(tmp_path, texto):
    pytest.importorskip("tomllib")
    home, config = _home_codex(tmp_path / "home", texto)
    recusado = integrate("codex", home=home, root=_raiz_minima(tmp_path))
    assert [r["reason"] for r in recusado["refused"]] == ["config_invalida"]
    assert config.read_bytes() == texto.encode("utf-8")


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


# --------------------------------------------------------------------------
# Manifesto por arquivo: um sha256 e o conjunto de donos (D5)
# --------------------------------------------------------------------------

AGENT_FALSO = "---\nname: sf-falso\ndescription: agent de teste\n---\ncorpo\n"


def _skill(nome: str) -> str:
    return f"---\nname: {nome}\ndescription: skill de teste\n---\ncorpo\n"


def _raiz_falsa(base: Path, arquivos: dict[str, str]) -> Path:
    """Uma raiz com `skills/` e `agents/` minimos: `arquivos` e {relativo: texto}."""
    for relativo, texto in {"agents/sf-falso.md": AGENT_FALSO, **arquivos}.items():
        caminho = base / relativo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(texto.encode("utf-8"))
    return base


def _manifesto(home: Path) -> dict:
    return json.loads((home / ".sparkforge" / "integrations.json").read_text("utf-8"))


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def test_skill_compartilhada_sobe_de_versao_sem_recusa_falsa(tmp_path):
    home = tmp_path / "home"

    def versao(n: int, ref: str) -> Path:
        return _raiz_falsa(tmp_path / f"v{n}", {
            "skills/sdd-plan/SKILL.md": _skill("sdd-plan"),
            "skills/sdd-plan/ref.md": ref,
        })

    v1, v2, v3 = versao(1, "A\n"), versao(2, "B\n"), versao(3, "C\n")
    ref = home / ".agents" / "skills" / "sdd-plan" / "ref.md"
    for nome in ("devin", "codex", "copilot"):
        assert integrate(nome, home=home, windows=False, root=v1)["refused"] == []
    # So o Devin sobe para v2: os outros donos continuam donos do MESMO arquivo.
    assert integrate("devin", home=home, windows=False, root=v2)["refused"] == []
    assert ref.read_text(encoding="utf-8") == "B\n"
    for nome in ("codex", "copilot", "devin"):
        resultado = integrate(nome, home=home, windows=False, root=v3)
        assert resultado["refused"] == [], (nome, resultado["refused"])
    assert ref.read_text(encoding="utf-8") == "C\n"
    manifesto = _manifesto(home)
    assert manifesto["schema"] == 2
    assert manifesto["files"][".agents/skills/sdd-plan/ref.md"] == {
        "sha256": _sha("C\n"), "owners": ["codex", "copilot", "devin"],
    }

    for nome in ("devin", "codex", "copilot"):
        assert detach(nome, home=home)["refused"] == []
    assert not (home / ".agents").exists()


def test_skill_removida_do_bundle_sai_quando_o_ultimo_dono_sai(tmp_path):
    home = tmp_path / "home"
    comum = {"skills/sdd-plan/SKILL.md": _skill("sdd-plan")}
    v1 = _raiz_falsa(tmp_path / "v1", {
        **comum, "skills/sdd-build/SKILL.md": _skill("sdd-build"),
        "skills/sdd-build/ref.md": "X\n",
    })
    v2 = _raiz_falsa(tmp_path / "v2", {
        **comum, "skills/sdd-build/SKILL.md": _skill("sdd-build"),
        "skills/sdd-build/ref.md": "Y\n",
    })
    v3 = _raiz_falsa(tmp_path / "v3", comum)
    build = home / ".agents" / "skills" / "sdd-build"
    for nome in ("devin", "codex"):
        assert integrate(nome, home=home, windows=False, root=v1)["refused"] == []
    assert integrate("devin", home=home, windows=False, root=v2)["refused"] == []

    # A skill sai do bundle: o Devin deixa de ser dono, o Codex ainda e.
    assert integrate("devin", home=home, windows=False, root=v3)["refused"] == []
    assert (build / "ref.md").read_text(encoding="utf-8") == "Y\n"
    # O Codex, ultimo dono, sai dela: o arquivo sai do disco, sem orfao.
    resultado = integrate("codex", home=home, windows=False, root=v3)
    assert resultado["refused"] == []
    assert not build.exists()
    assert not [k for k in _manifesto(home)["files"] if "sdd-build" in k]


def test_manifesto_v1_migra_para_um_sha_por_arquivo(tmp_path):
    from sparkforge.integrate import writer

    home = tmp_path / "home"
    compartilhado = home / ".agents" / "skills" / "sdd-plan" / "SKILL.md"
    compartilhado.parent.mkdir(parents=True)
    compartilhado.write_bytes(b"B\n")
    v1 = {
        "schema": 1,
        "hosts": {
            "codex": {"package_version": "0.1", "config": [],
                      "files": {".agents/skills/sdd-plan/SKILL.md": _sha("A\n")}},
            "devin": {"package_version": "0.2", "config": [],
                      "files": {".agents/skills/sdd-plan/SKILL.md": _sha("B\n"),
                                ".config/devin/agents/x.md": _sha("x\n")}},
        },
    }
    caminho = home / ".sparkforge" / "integrations.json"
    caminho.parent.mkdir(parents=True)
    caminho.write_text(json.dumps(v1), encoding="utf-8")
    manifesto = writer.load_manifest(home)
    assert manifesto["schema"] == 2
    # Com donos divergentes, vale o sha que esta em disco.
    assert manifesto["files"] == {
        ".agents/skills/sdd-plan/SKILL.md": {"sha256": _sha("B\n"), "owners": ["codex", "devin"]},
        ".config/devin/agents/x.md": {"sha256": _sha("x\n"), "owners": ["devin"]},
    }
    assert manifesto["hosts"]["devin"] == {"package_version": "0.2", "config": []}


def test_arquivo_preexistente_identico_nunca_sai_no_detach(tmp_path):
    raiz = _raiz_falsa(tmp_path / "raiz", {"skills/sdd-plan/SKILL.md": _skill("sdd-plan")})
    modelo = tmp_path / "modelo"
    integrate("copilot", home=modelo, root=raiz)
    relativo = ".agents/skills/sdd-plan/SKILL.md"

    home = tmp_path / "home"
    preexistente = home / relativo
    preexistente.parent.mkdir(parents=True)
    preexistente.write_bytes((modelo / relativo).read_bytes())
    antes = preexistente.read_bytes()

    assert integrate("copilot", home=home, root=raiz)["refused"] == []
    manifesto = _manifesto(home)
    resultado = detach("copilot", home=home)
    assert preexistente.is_file(), "o detach apagou arquivo que ja estava no HOME"
    assert preexistente.read_bytes() == antes
    assert not (home / ".copilot" / "agents").exists()
    assert resultado["refused"] == []
    assert relativo in resultado["hosts"][0]["kept_preexisting"]
    assert relativo not in resultado["hosts"][0]["removed"]
    assert manifesto["files"][relativo]["preexistente"] is True


def test_preexistente_nao_e_regravado_quando_o_bundle_muda(tmp_path):
    def versao(n: int, ref: str) -> Path:
        return _raiz_falsa(tmp_path / f"v{n}", {
            "skills/sdd-plan/SKILL.md": _skill("sdd-plan"),
            "skills/sdd-plan/ref.md": ref,
        })

    v1, v2, v3 = versao(1, "A\n"), versao(2, "B\n"), versao(3, "C\n")
    relativo = ".agents/skills/sdd-plan/ref.md"
    home = tmp_path / "home"
    ref = home / relativo
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"A\n")

    assert integrate("copilot", home=home, root=v1)["refused"] == []
    assert _manifesto(home)["files"][relativo]["preexistente"] is True
    for raiz in (v2, v3):
        resultado = integrate("copilot", home=home, root=raiz)
        assert resultado["refused"] == [], raiz.name
        assert ref.read_bytes() == b"A\n", "o preexistente foi regravado"
        (host,) = resultado["hosts"]
        assert host["preexisting"] == [
            {"path": relativo, "status": "preexistente_desatualizado"}
        ], raiz.name
        assert relativo not in host["written"]
        registro = _manifesto(home)["files"][relativo]
        assert (registro["sha256"], registro["preexistente"]) == (_sha("A\n"), True)

    resultado = detach("copilot", home=home)
    assert resultado["refused"] == []
    assert ref.read_bytes() == b"A\n"


def test_orfao_preexistente_aparece_no_relatorio(tmp_path):
    comum = {"skills/sdd-plan/SKILL.md": _skill("sdd-plan")}
    v1 = _raiz_falsa(tmp_path / "v1", {**comum, "skills/sdd-build/SKILL.md": _skill("sdd-build")})
    v2 = _raiz_falsa(tmp_path / "v2", comum)
    modelo = tmp_path / "modelo"
    integrate("copilot", home=modelo, root=v1)
    relativo = ".agents/skills/sdd-build/SKILL.md"
    home = tmp_path / "home"
    (home / relativo).parent.mkdir(parents=True)
    (home / relativo).write_bytes((modelo / relativo).read_bytes())

    assert integrate("copilot", home=home, root=v1)["refused"] == []
    (host,) = integrate("copilot", home=home, root=v2)["hosts"]
    assert host["kept_preexisting"] == [relativo]
    assert (home / relativo).is_file()


def test_arquivo_registrado_fora_do_disco_sai_absent(tmp_path):
    home = tmp_path / "home"
    assert integrate("copilot", home=home, root=_raiz_minima(tmp_path))["refused"] == []
    relativo = ".copilot/agents/sf-falso.agent.md"
    (home / relativo).unlink()
    (host,) = detach("copilot", home=home)["hosts"]
    assert relativo in host["absent"]
    assert relativo not in host["removed"]


def test_appdata_divergente_recusa_sem_tocar(tmp_path):
    raiz = _raiz_minima(tmp_path)
    home = tmp_path / "home"
    certo, outro = tmp_path / "appdata_a", tmp_path / "appdata_b"
    assert integrate("devin", home=home, windows=True, appdata=certo, root=raiz)["refused"] == []
    antes = _foto(tmp_path)

    for resultado in (
        detach("devin", home=home, appdata=outro),
        integrate("devin", home=home, windows=True, appdata=outro, root=raiz),
    ):
        (recusa,) = resultado["refused"]
        assert recusa["reason"] == "appdata_divergente"
        assert resultado["hosts"] == []
    assert _foto(tmp_path) == antes, "com APPDATA divergente, algo foi tocado"

    assert detach("devin", home=home, appdata=certo)["refused"] == []
    assert not (certo / "devin").exists()


def test_manifesto_de_versao_futura_recusa(tmp_path):
    raiz = _raiz_minima(tmp_path)
    home = tmp_path / "home"
    assert integrate("copilot", home=home, root=raiz)["refused"] == []
    caminho = home / ".sparkforge" / "integrations.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["schema"] = 99
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    antes = _foto(home)
    for resultado in (integrate("copilot", home=home, root=raiz), detach("copilot", home=home)):
        (recusa,) = resultado["refused"]
        assert recusa["reason"] == "manifesto_de_versao_futura"
        assert resultado["hosts"] == []
    assert _foto(home) == antes


def test_poda_nao_remove_diretorio_que_ja_existia(tmp_path):
    home = tmp_path / "home"
    for relativo in (".copilot/agents", ".agents", ".sparkforge"):
        (home / relativo).mkdir(parents=True)
    assert integrate("copilot", home=home, root=_raiz_minima(tmp_path))["refused"] == []
    assert detach("copilot", home=home)["refused"] == []
    for relativo in (".copilot/agents", ".agents", ".sparkforge"):
        assert (home / relativo).is_dir(), f"a poda removeu {relativo}, que ja existia"
    assert not (home / ".agents" / "skills").exists()
    assert not (home / ".sparkforge" / "integrations.json").exists()


# --------------------------------------------------------------------------
# Escrita atomica e manifesto que nao se deixa ler (recusas nomeadas)
# --------------------------------------------------------------------------


def _raiz_minima(tmp_path: Path) -> Path:
    return _raiz_falsa(tmp_path / "raiz", {"skills/sdd-plan/SKILL.md": _skill("sdd-plan")})


def test_escrita_atomica_nao_deixa_arquivo_pela_metade(tmp_path, monkeypatch):
    import os

    raiz = _raiz_minima(tmp_path)
    home = tmp_path / "home"
    config = home / ".copilot" / "mcp-config.json"
    config.parent.mkdir(parents=True)
    original = json.dumps({"mcpServers": {"outro": {"command": "node"}}})
    config.write_bytes(original.encode("utf-8"))

    def falha(*_args, **_kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", falha)
    with pytest.raises(OSError, match="disco cheio"):
        integrate("copilot", home=home, root=raiz)
    assert config.read_bytes() == original.encode("utf-8")
    assert _relativos(home) == [".copilot/mcp-config.json"], "sobrou temporario ou meio arquivo"


def test_escrita_atomica_da_config_deixa_a_original_intacta(tmp_path, monkeypatch):
    """Os agents e skills ja estao no HOME, identicos: a primeira escrita e a da
    config, e e so o `replace` dela que falha."""
    import os

    raiz = _raiz_minima(tmp_path)
    modelo = tmp_path / "modelo"
    integrate("copilot", home=modelo, root=raiz)
    home = tmp_path / "home"
    for relativo in _relativos(modelo):
        if relativo.startswith((".agents/", ".copilot/agents/")):
            destino = home / relativo
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes((modelo / relativo).read_bytes())
    config = home / ".copilot" / "mcp-config.json"
    original = json.dumps({"mcpServers": {"outro": {"command": "node"}}}).encode("utf-8")
    config.write_bytes(original)
    antes = set(_relativos(home))

    replace = os.replace

    def falha_na_config(origem, destino):
        if Path(destino).name == "mcp-config.json":
            raise OSError("disco cheio")
        return replace(origem, destino)

    monkeypatch.setattr(os, "replace", falha_na_config)
    with pytest.raises(OSError, match="disco cheio"):
        integrate("copilot", home=home, root=raiz)
    assert config.read_bytes() == original
    sobra = set(_relativos(home)) - antes - {".sparkforge/integrations.json"}
    assert sobra == set(), f"sobrou temporario ou meio arquivo: {sobra}"


def test_all_renderiza_todos_os_hosts_antes_da_primeira_escrita(tmp_path):
    # O Devin aceita o `>-`; o Codex, que vem depois dele em `all`, recusa.
    dobrado = "---\nname: sf-dobrado\ndescription: >-\n  dobrado\n---\ncorpo\n"
    raiz = _raiz_falsa(tmp_path / "raiz", {
        "skills/sdd-plan/SKILL.md": _skill("sdd-plan"),
        "agents/sf-dobrado.md": dobrado,
    })
    home = tmp_path / "home"
    home.mkdir()
    with pytest.raises(ValueError, match="escalar_yaml_nao_suportado"):
        integrate("all", home=home, windows=False, root=raiz)
    assert _relativos(home) == [], "o render do codex estourou depois de o devin gravar"


def test_falha_de_escrita_no_meio_deixa_o_gravado_no_manifesto(tmp_path, monkeypatch):
    from sparkforge.integrate import writer

    raiz = _raiz_minima(tmp_path)
    home = tmp_path / "home"
    original = writer.gravar_atomico
    chamadas = {"n": 0}

    def falha_na_terceira(caminho, dados):
        if Path(caminho).name != "integrations.json":
            chamadas["n"] += 1
            if chamadas["n"] == 3:
                raise PermissionError("sem permissao")
        return original(caminho, dados)

    monkeypatch.setattr(writer, "gravar_atomico", falha_na_terceira)
    with pytest.raises(PermissionError):
        integrate("all", home=home, windows=False, root=raiz)
    gravados = {r for r in _relativos(home) if r != ".sparkforge/integrations.json"}
    assert gravados, "o teste nao chegou a gravar nada antes da falha"
    registrados = set(_manifesto(home)["files"])
    assert gravados <= registrados, f"gravado fora do manifesto: {gravados - registrados}"


def test_manifesto_truncado_sai_recusa_nomeada(tmp_path):
    raiz = _raiz_minima(tmp_path)
    home = tmp_path / "home"
    assert integrate("copilot", home=home, root=raiz)["refused"] == []
    manifesto = home / ".sparkforge" / "integrations.json"
    texto = manifesto.read_bytes()
    manifesto.write_bytes(texto[: len(texto) // 2])
    antes = _foto(home)

    for resultado in (integrate("copilot", home=home, root=raiz), detach("copilot", home=home)):
        (recusa,) = resultado["refused"]
        assert recusa["reason"] == "manifesto_ilegivel"
        assert recusa["path"] == manifesto.as_posix()
        assert recusa["action"]
        assert resultado["hosts"] == []
    assert _foto(home) == antes, "com o manifesto ilegivel, algo foi tocado"


@pytest.mark.parametrize(
    "forma", ["absoluta", "sobe", "sobe_no_meio", "barra_invertida", "appdata_sobe"]
)
def test_chave_fora_do_home_recusa_sem_apagar(tmp_path, forma):
    raiz = _raiz_minima(tmp_path)
    home = tmp_path / "home"
    assert integrate("copilot", home=home, root=raiz)["refused"] == []
    fora = tmp_path / "fora.txt"
    fora.write_bytes(b"do usuario\n")
    chave = {
        "absoluta": fora.as_posix(),
        "sobe": "../fora.txt",
        "sobe_no_meio": ".agents/../../fora.txt",
        "barra_invertida": r"..\fora.txt",
        "appdata_sobe": "%APPDATA%/../fora.txt",
    }[forma]
    caminho = home / ".sparkforge" / "integrations.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["files"][chave] = {"sha256": hashlib.sha256(b"do usuario\n").hexdigest(),
                             "owners": ["copilot"]}
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    antes = _foto(tmp_path)

    resultado = detach("copilot", home=home)
    assert fora.is_file(), "o detach apagou arquivo fora do HOME"
    assert _foto(tmp_path) == antes, "com chave fora do HOME, algo foi apagado"
    (recusa,) = resultado["refused"]
    assert recusa["reason"] == "manifesto_fora_do_home"
    assert recusa["key"] == chave


def test_appdata_vem_do_home_e_o_manifesto_so_guarda_relativo(tmp_path, monkeypatch):
    raiz = _raiz_minima(tmp_path)
    real = tmp_path / "appdata_real"
    monkeypatch.setenv("APPDATA", str(real))

    # `home` injetado e sem `appdata`: o APPDATA vem do home, nunca do ambiente.
    home = tmp_path / "home"
    assert integrate("devin", home=home, windows=True, root=raiz)["refused"] == []
    assert not real.exists(), "com home injetado, integrate leu o APPDATA real"
    assert (home / "AppData" / "Roaming" / "devin" / "agents" / "sf-falso.md").is_file()
    assert detach("devin", home=home)["refused"] == []
    assert not (home / "AppData").exists()

    # APPDATA explicito fora do HOME: chave relativa a raiz declarada, e o detach
    # poda os diretorios vazios dos dois lados sem apagar as raizes.
    fora = tmp_path / "appdata_fora"
    casa = tmp_path / "casa"
    assert integrate("devin", home=casa, windows=True, appdata=fora, root=raiz)["refused"] == []
    manifesto = _manifesto(casa)
    chaves = [*manifesto["files"], *(c["path"] for c in manifesto["hosts"]["devin"]["config"])]
    assert all(not Path(c).is_absolute() and ":" not in c for c in chaves), chaves
    assert ".agents/skills/sdd-plan/SKILL.md" in chaves
    assert "%APPDATA%/devin/agents/sf-falso.md" in chaves
    assert "%APPDATA%/devin/mcp_config.json" in chaves
    assert detach("devin", home=casa, appdata=fora)["refused"] == []
    assert not (fora / "devin").exists()
    assert fora.is_dir()
    assert not (casa / ".agents").exists()


def _sem_modo(relatorio: dict) -> dict:
    """O relatorio sem a marca de dry-run, para comparar ensaio e execucao."""
    copia = {k: v for k, v in relatorio.items() if k != "dry_run"}
    copia["hosts"] = [{k: v for k, v in h.items() if k != "dry_run"} for h in copia["hosts"]]
    return copia


def test_dry_run_de_all_simula_o_manifesto_entre_hosts(tmp_path):
    comum = {"skills/sdd-plan/SKILL.md": _skill("sdd-plan")}
    v1 = _raiz_falsa(tmp_path / "v1", {
        **comum, "skills/sdd-build/SKILL.md": _skill("sdd-build"),
    })
    v2 = _raiz_falsa(tmp_path / "v2", {**comum, "skills/sdd-plan/ref.md": "novo\n"})
    home = tmp_path / "home"
    config = home / ".copilot" / "mcp-config.json"
    config.parent.mkdir(parents=True)
    config.write_bytes(json.dumps({"mcpServers": {"outro": {"command": "node"}}}).encode())

    for raiz in (v1, v2):
        antes = _foto(home)
        ensaio = integrate("all", home=home, dry_run=True, windows=False, root=raiz)
        assert _foto(home) == antes, "o dry-run escreveu"
        real = integrate("all", home=home, windows=False, root=raiz)
        assert _sem_modo(ensaio) == _sem_modo(real), raiz.name

    antes = _foto(home)
    ensaio = detach("all", home=home, dry_run=True)
    assert _foto(home) == antes, "o dry-run do detach removeu"
    real = detach("all", home=home)
    assert _sem_modo(ensaio) == _sem_modo(real)
    assert not (home / ".agents").exists()


# --------------------------------------------------------------------------
# Claude Code: marketplace local e o `claude plugin` (D8)
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# Copia vendorizada em dobro (D9) e a guarda do escopo de usuario
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# CLI e doctor por host (AC11)
# --------------------------------------------------------------------------


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
