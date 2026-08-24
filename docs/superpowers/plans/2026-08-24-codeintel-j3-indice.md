# SparkForge Code Intelligence — fase J3, o índice

> **Para trabalhadores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> `superpowers:subagent-driven-development` (recomendado) ou
> `superpowers:executing-plans` para implementar este plano tarefa a tarefa. Os
> passos usam caixas de seleção (`- [ ]`) para acompanhamento.

**Objetivo:** persistir o que os extratores já produzem num índice SQLite local,
e responder "onde está X" sem ler arquivo — começando pelo próprio
`spark-forge-aws`, que é o repositório com consumidor imediato.

**Arquitetura:** um pacote novo, `sparkforge/codeintel/`, com banco SQLite +
FTS5 da biblioteca padrão. Ele **consome** a varredura de `facts/scan.py` e o
`ast` que os extratores já usam — não reimplementa nem um nem outro. Nenhuma
tool MCP nova nesta fase.

**Pilha:** Python ≥3.10, só biblioteca padrão (`sqlite3`, `ast`, `hashlib`,
`pathlib`). Zero dependência nova — é requisito, não preferência.

---

## O que já foi medido, e o que isso decide

Tudo abaixo foi medido neste repositório antes de escrever o plano. Quem
executar deve **confirmar**, não repetir de confiança.

**Viabilidade do Tier 0**, na versão local (Python 3.14.6, sqlite 3.50.4):

```
pragmas WAL/foreign_keys/synchronous/temp_store/busy_timeout : aceitos
FTS5 CREATE VIRTUAL TABLE + MATCH                            : ok
BLAKE2b deterministico, digest_size=16                       : ok, id de 37 chars
5668 ids gerados                                             : 6 ms
```

**Tamanho do alvo**, usando `iter_source_files` (a varredura da fase J0, com
denylist):

```
369 arquivos .py, 3591 KB
368 modulos parseaveis
761 class + 4907 function = 5668 simbolos de topo
indice estimado: ~1,1 MB de metadado
```

**Isto decide duas coisas.** O índice cabe folgado em SQLite, e a geração de id
não é gargalo. E o alvo é o próprio repositório: 369 arquivos é grande o
bastante para o ganho aparecer e pequeno o bastante para reindexar inteiro em
segundos, o que torna o incremental (fase J4) uma otimização e não um
pré-requisito.

**Uma ressalva que o plano herda e não resolve.** O CI roda Python 3.10 e 3.11;
as medições acima são de 3.14.6. Nada no repositório mede FTS5 nas versões
suportadas, e o módulo `ast` mudou no intervalo (`ast.Str` e `ast.Num` saíram em
3.12). A Task 1 mede isso antes de qualquer outra coisa — se FTS5 faltar em
alguma versão suportada, o plano para e a decisão sobe.

## O que NÃO está nesta fase

- **Incremental** (§42). Reindexar 369 arquivos é barato; medir quanto custa é
  parte da Task 6, e o incremental entra em J4 com o número na mão.
- **Ranking e `ContextPack`** (§47–55). Sem ranking, `search` devolve em ordem
  determinística — o que já serve para "onde está X".
- **Tools MCP** (§56–67). O mapa recusou criá-las antes de existir o que elas
  consultariam, e a razão continua: uma tool sem índice responde igual a um
  modelo sem ferramenta, e cada tool nova entra no gate de paridade para sempre.
- **Corpo de função no banco** (§20, `INV-010`). O banco guarda metadado e
  posição; quem quiser o código lê o arquivo pela posição.

## Decisões que o plano fixa

**O banco é descartável.** Ele é derivado do código e reconstruível a qualquer
momento. Nada no motor pode depender dele para responder — se o índice sumir, a
análise determinística continua funcionando como hoje. Isso é o que permite
`synchronous=NORMAL`.

**O banco não guarda corpo de função.** `INV-010` da SPEC. O que se guarda é
nome, nome qualificado, tipo, arquivo relativo, posição e assinatura
normalizada. Assinatura **sem valor literal**: `def connect(password="x")` vira
`connect(password=<literal>)`, pela §25 — o default é onde credencial aparece.

**Caminho sempre relativo à raiz.** `metadata` não guarda caminho absoluto
(§21). Isso é o que torna o banco movível e o que impede o nome da máquina de
vazar para um artefato.

