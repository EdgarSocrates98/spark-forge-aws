"""`forge migrate glue` julga com o catalogo `SF-MIG`, nao por substring.

O comando existia desde a vNext e rodava `GlueMigrationAnalyzer`:
correspondencia de substring, sem fonte, sem `runtime_scope`, com
`--to` default `"5.1"` fixado no codigo. Enquanto ele foi assim, as regras
`SF-MIG`, `SF-SPARK4` e `SF-LF` -- catalogadas, versionadas e com fonte --
so eram alcancaveis por quem chamasse `assess()` em Python. Este arquivo
prova a religacao: a porta de entrada publicada passa pelo mesmo motor.

DECISAO REGISTRADA -- o comando aceita DIRETORIO **ou** ARQUIVO.

A interface publicada aceitava um `.py`, e quebra-la em silencio seria
trocar um defeito por outro. Aceitar os dois nao e concessao: e a convencao
que todo verbo de `sparkforge/adapters/_core.py` ja segue (`is_dir()` chama
o extrator de arvore, arquivo chama o de caminho) e ela existe porque uma
migracao de Glue e julgada sobre o CONJUNTO de artefatos do job -- codigo,
`requirements*.txt` e `.jar` --, que so um diretorio carrega. Um `.py`
sozinho continua respondido, com menos evidencia, e isso aparece no
resultado em vez de virar silencio.

A quebra deliberada e outra, e e o ponto da mudanca: `--from` e `--to`
passam a ser OBRIGATORIOS. O default `"5.1"` fixado no codigo respondia
sobre um alvo que ninguem pediu, e essa e exatamente a classe de defeito
que este repositorio persegue.
"""
import json

import pytest

from sparkforge.cli.forge import main


def _job(raiz):
    (raiz / "job.py").write_text(
        "import com.amazonaws.services.s3.AmazonS3\n", encoding="utf-8"
    )
    return raiz


class TestOMotorDeRegras:
    def test_o_comando_usa_o_motor_de_regras_e_nao_o_analisador_antigo(
        self, tmp_path, capsys
    ):
        _job(tmp_path)
        codigo = main(["migrate", "glue", str(tmp_path), "--from", "4.0", "--to", "6.0"])
        saida = json.loads(capsys.readouterr().out)

        assert codigo == 0
        assert saida["source_runtime"] == "4.0" and saida["target_runtime"] == "6.0"
        assert "SF-MIG-001" in {f["rule_id"] for f in saida["findings"]}
        assert saida["gates"]["dados"] == "BLOCKED"
        assert saida["report"], "o relatorio deduplicado precisa sair junto"

    def test_o_caminho_atravessa_os_degraus_intermediarios(self, tmp_path, capsys):
        """`assess()` expande o par em degraus; um comando que julgasse so a
        ponta esconderia o breaking change do meio."""
        _job(tmp_path)
        main(["migrate", "glue", str(tmp_path), "--from", "4.0", "--to", "6.0"])
        saida = json.loads(capsys.readouterr().out)

        assert [tuple(s) for s in saida["steps"]] == [
            ("4.0", "5.0"),
            ("5.0", "5.1"),
            ("5.1", "6.0"),
        ]

    def test_o_eixo_que_nao_foi_avaliado_sai_nomeado(self, tmp_path, capsys):
        """Gate sem evidencia e BLOCKED com o motivo, nunca PASS calado."""
        _job(tmp_path)
        main(["migrate", "glue", str(tmp_path), "--from", "4.0", "--to", "5.1"])
        saida = json.loads(capsys.readouterr().out)

        assert set(saida["missing_evidence"]) >= {"dados", "performance", "custo", "canary"}
        assert all(texto.strip() for texto in saida["missing_evidence"].values())


class TestDiretorioOuArquivo:
    def test_o_diretorio_junta_codigo_e_dependencia_pinada(self, tmp_path, capsys):
        """A razao de aceitar diretorio: `requirements.txt` e `.jar` nao tem
        linha de fonte Python, e o analisador antigo, que lia um `.py` por vez,
        nunca os via. `SF-SPARK4-003` julga o pin de PyArrow, e o pin sobrevive
        a troca de runtime justamente por morar fora dele."""
        _job(tmp_path)
        (tmp_path / "requirements.txt").write_text("pyarrow==14.0.0\n", encoding="utf-8")
        main(["migrate", "glue", str(tmp_path), "--from", "4.0", "--to", "6.0"])
        pelo_diretorio = json.loads(capsys.readouterr().out)

        main(["migrate", "glue", str(tmp_path / "job.py"), "--from", "4.0", "--to", "6.0"])
        pelo_arquivo = json.loads(capsys.readouterr().out)

        assert "SF-SPARK4-003" in {f["rule_id"] for f in pelo_diretorio["findings"]}
        assert "SF-SPARK4-003" not in {f["rule_id"] for f in pelo_arquivo["findings"]}

    def test_o_arquivo_continua_aceito(self, tmp_path, capsys):
        """A interface publicada aceitava um `.py`. Ela continua valendo."""
        _job(tmp_path)
        codigo = main(
            ["migrate", "glue", str(tmp_path / "job.py"), "--from", "4.0", "--to", "6.0"]
        )
        saida = json.loads(capsys.readouterr().out)

        assert codigo == 0
        assert "SF-MIG-001" in {f["rule_id"] for f in saida["findings"]}

    def test_caminho_inexistente_e_recusado_com_o_caminho_no_texto(
        self, tmp_path, capsys
    ):
        codigo = main(
            ["migrate", "glue", str(tmp_path / "nada"), "--from", "4.0", "--to", "6.0"]
        )
        saida = json.loads(capsys.readouterr().out)

        assert codigo == 1
        assert "nada" in saida["error"]


class TestOParDeVersaoNaoTemDefault:
    """A quebra deliberada desta fase.

    `--to` tinha default `"5.1"` no codigo. Quem pedisse `migrate glue job.py`
    recebia um veredito sobre um alvo que nunca declarou -- e o veredito
    parecia tao legitimo quanto qualquer outro.
    """

    @pytest.mark.parametrize(
        "argv",
        [
            ["migrate", "glue", "<path>"],
            ["migrate", "glue", "<path>", "--from", "4.0"],
            ["migrate", "glue", "<path>", "--to", "6.0"],
        ],
        ids=["sem-nenhum", "so-from", "so-to"],
    )
    def test_par_incompleto_e_recusado_pelo_parser(self, argv, tmp_path):
        _job(tmp_path)
        resolvido = [str(tmp_path) if a == "<path>" else a for a in argv]
        with pytest.raises(SystemExit) as exc:
            main(resolvido)
        assert exc.value.code == 2

    def test_par_invalido_propaga_a_mensagem_nomeada_do_motor(self, tmp_path, capsys):
        """`version_path.steps` ja nomeia o defeito. Traduzir para um erro
        generico perderia a unica informacao util da falha."""
        _job(tmp_path)
        codigo = main(["migrate", "glue", str(tmp_path), "--from", "6.0", "--to", "4.0"])
        saida = json.loads(capsys.readouterr().out)

        assert codigo == 1
        assert "6.0" in saida["error"] and "4.0" in saida["error"]

    def test_versao_fora_da_matriz_diz_quais_existem(self, tmp_path, capsys):
        _job(tmp_path)
        codigo = main(["migrate", "glue", str(tmp_path), "--from", "4.0", "--to", "9.9"])
        saida = json.loads(capsys.readouterr().out)

        assert codigo == 1
        assert "9.9" in saida["error"]
