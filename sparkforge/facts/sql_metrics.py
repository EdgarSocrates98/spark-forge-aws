"""Extrator de metricas SQL por no do plano, a partir do Spark event log.

O MESMO artefato que `facts/event_log.py` le, com outra pergunta. Aquele
responde "quanto cada stage custou"; este responde "quanto cada FONTE custou".
Modulo separado pelo precedente que o repositorio ja tem: `data_quality` e
`graph` leem o mesmo `.py` que `pyspark_ast`, cada um com o seu vocabulario.

O que liga os dois lados ja esta dentro do arquivo, e ninguem lia:
`SparkListenerSQLExecutionStart` carrega `sparkPlanInfo`, a arvore do plano com
os `accumulatorId` de cada metrica; os valores chegam depois, em
`SparkListenerDriverAccumUpdates` (driver) e nos `Accumulables` de
`SparkListenerTaskEnd` (tarefa, somando `Update`, nunca o `Value` corrente).
Esta Task (4 de 9) atribui esses valores ao no que os publicou. Acumulador de
no reatribuido ou sem no continua fora de qualquer measure -- ele so soma em
`unattributed_accumulators`, no fact `spark.sql.analyzed`. AQE e as recusas
estruturadas sao a Task 5.

Streaming, uma passada, como `extract_event_log`: o insumo pode ter centenas de
MB, e uma unica linha de `SQLExecutionStart` carrega o
`physicalPlanDescription` inteiro.

Puro e deterministico: nunca aplica limiar, nunca atribui severidade, nunca
toca a rede.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from sparkforge.facts.secrets import redact
from sparkforge.facts.sql_metric_names import measure_for
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "sql_metrics@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "spark.sql.scan",
        "spark.sql.execution",
        "spark.sql.unresolved",
        "spark.sql.analyzed",
    }
)

_SQL_START = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart"
_SQL_AQE = "org.apache.spark.sql.execution.ui.SparkListenerSQLAdaptiveExecutionUpdate"
_SQL_END = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd"
_DRIVER_ACCUM = "org.apache.spark.sql.execution.ui.SparkListenerDriverAccumUpdates"
_TASK_END = "SparkListenerTaskEnd"

# Mesma distincao que `spark_plan.py` faz sobre o texto do `explain`, aplicada
# aqui sobre `simpleString`. Reescrita em vez de importada pela razao ja
# registrada em `iceberg_metadata.py`: os extratores sao modulos independentes
# por desenho, e o que garante que os dois concordam e teste, nao import.
# O token de formato precisa comecar em MINUSCULA: `Scan` tambem prefixa
# operadores que nao leem arquivo (`Scan ExistingRDD`, `Scan OneRowRelation`).
_SCAN_V1_RE = re.compile(r"^(?:File)?Scan\s+([a-z][\w-]*)\s+([^\[\s]+)")
_SCAN_V2_RE = re.compile(r"^BatchScan\s+([^\[\s]+)")


def _scan_of(node: dict[str, Any]) -> tuple[str, str, str] | None:
    """Devolve `(scan_api, relation, format)` se o no le arquivo, senao `None`."""
    simple = str(node.get("simpleString") or "").strip()
    formato = str((node.get("metadata") or {}).get("Format") or "").lower()

    casou_v2 = _SCAN_V2_RE.match(simple)
    if casou_v2:
        return "v2", casou_v2.group(1), formato

    casou_v1 = _SCAN_V1_RE.match(simple)
    if casou_v1:
        return "v1", casou_v1.group(2), formato or casou_v1.group(1)

    return None


def _walk(node: dict[str, Any], proximo: list[int]) -> Iterator[tuple[int, dict[str, Any]]]:
    """Percorre a arvore em preorder, numerando os nos.

    O `sparkPlanInfo` NAO carrega id de no. O indice de preorder e a
    identidade que este extrator constroi, e ela e estavel para a mesma
    arvore: raiz = 0, e cada filho na ordem em que o Spark os escreveu.
    Numerar de outro jeito -- por hash do texto, por exemplo -- faria dois
    nos identicos em ramos diferentes colidirem.
    """
    meu = proximo[0]
    proximo[0] += 1
    yield meu, node
    for filho in node.get("children") or []:
        yield from _walk(filho, proximo)


class _Execution:
    """Estado acumulado de uma execucao SQL durante a passada.

    `accum` e `reassigned` guardam o mapa `accumulatorId -> (node_id, nome)`
    que a Task 4 vai consumir para atribuir valores. Nenhum valor entra aqui
    ainda: este extrator so registra ONDE cada acumulador vive na arvore.
    """

    def __init__(self, execution_id: int, description: str) -> None:
        self.execution_id = execution_id
        self.description, self.redacted = redact("description", description)
        self.plan_source = "initial"
        self.nodes: dict[int, dict[str, Any]] = {}
        self.nodes_total = 0
        # accumulatorId -> (node_id, nome publicado da metrica)
        self.accum: dict[int, tuple[int, str]] = {}
        self.reassigned: set[int] = set()
        self.values: dict[int, float] = {}
        self.ended = False
        # Mapa acumulado de TODAS as arvores desta execucao. `accum` guarda a
        # arvore corrente, que e quem define identidade de no; este guarda o
        # que ja foi declarado antes, para que um valor medido sob o plano
        # inicial nao evapore quando o AQE repoe a arvore.
        self.accum_historico: dict[int, tuple[int, str]] = {}

    def add_value(self, accum_id: int, valor: float) -> bool:
        """Soma um valor a um acumulador conhecido. Devolve se ele foi atribuido."""
        if accum_id in self.reassigned:
            return False
        if accum_id not in self.accum and accum_id not in self.accum_historico:
            return False
        self.values[accum_id] = self.values.get(accum_id, 0.0) + valor
        return True

    def measures_by_node(
        self,
    ) -> tuple[dict[int, dict[str, Any]], list[tuple[int, str]], list[int]]:
        """`{node_id: {measure: valor}}`, os nomes fora do mapa, e os orfaos.

        Um acumulador declarado numa arvore anterior continua valendo se o
        `node_id` dele ainda existe no plano corrente: o valor foi medido, e o
        no e o mesmo. Se o no sumiu, o valor nao tem onde pousar -- e isso vira
        lacuna nomeada, nunca silencio.
        """
        conhecidos: dict[int, tuple[int, str]] = dict(self.accum_historico)
        conhecidos.update(self.accum)

        por_no: dict[int, dict[str, Any]] = {}
        desconhecidos: list[tuple[int, str]] = []
        orfaos: list[int] = []
        for accum_id, (node_id, nome) in sorted(conhecidos.items()):
            if accum_id not in self.values:
                # Metrica declarada no plano e nunca publicada. Ausencia, nao zero.
                continue
            if node_id not in self.nodes:
                orfaos.append(accum_id)
                continue
            measure = measure_for(nome)
            if measure is None:
                desconhecidos.append((node_id, nome))
                continue
            valor = self.values[accum_id]
            por_no.setdefault(node_id, {})[measure] = (
                int(valor) if float(valor).is_integer() else valor
            )
        return por_no, desconhecidos, orfaos

    def absorb_plan(self, plano: dict[str, Any], source: str) -> None:
        """Substitui a arvore corrente por `plano`, preservando o que veio antes.

        Sob AQE isto e chamado mais de uma vez para a mesma execucao. `nodes` e
        `accum` sao reconstruidos do zero porque descrevem a arvore CORRENTE --
        identidade de no e por indice de preorder, e o indice muda quando a
        arvore muda. Mas um valor ja publicado contra a arvore anterior foi
        medido sob aquele plano e continua valendo: por isso `accum` de antes
        de resetar entra em `accum_historico`, que `measures_by_node` tambem
        consulta.
        """
        self.plan_source = source
        self.nodes = {}
        self.nodes_total = 0
        for node_id, node in _walk(plano, [0]):
            self.nodes_total += 1
            scan = _scan_of(node)
            if scan is None:
                continue
            api, relation, formato = scan
            self.nodes[node_id] = {
                "node_name": str(node.get("nodeName") or "").strip(),
                "relation": relation,
                "scan_api": api,
                "format": formato,
            }

        self.accum_historico.update(self.accum)
        self.accum = {}
        self.reassigned = set()
        for node_id, node in _walk(plano, [0]):
            for metrica in node.get("metrics") or []:
                accum_id = metrica.get("accumulatorId")
                nome = str(metrica.get("name") or "")
                if not isinstance(accum_id, int):
                    continue
                anterior = self.accum.get(accum_id)
                if anterior is not None and anterior[0] != node_id:
                    # O mesmo acumulador em dois nos: atribuir a qualquer um
                    # poria bytes no no errado, e o relatorio ficaria plausivel
                    # e falso.
                    self.reassigned.add(accum_id)
                    continue
                self.accum[accum_id] = (node_id, nome)


def _plan_node_subject(
    execution_id: int, node_id: int, operator: str, relation: str
) -> dict[str, Any]:
    """Subject de no de plano, na forma que o schema de Fact exige.

    `symbol` inclui o `execution_id` porque `same_subject` agrupa por ele: duas
    execucoes do mesmo plano tem o mesmo `node_id`, e sem o prefixo elas cairiam
    no mesmo grupo -- os bytes de uma vazariam para o achado da outra.
    """
    return {
        "type": "plan_node",
        "node_id": node_id,
        "operator": operator,
        "relation": relation,
        "symbol": f"{execution_id}:{node_id}",
        "execution_id": execution_id,
    }


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def extract_sql_metrics(lines: Iterable[str], path: str) -> list[Fact]:
    """Extrai Facts de um Spark event log dado como `Iterable[str]`.

    Le `SparkListenerSQLExecutionStart` (e a atualizacao de AQE, cujo
    tratamento pleno e Task 5) para montar a arvore do plano por execucao e o
    mapa de acumuladores, depois `SparkListenerDriverAccumUpdates` e os
    `Accumulables` de `SparkListenerTaskEnd` para atribuir os valores a esse
    mapa. Um `TaskEnd` cujo acumulador nao esta em `accum` (nao veio do plano
    SQL, ou foi reatribuido) engorda `unattributed_accumulators` em vez de
    ser descartado em silencio -- o fact `spark.sql.analyzed` fica com o
    tamanho do que este extrator nao pode explicar.
    """
    provenance = {"artifact": path, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    execucoes: dict[int, _Execution] = {}
    nao_atribuidos = 0
    malformadas = 0

    for linha in lines:
        texto = linha.strip()
        if not texto:
            continue
        try:
            evento = json.loads(texto)
        except (ValueError, TypeError):
            malformadas += 1
            continue
        if not isinstance(evento, dict):
            continue
        nome = evento.get("Event")

        if nome in (_SQL_START, _SQL_AQE):
            execution_id = evento.get("executionId")
            plano = evento.get("sparkPlanInfo")
            if not isinstance(execution_id, int) or not isinstance(plano, dict):
                continue
            execucao = execucoes.get(execution_id)
            if execucao is None:
                execucao = _Execution(execution_id, str(evento.get("description") or ""))
                execucoes[execution_id] = execucao
            execucao.absorb_plan(plano, "final_aqe" if nome == _SQL_AQE else "initial")

        elif nome == _DRIVER_ACCUM:
            execucao = execucoes.get(evento.get("executionId"))
            if execucao is None:
                continue
            for par in evento.get("accumUpdates") or []:
                if not isinstance(par, (list, tuple)) or len(par) != 2:
                    continue
                accum_id, valor = par
                if not isinstance(accum_id, int):
                    continue
                try:
                    numero = float(valor)
                except (TypeError, ValueError):
                    continue
                if not execucao.add_value(accum_id, numero):
                    nao_atribuidos += 1

        elif nome == _TASK_END:
            acumulaveis = ((evento.get("Task Info") or {}).get("Accumulables")) or []
            for acumulavel in acumulaveis:
                accum_id = acumulavel.get("ID")
                if not isinstance(accum_id, int):
                    continue
                try:
                    # `Update` e a contribuicao DESTA task; `Value` e o total
                    # corrente do acumulador. Somar `Value` contaria o total uma
                    # vez por task.
                    numero = float(acumulavel.get("Update"))
                except (TypeError, ValueError):
                    continue
                atribuido = any(e.add_value(accum_id, numero) for e in execucoes.values())
                if not atribuido:
                    nao_atribuidos += 1

        elif nome == _SQL_END:
            execucao = execucoes.get(evento.get("executionId"))
            if execucao is not None:
                execucao.ended = True

    facts: list[Fact] = []
    orfaos_por_execucao: dict[int, list[int]] = {}
    for execucao in sorted(execucoes.values(), key=lambda e: e.execution_id):
        por_no, desconhecidos, orfaos = execucao.measures_by_node()
        orfaos_por_execucao[execucao.execution_id] = orfaos
        for node_id, node in sorted(execucao.nodes.items()):
            facts.append(
                Fact(
                    kind="spark.sql.scan",
                    subject=_plan_node_subject(
                        execucao.execution_id, node_id, node["node_name"], node["relation"]
                    ),
                    measures=por_no.get(node_id, {}),
                    attrs={
                        "format": node["format"],
                        "scan_api": node["scan_api"],
                        "node_name": node["node_name"],
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        for node_id, metric_name in desconhecidos:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(
                        execucao.execution_id,
                        node_id,
                        execucao.nodes[node_id]["node_name"],
                        execucao.nodes[node_id]["relation"],
                    ),
                    attrs={
                        "reason": "unknown_metric_name",
                        "metric_name": metric_name,
                        "detail": (
                            "Nome de metrica fora de knowledge/spark/sql-metrics.yaml. "
                            "Casar por substring produziria numero com aparencia de "
                            "medido; o nome cru fica aqui para quem for atualizar o mapa."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        facts.append(
            Fact(
                kind="spark.sql.execution",
                subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                attrs={
                    "plan_source": execucao.plan_source,
                    "description": execucao.description,
                    "redacted": execucao.redacted,
                },
                measures={
                    "scan_nodes": len(execucao.nodes),
                    "nodes_total": execucao.nodes_total,
                },
                provenance=provenance,
            )
        )

    for execucao in sorted(execucoes.values(), key=lambda e: e.execution_id):
        for accum_id in orfaos_por_execucao[execucao.execution_id]:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "value_orphaned_by_replan",
                        "accumulator_id": accum_id,
                        "detail": (
                            "Valor publicado contra um no que sumiu do plano corrente, "
                            "provavelmente numa reposta de AQE. O numero foi medido, mas "
                            "nao ha no a que atribui-lo; soma-lo a outro no poria bytes no "
                            "lugar errado."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        for accum_id in sorted(execucao.reassigned):
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "accumulator_reassigned",
                        "accumulator_id": accum_id,
                        "detail": (
                            "O mesmo accumulatorId aparece em dois nos do plano. Nenhum "
                            "dos dois recebe o valor: escolher um poria bytes no no "
                            "errado, e o relatorio ficaria plausivel e falso."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        if not execucao.ended:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "incomplete_execution",
                        "detail": (
                            "Nenhum SparkListenerSQLExecutionEnd para esta execucao. O log "
                            "foi cortado antes do fim, e as measures sao parciais."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )

    if not execucoes:
        facts.append(
            Fact(
                kind="spark.sql.unresolved",
                subject=_file_subject(path),
                attrs={
                    "reason": "no_sql_events",
                    "detail": (
                        "Nenhum evento do namespace org.apache.spark.sql.execution.ui neste "
                        "log. Job que usa so RDD nao publica metrica de plano SQL -- e outra "
                        "coisa, nao um defeito."
                    ),
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        )

    facts.append(
        Fact(
            kind="spark.sql.analyzed",
            subject=_file_subject(path),
            measures={
                "executions": len(execucoes),
                "scan_nodes": sum(len(e.nodes) for e in execucoes.values()),
                "unattributed_accumulators": nao_atribuidos,
                "malformed_lines": malformadas,
            },
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_sql_metrics_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Le o event log do disco em streaming e delega para `extract_sql_metrics`.

    Falha ao abrir vira um unico `spark.sql.unresolved` com razao `read_error`,
    nunca uma excecao que derruba quem chamou -- mesma convencao de
    `event_log.extract_event_log_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    try:
        with path.open(encoding="utf-8-sig") as handle:
            return extract_sql_metrics(handle, anchor)
    except OSError as exc:
        return [
            Fact(
                kind="spark.sql.unresolved",
                subject=_file_subject(anchor),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance={"extractor": EXTRACTOR_ID, "artifact": anchor},
            )
        ]
