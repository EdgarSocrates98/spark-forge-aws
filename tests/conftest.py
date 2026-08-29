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
    """Isola o ledger de contexto compartilhado (`call_tool` E
    `economy_report`, os dois pelo MESMO `shared_ledger()`) do
    `.sparkforge/traces.db` real do repositorio durante toda a sessao de
    teste.

    POR QUE AQUI, E NAO NO PRODUTO. `sparkforge.observability.context_ledger.
    shared_ledger()` materializa o ledger do processo na primeira chamada que
    nao monkeypatcha o proprio ledger -- e o default e `.sparkforge/
    traces.db` relativo ao `cwd`, que ao rodar a suite E o repositorio.
    Achado do revisor, medido: rodar so `tests/test_adapters_tools.py` (99
    chamadas de `call_tool`, nenhuma monkeypatchando o ledger) gravou 188
    spans no banco real numa unica execucao. Isolamento e responsabilidade
    de quem TESTA, nao do produto -- nenhuma flag ou variavel de ambiente
    entra no codigo de producao so para o teste "saber" que esta sob teste.

    UM PONTO SO, DE PROPOSITO. Antes de `shared_ledger()` existir,
    `tools.py` guardava o seu proprio singleton e `_core.economy_report()`
    construia uma `ContextLedger()` independente -- esta fixture chegou a
    precisar substituir OS DOIS por nome. Com uma fonte so, substituir
    `context_ledger._SHARED_LEDGER` cobre os dois consumidores de uma vez.

    Testes que monkeypatcham `context_ledger._SHARED_LEDGER` sozinhos (a
    maioria de `tests/test_context_ledger.py`) continuam funcionando: o
    `monkeypatch` de escopo de funcao deles substitui este valor durante o
    teste e o `pytest` restaura o valor DESTA fixture ao fim -- nunca o
    `None` original, porque a substituicao aconteceu depois desta fixture
    rodar.
    """
    from sparkforge.observability import context_ledger

    db_path = tmp_path_factory.mktemp("observability") / "traces.db"
    context_ledger._SHARED_LEDGER = context_ledger.ContextLedger(
        db_path=db_path, run_id="run_suite_de_teste"
    )

    yield

    context_ledger._SHARED_LEDGER.flush(final=True)

    # BACKSTOP ESTRUTURAL. A substituicao acima cobre os pontos de entrada
    # CONHECIDOS (`shared_ledger()`), mas uma lista de nomes nunca e garantia
    # -- um terceiro ponto que um dia importe `ContextLedger` e a use por
    # conta propria escaparia dela, e nenhum teste acusaria. Este backstop
    # nao depende de saber QUEM construiu o ledger: verifica o EFEITO --
    # o `.sparkforge/traces.db` do repositorio simplesmente nao pode existir
    # ao fim da suite. Pega qualquer ponto novo, presente ou futuro.
    traces_do_repo = _ROOT / ".sparkforge" / "traces.db"
    assert not traces_do_repo.exists(), (
        f"{traces_do_repo} foi criado durante a suite -- algum ponto de "
        "codigo construiu ContextLedger() por fora de shared_ledger() e de "
        "qualquer db_path isolado de teste."
    )
