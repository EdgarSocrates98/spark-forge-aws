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

**Não medido:** Devin e Opus não foram executados nesta rodada.
