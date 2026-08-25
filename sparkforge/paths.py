# sparkforge/paths.py
"""Confinamento de caminho: UMA implementacao, para todos os consumidores.

O algoritmo -- resolver o alvo debaixo de uma raiz ja resolvida e recusar o que
escapar dela -- estava escrito TRES vezes quando esta fase comecou:
`rules/loader.py:safe_catalog_file`, `knowledge_ref.py:safe_knowledge_file` e,
inline, dentro de `facts/scan.py:iter_source_files`. As duas primeiras eram
copia byte a byte uma da outra, com so o texto do erro mudando; a terceira e
uma variante de forma diferente (ver o paragrafo final).

Copiar de novo para a cadeia de autorizacao seria a QUARTA, e e exatamente a
familia de defeito que a fase J0 acabou de fechar para o detector de segredo:
la eram quatro copias, uma delas ja divergente, e a divergencia era muda. Uma
copia so precisa de UM autor apressado corrigindo `!=` para `not in` num
lugar e nao no outro para virar dois niveis de seguranca diferentes com o
mesmo nome.

Esta funcao devolve `None` em vez de levantar de proposito: quem chama e que
sabe qual excecao pertence ao dominio dele (`CatalogError`, `KnowledgeError`)
ou se o resultado nem e excecao, e sim uma `AuthorizationDecision` de recusa.
Uma excecao unica aqui obrigaria os tres a traduzir.

O que ela NAO absorve, e por que: a checagem inline de `iter_source_files` roda
dentro do laco de varredura, sobre uma raiz que ja foi resolvida uma vez fora
do laco, e devolve "pula este arquivo" -- nao "recusa esta chamada". Reescreve-la
para chamar aqui pagaria `Path(base).resolve()` por arquivo visitado, que e
justamente o custo que aquele modulo mede e evita. A sobreposicao e conceitual
e esta declarada; a fusao seria regressao de desempenho, nao limpeza.
"""
from __future__ import annotations

from pathlib import Path


def resolve_within(base: Path | str, target: Path | str) -> Path | None:
    """O caminho real de `target` sob `base`, ou `None` se ele escapa de `base`.

    `target` absoluto e aceito e verificado como qualquer outro: `Path.__truediv__`
    descarta o lado esquerdo quando o direito e absoluto, entao um `/etc/passwd`
    ou `C:\\Windows\\...` chega em `resolve()` como ele mesmo e cai fora da raiz.

    `resolve()` nos DOIS lados e o que faz a checagem valer contra symlink: sem
    resolver a raiz, uma raiz que ela mesma contenha `..` ou um link compararia
    contra um prefixo que nao existe no disco.

    `expanduser()` so na RAIZ, nunca no alvo, e isso e deliberado. A raiz vem de
    configuracao (variavel de ambiente, argumento de CLI), onde `~` e grafia
    normal e esperada. O alvo, nos consumidores de hoje, vem de dentro do
    codigo ou de fora do processo -- expandir `~` la significaria transformar
    `~/.aws/credentials` num caminho de verdade dentro desta funcao, e a
    decisao de aceitar essa expansao pertence a quem chama, nao a ela. Quem
    precisa recusar `~` recusa antes (ver `agents/autonomy.py`).

    Devolve o caminho JA RESOLVIDO, e nao o original: quem vai abrir o arquivo
    deve abrir o que foi verificado, e nao o texto que passou pela verificacao.
    """
    root = Path(base).expanduser().resolve()
    alvo = (root / Path(target)).resolve()
    if root != alvo and root not in alvo.parents:
        return None
    return alvo
