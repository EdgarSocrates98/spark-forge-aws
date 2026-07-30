"""Superficie de ferramentas MCP da Fase 0. Nao importa o SDK do MCP.

`mcp.py` e a unica camada que fala com o SDK; este modulo so declara os
contratos (`TOOLS`) e despacha (`call_tool`) para `sparkforge.adapters._core`
-- as mesmas funcoes que a CLI usa. Isto garante que a CLI e o cliente MCP
nunca podem discordar sobre o que uma analise ou um julgamento devolve.

`outputSchema` em toda ferramenta e o ponto: um cliente MCP le
`structuredContent` sem reparsear texto, entao o contrato e identico sob
qualquer LLM. `sparkforge_rules_lookup` e `sparkforge_validate_output` sao o
nucleo da independencia de modelo -- ver as descricoes abaixo.

Nenhuma ferramenta da Fase 0 e destrutiva nem open-world: o nucleo e
offline, e coletores AWS ficam para a Fase 1. So `case_open` e `case_update`
escrevem em disco (`.sparkforge/case.yaml`); todas as outras sao read-only.
"""
from __future__ import annotations

from typing import Any

from sparkforge.adapters import _core

_OBJECT_SCHEMA: dict[str, Any] = {"type": "object"}

_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_WRITE_NOT_IDEMPOTENT = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": False,
}

_WRITE_IDEMPOTENT = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

