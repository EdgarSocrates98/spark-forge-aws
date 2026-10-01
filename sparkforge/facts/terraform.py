"""Extrator de definicoes Terraform HCL de `aws_glue_job` em Facts.

Nao ha biblioteca de parsing HCL nas dependencias do projeto, e adicionar uma
nao se justifica so para os poucos atributos que as seis regras `SF-GLUE-*`
precisam. Este modulo e, de proposito, um parser de linha limitado -- nao um
parser HCL geral. Ele entende exatamente as formas que Terraform real de Glue
usa (visto em `knowledge/glue/job-arguments.md` e `workers-and-capacity.md`):
um bloco `resource "aws_glue_job" "nome" { ... }` por job, com os blocos
aninhados `default_arguments`, `command` e `execution_property`.

O que este parser deliberadamente NAO tenta entender: interpolacao `${...}`,
heredoc (`<<EOT`), bloco `dynamic`, meta-argumento `for_each`, chamada de
funcao, e expressao HCL geral (ternario, aritmetica, listas/mapas literais
multi-linha). Cada uma dessas formas produz um Fact `tf.unresolved` com
`attrs.reason` especifico -- nunca um valor adivinhado. `attrs.reason` usa um
vocabulario fechado de sete valores (ver `EMITTED_KINDS`-adjacent docstring de
`extract_terraform`); construcoes nao cobertas por um reason mais especifico
(ternario, aritmetica, lista multi-linha) caem no valor mais generico do
vocabulario fechado, `function_call` -- e melhor reportar sob um reason
aproximado do que inventar um oitavo valor fora do que a Fase 1 definiu.

Limitacoes conhecidas e aceitas (parser de linha, nao de arvore):
  - O `{` de abertura de um bloco precisa estar na mesma linha do cabecalho
    (`resource "..." "..." {`, `default_arguments = {`). E o estilo que
    `terraform fmt` produz; um `{` sozinho na linha seguinte nao e detectado.
  - Um valor de atributo precisa caber em uma unica linha. Lista ou mapa
    literal que continua na linha seguinte vira uma leitura best-effort
    classificada como `function_call` (nao um crash, nao um valor errado).
  - String literal nao cruza linha (HCL exige heredoc para isso, e heredoc ja
    vira `tf.unresolved` explicito) -- por isso o estado de aspas de
    `_strip_comment`/`_brace_delta` pode ser resetado a cada linha, sem
    perder correcao.

Como `pyspark_ast.py` e `event_log.py`: extrator puro e deterministico. Nunca
aplica limiar, nunca atribui severidade, nunca decide o que e ruim -- so
observa e ancora.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.facts.secrets import looks_like_secret as _looks_like_secret
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "terraform@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "tf.attribute",
        "tf.spark_conf",
        "tf.resource",
        "tf.unresolved",
        "tf.module_analyzed",
        "tf.observability.spark_ui",
        # Os dois argumentos de observabilidade existem no recurso, mas ao
        # menos um tem valor que so o `terraform apply` resolve (interpolacao,
        # heredoc, chamada de funcao). Nem confirmado nem ausente -- ver
        # `_check_observability`.
        "tf.observability.unknown",
        # O IaC entrega o jar de GraphFrames a este job? Kind DERIVADO, no
        # mesmo molde dos dois acima e pela mesma razao de motor: o `absent`
        # do catalogo compara so `kind`, e `--extra-jars` e `tf.attribute`
        # como qualquer outro argumento -- ver `_check_graphframes_jar`.
        "tf.graphframes.jar",
        "tf.graphframes.unknown",
    }
)

# Atributos de raiz do bloco `resource "aws_glue_job" "x" { ... }` que as
# regras do catalogo referenciam. Uma chave de raiz fora desta lista (ex.:
# `description`, `tags`) nao e um caso de parse malsucedido --
# e uma decisao deliberada de escopo, e por isso e ignorada em silencio, ao
# contrario de uma construcao genuinamente nao suportada (que sempre vira
# `tf.unresolved`).
_ROOT_ATTRS = frozenset(
    {
        "glue_version",
        "worker_type",
        "number_of_workers",
        "max_retries",
        "timeout",
        "max_capacity",
        "execution_class",
        "role_arn",
        "name",
        # Os dois entraram com as areas SF-KMS e SF-NET: `security_configuration`
        # e a ponta de encriptacao que exige rota ate o KMS, e `connections` e o
        # que coloca o job dentro da VPC. Antes deles o comentario acima citava
        # `connections` como exemplo de chave DELIBERADAMENTE fora de escopo --
        # e estava certo enquanto nenhuma regra a consumia. Agora duas consomem.
        "security_configuration",
        "connections",
    }
)

_RESOURCE_RE = re.compile(r'^resource\s+"([A-Za-z0-9_]+)"\s+"([A-Za-z0-9_.-]+)"\s*\{\s*$')
_DYNAMIC_RE = re.compile(r'^dynamic\s+"([A-Za-z0-9_]+)"\s*\{\s*$')
_FOR_EACH_RE = re.compile(r"^for_each\s*=")
_BLOCK_OPEN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*)?\{\s*$")
_ATTR_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")
_MAP_KEY_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"\s*=\s*(.+)$')

_STRING_LIT_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
_REF_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*(\.[A-Za-z_][A-Za-z0-9_-]*)+$")
_FUNC_CALL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*\(")
_ESCAPE_RE = re.compile(r"\\(.)")

# SF-GLUE-006: os padroes de credencial NAO moram mais aqui. Este modulo tinha
# copia privada deles, e as outras duas copias viviam em `facts/emr_cluster.py`
# e `facts/emr_serverless.py`. Copia de controle de seguranca apodrece calada:
# um padrao acrescentado num arquivo e esquecido nos outros vaza segredo por um
# extrator e nao pelos demais, e nada acusa. A fonte unica e
# `facts/secrets.py`, e `tests/test_facts_secrets.py` tem gate estrutural que
# quebra se alguem escrever a proxima.


def _unescape(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        char = match.group(1)
        return {'"': '"', "\\": "\\", "n": "\n", "t": "\t"}.get(char, "\\" + char)

    return _ESCAPE_RE.sub(repl, text)


def _strip_comment(line: str) -> str:
    """Remove `#` e `//` fora de string. Aspas escapadas (`\\"`) nao fecham a string."""
    out: list[str] = []
    in_string = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(line[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "#" or (ch == "/" and i + 1 < n and line[i + 1] == "/"):
            break
        out.append(ch)
        i += 1
    return "".join(out)


def _brace_delta(text: str) -> int:
    """Saldo de `{`/`}` na linha, ignorando os que estao dentro de string."""
    delta = 0
    in_string = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            delta += 1
        elif ch == "}":
            delta -= 1
        i += 1
    return delta


def _find_block_end(lines: list[str], start: int, limit: int | None = None) -> int | None:
    """Indice (0-based) da linha que fecha o bloco aberto em `start - 1`.

    `start` e a primeira linha DEPOIS do `{` de abertura (profundidade ja em
    1). Devolve None se a profundidade nunca volta a zero antes de `limit`
    (ou do fim do arquivo) -- chaves desbalanceadas.
    """
    depth = 1
    stop = len(lines) if limit is None else limit
    i = start
    while i < stop:
        depth += _brace_delta(lines[i])
        if depth <= 0:
            return i
        i += 1
    return None


def _line_subject(path: str, line: int, snippet: str = "") -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": snippet,
    }


def _resource_subject(path: str, line: int, symbol: str) -> dict[str, Any]:
    return {"type": "tf_resource", "file": path, "line": line, "symbol": symbol}


def _classify_unhandled_line(text: str) -> str:
    """Reason (do vocabulario fechado) para uma linha que nao casa nenhum padrao conhecido."""
    if text.startswith("<<"):
        return "heredoc"
    if "${" in text:
        return "interpolation"
    if re.match(r'^dynamic\s*"', text):
        return "dynamic_block"
    if _FOR_EACH_RE.match(text):
        return "for_each"
    return "function_call"


# Lista LITERAL de strings numa linha so: `["a", "b"]`, e tambem a vazia `[]`.
# Antes desta adicao ela caia no reason `function_call`, que e classificacao
# ERRADA -- `["a"]` nao e chamada de funcao nenhuma. O defeito so nao aparecia
# porque nenhuma chave de `_ROOT_ATTRS` era lista; `connections` passou a ser, e
# um `tf.unresolved` mentindo o motivo e pior que um valor nao lido.
#
# Lista com interpolacao, referencia ou quebra de linha NAO casa aqui e continua
# indo para o reason generico: este parser e linha a linha, e adivinhar o
# conteudo de uma lista que continua na proxima linha seria inventar valor.
_STRING_ITEM_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
_STRING_LIST_RE = re.compile(r'^\[\s*(?:"(?:[^"\\]|\\.)*"\s*,?\s*)*\]$')


def _classify_value(raw_value: str) -> tuple[str | None, Any, bool]:
    """Classifica o lado direito de `chave = valor`.

    Devolve `(unresolved_reason, valor, literal)`. `unresolved_reason` None
    significa que o valor foi entendido -- literal (string/numero/bool) ou
    referencia nao-literal (`var.x`, `local.x`, `data.x.y`, ou atributo de
    outro recurso como `aws_iam_role.glue.arn`). Caso contrario, o valor nunca
    e adivinhado: o chamador emite `tf.unresolved` com esse reason.
    """
    value = raw_value.strip().rstrip(",").strip()
    if not value:
        return "function_call", None, False
    if value.startswith("<<"):
        return "heredoc", None, False
    if "${" in value:
        return "interpolation", None, False

    literal_match = _STRING_LIT_RE.match(value)
    if literal_match:
        return None, _unescape(literal_match.group(1)), True
    if value in ("true", "false"):
        return None, value == "true", True
    if _NUMBER_RE.match(value):
        return None, (float(value) if "." in value else int(value)), True
    if _REF_RE.match(value):
        return None, value, False
    if _STRING_LIST_RE.match(value):
        # Uma lista vira UM valor: os elementos juntos, separados por virgula.
        # Nao um fact por elemento -- a pergunta que as regras fazem sobre
        # `connections` e "o job esta dentro de uma VPC?", e essa pergunta e do
        # job, nao de cada conexao. Lista VAZIA devolve string vazia, que e
        # distinguivel de ausente: `attrs.present` continua True e
        # `attrs.value == ""` diz que a chave foi declarada sem conteudo -- o
        # mesmo par que `SF-LF-001` usa para nao acusar `--extra-jars = ""`.
        itens = _STRING_ITEM_RE.findall(value)
        return None, ",".join(_unescape(item) for item in itens), True
    if _FUNC_CALL_RE.match(value):
        return "function_call", None, False
    # Ternario, aritmetica, lista/mapa literal, ou qualquer outra expressao
    # HCL que este parser de linha nao modela: cai no reason mais generico do
    # vocabulario fechado. Ver docstring do modulo.
    return "function_call", None, False


def _value_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _attribute_fact(
    key: str,
    raw_value: str,
    path: str,
    line: int,
    symbol: str,
    block: str,
    provenance: dict[str, Any],
) -> Fact:
    reason, value, literal = _classify_value(raw_value)
    if reason is not None:
        return Fact(
            kind="tf.unresolved",
            subject=_line_subject(path, line),
            attrs={"reason": reason, "key": key, "block": block},
            provenance=provenance,
        )

    attrs: dict[str, Any] = {
        "key": key,
        "value": _value_to_str(value),
        "present": True,
        "literal": literal,
        "block": block,
    }
    measures: dict[str, Any] = {}

    if isinstance(value, str) and _looks_like_secret(key, value):
        # Nunca escreve o valor suspeito de segredo em attrs.value: um golden
        # de fixture commitado com uma credencial real seria o analisador
        # causando o exato dano que SF-GLUE-006 existe para prevenir.
        attrs["value"] = "<redigido>"
        attrs["redacted"] = True
        attrs["secret_pattern_match"] = True
    elif literal and isinstance(value, int | float) and not isinstance(value, bool):
        measures["value"] = value

    return Fact(
        kind="tf.attribute",
        subject=_resource_subject(path, line, symbol),
        attrs=attrs,
        measures=measures,
        provenance=provenance,
    )


_HEREDOC_START_RE = re.compile(r'^<<-?\s*"?([A-Za-z_][A-Za-z0-9_]*)"?\s*$')


def _heredoc_delimiter(raw_value: str) -> str | None:
    match = _HEREDOC_START_RE.match(raw_value.strip())
    return match.group(1) if match else None


def _find_heredoc_end(lines: list[str], start: int, end: int, delimiter: str) -> int | None:
    i = start
    while i < end:
        if lines[i].strip() == delimiter:
            return i
        i += 1
    return None


def _consume_heredoc(
    lines: list[str],
    key_line_idx: int,
    key: str,
    raw_value: str,
    end: int,
    path: str,
    block: str,
    provenance: dict[str, Any],
) -> tuple[Fact, int] | None:
    """Se `raw_value` abre um heredoc, devolve `(fact_unresolved, proximo_j)`.

    None se `raw_value` nao abre heredoc -- o chamador segue o caminho normal
    de `_attribute_fact`. O corpo do heredoc e pulado inteiro (ate a linha do
    delimitador de fechamento, ou ate `end` se o delimitador nao aparecer
    antes do fim do bloco -- HCL invalido, ou heredoc que atravessa a
    fronteira que `_find_block_end` calculou): sem pular o corpo, cada linha
    dele viraria um `tf.unresolved` avulso, tecnicamente honesto mas ruidoso
    e mal atribuido. Residual conhecido: se o corpo do heredoc contiver `{`
    ou `}`, a contagem de chaves de `_find_block_end` do bloco ao redor (que
    roda ANTES deste pulo, para achar onde esse bloco termina) ja pode ter
    contado essas chaves de forma errada -- ver docstring do modulo.
    """
    delimiter = _heredoc_delimiter(raw_value)
    if delimiter is None:
        return None
    fact = Fact(
        kind="tf.unresolved",
        subject=_line_subject(path, key_line_idx + 1),
        attrs={"reason": "heredoc", "key": key, "block": block},
        provenance=provenance,
    )
    terminator = _find_heredoc_end(lines, key_line_idx + 1, end, delimiter)
    next_j = (terminator + 1) if terminator is not None else end
    return fact, next_j


def _parse_flat_block(
    lines: list[str],
    start: int,
    end: int,
    path: str,
    symbol: str,
    provenance: dict[str, Any],
    block: str,
) -> list[Fact]:
    """`command { ... }` / `execution_property { ... }`: chaves nuas (bare identifier)."""
    facts: list[Fact] = []
    j = start
    while j < end:
        text = lines[j].strip()
        if not text:
            j += 1
            continue
        match = _ATTR_RE.match(text)
        if match:
            key, raw_value = match.group(1), match.group(2)
            consumed = _consume_heredoc(lines, j, key, raw_value, end, path, block, provenance)
            if consumed is not None:
                fact, next_j = consumed
                facts.append(fact)
                j = next_j
                continue
            facts.append(_attribute_fact(key, raw_value, path, j + 1, symbol, block, provenance))
        else:
            reason = _classify_unhandled_line(text)
            facts.append(
                Fact(
                    kind="tf.unresolved",
                    subject=_line_subject(path, j + 1),
                    attrs={"reason": reason, "block": block},
                    provenance=provenance,
                )
            )
        j += 1
    return facts


def _parse_map_block(
    lines: list[str],
    start: int,
    end: int,
    path: str,
    symbol: str,
    provenance: dict[str, Any],
    block: str,
) -> list[Fact]:
    """`default_arguments = { ... }`: chaves entre aspas (map(string))."""
    facts: list[Fact] = []
    j = start
    while j < end:
        text = lines[j].strip()
        if not text:
            j += 1
            continue
        match = _MAP_KEY_RE.match(text)
        if match:
            key, raw_value = match.group(1), match.group(2)
            consumed = _consume_heredoc(lines, j, key, raw_value, end, path, block, provenance)
            if consumed is not None:
                fact, next_j = consumed
                facts.append(fact)
                j = next_j
                continue
            attr_fact = _attribute_fact(key, raw_value, path, j + 1, symbol, block, provenance)
            facts.append(attr_fact)
            # So decompoe quando o `tf.attribute` saiu resolvido: valor com
            # interpolacao ou heredoc ja virou `tf.unresolved`, e desmontar
            # texto que o parser declarou nao entender inventaria propriedade.
            if key == "--conf" and attr_fact.kind == "tf.attribute":
                facts.extend(
                    _spark_conf_facts(
                        attr_fact.attrs.get("value", ""), path, j + 1, symbol, block, provenance
                    )
                )
        else:
            reason = _classify_unhandled_line(text)
            facts.append(
                Fact(
                    kind="tf.unresolved",
                    subject=_line_subject(path, j + 1),
                    attrs={"reason": reason, "block": block},
                    provenance=provenance,
                )
            )
        j += 1
    return facts


# `--conf` no Glue nao carrega UMA propriedade: carrega uma string com varias,
# separadas pela repeticao literal do proprio flag. A forma que a AWS documenta e:
#
#   "--conf" = "spark.sql.shuffle.partitions=200 --conf spark.sql.adaptive.enabled=false"
#
# Como `tf.attribute`, isso e um unico fact cujo `value` e a string inteira.
# Nenhuma regra consegue perguntar "o AQE esta desligado na definicao do job?"
# sobre uma string dessas sem fazer parsing dentro da condicao do catalogo -- que
# e exatamente o que o catalogo NAO faz, porque condicao com parser embutido
# deixa de ser dado e vira codigo escondido em YAML.
#
# `tf.spark_conf` desmonta a string em um fact por propriedade, ao lado do
# `tf.attribute` original, que continua sendo emitido intacto. Nada e
# substituido: o fact bruto e a evidencia de que a linha existe com aquele texto,
# e o decomposto e o que a regra cita.
_CONF_SPLIT_RE = re.compile(r"\s*--conf\s+")


def _spark_conf_facts(
    raw_value: str,
    path: str,
    line: int,
    symbol: str,
    block: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    """Desmonta o valor de `--conf` em um fact por propriedade Spark.

    Pedaco sem `=` nao vira fact silenciosamente: vira `tf.unresolved` com
    `reason: malformed_conf_pair`. Um `--conf spark.sql.adaptive.enabled` sem
    valor e erro de definicao de job que o operador quer ver, e engoli-lo
    produziria o falso negativo de "a chave nao estava la".
    """
    facts: list[Fact] = []
    for pedaco in _CONF_SPLIT_RE.split(raw_value.strip()):
        pedaco = pedaco.strip()
        if not pedaco:
            continue
        if "=" not in pedaco:
            facts.append(
                Fact(
                    kind="tf.unresolved",
                    subject=_line_subject(path, line),
                    attrs={
                        "reason": "malformed_conf_pair",
                        "key": "--conf",
                        "detail": pedaco,
                        "block": block,
                    },
                    provenance=provenance,
                )
            )
            continue
        chave, _, valor = pedaco.partition("=")
        chave, valor = chave.strip(), valor.strip()
        attrs: dict[str, Any] = {
            "key": chave,
            "value": valor,
            "source_argument": "--conf",
            "block": block,
        }
        if _looks_like_secret(chave, valor):
            attrs["value"] = "<redigido>"
            attrs["redacted"] = True
            attrs["secret_pattern_match"] = True
        facts.append(
            Fact(
                kind="tf.spark_conf",
                subject=_resource_subject(path, line, f"{symbol}#{chave}"),
                attrs=attrs,
                provenance=provenance,
            )
        )
    return facts


def _parse_resource_body(
    lines: list[str],
    start: int,
    end: int,
    path: str,
    symbol: str,
    provenance: dict[str, Any],
) -> tuple[list[Fact], bool]:
    """Percorre o corpo (ja delimitado) de um bloco `resource "aws_glue_job" ...`.

    Devolve `(facts, for_each_bail)`. Se `for_each_bail` for True, `facts`
    contem so o `tf.unresolved` do meta-argumento -- ver comentario abaixo
    sobre por que o recurso inteiro e descartado nesse caso, nao so a linha.
    """
    facts: list[Fact] = []
    j = start
    while j < end:
        text = lines[j].strip()
        if not text:
            j += 1
            continue

        # `for_each` faz o mesmo bloco `resource` gerar N recursos, um por
        # item -- valores de atributo passam a depender de `each.key` /
        # `each.value`, que este parser de arquivo unico nunca resolve.
        # Continuar lendo os atributos "literais" abaixo do for_each seria
        # fingir uma leitura estatica de algo que so existe em runtime do
        # Terraform: por isso o recurso inteiro vira um unico tf.unresolved,
        # nao um tf.resource com atributos parcialmente confiaveis.
        if _FOR_EACH_RE.match(text):
            return [
                Fact(
                    kind="tf.unresolved",
                    subject=_line_subject(path, j + 1),
                    attrs={"reason": "for_each"},
                    provenance=provenance,
                )
            ], True

        dynamic_match = _DYNAMIC_RE.match(text)
        if dynamic_match:
            close = _find_block_end(lines, j + 1, end)
            facts.append(
                Fact(
                    kind="tf.unresolved",
                    subject=_line_subject(path, j + 1),
                    attrs={"reason": "dynamic_block", "block_label": dynamic_match.group(1)},
                    provenance=provenance,
                )
            )
            if close is None:
                facts.append(
                    Fact(
                        kind="tf.unresolved",
                        subject=_line_subject(path, j + 1),
                        attrs={"reason": "unbalanced_braces"},
                        provenance=provenance,
                    )
                )
                return facts, False
            j = close + 1
            continue

        block_match = _BLOCK_OPEN_RE.match(text)
        if block_match:
            block_name = block_match.group(1)
            close = _find_block_end(lines, j + 1, end)
            if close is None:
                facts.append(
                    Fact(
                        kind="tf.unresolved",
                        subject=_line_subject(path, j + 1),
                        attrs={"reason": "unbalanced_braces"},
                        provenance=provenance,
                    )
                )
                return facts, False
            if block_name == "default_arguments":
                facts.extend(
                    _parse_map_block(lines, j + 1, close, path, symbol, provenance, block_name)
                )
            elif block_name in ("command", "execution_property"):
                facts.extend(
                    _parse_flat_block(lines, j + 1, close, path, symbol, provenance, block_name)
                )
            # Outros blocos aninhados (ex.: `tags = {...}`, `notification_property {...}`)
            # sao fora do escopo das seis regras SF-GLUE-* e ignorados de proposito --
            # nao e falha de parse, e decisao de escopo (ver `_ROOT_ATTRS`).
            j = close + 1
            continue

        attr_match = _ATTR_RE.match(text)
        if attr_match:
            key, raw_value = attr_match.group(1), attr_match.group(2)
            # O corpo de um heredoc precisa ser pulado mesmo para uma chave
            # fora de `_ROOT_ATTRS`: sem isso a linha do delimitador de
            # fechamento (ex.: "EOT") e o texto entre ela e a chave viram
            # linhas de atributo "root" perdidas, avaliadas fora de contexto.
            consumed = _consume_heredoc(lines, j, key, raw_value, end, path, "root", provenance)
            if consumed is not None:
                fact, next_j = consumed
                if key in _ROOT_ATTRS:
                    facts.append(fact)
                j = next_j
                continue
            if key in _ROOT_ATTRS:
                facts.append(
                    _attribute_fact(key, raw_value, path, j + 1, symbol, "root", provenance)
                )
            j += 1
            continue

        reason = _classify_unhandled_line(text)
        facts.append(
            Fact(
                kind="tf.unresolved",
                subject=_line_subject(path, j + 1),
                attrs={"reason": reason, "block": "root"},
                provenance=provenance,
            )
        )
        j += 1

    return facts, False


_OBSERVABILITY_KEYS = frozenset({"--enable-spark-ui", "--spark-event-logs-path"})


def _check_observability(resource_facts: list[Fact]) -> str:
    """Estado da observabilidade do recurso: `confirmed`, `unknown` ou `absent`.

    Tres estados, nao dois, e a distincao entre os dois ultimos e a razao de
    esta funcao nao devolver mais um bool. `--spark-event-logs-path` escrito
    como `"s3://${var.bucket_logs}/sparkui/"` e a forma NORMAL de escrever
    Terraform -- o valor so existe depois do `terraform apply`, e o extrator
    nunca o adivinha (vira `tf.unresolved` com reason `interpolation`).
    Tratar esse caso como "nao configurou" faz SF-GLUE-002 acusar de
    observabilidade ausente, em P1, um job que tem observabilidade
    configurada. E o mesmo defeito que `plan.unresolved` /
    `partition_status_unknown` fecha do lado do plano fisico: ausencia de
    evidencia nao e evidencia de ausencia.

    `confirmed` exige os dois argumentos juntos e literais, nao um so: com
    apenas um habilitado o job ainda fica sem condicao real de ser
    diagnosticado depois do fato -- ver explanation de SF-GLUE-002 e
    `knowledge/glue/job-arguments.md` secao 1.
    """
    enabled = False
    has_path = False
    indeterminate = False

    for fact in resource_facts:
        if fact.attrs.get("block") != "default_arguments":
            continue
        key = fact.attrs.get("key")
        if fact.kind == "tf.unresolved":
            # O argumento ESTA la; o que falta e o valor, que so o apply
            # resolve. Nao da para afirmar nem confirmar.
            if key in _OBSERVABILITY_KEYS:
                indeterminate = True
            continue
        if fact.kind != "tf.attribute" or not fact.attrs.get("literal"):
            continue
        value = fact.attrs.get("value")
        if key == "--enable-spark-ui" and value == "true":
            enabled = True
        elif key == "--spark-event-logs-path" and value:
            has_path = True

    if enabled and has_path:
        return "confirmed"
    return "unknown" if indeterminate else "absent"


# Argumentos de job Glue que ENTREGAM um artefato ao driver e aos executores.
# `--extra-py-files` entra ao lado de `--extra-jars` porque o jar legado de
# GraphFrames carrega treze arquivos `.py` DENTRO dele (medido em
# `knowledge/graph/availability.md`, veto V-AV-3): apontar o proprio jar em
# `--extra-py-files` e caminho valido e documentado, nao engano.
_JAR_DELIVERY_ARGS = frozenset({"--extra-jars", "--extra-py-files"})

# As mesmas portas, abertas pelo outro lado. `--conf` no Glue carrega uma
# string com varias propriedades, e `_spark_conf_facts` ja a desmonta -- entao
# aqui a chave lida e a propriedade, nao o argumento.
_JAR_DELIVERY_CONFS = frozenset({"spark.jars", "spark.jars.packages"})

# O nome do artefato, nas duas linhagens: `graphframes-0.8.2-spark3.2-s_2.12.jar`
# (spark-packages) e `graphframes-spark3_2.12-0.12.1.jar` (io.graphframes), mais
# a coordenada Maven `graphframes:graphframes:...`. Um substring, e nao um
# regex de versao: a pergunta e "a biblioteca aparece aqui?", e travar o formato
# do nome faria a leitura envelhecer a cada release nova.
# NAO chamar de `_TOKEN`: o `S105` do ruff acusa constante com esse sufixo
# como senha embutida, e o achado seria falso -- isto e a marca textual da
# biblioteca, procurada por substring.
_GRAPHFRAMES_MARCA = "graphframes"

# `--conf` ilegivel esconde `spark.jars.packages` inteiro, entao ele conta como
# porta aberta que nao deu para ler -- nunca como ausencia.
_UNREADABLE_DELIVERY_KEYS = _JAR_DELIVERY_ARGS | {"--conf"}

# ...COM UMA EXCECAO MEDIDA. `malformed_conf_pair` nao e valor escondido: a
# string do `--conf` FOI lida e desmontada, e o que falta e o `=` de UM par
# (`fixtures/terraform/spark_conf_in_arguments` tem exatamente isso). Um par sem
# valor nao pode conter `spark.jars.packages=...`, entao trata-lo como "nao deu
# para ler" calaria a regra sobre um job cujo `--conf` esta inteiramente
# visivel.
_READ_DESPITE_UNRESOLVED = frozenset({"malformed_conf_pair"})


def _check_graphframes_jar(resource_facts: list[Fact]) -> str:
    """O IaC entrega GraphFrames a este job? `declared`, `unknown` ou `absent`.

    Tres estados pela mesma razao de `_check_observability`, e o kind derivado
    existe pela razao registrada no veto `V-GR-1` de `rules/catalog/graph.yaml`:
    `engine._absent_satisfied` compara SO `kind`, e `--extra-jars` sai como
    `tf.attribute` igual a qualquer outro argumento. Uma regra escrita com
    `absent: tf.attribute` seria falsa para todo Terraform lido e acusaria
    tambem o job que declarou o jar. Quem enxerga a pergunta inteira e o
    extrator, e por isso ele decide UMA vez.

    `absent` EXIGE que a lista tenha sido lida e a biblioteca nao esteja nela.
    Um `--extra-jars` literal apontando para outro jar e ausencia MEDIDA -- a
    lista existe, foi lida, e GraphFrames nao esta la --, e nao duvida:
    chamar isso de indeterminado calaria a regra em todo job que declara
    qualquer outro jar, que e a maioria dos jobs reais. O residual conhecido --
    um jar renomeado, ou um fat jar que carregue a biblioteca sem dize-lo no
    nome -- vai escrito DENTRO do achado, no padrao de `V-AS-2`, e nao apagado
    daqui transformando a regra em silencio.

    `unknown` e o valor que so o `terraform apply` resolve: interpolacao,
    heredoc ou chamada de funcao numa das portas de entrega. Ausencia de
    evidencia nao e evidencia de ausencia.
    """
    declared = False
    indeterminate = False

    for fact in resource_facts:
        if fact.attrs.get("block") != "default_arguments":
            continue
        key = fact.attrs.get("key")
        if fact.kind == "tf.unresolved":
            if (
                key in _UNREADABLE_DELIVERY_KEYS
                and fact.attrs.get("reason") not in _READ_DESPITE_UNRESOLVED
            ):
                indeterminate = True
            continue
        if fact.kind == "tf.attribute":
            if key not in _JAR_DELIVERY_ARGS or not fact.attrs.get("literal"):
                continue
        elif fact.kind == "tf.spark_conf":
            if key not in _JAR_DELIVERY_CONFS:
                continue
        else:
            continue
        value = fact.attrs.get("value")
        if isinstance(value, str) and _GRAPHFRAMES_MARCA in value.lower():
            declared = True

    if declared:
        return "declared"
    return "unknown" if indeterminate else "absent"


def extract_terraform(source: str, path: str) -> list[Fact]:
    """Extrai Facts de um arquivo `.tf` ja lido, dado como string.

    Nunca levanta excecao por conteudo malformado: chaves desbalanceadas,
    dynamic/for_each, interpolacao, heredoc e chamada de funcao viram
    `tf.unresolved` e a leitura do arquivo continua (ou, no caso de chaves
    desbalanceadas no nivel do proprio `resource`, para naquele ponto do
    arquivo -- depois disso a fronteira do bloco nao e mais confiavel).
    """
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    provenance = {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}

    raw_lines = source.splitlines()
    lines = [_strip_comment(line) for line in raw_lines]
    n = len(lines)

    facts: list[Fact] = []
    resource_count = 0
    attribute_count = 0
    unresolved_count = 0

    i = 0
    while i < n:
        text = lines[i].strip()
        if not text:
            i += 1
            continue

        match = _RESOURCE_RE.match(text)
        if not match:
            i += 1
            continue

        resource_type, resource_name = match.group(1), match.group(2)
        header_line = i + 1
        close_idx = _find_block_end(lines, i + 1)
        if close_idx is None:
            facts.append(
                Fact(
                    kind="tf.unresolved",
                    subject=_line_subject(path, header_line),
                    attrs={"reason": "unbalanced_braces"},
                    provenance=provenance,
                )
            )
            unresolved_count += 1
            # Sem o fechamento do bloco, nenhuma fronteira depois deste ponto
            # e confiavel: parar de proposito, em vez de arriscar interpretar
            # o resto do arquivo com a contagem de chaves ja errada.
            break

        if resource_type != "aws_glue_job":
            i = close_idx + 1
            continue

        symbol = f"{resource_type}.{resource_name}"
        body_facts, bailed = _parse_resource_body(
            lines, i + 1, close_idx, path, symbol, provenance
        )
        facts.extend(body_facts)

        if bailed:
            unresolved_count += len(body_facts)
        else:
            n_attr = sum(1 for f in body_facts if f.kind == "tf.attribute")
            n_unresolved = sum(1 for f in body_facts if f.kind == "tf.unresolved")
            attribute_count += n_attr
            unresolved_count += n_unresolved
            resource_count += 1
            facts.append(
                Fact(
                    kind="tf.resource",
                    subject=_resource_subject(path, header_line, symbol),
                    attrs={"resource_type": resource_type, "resource_name": resource_name},
                    measures={"attribute_count": n_attr},
                    provenance=provenance,
                )
            )
            observability = _check_observability(body_facts)
            if observability != "absent":
                facts.append(
                    Fact(
                        kind=(
                            "tf.observability.spark_ui"
                            if observability == "confirmed"
                            else "tf.observability.unknown"
                        ),
                        subject=_resource_subject(path, header_line, symbol),
                        provenance=provenance,
                    )
                )
            graphframes_jar = _check_graphframes_jar(body_facts)
            if graphframes_jar != "absent":
                facts.append(
                    Fact(
                        kind=(
                            "tf.graphframes.jar"
                            if graphframes_jar == "declared"
                            else "tf.graphframes.unknown"
                        ),
                        subject=_resource_subject(path, header_line, symbol),
                        provenance=provenance,
                    )
                )

        i = close_idx + 1

    # Sentinela: prova de que a extracao Terraform rodou sobre este arquivo.
    # Sem isso, `absent: tf.observability.spark_ui` (SF-GLUE-002) seria
    # vazamente verdadeiro quando o extrator nunca rodou sobre nenhum
    # arquivo, nao so quando genuinamente nao encontrou observabilidade
    # configurada. Mirror de `pyspark.module_analyzed` / `spark.log_analyzed`.
    facts.append(
        Fact(
            kind="tf.module_analyzed",
            subject=_line_subject(path, 0),
            measures={
                "resource_count": resource_count,
                "attribute_count": attribute_count,
                "unresolved_count": unresolved_count,
            },
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_terraform_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.tf`, ancorando o path relativo a `repo_root`.

    Falha ao abrir o arquivo vira um unico Fact `tf.unresolved` com reason
    "read_error", nunca uma excecao que derruba quem chamou -- mesma
    convencao de `event_log.extract_event_log_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [
            Fact(
                kind="tf.unresolved",
                subject=_line_subject(anchor, 0),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance={"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
            )
        ]
    return extract_terraform(text, anchor)


def extract_terraform_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.tf` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico (permissao,
    encoding invalido, qualquer excecao inesperada) vira um unico Fact
    `tf.unresolved` para aquele arquivo, e a travessia continua -- mesma
    convencao de `pyspark_ast.extract_tree`.
    """
    facts: list[Fact] = []
    for tf_file in iter_source_files(root, "*.tf"):
        rel = str(tf_file.relative_to(repo_root)) if repo_root else str(tf_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_terraform_path(tf_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            facts.append(
                Fact(
                    kind="tf.unresolved",
                    subject=_line_subject(anchor, 0),
                    attrs={"reason": "read_error", "detail": str(exc)},
                    provenance={
                        "artifact": anchor,
                        "artifact_sha256": "",
                        "extractor": EXTRACTOR_ID,
                    },
                )
            )
    return sort_facts(facts)


def _attribute_index(facts: list[Fact]) -> dict[tuple[str, str, str], Any]:
    """`(recurso, bloco, chave) -> valor` dos `tf.attribute` literais.

    A chave NAO inclui arquivo nem linha: mover o recurso de `main.tf` para
    `glue.tf`, ou empurrar o bloco dez linhas para baixo, nao e mudanca de
    configuracao -- e seria lida como uma se a identidade do atributo
    dependesse da localizacao.
    """
    index: dict[tuple[str, str, str], Any] = {}
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        symbol = fact.subject.get("symbol", "")
        key = fact.attrs.get("key", "")
        block = fact.attrs.get("block", "")
        index[(symbol, block, key)] = fact.attrs.get("value")
    return index


def extract_terraform_diff(
    before: Path, after: Path, repo_root: Path | None = None
) -> list[Fact]:
    """Facts do lado DEPOIS, anotados com o que mudou em relacao ao ANTES.

    Recebe dois diretorios -- dois checkouts, dois `git worktree`, o `main` e o
    branch do PR -- e nao a saida de `terraform plan`: rodar terraform exige
    backend e credencial, e o nucleo deste pacote e offline. O preco e conhecido
    e esta declarado aqui: valor que vem de variavel ou de modulo aparece como
    `tf.unresolved` nos dois lados e nao entra na comparacao. O diff cobre o que
    esta escrito no HCL, que e o que o revisor do PR ve.

    So os facts do lado DEPOIS voltam. Devolver os dois lados faria toda regra
    existente contar cada recurso duas vezes -- SF-GLUE-002, por exemplo,
    acusaria observabilidade ausente no estado antigo, que ninguem pode mais
    consertar.

    `attrs.changed` e emitido em TODO `tf.attribute` deste caminho, `false`
    inclusive. Marcar so os alterados tornaria indistinguivel "nao mudou" de
    "esta extracao nao sabe se mudou", que e o estado dos facts do
    `extract_terraform_tree` normal -- e uma regra com `where: {changed: true}`
    nunca deve casar por acidente num fact que nao veio de um diff.
    """
    # Cada lado e ancorado na PROPRIA raiz. O lado "antes" costuma estar fora
    # da arvore do "depois" -- outro checkout, outro worktree -- e ancora-lo em
    # `repo_root` levanta `ValueError: is not in the subpath of`. Os paths do
    # lado antigo nunca aparecem no resultado: eles so alimentam o indice de
    # comparacao, cuja chave e (recurso, bloco, atributo), sem arquivo.
    before_index = _attribute_index(extract_terraform_tree(before, before))
    after_facts = extract_terraform_tree(after, repo_root or after)

    annotated: list[Fact] = []
    for fact in after_facts:
        if fact.kind != "tf.attribute":
            annotated.append(fact)
            continue

        identity = (
            fact.subject.get("symbol", ""),
            fact.attrs.get("block", ""),
            fact.attrs.get("key", ""),
        )
        attrs = dict(fact.attrs)
        if identity in before_index:
            previous = before_index[identity]
            attrs["changed"] = previous != fact.attrs.get("value")
            if attrs["changed"]:
                attrs["previous_value"] = previous
        else:
            # Atributo que nao existia antes. E mudanca, e o valor anterior nao
            # e `None` nem `""` -- e ausencia, e `previous_value` fica de fora
            # em vez de fingir um valor que nunca existiu.
            attrs["changed"] = True
            attrs["previously_absent"] = True

        annotated.append(
            Fact(
                kind=fact.kind,
                subject=fact.subject,
                measures=fact.measures,
                attrs=attrs,
                provenance=fact.provenance,
            )
        )

    return sort_facts(annotated)
