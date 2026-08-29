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

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))


@pytest.fixture(autouse=True, scope="session")
def _ledger_de_contexto_isolado_da_sessao_de_teste(tmp_path_factory):
    """Isola o ledger de contexto de `call_tool` E de `economy_report` do
    `.sparkforge/traces.db` real do repositorio durante toda a sessao de
    teste.

    POR QUE AQUI, E NAO NO PRODUTO. `sparkforge.adapters.tools._ledger()`
    materializa `_LEDGER` na primeira chamada de `call_tool` que nao
    monkeypatcha o proprio ledger -- e o default e `.sparkforge/traces.db`
    relativo ao `cwd`, que ao rodar a suite E o repositorio. Achado do
    revisor, medido: rodar so `tests/test_adapters_tools.py` (99 chamadas de
    `call_tool`, nenhuma monkeypatchando `_LEDGER`) gravou 188 spans no banco
    real numa unica execucao. Isolamento e responsabilidade de quem TESTA,
    nao do produto -- nenhuma flag ou variavel de ambiente entra no codigo de
    producao so para o teste "saber" que esta sob teste. Um autouse de sessao
    aqui, substituindo `tools._LEDGER` por um ledger apontado para um
    diretorio temporario, resolve sem tocar `context_ledger.py` nem
    `adapters/tools.py`.

    DOIS PONTOS DE ENTRADA, NAO UM. `sparkforge.adapters._core.economy_report`
    constroi o SEU PROPRIO `ContextLedger()`, sem `db_path` -- ela LE o que
    quer que esteja no `.sparkforge/traces.db` relativo ao `cwd`, por fora do
    singleton de `tools.py`. So isolar `tools._LEDGER` nao bastava: depois da
    correcao de `spans_of()` passar a materializar o store tambem para
    LEITURA (e nao so escrita), `sparkforge_economy_report` (chamado dentro
    de `tests/test_adapters_tools.py`, entre outros) passou a criar de
    verdade o `.sparkforge/traces.db` do repositorio so para checar que ele
    estava vazio -- medido, 20KB apos uma unica rodada. Por isso este fixture
    tambem substitui `_core.ContextLedger` por um `functools.partial` que
    fixa o MESMO `db_path` temporario: `economy_report()` continua chamando
    `ContextLedger()` sem argumento nenhum, e ainda assim cai no diretorio
    isolado.

    Testes que monkeypatcham `tools._LEDGER` sozinhos (a maioria de
    `tests/test_context_ledger.py`) continuam funcionando: o `monkeypatch`
    de escopo de funcao deles substitui este valor durante o teste e o
    `pytest` restaura o valor DESTA fixture ao fim -- nunca o `None`
    original, porque a substituicao aconteceu depois desta fixture rodar.
    """
    import functools

    from sparkforge.adapters import _core, tools
    from sparkforge.observability.context_ledger import ContextLedger

    db_path = tmp_path_factory.mktemp("observability") / "traces.db"
    tools._LEDGER = ContextLedger(db_path=db_path, run_id="run_suite_de_teste")

    _context_ledger_original = _core.ContextLedger
    _core.ContextLedger = functools.partial(ContextLedger, db_path=db_path)

    yield

    tools._LEDGER.flush(final=True)
    _core.ContextLedger = _context_ledger_original
