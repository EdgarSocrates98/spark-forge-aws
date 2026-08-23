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

# Padroes que identificam credencial pelo VALOR, sem depender do nome da chave.
# Cada um tem prefixo publicado pelo emissor, o que os torna reconheciveis sem
# heuristica de entropia -- e entropia sozinha produz falso positivo em sha, em
# caminho de S3 e em nome de classe Java.
_PADROES_POR_VALOR: tuple[tuple[str, re.Pattern[str]], ...] = (
    # AWS: formato publico, documentado, sem ambiguidade.
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA|AIDA|AROA)[0-9A-Z]{16}\b")),
    # GitHub, os dois formatos vivos. O classico tem 36 caracteres depois do
    # prefixo; o fine-grained e mais longo e tem underscore no meio.
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    # JWT: tres segmentos base64url separados por ponto, comecando por um header
    # que quase sempre serializa para `eyJ`.
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    # Chave privada PEM, qualquer variante. O cabecalho e literal e padronizado.
    ("private_key", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    # Slack: prefixo por tipo de token, todos com o mesmo formato segmentado.
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
)


def looks_like_secret(key: str, value: str) -> bool:
    """`True` quando o par chave/valor tem forma de credencial.

    Tres gatilhos independentes, em ordem de confianca:

    1. O valor casa um padrao de credencial publicado -- access key da AWS,
       token do GitHub, JWT, cabecalho de chave privada PEM, token do Slack.
       Todos tem prefixo definido pelo emissor, entao o gatilho nao olha o nome
       da chave: segredo chega em campo chamado `data` ou `payload` com a mesma
       frequencia com que chega em campo chamado `password`.
    2. O valor tem senha embutida numa URL.
    3. O NOME da chave sugere segredo E o valor tem forma de material
       criptografico. Este gatilho continua existindo porque o gatilho 1 so
       alcanca emissor com prefixo publicado: segredo proprietario -- senha de
       banco interno, chave de HMAC da propria casa -- nao tem prefixo nenhum, e
       so o nome da chave denuncia. Os dois juntos:
       `spark.hadoop.fs.s3a.secret.key` com valor `true` nao e segredo, e um
       hash de 40 caracteres numa chave chamada `spark.sql.warehouse.dir`
       tambem nao.
    """
    if not isinstance(key, str) or not isinstance(value, str):
        return False
    for _, padrao in _PADROES_POR_VALOR:
        if padrao.search(value):
            return True
    if _URL_PASSWORD_RE.search(value):
        return True
    key_lower = key.lower()
    if any(hint in key_lower for hint in _SECRET_KEY_HINTS) and _HIGH_ENTROPY_RE.fullmatch(value):
        return True
    return False


def detectores(key: str, value: str) -> tuple[str, ...]:
    """Nomes dos detectores que dispararam, em ordem estavel.

    NUNCA devolve o valor casado -- e essa a diferenca entre relatorio de
    seguranca e vazamento. Um chamador que queira gravar "havia credencial aqui"
    grava estes nomes; um que queira o valor nao tem como obte-lo por aqui.
    """
    if not isinstance(key, str) or not isinstance(value, str):
        return ()
    achados = [nome for nome, padrao in _PADROES_POR_VALOR if padrao.search(value)]
    if _URL_PASSWORD_RE.search(value):
        achados.append("url_password")
    key_lower = key.lower()
    if any(h in key_lower for h in _SECRET_KEY_HINTS) and _HIGH_ENTROPY_RE.fullmatch(value):
        achados.append("nome_de_chave_com_entropia")
    return tuple(achados)


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
