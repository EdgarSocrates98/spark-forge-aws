# SparkForge AWS — Roadmap: especialização por banco de dados

**Data:** 2026-08-03
**Última atualização:** 2026-08-05 — a §3.1 (`SF-GRAPH`) foi entregue como Fase 6a.
**Status:** roadmap. **Não é spec de fase** — cada fase ganha spec e plano
próprios quando chega a vez. Este documento **se atualiza** conforme as fases
fecham: ele não é registro histórico, e por isso não ganha seção de desvios.
**Decidido com:** o mantenedor, em 2026-08-03, ao fechar a Fase 4a.
**Entregue até aqui:** §3.1 `SF-GRAPH` (Fase 6a, 2026-08-05).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. O que este documento decide, e o que ele recusa decidir

Decide **a decomposição**: a especialização em bancos é mais de uma fase, uma por
ferramenta, e não uma área `SF-DB` que junte três modelos de dado sem nada em
comum além de não serem Iceberg.

Recusa decidir **o conteúdo de cada fase**. Os candidatos de regra listados aqui
são hipóteses de partida, não escopo aprovado. Em quatro fases seguidas — 5b, 5c,
5c.2 e 4a — a pesquisa de fontes matou premissa que parecia óbvia no papel:
`aws emr list-configurations` não existe, `SparkDFDataset` morreu na versão 1.0,
uma `VerificationSuite` não é uma passada, não existe fact de duração de relógio.
Um roadmap que fixasse regras antes da pesquisa estaria repetindo o erro com mais
confiança.

**Cada fase abre com Task 0 de pesquisa de fontes**, e o resultado dela pode
esvaziar metade dos candidatos abaixo. Isso é sucesso, não atraso.

## 2. A fronteira que vale para todas

O motor lê artefato e julga com regra que cita `fact_id`. Ele **não executa**,
não consulta banco em tempo de análise, e não afirma sobre dado que não viu.

Disso decorre o corte que separa o que entra do que não entra, e ele é o mesmo
da §"Metade B" do `STATUS.md`:

| Entra | Fica de fora |
|---|---|
| Configuração do conector, lida do `.py` | "Qual banco usar para este caso" |
| Dump de descrição do recurso (`describe-*`) | Modelagem — chave de partição, formato do grafo, forma do documento |
| Métrica já coletada (CloudWatch, status de loader) | "Boas práticas" genéricas sem artefato que as ancore |
| Estrutura de chamada no código | Recomendação de desenho |

O que fica de fora **não é descartado**: vira restrição auditável em
`knowledge/`, com URL e data, que as skills e os coordenadores citam. É a camada
do meio que o spec da Fase 0 chama de *auditável* — não determinística como um
finding, e muito acima de opinião. O mecanismo de recomendação com garantia
declarada continua adiado, por decisão registrada, até a base de restrições
sustentá-lo.

## 3. As fases, na ordem proposta

A ordem é por **custo de artefato**, do mais barato ao mais caro. Fase que precisa
de coletor novo custa mais que fase que lê o `.py` que o motor já lê.

### 3.1 `SF-GRAPH` — grafo com Spark — **CONCLUÍDA (Fase 6a, 2026-08-05)**

Spec e decisões: [`2026-08-05-sparkforge-fase6a-graph-design.md`](2026-08-05-sparkforge-fase6a-graph-design.md).
Estado corrente e dívidas: [`../STATUS.md`](../STATUS.md).

**A previsão de "por que primeiro" se confirmou:** o artefato é o `.py`, nenhum
coletor novo, nenhuma credencial. `sparkforge/facts/graph.py` é o 19º extrator e
lê a mesma árvore que `pyspark_ast.py` e `data_quality.py`, pela terceira vez.

**O que de fato entrou:** seis kinds (`graph.import`, `graph.construction`,
`graph.algorithm`, `graph.checkpoint_dir`, `graph.unresolved` e a sentinela
`graph.module_analyzed`) e **quatro regras**:

