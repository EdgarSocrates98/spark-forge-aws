"""Os fakes de coleta precisam RECUSAR o que o servico real recusa.

## A classe de defeito que este arquivo fecha

Medido em 2026-09-03, contra o Athena real: `$delete_files` NAO EXISTE -- a
consulta responde `TABLE_REDIRECTION_ERROR`. Ela estava em
`ICEBERG_METADATA_SECTIONS` e toda coleta falhava naquela secao, com o extrator
recebendo um dump indistinguivel de uma tabela sem deletes.

**O teste ficava verde porque o fake respondia.** `FakeAthenaClient` devolvia
lista vazia para qualquer `QueryString`, entao a consulta impossivel passava.

    Um fake que aceita tudo prova que o codigo chama o que ele espera,
    nunca que o servico responde.

A auditoria que se seguiu achou o mesmo padrao no CloudWatch: o fake devolvia
UM resultado para 17 consultas, e nem a paginacao por `NextToken` nem o caso de
resposta parcial eram exercitados.

## O que estes testes travam

Nao e possivel provar aqui que um fake concorda com a AWS -- isso exige a AWS.
O que da para travar e mais estreito e ainda util: **o fake precisa ter uma
forma de dizer NAO**. Um fake sem caminho de recusa nao consegue exercitar o
ramo de erro do coletor, e e nesse ramo que os defeitos desta classe moram.
"""

from __future__ import annotations

import inspect

import pytest

import tests.test_collect_aws as tc

# Os fakes que respondem por um servico AWS. `FakeBoto3` e roteador, nao
# servico, e por isso fica de fora.
FAKES = [
    nome
    for nome in dir(tc)
    if nome.startswith(("Fake", "Empty", "Failing"))
    and nome != "FakeBoto3"
    and inspect.isclass(getattr(tc, nome))
]


def test_a_lista_de_fakes_nao_esta_vazia():
    """Guarda do proprio guard: se a deteccao quebrar, os testes abaixo
    passariam sobre lista vazia."""
    assert len(FAKES) >= 8, f"esperado >= 8 fakes, achei {FAKES}"


class TestCadaServicoTemUmCaminhoDeRecusa:
    """Para cada servico, existe pelo menos um fake que FALHA ou devolve vazio.

    Sem isso, o ramo de erro do coletor -- `CollectionFailed`, secao ausente,
    resposta parcial -- nunca roda em teste nenhum.
    """

    def test_athena_tem_fake_que_falha(self):
        assert hasattr(tc, "FailingAthenaClient")

    def test_s3_tem_fake_vazio(self):
        """`EmptyS3Client` e o que exercita "prefixo sem objeto" -- a resposta
        que o S3 real da para um event log que nao existe."""
        assert hasattr(tc, "EmptyS3Client")

    def test_cloudwatch_sabe_paginar_e_sabe_faltar(self):
        """Os dois comportamentos reais que o fake antigo nao tinha.

        `get_metric_data` pagina por `NextToken`, e pode devolver menos
        resultados do que se pediu. Um fake que sempre devolve tudo de uma vez
        nao exercita nenhum dos dois.
        """
        assinatura = inspect.signature(tc.FakeCloudWatchClient.__init__)
        assert "paginas" in assinatura.parameters, (
            "o fake precisa saber paginar; sem isso, o coletor que ignora "
            "`NextToken` passa no teste e trunca a serie em producao"
        )
        assert "faltando" in assinatura.parameters, (
            "o fake precisa saber devolver menos do que se pediu; sem isso, um "
            "payload parcial sai com a mesma cara de um completo"
        )


class TestOFakeDoAthenaNaoInventaTabela:
    """O defeito original, travado pela raiz.

    `FakeAthenaClient` devolve `[]` para query que nao esta em `rows_by_query`.
    Isso e adequado para "a tabela existe e esta vazia" -- e ERRADO para "a
    tabela nao existe", que e `TABLE_REDIRECTION_ERROR`.

    Enquanto os dois casos derem a mesma resposta, uma secao impossivel na lista
    do coletor continua invisivel.
    """

    def test_secao_impossivel_nao_esta_na_lista_do_coletor(self):
        """A trava direta: `delete_files` fora de `ICEBERG_METADATA_SECTIONS`.

        Medido contra o Athena real -- ver
        `ICEBERG_SECOES_INDISPONIVEIS_NO_ATHENA` em `collect/aws.py`, que
        nomeia cada uma e diz o que custaria destravar.
        """
        from sparkforge.collect import aws

        indisponiveis = set(aws.ICEBERG_SECOES_INDISPONIVEIS_NO_ATHENA)
        pedidas = set(aws.ICEBERG_METADATA_SECTIONS)
        intersecao = pedidas & indisponiveis
        assert not intersecao, (
            f"o coletor pede secao que o Athena nao expoe: {sorted(intersecao)}. "
            f"A consulta da TABLE_REDIRECTION_ERROR, e o dump chega sem a secao "
            f"-- indistinguivel de uma tabela que genuinamente nao a tem."
        )

    def test_toda_secao_indisponivel_diz_o_que_custaria(self):
        from sparkforge.collect import aws

        for secao, razao in aws.ICEBERG_SECOES_INDISPONIVEIS_NO_ATHENA.items():
            assert razao.strip(), f"{secao} sem razao escrita"

    def test_delete_files_esta_entre_as_indisponiveis_com_a_alternativa(self):
        """A recusa precisa dizer ONDE os deletes estao, nao so que a secao
        falta: eles vem de `$files` pela coluna `content`."""
        from sparkforge.collect import aws

        razao = aws.ICEBERG_SECOES_INDISPONIVEIS_NO_ATHENA["delete_files"]
        assert "content" in razao
        assert "files" in razao


@pytest.mark.parametrize("nome", FAKES)
def test_todo_fake_registra_o_que_lhe_pediram(nome):
    """Um fake que nao guarda as chamadas nao permite asserir sobre elas.

    E como se mede que o coletor pediu o que devia -- e foi assim que a
    auditoria de 2026-09-03 viu que ele pedia `$delete_files`.
    """
    cls = getattr(tc, nome)
    fonte = inspect.getsource(cls)
    if "def __init__" not in fonte:
        pytest.skip(f"{nome} nao tem estado; nada a registrar")
    assert "self.calls" in fonte or "raise" in fonte, (
        f"{nome} nao registra chamadas nem levanta. Um fake assim so pode "
        f"provar que o codigo nao explodiu."
    )
