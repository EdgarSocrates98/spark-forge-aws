"""Recall e economia do `ContextPack`, contra denominador DECLARADO.

## O que este modulo mede, e por que o denominador vem junto

`montar()` produz um `ContextPack` dentro de um orcamento de bytes. A pergunta
que ninguem tinha respondido e dupla:

1. **O pack contem o simbolo que responde a pergunta?** -- recall.
2. **Quanto ele custa contra a alternativa?** -- economia.

A segunda so significa alguma coisa com a primeira ao lado. Um pack vazio
"economiza" 100% e nao responde nada. A §14 de `docs/harness/CODEINTEL-GAP.md`
escreve a assimetria e este modulo a torna executavel:

> economia que omite o simbolo necessario e falha, nao sucesso

## Por que economia NAO tem piso aqui

A medicao da §10 daquele documento provou que o denominador decide o **sinal**
do resultado, na mesma ferramenta: contra ler arquivo o indice economiza 645x;
contra um `grep` cirurgico pela definicao ele CUSTA 5.3x mais. Fixar um piso de
economia seria escolher o denominador que agrada.

Entao os tres denominadores saem **juntos**, sempre, e nenhum deles vira alvo:

- `bytes_arquivos` -- soma dos arquivos que contem os simbolos exigidos. E o que
  um agente sem ferramenta de fato faz.
- `bytes_grep` -- a saida de `grep -n "def <simbolo>"`. O piso adversarial: o
  denominador que menos favorece a ferramenta.
- `bytes_por_nivel` -- o pack em cada `detail_level` pedido. Fecha a divida da
  regra 28 do `CLAUDE.md` neste eixo: "antes de afirmar que `detail_level`
  reduz, leia o numero".

Bytes UTF-8 sempre, token nunca (regra 22). `budget.estimar_tokens` existe e sai
como `estimated_tokens` no pacote -- estimativa DECLARADA, e ela nao entra em
razao de economia nenhuma aqui.

## O que este modulo NAO faz

Nao atribui economia a uma causa e nao estima ganho financeiro (regra 13). Ele
mede quatro numeros e os poe lado a lado; concluir e de quem le.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.codeintel import budget
from sparkforge.economy.goldset import PerguntaDeOuro, derivar_goldset

# Os niveis que a medicao percorre. `None` e "sem pedido", que e como a CLI
# chama quando o operador nao passa nada -- precisa estar aqui porque e o
# caminho mais usado, e medi-lo separado do `summary` explicito e o que
# responde se os dois de fato coincidem.
NIVEIS = (None, "summary", "full")


@dataclass(frozen=True)
class SimboloExigido:
    """Um par `(arquivo, simbolo)` e se o pack o trouxe. Booleano, nunca media.

    Media sobre simbolos esconde o zero: um pack com 9 de 10 simbolos exigidos
    tem 90% e NAO responde a pergunta, porque o que falta pode ser exatamente o
    que a regra ancora.
    """

    arquivo: str
    simbolo: str
    presente: bool


@dataclass(frozen=True)
class MedidaDeRecall:
    """O resultado de uma pergunta, nos DOIS eixos que ela tem.

    ## Por que duas perguntas, e nao uma

    Medido em 2026-09-02: o titulo da regra
    `"connectedComponents sem diretorio de checkpoint"` expande para
    `('connectedcomponents', 'sem', 'diretorio', 'checkpoint', ...)` e devolve
    **zero** candidatos na fixture cujo simbolo se chama `componentes`. O titulo
    descreve o DEFEITO; o indice guarda o NOME. As duas coisas nao se encontram,
    e isso nao e defeito de nenhum dos dois.

    Entao a mesma fixture rende duas medidas, com estatutos diferentes:

    - `nominal` -- a consulta e o nome do simbolo. Isto o indice TEM de
      responder: se `buscar(banco, "componentes")` acha o no e o pack nao o
      entrega, o funil perdeu no caminho. **Piso duro.**
    - `conceitual` -- a consulta e o titulo da regra, que e como um operador
      descreve o problema. Isto o subsistema nao promete hoje. **Medido e
      publicado, sem piso.**

    Dar piso ao conceitual reprovaria uma capacidade que ninguem construiu e que
    a SPEC nao promete; omiti-lo esconderia o numero que diz o quanto falta.
    Publicar os dois lado a lado e o que a §10 do CODEINTEL-GAP fez quando
    mediu 645x a favor e 5.3x contra na mesma ferramenta.
    """

    chave: str
    pergunta_conceitual: str
    nominal: tuple[SimboloExigido, ...]
    conceitual: tuple[SimboloExigido, ...]
    bytes_pack: int
    bytes_arquivos: int
    bytes_grep: int
    bytes_por_nivel: dict[str, int]
    erro: str = ""

    @property
    def respondeu(self) -> bool:
        """Piso duro: todo simbolo exigido veio pela consulta NOMINAL."""
        return not self.erro and all(s.presente for s in self.nominal)

    @property
    def respondeu_conceitual(self) -> bool:
        """Sem piso -- reportado para dizer o quanto falta."""
        return not self.erro and all(s.presente for s in self.conceitual)

    @property
    def faltaram(self) -> tuple[str, ...]:
        return tuple(
            f"{s.arquivo}::{s.simbolo}" for s in self.nominal if not s.presente
        )


def _nomes_do_pack(pacote: dict[str, Any]) -> set[tuple[str, str]]:
    """Os pares `(basename, nome)` que o pack de fato traz.

    Compara por BASENAME porque `fact.subject.file` e relativo ao artefato
    (`job.py`) e `Achado.path` e relativo a raiz indexada -- os dois nomeiam o
    mesmo arquivo por caminhos de origens diferentes, e casar o caminho inteiro
    exigiria que as duas convencoes coincidissem por acidente.

    Casa contra `name` E `qualified_name`: um metodo ancorado como `metodo` pelo
    extrator aparece no indice como `Classe.metodo`, e exigir so o primeiro
    perderia o caso que o indice resolveu MELHOR.

    Le `entry_points` E `symbols`, e a razao esta MEDIDA: `montar()` fatia a
    lista ordenada em duas -- os primeiros viram `entry_points`, o resto vira
    `symbols` (`context.py:775`) -- e a propria metrica do pacote soma as duas
    para reportar `selected_symbols` (`context.py:861`). Ler so `symbols` daria
    recall zero para todo caso em que o simbolo exigido e o MAIS relevante, que
    e exatamente o caso que a ferramenta acertou. A primeira versao deste modulo
    tinha esse defeito, e ele se parecia com defeito do produto: o pacote dizia
    `selected_symbols: 1` com `symbols` vazio.
    """
    encontrados: set[tuple[str, str]] = set()
    for simbolo in (*pacote.get("entry_points", ()), *pacote.get("symbols", ())):
        base = Path(str(simbolo.get("path", ""))).name
        for campo in ("name", "qualified_name"):
            nome = str(simbolo.get(campo, ""))
            if nome:
                encontrados.add((base, nome))
                # `Classe.metodo` casa tambem por `metodo`, que e como o
                # extrator o ancorou.
                if "." in nome:
                    encontrados.add((base, nome.rsplit(".", 1)[-1]))
    return encontrados


def _bytes_dos_arquivos(raiz: Path, arquivos: Sequence[str]) -> int:
    """Soma o tamanho dos arquivos que contem os simbolos exigidos.

    Le em bytes e normaliza CRLF para LF antes de contar. `os.path.getsize`
    divergiria entre um checkout Windows e o do CI, e este numero e publicado --
    a mesma armadilha que VNX-430 pagou (51 KB em LF, 52 KB em CRLF).
    """
    total = 0
    for nome in sorted(set(arquivos)):
        for caminho in raiz.rglob(nome):
            try:
                total += len(caminho.read_bytes().replace(b"\r\n", b"\n"))
            except OSError:
                continue
            break
    return total


def _bytes_do_grep(raiz: Path, simbolos: Sequence[tuple[str, str]]) -> int:
    """O que `grep -n "def <simbolo>"` devolveria, em bytes.

    Reimplementado em Python e nao por subprocesso: o modulo roda dentro da
    suite, e chamar binario externo tornaria a medida dependente de qual `grep`
    o sistema tem. O formato e o do `grep -n`: `caminho:linha:texto`.
    """
    total = 0
    for arquivo, simbolo in sorted(set(simbolos)):
        padrao = re.compile(rf"^\s*(?:async\s+)?(?:def|class)\s+{re.escape(simbolo)}\b")
        for caminho in raiz.rglob(arquivo):
            try:
                linhas = caminho.read_text(encoding="utf-8", errors="replace").split("\n")
            except OSError:
                continue
            rel = caminho.relative_to(raiz).as_posix()
            for numero, linha in enumerate(linhas, start=1):
                if padrao.match(linha):
                    total += len(f"{rel}:{numero}:{linha}\n".encode())
            break
    return total


def _ausentes(pergunta: PerguntaDeOuro) -> tuple[SimboloExigido, ...]:
    return tuple(
        SimboloExigido(arquivo=a, simbolo=s, presente=False)
        for a, s in pergunta.simbolos_exigidos
    )


def _presenca(
    pergunta: PerguntaDeOuro, encontrados: set[tuple[str, str]]
) -> tuple[SimboloExigido, ...]:
    return tuple(
        SimboloExigido(arquivo=a, simbolo=s, presente=(Path(a).name, s) in encontrados)
        for a, s in pergunta.simbolos_exigidos
    )


def _medir_uma(pergunta: PerguntaDeOuro) -> MedidaDeRecall:
    from sparkforge.codeintel.context import montar
    from sparkforge.codeintel.index import indexar

    raiz = pergunta.entrada
    base = {
        "chave": pergunta.chave,
        "pergunta_conceitual": pergunta.pergunta,
        "nominal": _ausentes(pergunta),
        "conceitual": _ausentes(pergunta),
        "bytes_pack": 0,
        "bytes_arquivos": 0,
        "bytes_grep": 0,
        "bytes_por_nivel": {},
    }
    if not raiz.is_dir():
        return MedidaDeRecall(**base, erro=f"input ausente: {raiz}")

    # Banco em diretorio temporario: a medicao NUNCA escreve na arvore do
    # repositorio. Um indice deixado em `fixtures/` viraria arquivo nao
    # rastreado que o gate de artefato bruto do CI teria de perdoar.
    #
    # `ignore_cleanup_errors` porque no Windows o sqlite so solta o arquivo
    # quando a conexao fecha, e `codeintel` mantem a sua em cache. MEDIDO: sem
    # isso, a limpeza levanta `PermissionError: [WinError 32]` e derruba a
    # medicao inteira -- instrumentacao que quebra o produto e defeito (regra
    # 27), e aqui derrubaria o proprio gate.
    with tempfile.TemporaryDirectory(
        prefix="sf-recall-", ignore_cleanup_errors=True
    ) as tmp:
        banco = Path(tmp) / "indice.sqlite3"
        try:
            indexar(raiz, banco)
        except Exception as erro:  # noqa: BLE001 - medicao nunca derruba a chamada
            return MedidaDeRecall(**base, erro=f"indexar: {erro!r}")

        # A consulta NOMINAL junta os nomes exigidos: e a pergunta dirigida que
        # o indice tem de responder. A CONCEITUAL e o titulo da regra.
        nominal = " ".join(sorted({s for _, s in pergunta.simbolos_exigidos}))
        try:
            pacote = montar(banco, nominal).para_dicionario()
            conceitual = montar(banco, pergunta.pergunta).para_dicionario()
        except Exception as erro:  # noqa: BLE001
            return MedidaDeRecall(**base, erro=f"montar: {erro!r}")

        por_nivel = {
            str(nivel): budget.tamanho_em_bytes(
                pacote if nivel is None else _no_nivel(pacote, nivel)
            )
            for nivel in NIVEIS
        }

    return MedidaDeRecall(
        chave=pergunta.chave,
        pergunta_conceitual=pergunta.pergunta,
        nominal=_presenca(pergunta, _nomes_do_pack(pacote)),
        conceitual=_presenca(pergunta, _nomes_do_pack(conceitual)),
        bytes_pack=budget.tamanho_em_bytes(pacote),
        bytes_arquivos=_bytes_dos_arquivos(
            raiz, [a for a, _ in pergunta.simbolos_exigidos]
        ),
        bytes_grep=_bytes_do_grep(raiz, pergunta.simbolos_exigidos),
        bytes_por_nivel=por_nivel,
    )


def _no_nivel(corpo: dict[str, Any], nivel: str) -> dict[str, Any]:
    """O pack reduzido ao nivel pedido.

    `montar()` nao recebe `detail_level` -- quem o aplica e a camada de
    adaptador. Reproduzir a reducao aqui mediria a MINHA reducao e nao a do
    produto, entao `summary` derruba os campos volumosos que o adaptador ja
    trata como opcionais, e `full` e o pack inteiro. O que este numero responde e
    estreito e esta declarado: quanto do pack e snippet e quebra de escore.
    """
    if nivel == "full":
        return corpo
    magro = dict(corpo)
    magro["snippets"] = []
    magro["symbols"] = [
        {k: v for k, v in s.items() if k != "score_breakdown"}
        for s in corpo.get("symbols", ())
    ]
    return magro


def medir(
    perguntas: Sequence[PerguntaDeOuro] | None = None,
) -> tuple[MedidaDeRecall, ...]:
    """Mede todas as perguntas do gold set, ou as que forem passadas."""
    alvo = tuple(perguntas) if perguntas is not None else derivar_goldset()
    return tuple(_medir_uma(p) for p in alvo)


__all__ = ["NIVEIS", "MedidaDeRecall", "SimboloExigido", "medir"]
