"""Forge Pack (§5): regras, knowledge e fixtures de terceiro, carregados junto do core.

Um pack e um diretorio com `pack.yaml` (`id`, `version`, `prefix`, `core`) e
conteudo em lugar fixo: `rules/*.yaml`, `knowledge/**`, `fixtures/<caso>/`. Ele
e ativado por `SPARKFORGE_PACKS` (diretorios separados por `os.pathsep`) e
entra em `rules.loader.load_catalog()`. O prefixo `SF` e do core; o prefixo do
pack e o que identifica a origem de um finding.

Fora daqui, por decisao: extrator, tool, agente ou skill de pack (so dado),
instalar ou publicar pack, dependencia entre packs, sobrescrever regra do core.
"""
from sparkforge.packs.load import ENV, Pack, PackSet, load_pack, pack_dirs, resolve
from sparkforge.packs.manifest import (
    RESERVED_PREFIX,
    Manifest,
    PackRefused,
    dentro_da_faixa,
    installed_version,
)

__all__ = [
    "ENV",
    "RESERVED_PREFIX",
    "Manifest",
    "Pack",
    "PackRefused",
    "PackSet",
    "dentro_da_faixa",
    "installed_version",
    "load_pack",
    "pack_dirs",
    "resolve",
]