**`unresolved` é primeira classe.** Referência que o AST não resolve vira linha
em `unresolved_refs` com razão, nunca aresta inventada. É o princípio que
`graph.unresolved` e `sql.unresolved` já aplicam no repositório.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/codeintel/__init__.py` | Superfície pública do pacote |
| `sparkforge/codeintel/db.py` | Schema, conexão, pragmas, migração de versão |
| `sparkforge/codeintel/ids.py` | Id determinístico e assinatura normalizada |
| `sparkforge/codeintel/extract.py` | AST → nós e referências, sobre `iter_source_files` |
| `sparkforge/codeintel/index.py` | Orquestra varredura → extração → banco |
| `sparkforge/codeintel/search.py` | Consulta por nome e por nome qualificado |
| `sparkforge/adapters/cli.py` | Verbo `code` com `index`, `search`, `status` |
| `tests/test_codeintel_db.py` | Schema, pragmas, versão, reconstrutibilidade |
| `tests/test_codeintel_ids.py` | Determinismo, colisão, sanitização de assinatura |
| `tests/test_codeintel_extract.py` | Nós, posições, `unresolved`, ausência de corpo |
| `tests/test_codeintel_index.py` | Ponta a ponta sobre fixture, e sobre o próprio repo |
| `tests/test_codeintel_search.py` | Busca, ordem determinística, escape de FTS |

---

## Os três tipos que atravessam as tarefas

Definidos aqui porque as tarefas os usam antes de os criar, e um plano que
referencia atributo de tipo não declarado obriga quem executa a adivinhar.

`No`, devolvido por `extrair_nos` (Task 4) e consumido por `indexar` (Task 5):

```python
@dataclass(frozen=True)
class No:
    """Um simbolo extraido do AST, sem o corpo dele.

    `normalized_signature` ja vem por `normalizar_assinatura`, entao nenhum
    valor literal de default chega aqui -- e daqui ao banco, que persiste.
    """

    kind: str                      # "class" | "function" | "method"
    name: str                      # `executar`
    qualified_name: str            # `Pipeline.executar`
    path: str                      # relativo a raiz, sempre
    start_line: int
    end_line: int
    normalized_signature: str
```

`Resultado`, devolvido por `indexar` (Task 5):

```python
@dataclass(frozen=True)
class Resultado:
    """O que uma indexacao produziu, e o que ela NAO conseguiu ler.

    `ilegiveis` e primeira classe de proposito: arquivo que nao parseia e ponto
    cego, e ponto cego contado e diferente de ponto cego silencioso -- que e a
    lacuna que `facts/scan.py` ja registra como pendencia.
    """

    arquivos: int
    nos: int
    ilegiveis: int
    duracao_s: float
```

`Achado`, devolvido por `buscar` (Task 6):

```python
@dataclass(frozen=True)
class Achado:
    """Uma linha de resultado de busca.

    Ela carrega o suficiente para o chamador ir ao codigo -- `path` mais
    `start_line` -- sem que o indice precise guardar o codigo.
    """

    node_id: str
    name: str
    qualified_name: str
    kind: str
    path: str
    start_line: int
```

---

## Task 1: a viabilidade nas versões que o CI roda

**Arquivos:**
- Criar: `tests/test_codeintel_db.py`

Esta tarefa vem primeiro porque ela pode **parar o plano**. Se FTS5 não existir
numa versão suportada, nada do resto se sustenta.

- [ ] **Passo 1: escrever o teste de viabilidade**

```python
"""O que o indice exige do interpretador, verificado onde o CI roda.

Este arquivo vem antes de qualquer schema de proposito. As medicoes que
justificam a fase foram feitas em Python 3.14.6, e o `pyproject.toml` declara
suporte a partir do 3.10 -- FTS5 e compilado opcional do SQLite, e um ambiente
sem ele faria o indice falhar na criacao, nao na consulta. Melhor descobrir num
teste nomeado do que num traceback de usuario.
"""

import sqlite3

import pytest


