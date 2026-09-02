"""Campo tipado como lista nunca e declarado como escalar no YAML.

## O defeito que este arquivo fecha

Medido em 2026-09-02: **11 de 111** regras declaravam `rollback:` como bloco
escalar (`rollback: >`) em vez de lista. O campo e consumido como lista, e YAML
nao reclama -- entao a string era **iterada caractere a caractere**.

A consequencia chegava ao operador. O golden de
`fixtures/controlm/capacidade_abaixo_da_fronteira` guardava:

    SF-CTM-001 | rollback com 354 itens de 1 caractere
    ['R', 'e', 'v', 'e', 'r', 't', 'e', 'r', ' ', 'o', ' ', 'c', 'o', 'm', ...]

Ou seja: quem lesse o `Finding` recebia lixo no campo que diz **como desfazer a
mudanca** -- o campo que mais importa quando algo deu errado.

## Por que um teste, e nao uma coercao no loader

Coagir string para `[string]` na carga faria o defeito sumir da saida e
sobreviver no YAML, e a proxima regra nasceria igual. O YAML e a fonte que uma
pessoa edita; e la que a forma precisa estar certa.

## As quatro listas

`proposed_change`, `risks`, `tradeoffs`, `validation` e `rollback` sao os campos
que o schema de `recommendation:` declara como lista (ver `rules/catalog/README.md`
e `sparkforge/findings/models.py`). `sources` tambem e lista, mas de mapa, e tem
guarda propria em `tests/test_rules_loader.py`.
"""

from __future__ import annotations

import pytest

from sparkforge.rules.loader import load_catalog

# Campos que o consumidor itera. String aqui vira iteracao de caracteres.
CAMPOS_DE_LISTA = ("proposed_change", "risks", "tradeoffs", "validation", "rollback")


@pytest.fixture(scope="module")
def catalogo() -> list[dict]:
    return list(load_catalog())


@pytest.mark.parametrize("campo", CAMPOS_DE_LISTA)
def test_campo_de_lista_nunca_e_string(catalogo, campo):
    """O contrafactual esta medido: em 2026-09-02 este teste reprovaria 11
    regras em `rollback`, e zero nos outros quatro."""
    escalares = [r["id"] for r in catalogo if isinstance(r.get(campo), str)]
    assert not escalares, (
        f"{len(escalares)} regra(s) declaram `{campo}` como escalar em vez de lista: "
        f"{sorted(escalares)}. O campo e ITERADO pelo consumidor, entao a string "
        f"vira uma lista de caracteres no `Finding` -- e o operador le lixo no "
        f"lugar da instrucao. Envolva o texto num item de lista (`- >`), "
        f"preservando-o; nao coaja no loader, ou o YAML continua errado."
    )


@pytest.mark.parametrize("campo", CAMPOS_DE_LISTA)
def test_item_de_campo_de_lista_e_string_nao_vazia(catalogo, campo):
    """Lista com item vazio e a segunda forma do mesmo defeito: passa no teste
    acima e ainda entrega nada ao operador."""
    problemas = []
    for regra in catalogo:
        valor = regra.get(campo)
        if not isinstance(valor, list):
            continue
        for i, item in enumerate(valor):
            if not isinstance(item, str) or not item.strip():
                problemas.append(f"{regra['id']}[{i}]={item!r}")
    assert not problemas, f"itens vazios ou nao-string em `{campo}`: {problemas}"


def test_rollback_vazio_e_declarado_e_nao_esquecido():
    """`rollback: []` e resposta legitima -- quando nao ha o que desfazer.

    A primeira versao deste teste exigia `rollback` nao-vazio em toda regra
    executavel, e reprovou `SF-PLAN-004`. Medido, a regra estava CERTA: ela nao
    propoe mudar nada, propoe NAO AFIRMAR estrategia de join sem o plano final e
    ADIAR a recomendacao de hint. Nao ha o que desfazer.

    Entao o invariante nao e "toda regra tem rollback". E: toda regra que propoe
    MUDANCA tem rollback -- e o proxy conferivel disso e a existencia de
    `validation` com eixo de resultado, que `tests/test_rules_result_axis.py` ja
    cobra separadamente.

    O que fica travado aqui e mais estreito e mais util: `rollback` vazio precisa
    ser LISTA VAZIA declarada, nunca chave ausente. Ausencia e esquecimento;
    lista vazia e decisao.
    """
    ausentes = [
        r["id"]
        for r in load_catalog()
        if r.get("executable", True) and "rollback" not in r
    ]
    assert not ausentes, (
        f"regra executavel sem a chave `rollback`: {sorted(ausentes)}. "
        f"Se nao ha o que desfazer, declare `rollback: []` -- lista vazia e "
        f"decisao, chave ausente e esquecimento."
    )
