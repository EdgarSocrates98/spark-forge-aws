"""Golden test do corpus de validacao funcional.

Arquivo dedicado, e por um motivo que nenhum outro corpus tem: as fixtures daqui
exercitam DOIS verbos, e o `input/` traz DUAS fontes de fact mais os DOIS
resultados que o operador mediu.

  * `input/*.py` da o ALVO, por `pyspark.write.attrs.target`;
  * `input/catalog/*.json` da COLUNA E TIPO, por `catalog.table_schema`;
  * `input/before.json` e `input/after.json`, quando existem, sao os valores que
    o OPERADOR mediu de cada lado. O motor nunca os produz -- se produzisse,
    estaria medindo, e a fase inteira existe para dizer que quem mede e o
    operador.

As duas fontes de fact moram na mesma fixture porque **nenhum verbo produz as
duas no mesmo arquivo**, e sem as duas os eixos de schema e de agregado nao
existem. Isso nao e hipotese: a D-4c-6 mediu que as SETE fixtures do repositorio
que emitem `pyspark.write` saem todas com `undeclared_axes: ["aggregates",
"keys", "schema"]`, porque nenhuma delas junta um `catalog.table_schema` do
MESMO alvo. Este corpus e a divida que aquela medicao deixou aberta: sem ele, os
eixos de schema e de agregados nunca apareceriam em golden nenhum, e a fase
entregaria dois dos quatro eixos sem prova.

A presenca dos resultados separa as duas formas de fixture:

  * so `input/` -> fixture do PLANO. O golden guarda os `funcval.plan` e os
    `funcval.unresolved` da derivacao.
  * mais `before.json`/`after.json` -> fixture da COMPARACAO. O golden guarda o
    que a comparacao produziu, e o plano vira ENTRADA -- fica FORA do golden,
    pela mesma disciplina de `test_fixtures_golden_bench.py` e
    `test_fixtures_golden_callgraph.py`: repetir a entrada faria uma mudanca em
    `build_plan` quebrar sete goldens de comparacao pelo mesmo motivo,
    escondendo qual dos dois contratos regrediu.

Consequencia dessa disciplina, e ela esta registrada como D-4c-19: o campo
`origin` do check NAO aparece no golden de comparacao, porque `funcval.check_delta`
nao o carrega -- o plano e que carrega. Entao a procedencia do eixo declarado e
provada onde ela e observavel, no golden de `plan_com_chave_declarada`, que poe
`origin: "declared"` com `derived_from: []` ao lado de quatro derivados com
`origin: "derived"` e o `fact_id`. `TestAdversarial` ainda confere o plano
derivado de `duplicate_key_appeared` diretamente, para que a chave daquela
fixture nao possa virar derivada sem que nada acuse.

Nesta task todo `findings.json` sai VAZIO: as cinco regras `SF-FVAL-*` nascem na
Task 6, e fixture que declarasse achado antes da regra existir estaria provando
uma regra que ninguem escreveu. Os `expects_rules: []` de agora sao o correto, e
e a Task 6 que os preenche.

`TestAdversarial` e a parte que impede a fixture de virar decoracao: cada
diretorio afirma no nome o que prova, e ali as medidas do golden sao lidas contra
essa afirmacao. Fixture cujo nome diz uma coisa e cujos numeros dizem outra passa
em todos os testes de igualdade acima e nao prova nada.
"""
import json
from pathlib import Path

import pytest
import yaml

from scripts.regen_fixtures import with_plan_ref
from sparkforge.facts.catalog_schema import extract_catalog_schema_tree
from sparkforge.facts.funcval import EMITTED_KINDS, build_comparison, build_plan
from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "funcval"

