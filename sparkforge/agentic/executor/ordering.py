"""Ordem de aplicacao das acoes -- a decisao 4 da secao 5.4 do spec.

Ordenacao topologica sobre `depends_on`, mais duas restricoes derivadas:

1. acao com `direction: investigate` sobre um `target` vem ANTES de qualquer
   acao que mude aquele mesmo `target` -- medir antes de mexer;
2. duas acoes que compartilham eixo de `nature: measure` nao entram no mesmo
   run. Sai como restricao de SEQUENCIAMENTO com a razao nomeada, nunca como
   proibicao de aplicar.

## Por que a restricao 2 FILTRA por `nature: measure`, e a contradicao nao

As duas perguntas parecem a mesma e nao sao. `conflict.direct_conflicts` nao
filtra por eixo, e o registro de por que esta la (o filtro apagava o caso real
junto com o falso positivo).

Aqui o filtro e obrigatorio, e a razao e principiada, nao conveniencia: a
restricao existe por causa da regra 13 do `CLAUDE.md` -- aplicar no mesmo run
duas mudancas que movem a mesma MEDIDA torna o antes/depois inatribuivel, e
atribuir a melhora a uma delas exigiria o custo do run que nao aconteceu.

`correctness.write_result` esta em 33 das 112 e e `nature: risk`: ele diz *o
resultado pode se mover*, e nao e grandeza comparavel. Tratado como medida, o
maior grupo teria 33 regras -- isso e ruido, nao restricao. So com os eixos de
medida o maior grupo tem 10 (`runtime.wall_clock`). E duas mudancas que ambas
*podem alterar o resultado* nao tem o problema de atribuicao; o que elas exigem
e validacao funcional de cada uma, que e `funcval` e outro mecanismo.

## Por que ciclo nao vira ordem

Ordenar um ciclo produziria uma sequencia que PARECE decidida e nao e. A saida e
`order.unresolved` com os ids do ciclo e ordem vazia -- regra 20: recusa tem
nome, e a lacuna sai nomeada em vez de virar uma ordem arbitraria que ninguem
conseguiria auditar.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

# O texto que acompanha a restricao. Ele nomeia a razao (regra 13) e nao promete
# nada sobre o resultado de aplicar junto -- a restricao e sobre ATRIBUICAO, nao
# sobre risco tecnico de aplicar as duas.
_EXPLICACAO_DE_EIXO = (
    "as duas acoes movem a mesma medida; aplicadas no mesmo run, o antes/depois "
    "fica inatribuivel e atribuir a mudanca a uma delas exigiria o run que nao "
    "aconteceu"
)


def _action_kinds_path() -> Path:
    """Caminho default de `rules/catalog/action_kinds.yaml`.

    Mesma resolucao de `authority._authority_map_path`: `parents[3]` porque este
    arquivo esta em `sparkforge/agentic/executor/`.
    """
    return Path(__file__).resolve().parents[3] / "rules" / "catalog" / "action_kinds.yaml"


def load_measure_axes(path: Path | None = None) -> set[str]:
    """Os eixos declarados com `nature: measure` no vocabulario fechado.

    Arquivo ausente levanta `FileNotFoundError` em vez de devolver conjunto
    vazio, pela mesma disciplina de `authority.load_authority_map`: a lacuna que
    este codigo trata e eixo NAO DECLARADO como medida, nunca vocabulario
    desaparecido. Conjunto vazio desligaria a restricao inteira em silencio, e
    quem lesse o relatorio veria "nenhuma restricao" onde o certo era um erro.

    Eixo sem `nature` nao e medida. Nao e leniencia: `tests/
    test_rules_action_field.py` ja derruba o catalogo com eixo sem `nature` ou
    com `nature` fora de `{measure, risk}`, entao o gate falha primeiro e este
    modulo nunca ve o caso num repositorio saudavel. Aqui a leitura literal e a
    conservadora -- eixo que ninguem declarou como grandeza comparavel nao gera
    restricao de atribuicao.
    """
    alvo = Path(path) if path is not None else _action_kinds_path()
    documento = yaml.safe_load(alvo.read_text(encoding="utf-8-sig")) or {}
    eixos = documento.get("axes") or {}
    return {
        str(nome)
        for nome, corpo in eixos.items()
        if isinstance(corpo, dict) and corpo.get("nature") == "measure"
    }


def order_actions(
    findings: list[dict], eixos_de_medida: set[str] | None = None
) -> tuple[list[str], list[dict], dict]:
    """Ordem de aplicacao, restricoes de sequenciamento e a lacuna, se houver.

    Args:
        findings: findings julgados. So `rule_id` e `action` sao lidos; finding
            sem bloco `action` nao entra na ordem -- ele nao propoe mudanca.
        eixos_de_medida: os eixos `nature: measure`. `None` le
            `rules/catalog/action_kinds.yaml`. O parametro existe para o teste
            poder fixar o vocabulario sem depender do catalogo, e para quem tiver
            um vocabulario proprio nao precisar reescrever o arquivo.

    Returns:
        `(ordem, restricoes, unresolved)`.

        - `ordem`: `rule_id` na sequencia topologica, ou `[]` quando ha ciclo;
        - `restricoes`: `[{"axis", "rules", "reason", "explanation"}]`, ordenada
          por eixo. Cada entrada nomeia duas ou mais regras que movem a mesma
          medida;
        - `unresolved`: `{}` quando fecha, ou
          `{"reason": "order.unresolved", "cycle": [ids]}`.

    Duas ocorrencias da mesma regra sao dois findings e UMA acao: o `rule_id`
    entra uma vez so, com o primeiro bloco `action` visto. Repeti-lo na ordem
    mandaria aplicar a mesma mudanca duas vezes, e no grupo de eixo inflaria a
    contagem a ponto de uma regra sozinha virar "restricao" consigo mesma.

    Sem aresta, a ordem de entrada e preservada. Desempatar por ordem alfabetica
    seria igualmente deterministico e diria uma coisa a mais que nao e verdade:
    que `SF-A` vem antes de `SF-B` por alguma razao. A ordem de entrada nao
    afirma nada -- ela so nao inventa.

    As restricoes de eixo saem MESMO com ciclo. Elas nao dependem de ordem, e
    recusar as duas coisas juntas esconderia uma informacao que continua valida.
    """
    if eixos_de_medida is None:
        eixos_de_medida = load_measure_axes()

    acao_por_regra: dict[str, dict[str, Any]] = {}
    ordem_de_entrada: list[str] = []
    for finding in findings or []:
        if not isinstance(finding, dict):
            continue
        acao = finding.get("action")
        rule_id = str(finding.get("rule_id") or "").strip()
        if not rule_id or not isinstance(acao, dict) or not acao:
            continue
        if rule_id not in acao_por_regra:
            acao_por_regra[rule_id] = acao
            ordem_de_entrada.append(rule_id)

    arestas = _arestas(acao_por_regra, ordem_de_entrada)
    ordem, ciclo = _topologica(ordem_de_entrada, arestas)
    restricoes = _restricoes_de_eixo(acao_por_regra, ordem_de_entrada, eixos_de_medida)

    unresolved: dict[str, Any] = {}
    if ciclo:
        unresolved = {"reason": "order.unresolved", "cycle": ciclo}

    return ordem, restricoes, unresolved


def _arestas(
    acao_por_regra: dict[str, dict[str, Any]], ordem_de_entrada: list[str]
) -> set[tuple[str, str]]:
    """As arestas `antes -> depois`, das duas origens que as produzem.

    1. `depends_on`: a regra citada precisa vir antes da que a cita. Dependencia
       para regra AUSENTE do case e ignorada, e isso e escolha: `depends_on`
       nomeia quem vem antes SE as duas dispararem. Transforma-la em lacuna
       diria que falta medir alguma coisa, quando o que houve foi a outra regra
       nao casar com os facts.
    2. `investigate` sobre um `target` -> toda acao que MUDA aquele target.
       Dois `investigate` no mesmo alvo nao se ordenam entre si: nenhum dos dois
       precisa do outro, e inventar uma ordem ali seria a mesma arbitrariedade
       que o ciclo recusa.
    """
    presentes = set(acao_por_regra)
    arestas: set[tuple[str, str]] = set()

    for regra in ordem_de_entrada:
        for bruto in acao_por_regra[regra].get("depends_on") or []:
            dependencia = str(bruto).strip()
            if dependencia in presentes and dependencia != regra:
                arestas.add((dependencia, regra))

    investiga: dict[str, list[str]] = defaultdict(list)
    muda: dict[str, list[str]] = defaultdict(list)
    for regra in ordem_de_entrada:
        acao = acao_por_regra[regra]
        alvo = str(acao.get("target") or "").strip()
        if not alvo:
            continue
        destino = investiga if str(acao.get("direction") or "") == "investigate" else muda
        destino[alvo].append(regra)

    for alvo, medidores in investiga.items():
        for medidor in medidores:
            for mudanca in muda.get(alvo, ()):
                if medidor != mudanca:
                    arestas.add((medidor, mudanca))

    return arestas


def _topologica(
    nos: list[str], arestas: set[tuple[str, str]]
) -> tuple[list[str], list[str]]:
    """Kahn estavel na ordem de entrada. Devolve `(ordem, ciclo)`.

    Fechando sem ciclo, `ciclo` e `[]` e `ordem` tem todos os nos. Com ciclo,
    `ordem` sai VAZIA -- entregar o prefixo que deu para ordenar seria entregar
    meia sequencia com cara de sequencia inteira.
    """
    posicao = {no: i for i, no in enumerate(nos)}
    sucessores: dict[str, set[str]] = defaultdict(set)
    grau_de_entrada = dict.fromkeys(nos, 0)
    for antes, depois in arestas:
        sucessores[antes].add(depois)
        grau_de_entrada[depois] += 1

    prontos = sorted((no for no in nos if grau_de_entrada[no] == 0), key=posicao.get)
    ordem: list[str] = []
    while prontos:
        atual = prontos.pop(0)
        ordem.append(atual)
        novos: list[str] = []
        for seguinte in sucessores[atual]:
            grau_de_entrada[seguinte] -= 1
            if grau_de_entrada[seguinte] == 0:
                novos.append(seguinte)
        if novos:
            prontos = sorted(prontos + novos, key=posicao.get)

    if len(ordem) == len(nos):
        return ordem, []

    return [], _nos_em_ciclo(nos, sucessores)


def _nos_em_ciclo(nos: list[str], sucessores: dict[str, set[str]]) -> list[str]:
    """Os nos que estao EM ciclo, por componentes fortemente conexas (Tarjan).

    Chamar de ciclo tudo que sobrou do Kahn seria mais barato e diria uma coisa
    falsa: um no a JUSANTE do ciclo nao participa dele, so nao tem como ser
    ordenado enquanto o ciclo existir. Nomear o inocente junto faria quem lesse
    o relatorio procurar a aresta errada.

    Iterativo de proposito: o grafo vem do catalogo e nao ha limite declarado
    para a profundidade dele, e recursao aqui trocaria um ciclo de dados por um
    `RecursionError`.
    """
    indice: dict[str, int] = {}
    menor: dict[str, int] = {}
    na_pilha: set[str] = set()
    pilha: list[str] = []
    proximo = 0
    em_ciclo: set[str] = set()

    for raiz in nos:
        if raiz in indice:
            continue
        trabalho: list[tuple[str, list[str]]] = [(raiz, sorted(sucessores[raiz]))]
        indice[raiz] = menor[raiz] = proximo
        proximo += 1
        pilha.append(raiz)
        na_pilha.add(raiz)

        while trabalho:
            atual, restantes = trabalho[-1]
            if restantes:
                seguinte = restantes.pop()
                if seguinte not in indice:
                    indice[seguinte] = menor[seguinte] = proximo
                    proximo += 1
                    pilha.append(seguinte)
                    na_pilha.add(seguinte)
                    trabalho.append((seguinte, sorted(sucessores[seguinte])))
                elif seguinte in na_pilha:
                    menor[atual] = min(menor[atual], indice[seguinte])
                continue

            trabalho.pop()
            if trabalho:
                pai = trabalho[-1][0]
                menor[pai] = min(menor[pai], menor[atual])

            if menor[atual] == indice[atual]:
                componente: list[str] = []
                while True:
                    membro = pilha.pop()
                    na_pilha.discard(membro)
                    componente.append(membro)
                    if membro == atual:
                        break
                # Componente de um no so e ciclo apenas com auto-aresta.
                if len(componente) > 1 or atual in sucessores[atual]:
                    em_ciclo.update(componente)

    return sorted(em_ciclo)


def _restricoes_de_eixo(
    acao_por_regra: dict[str, dict[str, Any]],
    ordem_de_entrada: list[str],
    eixos_de_medida: set[str],
) -> list[dict]:
    """Grupos de duas ou mais regras que movem o mesmo eixo de medida.

    Eixo que so uma regra move nao restringe nada -- nao ha o que sequenciar. E
    eixo `nature: risk` nao entra: ver o cabecalho deste modulo para a medida que
    fechou a decisao.
    """
    por_eixo: dict[str, list[str]] = defaultdict(list)
    for regra in ordem_de_entrada:
        for bruto in acao_por_regra[regra].get("moves") or []:
            eixo = str(bruto).strip()
            if eixo in eixos_de_medida and regra not in por_eixo[eixo]:
                por_eixo[eixo].append(regra)

    return [
        {
            "axis": eixo,
            "rules": sorted(regras),
            "reason": "same_measure_axis",
            "explanation": _EXPLICACAO_DE_EIXO,
        }
        for eixo, regras in sorted(por_eixo.items())
        if len(regras) > 1
    ]
