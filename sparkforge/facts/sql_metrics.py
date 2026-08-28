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
        "spark.sql.join",
        "spark.sql.join_input",
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


# Teto de profundidade da arvore. `_walk` e recursivo, e um `sparkPlanInfo`
# suficientemente profundo estoura a pilha do Python antes de qualquer
# verificacao -- o extrator morreria com `RecursionError` no meio de uma
# extracao que ja produziu facts validos. Falha com nome e diagnostico; falha
# por estouro de pilha e acidente.
_TETO_DE_PROFUNDIDADE = 200

_JOIN_OPERADORES = frozenset(
    {
        "BroadcastHashJoin",
        "SortMergeJoin",
        "ShuffledHashJoin",
        "BroadcastNestedLoopJoin",
        "CartesianProduct",
    }
)

_BUILD_RE = re.compile(r"\bBuild(Left|Right)\b")


def _join_of(node: dict[str, Any]) -> tuple[str, str, str] | None:
    """Devolve `(strategy, join_type, build_side)` se o no e join, senao `None`.

    `build_side` sai `""` quando o operador nao publica lado de build --
    `SortMergeJoin` ordena e mescla os dois lados, e atribuir um lado a ele
    seria afirmar o que o plano nao diz.
    """
    operador = str(node.get("nodeName") or "").strip()
    if operador not in _JOIN_OPERADORES:
        return None
    texto = str(node.get("simpleString") or "")
    join_type = ""
    for candidato in ("Inner", "LeftOuter", "RightOuter", "FullOuter", "LeftSemi", "LeftAnti"):
        if re.search(rf"\b{candidato}\b", texto):
            join_type = candidato
            break
    build = _BUILD_RE.search(texto)
    return operador, join_type, build.group(1).lower() if build else ""


def _estrutura(plano: dict[str, Any]) -> tuple[dict[int, list[int]], int]:
    """`{node_id: [ids dos filhos]}` e a profundidade maxima da arvore.

    Numeracao identica a de `_walk`: preorder, raiz = 0. Os dois precisam
    concordar, porque o `node_id` de um fact de scan e o de uma aresta tem que
    apontar para o mesmo no -- e e teste que garante isso, nao import.
    """
    filhos: dict[int, list[int]] = {}
    proximo = [0]
    profundidade_maxima = [0]

    def visita(node: dict[str, Any], nivel: int) -> int:
        meu = proximo[0]
        proximo[0] += 1
        profundidade_maxima[0] = max(profundidade_maxima[0], nivel + 1)
        meus_filhos: list[int] = []
        for filho in node.get("children") or []:
            meus_filhos.append(visita(filho, nivel + 1))
        filhos[meu] = meus_filhos
        return meu

    visita(plano, 0)
    return filhos, profundidade_maxima[0]


