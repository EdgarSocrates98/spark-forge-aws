"""Extrator de Facts a partir do arquivo `.py` de um DAG do Apache Airflow.

Le o DAG com `ast.parse` e NUNCA o importa nem o executa: importar um modulo de DAG
executa o codigo do operador e do que ele importa, e este repositorio nao executa
artefato analisado (D1 de `docs/sdd/AIRFLOW_DAG/design.md`). Molde de leitura de
Python: `sparkforge/facts/pyspark_ast.py`. Molde de dominio novo inteiro:
`sparkforge/facts/stepfunctions.py`.

Como `stepfunctions.py`, NAO coleta nada e NUNCA levanta excecao por arquivo
malformado: o que nao consegue ler vira `af.unresolved` com `attrs.reason`, e a
sentinela `af.analyzed` sai sempre, uma por arquivo.

## Por que `af.`

E o prefixo curto de Airflow, e nenhum kind existente comeca com ele (D1).

## O que sai

- `af.dag` -- um por chamada `DAG(...)` lida. `attrs.dag_id` e `attrs.schedule` so
  aparecem quando sao literais; `measures.default_retries` e
  `measures.default_execution_timeout_seconds`, quando `default_args` e legivel.
- `af.task` -- um por operador instanciado. O `subject` NAO afirma simbolo: ancora
  `file` e `line`, como o `sfn.task` faz, porque `task_id` e variavel de modulo e
  `subject.symbol` promete simbolo que o indice de codigo tem. `attrs.task_id` traz
  o `task_id` literal quando ha um, e `attrs.var_name` sempre o nome da variavel,
  que e por onde as dependencias se referem a task.
- `af.dependency` -- um por elo declarado por `>>`, `<<`, `set_downstream` ou
  `set_upstream`, com `attrs.form` dizendo qual das quatro formas o declarou.
- `af.unresolved` -- o que nao deu para ler. Razoes: `invalid_python`, `read_error`,
  `size_above_limit`, `dag_dinamico`, `operador_em_funcao`, `taskflow_decorador`,
  `multiplos_dags`, `arg_nao_literal`, `dependencia_dinamica` e `task_id_nao_literal`.
- `af.analyzed` -- a sentinela, com as contagens.
- `af.glue_job_link` -- DERIVADO, nunca lido de arquivo: `build_af_glue_link` liga a
  task do `GlueJobOperator` ao `aws_glue_job` de mesmo `name` quando os dois estao no
  pool, e `fusion.fuse` a chama (D5). As razoes de `af.unresolved` que so ela emite:
  `job_name_dynamic`, `job_name_absent`, `job_definition_absent`,
  `job_definition_ambiguous` e `glue_max_retries_not_literal`.

Nenhum fact deste modulo carrega `subject.snippet`: `tests/test_harness_untrusted.py`
mede quais extratores produzem snippet, e este nao entra em `EXTRATORES_COM_SNIPPET`.

## O que e "operador", e como se sabe

A leitura adotada, escrita aqui porque e uma escolha: chamada cujo nome termina em
`Operator` ou em `Sensor`. E estrutural (nao executa nada, nao resolve import) e casa
a convencao que o Airflow publica e que todo provider segue. O que ela NAO alcanca e
a TaskFlow API (`@task`, `@dag`), e por isso o decorador nao e lido como operador: ele
sai em `af.unresolved` com `taskflow_decorador`, nomeado em vez de adivinhado (a
TaskFlow esta fora de escopo no `define`).

`GlueJobOperator` e o legado `AwsGlueJobOperator` recebem `attrs.operator_family:
glue_job`; qualquer outro operador entra com familia vazia. A familia e o predicado
que as regras leem -- derivar aqui e o que a regra 33 exige, porque
`sparkforge/rules/expr.py` nao tem funcao e `where` so compara por igualdade.

## Os defaults publicados moram AQUI, com a fonte ao lado

A regra nao sabe o default. O fact grava o valor EFETIVO e a marca de que ele foi
omitido (D2), e argumento que NAO e literal deixa o atributo AUSENTE -- nunca o
default para o que ninguem leu.

## `execution_timeout` e a excecao declarada a essa frase

A regra `SF-AIRFLOW-002` julga a DECLARACAO de `execution_timeout`, nao o valor dele.
A presenca da palavra-chave e lida do AST com exatidao, e vira
`attrs.execution_timeout_declared`. O valor so vira `measures.execution_timeout_seconds`
quando e `timedelta(**literais)` -- a forma que a documentacao ensina --, e quando nao
e, a medida fica ausente SEM `af.unresolved`, porque nada do que a regra le deixou de
ser lido. Tratar `timedelta(...)` como nao literal deixaria a regra calada em todo DAG
real, que e o modo de falha que esta escolha evita.
"""
from __future__ import annotations

