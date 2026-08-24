"""A varredura unica dos extratores, com denylist e confinamento.

Catorze sitios de `rglob` faziam isto separadamente, e so tres pulavam sequer
`__pycache__`. Consolidar aqui e o que torna a fronteira auditavel: existe UM
lugar que decide o que o motor pode ler, e ele tem teste.

Fail-closed em toda decisao: symlink, arquivo especial, caminho de nome
sensivel e arquivo grande demais sao PULADOS, nunca lidos "so para ver". A
excecao e raiz inexistente, que e erro nomeado -- devolver lista vazia ali
pareceria "nao ha nada a analisar", quando o certo e "voce apontou para o lugar
errado".

As listas deste modulo sao DUAS, e acrescentar um nome a uma delas e uma
decisao diferente de acrescentar a outra:

- `DIRETORIOS_IGNORADOS` e CUSTO E RUIDO. `.venv`, `node_modules`, `build`,
  `dist`, os caches: arvore de dependencia e artefato, nao codigo do projeto
  analisado. Tirar um nome dali torna a varredura mais cara e mais barulhenta,
  e nada mais.
- `DIRETORIOS_SENSIVEIS`, `NOMES_SENSIVEIS`, `SUFIXOS_SENSIVEIS` e
  `PREFIXOS_SENSIVEIS` sao CREDENCIAL. `.pem`, `.key`, `credentials`, `.env`,
  `id_rsa`, `.tfstate`, `kubeconfig`, `.aws/`, `.ssh/`. Tirar um nome dali faz
  o motor ler segredo de cliente. Nenhuma allowlist de extensao pode reabilitar
  o que esta aqui -- e por isso a checagem de sensivel roda DEPOIS do
  casamento de padrao, nao antes.

O teto de tamanho tambem e DOIS, pelo mesmo tipo de razao. Um teto unico de
1 MiB ja esteve aqui e era defeito: ele vinha da regra de indexar codigo-fonte,
e esta varredura nao le so codigo. Ver `_teto_para`.

PENDENCIA REGISTRADA -- pular e silencioso. Arquivo descartado por tamanho,
por symlink ou por confinamento simplesmente nao aparece, e quem le a saida nao
distingue "nao havia nada" de "havia e eu nao li". Isso contraria o principio do
`unresolved` que a casa aplica em `graph.unresolved` e `sql.unresolved`: ponto
cego nao e ausencia de problema. Fechar depende de a varredura poder devolver
mais que caminho -- um `Iterator[Path]` nao comporta o sinal -- e isso e decisao
de design maior que este modulo. Nao ha gate aqui que pegue essa lacuna.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path


class ScanError(Exception):
    """Raiz inexistente, ilegivel, ou que nao e diretorio."""


# Arvore de dependencia, artefato de build e metadados de ferramenta. Nada aqui
# e codigo do projeto analisado, e tudo aqui e volumoso.
DIRETORIOS_IGNORADOS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        ".env",
        "site-packages",
        ".tox",
        ".nox",
        "node_modules",
        "bower_components",
        "vendor",
        "build",
        "dist",
        ".eggs",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
        ".gradle",
        "target",
        ".terraform",
        ".sparkforge",
    }
)

# Cofres de credencial de ferramenta. Separados dos ignorados acima porque a
# razao e outra: nao sao volumosos nem irrelevantes, sao proibidos. O nome do
# arquivo la dentro nao denuncia nada (`.ssh/chave.json` e um `*.json` comum),
# entao a unica defesa e podar a pasta.
DIRETORIOS_SENSIVEIS: frozenset[str] = frozenset(
    {".aws", ".ssh", ".gnupg", ".kube", ".docker", ".azure", ".gcloud"}
)

# Caminhos que NUNCA sao lidos, mesmo casando a extensao pedida. A allowlist de
# extensao nao pode reabilitar arquivo de credencial -- e por isso a checagem
# vem DEPOIS do casamento de padrao, nao antes.
NOMES_SENSIVEIS: frozenset[str] = frozenset(
    {"credentials", "secrets", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "kubeconfig"}
)
SUFIXOS_SENSIVEIS: tuple[str, ...] = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".tfstate",
    ".tfvars",
    ".npmrc",
    ".pypirc",
)
PREFIXOS_SENSIVEIS: tuple[str, ...] = (".env", "credentials", "secrets", ".netrc")

# Codigo-fonte: 1 MiB. A razao e parsing. Um `.py` de 1 MiB e gerado ou
# minificado, nao e codigo para ler, e montar AST de arquivo gigante e vetor de
# DoS. So entra aqui extensao que algum extrator realmente parseia por AST --
# hoje so `.py`. Conjunto minimo de proposito: extensao que ninguem parseia cair
# no teto de dados e o erro barato; artefato legitimo pulado e o caro.
EXTENSOES_CODIGO: frozenset[str] = frozenset({".py"})
TAMANHO_MAXIMO_CODIGO_BYTES = 1024 * 1024

# Artefato de dados: 128 MiB. O operador apontou para ele de proposito -- dump
# de listagem S3, plano de Terraform, metadados de Iceberg, event log -- e o
# teto existe para conter o patologico, nao para cortar o caso normal.
#
# Medido neste repositorio: uma listagem S3 custa 143 bytes por objeto, estavel
# em tres fixtures (1.5 mil, 10 mil e 100 mil objetos). A maior tem 13.64 MiB.
# 128 MiB comporta ~940 mil objetos num prefixo, 9x a maior medida. Parsear
# custa 2.6x o arquivo em RAM (medido com tracemalloc nas tres), entao 128 MiB
# tem pico de ~333 MiB -- pesado e sobrevivel. Dobrar o teto dobra o pico, e e
# ai que arquivo patologico deixa de ser lento e passa a derrubar o processo.
TAMANHO_MAXIMO_DADOS_BYTES = 128 * 1024 * 1024


def _teto_para(caminho: Path) -> int:
    """Teto por tipo de conteudo, porque a razao de cada um e diferente.

    Um teto unico de 1 MiB esteve aqui e era defeito: ele vinha da regra de
    indexar codigo-fonte, onde e protecao legitima contra parsear AST de
    arquivo gigante. Aplicado a artefato de dados, cortava o caso normal --
    as duas fixtures que provam os limiares P0 e P1 de small files passam de
    1 MiB, e a travessia devolvia zero fact sobre elas.

    Extensao desconhecida usa o teto de dados. Pular por engano um artefato
    legitimo e pior que ler um arquivo grande que nao interessa.
    """
    if caminho.suffix.lower() in EXTENSOES_CODIGO:
        return TAMANHO_MAXIMO_CODIGO_BYTES
    return TAMANHO_MAXIMO_DADOS_BYTES


def _e_sensivel(caminho: Path) -> bool:
    nome = caminho.name.lower()
    talo = caminho.stem.lower()
    if talo in NOMES_SENSIVEIS:
        return True
    # Todos os sufixos, nao so o ultimo: `terraform.tfstate.json` termina em
    # `.json` e um `endswith` sozinho o entregaria como JSON comum.
    if any(s.lower() in SUFIXOS_SENSIVEIS for s in caminho.suffixes):
        return True
    # `.npmrc` e `.pypirc` sao nome inteiro, nao sufixo: para o pathlib um
    # arquivo que so tem ponto inicial nao tem sufixo nenhum.
    if any(nome.endswith(s) for s in SUFIXOS_SENSIVEIS):
        return True
    return any(nome.startswith(p) for p in PREFIXOS_SENSIVEIS)


def iter_source_files(root: Path | str, pattern: str) -> Iterator[Path]:
    """Arquivos regulares sob `root` que casam `pattern`, em ordem estavel.

    A raiz e validada agora, nao no primeiro `next()`: quem chama sem iterar
    -- ou quem so mede `len` depois -- receberia silencio de um gerador
    preguicoso, e apontar para o lugar errado tem que doer na hora.

    A ordem e a ordenacao global por caminho, identica a `sorted(root.rglob())`
    que estes extratores usavam. `os.walk` visita por nivel, o que intercala
    subpasta e arquivo diferente; reordenar no fim e o que impede a troca de
    varredura de mexer em golden de extrator que nao reordena por conta.

    Os caminhos devolvidos preservam a grafia de `root` -- so o confinamento
    resolve links. Devolver o caminho resolvido quebraria o
    `relative_to(repo_root)` de quem chama sempre que a raiz for relativa.
    """
    raiz = Path(root).expanduser()
    if not raiz.exists():
        raise ScanError(f"raiz inexistente: {raiz}")
    if not raiz.is_dir():
        raise ScanError(f"raiz nao e diretorio: {raiz}")
    raiz_real = raiz.resolve()

    achados: list[Path] = []
    for pasta_atual, subpastas, arquivos in os.walk(raiz, followlinks=False):
        # Poda no lugar: os.walk respeita a mutacao e nem desce nas removidas.
        # Filtrar so no fim daria a mesma lista tendo pago para listar o
        # `.venv` inteiro, que e o custo que esta varredura existe para evitar.
        subpastas[:] = [
            d
            for d in subpastas
            if d not in DIRETORIOS_IGNORADOS and d.lower() not in DIRETORIOS_SENSIVEIS
        ]
        base = Path(pasta_atual)
        for nome in arquivos:
            caminho = base / nome
            if not caminho.match(pattern):
                continue
            if caminho.is_symlink() or not caminho.is_file():
                continue
            if _e_sensivel(caminho):
                continue
            try:
                if caminho.stat().st_size > _teto_para(caminho):
                    continue
                # Confinamento: mesmo com followlinks=False, um componente
                # intermediario pode ter sido substituido durante a varredura.
                real = caminho.resolve()
                if raiz_real != real and raiz_real not in real.parents:
                    continue
            except OSError:
                continue
            achados.append(caminho)
    return iter(sorted(achados))
