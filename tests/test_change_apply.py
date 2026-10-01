"""O aplicador estrito do L2: formas recusadas no parse, tudo ou nada na aplicacao."""
from __future__ import annotations

import pytest

from sparkforge.change.apply import DIFF_MAX_BYTES, apply_patches, parse_unified_diff
from sparkforge.change.plan import BOM, diff_unificado
from sparkforge.change.refusals import (
    ARQUIVO_FORA_DA_COPIA,
    CAMINHO_FORA_DA_RAIZ,
    DIFF_GRANDE_DEMAIS,
    DIFF_MALFORMADO,
    DIFF_NAO_APLICA,
    DIFF_NAO_SUPORTADO,
    DIFF_VAZIO,
    ChangeError,
)


def _diff(rel: str, corpo: str) -> str:
    return f"--- a/{rel}\n+++ b/{rel}\n{corpo}"


@pytest.mark.parametrize(
    "texto,razao",
    [
        ("", DIFF_VAZIO),
        ("so prosa\n", DIFF_VAZIO),
        ("--- /dev/null\n+++ b/novo.txt\n@@ -0,0 +1 @@\n+a\n", DIFF_NAO_SUPORTADO),
        ("--- a/x.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-a\n", DIFF_NAO_SUPORTADO),
        ("--- a/x.txt\n+++ b/y.txt\n@@ -1 +1 @@\n-a\n+b\n", DIFF_NAO_SUPORTADO),
        (
            "diff --git a/x.bin b/x.bin\nBinary files a/x.bin and b/x.bin differ\n",
            DIFF_NAO_SUPORTADO,
        ),
        ("rename from x\nrename to y\n", DIFF_NAO_SUPORTADO),
        ("--- /etc/passwd\n+++ /etc/passwd\n@@ -1 +1 @@\n-a\n+b\n", CAMINHO_FORA_DA_RAIZ),
        ("--- a/C:/x.txt\n+++ b/C:/x.txt\n@@ -1 +1 @@\n-a\n+b\n", CAMINHO_FORA_DA_RAIZ),
        ("--- a/d/../../x\n+++ b/d/../../x\n@@ -1 +1 @@\n-a\n+b\n", CAMINHO_FORA_DA_RAIZ),
        (_diff("x.txt", "@@ -1,2 +1,2 @@\n-a\n+b\n"), DIFF_MALFORMADO),
        (_diff("x.txt", "@@ -1 +1 @@\n*a\n+b\n"), DIFF_MALFORMADO),
        (_diff("x.txt", "") + "texto\n", DIFF_MALFORMADO),
        (_diff("x.txt", "@@ -1 +1 @@\n-a\n+b\n") * 2, DIFF_MALFORMADO),
    ],
)
def test_formas_recusadas_no_parse(texto, razao):
    with pytest.raises(ChangeError) as exc:
        parse_unified_diff(texto)
    assert exc.value.reason == razao


def test_diff_acima_do_teto_e_recusado_antes_do_parse():
    with pytest.raises(ChangeError) as exc:
        parse_unified_diff("x" * (DIFF_MAX_BYTES + 1))
    assert exc.value.reason == DIFF_GRANDE_DEMAIS


def test_aceita_prefixo_git_e_sem_prefixo():
    sem_prefixo = "--- d/x.txt\n+++ d/x.txt\n@@ -1 +1 @@\n-a\n+b\n"
    for texto in (_diff("d/x.txt", "@@ -1 +1 @@\n-a\n+b\n"), sem_prefixo):
        (patch,) = parse_unified_diff(texto)
        assert patch.path == "d/x.txt"
        assert apply_patches({"d/x.txt": b"a\n"}, [patch]) == {"d/x.txt": b"b\n"}


def test_contexto_que_nao_bate_recusa_tudo_sem_mexer_na_entrada():
    conteudos = {"a.txt": b"um\ndois\n", "b.txt": b"tres\n"}
    diff = _diff("a.txt", "@@ -1 +1 @@\n-um\n+UM\n") + _diff("b.txt", "@@ -1 +1 @@\n-TRES\n+x\n")
    with pytest.raises(ChangeError) as exc:
        apply_patches(conteudos, parse_unified_diff(diff))
    assert exc.value.reason == DIFF_NAO_APLICA
    assert conteudos == {"a.txt": b"um\ndois\n", "b.txt": b"tres\n"}


def test_arquivo_ausente_e_recusado():
    with pytest.raises(ChangeError) as exc:
        apply_patches({}, parse_unified_diff(_diff("x.txt", "@@ -1 +1 @@\n-a\n+b\n")))
    assert exc.value.reason == ARQUIVO_FORA_DA_COPIA


def test_diff_lf_sobre_arquivo_crlf_adota_o_fim_do_arquivo():
    (patch,) = parse_unified_diff(_diff("x.txt", "@@ -1,2 +1,2 @@\n a\n-b\n+c\n"))
    assert apply_patches({"x.txt": b"a\r\nb\r\n"}, [patch]) == {"x.txt": b"a\r\nc\r\n"}


def test_insercao_sem_newline_no_fim_e_bom():
    antes = BOM + "a\nb"
    depois = BOM + "a\nnovo\nb"
    diff = diff_unificado("x.txt", antes[1:], depois[1:])
    assert "\\ No newline at end of file" in diff
    (patch,) = parse_unified_diff(diff)
    resultado = apply_patches({"x.txt": antes.encode("utf-8")}, [patch])
    assert resultado["x.txt"].decode("utf-8") == depois
    (volta,) = parse_unified_diff(diff_unificado("x.txt", depois[1:], antes[1:]))
    assert apply_patches(resultado, [volta])["x.txt"].decode("utf-8") == antes


def test_insercao_em_hunk_sem_linha_velha():
    (patch,) = parse_unified_diff(_diff("x.txt", "@@ -1,0 +2 @@\n+b\n"))
    assert apply_patches({"x.txt": b"a\nc\n"}, [patch]) == {"x.txt": b"a\nb\nc\n"}


def test_binario_na_copia_e_recusado():
    (patch,) = parse_unified_diff(_diff("x.bin", "@@ -1 +1 @@\n-a\n+b\n"))
    with pytest.raises(ChangeError) as exc:
        apply_patches({"x.bin": b"\xff\xfe\x00"}, [patch])
    assert exc.value.reason == DIFF_NAO_SUPORTADO
