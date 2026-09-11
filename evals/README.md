# Evals — SparkForge AWS

Este diretório contém a suite de avaliação da Fase 0: `fase0.xml`, dez pares
pergunta/resposta verificáveis por comparação exata de string.

## Dois níveis de gate, dois significados diferentes

### Nível determinístico

Facts e Findings são idênticos entre execuções e entre modelos, por
construção: o extrator é AST estático (nunca importa nem executa código) e o
motor de regras é uma máquina de avaliação sobre YAML versionado. Nenhum LLM
participa da extração ou do julgamento.

Este nível é garantido pelos golden tests (`tests/test_fixtures_golden.py`,
17 fixtures, ambas as direções: facts e findings) e por
`scripts/check_evals.py`, que recomputa cada uma das dez respostas deste
diretório a partir do corpus real antes de aceitar o arquivo.

**Uma divergência aqui é um bug.** Não se corrige ajustando a resposta para
combinar com uma saída errada — corrige-se o extrator, o motor de regras ou o
catálogo, e as respostas em `fase0.xml` são recomputadas.

### Nível de agente

`fase0.xml` mede se um agente **usa as ferramentas corretamente** — chama
`analyze_pyspark`, `judge`, `rules_lookup` e as demais na ordem certa, lê o
resultado estruturado em vez de adivinhar, e responde com o valor exato que
o catálogo e o corpus determinam. Não mede o analisador: isso já está coberto
pelo nível determinístico acima.

O gate é **10/10 para qualquer modelo testado**. Uma resposta errada de um
agente não é evidência de que o modelo é fraco — é evidência de que a
descrição de uma tool, ou uma regra em `AGENT_PROTOCOL.md`, é ambígua o
suficiente para um agente competente errar. **A correção é sempre no prompt
ou no protocolo, nunca na troca do modelo.**

## Matriz de execução

A suite roda contra:

- Claude (Opus, Sonnet, Haiku)
- Devin

Qualidade narrativa (tom, concisão, formatação da explicação) **não é
gateada**. O que é gateado é a exatidão do valor extraído do corpus —
`rule_id`, linha, severidade, contagem, threshold — comparado por igualdade
de string exata contra `evals/fase0.xml`.

## Rodando localmente

```bash
python scripts/check_evals.py   # confere as respostas contra o corpus
python -m pytest tests/test_evals.py -q
```

Um agente (humano ou modelo) roda as dez perguntas via as tools MCP ou a CLI
`sparkforge` e compara a resposta literal com `evals/fase0.xml`.

Até 2026-09-10 este parágrafo terminava em "não há harness automatizado de
execução de agente neste repositório". Continua verdade que o **pacote** não
executa agente (regra 23), mas o nível de agente agora tem pontuação
reprodutível: ver a seção seguinte.

## Nível de agente pontuado — `evals/agentic/`

`evals/agentic/fase0/suite.yaml` é o gabarito agêntico. As dez perguntas são as
de `fase0.xml`, referenciadas por índice e sem cópia. O arquivo acrescenta o que
o XML não diz: que tools cada resposta exige (`required_tools`, com alternativa
quando há mais de um caminho honesto), em que ordem parcial (`order`), e três
perguntas cuja resposta certa é **recusar** (`expects_abstention`). Cada uma
dessas três ancora num fact `*.unresolved` que o corpus de fato emite, e
`tests/test_evals_suite.py` confere a âncora.

```bash
# 1. roda o agente e pontua cada execucao -- gasta token do host, fora do CI.
#    Grava em ~/.sparkforge/agentic-evals/: uma pasta por execucao (com
#    scorecard.json) e o conjunto fase0-<data>/ com os N scorecards.
python scripts/run_agentic_eval.py --repeat 3 --model haiku
# 2. repontua uma execucao, se o gabarito mudou
python -m sparkforge.evals grade --suite fase0 --run <run_id>
# 3. compara dois conjuntos: cada nome e procurado em
#    evals/agentic/fase0/baselines/ (commitado) e em ~/.sparkforge/agentic-evals/
python -m sparkforge.evals compare --suite fase0 --baseline <nome> --candidate <nome>
```

