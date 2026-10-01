"""Executor agentico deterministico.

Roda DEPOIS de `judge`, sobre findings ja julgados, e produz `Claim`,
`Evidence`, `Contradiction`, `Objection`, `Unknown`, `Experiment` e `Decision`
no blackboard. Nao chama provider nenhum -- a regra 23 do `CLAUDE.md` vale aqui
igual: quem gasta token e o host que executa os agents, e este pacote nao
importa `anthropic`, `openai`, `bedrock` nem `litellm`.

`run_executor` e a unica coisa reexportada. Os seis modulos que ele orquestra
(`authority`, `claims`, `conflict`, `ordering`, `unknowns`, `plan`) continuam
importaveis um a um: quem so quer classificar autoridade de fonte nao precisa
carregar o motor inteiro.
"""

from __future__ import annotations

from sparkforge.agentic.executor.run import run_executor

__all__ = ["run_executor"]
