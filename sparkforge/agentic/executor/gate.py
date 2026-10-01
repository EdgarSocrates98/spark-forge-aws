"""O Debate ROI Gate (§11 de `prompt_new_evo.md`): este par pede debate?

Todo par de contradicao direta que a arbitragem nao fecha vira plano de debate
(`run._arbitra_pares`). Debate e a etapa mais cara do fluxo -- o host gasta
rodadas de modelo --, e nem todo par o justifica: um pede medida antes, outro e
barato o bastante para decisao humana direta. Este modulo diz qual, e por que.

## A ordem, e por que ela e esta

A primeira regra que casa vence:

1. ha `Unknown` bloqueante citando o par, com o `Experiment` que o mede ->
   `experimentar_antes`. Debate nao cria a medida que falta; ele so reextrai
   artefato que ja existe.
2. severidade em `debate_severities`, ou `kind` declarado `reversible: false`,
   ou arbitragem sem lastro (`escalate`, ou sem claim vencedora) -> `debater`.
3. todos os sinais de decisao conhecidos, e nenhum dos acima -> `nao_debater`.
4. senao -> `unresolved`, nomeando cada sinal que falta.

Condicao suficiente CONHECIDA decide mesmo com outro sinal ausente: um P0 medido
nao deixa de abrir debate porque o `kind` do outro lado nao declara
reversibilidade. So `nao_debater` exige tudo conhecido -- dispensar debate por
falta de dado seria decidir pelo que nao se sabe.

## O que o gate NAO faz

Nao pesa nem pontua sinal: pesos seriam convencao sem calibracao, o defeito que o
`CLAUDE.md` aponta em `assess_claim`. Nao calcula `expected_information_gain`:
sem modelo de probabilidade nao ha fonte, e ele sai em `refused` com o motivo.
Nao afirma quanto um debate evitado poupa -- a regra 30 do `CLAUDE.md` proibe
afirmacao sem benchmark dos dois lados.

## Politica invalida nao derruba o plano

`debate_gate.yaml` ausente ou malformado vira `verdict: unresolved` com a
mensagem, e o plano sai do mesmo jeito (regra 27: instrumentacao que quebra o
produto e defeito). O mesmo para `action_kinds.yaml`: sem o vocabulario, a
reversibilidade de cada lado sai ausente, e so decide outro sinal suficiente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sparkforge.agentic.executor.unknowns import experiments_from
from sparkforge.rules.loader import CatalogError, catalog_dir, safe_catalog_file

POLICY_FILE = "debate_gate.yaml"
KINDS_FILE = "action_kinds.yaml"
SEVERIDADES = ("P0", "P1", "P2", "P3")

EXPERIMENTAR_ANTES = "experimentar_antes"
DEBATER = "debater"
NAO_DEBATER = "nao_debater"
UNRESOLVED = "unresolved"
VEREDITOS = (EXPERIMENTAR_ANTES, DEBATER, NAO_DEBATER, UNRESOLVED)

_ARBITRAGEM_SEM_LASTRO = frozenset({"escalate", "sem_vencedor"})

_MOTIVO_SEM_FONTE = (
    "sem fonte: exigiria um modelo de probabilidade do que o debate revelaria, e "
    "nenhum existe neste pacote -- modelo mora no host (regra 23). Um numero aqui "
    "seria inventado"
)

_cache_politica: dict[str, Any] | None = None
_cache_reversibilidade: dict[str, bool | None] | None = None


class GatePolicyError(ValueError):
    """A politica do gate nao pode ser usada; a mensagem nomeia o campo."""


def validate_policy(doc: Any) -> None:
    """Recusa a politica malformada, nomeando o campo."""
    if not isinstance(doc, dict):
        raise GatePolicyError(f"{POLICY_FILE}: esperado um mapa no topo")
    if not isinstance(doc.get("policy_version"), int):
        raise GatePolicyError(f"{POLICY_FILE}: `policy_version` inteiro e obrigatorio")
    severidades = doc.get("debate_severities")
    if (
        not isinstance(severidades, list)
        or not severidades
        or any(s not in SEVERIDADES for s in severidades)
    ):
        raise GatePolicyError(
            f"{POLICY_FILE}: `debate_severities` precisa ser lista nao vazia dentro de "
            f"{list(SEVERIDADES)}"
        )


def load_policy(path: Path | None = None) -> dict[str, Any]:
    """A politica validada. Sem `path`, le do catalogo e memoriza."""
    global _cache_politica
    if path is None and _cache_politica is not None:
        return _cache_politica
    alvo = Path(path) if path is not None else safe_catalog_file(catalog_dir(), POLICY_FILE)
    doc = yaml.safe_load(alvo.read_text(encoding="utf-8-sig"))
    validate_policy(doc)
    if path is None:
        _cache_politica = doc
    return doc


def load_reversibility(path: Path | None = None) -> dict[str, bool | None]:
    """`kind -> reversible`, com `None` para o `kind` que nao declara booleano."""
    global _cache_reversibilidade
    if path is None and _cache_reversibilidade is not None:
        return _cache_reversibilidade
    alvo = Path(path) if path is not None else safe_catalog_file(catalog_dir(), KINDS_FILE)
    doc = yaml.safe_load(alvo.read_text(encoding="utf-8-sig")) or {}
    mapa: dict[str, bool | None] = {}
    for nome, corpo in (doc.get("kinds") or {}).items():
        valor = corpo.get("reversible") if isinstance(corpo, dict) else None
        mapa[str(nome)] = valor if isinstance(valor, bool) else None
    if path is None:
        _cache_reversibilidade = mapa
    return mapa


def fala_de(lacuna: Any, rule_id: str) -> bool:
    """A lacuna cita esta regra, na pergunta ou no impacto?

    As duas origens de `Unknown` nomeiam a regra em campos diferentes: a de
    ancora ausente comeca a pergunta com `finding <rule_id>`, e a de recusa
    nomeia quem cita o fact em `impact`. Procurar nos dois e o que nao perde
    nenhuma das duas.
    """
    return rule_id in str(getattr(lacuna, "question", "")) or rule_id in str(
        getattr(lacuna, "impact", "")
    )


def avaliar(
    regras: tuple[str, str] | list[str],
    resultado: Any,
    findings: list[dict[str, Any]],
    lacunas: list[Any],
    contradicoes: int,
    plano: dict[str, Any],
    politica: dict[str, Any] | None = None,
    reversibilidade: dict[str, bool | None] | None = None,
) -> dict[str, Any]:
    """O bloco `debate_gate` de um par que a arbitragem nao fechou.

    Args:
        regras: o par, na ordem da arbitragem.
        resultado: o `ArbitrationResult` do par.
        findings: os findings julgados do case.
        lacunas: os `Unknown` do case (`unknowns_from`).
        contradicoes: quantas contradicoes diretas o case tem.
        plano: o `debate_plan` do par (participantes lidos para `complexity`).
        politica: a politica ja carregada; `None` le o catalogo.
        reversibilidade: `kind -> reversible`; `None` le o catalogo.

    Returns:
        `{verdict, reasons, missing, signals, refused, policy}`, serializavel.
    """
    par = [str(r) for r in regras]
    erro_de_politica: str | None = None
    if politica is None:
        try:
            politica = load_policy()
        except (GatePolicyError, CatalogError, OSError, yaml.YAMLError) as exc:
            erro_de_politica = str(exc)
    if reversibilidade is None:
        try:
            reversibilidade = load_reversibility()
        except (CatalogError, OSError, yaml.YAMLError):
            reversibilidade = {}

    sinais = _sinais(par, resultado, findings, lacunas, contradicoes, plano, reversibilidade)
    if erro_de_politica is not None:
        veredito, motivos, faltando = UNRESOLVED, [], ["policy"]
        bloco_politica: dict[str, Any] = {"status": "unresolved", "reason": erro_de_politica}
    else:
        veredito, motivos, faltando = _veredito(sinais, politica or {})
        bloco_politica = {
            "status": "declared",
            "file": POLICY_FILE,
            "debate_severities": list((politica or {}).get("debate_severities") or []),
        }
    return {
        "verdict": veredito,
        "reasons": motivos,
        "missing": faltando,
        "signals": sinais,
        "refused": {"expected_information_gain": {"reason": _MOTIVO_SEM_FONTE}},
        "policy": bloco_politica,
    }


def _sinais(
    par: list[str],
    resultado: Any,
    findings: list[dict[str, Any]],
    lacunas: list[Any],
    contradicoes: int,
    plano: dict[str, Any],
    reversibilidade: dict[str, bool | None],
) -> dict[str, Any]:
    severidade = {regra: _pior_severidade(regra, findings) for regra in par}
    kinds = {regra: _kind_da_regra(regra, findings) for regra in par}
    reversivel = {
        regra: (reversibilidade.get(kind) if kind else None) for regra, kind in kinds.items()
    }
    if not getattr(resultado, "winning_claim_id", None):
        arbitragem = "sem_vencedor"
    else:
        arbitragem = str(getattr(resultado, "recommendation", "") or "")
    participantes = len(plano.get("participants") or []) + len(
        plano.get("participants_unresolved") or []
    )
    return {
        "severity": severidade,
        "action_kind": kinds,
        "reversible": reversivel,
        "arbitration": arbitragem,
        "evidence_gap": _lacunas_do_par(par, lacunas),
        "complexity": participantes,
        "contradiction_count": int(contradicoes),
    }


def _veredito(
    sinais: dict[str, Any], politica: dict[str, Any]
) -> tuple[str, list[str], list[str]]:
    if sinais["evidence_gap"]:
        return EXPERIMENTAR_ANTES, ["lacuna_mensuravel"], []
    limiar = set(politica.get("debate_severities") or [])
    motivos: list[str] = []
    faltando: list[str] = []
    for regra, severidade in sinais["severity"].items():
        if severidade is None:
            faltando.append(f"severity:{regra}")
        elif severidade in limiar:
            motivos.append(f"severidade:{regra}={severidade}")
    for regra, reversivel in sinais["reversible"].items():
        if reversivel is None:
            faltando.append(f"reversible:{regra}")
        elif reversivel is False:
            motivos.append(f"irreversivel:{regra}")
    if sinais["arbitration"] in _ARBITRAGEM_SEM_LASTRO:
        motivos.append(f"sem_lastro:{sinais['arbitration']}")
    if motivos:
        return DEBATER, motivos, faltando
    if faltando:
        return UNRESOLVED, [], faltando
    return NAO_DEBATER, ["barato_e_reversivel"], []


def _findings_da_regra(regra: str, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        f
        for f in findings or []
        if isinstance(f, dict) and str(f.get("rule_id") or "").strip() == regra
    ]


def _pior_severidade(regra: str, findings: list[dict[str, Any]]) -> str | None:
    """A severidade mais grave entre os findings da regra, ou `None`."""
    validas = [
        str(f.get("severity")) for f in _findings_da_regra(regra, findings)
        if str(f.get("severity")) in SEVERIDADES
    ]
    return min(validas, key=SEVERIDADES.index) if validas else None


def _kind_da_regra(regra: str, findings: list[dict[str, Any]]) -> str | None:
    for finding in _findings_da_regra(regra, findings):
        acao = finding.get("action")
        if isinstance(acao, dict) and str(acao.get("kind") or "").strip():
            return str(acao["kind"]).strip()
    return None


def _lacunas_do_par(par: list[str], lacunas: list[Any]) -> list[dict[str, Any]]:
    """As lacunas bloqueantes que citam o par, com o experimento que as mede."""
    do_par = [
        u for u in lacunas or []
        if getattr(u, "blocking", False) and any(fala_de(u, regra) for regra in par)
    ]
    saida: list[dict[str, Any]] = []
    for lacuna in do_par:
        # Um por vez: `Experiment` nao guarda a pergunta de origem, entao a ligacao
        # lacuna -> experimento e a propria chamada, e nao um campo a casar.
        experimentos = experiments_from([lacuna])
        if not experimentos:
            continue
        saida.append(
            {
                "rules": [regra for regra in par if fala_de(lacuna, regra)],
                "question": lacuna.question,
                "experiment": {
                    "variable": experimentos[0].variable,
                    "evidence_needed": list(getattr(lacuna, "evidence_needed", []) or []),
                },
            }
        )
    return saida
