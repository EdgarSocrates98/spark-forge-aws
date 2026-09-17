"""Os gates do SDD: cada falha e uma recusa com nome e o que a destrava."""

from __future__ import annotations

import ast
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from sparkforge.case.store import CASE_DIR, CASE_FILE
from sparkforge.change.proposal import PROPOSAL_DIR
from sparkforge.change.sandbox import SANDBOX_DIR
from sparkforge.facts.scan import (
    DIRECTORY_IGNORED,
    DIRECTORY_REPARSE_POINT,
    DIRECTORY_SENSITIVE,
    Pulo,
)
from sparkforge.paths import resolve_within
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.load import FEATURE_RE, Artifact, discover, load_artifact

_AQUI = Path(__file__).resolve().parent


@cache
def schema_for(phase: str) -> dict[str, Any]:
    """Schema da fase = campos comuns + campos proprios, sem campo extra."""
    comum = json.loads((_AQUI / "schema" / "common.json").read_text(encoding="utf-8"))
    propria = json.loads((_AQUI / "schema" / f"{phase}.json").read_text(encoding="utf-8"))
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": [*comum["required"], *propria.get("required", [])],
        "properties": {**comum["properties"], **propria["properties"]},
    }
    if "$defs" in propria:
        schema["$defs"] = propria["$defs"]
    return schema


@cache
def change_kinds() -> dict[str, dict[str, Any]]:
    return yaml.safe_load((_AQUI / "change_kinds.yaml").read_text(encoding="utf-8"))


PREDECESSOR: dict[str, str] = {
    "design": "define",
    "plan": "design",
    "build_report": "plan",
    "ship": "build_report",
}
PRONTO = ("ready", "done")


@dataclass
class _Contexto:
    repo: Path
    feature: str
    caminhos: dict[str, Path]
    artefatos: dict[str, Artifact] = field(default_factory=dict)
    refused: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[dict[str, Any]] = field(default_factory=list)

    def rel(self, caminho: Path) -> str:
        try:
            return caminho.resolve().relative_to(self.repo.resolve()).as_posix()
        except ValueError:
            return str(caminho)

    def recusa(self, code: str, caminho: Path, campo: str | None, unlock: str) -> None:
        self.refused.append(
            {"code": code, "feature": self.feature, "path": self.rel(caminho),
             "field": campo, "unlock": unlock}
        )

    def lacuna(self, code: str, caminho: Path, unlock: str) -> None:
        self.unresolved.append(
            {"code": code, "feature": self.feature, "path": self.rel(caminho), "unlock": unlock}
        )


Gate = Callable[[_Contexto, str, Artifact], None]


def _carrega(ctx: _Contexto) -> None:
    for fase in PHASES:
        caminho = ctx.caminhos.get(fase)
        if caminho is None:
            continue
        artefato = load_artifact(caminho)
        if artefato.error is not None:
            ctx.recusa("schema_invalid", caminho, None, artefato.error)
            continue
        erros = sorted(
            Draft202012Validator(schema_for(fase)).iter_errors(artefato.meta),
            key=lambda erro: [str(parte) for parte in erro.absolute_path],
        )
        if erros:
            for erro in erros:
                campo = "/".join(str(parte) for parte in erro.absolute_path) or None
                ctx.recusa("schema_invalid", caminho, campo, erro.message)
            continue
        if artefato.meta["phase"] != fase:
            ctx.recusa("schema_invalid", caminho, "phase",
                       f"o arquivo {fase}.md declara phase {artefato.meta['phase']}")
            continue
        if artefato.meta["feature"] != ctx.feature:
            ctx.recusa("schema_invalid", caminho, "feature",
                       f"o arquivo mora em {ctx.feature}/ e declara feature "
                       f"{artefato.meta['feature']}")
            continue
        ctx.artefatos[fase] = artefato


