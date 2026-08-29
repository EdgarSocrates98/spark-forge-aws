# SparkForge AWS — Contabilidade de contexto: medir o que o projeto põe na janela

> Subprojeto J. Primeiro item da fila de `prompt_evo_forge.md`, e a reformulação
> do que aquele documento chama de *Token Economy Runtime v2* — reformulado
> porque a premissa original não tem produtor neste repositório.

## 1. Contexto: a infraestrutura existe e ninguém a alimenta

O documento de origem coloca telemetria de token acima de qualquer capacidade
nova, e o argumento é o certo: os itens que reduzem o custo de contexto reduzem
o custo de **tudo** que vier depois. Medido contra a árvore, o diagnóstico dele
se confirma em cinco pontos:

| Afirmação | Medido em 2026-08-29 |
|---|---|
| `sparkforge_inventory` é declarada e não existe | confirmado — não está em `TOOLS` |
| Não há verbo que busque fact por id | confirmado — zero tools com `fact`/`evidence` no nome |
| `.rtk/filters.toml` é template | confirmado — 13 linhas, 11 são comentário |
| `confidence=0.95` cravado no RCA | confirmado — `sparkforge/reliability/rca.py:90` |
| Três sistemas de budget | confirmado — `agents/autonomy.py`, `agents/supervisor.py`, `economy/budget.py` |

### 1.1 A premissa que muda

O documento pede *Provider Token Telemetry*: "cada chamada real deveria produzir
usage". Medido: `sparkforge/` **não importa** `anthropic`, `openai`, `bedrock`
nem `litellm` em lugar nenhum — existe `providers/mock.py`, e
`economy/router.py` devolve `estimated_cost_usd: float = 0.001` cravado no
dataclass.

**O SparkForge nunca chama um provider.** Quem gasta token é o host — Claude
Code, Devin, Codex — executando os agents em markdown. Instrumentar "a chamada
real" não tem produtor aqui, e um subprojeto construído sobre isso mediria uma
coisa que este processo não faz.

Sobra o que ele **de fato controla**: os bytes que ele coloca na janela de
contexto. Schema de tool, payload de resposta, seção de knowledge, markdown de
skill. Isso é determinístico, não depende de provider, e é o que sustenta os
subprojetos 2, 3, 5, 6 e 12 daquela fila — nenhum deles pode provar ganho sem
esta medição existir antes.

### 1.2 O ledger já existe, e dois campos dele mentem

`sparkforge/observability/store.py` cria `.sparkforge/traces.db` com as tabelas
`traces` e `spans`. `TraceSpan` já declara `component_type` — com `"tool"` entre
os valores previstos —, `input_tokens`, `output_tokens`, `cached_tokens` e
`estimated_cost_usd`. Nenhum caminho de execução escreve nele.

Alimentá-lo como está gravaria duas mentiras:

- **`estimated_cost_usd` num span de tool é número inventado.** Fonte nenhuma
  publica preço para uma chamada local.
- **`input_tokens` num span de tool é erro de categoria.** Resposta de tool tem
  byte; token de provider é do host, e o span não tem como sabê-lo.

## 2. Escopo

**Dentro:**

1. Um span por chamada de tool, com `payload_bytes` medido, em `call_tool`.
2. Medição estática do catálogo em repouso: schemas, skills, knowledge.
3. Agregação por tarefa, ancorada no `run_id` do case.
4. Ingestão do usage que o host registrou, no molde do `collect *`.
5. Verbo `economy report`, e **um** gate no CI — o do catálogo em repouso.

**Fora, por escrito:**

1. **Instrumentar chamada de modelo.** Não existe neste processo (§1.1).
2. **Gate por execução** (`tests/token_golden/` com tolerância por fixture).
   Calibrar tolerância exige histórico medido; hoje a amostra seria de um. Entra
   no spec seguinte, quando houver série.
3. **Tokenizer embarcado.** Dependência nova num projeto offline-first, e o
   tokenizer de um fornecedor não conta igual ao de outro: seria um número
   preciso e errado.
4. **Custo em dólar por chamada de tool.** Mesmo contrafactual que o subprojeto
   E recusou por escrito.

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 Um ponto de instrumentação, o mesmo que já autoriza

