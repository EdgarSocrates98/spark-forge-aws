# SparkForge AWS — Gate de recall e economia: o pack que omite o símbolo é falha, não sucesso

**Data:** 2026-09-02
**Status:** **proposta**.
**Origem:** primeiro incremento de `prompt_evo_graph_economy.md` (FASE 11), depois da medição
que reordenou o prompt inteiro — ver a seção 2.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. A lacuna está nomeada há semanas, e por três vezes

`docs/harness/CODEINTEL-GAP.md` §14 tem três linhas contíguas que dizem **NÃO EXISTE**:

| Componente pedido | O que a auditoria escreveu |
|---|---|
| Corpus de query de referência | *"as quinze perguntas que a SPEC enumera não existem como corpus, e nada as responde hoje sem varredura de arquivo"* |
| Gold set com símbolo e arquivo exigidos por query | *"consequência da linha acima"* |
| **Gate de recall e de economia** | *"nenhuma medição de recuperação, e portanto nenhum piso"* |

E a linha 292 do mesmo documento já escreveu a consequência, sem poder torná-la executável:

> *"economia que omite o símbolo necessário é falha, não sucesso."*

Esta spec transforma essa frase em gate.

## 2. A medição que reordenou o prompt de origem

`prompt_evo_graph_economy.md` pede 14 fases sobre a premissa de que *"a capacidade de grafo
existe em partes separadas, mas não há uma camada unificada"*. **Medido em 2026-09-02, a premissa
é majoritariamente falsa.** `sparkforge/codeintel/` tem 16 módulos e ~300 KB:

| Fase do prompt | Estado medido |
|---|---|
| F1 modelo de nó e aresta | **existe, em dois** — `NoDoGrafo` (`codeintel/graph.py`), `NoDeDados`/`ArestaDeDados`/`GrafoDeDados` (`lineage.py`) |
| F2 reuso dos facts | **existe** — `build_call_graph` emite quatro kinds `callgraph.*` |
| F3 update incremental | **existe e é maior que o pedido** — `staleness.py` (56 KB), git-aware, com `NegadoPorFrescor` |
| F4 consultas | **5 de 14** — `impacto`, `chamadores`, `chamados`, `montante`/`jusante`, `callgraph.cycle` |
| F5 contexto e economia | **existe** — `montar()` → `ContextPack` de 13 campos; `budget.py` com `alocar`/`cortar_por_bytes` |
| F7 CLI e MCP | **existe** — seis tools (`code_context`, `code_search`, `code_symbol`, `code_read`, `code_sync`, `code_status`) |
| F9 segurança | **existe e é maior** — `security.py` com `imports_proibidos`, `install_audit_hook`, `apply_resource_limits` |
| F10 testes | **existe** — onze arquivos `test_codeintel_*` |
| **F11 benchmark** | **NÃO EXISTE** — esta spec |

Ficam para incrementos seguintes, nesta ordem: `shortest_path` e `graph_stats` (F4), ponte
grafo ↔ Spark (F6), comunidades e god nodes (F8), `GraphifyJsonAdapter` (F1.6). O adaptador é
**último de propósito**: é o único item genuinamente novo e o de menor valor, porque exporta para
uma ferramenta fora do fluxo do operador.

**F11 vem primeiro porque tudo o que vier depois publicaria ganho sem lastro.** O repositório já
tem essa cicatriz escrita na regra 28 do `CLAUDE.md` — *"antes de afirmar que `detail_level`
reduz, leia o número"*, uma frase que esteve publicada por muito tempo sem medição.

## 3. O que `montar()` nunca teve

A medição de 87 KB da §10 do CODEINTEL-GAP cobre **`buscar()`** — busca por nome. Ela é honesta e
o resultado não agrada: contra ler arquivo o índice economiza **645×**, contra `grep` pelo nome
**9.4×**, e contra um `grep` cirúrgico pela definição ele **custa 5.3× mais**.

**`montar()` — o `ContextPack`, 38 KB, que é onde mora a alegação de economia do subsistema —
nunca foi medido contra denominador nenhum.**

## 4. Decisões de desenho

### D-1 — o gold set é DERIVADO das regras, nunca escrito

`Fact.subject` carrega `{type, file, line, col, symbol, snippet}`. `Finding.evidence` é lista de
`fact_id`. A cadeia fecha sem heurística:

```
finding.evidence[] -> fact.id -> fact.subject.{file, symbol}
```

Medido: **23 pares (fixture, regra) com símbolo `.py` ancorado, cobrindo 18 regras distintas.**
Outros **25 pares em 17 regras** ancoram fora de `.py` (JSON, Terraform, HCL) e ficam de fora —
**nomeados na saída, nunca silenciados**.

A pergunta de cada item vem do `title` da regra: texto já versionado em `rules/catalog/`.

**O gold set é derivado a cada execução e nunca versionado como JSON.** Gold set congelado num
arquivo é a segunda cópia da verdade que envelhece calada — é o defeito que o sub-projeto 2
existiu para remover (`EMR_MATRIX` literal em código contra a matriz em YAML). Derivado, ele não
pode divergir das regras: se a regra mudar, o gold set muda junto e o gate pega.

