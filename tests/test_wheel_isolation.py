# tests/test_wheel_isolation.py
"""Install-2.0 §8.4 — Wheel Isolation Test.

O canal pip e um contrato separado do checkout: este teste constroi o wheel,
instala numa venv LIMPA e executa o ciclo de vida `install` a partir de um
diretorio fora do repositorio. Se qualquer recurso (skills, agents, rules,
knowledge) so existir no clone, uma das etapas falha — e esse e o defeito que
o §8 existe para pegar antes da publicacao.

Pipeline (spec-fonte `prompt_evo_install2.0.md` §8.4):

    build wheel -> venv limpa -> install wheel -> cwd fora do checkout
    -> `sparkforge-aws install` -> registry + contratos -> retrieve knowledge
    -> retrieve rule -> verify protocol -> verificacao offline
    -> uninstall / repair / reinstall

O gate `scripts/verify_wheel.py` ja prova que os GOLDENS reproduzem sob o
wheel; este teste cobre a outra metade que ele nao cobre: o instalador
(integrate/bundle), o registry `.forge/context/` e os verbos de retrieval.
`tests/test_installed_provenance.py` e a guarda de procedencia daquele gate;
aqui a procedencia e estrutural — o subprocesso roda com o python/CLI DA VENV
e cwd dentro do diretorio temporario, entao `import sparkforge_aws` so pode
resolver para o site-packages da venv.

Variaveis `SPARKFORGE_AWS_*` sao removidas do ambiente dos subprocessos pelo
mesmo motivo que `verify_wheel.py` as remove: um override apontando para
`rules/catalog` ou `knowledge` do checkout faria o teste passar contra o
repositorio, nao contra o que veio no wheel.

O que NAO se afirma aqui: verbos de discovery do registry de contexto que o
lf-0037 esta adicionando (`context`/`distribution` sobre `.forge/context/`).
Quando entrarem, a cobertura planejada esta marcada PLANNED — o teste nao pode
falhar por um verbo que ainda nao existe na main.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WHEEL_GLOB = "sparkforge_aws-*.whl"
PACKAGE = "sparkforge_aws"
CLI = "sparkforge-aws"
FORGE_ID = "spark-forge-aws"
# `.mcp.json` e skills sao assets gerenciados comprovadamente escritos pelo
# install; o registry `forge/context/v1` e o contrato do ciclo 2.
CONTEXT_REGISTRY = Path(".forge/context/registry.json")
CONTEXT_CAPABILITY = Path(f".forge/context/capabilities/{FORGE_ID}.json")
STATE_DIR = ".sparkforge_aws"


def _scripts_dir(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if sys.platform == "win32" else "bin")


def _build_wheel(tmp: Path) -> Path:
    """Constroi o wheel DESTA arvore em tmp — nunca reutiliza `dist/`.

    O atalho "reuse dist/ se existir" (padrao do teste de wheel do
    data-sentinel) foi descartado depois de observado na pratica: um
    `dist/*.whl` stale — construido antes do merge que este teste existe para
    vigiar — faz o gate inteiro medir o pacote ERRADO e reprovar (ou, pior,
    aprovar) contra artefato que nao e o da arvore. O wheel sob teste tem que
    ser uma funcao do checkout atual; os ~60s de rebuild sao o preco de nao
    testar outro pacote."""
    dist = tmp / "dist"
    dist.mkdir()
    result = subprocess.run(  # build chamado pelo proprio teste
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(ROOT)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"`python -m build` indisponivel ou falhou: {result.stderr[-400:]}")
    wheels = sorted(dist.glob(WHEEL_GLOB))
    assert wheels, "build terminou com sucesso e nao produziu wheel"
    return wheels[0]


def _clean_env() -> dict[str, str]:
    """Ambiente do subprocesso sem os overrides que apontariam para o
    checkout — a segunda metade da guarda de procedencia (verify_wheel.py)."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    for key in [k for k in env if k.startswith("SPARKFORGE_AWS_")]:
        env.pop(key)
    env["PYTHONSAFEPATH"] = "1"
    return env


