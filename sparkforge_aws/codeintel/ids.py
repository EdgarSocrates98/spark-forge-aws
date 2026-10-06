"""Identidade deterministica de no do indice.

BLAKE2b e nao UUID porque o id precisa ser reproduzivel: reindexar um arquivo
que nao mudou tem que produzir os mesmos ids, senao a fase incremental nao
consegue distinguir "mudou" de "reindexado".

O separador `\\x00` entre campos existe para que ("ab","c") e ("a","bc") nao
colidam -- concatenar sem separador transformaria fronteira de campo em
ambiguidade. Ele e `\\x00` e nao `:` ou `|` porque esses aparecem em caminho e
em assinatura, e um separador que pode ocorrer dentro de um campo nao separa
nada.

A assinatura entra no id, entao ela precisa ser estavel entre versoes de
Python. Medido: `ast.unparse` devolve `conectar(usuario, senha='hunter2',
tentativas=3)`, caractere por caractere igual, em 3.10.20, 3.11.15 e 3.14.6.
"""

from __future__ import annotations

import hashlib

_SEPARADOR = "\x00"
_TAMANHO_DIGEST = 16

_MARCADOR = "<literal>"
_ABRE = "([{"
_FECHA = ")]}"
_ASPAS_TRIPLAS = ('"""', "'''")


def node_id(caminho: str, kind: str, nome_qualificado: str, assinatura: str) -> str:
    """Id estavel de um no, derivado dos campos que o identificam.

    `nome_qualificado` precisa ser mesmo QUALIFICADO -- `Pipeline.executar`, e
    nao `executar`. E ele que carrega a unicidade dentro de um arquivo, e quem
    o alimentar com o nome simples produz id repetido sem que nada acuse.

    Medido sobre os 5695 simbolos dos 369 arquivos versionados, com os outros
    tres campos iguais nos dois casos:

        nome simples      5608 ids distintos -- 134 simbolos colidindo
        nome qualificado  5695 ids distintos --   0 colidindo

    `adapters/platforms/targets.py` sozinho tem quatro `platform_name(self)` em
    quatro classes, indistinguiveis sem o prefixo da classe. Isto e contrato
    para quem chama, e nao algo que esta funcao possa conferir: ela recebe uma
    string e nao tem como saber se ela foi qualificada.
    """
    material = _SEPARADOR.join((caminho, kind, nome_qualificado, assinatura))
    digest = hashlib.blake2b(material.encode("utf-8"), digest_size=_TAMANHO_DIGEST)
    return f"node_{digest.hexdigest()}"


def normalizar_assinatura(assinatura: str) -> str:
    """Assinatura sem valor literal de default.

    `connect(password='hunter2')` vira `connect(password=<literal>)`. Nome e
    ordem dos parametros ficam: sao eles que fazem a assinatura valer a pena
    guardar. O que vem depois do parentese que fecha -- anotacao de retorno --
    tambem fica, porque faz parte da assinatura como um humano a le.

    Isto e um varredor com profundidade, e nao uma substituicao por expressao
    regular, porque valor de default nao e um token: ele pode abrir parentese,
    conter virgula dentro de aspas e aninhar outra chamada.

    Medido sobre os 433 defaults dos 369 arquivos `.py` versionados fora de
    `vendor/`, cada um isolado numa assinatura minima `f(p=<valor>)`:

        casamento por token unico   14 valores sobraram inteiros, 4 com string
        este varredor                0 valores sobraram

    Os 14 comecam todos com `(` -- `('SF-PY-001',)`, `('2026-07-29',)` -- e um
    casamento por token nao ancora em nenhum deles, entao nao substitui nada e
    devolve o valor intacto. O varredor consome o default ate a virgula de topo,
    que e onde ele de fato acaba.
    """
    abre = assinatura.find("(")
    if abre < 0:
        return assinatura

    saida = [assinatura[: abre + 1]]
    profundidade = 1
    pulando = False
    i = abre + 1
    tamanho = len(assinatura)

    while i < tamanho:
        caractere = assinatura[i]

        if caractere in "\"'":
            fim = _fim_da_string(assinatura, i)
            if not pulando:
                # String fora de default e anotacao (`x: 'DataFrame'`), nao valor.
                saida.append(assinatura[i:fim])
            i = fim
            continue

        if caractere in _ABRE:
            profundidade += 1
        elif caractere in _FECHA:
            profundidade -= 1
            if profundidade == 0:
                # Daqui em diante nao ha mais parametro: e anotacao de retorno.
                saida.append(assinatura[i:])
                return "".join(saida)

        if pulando:
            if profundidade == 1 and caractere == ",":
                pulando = False
                saida.append(caractere)
            i += 1
            continue

        if caractere == "=" and profundidade == 1 and assinatura[i + 1 : i + 2] != "=":
            saida.append(f"={_MARCADOR}")
            pulando = True
            i += 1
            continue

        saida.append(caractere)
        i += 1

    return "".join(saida)


def _fim_da_string(assinatura: str, inicio: int) -> int:
    """Indice logo apos a string literal que comeca em `inicio`.

    Aspas sao tratadas em bloco para que virgula e parentese DENTRO delas nao
    contem como fronteira de parametro nem mexam na profundidade -- se
    contassem, `a='x, hunter2'` teria o segredo reaparecendo como se fosse o
    proximo parametro.
    """
    abertura = assinatura[inicio : inicio + 3]
    if abertura not in _ASPAS_TRIPLAS:
        abertura = assinatura[inicio]

    i = inicio + len(abertura)
    tamanho = len(assinatura)
    while i < tamanho:
        if assinatura[i] == "\\":
            i += 2
            continue
        if assinatura.startswith(abertura, i):
            return i + len(abertura)
        i += 1
    return tamanho  # string sem fechamento: consome o resto, nunca vaza


__all__ = ["node_id", "normalizar_assinatura"]
