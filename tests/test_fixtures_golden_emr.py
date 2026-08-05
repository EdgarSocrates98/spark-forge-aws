"""Golden test do corpus de cluster EMR on EC2.

Arquivo dedicado, mesma razao de `test_fixtures_golden_athena.py`: a fixture e
um dump `*.json` sob `input/`, extraido por `extract_emr_cluster_path` -- um
dump ja e a uniao das saidas dos seis subcomandos de um cluster, entao nao ha
variante `_tree`.

Ate a Task 3 nenhuma fixture deste corpus disparava regra: o extrator entrou
antes da area `SF-EMR` de proposito (regra sem fact e regra que nunca foi
provada). Com a Task 4 as regras existem, e `expects_rules` deixou de ser
uniformemente vazio -- os `[]` que sobraram passaram a ser goldens NEGATIVOS
reais: se alguma regra disparar sobre um dump que nao a justifica, o diff
aparece aqui.

Tres deles carregam essa carga de proposito, e `TestAdversarial` abaixo trava
cada um: `all_spot_groups_maximize` e a recomendacao oficial da AWS escrita como
dump (primary Spot com core Spot), `reconfiguration_pending_with_managed_scaling`
tem todos os ingredientes de SF-EMR-003 e e barrado so pelo guarda de evidencia,
e `configuration_not_applied` prova que a divergencia de configuracao e por
grupo.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.emr_cluster import extract_emr_cluster_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "emr"

REQUIRED_FIXTURES = {
    "instance_groups_spot_task",
    "instance_fleets_maximize",
    "configuration_not_applied",
    "missing_instance_model",
    "malformed_sections",
    "empty_dump",
    # Task 4: os dois que a area SF-EMR acrescentou. O primeiro e o unico golden
    # positivo de SF-EMR-003; o segundo e a contraparte NEGATIVA de SF-EMR-001 e
    # SF-EMR-004, e e um cluster que a AWS recomenda -- e o corpus precisa provar
    # que a ferramenta nao acusa a recomendacao oficial.
    "managed_scaling_static_executors",
    "all_spot_groups_maximize",
    # O par de `managed_scaling_static_executors`: mesmo gatilho, e a unica
    # diferenca e a qualidade da evidencia. Sem ele o `absent:
    # emr.configuration.unapplied` de SF-EMR-003 seria uma linha que nunca fez
    # diferenca em golden nenhum.
    "reconfiguration_pending_with_managed_scaling",
    # Task 4b: a proteção PELA METADE. `yarn.node-labels.enabled=true` sozinho
    # aparenta prender o ApplicationMaster e não prende, e é o único cenário em
    # que um extrator ingênuo -- "vi propriedade de node label, logo está
    # protegido" -- calaria SF-EMR-008 sobre um cluster genuinamente exposto.
    "node_labels_half_configured",
    # Task 5: os tres de SF-EMR-009, a regra que fechou a divida de
    # `measures.idle_timeout_seconds` -- measure que o extrator emitia e nenhuma
    # regra consumia. O primeiro e o teto da API (604800 s) com JupyterHub,
    # Zeppelin e Hue instalados, e prova as duas coisas de uma vez: o ramo P1 de
    # `severity_by`, e que a aplicacao interativa NAO cala a regra. Os outros dois
    # sao o par do limiar, identicos entre si exceto pelo numero: 86400 dispara,
    # 82800 nao.
    "auto_termination_idle_week",
    "auto_termination_idle_day",
    "auto_termination_near_threshold",
    # O par de `instance_fleets_maximize` no ramo de `severity_by` de
    # SF-EMR-006: mesmo `log_uri_present: false`, e a unica diferenca e
    # `auto_terminate`. Sem ele o `severity_default` P2 da regra nunca foi
    # comparado contra golden nenhum -- podia virar qualquer valor com a suite
    # inteira verde.
    "log_uri_absent_long_lived",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_emr_cluster_path(dump, repo_root=input_dir))
    return facts


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


# Chave de propriedade ou prefixo de argumento que carrega valor sensivel. Mesmo
# vocabulario que o extrator usa para marcar `secret_pattern_match`; aqui ele
# serve para EXTRAIR do input o que nao pode aparecer no golden.
_MARCADORES_DE_SEGREDO = ("secret", "password", "passwd", "token", "credential", "apikey")


def _secret_values(node) -> set[str]:
    """Valores sensiveis do dump de entrada, achados por varredura recursiva.

    Derivado, nunca escrito a mao: o teste que os consome nao pode repetir a
    credencial, senao ele proprio vira mais um lugar onde ela mora -- e trocar
    o segredo da fixture faria a assercao parar de testar sem ninguem notar.
    """
    achados: set[str] = set()

    def sensivel(chave: str) -> bool:
        baixo = str(chave).lower()
        return any(marca in baixo for marca in _MARCADORES_DE_SEGREDO)

    def caminhar(valor) -> None:
        if isinstance(valor, dict):
            for chave, filho in valor.items():
                if sensivel(chave) and isinstance(filho, str) and filho:
                    achados.add(filho)
                caminhar(filho)
        elif isinstance(valor, list):
            for item in valor:
                caminhar(item)
        elif isinstance(valor, str) and "=" in valor:
            # `--password=xxx` num `Args` de bootstrap: a chave e o proprio token.
            nome, _, resto = valor.partition("=")
            if sensivel(nome) and resto:
                achados.add(resto)

    caminhar(node)
    return achados


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio de fixtures
# vazio, o pytest 8.x invoca o callable sobre o sentinela interno NOTSET durante
# a coleta e aborta a sessao INTEIRA, nao so este arquivo. Mesma guarda de
# `test_agent_coverage.py`.
@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
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

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second

    def test_no_two_facts_share_an_id(self, directory):
        """Dois facts com o mesmo id sao dois conteudos diferentes com uma
        rastreabilidade so: o `evidence` de um Finding apontaria para o par, e
        nao para o fact que o justifica. O risco e real aqui porque um dump tem
        muitas propriedades de configuracao sob o mesmo cluster, e `Fact.id` e
        o hash de (kind, subject, measures) -- sem symbol distinto por
        propriedade, todas colidiriam.

        `emr.unresolved` fica de fora, e nao por conveniencia: ele e ancorado
        no ARQUIVO e o que o distingue (`reason`) vive em `attrs`, que por
        contrato de `Fact.id` nao entra no hash. Isso vale para todo extrator
        do pacote (`athena.unresolved`, `tf.unresolved`), e divergir aqui
        seria inventar uma identidade que o resto do projeto nao tem.
        """
        _, facts, _, _ = run_fixture(directory)
        ids = [f.id for f in facts if f.kind != "emr.unresolved"]
        assert len(ids) == len(set(ids))


class TestAdversarial:
    def test_spot_question_has_one_shape_in_both_instance_models(self):
        """O nucleo da decisao de kind unico: `Market == "SPOT"` num grupo e
        `TargetSpotCapacity > 0` num fleet chegam ao MESMO atributo. Se
        virassem kinds distintos, toda regra que pergunta por Spot precisaria
        ser escrita duas vezes -- e a metade esquecida ficaria calada em metade
        dos clusters."""
        _, groups, _, _ = run_fixture(FIXTURES / "instance_groups_spot_task")
        _, fleets, _, _ = run_fixture(FIXTURES / "instance_fleets_maximize")

        def spot_roles(facts):
            return {
                f.attrs["role"]
                for f in _by_kind(facts, "emr.instance_capacity")
                if f.attrs["has_spot_capacity"]
            }

        assert spot_roles(groups) == {"TASK"}
        assert spot_roles(fleets) == {"MASTER"}
        assert {f.attrs["collection_type"] for f in _by_kind(groups, "emr.instance_capacity")} == {
            "INSTANCE_GROUP"
        }
        assert {f.attrs["collection_type"] for f in _by_kind(fleets, "emr.instance_capacity")} == {
            "INSTANCE_FLEET"
        }

    def test_group_level_property_records_that_it_overrides_the_cluster(self):
        """Achatar os dois niveis num kind sem discriminante faria uma regra
        afirmar sobre o cluster inteiro o que so vale onde ninguem redefiniu.
        `spark.dynamicAllocation.enabled` esta `false` no cluster e `true` no
        grupo TASK: os dois facts existem, cada um com o seu nivel, e a
        sobreposicao aparece nos dois sentidos."""
        _, facts, _, _ = run_fixture(FIXTURES / "instance_groups_spot_task")
        configs = _by_kind(facts, "emr.configuration")
        cluster_level = next(
            f
            for f in configs
            if f.attrs["level"] == "cluster"
            and f.attrs["key"] == "spark.dynamicAllocation.enabled"
        )
        group_level = next(
            f
            for f in configs
            if f.attrs["level"] == "instance_group"
            and f.attrs["key"] == "spark.dynamicAllocation.enabled"
        )
        assert cluster_level.attrs["value"] == "false"
        assert cluster_level.attrs["overridden_in"] == ["ig-TASK"]
        assert cluster_level.measures["overriding_group_count"] == 1
        assert group_level.attrs["value"] == "true"
        assert group_level.attrs["overrides_cluster"] is True
        assert group_level.attrs["cluster_value"] == "false"

    def test_requested_configuration_that_never_applied_becomes_a_guard(self):
        """O fact mais importante do extrator: sem ele, uma regra afirma sobre
        configuracao que NAO esta em vigor. Ele e por grupo, nao por cluster --
        o grupo TASK do mesmo dump tem pedido e aplicado identicos e nao produz
        guard nenhum."""
        _, facts, _, _ = run_fixture(FIXTURES / "configuration_not_applied")
        guards = _by_kind(facts, "emr.configuration.unapplied")
        assert [g.attrs["scope"] for g in guards] == ["ig-CORE"]
        assert guards[0].attrs["pending"] == ["spark-defaults/spark.dynamicAllocation.enabled"]
        assert guards[0].measures["configurations_version"] == 7

    def test_a_clean_dump_produces_no_guard(self):
        """O sentido negativo: `LastSuccessfullyAppliedConfigurations` igual a
        `Configurations` nao pode virar guard. Um guard que dispara sempre e
        um guard que ninguem le, e ele apagaria toda regra de configuracao."""
        _, facts, _, _ = run_fixture(FIXTURES / "instance_groups_spot_task")
        assert _by_kind(facts, "emr.configuration.unapplied") == []

    def test_no_secret_value_survives_into_a_committed_golden(self):
        """Um golden commitado com credencial real seria o analisador causando
        o dano que a regra de segredo existe para prevenir. Vale para os dois
        lugares onde as APIs Describe/List devolvem texto claro: propriedade de
        configuracao e argumento de bootstrap action.

        Os valores sao DERIVADOS do input, nunca repetidos aqui. Repeti-los
        criaria duas verdades: trocar o segredo da fixture faria a assercao
        parar de testar em silencio, e um segredo NOVO acrescentado ao input
        nao seria coberto por ninguem. Derivando, a cobertura acompanha a
        fixture -- e o teste deixa de ser mais um lugar onde credencial mora.
        """
        directory = FIXTURES / "instance_groups_spot_task"
        entrada = json.loads(
            (directory / "input" / "cluster.json").read_text(encoding="utf-8")
        )
        segredos = _secret_values(entrada)
        assert segredos, (
            "a fixture do teste de segredo nao tem nenhum valor sensivel; ela existe "
            "para provar redacao, entao sem valor ela passa sem verificar nada"
        )

        raw = (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        vazados = sorted(v for v in segredos if v in raw)
        assert not vazados, (
            f"{len(vazados)} valor(es) sensivel(is) do input sobreviveram ao golden "
            f"commitado. O extrator tem que redigir antes de o fact existir."
        )

        _, facts, _, _ = run_fixture(directory)
        flagged = [f for f in facts if f.attrs.get("secret_pattern_match")]
        assert {f.kind for f in flagged} == {"emr.configuration", "emr.bootstrap_action"}
        for fact in flagged:
            assert fact.attrs.get("redacted") is True

    def test_missing_instance_dump_is_incomplete_not_a_cluster_without_capacity(self):
        """Lista ausente vira `unresolved`, nunca lista vazia: uma regra que
        perguntasse "ha Spot?" sobre zero facts concluiria "nao ha", que e o
        falso negativo silencioso que o catalogo trata como pior defeito."""
        _, facts, _, _ = run_fixture(FIXTURES / "missing_instance_model")
        assert _by_kind(facts, "emr.instance_capacity") == []
        assert [f.attrs["reason"] for f in _by_kind(facts, "emr.unresolved")] == [
            "missing_instance_model"
        ]

    def test_every_way_the_dump_can_fail_has_its_own_reason(self):
        _, facts, _, _ = run_fixture(FIXTURES / "malformed_sections")
        reasons = {f.attrs["reason"] for f in _by_kind(facts, "emr.unresolved")}
        assert reasons == {
            "malformed_json",
            "conflicting_instance_models",
            "missing_market",
            "missing_instance_role",
            "missing_fleet_capacity",
            "missing_classification",
            "missing_bootstrap_name",
        }
        assert _by_kind(facts, "emr.instance_capacity") == []
        assert _by_kind(facts, "emr.managed_scaling") == []

    def test_sentinel_exists_in_every_fixture_and_counts_what_it_says(self):
        """`emr.analyzed` e o que distingue "analisei e nao ha" de "nunca
        analisei". Sem ela, `absent:` sobre fact de EMR e vacuamente verdadeiro
        num repositorio onde o extrator nunca rodou."""
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            sentinel = next(f for f in facts if f.kind == "emr.analyzed")
            counted = len(_by_kind(facts, "emr.unresolved"))
            assert sentinel.measures["unresolved_count"] == counted, directory.name
            assert sentinel.measures["configuration_count"] == len(
                _by_kind(facts, "emr.configuration")
            ), directory.name

    def test_the_evidence_guard_is_what_stops_the_rule_not_a_missing_ingredient(self):
        """`- absent: emr.configuration.unapplied` em SF-EMR-003 tem que ser a
        linha que decide, e nao decoracao ao lado de uma condicao que ja daria
        falso sozinha.

        `reconfiguration_pending_with_managed_scaling` tem os TRES ingredientes
        da regra -- `spark.dynamicAllocation.enabled=false` no nivel cluster,
        `overriding_group_count == 0`, e politica de managed scaling --, e
        mesmo assim nao dispara. Este teste remove o guarda de uma copia do
        catalogo e mostra que sem ele a regra dispararia: e a prova de que o
        cluster esta rodando com alocacao dinamica LIGADA no grupo TASK (o
        `dropped` do guarda) enquanto o dump aparenta o contrario.

        Sem esta prova, alguem poderia apagar a linha do `when` e a suite
        inteira continuaria verde.
        """
        import copy

        directory = FIXTURES / "reconfiguration_pending_with_managed_scaling"
        meta, facts, findings, _ = run_fixture(directory)
        assert [f.rule_id for f in findings] == []

        sem_guarda = copy.deepcopy(load_catalog())
        for rule in sem_guarda:
            if rule["id"] == "SF-EMR-003":
                rule["when"]["all"] = [
                    c for c in rule["when"]["all"] if "absent" not in c
                ]
        degradado = judge(facts, sem_guarda, meta["runtime"])
        assert [f.rule_id for f in degradado] == ["SF-EMR-003"]

    def test_the_official_recommendation_is_never_accused(self):
        """Primary em Spot e RECOMENDADO pela AWS em dois dos quatro cenarios da
        tabela oficial, e nos dois o core tambem e Spot. Uma versao ingenua de
        SF-EMR-004 -- "MASTER com Spot" -- acusaria exatamente a recomendacao.

        `all_spot_groups_maximize` e essa recomendacao escrita como dump, e ela
        nao pode produzir achado nenhum. O lado positivo e
        `instance_fleets_maximize`, onde o core e On-Demand e a contradicao
        existe.
        """
        _, limpo, findings_limpo, _ = run_fixture(FIXTURES / "all_spot_groups_maximize")
        papeis_spot = {
            f.attrs["role"]
            for f in _by_kind(limpo, "emr.instance_capacity")
            if f.attrs["has_spot_capacity"]
        }
        assert papeis_spot == {"MASTER", "CORE", "TASK"}
        assert [f.rule_id for f in findings_limpo] == []

        _, _, findings_contraditorio, _ = run_fixture(FIXTURES / "instance_fleets_maximize")
        assert "SF-EMR-004" in {f.rule_id for f in findings_contraditorio}

    def test_maximize_resource_allocation_is_only_a_defect_on_fleets(self):
        """A mesma propriedade, com o mesmo valor, nos dois modelos de instancia:
        defeito num, correto no outro. Se o `when` perder a condicao sobre
        `instance_collection_type`, esta assercao quebra em vez de a regra
        passar a acusar todo cluster que usa o calculo automatico."""
        for name in ("instance_fleets_maximize", "all_spot_groups_maximize"):
            directory = FIXTURES / name
            _, facts, _, _ = run_fixture(directory)
            assert any(
                f.attrs["key"] == "maximizeResourceAllocation" and f.attrs["value"] == "true"
                for f in _by_kind(facts, "emr.configuration")
            ), directory.name

        _, _, fleets, _ = run_fixture(FIXTURES / "instance_fleets_maximize")
        _, _, groups, _ = run_fixture(FIXTURES / "all_spot_groups_maximize")
        assert "SF-EMR-001" in {f.rule_id for f in fleets}
        assert "SF-EMR-001" not in {f.rule_id for f in groups}

    def test_the_derived_fact_is_what_stops_the_am_rule_not_a_missing_ingredient(self):
        """SF-EMR-008 e a unica regra da area cujo guarda e um fact DERIVADO, e
        este teste prova que ele decide.

        `all_spot_groups_maximize` casa as duas primeiras condicoes da regra --
        release 6.15.0 e Spot no grupo TASK -- e nao dispara. O unico motivo e
        `absent: emr.yarn.am_node_label` falhando, porque o `yarn-site` daquele
        cluster tem as DUAS propriedades no nivel cluster. Removido o `absent:`
        de uma copia do catalogo, a regra dispara: sem o fact derivado ela
        acusaria um cluster que fixou o AM corretamente, que e o falso positivo
        que a Task 4 recusou produzir.

        Sem esta prova, alguem poderia apagar a linha do `when` -- ou fazer o
        extrator parar de emitir o fact -- e a unica coisa a quebrar seria um
        golden, sem nenhum teste dizendo o que se perdeu.
        """
        import copy

        directory = FIXTURES / "all_spot_groups_maximize"
        meta, facts, findings, _ = run_fixture(directory)
        assert [f.rule_id for f in findings] == []

        cluster = next(f for f in facts if f.kind == "emr.cluster")
        assert cluster.measures["release_major"] == 6
        assert any(
            f.attrs["role"] == "TASK" and f.attrs["has_spot_capacity"]
            for f in _by_kind(facts, "emr.instance_capacity")
        )
        label = next(f for f in facts if f.kind == "emr.yarn.am_node_label")
        assert label.attrs["decision"] == "pinned"
        assert label.attrs["expression"] == "CORE"

        sem_guarda = copy.deepcopy(load_catalog())
        for rule in sem_guarda:
            if rule["id"] == "SF-EMR-008":
                rule["when"]["all"] = [c for c in rule["when"]["all"] if "absent" not in c]
        degradado = judge(facts, sem_guarda, meta["runtime"])
        assert [f.rule_id for f in degradado] == ["SF-EMR-008"]

    def test_half_configured_node_labels_are_not_protection(self):
        """O caso que separa "alguem escreveu algo em yarn-site" de "o AM esta
        protegido". `node_labels_half_configured` tem
        `yarn.node-labels.enabled=true` e nao tem a expressao de AM: o AM cai na
        particao DEFAULT, e o EMR nao rotula nos de task, entao a particao
        DEFAULT e onde o Spot esta. Um extrator que emitisse o fact ao ver
        qualquer propriedade de node label calaria a regra aqui -- e o silencio
        leria como "revisei e esta protegido"."""
        _, exposto, findings_exposto, _ = run_fixture(FIXTURES / "node_labels_half_configured")
        assert _by_kind(exposto, "emr.yarn.am_node_label") == []
        assert [f.rule_id for f in findings_exposto] == ["SF-EMR-008"]

        chaves = {
            f.attrs["key"]
            for f in _by_kind(exposto, "emr.configuration")
            if f.attrs["classification"] == "yarn-site"
        }
        assert chaves == {"yarn.node-labels.enabled"}

        _, protegido, findings_protegido, _ = run_fixture(FIXTURES / "all_spot_groups_maximize")
        protegidas = {
            f.attrs["key"]
            for f in _by_kind(protegido, "emr.configuration")
            if f.attrs["classification"] == "yarn-site"
        }
        # A unica diferenca entre os dois dumps, no que esta regra le, e a
        # segunda propriedade -- e ela e a que decide.
        assert protegidas - chaves == {"yarn.node-labels.am.default-node-label-expression"}
        assert "SF-EMR-008" not in {f.rule_id for f in findings_protegido}

    def test_the_idle_timeout_threshold_is_read_and_compared(self):
        """O par near-threshold de SF-EMR-009.

        `auto_termination_idle_day` e `auto_termination_near_threshold` sao o
        MESMO dump com uma unica diferenca -- 86400 contra 82800 segundos --, e
        so um dos dois e acusado. Sem o par, a regra poderia estar disparando
        pela mera PRESENCA de `measures.idle_timeout_seconds` e os dois goldens
        continuariam verdes; o negativo e o unico lugar onde a comparacao com o
        limiar precisa acontecer de verdade.

        A assercao sobre o limiar vem do catalogo, nunca de um numero repetido
        aqui: um limiar escrito em dois lugares vira dois limiares no dia em que
        alguem ajustar so um.
        """
        regra = next(r for r in load_catalog() if r["id"] == "SF-EMR-009")
        limiar = regra["threshold"]["idle_timeout_seconds"]

        _, dispara, findings_dispara, _ = run_fixture(FIXTURES / "auto_termination_idle_day")
        _, cala, findings_cala, _ = run_fixture(FIXTURES / "auto_termination_near_threshold")

        acima = next(f for f in dispara if f.kind == "emr.cluster")
        abaixo = next(f for f in cala if f.kind == "emr.cluster")
        assert acima.measures["idle_timeout_seconds"] == limiar
        assert abaixo.measures["idle_timeout_seconds"] < limiar

        assert [f.rule_id for f in findings_dispara] == ["SF-EMR-009"]
        assert [f.rule_id for f in findings_cala] == []

        # A measure existe nos DOIS. O que separa os dois e a comparacao, e nao
        # a presenca do dado -- que era a unica coisa que o corpus provava antes.
        assert "idle_timeout_seconds" in abaixo.measures

    def test_an_absent_policy_never_accuses(self):
        """A terceira direcao de SF-EMR-009, e a que o motor decide sozinho.

        Dump sem `AutoTerminationPolicy` nao tem a measure; o avaliador levanta
        "caminho ausente no contexto", `_expr_matches` engole o `ExprError` e
        devolve falso. E por isso que a AUSENCIA de politica nao pode ser o
        gatilho desta regra (item 6 do cabecalho de `emr-infra.yaml`): ausencia
        de measure falha FECHADA nas duas superficies do `when`.

        `instance_groups_spot_task` cobre o caso vizinho -- politica presente com
        o default da AWS, 3600 s --, e tambem nao dispara.
        """
        sem_measure = []
        for directory in fixture_dirs():
            _, facts, findings, _ = run_fixture(directory)
            clusters = _by_kind(facts, "emr.cluster")
            if clusters and "idle_timeout_seconds" not in clusters[0].measures:
                sem_measure.append(directory.name)
                assert "SF-EMR-009" not in {f.rule_id for f in findings}, directory.name

        assert len(sem_measure) >= 5, (
            "quase todo o corpus deveria estar sem politica de auto-terminacao; "
            f"so {len(sem_measure)} estao, e a assercao virou quase vazia"
        )

        _, com_default, findings_default, _ = run_fixture(FIXTURES / "instance_groups_spot_task")
        cluster = next(f for f in com_default if f.kind == "emr.cluster")
        assert cluster.measures["idle_timeout_seconds"] == 3600
        assert "SF-EMR-009" not in {f.rule_id for f in findings_default}

    def test_an_interactive_cluster_is_accused_not_silenced(self):
        """A decisao de escopo de SF-EMR-009, travada.

        A pesquisa propos calar a regra em cluster com JupyterHub, Zeppelin ou
        Hue, porque auto-terminacao derruba sessao de usuario.
        `auto_termination_idle_week` tem as tres aplicacoes E a janela no teto da
        API, e e acusado assim mesmo -- a justificativa esta no primeiro item de
        `tradeoffs` da regra, e o ponto operacional e que ela chega ao operador
        DENTRO do achado, em vez de virar um `skipped` que ninguem le.

        Se alguem acrescentar o gate depois, este teste quebra e obriga a decisao
        a ser tomada de novo, com a fonte na mao.
        """
        _, facts, findings, skipped = run_fixture(FIXTURES / "auto_termination_idle_week")

        aplicacoes = {f.attrs["name"] for f in _by_kind(facts, "emr.application")}
        assert {"JupyterHub", "Zeppelin", "Hue"} <= aplicacoes

        achado = next(f for f in findings if f.rule_id == "SF-EMR-009")
        # O ramo de `severity_by`: 604800 s e o maximo que a API aceita.
        assert achado.severity == "P1"
        assert achado.measured["idle_timeout_seconds"] == 604800
        assert "SF-EMR-009" not in {s["rule_id"] for s in skipped}
        assert any("JupyterHub" in t for t in achado.tradeoffs)

    def test_both_severity_branches_of_the_log_uri_rule_have_a_fixture(self):
        """Os dois ramos de SF-EMR-006, e o que os separa.

        `instance_fleets_maximize` e `log_uri_absent_long_lived` tem os dois
        `log_uri_present: false` -- o `when` da regra casa nos dois. O unico
        campo que decide a severidade e `attrs.auto_terminate`: True vira P1
        pelo ramo de `severity_by`, False cai no `severity_default` P2.

        Antes do segundo fixture o ramo default nao aparecia em golden nenhum,
        e severidade sem golden pode virar qualquer valor com a suite inteira
        verde -- nada no repositorio compara severidade de regra contra fixture
        fora do golden de `findings`. As severidades vem do CATALOGO, nunca de
        literais repetidos aqui: escritas em dois lugares, viram duas verdades
        no dia em que alguem ajustar so uma.
        """
        regra = next(r for r in load_catalog() if r["id"] == "SF-EMR-006")
        ramo = next(b for b in regra["severity_by"] if "auto_terminate" in b["when"])

        _, efemero, findings_efemero, _ = run_fixture(FIXTURES / "instance_fleets_maximize")
        _, duradouro, findings_duradouro, _ = run_fixture(
            FIXTURES / "log_uri_absent_long_lived"
        )

        cluster_efemero = next(f for f in efemero if f.kind == "emr.cluster")
        cluster_duradouro = next(f for f in duradouro if f.kind == "emr.cluster")
        assert cluster_efemero.attrs["log_uri_present"] is False
        assert cluster_duradouro.attrs["log_uri_present"] is False
        assert cluster_efemero.attrs["auto_terminate"] is True
        assert cluster_duradouro.attrs["auto_terminate"] is False

        achado_efemero = next(f for f in findings_efemero if f.rule_id == "SF-EMR-006")
        achado_duradouro = next(f for f in findings_duradouro if f.rule_id == "SF-EMR-006")
        assert achado_efemero.severity == ramo["severity"]
        assert achado_duradouro.severity == regra["severity_default"]
        assert achado_efemero.severity != achado_duradouro.severity

    def test_empty_dump_still_proves_the_extractor_ran(self):
        _, facts, _, _ = run_fixture(FIXTURES / "empty_dump")
        assert {f.kind for f in facts} == {"emr.analyzed", "emr.unresolved"}
        assert facts[0].measures["cluster_count"] == 0
