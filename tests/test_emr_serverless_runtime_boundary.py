"""`--emr` sobre facts de EMR Serverless: o que a fonte publica, e so isso.

O `STATUS.md` registrava, na primeira linha da tabela de dividas, que
`sparkforge judge --facts <facts de EMR Serverless> --emr 7.5.0` gravava
`{"spark": "3.5.2-amzn-1", "python": "3.9", "iceberg": "1.6.1-amzn-1"}` --
tudo derivado da `EMR_MATRIX`, que e a matriz de EMR on EC2 -- sobre um
conjunto de facts que nao tem um unico fact de EC2. Tres eixos inventados
sobre um artefato que nao declara nenhum deles.

A DIVIDA LISTAVA TRES SAIDAS, e escolher entre elas era a decisao: recusar a
flag (o que a fase de EMR on EKS fez para `emrc.*`), avisar e marcar os eixos
como derivados de matriz alheia, ou derivar da tabela do Serverless o
componente que ela publica e deixar vazio o que ela nao publica. A terceira foi
a escolhida, e a medicao que a sustenta esta em
`knowledge/emr-serverless/runtime-matrix.md` secoes 2 e 4:

  - a tabela da secao 2 cobre as 30 releases da `EMR_MATRIX`, e e regular: 24
    trazem valor de Spark do Serverless em `X.Y.Z`, 6 trazem `nao existe` (o
    Serverless comeca em 6.6.0, e as quatro releases de patch da serie 6.x nao
    existem la);
  - nas 24, a versao de comunidade coincide com a de EC2 truncada no sufixo do
    fork -- nenhuma divergiu;
  - Hadoop, Iceberg e Python NAO sao publicados por release numerada nenhuma do
    Serverless, e a secao 4 mede as duas unicas releases que publicam Iceberg
    (`emr-spark-8.0.0` e `emr-spark-8.0-preview`), que a `EMR_MATRIX` nem
    sequer conhece.

A assimetria com o EKS e deliberada e esta medida na propria divida: la a
matriz de EC2 e MEDIDAMENTE ERRADA (a AWS publica matriz do EKS e ela diverge),
o que torna a recusa a unica saida defensavel; aqui ela e inaplicavel por FALTA
DE FONTE em tres colunas -- e a quarta, `spark`, a fonte do Serverless publica.
Recusar entregaria menos do que a fonte sustenta.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.adapters._core import AdapterError, judge_findings
from sparkforge.facts import runtime_matrix
from sparkforge.facts.runtime_detect import EMR_MATRIX, EMR_SERVERLESS_MATRIX

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "knowledge" / "emr-serverless" / "runtime-matrix.md"
FACTS_EMRS = (
    ROOT / "fixtures" / "emr_serverless" / "app_saudavel" / "expected" / "facts.json"
)
FACTS_EC2_DIR = ROOT / "fixtures" / "emr"

# `emr-7.5.0` e a release do golden, e ela e o caso que interessa: a `EMR_MATRIX`
# de EC2 publica `3.5.2-amzn-1` e a tabela do Serverless publica `3.5.2`. Acertar
# a versao de comunidade por truncamento nao seria acerto -- o valor REPORTADO
# continuaria afirmando um fork que a fonte do Serverless nao declara.
RELEASE = "7.5.0"
SPARK_NO_EC2 = "3.5.2-amzn-1"
SPARK_NO_SERVERLESS = "3.5.2"

# Os dois eixos que a fonte do Serverless nao publica em release numerada
# nenhuma. `python` sai de `EMR_MATRIX["7.5.0"]["python"]` e `iceberg` de
# `EMR_MATRIX["7.5.0"]["iceberg"]`, e nenhum dos dois tem fonte do lado do
# Serverless (secao 5 do knowledge: Hadoop nao e nomeado em nenhuma das 24
# paginas, Iceberg tem um ponto em release note, Python tem um numero num aviso
# de procedimento para 6.6.0).
EIXOS_SEM_FONTE = ("python", "iceberg")

_AUSENTE = {"**nao existe**", "**não existe**", "—", "-", ""}


def _judge(release: str | None = None, facts_path: Path = FACTS_EMRS) -> dict:
    return judge_findings(facts_path=str(facts_path), emr=release)


def _tabela_do_knowledge() -> dict[str, dict[str, str]]:
    """Le as tabelas das secoes 2 e 4 de `knowledge/emr-serverless/runtime-matrix.md`.

    Parsear o markdown em vez de reescrever os valores aqui e o que faz deste um
    guard de DRIFT e nao uma terceira copia da matriz: ela existe em dois
    lugares -- a pagina auditada e o YAML legivel por maquina -- e este teste e
    a ponte entre eles. Mesmo mecanismo de
    `tests/test_runtime_emr_matrix.py::_committed_matrix`.

    As duas tabelas tem quatro colunas e se distinguem pelo rotulo: as da secao
    2 sao `emr-<major>.<minor>.<patch>` e trazem (EC2, Serverless, bate); as da
    secao 4 sao `emr-spark-*` e trazem (Spark, Iceberg, observacao).
    """
    linhas: dict[str, dict[str, str]] = {}
    for linha in DOC.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("|"):
            continue
        # As duas tabelas nao escrevem o rotulo do mesmo jeito -- a da secao 4
        # o poe entre crases --, e um parser que so aceite uma das formas leria
        # metade da matriz e deixaria a outra metade sem guard nenhum.
        celulas = [c.strip().strip("`") for c in linha.strip().strip("|").split("|")]
        rotulo = celulas[0]
        if not rotulo.startswith("emr-"):
            continue
        chave = rotulo[4:] if rotulo.lower().startswith("emr-") else rotulo
        if rotulo.startswith("emr-spark-"):
            linhas[chave] = {"spark": celulas[1], "iceberg": celulas[2]}
            continue
        serverless = celulas[2]
        if serverless in _AUSENTE:
            continue
        linhas[chave] = {"spark": serverless}
    return linhas


COMMITTED = _tabela_do_knowledge()


class TestAPremissa:
    """Medida antes da afirmacao: o conjunto de facts nao tem lado de EC2.

    Se um fact `emr.*` entrasse neste golden, `--emr` passaria a ser declaracao
    legitima sobre um artefato presente, e todo o resto deste arquivo mediria
    outra coisa.
    """

    def test_o_golden_so_tem_kinds_de_serverless(self):
        kinds = sorted(
            {f["kind"] for f in json.loads(FACTS_EMRS.read_text(encoding="utf-8"))}
        )
        assert kinds, f"{FACTS_EMRS} vazio"
        assert all(k.startswith("emrs.") for k in kinds), (
            f"{FACTS_EMRS} carrega kinds fora de `emrs.`: {kinds}"
        )

    def test_a_release_do_golden_e_a_que_este_arquivo_mede(self):
        facts = json.loads(FACTS_EMRS.read_text(encoding="utf-8"))
        labels = {
            f["attrs"]["release_label"]
            for f in facts
            if f["kind"] == "emrs.application" and "release_label" in f.get("attrs", {})
        }
        assert labels == {f"emr-{RELEASE}"}, f"o golden mudou de release: {sorted(labels)}"

    def test_as_duas_matrizes_discordam_nesta_release(self):
        """Sem esta discordancia o teste passaria por coincidencia."""
        assert EMR_MATRIX[RELEASE]["spark"] == SPARK_NO_EC2
        assert COMMITTED[RELEASE]["spark"] == SPARK_NO_SERVERLESS
        assert SPARK_NO_EC2 != SPARK_NO_SERVERLESS


class TestOQueAFonteDoServerlessPublica:
    def test_spark_sai_sem_o_sufixo_que_a_fonte_nao_publica(self):
        runtime = _judge(RELEASE)["runtime"]
        assert runtime["spark"] == SPARK_NO_SERVERLESS, (
            f"`--emr {RELEASE}` sobre facts `emrs.*` gravou {runtime['spark']!r}. "
            f"A fonte do Serverless publica {SPARK_NO_SERVERLESS!r}; "
            f"{SPARK_NO_EC2!r} e o fork de EC2, e o sufixo `-amzn-N` nao existe "
            f"na fonte do Serverless (secao 1 do knowledge)."
        )

    @pytest.mark.parametrize("eixo", EIXOS_SEM_FONTE)
    def test_o_eixo_sem_fonte_fica_vazio(self, eixo):
        runtime = _judge(RELEASE)["runtime"]
        assert runtime[eixo] == "", (
            f"`--emr {RELEASE}` sobre facts `emrs.*` gravou {eixo}={runtime[eixo]!r}, "
            f"copiado de `EMR_MATRIX[{RELEASE!r}]`. A fonte do EMR Serverless nao "
            f"publica {eixo} para release numerada nenhuma (secao 5 do knowledge). "
            f"Vazio e como este motor diz `nao sei`: `in_scope` reprova o eixo e a "
            f"regra e pulada por ausencia."
        )

    def test_o_eixo_emr_continua_lido_porque_o_operador_o_declarou(self):
        """`emr` nao e derivado: e a propria declaracao da flag, e o Serverless
        usa o MESMO namespace de release label (`emr-7.5.0`), como o proprio
        golden mostra. Apaga-lo trocaria invencao por perda de informacao."""
        assert _judge(RELEASE)["runtime"]["emr"] == RELEASE

    def test_detected_from_distingue_o_eixo_lido_do_eixo_derivado(self):
        detected = _judge(RELEASE)["runtime"]["detected_from"]
        assert "cli" in detected
        derivados = [d for d in detected if d.endswith(":matrix")]
        assert derivados, (
            f"`detected_from` saiu {detected}: sem nomear a matriz, o operador nao "
            f"tem como distinguir o eixo `emr` que ele DECLAROU do eixo `spark` que "
            f"o motor DERIVOU de uma tabela."
        )
        assert any("serverless" in d for d in derivados), (
            f"a origem derivada precisa NOMEAR a matriz do Serverless. Saiu: {derivados}"
        )

    def test_release_que_o_serverless_nao_publica_nao_deriva_nada(self):
        """`emr-6.4.0` esta na `EMR_MATRIX` e NAO existe no Serverless: a propria
        pagina de releases declara 6.6.0 como piso. Derivar dela seria afirmar um
        runtime para uma combinacao que a AWS nao oferece."""
        assert "6.4.0" in EMR_MATRIX
        assert "6.4.0" not in COMMITTED
        runtime = _judge("6.4.0")["runtime"]
        assert runtime["spark"] == "", (
            f"gravou spark={runtime['spark']!r} para uma release que o EMR "
            f"Serverless nao publica (secao 3 do knowledge)."
        )

    def test_sem_a_flag_o_julgamento_continua_acontecendo(self):
        """A derivacao e da FLAG. Sem ela, nada muda -- e as regras `SF-EMRS`
        declaram `runtime_scope: {}` e nao dependem de eixo nenhum."""
        resultado = _judge(None)
        assert resultado["runtime"]["emr"] == ""
        assert resultado["runtime"]["spark"] == ""
        assert resultado["total_count"] == 0, (
            f"`app_saudavel` e o negativo da area: nenhuma regra deve disparar. "
            f"Saiu {resultado['items']}"
        )

    def test_um_conjunto_com_facts_de_ec2_continua_na_matriz_de_ec2(self, tmp_path):
        """A troca de matriz e ESTREITA, no molde da recusa de EKS.

        Fundir um `describe-cluster` com um `get-application` e caso legitimo, e
        ali `--emr` declara o lado de EC2 que esta de fato presente -- com o
        fork, que aquela fonte publica.
        """
        emrs = json.loads(FACTS_EMRS.read_text(encoding="utf-8"))
        primeiro = sorted(p for p in FACTS_EC2_DIR.iterdir() if p.is_dir())[0]
        ec2_facts = json.loads(
            (primeiro / "expected" / "facts.json").read_text(encoding="utf-8")
        )
        assert any(f["kind"].startswith("emr.") for f in ec2_facts), (
            "o corpus de EC2 mudou de namespace e este contrafactual perdeu o sentido"
        )
        misto = tmp_path / "facts.json"
        misto.write_text(json.dumps(emrs + ec2_facts), encoding="utf-8")
        runtime = _judge(RELEASE, misto)["runtime"]
        # Qual release vence o eixo `emr` nao e assunto desta guarda: a flag e
        # DECLARACAO e perde para o `describe-cluster`, que este conjunto tambem
        # carrega. O que se mede aqui e a MATRIZ consultada -- e o sufixo do fork
        # e a assinatura da de EC2, que so ela publica.
        assert "-amzn" in runtime["spark"], (
            f"com um `describe-cluster` presente, o lado de EC2 existe e a matriz "
            f"de EC2 e a certa -- ela publica o fork. Saiu {runtime['spark']!r}"
        )
        assert not [d for d in runtime["detected_from"] if "serverless" in d], (
            f"a matriz do Serverless foi consultada num conjunto que tem artefato "
            f"de EC2: {runtime['detected_from']}"
        )


class TestOEksContinuaRecusando:
    """A saida escolhida aqui nao pode afrouxar a que a fase de EKS fechou."""

    def test_a_flag_sobre_facts_de_eks_continua_recusada(self):
        eks = (
            ROOT
            / "fixtures"
            / "emr_eks"
            / "job_run_saudavel"
            / "expected"
            / "facts.json"
        )
        with pytest.raises(AdapterError) as erro:
            _judge(RELEASE, eks)
        assert erro.value.exit_code == 2


class TestGuardDeDriftContraOKnowledge:
    """A matriz legivel por maquina espelha a pagina auditada, celula a celula."""

    def test_a_pagina_foi_parseada_de_verdade(self):
        assert len(COMMITTED) >= 26, (
            f"o parser leu {len(COMMITTED)} linhas -- se o formato da tabela mudar, "
            f"este guard passaria vazio"
        )

    def test_o_conjunto_de_releases_e_identico(self):
        assert set(EMR_SERVERLESS_MATRIX) == set(COMMITTED)

    @pytest.mark.parametrize("release", sorted(COMMITTED))
    def test_cada_celula_casa_com_a_pagina(self, release):
        assert EMR_SERVERLESS_MATRIX[release] == COMMITTED[release]

    def test_nenhuma_release_numerada_carrega_python_ou_iceberg(self):
        """A invariante que separa esta matriz da de EC2: coluna sem fonte nao
        existe. As duas unicas com `iceberg` sao as `emr-spark-8.0*` da secao 4,
        que a fonte do Serverless publica com sufixo."""
        for release, linha in EMR_SERVERLESS_MATRIX.items():
            assert "python" not in linha, (
                f"{release} carrega `python`, e a fonte do Serverless nao o publica "
                f"para release nenhuma (secao 5 do knowledge)"
            )
            if "iceberg" in linha:
                assert release.startswith("spark-"), (
                    f"{release} carrega `iceberg` e nao e uma das duas releases da "
                    f"secao 4, as unicas em que a fonte do Serverless o publica"
                )


class TestAFonteEVigiada:
    def test_toda_url_declarada_esta_na_watchlist(self):
        """URL na matriz sem entrada em `knowledge/sources.lock.json` nao tem hash
        nem data revalidados por `scripts/refresh_knowledge.py` -- e a mesma
        invariante que a matriz do Glue carrega."""
        vigiadas = runtime_matrix.watched_sources()
        faltando = [
            url for url in runtime_matrix.emr_serverless_sources() if url not in vigiadas
        ]
        assert not faltando, f"fontes fora da watchlist: {faltando}"
