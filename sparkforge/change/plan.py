"""L1 do §15 (produce change): o diff de um VALOR de configuracao, sem aplicar.

A procedencia diz ONDE o valor foi pedido (`tf.spark_conf`, `pyspark.conf_set`,
regra 19). Este modulo le a linha que o fact aponta, confere que o valor do fact
ainda esta la e troca so o literal. Nada e gravado: o diff e o diff de rollback
saem no retorno, e aplicar e decisao de quem le.

Python e trocado pelo SPAN do no do valor, e nao pela linha: num builder
encadeado (`SparkSession.builder\\n  .config(k, v)`) o `lineno` do `Call` e o
inicio da expressao. Os offsets de coluna do `ast` sao em bytes UTF-8, e a troca
converte antes de fatiar o texto. No Terraform, varias chaves dividem a linha do
`--conf` e so o par `chave=valor` muda, com fronteira de token.
"""
from __future__ import annotations

import ast
import difflib
import io
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.change.refusals import (
    CAMINHO_FORA_DA_RAIZ,
    LINHA_NAO_CONFERE,
    PROCEDENCIA_AMBIGUA,
    SEM_PROCEDENCIA,
    VALOR_INVALIDO,
    VALOR_JA_IGUAL,
    VALOR_NAO_LITERAL,
    VALOR_REDIGIDO,
    ChangeError,
)
from sparkforge.findings.models import Fact
from sparkforge.paths import resolve_within

STAGE_PLAN = "produce_change"
PROCEDENCIA_POR_KIND = {"tf.spark_conf": "terraform", "pyspark.conf_set": "code"}
BOM = "﻿"

_NUMERO = re.compile(r"-?\d+(\.\d+)?")
_VALOR_TF = re.compile(r"[^\s\"'\\$]+")


@dataclass(frozen=True)
class Lugar:
    kind: str
    file: str
    line: int
    value: str
    fact_id: str
    redacted: bool

    @property
    def provenance(self) -> str:
        return PROCEDENCIA_POR_KIND[self.kind]


def linhas_de(texto: str) -> list[str]:
    """Linhas com o fim de cada uma, quebrando em `\\n`, `\\r\\n` e `\\r` como o `ast`."""
    return io.StringIO(texto, newline="").readlines()


def separar_bom(dados: bytes, rel: str) -> tuple[str, str]:
    try:
        texto = dados.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ChangeError(LINHA_NAO_CONFERE, f"{rel}: o arquivo nao e texto UTF-8") from exc
    if texto.startswith(BOM):
        return BOM, texto[len(BOM):]
    return "", texto


def lugares(facts: Sequence[Fact], chave: str) -> list[Lugar]:
    vistos: dict[tuple[str, str, int], Lugar] = {}
    for fact in facts:
        if fact.kind not in PROCEDENCIA_POR_KIND or str(fact.attrs.get("key")) != chave:
            continue
        subject = fact.subject or {}
        lugar = Lugar(
            kind=fact.kind,
            file=str(subject.get("file") or ""),
            line=int(subject.get("line") or 0),
            value=str(fact.attrs.get("value") or ""),
            fact_id=fact.id,
            redacted=bool(fact.attrs.get("redacted")),
        )
        vistos.setdefault((lugar.kind, lugar.file, lugar.line), lugar)
    return sorted(vistos.values(), key=lambda lugar: (lugar.file, lugar.line, lugar.kind))


def _unico_lugar(facts: Sequence[Fact], chave: str) -> Lugar:
    encontrados = lugares(facts, chave)
    if not encontrados:
        raise ChangeError(
            SEM_PROCEDENCIA,
            f"{chave}: nenhum tf.spark_conf nem pyspark.conf_set pede esta chave nos facts",
        )
    if len(encontrados) > 1:
        onde = ", ".join(f"{lugar.file}:{lugar.line} ({lugar.provenance})" for lugar in encontrados)
        raise ChangeError(
            PROCEDENCIA_AMBIGUA, f"{chave}: pedida em {len(encontrados)} lugares: {onde}"
        )
    lugar = encontrados[0]
    if lugar.redacted:
        raise ChangeError(VALOR_REDIGIDO, f"{chave}: valor redigido em {lugar.file}:{lugar.line}")
    return lugar


def _posicao(linhas: list[str], lineno: int, col_bytes: int) -> int:
    base = sum(len(linha) for linha in linhas[: lineno - 1])
    return base + len(linhas[lineno - 1].encode("utf-8")[:col_bytes].decode("utf-8"))


def _literal_novo(atual: object, literal: str, novo: str, chave: str) -> str:
    if isinstance(atual, bool):
        if novo not in ("True", "False"):
            raise ChangeError(VALOR_INVALIDO, f"{chave}: e booleano no codigo e {novo!r} nao e")
        return novo
    if isinstance(atual, int | float):
        if not _NUMERO.fullmatch(novo):
            raise ChangeError(VALOR_INVALIDO, f"{chave}: e numero no codigo e {novo!r} nao e")
        return novo
    aspa = literal[:1]
    if aspa not in ("'", '"') or literal[:3] in ("'''", '"""'):
        raise ChangeError(
            VALOR_NAO_LITERAL, f"{chave}: literal com prefixo ou aspas triplas ({literal[:12]})"
        )
    if aspa in novo or "\\" in novo or "\n" in novo or "\r" in novo:
        raise ChangeError(VALOR_INVALIDO, f"{chave}: {novo!r} nao cabe entre {aspa}")
    return f"{aspa}{novo}{aspa}"


