"""Knowledge Drift Radar (§17): o que uma fonte vigiada que mudou arrasta.

Quando o hash de uma pagina oficial muda (`changed_at` no lock), a pergunta nao
e so "que regras a citam" -- isso o lock ja responde -- e sim "o que precisa ser
relido e rodado de novo": as regras e documentos que a leram ANTES da mudanca,
os goldens que provam essas regras, os evals que as citam e os agentes que as
declaram. Tudo aqui e calculado na leitura e so por ligacao que existe em
arquivo; nada e inferido.

`drift` e pura: quem chama monta o lock (o do disco, ou o que o refresh acabou
de conferir), o catalogo, as citacoes dos documentos e o indice do repositorio.
Instalado por pip, o wheel nao leva `fixtures/`, `evals/` nem `agents/`: sem
indice, esses tres saltos saem `unresolved` com `sem_repositorio`, e nunca como
lista vazia -- que pareceria "nada afetado".

O radar NAO diz se a mudanca tocou o trecho que a regra cita: o lock guarda o
hash da pagina inteira, e saber isso exige leitura humana (`refused`).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from sparkforge.facts.scan import iter_source_files
from sparkforge.knowledge_freshness import estado

RULE_ID = re.compile(r"\b[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\d{3}\b")
_FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)
_TEXTO = frozenset({".yaml", ".yml", ".json", ".xml", ".md", ".txt"})
SALTOS_DO_REPOSITORIO = ("goldens", "evals", "agents")
IMPACTO = ("rules", "docs", *SALTOS_DO_REPOSITORIO)
REFUSED: tuple[dict[str, str], ...] = (
    {"field": "conteudo_da_mudanca", "reason": "exige_leitura_humana_da_fonte"},
)


@dataclass(frozen=True)
class RepoIndex:
    goldens: Mapping[str, frozenset[str]]
    evals: Mapping[str, frozenset[str]]
    agent_areas: Mapping[str, frozenset[str]]
    agent_citations: Mapping[str, frozenset[str]]

    def agents_of(self, rule_id: str) -> set[str]:
        """Agente que declara a area da regra OU cita o `rule_id`. A area e o
        prefixo ate o ultimo hifen, o mesmo recorte de `root_cause`."""
        area = rule_id.rsplit("-", 1)[0]
        por_area = {agente for agente, areas in self.agent_areas.items() if area in areas}
        return por_area | set(self.agent_citations.get(rule_id, ()))


def repo_root() -> Path | None:
    """A raiz do repositorio, quando ha checkout: a mesma raiz que `catalog_dir()`
    tenta primeiro. Instalado por pip, nenhum dos tres diretorios existe."""
    raiz = Path(__file__).resolve().parents[1]
    if all((raiz / nome).is_dir() for nome in ("fixtures", "evals", "agents")):
        return raiz
    return None


def _congelar(mapa: Mapping[str, set[str]]) -> dict[str, frozenset[str]]:
    return {chave: frozenset(valor) for chave, valor in mapa.items()}


def build_index(root: Path) -> RepoIndex:
    """Goldens, evals e agentes da raiz, pela porta de leitura da casa."""
    goldens: dict[str, set[str]] = defaultdict(set)
    base = root / "fixtures"
    for caminho in iter_source_files(base, "findings.json"):
        if caminho.parent.name != "expected":
            continue
        caso = caminho.parent.parent.relative_to(base).as_posix()
        try:
            achados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for achado in achados if isinstance(achados, list) else []:
            if isinstance(achado, dict) and achado.get("rule_id"):
                goldens[str(achado["rule_id"])].add(caso)

    evals: dict[str, set[str]] = defaultdict(set)
    for caminho in iter_source_files(root / "evals", "*"):
        if caminho.suffix not in _TEXTO:
            continue
        relativo = caminho.relative_to(root).as_posix()
        for rule_id in set(RULE_ID.findall(caminho.read_text(encoding="utf-8", errors="replace"))):
            evals[rule_id].add(relativo)

    areas: dict[str, set[str]] = {}
    citacoes: dict[str, set[str]] = defaultdict(set)
    for caminho in iter_source_files(root / "agents", "*.md"):
        relativo = caminho.relative_to(root).as_posix()
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        declaradas: set[str] = set()
        casou = _FRONTMATTER.match(texto)
        if casou:
            try:
                frente = yaml.safe_load(casou.group(1)) or {}
            except yaml.YAMLError:
                frente = {}
            if isinstance(frente, dict):
                declaradas = {str(a) for a in frente.get("rule_areas") or []}
        areas[relativo] = declaradas
        for rule_id in set(RULE_ID.findall(texto)):
            citacoes[rule_id].add(relativo)

    return RepoIndex(_congelar(goldens), _congelar(evals), _congelar(areas), _congelar(citacoes))


def _citacoes(
    url: str,
    rules: Sequence[Mapping[str, Any]],
    doc_citations: Mapping[str, Mapping[str, Sequence[Any]]],
    lock: Mapping[str, Mapping[str, Any]],
    as_of: date,
) -> list[dict[str, Any]]:
    """Cada regra e documento que cita `url`, com a data MAIS ANTIGA declarada
    (a mesma escolha de `knowledge_freshness.mapa`) e o estado dela."""
    saida: list[dict[str, Any]] = []
    for regra in rules:
        datas = [
            str(fonte.get("retrieved"))
            for fonte in regra.get("sources") or []
            if isinstance(fonte, Mapping) and fonte.get("url") == url and fonte.get("retrieved")
        ]
        fontes = regra.get("sources") or []
        if not any(isinstance(f, Mapping) and f.get("url") == url for f in fontes):
            continue
        validado = min(datas) if datas else None
        situacao = estado(url, validado, lock, as_of)
        saida.append(
            {"kind": "rule", "id": str(regra["id"]), "retrieved": validado,
             "state": situacao.state, "reason": situacao.reason}
        )
    for doc in sorted(doc_citations):
        datas = [str(d) for d in doc_citations[doc].get(url, []) if d]
        if url not in doc_citations[doc]:
            continue
        validado = min(datas) if datas else None
        situacao = estado(url, validado, lock, as_of)
        saida.append(
            {"kind": "doc", "id": doc, "retrieved": validado,
             "state": situacao.state, "reason": situacao.reason}
        )
    return saida


def drift(
    lock: Mapping[str, Mapping[str, Any]] | None,
    motivo_lock: str | None,
    rules: Sequence[Mapping[str, Any]],
    doc_citations: Mapping[str, Mapping[str, Sequence[Any]]],
    index: RepoIndex | None,
    as_of: date,
    url: str | None = None,
) -> dict[str, Any]:
    """O impacto de cada fonte com `changed_at` (fixa por versao nunca entra).

    Citacao `stale` (lida antes da mudanca) entra no impacto; qualquer outro
    estado numa fonte mudada e `revalidated`: alguem ja releu, e ela conta no
    total sem pedir releitura de novo.
    """
    fontes = lock or {}
    mudadas = sorted(
        u for u, entrada in fontes.items()
        if isinstance(entrada, Mapping) and entrada.get("changed_at") and not entrada.get("pinned")
    )
    if url is not None:
        mudadas = [u for u in mudadas if u == url]

    por_fonte: list[dict[str, Any]] = []
    distintos: dict[str, set[str]] = {chave: set() for chave in IMPACTO}
    for alvo in mudadas:
        citacoes = _citacoes(alvo, rules, doc_citations, fontes, as_of)
        velhas = [c for c in citacoes if c["state"] == "stale"]
        regras = sorted({c["id"] for c in velhas if c["kind"] == "rule"})
        docs = sorted({c["id"] for c in velhas if c["kind"] == "doc"})
        impacto: dict[str, list[str] | None] = {"rules": regras, "docs": docs}
        if index is None:
            impacto.update({chave: None for chave in SALTOS_DO_REPOSITORIO})
        else:
            impacto["goldens"] = sorted({g for r in regras for g in index.goldens.get(r, ())})
            impacto["evals"] = sorted({e for r in regras for e in index.evals.get(r, ())})
            impacto["agents"] = sorted({a for r in regras for a in index.agents_of(r)})
        for chave, valores in impacto.items():
            distintos[chave].update(valores or [])
        por_fonte.append(
            {
                "url": alvo,
                "changed_at": str(fontes[alvo]["changed_at"]),
                "citations": citacoes,
                "revalidated": sorted({c["id"] for c in citacoes if c["state"] != "stale"}),
                "impact": impacto,
            }
        )

    unresolved: list[dict[str, str]] = []
    if lock is None:
        unresolved.append({"field": "lock", "reason": motivo_lock or "lock_ausente"})
    if index is None:
        unresolved.extend(
            {"field": chave, "reason": "sem_repositorio"} for chave in SALTOS_DO_REPOSITORIO
        )
    entradas = [e for e in fontes.values() if isinstance(e, Mapping)]
    return {
        "as_of": as_of.isoformat(),
        "lock": {
            "sources": len(entradas),
            "checked": sum(1 for e in entradas if e.get("checked_at")),
            "pinned": sum(1 for e in entradas if e.get("pinned")),
            "changed": sum(1 for e in entradas if e.get("changed_at") and not e.get("pinned")),
        },
        "changed_sources": por_fonte,
        "totals": {chave: len(distintos[chave]) for chave in IMPACTO},
        "unresolved": unresolved,
        "refused": [dict(item) for item in REFUSED],
    }


_ROTULOS = {
    "rules": "Regras a reler",
    "docs": "Documentos de `knowledge/` a reler",
    "goldens": "Goldens que provam essas regras",
    "evals": "Evals que citam essas regras",
    "agents": "Agentes que declaram a area ou citam a regra",
}


def render_markdown(payload: Mapping[str, Any]) -> str:
    """A secao "Impacto" do relatorio do refresh, a partir da saida de `drift`."""
    totais = payload["totals"]
    linhas = [
        "## Impacto",
        "",
        f"Fontes que mudaram: {len(payload['changed_sources'])}. No impacto: "
        + ", ".join(f"{totais[chave]} {chave}" for chave in IMPACTO) + ".",
        "",
    ]
    for fonte in payload["changed_sources"]:
        linhas += [f"### {fonte['url']} (mudou em {fonte['changed_at']})", ""]
        for chave in IMPACTO:
            valores = fonte["impact"][chave]
            if valores is None:
                linhas.append(f"- {_ROTULOS[chave]}: sem repositorio (`unresolved`)")
            elif valores:
                linhas.append(f"- {_ROTULOS[chave]}: {', '.join(valores)}")
        if fonte["revalidated"]:
            linhas.append(f"- Ja relidas depois da mudanca: {', '.join(fonte['revalidated'])}")
        linhas.append("")
    linhas.append(
        "O radar nao diz se a mudanca tocou o trecho que cada regra cita: o lock guarda "
        "o hash da pagina inteira (`refused: conteudo_da_mudanca`)."
    )
    linhas.append("")
    return "\n".join(linhas)
