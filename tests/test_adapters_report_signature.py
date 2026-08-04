"""`report sign` e `report verify` nos tres adaptadores.

O que cada grupo trava, e por que:

- o bloco fica FORA do corpo que cobre, e assinar duas vezes devolve o mesmo
  arquivo -- sem isso a segunda assinatura hashearia a primeira;
- `verify` NOMEIA qual das tres partes divergiu (criterio 8 do spec da Fase 4b),
  e cobre tambem bloco ausente e bloco malformado, que sao estados diferentes de
  "nao corresponde";
- o texto do bloco diz que prova correspondencia e NAO autoria (criterio 9);
- os tres adaptadores (CLI, `_core`, tool MCP) chegam ao mesmo lugar.
"""
import json

import pytest

from sparkforge.adapters import _core
from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import call_tool
from sparkforge.findings.signature import SIGNATURE_RE

BODY = """# Relatorio de Performance

## 1. Resumo executivo

- Gargalo dominante: escrita com coalesce(1)
- Impacto atual: 40% do runtime

## 6. Recomendacoes

    df.write.parquet(dest)
"""


def _findings(tmp_path, **overrides):
    finding = {
        "rule_id": "SF-PY-005",
        "schema_version": 1,
        "catalog_version": 1,
        "title": "coalesce(1)",
        "severity": "P0",
        "confidence": "high",
        "status": "structural",
        "subject": {"type": "source_location", "file": "loader.py", "line": 2},
        "evidence": ["f_4f6c65", "f_aaa111"],
    }
    finding.update(overrides)
    path = tmp_path / "findings.json"
    path.write_text(json.dumps([finding]), encoding="utf-8")
    return str(path)


def _report(tmp_path, body=BODY, name="relatorio.md"):
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return str(path)


class TestOBlocoFicaForaDoCorpoQueEleCobre:
    def test_assinar_acrescenta_o_bloco_delimitado_no_fim(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        text = (tmp_path / "relatorio.md").read_text(encoding="utf-8")
        assert text.count("<!-- sparkforge:signature -->") == 1
        assert text.rstrip().endswith("<!-- /sparkforge:signature -->")
        assert text.index("## 6. Recomendacoes") < text.index("<!-- sparkforge:signature -->")

    def test_a_assinatura_do_arquivo_e_a_do_corpo_sem_o_bloco(self, tmp_path):
        """O bloco nao entra no hash que ele mesmo carrega: a assinatura escrita
        no arquivo e exatamente a do corpo cru, calculada antes de existir."""
        from sparkforge.findings.signature import compute_signature

        report = _report(tmp_path)
        payload = _core.report_sign(report, _findings(tmp_path))
        assert payload["signature"] == compute_signature(
            BODY, ["f_4f6c65", "f_aaa111"], ["SF-PY-005"], 1, 1
        )

    def test_assinar_duas_vezes_devolve_o_mesmo_arquivo(self, tmp_path):
        report = _report(tmp_path)
        primeira = _core.report_sign(report, _findings(tmp_path))
        texto_um = (tmp_path / "relatorio.md").read_text(encoding="utf-8")
        segunda = _core.report_sign(report, _findings(tmp_path))
        texto_dois = (tmp_path / "relatorio.md").read_text(encoding="utf-8")
        assert primeira["signature"] == segunda["signature"]
        assert texto_um == texto_dois

    def test_reassinar_um_relatorio_editado_produz_assinatura_nova_e_valida(self, tmp_path):
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        antes = _core.report_sign(report, findings)["signature"]
        corpo, _bloco, _ = _core._split_report(
            (tmp_path / "relatorio.md").read_text(encoding="utf-8")
        )
        (tmp_path / "relatorio.md").write_text(corpo + "\nlinha nova\n", encoding="utf-8")
        depois = _core.report_sign(report, findings)["signature"]
        assert antes != depois
        assert _core.report_verify(report, findings)["valid"]

    def test_conteudo_depois_do_bloco_e_recusado_em_vez_de_ignorado(self, tmp_path):
        """Ignorar abriria a porta que a assinatura fecha: um paragrafo apendado
        ao fim do arquivo que nenhuma assinatura cobre e que o leitor le como
        parte do relatorio verificado."""
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        _core.report_sign(report, findings)
        path = tmp_path / "relatorio.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\nP.S. o ganho foi de 90%.\n",
            encoding="utf-8",
        )
        with pytest.raises(_core.AdapterError) as exc:
            _core.report_sign(report, findings)
        assert "depois do bloco" in str(exc.value)

    def test_um_relatorio_com_o_bloco_vazio_do_template_assina(self, tmp_path):
        """O template ja carrega os delimitadores vazios; assinar precisa
        preenche-los, nunca duplica-los."""
        report = _report(
            tmp_path,
            body=BODY + "\n<!-- sparkforge:signature -->\n<!-- /sparkforge:signature -->\n",
        )
        _core.report_sign(report, _findings(tmp_path))
        text = (tmp_path / "relatorio.md").read_text(encoding="utf-8")
        assert text.count("<!-- sparkforge:signature -->") == 1
        assert _core.report_verify(report, _findings(tmp_path))["valid"]


