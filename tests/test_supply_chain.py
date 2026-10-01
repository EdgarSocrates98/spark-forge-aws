"""Gates da metade de supply chain: lock congelado, SBOM e politica de auditoria.

O que ESTA suite consegue provar, e o que ela deliberadamente nao tenta
=======================================================================

Nada aqui usa rede. Isso nao e limitacao aceita a contragosto -- e a razao pela
qual os tres artefatos foram desenhados com a parte que precisa de rede
separada da parte que precisa de gate:

- **Lock** -- gerar exige indice do PyPI; conferir forma, cobertura e
  consistencia nao exige nada. E a conferencia que roda aqui e no CI.
- **SBOM** -- o gerador le o lock commitado e hasheia arquivos de disco. Da
  para provar formato, campos obrigatorios, escopo e determinismo sem baixar
  coisa nenhuma.
- **Auditoria** -- o `pip-audit` consulta base externa; a POLITICA sobre o
  resultado dele e uma funcao pura sobre JSON. E a politica que tem gate, com
  relatorios sinteticos, inclusive o caso que mais importa: base nao
  consultada NAO e aprovacao.

O que nao da para provar sem rede, e fica dito: que a versao pinada continua
sendo a que o indice serve, e se ela tem vulnerabilidade conhecida hoje. Essa
pergunta e do job `audit`, que roda separado justamente porque a resposta dela
depende de um servico de terceiro estar de pe.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_policy, gen_lock, gen_sbom  # noqa: E402

CI = ROOT / ".github" / "workflows" / "ci.yml"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


def _workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _runs(job: dict) -> list[str]:
    return [step.get("run", "") for step in job.get("steps", [])]


# --------------------------------------------------------------------- lock


class TestLockIntegrity:
    def test_check_passes_on_the_committed_locks(self):
        """O mesmo `--check` que o CI roda, rodando aqui.

        Sem isto, um lock quebrado so apareceria no CI -- e a suite local diria
        que esta tudo bem enquanto a instalacao congelada nao monta.
        """
        problems: list[str] = []
        for version in gen_lock.PYTHON_VERSIONS:
            problems.extend(gen_lock.check(version))
        assert problems == []

    @pytest.mark.parametrize("version", gen_lock.PYTHON_VERSIONS)
    def test_every_entry_is_pinned_and_hashed(self, version):
        packages = gen_lock.load(version)
        assert packages, f"lock de {version} vazio"
        for package in packages:
            assert package.version, package.name
            assert package.hashes, f"{package.name} sem hash"
            for digest in package.hashes:
                assert re.fullmatch(r"[0-9a-f]{64}", digest), (package.name, digest)

    @pytest.mark.parametrize("version", gen_lock.PYTHON_VERSIONS)
    def test_every_declared_requirement_is_locked(self, version):
        """Cobertura pelo que `pyproject.toml` declara, nunca por lista a mao.

        Uma dependencia nova em `pyproject.toml` sem regenerar o lock quebra
        aqui, que e o mesmo desenho de `gen_requirements.py --check`.
        """
        locked = {gen_lock.canonical(p.name) for p in gen_lock.load(version)}
        assert gen_lock.declared_names() <= locked

    @pytest.mark.parametrize("version", gen_lock.PYTHON_VERSIONS)
    def test_the_build_backend_is_locked(self, version):
        """Sem o backend no lock, o install editavel do CI baixaria hatchling do
        indice em tempo de CI -- resolucao, que e exatamente o que o lock existe
        para eliminar. O nome sai de `[build-system] requires`, nao de uma
        constante: trocar de backend nao pode deixar este gate mudo."""
        _, _, build = gen_lock._pyproject_arrays()
        esperados = {gen_lock.requirement_name(req) for req in build}
        locked = {gen_lock.canonical(p.name) for p in gen_lock.load(version)}
        assert esperados <= locked

    @pytest.mark.parametrize("version", gen_lock.PYTHON_VERSIONS)
    def test_the_dynamic_build_requirement_is_locked_too(self, version):
        """`editables` nao aparece em `[build-system] requires` -- o hatchling o
        declara pelo hook do PEP 660. Com isolamento de build o pip o baixaria
        na hora; com `--no-build-isolation`, que e o que o CI usa justamente
        para nao baixar nada, ele nao baixa, e o install editavel quebra num
        `from editables import EditableProject`. Este teste existe porque essa
        dependencia e invisivel em todo lugar onde alguem iria procurar."""
        locked = {gen_lock.canonical(p.name) for p in gen_lock.load(version)}
        for helper in gen_lock.BUILD_HELPERS:
            assert gen_lock.requirement_name(helper) in locked, helper

    @pytest.mark.parametrize("version", gen_lock.PYTHON_VERSIONS)
    def test_the_header_names_its_own_python_version(self, version):
        """Dois locks parecidos sao faceis de trocar num copiar-e-colar. O
        cabecalho de cada um diz para que versao ele foi resolvido, e este teste
        cobra que o arquivo `py3.10.txt` nao diga 3.11."""
        head = gen_lock.lock_path(version).read_text(encoding="utf-8").split("\n", 12)[:12]
        assert any(f"CPython {version}" in line for line in head), head

    def test_there_is_a_lock_for_every_python_in_the_ci_matrix(self):
        """A matriz do CI e a fonte; a tupla do gerador e o espelho.

        Acrescentar 3.12 ao CI sem gerar o lock correspondente quebra aqui, e
        nao no runner com uma mensagem de arquivo ausente.
        """
        matriz = _workflow(CI)["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert set(matriz) == set(gen_lock.PYTHON_VERSIONS)
        for version in matriz:
            assert gen_lock.lock_path(version).is_file()


class TestLockParserFailsClosed:
    """Uma linha nao prevista num arquivo que o pip instala e uma dependencia
    que ninguem reviu. O parser e o ultimo lugar onde ela ainda sai de graca."""

    def test_rejects_a_pin_without_the_metadata_line(self):
        with pytest.raises(ValueError, match="sem linha"):
            gen_lock.parse("attrs==26.1.0 \\\n    --hash=sha256:" + "a" * 64 + "\n")

    def test_rejects_a_hash_without_a_pin(self):
        with pytest.raises(ValueError, match="hash sem pin"):
            gen_lock.parse("    --hash=sha256:" + "a" * 64 + "\n")

    def test_rejects_an_unrecognized_line(self):
        with pytest.raises(ValueError, match="forma nao reconhecida"):
            gen_lock.parse("attrs\n")

    def test_rejects_a_file_that_ends_mid_entry(self):
        text = "# sparkforge-lock: scope=required license=MIT\nattrs==26.1.0 \\\n"
        with pytest.raises(ValueError, match="termina no meio"):
            gen_lock.parse(text)

    def test_accepts_the_shape_it_generates(self):
        package = gen_lock.LockedPackage("attrs", "26.1.0", ["a" * 64, "b" * 64], "MIT", "required")
        [lido] = gen_lock.parse(package.render())
        assert (lido.name, lido.version, lido.scope, lido.license) == (
            "attrs",
            "26.1.0",
            "required",
            "MIT",
        )
        assert lido.hashes == ["a" * 64, "b" * 64]


class TestLockCheckIsOffline:
    def test_check_reports_a_missing_lock_instead_of_raising(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gen_lock, "LOCK_DIR", tmp_path)
        [problema] = gen_lock.check("3.10")
        assert "ausente" in problema

    def test_check_reports_a_pin_that_lost_its_hash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gen_lock, "LOCK_DIR", tmp_path)
        (tmp_path / "py3.10.txt").write_text(
            "# sparkforge-lock: scope=required license=MIT\nattrs==26.1.0 \\\n",
            encoding="utf-8",
        )
        problemas = gen_lock.check("3.10")
        assert any("termina no meio" in item for item in problemas), problemas


# ---------------------------------------------------------------------- SBOM


@pytest.fixture
def dist(tmp_path):
    """Um `dist/` com os nomes que o release produz.

    O conteudo dos arquivos e irrelevante e isso e proposital: o gerador so
    hasheia bytes. Construir um wheel de verdade aqui trocaria um teste de
    milissegundos por um de minutos sem provar nada a mais sobre o SBOM -- o
    wheel de verdade ja tem o proprio gate em `scripts/verify_wheel.py`.
    """
    version = gen_sbom.project_version()
    directory = tmp_path / "dist"
    directory.mkdir()
    (directory / f"{gen_sbom.DIST_STEM}-{version}-py3-none-any.whl").write_bytes(b"wheel")
    (directory / f"{gen_sbom.DIST_STEM}-{version}.tar.gz").write_bytes(b"sdist")
    return directory


class TestSbomShape:
    def test_declares_the_cyclonedx_envelope(self, dist):
        sbom = gen_sbom.build_sbom(dist)
        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["specVersion"] == gen_sbom.SPEC_VERSION
        assert sbom["version"] == 1
        assert sbom["serialNumber"].startswith("urn:uuid:")

    def test_the_root_component_is_the_package_with_license_and_purl(self, dist):
        root = gen_sbom.build_sbom(dist)["metadata"]["component"]
        assert root["name"] == gen_sbom.PROJECT_NAME
        assert root["version"] == gen_sbom.project_version()
        assert root["purl"] == f"pkg:pypi/{gen_sbom.PROJECT_NAME}@{root['version']}"
        assert root["licenses"][0]["license"]["name"] == gen_sbom.project_license()

    def test_every_library_component_carries_the_five_required_fields(self, dist):
        """Pacote, versao, hash, licenca e origem -- os cinco que a exigencia
        enumera, conferidos um a um em cada componente."""
        for component in gen_sbom.build_sbom(dist)["components"]:
            if component["type"] != "library":
                continue
            assert component["name"]
            assert component["version"]
            assert component["hashes"]
            for digest in component["hashes"]:
                assert digest["alg"] == "SHA-256"
                assert len(digest["content"]) == 64
            assert component["licenses"][0]["license"]["name"]
            assert component["purl"].startswith("pkg:pypi/")
            origem = component["externalReferences"][0]["url"]
            assert origem.startswith("https://pypi.org/project/")

    def test_the_artifact_bytes_are_in_the_sbom(self, dist):
        """O que amarra o SBOM a UM release e o sha256 dos arquivos. Sem isto
        ele descreveria uma versao no abstrato, e dois wheels diferentes da
        mesma versao teriam o mesmo documento."""
        componentes = gen_sbom.build_sbom(dist)["components"]
        arquivos = {
            c["name"]: c["hashes"][0]["content"] for c in componentes if c["type"] == "file"
        }
        assert len(arquivos) == 2
        for path in dist.iterdir():
            assert arquivos[path.name] == gen_sbom.sha256_of(path)

    def test_the_real_core_dependencies_appear_as_required(self, dist):
        """Escopo derivado do que `pyproject.toml` declara, nunca de uma lista
        copiada: acrescentar dependencia de nucleo sem regenerar o lock quebra
        aqui."""
        core, _, _ = gen_lock._pyproject_arrays()
        esperados = {gen_lock.requirement_name(req) for req in core}
        required = {
            gen_lock.canonical(c["name"])
            for c in gen_sbom.build_sbom(dist)["components"]
            if c.get("scope") == "required"
        }
        assert esperados <= required

    def test_development_tooling_is_marked_excluded_not_required(self, dist):
        """`ruff` e `pytest` existem no ambiente que testa e nao dentro do que e
        publicado. Marca-los como `required` faria o SBOM afirmar que quem
        instala o pacote instala o linter junto."""
        escopos = {
            gen_lock.canonical(c["name"]): c.get("scope")
            for c in gen_sbom.build_sbom(dist)["components"]
            if c["type"] == "library"
        }
        for ferramenta in ("ruff", "pytest"):
            assert escopos.get(ferramenta) == "excluded", (ferramenta, escopos.get(ferramenta))


class TestSbomIsDeterministic:
    def test_two_generations_with_the_same_epoch_are_byte_identical(self, dist, monkeypatch):
        """O repositorio constroi wheel reproduzivel bit a bit. Um SBOM com
        relogio dentro seria o unico arquivo nao-reproduzivel do release."""
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1580601600")
        primeiro = gen_sbom.render(gen_sbom.build_sbom(dist))
        segundo = gen_sbom.render(gen_sbom.build_sbom(dist))
        assert primeiro == segundo
        assert "2020-02-02T00:00:00Z" in primeiro

    def test_the_serial_number_follows_the_artifact_bytes(self, dist, monkeypatch):
        """Numero de serie derivado do artefato, e nao sorteado: mudou o byte,
        mudou o numero; nao mudou nada, o documento e o mesmo."""
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1580601600")
        antes = gen_sbom.build_sbom(dist)["serialNumber"]
        wheel = next(dist.glob("*.whl"))
        wheel.write_bytes(b"outro wheel")
        assert gen_sbom.build_sbom(dist)["serialNumber"] != antes


class TestSbomRefusesTheWrongDist:
    def test_refuses_a_directory_without_the_artifacts(self, tmp_path):
        with pytest.raises(SystemExit, match="esperava wheel e sdist"):
            gen_sbom.build_sbom(tmp_path)

    def test_refuses_artifacts_of_another_version(self, tmp_path):
        """Um `dist/` velho produziria um SBOM que descreve bytes que ninguem
        vai publicar -- e um documento que parece prova e fala de outra coisa e
        pior que documento nenhum."""
        (tmp_path / f"{gen_sbom.DIST_STEM}-0.0.1-py3-none-any.whl").write_bytes(b"x")
        (tmp_path / f"{gen_sbom.DIST_STEM}-0.0.1.tar.gz").write_bytes(b"y")
        with pytest.raises(SystemExit, match="esperava wheel e sdist"):
            gen_sbom.build_sbom(tmp_path)

    def test_refuses_a_path_that_is_not_a_directory(self, tmp_path):
        arquivo = tmp_path / "dist"
        arquivo.write_text("nao sou diretorio", encoding="utf-8")
        with pytest.raises(SystemExit, match="nao e diretorio"):
            gen_sbom.build_sbom(arquivo)


# ------------------------------------------------------------ politica de audit


def _report(dependencies: list[dict]) -> dict:
    return {"dependencies": dependencies, "fixes": []}


class TestAuditPolicy:
    def test_a_vulnerability_with_a_published_fix_blocks(self):
        vuln = {"id": "V-1", "fix_versions": ["1.1"]}
        verdict = audit_policy.classify(
            _report([{"name": "x", "version": "1.0", "vulns": [vuln]}])
        )
        assert verdict.exit_code == audit_policy.EXIT_FIXABLE
        assert verdict.fixable and not verdict.unfixable

    def test_a_vulnerability_without_a_fix_only_reports(self):
        """Nao ha para onde subir. Derrubar o CI aqui nao acelera correcao
        nenhuma -- so treina o time a ignorar vermelho."""
        verdict = audit_policy.classify(
            _report([{"name": "x", "version": "1.0", "vulns": [{"id": "V-2", "fix_versions": []}]}])
        )
        assert verdict.exit_code == audit_policy.EXIT_OK
        assert verdict.unfixable and not verdict.fixable
        assert any("V-2" in line for line in verdict.lines)

    def test_the_same_finding_starts_blocking_the_day_it_gets_a_fix(self):
        """A migracao entre as duas categorias e automatica: o gatilho e o
        campo `fix_versions`, e nao uma lista de excecao para alguem manter."""
        def relatorio(fix_versions: list[str]) -> dict:
            vuln = {"id": "V", "fix_versions": fix_versions}
            return _report([{"name": "x", "version": "1.0", "vulns": [vuln]}])

        sem = relatorio([])
        com = relatorio(["2"])
        assert audit_policy.classify(sem).exit_code == audit_policy.EXIT_OK
        assert audit_policy.classify(com).exit_code == audit_policy.EXIT_FIXABLE

    def test_a_clean_report_passes(self):
        verdict = audit_policy.classify(_report([{"name": "x", "version": "1.0", "vulns": []}]))
        assert verdict.exit_code == audit_policy.EXIT_OK
        assert verdict.audited == 1

    def test_a_partially_skipped_report_passes_and_says_so(self):
        verdict = audit_policy.classify(
            _report(
                [
                    {"name": "x", "version": "1.0", "vulns": []},
                    {"name": "y", "skip_reason": "nao esta no indice"},
                ]
            )
        )
        assert verdict.exit_code == audit_policy.EXIT_OK
        assert verdict.skipped
        assert any("cobertura parcial" in line for line in verdict.lines)


class TestAbsenceIsNotApproval:
    """O caso que mais importa acertar: "nao consegui perguntar" nunca pode ser
    lido como "nao ha nada". E a mesma disciplina de `pyspark.unresolved` e de
    indice velho respondendo "nenhum simbolo"."""

    def test_every_package_skipped_is_not_consulted(self):
        verdict = audit_policy.classify(_report([{"name": "x", "skip_reason": "sem rede"}]))
        assert verdict.exit_code == audit_policy.EXIT_NOT_CONSULTED

    def test_an_empty_report_is_not_consulted(self):
        assert audit_policy.classify(_report([])).exit_code == audit_policy.EXIT_NOT_CONSULTED

    def test_a_report_without_the_dependencies_key_is_not_consulted(self):
        assert audit_policy.classify({"fixes": []}).exit_code == audit_policy.EXIT_NOT_CONSULTED

    def test_a_report_that_is_not_an_object_is_not_consulted(self):
        assert audit_policy.classify([]).exit_code == audit_policy.EXIT_NOT_CONSULTED

    def test_a_report_that_does_not_cover_the_lock_is_not_consulted(self):
        """Relatorio bem formado sobre OUTRA coisa. Todas as demais checagens
        passariam: ele tem `dependencies`, tem pacote auditado e nao tem
        vulnerabilidade. E nao respondeu nada sobre o lock."""
        esperados = {gen_lock.canonical(p.name) for p in gen_lock.load("3.11")}
        verdict = audit_policy.classify(
            _report([{"name": "flask", "version": "3.0.0", "vulns": []}]), esperados
        )
        assert verdict.exit_code == audit_policy.EXIT_NOT_CONSULTED
        assert "nao cobre" in verdict.lines[0]

    def test_the_real_report_of_the_real_lock_covers_it(self):
        """O caminho feliz da mesma checagem, montado a partir do proprio lock:
        cobertura completa passa. Sem este par, o teste acima poderia estar
        medindo um comparador que reprova sempre."""
        packages = gen_lock.load("3.11")
        esperados = {gen_lock.canonical(p.name) for p in packages}
        relatorio = _report(
            [{"name": p.name, "version": p.version, "vulns": []} for p in packages]
        )
        verdict = audit_policy.classify(relatorio, esperados)
        assert verdict.exit_code == audit_policy.EXIT_OK
        assert verdict.audited == len(packages)

    def test_a_skipped_package_still_counts_as_covered(self):
        """Pulado e cobertura declarada: o relatorio falou daquele pacote e disse
        por que nao o auditou. Trata-lo como ausente confundiria "nao consegui"
        com "nem olhei"."""
        verdict = audit_policy.classify(
            _report(
                [
                    {"name": "x", "version": "1.0", "vulns": []},
                    {"name": "y", "skip_reason": "sem wheel"},
                ]
            ),
            {"x", "y"},
        )
        assert verdict.exit_code == audit_policy.EXIT_OK

    def test_a_missing_file_is_not_consulted(self, tmp_path):
        verdict = audit_policy.classify_path(tmp_path / "nao-existe.json")
        assert verdict.exit_code == audit_policy.EXIT_NOT_CONSULTED
        assert "ausente" in verdict.lines[0]

    def test_an_unreadable_file_is_not_consulted(self, tmp_path):
        quebrado = tmp_path / "audit.json"
        quebrado.write_text("{isto nao e json", encoding="utf-8")
        verdict = audit_policy.classify_path(quebrado)
        assert verdict.exit_code == audit_policy.EXIT_NOT_CONSULTED
        assert "ilegivel" in verdict.lines[0]

    def test_the_cli_exits_with_the_verdict_code(self, tmp_path):
        """O codigo de saida e o contrato com o workflow: e ele que decide a cor
        do job, e um `print` bonito com saida 0 nao decide nada."""
        relatorio = tmp_path / "audit.json"
        relatorio.write_text(json.dumps({"fixes": []}), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "audit_policy.py"), str(relatorio)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == audit_policy.EXIT_NOT_CONSULTED
        assert "base nao consultada" in result.stderr


# ------------------------------------------------------------------ workflows


class TestCiInstallsFrozen:
    def test_the_test_job_installs_from_the_matrix_lock_with_require_hashes(self):
        runs = "\n".join(_runs(_workflow(CI)["jobs"]["test"]))
        assert "--require-hashes" in runs
        assert "locks/py${{ matrix.python-version }}.txt" in runs

    def test_the_editable_install_neither_resolves_nor_downloads_the_backend(self):
        """`--no-deps` impede o pip de resolver os pisos de novo;
        `--no-build-isolation` impede que ele baixe hatchling em tempo de CI.
        Sem os dois juntos, "instalacao congelada" e so um nome."""
        runs = "\n".join(_runs(_workflow(CI)["jobs"]["test"]))
        assert "pip install -e . --no-deps --no-build-isolation" in runs

    def test_the_test_job_checks_the_lock_offline(self):
        runs = "\n".join(_runs(_workflow(CI)["jobs"]["test"]))
        assert "gen_lock.py --check" in runs


class TestAuditIsItsOwnJob:
    def test_there_is_an_audit_job(self):
        assert "audit" in _workflow(CI)["jobs"]

    def test_the_audit_job_applies_the_declared_policy(self):
        runs = "\n".join(_runs(_workflow(CI)["jobs"]["audit"]))
        assert "pip-audit" in runs
        assert "scripts/audit_policy.py" in runs
        assert "--lock locks/py3.11.txt" in runs, "sem --lock a cobertura nao e conferida"

    def test_the_audit_job_audits_the_lock_and_not_the_floors(self):
        """Auditar `requirements.txt` seria auditar PISOS. `PyYAML>=6.0` nao tem
        CVE; a versao instalada e que tem."""
        runs = "\n".join(_runs(_workflow(CI)["jobs"]["audit"]))
        assert "locks/py3.11.txt" in runs
        assert "-r requirements.txt" not in runs

    def test_the_audit_reads_the_lock_instead_of_installing_it(self):
        """Sem `--disable-pip`, o pip-audit cria um virtualenv e instala o lock
        inteiro so para enumerar o que instalou. Com ele, le o arquivo -- que ja
        e um fecho pinado -- e consulta so a base."""
        runs = "\n".join(_runs(_workflow(CI)["jobs"]["audit"]))
        assert "--require-hashes" in runs
        assert "--disable-pip" in runs

    def test_the_test_job_never_touches_the_vulnerability_database(self):
        """A separacao E o desenho: o gate de teste roda offline, e a cor dele
        precisa significar "o codigo esta certo", nunca "o servico de terceiro
        estava de pe"."""
        runs = "\n".join(_runs(_workflow(CI)["jobs"]["test"]))
        assert "pip-audit" not in runs


