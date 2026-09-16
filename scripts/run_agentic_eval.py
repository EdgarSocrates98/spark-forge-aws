#!/usr/bin/env python3
"""Roda o nivel de agente de uma suite: uma sessao `claude -p` por pergunta.

FORA do pacote de proposito (regra 23): `sparkforge/` nao dispara host nem chama
provider, e o grader (`python -m sparkforge.evals grade`) so le arquivo. Este script e o
unico lugar do repositorio que gasta token, e so quando o operador o roda --
nunca no CI.

Para cada pergunta da suite:

  1. gera um uuid e chama `claude -p --session-id <uuid> ...` com o texto da
     pergunta mais o `answer_protocol` da suite, a partir da raiz do repositorio;
  2. localiza o transcript que a sessao PERSISTIU em
     `~/.claude/projects/*/<uuid>.jsonl` -- o formato que o extrator conhece
     (conferido no smoke de 2026-09-10) -- e o copia para o diretorio da
     execucao, como `<qid>.jsonl`;
  3. guarda o JSON final do stdout em `<qid>.result.json`, que o grader nao le.

`run.json` e `scorecard.json` ficam em cada execucao, e o conjunto
`~/.sparkforge/agentic-evals/<suite>-<data>/` junta os N scorecards (`r1.json`...)
para `python -m sparkforge.evals compare`. `run.json` registra argv,
`claude --version`, data, a suite (id e sha256), o workspace de prova e o
status de cada pergunta. Pergunta que falhou no host (`host_failed`) segue sem
transcript, e o grader a conta como `transcript_not_found` -- nunca como erro.

NENHUM VALOR DO ARGV CHEGA A UM CAMINHO, E NENHUM VALOR LIVRE CHEGA A
`subprocess`. A suite e constante (`evals/agentic/fase0`), o modelo e as fontes
de configuracao sao mapeados de allowlist, o executavel e o `claude` do PATH, a
configuracao MCP e `evals/agentic/mcp.json`, e a saida mora sempre sob
`~/.sparkforge/agentic-evals/` -- fora de qualquer repositorio, porque
transcript de sessao real carrega caminho e contexto do operador. Uma suite nova
entra como constante nova, e a mudanca fica no diff: escolher o diretorio pelo
argv, mesmo contra lista fechada, e o fluxo que o scanner de seguranca recusou.

Isolamento, e o numero que o motivou: no smoke de 2026-09-10, uma sessao Haiku
de uma pergunta gastou 120 122 tokens de `cache_creation` so com a configuracao
GLOBAL do operador (hooks, MCPs, CLAUDE.md de usuario), e estourou um teto de
US$ 0,10 antes de a primeira tool responder. Por isso os defaults sao
`--strict-mcp-config` e `--setting-sources project`, os dois gravados em
`run.json`, porque mudam o que o agente viu.

Superficie de tools (`--surface`), acrescentada em 2026-09-15 para medir se o
TAMANHO da superficie muda o comportamento do agente. `full` e o servidor MCP
inteiro. `suite` nega, por `--disallowedTools`, toda tool do registro que o
gabarito da suite nao exige -- a lista sai de `required_tools` contra
`sparkforge.adapters.tools.TOOLS`, nunca do argv. Os dois bracos gravam em
`run.json` quantas tools MCP o agente pode ver.

Uso:
    python scripts/run_agentic_eval.py --repeat 3 --model haiku
    python scripts/run_agentic_eval.py --repeat 3 --model haiku --surface suite
    python scripts/run_agentic_eval.py --dry-run    # nao gasta
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sparkforge.adapters.tools import TOOLS  # noqa: E402
from sparkforge.evals.cli import SCORECARD, eval_grade  # noqa: E402
from sparkforge.evals.suite import QUESTION_ID, Question, Suite, load_suite  # noqa: E402

AGENTIC = ROOT / "evals" / "agentic"
SUITE_DIR = AGENTIC / "fase0"
MCP_CONFIG = AGENTIC / "mcp.json"
OUT_BASE = Path.home() / ".sparkforge" / "agentic-evals"
TRANSCRIPTS = Path.home() / ".claude" / "projects"

MODELOS = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
    "fable": "fable",
}
FONTES = {
    "project": "project",
    "project,local": "project,local",
    "user,project,local": "user,project,local",
}
WORKSPACE_DIRS = ("sparkforge", "rules", "knowledge", "skills", "agents", "fixtures")
WORKSPACE_FILES = ("CLAUDE.md", "AGENTS.md", "AGENT_PROTOCOL.md", "pyproject.toml")
SEM_GABARITO = {"expected", "meta.yaml", "host_transcript", "__pycache__", ".pytest_cache"}
ALLOWED_TOOLS = ",".join(
    (
        "mcp__sparkforge",
        "Bash(sparkforge:*)",
        "Bash(python -m sparkforge:*)",
        "Read",
        "Grep",
        "Glob",
    )
)
SUPERFICIES = ("full", "suite")
MCP_PREFIX = "mcp__sparkforge__"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--repeat", type=int, default=1, help="Execucoes da suite inteira (N), 1..50.")
    p.add_argument(
        "--model", choices=sorted(MODELOS), help="Alias de modelo repassado ao claude -p."
    )
    p.add_argument("--max-budget-usd", type=float, help="Teto por PERGUNTA, em (0, 1000].")
    p.add_argument("--timeout", type=int, default=600, help="Segundos por pergunta, 1..7200.")
    p.add_argument("--only", action="append", default=[], help="Roda so estes ids (repetivel).")
    p.add_argument(
        "--setting-sources",
        choices=sorted(FONTES),
        default="project",
        help="Repassado ao claude -p. Default: so a configuracao do repositorio.",
    )
    p.add_argument(
        "--no-strict-mcp",
        action="store_true",
        help="Nao passa --strict-mcp-config (o agente vera os MCPs globais do operador).",
    )
    p.add_argument(
        "--surface",
        choices=SUPERFICIES,
        default="full",
        help="full: todas as tools MCP. suite: so as que o gabarito exige.",
    )
    p.add_argument("--dry-run", action="store_true", help="Mostra os comandos e sai.")
    return p


def _inside(caminho: Path, base: Path) -> bool:
    resolvido, raiz = caminho.resolve(), base.resolve()
    return resolvido == raiz or raiz in resolvido.parents


def _claude() -> str:
    executavel = shutil.which("claude")
    if executavel is None:
        raise SystemExit("executavel `claude` nao encontrado no PATH")
    return str(Path(executavel).resolve())


def _budget(valor: float | None) -> str | None:
    if valor is None:
        return None
    if not 0 < valor <= 1000:
        raise SystemExit("--max-budget-usd precisa estar em (0, 1000]")
    return f"{valor:.4f}"


def _prompt(suite: Suite, question: Question) -> str:
    return f"{question.question}\n\n{suite.answer_protocol}"


def _negadas(suite: Suite, superficie: str) -> list[str]:
    """Tools MCP negadas ao agente no braco `suite`; nenhuma no `full`.

    A lista e a MESMA para toda pergunta: a uniao de `required_tools` da suite,
    alternativas incluidas, e nao as tools da propria pergunta -- entregar so a
    tool certa mediria leitura de gabarito, nao escolha. Verbo exigido que o
    registro nao conhece derruba a execucao, porque um braco que negasse a tool
    certa mediria outra coisa.
    """
    if superficie == "full":
        return []
    verbos: set[str] = set()
    for pergunta in suite.questions:
        for item in pergunta.required_tools:
            verbos.update((item,) if isinstance(item, str) else item)
    exigidas = {f"sparkforge_{verbo}" for verbo in verbos}
    desconhecidas = sorted(exigidas - set(TOOLS))
    if desconhecidas:
        raise SystemExit(f"verbo exigido pela suite sem tool no registro: {desconhecidas}")
    return [MCP_PREFIX + nome for nome in sorted(set(TOOLS) - exigidas)]


def _command(
    claude: str,
    args: argparse.Namespace,
    suite: Suite,
    question: Question,
    session: str,
) -> list[str]:
    comando = [
        claude,
        "-p",
        "--session-id",
        session,
        "--output-format",
        "json",
        "--mcp-config",
        str(MCP_CONFIG),
        "--setting-sources",
        FONTES[args.setting_sources],
        "--allowedTools",
        ALLOWED_TOOLS,
    ]
    negadas = _negadas(suite, args.surface)
    if negadas:
        comando += ["--disallowedTools", ",".join(negadas)]
    if not args.no_strict_mcp:
        comando.append("--strict-mcp-config")
    if args.model:
        comando += ["--model", MODELOS[args.model]]
    teto = _budget(args.max_budget_usd)
    if teto:
        comando += ["--max-budget-usd", teto]
    comando.append(_prompt(suite, question))
    return comando


def _persisted(session: uuid.UUID) -> Path | None:
    """O transcript que a sessao gravou -- so dentro de `~/.claude/projects`."""
    nome = f"{session}.jsonl"
    if not TRANSCRIPTS.is_dir():
        return None
    achados = [
        projeto / nome
        for projeto in sorted(TRANSCRIPTS.iterdir())
        if projeto.is_dir() and (projeto / nome).is_file()
    ]
    if len(achados) != 1 or not _inside(achados[0], TRANSCRIPTS):
        return None
    return achados[0]


def _sem_gabarito(_diretorio: str, nomes: list[str]) -> set[str]:
    return {n for n in nomes if n in SEM_GABARITO}


def _workspace(destino: Path) -> Path:
    """Copia de PROVA do repositorio: o que o agente precisa, sem o gabarito.

    No primeiro baseline (2026-09-10) o agente respondeu `fase0-01` abrindo
    `fixtures/.../expected/findings.json` -- o caderno de respostas estava na
    mesa, e o acerto media leitura de golden, nao uso de tool. A copia leva o
    pacote, o catalogo, o knowledge, as skills, os agentes e as ENTRADAS das
    fixtures; deixa de fora `expected/`, o `meta.yaml` (cujo `proves` cita a
    regra esperada), o corpus `host_transcript` (cuja suite de fixture traz
    respostas), e `tests/`, `evals/`, `docs/`, `.claude/`, `.git/` inteiros.
    Mesma logica do holdout: resposta disponivel nao mede capacidade.
    """
    if not _inside(destino, OUT_BASE):
        raise SystemExit(f"workspace fora de {OUT_BASE}: {destino}")
    destino.mkdir(parents=True, exist_ok=False)
    for nome in WORKSPACE_DIRS:
        shutil.copytree(ROOT / nome, destino / nome, ignore=_sem_gabarito)
    for nome in WORKSPACE_FILES:
        if (ROOT / nome).is_file():
            shutil.copy2(ROOT / nome, destino / nome)
    return destino


def _claude_version(claude: str) -> str:
    try:
        saida = subprocess.run(  # noqa: S603 -- executavel resolvido do PATH, argv fixo
            [claude, "--version"], capture_output=True, text=True, check=False, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    return saida.stdout.strip() or saida.stderr.strip()


def _run_question(
    claude: str,
    args: argparse.Namespace,
    suite: Suite,
    question: Question,
    destino: Path,
    workspace: Path,
) -> dict[str, object]:
    session = uuid.uuid4()
    comando = _command(claude, args, suite, question, str(session))
    registro: dict[str, object] = {"id": question.id, "session_id": str(session)}
    alvo_resultado = destino / f"{question.id}.result.json"
    alvo_transcript = destino / f"{question.id}.jsonl"
    if not (_inside(alvo_resultado, destino) and _inside(alvo_transcript, destino)):
        registro.update(status="host_failed", reason="destination_outside_run_dir")
        return registro
    try:
        resultado = subprocess.run(  # noqa: S603 -- argv de listas fechadas, sem shell
            comando,
            cwd=workspace,
            # Sem isto o `claude -p` espera stdin por ~3 s antes de ler o prompt
            # do argv (medido no smoke do executor de debate, 2026-09-11).
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        registro.update(status="host_failed", reason="timeout")
        return registro
    except OSError as exc:
        registro.update(status="host_failed", reason=f"exec: {exc}")
        return registro
    alvo_resultado.write_text(resultado.stdout or "", encoding="utf-8")
    registro["exit_code"] = resultado.returncode
    transcript = _persisted(session)
    if transcript is None:
        registro.update(status="host_failed", reason="session_file_not_found")
        return registro
    shutil.copyfile(transcript, alvo_transcript)
    registro["status"] = "ok" if resultado.returncode == 0 else "host_exit_nonzero"
    print(f"{question.id}: {registro['status']} -> {alvo_transcript}", flush=True)
    return registro


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not 1 <= args.repeat <= 50:
        raise SystemExit("--repeat precisa estar em [1, 50]")
    if not 1 <= args.timeout <= 7200:
        raise SystemExit("--timeout precisa estar em [1, 7200] segundos")
    invalidos = [q for q in args.only if not QUESTION_ID.fullmatch(q)]
    if invalidos:
        raise SystemExit(f"--only com id invalido: {invalidos}")
    suite = load_suite(SUITE_DIR)
    perguntas = [q for q in suite.questions if not args.only or q.id in args.only]
    if not perguntas:
        raise SystemExit("nenhuma pergunta selecionada")
    if _inside(OUT_BASE, ROOT):
        raise SystemExit(f"{OUT_BASE} fica dentro de {ROOT}; o repositorio nao guarda transcript")
    claude = _claude()

    if args.dry_run:
        for pergunta in perguntas:
            print(" ".join(_command(claude, args, suite, pergunta, "<uuid>")[:-1]) + " '<prompt>'")
        print(
            f"{len(perguntas)} pergunta(s) x {args.repeat} execucao(oes) em {OUT_BASE}; "
            f"superficie {args.surface}: {len(TOOLS) - len(_negadas(suite, args.surface))} "
            f"de {len(TOOLS)} tools MCP visiveis; nada foi executado."
        )
        return 0

    carimbo = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    versao = _claude_version(claude)
    workspace = _workspace(OUT_BASE / f"workspace-{carimbo}")
    conjunto = OUT_BASE / f"{suite.id}-{carimbo}"
    conjunto.mkdir(parents=True, exist_ok=False)
    for rodada in range(1, args.repeat + 1):
        run_id = f"{suite.id}-{carimbo}-r{rodada}"
        destino = OUT_BASE / run_id
        if not _inside(destino, OUT_BASE):
            raise SystemExit(f"diretorio de execucao fora de {OUT_BASE}: {destino}")
        destino.mkdir(parents=True, exist_ok=False)
        registros = [
            _run_question(claude, args, suite, q, destino, workspace) for q in perguntas
        ]
        (destino / "run.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "suite": {"id": suite.id, "sha256": suite.sha256},
                    "claude_version": versao,
                    "argv_template": _command(claude, args, suite, perguntas[0], "<uuid>")[:-1],
                    "started_utc": carimbo,
                    "surface": {
                        "arm": args.surface,
                        "mcp_tools_registered": len(TOOLS),
                        "mcp_tools_disallowed": len(_negadas(suite, args.surface)),
                    },
                    "workspace": {
                        "path": str(workspace),
                        "dirs": list(WORKSPACE_DIRS),
                        "files": list(WORKSPACE_FILES),
                        "excluded_names": sorted(SEM_GABARITO),
                    },
                    "questions": registros,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        scorecard = json.dumps(eval_grade(SUITE_DIR, destino), indent=2, ensure_ascii=False)
        (destino / SCORECARD).write_text(scorecard + "\n", encoding="utf-8")
        (conjunto / f"r{rodada}.json").write_text(scorecard + "\n", encoding="utf-8")
        print(f"run {run_id}: {destino / SCORECARD}", flush=True)
    print(
        f"conjunto {conjunto.name}: python -m sparkforge.evals compare --suite {suite.id} "
        f"--baseline <baseline> --candidate {conjunto.name}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
