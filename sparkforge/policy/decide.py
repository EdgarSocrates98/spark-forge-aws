"""Decisao pura da policy sobre um comando, um caminho ou uma tool.

Regra de Bash casa o TEXTO do comando, nao o programa (a documentacao de
permissoes do Claude Code diz o mesmo: "isn't a security boundary around the
program"). `dividir_comando` cobre as formas que o agente costuma escrever --
composto, subshell, substituicao, `bash -c`, invólucros --; alias, script que
chama o programa por dentro e caminho absoluto do binario ficam de fora, e
isso esta declarado em `docs/harness/THREAT-MODEL.md` (T-024).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any

from sparkforge.policy.load import Politica, Regra

ALLOW, ASK, DENY = "allow", "ask", "deny"
_ORDEM = {DENY: 0, ASK: 1, ALLOW: 2}
_SEPARADORES = re.compile(r"&&|\|\||;|\||\n")
_SUBSTITUICAO = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
_SHELL_C = re.compile(r"^(?:bash|sh|zsh)\s+-c\s+(['\"])(.*)\1\s*$", re.DOTALL)
_ATRIBUICAO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_INVOLUCROS = {"sudo", "env", "nohup", "time", "command", "exec"}
_ESCRITA = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
            "NotebookEdit": "notebook_path"}


@dataclass(frozen=True)
class Decisao:
    decision: str
    rule: str | None = None
    reason: str | None = None
    subject: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"decision": self.decision, "rule": self.rule, "reason": self.reason,
                "subject": self.subject}


def _limpar(parte: str) -> str:
    tokens = parte.split()
    mudou = True
    while mudou and tokens:
        mudou = False
        while tokens and _ATRIBUICAO.match(tokens[0]):
            tokens.pop(0)
            mudou = True
        while tokens and tokens[0] in _INVOLUCROS:
            tokens.pop(0)
            mudou = True
        if tokens and tokens[0] == "timeout":
            tokens.pop(0)
            if tokens and re.match(r"^\d", tokens[0]):
                tokens.pop(0)
            mudou = True
    return " ".join(tokens)


def dividir_comando(comando: str) -> list[str]:
    """Os subcomandos que o shell executaria, na ordem em que aparecem."""
    pendentes = [comando]
    saida: list[str] = []
    while pendentes:
        atual = pendentes.pop(0)
        for grupo in _SUBSTITUICAO.findall(atual):
            pendentes.append(grupo[0] or grupo[1])
        atual = _SUBSTITUICAO.sub(" ", atual).replace("(", " ").replace(")", " ")
        for parte in _SEPARADORES.split(atual):
            segmento = _limpar(parte)
            if not segmento:
                continue
            embrulhado = _SHELL_C.match(segmento)
            if embrulhado:
                pendentes.append(embrulhado.group(2))
                continue
            if segmento not in saida:
                saida.append(segmento)
    return saida


def casa_comando(regra: str, segmento: str) -> bool:
    """Sintaxe do Claude Code: `terraform destroy *` casa com e sem argumentos."""
    if regra.endswith(" *") and segmento == regra[:-2]:
        return True
    return fnmatchcase(segmento, regra)


def casa_caminho(regra: str, relativo: str) -> bool:
    """`**/*.tf` casa na raiz tambem; `rules/catalog/**` casa em qualquer profundidade."""
    if fnmatchcase(relativo, regra):
        return True
    return regra.startswith("**/") and fnmatchcase(relativo, regra[3:])


def _mais_estrita(atual: Decisao, regra: Regra, sujeito: str) -> Decisao:
    if _ORDEM[regra.decision] < _ORDEM[atual.decision]:
        return Decisao(regra.decision, regra.rule, regra.reason, sujeito)
    return atual


def decidir_bash(comando: str, regras: tuple[Regra, ...] | list[Regra]) -> Decisao:
    decisao = Decisao(ALLOW)
    for segmento in dividir_comando(comando):
        for regra in regras:
            if casa_comando(regra.rule, segmento):
                decisao = _mais_estrita(decisao, regra, segmento)
    return decisao


def relativo_a(raiz: Path | str, caminho: str) -> str:
    alvo = Path(caminho)
    if alvo.is_absolute():
        try:
            return alvo.resolve().relative_to(Path(raiz).resolve()).as_posix()
        except (ValueError, OSError):
            return alvo.as_posix()
    return PurePosixPath(caminho.replace("\\", "/")).as_posix()


def decidir_caminho(
    caminho: str, regras: tuple[Regra, ...] | list[Regra], raiz: Path | str = "."
) -> Decisao:
    relativo = relativo_a(raiz, caminho)
    decisao = Decisao(ALLOW)
    for regra in regras:
        if casa_caminho(regra.rule, relativo):
            decisao = _mais_estrita(decisao, regra, relativo)
    return decisao


def decidir_tool(nome: str, classe: str | None, politica: Politica) -> Decisao:
    if nome in politica.denied:
        return Decisao(DENY, "tools.denied", "tool negada pela policy", nome)
    if nome in politica.ask_names:
        return Decisao(ASK, "tools.ask.names", "tool pede confirmacao", nome)
    if classe is not None and classe in politica.ask_classes:
        return Decisao(ASK, "tools.ask.classes", f"classe {classe} pede confirmacao", nome)
    return Decisao(ALLOW, subject=nome)


def decidir_entrada(entrada: dict[str, Any], politica: Politica, raiz: Path | str) -> Decisao:
    """A decisao para o stdin do `PreToolUse`: Bash pelo comando, escrita pelo caminho."""
    nome = str(entrada.get("tool_name") or "")
    argumentos = entrada.get("tool_input") or {}
    if nome == "Bash":
        return decidir_bash(str(argumentos.get("command") or ""), politica.bash)
    if nome in _ESCRITA:
        alvo = argumentos.get(_ESCRITA[nome])
        if isinstance(alvo, str) and alvo:
            return decidir_caminho(alvo, politica.paths, raiz)
    return Decisao(ALLOW, subject=nome)
