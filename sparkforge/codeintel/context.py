"""`ContextPack`: o objeto canonico da secao 55, montado sobre o indice local.

POR QUE ELE NAO E O QUARTO EMPACOTADOR
---------------------------------------
Este repositorio ja tem tres empacotadores de contexto, e o mapa
`docs/harness/CODEINTEL-GAP.md` recusa explicitamente um quarto que ignore os
tres. A recusa vale, e a justificativa de existir mesmo assim e por medicao, nao
por vontade -- os tres empacotam OUTRA COISA:

- `sparkforge/context/funnel.py:ContextFunnel` empacota TRECHO DE CODIGO-FONTE:
  `ContextChunk` e `(arquivo, conteudo, linha inicial, linha final, relevancia)`,
  deduplicado por hash do conteudo.
- `sparkforge/tools/context.py:pack_context` empacota MENSAGEM de agente:
  `(kind, content, source)`, priorizada por tipo.
- `sparkforge/agents/budget.py:select_context` empacota REGISTRO DE MEMORIA:
  dict arbitrario, pontuado por palavra da query dentro do JSON.

Nenhum dos tres tem campo de simbolo, de relacao, de lineage, de regra, de
runtime, de referencia nao resolvida ou de seguranca -- os sete campos que a
secao 55 exige. Nenhum dos tres sabe o que e um `node_id`. Empacotar simbolo
neles seria enfiar o dominio inteiro do indice dentro de um `content: str`, e a
saida deixaria de ser consultavel por campo, que e a razao de a secao 55 existir.

E A FRONTEIRA ONDE ELES SE ENCONTRARIAM ESTA DECLARADA
-------------------------------------------------------
Ha exatamente um campo em que este pacote e `ContextFunnel` fariam a mesma
coisa: `snippets`. Ele sai VAZIO aqui, sempre, e nao por esquecimento -- o ciclo
de vida de recuperacao de source da SPEC (ler faixa confinada, servir, e o
trecho sumir) nao existe neste repositorio, e a INV-010 proibe corpo de fonte
persistido. No dia em que esse ciclo existir, `snippets` deve ser preenchido
CONSUMINDO `ContextFunnel`, e nao por um empacotador de trecho escrito aqui.
Fica dito antes de acontecer porque e assim que a duplicacao entra: alguem
precisa de trecho, o campo existe vazio, e escrever quinze linhas parece mais
barato que ler o modulo que ja faz isso.

`lineage` DEIXOU DE SAIR VAZIO, E O PRECO DISSO FOI MEDIDO ANTES
-----------------------------------------------------------------
Ate esta fase `lineage` saia vazio ao lado de `snippets`, com a razao "nao
existe no de tabela no schema". A razao era verdadeira e a lacuna era real:
`codeintel.lineage` sabia ligar `bronze.vendas` a `gold.vendas` e o pacote nunca
lhe perguntava nada -- respondia lista vazia, que se le igual a "este job nao
move dado".

O caminho para fechar a lacuna nao era obvio, e a escolha saiu de medicao e nao
de gosto. `montar` recebe BANCO e nao raiz -- e `db.py` recusa gravar a raiz de
proposito, porque o caminho absoluto nomeia a maquina num artefato que pode ser
copiado. Entao havia duas saidas:

- DERIVAR na hora da consulta, lendo a fonte dos arquivos selecionados. Medido
  sobre este repositorio, para os 3 arquivos de um pacote tipico, passando pela
  MESMA fronteira de leitura que o indexador usa (`iter_source_files`, que e o
  unico lugar autorizado a decidir o que o motor le):

      varredura de `iter_source_files` sozinha   234 / 241 / 242 / 265 ms
      derivar linhagem de 3 arquivos             343 / 350 / 358 / 448 ms

  ~350 ms POR PACOTE, dominados pela varredura de arvore -- que se paga inteira
  para ler tres arquivos. E ainda exigiria uma raiz por parametro, o que faria
  a secao ficar sem resposta exatamente quando `montar` e chamado como esta
  desenhado, so com o banco.

- PERSISTIR na indexacao. Medido sobre este repositorio, tres rodadas:

      indexar antes desta fase          3.167 / 3.725 / 3.859 s
      `lineage.construir` na arvore     2.766 / 2.834 / 2.962 s
        dos quais `ast.parse`             0.586 / 0.608 / 0.635 s
        e a travessia                     1.908 / 2.038 / 2.672 s

  ~+2.8 s de UMA vez, e a consulta do pacote passa a ser um `SELECT` por
  `file_id` indexado.

Persistir ganhou porque o pacote e OBJETO DE CONSULTA: ele e montado uma vez por
pergunta de agente, e a indexacao uma vez por arvore. 350 ms multiplicados pelo
numero de perguntas contra 2.8 s multiplicados por um. O preco esta publicado na
docstring de `index.indexar`, e ele nao e pequeno -- e quase o dobro da
indexacao anterior.

MEDIDO E DESCARTADO: um pre-filtro por substring, que so construiria linhagem em
arquivo que mencione algum dos 63 metodos-gatilho, nao paga. 376 dos 404
arquivos desta arvore passam no filtro -- `read`, `write`, `table`, `path`,
`sort`, `limit` e `sample` aparecem em quase todo Python -- e o tempo com filtro
(2.721 / 2.785 / 3.828 s) e o mesmo sem ele. Fica registrado para que a ideia
nao volte como sugestao.

O QUE ESTE PACOTE NAO SABE DIZER
---------------------------------
`index.fresh` sai `None`, e nao `true`. O indice deste repositorio nao sabe
dizer que envelheceu: nao ha comparacao de `content_sha256` contra a arvore na
hora da consulta, nem `head` de git gravado. `true` seria afirmacao sem
medicao -- exatamente a classe de alegacao que `scripts/check_vnext_claims.py`
existe para recusar. `None` diz "nao medido", que e a verdade.
`test_index_fresh_e_nulo_porque_staleness_nao_e_medido` prende isso.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from sparkforge.codeintel import budget
from sparkforge.codeintel.db import abrir
from sparkforge.codeintel.graph import chamadores, chamados
from sparkforge.codeintel.ranking import Escore, Expansao, escore, expandir, ordenar
from sparkforge.codeintel.search import Achado, buscar, resumo

SCHEMA_VERSION = 1

# Quantos termos da expansao chegam a virar consulta. `buscar` abre e fecha uma
# conexao por chamada, entao o custo e linear no numero de termos, e a expansao
# de uma pergunta com tres clusters passa de vinte termos. Os primeiros sao os
# literais (`Expansao.termos` garante a ordem), entao cortar aqui sacrifica
# termo derivado, nunca a palavra que a pessoa escreveu.
TERMOS_MAXIMOS = 12

# Candidatos por termo. `buscar` exige TODOS os tokens do termo (o espaco e AND
# implicito no FTS5), e cada termo aqui e uma palavra so, entao o limite e o que
# impede uma palavra comum -- `test`, `table` -- de trazer o indice inteiro.
CANDIDATOS_POR_TERMO = 20

# Quantos candidatos viram ancora da travessia de grafo. Cada semente custa duas
# consultas (chamadores e chamados), e a proximidade so muda a ordem dos
# vizinhos diretos dela -- ancorar em vinte candidatos pintaria o conjunto
# inteiro de proximidade e o componente pararia de discriminar.
SEMENTES = 3

# Quantos simbolos do topo viram ponto de entrada. A secao 54 protege "entry
# point principal", no singular; os tres primeiros aparecem separados dos demais
# porque e sobre eles que a travessia de grafo e as relacoes sao construidas, e
# so o PRIMEIRO e irredutivel.
ENTRY_POINTS = 3

# Teto da lista de referencias nao resolvidas, aplicado ja no `LIMIT` da
# consulta. A maioria das referencias deste indice nao resolve, e
# `UNKNOWN_RECEIVER` domina o motivo: sem teto, um unico pacote sairia com
# milhares de linhas de um mesmo motivo repetido, e o custo apareceria em
# memoria antes de aparecer no orcamento. O numero absoluto anda com a arvore e
# nao esta escrito aqui -- `Resultado.nao_resolvidas` de `indexar` o mede. O
# TOTAL continua em `metrics.unresolved_total`, que e o aviso que a secao 54
# protege; este teto corta a AMOSTRA, nunca o aviso.
UNRESOLVED_MAXIMO = 20

_AVISO_DE_CONFIANCA = "untrusted_repository_content"

# Dois campos so podem ser escritos DEPOIS da reducao: `reductions`, que nao
# existe antes de a reducao acontecer, e `estimated_tokens`, que so descreve o
# que sai se for medido sobre o que sai. Os dois CRESCEM o pacote depois de ele
# ja ter passado no teto -- `"estimated_tokens":0` vira `"estimated_tokens":4210`
# e `"reductions":[]` vira uma lista de nomes -- e um teto que nao reservasse
# esse espaco seria um teto que estoura no ultimo passo, exatamente na saida.
#
# A reserva e o PIOR CASO calculado dos proprios dados, e nao um numero redondo:
# a lista completa de passos mais oito digitos de estimativa. Derivar em vez de
# fixar e o que impede a reserva de envelhecer quando `ORDEM_DE_REDUCAO` mudar.
_PIOR_CASO_DE_REDUCAO = [*budget.ORDEM_DE_REDUCAO, "ultimo_recurso"]
# 16 = oito digitos para `estimated_tokens` e oito para `over_budget_bytes`, que
# sao os dois campos que `_fixar_metricas_do_posfixo` escreve depois do corte.
_RESERVA_DE_POSFIXO = (
    len(budget.serializar({"r": _PIOR_CASO_DE_REDUCAO}))
    - len(budget.serializar({"r": []}))
    + 16
)

_SQL_UNRESOLVED = (
    "SELECT unresolved_refs.reference_name, unresolved_refs.reference_kind,"
    "       unresolved_refs.reason, files.path, unresolved_refs.line"
    "  FROM unresolved_refs"
    "  JOIN files ON files.id = unresolved_refs.file_id"
    " WHERE files.path IN ({marcadores})"
    " ORDER BY files.path, unresolved_refs.line,"
    "          unresolved_refs.reference_name, unresolved_refs.id"
    " LIMIT ?"
)

_SQL_UNRESOLVED_TOTAL = (
    "SELECT COUNT(*)"
    "  FROM unresolved_refs"
    "  JOIN files ON files.id = unresolved_refs.file_id"
    " WHERE files.path IN ({marcadores})"
)

# As duas metades do fluxo de dado dos arquivos selecionados. Ordem TOTAL nas
# duas, e nao so por linha: dois fluxos podem partilhar arquivo e linha (uma
# cadeia com dois elos escritos na mesma linha e o caso comum), e sem o
# desempate a ordem passaria a ser a que o SQLite achou mais barata -- um teste
# de assinatura de bytes falharia de forma INTERMITENTE.
_SQL_DATA_FLOW = (
    "SELECT files.path, data_flow.source_name, data_flow.source_kind,"
    "       data_flow.source_resolved, data_flow.target_name,"
    "       data_flow.target_kind, data_flow.target_resolved,"
    "       data_flow.operation, data_flow.scope, data_flow.line,"
    "       data_flow.confidence"
    "  FROM data_flow"
    "  JOIN files ON files.id = data_flow.file_id"
    " WHERE files.path IN ({marcadores})"
    " ORDER BY files.path, data_flow.line, data_flow.source_name,"
    "          data_flow.target_name, data_flow.id"
)

_SQL_DATA_FLOW_BLIND = (
    "SELECT files.path, data_flow_blind_spots.reason,"
    "       data_flow_blind_spots.template, data_flow_blind_spots.variables,"
    "       data_flow_blind_spots.operation, data_flow_blind_spots.line"
    "  FROM data_flow_blind_spots"
    "  JOIN files ON files.id = data_flow_blind_spots.file_id"
    " WHERE files.path IN ({marcadores})"
    " ORDER BY files.path, data_flow_blind_spots.line,"
    "          data_flow_blind_spots.reason, data_flow_blind_spots.id"
)

# Os dois discriminadores da secao `lineage`. Uma lista so, com o tipo na
# propria entrada, e nao dois campos irmaos: o que o pacote sabe do fluxo e o
# que ele se recusou a adivinhar sobre o MESMO fluxo tem que chegar juntos a
# quem le. Separados, uma secao `lineage` cheia ao lado de uma
# `lineage_blind_spots` que ninguem olhou se le como linhagem completa -- e e
# exatamente por isso que `GrafoDeDados` guarda `nao_resolvidos` como campo do
# grafo em vez de lista jogada fora.
_FLUXO = "flow"
_RECUSA = "blind_spot"

# Fluxo cuja ponta e um dataset -- a leitura e a escrita, "de que tabela veio
# esta tabela". Fluxo entre dois DataFrames e o CAMINHO entre as duas, e e ele
# que `secondary_lineage` sacrifica primeiro. Ver `_redutores`.
_KIND_DATASET = "dataset"


@dataclass(frozen=True)
class ContextPack:
    """O objeto da secao 55, ja dentro do orcamento.

    Campos como tupla e nao lista porque o pacote e RESULTADO: a reducao ja
    aconteceu quando ele existe, e uma lista mutavel convidaria quem le a
    acrescentar item depois do corte -- o pacote passaria do teto que ele
    acabou de respeitar, e nada mediria de novo.
    """

    query: dict[str, Any]
    index: dict[str, Any]
    entry_points: tuple[dict[str, Any], ...]
    symbols: tuple[dict[str, Any], ...]
    relationships: tuple[dict[str, Any], ...]
    lineage: tuple[dict[str, Any], ...]
    rules: tuple[dict[str, Any], ...]
    runtime: dict[str, Any]
    snippets: tuple[dict[str, Any], ...]
    unresolved: tuple[dict[str, Any], ...]
    security: dict[str, Any]
    metrics: dict[str, Any]
    reductions: tuple[str, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def para_dicionario(self) -> dict[str, Any]:
        """As chaves exatas da secao 55, mais `reductions`.

        `reductions` e extensao DECLARADA, e nao esquecimento de fidelidade: a
        secao 54 exige uma ordem de reducao, e um pacote que encolheu sem dizer
        o que caiu transforma corte em perda de evidencia silenciosa -- o mesmo
        defeito que `pack_context` evita com o campo `truncated`. Tupla vazia
        quando nada foi reduzido, para que a chave exista sempre e quem consome
        nao precise de `get`.
        """
        return {
            "schema_version": self.schema_version,
            "query": dict(self.query),
            "index": dict(self.index),
            "entry_points": [dict(item) for item in self.entry_points],
            "symbols": [dict(item) for item in self.symbols],
            "relationships": [dict(item) for item in self.relationships],
            "lineage": [dict(item) for item in self.lineage],
            "rules": [dict(item) for item in self.rules],
            "runtime": dict(self.runtime),
            "snippets": [dict(item) for item in self.snippets],
            "unresolved": [dict(item) for item in self.unresolved],
            "security": dict(self.security),
            "metrics": dict(self.metrics),
            "reductions": list(self.reductions),
        }


def _simbolo(achado: Achado, pontos: Escore) -> dict[str, Any]:
    """Um simbolo na forma que sai no pacote.

    `score` inteiro e a quebra por componente juntos: o total ordena, e a quebra
    e o que responde POR QUE ele veio nesta posicao sem reler o codigo do escore.
    """
    return {
        "node_id": achado.node_id,
        "name": achado.name,
        "qualified_name": achado.qualified_name,
        "kind": achado.kind,
        "path": achado.path,
        "start_line": achado.start_line,
        "score": pontos.total,
        "score_breakdown": {
            "exact_name": pontos.exact_name,
            "qualified_name": pontos.qualified_name,
            "fts": pontos.fts,
            "path": pontos.path,
            "graph": pontos.graph,
            "domain": pontos.domain,
            "entrypoint": pontos.entrypoint,
            "lineage": pontos.lineage,
        },
    }


def _candidatos(
    banco: str | os.PathLike[str],
    expansao: Expansao,
    limite: int,
) -> dict[str, tuple[Achado, int]]:
    """`{node_id: (achado, melhor posicao no FTS)}`, na ordem em que apareceram.

    A MENOR posicao vence quando o mesmo no aparece na busca de mais de um
    termo, e nao a ultima: aparecer no topo de qualquer termo e o sinal, e
    deixar o ultimo termo sobrescrever faria a ordem depender de qual palavra a
    pessoa escreveu por ultimo.
    """
    encontrados: dict[str, tuple[Achado, int]] = {}
    for termo in expansao.termos[:TERMOS_MAXIMOS]:
        for posicao, achado in enumerate(buscar(banco, termo, limite)):
            anterior = encontrados.get(achado.node_id)
            if anterior is None or posicao < anterior[1]:
                encontrados[achado.node_id] = (achado, posicao)
    return encontrados


def _profundidades(
    banco: str | os.PathLike[str],
    sementes: list[str],
) -> dict[str, int]:
    """`{node_id: menor profundidade}` a partir das sementes, um salto.

    Um salto so, nas duas direcoes. `impacto` faria travessia transitiva e
    devolveria raio, que e outra pergunta -- aqui a proximidade so precisa
    separar "vizinho direto de uma semente" de "o grafo nunca viu". O peso da
    secao 49 ja decai por salto, e um segundo salto acrescentaria custo de
    consulta para mover o candidato cinco pontos.
    """
    perto: dict[str, int] = {}
    for semente in sementes:
        perto[semente] = 0
    for semente in sementes:
        for vizinho in list(chamados(banco, semente)) + list(chamadores(banco, semente)):
            if perto.get(vizinho.node_id, 99) > 1:
                perto[vizinho.node_id] = 1
    return perto


def _relacoes(
    banco: str | os.PathLike[str],
    entradas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """As arestas de chamada que tocam os pontos de entrada, em ordem estavel.

    Sai deduplicada por `(source_id, target_id, kind)`: `f(g(), g())` sao duas
    arestas em `edges` de proposito -- a contagem de chamadas mentiria sem isso
    -- mas no pacote de contexto a mesma ligacao repetida gasta byte sem
    acrescentar informacao, e byte e o que o orcamento conta.
    """
    vistas: set[tuple[str, str, str]] = set()
    saida: list[dict[str, Any]] = []
    for entrada in entradas:
        origem = entrada["node_id"]
        for alvo in chamados(banco, origem):
            chave = (origem, alvo.node_id, "calls")
            if chave in vistas:
                continue
            vistas.add(chave)
            saida.append(
                {
                    "source": entrada["qualified_name"],
                    "source_id": origem,
                    "target": alvo.qualified_name,
                    "target_id": alvo.node_id,
                    "kind": "calls",
                }
            )
        for chamador in chamadores(banco, origem):
            chave = (chamador.node_id, origem, "calls")
            if chave in vistas:
                continue
            vistas.add(chave)
            saida.append(
                {
                    "source": chamador.qualified_name,
                    "source_id": chamador.node_id,
                    "target": entrada["qualified_name"],
                    "target_id": origem,
                    "kind": "calls",
                }
            )
    return sorted(saida, key=lambda r: (r["source"], r["target"], r["source_id"], r["target_id"]))


def _nao_resolvidos(
    banco: str | os.PathLike[str],
    caminhos: list[str],
) -> tuple[list[dict[str, Any]], int]:
    """Referencias que o resolvedor nao fechou nos arquivos selecionados.

    Devolve a amostra e o TOTAL, e os dois numeros sao diferentes de proposito:
    a amostra cabe no orcamento, o total e o aviso. Sem o total, um pacote com
    vinte linhas de nao resolvido pareceria ter vinte pontos cegos quando tem
    milhares, e a secao 54 protege exatamente esse aviso.

    Caminho entra por marcador `?`, nunca interpolado -- e `path` do proprio
    indice, mas a regra da secao 30 nao tem excecao por procedencia.
    """
    if not caminhos:
        return [], 0
    marcadores = ",".join("?" * len(caminhos))
    conexao = abrir(banco)
    try:
        (total,) = conexao.execute(
            _SQL_UNRESOLVED_TOTAL.format(marcadores=marcadores), tuple(caminhos)
        ).fetchone()
        linhas = conexao.execute(
            _SQL_UNRESOLVED.format(marcadores=marcadores),
            (*caminhos, UNRESOLVED_MAXIMO),
        ).fetchall()
    finally:
        conexao.close()
    amostra = [
        {
            "reference_name": linha[0],
            "reference_kind": linha[1],
            "reason": linha[2],
            "path": linha[3],
            "line": linha[4],
        }
        for linha in linhas
    ]
    return amostra, int(total)


def _linhagem(
    banco: str | os.PathLike[str],
    caminhos: list[str],
) -> tuple[list[dict[str, Any]], int, int]:
    """O fluxo de dado dos arquivos selecionados, e o que nele nao tem nome.

    Devolve `(entradas, total de fluxos, total de recusas)`. Os dois totais sao
    devolvidos separados da lista pela mesma razao que em `_nao_resolvidos`: a
    lista cabe no orcamento e o total e o aviso. Um pacote que mostrasse tres
    fluxos de um job de quarenta e cinco pareceria descrever o job inteiro.

    A ORDEM DA LISTA E A PRIORIDADE DO CORTE, porque `cortar_por_bytes` corta
    por PREFIXO. Ela e, nesta ordem:

    1. RECUSA -- o nome que se tentou resolver e nao deu;
    2. fluxo que toca dataset -- a leitura e a escrita, que e a pergunta
       ("de que tabela veio esta tabela") que a secao 37 desenha;
    3. fluxo entre dois DataFrames -- o caminho, que e detalhe.

    A recusa vir PRIMEIRO nao e simetria com nada; e conserto de um defeito
    medido. Com ela em segundo lugar, a fatia de 15% da secao 53 -- 810 bytes
    sobre o orcamento padrao de 5400 -- cortava exatamente ela: os tres fluxos
    primarios de uma carga simples custam 245 + 244 + 242 = 731 bytes, e a
    recusa de 158 bytes nao cabia nos 79 que sobravam. O pacote saia com tres
    fluxos e nenhum aviso de que uma quarta tabela existe e nao tem nome, que e
    a leitura errada que este subsistema inteiro existe para impedir.

    E ela e a entrada mais BARATA das tres (158 bytes contra ~245), entao
    poe-la na frente custa menos fluxo do que qualquer outra ordem custaria de
    aviso.

    NAO HA TRAVESSIA AQUI, e a ausencia e escolha. `montante`, `jusante` e
    `linhagem_de_tabela` atravessam ARQUIVO, e para isso precisam do grafo
    inteiro em memoria -- que e onde eles ja estao escritos e testados.
    Reconstruir a travessia em SQL para o pacote daria uma segunda
    implementacao da mesma pergunta, e a divergencia entre as duas nao
    levantaria nada. O que se consulta daqui e "que fluxo existe NESTES
    arquivos", que e varredura por `file_id` e nao travessia.

    Caminho entra por marcador `?`, nunca interpolado -- e `path` do proprio
    indice, mas a regra da secao 30 nao tem excecao por procedencia.
    """
    if not caminhos:
        return [], 0, 0
    marcadores = ",".join("?" * len(caminhos))
    conexao = abrir(banco)
    try:
        fluxos = conexao.execute(
            _SQL_DATA_FLOW.format(marcadores=marcadores), tuple(caminhos)
        ).fetchall()
        recusas = conexao.execute(
            _SQL_DATA_FLOW_BLIND.format(marcadores=marcadores), tuple(caminhos)
        ).fetchall()
    finally:
        conexao.close()

    primarios: list[dict[str, Any]] = []
    secundarios: list[dict[str, Any]] = []
    for linha in fluxos:
        entrada = {
            "kind": _FLUXO,
            "source": linha[1],
            "source_kind": linha[2],
            "source_resolved": bool(linha[3]),
            "target": linha[4],
            "target_kind": linha[5],
            "target_resolved": bool(linha[6]),
            "operation": linha[7],
            "scope": linha[8],
            "path": linha[0],
            "line": linha[9],
            "confidence": linha[10],
        }
        if _KIND_DATASET in (linha[2], linha[5]):
            primarios.append(entrada)
        else:
            secundarios.append(entrada)

    cegos = [
        {
            "kind": _RECUSA,
            "reason": linha[1],
            "template": linha[2],
            # `variables` volta a ser lista aqui e nao fica como o JSON gravado:
            # quem consome o pacote leria uma string onde a secao 55 promete
            # estrutura, e precisaria desserializar de novo para usar.
            "variables": json.loads(linha[3]),
            "operation": linha[4],
            "path": linha[0],
            "line": linha[5],
        }
        for linha in recusas
    ]
    return [*cegos, *primarios, *secundarios], len(fluxos), len(cegos)


def _redutores(protegidas: set[tuple[str, str]]) -> dict[str, Any]:
    """Os redutores da secao 54 que este pacote sabe aplicar, por nome do passo.

    Tres dos sete passos da `ORDEM_DE_REDUCAO` tinham redutor aqui; agora sao
    quatro, e os tres que continuam de fora seguem registrados:

    - `comments` e `docstrings`: o pacote nao carrega corpo de codigo. A INV-010
      proibe corpo de fonte persistido, e `snippets` sai vazio (ver a docstring
      do modulo). Nao ha comentario nem docstring no que sai daqui para cortar.
    - `snippet_context_lines`: mesma razao, uma camada acima -- sem trecho, nao
      ha linha de contexto de trecho.

    Registrar um redutor que devolvesse sempre `False` para esses tres teria o
    mesmo efeito em execucao e o efeito oposto na leitura: pareceria que a
    reducao tentou e nao rendeu, quando na verdade nao ha o que reduzir.

    `secondary_lineage` ESTAVA nessa lista, com a razao "nao existe no de tabela
    no schema". A razao deixou de valer quando `data_flow` entrou em `db.py`, e
    o passo passou a ter trabalho -- ver `_sacrificar_fluxo_secundario`.

    `protegidas` sao as arestas que tocam o ponto de entrada principal.
    `low_score_edges` para nelas e `graph_depth` e quem as leva -- e por isso
    que os dois passos existem separados em vez de um esvaziar a lista inteira e
    deixar o outro sem trabalho para sempre.
    """

    def tirar_no_de_menor_escore(pacote: dict[str, Any]) -> bool:
        """Tira o simbolo de menor escore, e so entao encosta nos pontos de entrada.

        A lista ja esta em ordem decrescente de escore, entao o ultimo E o de
        menor escore -- reordenar aqui seria refazer o trabalho de `ordenar` com
        um criterio que podia divergir dele.

        Depois de `symbols` esvaziar, este passo continua nos pontos de entrada
        DE TRAS PARA A FRENTE ate sobrar um. A secao 54 protege "entry point
        principal", no singular: parar com tres pontos de entrada intocados
        deixaria o passo sem trabalho justamente quando a busca devolve poucos
        candidatos -- e ai todo candidato vira ponto de entrada e a reducao nao
        teria mais o que sacrificar antes de desistir. O primeiro nunca cai.
        """
        simbolos = pacote["symbols"]
        if simbolos:
            simbolos.pop()
            return True
        entradas = pacote["entry_points"]
        if len(entradas) > 1:
            entradas.pop()
            return True
        return False

    def tirar_aresta_de_menor_escore(pacote: dict[str, Any]) -> bool:
        relacoes = pacote["relationships"]
        for indice in range(len(relacoes) - 1, -1, -1):
            chave = (relacoes[indice]["source_id"], relacoes[indice]["target_id"])
            if chave not in protegidas:
                relacoes.pop(indice)
                return True
        return False

    def colapsar_profundidade(pacote: dict[str, Any]) -> bool:
        if not pacote["relationships"]:
            return False
        pacote["relationships"] = []
        return True

    def sacrificar_fluxo_secundario(pacote: dict[str, Any]) -> bool:
        """Larga o CAMINHO do dado antes das pontas, e a recusa por ultimo.

        A ordem de sacrificio e o inverso da ordem de valor, e ela e:

        1. fluxo entre dois DataFrames -- os quarenta `withColumn` no meio de
           uma carga sao detalhe do caminho, e as pontas ja o descrevem;
        2. fluxo que toca dataset -- a leitura e a escrita, de tras para a
           frente, que e como `low_score_nodes` ja corta;
        3. nada. A RECUSA NAO CAI AQUI.

        A recusa nao cair e o ponto inteiro deste passo. `spark.table(f"{db}.{t}")`
        e uma leitura que existe e cujo nome nao se pode saber, e um redutor que
        esvaziasse a secao jogaria fora o aviso junto com o detalhe -- o mesmo
        erro que `_ultimo_recurso` evita ao trocar a lista de nao resolvidas
        pela contagem em vez de apagar as duas. Quando so restam recusas este
        passo devolve `False` e a reducao segue para o proximo, que e o
        comportamento correto: nao ha mais lineage secundario, e insistir aqui
        seria apagar evidencia para caber.

        `metrics.lineage_flows_total` e `metrics.lineage_blind_spots_total`
        sobrevivem a tudo isto, e sao eles que dizem quanto foi cortado.
        """
        linhagem = pacote["lineage"]
        for indice in range(len(linhagem) - 1, -1, -1):
            if linhagem[indice]["kind"] != _FLUXO:
                continue
            if linhagem[indice]["source_kind"] != _KIND_DATASET:
                if linhagem[indice]["target_kind"] != _KIND_DATASET:
                    linhagem.pop(indice)
                    return True
        for indice in range(len(linhagem) - 1, -1, -1):
            if linhagem[indice]["kind"] == _FLUXO:
                linhagem.pop(indice)
                return True
        return False

    return {
        "low_score_nodes": tirar_no_de_menor_escore,
        "low_score_edges": tirar_aresta_de_menor_escore,
        "graph_depth": colapsar_profundidade,
        "secondary_lineage": sacrificar_fluxo_secundario,
    }


def _ultimo_recurso(pacote: dict[str, Any]) -> bool:
    """Larga o DETALHE das nao resolvidas, e nunca o aviso.

    A secao 54 diz que o aviso de nao resolvido nao cai ANTES dos sete passos --
    nao que ele nao caia nunca. Depois de a ordem inteira ser gasta a
    alternativa e `OrcamentoImpossivel`, e a concessao minima e trocar a lista
    pela contagem: `metrics.unresolved_total` sobrevive, e um total diferente de
    zero E o aviso. Ponto de entrada principal, procedencia e bloco de seguranca
    continuam intocados.
    """
    if not pacote["unresolved"]:
        return False
    pacote["unresolved"] = []
    return True


def _fixar_metricas_do_posfixo(corpo: dict[str, Any], orcamento: int) -> None:
    """Escreve `estimated_tokens` e `over_budget_bytes` ate os dois pararem de mudar.

    OS DOIS SE MEDEM A SI MESMOS, E E POR ISSO QUE ISTO E UM LACO.
    `estimated_tokens` e medido sobre o corpo inteiro, que inclui o campo
    `estimated_tokens`; escrever `4210` onde havia `0` acrescenta tres bytes ao
    corpo, e o numero certo passa a ser outro. `over_budget_bytes` tem o mesmo
    problema, uma casa adiante. Escrever uma vez so devolve um numero que ja
    estava errado no instante em que foi escrito.

    O laco e LIMITADO em quatro voltas, e nao `while True`, porque um laco sem
    teto sobre uma funcao que se realimenta e um travamento esperando um caso
    que ninguem previu. Quatro e folga larga: escrever um numero maior so pode
    aumentar o corpo, aumentar o corpo so pode aumentar o numero, e a largura de
    um inteiro cresce em log -- do zero inicial ate um valor que cabe no teto
    duro sao poucas trocas de largura.

    O teto tem um custo, e ele fica dito: se as quatro voltas se esgotarem sem
    igualdade, a funcao sai com um numero MENOR que o real, calada. E por isso
    que `test_metricas_do_posfixo_convergem` compara o campo com o tamanho final
    medido, sobre varios orcamentos, em vez de so verificar que a funcao rodou.
    Um dia em que quatro nao bastem aparece la, e nao em producao.

    `over_budget_bytes` existe porque o orcamento pedido e ALVO e o teto duro e
    que e limite. Quando o nucleo irredutivel -- ponto de entrada principal,
    procedencia, seguranca, aviso de nao resolvido -- ja passa do alvo, a
    alternativa seria devolver um pacote sem o que a secao 54 manda preservar. O
    excedente sai NO PACOTE em vez de calado: zero e o caso normal, e diferente
    de zero e a unica forma de quem pediu 800 bytes descobrir que recebeu mais.
    """
    for _ in range(4):
        estimativa = budget.estimar_tokens(corpo)
        excedente = max(0, budget.tamanho_em_bytes(corpo) - orcamento)
        if (
            corpo["metrics"]["estimated_tokens"] == estimativa
            and corpo["metrics"]["over_budget_bytes"] == excedente
        ):
            return
        corpo["metrics"]["estimated_tokens"] = estimativa
        corpo["metrics"]["over_budget_bytes"] = excedente


def montar(
    banco: str | os.PathLike[str],
    tarefa: str,
    *,
    task_type: str = "code_understanding",
    max_bytes: int | None = None,
    regras: tuple[dict[str, Any], ...] = (),
    runtime: dict[str, Any] | None = None,
    dicionario: str | None = None,
) -> ContextPack:
    """O `ContextPack` da secao 55 para `tarefa`, sobre o indice em `banco`.

    O pipeline e o da secao 50, com os degraus que este repositorio sustenta:
    normalizar, expandir pelo dicionario, recuperar candidatos do FTS, reordenar
    pelo escore composto, ancorar no grafo, ler o fluxo de dado dos arquivos
    selecionados, e caber no orcamento. O degrau que ele ainda nao sustenta --
    carregamento seguro de trecho -- sai como campo vazio, nunca como campo
    inventado.

    `lineage` sai com as duas metades juntas: o fluxo que o indice ligou e a
    recusa do que ele nao pode nomear. Nome de tabela montado em execucao
    continua sendo `DYNAMIC_TABLE_IDENTIFIER` com o template de buracos
    preservados, e nunca um palpite -- ver `_linhagem`.

    `regras` e `runtime` entram por parametro e nao sao descobertos aqui: o
    motor de regras deste repositorio consome FATO e o indice devolve SIMBOLO, e
    ligar os dois e decisao de outra fase. Aceitar os dois como entrada deixa o
    pacote completo para quem ja os tem, sem este modulo fingir uma integracao
    que nao existe.

    Levanta `budget.OrcamentoImpossivel` se nem o nucleo irredutivel couber no
    teto duro -- ver a docstring daquela excecao sobre por que falhar fechado.
    """
    orcamento = budget.normalizar_orcamento(max_bytes)
    expansao = expandir(tarefa, dicionario=dicionario)
    encontrados = _candidatos(banco, expansao, CANDIDATOS_POR_TERMO)

    # Primeira passada SEM grafo, so para escolher a ancora. Ancorar antes de
    # pontuar exigiria escolher semente por posicao do FTS sozinha, que e o
    # criterio que o escore composto existe para melhorar.
    preliminar = [
        (achado, escore(achado, expansao, posicao_fts=posicao))
        for achado, posicao in encontrados.values()
    ]
    sementes = [achado.node_id for achado, _ in ordenar(preliminar)[:SEMENTES]]
    perto = _profundidades(banco, sementes)

    pontuados = ordenar(
        [
            (
                achado,
                escore(
                    achado,
                    expansao,
                    posicao_fts=posicao,
                    profundidade_no_grafo=perto.get(achado.node_id),
                ),
            )
            for achado, posicao in encontrados.values()
        ]
    )

    # A secao 53 reparte o orcamento por categoria, e o corte por categoria
    # acontece AQUI, antes da reducao da secao 54. As duas nao sao redundantes:
    # a alocacao impede que uma categoria gulosa -- a lista de nao resolvidas e
    # a pior delas -- coma a fatia das outras, e a reducao trata do que sobrar
    # quando a soma das fatias ainda nao couber.
    fatias = budget.alocar(orcamento)

    simbolos = [_simbolo(achado, pontos) for achado, pontos in pontuados]
    entradas = budget.cortar_por_bytes(
        simbolos[:ENTRY_POINTS], fatias["entry_points"], minimo=1
    )
    restantes = budget.cortar_por_bytes(simbolos[len(entradas) :], fatias["symbols"])

    relacoes = budget.cortar_por_bytes(_relacoes(banco, entradas), fatias["relationships"])
    protegidas = set()
    if entradas:
        principal = entradas[0]["node_id"]
        protegidas = {
            (r["source_id"], r["target_id"])
            for r in relacoes
            if principal in (r["source_id"], r["target_id"])
        }

    caminhos = sorted({item["path"] for item in entradas})
    nao_resolvidas, total_nao_resolvidas = _nao_resolvidos(banco, caminhos)
    # A fatia de procedencia da secao 53 e 5%, e a lista de nao resolvidas e a
    # categoria mais gulosa que existe aqui -- a maioria das referencias deste
    # indice nao resolve. Sem este corte, a lista sozinha comeria a fatia de
    # simbolo e de relacao, e a reducao da secao 54 chegaria depois de o estrago
    # estar feito.
    nao_resolvidas = budget.cortar_por_bytes(nao_resolvidas, fatias["provenance"])

    # Os MESMOS caminhos das nao resolvidas, e nao os de `symbols`: a pergunta
    # aqui e "o que estes arquivos fazem com dado", e o arquivo do ponto de
    # entrada e o que a resposta descreve. Ampliar para todo simbolo entregue
    # traria o fluxo de arquivos que entraram no pacote por parentesco de nome,
    # e a secao encheria de linhagem que ninguem perguntou.
    linhagem, total_fluxos, total_recusas = _linhagem(banco, caminhos)
    linhagem = budget.cortar_por_bytes(linhagem, fatias["lineage"])

    indice = resumo(banco)
    corpo: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "query": {
            # O texto da tarefa NAO e ecoado. Ele nao esta na secao 55, quem
            # chamou ja o tem, e ele e a unica string do pacote que veio de fora
            # sem passar por normalizacao -- devolve-la seria carregar conteudo
            # nao sanitizado num objeto que outro agente vai ler. O que sai e a
            # EXPANSAO dela, que e derivada do dicionario e auditavel.
            "task_type": task_type,
            "terms": list(expansao.termos[:TERMOS_MAXIMOS]),
            "clusters": list(expansao.clusters),
            "dictionary_version": expansao.versao,
            "budget_bytes": orcamento,
        },
        "index": {
            # Ver a docstring do modulo: nao medido nao vira `true`.
            "fresh": None,
            "head": None,
            "worktree": None,
            "root_fingerprint": indice["root_fingerprint"],
            "engine_version": indice["engine_version"],
            "created_at": indice["created_at"],
        },
        "entry_points": entradas,
        "symbols": restantes,
        "relationships": relacoes,
        "lineage": linhagem,
        "rules": [dict(r) for r in regras],
        "runtime": dict(runtime or {}),
        "snippets": [],
        "unresolved": nao_resolvidas,
        "security": {"trust": _AVISO_DE_CONFIANCA},
        "metrics": {
            "candidate_files": len({achado.path for achado, _ in preliminar}),
            "selected_files": len({item["path"] for item in simbolos}),
            "selected_symbols": len(simbolos),
            "unresolved_total": total_nao_resolvidas,
            # Os dois saem SEMPRE, inclusive valendo zero, e e isso que separa
            # "estes arquivos nao movem dado" de "ninguem perguntou". A lista
            # vazia sozinha nao distingue os dois casos -- era exatamente o
            # estado do campo `lineage` antes de `data_flow` existir.
            "lineage_flows_total": total_fluxos,
            "lineage_blind_spots_total": total_recusas,
            "estimated_tokens": 0,
            "over_budget_bytes": 0,
        },
        "reductions": [],
    }

    corpo, passos = budget.aplicar_reducao(
        corpo,
        max(1, orcamento - _RESERVA_DE_POSFIXO),
        _redutores(protegidas),
        ultimo_recurso=_ultimo_recurso,
    )
    corpo["reductions"] = list(passos)
    entregues = corpo["entry_points"] + corpo["symbols"]
    corpo["metrics"]["selected_symbols"] = len(entregues)
    corpo["metrics"]["selected_files"] = len({item["path"] for item in entregues})
    _fixar_metricas_do_posfixo(corpo, orcamento)

    return ContextPack(
        query=corpo["query"],
        index=corpo["index"],
        entry_points=tuple(corpo["entry_points"]),
        symbols=tuple(corpo["symbols"]),
        relationships=tuple(corpo["relationships"]),
        lineage=tuple(corpo["lineage"]),
        rules=tuple(corpo["rules"]),
        runtime=corpo["runtime"],
        snippets=tuple(corpo["snippets"]),
        unresolved=tuple(corpo["unresolved"]),
        security=corpo["security"],
        metrics=corpo["metrics"],
        reductions=tuple(passos),
    )


__all__ = [
    "CANDIDATOS_POR_TERMO",
    "ENTRY_POINTS",
    "SCHEMA_VERSION",
    "SEMENTES",
    "TERMOS_MAXIMOS",
    "UNRESOLVED_MAXIMO",
    "ContextPack",
    "montar",
]
