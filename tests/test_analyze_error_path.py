"""Os dois verbos que faltavam para o erro sair do golden e chegar ao operador.

MEDIDO em 2026-09-09, antes desta entrega: `extract_cloudwatch_logs_tree` era
referenciado por `scripts/regen_fixtures.py` e mais nada. Existia
`collect cloudwatch-logs` (a coleta) e existia o golden (a prova), e no meio
nao existia verbo nenhum -- um operador que baixasse o log precisava do corpus
de fixture para ver o fact. Era a lacuna D-4 da frente de stacktrace.

## Por que DOIS verbos, e nao um

`analyze cloudwatch-logs` LE ARTEFATO. `analyze error-signatures` NAO le: e
derivacao pura sobre a UNIAO dos facts, no molde de `analyze call-graph`.

Juntar os dois pareceria conveniencia e seria defeito, e a razao esta na forma
da RECUSA. `build_signature_matches` recusa por ESCOPO -- um
`error.signature.unresolved` por (run, log group) e um por excecao que nao
casou. Rodando o matcher dentro do verbo do log, uma excecao do event log
ausente daquele arquivo nao produziria recusa nenhuma: o ponto cego sumiria em
silencio, que e exatamente o que a recusa nomeada existe para impedir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.adapters import _core
from sparkforge.adapters._core import AdapterError

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "fixtures" / "cloudwatch_logs"
QUATRO = CORPUS / "quatro_assinaturas_de_log" / "input"
SEM_CREDENCIAL = CORPUS / "sem_credencial" / "input"
CREDENCIAL_NA_LINHA = CORPUS / "linha_com_credencial" / "input"


def _kinds(resultado: dict) -> dict[str, int]:
    return resultado["by_kind"]


class TestAnalyzeCloudwatchLogs:
    def test_le_o_diretorio_inteiro(self):
        """Arquivo OU diretorio, e o diretorio e o caso comum: o coletor grava
        um artefato por (job, run, log group), e quem baixou `error` e `output`
        do mesmo run tem dois."""
        resultado = _core.analyze_cloudwatch_logs(str(QUATRO), limit=None)
        assert _kinds(resultado)["cloudwatch.log_event"] == 5
        assert _kinds(resultado)["cloudwatch.logs.analyzed"] == 1

    def test_le_um_arquivo_so(self):
        artefato = next(QUATRO.glob("*.json"))
        resultado = _core.analyze_cloudwatch_logs(str(artefato), limit=None)
        assert _kinds(resultado)["cloudwatch.log_event"] == 5

    def test_a_recusa_do_coletor_chega_ate_o_verbo(self):
        """`sem_credencial` e o estado em que a requisicao NUNCA SAIU, e ele nao
        pode chegar aqui como lista vazia: os quatro estados de recusa produzem
        a mesma lista de eventos, e so a razao os separa."""
        resultado = _core.analyze_cloudwatch_logs(str(SEM_CREDENCIAL), limit=None)
        assert _kinds(resultado).get("cloudwatch.logs.unresolved") == 1
        recusa = [
            i for i in resultado["items"] if i["kind"] == "cloudwatch.logs.unresolved"
        ][0]
        assert recusa["attrs"]["reason"] == "sem_credencial"

    def test_a_linha_com_segredo_chega_REDIGIDA(self):
        """A amarra da redacao, cobrada no verbo e nao so no extrator: e por
        aqui que a linha sai para o operador e para o `--out` commitado."""
        resultado = _core.analyze_cloudwatch_logs(str(CREDENCIAL_NA_LINHA), limit=None)
        redigidas = [
            i
            for i in resultado["items"]
            if i["kind"] == "cloudwatch.log_event" and i["attrs"].get("redacted")
        ]
        assert redigidas, "a fixture existe para exercitar a redacao"
        for linha in redigidas:
            assert linha["attrs"]["message"] == "<redigido>"

    def test_caminho_inexistente_recusa_com_o_comando_que_produz_o_artefato(self):
        with pytest.raises(AdapterError) as erro:
            _core.analyze_cloudwatch_logs(str(ROOT / "nao_existe_nenhum_lugar"))
        assert "collect" in str(erro.value) and "cloudwatch-logs" in str(erro.value)


class TestAnalyzeErrorSignatures:
    def _facts_do_log(self, tmp_path: Path, entrada: Path) -> Path:
        resultado = _core.analyze_cloudwatch_logs(str(entrada), limit=None)
        destino = tmp_path / "facts.json"
        destino.write_text(
            json.dumps(resultado["items"], ensure_ascii=False), encoding="utf-8"
        )
        return destino

    def test_casa_as_quatro_de_mensagem_pelo_caminho_de_log(self, tmp_path):
        caminho = self._facts_do_log(tmp_path, QUATRO)
        resultado = _core.analyze_error_signatures(str(caminho), limit=None)
        casados = {
            i["attrs"]["signature_id"]
            for i in resultado["items"]
            if i["kind"] == "error.signature_match"
        }
        assert casados == {"ERR-ATH-001", "ERR-GLUE-001", "ERR-ICE-001", "ERR-LF-001"}

    def test_matched_on_diz_por_qual_porta_a_assinatura_entrou(self, tmp_path):
        caminho = self._facts_do_log(tmp_path, QUATRO)
        resultado = _core.analyze_error_signatures(str(caminho), limit=None)
        portas = {
            i["attrs"]["matched_on"]
            for i in resultado["items"]
            if i["kind"] == "error.signature_match"
        }
        assert portas == {"log_line"}

    def test_a_recusa_e_por_ESCOPO_e_nao_por_linha(self, tmp_path):
        """O ponto cego de um log de N linhas sem assinatura nenhuma e UM, nao
        N. E e essa forma de recusa que impede o matcher de morar dentro do
        verbo do log."""
        caminho = self._facts_do_log(
            tmp_path, CORPUS / "nenhuma_assinatura_no_log" / "input"
        )
        resultado = _core.analyze_error_signatures(str(caminho), limit=None)
        recusas = [
            i for i in resultado["items"] if i["kind"] == "error.signature.unresolved"
        ]
        assert len(recusas) == 1
        assert recusas[0].get("measures", {}).get("lines_examined", 0) > 1
        assert recusas[0]["attrs"]["reason"] == "nenhuma_assinatura_casou_no_log"

    def test_NAO_devolve_juizo(self):
        """`confidence=0.98` morreu na T2 e nao volta por este verbo. O que ele
        emite e fato; `likely_causes`, `fixes` e `diagnostic_steps` sao das
        regras `SF-ERR-*`."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            caminho = self._facts_do_log(Path(tmp), QUATRO)
            resultado = _core.analyze_error_signatures(str(caminho), limit=None)
        for item in resultado["items"]:
            for proibido in ("confidence", "fixes", "likely_causes", "diagnostic_steps"):
                assert proibido not in item["attrs"], (item["kind"], proibido)

    def test_arquivo_de_facts_inexistente_nomeia_os_DOIS_produtores(self, tmp_path):
        """A mensagem de erro precisa dizer de onde vem cada metade da uniao --
        um operador que so conhece o event log fica sem o log do CloudWatch, e e
        justamente essa metade que destrava as quatro assinaturas de mensagem."""
        with pytest.raises(AdapterError) as erro:
            _core.analyze_error_signatures(str(tmp_path / "nao_existe.json"))
        texto = str(erro.value)
        assert "analyze event-log" in texto
        assert "analyze cloudwatch-logs" in texto


