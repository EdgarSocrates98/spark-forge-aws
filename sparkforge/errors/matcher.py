"""O matcher tem DOIS caminhos, e so um deles e fato.

`build_signature_matches` constata que a excecao ja estruturada casa com uma
assinatura de `knowledge/errors/`. Isso e observacao: a classe lancada contem o
texto que a assinatura declara, ou nao contem. O que fazer a respeito --
`likely_causes`, `fixes`, `diagnostic_steps`, `unsafe_fixes` -- e JUIZO, e juizo
mora no catalogo de regras, nao aqui.

## Ele consome DUAS fontes, e a segunda destrava quatro assinaturas

MEDIDO em 2026-09-09 sobre `knowledge/errors/`: das SEIS assinaturas, apenas
duas -- `NoSuchMethodError` (ERR-GLUE-002) e `NoSuchFieldError` (ERR-GLUE-003)
-- sao nome de classe de excecao. As outras QUATRO sao trecho de mensagem de
LOG, e por `spark.exception` nunca casavam:

    ERR-ATH-001   Cannot read unsupported version 3
    ERR-GLUE-001  Container killed by YARN for exceeding memory limits
    ERR-ICE-001   CommitFailedException: Commit failed: Table was updated concurrently
    ERR-LF-001    Insufficient Lake Formation permission(s) on

`cloudwatch.log_event` (de `sparkforge/facts/cloudwatch_logs.py`) e o caminho
delas: a mesma assinatura, casada contra o TEXTO DA LINHA em vez da classe, e
`matched_on: "log_line"` diz por onde ela entrou. As duas de classe continuam
casando pelos dois caminhos -- `NoSuchMethodError` aparece tanto no
`exception_class` quanto na linha de log que o imprime --, e e por isso que
`matched_on` existe: sem ele, dois matches do mesmo id seriam indistinguiveis.

A linha ja chega REDIGIDA do extrator, e uma linha redigida vira `<redigido>`
inteiro: ela nao casa assinatura nenhuma, e nao deve casar. Ela entra na
contagem de linhas examinadas e nada mais.

`match_log` e `ErrorMatchResult` continuam existindo porque
`sparkforge forge errors match` os usa. Eles casam SUBSTRING de log cru e
carregam o juizo junto -- e e por isso que precisam de `confidence=0.98`, que e
constante literal, nunca medida (regra 28 do `CLAUDE.md`: antes de afirmar,
leia o numero; aqui nao ha numero para ler). O caminho de fact nao carrega
`confidence` nenhum, porque nao finge julgar.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.knowledge_ref import knowledge_dir

EXTRACTOR_ID = "error_signature@0.1.0"

EMITTED_KINDS = frozenset({"error.signature_match", "error.signature.unresolved"})


@dataclass
class ErrorMatchResult:
    error_id: str
    signature: str
    service: str
    likely_causes: list[str]
    diagnostic_steps: list[str]
    fixes: list[str]
    confidence: float
    matched_snippet: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeterministicErrorMatcher:
    """Matches stacktraces and logs against local Error KB signatures with zero LLM calls."""

    def __init__(self, errors_dir: Path | None = None) -> None:
        # `knowledge_dir()` e nao `Path(__file__).parent.parent.parent`, e a
        # diferenca so aparece no WHEEL. No repositorio os dois resolvem para
        # `<raiz>/knowledge/errors` e o defeito e invisivel; instalado por pip,
        # o caminho relativo aponta para `site-packages/knowledge/errors`,
        # que nao existe -- o `force-include` do `pyproject.toml` poe o
        # diretorio em `sparkforge/knowledge`, e e por isso que
        # `sparkforge/knowledge_ref.py` existe.
        #
        # O modo de falha era SILENCIOSO e por isso caro: `_load_signatures`
        # devolve cedo quando o diretorio nao existe, `self.signatures` fica
        # vazia, e `build_signature_matches` passa a emitir
        # `error.signature.unresolved` para TUDO. Um operador com o pacote
        # instalado veria "nenhuma assinatura conhecida cobre isto" sobre um
        # `NoSuchMethodError` que o catalogo conhece. Quem pegou foi o
        # `Artifact parity gate` do CI (`scripts/verify_wheel.py`), que roda o
        # corpus contra o wheel instalado -- e e exatamente para isso que ele
        # existe.
        self.errors_dir = errors_dir or (knowledge_dir() / "errors")
        self.signatures: list[dict[str, Any]] = []
        self._load_signatures()

    def _load_signatures(self) -> None:
        # `errors_dir` vem do construtor, entao o default embarcado nao e
        # garantia: quem instancia pode apontar para fora do `knowledge/`, e a
        # partir dai isto e varredura de arvore de terceiro como qualquer outra.
        if not self.errors_dir.is_dir():
            return
        for err_file in iter_source_files(self.errors_dir, "*.json"):
            try:
                data = json.loads(err_file.read_text(encoding="utf-8"))
                if "id" in data and "signature" in data:
                    self.signatures.append(data)
            except Exception:  # noqa: S110 -- assinatura invalida nao derruba o catalogo inteiro
                pass

    def match_log(self, log_content: str) -> list[ErrorMatchResult]:
        matches: list[ErrorMatchResult] = []
        log_lower = log_content.lower()

        for sig in self.signatures:
            sig_pattern = sig["signature"].lower()
            if sig_pattern in log_lower or re.search(re.escape(sig_pattern), log_lower):
                # Find matching snippet
                idx = log_lower.find(sig_pattern)
                start = max(0, idx - 40)
                end = min(len(log_content), idx + len(sig_pattern) + 40)
                snippet = log_content[start:end].strip()

                matches.append(
                    ErrorMatchResult(
                        error_id=sig["id"],
                        signature=sig["signature"],
                        service=sig.get("service", "unknown"),
                        likely_causes=sig.get("likely_causes", []),
                        diagnostic_steps=sig.get("diagnostic_steps", []),
                        fixes=sig.get("fixes", []),
                        # CONSTANTE LITERAL, e ela nao mede nada: nenhum
                        # experimento calibrou 0.98, e nao ha o que ler
                        # (regra 28). Ela existe porque este caminho devolve
                        # juizo junto com a constatacao, e juizo pede um numero
                        # de confianca. `build_signature_matches` nao devolve
                        # juizo, e por isso nao carrega confidence nenhum.
                        confidence=0.98,
                        matched_snippet=snippet,
                    )
                )

        return matches


def build_signature_matches(facts: Sequence[Fact]) -> list[Fact]:
    """Casa `spark.exception` E `cloudwatch.log_event` contra `knowledge/errors/`.

    Funcao PURA sobre Facts: nunca le artefato e nunca reparseia texto cru de
    arquivo. As duas fontes chegam ja estruturadas -- a excecao por
    `sparkforge/facts/exception.py`, a linha de log por
    `sparkforge/facts/cloudwatch_logs.py`, que a redigiu antes de emiti-la.

    No caminho da EXCECAO, `attrs.caused_by` entra na busca junto com
    `attrs.exception_class`, porque a assinatura que importa costuma estar na
    causa raiz e nao no `SparkException` que a embrulha -- e `matched_on` diz
    por qual dos dois ela entrou.

    No caminho do LOG, a assinatura e casada contra `attrs.message`, e
    `matched_on` sai `log_line`. A recusa e AGREGADA por (run, log group) e nao
    por linha: emitir um `unresolved` por linha que nao casa transformaria um
    log de 500 linhas em 500 facts de ponto cego, e o ponto cego e um so --
    "nenhuma assinatura conhecida aparece neste log".

    Lista vazia so acontece quando NAO HA nenhuma das duas fontes no case.
    Havendo, sai `error.signature_match` ou sai `error.signature.unresolved`: a
    diferenca entre "nenhuma assinatura conhecida cobre isto" e "ninguem
    perguntou" e o que a recusa nomeada guarda.
    """
    assinaturas = DeterministicErrorMatcher().signatures
    saida: list[Fact] = []
    saida.extend(_casar_log(facts, assinaturas))
    for fact in facts:
        if fact.kind != "spark.exception":
            continue
        subject = dict(fact.subject)
        attrs = fact.attrs or {}
        provenance = _fact_provenance(fact)

        classe = str(attrs.get("exception_class") or "")
        causas = [str(c) for c in (attrs.get("caused_by") or [])]
        # A cabeca da mensagem, com a classe na frente: e assim que a assinatura
        # a escreve (`java.lang.OutOfMemoryError: Java heap space`), e casar so
        # contra `message_head` cru perderia o prefixo.
        cabeca = f"{classe}: {attrs.get('message_head') or ''}".strip()

        casados: list[tuple[str, str, str]] = []
        for sig in assinaturas:
            padrao = str(sig.get("signature") or "")
            if not padrao:
                continue
            alvo = padrao.lower()
            if alvo in classe.lower():
                casados.append((str(sig["id"]), "exception_class", classe))
                continue
            causa = next((c for c in causas if alvo in c.lower()), None)
            if causa is not None:
                casados.append((str(sig["id"]), "caused_by", causa))
                continue
            # `message_head` e a TERCEIRA porta, e o desenho da frente ja a
            # previa (`matched_on: exception_class | message_head | frame`) --
            # ela so nao tinha sido implementada porque nenhuma assinatura
            # precisava dela ate 2026-09-09.
            #
            # Quem a exigiu foram `ERR-SPARK-006` e `ERR-SPARK-007`: as duas sao
            # `java.lang.OutOfMemoryError`, e o que as separa esta na MENSAGEM
            # -- "Java heap space" contra "GC overhead limit exceeded". Casar so
            # por classe as tornaria indistinguiveis, e os dois consertos
            # divergem (distribuicao por task contra conjunto vivo).
            #
            # Ela vem DEPOIS das outras duas de proposito: uma assinatura que
            # case pela classe deve reportar `exception_class`, e nao
            # `message_head`, mesmo quando o texto tambem aparece na mensagem.
            if alvo in cabeca.lower():
                casados.append((str(sig["id"]), "message_head", cabeca))

        if not casados:
            saida.append(
                Fact(
                    kind="error.signature.unresolved",
                    subject=subject,
                    measures={},
                    attrs={
                        "reason": "nenhuma_assinatura_casou",
                        "exception_class": classe,
                    },
                    provenance=provenance,
                )
            )
            continue

        for sig_id, onde, valor in casados:
            saida.append(
                Fact(
                    kind="error.signature_match",
                    # `signature_id` entra no subject porque duas assinaturas
                    # podem casar a MESMA excecao, e o id do Fact e derivado de
                    # (kind, subject, measures): sem ele, o segundo match
                    # colidiria com o primeiro.
                    subject={**subject, "signature_id": sig_id},
                    measures={},
                    attrs={
                        "signature_id": sig_id,
                        "matched_on": onde,
                        "matched_class": valor,
                    },
                    provenance=provenance,
                )
            )
    return sort_facts(saida)


# Teto do trecho de linha gravado em `attrs.matched_line`. Mesmo numero de
# `message_head` em `facts/exception.py`, pela mesma razao: o fact guarda o que
# identifica o casamento, nao o log inteiro.
_TRECHO = 200


def _casar_log(
    facts: Sequence[Fact], assinaturas: list[dict[str, Any]]
) -> list[Fact]:
    """O caminho de LOG, separado do de excecao porque a recusa dele e agregada.

    Uma linha `redacted` nao e examinada contra assinatura nenhuma -- o texto
    dela e `<redigido>`, e casar assinatura contra isso seria casar contra a
    propria redacao. Ela conta em `lines_examined` mesmo assim: o operador
    precisa saber que havia linha ali.
    """
    saida: list[Fact] = []
    # (job, run, log group) -> [linhas examinadas, houve match, subject, provenance]
    escopos: dict[tuple[str, str, str], list[Any]] = {}

    for fact in facts:
        if fact.kind != "cloudwatch.log_event":
            continue
        subject = dict(fact.subject)
        attrs = fact.attrs or {}
        provenance = _fact_provenance(fact)
        chave = (
            str(subject.get("job_name") or ""),
            str(subject.get("job_run_id") or ""),
            str(subject.get("log_group") or ""),
        )
        escopo = escopos.setdefault(chave, [0, False, subject, provenance])
        escopo[0] += 1

        if attrs.get("redacted"):
            continue
        mensagem = str(attrs.get("message") or "")
        if not mensagem:
            continue
        alvo_linha = mensagem.lower()
        for sig in assinaturas:
            padrao = str(sig.get("signature") or "")
            if not padrao or padrao.lower() not in alvo_linha:
                continue
            escopo[1] = True
            saida.append(
                Fact(
                    kind="error.signature_match",
                    subject={**subject, "signature_id": str(sig["id"])},
                    measures={},
                    attrs={
                        "signature_id": str(sig["id"]),
                        "matched_on": "log_line",
                        "matched_line": mensagem[:_TRECHO],
                    },
                    provenance=provenance,
                )
            )

    for (_, _, _), (linhas, casou, subject, provenance) in escopos.items():
        if casou:
            continue
        # O subject da recusa e o do ESCOPO, sem o `event`: o ponto cego e do
        # log inteiro, nao da linha 37.
        escopo_subject = {k: v for k, v in subject.items() if k != "event"}
        saida.append(
            Fact(
                kind="error.signature.unresolved",
                subject=escopo_subject,
                measures={"lines_examined": float(linhas)},
                attrs={
                    "reason": "nenhuma_assinatura_casou_no_log",
                    "source": "cloudwatch.log_event",
                },
                provenance=provenance,
            )
        )
    return saida


def _fact_provenance(fact: Fact) -> dict[str, Any]:
    """Herda o artefato do fact de origem, e assina com ESTE extrator."""
    origem = fact.provenance or {}
    return {
        "artifact": origem.get("artifact", "facts"),
        "artifact_sha256": origem.get("artifact_sha256", ""),
        "extractor": EXTRACTOR_ID,
    }


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "DeterministicErrorMatcher",
    "ErrorMatchResult",
    "build_signature_matches",
]