`adapters/tools.py:call_tool` é o despacho único: as 58 tools passam por ele,
`adapters/mcp.py` entra por ele, e é onde `CallPolicy` já morde. O span nasce
ali, depois do handler retornar e antes do `return`, **em todos os caminhos** —
inclusive os três de erro (`UNAUTHORIZED`, `CodeIndexError`, `AdapterError`),
porque recusa também ocupa contexto e uma investigação cheia de recusa pareceria
barata se elas não fossem contadas.

A alternativa recusada é o **replay**: um verbo que relesse os `--out` já
gravados e medisse o que teria ido para o contexto. Não toca o caminho quente,
mas só enxerga o que foi para disco — e a chamada via MCP devolve o payload
direto ao agente, sem `--out`. Mediria o caso menos frequente.

### 3.2 `payload_bytes` é medida, e a base dela viaja junto

```
payload_bytes = len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))
```

Isso é provável e reproduzível. **Não é "o que o modelo viu"**: o host
reserializa com espaçamento próprio, e afirmar que são o mesmo número seria a
mentira confortável desta fase. O span carrega `payload_basis` com a fórmula,
pelo mesmo motivo que `glue.run_cost` carrega a sua.

### 3.3 Byte sempre; token só com fonte

`payload_bytes` existe em todo span de tool. Os campos de token ficam **vazios**
nesse span, e vazio aqui significa "não se aplica" — não "deu zero". Token só é
preenchido pelo nível 4, com a fonte nomeada.

Quem pedir token onde não há fonte recebe `tokens_unresolved: no_source`. A
alternativa recusada é o `len(content) // 4` que o `context/funnel.py` usa hoje:
serve como heurística interna, não pode sair com o nome de token. É a mesma
disciplina do `UNQUALIFIED` em `glue.run_cost` — valor de primeira classe para
"a fonte foi lida e não qualificou", distinto de campo ausente.

### 3.4 Isto não é Fact, e a razão é o invariante do barramento

Um `Fact` é observação ancorada no **artefato analisado**. Telemetria do próprio
SparkForge não é sobre o job do cliente, e emiti-la em `--out` misturaria as
duas no mesmo arquivo que vira handoff entre sessões. Por isso o ledger é outro
lugar, com outro verbo.

A alternativa recusada era emitir `econ.*` como Fact e ganhar o motor de regras
de graça. Ganharia — e quebraria o invariante que sustenta todo o resto.

### 3.5 Reusar o ledger, não criar o segundo

`SQLiteTraceStore` existe, tem o schema quase certo, e a lacuna que este
repositório já identificou como a real é **duplicação, não camada nova**. O
subprojeto corrige os dois campos que mentem (§1.2) e acrescenta os que faltam,
em vez de abrir um segundo lugar que responda "o que esta execução gastou".

### 3.6 A correlação por tarefa é o ponto frágil, e fica declarada

`call_tool` não recebe id de case. O span nasce com um `run_id` ambiente —
`SPARKFORGE_RUN_ID` quando o host o define, senão um por processo — e o case
grava qual `run_id` é dele. Sem correlação, a agregação sai
`run_unresolved`: `verified findings / 1K bytes` calculado sobre spans de outra
investigação é pior que número nenhum.

### 3.7 O gate é um lock, não um limiar

`docs/surface.lock.json`, no mecanismo que `docs/claims.lock.json` já provou: o
número medido de cada superfície fica travado, e o teste falha quando a
superfície cresce sem o lock acompanhar. Não se inventa "20% é demais" — obriga
a **declarar** o crescimento, que é o que este repositório já faz com toda
alegação publicada.

Ele mede sem executar nada e roda em segundos. Isso importa hoje: o CI reprova
com `exit code 152` (SIGXCPU, limite de CPU do runner) porque a suíte inteira
não cabe num job, então um gate que precisasse dela não teria onde rodar.

## 4. Modelo

### 4.1 `TraceSpan`, os campos novos e os corrigidos

| Campo | Estado | Conteúdo |
|---|---|---|
| `payload_bytes` | novo | bytes da serialização canônica da resposta |
| `payload_basis` | novo | a fórmula, literal |
| `detail_level` | novo | o que a chamada pediu (`full`/`normal`/`summary`), vazio quando a tool não o aceita |
| `item_count` | novo | quantos itens a resposta trouxe, quando ela é lista |
| `outcome` | novo | `ok`, `unauthorized`, `error` |
| `estimated_cost_usd` | **removido do span** | número inventado; custo volta só com fonte |
| `input_tokens` / `output_tokens` / `cached_tokens` | mantidos, **só o nível 4 preenche** | vazio em span de tool significa "não se aplica" |

