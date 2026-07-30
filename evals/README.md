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
16 fixtures, ambas as direções: facts e findings) e por
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
`sparkforge` e compara a resposta literal com `evals/fase0.xml`. Não há
harness automatizado de execução de agente neste repositório — isso é
responsabilidade de quem opera a plataforma de avaliação (Claude, Devin).


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

Q6 foi reescrita uma segunda vez: Opus notou que "o caminho pontuado do lado esquerdo...
o lado do fact" podia sugerir incluir o kind (`pyspark.withcolumn_run.measures.run_length`).
Agora pede o texto exato copiado do YAML.

**Padrão das duas rodadas:** nenhuma das cinco execuções produziu um erro de análise. Os
três modelos derivaram os mesmos números do mesmo corpus. Todo desacordo foi sobre o que a
**pergunta** queria. É o resultado que a arquitetura prevê — a extração e o julgamento são
determinísticos, então o que sobra para variar é a especificação, e é isso que a eval
mede.

**Não medido:** Devin não foi executado.