class TestAsDuasTools:
    def test_estao_declaradas_e_despachaveis(self):
        from sparkforge.adapters import tools

        novas = {
            "sparkforge_analyze_cloudwatch_logs",
            "sparkforge_analyze_error_signatures",
        }
        assert novas <= set(tools.TOOLS)
        assert novas <= set(tools._HANDLERS)

    def test_as_duas_sao_LEITURA(self):
        """Nenhuma das duas escreve artefato nem sai para a rede: uma le o
        artefato que o coletor ja gravou, a outra deriva sobre facts."""
        from sparkforge.adapters.tools import TOOLS

        for nome in (
            "sparkforge_analyze_cloudwatch_logs",
            "sparkforge_analyze_error_signatures",
        ):
            anotacoes = TOOLS[nome]["annotations"]
            assert anotacoes["readOnlyHint"] is True, nome
            assert anotacoes["openWorldHint"] is False, nome

    def test_a_descricao_da_tool_de_assinaturas_declara_a_UNIAO(self):
        """A recusa mora na descricao, e um teste a varre: alimentar a tool com
        metade dos facts nao devolve metade das respostas."""
        from sparkforge.adapters.tools import TOOLS

        descricao = TOOLS["sparkforge_analyze_error_signatures"]["description"]
        assert "UNIAO" in descricao or "UNIÃO" in descricao
        assert "confidence" in descricao
