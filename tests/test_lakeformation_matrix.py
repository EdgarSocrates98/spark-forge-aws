"""O eixo de versao de Lake Formation existe em DOIS lugares, e este arquivo os
trava juntos.

`knowledge/glue/lakeformation-matrix.yaml` e a forma legivel por maquina;
a tabela da §0 de `knowledge/glue/lakeformation-fgac.md` e a que uma pessoa le.
Prosa e dado divergindo em silencio e o mesmo defeito que o gate de lastro fecha
para NUMERO -- e que aqui, ate 2026-09-09, nao tinha guarda nenhuma porque a
matriz nao era dado.

O que estes testes cobram, em ordem de gravidade:

  1. toda celula com status que EXIGE fonte tem fonte, e a fonte esta declarada;
  2. as tres colunas da tabela markdown sao as mesmas do YAML;
  3. toda linha da tabela markdown tem eixo correspondente no YAML;
  4. nenhuma celula `not_declared` carrega frase -- se carregasse, nao seria
     nao declarada;
  5. o verbo devolve `unresolved` NOMEADO para runtime fora da matriz, e nunca
     um palpite por analogia.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from sparkforge.adapters import _core
from sparkforge.facts import lakeformation_matrix as matriz

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "knowledge" / "glue" / "lakeformation-fgac.md"

# As duas linhas da tabela markdown que o YAML NAO carrega, e a ausencia e
# deliberada: versao de componente por runtime mora em `runtime-matrix.yaml`, e
# um segundo arquivo com `Spark 3.5.6` criaria duas fontes de verdade para o
# mesmo numero.
VERSOES_SO_NA_PROSA = frozenset({"spark", "iceberg"})


def _normaliza(rotulo: str) -> str:
    """Rotulo comparavel entre prosa e YAML: sem backtick, sem caixa.

    A prosa escreve ``FGAC via `GlueContext`/DynamicFrame`` e o YAML escreve o
    mesmo sem os backticks -- markdown formata, dado nao. Comparar cru faria o
    gate reprovar por marcacao.
    """
    return rolo.strip().replace("`", "").replace("*", "").lower() if (rolo := rotulo) else ''


def _tabela_do_markdown() -> tuple[list[str], list[tuple[str, list[str]]]]:
    """`(cabecalho, linhas)` da tabela da §0, lida do markdown.

    Ancorada na §0 e na PRIMEIRA tabela dela: o documento tem outras tabelas
    (a §6 tem a das quatro frases em conflito), e casar "qualquer tabela"
    passaria a conferir a errada assim que uma nova entrasse.
    """
    texto = DOC.read_text(encoding="utf-8")
    inicio = texto.index("## 0. O eixo de versão")
    fim = texto.index("## 1. O que FGAC exige")
    secao = texto[inicio:fim]
    linhas = [linha.strip() for linha in secao.split("\n") if linha.strip().startswith("|")]
    assert linhas, "a §0 nao tem tabela"

    def celulas(linha: str) -> list[str]:
        return [c.strip() for c in linha.strip("|").split("|")]

    cabecalho = celulas(linhas[0])
    corpo: list[tuple[str, list[str]]] = []
    for linha in linhas[1:]:
        cs = celulas(linha)
        # A linha separadora (`|---|---|`) nao e dado.
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cs if c):
            continue
        corpo.append((cs[0], cs[1:]))
    return cabecalho, corpo


class TestYamlValida:
    def test_carrega_sem_erro(self):
        """`load()` valida na carga: status fora do vocabulario, fonte que nao
        esta em `fontes`, ou eixo sem celula em algum runtime derrubam aqui."""
        assert matriz.load()

    def test_todo_status_esta_no_vocabulario_fechado(self):
        for runtime in matriz.known_runtimes():
            for eixo in matriz.eixos():
                celula = matriz.capability(runtime, eixo["id"])
                assert celula is not None, (runtime, eixo["id"])
                assert celula["status"] in matriz.STATUS_VALIDOS

    def test_status_que_exige_fonte_tem_fonte_declarada(self):
        fontes = set((matriz.load().get("fontes") or {}).keys())
        for runtime in matriz.known_runtimes():
            for eixo in matriz.eixos():
                celula = matriz.capability(runtime, eixo["id"]) or {}
                if celula["status"] not in matriz.EXIGEM_FONTE:
                    continue
                assert celula.get("source") in fontes, (runtime, eixo["id"])

    def test_not_declared_nao_carrega_frase(self):
        """Celula `not_declared` com `quote` seria contradicao: a frase provaria
        que alguem declarou."""
        for runtime in matriz.known_runtimes():
            for eixo in matriz.eixos():
                celula = matriz.capability(runtime, eixo["id"]) or {}
                if celula["status"] != "not_declared":
                    continue
                assert not (celula.get("quote") or "").strip(), (runtime, eixo["id"])
                assert not celula.get("source"), (runtime, eixo["id"])

    def test_celula_sem_frase_explica_por_que(self):
        """`supported` sem `quote` e legitimo -- parte da matriz da AWS e tabela e
        nao sentenca --, mas tem de dizer isso em `nota`. Sem a nota, a celula e
        indistinguivel de uma que perdeu a citacao por descuido."""
        for runtime in matriz.known_runtimes():
            for eixo in matriz.eixos():
                celula = matriz.capability(runtime, eixo["id"]) or {}
                if celula["status"] not in matriz.EXIGEM_FONTE:
                    continue
                if matriz.citada(runtime, eixo["id"]):
                    continue
                assert (celula.get("nota") or "").strip(), (runtime, eixo["id"])

    def test_limites_estao_declarados(self):
        limites = matriz.limites_declarados()
        assert limites
        # O 6.0 tem de estar nomeado: ele existe, a pagina dele e vigiada por
        # `runtime-matrix.yaml`, e o que falta e leitura. Silenciar isso faria a
        # matriz parecer completa.
        assert any("6.0" in limite for limite in limites)


class TestYamlEProsaConcordam:
    def test_as_colunas_sao_os_runtimes_do_yaml(self):
        cabecalho, _ = _tabela_do_markdown()
        # A primeira coluna e o rotulo do eixo e nao um runtime.
        colunas = [c.replace("Glue", "").replace("*", "").strip() for c in cabecalho[1:]]
        assert colunas == list(matriz.known_runtimes())

    def test_toda_linha_da_tabela_tem_eixo_no_yaml(self):
        """A tabela markdown MISTURA duas coisas, e o YAML nao.

        Ela tem duas linhas de VERSAO DE COMPONENTE -- `Spark` e `Iceberg` -- ao
        lado das de capacidade. O YAML nao as carrega de proposito: versao de
        componente por runtime mora em `runtime-matrix.yaml`, e duplicar
        `Spark 3.5.6` num segundo arquivo criaria duas fontes de verdade para o
        mesmo numero. E a duplicacao que o cabecalho do proprio YAML recusa.

        Consequencia: este teste cobra que toda linha de CAPACIDADE case, e
        declara as duas de versao como esperadas do lado da prosa.
        """
        _, corpo = _tabela_do_markdown()
        titulos_do_yaml = {_normaliza(e["titulo"]) for e in matriz.eixos()}
        titulos_da_prosa = {_normaliza(rotulo) for rotulo, _ in corpo}
        assert titulos_da_prosa - titulos_do_yaml == VERSOES_SO_NA_PROSA
        assert titulos_do_yaml - titulos_da_prosa == set()

    def test_a_tabela_tem_uma_celula_por_runtime_em_cada_linha(self):
        _, corpo = _tabela_do_markdown()
        for rotulo, celulas in corpo:
            assert len(celulas) == len(matriz.known_runtimes()), rotulo


class TestVerbo:
    def test_matriz_inteira_sai_com_uma_linha_por_par(self):
        saida = _core.lakeformation_matrix()
        assert saida["status"] == "ok"
        esperado = len(matriz.known_runtimes()) * len(matriz.eixos())
        assert len(saida["rows"]) == esperado

    def test_filtro_por_runtime_e_eixo(self):
        saida = _core.lakeformation_matrix(runtime="5.1", axis="fgac_spark_native_write")
        assert len(saida["rows"]) == 1
        linha = saida["rows"][0]
        assert linha["glue_version"] == "5.1"
        assert linha["status"] == "supported"
        assert linha["quoted"] is True
        # A nota tem de dizer que a celula esta em conflito declarado: ela e a
        # unica da matriz que a §6 do documento de conhecimento nao fecha.
        assert "CONFLITO" in linha["note"]

    def test_runtime_fora_da_matriz_e_unresolved_nomeado(self):
        saida = _core.lakeformation_matrix(runtime="6.0")
        assert saida["status"] == "unresolved"
        assert saida["reason"] == "runtime_fora_da_matriz"
        assert saida["unblocked_by"]
        assert "6.0" not in saida["known_runtimes"]

    def test_eixo_desconhecido_e_unresolved_nomeado(self):
        saida = _core.lakeformation_matrix(axis="nao_existe")
        assert saida["status"] == "unresolved"
        assert saida["reason"] == "eixo_desconhecido"
        assert saida["known_axes"]

    def test_summary_omite_fonte_frase_e_nota(self):
        cheio = _core.lakeformation_matrix(runtime="5.1", detail_level="full")
        resumo = _core.lakeformation_matrix(runtime="5.1", detail_level="summary")
        assert any("quote" in linha for linha in cheio["rows"])
        assert all("quote" not in linha for linha in resumo["rows"])
        assert all("source" not in linha for linha in resumo["rows"])
        # `status` e `quoted` sobrevivem ao `summary`: eles sao o resultado, e
        # comprimir evidencia ate apagar o resultado nao e compressao.
        assert all(linha["status"] for linha in resumo["rows"])

    def test_a_contagem_de_evidencia_soma_com_as_linhas_que_a_pedem(self):
        saida = _core.lakeformation_matrix()
        evidencia = saida["evidence"]
        com_fonte = sum(
            1
            for linha in saida["rows"]
            if linha["status"] in matriz.EXIGEM_FONTE
        )
        assert evidencia["with_quote"] + evidencia["sourced_without_quote"] == com_fonte
        nao_declarados = sum(1 for linha in saida["rows"] if linha["status"] == "not_declared")
        assert evidencia["not_declared"] == nao_declarados

    def test_nao_publica_nenhuma_afirmacao_de_ganho(self):
        """A matriz descreve capacidade. Ela nao promete resultado, nao estima
        economia e nao pontua confianca -- mesmas tres recusas que a tool de
        arbitragem declara."""
        import json

        texto = json.dumps(_core.lakeformation_matrix(), ensure_ascii=False).lower()
        for proibido in ("economiz", "ganho de", "expected_gain", "confidence_score"):
            assert proibido not in texto, proibido


@pytest.mark.parametrize("runtime", ["4.0", "5.0", "5.1"])
def test_o_filesystem_default_e_a_celula_que_muda_no_51(runtime):
    """A troca de EMRFS por S3A e o breaking change que quebra CALADO, e a matriz
    tem de dizer isso sem que ninguem leia prosa."""
    celula = matriz.capability(runtime, "filesystem_s3_default")
    esperado = {"4.0": "EMRFS", "5.0": "EMRFS", "5.1": "S3A"}[runtime]
    assert celula["valor"] == esperado
