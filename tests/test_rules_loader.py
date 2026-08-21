from pathlib import Path

import pytest
import yaml

from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import CatalogError, catalog_dir, load_catalog

ROOT = Path(__file__).resolve().parents[1]


class TestCatalogDiscovery:
    def test_finds_repo_root_catalog(self):
        assert catalog_dir() == ROOT / "rules" / "catalog"

    def test_env_var_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))
        assert catalog_dir() == tmp_path


class TestLoadCommittedCatalog:
    def test_loads_every_rule_declared_on_disk(self):
        """O total carregado bate com o que existe nos arquivos, exceto routing.

        Antes este teste fixava o literal 43. Um literal aqui obriga a editar o
        teste toda vez que o catalogo cresce por um motivo legitimo -- e nao pega
        a falha que importa, que e um arquivo de area parar de ser lido em
        silencio e as regras dele sumirem do relatorio. Contar o que esta no
        disco pega isso; um numero fixo nao.
        """
        declared = 0
        for path in sorted((ROOT / "rules" / "catalog").glob("*.yaml")):
            if path.name == "routing.yaml":
                continue
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            declared += len(document.get("rules") or [])

        assert declared > 0, "nenhuma regra no disco -- o glob esta errado"
        assert len(load_catalog()) == declared

    def test_every_area_file_contributes_at_least_one_rule(self):
        """Arquivo de area vazio ou ilegivel e regressao silenciosa."""
        areas = {r["_source_file"] for r in load_catalog()}
        on_disk = {
            p.name
            for p in (ROOT / "rules" / "catalog").glob("*.yaml")
            if p.name != "routing.yaml"
        }
        assert areas == on_disk

    def test_routing_is_excluded(self):
        assert not [r for r in load_catalog() if r["id"].startswith("ROUTE-")]

    def test_every_rule_id_is_unique(self):
        ids = [r["id"] for r in load_catalog()]
        assert len(ids) == len(set(ids))

    def test_every_rule_has_required_fields(self):
        required = (
            "id",
            "category",
            "title",
            "requires_facts",
            "when",
            "runtime_scope",
            "sources",
        )
        for rule in load_catalog():
            for key in required:
                assert key in rule, f"{rule.get('id')} sem {key}"

    def test_status_is_required_of_the_rules_that_judge_and_absent_from_the_others(self):
        """`status` e status do FINDING, entao so quem produz finding o declara.

        Area de coordenacao (`executable: false`) nao julga nada: declarar
        `structural` ou `confirmed` ali seria afirmacao sobre um achado que nao
        existe. Foi essa sobrecarga -- 35 areas escritas com `status:
        structural` -- que tirou do gate de golden as 26 regras que sao
        `structural` de verdade, por carona no filtro.
        """
        for rule in load_catalog():
            if rule.get("executable", True):
                assert "status" in rule, f"{rule['id']} executavel sem status"
            else:
                assert "status" not in rule, (
                    f"{rule['id']} nao e executavel e declara status"
                )

    def test_every_rule_has_a_severity(self):
        for rule in load_catalog():
            assert "severity_default" in rule or "severity_by" in rule, rule["id"]

    def test_every_source_has_url_or_origin(self):
        for rule in load_catalog():
            for src in rule["sources"]:
                assert "url" in src or "origin" in src, rule["id"]

    def test_every_expr_is_accepted_by_the_safe_evaluator(self):
        """Expressao invalida no catalogo falha na carga, nao em producao."""
        load_catalog(validate_exprs=True)

    def test_catalog_version_is_stamped(self):
        for rule in load_catalog():
            assert isinstance(rule["catalog_version"], int)

    def test_sf_env_003_requires_the_pyspark_sentinel(self):
        """`absent: pyspark.glue_context_init` so e som quando pyspark.module_analyzed
        provar que o extrator PySpark rodou. Sem isso, analise so-Terraform dispararia
        falso positivo por ausencia vazia. Guarda contra regressao dessa correcao."""
        rule = next(r for r in load_catalog() if r["id"] == "SF-ENV-003")
        assert "pyspark.module_analyzed" in rule["requires_facts"]
        conditions = rule["when"]["all"]
        assert any(c.get("fact") == "pyspark.module_analyzed" for c in conditions)
        assert any(c.get("absent") == "pyspark.glue_context_init" for c in conditions)