def test_fts5_esta_disponivel():
    conexao = sqlite3.connect(":memory:")
    try:
        conexao.execute("CREATE VIRTUAL TABLE t USING fts5(a, b)")
    except sqlite3.OperationalError as erro:  # pragma: no cover - so em build sem FTS5
        pytest.fail(
            "FTS5 ausente neste interpretador: o indice de codigo depende dele. "
            f"sqlite {sqlite3.sqlite_version}, erro: {erro}"
        )
    finally:
        conexao.close()


def test_fts5_casa_termo_dentro_de_nome_composto():
    """`iter_source_files` tem que ser achavel por `source`.

    O tokenizador default do FTS5 quebra em nao-alfanumerico, entao
    `iter_source_files` vira tres tokens. Se isso deixar de valer, a busca por
    parte de nome para de funcionar e nenhum outro teste acusa.
    """
    conexao = sqlite3.connect(":memory:")
    conexao.execute("CREATE VIRTUAL TABLE t USING fts5(node_id UNINDEXED, name)")
    conexao.execute("INSERT INTO t VALUES ('n1', 'iter_source_files')")
    achados = conexao.execute("SELECT node_id FROM t WHERE t MATCH 'source'").fetchall()
    conexao.close()
    assert achados == [("n1",)]


@pytest.mark.parametrize(
    "pragma",
    ["journal_mode=WAL", "foreign_keys=ON", "synchronous=NORMAL",
     "temp_store=MEMORY", "busy_timeout=30000"],
)
def test_pragma_e_aceito(pragma):
    conexao = sqlite3.connect(":memory:")
    try:
        conexao.execute(f"PRAGMA {pragma}")
    finally:
        conexao.close()
```

- [ ] **Passo 2: rodar**

```
python -m pytest tests/test_codeintel_db.py -q
```
Esperado: **todos passam** na sua versão local.

- [ ] **Passo 3: medir nas versões do CI**

Leia `.github/workflows/` e descubra quais versões de Python o CI roda.
Se houver interpretador de alguma delas disponível na máquina, rode o arquivo
com ele. Se não houver, **diga isso no relatório** — não presuma que passa.

Se FTS5 faltar em alguma versão suportada, **pare** e reporte: a decisão de
subir o piso de Python ou de abandonar FTS5 não é sua.

- [ ] **Passo 4: commit**

```bash
git add tests/test_codeintel_db.py
git commit -F <arquivo com a mensagem>
```

## Task 2: id determinístico e assinatura sem literal

**Arquivos:**
- Criar: `sparkforge/codeintel/__init__.py`, `sparkforge/codeintel/ids.py`
- Criar: `tests/test_codeintel_ids.py`

- [ ] **Passo 1: escrever o teste**

```python
"""Identidade de no, e o que uma assinatura NAO pode carregar.

O id existe para ser estavel entre execucoes: o mesmo simbolo no mesmo lugar
tem que dar o mesmo id, senao o indice incremental da fase seguinte nao
consegue dizer o que mudou. Por isso BLAKE2b sobre campos declarados, e nunca
UUID.

A assinatura existe para ser lida, e por isso ela e o lugar mais provavel de um
segredo entrar no banco: `def connect(password="hunter2")` levaria a senha para
o indice, que persiste em disco. Valor literal e substituido por marcador.
"""

from sparkforge.codeintel.ids import node_id, normalizar_assinatura


def test_mesmo_simbolo_no_mesmo_lugar_da_o_mesmo_id():
    a = node_id("jobs/etl.py", "function", "etl.processar", "processar(df)")
    b = node_id("jobs/etl.py", "function", "etl.processar", "processar(df)")
    assert a == b
    assert a.startswith("node_")


def test_campo_diferente_da_id_diferente():
    base = ("jobs/etl.py", "function", "etl.processar", "processar(df)")
    variantes = [
        ("jobs/outro.py", "function", "etl.processar", "processar(df)"),
        ("jobs/etl.py", "class", "etl.processar", "processar(df)"),
        ("jobs/etl.py", "function", "etl.outro", "processar(df)"),
        ("jobs/etl.py", "function", "etl.processar", "processar(df, extra)"),
    ]
    ids = {node_id(*base)} | {node_id(*v) for v in variantes}
    assert len(ids) == 5, "algum campo nao entra no id"


