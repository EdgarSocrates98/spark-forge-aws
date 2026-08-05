"""Golden test do corpus de application EMR Serverless.

Arquivo dedicado, mesma razao de `test_fixtures_golden_emr.py`: a fixture e um
dump `*.json` sob `input/`, saida de `aws emr-serverless get-application`. UMA
chamada devolve capacidade inicial, maxima, auto-start/stop,
`runtimeConfiguration` e `monitoringConfiguration` no mesmo objeto -- por isso
nao ha o `_tree` de conveniencia sobre seis subcomandos que o EMR on EC2 exige.

A extracao usa `extract_emr_serverless_tree`, e nao um laco sobre `*.json`, pela
razao escrita em `scripts/regen_fixtures.py:regen_emr_serverless`: e a funcao que
`adapters/_core.py` chama quando o `--path` e diretorio, e tres fixtures deste
corpus tem mais de um payload. Golden e teste precisam extrair pela MESMA porta
por onde o produto extrai.

**Todo `expects_rules` nasceu vazio, e isso era projeto, nao lacuna.** A area
`SF-EMRS` e a Task 5 da Fase 5d; este corpus e a Task 4. Extrator e corpus antes
de regra e a ordem que o repositorio ja usou na Fase 5b para EMR on EC2 e na 4c
para `SF-FVAL`: regra sem fixture e regra que nunca foi provada, e escrever as
duas coisas juntas apaga a chance de a fixture contradizer a regra.

Com a Task 5 as regras existem, `python scripts/regen_fixtures.py` reescreveu os
`findings.json`, e `expects_rules` deixou de ser uniformemente vazio: **6 das 16
fixtures disparam regra, uma para cada uma das seis `SF-EMRS`**. Os `[]` que
sobraram sao goldens NEGATIVOS reais -- se alguma regra disparar sobre um payload
que nao a justifica, o diff aparece aqui.

`TestAdversarial` abaixo e o que sobrevive a essa transicao: ele nao pergunta
"que regra disparou", pergunta se o FACT diz o que o payload autoriza. Cinco
pares carregam a carga:

  * `preinit_sem_autostop` x `autostop_ausente_default_seguro` -- desligado de
    proposito contra bloco ausente. Confundir os dois faz o motor acusar o
    default seguro da AWS, que e a maioria das applications reais.
  * `capacidade_excede_teto` x `capacidade_indecidivel` -- decisao construida
    contra o caso comum de nao dar para decidir.
  * `segredo_em_runtime_config` x `segredo_anotado_nao_e_achado` -- o defeito
    contra a CORRECAO do defeito.
  * `sem_destino_de_log` x `s3_sem_managed_storage` x `app_saudavel` -- zero,
    um e dois destinos de log.
  * `identidade_ausente` x `secoes_malformadas` -- payload sem quem ancorar
    contra payload torto com application identificada.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.emr_serverless import EMITTED_KINDS, extract_emr_serverless_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "emr_serverless"

REQUIRED_FIXTURES = {
    # Os oito da tabela do plano da Task 4.
    "empty_payload",
    "app_saudavel",
    "preinit_sem_autostop",
    "autostop_longo",
    "capacidade_excede_teto",
    "sem_destino_de_log",
    "segredo_em_runtime_config",
    "unidade_desconhecida",
    # Os sete que a medicao das Tasks 1 a 3 acrescentou, cada um com o desvio
    # que o exige:
    #
    # D-5d-16 -- bloco de auto-stop AUSENTE e o default SEGURO da AWS, e o
    # extrator nao o materializa. Sem esta fixture, "desligado de proposito" e
    # "nunca declarado" nao tem golden que os separe.
    "autostop_ausente_default_seguro",
    # D-5d-7 -- `maximumCapacity` e `Required: No`, e disco ausente de um lado
    # ja basta para a decisao nao existir. O indecidivel e o caso COMUM.
    "capacidade_indecidivel",
    # D-5d-4, bonus -- S3 configurado com managed storage desligado: ha destino
    # de log e mesmo assim se perde a UI de aplicacao.
    "s3_sem_managed_storage",
    # D-5d-8 -- `EMR.secret@{{Nome}}` e a anotacao CORRETA. Sem golden, a regra
    # de segredo da Task 5 pode acusar a propria correcao que recomenda.
    "segredo_anotado_nao_e_achado",
    # D-5d-6 -- `emr-spark-8.0.0` e `emr-spark-8.0-preview` sao labels validos
    # que nao casam `emr-<major>.<minor>.<patch>`; a serie e omitida, nao
    # forcada.
    "release_sem_serie",
    # As duas familias de ponto cego, que nenhuma tabela previu e sem as quais
    # metade do vocabulario de `emrs.unresolved` nao aparece em golden nenhum.
    "secoes_malformadas",
    "identidade_ausente",
    # A decima sexta, acrescentada pela Task 5 e medida pela verificacao de
    # apagabilidade, nao prevista por tabela nenhuma: `initial_capacity_worker_type_count
    # >= 1` e termo de SF-EMRS-001 e de SF-EMRS-005, e sem uma application SEM
    # pre-init os dois termos podiam ser apagados do catalogo sem nenhum golden
    # reclamar. Dois payloads, um por regra, porque as duas condicoes de
    # auto-stop sao mutuamente exclusivas.
    "sem_preinit_nada_a_cobrar",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    return extract_emr_serverless_tree(input_dir, repo_root=input_dir)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _one(facts, kind):
    encontrados = _by_kind(facts, kind)
    assert len(encontrados) == 1, f"esperava um {kind}, achei {len(encontrados)}"
    return encontrados[0]


def _reasons(facts):
    return sorted(f.attrs["reason"] for f in _by_kind(facts, "emrs.unresolved"))


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio de fixtures
# vazio, o pytest 8.x invoca o callable sobre o sentinela interno NOTSET durante
# a coleta e aborta a sessao INTEIRA, nao so este arquivo. Mesma guarda de
# `test_fixtures_golden_emr.py`.
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
        """Dois facts com o mesmo id sao dois conteudos com uma rastreabilidade
        so: o `evidence` de um Finding apontaria para o par, nao para o fact que
        o justifica. O risco e concreto aqui porque `runtimeConfiguration` pode
        trazer a mesma classificacao duas vezes -- e por isso `_SymbolPool`
        sufixa `#N`.

        `emrs.unresolved` fica de fora pelo mesmo contrato que vale para
        `emr.unresolved` e `athena.unresolved`: ele e ancorado no ARQUIVO, e o
        que o distingue (`reason`) vive em `attrs`, que nao entra no hash de
        `Fact.id`.
        """
        _, facts, _, _ = run_fixture(directory)
        ids = [f.id for f in facts if f.kind != "emrs.unresolved"]
        assert len(ids) == len(set(ids))

    def test_sentinel_counts_what_it_says(self, directory):
        """`emrs.analyzed` e o que distingue "analisei e nao ha" de "nunca
        analisei". Um contador que para de contar devolve zero, e zero e
        exatamente o que uma extracao limpa devolve -- o apodrecimento seria
        invisivel."""
        _, facts, _, _ = run_fixture(directory)
        sentinelas = _by_kind(facts, "emrs.analyzed")
        arquivos = len(list((directory / "input").glob("*.json")))
        assert len(sentinelas) == arquivos, "uma sentinela por payload, sempre"
        for campo, kind in (
            ("application_count", "emrs.application"),
            ("initial_capacity_count", "emrs.initial_capacity"),
            ("configuration_count", "emrs.configuration"),
            ("unresolved_count", "emrs.unresolved"),
        ):
            assert sum(s.measures[campo] for s in sentinelas) == len(_by_kind(facts, kind)), campo

    def test_no_rule_of_this_area_is_skipped_for_runtime_scope(self, directory):
        """O corpus julga com `runtime: {}` de proposito (a razao esta em cada
        `meta.yaml`): a AWS nao publica a matriz de release do Serverless
        (D-5d-5), entao nao ha versao que este artefato sustente.

        A consequencia e um contrato para a Task 5: regra `SF-EMRS` com
        `runtime_scope` nao vazio seria PULADA aqui, e o golden ficaria verde
        sem ter avaliado nada -- verde por skip e pior que vermelho, porque
        ninguem investiga o que passou. Este teste transforma esse silencio em
        falha no minuto em que a regra entrar.
        """
        _, _, _, skipped = run_fixture(directory)
        fora_de_escopo = [
            s
            for s in skipped
            if s["reason"] == "runtime_scope" and str(s["rule_id"]).startswith("SF-EMRS")
        ]
        assert not fora_de_escopo, fora_de_escopo


class TestAdversarial:
    def test_every_emitted_kind_appears_in_this_corpus(self):
        """Recorte local do invariante global de
        `test_fixtures_kind_coverage.py`. Aqui ele falha com a mensagem certa:
        kind do EMR Serverless sem fixture do EMR Serverless."""
        vistos: set[str] = set()
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            vistos.update(f.kind for f in facts)
        assert set(EMITTED_KINDS) - vistos == set()

    def test_disabled_auto_stop_and_absent_auto_stop_are_two_different_facts(self):
        """O par que a Task 5 vai depender de encontrar separado.

        As duas applications tem capacidade pre-inicializada. Numa,
        `autoStopConfiguration.enabled` e `false` -- ato deliberado, e o estado
        que a AWS nomeia como causa de `unexpected charges`. Na outra o bloco
        simplesmente nao veio, e o default documentado (ligado, 15 minutos) e o
        estado SEGURO.

        O extrator NAO materializa esse default: `auto_stop_enabled` e chave
        OMITIDA, e `auto_stop_declared` responde sobre o payload. Uma regra
        escrita sobre ausencia acusaria a application correta.
        """
        _, desligado, _, _ = run_fixture(FIXTURES / "preinit_sem_autostop")
        _, ausente, _, _ = run_fixture(FIXTURES / "autostop_ausente_default_seguro")

        app_desligado = _one(desligado, "emrs.application")
        app_ausente = _one(ausente, "emrs.application")

        assert app_desligado.attrs["auto_stop_declared"] is True
        assert app_desligado.attrs["auto_stop_enabled"] is False

        assert app_ausente.attrs["auto_stop_declared"] is False
        assert "auto_stop_enabled" not in app_ausente.attrs
        assert "idle_timeout_minutes" not in app_ausente.measures

        # A pre-init existe nos dois: e o outro termo da conjuncao da P0, e ele
        # mora no MESMO fact (D-5d-17) para que a regra nao case a application
        # A com a capacidade da application B.
        for app in (app_desligado, app_ausente):
            assert app.measures["initial_capacity_worker_type_count"] >= 1

    def test_the_long_window_is_the_api_ceiling_and_the_short_one_is_the_default(self):
        """Os dois extremos declarados pela fonte, um em cada fixture: 10080
        minutos e o "Maximum value" da referencia (sete dias), 15 e o default.
        Qualquer limiar que a Task 5 escolha vive entre os dois, e os dois
        precisam de golden para o limiar ser apagavel."""
        _, longo, _, _ = run_fixture(FIXTURES / "autostop_longo")
        _, curto, _, _ = run_fixture(FIXTURES / "app_saudavel")
        assert _one(longo, "emrs.application").measures["idle_timeout_minutes"] == 10080
        assert _one(curto, "emrs.application").measures["idle_timeout_minutes"] == 15
        assert _one(longo, "emrs.application").attrs["auto_stop_enabled"] is True

    def test_the_capacity_verdict_is_per_axis_and_constructed_not_observed(self):
        """A fixture positiva de `initial_exceeds_maximum` e CONSTRUIDA: a fonte
        nao declara se a API aceita ou rejeita esse estado (D-5d-7).

        A soma estoura UM eixo so, de proposito. Se a comparacao fosse feita
        num agregado unico em vez de eixo a eixo, `capacity_axes_exceeded`
        traria os tres ou nenhum e esta assercao quebraria -- e o achado diria
        ao operador para mexer em cpu e disco, que cabem.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "capacidade_excede_teto")
        app = _one(facts, "emrs.application")
        assert app.attrs["initial_exceeds_maximum"] is True
        assert app.attrs["capacity_axes_exceeded"] == ["memory_gb"]
        # 1x30 + 10x30 = 330 GB contra o teto de 200; cpu e disco cabem.
        assert sum(
            f.measures["worker_count"] * f.measures["memory_gb"]
            for f in _by_kind(facts, "emrs.initial_capacity")
        ) == 330

    def test_undecidable_capacity_omits_the_verdict_instead_of_saying_it_fits(self):
        """O caso COMUM, e o falso negativo que ele evita.

        `maximumCapacity` e `Required: No`, e `disk` e opcional no worker: as
        duas causas estao neste corpus, uma por payload. Nos dois casos as duas
        chaves sao OMITIDAS -- `false` afirmaria que a capacidade cabe, que e
        exatamente a afirmacao a partir do silencio do payload que este pacote
        recusa. E o ponto cego fica CONTADO, com `detail` que diz qual dos dois
        buracos e.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "capacidade_indecidivel")
        for app in _by_kind(facts, "emrs.application"):
            assert "initial_exceeds_maximum" not in app.attrs
            assert "capacity_axes_exceeded" not in app.attrs
        detalhes = {
            f.attrs["detail"]
            for f in _by_kind(facts, "emrs.unresolved")
            if f.attrs["reason"] == "capacity_comparison_undecidable"
        }
        assert detalhes == {"missing_maximum_capacity", "missing_capacity_axis"}

    def test_an_unreadable_unit_is_not_counted_as_a_blind_spot_twice(self):
        """`unidade_desconhecida` tem `maximumCapacity` completo: a comparacao
        PODERIA ser tentada e falharia por falta de eixo legivel. Contar de novo
        inflaria o ponto cego do mesmo defeito, e a sentinela deixaria de medir
        o que diz medir.

        Prova junto que unidade fora do conjunto nunca vira numero: `16384MB`
        lido como GB inflaria a memoria mil vezes.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "unidade_desconhecida")
        assert _reasons(facts) == ["unknown_capacity_unit", "unknown_capacity_unit"]
        capacidades = _by_kind(facts, "emrs.initial_capacity")
        por_tipo = {f.attrs["worker_type"]: f.measures for f in capacidades}
        assert "memory_gb" not in por_tipo["DRIVER"]
        assert "cpu" not in por_tipo["EXECUTOR"]
        # O que DEU para ler continua lido: o ponto cego e por eixo, nao por
        # worker.
        assert por_tipo["DRIVER"]["cpu"] == 4
        assert por_tipo["EXECUTOR"]["memory_gb"] == 16

    def test_no_secret_value_survives_into_a_committed_golden(self):
        """Um golden commitado com credencial seria o analisador causando o dano
        que a regra previne. Os valores sao DERIVADOS do input, nunca repetidos
        aqui: repeti-los faria trocar o segredo da fixture parar a assercao em
        silencio, e um segredo novo no input nao seria coberto por ninguem.
        """
        directory = FIXTURES / "segredo_em_runtime_config"
        entrada = (directory / "input" / "application.json").read_text(encoding="utf-8")
        sensiveis = sorted(
            valor
            for valor in _valores_de_chaves_sensiveis(json.loads(entrada))
            if not valor.startswith("EMR.secret@")
        )
        assert sensiveis, (
            "a fixture do teste de redacao nao tem valor sensivel nenhum; sem ele "
            "ela passa sem verificar nada"
        )

        golden = (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        vazados = [v for v in sensiveis if v in golden]
        assert not vazados, (
            f"{len(vazados)} valor(es) sensivel(is) sobreviveram ao golden commitado. "
            "A redacao tem que acontecer antes de o fact existir."
        )

        _, facts, _, _ = run_fixture(directory)
        marcados = [f for f in facts if f.attrs.get("secret_pattern_match")]
        assert {f.kind for f in marcados} == {"emrs.configuration"}
        assert len(marcados) == len(sensiveis)
        for fact in marcados:
            assert fact.attrs["redacted"] is True
            assert fact.attrs["value"] == "<redigido>"

    def test_the_secret_annotation_is_the_fix_and_is_never_accused(self):
        """`EMR.secret@{{Nome}}` e um ID de segredo, nao um segredo. Acusa-lo
        seria acusar exatamente a correcao que o achado de
        `segredo_em_runtime_config` recomenda.

        A segunda propriedade da fixture testa a PRECEDENCIA, que nao e
        cosmetica: o nome do segredo casa `_AKIA_RE`, e como o padrao usa
        `search` e nao `fullmatch`, a heuristica acusaria o valor anotado se
        rodasse primeiro.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "segredo_anotado_nao_e_achado")
        configs = _by_kind(facts, "emrs.configuration")
        assert configs, "a fixture perdeu as propriedades anotadas"
        for config in configs:
            assert config.attrs["secret_reference"] is True
            assert "secret_pattern_match" not in config.attrs
            assert "redacted" not in config.attrs
            assert config.attrs["value"].startswith("EMR.secret@")

    def test_the_three_points_of_the_log_destination_scale_are_in_the_corpus(self):
        """Zero, um e dois destinos, cada um numa fixture, porque a regra da
        Task 5 e uma CONJUNCAO e cada termo precisa poder ser apagado.

        `sem_destino_de_log` e o unico estado que a fonte autoriza acusar, e ele
        exige `managedPersistenceMonitoringConfiguration.enabled: false`
        ESCRITO -- ausencia significa managed storage ligada (D-5d-4).
        `s3_sem_managed_storage` tem managed desligado tambem, e mesmo assim
        grava log: um `where` sobre `managed_persistence_enabled == false`
        sozinho o acusaria.
        """
        esperado = {
            "sem_destino_de_log": 0,
            "s3_sem_managed_storage": 1,
            "app_saudavel": 2,
        }
        medido = {}
        for nome in esperado:
            _, facts, _, _ = run_fixture(FIXTURES / nome)
            medido[nome] = _one(facts, "emrs.monitoring").measures["log_destination_count"]
        assert medido == esperado

        _, zerado, _, _ = run_fixture(FIXTURES / "sem_destino_de_log")
        monitoring = _one(zerado, "emrs.monitoring")
        assert monitoring.attrs["managed_persistence_enabled"] is False
        assert monitoring.attrs["s3_log_uri_present"] is False
        assert monitoring.attrs["cloudwatch_enabled"] is False
        # Os tres LIDOS, nenhum presumido -- e o que separa este estado do
        # default seguro.
        assert monitoring.attrs["monitoring_declared"] is True
        assert monitoring.attrs["managed_persistence_declared"] is True
        assert monitoring.attrs["cloudwatch_declared"] is True

    def test_a_release_label_outside_the_numeric_shape_never_invents_a_series(self):
        """`emr-spark-8.0.0` e `emr-spark-8.0-preview` sao labels validos do
        Serverless. Um regex frouxo extrairia `8` do segundo e a application
        passaria a ser julgada como serie 8 sem que ninguem tenha afirmado
        isso. O label cru continua saindo; so a derivacao falta."""
        _, facts, _, _ = run_fixture(FIXTURES / "release_sem_serie")
        apps = _by_kind(facts, "emrs.application")
        assert sorted(f.attrs["release_label"] for f in apps) == [
            "emr-spark-8.0-preview",
            "emr-spark-8.0.0",
        ]
        for app in apps:
            assert "release_major" not in app.measures
            assert "release_minor" not in app.measures

        # O contraste: a forma reconhecida DA a serie.
        _, saudavel, _, _ = run_fixture(FIXTURES / "app_saudavel")
        assert _one(saudavel, "emrs.application").measures["release_major"] == 7

    def test_every_way_the_payload_can_be_crooked_has_its_own_reason(self):
        """Vocabulario fechado de ponto cego, medido e nao afirmado. Um payload
        torto nunca derruba a extracao nem vira silencio."""
        _, facts, _, _ = run_fixture(FIXTURES / "secoes_malformadas")
        assert set(_reasons(facts)) == {
            "malformed_json",
            "missing_worker_count",
            "missing_classification",
            "missing_property_key",
        }
        secoes = {
            f.attrs["section"]
            for f in _by_kind(facts, "emrs.unresolved")
            if "section" in f.attrs
        }
        assert secoes == {
            "initialCapacity[]",
            "maximumCapacity",
            "runtimeConfiguration",
            "runtimeConfiguration[]",
            "spark-defaults.properties",
            "monitoringConfiguration",
        }
        # A application foi identificada, entao o monitoramento continua
        # respondivel -- com os defaults documentados.
        assert _by_kind(facts, "emrs.monitoring")

    def test_a_payload_without_identity_anchors_nothing_but_still_reports(self):
        """As tres formas de nao haver identidade, cada uma com a sua razao. Nos
        tres a extracao aborta cedo, e nos tres a sentinela sai -- abortar cedo
        nao pode virar "nenhum fact", porque nenhum fact e indistinguivel de "o
        extrator nunca rodou".

        E o que NAO sai importa tanto quanto: emitir `emrs.monitoring` com os
        defaults da AWS aqui seria afirmar sobre uma application que nao se
        conseguiu identificar.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "identidade_ausente")
        assert _reasons(facts) == [
            "malformed_json",
            "malformed_json",
            "missing_application_id",
        ]
        assert _by_kind(facts, "emrs.application") == []
        assert _by_kind(facts, "emrs.monitoring") == []
        assert len(_by_kind(facts, "emrs.analyzed")) == 3

        _, vazio, _, _ = run_fixture(FIXTURES / "empty_payload")
        assert _reasons(vazio) == ["missing_application"]

    def test_the_healthy_application_is_never_accused(self):
        """O sentido negativo do golden vale tanto quanto o positivo. Pre-init
        COM auto-stop ligado e o arranjo que a documentacao recomenda; acusa-lo
        mandaria o operador desfazer uma configuracao correta.

        Enquanto `SF-EMRS` nao existe isto e trivialmente verdadeiro. Vale
        escrito assim mesmo: no dia em que a Task 5 entrar, este e o teste que
        falha primeiro se uma regra nascer larga demais.
        """
        _, facts, findings, _ = run_fixture(FIXTURES / "app_saudavel")
        app = _one(facts, "emrs.application")
        assert app.attrs["auto_stop_enabled"] is True
        assert app.attrs["initial_exceeds_maximum"] is False
        assert app.measures["initial_capacity_worker_type_count"] == 2
        assert _by_kind(facts, "emrs.unresolved") == []
        assert findings == []


