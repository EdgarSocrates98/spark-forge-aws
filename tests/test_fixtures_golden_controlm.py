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
    # DESDE 2026-09-02 ela e tambem o NEGATIVO de `SF-CTM-004`: folder em array
    # com os jobs declarados como objetos nomeados nao e "job definitions in an
    # array format", e a regra tem de continuar calada sobre ela.
    "folder_em_array",
    # A sentinela e o ponto cego contado quando o JSON nao abre.
    "artefato_ilegivel",
    # ── incremento 3 (2026-09-02): janela e dependencia ──────────────────────
    # As TRES de `SF-CTM-002`, e as tres sao necessarias porque o defeito tem
    # duas formas e a fonte declara um default. A primeira e a que testa o
    # DESENHO: sem o kind derivado no extrator ela produz zero achados.
    "janela_data_especifica_sem_neutralizar",
    "janela_data_especifica_com_dia_da_semana",
    # Esta acumula dois papeis declarados: a terceira de `SF-CTM-002` (as tres
    # opcoes anuladas) e a metade que PASSA da fronteira de `SF-CTM-003` (400).
    "janela_no_teto_de_datas",
    "janela_acima_do_teto_de_datas",
    # `SF-CTM-004`, com o exemplo de dois jobs homonimos da propria pagina.
    "job_em_array_com_nome",
    # O par de `SF-CTM-005`: o aninhado, e o exemplo `Wait2` da pagina, que tem
    # parenteses IRMAOS e nao pode ser acusado.
    "evento_com_parenteses_aninhados",
    "evento_com_parenteses_no_mesmo_nivel",
    # O par de `SF-CTM-006`: o mesmo `Parent`, e a unica diferenca e o job
    # explicito dentro do sub-folder que tem `ReferencePath`.
    "subpasta_com_referencia_e_job_explicito",
    "subpasta_com_referencia_sem_job_explicito",
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


class TestAOmissaoEDecididaNoExtrator:
    """A D-1 do incremento 3, e o teste que separa a regra certa da regra fácil.

    A fonte diz que `SpecificDates` não pode acompanhar `WeekDays`, `Months` nem
    `MonthDays`, **e** que o default das três é `ALL` -- portanto omitir já é
    combinar. O `where` óbvio (as duas propriedades presentes) pega só quem
    escreveu o defeito, e erra quem o herdou do default.

    O motor não consegue exprimir a omissão: `engine._where_matches` reprova
    caminho AUSENTE por construção. Então a decisão vira kind derivado, e esta
    classe é o que prova que ela existe -- desligando-a e medindo o silêncio.
    """

    def test_o_defeito_por_omissao_dispara(self):
        _, facts, findings, _ = run_fixture(
            FIXTURES / "janela_data_especifica_sem_neutralizar"
        )
        agenda = _by_kind(facts, "ctm.schedule")
        assert len(agenda) == 1
        attrs = agenda[0].attrs
        assert attrs["specific_dates_conflict"] is True
        # As TRES estao ausentes, e nenhuma esta escrita com outro valor: e o
        # caso puro de omissao, que e o que a regra existe para pegar.
        assert attrs["specific_dates_conflict_by_omission"] == [
            "MonthDays",
            "Months",
            "WeekDays",
        ]
        assert attrs["specific_dates_conflict_declared"] == []
        assert [f.rule_id for f in findings] == ["SF-CTM-002"]

    def test_sem_o_kind_derivado_a_fixture_de_omissao_fica_verde(self, monkeypatch):
        """O CONTRAFACTUAL, e ele é a razão de o extrator ter mudado.

        `_specific_dates` é a função que não existia antes de 2026-09-02.
        Desligá-la reproduz exatamente o `ctm.schedule` anterior -- sem
        `specific_dates_conflict` --, e `_where_matches` reprova caminho ausente:
        a regra fica calada sobre um artefato defeituoso.

        Se este teste passar a falhar porque a fixture continua vermelha com a
        decisão desligada, alguém moveu o julgamento para uma condição do
        catálogo, e aquela condição não pode estar vendo a omissão.
        """
        from sparkforge.facts import controlm_jobs as cj

        monkeypatch.setattr(cj, "_specific_dates", lambda quando, measures, attrs: None)
        directory = FIXTURES / "janela_data_especifica_sem_neutralizar"
        _, facts, findings, _ = run_fixture(directory)
        agenda = _by_kind(facts, "ctm.schedule")
        assert "specific_dates_conflict" not in agenda[0].attrs
        assert findings == []

    def test_a_opcao_escrita_com_outro_valor_sai_no_campo_certo(self):
        """A segunda forma do mesmo defeito. Ela e a omissao produzem o MESMO
        `rule_id` e evidências diferentes -- e é a diferença que decide se a
        correção acrescenta linha ou troca valor."""
        _, facts, findings, _ = run_fixture(
            FIXTURES / "janela_data_especifica_com_dia_da_semana"
        )
        attrs = _by_kind(facts, "ctm.schedule")[0].attrs
        assert attrs["specific_dates_conflict"] is True
        assert attrs["specific_dates_conflict_declared"] == ["WeekDays"]
        assert attrs["specific_dates_conflict_by_omission"] == []
        assert [f.rule_id for f in findings] == ["SF-CTM-002"]

    def test_as_tres_anuladas_com_none_nao_disparam(self):
        """O negativo, na forma que o exemplo da própria página publica: `NONE`
        dentro de uma LISTA de um item, e não como escalar. Aceitar só o escalar
        acusaria o exemplo oficial da BMC."""
        _, facts, findings, _ = run_fixture(FIXTURES / "janela_no_teto_de_datas")
        attrs = _by_kind(facts, "ctm.schedule")[0].attrs
        assert attrs["specific_dates"] is True
        assert attrs["specific_dates_conflict"] is False
        assert findings == []

    def test_none_conta_nas_duas_grafias_e_lista_com_dois_itens_nao_anula(self):
        """As três decisões de `_neutralized`, medidas direto: lista de um item,
        escalar, e a lista que declara um dia AO LADO da anulação -- que é a
        combinação que a fonte proíbe, e não uma anulação."""
        from sparkforge.facts.controlm_jobs import _neutralized

        assert _neutralized(["NONE"]) is True
        assert _neutralized("NONE") is True
        assert _neutralized("none") is True  # caixa nao e julgada: ver o docstring
        assert _neutralized(["NONE", "MON"]) is False
        assert _neutralized(["ALL"]) is False
        assert _neutralized([]) is False
        assert _neutralized(None) is False


