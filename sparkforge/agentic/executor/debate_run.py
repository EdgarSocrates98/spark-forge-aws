"""O executor de debate: uma maquina de estados PURA sobre arquivos do case.

`sparkforge arbitrate` emite um `DebatePlan` quando a arbitragem nao fecha, e
para em `debate.unresolved`. Este modulo conduz esse plano ate uma `Decision`
sem gerar uma palavra de argumento: quem escreve claim, objecao e replica e o
HOST (subagente, `claude -p`), fora de `sparkforge/` -- a regra 23 do
`CLAUDE.md` vale aqui igual, e nada neste arquivo chama provider nem abre
processo. O que ele faz e o que se faz sem modelo: dizer de quem e a vez,
recusar por nome a submissao que fere o protocolo, gravar a que passa e fechar
pelo `referee`.

Tres verbos:

- `start` recalcula os planos pelo MESMO caminho do `arbitrate`
  (`run.open_debate_plans`), sem gravar a saida dele, e congela o plano do par
  pedido em `.sparkforge/debate/<debate_id>/plan.json`;
- `next_step` le so os arquivos do debate e devolve o brief do lado da vez, ou
  fecha e devolve `done`;
- `submit` valida TUDO antes de gravar QUALQUER coisa. Recusa deixa o estado
  byte a byte igual.

## Estado so em arquivo

Nada vive em memoria entre chamadas. O driver pode morrer entre dois `submit`
e o proximo `next_step` devolve o mesmo brief (SC2): o turno, a rodada, o que
cada lado ja disse e o que falta responder saem de `submissions.jsonl`.
Nenhuma entidade recebe hora -- id content-addressed com relogio dentro deixa
de ser content-addressed.

## Lados sao as regras

O lado A defende `rules[0]` e objeta `rules[1]`; o lado B, o inverso. Ordem A
depois B em cada rodada. Os papeis nascem do dado (Decisao 2 do DESIGN), e o
autor de cada entidade gravada no blackboard e `<debate_id>/<lado>/<rule_id>`:
o id do debate viaja com a claim, e duas rodadas de debates diferentes nunca
colidem num id.

## Fechamento: sempre pelo `referee`, nunca por maioria

O debate fecha quando a ultima rodada completa nao trouxe objecao nova
(consenso) ou quando `max_rounds` -- o teto que o `case.yaml` DECLARA, nunca o
default de `DebateBudget` -- se esgota. O vencedor candidato e a regra do lado
que NAO concedeu, quando exatamente um lado concedeu. Nenhum lado concedeu, ou
os dois concederam: o candidato e `unresolved`. Contagem de claim, de
evidencia ou de rodada nunca escolhe vencedor -- seria julgamento sem garantia.

O candidato passa pelo `referee_over_blackboard` numa COPIA do blackboard com a
decisao candidata dentro, e so entao a decisao final e gravada: o blackboard e
append-only, e gravar o candidato para depois "troca-lo" deixaria no registro
um vencedor que o arbitro recusou. `upheld: false` vira `Decision` `unresolved`
com as violacoes citadas.

O `referee` le o blackboard INTEIRO do case, e isso e deliberado: a `Decision`
gravada fecha o blackboard do case, e o `sparkforge debate referee` rodado
depois precisa dar o mesmo veredito. A consequencia e declarada: objecao sem
replica deixada no case por outra fonte tambem impede um vencedor aqui.

## O que ele NAO faz

- nao aplica mudanca (autonomia L0; `applied_changes` sai sempre `false`);
- nao aceita fact escrito pelo agente -- evidencia nova e reextraida
  (`debate_evidence`);
- nao afirma ganho sobre a arbitragem deterministica (regra 30).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sparkforge.agentic.blackboard import (
    append_claim,
    append_decision,
    append_objection,
    append_rebuttal,
    blackboard_path,
    init_blackboard,
    read_claims,
    read_decisions,
    read_objections,
    read_rebuttals,
)
from sparkforge.agentic.executor import gate
from sparkforge.agentic.executor.debate_evidence import (
    EVIDENCE_EXTRACTORS,
    EvidenceRefused,
    append_evidence_facts,
    extract_evidence,
    read_evidence_facts,
)
from sparkforge.agentic.executor.run import open_debate_plans
from sparkforge.agentic.models import (
    CONFIDENCE_VALUES,
    Claim,
    ClaimType,
    Decision,
    Objection,
    Rebuttal,
)
from sparkforge.agentic.referee import referee_over_blackboard
from sparkforge.case.store import CASE_DIR, load_case

AGENTE = "sparkforge.agentic.executor.debate_run"
NIVEL_DE_AUTONOMIA = "L0"
SCHEMA_VERSION = 1

DEBATE_DIR = "debate"
PLAN_FILE = "plan.json"
SUBMISSIONS_FILE = "submissions.jsonl"
DECISION_FILE = "decision.json"

LADOS = ("A", "B")

# Recusas nomeadas. O host decide o que fazer pelo NOME; `detail` e para humano.
BUDGET_UNDECLARED = "budget_undeclared"
NO_OPEN_DEBATE = "no_open_debate_for_rules"
DEBATE_EXISTS_OTHER_PLAN = "debate_exists_with_other_plan"
INVALID_RULES = "invalid_rules"
DEBATE_NOT_FOUND = "debate_not_found"
INVALID_SCHEMA = "invalid_schema"
OUT_OF_TURN = "out_of_turn"
CLAIM_WITHOUT_EVIDENCE = "claim_without_evidence"
DANGLING_EVIDENCE_REF = "dangling_evidence_ref"
DANGLING_TARGET_REF = "dangling_target_ref"
DUPLICATE_ENTITY = "duplicate_entity"
DEBATE_CLOSED = "debate_closed"
# O Debate ROI Gate (§11): o par existe, mas o veredito nao e `debater`.
GATE_EXPERIMENTAR_ANTES = "gate_experimentar_antes"
GATE_NAO_DEBATER = "gate_nao_debater"
GATE_UNRESOLVED = "gate_unresolved"

# A opcao que a `Decision` escolhe quando o debate nao elege vencedor. Ela e
# OPCAO de verdade -- `Decision` exige `selected_option in options` --, e nao um
# campo a parte, para que "nao decidido" seja uma decisao registrada e auditavel
# e nao a ausencia de registro.
OPCAO_UNRESOLVED = "unresolved: nenhuma das duas acoes e escolhida"

# `dbt_` + 8 hex. Conferido ANTES de virar caminho: o id chega do argv e da
# tool MCP, e sem a checagem `../..` seria um nome de debate valido.
_ID_VALIDO = re.compile(r"^dbt_[0-9a-f]{8}$")

_CHAVES_DA_SUBMISSAO = frozenset(
    {"side", "round", "claims", "objections", "rebuttals", "concede", "evidence_artifacts"}
)
_CHAVES_DA_CLAIM = frozenset(
    {"claim_type", "statement", "evidence_refs", "confidence", "assumptions", "supersedes"}
)
_OBRIGATORIAS_DA_CLAIM = frozenset({"claim_type", "statement", "evidence_refs", "confidence"})
_CHAVES_DA_OBJECAO = frozenset({"target_claim", "statement", "evidence_refs"})
_CHAVES_DA_REPLICA = frozenset({"target_objection", "statement", "evidence_refs"})

# O schema como o brief o publica. Texto e nao JSON Schema formal: quem le e um
# agente, e o validador e `_valida_forma` -- duas fontes da mesma regra seriam
# duas coisas para manter iguais.
ESQUEMA_DA_SUBMISSAO: dict[str, Any] = {
    "side": "'A' ou 'B' -- o lado da vez (obrigatorio)",
    "round": "int -- a rodada da vez (obrigatorio)",
    "claims": (
        "lista de {claim_type: observation|inference|hypothesis|recommendation, "
        "statement, evidence_refs: [fact_id, ...] (nao vazia), confidence: "
        "low|medium|high, assumptions?: [texto], supersedes?: claim_id seu}. "
        "A rodada 1 exige ao menos uma claim"
    ),
    "objections": (
        "lista de {target_claim: claim_id do outro lado, statement, "
        "evidence_refs: [fact_id, ...]}"
    ),
    "rebuttals": (
        "lista de {target_objection: objection_id do outro lado contra claim sua, "
        "statement, evidence_refs: [fact_id, ...]}"
    ),
    "concede": "bool -- true: este lado aceita a regra do outro lado",
    "evidence_artifacts": (
        "lista de {extractor: nome da allowlist, path: relativo a raiz do case}. "
        "Os facts sao REEXTRAIDOS pelo executor e podem ser citados na mesma submissao"
    ),
}

_PROTOCOLO = (
    "O lado A defende rules[0] e objeta rules[1]; o lado B faz o inverso; ordem A, B.",
    "Toda claim cita ao menos um fact_id citavel (uniao congelada ou reextraido).",
    "Objecao sem replica impede fechamento com vencedor (o referee recusa).",
    "Hipotese sobrevivendo ao fechamento impede vencedor (o referee recusa).",
    "Fecha por consenso (rodada completa sem objecao nova) ou por max_rounds.",
    "Vencedor so existe quando exatamente um lado concede; nunca por contagem.",
)


# ==========================================================================
# start
# ==========================================================================


def start(
    case_root: Path | str,
    findings: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    runtime: dict[str, Any] | None,
    rules: tuple[str, str] | list[str],
) -> dict[str, Any]:
    """Congela o plano de debate do par `rules` e devolve o `debate_id`.

    Args:
        case_root: raiz do case -- o estado vai em `<root>/.sparkforge/debate/`.
        findings: os mesmos findings que `arbitrate` recebeu.
        facts: a UNIAO dos facts do case, com `id` (o mesmo conjunto do
            `arbitrate`; subconjunto fabricaria claim desancorada).
        runtime: o runtime efetivo, como `arbitrate` o calcula.
        rules: `(A, B)`. O lado A defende `rules[0]`.

    Returns:
        `{"status": "started", "debate_id", "created", ...}` ou
        `{"status": "refused", "reason", "detail"}`. Recusa nao grava nada.

    Idempotente: o mesmo plano da o mesmo id, e o segundo `start` devolve
    `created: false` sem reescrever. Outro plano para o mesmo par e recusado --
    dois debates do mesmo par dariam duas decisoes para uma contradicao.
    """
    par = _par_pedido(rules)
    if par is None:
        return _recusa(INVALID_RULES, "informe exatamente duas regras distintas, `A,B`")

    budget = _budget_do_case(case_root)
    planos = open_debate_plans(findings, facts, runtime, budget)
    entrada = next((p for p in planos if set(p.get("rules") or []) == set(par)), None)
    if entrada is None:
        return _recusa(
            NO_OPEN_DEBATE,
            f"a arbitragem deste case nao deixa debate aberto para {par[0]} x {par[1]}: "
            f"ou o par nao se contradiz diretamente, ou a arbitragem ja fechou",
        )

    # O gate vem ANTES do budget: par que nao sera debatido nao precisa de teto.
    recusa_do_gate = _recusa_do_gate(entrada, par, findings)
    if recusa_do_gate is not None:
        return recusa_do_gate

    plano = entrada["plan"]
    if (plano.get("budget") or {}).get("status") != "declared":
        return _recusa(BUDGET_UNDECLARED, str((plano.get("budget") or {}).get("reason")))
    rodadas = plano.get("rounds") or {}
    if rodadas.get("status") != "declared":
        return _recusa(BUDGET_UNDECLARED, str(rodadas.get("reason")))

    documento = _plano_congelado(par, entrada, int(rodadas["max_rounds"]), findings, facts, runtime)
    debate_id = "dbt_" + _sha1(_canonico(documento))[:8]

    existente = _debate_do_par(case_root, par)
    if existente is not None and existente != debate_id:
        return _recusa(
            DEBATE_EXISTS_OTHER_PLAN,
            f"o par {par[0]} x {par[1]} ja tem o debate {existente}, congelado com outro "
            f"plano (outros facts, outro budget ou outra ordem de lados)",
        )

    criado = existente is None
    if criado:
        destino = _dir_do_debate(case_root, debate_id)
        destino.mkdir(parents=True, exist_ok=True)
        _escreve_json(destino / PLAN_FILE, {**documento, "debate_id": debate_id})

    return {
        "status": "started",
        "debate_id": debate_id,
        "created": criado,
        "rules": list(par),
        "max_rounds": documento["max_rounds"],
        "state_dir": f"{CASE_DIR}/{DEBATE_DIR}/{debate_id}",
    }


def _par_pedido(rules: Any) -> tuple[str, str] | None:
    """`(A, B)` limpos, ou `None` quando nao sao duas regras distintas."""
    if not isinstance(rules, (list, tuple)) or len(rules) != 2:
        return None
    a, b = (str(r or "").strip() for r in rules)
    if not a or not b or a == b:
        return None
    return a, b


def _budget_do_case(case_root: Path | str) -> dict[str, Any] | None:
    """O bloco `budget:` do `case.yaml`, ou `None` -- nunca o default do codigo.

    Mesma leitura de `adapters._core._budget_declarado`: case ausente ou
    ilegivel e "sem budget", e o plano sai `unresolved` nomeando a lacuna, que
    vira `budget_undeclared` aqui.
    """
    try:
        case = load_case(case_root)
    except Exception:
        return None
    bloco = case.get("budget")
    return bloco if isinstance(bloco, dict) else None


def _plano_congelado(
    par: tuple[str, str],
    entrada: dict[str, Any],
    max_rodadas: int,
    findings: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    runtime: dict[str, Any] | None,
) -> dict[str, Any]:
    """O documento que `plan.json` guarda, sem o id (o id e o hash dele).

    `rule_context` sai dos FINDINGS e nao das claims do executor: as claims so
    existem no blackboard se `arbitrate` rodou, e o brief precisa do titulo, da
    acao e das ancoras de cada regra de qualquer jeito.
    """
    a, b = par
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "debate.frozen_plan",
        "rules": [a, b],
        "sides": {
            "A": {"defends": a, "objects": b},
            "B": {"defends": b, "objects": a},
        },
        "max_rounds": max_rodadas,
        "arbitration": {
            "recommendation": entrada.get("recommendation"),
            "reason": entrada.get("reason"),
        },
        "plan": entrada["plan"],
        "rule_context": {regra: _contexto_da_regra(regra, findings) for regra in par},
        "union_fact_ids": sorted(
            {
                str(f.get("id"))
                for f in facts or []
                if isinstance(f, dict) and f.get("id")
            }
        ),
        "runtime": dict(runtime or {}),
    }


def _contexto_da_regra(regra: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Titulo, acao, ancoras e validacao que os findings da regra declaram."""
    titulos: list[str] = []
    ancoras: list[str] = []
    validacao: list[str] = []
    acao: dict[str, Any] = {}
    for finding in findings or []:
        if not isinstance(finding, dict) or str(finding.get("rule_id") or "").strip() != regra:
            continue
        titulo = str(finding.get("title") or "").strip()
        if titulo and titulo not in titulos:
            titulos.append(titulo)
        for bruto in finding.get("evidence") or []:
            fact_id = str(bruto).strip()
            if fact_id and fact_id not in ancoras:
                ancoras.append(fact_id)
        for bruto in finding.get("validation") or []:
            item = str(bruto).strip()
            if item and item not in validacao:
                validacao.append(item)
        if not acao and isinstance(finding.get("action"), dict):
            acao = {
                chave: finding["action"].get(chave)
                for chave in ("kind", "target", "direction")
            }
    return {
        "titles": titulos,
        "action": acao,
        "anchor_fact_ids": ancoras,
        "validation": validacao,
    }