def test_separador_impede_colisao_por_concatenacao():
    """Sem separador, ("ab","c") e ("a","bc") dariam o mesmo id."""
    assert node_id("ab", "c", "x", "y") != node_id("a", "bc", "x", "y")


def test_assinatura_troca_literal_por_marcador():
    entrada = "connect(password='hunter2', region='us-east-1', tentativas=3)"
    saida = normalizar_assinatura(entrada)
    assert "hunter2" not in saida
    assert "us-east-1" not in saida
    assert "password=<literal>" in saida
    assert "region=<literal>" in saida


def test_assinatura_preserva_nome_e_ordem_dos_parametros():
    saida = normalizar_assinatura("processar(df, chaves, modo='append')")
    assert saida.startswith("processar(")
    assert saida.index("df") < saida.index("chaves") < saida.index("modo")


def test_assinatura_sem_default_nao_muda():
    assert normalizar_assinatura("processar(df, chaves)") == "processar(df, chaves)"
```

- [ ] **Passo 2: rodar e ver falhar**

```
python -m pytest tests/test_codeintel_ids.py -q
```
Esperado: `ModuleNotFoundError: No module named 'sparkforge.codeintel'`.

- [ ] **Passo 3: escrever `ids.py`**

```python
"""Identidade deterministica de no do indice.

BLAKE2b e nao UUID porque o id precisa ser reproduzivel: reindexar um arquivo
que nao mudou tem que produzir os mesmos ids, senao a fase incremental nao
consegue distinguir "mudou" de "reindexado". Medido neste repositorio: 5668 ids
em 6 ms, entao o custo nao pesa na decisao.

O separador `\\x00` entre campos existe para que ("ab","c") e ("a","bc") nao
colidam -- concatenar sem separador transformaria fronteira de campo em
ambiguidade.
"""

from __future__ import annotations

import hashlib
import re

_SEPARADOR = "\x00"
_TAMANHO_DIGEST = 16

# Default de parametro e onde credencial entra numa assinatura sem que ninguem
# perceba: `def connect(password="hunter2")`. O indice persiste em disco, entao
# o valor e substituido antes de chegar la. O NOME do parametro fica -- ele e o
# que torna a assinatura legivel, e nao carrega segredo.
_LITERAL_DE_DEFAULT = re.compile(r"(=)\s*(?:'[^']*'|\"[^\"]*\"|[^,()]+)")


def node_id(caminho: str, kind: str, nome_qualificado: str, assinatura: str) -> str:
    """Id estavel de um no, derivado dos campos que o identificam."""
    material = _SEPARADOR.join((caminho, kind, nome_qualificado, assinatura))
    digest = hashlib.blake2b(material.encode("utf-8"), digest_size=_TAMANHO_DIGEST)
    return f"node_{digest.hexdigest()}"


def normalizar_assinatura(assinatura: str) -> str:
    """Assinatura sem valor literal de default.

    `connect(password='hunter2')` vira `connect(password=<literal>)`. Nome e
    ordem dos parametros ficam: sao eles que fazem a assinatura valer a pena
    guardar.
    """
    return _LITERAL_DE_DEFAULT.sub(r"\1<literal>", assinatura)
```

E `__init__.py`:

```python
"""Indice local de codigo, offline e sem dependencia externa.

Ele CONSOME o que o repositorio ja tem -- a varredura de `facts/scan.py` e o
`ast` que os extratores ja usam -- e persiste metadado consultavel. Ele nao
reimplementa extracao, e nao guarda corpo de funcao: o banco tem posicao, e
quem quiser o codigo le o arquivo.

O banco e DESCARTAVEL. Nada no motor determinístico depende dele para
responder; se sumir, a analise continua igual e o indice se reconstroi.
"""

from sparkforge.codeintel.ids import node_id, normalizar_assinatura

__all__ = ["node_id", "normalizar_assinatura"]
```

- [ ] **Passo 4: rodar**

```
python -m pytest tests/test_codeintel_ids.py -q
```
Esperado: **todos passam**.

- [ ] **Passo 5: teste de mutação, sobre cópia**

Copie `ids.py` para um diretório temporário, aponte `sys.path` para lá, e injete:
o separador removido; `digest_size` mudado; um campo fora do material do id; o
marcador de literal desligado. **Todas têm que ser pegas.** Diga quantas foram.

- [ ] **Passo 6: commit**

## Task 3: schema e conexão

**Arquivos:**
- Criar: `sparkforge/codeintel/db.py`
- Modificar: `tests/test_codeintel_db.py`

- [ ] **Passo 1: acrescentar o teste do schema**

```python
import pathlib

