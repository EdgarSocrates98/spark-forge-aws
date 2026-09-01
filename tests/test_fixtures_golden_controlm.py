"""Golden test do corpus de definicao `Jobs-as-Code` do Control-M.

Arquivo dedicado, e por uma razao que nenhum outro corpus tem: **a extracao
recebe um parametro que nao vem do artefato**. A versao do Control-M e
DECLARADA pelo operador (D-1 da spec), mora em `controlm_version` no `meta.yaml`
e entra em `extract_controlm_jobs_tree(..., declared_version=...)`. Um golden
generico que so passasse `input/` extrairia sempre sem versao e o contrafactual
inteiro -- a razao de esta area existir -- ficaria sem teste.

Este modulo NAO e opcional, e a razao esta escrita em
`test_fixtures_kind_coverage.py::test_every_fixture_domain_has_a_golden_module`:
`scripts/verify_wheel.py` monta o gate de paridade a partir dos MODULOS
(`tests/test_fixtures_*.py`), nunca dos diretorios. Um `fixtures/controlm/` sem
modulo que o carregue existiria parecendo cobertura, e o gate de wheel nunca o
executaria contra o pacote instalado.

**O CONTRAFACTUAL E O TESTE CENTRAL DESTE ARQUIVO.**
`capacidade_abaixo_da_fronteira` e `capacidade_acima_da_fronteira` tem o MESMO
`jobs.json` byte a byte, e so `controlm_version` muda. Se os dois produzissem o
mesmo veredito, nao haveria cruzamento com a matriz -- haveria numero embutido
na regra, que e exatamente o defeito que a D-3 proibiu.
`TestOContrafactual` afirma as tres pontas: os inputs sao identicos, os vereditos
sao opostos, e nenhum arquivo de `rules/catalog/controlm.yaml` carrega um numero
de versao.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.controlm_jobs import EMITTED_KINDS, extract_controlm_jobs_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "controlm"
CATALOGO = ROOT / "rules" / "catalog" / "controlm.yaml"

# Lista escrita a mao de proposito: fixture removida em silencio some do
# `parametrize` sem que nada reclame, e o corpus encolhe sem deixar rastro.
REQUIRED_FIXTURES = {
    # As DUAS metades do contrafactual. Mesmo artefato, versoes diferentes.
    "capacidade_abaixo_da_fronteira",
    "capacidade_acima_da_fronteira",
    # A D-1: sem versao declarada nao ha cruzamento, e a ausencia e NOMEADA.
    "versao_nao_declarada",
    # O negativo de referencia: o fluxo oficial da BMC, cujos job types a matriz
    # nao data. Nenhum fact de capacidade, nenhum achado.
    "fluxo_sem_capacidade_datada",
    # A segunda sonda, que nao e job type: a estrutura de array `Folders`.
    "folder_em_array",
    # A sentinela e o ponto cego contado quando o JSON nao abre.
    "artefato_ilegivel",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _extract(directory: Path):
    """Extrai pela MESMA porta do produto, com a versao do `meta.yaml`.

    `meta.get("controlm_version")` e nao `meta["controlm_version"]`: a chave e
    OPCIONAL, e a fixture `versao_nao_declarada` existe justamente para exercitar
    a ausencia dela.
    """
    input_dir = directory / "input"
    return extract_controlm_jobs_tree(
        input_dir,
        repo_root=input_dir,
        declared_version=_meta(directory).get("controlm_version"),
    )


def run_fixture(directory: Path):
    meta = _meta(directory)
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio de fixtures
# vazio, o pytest 8.x invoca o callable sobre o sentinela interno NOTSET durante
# a coleta e aborta a sessao INTEIRA, nao so este arquivo.
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

    def test_sentinel_counts_what_it_says(self, directory):
        """`ctm.analyzed` e o que distingue "li e nao ha" de "nunca li". Um
        contador que para de contar devolve zero, e zero e exatamente o que uma
        extracao limpa devolve -- o apodrecimento seria invisivel."""
        _, facts, _, _ = run_fixture(directory)
        sentinelas = _by_kind(facts, "ctm.analyzed")
        arquivos = len(list((directory / "input").glob("*.json")))
        assert len(sentinelas) == arquivos, "uma sentinela por artefato, sempre"
        for campo, kinds in (
            ("folder_count", ("ctm.folder",)),
            ("job_count", ("ctm.job",)),
            ("dependency_count", ("ctm.dependency",)),
            (
                "capability_probe_count",
                (
                    "ctm.capability_supported",
                    "ctm.capability_incompatible",
                    "ctm.capability_unresolved",
                ),
            ),
            ("capability_unresolved_count", ("ctm.capability_unresolved",)),
            ("unresolved_count", ("ctm.unresolved",)),
        ):
            esperado = sum(len(_by_kind(facts, k)) for k in kinds)
            assert sum(s.measures[campo] for s in sentinelas) == esperado, campo

    def test_the_sentinel_says_whether_a_version_was_declared(self, directory):
        """A sentinela carrega `version_declared`, e nao so as contagens.

        Sem esse booleano, um relatorio sem achado `SF-CTM` seria ambiguo entre
        "julguei e esta compativel" e "nem cheguei a perguntar". Ele e a metade
        legivel da D-1."""
        meta, facts, _, _ = run_fixture(directory)
        declarada = meta.get("controlm_version") is not None
        for sentinela in _by_kind(facts, "ctm.analyzed"):
            assert sentinela.attrs["version_declared"] is declarada


class TestOContrafactual:
    """O teste que prova que o cruzamento com a matriz EXISTE.

    Se ele nao conseguir ficar vermelho quando alguem embutir a fronteira na
    regra, este corpus inteiro nao mede nada.
    """

    ABAIXO = FIXTURES / "capacidade_abaixo_da_fronteira"
    ACIMA = FIXTURES / "capacidade_acima_da_fronteira"

    def test_os_dois_inputs_sao_o_mesmo_arquivo(self):
        """A primeira ponta. Se os `jobs.json` divergirem, o contrafactual passa
        a comparar dois artefatos e nao duas versoes -- e o veredito diferente
        deixa de provar qualquer coisa sobre a matriz."""
        a = (self.ABAIXO / "input" / "jobs.json").read_bytes()
        b = (self.ACIMA / "input" / "jobs.json").read_bytes()
        assert a == b, "as duas metades do contrafactual precisam do MESMO artefato"

    def test_so_a_versao_declarada_muda(self):
        assert _meta(self.ABAIXO)["controlm_version"] == "9.0.21.300"
        assert _meta(self.ACIMA)["controlm_version"] == "9.0.22.010"

    def test_o_veredito_e_oposto(self):
        """A segunda ponta, e a que a spec cobra: achado DIFERENTE."""
        _, abaixo_facts, abaixo_findings, _ = run_fixture(self.ABAIXO)
        _, acima_facts, acima_findings, _ = run_fixture(self.ACIMA)

        assert [f.rule_id for f in abaixo_findings] == ["SF-CTM-001"]
        assert acima_findings == []

        incompativel = _by_kind(abaixo_facts, "ctm.capability_incompatible")
        suportada = _by_kind(acima_facts, "ctm.capability_supported")
        assert len(incompativel) == 1 and len(suportada) == 1
        # A MESMA capacidade nos dois lados: o que muda e o veredito, nao o que
        # foi observado. Se a capacidade sumisse de um dos lados, o achado
        # diferente viria de o extrator ter parado de ver o job -- verde falso.
        assert incompativel[0].attrs["capability"] == suportada[0].attrs["capability"]
        assert incompativel[0].attrs["boundary_version"] == suportada[0].attrs["boundary_version"]

    def test_a_fronteira_vem_da_matriz_e_nao_da_regra(self):
        """A terceira ponta, e a unica que pega o defeito na origem.

        `rules/catalog/controlm.yaml` nao pode conter um numero de versao do
        Control-M. Se alguem embutir `9.0.22.005` no `when` de uma regra, este
        teste cai antes de o contrafactual precisar cair -- e a mensagem diz
        exatamente qual e o defeito.
        """
        import re

        texto = CATALOGO.read_text(encoding="utf-8")
        # `9.0.` seguido de digito e a grafia de versao do Control-M. As mencoes
        # em prosa (`9.0.21.200`-`9.0.22.100` no cabecalho e no `explanation`)
        # sao permitidas: o que nao pode e a fronteira estar no PREDICADO.
        documento = yaml.safe_load(texto)
        predicados = json.dumps(
            [r.get("when") for r in documento["rules"]], ensure_ascii=False
        )
        achados = re.findall(r"9\.0\.\d", predicados)
        assert not achados, (
            f"o predicado de alguma regra SF-CTM carrega versao do Control-M "
            f"({achados}). A fronteira mora em "
            f"knowledge/controlm/automation-api-matrix.yaml e o cruzamento acontece "
            f"no extrator -- repeti-la aqui faz a segunda copia do mesmo fato."
        )

    def test_a_fronteira_lida_no_fact_e_a_mesma_da_matriz(self):
        """E a matriz REALMENTE decide? O fact tem de citar o valor que o YAML
        de `knowledge/` publica, e nao um valor proprio."""
        from sparkforge.controlm import matrix as cm

        _, facts, _, _ = run_fixture(self.ABAIXO)
        fact = _by_kind(facts, "ctm.capability_incompatible")[0]
        entrada = cm.load()["capabilities"][fact.attrs["capability"]]
        assert str(entrada[fact.attrs["boundary"]]) == fact.attrs["boundary_version"]


class TestARecusaTemNome:
    """D-1 e D-4: o que nao foi cruzado sai NOMEADO, nunca aprovado por omissao."""

    def test_sem_versao_declarada_a_regra_nao_dispara_e_a_recusa_e_nomeada(self):
        directory = FIXTURES / "versao_nao_declarada"
        _, facts, findings, skipped = run_fixture(directory)

        assert findings == [], "sem versao declarada nao ha o que julgar"
        # `ctm.version_declared` NAO existe, e e por isso que a regra e pulada.
        assert _by_kind(facts, "ctm.version_declared") == []
        pulos = [s for s in skipped if s.get("rule_id") == "SF-CTM-001"]
        assert len(pulos) == 1, "a regra tem de aparecer em `skipped`, nao sumir"
        assert pulos[0]["reason"] == "requires_facts"

        # E a capacidade continua OBSERVADA: o extrator viu o job, e o que faltou
        # foi a medida. `unblocked_by` diz qual.
        recusas = _by_kind(facts, "ctm.capability_unresolved")
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == "version_not_declared"
        assert "--version" in recusas[0].attrs["unblocked_by"]
        assert "declared_version" not in recusas[0].attrs

    def test_versao_fora_da_faixa_recusa_em_vez_de_extrapolar(self):
        """A faixa e passado FECHADO. `9.0.22.125` existe na fonte e esta acima
        do teto; responder por ela usando a fronteira mais proxima seria
        extrapolar entre versoes observadas."""
        from sparkforge.controlm import descriptor as cd
        from sparkforge.facts.controlm_jobs import extract_controlm_jobs_tree as extrair

        input_dir = FIXTURES / "capacidade_abaixo_da_fronteira" / "input"
        facts = extrair(input_dir, repo_root=input_dir, declared_version="9.0.22.125")
        recusas = [f for f in facts if f.kind == "ctm.capability_unresolved"]
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == cd.VERSION_OUTSIDE_RANGE
        assert not [f for f in facts if f.kind == "ctm.capability_incompatible"]
        assert not [f for f in facts if f.kind == "ctm.capability_supported"]

    def test_versao_que_a_fonte_nao_publica_tem_recusa_propria(self):
        """A fonte anda de 5 em 5. `9.0.21.301` esta DENTRO da faixa e nao
        existe, e a recusa e outra: ela destrava com uma leitura que mostre que a
        versao existe, nao com ampliar a faixa."""
        from sparkforge.controlm import descriptor as cd
        from sparkforge.facts.controlm_jobs import extract_controlm_jobs_tree as extrair

        input_dir = FIXTURES / "capacidade_abaixo_da_fronteira" / "input"
        facts = extrair(input_dir, repo_root=input_dir, declared_version="9.0.21.301")
        recusas = [f for f in facts if f.kind == "ctm.capability_unresolved"]
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == cd.VERSION_NOT_PUBLISHED

    def test_capacidade_que_a_matriz_nao_nomeia_e_recusa_e_nunca_aprovacao(self, monkeypatch):
        """D-4 em estado puro, e o unico caminho que precisa de monkeypatch.

        Sonda que aponta para um slug ausente da matriz nao pode virar
        `supported`: a matriz calou, e calar nao e aprovar. Medido pelo
        contrafactual -- com a sonda apontando para o slug real, a mesma extracao
        produz `ctm.capability_incompatible`.
        """
        from sparkforge.facts import controlm_jobs as cj

        input_dir = FIXTURES / "capacidade_abaixo_da_fronteira" / "input"
        monkeypatch.setattr(
            cj,
            "_JOB_TYPE_CAPABILITIES",
            {"Job:DetachedEmbeddedScript": "capacidade_que_a_matriz_nao_nomeia"},
        )
        facts = cj.extract_controlm_jobs_tree(
            input_dir, repo_root=input_dir, declared_version="9.0.21.300"
        )
        recusas = [f for f in facts if f.kind == "ctm.capability_unresolved"]
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == cj.CAPABILITY_NOT_IN_MATRIX
        assert "What's New" in recusas[0].attrs["unblocked_by"]
        assert not [f for f in facts if f.kind == "ctm.capability_supported"]


class TestAdversarial:
    def test_every_emitted_kind_appears_in_this_corpus(self):
        """Recorte local do invariante global de
        `test_fixtures_kind_coverage.py`. Aqui ele falha com a mensagem certa:
        kind do Control-M sem fixture do Control-M."""
        vistos: set[str] = set()
        for directory in fixture_dirs():
            vistos.update(f.kind for f in _extract(directory))
        assert set(EMITTED_KINDS) - vistos == set(), sorted(set(EMITTED_KINDS) - vistos)

    def test_o_job_type_que_a_matriz_nao_data_nao_produz_fact_de_capacidade(self):
        """Veto V-CTM-4. A pagina *Job Types* publica 71 tipos e a matriz nomeia
        um na faixa. Sondar os outros 70 diria "esta versao nao suporta
        `Job:Command`", que e falso: eles sao anteriores a faixa."""
        _, facts, findings, _ = run_fixture(FIXTURES / "fluxo_sem_capacidade_datada")
        tipos = {f.attrs["job_type"] for f in _by_kind(facts, "ctm.job")}
        assert tipos == {"Job:Command", "Job:Script"}
        assert not [f for f in facts if f.kind.startswith("ctm.capability")]
        assert findings == []

    def test_o_json_truncado_conta_o_ponto_cego_em_vez_de_levantar(self):
        """Artefato que nao abre nao derruba a extracao nem sai calado, e a
        declaracao do operador continua valendo -- ela nao depende de o arquivo
        ter sido legivel."""
        _, facts, _, _ = run_fixture(FIXTURES / "artefato_ilegivel")
        pontos_cegos = _by_kind(facts, "ctm.unresolved")
        assert [f.attrs["reason"] for f in pontos_cegos] == ["malformed_json"]
        sentinela = _by_kind(facts, "ctm.analyzed")
        assert len(sentinela) == 1
        assert sentinela[0].measures["unresolved_count"] == 1
        assert len(_by_kind(facts, "ctm.version_declared")) == 1

    def test_a_variavel_com_forma_de_credencial_sai_redigida(self):
        """A redacao nao alimenta regra nenhuma -- o veto V-CTM-1 recusa o quarto
        exemplar do julgamento de segredo em texto claro -- e existe mesmo assim,
        porque ela impede que o proprio `facts.json` do handoff vire a segunda
        copia do segredo."""
        _, facts, _, _ = run_fixture(FIXTURES / "capacidade_abaixo_da_fronteira")
        variaveis = {f.attrs["name"]: f.attrs for f in _by_kind(facts, "ctm.variable")}
        assert variaveis["TOKEN_DO_PORTAL"]["redacted"] is True
        assert variaveis["TOKEN_DO_PORTAL"]["secret_pattern_match"] is True
        assert variaveis["TOKEN_DO_PORTAL"]["value"] == "<redigido>"
        # O negativo: variavel comum nao e redigida. Redacao que sai de graca
        # esconde o dado sem proteger nada.
        assert "redacted" not in variaveis["DataDeCorte"]
        assert variaveis["DataDeCorte"]["value"] == "%%$DATE"
        # E o literal NAO esta no golden commitado, em lugar nenhum dele.
        golden = (
            FIXTURES / "capacidade_abaixo_da_fronteira" / "expected" / "facts.json"
        ).read_text(encoding="utf-8")
        assert "ghp_" not in golden

    def test_o_objeto_if_e_reconhecido_pelo_type_e_nao_pelo_nome(self):
        """`ActionIfFailure` NAO e propriedade do schema: e o NOME que o exemplo
        oficial da BMC da ao objeto, cujo `Type` e `If`. Procurar a chave literal
        acharia o exemplo e perderia todo `If` batizado de outro jeito."""
        _, facts, _, _ = run_fixture(FIXTURES / "capacidade_abaixo_da_fronteira")
        acoes = _by_kind(facts, "ctm.action")
        assert len(acoes) == 1
        assert acoes[0].attrs["name"] == "ActionIfFailure"
        assert acoes[0].attrs["trigger"] == "completion_status"
        assert acoes[0].attrs["action_types"] == ["Action:Mail"]

    def test_as_tres_direcoes_de_dependencia_saem_separadas(self):
        """Evento esperado, evento adicionado e sequencia de `Flow` sao a mesma
        pergunta -- o que precisa acontecer antes deste job -- e por isso o mesmo
        kind; a DIRECAO e que separa, e ela sai em `attrs`."""
        _, facts, _, _ = run_fixture(FIXTURES / "capacidade_abaixo_da_fronteira")
        direcoes = sorted(f.attrs["direction"] for f in _by_kind(facts, "ctm.dependency"))
        assert direcoes == ["add", "sequence", "wait"]