def _run(argv: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # CLI/venv criados pelo proprio teste
        argv,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def _json(doc: subprocess.CompletedProcess, step: str) -> dict:
    try:
        return json.loads(doc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(
            f"{step}: saida nao e JSON (rc={doc.returncode}):\n"
            f"{doc.stdout[-800:]}\n{doc.stderr[-800:]}"
        ) from None


@pytest.mark.slow
def test_wheel_install_lifecycle_outside_checkout(tmp_path: Path):
    wheel = _build_wheel(tmp_path)
    # O wheel tem que carregar os manifestos do forge que o instalador
    # consome: sem eles o registry de contexto sai degradado num pip install
    # (integrity/discovery.manifest vazios — paridade §8.2, gate barato aqui).
    import zipfile

    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
    for packaged in (
        f"{PACKAGE}/forge.json",
        f"{PACKAGE}/forge.agentic.json",
        f"{PACKAGE}/integrate/bundle/skills",
        f"{PACKAGE}/integrate/bundle/agents",
        f"{PACKAGE}/rules/catalog",
        f"{PACKAGE}/knowledge",
    ):
        assert any(n.startswith(packaged) for n in names), f"{packaged} ausente do wheel"

    env = _clean_env()

    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True)
    scripts = _scripts_dir(venv_dir)
    python = scripts / "python"
    pip = scripts / "pip"

    install = _run(
        [str(pip), "install", "--quiet", str(wheel)], cwd=tmp_path, env=env
    )
    assert install.returncode == 0, f"pip install do wheel falhou: {install.stderr[-800:]}"

    cli = scripts / CLI
    assert cli.is_file() or cli.with_suffix(".exe").is_file(), (
        f"console script {CLI} ausente na venv: {sorted(p.name for p in scripts.iterdir())}"
    )

    # Procedencia estrutural: o pacote importado vem do site-packages da
    # venv, nunca do checkout — antes de qualquer assercao de comportamento.
    probe = _run(
        [
            str(python),
            "-c",
            (
                "import sys, sysconfig\n"
                f"import {PACKAGE}\n"
                f"print({PACKAGE}.__file__)\n"
                "print(sysconfig.get_paths()['purelib'])"
            ),
        ],
        cwd=tmp_path,
        env=env,
    )
    assert probe.returncode == 0, probe.stderr[-400:]
    module_file, purelib = (Path(line) for line in probe.stdout.strip().splitlines()[-2:])
    assert module_file.is_relative_to(purelib), (
        f"{PACKAGE} importado de fora da venv: {module_file} (purelib={purelib})"
    )

    target = tmp_path / "consumer"
    target.mkdir()
    git = shutil.which("git")
    if git is not None:
        _run([git, "init", "-q"], cwd=target, env=env)

    # -- install (apply) -----------------------------------------------------
    out = _run(
        [str(cli), "install", "--root", str(target), "--yes"],
        cwd=target,
        env=env,
    )
    assert out.returncode == 0, f"install falhou:\n{out.stdout[-800:]}\n{out.stderr[-800:]}"
    receipt = _json(out, "install")
    assert receipt["status"] == "completed", receipt
    assert receipt["checks"], "recibo sem checks"
    context_check = next(c for c in receipt["checks"] if c["id"] == "context-registry")
    assert context_check["status"] == "PASS", context_check

    # -- registry + contratos -------------------------------------------------
    registry = json.loads((target / CONTEXT_REGISTRY).read_text(encoding="utf-8"))
    assert registry["schema"] == "forge/context-registry/v1", registry.get("schema")
    assert any(f.get("forge_id") == FORGE_ID for f in registry["forges"])
    capability = json.loads((target / CONTEXT_CAPABILITY).read_text(encoding="utf-8"))
    assert capability["schema"] == "forge/context/v1", capability.get("schema")
    assert capability["forge_id"] == FORGE_ID
    for cap in ("skills", "agents", "rules", "knowledge", "protocols"):
        assert capability["capabilities"][cap]["available"] is True, cap
    # ledger de posse do integrador
    assert (target / STATE_DIR / "integrations.json").is_file()
    assert (target / ".mcp.json").is_file()

    # -- retrieve knowledge ---------------------------------------------------
    out = _run([str(cli), "knowledge", "list"], cwd=target, env=env)
    assert out.returncode == 0, out.stderr[-400:]
    listed = _json(out, "knowledge list")
    assert listed["docs"], "knowledge list vazio sob o wheel"
    # a raiz resolvida tem que ser o bundle do pacote, nao o checkout
    assert str(ROOT) not in listed["root"], listed["root"]

    # -- retrieve rule ---------------------------------------------------------
    out = _run(
        [str(cli), "rules", "lookup", "--id", "SF-WASTE-001"], cwd=target, env=env
    )
    assert out.returncode == 0, out.stderr[-400:]
    lookup = _json(out, "rules lookup")
    assert lookup["total_count"] >= 1, lookup
    assert lookup["rules"][0]["id"] == "SF-WASTE-001"

    # -- verify protocol -------------------------------------------------------
    # `install doctor` sai 1 mesmo saudavel: o dispatch so zera para
    # completed/planned, e InstallationHealth fala outro vocabulario (healthy).
    out = _run([str(cli), "install", "doctor", "--root", str(target)], cwd=target, env=env)
    health = _json(out, "install doctor")
    assert health["status"] in ("healthy", "degraded"), health.get("status")
    state_check = next(
        (c for c in health["checks"] if c["id"] == "install-state"), None
    )
    assert state_check is not None and state_check["status"] in (
        "HEALTHY",
        "PASS",
        "OK",
    ), health["checks"]

    # -- verificacao offline ----------------------------------------------------
    # `doctor` sem `--online` nao toca a AWS; `doctor agentic` confere o plano
    # agêntico local. Um env incompleto pode degradar, nunca quebrar em
    # traceback — e o JSON tem que continuar parseavel.
    out = _run([str(cli), "doctor", "--repo", str(target)], cwd=target, env=env)
    assert "Traceback" not in out.stderr, out.stderr[-800:]
    out = _run([str(cli), "doctor", "agentic"], cwd=target, env=env)
    assert "Traceback" not in out.stderr, out.stderr[-800:]

    # -- repair ------------------------------------------------------------------
    victim = target / ".mcp.json"
    assert victim.is_file()
    victim.unlink()
    out = _run([str(cli), "repair", "--root", str(target)], cwd=target, env=env)
    assert out.returncode == 0, out.stderr[-400:]
    assert victim.is_file(), "repair nao restaurou asset gerenciado removido"

    # -- uninstall + reinstall ---------------------------------------------------
    out = _run([str(cli), "uninstall", "--root", str(target)], cwd=target, env=env)
    assert out.returncode == 0, out.stderr[-400:]
    gone = _json(out, "uninstall")
    assert gone["status"] in ("completed", "uninstalled"), gone.get("status")
    assert not victim.exists(), "uninstall nao removeu asset gerenciado"
    assert not (target / CONTEXT_CAPABILITY).exists()

    out = _run(
        [str(cli), "install", "--root", str(target), "--yes"], cwd=target, env=env
    )
    assert out.returncode == 0, out.stderr[-400:]
    assert _json(out, "reinstall")["status"] == "completed"
    assert (target / CONTEXT_REGISTRY).is_file()


# PLANNED (lf-0037, discovery de conhecimento/regras via `.forge/context/`):
# quando `context`/`distribution` ganharem verbos de discovery sobre o
# registry instalado, estender este teste para le-los — hoje a prova de
# retrieval e por `knowledge list` + `rules lookup` (verbos estaveis).
