"""SDD proprio do SparkForge: contrato conferivel dos artefatos de spec.

Logica pura. Nada aqui chama modelo (regra 23): o agente escreve o artefato, o
pacote confere o que da para conferir e recusa por nome o resto. O corpo em
prosa nunca e julgado.
"""

from __future__ import annotations

PHASES: tuple[str, ...] = ("explore", "define", "design", "plan", "build_report", "ship")
DEFAULT_ROOT = "docs/sdd"
