"""O grafo de tarefas do plan: `depends_on`, ordem e escopo de escrita.

Campos opcionais da tarefa que o gate deste modulo confere: `depends_on`
(ids de tarefa), `parallel_safe`, `risk`, `write_scope` (caminhos) e
`blocking`. O grafo precisa ser DAG, a ordem declarada respeita as
dependencias, todo requisito do define tem ao menos uma tarefa, toda tarefa
cobre ao menos um criterio ou requisito do define, e duas tarefas
declaradas seguras para paralelo nao escrevem no mesmo lugar. Tudo
deterministico vira recusa; o que pede julgamento (cobertura de requisito,
tarefa sem criterio, sobreposicao de escrita) vira lacuna.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Finding:
    """Um problema do grafo; `kind` vira o codigo do contrato no gate."""

    kind: str  # dep_unknown | cycle | order | req_uncovered | covers_nothing | write_overlap
    item: str | None
    detail: str


def _ciclos(por_id: dict[str, dict[str, Any]]) -> set[str]:
    """Os ids presos em ciclo de `depends_on` (DFS iterativo)."""
    em_ciclo: set[str] = set()
    for origem in por_id:
        pilha = [origem]
        vistos: set[str] = set()
        while pilha:
            atual = pilha.pop()
            if atual in vistos:
                continue
            vistos.add(atual)
            for dep in por_id.get(atual, {}).get("depends_on") or []:
                if dep == origem:
                    em_ciclo.add(origem)
                elif dep in por_id:
                    pilha.append(dep)
    return em_ciclo


def _normaliza(caminho: str) -> str:
    return caminho.replace("\\", "/").removeprefix("./").rstrip("/")


def _sobrepoe(a: str, b: str) -> bool:
    """Um escopo cobre o outro: caminho igual ou um prefixo de diretorio do outro."""
    return a == b or a.startswith(f"{b}/") or b.startswith(f"{a}/")


def topo_order(tasks: list[dict[str, Any]]) -> list[str]:
    """Os ids em ordem topologica (dependencia antes de dependente).

    Ciclo nao derruba: quem esta fora sai na ordem e quem esta dentro entra no
    fim, ordenado -- o gate ja nomeou o ciclo, aqui so interessa uma ordem
    estavel para exibicao (`sdd status`).
    """
    por_id = {t["id"]: t for t in tasks if isinstance(t, dict) and t.get("id")}
    em_ciclo = _ciclos(por_id)
    ordem: list[str] = []
    vistos: set[str] = set()

    def visita(ident: str) -> None:
        if ident in vistos:
            return
        vistos.add(ident)
        for dep in sorted(por_id.get(ident, {}).get("depends_on") or []):
            if dep in por_id and dep not in em_ciclo:
                visita(dep)
        ordem.append(ident)

    for ident in [t["id"] for t in tasks if isinstance(t, dict) and t.get("id")]:
        if ident not in em_ciclo:
            visita(ident)
    ordem.extend(sorted(em_ciclo))
    return ordem


def validate_tasks(
    tasks: list[dict[str, Any]],
    requirement_ids: list[str],
    acceptance_ids: list[str] | None = None,
) -> list[Finding]:
    """Os problemas do grafo de tarefas.

    `requirement_ids` sao os ids de `requirements` do define (REQ/NFR/US); a
    cobertura dos `AC` na direcao criterio->tarefa segue com
    `acceptance_uncovered`, que ja existe. `acceptance_ids` sao os ids de
    `acceptance` do define, que junto dos requisitos formam os ids que um
    `covers` pode nomear: na direcao tarefa->criterio, `covers` vazio sempre
    vira `covers_nothing`, e `covers` so com ids desconhecidos vira quando ha
    define para julgar (sem define a lista vem vazia e so o covers vazio
    dispara).
    """
    achados: list[Finding] = []
    por_id = {t["id"]: t for t in tasks if isinstance(t, dict) and t.get("id")}
    posicao = {t["id"]: i for i, t in enumerate(tasks) if isinstance(t, dict) and t.get("id")}
    for tarefa in tasks:
        ident = tarefa["id"]
        for dep in tarefa.get("depends_on") or []:
            if dep not in por_id:
                achados.append(Finding(
                    "dep_unknown", ident,
                    f"{ident} depende de {dep}, que nao e tarefa do plan",
                ))
            elif posicao[dep] > posicao[ident]:
                achados.append(Finding(
                    "order", ident,
                    f"{ident} depende de {dep}, que vem depois na lista; "
                    "declare as tarefas na ordem em que elas rodam",
                ))
    for ident in sorted(_ciclos(por_id)):
        achados.append(Finding(
            "cycle", ident,
            f"{ident} esta num ciclo de depends_on; corte a aresta que fecha o laco",
        ))
    cobertos = {
        ac for tarefa in tasks for ac in (tarefa.get("covers") or [])
    }
    for ident in requirement_ids:
        if ident not in cobertos:
            achados.append(Finding(
                "req_uncovered", ident,
                f"{ident} do define nao aparece em nenhum covers de tarefa; "
                "cubra-o ou explique por que ele nao precisa de tarefa",
            ))
    conhecidos = {*requirement_ids, *(acceptance_ids or ())}
    for tarefa in tasks:
        ident = tarefa["id"]
        alvos = tarefa.get("covers") or []
        if not alvos:
            achados.append(Finding(
                "covers_nothing", ident,
                f"{ident} tem covers vazio: a tarefa nao cobre criterio nem "
                "requisito do define; ligue-a a um id real ou explique por "
                "que ela existe",
            ))
        elif conhecidos and not any(alvo in conhecidos for alvo in alvos):
            achados.append(Finding(
                "covers_nothing", ident,
                f"{ident} cobre so ids que o define nao tem "
                f"({', '.join(sorted(set(alvos) - conhecidos))}); corrija o "
                "covers ou crie o criterio",
            ))
    for i, tarefa in enumerate(tasks):
        if not tarefa.get("parallel_safe"):
            continue
        escopo_a = {_normaliza(p) for p in tarefa.get("write_scope") or []}
        for outra in tasks[i + 1:]:
            if not outra.get("parallel_safe"):
                continue
            comuns = {
                a for a in escopo_a
                for b in (_normaliza(p) for p in outra.get("write_scope") or [])
                if _sobrepoe(a, b)
            }
            for caminho in sorted(comuns):
                achados.append(Finding(
                    "write_overlap", tarefa["id"],
                    f"{tarefa['id']} e {outra['id']} sao parallel_safe e escrevem "
                    f"em {caminho}; o paralelismo declarado nao e seguro",
                ))
    return achados
