"""O aplicador estrito do L2: diff unificado sobre bytes em memoria, tudo ou nada.

O diff chega do host e e entrada nao confiavel. Toda recusa de FORMA sai no
parse, antes de qualquer disco: tamanho, criacao/remocao/renome/binario,
caminho que escapa da raiz. Na aplicacao, contexto e linha removida precisam
bater na posicao declarada -- sem fuzz e sem deslocamento --, e o primeiro hunk
que nao bate recusa o diff inteiro. Nada e gravado aqui: quem chama recebe os
bytes novos e decide onde escreve-los.

Unica tolerancia, e declarada: `\\r\\n` contra `\\n` no FIM da linha. Um diff de
`git diff` (LF) sobre uma copia com CRLF no Windows seria recusado inteiro por
um byte que nao muda o conteudo; a linha acrescentada adota o fim de linha do
arquivo.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sparkforge.change.plan import BOM, linhas_de
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

DIFF_MAX_BYTES = 2 * 1024 * 1024

_NAO_SUPORTADOS = (
    "GIT binary patch",
    "Binary files ",
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
    "new file mode",
    "deleted file mode",
    "similarity index",
)
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DRIVE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class Hunk:
    old_start: int
    old_len: int
    new_start: int
    new_len: int
    lines: tuple[str, ...]

    @property
    def header(self) -> str:
        return f"@@ -{self.old_start},{self.old_len} +{self.new_start},{self.new_len} @@"


@dataclass(frozen=True)
class Patch:
    path: str
    hunks: tuple[Hunk, ...]


def validar_caminho(rel: str) -> str:
    normal = rel.replace("\\", "/")
    partes = normal.split("/")
    if (
        not normal
        or normal.startswith("/")
        or _DRIVE.match(normal)
        or any(parte in ("", ".", "..") for parte in partes)
    ):
        raise ChangeError(CAMINHO_FORA_DA_RAIZ, f"{rel!r} nao e caminho relativo dentro da raiz")
    return normal


def _caminho_do_cabecalho(resto: str) -> str:
    caminho = resto.rstrip("\r").split("\t")[0].strip()
    if caminho.startswith('"'):
        raise ChangeError(DIFF_NAO_SUPORTADO, f"caminho entre aspas no cabecalho: {caminho[:60]}")
    return caminho


def _sem_prefixo(caminho: str, prefixo: str) -> str:
    return caminho[len(prefixo):] if caminho.startswith(prefixo) else caminho


def _hunk(brutas: list[str], i: int) -> tuple[Hunk, int]:
    casou = _HUNK.match(brutas[i])
    if casou is None:
        raise ChangeError(DIFF_MALFORMADO, f"linha {i + 1}: cabecalho de hunk ilegivel")
    old_start, new_start = int(casou[1]), int(casou[3])
    old_len = int(casou[2]) if casou[2] is not None else 1
    new_len = int(casou[4]) if casou[4] is not None else 1
    i += 1
    linhas: list[str] = []
    velho = novo = 0
    while velho < old_len or novo < new_len:
        if i >= len(brutas):
            raise ChangeError(
                DIFF_MALFORMADO, f"hunk {brutas[i - 1][:40]} termina antes das linhas declaradas"
            )
        bruta = brutas[i]
        if bruta.startswith("\\"):
            if not linhas:
                raise ChangeError(DIFF_MALFORMADO, f"linha {i + 1}: marcador sem linha antes")
            linhas[-1] = linhas[-1][:-1]
            i += 1
            continue
        marca = bruta[:1] or " "
        if marca == " ":
            velho += 1
            novo += 1
        elif marca == "-":
            velho += 1
        elif marca == "+":
            novo += 1
        else:
            raise ChangeError(DIFF_MALFORMADO, f"linha {i + 1}: {bruta[:40]!r} dentro de hunk")
        linhas.append(marca + bruta[1:] + "\n")
        i += 1
    if i < len(brutas) and brutas[i].startswith("\\"):
        linhas[-1] = linhas[-1][:-1]
        i += 1
    return Hunk(old_start, old_len, new_start, new_len, tuple(linhas)), i


def parse_unified_diff(texto: str) -> list[Patch]:
    if len(texto.encode("utf-8")) > DIFF_MAX_BYTES:
        raise ChangeError(DIFF_GRANDE_DEMAIS, f"o diff passa de {DIFF_MAX_BYTES} bytes")
    brutas = texto.split("\n")
    if brutas and brutas[-1] == "":
        brutas.pop()
    patches: list[Patch] = []
    vistos: set[str] = set()
    i = 0
    while i < len(brutas):
        linha = brutas[i]
        if linha.startswith(_NAO_SUPORTADOS):
            raise ChangeError(DIFF_NAO_SUPORTADO, f"linha {i + 1}: {linha[:60]}")
        cabecalho = linha.startswith("--- ") and i + 1 < len(brutas)
        if not (cabecalho and brutas[i + 1].startswith("+++ ")):
            i += 1
            continue
        origem = _caminho_do_cabecalho(linha[4:])
        destino = _caminho_do_cabecalho(brutas[i + 1][4:])
        i += 2
        if "/dev/null" in (origem, destino):
            raise ChangeError(
                DIFF_NAO_SUPORTADO, f"criacao ou remocao de arquivo: {origem} -> {destino}"
            )
        rel_origem, rel_destino = _sem_prefixo(origem, "a/"), _sem_prefixo(destino, "b/")
        if rel_origem != rel_destino:
            raise ChangeError(
                DIFF_NAO_SUPORTADO, f"renome de arquivo: {rel_origem} -> {rel_destino}"
            )
        rel = validar_caminho(rel_destino)
        if rel in vistos:
            raise ChangeError(DIFF_MALFORMADO, f"{rel} aparece duas vezes no diff")
        hunks: list[Hunk] = []
        while i < len(brutas) and brutas[i].startswith("@@"):
            hunk, i = _hunk(brutas, i)
            hunks.append(hunk)
        if not hunks:
            raise ChangeError(DIFF_MALFORMADO, f"{rel}: cabecalho sem hunk")
        patches.append(Patch(rel, tuple(hunks)))
        vistos.add(rel)
    if not patches:
        raise ChangeError(DIFF_VAZIO, "nenhum arquivo com hunk no diff")
    return patches


def _sem_fim(linha: str) -> str:
    if linha.endswith("\r\n"):
        return linha[:-2]
    if linha.endswith(("\n", "\r")):
        return linha[:-1]
    return linha


def _tem_fim(linha: str) -> bool:
    return linha.endswith(("\n", "\r"))


def _mesma_linha(arquivo: str, diff: str) -> bool:
    return _sem_fim(arquivo) == _sem_fim(diff) and _tem_fim(arquivo) == _tem_fim(diff)


def _fim_de_linha(linhas: Sequence[str]) -> str:
    for linha in linhas:
        if linha.endswith("\r\n"):
            return "\r\n"
        if linha.endswith(("\n", "\r")):
            return linha[-1]
    return "\n"


def _aplicar(patch: Patch, dados: bytes) -> bytes:
    try:
        texto = dados.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ChangeError(DIFF_NAO_SUPORTADO, f"{patch.path}: o arquivo nao e texto UTF-8") from exc
    bom = BOM if texto.startswith(BOM) else ""
    linhas = linhas_de(texto[len(bom):])
    fim = _fim_de_linha(linhas)
    resultado: list[str] = []
    pos = 0
    for hunk in patch.hunks:
        inicio = hunk.old_start - 1 if hunk.old_len else hunk.old_start
        if inicio < pos or inicio > len(linhas):
            raise ChangeError(
                DIFF_NAO_APLICA, f"{patch.path} {hunk.header}: posicao fora do arquivo"
            )
        resultado.extend(linhas[pos:inicio])
        pos = inicio
        for linha in hunk.lines:
            marca, corpo = linha[0], linha[1:]
            if marca == "+":
                resultado.append(_sem_fim(corpo) + fim if _tem_fim(corpo) else corpo)
                continue
            if pos >= len(linhas) or not _mesma_linha(linhas[pos], corpo):
                tem = _sem_fim(linhas[pos]) if pos < len(linhas) else "<fim do arquivo>"
                raise ChangeError(
                    DIFF_NAO_APLICA,
                    f"{patch.path} {hunk.header}: na linha {pos + 1} esperava "
                    f"{_sem_fim(corpo)!r} e o arquivo tem {tem!r}",
                )
            if marca == " ":
                resultado.append(linhas[pos])
            pos += 1
    resultado.extend(linhas[pos:])
    return (bom + "".join(resultado)).encode("utf-8")


def apply_patches(conteudos: Mapping[str, bytes], patches: Sequence[Patch]) -> dict[str, bytes]:
    """Os bytes novos de cada arquivo tocado; o primeiro hunk que nao bate recusa tudo."""
    saida: dict[str, bytes] = {}
    for patch in patches:
        if patch.path not in conteudos:
            raise ChangeError(
                ARQUIVO_FORA_DA_COPIA, f"{patch.path}: nao ha este arquivo para aplicar"
            )
        saida[patch.path] = _aplicar(patch, conteudos[patch.path])
    return saida