from sparkforge.codeintel.db import SCHEMA_VERSION, abrir, criar_schema


def test_schema_cria_as_tabelas_declaradas(tmp_path):
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    tabelas = {
        linha[0]
        for linha in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    }
    conexao.close()
    assert {"metadata", "files", "nodes", "unresolved_refs", "symbols_fts"} <= tabelas


def test_schema_grava_a_versao_e_nao_grava_caminho_absoluto(tmp_path):
    """O banco nao pode carregar o caminho da maquina.

    Caminho absoluto no `metadata` vazaria o nome do usuario e do diretorio num
    artefato que pode ser copiado, e tornaria o banco preso a uma maquina.
    """
    caminho = tmp_path / "graph.sqlite3"
    conexao = abrir(caminho)
    criar_schema(conexao)
    valores = dict(conexao.execute("SELECT key, value FROM metadata"))
    conexao.close()
    assert valores["schema_version"] == str(SCHEMA_VERSION)
    for chave, valor in valores.items():
        assert str(tmp_path) not in valor, f"{chave} carrega caminho absoluto"


def test_apagar_arquivo_apaga_os_nos_dele(tmp_path):
    """ON DELETE CASCADE, verificado de verdade.

    `PRAGMA foreign_keys=ON` nao e o default do SQLite -- sem ele o CASCADE e
    declarado e nao acontece, e o banco acumula no orfao a cada reindexacao.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    conexao.execute(
        "INSERT INTO files (id, path, language, content_sha256, size_bytes, "
        "modified_ns, indexed_at) VALUES ('f1','a.py','python','abc',1,1,1)"
    )
    conexao.execute(
        "INSERT INTO nodes (id, file_id, kind, name, qualified_name, "
        "start_line, end_line) VALUES ('n1','f1','function','x','a.x',1,2)"
    )
    conexao.execute("DELETE FROM files WHERE id = 'f1'")
    restantes = conexao.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    conexao.close()
    assert restantes == 0
```

- [ ] **Passo 2: rodar e ver falhar**

- [ ] **Passo 3: escrever `db.py`**

O schema segue as §21 a §29 da SPEC, com uma diferença deliberada: **não há
tabela `edges` nesta fase**. Arestas exigem resolução de referência, que é onde
mora a decisão difícil (`unresolved`), e misturar isso com a criação do banco
tornaria as duas indepuráveis. `unresolved_refs` existe desde já porque toda
referência não resolvida cai nela.

Campos obrigatórios de `metadata`: `schema_version`, `engine_version`,
`created_at`, `root_fingerprint`. **Nenhum caminho absoluto.**

Pragmas na abertura, todos: `journal_mode=WAL`, `foreign_keys=ON`,
`synchronous=NORMAL`, `temp_store=MEMORY`, `busy_timeout=30000`. O
`foreign_keys=ON` é o que faz o teste de CASCADE passar, e ele **não** é default
do SQLite.

Escreva na docstring por que `synchronous=NORMAL` é aceitável: o banco é
reconstruível, então perder a última transação num crash custa uma reindexação,
não um dado.

- [ ] **Passo 4: rodar, mutar sobre cópia, commitar**

Mutações mínimas: `foreign_keys` desligado; `schema_version` não gravado; uma
tabela fora do schema. Diga quantas foram pegas.

## Task 4: AST → nós, sem corpo

**Arquivos:**
- Criar: `sparkforge/codeintel/extract.py`
- Criar: `tests/test_codeintel_extract.py`

- [ ] **Passo 1: escrever o teste**

```python
"""Extracao de no a partir do AST, e o que o indice NAO guarda.