def _gate_order(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    anterior = PREDECESSOR[fase]
    if anterior in ctx.caminhos and anterior not in ctx.artefatos:
        return  # o anterior existe e ja foi recusado por schema; nao repete a causa
    previo = ctx.artefatos.get(anterior)
    if previo is None or previo.meta["status"] not in PRONTO:
        ctx.recusa("phase_out_of_order", artefato.path, "phase",
                   f"{fase} exige {anterior}.md com status ready ou done")


def _upstream_esperado(ctx: _Contexto, fase: str) -> str | None:
    if fase in PREDECESSOR:
        return PREDECESSOR[fase]
    if fase == "define" and "explore" in ctx.caminhos:
        return "explore"
    return None


def _gate_upstream(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    esperado = _upstream_esperado(ctx, fase)
    declarado = artefato.meta.get("upstream")
    if esperado is None:
        if declarado is not None:
            motivo = (
                "explore e a primeira fase e nao tem upstream"
                if fase == "explore"
                else "define so declara upstream quando explore.md existe na feature"
            )
            ctx.recusa("schema_invalid", artefato.path, "upstream",
                       f"{motivo}; remova o bloco upstream")
        return
    esperado_rel = f"{ctx.rel(ctx.caminhos[esperado])}" if esperado in ctx.caminhos else (
        f"{ctx.rel(artefato.path.parent)}/{esperado}.md"
    )
    if declarado is None:
        ctx.recusa("upstream_missing", artefato.path, "upstream",
                   f"declare upstream.path: {esperado_rel} e rode `sparkforge sdd stamp`")
        return
    alvo = resolve_within(ctx.repo, declarado["path"])
    if alvo is None or not alvo.is_file():
        ctx.recusa("upstream_missing", artefato.path, "upstream/path",
                   f"{declarado['path']} nao existe; o upstream de {fase} e {esperado_rel}")
        return
    if esperado in ctx.caminhos and alvo != ctx.caminhos[esperado].resolve():
        ctx.recusa("upstream_missing", artefato.path, "upstream/path",
                   f"{declarado['path']} nao e o upstream de {fase}; use {esperado_rel}")
        return
    if declarado["sha256"] != text_sha256(alvo):
        ctx.recusa("upstream_stale", artefato.path, "upstream/sha256",
                   f"{declarado['path']} mudou; revise {fase} e rode "
                   f"`sparkforge sdd stamp --repo . {ctx.rel(artefato.path)}`")


def _nomes_de_teste(corpo: list[ast.stmt], prefixo: str = "") -> set[str]:
    """Os nomes que o pytest coleta por padrao: `test*` e `Test*`, com classe aninhada."""
    nomes: set[str] = set()
    for no in corpo:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if no.name.startswith("test"):
                nomes.add(f"{prefixo}{no.name}")
        elif isinstance(no, ast.ClassDef) and no.name.startswith("Test"):
            nomes |= _nomes_de_teste(no.body, f"{prefixo}{no.name}::")
    return nomes


def _separa_ref(referencia: str) -> tuple[str, str]:
    """(arquivo, nome) de um node id do pytest, sem o sufixo `[...]` do parametrize."""
    caminho, _, nome = referencia.partition("::")
    if nome.endswith("]") and "[" in nome:
        nome = nome[: nome.index("[")]
    return caminho, nome


def _ref_de_teste_valida(referencia: str) -> bool:
    caminho, nome = _separa_ref(referencia)
    return bool(caminho) and bool(nome) and all(nome.split("::"))


def _teste_existe(repo: Path, referencia: str) -> bool:
    caminho, nome = _separa_ref(referencia)
    alvo = resolve_within(repo, caminho) if caminho else None
    if alvo is None or not alvo.is_file() or not nome:
        return False
    try:
        arvore = ast.parse(alvo.read_bytes())
    except (OSError, SyntaxError, ValueError):
        return False
    return nome in _nomes_de_teste(arvore.body)


def _build_pronto(ctx: _Contexto) -> bool:
    """O build_report da feature carregou e esta ready ou done: o build ja aconteceu."""
    build = ctx.artefatos.get("build_report")
    return build is not None and build.meta["status"] in PRONTO


def _conferir_teste(
    ctx: _Contexto, artefato: Artifact, campo: str, referencia: str, dono: str
) -> None:
    if _teste_existe(ctx.repo, referencia):
        return
    if _build_pronto(ctx):
        ctx.recusa("verified_by_dangling", artefato.path, campo,
                   f"{referencia} nao existe depois do build; escreva o teste ou corrija a "
                   "referencia")
    else:
        ctx.lacuna("test_not_written", artefato.path,
                   f"{referencia} ainda nao existe; o build escreve o teste de {dono} antes do "
                   "codigo")


def _itens_de_fact(arquivo: Path) -> list[dict[str, Any]]:
    """Os facts de um arquivo: lista crua ou `{"items": [...]}`; o resto vira lista vazia."""
    try:
        dado = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    itens = dado.get("items", []) if isinstance(dado, dict) else dado
    if not isinstance(itens, list):
        return []
    return [item for item in itens if isinstance(item, dict)]


_SELETOR_KIND = "kind:"


def _fact_presente(arquivo: Path, seletor: str) -> bool:
    """`#<id>` casa o id; `#kind:<kind>` casa qualquer fact daquele kind."""
    itens = _itens_de_fact(arquivo)
    if seletor.startswith(_SELETOR_KIND):
        kind = seletor[len(_SELETOR_KIND):]
        return bool(kind) and any(item.get("kind") == kind for item in itens)
    return seletor in {str(item["id"]) for item in itens if item.get("id")}


def _conferir_fact(ctx: _Contexto, artefato: Artifact, referencia: str) -> None:
    caminho, _, seletor = referencia.partition("#")
    alvo = resolve_within(ctx.repo, caminho) if caminho else None
    if alvo is None or not alvo.is_file() or not _fact_presente(alvo, seletor):
        ctx.lacuna("fact_not_collected", artefato.path,
                   f"{seletor or referencia} nao esta em {caminho}; colete o artefato e "
                   "rode o `sparkforge analyze` que o extrai")


def _gate_success_source(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, item in enumerate(artefato.meta["success"]):
        if not str(item.get("source") or "").strip():
            ctx.recusa("success_without_source", artefato.path, f"success/{indice}/source",
                       f"diga de onde vem o numero de {item['id']} (regra 24)")


def _gate_change_kinds(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    conhecidos = change_kinds()
    for indice, chave in enumerate(artefato.meta["change_kinds"]):
        if chave not in conhecidos:
            ctx.recusa("schema_invalid", artefato.path, f"change_kinds/{indice}",
                       f"'{chave}' nao existe em sparkforge/sdd/change_kinds.yaml; use uma de: "
                       + ", ".join(sorted(conhecidos)))


def _conferir_funcval(
    ctx: _Contexto, artefato: Artifact, campo: str, alvo: Path, referencia: str
) -> None:
    # a FORMA da comparacao, nunca o veredito: divergir ou nao e das SF-FVAL no judge
    itens = _itens_de_fact(alvo)
    if not any(item.get("kind") == "funcval.check_delta" for item in itens):
        ctx.recusa("funcval_not_comparison", artefato.path, campo,
                   f"{referencia} nao tem nenhum funcval.check_delta; rode `sparkforge funcval "
                   f"compare --plan <plano> --before <a> --after <b> --out {referencia}`")
        return
    for item in itens:
        if item.get("kind") == "funcval.unresolved":
            ctx.lacuna("funcval_blind_spot", artefato.path,
                       f"{referencia} nao comparou {_nome_do_ponto_cego(item)}; resolva o motivo "
                       "e rode `sparkforge funcval compare` de novo")


def _nome_do_ponto_cego(item: dict[str, Any]) -> str:
    """O que o funcval deixou sem comparar: o `symbol` do subject (ou o subject cru) e o motivo."""
    sujeito = item.get("subject")
    sujeito = sujeito if isinstance(sujeito, dict) else {}
    nome = _texto_ou_none(sujeito.get("symbol")) or ", ".join(
        f"{chave}={valor}" for chave, valor in sorted(sujeito.items())
    ) or str(item.get("id") or "?")
    atributos = item.get("attrs")
    motivo = _texto_ou_none(atributos.get("reason")) if isinstance(atributos, dict) else None
    return f"{nome} (reason: {motivo})" if motivo else nome


def _gate_verified_by(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, item in enumerate(artefato.meta["acceptance"]):
        prova = item["verified_by"]
        campo = f"acceptance/{indice}/verified_by"
        referencia = prova["ref"]
        if prova["kind"] == "test":
            if not _ref_de_teste_valida(referencia):
                ctx.recusa("schema_invalid", artefato.path, f"{campo}/ref",
                           f"'{referencia}' nao e node id do pytest; use "
                           "tests/arquivo.py::test_nome (ou ::TestClasse::test_nome)")
                continue
            _conferir_teste(ctx, artefato, campo, referencia, item["id"])
        elif prova["kind"] == "fact":
            _conferir_fact(ctx, artefato, referencia)
        elif prova["kind"] == "funcval":
            alvo = resolve_within(ctx.repo, referencia)
            if alvo is None or not alvo.is_file():
                ctx.lacuna("funcval_not_run", artefato.path,
                           f"rode `sparkforge funcval compare --out {referencia}` para "
                           f"{item['id']}")
                continue
            _conferir_funcval(ctx, artefato, campo, alvo, referencia)


def _gate_manifest(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    # delete sumido depois do build pronto e o design cumprido, nao caminho errado;
    # modify sumido e erro em qualquer fase
    build_pronto = _build_pronto(ctx)
    for indice, item in enumerate(artefato.meta["files"]):
        if item["action"] == "create":
            continue
        alvo = resolve_within(ctx.repo, item["path"])
        if alvo is not None and item["action"] == "delete" and build_pronto:
            continue
        if alvo is None or not alvo.exists():
            ctx.recusa("manifest_path_unknown", artefato.path, f"files/{indice}/path",
                       f"{item['path']} nao existe para {item['action']}; confira o caminho ou "
                       "use action: create")


def _gate_rollback(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, decisao in enumerate(artefato.meta["decisions"]):
        if not str(decisao.get("rollback") or "").strip():
            ctx.recusa("rollback_missing", artefato.path, f"decisions/{indice}/rollback",
                       f"diga como desfazer {decisao['id']}")


def _gate_cobertura(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    define = ctx.artefatos.get("define")
    if define is None:
        return
    if fase == "design":
        cobertos = {ac for parte in artefato.meta["covers"] for ac in parte["acceptance"]}
        campo = "covers"
    else:
        cobertos = {ac for tarefa in artefato.meta["tasks"] for ac in tarefa["covers"]}
        campo = "tasks"
    for item in define.meta["acceptance"]:
        if item["id"] not in cobertos:
            ctx.recusa("acceptance_uncovered", artefato.path, campo,
                       f"{item['id']} do define nao aparece em nenhum covers do {fase}")


def _gate_task_test(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, tarefa in enumerate(artefato.meta["tasks"]):
        teste = tarefa.get("test")
        campo = f"tasks/{indice}/test"
        if not teste:
            ctx.recusa("task_without_test", artefato.path, campo,
                       f"{tarefa['id']} precisa do teste que falha antes do codigo")
            continue
        _conferir_teste(ctx, artefato, campo, f"{teste['path']}::{teste['name']}", tarefa["id"])


def _gate_red(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, tarefa in enumerate(artefato.meta["tasks"]):
        if tarefa["status"] != "done":
            continue
        vermelho = tarefa.get("red")
        if not vermelho or vermelho["exit"] == 0:
            ctx.recusa("red_not_declared", artefato.path, f"tasks/{indice}/red",
                       f"registre o comando que falhou antes do codigo de {tarefa['id']} "
                       "(exit diferente de zero)")


def _gate_claims(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, afirmacao in enumerate(artefato.meta["claims"]):
        if not str(afirmacao.get("evidence_ref") or "").strip():
            ctx.recusa("claim_without_evidence", artefato.path, f"claims/{indice}/evidence_ref",
                       "aponte o arquivo, teste ou fact que sustenta a afirmacao")


def _gate_hypothesis(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    if not artefato.meta.get("hypothesis_outcome"):
        ctx.recusa("hypothesis_open_at_ship", artefato.path, "hypothesis_outcome",
                   "feche a hipotese com confirmed, refuted ou abandoned, sem reescrever a "
                   "afirmacao (regra 21)")


def _gate_registries(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    define = ctx.artefatos.get("define")
    if define is None:
        return
    conhecidos = change_kinds()
    marcados = set(artefato.meta["registries"])
    vistos: set[str] = set()
    for chave in define.meta["change_kinds"]:
        tipo = conhecidos.get(chave)
        if tipo is None:
            continue
        for registro in tipo["registries"]:
            if registro in marcados or registro in vistos:
                continue
            vistos.add(registro)
            ctx.recusa("registry_unchecked", artefato.path, "registries",
                       f"{registro} e exigido por '{tipo['section']}' "
                       "(docs/gates-por-mudanca.md); rode o gate e liste-o")


def _texto_ou_none(valor: Any) -> str | None:
    texto = "" if valor is None else str(valor).strip()
    return texto or None


def _case_id_atual(repo: Path) -> str | None:
    arquivo = repo / CASE_DIR / CASE_FILE
    if not arquivo.is_file():
        return None
    try:
        dado = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return _texto_ou_none(dado.get("case_id")) if isinstance(dado, dict) else None


def _ship_feito(ctx: _Contexto) -> bool:
    """O ship carregou com status done: case e mudanca citados viraram historia."""
    ship = ctx.artefatos.get("ship")
    return ship is not None and ship.meta["status"] == "done"


def _gate_case(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    if artefato.meta["profile"] != "operator" or _ship_feito(ctx):
        return
    declarado = _texto_ou_none(artefato.meta.get("case_id"))
    if declarado is None or declarado != _case_id_atual(ctx.repo):
        ctx.recusa("case_missing", artefato.path, "case_id",
                   "abra o case com `sparkforge case open` e copie o case_id dele para o define")


_BASES_DA_MUDANCA: tuple[tuple[PurePosixPath, str], ...] = (
    (SANDBOX_DIR, "report.json"),
    (PROPOSAL_DIR, "evidence/sandbox_report.json"),
)


def _pastas_da_mudanca(repo: Path, ident: str) -> list[tuple[Path, str]]:
    """As pastas de `ident` que existem, com o relatorio que cada uma guarda."""
    # um segmento so, sem separador: `..`, `.` e `a/../b` nao sao id de mudanca
    if not ident or "/" in ident or "\\" in ident or ident in (".", ".."):
        return []
    achadas: list[tuple[Path, str]] = []
    for base_rel, relatorio in _BASES_DA_MUDANCA:
        base = repo / base_rel
        alvo = resolve_within(base, ident)
        if alvo is not None and alvo.parent == base.resolve() and alvo.is_dir():
            achadas.append((alvo, relatorio))
    return achadas


def _gate_change(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    if artefato.meta["profile"] != "operator" or _ship_feito(ctx):
        return
    ident = str(artefato.meta.get("change_id") or "")
    if not _pastas_da_mudanca(ctx.repo, ident):
        ctx.recusa("change_missing", artefato.path, "change_id",
                   "o build do operador passa por `sparkforge change sandbox`; registre o id "
                   "em change_id (vale enquanto existir .sparkforge/sandbox/<id>/ ou "
                   ".sparkforge/proposal/<id>/)")


_GATES: dict[str, tuple[Gate, ...]] = {
    "explore": (_gate_upstream,),
    "define": (
        _gate_upstream, _gate_success_source, _gate_change_kinds, _gate_verified_by, _gate_case,
    ),
    "design": (_gate_order, _gate_upstream, _gate_manifest, _gate_rollback, _gate_cobertura),
    "plan": (_gate_order, _gate_upstream, _gate_cobertura, _gate_task_test),
    "build_report": (_gate_order, _gate_upstream, _gate_red, _gate_claims, _gate_change),
    "ship": (_gate_order, _gate_upstream, _gate_hypothesis, _gate_registries),
}


def _check_feature(repo: Path, feature: str, caminhos: dict[str, Path]) -> _Contexto:
    ctx = _Contexto(repo=repo, feature=feature, caminhos=caminhos)
    _carrega(ctx)
    for fase in PHASES:
        artefato = ctx.artefatos.get(fase)
        if artefato is None:
            continue
        for gate in _GATES[fase]:
            gate(ctx, fase, artefato)
    return ctx


_RAZOES_DE_PASTA = frozenset({DIRECTORY_IGNORED, DIRECTORY_SENSITIVE, DIRECTORY_REPARSE_POINT})


def _pulo_alcancavel(pulo: Pulo) -> bool:
    """O pulo esconde algo que `discover` leria como feature ou artefato?

    So estes contam: pasta de primeiro nivel com nome de feature, pasta de segundo
    nivel dentro de uma, e `.md` de fase dentro de uma. O resto (arquivo na raiz,
    `templates/vendor/`, fundo demais) a descoberta ignoraria mesmo sem a poda, e
    virar lacuna deixaria `ok` falso para sempre.
    """
    partes = pulo.relativo.split("/")
    if not FEATURE_RE.fullmatch(partes[0]):
        return False
    if pulo.razao in _RAZOES_DE_PASTA:
        return len(partes) <= 2
    return len(partes) == 2 and partes[1].endswith(".md") and partes[1][: -len(".md")] in PHASES


def _lacuna_de_pulo(root: str, pulo: Pulo) -> dict[str, Any]:
    """Um caminho que a varredura nao leu vira lacuna com nome, nunca silencio."""
    return {
        "code": "path_skipped",
        "feature": pulo.relativo.split("/")[0],
        "path": f"{root.rstrip('/')}/{pulo.relativo}",
        "unlock": (
            f"a varredura pulou {pulo.relativo} ({pulo.razao}): o nome esta na lista de "
            "pulos de sparkforge/facts/scan.py; renomeie a pasta ou o arquivo para que "
            "o SDD o leia"
        ),
    }


def evaluate(
    repo: Path | str, root: str, feature: str | None
) -> tuple[dict[str, Any], dict[str, _Contexto]]:
    """Uma varredura so: o relatorio do `check` e o contexto de cada feature.

    `status` le os mesmos contextos, entao os dois nunca discordam sobre a arvore.
    """
    raiz_repo = Path(repo)
    raiz = resolve_within(raiz_repo, root)
    if raiz is None or not raiz.is_dir():
        return {
            "ok": False,
            "root": root,
            "features": [],
            "refused": [],
            "unresolved": [{
                "code": "root_missing", "feature": None, "path": root,
                "unlock": f"crie {root}/<FEATURE>/ ou passe --root para a pasta dos artefatos",
            }],
        }, {}
    descoberta = discover(raiz)
    todas = descoberta.features
    nomes = sorted(todas) if feature is None else [n for n in sorted(todas) if n == feature]
    refused: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for pulo in descoberta.pulos:
        if not _pulo_alcancavel(pulo):
            continue
        item = _lacuna_de_pulo(root, pulo)
        if feature is None or item["feature"] == feature:
            unresolved.append(item)
    contextos: dict[str, _Contexto] = {}
    for nome in nomes:
        ctx = _check_feature(raiz_repo, nome, todas[nome])
        contextos[nome] = ctx
        refused.extend(ctx.refused)
        unresolved.extend(ctx.unresolved)
    return {
        "ok": not refused and not unresolved,
        "root": root,
        "features": nomes,
        "refused": refused,
        "unresolved": unresolved,
    }, contextos


def check(repo: Path | str, root: str = DEFAULT_ROOT, feature: str | None = None) -> dict[str, Any]:
    """`{ok, root, features, refused, unresolved}` sobre `repo/root`."""
    return evaluate(repo, root, feature)[0]