class TestOTetoDeDatasEExato:
    """`J-2`: *"You can list up to 400 dates."* -- e "up to 400" INCLUI 400.

    O par de fixtures existe porque um limiar escrito com `>=` em vez de `>`
    passaria toda a suíte com uma fixture só.
    """

    def test_quatrocentas_datas_passam(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "janela_no_teto_de_datas")
        assert _by_kind(facts, "ctm.schedule")[0].measures["specific_dates_count"] == 400
        assert findings == []

    def test_quatrocentas_e_uma_disparam(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "janela_acima_do_teto_de_datas")
        assert _by_kind(facts, "ctm.schedule")[0].measures["specific_dates_count"] == 401
        assert [f.rule_id for f in findings] == ["SF-CTM-003"]

    def test_o_numero_quatrocentos_esta_na_regra_e_nao_no_extrator(self):
        """Limiar é regra (seção 11 do `CLAUDE.md`), e o extrator só CONTA.

        É o mesmo contrafactual que `SF-CTM-001` faz com `9.0.` no catálogo: se o
        número estiver nos dois lugares, um deles vai divergir na primeira
        atualização da fonte.

        A busca é sobre o AST e não sobre o texto, e a diferença importa: o
        docstring do módulo cita `400` ao EXPLICAR que o limiar mora na regra, e
        uma busca textual reprovaria justamente a prosa que documenta a decisão.
        O que não pode existir é um literal `400` em código executável.
        """
        import ast
        from pathlib import Path as _Path

        import sparkforge.facts.controlm_jobs as cj

        arvore = ast.parse(_Path(cj.__file__).read_text(encoding="utf-8"))
        literais = [
            n.value
            for n in ast.walk(arvore)
            if isinstance(n, ast.Constant) and isinstance(n.value, int)
        ]
        assert 400 not in literais
        regra = next(r for r in load_catalog() if r["id"] == "SF-CTM-003")
        assert regra["threshold"] == {"max_dates": 400}