O corpo da funcao nao entra no banco (INV-010 da SPEC): o indice guarda posicao,
e quem precisa do codigo le o arquivo. Guardar corpo faria o banco virar copia
do repositorio, com o custo de disco e o risco de vazamento que vem junto.
"""

import textwrap

from sparkforge.codeintel.extract import extrair_nos


def _nos(fonte: str, caminho: str = "jobs/etl.py"):
    return extrair_nos(textwrap.dedent(fonte), caminho)


def test_extrai_funcao_classe_e_metodo():
    nos = _nos("""
        class Pipeline:
            def executar(self, df):
                return df

        def principal():
            pass
    """)
    por_kind = {(n.kind, n.qualified_name) for n in nos}
    assert ("class", "Pipeline") in por_kind
    assert ("method", "Pipeline.executar") in por_kind
    assert ("function", "principal") in por_kind


def test_posicao_permite_achar_o_codigo_depois():
    (no,) = [n for n in _nos("""
        def principal():
            pass
    """) if n.kind == "function"]
    assert no.start_line == 2
    assert no.end_line >= no.start_line


def test_nenhum_no_carrega_corpo():
    nos = _nos("""
        def com_segredo():
            senha = "hunter2"
            return senha
    """)
    for no in nos:
        assert "hunter2" not in repr(no), "corpo vazou para o no"


def test_default_literal_nao_entra_na_assinatura():
    (no,) = [n for n in _nos("""
        def conectar(usuario, senha="hunter2"):
            pass
    """) if n.kind == "function"]
    assert "hunter2" not in no.normalized_signature
    assert "senha=<literal>" in no.normalized_signature


def test_arquivo_que_nao_parseia_nao_derruba_a_extracao():
    """Sintaxe invalida e ponto cego, nao erro fatal.

    Um repositorio de cliente tem arquivo com sintaxe de outra versao de Python,
    template com placeholder, arquivo pela metade. Derrubar a indexacao inteira
    por causa de um seria trocar cobertura parcial por nenhuma.
    """
    nos = extrair_nos("def (:::", "quebrado.py")
    assert nos == []


def test_funcao_aninhada_ganha_nome_qualificado_do_escopo():
    nos = _nos("""
        def externa():
            def interna():
                pass
    """)
    qualificados = {n.qualified_name for n in nos}
    assert "externa.interna" in qualificados
```

- [ ] **Passo 2: rodar e ver falhar**

- [ ] **Passo 3: escrever `extract.py`**

Use `ast.parse` e um visitante que mantém pilha de escopo para o nome
qualificado. `end_line` vem de `node.end_lineno`, disponível desde 3.8.

**Atenção à compatibilidade que o plano herda:** o módulo `ast` mudou entre 3.10
e 3.14. Não use `ast.Str` nem `ast.Num` (removidos em 3.12). Para reconstruir a
assinatura, prefira `ast.unparse` (3.9+) e passe o resultado por
`normalizar_assinatura`. Se `ast.unparse` produzir saída diferente entre
versões, **meça e diga** — o id depende da assinatura, e assinatura instável
entre versões daria id instável.

Sintaxe inválida devolve lista vazia, nunca levanta.

- [ ] **Passo 4: rodar, mutar sobre cópia, commitar**

Mutações mínimas: pilha de escopo desligada (nome qualificado vira nome
simples); `normalizar_assinatura` não chamada; `end_line` igual a `start_line`;
`SyntaxError` propagado. Diga quantas foram pegas.

## Task 5: indexar, e indexar o próprio repositório

**Arquivos:**
- Criar: `sparkforge/codeintel/index.py`
- Criar: `tests/test_codeintel_index.py`

- [ ] **Passo 1: escrever o teste**

```python
"""Indexacao ponta a ponta, incluindo sobre o proprio repositorio.

