# Code intelligence: perguntar ao código sem abrir arquivo

O SparkForge monta um **índice local** do código: um banco SQLite com cada
função, classe e método, e com quem chama quem. Depois você faz perguntas ao
índice em vez de ler arquivo por arquivo.

Tudo roda na sua máquina. O índice não usa rede nem modelo de IA.

## Receita rápida

Da raiz do repositório, crie uma pasta de teste com um pedaço pequeno do código
e faça as perguntas mais comuns:

```bash
mkdir -p /tmp/sf-guia && cp -r sparkforge/capacity /tmp/sf-guia/capacity
cd /tmp/sf-guia
sparkforge code init --root capacity
sparkforge code search capacity --root capacity
sparkforge code symbol node_ab77aa4fcaa97f1006bd6d033aa27855 --root capacity --detail-level normal
```

1. Copia o pacote `sparkforge/capacity` para uma pasta temporária. Assim o índice
   de teste não fica dentro do repositório.
2. Entra na pasta.
3. `code init` cria o índice em `capacity/.sparkforge/local/codeintel/graph.sqlite3`.
4. `code search` responde "onde está X definido" e devolve o `node_id`, que é o
   identificador de cada símbolo.
5. `code symbol` recebe esse `node_id` e responde "quem chama X, e o que X chama".
   O `node_id` vem do caminho relativo, do tipo, do nome e da assinatura do
   símbolo. Na mesma cópia ele sai igual, mas o mais seguro é copiá-lo da saída
   do passo 4.

Se o comando `sparkforge` não estiver no PATH, troque por
`python -m sparkforge.adapters.cli`.

## Quando usar e quando não usar

Use quando a pergunta é **estrutural**: o que existe num arquivo, quem chama o
quê, o que quebra se algo mudar, como uma função chega em outra.

