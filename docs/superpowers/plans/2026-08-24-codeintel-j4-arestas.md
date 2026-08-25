# SFCI — fase J4: arestas, chamadores e impacto

> **Para trabalhadores agênticos:** SUB-SKILL OBRIGATÓRIA:
> `superpowers:subagent-driven-development`. Passos usam `- [ ]`.

**Objetivo:** responder "quem chama isto" e "o que quebra se eu mudar" — as
perguntas que `grep` não responde sem parse, e onde a medição de J3 mostrou que
o índice ganha.

**Arquitetura:** tabela `edges` e `unresolved_refs` sobre o `nodes` que J3 já
persiste. Resolução por nome qualificado, com fallback declarado. Sem
dependência nova.

---

## Por que esta fase, e por que antes do retrieval

A SPEC ordena retrieval (§162) antes de integração (§164). **Divergimos, com
razão medida em J3:**

```
"onde está X definido"     índice 963 B  vs  grep 419 B   -> 2,3x CONTRA
"símbolos de scan.py"      índice ~1520 B vs arquivo 14681 B -> 9,7x A FAVOR
```

Ranquear melhor uma resposta que já perde não muda o sinal. Responder "quem
chama isto" muda — não existe `grep` que responda sem parse.

**Dimensionado antes de escrever:** 23145 chamadas e 1858 imports nos arquivos
que `iter_source_files` entrega. ~25 mil arestas, ~2,9 MB a 120 B por aresta.
O banco de J3 tem 3,4 MiB; isso o leva a ~6,3 MiB. Cabe.

## O que NÃO está nesta fase

- Ranking e `ContextPack` (J5).
- Tools MCP (J6) — uma tool sem `edges` responde igual a um modelo sem
  ferramenta.
- Lineage de DataFrame e tabela (J8) — precisa de `edges` primeiro.
- Incremental (J7).

## A decisão difícil: resolução de referência

O AST vê `foo(x)`. Ele **não** sabe qual `foo`. Resolver exige escopo, imports,
herança — e resolver errado é pior que não resolver, porque uma aresta falsa faz
alguém investigar o lugar errado.

**A regra:** resolver só o que é inequívoco; todo o resto vira `unresolved_refs`
com razão. Isso é o princípio que `graph.unresolved` e `sql.unresolved` já
aplicam neste repositório — *unresolved é ponto cego, não ausência de problema*.

Razões que a fase reconhece: `NO_CANDIDATE`, `AMBIGUOUS`, `DYNAMIC_ATTRIBUTE`,
`UNKNOWN_RECEIVER`, `BUILTIN`.

**Meça a taxa de resolução e publique-a.** Se resolvermos 30%, o documento diz
30% — número baixo medido vale mais que número alto inventado.

---