O teste sobre o proprio repo nao e vaidade: ele e o unico que exercita a escala
real (369 arquivos, 5668 simbolos medidos antes da fase) e o unico que pegaria
uma regressao de desempenho ou um arquivo do repositorio que o extractor nao
aguenta.
"""

import pathlib

from sparkforge.codeintel.index import indexar


def test_indexa_arvore_pequena(tmp_path):
    (tmp_path / "jobs").mkdir()
    (tmp_path / "jobs" / "etl.py").write_text(
        "class Pipeline:\n    def executar(self):\n        pass\n", encoding="utf-8"
    )
    (tmp_path / "jobs" / "util.py").write_text("def ajudar():\n    pass\n", encoding="utf-8")
    resultado = indexar(tmp_path, tmp_path / "graph.sqlite3")
    assert resultado.arquivos == 2
    assert resultado.nos >= 3


def test_caminho_gravado_e_relativo_a_raiz(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    indexar(tmp_path, tmp_path / "graph.sqlite3")
    import sqlite3

    conexao = sqlite3.connect(tmp_path / "graph.sqlite3")
    caminhos = [linha[0] for linha in conexao.execute("SELECT path FROM files")]
    conexao.close()
    assert caminhos == ["a.py"]
    for caminho in caminhos:
        assert not pathlib.Path(caminho).is_absolute()


def test_reindexar_sem_mudanca_produz_os_mesmos_ids(tmp_path):
    """Id estavel entre execucoes -- a pre-condicao da fase incremental."""
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    import sqlite3

    def ids():
        indexar(tmp_path, tmp_path / "graph.sqlite3")
        conexao = sqlite3.connect(tmp_path / "graph.sqlite3")
        achados = sorted(linha[0] for linha in conexao.execute("SELECT id FROM nodes"))
        conexao.close()
        return achados

    assert ids() == ids()


def test_a_denylist_da_varredura_vale_no_indice(tmp_path):
    """O indice herda a fronteira de leitura da fase J0, nao a reimplementa."""
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    ruido = tmp_path / ".venv" / "lib"
    ruido.mkdir(parents=True)
    (ruido / "terceiro.py").write_text("def g():\n    pass\n", encoding="utf-8")
    resultado = indexar(tmp_path, tmp_path / "graph.sqlite3")
    assert resultado.arquivos == 1


def test_indexa_o_proprio_repositorio(tmp_path):
    raiz = pathlib.Path(__file__).resolve().parent.parent
    resultado = indexar(raiz, tmp_path / "graph.sqlite3")
    assert resultado.arquivos > 300, resultado.arquivos
    assert resultado.nos > 4000, resultado.nos
    assert resultado.ilegiveis < resultado.arquivos // 10, (
        f"{resultado.ilegiveis} arquivos nao parsearam -- investigue antes de aceitar"
    )
```

- [ ] **Passo 2: rodar e ver falhar**

- [ ] **Passo 3: escrever `index.py`**

`indexar(raiz, banco)` devolve um resultado com `arquivos`, `nos`, `ilegiveis` e
`duracao_s`. Ele **chama `iter_source_files`** da fase J0 — não varre por conta
própria. Arquivo que não parseia conta em `ilegiveis` e segue.

O último teste usa limites frouxos (`> 300`, `> 4000`) de propósito: um número
exato quebraria a cada arquivo novo no repositório, e o que interessa é a ordem
de grandeza. Escreva isso no comentário.

- [ ] **Passo 4: rodar e MEDIR**

```
python -m pytest tests/test_codeintel_index.py -q
```

Depois meça, e **anote os números** — eles vão para o commit e para a Task 6:
quanto tempo leva indexar o próprio repositório, quantos arquivos, quantos nós,
quantos ilegíveis, e o tamanho do arquivo `.sqlite3` resultante.

Se `ilegiveis` for alto, **investigue antes de aceitar**: pode ser incompatibilidade
de `ast` entre versões, e isso é achado, não ruído.

- [ ] **Passo 5: commit**

## Task 6: buscar, e provar que economiza

**Arquivos:**
- Criar: `sparkforge/codeintel/search.py`
- Criar: `tests/test_codeintel_search.py`
- Modificar: `sparkforge/adapters/cli.py`

- [ ] **Passo 1: escrever o teste**

```python
"""Busca por nome, e a seguranca da consulta.