def _recusa_do_gate(
    entrada: dict[str, Any], par: tuple[str, str], findings: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """A recusa nomeada quando o Debate ROI Gate nao diz `debater`, ou `None`.

    Entrada sem `debate_gate` e tratada como `unresolved`: abrir debate sem o
    veredito seria pular o gate calado.
    """
    bloco = entrada.get("debate_gate")
    if not isinstance(bloco, dict):
        return _recusa(
            GATE_UNRESOLVED,
            "o plano do par nao traz `debate_gate`: recalcule pelo `arbitrate` desta versao",
        )
    veredito = bloco.get("verdict")
    if veredito == gate.DEBATER:
        return None
    if veredito == gate.EXPERIMENTAR_ANTES:
        medidas = "; ".join(
            f"{lacuna.get('question')} -> medir {lacuna.get('experiment', {}).get('variable')}"
            for lacuna in bloco.get("signals", {}).get("evidence_gap") or []
        )
        return _recusa(
            GATE_EXPERIMENTAR_ANTES,
            f"o par {par[0]} x {par[1]} tem lacuna mensuravel, e debate nao cria medida: "
            f"{medidas}",
        )
    if veredito == gate.NAO_DEBATER:
        acoes = "; ".join(_acao_com_rollback(regra, findings) for regra in par)
        return _recusa(
            GATE_NAO_DEBATER,
            f"o par {par[0]} x {par[1]} e de severidade abaixo de "
            f"{bloco.get('policy', {}).get('debate_severities')} e as duas acoes sao "
            f"reversiveis: decisao humana direta entre elas. {acoes}",
        )
    faltando = ", ".join(bloco.get("missing") or []) or "sinal desconhecido"
    motivo_da_politica = bloco.get("policy", {}).get("reason")
    return _recusa(
        GATE_UNRESOLVED,
        f"o gate nao decide sem: {faltando}"
        + (f" ({motivo_da_politica})" if motivo_da_politica else ""),
    )


def _acao_com_rollback(regra: str, findings: list[dict[str, Any]]) -> str:
    """`regra: kind (direction); rollback: ...`, lido dos findings da regra."""
    contexto = _contexto_da_regra(regra, findings)
    acao = contexto["action"]
    rollback: list[str] = []
    for finding in findings or []:
        if isinstance(finding, dict) and str(finding.get("rule_id") or "").strip() == regra:
            for bruto in finding.get("rollback") or []:
                item = str(bruto).strip()
                if item and item not in rollback:
                    rollback.append(item)
    return (
        f"{regra}: {acao.get('kind')} ({acao.get('direction')}); rollback: "
        f"{' | '.join(rollback) or 'nao declarado'}"
    )


def _debate_do_par(case_root: Path | str, par: tuple[str, str]) -> str | None:
    """O debate ja congelado para este par (em qualquer ordem), ou `None`.

    `os.scandir` e nao `glob`: `tests/test_facts_scan.py` proibe varredura crua
    em `sparkforge/`, e aqui a arvore e um nivel so, de nomes que este modulo
    mesmo escreveu.
    """
    base = Path(case_root) / CASE_DIR / DEBATE_DIR
    if not base.is_dir():
        return None
    with os.scandir(base) as entradas:
        nomes = sorted(e.name for e in entradas if e.is_dir() and _ID_VALIDO.match(e.name))
    for nome in nomes:
        arquivo = base / nome / PLAN_FILE
        if not arquivo.is_file():
            continue
        documento = json.loads(arquivo.read_text(encoding="utf-8"))
        if set(documento.get("rules") or []) == set(par):
            return nome
    return None


# ==========================================================================
# next_step
# ==========================================================================


def next_step(case_root: Path | str, debate_id: str) -> dict[str, Any]:
    """O proximo passo do debate, derivado SO dos arquivos.

    Devolve o brief do lado da vez (`status: brief`) ou fecha e devolve
    `status: done`. Depois do fechamento devolve sempre o mesmo `done`, lido de
    `decision.json`.
    """
    estado = _carrega(case_root, debate_id)
    if estado is None:
        return _recusa(DEBATE_NOT_FOUND, f"nenhum debate `{debate_id}` neste case")
    if estado["done"] is not None:
        return estado["done"]
    fechamento = _fechamento_devido(estado)
    if fechamento is not None:
        return _fechar(case_root, estado, fechamento)
    return {"status": "brief", "debate_id": debate_id, "brief": _brief(estado)}


def _carrega(case_root: Path | str, debate_id: str) -> dict[str, Any] | None:
    """Todo o estado do debate, relido do disco a cada chamada."""
    if not isinstance(debate_id, str) or not _ID_VALIDO.match(debate_id):
        return None
    diretorio = _dir_do_debate(case_root, debate_id)
    arquivo = diretorio / PLAN_FILE
    if not arquivo.is_file():
        return None
    plano = json.loads(arquivo.read_text(encoding="utf-8"))
    submissoes = _le_jsonl(diretorio / SUBMISSIONS_FILE)
    decisao = diretorio / DECISION_FILE
    return {
        "debate_id": debate_id,
        "dir": diretorio,
        "plan": plano,
        "submissions": submissoes,
        "evidence": read_evidence_facts(diretorio),
        "done": json.loads(decisao.read_text(encoding="utf-8")) if decisao.is_file() else None,
    }


def _vez(estado: dict[str, Any]) -> tuple[str, int]:
    """`(lado, rodada)` da proxima submissao. A antes de B em toda rodada."""
    n = len(estado["submissions"])
    return LADOS[n % 2], n // 2 + 1


def _fechamento_devido(estado: dict[str, Any]) -> str | None:
    """`consensus`, `budget` ou `None`. So avaliado ao fim de rodada completa.

    Consenso e a ultima rodada completa sem objecao NOVA de nenhum lado. Uma
    rodada inteira de silencio tambem conta: nenhum lado achou o que objetar,
    e prolongar o debate ate o teto so gastaria rodada.
    """
    submissoes = estado["submissions"]
    n = len(submissoes)
    if n == 0 or n % 2:
        return None
    ultima_rodada = submissoes[-2:]
    if not any(s["entities"]["objections"] for s in ultima_rodada):
        return "consensus"
    if n // 2 >= int(estado["plan"]["max_rounds"]):
        return "budget"
    return None


def _brief(estado: dict[str, Any]) -> dict[str, Any]:
    """O que o lado da vez precisa para escrever a submissao.

    As submissoes anteriores vem rotuladas `untrusted_content: true`: sao texto
    de agente, e um brief que as repassasse sem rotulo convidaria o proximo
    agente a trata-las como instrucao.
    """
    plano = estado["plan"]
    lado, rodada = _vez(estado)
    outro = LADOS[1 - LADOS.index(lado)]
    defende = plano["sides"][lado]["defends"]
    objeta = plano["sides"][lado]["objects"]
    indice = _indice(estado)
    maximo = int(plano["max_rounds"])

    return {
        "side": lado,
        "round": rodada,
        "max_rounds": maximo,
        "rounds_remaining": maximo - rodada + 1,
        "defends": {"rule_id": defende, **plano["rule_context"][defende]},
        "opposes": {"rule_id": objeta, **plano["rule_context"][objeta]},
        "arbitration": plano["arbitration"],
        "citable_fact_ids": sorted(_citaveis(estado)),
        "extracted_facts": [
            {
                "id": r["fact"]["id"],
                "kind": r["fact"].get("kind"),
                "extractor": r["extractor"],
                "path": r["path"],
            }
            for r in estado["evidence"]
        ],
        "your_claims": indice["claims_por_lado"][lado],
        "opponent_claims": indice["claims_por_lado"][outro],
        "open_objections_against_you": [
            o for o in indice["objecoes_contra"][lado] if o not in indice["respondidas"]
        ],
        "conceded": {s: s in indice["concederam"] for s in LADOS},
        "prior_submissions": [
            {
                "untrusted_content": True,
                "seq": s["seq"],
                "side": s["side"],
                "round": s["round"],
                "concede": s["concede"],
                "claims": s["entities"]["claims"],
                "objections": s["entities"]["objections"],
                "rebuttals": s["entities"]["rebuttals"],
                "facts_added": s["facts_added"],
            }
            for s in estado["submissions"]
        ],
        "submission_schema": ESQUEMA_DA_SUBMISSAO,
        "evidence_extractors": sorted(EVIDENCE_EXTRACTORS),
        "protocol": list(_PROTOCOLO),
    }


def _indice(estado: dict[str, Any]) -> dict[str, Any]:
    """Quem disse o que, achatado sobre as submissoes aceitas."""
    claims_por_lado: dict[str, list[str]] = {lado: [] for lado in LADOS}
    objecoes: dict[str, dict[str, Any]] = {}
    objecoes_contra: dict[str, list[str]] = {lado: [] for lado in LADOS}
    respondidas: set[str] = set()
    concederam: set[str] = set()
    dono_da_claim: dict[str, str] = {}
    for sub in estado["submissions"]:
        lado = sub["side"]
        for claim in sub["entities"]["claims"]:
            claims_por_lado[lado].append(claim["id"])
            dono_da_claim[claim["id"]] = lado
        for objecao in sub["entities"]["objections"]:
            objecoes[objecao["id"]] = {**objecao, "side": lado}
        for replica in sub["entities"]["rebuttals"]:
            respondidas.add(replica["target_objection"])
        if sub["concede"]:
            concederam.add(lado)
    for objecao_id, objecao in objecoes.items():
        alvo = dono_da_claim.get(objecao["target_claim"])
        if alvo is not None:
            objecoes_contra[alvo].append(objecao_id)
    return {
        "claims_por_lado": claims_por_lado,
        "dono_da_claim": dono_da_claim,
        "objecoes": objecoes,
        "objecoes_contra": objecoes_contra,
        "respondidas": respondidas,
        "concederam": concederam,
    }


def _citaveis(estado: dict[str, Any]) -> set[str]:
    """Os `fact_id` que uma submissao pode citar: uniao congelada + reextraidos."""
    return set(estado["plan"]["union_fact_ids"]) | {
        str(r["fact"]["id"]) for r in estado["evidence"]
    }


# ==========================================================================
# submit
# ==========================================================================


def submit(case_root: Path | str, debate_id: str, payload: Any) -> dict[str, Any]:
    """Valida a submissao inteira e so entao grava. Recusa nao muda nada.

    A ordem das checagens e a do contrato: fechado, forma, vez, claim sem
    evidencia, reextracao, referencia de fact, referencia de alvo, duplicata. A
    reextracao roda ANTES da checagem de referencia porque um fact reextraido
    nesta submissao pode ser citado nela mesma.
    """
    estado = _carrega(case_root, debate_id)
    if estado is None:
        return _recusa(DEBATE_NOT_FOUND, f"nenhum debate `{debate_id}` neste case")
    if estado["done"] is not None or _fechamento_devido(estado) is not None:
        return _recusa(DEBATE_CLOSED, "o debate ja fechou; `next` devolve a decisao")

    try:
        normal = _valida_forma(payload)
    except _Recusa as exc:
        return _recusa(exc.reason, exc.detail)

    lado, rodada = _vez(estado)
    if normal["side"] != lado or normal["round"] != rodada:
        return _recusa(
            OUT_OF_TURN,
            f"a vez e do lado {lado} na rodada {rodada}; chegou lado "
            f"{normal['side']} rodada {normal['round']}",
        )
    if rodada == 1 and not normal["claims"]:
        return _recusa(INVALID_SCHEMA, "a rodada 1 abre com ao menos uma claim do lado")

    for i, claim in enumerate(normal["claims"]):
        if not claim["evidence_refs"]:
            return _recusa(
                CLAIM_WITHOUT_EVIDENCE, f"claims[{i}] sem `evidence_refs`: claim ancora em fact"
            )

    try:
        registros = extract_evidence(case_root, normal["evidence_artifacts"])
    except EvidenceRefused as exc:
        return _recusa(exc.reason, exc.detail)

    citaveis = _citaveis(estado) | {str(r["fact"]["id"]) for r in registros}
    for secao in ("claims", "objections", "rebuttals"):
        for i, item in enumerate(normal[secao]):
            soltos = [ref for ref in item["evidence_refs"] if ref not in citaveis]
            if soltos:
                return _recusa(
                    DANGLING_EVIDENCE_REF,
                    f"{secao}[{i}] cita {soltos}, fora da uniao congelada e dos facts "
                    f"reextraidos neste debate",
                )

    autor = _autor(estado, lado)
    try:
        entidades = _entidades(estado, normal, lado, autor)
    except _Recusa as exc:
        return _recusa(exc.reason, exc.detail)

    return _grava_submissao(case_root, estado, normal, lado, rodada, entidades, registros)


class _Recusa(Exception):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _valida_forma(payload: Any) -> dict[str, Any]:
    """A submissao normalizada, ou `_Recusa(invalid_schema)`.

    Chave desconhecida e recusada, e nao ignorada: um campo que o executor nao
    le e um campo que o agente acha que foi considerado.
    """
    if not isinstance(payload, dict):
        raise _Recusa(INVALID_SCHEMA, "a submissao deve ser um objeto JSON")
    sobrando = sorted(set(payload) - _CHAVES_DA_SUBMISSAO)
    if sobrando:
        raise _Recusa(INVALID_SCHEMA, f"chaves desconhecidas: {sobrando}")
    lado = payload.get("side")
    if lado not in LADOS:
        raise _Recusa(INVALID_SCHEMA, "`side` deve ser 'A' ou 'B'")
    rodada = payload.get("round")
    if not isinstance(rodada, int) or isinstance(rodada, bool) or rodada < 1:
        raise _Recusa(INVALID_SCHEMA, "`round` deve ser int >= 1")
    concede = payload.get("concede", False)
    if not isinstance(concede, bool):
        raise _Recusa(INVALID_SCHEMA, "`concede` deve ser bool")
    artefatos = payload.get("evidence_artifacts", [])
    if not isinstance(artefatos, list):
        raise _Recusa(INVALID_SCHEMA, "`evidence_artifacts` deve ser lista")

    return {
        "side": lado,
        "round": rodada,
        "concede": concede,
        "claims": [
            _item(bruto, f"claims[{i}]", _CHAVES_DA_CLAIM, _OBRIGATORIAS_DA_CLAIM)
            for i, bruto in enumerate(_lista(payload, "claims"))
        ],
        "objections": [
            _item(bruto, f"objections[{i}]", _CHAVES_DA_OBJECAO, _CHAVES_DA_OBJECAO)
            for i, bruto in enumerate(_lista(payload, "objections"))
        ],
        "rebuttals": [
            _item(bruto, f"rebuttals[{i}]", _CHAVES_DA_REPLICA, _CHAVES_DA_REPLICA)
            for i, bruto in enumerate(_lista(payload, "rebuttals"))
        ],
        "evidence_artifacts": artefatos,
    }


def _lista(payload: dict[str, Any], chave: str) -> list[Any]:
    valor = payload.get(chave, [])
    if not isinstance(valor, list):
        raise _Recusa(INVALID_SCHEMA, f"`{chave}` deve ser lista")
    return valor


def _item(
    bruto: Any, onde: str, permitidas: frozenset[str], obrigatorias: frozenset[str]
) -> dict[str, Any]:
    """Um item de claim, objecao ou replica, com os tipos conferidos."""
    if not isinstance(bruto, dict):
        raise _Recusa(INVALID_SCHEMA, f"{onde} deve ser objeto")
    sobrando = sorted(set(bruto) - permitidas)
    faltando = sorted(obrigatorias - set(bruto))
    if sobrando or faltando:
        raise _Recusa(
            INVALID_SCHEMA, f"{onde}: chaves desconhecidas {sobrando}, faltando {faltando}"
        )
    item = dict(bruto)
    for chave in ("statement", "target_claim", "target_objection"):
        if chave in item and (not isinstance(item[chave], str) or not item[chave].strip()):
            raise _Recusa(INVALID_SCHEMA, f"{onde}.{chave} deve ser texto nao vazio")
    for chave in ("evidence_refs", "assumptions"):
        if chave in item and (
            not isinstance(item[chave], list) or not all(isinstance(r, str) for r in item[chave])
        ):
            raise _Recusa(INVALID_SCHEMA, f"{onde}.{chave} deve ser lista de texto")
    if "claim_type" in item and item["claim_type"] not in {t.value for t in ClaimType}:
        raise _Recusa(INVALID_SCHEMA, f"{onde}.claim_type invalido: {item['claim_type']!r}")
    if "confidence" in item and item["confidence"] not in CONFIDENCE_VALUES:
        raise _Recusa(INVALID_SCHEMA, f"{onde}.confidence invalida: {item['confidence']!r}")
    if item.get("supersedes") is not None and (
        not isinstance(item["supersedes"], str) or not item["supersedes"].strip()
    ):
        raise _Recusa(INVALID_SCHEMA, f"{onde}.supersedes deve ser claim_id ou null")
    return item


def _autor(estado: dict[str, Any], lado: str) -> str:
    """`<debate_id>/<lado>/<rule_id>` -- o id do debate viaja em toda entidade."""
    return f"{estado['debate_id']}/{lado}/{estado['plan']['sides'][lado]['defends']}"


def _entidades(
    estado: dict[str, Any], normal: dict[str, Any], lado: str, autor: str
) -> dict[str, list[Any]]:
    """Constroi `Claim`/`Objection`/`Rebuttal` e confere cada alvo.

    Objecao so mira claim do OUTRO lado; replica so responde objecao do outro
    lado contra claim DESTE; `supersedes` so revisa claim deste lado. Alvo fora
    disso e referencia pendurada -- o `referee` a recusaria no fechamento, e
    recusar aqui poupa uma rodada gasta num debate que ja nasceu quebrado.
    """
    indice = _indice(estado)
    outro = LADOS[1 - LADOS.index(lado)]
    minhas = set(indice["claims_por_lado"][lado])
    dele = set(indice["claims_por_lado"][outro])
    objecoes_contra_mim = set(indice["objecoes_contra"][lado])
    ja_no_debate = (
        set(indice["dono_da_claim"])
        | set(indice["objecoes"])
        | {
            r["id"]
            for s in estado["submissions"]
            for r in s["entities"]["rebuttals"]
        }
    )

    claims: list[Claim] = []
    for i, item in enumerate(normal["claims"]):
        anterior = item.get("supersedes")
        if anterior is not None and anterior not in minhas:
            raise _Recusa(
                DANGLING_TARGET_REF, f"claims[{i}].supersedes `{anterior}` nao e claim sua"
            )
        claims.append(
            Claim(
                claimant=autor,
                claim_type=ClaimType(item["claim_type"]),
                statement=item["statement"],
                evidence_refs=list(item["evidence_refs"]),
                assumptions=list(item.get("assumptions") or []),
                confidence=item["confidence"],
                supersedes=anterior,
            )
        )
    objecoes: list[Objection] = []
    for i, item in enumerate(normal["objections"]):
        if item["target_claim"] not in dele:
            raise _Recusa(
                DANGLING_TARGET_REF,
                f"objections[{i}].target_claim `{item['target_claim']}` nao e claim do lado "
                f"{outro} neste debate",
            )
        objecoes.append(
            Objection(
                target_claim=item["target_claim"],
                objector=autor,
                statement=item["statement"],
                evidence_refs=list(item["evidence_refs"]),
            )
        )
    replicas: list[Rebuttal] = []
    for i, item in enumerate(normal["rebuttals"]):
        if item["target_objection"] not in objecoes_contra_mim:
            raise _Recusa(
                DANGLING_TARGET_REF,
                f"rebuttals[{i}].target_objection `{item['target_objection']}` nao e objecao "
                f"do lado {outro} contra claim sua",
            )
        replicas.append(
            Rebuttal(
                target_objection=item["target_objection"],
                rebuttal_by=autor,
                statement=item["statement"],
                evidence_refs=list(item["evidence_refs"]),
            )
        )

    ids = [e.id for e in (*claims, *objecoes, *replicas)]
    repetidos = sorted({i for i in ids if ids.count(i) > 1 or i in ja_no_debate})
    if repetidos:
        raise _Recusa(
            DUPLICATE_ENTITY,
            f"{repetidos} ja existem neste debate (ou se repetem na submissao): o id e "
            f"content-addressed, e a mesma afirmacao duas vezes e UMA",
        )
    return {"claims": claims, "objections": objecoes, "rebuttals": replicas}


def _grava_submissao(
    case_root: Path | str,
    estado: dict[str, Any],
    normal: dict[str, Any],
    lado: str,
    rodada: int,
    entidades: dict[str, list[Any]],
    registros: list[dict[str, Any]],
) -> dict[str, Any]:
    """Grava facts, entidades e, POR ULTIMO, a submissao.

    `submissions.jsonl` e o registro de commit: e ele que move o turno. Um
    processo morto antes dele deixa facts e entidades gravados sem mover a vez,
    e a mesma submissao reenviada e aceita -- a gravacao pula o id que ja esta
    no blackboard em vez de levantar duplicata.
    """
    adicionados = append_evidence_facts(estado["dir"], registros, _citaveis(estado))

    init_blackboard(case_root)
    existentes = {
        "claims": {str(r.get("id")) for r in read_claims(case_root)},
        "objections": {str(r.get("id")) for r in read_objections(case_root)},
        "rebuttals": {str(r.get("id")) for r in read_rebuttals(case_root)},
    }
    gravadores = {
        "claims": append_claim,
        "objections": append_objection,
        "rebuttals": append_rebuttal,
    }
    for secao, gravar in gravadores.items():
        for entidade in entidades[secao]:
            if entidade.id not in existentes[secao]:
                gravar(entidade, case_root)

    registro = {
        "seq": len(estado["submissions"]) + 1,
        "side": lado,
        "round": rodada,
        "concede": normal["concede"],
        "entities": {secao: [e.to_dict() for e in entidades[secao]] for secao in gravadores},
        "facts_added": adicionados,
        "evidence_artifacts": normal["evidence_artifacts"],
    }
    _anexa_jsonl(estado["dir"] / SUBMISSIONS_FILE, registro)

    return {
        "status": "accepted",
        "debate_id": estado["debate_id"],
        "seq": registro["seq"],
        "entities": {secao: [e.id for e in entidades[secao]] for secao in gravadores},
        "facts_added": adicionados,
        "next": next_step(case_root, estado["debate_id"]),
    }


# ==========================================================================
# Fechamento
# ==========================================================================


def _fechar(case_root: Path | str, estado: dict[str, Any], motivo: str) -> dict[str, Any]:
    """Decide o candidato, passa pelo `referee` numa copia e grava a final."""
    plano = estado["plan"]
    indice = _indice(estado)
    concederam = indice["concederam"]

    if len(concederam) == 1:
        perdedor = next(iter(concederam))
        vencedor = LADOS[1 - LADOS.index(perdedor)]
        regra_vencedora: str | None = plano["sides"][vencedor]["defends"]
        motivo_do_candidato = f"o lado {perdedor} concedeu; o lado {vencedor} nao"
    else:
        vencedor = None
        regra_vencedora = None
        motivo_do_candidato = (
            "os dois lados concederam: nao ha regra de pe"
            if concederam
            else "nenhum lado concedeu"
        )

    candidata = _decisao(estado, indice, vencedor, [motivo_do_candidato])
    veredito = _referee_com(case_root, candidata)

    if vencedor is not None and not veredito["upheld"]:
        motivos = [
            f"o referee recusou o fechamento com vencedor {regra_vencedora}",
            *(f"referee: {v['kind']}: {v['what']}" for v in veredito["violations"]),
        ]
        final = _decisao(estado, indice, None, motivos)
    elif vencedor is None:
        final = _decisao(
            estado,
            indice,
            None,
            [
                motivo_do_candidato,
                *(f"referee: {v['kind']}: {v['what']}" for v in veredito["violations"]),
            ],
        )
    else:
        final = candidata

    init_blackboard(case_root)
    if final.id not in {str(r.get("id")) for r in read_decisions(case_root)}:
        append_decision(final, case_root)

    ganhou = final.selected_option != OPCAO_UNRESOLVED
    done = {
        "status": "done",
        "debate_id": estado["debate_id"],
        "outcome": "winner" if ganhou else "unresolved",
        "winner_rule": regra_vencedora if ganhou else None,
        "closed_by": motivo,
        "rounds_completed": len(estado["submissions"]) // 2,
        "max_rounds": int(plano["max_rounds"]),
        "candidate": {
            "outcome": "winner" if vencedor is not None else "unresolved",
            "winner_rule": regra_vencedora,
            "reason": motivo_do_candidato,
        },
        "referee": {
            "upheld": veredito["upheld"],
            "violation_count": veredito["violation_count"],
            "violations": veredito["violations"],
        },
        "decision": final.to_dict(),
        "autonomy": {"level": NIVEL_DE_AUTONOMIA, "applied_changes": False},
    }
    _escreve_json(estado["dir"] / DECISION_FILE, done)
    # Devolve o que foi GRAVADO, relido: o primeiro `done` e os seguintes saem do
    # mesmo arquivo, e nao ha como um divergir do outro por serializacao.
    return json.loads((estado["dir"] / DECISION_FILE).read_text(encoding="utf-8"))


def _referee_com(case_root: Path | str, candidata: Decision) -> dict[str, Any]:
    """O veredito do `referee_over_blackboard` sobre o blackboard + a candidata.

    Numa copia temporaria, e nao no blackboard do case: gravar a candidata para
    depois troca-la deixaria um vencedor recusado no registro append-only. So
    os quatro arquivos que o `referee` le sao copiados.
    """
    origem = blackboard_path(case_root)
    with tempfile.TemporaryDirectory(prefix="sf_debate_referee_") as tmp:
        destino = init_blackboard(tmp)
        for nome in ("claims.jsonl", "objections.jsonl", "rebuttals.jsonl", "decisions.jsonl"):
            if (origem / nome).is_file():
                shutil.copyfile(origem / nome, destino / nome)
        if candidata.id not in {str(r.get("id")) for r in read_decisions(tmp)}:
            append_decision(candidata, tmp)
        return referee_over_blackboard(tmp)


def _decisao(
    estado: dict[str, Any],
    indice: dict[str, Any],
    vencedor: str | None,
    motivos: list[str],
) -> Decision:
    """A `Decision` do debate: vencedor ou `unresolved`, com `rollback` sempre.

    `confidence` sai no maximo `medium` pela mesma tabela que `run.py` aplica:
    `high` exige "nenhuma contradicao aberta", e o debate existe porque havia
    uma.
    """
    plano = estado["plan"]
    a, b = plano["rules"]
    alvo = str((plano["rule_context"][a].get("action") or {}).get("target") or "")
    opcoes = [_opcao(a, plano), _opcao(b, plano), OPCAO_UNRESOLVED]
    problema = (
        f"debate {estado['debate_id']}: contradicao direta em `{alvo}` entre {a} e {b}"
    )
    comum: dict[str, Any] = {
        "problem": problema,
        "options": opcoes,
        "debate_id": estado["debate_id"],
        "runtime": dict(plano.get("runtime") or {}),
        "decided_by": AGENTE,
    }

    if vencedor is None:
        return Decision(
            **comum,
            selected_option=OPCAO_UNRESOLVED,
            rejected_options=opcoes[:2],
            risks=list(motivos),
            confidence="low",
            validation=(
                "unresolved -- nenhuma das duas acoes foi escolhida, entao nao ha "
                "resultado a validar"
            ),
            rollback=(
                "nada a desfazer: nenhuma acao foi escolhida nem aplicada (autonomia "
                f"{NIVEL_DE_AUTONOMIA}); a contradicao continua aberta"
            ),
            falsification_condition=(
                "um debate novo sobre o par, com evidencia que leve exatamente um lado "
                "a conceder e o referee a aceitar o fechamento"
            ),
        )

    perdedor = LADOS[1 - LADOS.index(vencedor)]
    regra = plano["sides"][vencedor]["defends"]
    regra_perdedora = plano["sides"][perdedor]["defends"]
    sobreviventes = _claims_sobreviventes(estado, vencedor)
    refs: list[str] = []
    for claim in sobreviventes:
        for ref in [claim["id"], *claim["evidence_refs"]]:
            if ref not in refs:
                refs.append(ref)
    forca = {c["confidence"] for c in sobreviventes}
    validacao = plano["rule_context"][regra].get("validation") or []
    return Decision(
        **comum,
        selected_option=_opcao(regra, plano),
        rejected_options=[_opcao(regra_perdedora, plano), OPCAO_UNRESOLVED],
        evidence_refs=refs,
        risks=[
            f"o achado de {regra_perdedora} continua aberto: a acao dele nao e aplicada, "
            f"e a razao e a incompatibilidade com {regra}"
        ],
        assumptions=[*motivos, f"o lado {perdedor} ({regra_perdedora}) concedeu neste debate"],
        confidence="medium" if forca & {"high", "medium"} else "low",
        validation=(
            "; ".join(validacao)
            if validacao
            else f"unresolved -- {regra} nao declara `validation` no catalogo"
        ),
        rollback=(
            f"desfazer a acao de {regra} sobre `{alvo}`, restaurando o valor anterior do "
            f"alvo. Nada foi aplicado por este verbo: a autonomia e {NIVEL_DE_AUTONOMIA} e "
            f"a decisao e proposta"
        ),
        falsification_condition=(
            f"um fact novo contradiz o que o lado {perdedor} concedeu, ou a medida que "
            f"ancora {regra} deixa de valer no runtime do case"
        ),
    )


def _claims_sobreviventes(estado: dict[str, Any], lado: str) -> list[dict[str, Any]]:
    """As claims do lado que nenhuma outra claim dele substituiu."""
    claims = [
        c
        for s in estado["submissions"]
        if s["side"] == lado
        for c in s["entities"]["claims"]
    ]
    substituidas = {c.get("supersedes") for c in claims if c.get("supersedes")}
    return [c for c in claims if c["id"] not in substituidas]


def _opcao(regra: str, plano: dict[str, Any]) -> str:
    """A opcao como texto, no formato de `run._opcao`, a partir do plano congelado."""
    acao = plano["rule_context"][regra].get("action") or {}
    kind = str(acao.get("kind") or "").strip() or "acao nao declarada"
    alvo = str(acao.get("target") or "").strip() or "alvo nao declarado"
    direcao = str(acao.get("direction") or "").strip() or "direcao nao declarada"
    return f"{regra}: {kind} ({direcao}) em {alvo}"


# ==========================================================================
# Arquivos
# ==========================================================================


def _dir_do_debate(case_root: Path | str, debate_id: str) -> Path:
    return Path(case_root) / CASE_DIR / DEBATE_DIR / debate_id


def _canonico(valor: Any) -> str:
    return json.dumps(valor, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha1(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8"), usedforsecurity=False).hexdigest()


def _escreve_json(caminho: Path, valor: Any) -> None:
    caminho.write_text(
        json.dumps(valor, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def _anexa_jsonl(caminho: Path, registro: dict[str, Any]) -> None:
    with caminho.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=True, sort_keys=True) + "\n")


def _le_jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.is_file():
        return []
    with caminho.open("r", encoding="utf-8") as fh:
        return [json.loads(linha) for linha in fh if linha.strip()]


def _recusa(reason: str, detail: str) -> dict[str, Any]:
    return {"status": "refused", "reason": reason, "detail": detail}
