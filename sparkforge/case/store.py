"""Leitura e escrita de `.sparkforge/case.yaml` — o barramento de handoff.

O case file é o que atravessa a fronteira entre uma sessão Devin e uma sessão
Claude Code: são processos diferentes, sem contexto conversacional compartilhado.
O que sobrevive é um commit, e o case file é o estado desse commit.

Timestamp nunca é gerado aqui. Todo `created_at`/`at` chega como parâmetro,
injetado por quem chama (o adapter de CLI, tipicamente `datetime.now(UTC)`).
Isto mantém o módulo puro e reprodutível, e impede um LLM de inventar hora.
"""
from __future__ import annotations

import copy
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1
CASE_DIR = ".sparkforge"
CASE_FILE = "case.yaml"

PHASES = (
    "intake",
    "inventory",
    "facts",
    "diagnosis",
    "hypothesis",
    "experiment",
    "validation",
    "report",
)

GATES = (
    "baseline_captured",
    "dominant_bottleneck_identified",
    "functional_validation_defined",
    "flows_mapped",
)


class CaseError(ValueError):
    """Case ausente, malformado, ou mutação com valor fora do domínio."""


def case_path(root: Path | str) -> Path:
    return Path(root) / CASE_DIR / CASE_FILE


def new_case(
    case_id: str,
    created_at: str,
    runtime: dict[str, Any],
    repo: str = "",
    strict_gates: bool = False,
) -> dict[str, Any]:
    """Cria um case novo em fase `intake`, todos os gates falsos.

    `created_at` é injetado, nunca gerado: ver nota do módulo.

    `strict_gates` é a escolha de rigor, e ela é **do case**, não da invocação
    (D-3 do spec da Fase 4b): fica gravada no `case.yaml` e vale pela
    investigação inteira — outra sessão, outra máquina, outra ferramenta. Uma
    flag por invocação desligaria o gate em silêncio quando alguém esquecesse
    de passá-la, que é a família de defeito que esta fase existe para não
    cometer.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "created_at": created_at,
        "runtime": copy.deepcopy(runtime),
        "scope": {
            "repo": repo,
            "entrypoints": [],
            "job_names": [],
            "consumers": [],
        },
        "phase": "intake",
        "artifacts": [],
        "facts_index": {"path": "", "count": 0, "by_kind": {}},
        "findings_index": {"path": "", "count": 0, "by_severity": {}},
        "baseline": None,
        "hypotheses": [],
        "gates": dict.fromkeys(GATES, False),
        "strict_gates": bool(strict_gates),
        # Lista, nunca dicionário: dois overrides do mesmo gate em momentos
        # diferentes são dois fatos, e um mapa `gate -> motivo` apagaria o
        # primeiro motivo ao gravar o segundo.
        "gate_overrides": [],
        "skills_used": [],
        "open_questions": [],
    }


def save_case(case: dict[str, Any], root: Path | str) -> Path:
    """Escreve o case como YAML determinístico e legível em diff.

    Chaves ordenadas e `default_flow_style=False`: o mesmo case produz sempre o
    mesmo texto, condição necessária para o arquivo ser committável e revisável.
    """
    path = case_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        case, sort_keys=True, allow_unicode=True, default_flow_style=False
    )
    path.write_text(text, encoding="utf-8")
    return path


def load_case(root: Path | str) -> dict[str, Any]:
    """Carrega o case. Levanta CaseError se ausente ou schema divergente."""
    path = case_path(root)
    if not path.is_file():
        raise CaseError(
            f"Nenhum case em {path}. Rode `sparkforge case open` para criar um."
        )

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise CaseError(f"{path}: YAML inválido: {exc}") from exc

    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        raise CaseError(
            f"{path}: schema_version {version!r} não suportado "
            f"(esperado {SCHEMA_VERSION})"
        )

    return document


def _gate_contract() -> dict[str, dict[str, Any]]:
    """O bloco `gates` do `routing.yaml`, com os nomes conferidos contra `GATES`.

    Import tardio de propósito: sem rigor ligado, `set_phase` não lê o catálogo,
    e o comportamento é bit a bit o de antes desta fase.

    Duas recusas, e as duas só acontecem **sob rigor** — quem não pediu rigor
    nunca chega aqui, que é o critério 5 do spec da Fase 4b intacto:

    - nome **desconhecido**: typo no catálogo viraria gate inerte em silêncio;
    - nome **faltante**: era o buraco medido na revisão final da fase. Sem o
      bloco `gates`, `load_gate_contract` devolvia `{}`, `_gates_blocking` não
      achava contrato para gate nenhum e a lista de bloqueio saía vazia — um
      case com `strict_gates: true` transitava de `intake` a `report` sem
      evidência nenhuma. Rigor que falha **aberto** é pior que rigor ausente,
      porque o case afirma uma garantia que ninguém está prestando.

    Contrato **vazio** e contrato **parcial** recebem a mesma resposta, e isso é
    decisão registrada: os dois deixam pelo menos um gate de `GATES` sem
    contrato, e nesse estado ninguém sabe se aquele gate guarda a fase pedida.
    Tratar o bloco inteiro ausente como "catálogo de outra época, siga em
    frente" premiaria justamente o catálogo que esqueceu mais.
    """
    from sparkforge.case.router import load_gate_contract, routing_path

    contract = load_gate_contract()
    unknown = sorted(set(contract) - set(GATES))
    if unknown:
        raise CaseError(
            f"routing.yaml declara gate desconhecido: {', '.join(unknown)} "
            f"(esperado um de: {', '.join(GATES)}). Gate com nome errado seria "
            f"gate inerte em silêncio."
        )
    missing = [gate for gate in GATES if gate not in contract]
    if missing:
        raise CaseError(_missing_contract_message(missing, routing_path()))
    return contract


def _missing_contract_message(missing: list[str], path: Path) -> str:
    """Qual gate falta, onde ele deveria estar, e o que declarar por gate."""
    lines = [
        f"contrato de gates incompleto: {len(missing)} gate(s) de `store.GATES` "
        f"sem declaração no catálogo carregado.",
        f"  onde: bloco `gates` de {path}",
    ]
    for gate in missing:
        lines.append(f"  - {gate}: ausente do bloco `gates`")
    lines.append(
        "Declare cada um com `satisfied_by` + `produced_by` + `guards_phases` "
        "(gate que bloqueia) ou com `advisory_reason` (gate sem produtor). Este "
        "case foi aberto com `strict_gates`, e gate sem contrato não pode ser "
        "lido como gate satisfeito: seria rigor falhando ABERTO, com o case "
        "afirmando uma garantia que ninguém prestou."
    )
    return "\n".join(lines)


def overridden_gates(case: dict[str, Any]) -> set[str]:
    """Gates com override registrado no case.

    Lê a lista `gate_overrides`; case gravado antes da Fase 4b não tem a chave e
    responde conjunto vazio, sem migração.
    """
    return {
        str(entry.get("gate"))
        for entry in (case.get("gate_overrides") or [])
        if isinstance(entry, dict) and entry.get("gate")
    }


def _gates_blocking(
    phase: str, fact_kinds: set[str], overridden: set[str] | None = None
) -> list[tuple[str, str, str]]:
    """Gates que guardam `phase` e cujo fact produtor não está presente.

    Percorre `GATES` na ordem declarada, e não a do YAML: a mensagem de bloqueio
    é a mesma para o mesmo estado, independente de como o catálogo foi editado.

    Gate sem `satisfied_by` **nunca** entra na lista, nem sob rigor — é o
    critério da §1 do spec da Fase 4b, e ele mora aqui em uma linha só.

    `case["gates"][gate]` não é consultado de propósito (desvio D-4b-2):
    `case update --gate X --gate-value true` viraria override sem motivo e sem
    registro. O que destrava é evidência ou override declarado, nunca a flag.

    `overridden` é o conjunto de gates com override registrado — o D-4 do spec.
    Ele destrava porque tem nome e motivo gravados no case; a flag booleana não,
    porque não tem nem um nem outro.
    """
    contract = _gate_contract()
    skipped = overridden or set()
    blocking: list[tuple[str, str, str]] = []
    for gate in GATES:
        spec = contract.get(gate) or {}
        kind = spec.get("satisfied_by")
        if not kind:
            continue
        if phase not in (spec.get("guards_phases") or []):
            continue
        if gate in skipped:
            continue
        if kind in fact_kinds:
            continue
        blocking.append((gate, kind, str(spec.get("produced_by", "")).strip()))
    return blocking


def _blocked_message(phase: str, blocking: list[tuple[str, str, str]]) -> str:
    """Fase pedida, gate, fact que faltou e o comando exato — o D-5 do spec.

    A Fase 4a mediu que mensagem inacionável passa no CI, então o comando vai
    por extenso, copiável, vindo do `produced_by` do catálogo.
    """
    lines = [
        f"transição para `{phase}` bloqueada: este case foi aberto com rigor de "
        f"gates (`strict_gates`), e {len(blocking)} gate(s) sem a evidência que "
        f"os satisfaz:"
    ]
    for gate, kind, command in blocking:
        lines.append(f"  - {gate}: falta o fact `{kind}`")
        lines.append(f"    produza com: {command}")
        lines.append(
            f"    ou, se o dado genuinamente não existe (job descontinuado, "
            f"ambiente que sumiu): sparkforge case update --override-gate "
            f"{gate} --reason '<por que não existe>'"
        )
    lines.append(
        "O gate checa a PRESENÇA do kind, não o conteúdo do fact: ele prova que "
        "a análise rodou e produziu o artefato que destrava, nunca que ela "
        "cobriu todo `scope.entrypoints` nem que o benchmark é do job certo."
    )
    return "\n".join(lines)


def set_phase(
    case: dict[str, Any],
    phase: str,
    fact_kinds: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Move o case de fase, e — só sob `strict_gates` — cobra os gates da fase.

    `fact_kinds` é o conjunto de kinds de fact que o case já produziu. A
    checagem é por **presença de kind**, não por conteúdo de fact: ela prova que
    a análise rodou e emitiu o artefato que destrava o gate, e **não** prova que
    ela cobriu todo `scope.entrypoints`, nem que o benchmark é do job certo.
    Passar facts inteiros puxaria o índice de facts para dentro do store e faria
    o gate precisar saber o que é "o job certo", que é julgamento. O limite fica
    declarado aqui e na mensagem de bloqueio, como `dq.unresolved` declara o
    recorte dele.

    Parâmetro opcional: sem ele — e sem `strict_gates` no case — o comportamento
    é o de antes da Fase 4b, inclusive sem ler o catálogo. Qual gate guarda qual
    fase, e o que satisfaz cada um, é dado em `rules/catalog/routing.yaml`.
    """
    if phase not in PHASES:
        raise CaseError(
            f"fase desconhecida: {phase!r} (esperado uma de: {', '.join(PHASES)})"
        )
    if case.get("strict_gates"):
        blocking = _gates_blocking(
            phase, set(fact_kinds or ()), overridden_gates(case)
        )
        if blocking:
            raise CaseError(_blocked_message(phase, blocking))
    new = copy.deepcopy(case)
    new["phase"] = phase
    return new


