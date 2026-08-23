"""Reconhecimento de segredo em par chave/valor de configuracao.

POR QUE ESTE MODULO EXISTE, e por que ele nasce com tres copias vivas ao lado.

`_looks_like_secret` esta implementado hoje em `facts/emr_cluster.py`,
`facts/emr_serverless.py` e `facts/terraform.py`. Os dois primeiros carregam, em
comentario, a observacao de que repetem os padroes do terceiro. Enquanto a
duplicacao foi de tres extratores que ja tinham golden gravado, custava menos que
o risco de mexer neles.

A area SF-CFG muda a conta. Ela le CONFIGURACAO DE SPARK, que e onde credencial
aparece com mais frequencia -- `spark.hadoop.fs.s3a.secret.key`, senha dentro de
URL de JDBC em `spark.sql.catalog.*.uri`, token em `spark.kubernetes.*`. Virar a
QUARTA copia seria criar drift numa superficie de seguranca: um padrao corrigido
num arquivo e esquecido nos outros vaza segredo por um extrator e nao pelos
demais, e nada acusa.

Entao o modulo nasce como fonte unica para quem for escrito daqui em diante. Os
tres existentes NAO foram migrados nesta fase de proposito: cada um tem fixtures
golden gravadas, e mudar o caminho de redacao deles exigiria regravar golden que
nao tem defeito -- trabalho com risco de semantica e sem ganho medido. A
consolidacao esta registrada como divida em STATUS.md, com o custo medido, em vez
de ficar implicita neste comentario.

O contrato e deliberadamente conservador. Ele responde "isto PARECE segredo?",
nunca "isto E segredo": um falso positivo redige um valor que o operador podia
ler, e um falso negativo publica credencial num `facts.json` que vai para o
handoff commitado. A assimetria e obvia e o codigo escolhe o lado dela.
"""
from __future__ import annotations

import re

REDACTED = "<redigido>"

# Access key id da AWS. Formato fixo e publico; casa em qualquer valor.
_AKIA_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")

# Senha embutida em URL: `scheme://usuario:senha@host`. Pega JDBC, S3A com
# credencial no path e endpoint de catalogo Iceberg.
_URL_PASSWORD_RE = re.compile(r"://[^/\s:@]+:[^/\s@]+@")

# Nome de chave que sugere segredo. Casado como substring, minusculo.
_SECRET_KEY_HINTS = (
    "secret",
    "password",
    "passwd",
    "token",
    "credential",
    "private_key",
    "privatekey",
    "apikey",
    "api_key",
    "access_key",
    "accesskey",
    "auth",
)

# Valor com cara de material criptografico: longo e sem espaco. O piso de 16
# evita redigir `true`, `128MB` e nome de classe.
_HIGH_ENTROPY_RE = re.compile(r"^[A-Za-z0-9/+=_.\-]{16,}$")


def looks_like_secret(key: str, value: str) -> bool:
    """`True` quando o par chave/valor tem forma de credencial.

    Tres gatilhos independentes, em ordem de confianca:

    1. O valor contem um access key id da AWS. Formato publico, sem ambiguidade.
    2. O valor tem senha embutida numa URL.
    3. O NOME da chave sugere segredo E o valor tem forma de material
       criptografico. Os dois juntos: `spark.hadoop.fs.s3a.secret.key` com valor
       `true` nao e segredo, e um hash de 40 caracteres numa chave chamada
       `spark.sql.warehouse.dir` tambem nao.
    """
    if not isinstance(key, str) or not isinstance(value, str):
        return False
    if _AKIA_RE.search(value):
        return True
    if _URL_PASSWORD_RE.search(value):
        return True
    key_lower = key.lower()
    if any(hint in key_lower for hint in _SECRET_KEY_HINTS) and _HIGH_ENTROPY_RE.fullmatch(value):
        return True
    return False


def redact(key: str, value: str) -> tuple[str, bool]:
    """Devolve `(valor_publicavel, foi_redigido)`.

    Chamador grava `attrs["value"]` com o primeiro elemento e, quando o segundo
    e `True`, marca `attrs["redacted"] = True`. O fato de ter havido redacao e
    ele proprio um dado: uma regra pode querer saber que ha credencial em
    configuracao sem nunca ver o valor.
    """
    if looks_like_secret(key, value):
        return REDACTED, True
    return value, False
