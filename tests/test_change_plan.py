"""L1 do §15: troca pelo span do no, par com fronteira no Terraform, recusas, confinamento."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from sparkforge.change.plan import plan_change, trocar_py, trocar_tf
from sparkforge.change.refusals import (
    CAMINHO_FORA_DA_RAIZ,
    LINHA_NAO_CONFERE,
    VALOR_INVALIDO,
    VALOR_JA_IGUAL,
    VALOR_NAO_LITERAL,
    VALOR_REDIGIDO,
    ChangeError,
)
from sparkforge.findings.models import Fact

ROOT = Path(__file__).resolve().parents[1]
CHAVE = "spark.sql.shuffle.partitions"


def _conf(kind: str, arquivo: str, linha: int, valor: str, **attrs: object) -> Fact:
    return Fact(
        kind=kind,
        subject={"type": "source_location", "file": arquivo, "line": linha},
        attrs={"key": CHAVE, "value": valor, **attrs},
        provenance={"extractor": "teste"},
    )


def test_py_string_com_utf8_antes_do_valor_mantem_a_aspa():
    texto = "registrar('ação', spark.conf.set('spark.sql.shuffle.partitions', '800'))\n"
    assert trocar_py(texto, 1, CHAVE, "800", "320") == texto.replace("'800'", "'320'")


def test_py_numero_no_builder_multilinha_troca_so_o_literal():
    texto = (
        "spark = (\n"
        "    SparkSession.builder\n"
        "    .appName('x')\n"
        "    .config('spark.sql.shuffle.partitions', 800)\n"
        "    .getOrCreate()\n"
        ")\n"
    )
    assert trocar_py(texto, 2, CHAVE, "800", "320") == texto.replace(", 800)", ", 320)")


@pytest.mark.parametrize(
    "texto,atual,novo,razao",
    [
        ("spark.conf.set('spark.sql.shuffle.partitions', n)\n", "800", "320", VALOR_NAO_LITERAL),
        (
            "spark.conf.set('spark.sql.shuffle.partitions', '600')\n", "800", "320",
            LINHA_NAO_CONFERE,
        ),
        ("spark.conf.set('spark.sql.shuffle.partitions', 800)\n", "800", "muitas", VALOR_INVALIDO),
        ("spark.conf.set('spark.sql.shuffle.partitions', '800')\n", "800", "3'2", VALOR_INVALIDO),
        ("def f(:\n", "800", "320", LINHA_NAO_CONFERE),
    ],
)
def test_py_recusas(texto, atual, novo, razao):
    with pytest.raises(ChangeError) as exc:
        trocar_py(texto, 1, CHAVE, atual, novo)
    assert exc.value.reason == razao


def test_tf_troca_so_o_par_com_fronteira_de_token():
    linha = (
        '  "--conf" = "x.spark.sql.shuffle.partitions=800 --conf '
        "spark.sql.shuffle.partitions=800 --conf spark.sql.shuffle.partitions.y=800 "
        '--conf a=spark.sql.shuffle.partitions=8000"\n'
    )
    esperado = linha.replace(
        "--conf spark.sql.shuffle.partitions=800 ", "--conf spark.sql.shuffle.partitions=320 "
    )
    assert trocar_tf(linha, 1, CHAVE, "800", "320") == esperado


def test_tf_preserva_crlf_e_recusa_valor_com_espaco():
    texto = 'a = 1\r\n"--conf" = "spark.sql.shuffle.partitions=800"\r\n'
    assert trocar_tf(texto, 2, CHAVE, "800", "320") == texto.replace("=800", "=320")
    with pytest.raises(ChangeError) as exc:
        trocar_tf(texto, 2, CHAVE, "800", "3 20")
    assert exc.value.reason == VALOR_INVALIDO
    with pytest.raises(ChangeError) as exc:
        trocar_tf(texto, 9, CHAVE, "800", "320")
    assert exc.value.reason == LINHA_NAO_CONFERE


def test_plano_recusa_caminho_fora_redigido_e_igual(tmp_path):
    conteudo = '"--conf" = "spark.sql.shuffle.partitions=800"\n'
    (tmp_path / "main.tf").write_text(conteudo, encoding="utf-8")
    redigido = _conf("tf.spark_conf", "main.tf", 1, "<redigido>", redacted=True)
    casos = [
        ([_conf("tf.spark_conf", "../fora.tf", 1, "800")], "320", CAMINHO_FORA_DA_RAIZ),
        ([redigido], "320", VALOR_REDIGIDO),
        ([_conf("tf.spark_conf", "main.tf", 1, "800")], "800", VALOR_JA_IGUAL),
        ([_conf("tf.spark_conf", "nao_existe.tf", 1, "800")], "320", LINHA_NAO_CONFERE),
    ]
    for fatos, novo, razao in casos:
        resultado = plan_change(fatos, tmp_path, {CHAVE: novo})
        assert [r["reason"] for r in resultado["refused"]] == [razao], resultado
        assert resultado["diff"] == "" and resultado["changes"] == []


def test_plano_nao_escreve_nada(tmp_path):
    alvo = tmp_path / "main.tf"
    alvo.write_text('"--conf" = "spark.sql.shuffle.partitions=800"\n', encoding="utf-8")
    antes = hashlib.sha256(alvo.read_bytes()).hexdigest()
    resultado = plan_change([_conf("tf.spark_conf", "main.tf", 1, "800")], tmp_path, {CHAVE: "320"})
    assert resultado["changes"] and resultado["applied"] is False
    assert hashlib.sha256(alvo.read_bytes()).hexdigest() == antes
    assert sorted(p.name for p in tmp_path.iterdir()) == ["main.tf"]


def test_modulo_nao_usa_subprocess_git_nem_provider():
    proibidos = {"subprocess", "anthropic", "openai", "litellm", "bedrock", "boto3", "git"}
    for arquivo in sorted((ROOT / "sparkforge" / "change").glob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                nomes = {a.name.split(".")[0] for a in no.names}
            elif isinstance(no, ast.ImportFrom):
                nomes = {(no.module or "").split(".")[0]}
            elif isinstance(no, ast.Attribute):
                nomes = {no.attr} & {"system", "popen", "Popen", "spawnv", "execv"}
            else:
                continue
            assert not nomes & (proibidos | {"system", "popen", "Popen", "spawnv", "execv"}), (
                arquivo.name,
                nomes,
            )
