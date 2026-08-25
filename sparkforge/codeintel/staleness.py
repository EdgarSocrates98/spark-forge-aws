"""Frescor do indice: o que mudou, o que reindexar, e quando recusar a resposta.

POR QUE ESTE MODULO EXISTE
--------------------------
Indice velho responde "nenhum simbolo" com exatamente a mesma cara com que
responde sobre simbolo que nunca existiu. As duas respostas sao a string vazia,
e quem le nao tem como distinguir. Esse e o defeito que as quatro secoes da
SPEC cobertas aqui -- 42, 43, 44 e 46 -- existem para nao ter, e e por isso que
a regra final e recusar em vez de responder: contexto errado e pior que
contexto inexistente.

O QUE FOI MEDIDO, E O QUE A MEDICAO DECIDIU
--------------------------------------------
`indexar` reconstroi tudo. A pergunta que decide se este modulo se paga e:
quanto custa a MESMA arvore com tres arquivos alterados?

Medido sobre uma copia dos `*.py` deste repositorio -- 401 arquivos, 6308 nos,
9323 arestas, 11310 pontos cegos --, banco REUSADO nas duas colunas (nunca banco
novo, e a secao seguinte diz por que isso decide a validade da medicao), os
dois caminhos partindo do MESMO banco a cada rodada, 3 arquivos alterados entre
as rodadas:

    rodada   reconstrucao completa   sincronizacao   reresolvidos
      1            3.301 s              0.614 s          26
      2            3.202 s              0.557 s          26
      3            3.013 s              0.543 s          26

5.5x, e nao mais: os dois grafos foram comparados no, aresta e ponto cego a
cada rodada, e sao identicos -- se nao fossem, a medicao nao valeria nada.

Sem NENHUM arquivo alterado, so a deteccao:

    `detectar`   0.179 / 0.184 / 0.180 s

Esse 0.18 s e o numero que importa para a SPEC 43, e nao o 5.5x: e o que TODA
query paga fora do cooldown, mesmo quando nada mudou. E o que justifica o
cooldown de 30 s existir -- sem ele, 0.18 s entrariam em cada pergunta.

O ganho nao vem de escrever menos, vem de PARSEAR menos: 3 alterados mais 26
reresolvidos sao 29 arquivos parseados contra 401, ou 7%. Que 7% do trabalho
custe 17% do tempo tambem esta medido e tem causa conhecida: `detectar` sozinho
ja e 0.18 dos 0.55 s, e `catalogo_do_banco` le os 6308 nos independentemente de
quantos arquivos mudaram. O incremental nao e proporcional ao delta -- ele tem
um piso.

Por isso a deteccao usa `mtime` e `size` ANTES do sha-256 -- ler 401 arquivos
inteiros para hashear custaria a parte que se pretende economizar. O sha entra
so quando o par (mtime, size) diverge, que e onde ele de fato decide alguma
coisa: `touch` sem edicao e edicao que restaura o conteudo anterior sao os dois
casos em que mtime mente, e os dois aparecem em repositorio real (checkout,
stash pop, formatador).

MEDIR EM BANCO NOVO TERIA MEDIDO A COISA ERRADA
------------------------------------------------
A fatura de escala que J4 pagou -- `unresolved_refs.source_id` sem indice
fazendo o CASCADE varrer a tabela inteira, 1a indexacao 3.4 s e 4a 10.7 s -- nao
aparece em tmpdir, porque la o banco e sempre novo. Sincronizacao incremental
roda sobre banco existente POR DEFINICAO, entao a medicao acima foi feita com o
banco ja carregado -- duas indexacoes completas e duas sincronizacoes antes da
primeira cronometragem --, e o banco foi COPIADO para as duas colunas a cada
rodada, para que as duas partissem do mesmo estado em vez de uma herdar o
trabalho da outra.

A RESOLUCAO NAO E LOCAL, E E ISSO QUE TORNA O INCREMENTAL DIFICIL
-----------------------------------------------------------------
Reindexar so o arquivo alterado esta ERRADO, e erra calado. Tres motivos, todos
verificados em teste aqui:

1. `node_id` deriva de caminho, kind, nome qualificado e assinatura. Mudar a
   assinatura de uma funcao muda o id dela; a aresta que CHEGAVA nesse no cai
   pelo `ON DELETE CASCADE`, e o arquivo que a produziu nao foi tocado -- entao
   ninguem a recria. O chamador perde o chamado em silencio.
2. Mesmo quando o id NAO muda, o `DELETE FROM files` do arquivo alterado leva
   os nos dele, e as arestas de terceiros que apontavam para esses nos vao
   junto no segundo salto da cadeia. Reinserir o no identico nao ressuscita a
   aresta.
3. Definicao NOVA num arquivo alterado pode resolver referencia que estava em
   `unresolved_refs` de um arquivo INALTERADO -- e definicao duplicada pode
   tornar AMBIGUOUS o que era aresta.

Por isso a sincronizacao reparseia um conjunto maior que o alterado: os
alterados MAIS os arquivos cuja resolucao pode ter mudado por causa deles. Esse
conjunto e calculado do banco, nao adivinhado:

    dependentes   arquivo que tinha aresta entrando num arquivo alvo
    candidatos    arquivo com `unresolved_refs` cujo nome esta no delta de
                  nomes definidos/removidos pelos alvos
    ambiguos      arquivo com aresta JA RESOLVIDA para um no cujo nome esta no
                  delta -- a definicao nova em OUTRO arquivo pode ter tornado
                  aquela aresta ambigua

A terceira nasceu de uma falha da suite, e nao de projeto: as duas primeiras
deixavam `job.py -> lib.processar` de pe depois de `lib2.py` acrescentar um
segundo `processar`, enquanto a reconstrucao completa transformava a aresta em
ponto cego `AMBIGUOUS`. Ver `_fontes_com_alvo_no_delta`.

O delta de nomes e SUPERCONJUNTO de proposito -- entra `name` e
`qualified_name` de todo no removido e de todo no acrescentado. Errar para mais
custa reparsear arquivo a toa; errar para menos deixa aresta faltando calada, e
so a segunda forma de erro e indistinguivel de "nao ha chamada".

REFERENCIA NAO E PERSISTIDA, E ISSO E O TETO DO GANHO
------------------------------------------------------
`edges` guarda o que resolveu e `unresolved_refs` guarda o que nao resolveu --
nenhuma das duas guarda a referencia CRUA de quem resolveu. Entao todo arquivo
do conjunto afetado precisa de um `ast.parse` novo para reextrair referencia,
mesmo quando os nos dele nao mudaram. Isto e preco conhecido e nao surpresa: uma
tabela `refs` persistida trocaria esse parse por I/O, e J4 mediu que
`unresolved_refs` sozinha ja custa 28.9% do arquivo. Fica registrado como
limite: em arvore onde tudo depende de tudo, o conjunto afetado tende ao total e
o ganho tende a zero.

STRICT TREE NAO E O MESMO QUE STALENESS, E OS DOIS ENTRAM
----------------------------------------------------------
Staleness compara CONTEUDO de arquivo. Strict tree (SPEC 44) compara ESTADO DA
ARVORE -- HEAD, ref e identidade do worktree. Sao perguntas diferentes: trocar
de branch pode nao mudar nenhum `*.py` e ainda assim significar que o indice foi
construido para outra coisa, e um indice gravado sem estado de arvore nenhum nao
prova nada sobre si mesmo.

A regra e fail-closed (`INV-015`): estado ausente ou divergente NEGA. `indexar`
sozinho nao grava estado -- so `sincronizar` grava --, entao indice construido
pela via antiga e negado ate a primeira sincronizacao. Presumir fresco o que nao
se sabe seria a unica falha que este modulo nao pode ter.

O COOLDOWN NAO COBRE A CONFERENCIA DE ARVORE, E ISSO E DELIBERADO
------------------------------------------------------------------
A SPEC 43 declara 30 s de cooldown. Ele vale para a VARREDURA de disco, que e a
parte cara (391 `stat`, ~60 ms). Ler `.git/HEAD` e um ou dois `read_text`, e
cobre o evento de maior risco do conjunto -- `git checkout` de outro branch --
com custo que nao aparece na medicao. Colocar os dois sob o mesmo cooldown
economizaria microssegundos e compraria uma janela de 30 s respondendo com o
grafo do branch anterior.

GIT SEM EXECUTAR NADA (SPEC 45)
--------------------------------
Nenhum `subprocess`, nenhum `git`, nenhuma dependencia nova. Os arquivos de
`.git/` sao lidos diretamente -- `HEAD`, `refs/`, `packed-refs`, `commondir` --
porque ler arquivo nao dispara hook e chamar `git` dispara. `post-checkout` e
`pre-commit` do repositorio indexado sao codigo do repositorio, e `INV-005`
proibe executar codigo do repositorio.

O nome de ref lido de `HEAD` e conteudo de repositorio, logo NAO CONFIAVEL
(`INV-014`): ele vira caminho de arquivo, entao `_ref_confinada` recusa ref que
nao comece por `refs/`, que contenha `..` ou que seja absoluta. Sem essa guarda,
um `HEAD` com `ref: ../../../../etc/passwd` faria o modulo ler fora da arvore.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from sparkforge.codeintel.db import BANCO_PADRAO, abrir, criar_schema, impressao_da_raiz
from sparkforge.codeintel.extract import extrair_nos_ou_none
from sparkforge.codeintel.index import (
    _PADRAO,
    Resultado,
    _gravar,
    _ler,
    id_de_arquivo,
    indexar,
)
from sparkforge.codeintel.refs import Referencia, extrair_referencias
from sparkforge.codeintel.resolve import catalogo_do_banco, resolver
from sparkforge.facts.scan import iter_source_files

# SPEC 43. Segundos entre duas varreduras de disco para o mesmo banco.
COOLDOWN_S = 30.0

# SPEC 43. Acima disto a query e recusada em vez de sincronizada na hora: a
# sincronizacao entra no caminho da resposta, e 26 arquivos alterados ja custam
# mais que o orcamento de uma pergunta.
MAX_AUTO_SYNC_FILES = 25

# SPEC 43 nomeia esta acao no payload de `STALE_INDEX`. O verbo `code sync`
# ainda NAO existe em `adapters/cli.py` -- a entrada em Python e
# `staleness.sincronizar`. Fica como constante para que ligar o verbo mude uma
# linha, e nao onze mensagens de erro espalhadas.
ACAO_DE_SYNC = "sparkforge code sync"

# SPEC 46. Sob a raiz indexada, como `BANCO_PADRAO`.
DIRETORIO_DE_WORKTREES = BANCO_PADRAO.parent / "worktrees"

_METADATA_HEAD = "tree_head"
_METADATA_REF = "tree_ref"
_METADATA_IDENTIDADE = "tree_identity"
_METADATA_IMPRESSAO = "root_fingerprint"
_METADATA_CHECADO_NS = "freshness_checked_ns"
_METADATA_VEREDITO = "freshness_verdict"

_VEREDITO_FRESCO = "fresh"
_VEREDITO_STALE = "stale"

_TAMANHO_DIGEST = 16
_SUFIXO_DE_WORKTREE = 4

# Ref de git que vira caminho de arquivo. Ver a secao sobre `INV-014`.
_REF_ACEITA = re.compile(r"^refs/[A-Za-z0-9._/-]+$")

_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Mudancas:
    """O que a varredura viu, separado pelo que cada caso obriga a fazer.

    Quatro tuplas e nao um numero: `quantidade` decide se sincroniza ou recusa,
    mas so as listas dizem o que fazer com cada arquivo -- e um relatorio que
    diz "164 mudaram" sem dizer quais nao permite conferir nada.

    `tocados` e a quinta e nao entra em `quantidade` de proposito: e o arquivo
    cujo `mtime` andou e cujo conteudo NAO mudou. Ele nao gera trabalho de
    indexacao, so de atualizar o `mtime` gravado -- e se nao fosse registrado, a
    varredura seguinte tornaria a hashear os mesmos arquivos para sempre.
    """

    inalterados: tuple[str, ...] = ()
    alterados: tuple[str, ...] = ()
    novos: tuple[str, ...] = ()
    removidos: tuple[str, ...] = ()
    tocados: tuple[str, ...] = ()

    @property
    def quantidade(self) -> int:
        """Arquivos que obrigam reindexacao. E este numero que a SPEC 43 corta."""
        return len(self.alterados) + len(self.novos) + len(self.removidos)

    @property
    def vazio(self) -> bool:
        return self.quantidade == 0


@dataclass(frozen=True)
class EstadoDaArvore:
    """Identidade da arvore no momento em que o indice foi escrito (SPEC 44).

    `head` e `ref` respondem "qual commit e qual branch". `identidade` responde
    "qual WORKTREE" -- duas arvores no mesmo commit e no mesmo branch sao
    arvores diferentes, e o indice de uma nao vale para a outra. `impressao`
    repete `db.impressao_da_raiz` porque a raiz pode mudar sem que git mude
    nada (arvore copiada, arvore sem git).

    Nenhum caminho absoluto entra: `identidade` e digest, pelo mesmo motivo que
    `impressao_da_raiz` e digest -- o arquivo de indice pode ser copiado, e nao
    deve nomear a maquina de quem o construiu.

    Strings vazias sao legitimas e distinguem casos: arvore sem git tem `head`,
    `ref` e `identidade` vazios; arvore em detached HEAD tem `head` e
    `identidade` mas nao `ref`.
    """

    head: str = ""
    ref: str = ""
    identidade: str = ""
    impressao: str = ""

    @property
    def fingerprint(self) -> str:
        """Digest dos quatro campos, para comparar estado em uma unica string.

        Os campos separados continuam existindo porque a MENSAGEM de recusa
        precisa dizer o que divergiu; o digest existe porque comparar quatro
        campos em cada ponto de decisao daria quatro chances de esquecer um.
        """
        material = "\n".join((self.head, self.ref, self.identidade, self.impressao))
        return hashlib.blake2b(
            material.encode("utf-8"), digest_size=_TAMANHO_DIGEST
        ).hexdigest()


@dataclass(frozen=True)
class ResultadoSync:
    """O que a sincronizacao fez, incluindo o que ela NAO conseguiu evitar.

    `reresolvidos` e primeira classe porque e o custo escondido do incremental:
    sao os arquivos INALTERADOS que precisaram de um `ast.parse` novo so porque
    a resolucao deles podia ter mudado. Um relatorio que some esses arquivos aos
    alterados esconderia exatamente o numero que decide se o incremental se paga
    nesta arvore.

    `completa` diz que a sincronizacao caiu para reconstrucao total -- banco
    vazio, ausente ou de outra raiz. Sem esse campo, uma reconstrucao de 3.7 s
    seria indistinguivel de um incremental que por acaso demorou.

    `arquivos` conta o que ENTROU no indice nesta execucao, e existe separado de
    `mudancas` porque a reconstrucao completa nao tem lista de mudanca nenhuma:
    ela tratou todo arquivo como novo. Preencher `Mudancas.novos` com os 391
    caminhos daria um relatorio que parece incremental e nao e.
    """

    mudancas: Mudancas
    reresolvidos: tuple[str, ...]
    arquivos: int
    nos: int
    ilegiveis: int
    arestas: int
    nao_resolvidas: int
    duracao_s: float
    completa: bool
    estado: EstadoDaArvore = field(default_factory=EstadoDaArvore)


@dataclass(frozen=True)
class Frescor:
    """Veredito de `garantir_frescor` quando ele NAO recusa.

    `verificou=False` significa que o cooldown da SPEC 43 pulou a varredura de
    disco. Sai na resposta porque "conferi e esta fresco" e "confiei no veredito
    de 12 s atras" sao afirmacoes diferentes, e quem audita precisa distinguir.
    """

    verificou: bool
    sincronizou: bool
    mudancas: Mudancas | None = None


class NegadoPorFrescor(RuntimeError):
    """Recusa fail-closed (`INV-015`): a query nao e respondida.

    Carrega `payload` no formato da SPEC 43 -- `error`, mais o que o chamador
    precisa para agir -- porque a mensagem de excecao vira texto e o payload
    vira JSON, e a superficie de tool devolve JSON.
    """

    codigo = "STALE_INDEX"

    def __init__(self, mensagem: str, **detalhes: object) -> None:
        super().__init__(mensagem)
        self.payload: dict[str, object] = {
            "error": self.codigo,
            "action": ACAO_DE_SYNC,
            **detalhes,
        }


class IndiceAusente(NegadoPorFrescor):
    """Nao ha indice. Recusa em vez de indexar no caminho da resposta."""

    codigo = "INDEX_MISSING"


class ArvoreDivergente(NegadoPorFrescor):
    """SPEC 44: HEAD, ref ou identidade nao batem, ou nunca foram gravados."""

    codigo = "TREE_MISMATCH"


class IndiceDesatualizado(NegadoPorFrescor):
    """SPEC 43: mais arquivos mudaram do que cabe no caminho da resposta."""

    codigo = "STALE_INDEX"


# --------------------------------------------------------------------------
# SPEC 45 -- metadados de git lidos, nunca executados
# --------------------------------------------------------------------------


def estado_da_arvore(raiz: str | os.PathLike[str]) -> EstadoDaArvore:
    """HEAD, ref e identidade da arvore, lendo `.git/` sem executar `git`.

    Ler e nao executar porque `git checkout` dispara `post-checkout` do
    repositorio indexado, e `INV-005` proibe executar codigo do repositorio.
    Nenhuma dependencia nova entra por isto: o formato de `.git/HEAD`,
    `refs/*` e `packed-refs` e texto, e ler texto nao precisa de biblioteca.

    Arvore sem git devolve `EstadoDaArvore` com os tres campos de git vazios e
    a impressao preenchida -- e nao levanta. Repositorio de cliente exportado
    como tarball nao tem `.git/`, e recusar a indexa-lo trocaria cobertura por
    purismo. A impressao sozinha ainda distingue duas raizes diferentes.
    """
    base = Path(raiz).expanduser()
    impressao = impressao_da_raiz(base)
    diretorio = _diretorio_git(base)
    if diretorio is None:
        return EstadoDaArvore(impressao=impressao)

    comum = _diretorio_comum(diretorio)
    head, ref = _cabeca(diretorio, comum)
    return EstadoDaArvore(
        head=head,
        ref=ref,
        # O diretorio de git de um worktree e proprio dele
        # (`.git/worktrees/<nome>`), e e por isso que ele serve de identidade:
        # duas arvores do mesmo repositorio nunca compartilham este caminho.
        identidade=hashlib.blake2b(
            str(diretorio).encode("utf-8"), digest_size=_TAMANHO_DIGEST
        ).hexdigest(),
        impressao=impressao,
    )


def _diretorio_git(base: Path) -> Path | None:
    """`.git` como diretorio, ou o diretorio para onde o `.git` de worktree aponta.

    Em worktree `git worktree add`, `.git` e um ARQUIVO com `gitdir: <caminho>`.
    Tratar so o caso de diretorio faria todo worktree parecer arvore sem git --
    e arvore sem git nao tem branch, entao os indices de todos os worktrees
    cairiam no mesmo nome de arquivo, que e exatamente o que a SPEC 46 proibe.
    """
    ponto = base / ".git"
    try:
        if ponto.is_dir():
            return ponto.resolve()
        if not ponto.is_file():
            return None
        texto = ponto.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not texto.startswith("gitdir:"):
        return None
    alvo = Path(texto[len("gitdir:") :].strip())
    if not alvo.is_absolute():
        alvo = base / alvo
    try:
        resolvido = alvo.resolve()
    except OSError:
        return None
    return resolvido if resolvido.is_dir() else None


def _diretorio_comum(diretorio: Path) -> Path:
    """Onde ficam as refs compartilhadas: o `.git` principal do repositorio.

    Worktree guarda `HEAD` proprio no diretorio dele e `refs/` no comum, e o
    ponteiro para o comum esta em `commondir`. Sem seguir esse ponteiro, o
    `refs/heads/<branch>` de qualquer worktree seria procurado no lugar errado,
    a leitura cairia no ramo de `packed-refs` inexistente, e todo worktree
    reportaria `head` vazio -- ou seja, todos iguais.
    """
    ponteiro = diretorio / "commondir"
    try:
        if not ponteiro.is_file():
            return diretorio
        texto = ponteiro.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return diretorio
    if not texto:
        return diretorio
    alvo = Path(texto)
    if not alvo.is_absolute():
        alvo = diretorio / alvo
    try:
        resolvido = alvo.resolve()
    except OSError:
        return diretorio
    return resolvido if resolvido.is_dir() else diretorio


def _cabeca(diretorio: Path, comum: Path) -> tuple[str, str]:
    """`(sha, ref)` de `HEAD`, seguindo ref solta e depois `packed-refs`.

    A ordem importa: ref solta em `refs/heads/x` GANHA de `packed-refs`, porque
    e assim que o git resolve -- `git gc` empacota a ref e um commit posterior
    escreve a solta de novo, e as duas passam a existir com valores diferentes.
    Ler a empacotada primeiro devolveria um commit antigo sem levantar nada.

    Branch recem-criado sem commit nenhum nao tem arquivo de ref: devolve sha
    vazio e o nome do ref. Vazio e resposta, nao erro -- a arvore existe, ela so
    nao tem commit.
    """
    try:
        bruto = (diretorio / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "", ""
    if not bruto:
        return "", ""
    if not bruto.startswith("ref:"):
        return bruto.split()[0], ""

    ref = bruto[len("ref:") :].strip()
    if not _ref_confinada(ref):
        return "", ""
    for base in (diretorio, comum):
        arquivo = base / ref
        try:
            if arquivo.is_file():
                conteudo = arquivo.read_text(encoding="utf-8", errors="replace").strip()
                if conteudo:
                    return conteudo.split()[0], ref
        except OSError:
            continue
    return _de_packed_refs(comum, ref), ref


def _ref_confinada(ref: str) -> bool:
    """Recusa ref que sairia de `refs/` -- ela vira caminho de arquivo.

    `HEAD` e conteudo de repositorio, e `INV-014` diz que conteudo de
    repositorio nao e confiavel. `ref: ../../../../etc/passwd` e um arquivo de
    duas linhas que faria este modulo ler fora da arvore, e `INV-002` confina a
    leitura ao repositorio. Sem esta guarda a leitura obedeceria.
    """
    return bool(_REF_ACEITA.match(ref)) and ".." not in ref.split("/")


def _de_packed_refs(comum: Path, ref: str) -> str:
    """Sha do ref em `packed-refs`, ou string vazia.

    Linha empacotada e `<sha> <ref>`. As linhas que comecam com `#` sao o
    cabecalho e as que comecam com `^` sao o objeto apontado por uma tag
    anotada -- essa segunda e a que enganaria uma leitura ingenua, porque ela
    vem LOGO DEPOIS da linha do ref e um `split()` cego pegaria o sha errado.
    """
    arquivo = comum / "packed-refs"
    try:
        if not arquivo.is_file():
            return ""
        linhas = arquivo.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for linha in linhas:
        if not linha or linha[0] in "#^":
            continue
        partes = linha.split()
        if len(partes) >= 2 and partes[1] == ref:
            return partes[0]
    return ""


# --------------------------------------------------------------------------
# SPEC 46 -- namespace de worktree
# --------------------------------------------------------------------------


def banco_da_arvore(raiz: str | os.PathLike[str]) -> Path:
    """Caminho do indice desta arvore, com nome derivado de branch e identidade.

    SPEC 46: `main-a91f.sqlite3`, `feature-glue6-16ae.sqlite3`. O nome carrega
    as DUAS partes porque nenhuma sozinha separa o que precisa ser separado --
    o branch distingue dois checkouts da mesma pasta, e a identidade distingue
    dois worktrees no mesmo branch (que o git permite via `--detach`, e que
    arvore copiada sem git produz sempre).

    O sufixo NAO inclui `head`, e a ausencia e o ponto: incluir faria cada
    commit gerar um arquivo novo, e o disco encheria de indices de um commit so.
    A identidade e do worktree, e worktree nao muda a cada commit.
    """
    base = Path(raiz).expanduser()
    estado = estado_da_arvore(base)
    material = f"{estado.identidade}\n{estado.impressao}"
    sufixo = hashlib.blake2b(material.encode("utf-8"), digest_size=_TAMANHO_DIGEST)
    nome = f"{_slug_do_ref(estado.ref)}-{sufixo.hexdigest()[:_SUFIXO_DE_WORKTREE]}"
    return base / DIRETORIO_DE_WORKTREES / f"{nome}.sqlite3"


def _slug_do_ref(ref: str) -> str:
    """`refs/heads/feature/glue6` -> `feature-glue6`, e o resto vira `detached`.

    O nome vira NOME DE ARQUIVO, entao ele passa por um alfabeto fechado em vez
    de por uma lista de caracteres proibidos: nome de branch aceita `/`, `.` e
    unicode, e `refs/heads/../../x` seria um caminho valido para o sistema de
    arquivos. Alfabeto fechado nao tem caso esquecido.
    """
    if not ref.startswith("refs/"):
        return "detached"
    resto = ref[len("refs/") :]
    for prefixo in ("heads/", "remotes/", "tags/"):
        if resto.startswith(prefixo):
            resto = resto[len(prefixo) :]
            break
    limpo = _NAO_ALFANUMERICO.sub("-", resto.lower()).strip("-")
    return limpo or "detached"


# --------------------------------------------------------------------------
# SPEC 42 -- deteccao de mudanca
# --------------------------------------------------------------------------


def detectar(raiz: str | os.PathLike[str], conexao: sqlite3.Connection) -> Mudancas:
    """Compara disco contra `files` e classifica cada arquivo.

    A ordem de conferencia e o desempenho inteiro: `size` e `mtime` vem do
    `stat` que a varredura ja faz, e o sha-256 exige LER o arquivo. Hashear
    tudo custaria a leitura da arvore inteira -- que e a parte que a
    sincronizacao existe para evitar. Entao o sha so entra quando o par
    (mtime, size) diverge, e ai ele decide entre `alterado` e `tocado`.

    O sha nao e dispensavel nesse ramo, e o motivo e medido em repositorio real:
    `git checkout` reescreve `mtime` de tudo que ele toca, inclusive de arquivo
    cujo conteudo volta a ser identico, e formatador que nao muda nada tambem.
    Sem o sha esses arquivos seriam reindexados a cada sincronizacao, e a
    economia sumiria justamente depois de um checkout -- que e quando ela mais
    vale.

    Recebe CONEXAO e nao caminho porque quem chama ja abriu o banco e vai
    escrever nele em seguida; abrir uma segunda conexao daria duas visoes do
    mesmo arquivo, e sob WAL a segunda pode nao ver o que a primeira escreveu.

    Arquivo que nao da `stat` conta como REMOVIDO quando estava no indice, e e
    ignorado quando nao estava. Fail-closed: sumiu entre a varredura e o `stat`,
    ou ficou sem permissao -- nos dois casos o indice nao pode continuar
    afirmando que ele tem os simbolos dele.
    """
    base = Path(raiz).expanduser()
    gravados = {
        linha[0]: (linha[1], linha[2], linha[3])
        for linha in conexao.execute(
            "SELECT path, content_sha256, size_bytes, modified_ns FROM files"
        )
    }

    inalterados: list[str] = []
    alterados: list[str] = []
    novos: list[str] = []
    tocados: list[str] = []
    vistos: set[str] = set()

    for caminho in iter_source_files(base, _PADRAO):
        relativo = caminho.relative_to(base).as_posix()
        try:
            informacao = caminho.stat()
        except OSError:
            continue
        vistos.add(relativo)
        anterior = gravados.get(relativo)
        if anterior is None:
            novos.append(relativo)
            continue
        sha_gravado, tamanho_gravado, mtime_gravado = anterior
        if informacao.st_size == tamanho_gravado and informacao.st_mtime_ns == mtime_gravado:
            inalterados.append(relativo)
            continue
        atual = _sha_do_arquivo(caminho)
        if atual is None:
            continue
        if atual == sha_gravado:
            inalterados.append(relativo)
            tocados.append(relativo)
        else:
            alterados.append(relativo)

    removidos = sorted(set(gravados) - vistos)
    return Mudancas(
        inalterados=tuple(inalterados),
        alterados=tuple(alterados),
        novos=tuple(novos),
        removidos=tuple(removidos),
        tocados=tuple(tocados),
    )


def _sha_do_arquivo(caminho: Path) -> str | None:
    """Sha-256 dos BYTES, ou `None` quando o arquivo nao pode ser lido.

    Dos bytes e nao do texto decodificado, pela mesma razao que em `index._ler`:
    normalizacao de fim de linha faria dois arquivos diferentes terem o mesmo
    digest, e e este digest que decide se o arquivo mudou.
    """
    try:
        return hashlib.sha256(caminho.read_bytes()).hexdigest()
    except OSError:
        return None


# --------------------------------------------------------------------------
# SPEC 42 -- sincronizacao incremental
# --------------------------------------------------------------------------


def sincronizar(
    raiz: str | os.PathLike[str], banco: str | os.PathLike[str]
) -> ResultadoSync:
    """Aplica so o que mudou, e grava o estado da arvore junto.

    Cai para reconstrucao completa quando nao ha o que aproveitar -- banco sem
    `files`, ou banco de OUTRA raiz. Nao ha caminho incremental honesto sobre
    banco de outra raiz: todo `files.path` la dentro e relativo aquela raiz, e
    reaproveitar linha por linha produziria caminho que nao existe.

    O estado da arvore e gravado AQUI e em nenhum outro lugar. `indexar` nao o
    grava, e a consequencia esta na docstring do modulo: indice construido pela
    via antiga e negado por `conferir_arvore` ate a primeira sincronizacao. E
    fail-closed de proposito -- gravar estado num indice que ninguem conferiu
    seria afirmar sobre a arvore uma coisa que nao foi medida.
    """
    inicio = time.perf_counter()
    base = Path(raiz).expanduser()
    caminho_do_banco = Path(banco)
    estado = estado_da_arvore(base)

    if _precisa_de_reconstrucao(caminho_do_banco, base):
        completo = indexar(base, caminho_do_banco)
        _registrar_estado(caminho_do_banco, estado)
        return _do_resultado_completo(completo, estado, time.perf_counter() - inicio)

    conexao = abrir(caminho_do_banco)
    try:
        criar_schema(conexao, base)
        mudancas = detectar(base, conexao)
        conexao.execute("BEGIN")
        try:
            reresolvidos, nos, ilegiveis, arestas, nao_resolvidas = _aplicar(
                conexao, base, mudancas
            )
            _gravar_estado(conexao, estado)
            _gravar_veredito(conexao, _VEREDITO_FRESCO)
            conexao.execute("COMMIT")
        except BaseException:
            # Mesma razao que em `index.indexar`: um `ROLLBACK` que levanta por
            # cima da causa real troca o traceback util por "cannot rollback".
            try:
                conexao.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
    finally:
        conexao.close()

    return ResultadoSync(
        mudancas=mudancas,
        reresolvidos=reresolvidos,
        arquivos=len(mudancas.alterados) + len(mudancas.novos),
        nos=nos,
        ilegiveis=ilegiveis,
        arestas=arestas,
        nao_resolvidas=nao_resolvidas,
        duracao_s=time.perf_counter() - inicio,
        completa=False,
        estado=estado,
    )


def _precisa_de_reconstrucao(banco: Path, base: Path) -> bool:
    """Banco ausente, vazio ou de outra raiz -- os tres casos sem meio-termo."""
    if not banco.is_file():
        return True
    conexao = abrir(banco)
    try:
        tem_files = conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
        ).fetchone()
        if tem_files is None:
            return True
        (quantos,) = conexao.execute("SELECT COUNT(*) FROM files").fetchone()
        if quantos == 0:
            return True
        gravada = conexao.execute(
            "SELECT value FROM metadata WHERE key = ?", (_METADATA_IMPRESSAO,)
        ).fetchone()
    finally:
        conexao.close()
    return gravada is None or gravada[0] != impressao_da_raiz(base)


def _do_resultado_completo(
    completo: Resultado, estado: EstadoDaArvore, duracao_s: float
) -> ResultadoSync:
    """Traduz o `Resultado` de `indexar` sem inventar campo incremental nenhum.

    `mudancas` sai VAZIO e `completa` sai `True`. Nao ha lista de mudanca numa
    reconstrucao -- o banco nao tinha o que comparar --, e forjar uma seria
    afirmar uma medicao que ninguem fez.
    """
    return ResultadoSync(
        mudancas=Mudancas(),
        reresolvidos=(),
        arquivos=completo.arquivos,
        nos=completo.nos,
        ilegiveis=completo.ilegiveis,
        arestas=completo.arestas,
        nao_resolvidas=completo.nao_resolvidas,
        duracao_s=duracao_s,
        completa=True,
        estado=estado,
    )


def _aplicar(
    conexao: sqlite3.Connection, base: Path, mudancas: Mudancas
) -> tuple[tuple[str, ...], int, int, int, int]:
    """O incremental inteiro, dentro da transacao de quem chama.

    A ordem e obrigatoria e cada passo depende do anterior:

    1. nomes REMOVIDOS antes do delete, porque depois eles nao existem mais
    2. dependentes antes do delete, porque o `CASCADE` apaga a aresta que os
       identifica
    3. `symbols_fts` na mao, porque FTS5 e tabela virtual e chave estrangeira
       nao a alcanca
    4. `DELETE FROM files`, que leva nos, pontos cegos e arestas em cascata
    5. inserir os arquivos novos e alterados
    6. nomes ACRESCENTADOS, que so existem depois do passo 5
    7. reunir os afetados e reparsear so as referencias deles
    8. resolver TUDO de uma vez contra o catalogo ja completo

    Resolver antes do passo 5 daria `NO_CANDIDATE` para simbolo que estava a
    ser inserido, e a taxa de resolucao passaria a depender da ordem -- o mesmo
    defeito que `index.indexar` documenta e evita.
    """
    alvos = tuple(mudancas.alterados) + tuple(mudancas.novos) + tuple(mudancas.removidos)
    _preencher_temporaria(conexao, "sync_alvos", alvos)

    nomes_delta = _nomes_dos_alvos(conexao)
    dependentes = _fontes_dependentes(conexao)

    conexao.execute(
        "DELETE FROM symbols_fts WHERE node_id IN ("
        " SELECT nodes.id FROM nodes"
        " JOIN files ON files.id = nodes.file_id"
        " JOIN sync_alvos ON sync_alvos.path = files.path)"
    )
    conexao.execute("DELETE FROM files WHERE path IN (SELECT path FROM sync_alvos)")

    referencias: dict[str, list[Referencia]] = {}
    nos_inseridos = 0
    ilegiveis = 0
    for relativo in tuple(mudancas.alterados) + tuple(mudancas.novos):
        quantos = _indexar_um(conexao, base, relativo, referencias)
        if quantos is None:
            ilegiveis += 1
            continue
        nos_inseridos += quantos

    nomes_delta |= _nomes_dos_alvos(conexao)
    _preencher_temporaria(conexao, "sync_nomes", tuple(sorted(nomes_delta)))

    ja_parseados = set(referencias)
    afetados = sorted(
        (dependentes | _candidatos_por_nome(conexao) | _fontes_com_alvo_no_delta(conexao))
        - ja_parseados
        - set(mudancas.removidos)
    )
    _preencher_temporaria(conexao, "sync_reresolvidos", tuple(afetados))
    _apagar_resolucao_dos_reresolvidos(conexao)
    for relativo in afetados:
        _referencias_de(base, relativo, referencias)

    for relativo in mudancas.tocados:
        _atualizar_mtime(conexao, base, relativo)

    arestas, nao_resolvidas = _resolver_e_gravar(conexao, referencias)
    return tuple(afetados), nos_inseridos, ilegiveis, arestas, nao_resolvidas


def _preencher_temporaria(
    conexao: sqlite3.Connection, tabela: str, valores: tuple[str, ...]
) -> None:
    """Passa uma lista de caminhos para o SQL sem interpolar SQL.

    Tabela temporaria e nao `IN (?,?,?)` por duas razoes que valem sozinhas: a
    lista de placeholders teria que ser montada por concatenacao -- construir
    SQL por string e o que `INV-008` proibe --, e SQLite tem teto de parametros
    por instrucao, entao a versao com placeholders quebraria justamente na
    sincronizacao grande, que e a que ninguem testa a mao.

    O nome da tabela e literal de codigo, nunca argumento de fora.
    """
    if tabela not in _TEMPORARIAS:
        raise ValueError(f"tabela temporaria desconhecida: {tabela!r}")
    conexao.execute(_TEMPORARIAS[tabela])
    conexao.execute(_LIMPAR[tabela])
    conexao.executemany(_INSERIR[tabela], [(valor,) for valor in valores])


_TEMPORARIAS = {
    "sync_alvos": "CREATE TEMP TABLE IF NOT EXISTS sync_alvos (path TEXT PRIMARY KEY)",
    "sync_nomes": "CREATE TEMP TABLE IF NOT EXISTS sync_nomes (nome TEXT PRIMARY KEY)",
    "sync_reresolvidos": (
        "CREATE TEMP TABLE IF NOT EXISTS sync_reresolvidos (path TEXT PRIMARY KEY)"
    ),
}

_LIMPAR = {
    "sync_alvos": "DELETE FROM sync_alvos",
    "sync_nomes": "DELETE FROM sync_nomes",
    "sync_reresolvidos": "DELETE FROM sync_reresolvidos",
}

_INSERIR = {
    "sync_alvos": "INSERT OR IGNORE INTO sync_alvos (path) VALUES (?)",
    "sync_nomes": "INSERT OR IGNORE INTO sync_nomes (nome) VALUES (?)",
    "sync_reresolvidos": "INSERT OR IGNORE INTO sync_reresolvidos (path) VALUES (?)",
}


def _nomes_dos_alvos(conexao: sqlite3.Connection) -> set[str]:
    """`name` e `qualified_name` dos nos que vivem nos arquivos alvo.

    A metade `qualified_name` E CINTO, e nao necessidade -- MEDIDO, e o oposto
    do que esta docstring dizia antes de ser medida. Sobre este repositorio, com
    11268 pontos cegos e 3036 nomes qualificados que nao sao `name` de ninguem:

        referencias que casam SO por qualified_name   0

    A causa esta em `refs.py`: `Pipeline.processar(x)` vira
    `Referencia(nome="processar", receptor="Pipeline")`, entao
    `reference_name` guarda sempre o nome SIMPLES. Nao ha forma de referencia
    que produza o nome qualificado hoje.

    Fica porque `reference_name` e o que o extractor emitir, e o extractor muda:
    lineage de import (SPEC 36) tende a emitir caminho pontuado. Errar para mais
    custa uma linha na tabela temporaria; errar para menos deixaria ponto cego
    que nunca mais e reavaliado, e ponto cego que sobra e indistinguivel de
    ponto cego real.

    A MUTACAO QUE APAGA ESTA METADE SOBREVIVE A SUITE, e sobrevive com razao:
    nao ha caso nesta arvore que a exercite, e forjar um exigiria uma
    `Referencia` que o extractor nao produz. O registro aqui e o que substitui
    o teste que nao existe.
    """
    return {
        linha[0]
        for linha in conexao.execute(
            "SELECT nodes.name FROM nodes"
            " JOIN files ON files.id = nodes.file_id"
            " JOIN sync_alvos ON sync_alvos.path = files.path"
            " UNION"
            " SELECT nodes.qualified_name FROM nodes"
            " JOIN files ON files.id = nodes.file_id"
            " JOIN sync_alvos ON sync_alvos.path = files.path"
        )
    }


def _fontes_dependentes(conexao: sqlite3.Connection) -> set[str]:
    """Arquivos INALTERADOS que tinham aresta entrando num arquivo alvo.

    Esta consulta roda ANTES do delete, e nao depois, porque e a propria aresta
    que identifica o dependente -- depois do `CASCADE` ela nao existe mais e a
    pergunta fica sem como ser feita. Foi este o defeito que a docstring do
    modulo descreve no item 2: o no reinserido e identico, e a aresta de
    terceiro nao volta sozinha.
    """
    return {
        linha[0]
        for linha in conexao.execute(
            "SELECT DISTINCT origem.path FROM edges"
            " JOIN nodes AS fonte ON fonte.id = edges.source_id"
            " JOIN files AS origem ON origem.id = fonte.file_id"
            " JOIN nodes AS alvo ON alvo.id = edges.target_id"
            " JOIN files AS destino ON destino.id = alvo.file_id"
            " JOIN sync_alvos ON sync_alvos.path = destino.path"
            " WHERE origem.path NOT IN (SELECT path FROM sync_alvos)"
        )
    }


def _candidatos_por_nome(conexao: sqlite3.Connection) -> set[str]:
    """Arquivos com ponto cego cujo nome entrou ou saiu do catalogo.

    Ponto cego `NO_CANDIDATE` sobre `processar` deixa de ser ponto cego no
    instante em que alguem define `processar` -- e o inverso tambem vale: aresta
    vira `AMBIGUOUS` quando aparece a segunda definicao. Sem esta consulta o
    indice manteria os dois erros ate a proxima reconstrucao completa, e os dois
    sao silenciosos.
    """
    return {
        linha[0]
        for linha in conexao.execute(
            "SELECT DISTINCT files.path FROM unresolved_refs"
            " JOIN files ON files.id = unresolved_refs.file_id"
            " JOIN sync_nomes ON sync_nomes.nome = unresolved_refs.reference_name"
        )
    }


def _fontes_com_alvo_no_delta(conexao: sqlite3.Connection) -> set[str]:
    """Arquivos cuja aresta JA RESOLVIDA aponta para um nome que entrou no delta.

    Esta e a terceira fonte, e ela foi acrescentada porque a suite pegou o
    defeito -- as duas primeiras nao bastavam. O caso, medido em
    `test_incremental_produz_o_mesmo_grafo_que_reconstrucao_completa`:

        lib.py   define `processar`
        job.py   chama `processar`  -> ARESTA para lib.processar
        lib2.py  ACRESCENTADO, define `processar` tambem

    A reconstrucao completa transforma a aresta de `job.py` em ponto cego
    `AMBIGUOUS`, porque agora ha dois candidatos. O incremental nao a
    transformava: `job.py` nao tinha ponto cego (entao `_candidatos_por_nome`
    nao o via) e a aresta dele entrava em `lib.py`, que NAO e alvo (entao
    `_fontes_dependentes` tambem nao). O indice ficava afirmando uma aresta que
    a linguagem ja nao decide -- exatamente o tipo de erro que nao levanta.

    Casa por `nodes.name` e nao por `qualified_name` porque o delta sempre
    contem o `name` de todo no acrescentado ou removido, e ambiguidade exige
    nome qualificado igual, que por construcao implica `name` igual. Casar
    pelas duas colunas nao acrescentaria linha nenhuma e custaria um `OR` num
    join sobre `edges`.
    """
    return {
        linha[0]
        for linha in conexao.execute(
            "SELECT DISTINCT origem.path FROM edges"
            " JOIN nodes AS fonte ON fonte.id = edges.source_id"
            " JOIN files AS origem ON origem.id = fonte.file_id"
            " JOIN nodes AS alvo ON alvo.id = edges.target_id"
            " JOIN sync_nomes ON sync_nomes.nome = alvo.name"
            " WHERE origem.path NOT IN (SELECT path FROM sync_alvos)"
        )
    }


def _apagar_resolucao_dos_reresolvidos(conexao: sqlite3.Connection) -> None:
    """Tira arestas e pontos cegos dos afetados, que serao reescritos agora.

    Os NOS deles ficam: eles nao mudaram, e apagar o arquivo para reinserir
    identico trocaria trabalho por risco -- os ids seriam recalculados e
    qualquer divergencia de calculo viraria no fantasma.

    Sem este passo a resolucao seguinte ACRESCENTARIA a aresta antiga em vez de
    substitui-la, e `edges` nao tem chave unica (duas chamadas iguais na mesma
    linha sao duas arestas, de proposito). O indice passaria a contar cada
    chamada duas vezes a cada sincronizacao.
    """
    conexao.execute(
        "DELETE FROM edges WHERE source_id IN ("
        " SELECT nodes.id FROM nodes"
        " JOIN files ON files.id = nodes.file_id"
        " JOIN sync_reresolvidos ON sync_reresolvidos.path = files.path)"
    )
    conexao.execute(
        "DELETE FROM unresolved_refs WHERE file_id IN ("
        " SELECT files.id FROM files"
        " JOIN sync_reresolvidos ON sync_reresolvidos.path = files.path)"
    )


def _indexar_um(
    conexao: sqlite3.Connection,
    base: Path,
    relativo: str,
    referencias: dict[str, list[Referencia]],
) -> int | None:
    """Grava um arquivo e guarda as referencias dele. `None` quando ilegivel.

    Reusa `index._ler` e `index._gravar` em vez de repetir o calculo do
    `content_sha256`, do `file_id` e do `INSERT`. Sao privados, e importa-los e
    escolha: duplicar a regra daria DOIS lugares decidindo como um arquivo vira
    linha, e bastaria um deles mudar para a sincronizacao gravar `files`
    diferente do que `indexar` grava -- divergencia que nao levanta, so devolve
    resultado diferente conforme o caminho tomado. Um rename quebra o import em
    voz alta; a duplicacao quebraria calada.
    """
    caminho = base / relativo
    lido = _ler(caminho)
    if lido is None:
        return None
    dados, fonte, modificado_ns = lido
    nos = extrair_nos_ou_none(fonte, relativo)
    if nos is None:
        # DIVERGE DE `index.indexar` DE PROPOSITO, e a divergencia foi medida.
        #
        # `indexar` conta o ilegivel e nao grava linha em `files`. Para uma
        # reconstrucao isso nao custa nada; para a sincronizacao custa que o
        # arquivo fique ETERNAMENTE `novo` -- ele esta no disco e nunca no
        # indice --, e entao toda query fora do cooldown dispara uma
        # sincronizacao que reparseia o mesmo arquivo quebrado e volta a nao
        # grava-lo. Medido neste repositorio: `fixtures/graph/
        # fonte_que_nao_compila/input/carga_quebrada.py` fazia
        # `Mudancas.vazio` ser falso para sempre, e o frescor nunca assentava.
        #
        # A linha gravada nao mente: o arquivo FOI varrido, tem sha, tamanho e
        # mtime, e produziu zero no -- que e exatamente o que aconteceu. O
        # preco e que `files` fica com uma linha a mais que a reconstrucao
        # completa produziria, ate a sincronizacao seguinte. Converge em uma
        # rodada, e a alternativa nao converge nunca.
        # `fonte` NAO entra aqui de proposito: o arquivo nao parseou, e
        # `lineage.construir` sobre ele devolveria grafo vazio de qualquer
        # forma. Passa-la faria parecer que o fluxo de dado foi medido.
        _gravar(conexao, relativo, dados, modificado_ns, [])
        return None
    # `fonte` entra para que `data_flow` seja reescrita junto com `nodes`. Sem
    # isso o incremental deixaria a linhagem do arquivo alterado com o conteudo
    # da versao anterior -- e linhagem velha com cara de medida e pior que
    # linhagem ausente.
    _gravar(conexao, relativo, dados, modificado_ns, nos, fonte)
    referencias[relativo] = extrair_referencias(fonte, relativo)
    return len(nos)


def _referencias_de(
    base: Path, relativo: str, referencias: dict[str, list[Referencia]]
) -> None:
    """Reparseia um arquivo INALTERADO so para reextrair referencia.

    Este e o custo que a docstring do modulo chama de teto do ganho: a
    referencia crua nao e persistida em lugar nenhum, entao nao ha como
    reresolver sem parsear de novo. O arquivo nao e regravado -- os nos dele
    estao corretos, so a resolucao mudou.

    Arquivo ilegivel aqui NAO conta como ilegivel do resultado: ele ja esta no
    indice, foi lido com sucesso quando entrou, e o que aconteceu e que ele
    sumiu ou quebrou entre uma sincronizacao e outra. Contar dois eventos
    diferentes no mesmo numero faria o numero perder sentido.
    """
    lido = _ler(base / relativo)
    if lido is None:
        return
    referencias[relativo] = extrair_referencias(lido[1], relativo)


def _atualizar_mtime(conexao: sqlite3.Connection, base: Path, relativo: str) -> None:
    """Alinha o `mtime` gravado ao do disco para conteudo que nao mudou.

    Sem isto, `git checkout` que reescreve `mtime` sem mudar conteudo faria toda
    sincronizacao seguinte reler e rehashear os mesmos arquivos para sempre --
    a economia do par (mtime, size) sumiria justamente depois do evento que ela
    mais precisa cobrir.
    """
    try:
        modificado_ns = (base / relativo).stat().st_mtime_ns
    except OSError:
        return
    conexao.execute(
        "UPDATE files SET modified_ns = ? WHERE path = ?", (modificado_ns, relativo)
    )


def _resolver_e_gravar(
    conexao: sqlite3.Connection, referencias: dict[str, list[Referencia]]
) -> tuple[int, int]:
    """Resolve o conjunto afetado contra o catalogo INTEIRO e grava as duas metades.

    O catalogo vem do banco depois de todas as insercoes, e nao das referencias
    em memoria: aresta tem que apontar para o id que `nodes` guarda, e um id
    recalculado a partir do AST casa hoje e diverge no dia em que a assinatura
    mudar de forma -- e aresta apontando para no inexistente nao levanta, so
    devolve nada.

    A resolucao roda sobre o conjunto afetado e nao sobre a arvore toda, e e
    exatamente por isso que `_fontes_dependentes` e `_candidatos_por_nome`
    existem: elas sao o que garante que o conjunto afetado contenha todo arquivo
    cuja resposta pode ter mudado. Se elas errarem para menos, este atalho passa
    a mentir.
    """
    if not referencias:
        return 0, 0
    catalogo = catalogo_do_banco(conexao)
    resolucao = resolver(referencias, catalogo)
    conexao.executemany(
        "INSERT INTO edges (source_id, target_id, kind, line, confidence)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (a.source_id, a.target_id, a.kind, a.line, a.confidence)
            for a in resolucao.arestas
        ],
    )
    conexao.executemany(
        "INSERT INTO unresolved_refs"
        " (source_id, reference_name, reference_kind, file_id, line, reason)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                nao.source_id,
                nao.reference_name,
                nao.reference_kind,
                id_de_arquivo(nao.caminho),
                nao.line,
                nao.reason,
            )
            for nao in resolucao.nao_resolvidas
        ],
    )
    return len(resolucao.arestas), len(resolucao.nao_resolvidas)


# --------------------------------------------------------------------------
# SPEC 44 -- strict tree
# --------------------------------------------------------------------------


def estado_gravado(conexao: sqlite3.Connection) -> EstadoDaArvore | None:
    """Estado da arvore que o indice afirma sobre si, ou `None` se ele nao afirma.

    `None` e diferente de `EstadoDaArvore()` vazio, e a distincao decide a
    recusa: vazio e "arvore sem git", que e um estado legitimo e comparavel;
    `None` e "este indice nunca disse para qual arvore ele foi feito", que sob
    `INV-015` nao pode virar suposicao de que ele serve.
    """
    gravado = dict(
        conexao.execute(
            "SELECT key, value FROM metadata WHERE key IN (?, ?, ?, ?)",
            (
                _METADATA_HEAD,
                _METADATA_REF,
                _METADATA_IDENTIDADE,
                _METADATA_IMPRESSAO,
            ),
        )
    )
    if _METADATA_IDENTIDADE not in gravado:
        return None
    return EstadoDaArvore(
        head=gravado.get(_METADATA_HEAD, ""),
        ref=gravado.get(_METADATA_REF, ""),
        identidade=gravado.get(_METADATA_IDENTIDADE, ""),
        impressao=gravado.get(_METADATA_IMPRESSAO, ""),
    )


def _gravar_estado(conexao: sqlite3.Connection, estado: EstadoDaArvore) -> None:
    """Grava os quatro campos. `criar_schema` ja escreve `root_fingerprint`.

    Escrito de novo aqui de proposito: `criar_schema` grava a impressao a partir
    da raiz que recebeu, e `sincronizar` grava a partir do estado que conferiu.
    Sao a mesma coisa hoje; se um dia deixarem de ser, o valor que vale e o do
    estado, porque e ele que `conferir_arvore` compara.
    """
    conexao.executemany(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        (
            (_METADATA_HEAD, estado.head),
            (_METADATA_REF, estado.ref),
            (_METADATA_IDENTIDADE, estado.identidade),
            (_METADATA_IMPRESSAO, estado.impressao),
        ),
    )


def _registrar_estado(banco: Path, estado: EstadoDaArvore) -> None:
    """Abre so para gravar o estado, depois de uma reconstrucao completa."""
    conexao = abrir(banco)
    try:
        conexao.execute("BEGIN")
        _gravar_estado(conexao, estado)
        _gravar_veredito(conexao, _VEREDITO_FRESCO)
        conexao.execute("COMMIT")
    finally:
        conexao.close()


def _gravar_veredito(conexao: sqlite3.Connection, veredito: str) -> None:
    """Carimba o resultado da ultima conferencia, com a hora dela.

    O veredito acompanha a hora porque o cooldown so pode pular a varredura
    quando a ultima conferencia disse FRESCO. Guardar so a hora faria o cooldown
    pular tambem depois de um veredito de STALE, e o indice velho responderia
    por mais 30 s -- exatamente o que a SPEC 43 proibe na ultima linha.
    """
    conexao.executemany(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        (
            (_METADATA_CHECADO_NS, str(time.time_ns())),
            (_METADATA_VEREDITO, veredito),
        ),
    )


def conferir_arvore(raiz: str | os.PathLike[str], conexao: sqlite3.Connection) -> None:
    """SPEC 44. Levanta `ArvoreDivergente` quando o indice nao e desta arvore.

    Nao ha modo permissivo, e a ausencia dele e a secao inteira: um parametro
    `strict=False` seria usado no dia de pressa, e o resultado de responder com
    o grafo do outro branch e indistinguivel de responder certo -- os simbolos
    existem, os caminhos existem, e as linhas apontam para outro codigo.
    """
    atual = estado_da_arvore(raiz)
    gravado = estado_gravado(conexao)
    if gravado is None:
        raise ArvoreDivergente(
            "o indice nao registra para qual arvore foi construido; "
            f"sincronize com `{ACAO_DE_SYNC}`.",
            reason="NO_TREE_STATE",
            tree_head=atual.head,
        )
    if gravado.fingerprint == atual.fingerprint:
        return
    raise ArvoreDivergente(
        "o indice foi construido para outra arvore "
        f"(indice HEAD {gravado.head or '-'} ref {gravado.ref or '-'}; "
        f"arvore HEAD {atual.head or '-'} ref {atual.ref or '-'}); "
        f"sincronize com `{ACAO_DE_SYNC}`.",
        reason="HEAD_MISMATCH" if gravado.head != atual.head else "FINGERPRINT_MISMATCH",
        index_head=gravado.head,
        tree_head=atual.head,
        index_ref=gravado.ref,
        tree_ref=atual.ref,
    )


# --------------------------------------------------------------------------
# SPEC 43 -- frescor automatico
# --------------------------------------------------------------------------


def garantir_frescor(
    raiz: str | os.PathLike[str],
    banco: str | os.PathLike[str],
    *,
    cooldown_s: float = COOLDOWN_S,
    max_auto_sync_files: int = MAX_AUTO_SYNC_FILES,
    auto_sync: bool = True,
) -> Frescor:
    """Confere antes de responder, sincroniza se couber, e recusa se nao couber.

    A ordem das quatro portas e o contrato:

    1. indice ausente -> `IndiceAusente`. Indexar aqui poria 3.7 s dentro do
       caminho de uma pergunta, e sem aviso nenhum de que isso ia acontecer.
    2. estado da arvore -> divergiu ou nunca foi gravado. NAO passa pelo
       cooldown: ler `.git/HEAD` sao dois `read_text`, e e o unico sinal que
       pega `git checkout` de outro branch no instante em que ele acontece.
    3. cooldown (SPEC 43, 30 s) -> pula so a VARREDURA de disco, e so quando a
       ultima conferencia disse fresco.
    4. varredura -> ate `max_auto_sync_files` sincroniza na hora; acima disso
       recusa com `STALE_INDEX` e a contagem.

    Com `auto_sync=False` a porta 4 recusa em vez de sincronizar. E o modo de
    quem quer conferir sem escrever -- leitor concorrente, ou conferencia que
    nao pode custar o tempo da sincronizacao.

    Arvore divergente com ZERO arquivo alterado ainda sincroniza, e nao passa
    direto: a sincronizacao de zero arquivo nao reindexa nada, ela so grava o
    estado novo -- que e a prova que faltava. Deixar passar sem gravar faria a
    proxima query repetir a mesma conferencia, para sempre.
    """
    base = Path(raiz).expanduser()
    caminho = Path(banco)
    if not caminho.is_file():
        raise IndiceAusente(
            f"indice inexistente: {caminho.as_posix()}; construa com `{ACAO_DE_SYNC}`.",
            db=caminho.as_posix(),
        )

    conexao = abrir(caminho)
    try:
        divergiu = False
        try:
            conferir_arvore(base, conexao)
        except ArvoreDivergente:
            if not auto_sync:
                raise
            divergiu = True

        if not divergiu and _dentro_do_cooldown(conexao, cooldown_s):
            return Frescor(verificou=False, sincronizou=False)

        mudancas = detectar(base, conexao)
        if mudancas.vazio and not divergiu:
            conexao.execute("BEGIN")
            _gravar_veredito(conexao, _VEREDITO_FRESCO)
            conexao.execute("COMMIT")
            return Frescor(verificou=True, sincronizou=False, mudancas=mudancas)

        if not auto_sync or mudancas.quantidade > max_auto_sync_files:
            conexao.execute("BEGIN")
            _gravar_veredito(conexao, _VEREDITO_STALE)
            conexao.execute("COMMIT")
            raise IndiceDesatualizado(
                f"o indice esta atras da arvore em {mudancas.quantidade} arquivos; "
                f"sincronize com `{ACAO_DE_SYNC}`.",
                changed_files=mudancas.quantidade,
            )
    finally:
        conexao.close()

    sincronizar(base, caminho)
    return Frescor(verificou=True, sincronizou=True, mudancas=mudancas)


def _dentro_do_cooldown(conexao: sqlite3.Connection, cooldown_s: float) -> bool:
    """Verdadeiro so quando a ultima conferencia foi recente E disse fresco.

    As duas condicoes, e nao so a hora. Cooldown que ignora o veredito
    transformaria uma recusa por `STALE_INDEX` em 30 s de respostas com o grafo
    velho -- o oposto exato do que a secao 43 termina exigindo.

    Cooldown zero ou negativo desliga a porta, e isso e o que os testes usam
    para nao depender de relogio. Nao ha caminho em que ele ative sem que
    alguem tenha carimbado um veredito FRESCO antes.
    """
    if cooldown_s <= 0:
        return False
    gravado = dict(
        conexao.execute(
            "SELECT key, value FROM metadata WHERE key IN (?, ?)",
            (_METADATA_CHECADO_NS, _METADATA_VEREDITO),
        )
    )
    if gravado.get(_METADATA_VEREDITO) != _VEREDITO_FRESCO:
        return False
    bruto = gravado.get(_METADATA_CHECADO_NS)
    if not bruto:
        return False
    try:
        quando_ns = int(bruto)
    except ValueError:
        return False
    return (time.time_ns() - quando_ns) < int(cooldown_s * 1_000_000_000)


__all__ = [
    "ACAO_DE_SYNC",
    "COOLDOWN_S",
    "MAX_AUTO_SYNC_FILES",
    "ArvoreDivergente",
    "EstadoDaArvore",
    "Frescor",
    "IndiceAusente",
    "IndiceDesatualizado",
    "Mudancas",
    "NegadoPorFrescor",
    "ResultadoSync",
    "banco_da_arvore",
    "conferir_arvore",
    "detectar",
    "estado_da_arvore",
    "estado_gravado",
    "garantir_frescor",
    "sincronizar",
]