FTS5 tem sintaxe propria: aspas, `*`, `NEAR`, `OR` sao operadores. Termo vindo
de fora que chegue cru ao MATCH pode virar erro de sintaxe -- ou consulta que o
chamador nao pediu. A §30 da SPEC exige construtor de consulta, nunca MATCH com
texto de terceiro.
"""

import pathlib

import pytest

from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.search import buscar


@pytest.fixture
def indexado(tmp_path):
    (tmp_path / "jobs").mkdir()
    (tmp_path / "jobs" / "etl.py").write_text(
        "def iter_source_files():\n    pass\n\n\ndef processar_lote():\n    pass\n",
        encoding="utf-8",
    )
    banco = tmp_path / "graph.sqlite3"
    indexar(tmp_path, banco)
    return banco


def test_acha_por_parte_do_nome(indexado):
    achados = buscar(indexado, "source")
    assert [a.name for a in achados] == ["iter_source_files"]


def test_resultado_traz_arquivo_e_linha(indexado):
    (achado,) = buscar(indexado, "processar")
    assert achado.path == "jobs/etl.py"
    assert achado.start_line > 0


def test_ordem_e_deterministica(indexado):
    assert [a.node_id for a in buscar(indexado, "e")] == [
        a.node_id for a in buscar(indexado, "e")
    ]


@pytest.mark.parametrize(
    "termo",
    ['"', 'x"y', "a OR b", "NEAR(a b)", "*", "a*", "(", "a AND b", "'", "^x"],
)
def test_sintaxe_de_fts_no_termo_nao_levanta(indexado, termo):
    """Termo com operador de FTS e tratado como texto, nunca como sintaxe."""
    buscar(indexado, termo)


def test_termo_vazio_devolve_vazio_e_nao_o_indice_inteiro(indexado):
    assert buscar(indexado, "") == []
    assert buscar(indexado, "   ") == []
```

- [ ] **Passo 2: rodar e ver falhar**

- [ ] **Passo 3: escrever `search.py`**

O termo passa por um construtor: normaliza, quebra em tokens alfanuméricos mais
`_`, descarta o resto, e monta a expressão de MATCH a partir dos tokens. **Nunca
interpole o termo cru no MATCH.**

Ordem: por relevância do FTS e desempate estável por `(path, start_line, node_id)`
— sem desempate, a ordem do SQLite não é garantida e o teste de determinismo
falharia de forma intermitente, que é pior que falhar sempre.

- [ ] **Passo 4: expor na CLI**

Verbo `code` com três subcomandos: `index` (recebe `--root`, default `.`),
`search` (recebe termo), `status` (mostra o que o banco tem e quando foi feito).

O banco fica em `.sparkforge/local/codeintel/graph.sqlite3`, que **já está no
`.gitignore`** desde `715a657`. Confirme antes de escrever.

- [ ] **Passo 5: a medição que justifica a fase**

Escreva um script no scratchpad (**não commite**) que compare, para pelo menos
cinco perguntas reais do tipo "onde está X definido":

- **bytes que uma busca com índice devolve** (o resultado de `buscar`), contra
- **bytes que responder sem índice custaria** (o tamanho dos arquivos que um
  `grep` devolveria e que alguém teria que ler para achar a definição).

Use símbolos reais deste repositório — `iter_source_files`, `looks_like_secret`,
`project_items`, `tool_class`, `authorize`.

**Meça em bytes, nunca em tokens.** Os quatro estimadores de token do
repositório são `len/4` e divergem entre si.

Escreva o resultado em `docs/harness/CODEINTEL-GAP.md` e registre os claims com
prova `kind: command` que **execute**. **Nunca rode `--seed --force`** — o lock
tem 638 entradas de vários documentos.

- [ ] **Passo 6: rodar todos os gates e commitar**

---

## Gates de toda tarefa

1. O teste da tarefa
2. `python -m pytest tests/ -q` — linha de base **6598 passed, 5 skipped**
3. `ruff check sparkforge tests scripts` — **241**, não pode subir; `noqa` não é conserto
4. `python scripts/check_vnext_claims.py` — **0 divergências**
5. Commit com `git commit -F <arquivo>`. **Sem heredoc** — ele travou cinco agentes na fase anterior.

## Recusas declaradas

**Não guardamos corpo de função.** `INV-010`. O banco tem posição; quem quer o
código lê o arquivo.

**Não criamos tool MCP nesta fase.** Uma tool sem índice maduro responde igual a
um modelo sem ferramenta, e cada tool nova entra no gate de paridade para
sempre. Elas entram quando `search` tiver ranking e houver medição de que o
resultado serve.

**Não afirmamos economia em tokens.** Só em bytes, medidos.

**Não fazemos incremental agora.** Reindexar o repositório inteiro é barato o
bastante para o incremental ser otimização, e a Task 5 mede quanto custa. Sem
esse número, o incremental seria construído sem saber o que economiza.
