"""A prova do objetivo da Fase 5c, ponta a ponta.

O criterio 7 do spec: *a prova de ponta a ponta mostra achado `SF-DQ` e achado
`SF-PY` sobre a mesma linha, sem duplicacao semantica*. E a decisao D-3: a
fronteira entre as duas areas e **por construcao, nao por supressao**.

A diferenca importa, e e ela que esta suite mede. Fronteira por supressao seria
`SF-PY` se calar quando a linha for validacao -- achado unico e mais preciso, ao
custo de acoplar duas areas de catalogo, que foi o que a Fase 5a passou uma fase
inteira desfazendo. Fronteira por construcao e o que existe: `SF-DQ` so recebeu
gatilho que **exige saber que a action e uma validacao**, entao as duas areas
podem falar da mesma linha sem se repetirem, e nenhuma precisa ser calada.

O corpus e um job com um unico defeito composto: a validacao roda depois do
write **e** a cadeia que a implementa faz join antes de reduzir. Uma linha, dois
achados, dois assuntos. `SF-PY-003` fala do que a cadeia custa; `SF-DQ-001` fala
de o dado ruim ja estar publicado quando o alarme toca. Nenhum dos dois sabe
produzir o outro.

Como nas provas das fases anteriores, a investigacao roda **sem flag de runtime
nenhuma** e afirma sobre o relatorio inteiro -- regra individual ja tem cobertura
nas fixtures golden de `fixtures/dq/`; o que so aqui se prova e a composicao.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.facts.data_quality import extract_data_quality_tree
from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

# O job da investigacao. A linha do `ruins = ...` e o ponto em que as duas areas
# se encontram: para o extrator de `pyspark_ast` ela e uma cadeia com join antes
# da primeira reducao; para o de `data_quality` ela e um check artesanal que roda
# depois do `write` do mesmo alvo. Escrito aqui, e nao lido de `fixtures/dq/`,
# porque nenhuma das oito fixtures tem as duas leituras na mesma linha -- elas
# provam regra a regra, e esta suite prova o encontro.
JOB = '''
"""Publicacao diaria de vendas na camada curated."""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.getOrCreate()


def publicar(data_ref):
    pedidos = spark.read.parquet("s3://lake/raw/pedidos/")
    catalogo = spark.read.parquet("s3://lake/raw/catalogo/")

    vendas = pedidos.withColumn("valor", F.col("quantidade") * F.col("preco"))
    vendas.write.mode("overwrite").parquet("s3://lake/curated/vendas/")

    ruins = vendas.join(catalogo, "produto_id").filter(F.col("valor") < 0).count()
    if ruins > 0:
        raise ValueError(f"{ruins} vendas invalidas em {data_ref}")
'''

# Os mesmos seis guardas de infraestrutura Glue que a prova da Fase 5b vigia.
GLUE_INFRA = {
    # SF-GLUE-001 foi aposentada em 2026-08-28 (acusava a configuracao
    # correta); SF-GLUE-007 ocupa a mesma natureza -- infraestrutura Glue
    # guardada por versao -- e o id antigo NAO e reaproveitado.
    "SF-GLUE-007",
    "SF-GLUE-002",
    "SF-GLUE-003",
    "SF-GLUE-004",
    "SF-GLUE-005",
    "SF-GLUE-006",
}


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    raiz = tmp_path_factory.mktemp("dq_investigacao")
    (raiz / "job.py").write_text(JOB, encoding="utf-8")
    return raiz


@pytest.fixture(scope="module")
def facts(corpus) -> dict[str, list]:
    """Os dois extratores sobre a mesma arvore, que e o custo aceito por D-2.

    Separados por area para que os testes de independencia possam julgar cada
    metade sozinha -- e essa comparacao que distingue fronteira por construcao
    de fronteira por supressao.
    """
    return {
        "dq": list(extract_data_quality_tree(corpus, repo_root=corpus)),
        "py": list(extract_tree(corpus, repo_root=corpus)),
    }


@pytest.fixture(scope="module")
def relatorio(facts) -> tuple[list, list]:
    """Uma investigacao real: sem flag de runtime, contexto vazio."""
    return judge(facts["dq"] + facts["py"], load_catalog(), {}, return_skipped=True)


def _area(rule_id: str) -> str:
    return rule_id.rsplit("-", 1)[0]


def _assinatura(achados) -> list[tuple]:
    """Identidade comparavel de um achado, sem depender de `__eq__` do modelo."""
    return sorted(
        (
            f.rule_id,
            f.severity,
            f.subject.get("file", ""),
            f.subject.get("line", 0),
            f.subject.get("col", 0),
            tuple(f.evidence),
        )
        for f in achados
    )


class TestTheTwoAreasSpeakAboutTheSameLine:
    """Criterio 7, primeira metade: as duas areas alcancam a mesma linha."""

    def test_both_areas_produce_findings(self, relatorio):
        achados, _ = relatorio
        areas = {_area(f.rule_id) for f in achados}
        assert "SF-DQ" in areas, (
            "nenhum achado SF-DQ sobre um job que valida depois de escrever. O "
            "extrator de validacao nao alcancou o corpus, ou o gatilho de posicao "
            "parou de correlacionar check e write."
        )
        assert "SF-PY" in areas, (
            "nenhum achado SF-PY. A analise de codigo nao pode encolher porque a "
            "area SF-DQ passou a existir sobre o mesmo arquivo."
        )

    def test_the_same_line_carries_one_finding_from_each_area(self, relatorio):
        achados, _ = relatorio
        por_linha: dict[tuple[str, int], set[str]] = {}
        for f in achados:
            chave = (f.subject.get("file", ""), f.subject.get("line", 0))
            por_linha.setdefault(chave, set()).add(_area(f.rule_id))
        compartilhadas = [k for k, v in por_linha.items() if {"SF-DQ", "SF-PY"} <= v]
        assert compartilhadas, (
            f"nenhuma linha recebeu achado das duas areas. Distribuicao: {por_linha}. "
            f"O corpus foi montado para que a linha do check artesanal fosse lida "
            f"pelos dois extratores; se ela deixou de ser, a prova de D-3 perdeu o "
            f"caso que ela existe para julgar."
        )


class TestNoSemanticDuplication:
    """Criterio 7, segunda metade -- e a que falha se D-3 for desfeito.

    Duas coisas diferentes poderiam desfazer a decisao, e cada teste aqui pega
    uma delas:

    1. Alguem faz as areas dizerem a mesma coisa, dando a uma delas gatilho no
       namespace de fact da outra. `test_neither_area_reads_the_other_namespace`
       e `test_findings_of_the_two_areas_cite_disjoint_facts` reprovam.
    2. Alguem suprime uma area quando a outra fala, para "nao repetir".
       `test_each_area_judges_the_same_with_or_without_the_other` reprova, porque
       supressao so pode ser implementada olhando o fact alheio.
    """

    def test_the_two_areas_say_different_things_about_the_shared_line(self, relatorio):
        achados, _ = relatorio
        por_linha: dict[tuple[str, int], list] = {}
        for f in achados:
            chave = (f.subject.get("file", ""), f.subject.get("line", 0))
            por_linha.setdefault(chave, []).append(f)
        for chave, grupo in por_linha.items():
            areas = {_area(f.rule_id) for f in grupo}
            if not {"SF-DQ", "SF-PY"} <= areas:
                continue
            titulos = {f.title for f in grupo}
            assert len(titulos) == len(grupo), (
                f"em {chave} duas regras produziram o mesmo titulo: {sorted(titulos)}. "
                f"Achado repetido em area diferente e ruido com duas fontes -- o "
                f"operador le duas vezes e conclui que sao dois problemas."
            )

    def test_findings_of_the_two_areas_cite_disjoint_facts(self, relatorio):
        achados, _ = relatorio
        citados = {
            area: {fid for f in achados if _area(f.rule_id) == area for fid in f.evidence}
            for area in ("SF-DQ", "SF-PY")
        }
        comum = citados["SF-DQ"] & citados["SF-PY"]
        assert not comum, (
            f"as duas areas citam os mesmos facts como evidencia: {sorted(comum)}. "
            f"Falar da mesma linha e legitimo; sustentar-se no mesmo fact e a "
            f"definicao operacional de duplicacao semantica."
        )

    def test_neither_area_reads_the_other_namespace(self):
        """A disjuncao vale no catalogo inteiro, nao so nos achados deste corpus.

        Um corpus prova o que ele contem. Esta medida e sobre as regras: uma
        regra `SF-PY` que passe a ler `dq.*` -- ou o contrario -- reprova aqui
        mesmo antes de existir fixture que a dispare.
        """
        catalogo = load_catalog()
        for regra in catalogo:
            area = _area(regra["id"])
            if area not in {"SF-DQ", "SF-PY"}:
                continue
            alheio = "pyspark." if area == "SF-DQ" else "dq."
            lidos = set(regra.get("requires_facts") or []) | _kinds_in_when(regra["when"])
            invasores = sorted(k for k in lidos if k.startswith(alheio))
            assert not invasores, (
                f"{regra['id']} le {invasores}, do namespace da area vizinha. A "
                f"fronteira de D-3 e por construcao: cada area julga os facts do "
                f"seu proprio extrator. Regra que le fact alheio ou repete o que a "
                f"outra ja disse, ou a cala."
            )

    def test_each_area_judges_the_same_with_or_without_the_other(self, facts):
        """Nenhuma supressao cruzada existe -- e este teste e como se sabe.

        Se um dia `SF-PY` ganhar `absent: dq.check` para se calar sobre linha de
        validacao, o julgamento com os dois conjuntos de facts deixara de ser
        igual ao julgamento so com `pyspark.*`, e a asserção quebra. E o unico
        jeito de implementar supressao e olhando o fact da outra area.
        """
        catalogo = load_catalog()
        completo, _ = judge(facts["dq"] + facts["py"], catalogo, {}, return_skipped=True)
        for area, metade in (("SF-DQ", facts["dq"]), ("SF-PY", facts["py"])):
            sozinha, _ = judge(metade, catalogo, {}, return_skipped=True)
            esperado = [a for a in _assinatura(completo) if _area(a[0]) == area]
            obtido = [a for a in _assinatura(sozinha) if _area(a[0]) == area]
            assert obtido == esperado, (
                f"os achados de {area} mudam conforme os facts da outra area estao "
                f"presentes.\n  com as duas: {esperado}\n  sozinha:     {obtido}\n"
                f"Interferencia entre areas e acoplamento de catalogo, que foi o "
                f"defeito que a Fase 5a desfez."
            )


def _kinds_in_when(no: object) -> set[str]:
    """Todo kind de fact citado numa arvore de condicao (`fact:` e `absent:`)."""
    achados: set[str] = set()
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave in {"fact", "absent"} and isinstance(valor, str):
                achados.add(valor)
            else:
                achados |= _kinds_in_when(valor)
    elif isinstance(no, list):
        for item in no:
            achados |= _kinds_in_when(item)
    return achados


class TestGlueRulesAreReportedNotSilenced:
    """Herdado da prova da Fase 5b, e vale igual aqui.

    Uma investigacao de codigo puro nao tem eixo de infraestrutura Glue. As seis
    regras nao podem sumir dos dois lados do relatorio: silencio, para quem le,
    e indistinguivel de "revisei e esta certo".
    """

    def test_the_glue_infra_rules_appear_as_skipped_by_runtime_scope(self, relatorio):
        _, pulados = relatorio
        por_escopo = {s["rule_id"] for s in pulados if s.get("reason") == "runtime_scope"}
        faltando = sorted(GLUE_INFRA - por_escopo)
        assert not faltando, (
            f"{faltando} nao aparecem em `skipped` com `reason: runtime_scope` numa "
            f"investigacao sem runtime declarado. O operador nao fica sabendo que o "
            f"eixo de infraestrutura Glue nao foi coberto."
        )

    def test_every_skipped_rule_carries_a_reason(self, relatorio):
        _, pulados = relatorio
        sem_motivo = sorted(s["rule_id"] for s in pulados if not s.get("reason"))
        assert not sem_motivo, (
            f"{sem_motivo} foram puladas sem motivo declarado. Skip sem razao e "
            f"silencio com passos extras."
        )


class TestNoAreaIsSilentlyEmpty:
    """A ponta agregada, no molde da prova da 5b: nenhuma area some sem ser dita."""

    def test_every_area_either_fires_or_is_reported_as_skipped(self, relatorio):
        achados, pulados = relatorio
        todas = {_area(r["id"]) for r in load_catalog() if r.get("executable", True)}
        vistas = {_area(f.rule_id) for f in achados} | {_area(s["rule_id"]) for s in pulados}
        mudas = sorted(todas - vistas)
        assert not mudas, (
            f"areas que nao aparecem de lado nenhum do relatorio: {mudas}. Uma area "
            f"inteira ausente sem motivo e o falso negativo mais caro que existe: o "
            f"operador conclui que aquele eixo esta limpo."
        )