import ast
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.facts import scan
from sparkforge.facts.glue_terraform import glue_jobs_por_nome, glue_max_retries
from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "airflow_dag@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "af.dag",
        "af.task",
        "af.dependency",
        "af.unresolved",
        "af.analyzed",
        "af.glue_job_link",
    }
)

# O que liga a derivacao em `fusion.fuse`: sem `af.task` no pool, o `fuse` sai byte a
# byte igual ao de antes (molde de `timeout_diagnosis.SOURCE_KINDS`).
SOURCE_KINDS = frozenset({"af.task"})

# As duas origens de `job_name` que a derivacao recusa por serem resolvidas em
# execucao. `absent` e diferente das duas: o argumento nem foi escrito.
_ORIGENS_DINAMICAS = frozenset({"jinja", "nao_literal"})

# https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html
# wait_for_completion (default True): "Whether to wait for job run completion".
DEFAULT_WAIT_FOR_COMPLETION = True
# deferrable (default False): "If True, the operator will wait asynchronously for the
# job to complete".
DEFAULT_DEFERRABLE = False
# stop_job_run_on_kill (default False): "If True, Operator will stop the job run when
# task is killed".
DEFAULT_STOP_JOB_RUN_ON_KILL = False
# job_poll_interval (default 6). Nenhuma regra o julga; fica declarado porque o default
# publicado tem que morar ao lado da fonte que o publica.
DEFAULT_JOB_POLL_INTERVAL = 6
# https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html
# core.default_task_retries (default 0): "The number of retries each task is going to
# have by default".
DEFAULT_TASK_RETRIES = 0

_GLUE_OPERATORS = frozenset({"GlueJobOperator", "AwsGlueJobOperator"})
_TASKFLOW_DECORADORES = frozenset({"task", "dag", "task_group"})
_METODOS_DE_DEPENDENCIA = frozenset({"set_downstream", "set_upstream"})
_FUNCOES_DE_DEPENDENCIA = frozenset({"chain", "chain_linear", "cross_downstream"})
_BOOLEANOS_DO_GLUE = (
    ("wait_for_completion", DEFAULT_WAIT_FOR_COMPLETION),
    ("deferrable", DEFAULT_DEFERRABLE),
    ("stop_job_run_on_kill", DEFAULT_STOP_JOB_RUN_ON_KILL),
)
_SEGUNDOS_POR_UNIDADE = {
    "weeks": 604800,
    "days": 86400,
    "hours": 3600,
    "minutes": 60,
    "seconds": 1,
}

# Sentinela de "nao e literal". `None` nao serve: `x=None` e um valor que o DAG pode
# escrever, e confundir os dois faria o extrator afirmar leitura que nao houve.
_AUSENTE = object()


@dataclass
class _Tarefa:
    """O que se leu de UMA instanciacao de operador, antes de virar Fact.

    `has_downstream` so e conhecido depois de ler as dependencias, e por isso a
    tarefa espera aqui em vez de sair Fact na hora.
    """

    symbol: str
    var_name: str
    node: ast.AST
    attrs: dict[str, Any]
    measures: dict[str, Any]