TOOLS: dict[str, dict[str, Any]] = {
    "sparkforge_case_open": {
        "description": (
            "Cria um case novo em .sparkforge/case.yaml, detectando o runtime "
            "Glue/Spark/Python/Iceberg a partir dos parametros informados. E o barramento "
            "de handoff entre sessoes (Devin, Claude Code): sem case, next-step e resume "
            "nao tem estado sobre o qual operar. `now` e obrigatorio e nunca lido do relogio "
            "pela ferramenta -- quem chama fornece o timestamp."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "case_id", "now"],
            "properties": {
                "repo": {"type": "string", "description": "Raiz do repositorio analisado."},
                "case_id": {"type": "string"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
                "glue": {"type": "string"},
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _WRITE_IDEMPOTENT,
    },
    "sparkforge_case_get": {
        "description": (
            "Le o estado atual do case (.sparkforge/case.yaml): fase, gates, runtime "
            "detectado, indices de facts e findings. Falha com um erro que nomeia "
            "`sparkforge case open` quando nenhum case existe ainda no repositorio."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_case_update": {
        "description": (
            "Atualiza a fase, um gate booleano, ou registra o uso de uma skill no case "
            "atual. Cada mutacao e uma transicao de estado explicita e validada contra o "
            "dominio conhecido (PHASES, GATES) -- nunca um valor livre."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "phase": {"type": "string"},
                "gate": {"type": "string"},
                "gate_value": {"type": "boolean"},
                "skill": {"type": "string"},
                "now": {"type": "string"},
                "outcome": {"type": "string"},
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _WRITE_NOT_IDEMPOTENT,
    },
    "sparkforge_next_step": {
        "description": (
            "Decide o proximo passo (skill recomendada) a partir de routing.yaml -- o mesmo "
            "motor declarativo de sparkforge.rules.engine, mas sobre o estado do case e os "
            "achados atuais, nunca sobre o julgamento livre do agente. `blocked_by` e "
            "advisory: informa gates pendentes sem impedir a chamada."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "findings": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Findings atuais, usados para casar condicoes de roteamento.",
                },
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_resume": {
        "description": (
            "Monta o payload de rehidratacao de um case: onde parou, runtime, baseline, "
            "achados principais, hipoteses abertas, gates, artefatos ausentes e proximo "
            "passo. `coverage.unresolved` e um sinal de ponto cego, nao de ausencia de "
            "problema -- um no nao resolvido nunca deve ser lido como 'sem achados'."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "findings": {"type": "array", "items": {"type": "object"}},
                "unresolved": {"type": "integer"},
                "in_flight": {"type": "string"},
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_runtime_detect": {
        "description": (
            "Deriva glue/spark/python/iceberg/athena a partir dos parametros informados, "
            "usando a matriz oficial de compatibilidade do Glue. Divergencia entre fontes "
            "nao e resolvida escolhendo uma: e reportada em `divergences`, porque aplicar "
            "limiar ou API da versao errada invalida qualquer recomendacao seguinte."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "glue": {"type": "string"},
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_pyspark": {
        "description": (
            "Extrai facts deterministicos de codigo PySpark via AST estatico -- nunca "
            "importa nem executa o codigo analisado. So observa (particionamento, joins, "
            "UDFs, cache, acoes no driver, etc.); nao atribui severidade nem limiar. "
            "Paginado: `total_count`/`by_kind` refletem o conjunto completo apos filtros, "
            "nao so a pagina devolvida em `items`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Arquivo ou diretorio a analisar."},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_judge": {
        "description": (
            "Aplica o catalogo de regras versionado sobre facts ja extraidos, filtrado "
            "pelo runtime informado. Aceita `facts` inline ou `facts_path` (arquivo gerado "
            "por sparkforge_analyze_pyspark). Um `facts_path` ausente devolve um dict de "
            "erro com o comando de recoleta, nunca uma excecao. Regra fora de escopo de "
            "versao ou sem fact requerido aparece em `skipped` com o motivo, quando "
            "`show_skipped` e verdadeiro -- nunca descartada em silencio."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": {"type": "object"}},
                "facts_path": {"type": "string"},
                "glue": {"type": "string"},
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
                "severity": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "show_skipped": {"type": "boolean"},
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_rules_lookup": {
        "description": (
            "Consulta o catalogo de regras determinístico por id ou categoria, devolvendo "
            "threshold, runtime_scope e fontes completas. Este e o nucleo da independencia "
            "de modelo: o LLM nao precisa saber de cor o limiar ou a severidade de uma "
            "regra -- ele consulta o catalogo versionado e recebe sempre a mesma resposta, "
            "qualquer que seja o modelo por tras da chamada."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "array", "items": {"type": "string"}},
                "category": {"type": "string"},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_validate_output": {
        "description": (
            "Valida um finding proposto contra o JSON Schema e contra a regra de ganho sem "
            "benchmark_ref antes de aceita-lo. Este e o outro pilar da independencia de "
            "modelo: um LLM diferente pode redigir o finding de outra forma, mas so passa "
            "se for logicamente consistente com o catalogo -- a validacao decide o que e "
            "aceitavel, nao o modelo que escreveu."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["finding"],
            "properties": {"finding": {"type": "object"}},
        },
        "outputSchema": _OBJECT_SCHEMA,
        "annotations": _READ_ONLY,
    },
}


def _h_case_open(args: dict[str, Any]) -> dict[str, Any]:
    return _core.case_open(
        args["repo"],
        args["case_id"],
        args["now"],
        glue=args.get("glue"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
    )


def _h_case_get(args: dict[str, Any]) -> dict[str, Any]:
    return _core.case_get(args["repo"])


def _h_case_update(args: dict[str, Any]) -> dict[str, Any]:
    return _core.case_update(
        args["repo"],
        phase=args.get("phase"),
        gate=args.get("gate"),
        gate_value=args.get("gate_value", True),
        skill=args.get("skill"),
        now=args.get("now"),
        outcome=args.get("outcome"),
    )


def _h_next_step(args: dict[str, Any]) -> dict[str, Any]:
    return _core.next_step(args["repo"], args.get("findings") or [])


def _h_resume(args: dict[str, Any]) -> dict[str, Any]:
    return _core.resume_case(
        args["repo"],
        args.get("findings") or [],
        unresolved=args.get("unresolved", 0),
        in_flight=args.get("in_flight", ""),
    )


def _h_runtime_detect(args: dict[str, Any]) -> dict[str, Any]:
    return _core.runtime_detect(
        glue=args.get("glue"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
    )


def _h_analyze_pyspark(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_pyspark(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_judge(args: dict[str, Any]) -> dict[str, Any]:
    return _core.judge_findings(
        facts=args.get("facts"),
        facts_path=args.get("facts_path"),
        glue=args.get("glue"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
        severity=args.get("severity"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
        show_skipped=args.get("show_skipped", False),
    )


def _h_rules_lookup(args: dict[str, Any]) -> dict[str, Any]:
    return _core.rules_lookup(
        id=args.get("id"),
        category=args.get("category"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_validate_output(args: dict[str, Any]) -> dict[str, Any]:
    return _core.validate_output(args["finding"])


_HANDLERS = {
    "sparkforge_case_open": _h_case_open,
    "sparkforge_case_get": _h_case_get,
    "sparkforge_case_update": _h_case_update,
    "sparkforge_next_step": _h_next_step,
    "sparkforge_resume": _h_resume,
    "sparkforge_runtime_detect": _h_runtime_detect,
    "sparkforge_analyze_pyspark": _h_analyze_pyspark,
    "sparkforge_judge": _h_judge,
    "sparkforge_rules_lookup": _h_rules_lookup,
    "sparkforge_validate_output": _h_validate_output,
}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Despacha para o handler de `name`. Nome desconhecido: KeyError com as validas.

    Erros de fronteira (`_core.AdapterError`) nunca propagam como excecao: viram
    `{"error": ..., "exit_code": ...}`, para que um cliente MCP sempre receba um
    resultado estruturado, mesmo em falha.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        valid = ", ".join(sorted(TOOLS))
        raise KeyError(f"ferramenta desconhecida: {name!r}. Validas: {valid}")

    try:
        return handler(arguments or {})
    except _core.AdapterError as exc:
        return {"error": exc.message, "exit_code": exc.exit_code}