class TestOAninhamentoDeParenteses:
    """`D-1`: *"nesting of parentheses within parentheses is not supported."*

    Os parênteses são elementos STRING da mesma lista dos eventos, e
    profundidade é contagem -- coisa que nenhum `expr` deste motor faz. O
    extrator percorre a lista uma vez e emite o veredito pronto.
    """

    def test_o_aninhado_dispara_com_profundidade_dois(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "evento_com_parenteses_aninhados")
        logicas = _by_kind(facts, "ctm.event_logic")
        assert len(logicas) == 1
        assert logicas[0].measures["max_paren_depth"] == 2
        assert logicas[0].attrs["nested_parentheses"] is True
        assert logicas[0].attrs["balanced"] is True
        assert [f.rule_id for f in findings] == ["SF-CTM-005"]

    def test_o_exemplo_da_propria_pagina_nao_dispara(self):
        """Dois grupos IRMÃOS -- a forma que a BMC publica como correta. Uma
        regra escrita sobre "tem parêntese" acusaria o exemplo oficial."""
        _, facts, findings, _ = run_fixture(
            FIXTURES / "evento_com_parenteses_no_mesmo_nivel"
        )
        logica = _by_kind(facts, "ctm.event_logic")[0]
        assert logica.measures["max_paren_depth"] == 1
        assert logica.measures["open_paren_count"] == 2
        assert logica.attrs["nested_parentheses"] is False
        assert findings == []

    def test_bloco_de_evento_sem_token_logico_nao_produz_fact(self):
        """O `WaitForEvents` simples do corpus antigo não declara relação
        nenhuma -- o default é `AND` --, e um fact dizendo "profundidade zero"
        sobre ele responderia uma pergunta que ninguém fez. É também o que
        mantém os seis goldens do incremento 2 intactos."""
        _, facts, _, _ = run_fixture(FIXTURES / "capacidade_abaixo_da_fronteira")
        assert _by_kind(facts, "ctm.dependency")
        assert _by_kind(facts, "ctm.event_logic") == []

    def test_a_forma_de_objeto_nomeado_de_waitforevents_e_lida(self):
        """A página escreve `WaitForEvents` como objeto com `Type`, e o corpus do
        incremento 2 o escreve como chave direta no job. As duas formas existem,
        e até 2026-09-02 só a segunda era lida -- um artefato escrito como a
        fonte o escreve saía com zero dependências."""
        _, facts, _, _ = run_fixture(FIXTURES / "evento_com_parenteses_aninhados")
        dependencias = _by_kind(facts, "ctm.dependency")
        assert sorted(f.attrs["event"] for f in dependencias) == [
            "CARGA-CLIENTES",
            "CARGA-ITENS",
            "CARGA-PEDIDOS",
        ]
        assert {f.attrs["direction"] for f in dependencias} == {"wait"}
        assert {f.attrs["container"] for f in dependencias} == {"WaitForEvents"}

    def test_o_desbalanceamento_e_evidencia_e_nao_achado(self):
        """`attrs.balanced` viaja no fact e nenhuma regra o julga: a fonte fala
        de aninhamento e só, e `ctm build` é o validador de schema (`V-CTM-3`).
        Inventar a acusação aqui seria o sexto defeito sem fonte."""
        from sparkforge.facts.controlm_jobs import _event_logic_facts

        facts = _event_logic_facts(
            ["(", {"Event": "a"}, "OR", {"Event": "b"}],
            "WaitForEvents",
            "WaitForEvents",
            {"type": "source_location", "file": "x.json", "line": 0, "col": 0,
             "symbol": "F/J", "snippet": ""},
            {},
        )
        assert len(facts) == 1
        assert facts[0].attrs["balanced"] is False
        assert facts[0].attrs["nested_parentheses"] is False
        assert not any(
            "balanced" in str(r.get("when")) for r in load_catalog()
        )