| Regra | O que acusa | Severidade |
|---|---|---|
| `SF-GRAPH-001` | `connectedComponents` sem diretório de checkpoint em lugar nenhum do arquivo | P0 |
| `SF-GRAPH-002` | GraphFrames importado num Spark sem artefato publicado (`>=3.3`, `<3.4`) | P1 |
| `SF-GRAPH-003` | arestas do grafo não persistidas | P2 |
| `SF-GRAPH-004` | algoritmo de grafo dentro de laço Python | P2 |

**Dos cinco candidatos acima, dois morreram na Task 0 de pesquisa** — que é
exatamente o que a §1 deste documento prevê como sucesso:

- **"algoritmo iterativo sem limite de iteração" foi VETADA** (vetos `V-GF-2` e
  `V-GF-3` em `rules/catalog/graph.yaml`). Em nenhum dos dezesseis algoritmos com
  noção de iteração "ausente" é defeito: em seis é `TypeError`, em três é default
  documentado, em `pageRank` `tol` é o modo oficial alternativo a `maxIter` — e
  passar os dois é erro —, e em `connectedComponents` a doc recomenda **não**
  mexer. Nenhum fact da área carrega booleano de ausência de limite: o que sai é
  `iteration_arg`, que nomeia o parâmetro que o código passou.
- **"particionamento incompatível entre vértices e arestas" nunca existiu.** O
  `.py` não diz o particionamento de DataFrame nenhum, e a regra teria de inferir
  de uma coisa que a análise estática não vê.

Os outros três viraram regra: checkpoint (`SF-GRAPH-001`), arestas não
persistidas (`SF-GRAPH-003`, com a fronteira contra `SF-DQ-003` e `SF-PY-008`
medida em `tests/test_rules_graph_boundary.py`) e `GraphFrame` em laço, que
virou **algoritmo** em laço (`SF-GRAPH-004`) porque o custo está na chamada e não
na construção.

**A quinta regra a pesquisa TROUXE, e ela não estava prevista aqui:**
`SF-GRAPH-002` é a única do catálogo inteiro cuja resposta depende de uma faixa
de um minor de Spark — não há artefato publicado de GraphFrames para Spark 3.3,
em linhagem nenhuma, e são nove células de runtime (Glue 4.0 e EMR 6.8.0–6.11.1).

**A recusa se manteve:** modelagem continua fora. Se um atributo deve ser vértice
ou propriedade é julgamento, e está em `knowledge/graph/`.

### 3.2 `SF-DDB` — DynamoDB

**Por que segundo:** `describe-table` é dump JSON, e a Fase 5b já provou essa
forma inteira com `describe-cluster` — extrator, `collect`, fixtures com o dump
em `input/`.

**Artefatos:** `describe-table`, `describe-continuous-backups`, métricas de
throttling já coletadas do CloudWatch (o coletor existe desde a Fase 1), e a
configuração do conector no `.py` — `emr-dynamodb-connector` ou `spark-dynamodb`.

**Candidatos de regra, a confirmar:**
- `scan` onde a chave permitiria `query`
- `throughput.read.percent` alto contra tabela provisionada compartilhada com
  carga de produção
- GSI cuja projeção não cobre a consulta, forçando busca na tabela base
- segmentos de parallel scan desalinhados da capacidade
- `BatchWriteItem` sem tratamento de `UnprocessedItems` — escrita que se perde em
  silêncio, que é a família de defeito que este projeto persegue
- on-demand contra provisionado, decidido pelo padrão de carga observado

**A pesquisa precisa responder antes:** qual conector a AWS documenta hoje para
Glue e para EMR (eles divergem), e se `spark-dynamodb` ainda acompanha as versões
de Spark que `GLUE_MATRIX` e `EMR_MATRIX` cobrem. A Fase 5c mediu que PyDeequ não
alcança nenhuma release EMR 6.x — recomendar biblioteca que não roda no runtime
do usuário é conselho impossível de seguir.

