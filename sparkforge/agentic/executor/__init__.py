"""Executor agentico deterministico.

Roda DEPOIS de `judge`, sobre findings ja julgados, e produz `Claim`,
`Evidence`, `Contradiction`, `Unknown` e `Decision` no blackboard. Nao chama
provider nenhum -- a regra 23 do `CLAUDE.md` vale aqui igual: quem gasta token
e o host que executa os agents, e este pacote nao importa `anthropic`,
`openai`, `bedrock` nem `litellm`.

Nao reexporta nada ainda. `run_executor` entra aqui quando o motor existir;
reexportar antes disso quebraria `import sparkforge.agentic.executor` inteiro
para quem so quer `authority`.
"""

from __future__ import annotations