class TestOTextoDoBlocoDeclaraOLimite:
    def test_o_bloco_diz_correspondencia_e_nega_autoria(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        text = (tmp_path / "relatorio.md").read_text(encoding="utf-8").lower()
        assert "correspondência" in text
        assert "não autoria" in text
        assert "não há chave" in text

    def test_o_bloco_carrega_a_assinatura_inteira_de_64_hex(self, tmp_path):
        report = _report(tmp_path)
        payload = _core.report_sign(report, _findings(tmp_path))
        assert SIGNATURE_RE.match(payload["signature"])
        assert f"- assinatura: {payload['signature']}" in (
            tmp_path / "relatorio.md"
        ).read_text(encoding="utf-8")

    def test_o_bloco_diz_como_verificar(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        text = (tmp_path / "relatorio.md").read_text(encoding="utf-8")
        assert "sparkforge report verify" in text

    def test_o_payload_tambem_carrega_o_limite(self, tmp_path):
        """Quem consome pelo MCP nunca le o markdown: se o limite so estivesse no
        arquivo, o cliente veria um hash sem a frase que o qualifica."""
        payload = _core.report_sign(_report(tmp_path), _findings(tmp_path))
        assert "autoria" in payload["proves"]


class TestVerifyNomeiaAParteQueDivergiu:
    def test_relatorio_intacto_corresponde(self, tmp_path):
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        _core.report_sign(report, findings)
        resultado = _core.report_verify(report, findings)
        assert resultado["valid"]
        assert resultado["status"] == "signed"
        assert resultado["diverged"] == []

    def test_reformatar_o_corpo_nao_invalida(self, tmp_path):
        """A fronteira que `normalize_body` define, vista do verbo: espaco no fim
        da linha e linha em branco a mais nao sao edicao de conteudo."""
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        _core.report_sign(report, findings)
        path = tmp_path / "relatorio.md"
        corpo, bloco, _ = _core._split_report(path.read_text(encoding="utf-8"))
        path.write_text(
            corpo.replace("\n\n", "\n\n\n").replace("(1)", "(1)   ") + bloco + "\n",
            encoding="utf-8",
        )
        assert _core.report_verify(report, findings)["valid"]

    def test_editar_o_corpo_diverge_no_corpo(self, tmp_path):
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        _core.report_sign(report, findings)
        path = tmp_path / "relatorio.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("40%", "90%"), encoding="utf-8"
        )
        resultado = _core.report_verify(report, findings)
        assert resultado["valid"] is False
        assert resultado["diverged"] == ["body"]
        assert "corpo" in resultado["reason"]

    def test_mudar_a_indentacao_diverge_no_corpo(self, tmp_path):
        """`normalize_body` preserva recuo de proposito: em Markdown ele decide se
        a linha e bloco de codigo ou prosa."""
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        _core.report_sign(report, findings)
        path = tmp_path / "relatorio.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "    df.write.parquet(dest)", " df.write.parquet(dest)"
            ),
            encoding="utf-8",
        )
        assert _core.report_verify(report, findings)["diverged"] == ["body"]

    def test_trocar_a_evidencia_diverge_na_evidencia_e_nao_no_corpo(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        outros = _findings(tmp_path, evidence=["f_ccc333"])
        resultado = _core.report_verify(report, outros)
        assert resultado["valid"] is False
        assert resultado["diverged"] == ["evidence"]
        assert resultado["checks"]["body"]["ok"] is True
        assert "f_ccc333" in resultado["checks"]["evidence"]["detail"]

    def test_trocar_a_regra_diverge_na_evidencia(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        resultado = _core.report_verify(report, _findings(tmp_path, rule_id="SF-PY-007"))
        assert resultado["diverged"] == ["evidence"]
        assert "SF-PY-007" in resultado["checks"]["evidence"]["detail"]

    def test_trocar_o_catalogo_diverge_no_catalogo(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        resultado = _core.report_verify(report, _findings(tmp_path, catalog_version=2))
        assert resultado["valid"] is False
        assert resultado["diverged"] == ["catalog"]
        assert "catalog_version" in resultado["checks"]["catalog"]["detail"]

    def test_trocar_o_schema_version_diverge_no_catalogo(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        resultado = _core.report_verify(report, _findings(tmp_path, schema_version=2))
        assert resultado["diverged"] == ["catalog"]

    def test_duas_partes_divergentes_aparecem_as_duas(self, tmp_path):
        """`verify` nao para na primeira: um relatorio editado E rejulgado tem
        dois problemas, e reportar so um mandaria o leitor consertar metade."""
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        path = tmp_path / "relatorio.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("40%", "90%"), encoding="utf-8"
        )
        resultado = _core.report_verify(report, _findings(tmp_path, catalog_version=2))
        assert resultado["diverged"] == ["catalog", "body"]

    def test_a_ordem_de_diverged_e_fixa(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        path = tmp_path / "relatorio.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("40%", "90%"), encoding="utf-8"
        )
        resultado = _core.report_verify(
            report, _findings(tmp_path, catalog_version=2, evidence=["f_ccc333"])
        )
        assert resultado["diverged"] == ["evidence", "catalog", "body"]

    def test_expected_signature_e_a_que_reassinar_produziria(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        outros = _findings(tmp_path, evidence=["f_ccc333"])
        esperada = _core.report_verify(report, outros)["expected_signature"]
        assert _core.report_sign(report, outros)["signature"] == esperada


class TestBlocoAusenteEBlocoMalformado:
    def test_bloco_ausente_nao_e_o_mesmo_que_divergente(self, tmp_path):
        """Relatorio sem bloco nao e relatorio adulterado. Confundir os dois faria
        o leitor desconfiar do texto errado."""
        resultado = _core.report_verify(_report(tmp_path), _findings(tmp_path))
        assert resultado["valid"] is False
        assert resultado["status"] == "missing_block"
        assert resultado["diverged"] == []
        assert "sparkforge report sign" in resultado["reason"]

    def test_delimitador_de_abertura_sem_fechamento(self, tmp_path):
        report = _report(tmp_path, body=BODY + "\n<!-- sparkforge:signature -->\n")
        resultado = _core.report_verify(report, _findings(tmp_path))
        assert resultado["status"] == "malformed_block"
        assert resultado["valid"] is False

    def test_dois_blocos_no_mesmo_arquivo(self, tmp_path):
        bloco = "<!-- sparkforge:signature -->\n<!-- /sparkforge:signature -->\n"
        report = _report(tmp_path, body=BODY + bloco + bloco)
        assert _core.report_verify(report, _findings(tmp_path))["status"] == (
            "malformed_block"
        )

    def test_fechamento_antes_da_abertura(self, tmp_path):
        report = _report(
            tmp_path,
            body=BODY + "<!-- /sparkforge:signature -->\n<!-- sparkforge:signature -->\n",
        )
        assert _core.report_verify(report, _findings(tmp_path))["status"] == (
            "malformed_block"
        )

    def test_bloco_sem_a_linha_da_assinatura(self, tmp_path):
        report = _report(
            tmp_path,
            body=BODY
            + "<!-- sparkforge:signature -->\n- fact_ids: f_aaa111\n"
            "<!-- /sparkforge:signature -->\n",
        )
        resultado = _core.report_verify(report, _findings(tmp_path))
        assert resultado["status"] == "malformed_block"
        assert "assinatura" in resultado["reason"]

    def test_assinatura_truncada_e_malformada_e_nao_divergente(self, tmp_path):
        """`SIGNATURE_RE` e a unica verdade de forma. Uma assinatura de 16 hex --
        o que o plano da Task 5 mostrava -- e bloco malformado, nao divergencia."""
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        path = tmp_path / "relatorio.md"
        texto = path.read_text(encoding="utf-8")
        linha = next(ln for ln in texto.splitlines() if ln.startswith("- assinatura: "))
        path.write_text(texto.replace(linha, linha[: len("- assinatura: sig_") + 16]),
                        encoding="utf-8")
        resultado = _core.report_verify(report, _findings(tmp_path))
        assert resultado["status"] == "malformed_block"
        assert "64 hex" in resultado["reason"]

    def test_bloco_sem_a_linha_de_catalogo(self, tmp_path):
        report = _report(tmp_path)
        _core.report_sign(report, _findings(tmp_path))
        path = tmp_path / "relatorio.md"
        path.write_text(
            "\n".join(
                ln
                for ln in path.read_text(encoding="utf-8").splitlines()
                if not ln.startswith("- catalog_version:")
            ),
            encoding="utf-8",
        )
        assert _core.report_verify(report, _findings(tmp_path))["status"] == (
            "malformed_block"
        )

    def test_editar_os_ids_declarados_no_bloco_invalida(self, tmp_path):
        """O bloco mora fora do hash, entao ele e editavel -- e por isso o veredito
        nunca sai dele. Trocar um fact_id declarado quebra a assinatura."""
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        _core.report_sign(report, findings)
        path = tmp_path / "relatorio.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "- fact_ids: f_4f6c65, f_aaa111", "- fact_ids: f_4f6c65, f_ccc333"
            ),
            encoding="utf-8",
        )
        resultado = _core.report_verify(report, findings)
        assert resultado["valid"] is False
        assert "evidence" in resultado["diverged"]
        assert "body" in resultado["diverged"]


class TestDeOndeVemOsDadosDaAssinatura:
    def test_os_quatro_campos_saem_do_arquivo_de_findings(self, tmp_path):
        payload = _core.report_sign(_report(tmp_path), _findings(tmp_path))
        assert payload["fact_ids"] == ["f_4f6c65", "f_aaa111"]
        assert payload["rule_ids"] == ["SF-PY-005"]
        assert payload["catalog_version"] == 1
        assert payload["schema_version"] == 1

    def test_findings_vazio_e_recusado(self, tmp_path):
        path = tmp_path / "findings.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(_core.AdapterError) as exc:
            _core.report_sign(_report(tmp_path), str(path))
        assert "sparkforge judge" in str(exc.value)

    def test_finding_sem_evidencia_e_recusado_nomeando_o_campo(self, tmp_path):
        with pytest.raises(_core.AdapterError) as exc:
            _core.report_sign(_report(tmp_path), _findings(tmp_path, evidence=[]))
        assert "evidence" in str(exc.value)

    def test_catalog_version_divergente_e_recusado_em_vez_de_escolhido(self, tmp_path):
        """`compute_signature` recebe UM inteiro; escolher um dos dois faria a
        assinatura afirmar um catalogo que nao foi o unico usado."""
        path = tmp_path / "findings.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "rule_id": "SF-PY-005",
                        "evidence": ["f_aaa111"],
                        "catalog_version": 1,
                        "schema_version": 1,
                    },
                    {
                        "rule_id": "SF-PY-007",
                        "evidence": ["f_bbb222"],
                        "catalog_version": 2,
                        "schema_version": 1,
                    },
                ]
            ),
            encoding="utf-8",
        )
        with pytest.raises(_core.AdapterError) as exc:
            _core.report_sign(_report(tmp_path), str(path))
        assert "divergente" in str(exc.value)
        assert "1, 2" in str(exc.value)

    def test_findings_inexistente_manda_rodar_judge(self, tmp_path):
        with pytest.raises(_core.AdapterError) as exc:
            _core.report_sign(_report(tmp_path), str(tmp_path / "nao-existe.json"))
        assert "sparkforge judge" in str(exc.value)

    def test_relatorio_inexistente_manda_partir_do_template(self, tmp_path):
        with pytest.raises(_core.AdapterError) as exc:
            _core.report_sign(str(tmp_path / "nao-existe.md"), _findings(tmp_path))
        assert "performance-report.md" in str(exc.value)


