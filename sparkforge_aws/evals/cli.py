"""`python -m sparkforge_aws.evals grade|compare|debate` -- a CLI do nivel de agente.

Mora DENTRO do pacote de avaliacao, e nao em `sparkforge_aws/adapters/`, por causa
da fronteira que `tests/test_harness_boundary.py` tranca: o runtime nao importa
a avaliacao; a avaliacao mede o runtime. Aqui a dependencia corre no sentido
permitido: este modulo importa o extrator `sparkforge_aws.facts.host_transcript`.

A CLI aceita NOMES, nunca caminhos. Cada nome passa por `os.path.basename` e e
recusado se trouxer separador, e o diretorio sai de uma base fixa:

  * suite    -> `<cwd>/evals/agentic/<suite>`
  * execucao -> `~/.sparkforge_aws/agentic-evals/<run_id>` (onde o runner grava)
  * conjunto -> `<cwd>/evals/agentic/<suite>/baselines/<nome>` (commitado) ou
    `~/.sparkforge_aws/agentic-evals/<nome>` (recem-rodado); precisa existir em
    exatamente um dos dois.
  * debate   -> a suite e CONSTANTE (`<cwd>/evals/agentic/debate`), e a execucao
    e `~/.sparkforge_aws/debate-evals/<run>` (onde `scripts/run_debate.py` grava).
    O placar vai para `grade.json` dentro da propria execucao.

O scorecard de `grade` vai para `scorecard.json` dentro da propria execucao, e
`compare` so imprime -- sem `--out`, nenhum caminho do argv chega a escrita. A
decisao e do operador (2026-09-10), depois de o scanner de seguranca recusar a
versao que aceitava diretorio arbitrario mesmo confinado por `realpath`.

`eval_grade` e `eval_compare` continuam recebendo CAMINHO, para os testes, a
regeneracao de fixtures e o runner -- quem chama a biblioteca ja e codigo, nao
argv.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sparkforge_aws.case.store import state_path
from sparkforge_aws.evals.compare import compare
from sparkforge_aws.evals.debate_grade import GRADE_FILE, DebateGradeError, grade_debate_run
from sparkforge_aws.evals.evidence_adapters import (
    AuthorizedCommandAdapter,
    BundleFileAdapter,
    EvidenceAdapterError,
)
from sparkforge_aws.evals.evolution import EvolutionError, EvolutionService
from sparkforge_aws.evals.grade import grade
from sparkforge_aws.evals.suite import SuiteError, load_suite
from sparkforge_aws.facts.host_transcript import extract_host_transcript_path

# `state_path` mantem o historico de quem avaliava antes do rename: execucoes
# gravadas em `~/.sparkforge/agentic-evals/` seguem sendo O conjunto de runs.
RUNS_ROOT = state_path(Path.home(), "agentic-evals")
DEBATE_RUNS_ROOT = state_path(Path.home(), "debate-evals")
DEBATE_SUITE = ("evals", "agentic", "debate")
SCORECARD = "scorecard.json"


class EvalError(Exception):
    """Erro acionavel: mensagem para stderr e exit code 2."""


_SEPARADORES = ("/", "\\", ":")


def _nome(valor: str, flag: str) -> str:
    """Um NOME, recusado se trouxer separador de caminho de QUALQUER sistema.

    `os.path.basename` sozinho depende do SO: no Linux, `C:\\x` nao tem
    separador e passaria. O CI do PR #48 pegou isso.
    """
    nome = os.path.basename(valor)
    if not nome or nome in (".", "..") or nome != valor or any(s in nome for s in _SEPARADORES):
        raise EvalError(f"{flag} aceita um NOME, sem separador de caminho: {valor!r}")
    return nome


def _jsonl_stems(directory: Path) -> dict[str, Path]:
    """`<stem> -> caminho` dos `*.jsonl` DIRETAMENTE em `directory`.

    `os.scandir` plano, e nao `glob` (reprovado por AST em
    `tests/test_facts_scan.py`) nem a varredura com denylist do pacote, cujo
    teto de tamanho pularia um transcript grande e o faria virar pergunta sem
    transcript sem ninguem ver.
    """
    if not directory.is_dir():
        raise EvalError(f"diretorio de transcripts ausente: {directory}")
    with os.scandir(directory) as entradas:
        arquivos = sorted(e.name for e in entradas if e.is_file() and e.name.endswith(".jsonl"))
    return {nome[: -len(".jsonl")]: directory / nome for nome in arquivos}


def eval_grade(suite_dir: Path | str, transcripts_dir: Path | str) -> dict[str, Any]:
    """Scorecard de uma execucao: `suite.yaml` contra os `<qid>.jsonl`."""
    try:
        suite = load_suite(suite_dir)
    except SuiteError as exc:
        raise EvalError(f"suite invalida: {exc}") from exc
    diretorio = Path(transcripts_dir)
    transcripts = {
        qid: extract_host_transcript_path(caminho)
        for qid, caminho in _jsonl_stems(diretorio).items()
    }
    return grade(suite, transcripts, run_id=diretorio.resolve().name)


def _load_scorecards(directory: Path, flag: str) -> list[dict[str, Any]]:
    if not directory.is_dir():
        raise EvalError(f"{flag}: diretorio ausente: {directory}")
    with os.scandir(directory) as entradas:
        nomes = sorted(e.name for e in entradas if e.is_file() and e.name.endswith(".json"))
    scorecards = []
    for nome in nomes:
        try:
            dado = json.loads((directory / nome).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvalError(f"{flag}: {nome} nao e JSON legivel: {exc}") from exc
        if isinstance(dado, dict) and "suite" in dado and "questions" in dado:
            scorecards.append(dado)
    return scorecards


def eval_compare(baseline_dir: Path | str, candidate_dir: Path | str) -> dict[str, Any]:
    """Transicao por pergunta entre dois diretorios de scorecards. Recusa por
    nome o que nao e comparavel; nao conclui se melhorou (regra 30)."""
    return compare(
        _load_scorecards(Path(baseline_dir), "--baseline"),
        _load_scorecards(Path(candidate_dir), "--candidate"),
    )


def _suite_dir(nome: str) -> Path:
    return Path.cwd() / "evals" / "agentic" / _nome(nome, "--suite")


def _conjunto(suite: str, nome: str, flag: str) -> Path:
    alvo = _nome(nome, flag)
    candidatos = [
        base / alvo
        for base in (_suite_dir(suite) / "baselines", RUNS_ROOT)
        if (base / alvo).is_dir()
    ]
    if len(candidatos) != 1:
        raise EvalError(
            f"{flag} {nome!r}: precisa existir em exatamente um de "
            f"evals/agentic/{suite}/baselines/ e {RUNS_ROOT} (achado em {len(candidatos)})"
        )
    return candidatos[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sparkforge_aws.evals",
        description=(
            "Pontua transcripts de agente contra o gabarito de uma suite e compara "
            "execucoes. So le arquivo; nao executa agente. Recebe NOMES, nao caminhos."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)
    grade_p = sub.add_parser(
        "grade", help="Scorecard de uma execucao; grava scorecard.json dentro dela."
    )
    grade_p.add_argument("--suite", required=True, help="Nome da suite em evals/agentic/.")
    grade_p.add_argument(
        "--run", required=True, help=f"Nome da execucao em {RUNS_ROOT}."
    )
    compare_p = sub.add_parser(
        "compare", help="Transicao por pergunta entre dois conjuntos de scorecards (k/N)."
    )
    compare_p.add_argument("--suite", required=True, help="Nome da suite em evals/agentic/.")
    compare_p.add_argument("--baseline", required=True, help="Nome do conjunto de referencia.")
    compare_p.add_argument("--candidate", required=True, help="Nome do conjunto candidato.")
    debate_p = sub.add_parser(
        "debate",
        help=(
            "Placar de uma execucao de scripts/run_debate.py contra evals/agentic/debate; "
            "grava grade.json dentro dela."
        ),
    )
    debate_p.add_argument("--run", required=True, help=f"Nome da execucao em {DEBATE_RUNS_ROOT}.")
    candidate_p = sub.add_parser(
        "candidate", help="Valida, avalia, promove ou reverte candidato versionado."
    )
    candidate_sub = candidate_p.add_subparsers(dest="candidate_action", required=True)
    validate_p = candidate_sub.add_parser("validate")
    validate_p.add_argument("--repo", default=".")
    validate_p.add_argument("--candidate-id")
    evaluate_p = candidate_sub.add_parser("evaluate")
    evaluate_p.add_argument("--repo", default=".")
    evaluate_p.add_argument("--candidate", required=True)
    evaluate_p.add_argument("--suite")
    evaluate_p.add_argument("--bundle", "--evidence", dest="bundle")
    evaluate_p.add_argument("--external-command")
    promote_p = candidate_sub.add_parser("promote")
    promote_p.add_argument("--repo", default=".")
    promote_p.add_argument("--candidate", required=True)
    promote_p.add_argument("--allow-active", action="store_true")
    rollback_p = candidate_sub.add_parser("rollback")
    rollback_p.add_argument("--repo", default=".")
    rollback_p.add_argument("--candidate", required=True)
    rollback_p.add_argument("--previous", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "grade":
            execucao = RUNS_ROOT / _nome(args.run, "--run")
            payload = eval_grade(_suite_dir(args.suite), execucao)
            (execucao / SCORECARD).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        elif args.action == "debate":
            execucao = DEBATE_RUNS_ROOT / _nome(args.run, "--run")
            if not execucao.is_dir():
                raise EvalError(f"--run {args.run!r}: execucao ausente em {DEBATE_RUNS_ROOT}")
            payload = grade_debate_run(Path.cwd().joinpath(*DEBATE_SUITE), execucao)
            (execucao / GRADE_FILE).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        elif args.action == "candidate":
            service = EvolutionService(args.repo)
            if args.candidate_action == "validate":
                payload = service.validate(args.candidate_id)
            elif args.candidate_action == "evaluate":
                candidate = service.registry.get(args.candidate)
                if args.bundle and args.external_command:
                    raise EvalError("--bundle e --external-command sao mutuamente exclusivos")
                bundle = None
                if args.bundle:
                    bundle = BundleFileAdapter(args.repo).load(args.bundle)
                if args.external_command:
                    service.registry.load()
                    bundle = AuthorizedCommandAdapter(
                        service.registry.external_commands,
                        repo=args.repo,
                    ).run(args.external_command)
                payload = service.evaluate(
                    candidate,
                    bundle=bundle,
                    suite_path=args.suite,
                ).to_dict()
            elif args.candidate_action == "promote":
                candidate = service.registry.get(args.candidate)
                evaluation = service.latest_evaluation(candidate)
                payload = service.promote(
                    candidate, evaluation, caller_authorized=args.allow_active
                ).to_dict()
            else:
                candidate = service.registry.get(args.candidate)
                previous = service.registry.get(args.previous)
                payload = {
                    "candidate": service.rollback(candidate, previous).to_dict(),
                    "restored": previous.to_dict(),
                }
        else:
            payload = eval_compare(
                _conjunto(args.suite, args.baseline, "--baseline"),
                _conjunto(args.suite, args.candidate, "--candidate"),
            )
    except (EvalError, DebateGradeError, EvolutionError, EvidenceAdapterError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0