def _fontes_por_no(plano: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    """`{node_id: fontes abaixo dele}` para a arvore INTEIRA, numa unica passada.

    Mesma pergunta que `_fontes_abaixo` responde no a no, mas para todos os
    nos de uma vez: uma passada pos-ordem, em vez de uma passada da arvore
    inteira por no consultado. `absorb_plan` monta o grafo de joins chamando
    esta funcao UMA VEZ por arvore e consultando o dicionario por lado de
    join, em vez de chamar `_fontes_abaixo` (e `_fonte_do_proprio_no`) a cada
    lado -- e isso que tira a extracao de O(nos^2) para O(nos) em plano largo.

    A regra de `via_joins` e a mesma de `_fontes_abaixo`: conta os joins
    ESTRITAMENTE entre o scan e o no. Subindo da folha para a raiz, cada vez
    que o no do meio e ele mesmo um join, soma-se 1 a tudo que vem de baixo
    dele -- porque aquele no fica NO CAMINHO entre o scan e quem esta acima.
    Numeracao identica a de `_walk`/`_estrutura`: preorder, raiz = 0.
    """
    por_no: dict[int, list[dict[str, Any]]] = {}
    proximo = [0]

    def visita(node: dict[str, Any]) -> int:
        meu = proximo[0]
        proximo[0] += 1
        fontes: list[dict[str, Any]] = []
        for filho in node.get("children") or []:
            filho_id = visita(filho)
            scan = _scan_of(filho)
            if scan is not None:
                _, relation, _ = scan
                fontes.append({"node_id": filho_id, "relation": relation, "via_joins": 0})
                continue
            incremento = 1 if _join_of(filho) is not None else 0
            fontes.extend(
                dict(f, via_joins=f["via_joins"] + incremento) for f in por_no[filho_id]
            )
        por_no[meu] = fontes
        return meu

    visita(plano)
    return por_no


def _fontes_abaixo(plano: dict[str, Any], alvo: int) -> list[dict[str, Any]]:
    """As fontes alcancaveis abaixo de `alvo`, cada uma com `via_joins`.

    `via_joins` e quantos joins existem ENTRE o scan e `alvo`. Fonte que entra
    direto tem zero. Nao perde informacao e nao mente: quem quiser so o direto
    filtra por zero, quem quiser a arvore inteira soma tudo.

    Consulta fina sobre `_fontes_por_no`: mesma resposta de antes, mesma
    assinatura. Quem precisar da resposta para varios `alvo` na MESMA arvore
    -- como `absorb_plan` precisa, um por lado de join -- deve chamar
    `_fontes_por_no` uma vez e consultar o dicionario, nunca repetir esta
    chamada em loop: cada chamada aqui refaz a passada pela arvore inteira.
    """
    return _fontes_por_no(plano).get(alvo, [])


def _fonte_do_proprio_no(plano: dict[str, Any], alvo: int) -> list[dict[str, Any]]:
    """A fonte do PROPRIO no, quando o filho do join ja e um scan.

    `_fontes_abaixo` olha estritamente abaixo do alvo, porque `via_joins` conta
    o que ha ENTRE o scan e o join. O caso mais comum de todos -- join cujo
    filho e um scan direto -- cai fora daquela varredura, e sem este auxiliar
    sairia como lado sem fonte.
    """
    for node_id, node in _walk(plano, [0]):
        if node_id != alvo:
            continue
        scan = _scan_of(node)
        if scan is None:
            return []
        _, relation, _ = scan
        return [{"node_id": node_id, "relation": relation, "via_joins": 0}]
    return []


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
        self.joins: dict[int, dict[str, Any]] = {}
        self.arestas: list[dict[str, Any]] = []
        self.lados_sem_fonte: list[dict[str, Any]] = []
        self.profundidade = 0
        self.plano_profundo_demais = False

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

        self.joins = {}
        self.arestas = []
        self.lados_sem_fonte = []
        filhos, self.profundidade = _estrutura(plano)
        self.plano_profundo_demais = self.profundidade > _TETO_DE_PROFUNDIDADE
        if self.plano_profundo_demais:
            return

        # Uma passada pela arvore inteira, consultada por lado de join
        # abaixo -- em vez de uma passada inteira por lado (o que fazia a
        # montagem do grafo O(nos^2) em plano largo). `self.nodes` (populado
        # acima) ja responde "este node_id e um scan, e qual e a relation?"
        # em O(1), o mesmo papel que `_fonte_do_proprio_no` cumpria por
        # chamada.
        fontes_por_no = _fontes_por_no(plano)

        for node_id, node in _walk(plano, [0]):
            join = _join_of(node)
            if join is None:
                continue
            strategy, join_type, build_side = join
            meus_filhos = filhos.get(node_id) or []
            filhos_nos = node.get("children") or []
            if not meus_filhos:
                self.lados_sem_fonte.append(
                    {"node_id": node_id, "position": "", "reason": "join_without_children"}
                )
                continue

            # `children` vem em ordem: o primeiro e o lado esquerdo. `position`
            # e observacao; `side` e derivacao do token BuildLeft/BuildRight, e
            # so existe quando o operador o publica.
            contagem = {"left": 0, "right": 0}
            for indice, (filho_id, filho_no) in enumerate(
                zip(meus_filhos[:2], filhos_nos[:2], strict=True)
            ):
                position = "left" if indice == 0 else "right"
                if build_side:
                    side = "build" if position == build_side else "stream"
                else:
                    side = "unknown"
                fontes = fontes_por_no.get(filho_id, [])
                if _join_of(filho_no) is not None:
                    # `fontes_por_no[filho_id]` nao conta o proprio `filho_id`
                    # como join, porque ele E o no cujas fontes abaixo estao
                    # ali. Mas do ponto de vista DESTE join (o pai), o filho
                    # que e join tambem fica ENTRE o pai e cada fonte -- por
                    # isso soma 1 aqui, uma vez, em vez de la dentro.
                    fontes = [dict(f, via_joins=f["via_joins"] + 1) for f in fontes]
                # O proprio filho pode ser o scan, e `fontes_por_no[filho_id]`
                # so guarda o que esta ABAIXO dele -- entao o proprio filho e
                # conferido a parte, em `self.nodes` (que ja mapeia todo
                # node_id de scan para a relation, populado acima).
                no_proprio = self.nodes.get(filho_id)
                if no_proprio is not None:
                    fontes = fontes + [
                        {
                            "node_id": filho_id,
                            "relation": no_proprio["relation"],
                            "via_joins": 0,
                        }
                    ]
                if not fontes:
                    self.lados_sem_fonte.append(
                        {
                            "node_id": node_id,
                            "position": position,
                            "reason": "join_side_without_source",
                        }
                    )
                    continue
                contagem[position] = len(fontes)
                for fonte in fontes:
                    self.arestas.append(
                        {
                            "join_node_id": node_id,
                            "strategy": strategy,
                            "relation": fonte["relation"],
                            "position": position,
                            "side": side,
                            "via_joins": fonte["via_joins"],
                        }
                    )

            self.joins[node_id] = {
                "strategy": strategy,
                "join_type": join_type,
                "build_side": build_side,
                "inputs_left": contagem["left"],
                "inputs_right": contagem["right"],
            }


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
        for node_id, join in sorted(execucao.joins.items()):
            facts.append(
                Fact(
                    kind="spark.sql.join",
                    subject=_plan_node_subject(
                        execucao.execution_id, node_id, join["strategy"], ""
                    ),
                    attrs={
                        "strategy": join["strategy"],
                        "join_type": join["join_type"],
                        "build_side": join["build_side"],
                    },
                    measures={
                        "inputs_left": join["inputs_left"],
                        "inputs_right": join["inputs_right"],
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        for aresta in execucao.arestas:
            subject = _plan_node_subject(
                execucao.execution_id,
                aresta["join_node_id"],
                aresta["strategy"],
                "",
            )
            # `symbol` continua `<execution_id>:<join_node_id>` -- ele que
            # `same_subject` usa para agrupar por junção
            # (`rules/engine.py::_subject_group_key`), e nao pode mudar. Mas
            # `Fact.id` e hash de `kind + subject + measures`, sem `attrs`
            # (`findings/models.py::Fact.id`): duas arestas do MESMO join com o
            # mesmo `via_joins` tem subject e measures identicos e so
            # diferem em `attrs["relation"]`/`position`/`side`, que nao entra
            # no id. `relation` ja e propriedade declarada do subject
            # (`findings/schemas/fact.schema.json`); `position` nao e, mas o
            # schema nao fecha `subject` com `additionalProperties: false`, e
            # cobre o caso do self-join -- `db.a` dos dois lados do mesmo join
            # tem a mesma `relation`, e sem `position` as duas arestas
            # colidiriam de novo.
            subject["relation"] = aresta["relation"]
            subject["position"] = aresta["position"]
            facts.append(
                Fact(
                    kind="spark.sql.join_input",
                    subject=subject,
                    attrs={
                        "relation": aresta["relation"],
                        "position": aresta["position"],
                        "side": aresta["side"],
                        "strategy": aresta["strategy"],
                    },
                    measures={"via_joins": aresta["via_joins"]},
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        for lado in execucao.lados_sem_fonte:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(
                        execucao.execution_id, lado["node_id"], "join", ""
                    ),
                    attrs={
                        "reason": lado["reason"],
                        "position": lado["position"],
                        "detail": (
                            "Lado do join sem nenhum scan nomeavel abaixo. Subquery, "
                            "relacao em cache e `Scan ExistingRDD` nao sao fonte que se "
                            "possa nomear, e inventar um nome seria pior que a lacuna."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        if execucao.plano_profundo_demais:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "plan_too_deep",
                        "detail": (
                            f"Arvore com profundidade {execucao.profundidade}, acima do teto "
                            f"de {_TETO_DE_PROFUNDIDADE}. O grafo nao e montado: percorrer "
                            f"recursivamente ate o fim estouraria a pilha no meio de uma "
                            f"extracao que ja produziu facts validos."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
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