class TestReleaseCarriesTheSbom:
    def test_the_sbom_is_generated_after_the_parity_gate(self):
        runs = _runs(_workflow(RELEASE)["jobs"]["release"])
        gate = next(i for i, run in enumerate(runs) if "verify_wheel.py" in run)
        sbom = next(i for i, run in enumerate(runs) if "gen_sbom.py" in run)
        assert gate < sbom, "SBOM gerado antes do gate descreveria bytes nao provados"

    def test_the_sbom_is_generated_from_the_proved_dist(self):
        runs = "\n".join(_runs(_workflow(RELEASE)["jobs"]["release"]))
        assert "gen_sbom.py --dist dist" in runs

    def test_the_sbom_is_attached_to_the_release(self):
        """Gerar e nao anexar seria produzir a prova e nao entrega-la."""
        runs = "\n".join(_runs(_workflow(RELEASE)["jobs"]["release"]))
        assert "sparkforge-aws-sbom.cdx.json" in runs
        assert "gh release create" in runs

    def test_the_sbom_step_fixes_source_date_epoch(self):
        steps = _workflow(RELEASE)["jobs"]["release"]["steps"]
        [step] = [s for s in steps if "gen_sbom.py" in s.get("run", "")]
        assert step["env"]["SOURCE_DATE_EPOCH"]


class TestSupplyChainAddedNoRuntimeDependency:
    def test_the_core_still_declares_only_the_two_original_dependencies(self):
        """SBOM, lock e auditoria sao ferramenta de build e de CI. Se qualquer
        uma delas tivesse virado dependencia de runtime, todo consumidor do
        pacote pagaria por um controle que so o repositorio usa."""
        core, _, _ = gen_lock._pyproject_arrays()
        assert {gen_lock.requirement_name(req) for req in core} == {"pyyaml", "jsonschema"}

    def test_the_generators_import_only_the_standard_library(self):
        """Medido rodando os dois scripts num interpretador com `-I`, que ignora
        variavel de ambiente e o site do usuario. Um import de terceiro que
        tenha entrado sem querer falha aqui, e nao no runner."""
        for script in ("gen_lock.py", "gen_sbom.py", "audit_policy.py"):
            result = subprocess.run(
                [sys.executable, "-I", str(ROOT / "scripts" / script), "--help"],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            assert result.returncode == 0, (script, result.stderr[-600:])
