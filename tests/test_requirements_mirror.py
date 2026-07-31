"""`requirements.txt` e espelho gerado de `pyproject.toml`.

Espelho sem guarda vira drift, e drift num manifesto de dependencia e pior que
nao ter o espelho: o scan de SCA passa a olhar uma arvore que nao e a que o
`pip install` monta, e reporta "sem vulnerabilidade" sobre um pacote que o
projeto nao usa mais -- ou pior, deixa de olhar um que ele passou a usar.

Mesma disciplina de `scripts/sync_skills.py --check` para `.claude/`,
`.agents/` e `.github/`.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.gen_requirements import (  # noqa: E402
    REQUIREMENTS,
    render,
    requirements_from_pyproject,
)


class TestMirrorIsCurrent:
    def test_file_exists(self):
        assert REQUIREMENTS.is_file()

    def test_matches_pyproject_byte_for_byte(self):
        assert REQUIREMENTS.read_text(encoding="utf-8") == render()

    def test_check_mode_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "scripts/gen_requirements.py", "--check"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr


class TestExtraction:
    def test_core_dependencies_are_present(self):
        found = {r.split(">")[0].split("<")[0].split("=")[0].strip().lower()
                 for r in requirements_from_pyproject()}
        assert {"pyyaml", "jsonschema"} <= found

    def test_every_extra_is_included(self):
        """Os extras entram junto de proposito.

        `mcp` traz a arvore transitiva maior do projeto -- starlette, uvicorn,
        pydantic-settings. Gerar o espelho so com o nucleo esconderia justamente
        a parte que mais precisa de scan.
        """
        found = {r.split(">")[0].split("<")[0].split("=")[0].strip().lower()
                 for r in requirements_from_pyproject()}
        assert {"boto3", "mcp", "starlette", "uvicorn", "pytest", "ruff"} <= found

    def test_the_entry_point_is_not_mistaken_for_a_requirement(self):
        """`[project.scripts]` declara `sparkforge = "...cli:main"`. Sem o corte
        antes dessa secao, o entry point viraria uma linha de requisito e o
        `pip install -r` quebraria."""
        assert not any("cli:main" in r for r in requirements_from_pyproject())
        assert not any(r.lower().startswith("sparkforge") for r in requirements_from_pyproject())

    def test_the_build_backend_is_not_a_requirement(self):
        """`[build-system]` fica fora do recorte: setuptools e requisito de
        build, nao de runtime, e listá-lo aqui faria o scan reportar sobre um
        pacote que o projeto nao instala."""
        assert not any("setuptools" in r for r in requirements_from_pyproject())

    def test_no_duplicates(self):
        """`mcp`, `starlette` e `uvicorn` aparecem no extra `mcp` E em `dev`."""
        found = [r.lower().replace(" ", "") for r in requirements_from_pyproject()]
        assert len(found) == len(set(found))


class TestDriftIsDetected:
    def test_a_dependency_added_only_to_pyproject_fails_the_check(self, tmp_path, monkeypatch):
        """A falha que este espelho existe para pegar, provada por mutacao."""
        import scripts.gen_requirements as gen

        original = gen.PYPROJECT.read_text(encoding="utf-8")
        mutated = original.replace(
            '    "jsonschema>=4.0",\n',
            '    "jsonschema>=4.0",\n    "requests>=2.32",\n',
        )
        assert mutated != original, "a mutacao nao aplicou; o teste nao provaria nada"

        fake = tmp_path / "pyproject.toml"
        fake.write_text(mutated, encoding="utf-8")
        monkeypatch.setattr(gen, "PYPROJECT", fake)

        assert "requests>=2.32" in gen.requirements_from_pyproject()
        assert gen.render() != REQUIREMENTS.read_text(encoding="utf-8")