### D-2 — recall é booleano por símbolo, e a média é proibida

`recall` pergunta se **cada** `simbolo_exigido` aparece em `pack.symbols`. Média sobre símbolos
esconde o zero: um pack que traz 9 de 10 símbolos exigidos tem 90% e **não responde a pergunta**,
porque o símbolo que falta pode ser exatamente aquele que a regra ancora.

### D-3 — recall tem piso duro; economia NÃO tem piso

**Recall < 100% é falha dura.** É a assimetria que a §14 escreve e que este repositório
subscreve.

**Economia é reportada com o denominador ao lado, nunca aprovada contra alvo.** A medição
anterior provou que o denominador decide o *sinal* do resultado — 645× a favor e 5.3× contra, na
mesma ferramenta. Fixar piso de economia seria escolher o denominador que agrada, que é
exatamente o defeito que a §10 se recusou a cometer.

Os três denominadores, todos publicados juntos:

1. **Ler os arquivos** que contêm os símbolos exigidos — o que um agente sem ferramenta faz.
2. **`grep -n "def <simbolo>"`** — o piso adversarial, o que menos favorece a ferramenta.
3. **O pack em cada `detail_level`** — fecha a dívida da regra 28 neste eixo.

Bytes UTF-8 sempre, tokens nunca (regra 22). `budget.estimar_tokens` existe e sai como
`estimated_tokens` — **estimativa declarada**, e não entra em nenhuma razão de economia.

### D-4 — recusa tem nome, e recusa que curou é mentira

`SEM_RECALL` é dicionário de recusas nomeadas, no molde de `SEM_MEDIDA` em
`scripts/check_status_numbers.py`: chave `"<rule_id>@<fixture>"`, valor `(razão, medida que
destravaria)`.

O gate falha em **duas** direções:

- recall < 1 para item **fora** da lista;
- item **da lista** que passou — recusa que curou e ninguém removeu é afirmação falsa sobre o
  estado do sistema, do mesmo tipo que a regra 20 nomeia.

### D-5 — o contrafactual prova que o gate mede recuperação

Desligada a ancoragem no grafo (`_profundidades` em `context.py`), o recall de **pelo menos uma**
pergunta tem de cair. Se não cair, o gate não mede recuperação — mede que o FTS acha o nome, e
isso o `grep` já fazia. O teste grava o número dos dois lados.

## 5. O que entregar

```
sparkforge/economy/goldset.py           derivar_goldset() -> tuple[PerguntaDeOuro, ...]
sparkforge/economy/recall.py            medir() -> tuple[MedidaDeRecall, ...]
scripts/check_recall_economy.py         o gate, com RECALL_EXIGIDO e SEM_RECALL
tests/test_economy_goldset.py           derivacao, cobertura, e os 25 pares recusados
tests/test_economy_recall.py            recall, economia, contrafactual da ancoragem
```

Sem tool MCP e sem comando CLI nesta fase: o gate é de CI, e superfície nova moveria
`docs/surface.lock.json` sem que ninguém tivesse pedido a capacidade. Se o operador quiser
consultar recall fora do CI, é decisão de outra fase.

## 6. Testes e gates

- Os 23 pares derivam. A contagem é **piso, não igualdade**: cair significa que alguma regra
  perdeu ancoragem e é defeito; subir significa que uma regra nova ganhou fixture ancorada e é
  progresso. Igualdade pintaria de vermelho o próprio progresso — é a armadilha que
  `check_surface_lock.py` resolve deixando crescer e obrigando a **declarar de quanto foi**, e
  aqui a declaração é a mesma: o piso sobe no commit que o fez subir.
- Os 25 pares fora de `.py` saem **nomeados** na saída do gate.
- O contrafactual da D-5, com o número dos dois lados.
- `SEM_RECALL` vazio na entrega, ou com cada entrada carregando as duas metades.
- Indexação da fixture em banco temporário: nunca escreve na árvore do repositório.
- Gates de sempre: `check_status_numbers.py --strict` se a tabela de *Números correntes* ganhar
  linha, `check_vnext_claims.py` para todo número publicado, e a suíte em lotes.

## 7. Critérios de conclusão

- O gold set deriva das regras e **não existe como arquivo versionado**.
- Recall é booleano por símbolo, e a média não aparece em lugar nenhum.
- Economia sai com os três denominadores lado a lado, e **sem piso**.
- Toda recusa tem razão e medida que a destravaria, e recusa que curou derruba o gate.
- O contrafactual da ancoragem está medido e gravado.

## 8. Fora do escopo, e onde cada um mora

| | |
|---|---|
| `shortest_path`, `graph_stats` | incremento 2 (F4) |
| Ponte grafo ↔ plano físico e event log | incremento 3 (F6) |
| Comunidades e god nodes | incremento 4 (F8) — provavelmente `communities.unresolved`, porque a dependência não cabe no wheel mínimo |
| `GraphifyJsonAdapter` | incremento 5 (F1.6), último de propósito |
| Os 25 pares ancorados fora de `.py` | destravam com extrator de símbolo para SQL/HCL/JSON, que ninguém pediu |
| Tool MCP ou comando CLI de recall | não pedido; moveria a superfície sem capacidade solicitada |
