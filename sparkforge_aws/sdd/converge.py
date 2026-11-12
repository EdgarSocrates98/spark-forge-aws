"""Convergencia do ship: a comparacao read-only entre o que foi pedido e o que veio.

Cruza requisitos e criterios do define com `covers` do design, tarefas do
plan, resultado do build_report e evidencias declaradas -- mais o que os
gates dedicados ja nomeiam (`covered_by` marca o item que outra recusa ja
carrega, para a causa nao sair duas vezes). Classes de divergencia, na
ordem do contrato: `missing`, `partial`, `contradicts`, `unrequested`,
`unverified`, `stale`. `ok` so e falso quando alguma classe diferente de
`unrequested` tem item -- o que veio a mais e informacao, nao bloqueio.

O verbo `sdd converge` le; nunca reescreve arquivo nenhum. Sem `.git`, o
bloco `git` diz `available: false` e a comparacao segue sobre os artefatos.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sparkforge_aws.paths import resolve_within
from sparkforge_aws.receipt._hash import text_sha256
from sparkforge_aws.sdd import DEFAULT_ROOT
from sparkforge_aws.sdd.decisions import load_decisions
from sparkforge_aws.sdd.load import Artifact
from sparkforge_aws.sdd.receipts import CODIGO as RECEIPT_CODE
from sparkforge_aws.sdd.receipts import load_receipt, validate_receipt

SCHEMA_ID = "forge/ConvergenceReport/v1"
CLASSES = ("missing", "partial", "contradicts", "unrequested", "unverified", "stale")


def _item(
    classe: str,
    item: str,
    path: str,
    reason: str,
    covered_by: str | None = None,
) -> dict[str, Any]:
    return {
        "class": classe,
        "item": item,
        "path": path,
        "reason": reason,
        "covered_by": covered_by,
    }


def _caminho_da_arvore(
    repo: Path, caminhos: dict[str, Path], artefatos: dict[str, Artifact]
) -> Path | None:
    """A `decisions.json` da feature: a que o explore declara, ou a da pasta."""
    explore = artefatos.get("explore")
    declarado = explore.meta.get("decisions_ref") if explore is not None else None
    if declarado:
        return resolve_within(repo, str(declarado))
    for caminho in caminhos.values():
        convencional = caminho.parent / "decisions.json"
        if convencional.is_file():
            return convencional
    return None


def _caminho_de_evidencia(referencia: str) -> str | None:
    """O trecho de `evidence_ref` que e caminho, ou None quando e so prosa.

    Sem separador, `::`/`#` nem extensao de arquivo, nao ha o que conferir --
    a referencia e texto livre e pular nao e erro, e o honesto.
    """
    trecho = referencia.partition("#")[0].partition("::")[0].strip()
    if not trecho:
        return None
    if "/" in trecho or "\\" in trecho:
        return trecho
    if trecho.rsplit(".", 1)[-1] in (
        "json", "md", "py", "txt", "log", "out", "yaml", "yml", "patch", "diff",
    ):
        return trecho
    return None


def converge_artefatos(
    repo: Path,
    caminhos: dict[str, Path],
    artefatos: dict[str, Artifact],
    rel: Callable[[Path], str],
) -> list[dict[str, Any]]:
    """Os itens de divergencia da feature, sobre os artefatos ja carregados."""
    itens: list[dict[str, Any]] = []
    define = artefatos.get("define")
    design = artefatos.get("design")
    plano = artefatos.get("plan")
    build = artefatos.get("build_report")

    covers_design = {
        ac
        for parte in (design.meta["covers"] if design is not None else [])
        for ac in parte["acceptance"]
    }
    tarefas_plan = {t["id"]: t for t in (plano.meta["tasks"] if plano is not None else [])}
    tarefas_build = {t["id"]: t for t in (build.meta["tasks"] if build is not None else [])}
    covers_plan = {ac for t in tarefas_plan.values() for ac in t["covers"]}

    # -- requisitos e criterios: quem pediu x quem cobriu ---------------------
    if define is not None:
        for criterio in define.meta["acceptance"]:
            ident = criterio["id"]
            if ident not in covers_design:
                itens.append(_item(
                    "missing", ident, rel(design.path) if design else "",
                    f"{ident} nao aparece em nenhum covers do design",
                    covered_by="acceptance_uncovered",
                ))
            if ident not in covers_plan:
                itens.append(_item(
                    "missing", ident, rel(plano.path) if plano else "",
                    f"{ident} nao aparece em nenhum covers do plan",
                    covered_by="acceptance_uncovered",
                ))
            if criterio["verified_by"]["kind"] == "command":
                itens.append(_item(
                    "unverified", ident, rel(define.path),
                    f"{ident} e verificado por command, que o gate nao confere; "
                    "o ship registra o exit no corpo -- confirme que rodou",
                ))
        for req in define.meta.get("requirements") or []:
            ident = req["id"]
            if ident not in covers_plan:
                itens.append(_item(
                    "missing", ident, rel(plano.path) if plano else "",
                    f"o requisito {ident} nao tem tarefa que o cubra",
                    covered_by="requirement_uncovered",
                ))

    # -- tarefas: plan x build ------------------------------------------------
    for ident in tarefas_plan:
        feita = tarefas_build.get(ident)
        if feita is None:
            itens.append(_item(
                "missing", ident, rel(build.path) if build else "",
                f"a tarefa {ident} do plan nao aparece no build_report",
            ))
            continue
        if feita["status"] in ("skipped", "blocked"):
            itens.append(_item(
                "partial", ident, rel(build.path) if build else "",
                f"a tarefa {ident} esta {feita['status']}; a cobertura fica parcial",
            ))
        elif feita["status"] == "done":
            verde = feita.get("green")
            if verde is not None and verde["exit"] != 0:
                itens.append(_item(
                    "contradicts", ident, rel(build.path) if build else "",
                    f"{ident} esta done mas o green saiu com exit {verde['exit']}",
                ))
            elif verde is None and feita.get("moved") is None:
                itens.append(_item(
                    "unverified", ident, rel(build.path) if build else "",
                    f"{ident} esta done sem green registrado; nada prova o verde",
                ))
    for ident in tarefas_build:
        if ident not in tarefas_plan:
            itens.append(_item(
                "unrequested", ident, rel(build.path) if build else "",
                f"a tarefa {ident} do build_report nao esta no plan",
            ))

    # -- decisoes que os requisitos citam ------------------------------------
    referencias = [
        (req["id"], dep)
        for req in (define.meta.get("requirements") or []) if define is not None
        for dep in (req.get("decision_refs") or [])
    ]
    if referencias:
        caminho = _caminho_da_arvore(repo, caminhos, artefatos)
        arvore = None
        if caminho is not None and caminho.is_file():
            arvore, _ = load_decisions(caminho)
        estados = {
            d.get("id"): d.get("status")
            for d in (arvore or {}).get("decisions") or []
            if isinstance(d, dict)
        }
        for dono, dep in referencias:
            if dep not in estados:
                itens.append(_item(
                    "missing", dep, rel(caminho) if caminho else "",
                    f"{dono} cita a decisao {dep}, que a arvore nao tem",
                    covered_by="decision_ref_unknown",
                ))
            elif estados[dep] != "decided":
                itens.append(_item(
                    "unverified", dep, rel(caminho) if caminho else "",
                    f"{dono} depende de {dep}, que esta {estados[dep]}",
                    covered_by="decision_open",
                ))

    # -- evidencias declaradas no build ---------------------------------------
    if build is not None:
        for indice, afirmacao in enumerate(build.meta["claims"]):
            ref = afirmacao.get("evidence_ref")
            trecho = _caminho_de_evidencia(str(ref)) if ref else None
            if trecho is None:
                continue
            alvo = resolve_within(repo, trecho)
            if alvo is None or not alvo.is_file():
                itens.append(_item(
                    "missing", f"claims/{indice}", rel(build.path),
                    f"o evidence_ref {ref} nao existe no repo",
                ))
        for indice, ref in enumerate(build.meta.get("receipts") or []):
            alvo = resolve_within(repo, str(ref))
            if alvo is None or not alvo.is_file():
                itens.append(_item(
                    "missing", f"receipts/{indice}", rel(build.path),
                    f"o recibo {ref} nao existe no repo",
                    covered_by="receipt_missing",
                ))
                continue
            recibo, erro = load_receipt(alvo)
            if erro is not None or recibo is None:
                itens.append(_item(
                    "unverified", f"receipts/{indice}", rel(alvo),
                    f"o recibo {ref} nao le: {erro}",
                    covered_by="schema_invalid",
                ))
                continue
            for achado in validate_receipt(recibo, repo):
                classe = {
                    "invalid": "contradicts",
                    "failed": "contradicts",
                    "inconclusive": "unverified",
                    "output_missing": "missing",
                    "stale": "stale",
                }[achado.kind]
                itens.append(_item(
                    classe, f"receipts/{indice}", rel(alvo),
                    achado.detail,
                    covered_by=RECEIPT_CODE.get(achado.kind),
                ))

    # -- upstream: a cadeia inteira confere com o disco ------------------------
    for fase, artefato in artefatos.items():
        declarado = artefato.meta.get("upstream")
        if not declarado or not declarado.get("path"):
            continue
        alvo = resolve_within(repo, str(declarado["path"]))
        if alvo is None or not alvo.is_file():
            itens.append(_item(
                "stale", fase, rel(artefato.path),
                f"o upstream {declarado['path']} nao existe",
                covered_by="upstream_missing",
            ))
        elif text_sha256(alvo) != declarado.get("sha256"):
            itens.append(_item(
                "stale", fase, rel(artefato.path),
                f"o upstream {declarado['path']} mudou depois do stamp",
                covered_by="upstream_stale",
            ))
    return itens


def _le_head(gitdir: Path) -> tuple[str | None, str | None]:
    """(branch, commit) lidos de `.git` por arquivo -- nunca por subprocess."""
    head = gitdir / "HEAD"
    try:
        texto = head.read_text(encoding="utf-8").strip()
    except OSError:
        return None, None
    if not texto.startswith("ref:"):
        return None, texto[:40] or None
    ref = texto[4:].strip()
    branch = ref.rsplit("/", 1)[-1]
    candidato = gitdir / ref
    try:
        commit = candidato.read_text(encoding="utf-8").strip()
        return branch, commit or None
    except OSError:
        pass
    try:
        packed = (gitdir / "packed-refs").read_text(encoding="utf-8")
    except OSError:
        return branch, None
    for linha in packed.splitlines():
        if linha.endswith(f" {ref}"):
            return branch, linha.split(" ", 1)[0]
    return branch, None


def _git(repo: Path) -> dict[str, Any]:
    """O que o `.git` local informa sem rodar git: branch e commit ancoram o diff."""
    ponto = repo / ".git"
    if ponto.is_file():
        # worktree: `.git` e um arquivo com `gitdir: <caminho>`
        try:
            conteudo = ponto.read_text(encoding="utf-8").strip()
        except OSError:
            conteudo = ""
        if not conteudo.startswith("gitdir:"):
            return {"available": False, "reason": ".git e arquivo sem gitdir:"}
        ponto = (repo / conteudo[len("gitdir:"):].strip()).resolve()
    if not ponto.is_dir():
        return {
            "available": False,
            "reason": "sem .git: codigo modificado e julgado so pelos artefatos",
        }
    branch, commit = _le_head(ponto)
    return {
        "available": True,
        "head": branch,
        "commit": commit,
        "diff_stats": "unavailable: o motor nao roda subprocess de git",
    }


def converge(
    repo: Path | str, root: str = DEFAULT_ROOT, feature: str | None = None
) -> dict[str, Any]:
    """O relatorio de convergencia `forge/ConvergenceReport/v1`. So le."""
    from sparkforge_aws.sdd.checks import evaluate  # tardio: checks importa este modulo

    relatorio, contextos = evaluate(repo, root, feature)
    itens: list[dict[str, Any]] = []
    for nome in sorted(contextos):
        ctx = contextos[nome]
        for item in converge_artefatos(ctx.repo, ctx.caminhos, ctx.artefatos, ctx.rel):
            itens.append({"feature": nome, **item})
    counts = {classe: sum(1 for i in itens if i["class"] == classe) for classe in CLASSES}
    return {
        "schema": SCHEMA_ID,
        "ok": not any(i["class"] != "unrequested" for i in itens),
        "root": root,
        "features": relatorio["features"],
        "items": itens,
        "counts": counts,
        "git": _git(Path(repo)),
        "refused": relatorio["refused"],
        "unresolved": relatorio["unresolved"],
    }