**O que o scorecard mede, por pergunta e em colunas separadas:**
- resposta: `correct`, `wrong`, `answer_absent` ou `over_abstention`;
- abstenção: `abstained` ou `false_certainty`;
- tools: exigidas e ordem;
- custo: chamadas, bytes de resultado vistos no transcript e tokens do usage do host.

**O que ele não mede:**
- não existe nota composta;
- não há dólar (regra 25);
- não há latência;
- nada é somado entre byte e token (regra 22).

Pergunta sem transcript, ou com transcript ilegível, sai `ungraded`, nunca
`wrong`.

**O que o compare não faz.** Ele não declara que algo melhorou ou piorou. Por
pergunta, mostra `k/N` de cada lado e a transição entre as classes `pass`,
`fail` e `mixed`. Recusa comparar gabaritos diferentes (`suite_mismatch`) e
avisa quando um lado tem uma execução só (`single_sample`). Quem conclui é quem
lê — a regra 30 vale para o próprio harness.

**Isolamento do runner, e o número que o motivou.** No smoke de 2026-09-10, uma
sessão Haiku de uma pergunta gastou **120 122 tokens de `cache_creation`** só
com a configuração global do operador, e estourou um teto de US$ 0,10 antes da
primeira tool responder. Por isso o runner passa `--strict-mcp-config` e
`--setting-sources project` por padrão, e grava os dois em `run.json`.

**O runner só aceita valor de lista fechada.** A suíte é constante
(`evals/agentic/fase0`): uma suíte nova entra como constante nova, porque
escolher o diretório pelo argv, mesmo contra uma lista, foi o fluxo que o
scanner de segurança recusou. O modelo e as fontes de configuração saem de uma
allowlist. O
executável é o `claude` do PATH, e a configuração MCP é `evals/agentic/mcp.json`,
que não usa a `${CLAUDE_PLUGIN_ROOT}` do `.mcp.json` da raiz: fora do contexto de
plugin ela vira vazia, e o catálogo apontaria para `/rules/catalog`. A saída mora
sempre sob `~/.sparkforge/agentic-evals/`. Nenhum texto livre do argv chega a
`subprocess` nem a um caminho. Quem precisar de outro valor edita a lista, e a
mudança fica no diff.

**A CLI de avaliação recebe nomes, não caminhos.** `--suite`, `--run`,
`--baseline` e `--candidate` passam por `os.path.basename` e resolvem sob bases
fixas; `grade` grava o scorecard dentro da própria execução e `compare` só
imprime. A versão que aceitava diretório arbitrário, mesmo confinado por
`realpath`, foi recusada pelo scanner de segurança, e o operador escolheu os
nomes sob bases fixas (2026-09-10). A CLI mora em `sparkforge/evals/`, fora da
CLI `sparkforge`, porque o runtime não importa a avaliação
(`tests/test_harness_boundary.py`).

**O agente responde numa cópia de prova, sem gabarito.** No primeiro baseline
(2026-09-10), sessões Haiku rodando na raiz do repositório não chamaram
**nenhuma** tool do SparkForge em 10 perguntas. O servidor MCP estava
`connected`, com 83 tools, e mesmo assim o agente abriu
`fixtures/.../expected/findings.json` e copiou a resposta. O veredito de tools
(`failed` nas 10) foi o que denunciou o atalho; a coluna de resposta, sozinha,
teria lido acerto. Desde então o runner monta
`~/.sparkforge/agentic-evals/workspace-<data>/`, uma cópia com o pacote, o
catálogo, o knowledge, as skills, os agentes e só as **entradas** das fixtures.
Ficam de fora `expected/`, `meta.yaml` (o `proves` cita a regra esperada), o
corpus `host_transcript`, `tests/`, `evals/`, `docs/` e `.claude/`. É a mesma
lógica do holdout: resposta disponível não mede capacidade. Na mesma rodada, a
pergunta 1 foi respondida `SF-PY-005, 2` contra `SF-PY-005:2`, e o protocolo da
suíte passou a dizer o separador. A correção foi no protocolo, como manda a
regra desta página, e não no grader.