_MARCADORES_DE_SEGREDO = ("secret", "password", "passwd", "token", "credential", "apikey", "key")

# URL com credencial embutida (`esquema://usuario:senha@host`). Um `s3://` de
# destino de log NAO casa, e nao pode casar: ele e dado legitimo do golden, e
# trata-lo como segredo faria o teste reprovar a fixture saudavel.
_URL_COM_CREDENCIAL = re.compile(r"://[^\s:@/]+:[^\s@/]+@")


def _valores_de_chaves_sensiveis(node) -> set[str]:
    """Valores sob chave que carrega marcador de segredo, por varredura
    recursiva do input. Derivado, nunca escrito a mao -- ver o teste que o
    consome."""
    achados: set[str] = set()

    def sensivel(chave: str) -> bool:
        baixo = str(chave).lower()
        return any(marca in baixo for marca in _MARCADORES_DE_SEGREDO)

    def caminhar(valor, chave_pai: str = "") -> None:
        if isinstance(valor, dict):
            for chave, filho in valor.items():
                caminhar(filho, str(chave))
        elif isinstance(valor, list):
            for item in valor:
                caminhar(item, chave_pai)
        elif isinstance(valor, str) and valor:
            if sensivel(chave_pai) or _URL_COM_CREDENCIAL.search(valor):
                achados.add(valor)

    caminhar(node)
    return achados