## Estrutura

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/codeintel/db.py` | + tabelas `edges` e `unresolved_refs` |
| `sparkforge/codeintel/refs.py` | **novo** — AST → referência bruta |
| `sparkforge/codeintel/resolve.py` | **novo** — referência → aresta ou unresolved |
| `sparkforge/codeintel/graph.py` | **novo** — `chamadores`, `chamados`, `impacto` |
| `sparkforge/adapters/cli.py` | `code callers`, `code impact` |
| `tests/test_codeintel_refs.py` | extração de referência |
| `tests/test_codeintel_resolve.py` | resolução, ambiguidade, unresolved |
| `tests/test_codeintel_graph.py` | travessia, ciclo, profundidade |

---

## Task 1: schema de arestas

**Arquivos:** `sparkforge/codeintel/db.py`, `tests/test_codeintel_db.py`

- [ ] **Passo 1: teste**

```python
def test_schema_tem_edges_e_unresolved(tmp_path):
    conexao = abrir(tmp_path / "g.sqlite3")
    criar_schema(conexao)
    tabelas = {l[0] for l in conexao.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conexao.close()
    assert {"edges", "unresolved_refs"} <= tabelas


def test_apagar_no_apaga_as_arestas_dele(tmp_path):
    """CASCADE nos dois sentidos: aresta que sai e aresta que chega.

    Sem isso, reindexar um arquivo deixa aresta apontando para no que nao existe
    mais -- e uma travessia que segue essa aresta devolve resultado inventado.
    """
    conexao = abrir(tmp_path / "g.sqlite3")
    criar_schema(conexao)
    conexao.execute("INSERT INTO files (id,path,language,content_sha256,size_bytes,"
                    "modified_ns,indexed_at) VALUES ('f1','a.py','python','x',1,1,1)")
    for nid in ("n1", "n2"):
        conexao.execute("INSERT INTO nodes (id,file_id,kind,name,qualified_name,"
                        "start_line,end_line) VALUES (?,'f1','function',?,?,1,2)",
                        (nid, nid, nid))
    conexao.execute("INSERT INTO edges (source_id,target_id,kind,line) "
                    "VALUES ('n1','n2','calls',5)")
    conexao.execute("DELETE FROM nodes WHERE id='n2'")
    restantes = conexao.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    conexao.close()
    assert restantes == 0, "aresta sobreviveu ao alvo -- travessia devolveria no fantasma"
```

- [ ] **Passo 2:** rodar, ver falhar.
- [ ] **Passo 3:** acrescentar ao schema. `edges` com `source_id`, `target_id`,
  `kind`, `line`, `confidence`, FK **nos dois** com `ON DELETE CASCADE`, e índice
  em `source_id`, `target_id`, `kind`. `unresolved_refs` com `source_id`,
  `reference_name`, `reference_kind`, `file_id`, `line`, `reason`.
  **Suba `SCHEMA_VERSION`** — o banco antigo não tem as tabelas.
- [ ] **Passo 4:** rodar. Mutação sobre cópia: CASCADE só num sentido; índice
  ausente; `SCHEMA_VERSION` não subido. Diga quantas pegou.
- [ ] **Passo 5:** commit.

## Task 2: referência bruta do AST

**Arquivos:** `sparkforge/codeintel/refs.py`, `tests/test_codeintel_refs.py`

Uma `Referencia` é o que o AST vê, **antes** de saber a quem aponta:

```python
@dataclass(frozen=True)
class Referencia:
    """Uma mencao a nome, do ponto de vista de quem menciona.

    Ela NAO sabe a quem aponta -- resolver e trabalho de `resolve.py`. Separar
    as duas coisas e o que permite medir a taxa de resolucao: sem isso, uma
    referencia que ninguem resolveu seria indistinguivel de uma que ninguem
    extraiu.
    """
    origem_qualificada: str   # quem menciona: `Pipeline.executar`
    nome: str                 # o que menciona: `processar`
    kind: str                 # "calls" | "imports"
    line: int
    receptor: str             # `df` em `df.processar()`; "" quando nao ha
```

- [ ] **Passo 1: teste**

```python
def test_extrai_chamada_simples():
    refs = extrair_referencias("def a():\n    b()\n", "m.py")
    assert ("a", "b", "calls") in {(r.origem_qualificada, r.nome, r.kind) for r in refs}


def test_extrai_chamada_com_receptor():
    (r,) = [x for x in extrair_referencias("def a():\n    df.filtrar()\n", "m.py")
            if x.nome == "filtrar"]
    assert r.receptor == "df"


def test_extrai_import_e_from_import():
    refs = extrair_referencias("import os\nfrom pathlib import Path\n", "m.py")
    nomes = {(r.nome, r.kind) for r in refs}
    assert ("os", "imports") in nomes
    assert ("pathlib.Path", "imports") in nomes


def test_origem_e_o_escopo_que_contem_a_chamada():
    """Sem isso a aresta sai do modulo, nao da funcao, e `chamadores` mente."""
    (r,) = [x for x in extrair_referencias(
        "class P:\n    def m(self):\n        alvo()\n", "m.py") if x.nome == "alvo"]
    assert r.origem_qualificada == "P.m"


def test_chamada_no_topo_do_modulo_tem_origem_do_modulo():
    (r,) = [x for x in extrair_referencias("alvo()\n", "pacote/m.py")
            if x.nome == "alvo"]
    assert r.origem_qualificada == "pacote.m"


def test_sintaxe_invalida_devolve_vazio():
    assert extrair_referencias("def (:::", "m.py") == []
```

- [ ] **Passo 2:** rodar, ver falhar.
- [ ] **Passo 3:** implementar. Reuse a pilha de escopo de `extract.py` — **não
  duplique**; se ela não estiver exposta, extraia para função compartilhada. Duas
  pilhas de escopo divergiriam, e J0 já pagou esse preço com quatro detectores de
  segredo.
- [ ] **Passo 4:** rodar. Mutação: pilha de escopo desligada; receptor ignorado;
  `ImportFrom` fora. Diga quantas pegou.
- [ ] **Passo 5:** commit.

## Task 3: resolver, ou declarar que não resolveu

**Arquivos:** `sparkforge/codeintel/resolve.py`, `tests/test_codeintel_resolve.py`

- [ ] **Passo 1: teste**

```python
def test_resolve_nome_unico_no_indice():
    """Um so candidato: aresta com confidence alta."""
    ...  # monta indice com uma `processar`, resolve, afirma aresta

def test_nome_ambiguo_vira_unresolved_e_nao_aresta():
    """Duas `processar` em modulos diferentes.

    Escolher uma seria inventar: quem seguisse a aresta investigaria o arquivo
    errado, e nada acusaria. AMBIGUOUS e a resposta honesta.
    """
    ...  # afirma 0 arestas e 1 unresolved com reason AMBIGUOUS

def test_nome_desconhecido_vira_unresolved_no_candidate():
    ...

def test_builtin_nao_polui_unresolved():
    """`len`, `print`, `range` nao sao ponto cego -- sao biblioteca padrao.

    Sem esta regra, `unresolved_refs` enche de ruido e o numero perde sentido.
    """
    ...  # reason BUILTIN, ou fora da tabela; decida e escreva por que

def test_taxa_de_resolucao_e_medida_e_nao_estimada():
    """O relatorio publica a taxa. Este teste garante que ela vem de contagem."""
    ...
```

- [ ] **Passo 2:** rodar, ver falhar.
- [ ] **Passo 3:** implementar. Estratégia mínima, em ordem: nome qualificado
  exato → nome simples com candidato único no índice → `AMBIGUOUS` se vários →
  `NO_CANDIDATE` se nenhum. Receptor (`df.x()`) só resolve se o receptor for
  resolvível; senão `UNKNOWN_RECEIVER`. **Não invente heurística de tipo.**
- [ ] **Passo 4:** rodar. Mutação: ambíguo virando aresta (a mais importante —
  ela é o defeito que a fase existe para evitar); `reason` fixa; builtin poluindo.
- [ ] **Passo 5:** commit.

## Task 4: travessia

**Arquivos:** `sparkforge/codeintel/graph.py`, `tests/test_codeintel_graph.py`

- [ ] **Passo 1: teste**

```python
def test_chamadores_diretos():
    ...

def test_impacto_e_transitivo_com_profundidade():
    """`impacto(x, profundidade=2)` alcanca quem chama quem chama x."""
    ...

def test_ciclo_nao_causa_recursao_infinita():
    """a -> b -> a. Sem visitados, a travessia nao termina."""
    ...

def test_profundidade_zero_devolve_so_o_no():
    ...

def test_ordem_e_deterministica():
    """Sem desempate explicito, a ordem do SQLite nao e garantida e o teste
    falharia de forma intermitente -- pior que falhar sempre."""
    ...
```

- [ ] **Passo 2–5:** rodar, implementar, mutar (visitados removido; profundidade
  ignorada; desempate fora), commitar.

## Task 5: CLI e a medição que decide a fase

**Arquivos:** `sparkforge/adapters/cli.py`, `docs/harness/CODEINTEL-GAP.md`

- [ ] **Passo 1:** `code callers <nome>` e `code impact <nome> --depth N`.

- [ ] **Passo 2: MEDIR, e publicar o que der.**

Para cinco símbolos reais (`looks_like_secret`, `project_items`, `tool_class`,
`authorize`, `iter_source_files`), compare em **bytes**:

- resposta de `code callers`, contra
- o que responder sem índice custaria: `grep -n "<nome>("` mais a leitura dos
  arquivos necessários para distinguir **chamada** de **definição** e de
  **menção em comentário ou string**.

Descreva o método. O denominador honesto **não** é "ler o repositório" — é o que
um agente competente faria.

**Publique a taxa de resolução junto.** Uma resposta de `callers` que resolve 40%
das referências é 40% de resposta, e quem lê precisa saber disso para decidir se
confia.

- [ ] **Passo 3:** registrar em `CODEINTEL-GAP.md` com prova `kind: command` que
  **execute**. Número não-derivável não entra. **Nunca `--seed --force`.**

- [ ] **Passo 4:** commit.

---

## Gates de toda tarefa

1. Teste da tarefa
2. `python -m pytest tests/ -q` — base **6716 passed, 5 skipped**
3. `ruff check sparkforge tests scripts` — **241**; `noqa` não é conserto
4. `python scripts/check_vnext_claims.py` — **0**
5. `git commit -F <arquivo>`. **Sem heredoc.**

Rode também em 3.10 e 3.11:
```
C:\Users\edgar\AppData\Roaming\uv\python\cpython-3.10.20-windows-x86_64-none\python.exe
C:\Users\edgar\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe
```

## Recusas declaradas

**Aresta ambígua não vira aresta.** Vira `unresolved_refs` com `AMBIGUOUS`.
Aresta falsa faz alguém investigar o lugar errado, e nada acusa.

**Sem heurística de tipo.** Inferir que `df` é DataFrame porque o nome é `df`
seria adivinhação vestida de análise. `UNKNOWN_RECEIVER` é a resposta honesta.

**A taxa de resolução vai no documento, qualquer que seja.** Número baixo medido
vale mais que número alto inventado.

**Bytes, nunca tokens.**