**Formato de transcript: só Claude Code.** O extrator (`sparkforge/facts/
host_transcript.py`) lê o JSONL de sessão do Claude Code e recusa por nome o
resto. Transcript do Devin não é lido. Por isso a matriz de execução acima
continua com "Devin não foi executado" até alguém escrever esse leitor.

### Baseline de 2026-09-11 — Haiku 4.5, N = 3

`evals/agentic/fase0/baselines/2026-09-11-haiku-4-5/` (`r1.json`…`r3.json`), só
scorecards, sem transcript. Claude Code 2.1.268, `--strict-mcp-config`,
`--setting-sources project`, workspace de prova. Custo do host somado dos
`result.json`: US$ 6,68 pelas 39 sessões.

| Coluna | r1 | r2 | r3 |
|---|---|---|---|
| Pontuadas | 13/13 | 13/13 | 13/13 |
| Resposta `correct` (10 com valor) | 10 | 10 | 9 |
| `abstained` (3 de abstenção) | 2 | 2 | 2 |
| `false_certainty` | 1 | 1 | 1 |
| `tools_ok` | 0 | 3 | 3 |
| Chamadas de tool, `median_low` / máx. | 19 / 53 | 12 / 59 | 16 / 40 |

**O que o número diz.** O Haiku acerta quase todas as respostas, e quase nunca
pelo caminho que a suíte exige: nas três execuções, 3 de 39 perguntas passaram
pelas tools exigidas. As outras foram respondidas lendo a entrada da fixture e
o YAML do catálogo com `find`, `grep` e `Read`. Nas 105 cadeias `cd … &&`, a
normalização reconheceu o verbo sempre que havia um. É comportamento do agente,
não lacuna do harness.

**O que ele não diz.** Não diz que o Haiku é "melhor" ou "pior" que outro
modelo: não há segundo lado. Não diz que as tools são desnecessárias: a coluna
de resposta mede o gabarito de `fase0.xml`, feito para ser verificável, e não
um caso em que ler YAML não baste. `abst-03` (lista de campos truncada no
plano) saiu `false_certainty` em 3/3: o agente contou as colunas que o plano
mostrava, e esse é o erro que `plan.unresolved` existe para impedir.

**Duas execuções descartadas antes desta, e por quê:** uma na raiz do
repositório, em que o agente copiava o gabarito de `expected/` (ver o workspace
de prova, acima), e uma interrompida por um defeito do runner no Windows. O
runner lia a saída com o codepage local e, diante de um caractere fora dele,
recebia `stdout` vazio. Nenhuma das duas é baseline.

## Suíte do executor de debate — `evals/agentic/debate/` (2026-09-11)

A suíte tem três casos sobre o mesmo par de regras, `SF-GRAPH-005` ×
`SF-LF-001`, e a mesma união de facts (`uniao/findings.json` e
`uniao/facts.json`). Todos declaram `budget: {max_debates: 1, max_rounds: 3}`.
O que separa um caso do outro é o dump de `collect lakeformation` em
`artifacts/lakeformation/curated_arestas.json`. Em todos, o caso se decide pelo
fact `lakeformation.grant`, que o lado precisa **reextrair** pelo extrator
`lakeformation-grants`: o executor de debate não aceita fact escrito pelo
agente.

