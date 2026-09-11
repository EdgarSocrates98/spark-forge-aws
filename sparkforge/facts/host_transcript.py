"""O transcript do HOST como fact: que tools o agente chamou e o que respondeu.

O SparkForge nao executa agente e nao chama provider (regra 23). Quem roda o
agente e o host, e o host grava um transcript. Este extrator le esse arquivo e
diz, por fact, o que aconteceu nele -- e e sobre esses facts que
`sparkforge.evals.grade` pontua uma resposta contra o gabarito.

FORMATO CONHECIDO, e so ele: o JSONL de sessao do Claude Code, o mesmo que
`sparkforge.collect.host_usage` ja le. Conferido em 2026-09-10 contra
transcript real desta maquina, fora do repositorio: toda linha de `user` e
`assistant` traz `type` e `version`; `message.model` aparece em toda mensagem de
assistente; `tool_use` e bloco de `message.content` da linha `assistant`, com
`id`, `name` e `input`; `tool_result` e bloco da linha `user`, pareado por
`tool_use_id`, com `content` string ou lista e `is_error` opcional. Uma sessao
`claude -p` grava o mesmo envelope e ainda linhas de outros tipos (`attachment`,
`ai-title`, `queue-operation`, `last-prompt`) -- tipo que este modulo nao usa e
ignorado, e nao contado como formato alheio: a linha TEM `type`, entao e deste
host.

O QUE NENHUM FACT DAQUI CARREGA: texto de `tool_use.input` nem de
`tool_result.content`. Transcript e conteudo nao confiavel -- o comando Bash, o
arquivo lido, o resultado de uma tool podem trazer qualquer coisa, inclusive
instrucao --, e o que o grader precisa e verbo, ordem e tamanho. A unica string
que sai do corpo do transcript e a resposta declarada na linha `ANSWER:`,
truncada em `ANSWER_MAX_CHARS`. O `subject` cita o NOME do arquivo, nunca o
caminho: um caminho absoluto de transcript carrega o diretorio do usuario, e o
golden precisa ser o mesmo em qualquer maquina.

Recusa por nome, como `host_usage`. As sete razoes de `host_usage` valem aqui
com o mesmo significado, e duas sao deste modulo: `tool_result_orphan` (resultado
cujo `tool_use_id` nenhum `tool_use` declarou) e `tool_use_without_result`
(chamada que o transcript nunca respondeu -- a sessao acabou no meio, por
exemplo por teto de orcamento).
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sparkforge.collect.host_usage import SOURCE_CLAUDE_CODE, _somar_usage
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "host_transcript@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "host.transcript",
        "host.tool_call",
        "host.final_answer",
        "host.usage",
        "host.transcript.unresolved",
    }
)

ANSWER_MAX_CHARS = 200

UNRESOLVED_REASONS = frozenset(
    {
        "host_format_unknown",
        "malformed_line",
        "message_field_not_object",
        "usage_field_absent",
        "usage_value_malformed",
        "usage_value_fractional",
        "usage_value_negative",
        "tool_result_orphan",
        "tool_use_without_result",
    }
)

_ANSWER = re.compile(r"^\s*ANSWER:\s*(?P<valor>.*?)\s*$")
_MCP = re.compile(r"^mcp__.+__sparkforge_(?P<verbo>[a-z0-9_]+)$")
_SEPARADORES = re.compile(r"&&|\|\||;|\|")
_PREFIXOS = (("rtk",), ("uv", "run"), ("python", "-m"))
_PALAVRA = re.compile(r"^[a-z][a-z-]*$")


def canonical_verb(name: str, tool_input: Any) -> tuple[str, str | None]:
    """`(canal, verbo)` de uma chamada de tool.

    Canal `mcp` quando o nome e de tool do servidor SparkForge (com ou sem
    prefixo de plugin no servidor); `bash` quando o comando Bash invoca a CLI
    `sparkforge`; `other` no resto, com verbo None. Regra fechada e sem
    consulta ao parser da CLI -- `sparkforge.evals` nao depende de
    `sparkforge.adapters`. As bordas conhecidas estao no DESIGN
    (Decision 4) e em `tests/test_evals_normalize.py`.
    """
    casou = _MCP.match(name)
    if casou:
        return "mcp", casou.group("verbo")
    if name == "Bash" and isinstance(tool_input, dict):
        comando = tool_input.get("command")
        if isinstance(comando, str):
            for segmento in _SEPARADORES.split(comando):
                tokens = segmento.split()
                for prefixo in _PREFIXOS:
                    if tuple(tokens[: len(prefixo)]) == prefixo:
                        tokens = tokens[len(prefixo) :]
                        break
                if tokens[:1] == ["sparkforge"] and len(tokens) > 1 and _PALAVRA.match(tokens[1]):
                    partes = [tokens[1]]
                    if len(tokens) > 2 and _PALAVRA.match(tokens[2]):
                        partes.append(tokens[2])
                    return "bash", "_".join(partes).replace("-", "_")
    return "other", None


def _result_bytes(content: Any) -> int:
    if isinstance(content, str):
        return len(content.encode("utf-8"))
    canonico = json.dumps(content, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return len(canonico.encode("utf-8"))


def _first_line_is_ours(caminho: Path) -> bool:
    with caminho.open(encoding="utf-8", errors="replace") as arquivo:
        for linha in arquivo:
            limpa = linha.strip()
            if not limpa:
                continue
            try:
                evento = json.loads(limpa)
            except json.JSONDecodeError:
                return False
            return isinstance(evento, dict) and "type" in evento
    return False


def _sha256(caminho: Path) -> str:
    """sha256 do transcript com o fim de linha normalizado para LF.

    Byte cru dava um hash por sistema: o checkout do Windows converte os
    `.jsonl` para CRLF, e o golden de `fixtures/host_transcript/` falhava so no
    wheel do Windows (CI do PR #48) com o MESMO conteudo. Linha a linha, e nao
    `read_text`, porque transcript de host passa de megabytes; e o mesmo
    criterio de `facts/athena_workgroup.py`, que faz o hash depois de ler em
    modo texto.
    """
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for linha in arquivo:
            digest.update(linha.replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def _answer_in(texto: str) -> str | None:
    achado = None
    for linha in texto.splitlines():
        casou = _ANSWER.match(linha)
        if casou:
            achado = casou.group("valor")
    return achado


def extract_host_transcript_path(path: Path | str) -> list[Fact]:
    """Facts `host.*` de um transcript JSONL do Claude Code.

    Arquivo que nao e deste host -- sufixo diferente de `.jsonl`, ou primeira
    linha que nao e objeto JSON com `type` -- sai como UM
    `host.transcript.unresolved` com `host_format_unknown`, sem ler o resto: a
    medida de snippet de `tests/test_harness_untrusted.py` roda este extrator
    sobre o corpus inteiro, e os event logs de `fixtures/` sao JSONL de outro
    formato.
    """
    caminho = Path(path)
    subject = {"type": "source_location", "file": caminho.name, "symbol": caminho.stem}
    provenance: dict[str, Any] = {"extractor": EXTRACTOR_ID, "artifact": caminho.name}

    if caminho.suffix != ".jsonl" or not caminho.is_file() or not _first_line_is_ours(caminho):
        return [_unresolved(subject, provenance, "host_format_unknown", 1)]
    provenance["artifact_sha256"] = _sha256(caminho)

    lacunas: Counter[str] = Counter()
    chamadas: list[dict[str, Any]] = []
    resultados: dict[str, tuple[Any, bool]] = {}
    ordem_resultado: list[str] = []
    modelos: set[str] = set()
    versoes: set[str] = set()
    resposta: str | None = None
    mensagens_assistente = 0
    linhas = 0
    tokens = [0, 0, 0, 0]
    mensagens_com_usage = 0

    with caminho.open(encoding="utf-8", errors="replace") as arquivo:
        for numero, linha in enumerate(arquivo, start=1):
            limpa = linha.strip()
            if not limpa:
                continue
            linhas += 1
            try:
                evento = json.loads(limpa)
            except json.JSONDecodeError:
                lacunas["malformed_line"] += 1
                continue
            if not isinstance(evento, dict) or "type" not in evento:
                lacunas["host_format_unknown"] += 1
                continue
            tipo = evento.get("type")
            if tipo not in ("assistant", "user"):
                continue
            versao = evento.get("version")
            if isinstance(versao, str) and versao:
                versoes.add(versao)
            mensagem = evento.get("message")
            if mensagem is not None and not isinstance(mensagem, dict):
                lacunas["message_field_not_object"] += 1
                continue
            mensagem = mensagem or {}
            conteudo = mensagem.get("content")
            blocos = conteudo if isinstance(conteudo, list) else []

            if tipo == "user":
                for bloco in blocos:
                    if isinstance(bloco, dict) and bloco.get("type") == "tool_result":
                        chave = str(bloco.get("tool_use_id", ""))
                        resultados[chave] = (bloco.get("content"), bool(bloco.get("is_error")))
                        ordem_resultado.append(chave)
                continue

            mensagens_assistente += 1
            modelo = mensagem.get("model")
            if isinstance(modelo, str) and modelo:
                modelos.add(modelo)
            if isinstance(conteudo, str):
                achada = _answer_in(conteudo)
                if achada is not None:
                    resposta = achada
            for bloco in blocos:
                if not isinstance(bloco, dict):
                    continue
                if bloco.get("type") == "tool_use":
                    chamadas.append(
                        {
                            "id": str(bloco.get("id", "")),
                            "name": str(bloco.get("name", "")),
                            "input": bloco.get("input"),
                            "line": numero,
                        }
                    )
                elif bloco.get("type") == "text" and isinstance(bloco.get("text"), str):
                    achada = _answer_in(bloco["text"])
                    if achada is not None:
                        resposta = achada
            uso = mensagem.get("usage")
            if not isinstance(uso, dict):
                lacunas["usage_field_absent"] += 1
                continue
            somado, motivo = _somar_usage(uso)
            if motivo is not None:
                lacunas[motivo] += 1
                continue
            for indice, valor in enumerate(somado):
                tokens[indice] += valor
            mensagens_com_usage += 1

    facts: list[Fact] = [
        Fact(
            kind="host.transcript",
            subject=subject,
            measures={"assistant_message_count": mensagens_assistente, "line_count": linhas},
            attrs={
                "source": SOURCE_CLAUDE_CODE,
                "models": sorted(modelos),
                "host_versions": sorted(versoes),
            },
            provenance=provenance,
        )
    ]

    declarados = {chamada["id"] for chamada in chamadas}
    for ordinal, chamada in enumerate(chamadas, start=1):
        canal, verbo = canonical_verb(chamada["name"], chamada["input"])
        measures: dict[str, Any] = {"ordinal": ordinal}
        attrs: dict[str, Any] = {"channel": canal, "tool": chamada["name"], "verb": verbo}
        if chamada["id"] in resultados:
            conteudo_resultado, erro = resultados[chamada["id"]]
            measures["result_bytes"] = _result_bytes(conteudo_resultado)
            attrs["is_error"] = erro
        else:
            lacunas["tool_use_without_result"] += 1
            attrs["is_error"] = None
        facts.append(
            Fact(
                kind="host.tool_call",
                subject={**subject, "line": chamada["line"]},
                measures=measures,
                attrs=attrs,
                provenance=provenance,
            )
        )
    orfaos = sum(1 for chave in ordem_resultado if chave not in declarados)
    if orfaos:
        lacunas["tool_result_orphan"] += orfaos

    if resposta is not None:
        truncada = len(resposta) > ANSWER_MAX_CHARS
        facts.append(
            Fact(
                kind="host.final_answer",
                subject=subject,
                attrs={"answer": resposta[:ANSWER_MAX_CHARS], "truncated": truncada},
                provenance=provenance,
            )
        )

    if mensagens_com_usage:
        facts.append(
            Fact(
                kind="host.usage",
                subject=subject,
                measures={
                    "input_tokens": tokens[0],
                    "output_tokens": tokens[1],
                    "cache_read_tokens": tokens[2],
                    "cache_creation_tokens": tokens[3],
                    "message_count": mensagens_com_usage,
                },
                provenance=provenance,
            )
        )

    for razao, quantas in sorted(lacunas.items()):
        facts.append(_unresolved(subject, provenance, razao, quantas))
    return sort_facts(facts)


def _unresolved(
    subject: dict[str, Any], provenance: dict[str, Any], reason: str, count: int
) -> Fact:
    return Fact(
        kind="host.transcript.unresolved",
        subject=subject,
        measures={"count": count},
        attrs={"reason": reason},
        provenance=provenance,
    )
