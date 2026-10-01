"""O gold set de recuperacao, DERIVADO das regras -- nunca escrito a mao.

## Por que derivar, e nao versionar

Um gold set em arquivo e a segunda copia da verdade, e ela envelhece calada: a
regra muda o que ancora, o arquivo continua afirmando o que ancorava antes, e o
gate passa a medir o passado com cara de presente. E o mesmo defeito que o
sub-projeto 2 existiu para remover (`EMR_MATRIX` literal em codigo contra a
matriz em YAML).

Derivado a cada execucao, o gold set NAO PODE divergir das regras. Se uma regra
perder ancoragem, a contagem cai e o gate reclama; se uma regra nova ganhar
fixture ancorada, a contagem sobe e o piso e atualizado no commit que a fez
subir.

## A cadeia, e por que ela fecha sem heuristica

`Fact.subject` carrega `{type, file, line, col, symbol, snippet}` -- `symbol` e
CAMPO, nao inferencia. `Finding.evidence` e lista de `fact_id`. Entao:

    finding.evidence[] -> fact.id -> fact.subject.{file, symbol}

Nada aqui adivinha qual simbolo responde a pergunta. Quem decidiu foi o extrator
quando ancorou o fato, e a regra quando citou o fato como evidencia. Este modulo
so segue a referencia.

## O recorte, medido

Medido em 2026-09-02 sobre as 83 fixtures que tem `.py` no `input/`, 48 achados
no total:

    23  pergunta de ouro     -- evidencia ancora simbolo em arquivo `.py`
    23  evidencia_sem_simbolo -- `subject.symbol` vazio: ancora arquivo, nao simbolo
     2  extensao_nao_indexada -- ancora simbolo em `.tf` (SF-ENV-003, SF-GRAPH-005)

**A classe do meio e do mesmo tamanho que o gold set, e por isso ela e nomeada
em vez de descartada.** Metade dos achados destas fixtures cita fato que ancora
ARQUIVO e nao SIMBOLO -- e um limite dos extratores que produziram aqueles
fatos, nao deste modulo nem do indexador. Sem nomea-la, "o gate cobre 23
achados" seria lido como "existem 23 achados", e o gate estaria escondendo o
proprio denominador.

Uma versao anterior deste docstring dizia "25 pares em 17 regras ancorando fora
de .py", numero que veio de um filtro diferente e nao se sustentou na medicao.
Fica registrado porque a correcao e o ponto: os dois motivos de recusa destravam
com medidas DIFERENTES -- um mexe no indexador, o outro no extrator --, e
soma-los num rotulo so apagaria essa distincao.

Todas saem NOMEADAS em `fora_do_alcance()`, nunca descartadas em silencio:
listar a recusa e a diferenca entre "nao sei" e "nao perguntei" (regra 20).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# A raiz do repositorio, a partir deste arquivo: sparkforge/economy/goldset.py
_RAIZ = Path(__file__).resolve().parent.parent.parent

# So `.py` porque so `.py` e o que `codeintel.index.indexar` percorre. Estender
# esta tupla sem estender o indexador produziria pergunta que o pack nao tem
# como responder, e um vermelho que nao aponta defeito nenhum.
EXTENSOES_INDEXADAS = (".py",)


@dataclass(frozen=True)
class PerguntaDeOuro:
    """Uma pergunta com o simbolo que a resposta tem obrigatoriamente de conter.

    `simbolos_exigidos` e tupla de `(arquivo, simbolo)` e nao so o nome porque
    dois arquivos da mesma fixture podem definir o mesmo nome -- e porque a
    medida de recall precisa dizer QUAL par faltou, nao apenas que faltou algo.
    """

    fixture: str
    rule_id: str
    pergunta: str
    simbolos_exigidos: tuple[tuple[str, str], ...]

    @property
    def chave(self) -> str:
        """A chave estavel de `SEM_RECALL`, no molde `<rule_id>@<fixture>`."""
        return f"{self.rule_id}@{self.fixture}"

    @property
    def entrada(self) -> Path:
        """O diretorio `input/` que o indexador recebe."""
        return _RAIZ / self.fixture / "input"


@dataclass(frozen=True)
class ForaDoAlcance:
    """Par (fixture, regra) que nao rende pergunta, com a razao SEPARADA.

    As duas razoes destravam com medidas diferentes, e por isso nao podem
    compartilhar um rotulo:

    - `extensao_nao_indexada` -- a evidencia ancora simbolo, mas num arquivo que
      `codeintel.index.indexar` nao percorre. Destrava com extrator para aquela
      extensao.
    - `evidencia_sem_simbolo` -- a evidencia ancora ARQUIVO e nao simbolo:
      `subject.symbol` esta vazio. Destrava no EXTRATOR que produziu o fato, e
      nao no indexador. E a classe maior das duas, e nomea-la e o que impede que
      "o gate cobre 23 achados" seja lido como "existem 23 achados".

    Nenhuma das duas e defeito deste modulo. Sao limites declarados.
    """

    fixture: str
    rule_id: str
    razao: str
    extensoes: tuple[str, ...] = ()

    @property
    def medida_que_destravaria(self) -> str:
        if self.razao == "extensao_nao_indexada":
            return (
                "extrator de simbolo para as extensoes em `extensoes`, e a "
                "entrada correspondente em EXTENSOES_INDEXADAS"
            )
        return (
            "o extrator que produz o fato citado precisa preencher "
            "`subject.symbol`; hoje ele ancora arquivo e linha, sem simbolo"
        )


def _carregar(caminho: Path) -> Any:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _fatos(dados: Any) -> dict[str, dict[str, Any]]:
    """Indexa os fatos por id, aceitando as duas formas que o corpus guarda."""
    if isinstance(dados, dict):
        dados = dados.get("facts", [])
    if not isinstance(dados, list):
        return {}
    return {f["id"]: f for f in dados if isinstance(f, dict) and "id" in f}


def _titulo(rule_id: str, catalogo: dict[str, str]) -> str:
    """A pergunta vem do `title` da regra -- texto ja versionado em YAML.

    Escrever pergunta a mao aqui seria medir a minha suposicao sobre o que o
    operador perguntaria. O titulo da regra e o que o repositorio ja publica
    como a coisa que aquela regra procura.
    """
    return catalogo.get(rule_id, rule_id)


def _casos() -> Iterable[tuple[str, Path, Path]]:
    """Cada `(fixture, findings.json, facts.json)` com `.py` no `input/`."""
    for entrada in sorted(_RAIZ.glob("fixtures/*/*/input")):
        # `any(gerador for ...)` testaria a verdade do OBJETO gerador, que e
        # sempre verdadeira, e o filtro nao filtraria nada -- foi o defeito da
        # primeira versao, medido: 244 casos onde ha 85. `next(..., None)` forca
        # a producao do primeiro item, e e o que decide se ha arquivo indexavel.
        if not any(
            next(entrada.rglob(f"*{ext}"), None) is not None
            for ext in EXTENSOES_INDEXADAS
        ):
            continue
        base = entrada.parent
        achados = base / "expected" / "findings.json"
        fatos = base / "expected" / "facts.json"
        if achados.exists() and fatos.exists():
            yield base.relative_to(_RAIZ).as_posix(), achados, fatos


def _derivar() -> tuple[tuple[PerguntaDeOuro, ...], tuple[ForaDoAlcance, ...]]:
    from sparkforge.rules.loader import load_catalog

    catalogo = {r["id"]: r.get("title", r["id"]) for r in load_catalog()}
    perguntas: list[PerguntaDeOuro] = []
    fora: list[ForaDoAlcance] = []

    for fixture, caminho_achados, caminho_fatos in _casos():
        achados = _carregar(caminho_achados)
        indice = _fatos(_carregar(caminho_fatos))
        if not isinstance(achados, list):
            continue
        for achado in achados:
            if not isinstance(achado, dict) or "rule_id" not in achado:
                continue
            ancorados: set[tuple[str, str]] = set()
            extensoes: set[str] = set()
            for fact_id in achado.get("evidence", []):
                fato = indice.get(fact_id)
                if not isinstance(fato, dict):
                    continue
                subject = fato.get("subject") or {}
                arquivo = str(subject.get("file", ""))
                simbolo = str(subject.get("symbol", ""))
                if not (arquivo and simbolo):
                    continue
                ext = os.path.splitext(arquivo)[1]
                if ext in EXTENSOES_INDEXADAS:
                    ancorados.add((arquivo, simbolo))
                else:
                    extensoes.add(ext or "(sem extensao)")
            if ancorados:
                perguntas.append(
                    PerguntaDeOuro(
                        fixture=fixture,
                        rule_id=achado["rule_id"],
                        pergunta=_titulo(achado["rule_id"], catalogo),
                        simbolos_exigidos=tuple(sorted(ancorados)),
                    )
                )
            elif extensoes:
                fora.append(
                    ForaDoAlcance(
                        fixture=fixture,
                        rule_id=achado["rule_id"],
                        razao="extensao_nao_indexada",
                        extensoes=tuple(sorted(extensoes)),
                    )
                )
            else:
                fora.append(
                    ForaDoAlcance(
                        fixture=fixture,
                        rule_id=achado["rule_id"],
                        razao="evidencia_sem_simbolo",
                    )
                )

    perguntas.sort(key=lambda p: (p.rule_id, p.fixture))
    fora.sort(key=lambda f: (f.rule_id, f.fixture))
    return tuple(perguntas), tuple(fora)


def derivar_goldset() -> tuple[PerguntaDeOuro, ...]:
    """As perguntas com simbolo `.py` exigido, ordenadas por `(rule_id, fixture)`."""
    return _derivar()[0]


def fora_do_alcance() -> tuple[ForaDoAlcance, ...]:
    """Os pares que ancoram fora de arquivo indexado, NOMEADOS.

    Existe para que a saida do gate possa listar o que ficou de fora. Um gate
    que mede 23 perguntas e nao diz que outras 25 existem esconde o denominador
    do proprio recorte.
    """
    return _derivar()[1]


__all__ = [
    "EXTENSOES_INDEXADAS",
    "ForaDoAlcance",
    "PerguntaDeOuro",
    "derivar_goldset",
    "fora_do_alcance",
]