class TestRejections:
    def _write(self, tmp_path, monkeypatch, name, body):
        (tmp_path / name).write_text(body, encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))

    def test_duplicate_id_raises(self, tmp_path, monkeypatch):
        one = (
            "{id: SF-X-001, category: c, title: t, requires_facts: [k], "
            "when: {all: [{fact: k}]}, status: structural, severity_default: P2, "
            'runtime_scope: {glue: "*"}, sources: [{origin: field-heuristic}]}'
        )
        body = "catalog_version: 1\narea: SF-X\nrules:\n  - " + one + "\n  - " + one + "\n"
        self._write(tmp_path, monkeypatch, "dup.yaml", body)
        with pytest.raises(CatalogError, match="duplicado"):
            load_catalog()

    def test_missing_required_field_raises(self, tmp_path, monkeypatch):
        body = "catalog_version: 1\narea: SF-X\nrules:\n  - {id: SF-X-002, title: t}\n"
        self._write(tmp_path, monkeypatch, "bad.yaml", body)
        with pytest.raises(CatalogError, match="SF-X-002"):
            load_catalog()

    def test_unsafe_expr_raises_at_load_time(self, tmp_path, monkeypatch):
        body = (
            "catalog_version: 1\n"
            "area: SF-X\n"
            "rules:\n"
            "  - id: SF-X-003\n"
            "    category: c\n"
            "    title: t\n"
            "    requires_facts: [k]\n"
            "    when:\n"
            "      all:\n"
            "        - {fact: k, expr: \"__import__('os').system('x')\"}\n"
            "    status: structural\n"
            "    severity_default: P2\n"
            '    runtime_scope: {glue: "*"}\n'
            "    sources: [{origin: field-heuristic}]\n"
        )
        self._write(tmp_path, monkeypatch, "unsafe.yaml", body)
        with pytest.raises(CatalogError, match="SF-X-003"):
            load_catalog(validate_exprs=True)

    def _rule_with_when(self, when_block):
        return (
            "catalog_version: 1\n"
            "area: SF-X\n"
            "rules:\n"
            "  - id: SF-X-004\n"
            "    category: c\n"
            "    title: t\n"
            "    requires_facts: [k]\n"
            "    when:\n" + when_block + "    status: structural\n"
            "    severity_default: P2\n"
            '    runtime_scope: {glue: "*"}\n'
            "    sources: [{origin: field-heuristic}]\n"
        )

    def test_condition_without_fact_or_absent_raises(self, tmp_path, monkeypatch):
        """Typo na chave (`facts:` em vez de `fact:`) faria a regra nunca disparar,
        em silencio: o motor nao acha candidato, nao ha erro, relatorio sai limpo.
        Falso negativo mudo e o pior modo de falha, entao morre na carga."""
        body = self._rule_with_when("      all:\n        - {facts: k}\n")
        self._write(tmp_path, monkeypatch, "typo.yaml", body)
        with pytest.raises(CatalogError, match="sem `fact` nem `absent`"):
            load_catalog()

    def test_error_names_the_keys_actually_present(self, tmp_path, monkeypatch):
        body = self._rule_with_when("      all:\n        - {facts: k, where: {attrs.a: 1}}\n")
        self._write(tmp_path, monkeypatch, "typo2.yaml", body)
        with pytest.raises(CatalogError, match="facts, where"):
            load_catalog()

    def test_when_without_all_or_any_raises(self, tmp_path, monkeypatch):
        body = self._rule_with_when("      todos:\n        - {fact: k}\n")
        self._write(tmp_path, monkeypatch, "nogroup.yaml", body)
        with pytest.raises(CatalogError, match="sem grupo"):
            load_catalog()

    def test_condition_that_is_not_a_mapping_raises(self, tmp_path, monkeypatch):
        body = self._rule_with_when("      all:\n        - k\n")
        self._write(tmp_path, monkeypatch, "scalar.yaml", body)
        with pytest.raises(CatalogError, match="precisa ser um mapa"):
            load_catalog()

    def test_absent_only_condition_is_valid(self, tmp_path, monkeypatch):
        """`absent` sem `fact` e forma legitima: regra que dispara pela ausencia."""
        body = self._rule_with_when("      all:\n        - {absent: other.kind}\n")
        self._write(tmp_path, monkeypatch, "absent.yaml", body)
        assert [r["id"] for r in load_catalog()] == ["SF-X-004"]

    # --- `executable`: a fronteira entre regra que julga e area de coordenacao ---
    #
    # As de baixo fecham o buraco que a expansao agentica abriu ao escrever 35
    # areas de coordenacao com `status: structural` e ensinar os gates a filtrar
    # por esse valor. `status` e status de FINDING; usa-lo como marca de "isto
    # nao e regra" sobrecarregou um campo com dois sentidos, tirou do gate as 26
    # regras que sao `structural` de verdade, e nao impedia uma regra de
    # deteccao real de escapar de quatro redes so mudando uma palavra.

    def _rule_body(self, extra_lines, when_block=None):
        if when_block is None:
            when_block = "      all:\n        - {fact: k}\n"
        return (
            "catalog_version: 1\n"
            "area: SF-X\n"
            "rules:\n"
            "  - id: SF-X-005\n"
            "    category: c\n"
            "    title: t\n"
            "    requires_facts: []\n"
            "    when:\n" + when_block + "    severity_default: P2\n"
            "    runtime_scope: {}\n"
            "    sources: []\n" + extra_lines
        )

    def test_executable_rule_without_any_condition_raises(self, tmp_path, monkeypatch):
        """`when: {all: []}` passava por `_validate_conditions` -- o grupo existe.

        E o falso negativo mudo que aquela funcao foi escrita para matar, um
        nivel acima: a regra nunca dispara, nao ha erro, o relatorio sai limpo.
        Antes da expansao nenhuma regra commitada tinha essa forma; as 35 areas
        de coordenacao a introduziram, e o loader precisa distinguir "inerte de
        proposito" de "inerte por engano".
        """
        body = self._rule_body("    status: structural\n", when_block="      all: []\n")
        self._write(tmp_path, monkeypatch, "vazia.yaml", body)
        with pytest.raises(CatalogError, match="sem nenhuma condicao"):
            load_catalog()

    def test_non_executable_rule_that_declares_a_condition_raises(
        self, tmp_path, monkeypatch
    ):
        """Declarar-se inerte e ter condicao real e a mentira que abre o buraco.

        Uma regra de deteccao marcada assim sairia do gate de fixture, do gate
        de ramo de severidade e das duas assercoes de area muda dos testes ponta
        a ponta -- quatro redes de uma vez, com a suite verde.
        """
        body = self._rule_body("    executable: false\n")
        self._write(tmp_path, monkeypatch, "mentira.yaml", body)
        with pytest.raises(CatalogError, match="when"):
            load_catalog()

    @pytest.mark.parametrize(
        "campo,valor",
        [
            ("requires_facts", "[k]"),
            ("sources", "[{origin: field-heuristic}]"),
            ("blocked_on", "extractor-x"),
            ("status", "structural"),
        ],
    )
    def test_non_executable_rule_that_declares_judging_fields_raises(
        self, tmp_path, monkeypatch, campo, valor
    ):
        """Cada campo aqui e afirmacao sobre um achado que nao pode existir.

        `requires_facts` e `sources` saem vazios do corpo base e a linha extra
        sobrescreve o valor -- e o valor preenchido que se testa, nao a chave.
        """
        body = self._rule_body(
            "    executable: false\n    " + campo + ": " + valor + "\n",
            when_block="      all: []\n",
        )
        self._write(tmp_path, monkeypatch, "campo-" + campo + ".yaml", body)
        with pytest.raises(CatalogError, match=campo):
            load_catalog()

    def test_the_executable_flag_has_to_be_boolean(self, tmp_path, monkeypatch):
        """`executable: "false"` e verdadeiro em Python, e nao pode passar calado."""
        body = self._rule_body(
            '    executable: "false"\n', when_block="      all: []\n"
        )
        self._write(tmp_path, monkeypatch, "naobool.yaml", body)
        with pytest.raises(CatalogError, match="booleano"):
            load_catalog()

    def test_a_coordination_area_loads_and_cannot_produce_a_finding(
        self, tmp_path, monkeypatch
    ):
        """A forma valida, e a prova de que ela e inerte por contrato.

        Que `when: {all: []}` nao produza achado hoje e propriedade de
        `_evaluate_when`, que itera candidatos e nao encontra nenhum -- nao e
        `all([]) is True`, que devolveria o oposto. Propriedade de implementacao
        nao declarada some no proximo refactor, entao ela fica travada aqui.
        """
        body = self._rule_body("    executable: false\n", when_block="      all: []\n")
        self._write(tmp_path, monkeypatch, "area.yaml", body)
        regras = load_catalog()
        assert [r["id"] for r in regras] == ["SF-X-005"]

        fact = Fact(kind="k", subject={"path": "x"}, measures={"n": 1})
        assert judge([fact], regras, {}) == []
        assert judge([], regras, {}) == []

    def test_every_committed_coordination_area_is_inert(self):
        """O catalogo real, nao um dubles: nenhuma area de coordenacao julga.

        Se uma delas ganhar condicao sem virar executavel, o loader recusa; se
        ganhar condicao E virar executavel, ela cai no gate de golden. Este
        teste cobre o terceiro caminho -- a que passa pelos dois e ainda assim
        produz achado.
        """
        areas = [r for r in load_catalog() if not r.get("executable", True)]
        assert areas, "nenhuma area de coordenacao no catalogo: o filtro mudou?"
        facts = [
            Fact(kind=kind, subject={"path": "x"}, measures={"n": 1})
            for kind in ("pyspark.conf_set", "iceberg.snapshot", "glue.job")
        ]
        assert judge(facts, areas, {}) == []

    def test_real_catalog_still_passes_condition_validation(self):
        """Nenhuma regra commitada pode ter condicao malformada.

        Sem literal de contagem: o que este teste garante e que
        `validate_exprs=True` nao levanta CatalogError sobre o catalogo real. A
        contagem vive em `test_loads_every_rule_declared_on_disk`, comparada com
        o disco.
        """
        assert load_catalog(validate_exprs=True)