@dataclass
class _Leitura:
    """O estado de UM arquivo sendo lido: onde, com que `default_args`, e o que saiu."""

    path: str
    provenance: dict[str, Any]
    facts: list[Fact] = field(default_factory=list)
    tarefas: list[_Tarefa] = field(default_factory=list)
    com_downstream: set[str] = field(default_factory=set)
    default_args: ast.Dict | None = None
    default_args_legivel: bool = True


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _node_subject(path: str, node: ast.AST, symbol: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": getattr(node, "lineno", 0),
        "col": getattr(node, "col_offset", 0),
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(path: str, sha: str) -> dict[str, Any]:
    return {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}


def _unresolved(
    subject: dict[str, Any], reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="af.unresolved",
        subject=subject,
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _nome_chamado(node: ast.Call) -> str:
    """`GlueJobOperator(...)` e `glue.GlueJobOperator(...)` dao o mesmo nome curto."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _nome_decorador(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _nome_chamado(node)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _e_operador(nome: str) -> bool:
    return nome.endswith("Operator") or nome.endswith("Sensor")


def _literal(node: ast.AST | None) -> Any:
    """Valor quando o no e constante simples; `_AUSENTE` caso contrario."""
    if isinstance(node, ast.Constant) and isinstance(node.value, bool | int | float | str):
        return node.value
    return _AUSENTE


def _e_jinja(valor: Any) -> bool:
    """String com `{{ }}` e template do Airflow, resolvido em execucao -- nao e nome."""
    return isinstance(valor, str) and "{{" in valor and "}}" in valor


def _kwarg(node: ast.Call, nome: str) -> ast.AST | None:
    for kw in node.keywords:
        if kw.arg == nome:
            return kw.value
    return None


def _do_dict(no_dict: ast.Dict, chave: str) -> ast.AST | None:
    """Valor de uma chave literal num `ast.Dict`. Chave de `**spread` e `None`, e cai fora."""
    for chave_no, valor_no in zip(no_dict.keys, no_dict.values, strict=True):
        if isinstance(chave_no, ast.Constant) and chave_no.value == chave:
            return valor_no
    return None


def _timedelta_segundos(node: ast.AST | None) -> int | None:
    """Segundos de `timedelta(**literais)`; `None` para qualquer outra forma.

    So palavras-chave, e so as unidades inteiras: `timedelta(2)` posicional e
    `milliseconds=...` ficam de fora de proposito -- a medida so existe quando e exata.
    """
    if not isinstance(node, ast.Call) or _nome_chamado(node) != "timedelta" or node.args:
        return None
    total = 0
    for kw in node.keywords:
        if kw.arg not in _SEGUNDOS_POR_UNIDADE:
            return None
        valor = _literal(kw.value)
        if isinstance(valor, bool) or not isinstance(valor, int):
            return None
        total += valor * _SEGUNDOS_POR_UNIDADE[kw.arg]
    return total


class _Escopo:
    """No -> profundidade de laco e se esta dentro de `def`.

    Pilha explicita e nao recursao, pelo mesmo motivo de `pyspark_ast._Context`: um
    modulo com expressao profunda estouraria o limite de pilha do interpretador.
    """

    def __init__(self, tree: ast.AST) -> None:
        self.loop_depth: dict[int, int] = {}
        self.in_function: dict[int, bool] = {}
        pilha: list[tuple[ast.AST, int, bool]] = [(tree, 0, False)]
        while pilha:
            node, profundidade, dentro = pilha.pop()
            self.loop_depth[id(node)] = profundidade
            self.in_function[id(node)] = dentro
            proxima = profundidade
            if isinstance(
                node,
                ast.For
                | ast.AsyncFor
                | ast.While
                | ast.ListComp
                | ast.SetComp
                | ast.DictComp
                | ast.GeneratorExp,
            ):
                proxima = profundidade + 1
            interna = dentro or isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            for filho in ast.iter_child_nodes(node):
                pilha.append((filho, proxima, interna))

    def dinamico(self, node: ast.AST) -> bool:
        """DAG ou operador montado em laco, comprehension ou funcao: fora do alcance."""
        return self.em_laco(node) or self.em_funcao(node)

    def em_laco(self, node: ast.AST) -> bool:
        return self.loop_depth.get(id(node), 0) > 0

    def em_funcao(self, node: ast.AST) -> bool:
        """Dentro de `def`/`async def` -- inclusive a funcao decorada com `@dag`."""
        return self.in_function.get(id(node), False)


def _alvos_de_atribuicao(tree: ast.AST) -> dict[int, str]:
    """`id` da chamada -> nome da variavel a que ela foi atribuida.

    As dependencias se referem as tasks pelo nome da VARIAVEL, nao pelo `task_id`.
    Cobre `x = Op(...)`, `x: T = Op(...)` e `with DAG(...) as x:`.
    """
    alvos: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Call):
                    alvos[id(node.value)] = node.targets[0].id
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and isinstance(node.value, ast.Call):
                alvos[id(node.value)] = node.target.id
        elif isinstance(node, ast.withitem):
            if isinstance(node.context_expr, ast.Call) and isinstance(
                node.optional_vars, ast.Name
            ):
                alvos[id(node.context_expr)] = node.optional_vars.id
    return alvos


def _dicts_de_modulo(tree: ast.Module) -> dict[str, ast.Dict]:
    """Nome -> dicionario literal, para `NOME = {...}` no nivel de modulo.

    `default_args=DEFAULT_ARGS` e a forma comum, e ela e legivel por AST sem executar
    nada. So entra o nome atribuido UMA vez: reatribuido, nao se sabe qual valor vale.
    """
    contagem: dict[str, int] = {}
    valores: dict[str, ast.Dict] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        alvo = node.targets[0]
        if not isinstance(alvo, ast.Name):
            continue
        contagem[alvo.id] = contagem.get(alvo.id, 0) + 1
        if isinstance(node.value, ast.Dict):
            valores[alvo.id] = node.value
    return {nome: no for nome, no in valores.items() if contagem.get(nome) == 1}


def _le_dags(tree: ast.AST, leitura: _Leitura, escopo: _Escopo, alvos: dict[int, str],
             dicts: dict[str, ast.Dict]) -> None:
    """Emite um `af.dag` por chamada `DAG(...)` lida, e fixa o `default_args` do arquivo.

    Com DOIS ou mais DAGs no arquivo nao ha como dizer de qual deles vem o
    `default_args` de uma task: `default_args` fica ILEGIVEL para o arquivo inteiro e a
    lacuna sai como `multiplos_dags`. Adivinhar o primeiro seria afirmar heranca que
    ninguem leu.
    """
    blocos: list[ast.Dict | None] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _nome_chamado(node) != "DAG":
            continue
        var = alvos.get(id(node), "")
        if escopo.dinamico(node):
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, var),
                    "dag_dinamico",
                    leitura.provenance,
                    at="DAG",
                    unblocked_by="DAG declarado no nivel de modulo, fora de laco e de funcao",
                )
            )
            continue
        dag_id = _literal(_kwarg(node, "dag_id"))
        attrs: dict[str, Any] = {"dag_id_literal": isinstance(dag_id, str)}
        if isinstance(dag_id, str):
            attrs["dag_id"] = dag_id
        agenda_no, origem = _kwarg(node, "schedule"), "schedule"
        if agenda_no is None:
            agenda_no, origem = _kwarg(node, "schedule_interval"), "schedule_interval"
        agenda = _literal(agenda_no)
        attrs["schedule_declared"] = agenda_no is not None
        # A MARCA de literal sai sempre, como `dag_id_literal`: sem ela, `schedule`
        # ausente por ser `schedule=VARIAVEL` seria indistinguivel de nao declarado.
        attrs["schedule_literal"] = isinstance(agenda, str)
        attrs["schedule_source"] = origem if agenda_no is not None else "absent"
        if isinstance(agenda, str):
            attrs["schedule"] = agenda
        bruto = _kwarg(node, "default_args")
        bloco: ast.Dict | None = None
        if bruto is None:
            attrs["default_args_source"] = "absent"
        elif isinstance(bruto, ast.Dict):
            bloco, attrs["default_args_source"] = bruto, "inline"
        elif isinstance(bruto, ast.Name) and bruto.id in dicts:
            bloco, attrs["default_args_source"] = dicts[bruto.id], "module_name"
        else:
            attrs["default_args_source"] = "unreadable"
        measures: dict[str, Any] = {}
        retries = _literal(_do_dict(bloco, "retries")) if bloco is not None else _AUSENTE
        attrs["default_retries_declared"] = isinstance(retries, int) and not isinstance(
            retries, bool
        )
        if attrs["default_retries_declared"]:
            measures["default_retries"] = retries
        prazo = _do_dict(bloco, "execution_timeout") if bloco is not None else None
        attrs["default_execution_timeout_declared"] = prazo is not None
        segundos = _timedelta_segundos(prazo)
        if segundos is not None:
            measures["default_execution_timeout_seconds"] = segundos
        leitura.facts.append(
            Fact(
                kind="af.dag",
                subject=_node_subject(
                    leitura.path, node, dag_id if isinstance(dag_id, str) else var
                ),
                measures=measures,
                attrs=attrs,
                provenance=leitura.provenance,
            )
        )
        blocos.append(bloco if attrs["default_args_source"] != "unreadable" else None)
        if attrs["default_args_source"] == "unreadable":
            leitura.default_args_legivel = False
    if len(blocos) > 1:
        leitura.default_args, leitura.default_args_legivel = None, False
        leitura.facts.append(
            _unresolved(
                _file_subject(leitura.path),
                "multiplos_dags",
                leitura.provenance,
                dag_count=len(blocos),
                unblocked_by="um DAG por arquivo, ou `default_args` declarado na propria task",
            )
        )
    elif blocos:
        leitura.default_args = blocos[0]


def _le_decoradores(tree: ast.AST, leitura: _Leitura) -> None:
    """`@dag`, `@task` e `@task_group`: reconhecidos e NOMEADOS, nunca lidos."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        nomes = sorted({_nome_decorador(d) for d in node.decorator_list})
        usados = [n for n in nomes if n in _TASKFLOW_DECORADORES]
        if not usados:
            continue
        leitura.facts.append(
            _unresolved(
                _node_subject(leitura.path, node, node.name),
                "taskflow_decorador",
                leitura.provenance,
                decorators=usados,
                unblocked_by="operador instanciado como classe, fora da TaskFlow API",
            )
        )


def _le_bool(chamada: ast.Call, nome: str, default: bool, attrs: dict[str, Any],
             leitura: _Leitura, subject: dict[str, Any]) -> None:
    """`<nome>_effective` mais `<nome>_defaulted`, ou o nao literal nomeado (D2)."""
    valor_no = _kwarg(chamada, nome)
    if valor_no is None:
        attrs[f"{nome}_effective"] = default
        attrs[f"{nome}_defaulted"] = True
        return
    valor = _literal(valor_no)
    if not isinstance(valor, bool):
        leitura.facts.append(
            _unresolved(
                subject,
                "arg_nao_literal",
                leitura.provenance,
                arg=nome,
                unblocked_by=f"`{nome}` escrito como `True` ou `False` literal na task",
            )
        )
        return
    attrs[f"{nome}_effective"] = valor
    attrs[f"{nome}_defaulted"] = False


def _le_job_name(chamada: ast.Call, attrs: dict[str, Any], leitura: _Leitura,
                 subject: dict[str, Any]) -> None:
    """So o literal liga a task ao `aws_glue_job` de mesmo nome (D5)."""
    valor_no = _kwarg(chamada, "job_name")
    if valor_no is None:
        attrs["job_name_source"] = "absent"
        return
    valor = _literal(valor_no)
    if isinstance(valor, str) and valor.strip() and not _e_jinja(valor):
        attrs["job_name"] = valor
        attrs["job_name_source"] = "literal"
        return
    attrs["job_name_source"] = "jinja" if _e_jinja(valor) else "nao_literal"
    leitura.facts.append(
        _unresolved(
            subject,
            "arg_nao_literal",
            leitura.provenance,
            arg="job_name",
            job_name_source=attrs["job_name_source"],
            unblocked_by="`job_name` escrito como string literal na task",
        )
    )


def _le_retries(chamada: ast.Call, attrs: dict[str, Any], measures: dict[str, Any],
                leitura: _Leitura, subject: dict[str, Any]) -> None:
    """`retries` da task, senao de `default_args`, senao o default publicado (0)."""
    valor_no, origem = _kwarg(chamada, "retries"), "task"
    if valor_no is None and leitura.default_args is not None:
        valor_no, origem = _do_dict(leitura.default_args, "retries"), "default_args"
    if valor_no is None:
        if not leitura.default_args_legivel:
            leitura.facts.append(
                _unresolved(
                    subject,
                    "arg_nao_literal",
                    leitura.provenance,
                    arg="retries",
                    at="default_args",
                    unblocked_by="`default_args` legivel: um DAG por arquivo, dicionario literal",
                )
            )
            return
        measures["retries_effective"] = DEFAULT_TASK_RETRIES
        attrs["retries_source"] = "default_publicado"
        attrs["retries_defaulted"] = True
        return
    valor = _literal(valor_no)
    if isinstance(valor, bool) or not isinstance(valor, int):
        leitura.facts.append(
            _unresolved(
                subject,
                "arg_nao_literal",
                leitura.provenance,
                arg="retries",
                at=origem,
                unblocked_by="`retries` escrito como inteiro literal",
            )
        )
        return
    measures["retries_effective"] = valor
    attrs["retries_source"] = origem
    attrs["retries_defaulted"] = False


def _le_execution_timeout(chamada: ast.Call, attrs: dict[str, Any],
                          measures: dict[str, Any], leitura: _Leitura,
                          subject: dict[str, Any]) -> None:
    """A DECLARACAO e o que a regra le; o valor so vira medida quando e exato."""
    valor_no, origem = _kwarg(chamada, "execution_timeout"), "task"
    if valor_no is None and leitura.default_args is not None:
        valor_no = _do_dict(leitura.default_args, "execution_timeout")
        origem = "default_args"
    if isinstance(valor_no, ast.Constant) and valor_no.value is None:
        valor_no = None  # `execution_timeout=None` e a AUSENCIA declarada de prazo
    if valor_no is None:
        if not leitura.default_args_legivel:
            leitura.facts.append(
                _unresolved(
                    subject,
                    "arg_nao_literal",
                    leitura.provenance,
                    arg="execution_timeout",
                    at="default_args",
                    unblocked_by="`default_args` legivel: um DAG por arquivo, dicionario literal",
                )
            )
            return
        attrs["execution_timeout_declared"] = False
        attrs["execution_timeout_source"] = "absent"
        return
    attrs["execution_timeout_declared"] = True
    attrs["execution_timeout_source"] = origem
    segundos = _timedelta_segundos(valor_no)
    if segundos is not None:
        measures["execution_timeout_seconds"] = segundos


def _le_operadores(tree: ast.AST, leitura: _Leitura, escopo: _Escopo,
                   alvos: dict[int, str]) -> None:
    """Uma `_Tarefa` por operador instanciado. O Fact so sai depois das dependencias."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        classe = _nome_chamado(node)
        if not _e_operador(classe):
            continue
        var = alvos.get(id(node), "")
        if escopo.dinamico(node):
            # Laco e `def` sao lacunas DIFERENTES, e por isso tem razao diferente: o
            # laco monta N tasks que nao se sabe contar, e a funcao (tipicamente a
            # decorada com `@dag`) monta uma task que este extrator nao segue.
            em_laco = escopo.em_laco(node)
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, var),
                    "dag_dinamico" if em_laco else "operador_em_funcao",
                    leitura.provenance,
                    at=classe,
                    unblocked_by=(
                        "operador instanciado no nivel de modulo, fora de laco e def"
                        if em_laco
                        else "operador instanciado no nivel de modulo, fora de `def`"
                    ),
                )
            )
            continue
        task_id = _literal(_kwarg(node, "task_id"))
        simbolo = task_id if isinstance(task_id, str) and task_id.strip() else var
        subject = _node_subject(leitura.path, node, simbolo)
        attrs: dict[str, Any] = {
            "operator_class": classe,
            "operator_family": "glue_job" if classe in _GLUE_OPERATORS else "",
            "task_id_literal": isinstance(task_id, str),
            "var_name": var,
        }
        if isinstance(task_id, str):
            attrs["task_id"] = task_id
        else:
            leitura.facts.append(
                _unresolved(
                    subject,
                    "task_id_nao_literal",
                    leitura.provenance,
                    operator_class=classe,
                    unblocked_by="`task_id` escrito como string literal",
                )
            )
        measures: dict[str, Any] = {}
        _le_retries(node, attrs, measures, leitura, subject)
        _le_execution_timeout(node, attrs, measures, leitura, subject)
        if attrs["operator_family"] == "glue_job":
            _le_job_name(node, attrs, leitura, subject)
            for nome, default in _BOOLEANOS_DO_GLUE:
                _le_bool(node, nome, default, attrs, leitura, subject)
            espera = _literal(_kwarg(node, "job_poll_interval"))
            if isinstance(espera, int) and not isinstance(espera, bool):
                measures["job_poll_interval"] = espera
        leitura.tarefas.append(
            _Tarefa(symbol=simbolo, var_name=var, node=node, attrs=attrs, measures=measures)
        )


def _elos(node: ast.BinOp, tipo: type[ast.AST]) -> list[ast.AST]:
    """`a >> b >> c` e `BinOp(BinOp(a,b),c)`: devolve [a, b, c], com `while`, nao recursao."""
    saida: list[ast.AST] = []
    atual: ast.AST = node
    while isinstance(atual, ast.BinOp) and isinstance(atual.op, tipo):
        saida.append(atual.right)
        atual = atual.left
    saida.append(atual)
    saida.reverse()
    return saida


def _nomes_do_lado(node: ast.AST) -> list[str] | None:
    """Nomes de variavel de um lado do elo, ou `None` quando nao e legivel."""
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.List | ast.Tuple):
        nomes: list[str] = []
        for elemento in node.elts:
            if not isinstance(elemento, ast.Name):
                return None
            nomes.append(elemento.id)
        return nomes
    return None


def _emite_elo(leitura: _Leitura, mapa: dict[str, str], acima: ast.AST, abaixo: ast.AST,
               forma: str, node: ast.AST) -> None:
    ups, downs = _nomes_do_lado(acima), _nomes_do_lado(abaixo)
    if ups is None or downs is None:
        leitura.facts.append(
            _unresolved(
                _node_subject(leitura.path, node, ""),
                "dependencia_dinamica",
                leitura.provenance,
                form=forma,
                unblocked_by="elo entre variaveis de task, nao montado por lista dinamica",
            )
        )
        return
    for acima_var in ups:
        for abaixo_var in downs:
            resolvido = acima_var in mapa and abaixo_var in mapa
            um = mapa.get(acima_var, acima_var)
            outro = mapa.get(abaixo_var, abaixo_var)
            leitura.facts.append(
                Fact(
                    kind="af.dependency",
                    subject=_node_subject(leitura.path, node, f"{um} >> {outro}"),
                    attrs={
                        "upstream": um,
                        "downstream": outro,
                        "upstream_var": acima_var,
                        "downstream_var": abaixo_var,
                        "form": forma,
                        "resolved": resolvido,
                    },
                    provenance=leitura.provenance,
                )
            )
            if resolvido:
                leitura.com_downstream.add(um)


def _le_dependencias(tree: ast.AST, leitura: _Leitura, escopo: _Escopo) -> None:
    """As quatro formas declaradas, mais o que nao se le, nomeado.

    So `>>` e `<<` no NIVEL DE INSTRUCAO (`ast.Expr`): um `>>` dentro de outra
    expressao nao e declaracao de dependencia, e o de dentro de um laco cai em
    `dependencia_dinamica` pelo escopo.
    """
    mapa = {t.var_name: t.symbol for t in leitura.tarefas if t.var_name}
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.BinOp):
            operacao = node.value.op
            if not isinstance(operacao, ast.RShift | ast.LShift):
                continue
            if escopo.dinamico(node):
                leitura.facts.append(
                    _unresolved(
                        _node_subject(leitura.path, node, ""),
                        "dependencia_dinamica",
                        leitura.provenance,
                        form="rshift" if isinstance(operacao, ast.RShift) else "lshift",
                        unblocked_by="elo declarado fora de laco, entre variaveis de task",
                    )
                )
                continue
            direita = isinstance(operacao, ast.RShift)
            elos = _elos(node.value, ast.RShift if direita else ast.LShift)
            forma = "rshift" if direita else "lshift"
            for indice in range(len(elos) - 1):
                primeiro, segundo = elos[indice], elos[indice + 1]
                acima, abaixo = (primeiro, segundo) if direita else (segundo, primeiro)
                _emite_elo(leitura, mapa, acima, abaixo, forma, node)
            continue
        if not isinstance(node, ast.Call):
            continue
        nome = _nome_chamado(node)
        # `chain(a, b)` e `baseoperator.chain(a, b)` sao a MESMA declaracao, e o
        # extrator nao le nenhuma das duas: sem este ramo, a forma com ponto sumia em
        # silencio, porque `chain` nao esta em `_METODOS_DE_DEPENDENCIA`. As duas
        # familias sao disjuntas, e por isso o nome basta para decidir.
        if nome in _FUNCOES_DE_DEPENDENCIA:
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, ""),
                    "dependencia_dinamica",
                    leitura.provenance,
                    form=nome,
                    unblocked_by="elo declarado por `>>`, `<<`, `set_downstream` ou `set_upstream`",
                )
            )
            continue
        if nome not in _METODOS_DE_DEPENDENCIA or not isinstance(node.func, ast.Attribute):
            continue
        if escopo.dinamico(node) or len(node.args) != 1:
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, ""),
                    "dependencia_dinamica",
                    leitura.provenance,
                    form=nome,
                    unblocked_by="chamada com um argumento so, fora de laco",
                )
            )
            continue
        alvo, outro = node.func.value, node.args[0]
        acima, abaixo = (alvo, outro) if nome == "set_downstream" else (outro, alvo)
        _emite_elo(leitura, mapa, acima, abaixo, nome, node)


def _emite_tarefas(leitura: _Leitura) -> None:
    """Agora que as dependencias foram lidas, `has_downstream` e conhecido."""
    for tarefa in leitura.tarefas:
        attrs = {**tarefa.attrs, "has_downstream": tarefa.symbol in leitura.com_downstream}
        leitura.facts.append(
            Fact(
                kind="af.task",
                # Sem `symbol`: `task_id` e variavel de modulo, e `subject.symbol`
                # promete simbolo INDEXADO daquele arquivo (`economy/goldset.py`
                # segue `evidence -> subject.{file, symbol}` e o exige no indice).
                # A task se identifica por localizacao, como `sfn.task`; o
                # `task_id` mora em `attrs`, e o agrupamento interno abaixo
                # continua usando `tarefa.symbol`, que nunca sai no fact.
                subject=_node_subject(leitura.path, tarefa.node, ""),
                measures=dict(tarefa.measures),
                attrs=attrs,
                provenance=leitura.provenance,
            )
        )


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho em todo caminho."""
    facts.append(
        Fact(
            kind="af.analyzed",
            subject=_file_subject(path),
            measures={
                "dag_count": sum(1 for f in facts if f.kind == "af.dag"),
                "task_count": sum(1 for f in facts if f.kind == "af.task"),
                "dependency_count": sum(1 for f in facts if f.kind == "af.dependency"),
                "unresolved_count": sum(1 for f in facts if f.kind == "af.unresolved"),
            },
            provenance=provenance,
        )
    )
    desconhecidos = {f.kind for f in facts} - EMITTED_KINDS
    if desconhecidos:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(desconhecidos)}")
    return sort_facts(facts)


def extract_airflow_dag(source: str, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts do TEXTO de um DAG. `path` e ancora e procedencia.

    `ast.parse` levanta `SyntaxError` para Python invalido, `ValueError` para fonte com
    byte nulo e `RecursionError`/`MemoryError` para aninhamento extremo -- o parser do
    CPython usa "Parser stack overflowed" em vez de `RecursionError` conforme a versao,
    e os dois significam a mesma coisa para o operador. Os quatro viram
    `af.unresolved`, nunca excecao que derruba quem chamou.
    """
    provenance = _provenance(path, artifact_sha256)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        falha = _unresolved(
            {
                "type": "source_location",
                "file": path,
                "line": exc.lineno or 0,
                "col": exc.offset or 0,
                "symbol": "",
                "snippet": "",
            },
            "invalid_python",
            provenance,
            detail=str(exc.msg),
        )
        return _finish([falha], path, provenance)
    except (ValueError, RecursionError, MemoryError) as exc:
        falha = _unresolved(
            _file_subject(path), "invalid_python", provenance, detail=str(exc)
        )
        return _finish([falha], path, provenance)
    leitura = _Leitura(path=path, provenance=provenance)
    try:
        escopo = _Escopo(tree)
        alvos = _alvos_de_atribuicao(tree)
        _le_dags(tree, leitura, escopo, alvos, _dicts_de_modulo(tree))
        _le_decoradores(tree, leitura)
        _le_operadores(tree, leitura, escopo, alvos)
        _le_dependencias(tree, leitura, escopo)
        _emite_tarefas(leitura)
    except (RecursionError, MemoryError) as exc:
        falha = _unresolved(_file_subject(path), "read_error", provenance, detail=str(exc))
        return _finish([falha], path, provenance)
    return _finish(leitura.facts, path, provenance)


def extract_airflow_dag_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.py`, ancorando o caminho relativo a `repo_root`.

    Arquivo acima do teto de `scan._teto_para` -- o MESMO que a varredura aplica -- sai
    `size_above_limit`; falha ao abrir ou a decodificar, `read_error`. Le com
    `utf-8-sig`: sem isso um DAG salvo com BOM falharia o parse e seria reportado como
    ponto cego por engano.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    vazio = _provenance(anchor, "")
    try:
        tamanho, teto = path.stat().st_size, scan._teto_para(path)
        if tamanho > teto:
            falha = _unresolved(
                _file_subject(anchor), "size_above_limit", vazio, size=tamanho, limit=teto
            )
            return _finish([falha], anchor, vazio)
        texto = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
        return _finish([falha], anchor, vazio)
    sha = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    return extract_airflow_dag(texto, anchor, artifact_sha256=sha)


def extract_airflow_dag_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todo `*.py` sob `root`, em ordem deterministica de caminho.

    Falha por arquivo nao e fatal: vira `af.unresolved` daquele arquivo e a travessia
    continua.
    """
    facts: list[Fact] = []
    for arquivo in iter_source_files(root, "*.py"):
        rel = str(arquivo.relative_to(repo_root)) if repo_root else str(arquivo)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_airflow_dag_path(arquivo, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            vazio = _provenance(anchor, "")
            falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
            facts.extend(_finish([falha], anchor, vazio))
    return sort_facts(facts)


def build_af_glue_link(facts: Sequence[Fact]) -> list[Fact]:
    """Liga cada `af.task` do `GlueJobOperator` ao `aws_glue_job` de mesmo `name` (D5).

    Derivacao pura sobre a UNIAO dos facts, no molde de `build_sfn_glue_link`: o motor
    avalia um fact por condicao, e os dois lados tem `subject` diferente -- a task do
    DAG e o recurso do Terraform --, entao `same_subject` nao os junta. Nao liga por
    substring: nome de job e chave exata na API do Glue.

    `airflow_retries_effective` e o `retries_effective` da task: o da propria task, ou
    o de `default_args`, ou o default publicado (`core.default_task_retries`, 0). O que
    nao liga sai nomeado em `af.unresolved`, nunca como vinculo.
    """
    nomes = glue_jobs_por_nome(facts)
    saida: list[Fact] = []
    for task in facts:
        attrs = task.attrs or {}
        if task.kind != "af.task" or attrs.get("operator_family") != "glue_job":
            continue
        proveniencia: dict[str, Any] = {
            "artifact": str((task.provenance or {}).get("artifact", "")),
            "artifact_sha256": "",
            "extractor": EXTRACTOR_ID,
            "derived_from": [task.id],
        }
        nome = attrs.get("job_name")
        if not isinstance(nome, str):
            origem = str(attrs.get("job_name_source", ""))
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "job_name_dynamic" if origem in _ORIGENS_DINAMICAS else "job_name_absent",
                    proveniencia,
                    job_name_source=origem,
                    unblocked_by="`job_name` escrito como string literal na task",
                )
            )
            continue
        candidatos = nomes.get(nome, [])
        if len(candidatos) != 1:
            razao = "job_definition_absent" if not candidatos else "job_definition_ambiguous"
            saida.append(
                _unresolved(
                    dict(task.subject),
                    razao,
                    proveniencia,
                    job_name=nome,
                    resources=[simbolo for _, simbolo, _ in candidatos],
                    unblocked_by="sparkforge analyze terraform no aws_glue_job, e fuse",
                )
            )
            continue
        arquivo, simbolo, nome_id = candidatos[0]
        origem, retries, retries_id = glue_max_retries(facts, arquivo, simbolo)
        usados = [nome_id] + ([retries_id] if retries_id is not None else [])
        proveniencia = {**proveniencia, "derived_from": [task.id, *usados]}
        measures: dict[str, Any] = {}
        efetivo = (task.measures or {}).get("retries_effective")
        if efetivo is not None:
            measures["airflow_retries_effective"] = efetivo
        if retries is not None:
            measures["glue_max_retries"] = retries
        saida.append(
            Fact(
                kind="af.glue_job_link",
                subject=dict(task.subject),
                measures=measures,
                attrs={
                    "job_name": nome,
                    "resource": simbolo,
                    "resource_file": arquivo,
                    "glue_max_retries_source": origem,
                    "airflow_retries_defaulted": bool(attrs.get("retries_defaulted")),
                },
                provenance=proveniencia,
            )
        )
        if origem == "not_literal":
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "glue_max_retries_not_literal",
                    proveniencia,
                    job_name=nome,
                    resource=simbolo,
                    unblocked_by="`max_retries` escrito como numero literal no aws_glue_job",
                )
            )
    return sort_facts(saida)


__all__ = [
    "DEFAULT_DEFERRABLE",
    "DEFAULT_JOB_POLL_INTERVAL",
    "DEFAULT_STOP_JOB_RUN_ON_KILL",
    "DEFAULT_TASK_RETRIES",
    "DEFAULT_WAIT_FOR_COMPLETION",
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "SOURCE_KINDS",
    "build_af_glue_link",
    "extract_airflow_dag",
    "extract_airflow_dag_path",
    "extract_airflow_dag_tree",
]