class TestOsDoisVerbosNosTresAdaptadores:
    def test_a_cli_assina_e_verifica(self, tmp_path, capsys):
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        assert main(["report", "sign", "--report", report, "--findings", findings]) == 0
        assinado = json.loads(capsys.readouterr().out)
        assert SIGNATURE_RE.match(assinado["signature"])
        assert main(["report", "verify", "--report", report, "--findings", findings]) == 0
        assert json.loads(capsys.readouterr().out)["valid"] is True

    def test_a_cli_sai_com_codigo_1_quando_nao_corresponde(self, tmp_path, capsys):
        report = _report(tmp_path)
        findings = _findings(tmp_path)
        main(["report", "sign", "--report", report, "--findings", findings])
        capsys.readouterr()
        path = tmp_path / "relatorio.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("40%", "90%"), encoding="utf-8"
        )
        assert main(["report", "verify", "--report", report, "--findings", findings]) == 1
        assert json.loads(capsys.readouterr().out)["diverged"] == ["body"]

    def test_a_cli_devolve_2_quando_o_arquivo_nao_existe(self, tmp_path, capsys):
        code = main(
            [
                "report",
                "verify",
                "--report",
                str(tmp_path / "nao-existe.md"),
                "--findings",
                _findings(tmp_path),
            ]
        )
        assert code == 2
        assert "sparkforge report sign" in capsys.readouterr().err

    def test_a_tool_mcp_assina_e_verifica(self, tmp_path):
        args = {
            "report_path": _report(tmp_path),
            "findings_path": _findings(tmp_path),
        }
        assinado = call_tool("sparkforge_report_sign", args)
        assert SIGNATURE_RE.match(assinado["signature"])
        assert call_tool("sparkforge_report_verify", args)["valid"] is True

    def test_a_tool_mcp_devolve_erro_estruturado_em_vez_de_excecao(self, tmp_path):
        resultado = call_tool(
            "sparkforge_report_verify",
            {"report_path": str(tmp_path / "x.md"), "findings_path": "y.json"},
        )
        assert resultado["exit_code"] == 2
        assert "sparkforge" in resultado["error"]

    def test_os_tres_adaptadores_produzem_a_mesma_assinatura(self, tmp_path):
        """CLI, `_core` e tool MCP so podem divergir se alguem duplicar logica --
        e o unico lugar onde isso importa e o valor que vai no relatorio."""
        pelo_core = _core.report_sign(
            _report(tmp_path, name="a.md"), _findings(tmp_path)
        )["signature"]
        pela_tool = call_tool(
            "sparkforge_report_sign",
            {
                "report_path": _report(tmp_path, name="b.md"),
                "findings_path": _findings(tmp_path),
            },
        )["signature"]
        assert pelo_core == pela_tool


class TestOTemplateCarregaOBloco:
    def test_o_template_declara_onde_o_bloco_mora(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        texto = (root / "templates" / "performance-report.md").read_text(encoding="utf-8")
        assert "<!-- sparkforge:signature -->" in texto
        assert "<!-- /sparkforge:signature -->" in texto
        assert "sparkforge report sign" in texto
        assert texto.rstrip().endswith("<!-- /sparkforge:signature -->")

    def test_o_template_assina_como_esta(self, tmp_path):
        """O template e o ponto de partida real: se ele nao assinasse, o bloco
        seria decoracao que ninguem consegue usar."""
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        report = _report(
            tmp_path,
            body=(root / "templates" / "performance-report.md").read_text(encoding="utf-8"),
        )
        _core.report_sign(report, _findings(tmp_path))
        assert _core.report_verify(report, _findings(tmp_path))["valid"]
