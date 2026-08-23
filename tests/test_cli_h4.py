"""As duas entradas de CLI cujo motor ja existia.

Nenhuma constroi julgamento novo: `dependency-audit` le `mig.python_dep` e
`mig.jar_binary` -- que ja carregam `major` e `scala_minor` -- e julga com o
catalogo; `iceberg assess-upgrade` consulta a matriz de suporte de feature.
"""
import json

import pytest

from sparkforge.adapters.cli import main

JOB = "import com.amazonaws.services.s3.AmazonS3\n"
REQS = "pyarrow==8.0.0\npandas==1.5.3\n"
INVENTARIO = "consumers:\n  - table: db.t\n    service: {servico}\n"


def _job(tmp_path, com_inventario=None):
    (tmp_path / "job.py").write_text(JOB, encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(REQS, encoding="utf-8")
    if com_inventario:
        pasta = tmp_path / ".sparkforge"
        pasta.mkdir()
        (pasta / "consumers.yaml").write_text(
            INVENTARIO.format(servico=com_inventario), encoding="utf-8"
        )
    return tmp_path


class TestDependencyAudit:
    def test_lista_o_pin_observado_e_o_runtime_que_julgou(self, tmp_path, capsys):
        codigo = main(["glue", "dependency-audit", str(_job(tmp_path)), "--glue", "6.0"])
        saida = json.loads(capsys.readouterr().out)

        assert codigo == 0
        pins = {d["name"]: d for d in saida["dependencies"] if d["kind"] == "mig.python_dep"}
        assert "pyarrow" in pins and pins["pyarrow"]["attrs"]["version"] == "8.0.0"
        # O runtime aparece porque e ele que decide quais regras avaliaram.
        assert saida["runtime"]["glue"] == "6.0"

    def test_o_julgamento_vem_do_catalogo_nao_do_comando(self, tmp_path, capsys):
        main(["glue", "dependency-audit", str(_job(tmp_path)), "--glue", "6.0"])
        saida = json.loads(capsys.readouterr().out)
        # `pyarrow==8.0.0` esta abaixo do piso que SF-SPARK4-003 declara.
        assert "SF-SPARK4-003" in {f["rule_id"] for f in saida["findings"]}

    def test_sem_versao_de_runtime_o_comando_recusa(self, tmp_path):
        with pytest.raises(SystemExit):
            main(["glue", "dependency-audit", str(_job(tmp_path))])

    def test_diretorio_inexistente_devolve_erro_e_nao_estoura(self, tmp_path, capsys):
        # Convencao da CLI: erro operacional vai para stderr com codigo != 0, e
        # stdout NAO recebe um JSON de erro que um pipeline leria como resposta.
        codigo = main(
            ["glue", "dependency-audit", str(tmp_path / "nao-existe"), "--glue", "6.0"]
        )
        capturado = capsys.readouterr()
        assert codigo != 0
        assert capturado.out.strip() == ""
        assert "nao encontrado" in capturado.err


class TestIcebergAssessUpgrade:
    def test_consumidor_sem_suporte_bloqueia(self, tmp_path, capsys):
        alvo = _job(tmp_path, com_inventario="athena")
        codigo = main(["iceberg", "assess-upgrade", str(alvo), "--from", "2", "--to", "3"])
        saida = json.loads(capsys.readouterr().out)

        assert codigo == 0
        assert saida["verdict"] == "BLOCKED"
        assert saida["consumers"] == ["athena"]
        assert any(c["status"] == "UNSUPPORTED" and c["source"] for c in saida["cells"])

    def test_consumidor_sem_fonte_devolve_unresolved(self, tmp_path, capsys):
        alvo = _job(tmp_path, com_inventario="pyiceberg")
        main(["iceberg", "assess-upgrade", str(alvo), "--from", "2", "--to", "3"])
        saida = json.loads(capsys.readouterr().out)
        assert saida["verdict"] == "UNRESOLVED"
        assert saida["unresolved"]

    def test_sem_inventario_nao_responde_seguro(self, tmp_path, capsys):
        main(["iceberg", "assess-upgrade", str(_job(tmp_path)), "--from", "2", "--to", "3"])
        saida = json.loads(capsys.readouterr().out)
        assert saida["verdict"] == "UNRESOLVED"

    def test_alvo_anterior_a_origem_e_recusado(self, tmp_path, capsys):
        codigo = main(
            ["iceberg", "assess-upgrade", str(_job(tmp_path)), "--from", "3", "--to", "2"]
        )
        capturado = capsys.readouterr()
        assert codigo != 0
        assert "nao e upgrade" in capturado.err