def trocar_py(texto: str, linha: int, chave: str, atual: str, novo: str) -> str:
    try:
        arvore = ast.parse(texto)
    except SyntaxError as exc:
        raise ChangeError(
            LINHA_NAO_CONFERE, f"o arquivo nao e Python valido hoje: {exc.msg} (linha {exc.lineno})"
        ) from exc
    chamadas = [
        no
        for no in ast.walk(arvore)
        if isinstance(no, ast.Call)
        and no.lineno == linha
        and len(no.args) >= 2
        and isinstance(no.args[0], ast.Constant)
        and no.args[0].value == chave
    ]
    if len(chamadas) != 1:
        raise ChangeError(
            LINHA_NAO_CONFERE,
            f"{len(chamadas)} chamada(s) com {chave!r} comecando na linha {linha}; esperava 1",
        )
    valor = chamadas[0].args[1]
    if not isinstance(valor, ast.Constant):
        raise ChangeError(VALOR_NAO_LITERAL, f"{chave}: recebe expressao na linha {valor.lineno}")
    if str(valor.value) != atual:
        raise ChangeError(
            LINHA_NAO_CONFERE,
            f"{chave}: o arquivo tem {valor.value!r} e o fact diz {atual!r} (linha {linha})",
        )
    linhas = linhas_de(texto)
    fim_linha = valor.end_lineno or valor.lineno
    fim_coluna = valor.end_col_offset if valor.end_col_offset is not None else valor.col_offset
    inicio = _posicao(linhas, valor.lineno, valor.col_offset)
    fim = _posicao(linhas, fim_linha, fim_coluna)
    return texto[:inicio] + _literal_novo(valor.value, texto[inicio:fim], novo, chave) + texto[fim:]


def trocar_tf(texto: str, linha: int, chave: str, atual: str, novo: str) -> str:
    linhas = linhas_de(texto)
    if not 1 <= linha <= len(linhas):
        raise ChangeError(
            LINHA_NAO_CONFERE, f"o arquivo tem {len(linhas)} linhas e o fact aponta a {linha}"
        )
    if not _VALOR_TF.fullmatch(novo):
        raise ChangeError(VALOR_INVALIDO, f"{chave}: {novo!r} nao cabe num par do `--conf`")
    padrao = re.compile(r"(?<![\w.-])" + re.escape(f"{chave}={atual}") + r"(?=[\s\"]|$)")
    achados = list(padrao.finditer(linhas[linha - 1]))
    if len(achados) != 1:
        raise ChangeError(
            LINHA_NAO_CONFERE,
            f"{len(achados)} ocorrencia(s) de {chave}={atual} na linha {linha}; esperava 1",
        )
    par = achados[0]
    original = linhas[linha - 1]
    linhas[linha - 1] = original[: par.start()] + f"{chave}={novo}" + original[par.end():]
    return "".join(linhas)


def diff_unificado(rel: str, antes: str, depois: str) -> str:
    saida: list[str] = []
    for linha in difflib.unified_diff(
        linhas_de(antes), linhas_de(depois), fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3
    ):
        saida.append(linha if linha.endswith("\n") else linha + "\n\\ No newline at end of file\n")
    return "".join(saida)


def _rel_confinado(repo: Path, arquivo: str) -> tuple[str, Path]:
    alvo = resolve_within(repo, arquivo) if arquivo else None
    if alvo is None:
        raise ChangeError(CAMINHO_FORA_DA_RAIZ, f"{arquivo!r} esta fora de {repo}")
    if not alvo.is_file():
        raise ChangeError(
            LINHA_NAO_CONFERE,
            f"{arquivo} nao existe sob {repo}: extraido com outra raiz, ou o arquivo saiu",
        )
    return alvo.relative_to(Path(repo).expanduser().resolve()).as_posix(), alvo


def plan_change(
    facts: Sequence[Fact],
    repo: Path | str,
    valores: Mapping[str, str],
    bases: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Um diff por arquivo tocado, o diff inverso e o que ficou recusado, por chave."""
    raiz = Path(repo)
    bases = bases or {}
    originais: dict[str, str] = {}
    atuais: dict[str, str] = {}
    mudancas: list[dict[str, Any]] = []
    recusas: list[dict[str, Any]] = []
    for chave in sorted(valores):
        novo = str(valores[chave])
        try:
            lugar = _unico_lugar(facts, chave)
            if lugar.value == novo:
                raise ChangeError(
                    VALOR_JA_IGUAL, f"{chave}: {lugar.file}:{lugar.line} ja pede {novo}"
                )
            rel, alvo = _rel_confinado(raiz, lugar.file)
            if rel not in atuais:
                _, texto = separar_bom(alvo.read_bytes(), rel)
                originais[rel] = atuais[rel] = texto
            trocar = trocar_tf if lugar.kind == "tf.spark_conf" else trocar_py
            atuais[rel] = trocar(atuais[rel], lugar.line, chave, lugar.value, novo)
        except ChangeError as exc:
            recusas.append(exc.to_dict(key=chave))
            continue
        base = bases.get(chave)
        mudancas.append(
            {
                "key": chave,
                "file": rel,
                "line": lugar.line,
                "from": lugar.value,
                "to": novo,
                "provenance": lugar.provenance,
                "evidence": [lugar.fact_id],
                "basis": dict(base) if base is not None else None,
            }
        )
    arquivos = sorted(rel for rel in atuais if atuais[rel] != originais[rel])
    return {
        "stage": STAGE_PLAN,
        "applied": False,
        "changes": mudancas,
        "refused": recusas,
        "files": arquivos,
        "diff": "".join(diff_unificado(rel, originais[rel], atuais[rel]) for rel in arquivos),
        "rollback_diff": "".join(
            diff_unificado(rel, atuais[rel], originais[rel]) for rel in arquivos
        ),
    }
