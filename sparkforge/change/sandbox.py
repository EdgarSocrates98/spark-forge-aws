"""L2 do §15 (sandbox execute): o diff numa copia isolada, e o que ele move nos achados.

Duas copias do repositorio sob `.sparkforge/sandbox/<id>/`: `before/`, pristina,
e `after/`, com o diff aplicado. Cada uma passa pelo mesmo `scan` (injetado por
quem chama, para este modulo nao importar `adapters`), e a comparacao e a do
`simulate`, pela chave estavel do subject. Duas raizes separadas e o que impede
estado de um lado vazar no outro, e deixa o operador comparar as arvores com a
ferramenta que quiser.

A arvore principal nunca e escrita: toda recusa sai antes do primeiro byte em
disco, e o unico diretorio criado e o do `id`. A copia usa a varredura de
`facts/scan.py`, que nao le arquivo sensivel e poda `.venv`, `vendor`, `build` e
o proprio `.sparkforge` -- exceto `.sparkforge/artifacts/`, copiado a parte
porque e onde o `scan` acha os artefatos coletados.

O relatorio nao afirma ganho (regra 13): a diferenca de achados diz o que a
mudanca move no que o motor ve, e `next_steps` nomeia a medida que falta.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from sparkforge.change.apply import apply_patches, parse_unified_diff
from sparkforge.change.refusals import (
    ARQUIVO_FORA_DA_COPIA,
    CAMINHO_FORA_DA_RAIZ,
    ChangeError,
)
from sparkforge.facts.scan import varrer_source_files
from sparkforge.paths import resolve_within
from sparkforge.simulate.diff import diff as comparar

STAGE_SANDBOX = "sandbox_execute"
SANDBOX_DIR = PurePosixPath(".sparkforge/sandbox")
ARTIFACTS_DIR = PurePosixPath(".sparkforge/artifacts")
ID_HEX = 16
# O estado do proprio SparkForge (e as copias anteriores do sandbox) fica fora
# da copia por poda e fora de `copy_skipped`: listá-lo mudaria o relatorio da
# segunda execucao sobre a mesma entrada, que a primeira criou.
ESTADO_PROPRIO = ".sparkforge"

Varrer = Callable[[Path], Mapping[str, Any]]


@dataclass(frozen=True)
class Copia:
    manifesto: tuple[tuple[str, str], ...]
    origens: dict[str, Path]
    pulos: dict[str, str]


def _sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def inventariar(repo: Path) -> Copia:
    raiz = Path(repo).expanduser()
    varredura = varrer_source_files(raiz, "*")
    origens = {origem.relative_to(raiz).as_posix(): origem for origem in varredura.arquivos}
    pulos = {pulo.relativo: pulo.razao for pulo in varredura.pulos}
    artefatos = resolve_within(raiz, ARTIFACTS_DIR.as_posix())
    if artefatos is not None and artefatos.is_dir():
        extra = varrer_source_files(artefatos, "*")
        for origem in extra.arquivos:
            origens[(ARTIFACTS_DIR / origem.relative_to(artefatos).as_posix()).as_posix()] = origem
        for pulo in extra.pulos:
            pulos[(ARTIFACTS_DIR / pulo.relativo).as_posix()] = pulo.razao
    manifesto = tuple(sorted((rel, _sha256(caminho)) for rel, caminho in origens.items()))
    return Copia(manifesto=manifesto, origens=origens, pulos=pulos)


def sandbox_id(diff_texto: str, manifesto: Sequence[tuple[str, str]]) -> str:
    resumo = hashlib.sha256(diff_texto.encode("utf-8") + b"\0")
    for rel, sha in manifesto:
        resumo.update(f"{rel}\t{sha}\n".encode())
    return resumo.hexdigest()[:ID_HEX]


def _razao_do_pulo(rel: str, pulos: Mapping[str, str]) -> str | None:
    caminho = PurePosixPath(rel)
    for candidato in (caminho, *caminho.parents):
        if candidato.as_posix() in pulos:
            return pulos[candidato.as_posix()]
    return None


def _diretorio_do_id(raiz: Path, ident: str) -> Path:
    alvo = resolve_within(raiz, (SANDBOX_DIR / ident).as_posix())
    if alvo is None:
        raise ChangeError(CAMINHO_FORA_DA_RAIZ, f"{SANDBOX_DIR} resolve para fora de {raiz}")
    return alvo


def _copiar(copia: Copia, destino: Path) -> None:
    for rel, origem in copia.origens.items():
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem, alvo)


def _vazio() -> dict[str, Any]:
    return {
        "stage": STAGE_SANDBOX,
        "applied": False,
        "main_tree_touched": False,
        "refused": [],
        "sandbox": None,
        "id": None,
        "before": None,
        "after": None,
        "files_changed": [],
        "new": [],
        "resolved": [],
        "kept_count": 0,
        "moved_candidates": [],
        "proof_obligations": [],
        "next_steps": [],
        "copy_skipped": [],
        "scan_refused": {"before": [], "after": []},
    }


def recusa(exc: ChangeError) -> dict[str, Any]:
    return {**_vazio(), "refused": [exc.to_dict()]}


def _obrigacoes(
    itens: Sequence[Mapping[str, Any]], findings: Sequence[Mapping[str, Any]], lado: str
) -> list[dict[str, Any]]:
    por_chave = {
        (f.get("rule_id"), json.dumps(f.get("subject") or {}, sort_keys=True)): f for f in findings
    }
    saida: dict[str, dict[str, Any]] = {}
    for item in itens:
        achado = por_chave.get((item["rule_id"], json.dumps(item["subject"], sort_keys=True))) or {}
        saida.setdefault(
            str(item["rule_id"]),
            {
                "rule_id": str(item["rule_id"]),
                "side": lado,
                "validation": [str(v) for v in achado.get("validation") or []],
                "rollback": [str(r) for r in achado.get("rollback") or []],
            },
        )
    return [saida[chave] for chave in sorted(saida)]


def _deslocados(
    novos: Sequence[Mapping[str, Any]], resolvidos: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    pares = []
    for novo in novos:
        for velho in resolvidos:
            arquivo = (novo["subject"] or {}).get("file")
            if (
                novo["rule_id"] == velho["rule_id"]
                and arquivo
                and arquivo == (velho["subject"] or {}).get("file")
            ):
                pares.append(
                    {
                        "rule_id": str(novo["rule_id"]),
                        "file": str(arquivo),
                        "before_line": (velho["subject"] or {}).get("line"),
                        "after_line": (novo["subject"] or {}).get("line"),
                    }
                )
    return pares


def _proximos_passos(depois: str) -> list[dict[str, str]]:
    return [
        {
            "action": "run_your_tests",
            "detail": (
                f"rode os seus testes sobre {depois}: o sandbox nao executa comando do "
                "repositorio"
            ),
        },
        {
            "action": "sparkforge benchmark",
            "detail": (
                "desempenho so se afirma com dois runs medidos, antes e depois; a diferenca de "
                "achados nao e ganho"
            ),
        },
        {
            "action": "sparkforge funcval plan",
            "detail": (
                "confira que o resultado continua o mesmo: contagem, schema, chaves, agregados"
            ),
        },
    ]


def executar(
    repo: Path | str,
    diff_texto: str,
    varrer: Varrer,
    stable_keys: Mapping[str, list[str]],
) -> dict[str, Any]:
    raiz = Path(repo).expanduser()
    try:
        patches = parse_unified_diff(diff_texto)
        copia = inventariar(raiz)
        for patch in patches:
            if patch.path not in copia.origens:
                razao = _razao_do_pulo(patch.path, copia.pulos) or "ausente_no_repositorio"
                raise ChangeError(ARQUIVO_FORA_DA_COPIA, f"{patch.path}: fora da copia ({razao})")
        tocados = {patch.path: copia.origens[patch.path].read_bytes() for patch in patches}
        aplicados = apply_patches(tocados, patches)
        ident = sandbox_id(diff_texto, copia.manifesto)
        base = _diretorio_do_id(raiz, ident)
    except ChangeError as exc:
        return recusa(exc)

    if base.exists():
        shutil.rmtree(base)
    antes, depois = base / "before", base / "after"
    try:
        _copiar(copia, antes)
        _copiar(copia, depois)
        for rel, dados in aplicados.items():
            (depois / rel).write_bytes(dados)
        lado_antes = varrer(antes)
        lado_depois = varrer(depois)
    except Exception:
        shutil.rmtree(base, ignore_errors=True)
        raise

    comparacao = comparar(
        list(lado_antes["findings"]), list(lado_depois["findings"]), [], [], stable_keys
    )
    novos, resolvidos = comparacao["appeared"], comparacao["disappeared"]
    rel_base = SANDBOX_DIR / ident
    relatorio = {
        **_vazio(),
        "applied": True,
        "sandbox": rel_base.as_posix(),
        "id": ident,
        "before": (rel_base / "before").as_posix(),
        "after": (rel_base / "after").as_posix(),
        "files_changed": sorted(aplicados),
        "new": novos,
        "resolved": resolvidos,
        "kept_count": comparacao["persisted_count"],
        "moved_candidates": _deslocados(novos, resolvidos),
        "proof_obligations": [
            *_obrigacoes(novos, lado_depois["findings"], "new"),
            *_obrigacoes(resolvidos, lado_antes["findings"], "resolved"),
        ],
        "next_steps": _proximos_passos((rel_base / "after").as_posix()),
        "copy_skipped": [
            {"path": rel, "reason": razao}
            for rel, razao in sorted(copia.pulos.items())
            if rel != ESTADO_PROPRIO
        ],
        "scan_refused": {
            "before": list(lado_antes.get("refused") or []),
            "after": list(lado_depois.get("refused") or []),
        },
    }
    (base / "report.json").write_text(
        json.dumps(relatorio, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return relatorio


def limpar(repo: Path | str) -> dict[str, Any]:
    raiz = Path(repo).expanduser()
    alvo = resolve_within(raiz, SANDBOX_DIR.as_posix())
    if alvo is None:
        raise ChangeError(CAMINHO_FORA_DA_RAIZ, f"{SANDBOX_DIR} resolve para fora de {raiz}")
    removidos = sorted(p.name for p in alvo.iterdir() if p.is_dir()) if alvo.is_dir() else []
    if alvo.exists():
        shutil.rmtree(alvo)
    return {
        "stage": STAGE_SANDBOX,
        "main_tree_touched": False,
        "cleaned": True,
        "removed": removidos,
        "sandbox": SANDBOX_DIR.as_posix(),
    }
