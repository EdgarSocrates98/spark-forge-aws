"""Security — threat model e guardrails para o runtime agêntico.

Threat model:
- Prompt injection (external content hijacks agent instructions)
- Tool abuse (agent uses tool outside its scope)
- Agent impersonation (agent claims to be another)
- Privilege escalation (agent accesses tools it shouldn't)
- Memory poisoning (malicious data in memory)
- Evidence poisoning (fabricated evidence)
- Context poisoning (malicious context injected)
- Malicious artifacts (files designed to exploit)
- Cross-agent injection (agent A injects instructions into agent B)
- Untrusted tool output (tool returns malicious content)
- Secret leakage (secrets exposed in output)
- Cross-case contamination (memory from case A leaks to case B)

Guardrails:
1. Input validation
2. Relevance validation
3. Prompt-injection resistance
4. Tool authorization
5. Scope validation
6. Output validation
7. Schema validation
8. Policy validation
9. Version validation
10. Security validation
11. Human escalation

Deterministic validation before LLM-based validation wherever possible.
Agent messages are data, not system instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    TOOL_ABUSE = "tool_abuse"
    AGENT_IMPERSONATION = "agent_impersonation"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    MEMORY_POISONING = "memory_poisoning"
    EVIDENCE_POISONING = "evidence_poisoning"
    CONTEXT_POISONING = "context_poisoning"
    MALICIOUS_ARTIFACT = "malicious_artifact"
    CROSS_AGENT_INJECTION = "cross_agent_injection"
    UNTRUSTED_TOOL_OUTPUT = "untrusted_tool_output"
    SECRET_LEAKAGE = "secret_leakage"  # noqa: S105 - enum value, not a password
    CROSS_CASE_CONTAMINATION = "cross_case_contamination"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolRiskProfile:
    """Perfil de risco de uma tool.

    Determina se a tool requer:
    - additional validation
    - human approval
    - explicit policy
    """

    tool_name: str
    level: RiskLevel
    read_only: bool = True
    write: bool = False
    destructive: bool = False
    reversible: bool = True
    external_side_effect: bool = False
    financial_impact: bool = False
    security_impact: bool = False

    @property
    def requires_approval(self) -> bool:
        """High e critical operations require approval."""
        return self.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def requires_additional_validation(self) -> bool:
        """Medium+ operations require additional validation."""
        return self.level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)


@dataclass
class GuardrailResult:
    """Resultado de uma validação de guardrail."""

    passed: bool
    threat_type: ThreatType | None = None
    reason: str = ""
    blocked_content: str = ""


def validate_input(content: str) -> GuardrailResult:
    """Validação de input — determinística, antes de LLM.

    Detecta:
    - empty input
    - oversized input (>100KB)
    - binary content (null bytes)
    """
    if not content or not content.strip():
        return GuardrailResult(
            passed=False,
            reason="Input vazio.",
        )
    if len(content) > 100_000:
        return GuardrailResult(
            passed=False,
            reason=f"Input oversized: {len(content)} bytes > 100KB limit.",
        )
    if "\x00" in content:
        return GuardrailResult(
            passed=False,
            threat_type=ThreatType.MALICIOUS_ARTIFACT,
            reason="Input contém null bytes — possível conteúdo binário malicioso.",
        )
    return GuardrailResult(passed=True)


def detect_prompt_injection(content: str) -> GuardrailResult:
    """Detecta prompt injection em conteúdo externo.

    Heurística determinística: marcadores de instrução de sistema em conteúdo
    que deveria ser dado ("ignore previous instructions", "you are now",
    "new instructions:").

    O que esta função NÃO faz, e por quê: até 2026-09-03 ela também bloqueava
    "verbo imperativo + nome de serviço a menos de 50 caracteres". Medido
    contra o vocabulário deste produto, isso bloqueia conteúdo legítimo —
    "run the glue job novamente com 10 workers e delete os arquivos orfaos do
    S3" é uma recomendação normal do SparkForge e saía `passed=False`. Um
    guardrail que barra o caminho feliz é desligado pelo operador no primeiro
    dia, e aí não guarda nada. Detecção de intenção fica para validação
    LLM-based, que este módulo não faz.

    Esta é uma primeira linha de defesa, não a única.
    """
    if not content:
        return GuardrailResult(passed=True)

    content_lower = content.lower()

    # System instruction markers
    injection_markers = (
        "ignore previous instructions",
        "ignore all previous",
        "you are now",
        "system:",
        "act as",
        "pretend you are",
        "forget your instructions",
        "override your",
        "new instructions:",
    )
    for marker in injection_markers:
        if marker in content_lower:
            return GuardrailResult(
                passed=False,
                threat_type=ThreatType.PROMPT_INJECTION,
                reason=f"Prompt injection detectado: marker '{marker}' encontrado.",
                blocked_content=marker,
            )

    return GuardrailResult(passed=True)


def validate_agent_identity(
    claimed_agent_id: str,
    actual_agent_id: str,
) -> GuardrailResult:
    """Valida que um agente não está impersonando outro."""
    if claimed_agent_id != actual_agent_id:
        return GuardrailResult(
            passed=False,
            threat_type=ThreatType.AGENT_IMPERSONATION,
            reason=f"Agent {actual_agent_id!r} claiming to be {claimed_agent_id!r}.",
        )
    return GuardrailResult(passed=True)


def validate_tool_authorization(
    agent_id: str,
    tool_name: str,
    allowed_tools: list[str],
    denied_tools: list[str] | None = None,
) -> GuardrailResult:
    """Valida que um agente está autorizado a usar uma tool."""
    denied_tools = denied_tools or []

    if tool_name in denied_tools:
        return GuardrailResult(
            passed=False,
            threat_type=ThreatType.TOOL_ABUSE,
            reason=f"Tool {tool_name!r} está na deny list do agente {agent_id!r}.",
        )

    if allowed_tools and tool_name not in allowed_tools:
        return GuardrailResult(
            passed=False,
            threat_type=ThreatType.PRIVILEGE_ESCALATION,
            reason=f"Tool {tool_name!r} não está na allow list do agente {agent_id!r}.",
        )

    return GuardrailResult(passed=True)


# Segredo é chave COM VALOR, não a palavra sozinha. Até 2026-09-03 estes
# padrões eram substrings (`token=`, `private_key`, `AKIA`), e bloqueavam
# output legítimo deste produto: uma coluna chamada `private_key_column`, a
# prosa "token=" de um exemplo, `AKIA` dentro de qualquer palavra maiúscula.
# Cada padrão abaixo exige a forma do segredo, não a menção dele.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # AWS access key id: prefixo + 16 caracteres do alfabeto da AWS.
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    # Bloco PEM: a âncora é o delimitador inteiro, nunca a palavra "key".
    ("pem_private_key", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    # chave = valor, com valor plausível (>= 8 chars, sem espaço).
    (
        "secret_assignment",
        re.compile(
            r"(?i)\b(?:aws_secret_access_key|aws_session_token|secret_access_key|"
            r"password|passwd|api_key|apikey|access_token|auth_token|private_key)"
            r"\s*[:=]\s*[\"']?(?P<valor>[^\s\"',;]{8,})"
        ),
    ),
)

# Valor que não é segredo: placeholder, redação, variável de ambiente.
_SECRET_PLACEHOLDER = re.compile(
    r"(?i)^(?:<[^>]*>|\$\{[^}]*\}|\$[A-Z_]+|[*x]+|redacted.*|changeme|your[-_].*|"
    r"none|null|example.*|xxx.*)$"
)


def validate_output(content: str, expected_schema: dict[str, Any] | None = None) -> GuardrailResult:
    """Validação de output — determinística.

    Detecta:
    - secret leakage: chave com valor plausível, não a menção da palavra
      (ver `_SECRET_PATTERNS`); placeholder e variável de ambiente não contam
    - oversized output
    - schema mismatch (se schema declarado)
    """
    if not content:
        return GuardrailResult(passed=True)

    for nome, padrao in _SECRET_PATTERNS:
        for m in padrao.finditer(content):
            valor = m.groupdict().get("valor") if m.groupdict() else None
            if valor is not None and _SECRET_PLACEHOLDER.match(valor):
                continue
            return GuardrailResult(
                passed=False,
                threat_type=ThreatType.SECRET_LEAKAGE,
                reason=f"Secret leakage detectado: padrao '{nome}' no output.",
                blocked_content=nome,
            )

    # Oversized output
    if len(content) > 50_000:
        return GuardrailResult(
            passed=False,
            reason=f"Output oversized: {len(content)} bytes > 50KB limit.",
        )

    return GuardrailResult(passed=True)


def validate_cross_case_isolation(
    case_id: str,
    memory_case_id: str,
) -> GuardrailResult:
    """Valida que memória de um case não contamina outro."""
    if case_id != memory_case_id:
        return GuardrailResult(
            passed=False,
            threat_type=ThreatType.CROSS_CASE_CONTAMINATION,
            reason=f"Case {case_id!r} acessando memória do case {memory_case_id!r}.",
        )
    return GuardrailResult(passed=True)


@dataclass
class HumanApprovalRequest:
    """Pedido de aprovação humana.

    Enviado quando:
    - Critical actions
    - Destructive actions
    - High financial impact
    - High security impact
    - Production deployments
    - Low-confidence critical decisions
    - Unresolved contradictions
    """

    action: str
    risk_level: RiskLevel
    reasoning: str
    recommendation: str
    alternatives: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    disagreement: str = ""
    confidence: str = "low"
    risks: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    rollback: str = ""


def requires_human_approval(
    risk_level: RiskLevel,
    confidence: str = "high",
    is_destructive: bool = False,
    is_production: bool = False,
    has_unresolved_contradiction: bool = False,
) -> bool:
    """Determina se uma ação requer aprovação humana."""
    if risk_level == RiskLevel.CRITICAL:
        return True
    if is_destructive:
        return True
    if is_production and risk_level == RiskLevel.HIGH:
        return True
    if has_unresolved_contradiction:
        return True
    if risk_level == RiskLevel.HIGH and confidence == "low":
        return True
    return False