REQUIRED_FIXTURES = {
    "aggregate_outside_tolerance",
    "aggregate_within_tolerance",
    "clean_equivalence",
    "count_diverged",
    "duplicate_key_appeared",
    "partial_coverage",
    "plan_com_chave_declarada",
    "plan_sem_chave",
    "schema_diverged",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _source_facts(directory: Path):
    """Os facts de origem, na MESMA ordem de chamada de
    `scripts/regen_fixtures.py::regen_funcval`."""
    input_dir = directory / "input"
    facts = list(extract_tree(input_dir, repo_root=input_dir))
    catalog_dir = input_dir / "catalog"
    if catalog_dir.is_dir():
        facts.extend(extract_catalog_schema_tree(catalog_dir, repo_root=input_dir))
    return facts


def _keys(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    return tuple((meta.get("funcval") or {}).get("keys") or ())


def _plan_facts(directory: Path):
    return build_plan(
        _source_facts(directory), keys=_keys(directory), path_hint=directory.name
    )


def _derive(directory: Path):
    """O plano, e depois a comparacao quando a fixture tem os dois resultados.

    Espelha `regen_funcval` passo a passo, inclusive a guarda de UM plano: um
    resultado descreve UM alvo, e escolher entre planos aqui seria adivinhar.

    Um passo NAO e espelhado, e sim IMPORTADO: `with_plan_ref`. O `plan_ref` e o
    `Fact.id` do plano derivado deste mesmo corpus (D-4c-22), e reimplementa-lo
    aqui daria duas fontes para um id que so tem uma -- exatamente o que
    escreve-lo a mao no `input/` faria. Todo o resto continua reimplementado de
    proposito, porque ali a divergencia entre teste e regenerador e o que se quer
    ver.
    """
    derived = _plan_facts(directory)
    input_dir = directory / "input"
    before_file = input_dir / "before.json"
    after_file = input_dir / "after.json"
    if not (before_file.is_file() and after_file.is_file()):
        return derived

    plans = [f for f in derived if f.kind == "funcval.plan"]
    assert len(plans) == 1, (
        f"{directory.name}: fixture de comparacao precisa de UM plano, "
        f"e o corpus derivou {len(plans)}"
    )
    return build_comparison(
        plans[0].attrs,
        with_plan_ref(json.loads(before_file.read_text(encoding="utf-8")), plans[0]),
        with_plan_ref(json.loads(after_file.read_text(encoding="utf-8")), plans[0]),
        path_hint=directory.name,
    )


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    derived = _derive(directory)
    findings, skipped = judge(derived, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, derived, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _one(facts, kind):
    matches = _by_kind(facts, kind)
    assert len(matches) == 1, f"esperado exatamente um {kind}, veio {len(matches)}"
    return matches[0]


def _delta(facts, check):
    matches = [f for f in _by_kind(facts, "funcval.check_delta") if f.attrs["check"] == check]
    assert len(matches) == 1, f"esperado exatamente um check_delta de {check}"
    return matches[0]


def _plan_of(facts, target):
    matches = [f for f in _by_kind(facts, "funcval.plan") if f.attrs["target"] == target]
    assert len(matches) == 1, f"esperado exatamente um funcval.plan de {target}"
    return matches[0]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_derivation_is_deterministic(self, directory):
        assert [f.to_dict() for f in _derive(directory)] == [
            f.to_dict() for f in _derive(directory)
        ]


class TestAdversarial:
    def test_the_corpus_exercises_every_kind_of_the_namespace(self):
        """Os quatro kinds de `EMITTED_KINDS` precisam nascer em algum diretorio
        daqui. `tests/test_fixtures_kind_coverage.py` faz a mesma pergunta sobre
        o corpus inteiro; esta copia local diz QUAL corpus deveria ter coberto,
        que e a informacao que falta quando aquele teste acende."""
        kinds = set()
        for directory in fixture_dirs():
            kinds |= {f.kind for f in _derive(directory)}
        assert kinds == set(EMITTED_KINDS)

    def test_the_corpus_closes_the_debt_that_no_other_fixture_could(self):
        """A D-4c-6 em forma de teste. As sete fixtures reais com
        `pyspark.write` nao juntam um `catalog.table_schema` do mesmo alvo, e por
        isso saem todas com os tres eixos por declarar. Este corpus existe para
        que schema e agregados EXISTAM em golden: se nenhuma fixture daqui
        derivar os dois eixos, o corpus voltou a ser o que ele veio consertar."""
        plan = _plan_of(_plan_facts(FIXTURES / "plan_sem_chave"), "db.eventos")
        assert "schema" in plan.attrs["checks"]
        assert [c for c in plan.attrs["checks"] if c.startswith("agg:sum:")]
        # E os dois eixos vem de um `catalog.table_schema` REAL do mesmo alvo,
        # nao de um plano escrito a mao: o `derived_from` cita o fact.
        source = {f.id for f in _source_facts(FIXTURES / "plan_sem_chave")}
        assert set(plan.attrs["derived_from"]) <= source
        assert set(plan.attrs["checks"]["schema"]["derived_from"]) <= source

    # -- contagem ---------------------------------------------------------
    def test_count_diverged_moves_the_count_and_nothing_else(self):
        """Duas linhas a mais, e so a contagem enxerga. As linhas novas sao
        orfas com as medidas nulas, e `sum` ignora nulo -- entao os agregados e
        o schema ficam parados. Sem essa separacao a fixture provaria "alguma
        coisa mudou", que nao e o que o nome dela diz."""
        _, facts, _, _ = run_fixture(FIXTURES / "count_diverged")
        count = _delta(facts, "count")
        assert count.attrs["diverged"] is True
        assert count.measures["value_after"] - count.measures["value_before"] == 2
        analyzed = _one(facts, "funcval.analyzed")
        assert analyzed.measures["diverged_check_count"] == 1
        for check in ("schema", "agg:sum:cliente_id"):
            assert _delta(facts, check).attrs["diverged"] is False
        # E a cobertura esta cheia: o unico check divergente nao e um check que
        # faltou, e a SF-FVAL-005 nao tem o que ler aqui.
        assert analyzed.measures["reported_check_count"] == analyzed.measures[
            "planned_check_count"
        ]

    # -- schema -----------------------------------------------------------
    def test_schema_diverged_shows_the_three_shapes_of_divergence(self):
        """Coluna que sumiu, coluna que apareceu e tipo que mudou, num caso so."""
        _, facts, _, _ = run_fixture(FIXTURES / "schema_diverged")
        schema = _delta(facts, "schema")
        assert schema.attrs["diverged"] is True
        assert schema.attrs["removed_columns"] == ["dt"]
        assert schema.attrs["added_columns"] == ["carga_ts"]
        assert schema.attrs["type_changed_columns"] == ["valor"]

    def test_schema_diverged_would_be_invisible_to_a_column_count(self):
        """A razao de o check carregar o MAPA e nao `column_count`: aqui o numero
        de colunas e o mesmo dos dois lados. Um check de contagem de coluna nao
        veria nada, e a SF-FVAL-002 fala de coluna ausente E de tipo mudado."""
        _, facts, _, _ = run_fixture(FIXTURES / "schema_diverged")
        schema = _delta(facts, "schema")
        assert schema.measures["before_column_count"] == schema.measures["after_column_count"]
        assert schema.attrs["diverged"] is True

    def test_schema_diverged_still_compares_valor_as_the_plan_said(self):
        """O tipo vem do PLANO. `valor` virou `decimal(18,2)` do lado depois, e a
        comparacao continua relativa porque o plano derivou `double` do catalogo
        -- se o resultado escolhesse, o operador decidiria o rigor com que o
        proprio numero dele e julgado."""
        _, facts, _, _ = run_fixture(FIXTURES / "schema_diverged")
        valor = _delta(facts, "agg:sum:valor")
        assert valor.attrs["type"] == "double"
        assert valor.attrs["comparison"] == "relative"

    # -- chave ------------------------------------------------------------
    def test_duplicate_key_appeared_hits_the_strict_trigger_and_only_it(self):
        """Antes ZERO, depois maior que zero -- o gatilho estrito da §6, e nao
        "cresceu". A contagem nao se move porque foram os VALORES da chave que
        colidiram, nao o numero de linhas; se a contagem se mexesse, a fixture
        provaria SF-FVAL-001 junto e a 003 nunca teria prova isolada."""
        _, facts, _, _ = run_fixture(FIXTURES / "duplicate_key_appeared")
        key = _delta(facts, "key:pedido_id")
        assert key.attrs["axis"] == "key"
        assert key.attrs["comparison"] == "exact"
        assert key.attrs["diverged"] is True
        assert key.measures["value_before"] == 0
        assert key.measures["value_after"] > 0
        assert _one(facts, "funcval.analyzed").measures["diverged_check_count"] == 1
        assert _delta(facts, "count").attrs["diverged"] is False

    def test_the_key_of_duplicate_key_appeared_is_declared_and_says_so(self):
        """A procedencia, conferida no PLANO daquela fixture -- que e entrada da
        comparacao e por isso nao esta no golden dela (D-4c-19).

        Se a chave virasse derivada, o achado P0 passaria a afirmar que o motor
        descobriu a chave, e nenhum fact do repositorio nomeia chave de negocio.
        `derived_from` VAZIO e a forma de dizer "isto nao veio de fact nenhum"
        sem que a chave desapareca."""
        plan = _plan_of(_plan_facts(FIXTURES / "duplicate_key_appeared"), "db.eventos")
        check = plan.attrs["checks"]["key:pedido_id"]
        assert check["origin"] == "declared"
        assert check["derived_from"] == []
        assert plan.attrs["checks"]["count"]["origin"] == "derived"

    # -- agregado ---------------------------------------------------------
    def test_aggregate_outside_tolerance_refuses_to_call_it_divergence(self):
        """A D-4c-10 no golden, e a parte que se perde de vista: a soma esta
        4,76% longe, e `diverged_check_count` e ZERO. O modulo NAO julga ponto
        flutuante -- o limiar mora no catalogo. Ler esse zero como "nada
        divergiu" e o erro que `relative_delta_check_count` existe para
        impedir."""
        _, facts, _, _ = run_fixture(FIXTURES / "aggregate_outside_tolerance")
        valor = _delta(facts, "agg:sum:valor")
        assert valor.attrs["comparison"] == "relative"
        assert "diverged" not in valor.attrs
        assert valor.attrs["diverged_omitted_reason"]
        assert valor.measures["relative_delta"] > 0.01
        analyzed = _one(facts, "funcval.analyzed")
        assert analyzed.measures["diverged_check_count"] == 0
        assert analyzed.measures["relative_delta_check_count"] == 1

    def test_aggregate_within_tolerance_is_the_legitimate_repartition(self):
        """A metade negativa da SF-FVAL-004. `_round` corta os valores em tres
        casas e os dois lados saem IDENTICOS em `measures`; `relative_delta` vai
        a tres digitos SIGNIFICATIVOS e sobrevive em 1e-12. Se ele fosse
        arredondado como os valores, sairia 0.0 e toda divergencia pequena
        passaria (D-4c-12)."""
        _, facts, _, _ = run_fixture(FIXTURES / "aggregate_within_tolerance")
        valor = _delta(facts, "agg:sum:valor")
        assert valor.measures["value_before"] == valor.measures["value_after"]
        assert valor.measures["abs_delta"] == 0.0
        assert 0 < valor.measures["relative_delta"] < 1e-9

    def test_the_two_aggregate_fixtures_differ_by_the_number_and_nothing_else(self):
        """O par so e util se a UNICA diferenca entre eles for a grandeza que a
        regra vai ler. Mesmos checks, mesmo veredito ausente, mesma cobertura --
        e `relative_delta` separado por mais de nove ordens de grandeza."""
        _, dentro, _, _ = run_fixture(FIXTURES / "aggregate_within_tolerance")
        _, fora, _, _ = run_fixture(FIXTURES / "aggregate_outside_tolerance")
        assert {f.attrs["check"] for f in _by_kind(dentro, "funcval.check_delta")} == {
            f.attrs["check"] for f in _by_kind(fora, "funcval.check_delta")
        }
        assert _one(dentro, "funcval.analyzed").measures == _one(
            fora, "funcval.analyzed"
        ).measures
        assert _delta(fora, "agg:sum:valor").measures["relative_delta"] > 1e9 * _delta(
            dentro, "agg:sum:valor"
        ).measures["relative_delta"]

    # -- cobertura --------------------------------------------------------
    def test_partial_coverage_keeps_the_three_states_apart(self):
        """Zero, indisponivel e ausente sao TRES coisas, e so a terceira e
        cobertura faltante. Se duas colapsassem, `reported_check_count`
        continuaria fechando com o numero errado e ninguem veria."""
        _, facts, _, _ = run_fixture(FIXTURES / "partial_coverage")
        analyzed = _one(facts, "funcval.analyzed")
        assert analyzed.measures["planned_check_count"] == 5
        assert analyzed.measures["reported_check_count"] == 3

        # 1. rodou e deu zero -> COMPARADO, e conta como reportado.
        zero = _delta(facts, "key:pedido_id")
        assert zero.measures["value_before"] == 0 == zero.measures["value_after"]
        assert zero.attrs["diverged"] is False

        # 2. rodou e nao deu -> unresolved, e NAO conta como reportado.
        # 3. nao foi reportado -> unresolved de outra razao.
        cegos = _by_kind(facts, "funcval.unresolved")
        razoes = {f.attrs["check"]: f.attrs["reason"] for f in cegos}
        assert razoes == {
            "agg:sum:valor": "check_value_unavailable",
            "schema": "check_not_reported",
        }
        indisponivel = _one(
            [f for f in facts if f.attrs.get("check") == "agg:sum:valor"], "funcval.unresolved"
        )
        assert indisponivel.attrs["state"] == {"before": "unavailable", "after": "unavailable"}
        assert indisponivel.attrs["detail"]["before"]
        ausente = _one(
            [f for f in facts if f.attrs.get("check") == "schema"], "funcval.unresolved"
        )
        assert ausente.attrs["state"] == {"before": "absent", "after": "absent"}
        assert ausente.attrs["detail"] == {}
        # Nenhum dos dois virou check_delta: um valor inventado ali seria
        # observacao inventada.
        assert {f.attrs["check"] for f in _by_kind(facts, "funcval.check_delta")} == {
            "count",
            "agg:sum:cliente_id",
            "key:pedido_id",
        }

    # -- o negativo das cinco ---------------------------------------------
    def test_clean_equivalence_gives_the_five_rules_nothing_to_hold(self):
        """A metade negativa do corpus inteiro. Os quatro eixos cobertos, os
        cinco checks reportados, nenhuma divergencia, nenhum ponto cego. Se
        qualquer SF-FVAL disparar aqui, ela acusa equivalencia limpa -- o P0 que
        ninguem investiga duas vezes."""
        _, facts, findings, _ = run_fixture(FIXTURES / "clean_equivalence")
        analyzed = _one(facts, "funcval.analyzed")
        assert analyzed.measures["planned_check_count"] == 5
        assert analyzed.measures["reported_check_count"] == 5
        assert analyzed.measures["compared_check_count"] == 5
        assert analyzed.measures["diverged_check_count"] == 0
        assert analyzed.measures["unplanned_check_count"] == 0
        assert analyzed.attrs["undeclared_axes"] == []
        assert analyzed.attrs["blocked_by"] == []
        assert _by_kind(facts, "funcval.unresolved") == []
        assert findings == []
        # Os quatro eixos, presentes por CHAVE e nao por contagem de check.
        assert {f.attrs["axis"] for f in _by_kind(facts, "funcval.check_delta")} == {
            "count",
            "schema",
            "key",
            "aggregate",
        }

    def test_every_comparison_carries_the_plan_ref_of_its_own_plan(self):
        """A D-4c-22 em forma de teste, e o que ela custou a distinguir: campo
        VAZIO e campo que este corpus nao alimenta sao indistinguiveis para quem
        le o golden, e o `plan_ref: ""` das sete comparacoes era o segundo se
        passando pelo primeiro.

        A afirmacao e dupla, e as duas metades sao necessarias. Nao-vazio prova
        que o campo e alimentado; igual ao `Fact.id` do plano DERIVADO deste
        `input/` prova que ele nao foi escrito a mao -- um id constante sobrevive
        a nao-vazio e morre aqui, que e o defeito que a divida recusou cometer.
        """
        checados = 0
        for directory in fixture_dirs():
            input_dir = directory / "input"
            if not (input_dir / "before.json").is_file():
                continue
            plano = _one(_plan_facts(directory), "funcval.plan")
            analyzed = _one(_derive(directory), "funcval.analyzed")
            assert analyzed.attrs["plan_ref"] == plano.id, directory.name
            assert analyzed.attrs["plan_ref"], directory.name
            checados += 1
        assert checados == 7

    def test_every_comparison_declares_the_proxy_limit_in_the_output(self):
        """Criterio 8 da §9: o limite mora na SAIDA, nao no spec. Quem le
        "quatro proxies bateram" nao pode ter que ir ao spec descobrir o que isso
        nao prova."""
        for directory in fixture_dirs():
            facts = _derive(directory)
            for analyzed in _by_kind(facts, "funcval.analyzed"):
                assert analyzed.attrs["proxies"] == ["count", "schema", "keys", "aggregates"]
                assert "proxies" in analyzed.attrs["proxy_limit"]

    # -- os dois planos ---------------------------------------------------
    def test_plan_sem_chave_writes_the_missing_axis_instead_of_omitting_it(self):
        """O eixo de chaves DITO, com a razao. Ausencia escrita, na mesma
        disciplina de `dq.unresolved` e `bench.unresolved`: quem le nao pode ter
        que deduzir de um campo que sumiu."""
        facts = _derive(FIXTURES / "plan_sem_chave")
        plan = _plan_of(facts, "db.eventos")
        assert plan.attrs["undeclared_axes"] == ["keys"]
        razao = plan.attrs["undeclared_axes_reason"]["keys"]
        assert "chave de negocio" in razao and "--key" in razao
        assert plan.measures["declared_check_count"] == 0
        assert [c for c in plan.attrs["checks"] if c.startswith("key:")] == []

    def test_plan_sem_chave_proves_undeclared_axes_belongs_to_the_plan(self):
        """D-4c-6. O alvo em forma de caminho nao casa com simbolo nenhum do
        catalogo, entao ele nao tem schema NEM agregado, e `undeclared_axes` traz
        os tres. Se o campo fosse do eixo de chaves, este plano estaria calando
        dois eixos enquanto declara um -- meia-verdade com cara de declaracao."""
        facts = _derive(FIXTURES / "plan_sem_chave")
        caminho = _plan_of(facts, "s3://bucket/curated/eventos/")
        assert caminho.attrs["undeclared_axes"] == ["aggregates", "keys", "schema"]
        assert list(caminho.attrs["checks"]) == ["count"]
        cego = _one(facts, "funcval.unresolved")
        assert cego.attrs["reason"] == "catalog_schema_unmatched"
        assert cego.attrs["target"] == "s3://bucket/curated/eventos/"

    def test_plan_sem_chave_gives_each_target_its_own_plan(self):
        """D-4c-4. As chaves de `checks` (`count`, `schema`, `agg:sum:*`) nao tem
        namespace de alvo: dois alvos num plano so colidiriam nelas, e o contrato
        do resultado fixa `target` como string singular."""
        facts = _derive(FIXTURES / "plan_sem_chave")
        planos = _by_kind(facts, "funcval.plan")
        assert len(planos) == 2
        assert len({p.attrs["target"] for p in planos}) == 2
        assert len({p.id for p in planos}) == 2

    def test_plan_com_chave_declarada_shows_the_two_origins_side_by_side(self):
        """O unico lugar do corpus onde a procedencia e observavel, e o motivo de
        ele existir: `origin` aparece nos DOIS casos. Se so aparecesse no
        declarado seria excecao, e excecao nao e procedencia -- ninguem le um
        campo que so existe quando a resposta e feia."""
        facts = _derive(FIXTURES / "plan_com_chave_declarada")
        plan = _plan_of(facts, "db.eventos")
        checks = plan.attrs["checks"]
        assert checks["key:pedido_id+dt"] == {
            "origin": "declared",
            "type": "bigint",
            "derived_from": [],
        }
        derivados = {c: v for c, v in checks.items() if not c.startswith("key:")}
        assert derivados
        for nome, check in derivados.items():
            assert check["origin"] == "derived", nome
            assert check["derived_from"], nome
        assert plan.measures["declared_check_count"] == 1
        assert plan.measures["derived_check_count"] == len(derivados)
        # Os quatro eixos cobertos: com a chave declarada, nada fica por declarar.
        assert plan.attrs["undeclared_axes"] == []

    def test_the_declared_key_is_composite_and_the_name_keeps_it(self):
        """A virgula do `--key pedido_id,dt` faz UMA chave de duas colunas, nao
        duas chaves. O `+` no nome do check e o que preserva isso -- sem ele,
        "chave composta duplicou" e "duas chaves duplicaram" ficariam iguais."""
        facts = _derive(FIXTURES / "plan_com_chave_declarada")
        chaves = [c for c in _plan_of(facts, "db.eventos").attrs["checks"] if c.startswith("key:")]
        assert chaves == ["key:pedido_id+dt"]

    def test_the_declared_key_is_not_checked_against_the_catalog(self):
        """D-4c-8. O plano nao confere a chave declarada contra o schema: a
        afirmacao e do operador, e julga-la seria SF-DQ. As duas colunas daqui
        por acaso existem no dump; a prova e que o plano nao emite ponto cego
        nenhum sobre elas, e nao emitiria se elas nao existissem."""
        facts = _derive(FIXTURES / "plan_com_chave_declarada")
        assert _by_kind(facts, "funcval.unresolved") == []
        colunas = set(
            c.removeprefix("agg:sum:")
            for c in _plan_of(facts, "db.eventos").attrs["checks"]
            if c.startswith("agg:sum:")
        )
        # `dt` e `pedido_id` sao `string` no dump, entao nem sao colunas de
        # agregado -- e mesmo assim entram na chave sem uma palavra do motor.
        assert "dt" not in colunas and "pedido_id" not in colunas