def set_gate(case: dict[str, Any], gate: str, value: bool) -> dict[str, Any]:
    if gate not in GATES:
        raise CaseError(
            f"gate desconhecido: {gate!r} (esperado uma de: {', '.join(GATES)})"
        )
    new = copy.deepcopy(case)
    new["gates"][gate] = value
    return new


def override_gate(
    case: dict[str, Any], gate: str, reason: str, at: str = ""
) -> dict[str, Any]:
    """Registra que alguém passou por cima de um gate, e por quê (D-4 do spec).

    O dado às vezes genuinamente não existe — job descontinuado, ambiente que
    sumiu, corpus sem trabalho Spark alcançável. Gate sem escapatória reabre o
    impasse que a §5.5 da Fase 0 recusou. A escapatória custa uma frase escrita,
    e a frase fica no case: é a diferença entre *o gate não existe* e *o gate
    existe e alguém passou por cima com o nome dele registrado*.

    Sem motivo o override é recusado — um override anônimo seria a mesma coisa
    que `--gate-value true`, que o desvio D-4b-2 já recusou.

    `at` é injetado por quem chama, como todo timestamp deste módulo. Vazio é
    aceito porque `override_gate` é chamável de teste e de biblioteca; a CLI
    passa o `--now` que ela já exige.
    """
    if gate not in GATES:
        raise CaseError(
            f"gate desconhecido: {gate!r} (esperado uma de: {', '.join(GATES)})"
        )
    motivo = (reason or "").strip()
    if not motivo:
        raise CaseError(
            f"override do gate {gate!r} recusado: falta o motivo. Passe "
            f"`--reason \"<por que a evidência não existe>\"` — o case guarda "
            f"quem passou por cima de quê e por quê, e override sem motivo não "
            f"se distingue de gate esquecido."
        )
    new = copy.deepcopy(case)
    overrides = list(new.get("gate_overrides") or [])
    overrides.append({"gate": gate, "reason": motivo, "at": at})
    new["gate_overrides"] = overrides
    return new


def add_hypothesis(
    case: dict[str, Any], statement: str, prediction: str, experiment: str
) -> dict[str, Any]:
    new = copy.deepcopy(case)
    hyp_id = f"h{len(new['hypotheses']) + 1}"
    new["hypotheses"].append(
        {
            "id": hyp_id,
            "statement": statement,
            "prediction": prediction,
            "experiment": experiment,
            "status": "open",
        }
    )
    return new


def record_skill_use(
    case: dict[str, Any], skill: str, at: str, outcome: str
) -> dict[str, Any]:
    new = copy.deepcopy(case)
    new["skills_used"].append({"skill": skill, "at": at, "outcome": outcome})
    return new


def set_index(
    case: dict[str, Any],
    which: str,
    path: str,
    count: int,
    breakdown: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Atualiza `facts_index` ou `findings_index` com contagem e detalhe."""
    if which == "facts_index":
        breakdown_key = "by_kind"
    elif which == "findings_index":
        breakdown_key = "by_severity"
    else:
        raise CaseError(
            f"índice desconhecido: {which!r} (esperado facts_index ou findings_index)"
        )
    new = copy.deepcopy(case)
    new[which] = {"path": path, "count": count, breakdown_key: dict(breakdown or {})}
    return new