### 4.2 Os quatro níveis, e a garantia de cada um

| Nível | Mede | Garantia |
|---|---|---|
| 1. Resposta de tool | `payload_bytes` por chamada, com verbo, `detail_level`, itens e desfecho | **exata** — o projeto produziu aquele byte |
| 2. Catálogo em repouso | bytes dos schemas de `tools/list`, de cada `SKILL.md`, de cada doc de `knowledge/` | **exata e estática** — não executa nada |
| 3. Tarefa | agregação dos spans de um `run_id`, ao lado dos findings verificados do case | **derivada** do nível 1 |
| 4. Usage do host | `input_tokens`, `output_tokens`, `cached_tokens` que o host registrou | **externa** — artefato que o projeto não produz |

### 4.3 O nível 4 entra pela porta do `collect *`

É a única parte do projeto que já lê coisa de fora, e a disciplina é a mesma:
lê o artefato que outro produziu e recusa por nome o que não souber parsear. O
leitor desta fase é o do transcript do Claude Code, que é o formato disponível
aqui; qualquer outro host sai `usage.unresolved: host_format_unknown`, nunca um
parser adivinhado.

## 5. Superfície

Verbo de topo `sparkforge economy report` e tool `sparkforge_economy_report`,
pela mesma razão de `capacity`, `finops` e `tune`: não lê artefato, compõe sobre
o ledger. Devolve payload por verbo, o efeito medido do `detail_level`, o peso
do catálogo em repouso e — quando houver — o usage do host **ao lado**, nunca
somado ao byte.

## 6. Erros, cada um com o seu nome

**A medição nunca quebra a chamada.** Ledger indisponível — disco cheio, SQLite
travado, `.sparkforge/` sem permissão — e `call_tool` devolve o resultado do
handler do mesmo jeito. Instrumentação que derruba o produto é defeito, não
observabilidade; a falha de escrita é engolida com a razão escrita, no padrão
que `economy/cache.py` já usa para o cache best-effort.

- `run_unresolved` — span sem `run_id` correlacionável ao case.
- `tokens_unresolved: no_source` — pediram token e não há fonte.
- `usage.unresolved: host_format_unknown` — transcript de host desconhecido.
- `usage.unresolved: usage_field_absent` — transcript lido, campo ausente.
- `surface.unresolved` — arquivo de skill ou knowledge ilegível na medição estática.

## 7. Testes

1. **Byte exato** — payload conhecido, medida conferida contra a mesma fórmula
   calculada no teste; o que se prova é que o span registrou o que o despacho
   devolveu.
2. **Os três caminhos de erro geram span** — recusa de autorização,
   `CodeIndexError` e `AdapterError`.
3. **Ledger quebrado não quebra a tool** — store em caminho impossível, e a
   chamada continua devolvendo o resultado. É o teste que mais importa.
4. **O efeito do `detail_level`, medido e não desejado** — os três tamanhos
   sobre a mesma fixture. Se `summary` não for menor que `full`, o teste
   **reporta o número** em vez de afirmar o que se esperava: a frase
   "`detail_level` reduz" está publicada e nunca foi medida.
5. **Garantias sobre o subsistema inteiro** — nenhum span de tool carrega token
   de provider; nenhum lugar carrega custo em dólar.
6. **O lock bate com a medição** — mesmo gate do `claims.lock.json`.

## 8. Documentação

README (o verbo novo e os números medidos), `AGENTS.md` (a fronteira: o que o
projeto mede de si mesmo e o que ele não tem como medir), `STATUS.md` (a fase,
as decisões e o que ficou de fora), e o gate de números até `0 divergencia(s).`

## 9. Critérios de aceite

1. Toda chamada de tool gera span com `payload_bytes` e `payload_basis`, nos
   quatro caminhos de retorno.
2. Span de tool nunca carrega token de provider nem custo em dólar, provado
   sobre o subsistema inteiro.
3. Ledger indisponível não altera o resultado de `call_tool`, com teste.
4. O catálogo em repouso é medido sem executar nada, e o lock trava o número.
5. A agregação por tarefa recusa por nome quando não há `run_id`.
6. O usage do host é lido do formato conhecido e recusa nomeadamente os outros.
7. O efeito do `detail_level` sai medido no relatório, qualquer que seja.
