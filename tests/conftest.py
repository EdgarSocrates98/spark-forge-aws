"""Torna `scripts/` alcançável quando a suíte roda de fora do repositório.

**Quem quebrava sem isto:** `scripts/verify_wheel.py`, o gate de paridade do
artefato. Ele roda a suíte de golden a partir de um `cwd` fora do repositório,
com `PYTHONSAFEPATH=1` e `-o pythonpath=`, exatamente para que
`import sparkforge` venha do wheel instalado e não do diretório-fonte — sem
isso o gate compararia o repositório consigo mesmo. O efeito colateral é que
`scripts/` sai do `sys.path` junto, e `scripts/` **não vai no wheel**: ele é
andaime de teste, não parte do pacote. `tests/test_fixtures_golden_funcval.py`
importa `with_plan_ref` de lá, então a coleta parava com
`ModuleNotFoundError: No module named 'scripts'` antes de qualquer asserção
rodar — nos dois sistemas operacionais da matriz.

**Por que `append` e nunca `insert(0, ...)`:** a raiz entra no FIM do
`sys.path`, então `site-packages` continua vencendo para `sparkforge`. Este
caminho só resolve o que não existe no artefato. E o que impede isso de virar
teatro não é a ordem em si — configuração se perde em refactor — e sim
`tests/test_installed_provenance.py`, que roda no mesmo processo sob
`SPARKFORGE_VERIFY_INSTALLED=1` e falha se `sparkforge` tiver vindo do
diretório-fonte.

**Por que não copiar `with_plan_ref` para dentro do teste:** o docstring dele
declara a função pública de propósito, porque `plan_ref` derivado de dois
jeitos diverge em silêncio — é o defeito que a D-4c-22 recusou escrever à mão.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))