### 3.3 `SF-NEP` — Neptune

**Por que terceiro:** pareia com `SF-GRAPH` — o Neptune costuma ser a origem ou o
destino do grafo que o Spark processa —, e o artefato principal é uma resposta
JSON de endpoint, que o motor sabe ler.

**Artefatos:** status do bulk loader, formato dos arquivos de carga (CSV de
Gremlin ou RDF), configuração de export, e a config do conector no `.py`.

**Candidatos de regra, a confirmar:**
- carga em massa com arquivos pequenos demais — o mesmo defeito de *small files*
  que `SF-PQ` já trata noutro contexto
- paralelismo do loader incompatível com o tamanho da instância
- export rodando contra o cluster primário em vez de um clone, competindo com a
  carga de produção
- carga sem `updateSingleCardinalityProperties` quando a semântica pedida é
  substituição

**A pesquisa precisa responder antes:** o que a API do loader devolve de fato — a
Fase 5b descobriu que `ListBootstrapActions` não devolve status nem exit code, e
uma regra inteira morreu por isso.

### 3.4 `SF-MONGO` — MongoDB e DocumentDB

**Por que por último:** é o que tem menos artefato do lado da AWS. Quase tudo vem
do `.py`, e a distinção entre MongoDB e DocumentDB muda o que o conector
consegue fazer.

**Artefatos:** configuração do MongoDB Spark Connector no AST
(`spark.mongodb.read.*`), o pipeline de agregação passado ao conector, o
partitioner escolhido.

**Candidatos de regra, a confirmar:**
- partitioner default sobre coleção grande sem shard key
- filtro aplicado **depois** do read em vez de entrar no pipeline — pushdown
  perdido, que é `SF-PQ-002` com outro nome
- `readPreference: primary` em job analítico, competindo com a carga transacional
- ausência de `batchSize` em leitura de coleção grande

**A pesquisa precisa responder antes, e é a premissa mais frágil deste roadmap:**
DocumentDB **não é** MongoDB. Ele emula uma versão do wire protocol, e o que o
conector faz depende dessa versão. Uma regra escrita para MongoDB pode ser falsa
para DocumentDB, e a fase precisa decidir se cobre os dois ou declara o veto.

## 4. As duas frentes transversais

**Carga e manutenção de tabela** não vira área própria. Cada fase de banco carrega
as suas regras de carga, porque "carga robusta" significa coisa diferente em cada
um: em Iceberg é compaction e expiração de snapshot (já é `SF-ICE`), em DynamoDB
é capacidade e `UnprocessedItems`, em Neptune é formato de arquivo e paralelismo
do loader. Uma área transversal juntaria defeitos sem gatilho em comum.

**Batch → streaming** é a `SF-STR` que o roadmap da §16 já prevê, e continua fase
própria. Ela toca todos os bancos, e por isso vem **depois** de pelo menos um
deles — a transição de um pipeline batch para streaming só é analisável quando o
motor já sabe ler o destino.

## 5. O que decide a ordem real

A ordem da §3 é proposta, não compromisso — a §3.1 já foi entregue, e as outras
três continuam abertas. Três coisas podem mudar a ordem restante, e todas são
mensuráveis:

1. **Qual banco aparece nos jobs que o operador tem à mão.** Cobertura sem caso
   real vira catálogo que nunca dispara.
2. **O que a pesquisa de fontes encontrar.** Se a API do loader do Neptune não
   devolver o que a §3.3 supõe, aquela fase encolhe e outra sobe.
3. **A Fase 4b.** Ela fecha os três itens de rigor que faltam — validação
   funcional automatizada, gates fail-closed e assinatura de relatório — e vem
   **antes** de qualquer banco novo, por decisão do mantenedor registrada aqui.
   Cobertura nova multiplica achados; rigor multiplica confiança em todos eles de
   uma vez.