class TestJobEmArrayEReferencePath:
    """`J-3` e `D-2`, e as duas se defendem pela LITERALIDADE da frase da fonte."""

    def test_dois_jobs_homonimos_no_array_sao_dois_achados(self):
        """O array existe para permitir nome repetido, e o índice na trilha é o
        que separa os dois. Sem ele, `same_subject` juntaria os dois num achado
        só -- o relatório diria "um job" quando são dois."""
        _, facts, findings, _ = run_fixture(FIXTURES / "job_em_array_com_nome")
        formatos = _by_kind(facts, "ctm.job_array_format")
        assert [f.subject["symbol"] for f in formatos] == [
            "CargaDiaria/Jobs[0]/Job1",
            "CargaDiaria/Jobs[1]/Job1",
        ]
        assert {f.attrs["array_key"] for f in formatos} == {"Jobs"}
        assert {f.attrs["name"] for f in formatos} == {"Job1"}
        assert sorted(f.rule_id for f in findings) == ["SF-CTM-004", "SF-CTM-004"]

    def test_folder_em_array_com_job_nomeado_nao_dispara(self):
        """O negativo de `SF-CTM-004`, e ele é grátis porque a leitura foi
        literal: a fonte condiciona o setting a "job definitions in an array
        format". Ler "array" acusaria este artefato, que o corpus do incremento
        2 declara correto."""
        _, facts, findings, _ = run_fixture(FIXTURES / "folder_em_array")
        assert _by_kind(facts, "ctm.job") != []
        assert _by_kind(facts, "ctm.job_array_format") == []
        assert findings == []

    def test_o_par_de_reference_path_difere_so_pelo_job_explicito(self):
        """O contrafactual de `D-2`: mesmo `Parent`, mesmo `JobTemplate`, e a
        única diferença é o job dentro do sub-folder. Se os dois produzirem o
        mesmo veredito, há booleano constante em algum lugar."""
        _, com, achados_com, _ = run_fixture(
            FIXTURES / "subpasta_com_referencia_e_job_explicito"
        )
        _, sem, achados_sem, _ = run_fixture(
            FIXTURES / "subpasta_com_referencia_sem_job_explicito"
        )

        def _sub(facts):
            return next(
                f for f in _by_kind(facts, "ctm.folder")
                if f.attrs.get("folder_type") == "SubFolder"
            )

        assert _sub(com).attrs["reference_path"] == "JobTemplate"
        assert _sub(com).attrs["reference_path_with_explicit_jobs"] is True
        assert _sub(com).measures["explicit_job_count"] == 1
        assert _sub(sem).attrs["reference_path_with_explicit_jobs"] is False
        assert _sub(sem).measures["explicit_job_count"] == 0
        assert [f.rule_id for f in achados_com] == ["SF-CTM-006"]
        assert achados_sem == []

    def test_o_folder_de_topo_sem_reference_path_nao_ganha_atributo(self):
        """`ReferencePath` ausente não produz veredito nenhum, e é isso que
        mantém os seis goldens do incremento 2 intactos: contar job explícito em
        todo folder responderia uma pergunta que ninguém fez."""
        _, facts, _, _ = run_fixture(
            FIXTURES / "subpasta_com_referencia_e_job_explicito"
        )
        topo = next(
            f for f in _by_kind(facts, "ctm.folder") if f.subject["symbol"] == "Parent"
        )
        assert "reference_path" not in topo.attrs
        assert "reference_path_with_explicit_jobs" not in topo.attrs
        assert topo.measures == {}


class TestOSLAContinuaSemFonteEComVeto:
    """O não-objetivo declarado, e o único dos três eixos que sobreviveu ao veto.

    Medido em 2026-09-02 sobre `API_CodeRef_JobProperties.htm`: `SLA`,
    `ServiceLevel`, `Deadline`, `MaxWait` e `CompletionTime` têm ZERO ocorrência.
    Sem campo não há fact, e sem fonte que nomeie defeito não há regra.
    """

    def test_nenhuma_regra_da_area_julga_sla(self):
        regras = [r for r in load_catalog() if r["id"].startswith("SF-CTM-")]
        assert len(regras) == 6
        for regra in regras:
            texto = " ".join(
                [regra["title"], str(regra["when"]), " ".join(regra["requires_facts"])]
            ).lower()
            for palavra in ("sla", "servicelevel", "deadline", "maxwait", "completiontime"):
                assert palavra not in texto, (regra["id"], palavra)

    def test_o_extrator_nao_emite_kind_de_sla(self):
        from sparkforge.facts.controlm_jobs import EMITTED_KINDS

        for kind in EMITTED_KINDS:
            assert "sla" not in kind.lower()

    def test_o_veto_esta_escrito_com_a_medida_que_o_destrava(self):
        """Veto sem medida que o destrave é encolher de ombros, e o molde é o
        `V-GR-1`/`V-GR-2` de `graph.yaml`. `V-CTM-6` guarda a decisão sobre a
        fronteira de Enterprise Manager pela mesma razão."""
        texto = CATALOGO.read_text(encoding="utf-8")
        assert "V-CTM-5" in texto
        assert "V-CTM-6" in texto
        for palavra in ("ServiceLevel", "Deadline", "MaxWait", "CompletionTime"):
            assert palavra in texto
        assert "O QUE DESTRAVA" in texto

    def test_a_fronteira_de_enterprise_manager_nao_virou_eixo_da_matriz(self):
        """A D-2 do incremento 3, medida e não herdada.

        `9.0.21` da frase de `ReferencePath` é numeração de Enterprise Manager, e
        a matriz é do Automation API -- produtos diferentes. A matriz já
        encontrou exigência de EM e sempre a registrou como prosa em `summary`,
        nunca como fronteira legível por máquina, e o vocabulário dos dois eixos
        é FECHADO justamente para que ninguém acrescente chave por analogia.
        """
        from sparkforge.controlm import matrix as cm

        matriz = cm.load()
        for slug, entrada in matriz["capabilities"].items():
            assert set(entrada) <= set(cm.BOUNDARIES) | {"summary", "replaced_by"}, slug
        regra = next(r for r in load_catalog() if r["id"] == "SF-CTM-006")
        assert regra["runtime_scope"] == {}
        # A fronteira e CITADA no achado e nao julgada por condicao nenhuma.
        assert "Enterprise Manager" in regra["explanation"]
        assert "9.0.21" not in str(regra["when"])