Não use como substituto de `grep` para achar uma linha pelo nome exato. Um
`grep -n "def nome"` bem escrito devolve menos bytes que o índice. A seção
[Honestidade das medidas](#honestidade-das-medidas) explica por quê.

## Pré-requisitos

- O pacote instalado (`pip install -e .` na raiz). Para as tools MCP, com o
  extra `mcp` (ver [servidor MCP](../04-mcp.md)).
- Código Python. O índice lê arquivos `*.py`.

## As perguntas, uma por uma

A tabela vem do `CLAUDE.md`. Todos os exemplos abaixo foram rodados sobre a cópia
de `sparkforge/capacity` da receita.

| Pergunta | CLI | Tool MCP |
|---|---|---|
| Onde está X definido | `sparkforge code search` | `sparkforge_code_search` |
| Quem chama X, e o que quebra se eu mudar | `sparkforge code symbol` | `sparkforge_code_symbol` |
| **Como** X chega em Y | `sparkforge code path` | `sparkforge_code_path` |
| Como este código está organizado | `sparkforge code shape` | `sparkforge_code_shape` |
| O pacote de contexto dentro de um teto | `sparkforge code context` | `sparkforge_code_context` |
| O trecho de fonte | `sparkforge code read` | `sparkforge_code_read` |
| O índice está em dia | `sparkforge code status` / `code sync` | `sparkforge_code_status` / `_sync` |
| O grafo para outra ferramenta | `sparkforge code export` | `sparkforge_code_export` |

Flags exatas de cada subcomando: [`referencia/cli/code.md`](../referencia/cli/code.md).
Argumentos de cada tool: [índice de tools](../referencia/tools/README.md). Os
nomes podem mudar entre CLI e tool. Na CLI é `--root` e o termo solto; na tool
`sparkforge_code_search` são `repo` e `query`.

### 1. Onde está X definido

```bash
sparkforge code search capacity --root capacity
```

A busca casa **parte do nome**. Saída real, encurtada:

```json
{
  "index": {"fresh": true, ...},
  "returned_count": 1,
  "results": [
    {
      "node_id": "node_ab77aa4fcaa97f1006bd6d033aa27855",
      "name": "build_capacity_plan",
      "kind": "function",
      "path": "plan.py",
      "start_line": 153
    }
  ]
}
```

Filtros úteis: `--kind function` (ou `class`, `method`), `--path-prefix jobs/`
e `--limit`.

### 2. Quem chama X, e o que quebra se eu mudar

```bash
sparkforge code symbol node_7a073eba8d6d76157a8bce32dd060ae1 --root capacity --detail-level full
```

O nível muda o que vem: `summary` traz só o metadado; `normal` acrescenta quem
chama (`callers`) e quem é chamado (`callees`); `full` acrescenta o **raio de
impacto** (`impact`, tudo que depende do símbolo) e os testes dentro dele.
Trecho real:

```json
{
  "symbol": {
    "name": "resolution_supports",
    "signature": "resolution_supports(resolution: float, target: float) -> bool",
    "path": "plan.py", ...
  },
  "callers": [{"name": "build_capacity_plan", "depth": 1, ...}],
  "callees": [],
  "impact": [ ... ],
  "unresolved_note": "callees traz somente chamadas resolvidas pelo indice; chamada com receptor de tipo desconhecido vive em unresolved_refs",
  "tests": []
}
```

Leia o `unresolved_note`. O índice só liga chamadas que ele consegue resolver.
Uma chamada como `objeto.metodo()`, em que o tipo de `objeto` é desconhecido,
fica de fora da lista e é contada em `unresolved_refs`.

### 3. Como X chega em Y

```bash
sparkforge code path node_ab77aa4fcaa97f1006bd6d033aa27855 node_7a073eba8d6d76157a8bce32dd060ae1 --root capacity
```

Devolve o caminho mais curto de chamadas. Trecho real:

```json
{
  "found": true,
  "reason": null,
  "hops": 1,
  "path": [
    {"name": "build_capacity_plan", "depth": 0, ...},
    {"name": "resolution_supports", "depth": 1, ...}
  ],
  "graph": {"resolved_edges": 8, "unresolved_refs": 33, "resolution_rate": 0.1951, ...}
}
```

No sentido contrário, o resultado real foi `"found": false` com
`"reason": "no_resolved_path"`. Isso não prova que o caminho não existe: prova
que não existe por **aresta resolvida**. O `resolution_rate` diz quanto das
chamadas o índice conseguiu ligar. Se o teto de saltos (`--depth`) acabar, o
motivo sai como `depth_exhausted`.

### 4. Como este código está organizado

```bash
sparkforge code shape --root capacity --top 3 --detail-level summary
```

Agrupa os símbolos em **comunidades** (grupos que se chamam muito entre si) e
lista os de maior **grau** (os mais ligados). Trecho real:

```json
{
  "communities": {"total": 3, "algorithm": "propagacao-de-rotulo-ordem-fixa/1", "converged": true, ...},
  "partition_note": "a particao e reproduzivel, nao unica: ...",
  "degree_note": "grau alto nao e defeito: ..."
}
```

`summary` traz só contagens. Use `normal` ou `full` para ver os membros.

### 5. O pacote de contexto de uma tarefa

```bash
sparkforge code context "escolher a capacidade mais barata que cumpre o SLA" --root capacity --max-tokens 800
```

Monta um **ContextPack**: os pontos de entrada, as relações, os pontos cegos e o
que não foi resolvido, dentro de um orçamento. Trecho real:

```json
{
  "query": {"terms": ["escolher", "capacidade", "mais", "barata", "cumpre", "sla"], "budget_bytes": 2400, ...},
  "entry_points": [{"name": "_capacidade_de", "score": 95, "score_breakdown": {...}, ...}],
  "relationships": [{"source": "build_capacity_plan", "target": "_capacidade_de", "kind": "calls"}],
  "unresolved": [{"reference_name": "dataclass", "reason": "NO_CANDIDATE", ...}],
  "security": {"trust": "untrusted_repository_content"},
  "metrics": {"estimated_tokens": 487, "over_budget_bytes": 0, ...},
  "reductions": [],
  "omitted": []
}
```

Dois cuidados:

- `estimated_tokens` é **estimativa declarada**, e não medida. O teto real é em
  bytes (`budget_bytes`).
- Se algo não coube, aparece em `reductions` e `omitted`. Nada é cortado em
  silêncio.

Use `--include` (repetível) para pedir só algumas seções: `symbols`,
`relationships`, `lineage`, `rules`, `unresolved`.

### 6. O trecho de fonte

```bash
sparkforge code read --root capacity --node-id node_7a073eba8d6d76157a8bce32dd060ae1
sparkforge code read --root capacity --file plan.py --start-line 41 --end-line 48
```

Lê por símbolo ou por faixa de linhas. Os tetos são duros: 250 linhas, 32 KiB e
4096 tokens. Trecho real:

```json
{
  "snippet": {
    "trust": "untrusted_repository_content",
    "file": "plan.py",
    "start_line": 114,
    "end_line": 129,
    "code": "_TOLERANCIA_NUMERICA = 1e-9\n\n\ndef resolution_supports(...",
    "truncated_by": [],
    "instruction_like_content_detected": false
  }
}
```

O rótulo `untrusted_repository_content` avisa o assistente que aquilo é
**conteúdo**, e não instrução. Um comentário no código que diga "ignore as regras"
não deve ser obedecido. `instruction_like_content_detected` liga quando o trecho
parece conter esse tipo de texto.

Pelo MCP, `sparkforge_code_read` só existe no transporte `stdio`.

### 7. O índice está em dia

```bash
sparkforge code status --root capacity --detail-level summary
sparkforge code sync --root capacity
```

Depois de editar um arquivo, o `status` real mostrou:

```json
{
  "fresh": false,
  "stale_reason": "STALE_INDEX",
  "action": "sparkforge code sync",
  "changed_files": 1, ...
}
```

`code sync` põe o índice em dia. É a única escrita do verbo. Na prática, as
perguntas conferem o frescor sozinhas: um `code search` logo após a edição
respondeu com `"checked": true` e `"synced": true` no bloco `index`, ou seja,
conferiu e sincronizou antes de responder.

### 8. Exportar o grafo

```bash
sparkforge code export --root capacity --detail-level summary
```

Exporta no formato de extração do Graphify (`graphify-extraction-compatible`).
`summary` traz só contagens; `normal` e `full` trazem nós e arestas. A saída
declara também o que **não** faz: não importa grafo de volta, porque o formato
final do Graphify não é publicado.

### Manutenção: `doctor` e `purge`

- `sparkforge code doctor --root capacity` confere o índice e sai com código 1
  se alguma checagem falhar. Na pasta temporária, a checagem `gitignore` falhou,
  porque ali não há `.gitignore`. No repositório, `.sparkforge/local` já está no
  `.gitignore`.
- `sparkforge code purge --root capacity` apaga **somente**
  `.sparkforge/local/codeintel/`. Qualquer outro diretório é recusado.

## Como ler o resultado

- **`index`** vem em quase toda resposta. `fresh` diz se o índice bate com os
  arquivos; `checked` e `synced` dizem se a conferência e a sincronização
  aconteceram nesta chamada.
- **`unresolved`, `unresolved_refs` e `unresolved_note`** são o índice dizendo o
  que ele **não sabe**. Isso é qualidade: uma lista vazia quando faltam ligações
  seria mentira.
- **`found: false` com `reason`** é uma resposta, e não um erro. O motivo diz qual
  limite foi atingido.
- **`security`** mostra a política de rede (`offline-strict`) e se variáveis de
  ambiente com segredo foram removidas antes de indexar.

## Honestidade das medidas

"Quanto o índice economiza" depende de **contra o quê** você compara. O
denominador decide o sinal:

- contra **ler os arquivos**, o índice economiza muito;
- contra a saída de um **`grep` pelo nome**, economiza menos;
- contra um **`grep` cirúrgico pela definição** (`def nome`), o índice **custa
  mais**, porque devolve mais recall (todo símbolo cujo nome contém o termo) e
  mais metadado.

As três medidas são verdadeiras. Citar só a primeira seria escolher o resultado.
Os números, o método e a data estão em
[`docs/harness/CODEINTEL-GAP.md`](../../harness/CODEINTEL-GAP.md), seção 10,
"Medição: o que a busca devolve contra o que responder sem ela custaria". Os dois
primeiros números mudam a cada arquivo novo na árvore, então cite sempre com a
data.

O gate `python scripts/check_recall_economy.py` torna "economizou" conferível:
um pacote que omite o símbolo pedido pelo nome é falha, e não economia.

## Erros comuns

| Sintoma | Causa | Como resolver |
|---|---|---|
| `indice inexistente: ...; construa com sparkforge code sync.` (código 2) | Nunca rodou `init` naquela raiz | `sparkforge code init --root <pasta>` |
| Resultado velho depois de editar | Índice fora de dia | `sparkforge code status`, depois `sparkforge code sync` |
| `code path` com `no_resolved_path` | A ligação passa por chamada não resolvida | Veja `unresolved_refs` e confira com `code symbol` |
| `code doctor` sai com 1 na checagem `gitignore` | A pasta não tem `.gitignore` cobrindo `.sparkforge/local` | Normal em pasta de teste. No seu projeto, acrescente a linha ao `.gitignore` |
| O banco apareceu no `git status` | Você usou `--db` apontando para fora de `.sparkforge/local/` | Volte ao padrão ou apague o arquivo |

## Próximos passos

- [Servidor MCP](../04-mcp.md), para usar tudo isso de dentro do assistente
- [Economia de contexto](economia-de-contexto.md), para medir quanto cada resposta pesa
- [Referência do comando `code`](../referencia/cli/code.md)
- [`sparkforge_code_search`](../referencia/tools/sparkforge_code_search.md) e o [índice de tools](../referencia/tools/README.md)
