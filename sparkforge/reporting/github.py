"""Findings ja julgados, projetados para o GitHub: SARIF, resumo e anotacoes.

Tres saidas da MESMA projecao, para que nenhuma diga coisa diferente das outras:

* SARIF 2.1.0 para o Code Scanning, so com o que `locate.localizar` localizou;
* resumo em Markdown para o `$GITHUB_STEP_SUMMARY`, com TODOS os findings -- o
  que nao tem linha no repositorio sai numa secao propria, com o motivo;
* uma linha `::error|warning|notice ...::` por resultado do SARIF, que o GitHub
  transforma em anotacao no diff do PR.

Funcao pura: sem horario, sem caminho absoluto, ordem estavel. A mesma entrada
da os mesmos bytes, e e isso que deixa `fixtures/sarif/` ser golden byte a
byte.

O que fica de fora do SARIF de proposito:

* `partialFingerprints`: o `upload-sarif` o calcula a partir do fonte, e o
  GitHub so usa o `primaryLocationLineHash` (doc de SARIF do GitHub);
* `security-severity` e a tag `security`: as regras sao de performance e custo,
  e marca-las como seguranca as poria na contagem de vulnerabilidades.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sparkforge.reporting.locate import Localizado, Recusa, indice_de_callsites, localizar

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
)
INFORMATION_URI = "https://github.com/EdgarSocrates98/spark-forge-aws"

# Limites publicados pelo GitHub. Acima deles a saida RECUSA por nome
# (`limite_do_github`) em vez de truncar calada.
#   resultados exibidos por run: docs.github.com/.../sarif-support-for-code-scanning
#   step summary por step:       docs.github.com/.../workflow-commands (1 MiB)
LIMITE_RESULTADOS = 5000
LIMITE_SUMARIO_BYTES = 1_048_576

ORDEM_SEVERIDADE = ("P0", "P1", "P2", "P3", "P4")
LEVEL_POR_SEVERIDADE = {"P0": "error", "P1": "error", "P2": "warning", "P3": "note", "P4": "note"}
_COMANDO_POR_LEVEL = {"error": "error", "warning": "warning", "note": "notice"}


@dataclass(frozen=True)
class Projecao:
    sarif: dict[str, Any]
    summary: str
    annotations: tuple[str, ...]
    recusas: tuple[dict[str, Any], ...]
    total: int
    localizados: int
    gate: dict[str, Any]


# Escape dos workflow commands, conferido no fonte T2 (`actions/toolkit`,
# `packages/core/src/command.ts`: `escapeData` e `escapeProperty`). A pagina T1
# de workflow commands nao documenta o escape. Sem ele, um titulo com `::` ou
# quebra de linha poderia injetar OUTRO comando no log do workflow.
def _escape_dado(valor: str) -> str:
    return valor.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_propriedade(valor: str) -> str:
    return _escape_dado(valor).replace(":", "%3A").replace(",", "%2C")


def anotacao(level: str, uri: str, line: int, titulo: str, mensagem: str) -> str:
    """Uma linha de workflow command no formato `::cmd k=v,k2=v2::mensagem`."""
    propriedades = ",".join(
        f"{chave}={_escape_propriedade(valor)}"
        for chave, valor in (("file", uri), ("line", str(line)), ("title", titulo))
    )
    return f"::{_COMANDO_POR_LEVEL[level]} {propriedades}::{_escape_dado(mensagem)}"


def gate_disparou(severidades: Sequence[str], fail_on: str | None) -> bool:
    """`fail_on` P0 dispara com P0; P1 dispara com P0 ou P1. Sem `fail_on`, nunca."""
    if fail_on is None:
        return False
    limite = ORDEM_SEVERIDADE.index(fail_on)
    return any(ORDEM_SEVERIDADE.index(s) <= limite for s in severidades if s in ORDEM_SEVERIDADE)


def _mensagem(finding: Mapping[str, Any], local: Localizado | None = None) -> str:
    """Titulo, medida e, quando a linha veio de um callsite, a nota que diz de onde.

    A nota ("linha da acao X que originou o stage N (nao e a causa)") existe
    porque skew e spill nascem num join ou shuffle ANTES da acao: o alerta aponta
    onde o stage foi disparado, e dizer menos que isso seria afirmar causa.
    """
    titulo = str(finding.get("title") or finding.get("rule_id") or "")
    medido = finding.get("measured") or {}
    texto = titulo
    if medido:
        partes = ", ".join(f"{chave}={medido[chave]}" for chave in sorted(medido))
        texto = f"{titulo} (medido: {partes})"
    if local is not None and local.nota:
        texto = f"{texto} -- {local.nota}"
    return texto


def _lista_md(titulo: str, itens: Sequence[str]) -> list[str]:
    if not itens:
        return []
    return [f"**{titulo}**", "", *(f"- {item}" for item in itens), ""]


def _lista_texto(titulo: str, itens: Sequence[str]) -> list[str]:
    if not itens:
        return []
    return [f"{titulo}:", *(f"- {item}" for item in itens)]


def _regra(finding: Mapping[str, Any]) -> dict[str, Any]:
    rule_id = str(finding["rule_id"])
    blocos = (
        ("Mudanca proposta", list(finding.get("proposed_change") or [])),
        ("Validacao", list(finding.get("validation") or [])),
        ("Rollback", list(finding.get("rollback") or [])),
    )
    texto = [linha for nome, itens in blocos for linha in _lista_texto(nome, itens)]
    markdown = [linha for nome, itens in blocos for linha in _lista_md(nome, itens)]
    regra: dict[str, Any] = {
        "id": rule_id,
        "name": rule_id.replace("-", ""),
        "shortDescription": {"text": str(finding.get("title") or rule_id)},
        "fullDescription": {
            "text": str(finding.get("explanation") or finding.get("title") or rule_id).strip()
        },
        "defaultConfiguration": {"level": LEVEL_POR_SEVERIDADE[finding["severity"]]},
        "properties": {"precision": str(finding.get("confidence") or "medium")},
    }
    if texto:
        regra["help"] = {"text": "\n".join(texto), "markdown": "\n".join(markdown).strip()}
    url = next((s["url"] for s in finding.get("sources") or [] if s.get("url")), None)
    if url:
        regra["helpUri"] = str(url)
    return regra


def _resultado(finding: Mapping[str, Any], local: Localizado, indice: int) -> dict[str, Any]:
    regiao: dict[str, Any] = {"startLine": local.line}
    if local.col is not None:
        regiao["startColumn"] = local.col
    return {
        "ruleId": str(finding["rule_id"]),
        "ruleIndex": indice,
        "level": LEVEL_POR_SEVERIDADE[finding["severity"]],
        "message": {"text": _mensagem(finding, local)},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": local.uri, "uriBaseId": "%SRCROOT%"},
                    "region": regiao,
                }
            }
        ],
        "properties": {
            "evidence": list(finding.get("evidence") or []),
            "severity": finding["severity"],
            "status": str(finding.get("status") or ""),
        },
    }


def _celula(valor: Any) -> str:
    return str(valor).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def _sujeito(subject: Mapping[str, Any]) -> str:
    tipo = subject.get("type", "?")
    nome = subject.get("symbol") or subject.get("file") or ""
    return f"{tipo} `{nome}`" if nome else str(tipo)


def _chave_severidade(finding: Mapping[str, Any]) -> int:
    sev = finding.get("severity")
    return ORDEM_SEVERIDADE.index(sev) if sev in ORDEM_SEVERIDADE else len(ORDEM_SEVERIDADE)


def _sumario(
    total: Sequence[Mapping[str, Any]],
    no_sarif: Sequence[tuple[Mapping[str, Any], Localizado]],
    recusados: Sequence[tuple[Mapping[str, Any], str]],
    gate: Mapping[str, Any],
) -> str:
    cabecalho = [
        "# SparkForge: findings deste commit",
        "",
        "| Severidade | Findings | No Code Scanning | Sem localizacao no repositorio |",
        "|---|---|---|---|",
    ]
    for sev in ORDEM_SEVERIDADE:
        n = sum(1 for f in total if f.get("severity") == sev)
        if not n:
            continue
        loc = sum(1 for f, _ in no_sarif if f.get("severity") == sev)
        rec = sum(1 for f, _ in recusados if f.get("severity") == sev)
        cabecalho.append(f"| {sev} | {n} | {loc} | {rec} |")
    if gate["fail_on"] is None:
        cabecalho += ["", "**Gate:** desligado."]
    else:
        estado = "disparou" if gate["tripped"] else "ok"
        cabecalho += ["", f"**Gate:** `--fail-on {gate['fail_on']}`: {estado}."]

    corpo = ["", f"## No Code Scanning ({len(no_sarif)})", ""]
    if no_sarif:
        corpo += ["| Severidade | Regra | Local | Titulo |", "|---|---|---|---|"]
        for f, local in no_sarif:
            corpo.append(
                f"| {f['severity']} | {_celula(f['rule_id'])} | "
                f"`{_celula(local.uri)}:{local.line}` | {_celula(_mensagem(f, local))} |"
            )
    else:
        corpo.append("Nenhum finding com linha em arquivo do repositorio.")

    rodape = ["", f"## Sem localizacao no repositorio ({len(recusados)})", ""]
    linhas_recusa: list[str] = []
    if recusados:
        rodape += ["| Severidade | Regra | Motivo | Sujeito | Titulo |", "|---|---|---|---|---|"]
        for f, motivo in recusados:
            linhas_recusa.append(
                f"| {f['severity']} | {_celula(f['rule_id'])} | `{motivo}` | "
                f"{_celula(_sujeito(f.get('subject') or {}))} | {_celula(_mensagem(f))} |"
            )
    else:
        rodape.append("Todos os findings tem linha em arquivo do repositorio.")

    base = "\n".join(cabecalho + corpo + rodape)
    cabem: list[str] = []
    tamanho = len(base.encode("utf-8")) + 1
    reserva = 200
    for linha in linhas_recusa:
        custo = len(linha.encode("utf-8")) + 1
        if tamanho + custo + reserva > LIMITE_SUMARIO_BYTES:
            break
        cabem.append(linha)
        tamanho += custo
    partes = [base, *cabem]
    faltaram = len(linhas_recusa) - len(cabem)
    if faltaram:
        partes += [
            "",
            f"_{faltaram} linha(s) fora deste resumo: `limite_do_github` "
            f"({LIMITE_SUMARIO_BYTES} bytes por step summary)._",
        ]
    return "\n".join(partes) + "\n"


def projetar(
    findings: Sequence[Mapping[str, Any]],
    facts_por_id: Mapping[str, Mapping[str, Any]],
    raizes: Sequence[str],
    existe: Callable[[str], bool],
    *,
    versao: str,
    category: str | None = None,
    fail_on: str | None = None,
) -> Projecao:
    """A projecao inteira. `existe` recebe um caminho relativo a raiz do repositorio."""
    no_sarif: list[tuple[Mapping[str, Any], Localizado]] = []
    recusados: list[tuple[Mapping[str, Any], str]] = []
    callsites = indice_de_callsites(facts_por_id)
    for finding in findings:
        onde = localizar(finding, facts_por_id, raizes, existe, callsites)
        if isinstance(onde, Recusa):
            recusados.append((finding, onde.motivo))
        else:
            no_sarif.append((finding, onde))

    no_sarif.sort(key=lambda par: (par[1].uri, par[1].line, str(par[0]["rule_id"])))
    if len(no_sarif) > LIMITE_RESULTADOS:
        recusados += [(f, "limite_do_github") for f, _ in no_sarif[LIMITE_RESULTADOS:]]
        no_sarif = no_sarif[:LIMITE_RESULTADOS]
    recusados.sort(
        key=lambda par: (
            _chave_severidade(par[0]),
            str(par[0].get("rule_id")),
            par[1],
            _sujeito(par[0].get("subject") or {}),
        )
    )

    regras_por_id: dict[str, dict[str, Any]] = {}
    for finding, _ in sorted(no_sarif, key=lambda par: str(par[0]["rule_id"])):
        regras_por_id.setdefault(str(finding["rule_id"]), _regra(finding))
    ids = sorted(regras_por_id)
    indice = {rid: i for i, rid in enumerate(ids)}

    run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": "SparkForge",
                "semanticVersion": versao,
                "informationUri": INFORMATION_URI,
                "rules": [regras_por_id[rid] for rid in ids],
            }
        },
        "results": [
            _resultado(f, local, indice[str(f["rule_id"])]) for f, local in no_sarif
        ],
    }
    if category:
        run["automationDetails"] = {"id": f"{category}/"}
    sarif = {"$schema": SARIF_SCHEMA, "version": SARIF_VERSION, "runs": [run]}

    gate = {
        "fail_on": fail_on,
        "tripped": gate_disparou([str(f.get("severity")) for f in findings], fail_on),
    }
    annotations = tuple(
        anotacao(
            LEVEL_POR_SEVERIDADE[f["severity"]],
            local.uri,
            local.line,
            f"{f['rule_id']} {f['severity']}",
            _mensagem(f, local),
        )
        for f, local in no_sarif
    )
    recusas = tuple(
        {
            "rule_id": str(f.get("rule_id")),
            "severity": str(f.get("severity")),
            "reason": motivo,
            "subject_type": str((f.get("subject") or {}).get("type", "")),
        }
        for f, motivo in recusados
    )
    return Projecao(
        sarif=sarif,
        summary=_sumario(findings, no_sarif, recusados, gate),
        annotations=annotations,
        recusas=recusas,
        total=len(findings),
        localizados=len(no_sarif),
        gate=gate,
    )