| Caso | `is_iam_allowed_principals` do grant | Gabarito |
|---|---|---|
| `lf_vence` | `false` (grant do LF ao runtime role, localização registrada) | vence `SF-LF-001` |
| `graph_vence` | `true` (só `IAM_ALLOWED_PRINCIPALS`, localização não registrada) | vence `SF-GRAPH-005` |
| `sem_fato` | nenhum `lakeformation.grant`: o coletor não podia ler (`sem_permissao`), e o extrator emite `lakeformation.grants.unresolved` | `unresolved`; um vencedor aqui é `false_resolution` |

```bash
# headless: um `claude -p` por vez de lado, no workspace de prova (sem expected.yaml)
python scripts/run_debate.py --model haiku --max-budget-usd 0.3
python scripts/run_debate.py --dry-run          # monta e mostra; nao gasta
# repontua uma execucao em ~/.sparkforge/debate-evals/<run>/
python -m sparkforge.evals debate --run <run>
```

Por caso, o placar sai em cinco desfechos: `correct_winner`, `wrong_winner`,
`correct_unresolved`, `false_resolution` e `missed_resolution`. Ao lado vêm as
rodadas, as submissões recusadas e o custo dos transcripts, com byte e token
separados (regra 22). A decidibilidade é conferida sem modelo por
`tests/test_debate_suite.py`, com submissões gravadas. Sem o fact, o caso fecha
`unresolved`. Com o fact, fecha no gabarito.

### Dois achados medidos que limitam o que esta suíte pode dizer

**(a) O catálogo tem exatamente UM par de conflito direto.** Sobre as 155
regras com `action` (`load_catalog()`, 2026-09-11), `direct_conflicts` devolve
um par só: `SF-GRAPH-005` × `SF-LF-001`, `glue.default_arguments`, `add` ×
`remove`. Nenhuma fixture sozinha o produz. O executor é genérico, mas hoje o
debate alcança esse único caso.

**(b) Esse par só nasce da UNIÃO dos facts de dois jobs diferentes.** São eles
`grafo_sem_jar` (sem FGAC, de `fixtures/graph/import_sem_jar_no_iac`) e
`etl_fgac_com_jar` (com FGAC, de `fixtures/infra_code/fgac_com_jar_extra`). Um
smoke real com `claude -p` (Haiku, US$ 0,0723) argumentou, dentro do próprio
debate, que o conflito pode não existir para nenhum dos dois jobs sozinho. Cada
job tem só a metade do conflito, e a união é que o fabrica.

**Consequência.** A suíte mede **mecânica e decidibilidade** com submissões
gravadas: vez, recusa, reextração, fechamento pelo `referee` e o desfecho que o
fact impõe. O baseline de modelo (B8 do DESIGN) **não foi rodado, de
propósito**. Ele mediria o desempenho de um modelo num tópico mal posto, e o
número não diria nada sobre o executor nem sobre o modelo. Não há, portanto,
afirmação de ganho do debate sobre a arbitragem determinística (regra 30). O que
destrava o baseline é um par de conflito direto que caiba num job só.


## Execuções registradas

### 2026-07-30 — primeira execução cruzada

Dois agentes, tamanhos de modelo diferentes, mesmas dez perguntas, sem acesso a
`fase0.xml`, `check_evals.py` nem a qualquer `expected/*.json`. Ambos derivaram tudo do
CLI e da API sobre as fixtures.

| Modelo | Resultado | Observação |
|---|---|---|
| Haiku 4.5 | 9/10 | única divergência foi de formato em Q6 |
| Sonnet 5 | 10/10 | apontou Q6 como ambígua por conta própria |

**A divergência não era erro de modelo.** Q6 perguntava "qual o nome do campo de
`measures` que ela compara". Haiku respondeu `run_length`, o corpus esperava
`measures.run_length`. As duas leituras estão corretas: uma é o nome do campo, a outra é
o caminho. Sonnet acertou o formato esperado e ainda assim registrou que
`threshold.run_length` seria uma terceira leitura defensável, já que a expressão compara
os dois lados.

