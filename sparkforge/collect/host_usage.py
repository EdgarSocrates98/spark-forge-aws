"""O usage que o HOST registrou -- o unico token de provider que existe aqui.

O SparkForge nao chama provider nenhum: medido, `sparkforge/` nao importa
`anthropic`, `openai`, `bedrock` nem `litellm`. Quem gasta token e o host
executando os agents em markdown. Este modulo le o que o host gravou, e por
isso entra pela porta do `collect *` -- a unica parte do projeto que ja le
artefato de fora.

A DISCIPLINA E A MESMA DOS COLETORES: le o formato que conhece, e recusa por
NOME o que nao conhece. Um parser adivinhado sobre transcript de outro host
produziria numero com cara de medida.

Formato conhecido: o transcript JSONL do Claude Code, uma mensagem por linha,
com `usage` dentro de `message` nas linhas de tipo "assistant". Confirmado
contra transcript real desta maquina (~1958 mensagens de assistente de uma
sessao) -- os campos `input_tokens`, `output_tokens`,
`cache_read_input_tokens` e `cache_creation_input_tokens` aparecem em
praticamente toda mensagem, nao so "as vezes" como a suposicao inicial
temia.

Decisao sobre `cache_creation_input_tokens`: fica em campo proprio
(`cache_creation_tokens`), nunca somado a `input_tokens` nem a
`cached_tokens`. E token de ESCRITA em cache, cobrado a preco diferente do
input normal e tambem diferente do `cache_read_input_tokens` (que e LEITURA
de cache, mais barata ainda). Tres unidades de custo diferentes por token --
somar qualquer par sob um rotulo so produziria numero com cara de medida que
nao seria. Quem precisar do custo depois aplica o preco de cada campo
separadamente.

Decisao sobre `message` com forma errada (lista, string, numero em vez de
dicionario): recusado por nome em `message_field_not_object`, reason propria
e distinta de `host_format_unknown`. A distincao importa: `host_format_unknown`
e sobre o ENVELOPE da linha (nao tem "type", ou nao e nem dicionario) --
sinal de que a linha inteira nao e deste host. `message_field_not_object` e
sobre uma linha cujo envelope BATE com o formato conhecido (tem
"type": "assistant") mas cujo campo interno quebrou a forma esperada -- um
`.get("usage")` direto sobre lista ou string derruba a leitura inteira com
AttributeError, o que contradiz a promessa do modulo de nunca deixar uma
linha ruim matar as demais.

Decisao sobre numero impossivel: contagem de token nao existe negativa nem
fracionaria -- os dois viram lacuna nomeada em vez de entrar na soma.
Negativo e `usage_value_negative`. Fracionario e `usage_value_fractional`:
truncar em silencio (`int(12.7) == 12`) fabricaria um numero plausivel a
partir de um dado que ja esta corrompido, exatamente o "numero com cara de
medida que nao e" que este modulo existe para recusar.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE_CLAUDE_CODE = "claude_code_transcript"


def _vazio(razao: str) -> dict[str, Any]:
    # mesma forma do retorno normal, com tudo zerado -- quem consome o dict
    # nao precisa tratar dois shapes diferentes para os casos de recusa.
    return {
        "source": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "cache_creation_tokens": 0,
        "message_count": 0,
        "unresolved": [{"reason": razao, "count": 1}],
    }


_CAMPOS_USAGE = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def _valor_do_campo(bruto: Any) -> tuple[int | None, str | None]:
    """Valida um unico campo de usage. Retorna (valor, None) ou (None, motivo)."""
    if bruto is None:
        return 0, None
    # bool e subclasse de int em python -- isinstance(True, int) e True --
    # entao precisa ser barrado antes do isinstance(bruto, int) generico, ou
    # True/False virariam 1/0 silenciosamente.
    if isinstance(bruto, bool):
        return None, "usage_value_malformed"
    if isinstance(bruto, float):
        if not bruto.is_integer():
            # truncar em silencio fabricaria numero plausivel a partir de dado
            # corrompido -- recusa por nome em vez de int(12.7) == 12.
            return None, "usage_value_fractional"
        bruto = int(bruto)
    if isinstance(bruto, str):
        try:
            bruto = int(bruto)
        except ValueError:
            return None, "usage_value_malformed"
    if not isinstance(bruto, int):
        return None, "usage_value_malformed"
    if bruto < 0:
        # contagem de token negativa nao existe -- e "numero com cara de
        # medida" que este modulo recusa por principio.
        return None, "usage_value_negative"
    return bruto, None


def _somar_usage(uso: dict[str, Any]) -> tuple[tuple[int, int, int, int] | None, str | None]:
    # valor nao numerico, negativo ou fracionario nao derruba a leitura
    # inteira -- vira lacuna nomeada em read_host_usage em vez de estourar
    # excecao ou entrar na soma com cara de medida que nao e.
    valores = []
    for campo in _CAMPOS_USAGE:
        valor, motivo = _valor_do_campo(uso.get(campo))
        if motivo is not None:
            return None, motivo
        valores.append(valor)
    return tuple(valores), None


def read_host_usage(path: Path | str) -> dict[str, Any]:
    """Soma o usage das mensagens de assistente de um transcript do Claude Code."""
    caminho = Path(path)
    if not caminho.is_file():
        return _vazio("transcript_not_found")

    entrada = saida = cache_leitura = cache_escrita = mensagens = 0
    lacunas: Counter[str] = Counter()
    reconheceu = False

    # le linha a linha em vez de read_text() + splitlines(): um transcript de
    # sessao longa passa facil de centenas de MB, e carregar tudo em memoria
    # de uma vez (duas vezes, com o splitlines) nao escala.
    with caminho.open(encoding="utf-8", errors="replace") as arquivo:
        for linha in arquivo:
            limpa = linha.strip()
            if not limpa:
                continue
            try:
                evento = json.loads(limpa)
            except json.JSONDecodeError:
                lacunas["malformed_line"] += 1
                continue
            if not isinstance(evento, dict) or "type" not in evento:
                lacunas["host_format_unknown"] += 1
                continue
            reconheceu = True
            if evento.get("type") != "assistant":
                continue
            mensagem = evento.get("message")
            if mensagem is not None and not isinstance(mensagem, dict):
                # envelope bate com "assistant", mas o campo message nao e
                # objeto (lista, string, numero) -- forma quebrada, nao
                # ausencia de usage. .get direto sobre isso derrubaria a
                # leitura inteira com AttributeError.
                lacunas["message_field_not_object"] += 1
                continue
            uso = (mensagem or {}).get("usage")
            if not isinstance(uso, dict):
                lacunas["usage_field_absent"] += 1
                continue
            somado, motivo = _somar_usage(uso)
            if motivo is not None:
                lacunas[motivo] += 1
                continue
            e, s, cl, ce = somado
            entrada += e
            saida += s
            cache_leitura += cl
            cache_escrita += ce
            mensagens += 1

    return {
        "source": SOURCE_CLAUDE_CODE if reconheceu else "",
        "input_tokens": entrada,
        "output_tokens": saida,
        "cached_tokens": cache_leitura,
        "cache_creation_tokens": cache_escrita,
        "message_count": mensagens,
        "unresolved": [
            {"reason": razao, "count": quantas} for razao, quantas in sorted(lacunas.items())
        ],
    }