class TestCatalogPathIsContained:
    """SPARKFORGE_CATALOG vem do ambiente — em plugin instalado e escrito por
    configuracao externa (.mcp.json). Sem contencao, um valor com `..` ou um
    symlink apontando para fora vira leitura arbitraria de sistema de arquivos."""

    def test_env_var_pointing_at_a_file_is_rejected(self, tmp_path, monkeypatch):
        target = tmp_path / "nao-e-diretorio.txt"
        target.write_text("x", encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(target))
        with pytest.raises(CatalogError, match="nao e um diretorio"):
            catalog_dir()

    def test_env_var_pointing_at_a_missing_dir_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path / "inexistente"))
        with pytest.raises(CatalogError, match="nao e um diretorio"):
            catalog_dir()

    def test_env_var_is_resolved_to_an_absolute_path(self, tmp_path, monkeypatch):
        nested = tmp_path / "a" / ".." / "a"
        (tmp_path / "a").mkdir()
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(nested))
        resolved = catalog_dir()
        assert resolved.is_absolute()
        assert ".." not in resolved.parts

    def test_traversal_out_of_the_catalog_is_refused(self, tmp_path):
        from sparkforge.rules.loader import safe_catalog_file

        base = tmp_path / "catalog"
        base.mkdir()
        with pytest.raises(CatalogError, match="fora do diretorio"):
            safe_catalog_file(base, "../../etc/passwd")

    def test_a_plain_name_inside_the_catalog_is_allowed(self, tmp_path):
        from sparkforge.rules.loader import safe_catalog_file

        base = tmp_path / "catalog"
        base.mkdir()
        assert safe_catalog_file(base, "pyspark.yaml").parent == base.resolve()

    def test_the_real_catalog_still_loads_through_the_check(self):
        """A contencao de path nao pode rejeitar o catalogo legitimo."""
        assert load_catalog(validate_exprs=True)