Conforme a regra desta suíte, a correção foi **na pergunta**: ela agora pede
explicitamente o caminho pontuado do lado esquerdo da expressão, o lado do fact. Nenhum
modelo foi trocado e nenhuma resposta foi afrouxada.

Isso é a suíte funcionando como projetada. Ela não mediu qual modelo é melhor — mediu
onde a nossa própria especificação estava vaga, que é a única coisa acionável.



### 2026-07-30 — segunda rodada, três modelos

Depois de desambiguar Q6, uma terceira execução incluiu Opus.

| Modelo | Resultado | O que reportou |
|---|---|---|
| Haiku 4.5 | 9/10 | divergência de formato em Q6 |
| Sonnet 5 | 10/10 | apontou Q6 como ambígua |
| Opus 5 | 10/10 | apontou Q6 **e Q10**, esta última não vista pelos outros dois |

**O achado do Opus em Q10 é o mais valioso das duas rodadas.** A pergunta era
"quantas regras não-routing existem no catálogo". Duas leituras: contar o que
`load_catalog()` devolve (43, porque ele exclui `routing.yaml` por construção), ou
contar o diretório inteiro e subtrair as 16 de routing (59 − 16 = 43). **As duas
convergem em 43 por sorte, não por clareza da pergunta.** Um terceiro leitor poderia
entender "não-routing" como uma categoria dentro das 43 — que não existe — e responder
certo por caminho errado, ou travar e responder 59.

Uma pergunta cuja resposta certa é alcançável por raciocínio errado não mede nada. Foi
reescrita para nomear `load_catalog()` explicitamente.

> **Os números deste relato são de 2026-07-30 e não valem hoje.** O catálogo tinha 43
> regras de diagnóstico; hoje tem **48**, depois de a Fase 2 desbloqueá-lo e a Fase 3a
> acrescentar SF-PLAN e SF-CG. As 16 rotas seguem 16. A pergunta acabou reescrita uma
> terceira vez, justamente porque **contagem total é resposta que envelhece** — a §11.3
> do spec da Fase 0 exige resposta que não mude com o tempo, então a pergunta é que
> estava errada, não o número. Hoje ela pergunta `routing:athena`, cujo primeiro termo é
> 0 por construção.

Q6 foi reescrita uma segunda vez: Opus notou que "o caminho pontuado do lado esquerdo...
o lado do fact" podia sugerir incluir o kind (`pyspark.withcolumn_run.measures.run_length`).
Agora pede o texto exato copiado do YAML.

**Padrão das duas rodadas:** nenhuma das cinco execuções produziu um erro de análise. Os
três modelos derivaram os mesmos números do mesmo corpus. Todo desacordo foi sobre o que a
**pergunta** queria. É o resultado que a arquitetura prevê — a extração e o julgamento são
determinísticos, então o que sobra para variar é a especificação, e é isso que a eval
mede.

**Não medido:** Devin não foi executado.

---

## `holdout/` — cenários retidos

`evals/holdout/` guarda dois cenários de migração no formato de
`fixtures/scenarios/` (`meta.yaml` + `input/` + `expected/assessment.json`), com
uma regra a mais: **nenhum arquivo de `skills/`, `agents/` ou `knowledge/` cita o
nome de um diretório desse corpus**.

Ela existe para o nível de agente, não para o determinístico. O extrator e o
motor de regras não leem skill nenhuma, então um golden citado numa skill não
corrompe nada do que a seção anterior descreve. Um agente é outra coisa: ele é
instruído por `skills/`, `agents/` e `knowledge/`, e um exemplo resolvido dentro
das instruções é resposta disponível, não capacidade demonstrada.

`tests/test_evals_holdout.py` **prova** a propriedade a cada execução da suíte —
sem ele, "holdout" seria só um nome de pasta. Ver `evals/holdout/README.md` para
o que cada cenário retém e como mexer sem estragar.
