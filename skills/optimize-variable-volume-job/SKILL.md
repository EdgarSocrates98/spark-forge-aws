---
name: optimize-variable-volume-job
description: Use quando o mesmo job Glue roda de dezenas de registros a centenas de milhões e um único perfil configurado para o pior caso fica caro em microcarga e ainda inadequado no full. Use também quando a pergunta for "por que a carga vazia demora 5 minutos", "o job de teste custa quase igual ao de produção" ou "ficou mais lento essa semana" num job cujo volume varia muito entre execuções. Se você está prestes a comparar runs de volumes diferentes só de cabeça, rode `sparkforge analyze event-log` em cada run e `sparkforge analyze pyspark` no código em vez disso — subparalelismo (SF-UI-006) que é esperado numa carga micro é sintoma real numa carga full, e o catálogo não distingue os dois perfis sozinho; quem separa é você.
---

# Optimize Variable Volume Job

O catálogo julga cada execução isoladamente contra o mesmo limiar. `SF-UI-006` (subparalelismo) dispara igual num run de 200 linhas e num de 200 milhões — mas só o segundo é um achado real. Separar por perfil de volume é o que esta skill faz que o `judge` sozinho não faz.

## Procedimento

1. **Classifique as execuções por perfil** (empty, micro, small, medium, large, full/bootstrap) a partir do volume real de entrada de cada uma. Os limites vêm do workload observado, não de um valor universal.
2. Para cada perfil relevante, colete e extraia separadamente: `sparkforge collect event-log --repo . --job-run <id> --bucket <bucket> --prefix <prefix> --now <ISO8601>` → `sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id>.jsonl --out .sparkforge/facts_<perfil>.json`.
3. `sparkforge analyze pyspark --path <lib> --out .sparkforge/code_facts.json` extrai os facts estruturais (join, partitioning, hint de broadcast, loop) que não mudam entre execuções — são decisões congeladas no código, não no volume do dia.
4. `sparkforge judge --facts .sparkforge/facts_<perfil>.json --show-skipped` **em cada perfil separadamente**. Não julgue um `facts.json` que misture execuções de perfis diferentes — a mesma regra significa coisas opostas em cada um. Sem flag de versão: cada facts de event log já declara a versão do Spark observada naquele run (`spark.runtime_version`), e `judge` a usa sozinho — leia o campo `runtime` de cada saída, com `detected_from: ["event_log"]`. **É a checagem que esta skill mais precisa e a mais fácil de esquecer:** comparar perfis só faz sentido entre runs do mesmo runtime, e um `runtime.spark` diferente entre dois perfis significa que a diferença de findings pode ser de versão, não de volume. Para conferir os dois de uma vez sem abrir cada saída: `sparkforge runtime detect --facts .sparkforge/facts_<perfil_a>.json --facts .sparkforge/facts_<perfil_b>.json` — `divergences` vazio é o aceite.
   O event log preenche `spark`, não `glue` (a matriz de compatibilidade deriva numa direção só), então `SF-GLUE-001` — que é justamente a regra estrutural desta classe de job — fica em `--show-skipped` com `reason: runtime_scope`. Para cobri-la, junte os facts do Terraform na mesma chamada (`--facts` é repetível) em vez de digitar a versão; `--glue 5.1` só quando você a souber de fonte confiável.
5. Compare os findings entre perfis: o que dispara só no `empty`/`micro` é custo fixo (cold start, planejamento); o que dispara em todos os perfis, incluindo `full`, é estrutural no código, não do volume do dia.
6. Duração e DPU-hours por run não vêm de um extrator de facts — leia do job run do Glue (`sparkforge collect glue-job` traz a definição, não o histórico de runs) ou do CloudWatch bruto (`sparkforge collect cloudwatch`), manualmente, para separar custo fixo de custo proporcional ao volume.

## O que interpretar por perfil, não pelo limiar isolado

- **`SF-UI-006` no perfil `empty`/`micro`**: esperado, não é achado — poucas tasks porque há pouco dado, não subparalelismo real. No perfil `full`: real, e custa DPU-hours pagas e ociosas.
- **`SF-PY-009` (hint de broadcast fixo)**: decisão de código que não se adapta ao volume. O lado "pequeno" no perfil `full` pode não ser mais pequeno, e o hint não vai avisar.
- **`SF-GLUE-001` (Auto Scaling em conflito com `number_of_workers` fixo)**: um job de volume variável quase sempre deveria ter Auto Scaling; capacidade fixa dimensionada para o `full` paga o mesmo custo fixo em toda execução `empty`.
- **`SF-PY-004` (action/write em loop)**: o custo domina nos perfis `large`/`full`, onde o loop de batches de fato itera muitas vezes; num perfil `micro` pode nem chegar a rodar mais de uma iteração.

## Referência rápida

| Regra | Fact que consome | O que acusa — e por que depende do perfil |
|---|---|---|
| `SF-UI-006` | `spark.stage.task_count`, `spark.cluster.cores` | Tasks abaixo dos cores disponíveis — real no `full`, esperado no `empty`/`micro` |
| `SF-PY-009` | `pyspark.join` (hint de broadcast) | Estratégia de join congelada no código, nunca reavaliada por volume |
| `SF-GLUE-001` | `tf.attribute` | Capacidade fixa onde o volume varia é o sintoma estrutural mais comum desta classe de job |
| `SF-PY-004` | `pyspark.loop` | Custo de loop que só aparece — e domina — nos perfis grandes |

Limiares e severidade vêm de `sparkforge rules lookup --id <ID>`, nunca de memória.

## Quando NÃO usar

- O volume é estável entre execuções: use `tune-glue-job` para um único perfil bem dimensionado.
- O foco é provar que o incremental reduz trabalho frente ao full: use `design-incremental-processing`.
- Já isolou um perfil e só falta dimensionar workers para ele: use `tune-glue-job`.

## Red flags

- Julgar um `facts.json` que combina execuções de perfis diferentes e tirar uma conclusão só dele.
- Configurar um job único para o pior caso e pagar esse custo em toda microcarga.
- Não ter curto-circuito para execuções sem mudança (`empty`/`micro`) — o toolkit não detecta "sem mudança desde a última execução"; essa lógica é do seu job, não do sparkforge.
- Misturar full, incremental e manutenção Iceberg no mesmo job ou fila, escondendo qual perfil está pagando qual custo.

## Preservar o resultado, com o verbo que produz a evidência

O curto-circuito para `empty`/`micro` é a recomendação desta skill que mais parece inofensiva
e mais mexe no dado: pular a execução quando "não houve mudança" só preserva o resultado se a
detecção de "sem mudança" estiver certa. Errada, ela não falha — ela deixa o destino com o
conteúdo do run anterior, e nenhum alarme dispara.

`sparkforge funcval plan --facts <facts.json> --out <plano.json>` deriva o plano — `--facts`
é repetível, porque o alvo vem do `pyspark.write` e o schema e os agregados vêm do
`catalog.table_schema` —, e `sparkforge funcval compare --plan <plano.json> --before
<antes.json> --after <depois.json>` compara os dois lados **que o operador mediu**: nenhum dos
dois executa consulta, roda Spark ou chama AWS. Tools MCP: `sparkforge_funcval_plan` e
`sparkforge_funcval_compare`. O plano é a evidência do gate `functional_validation_defined`, e
`ROUTE-015` é a rota que manda defini-lo. O lado `--before` só existe se alguém o mediu
**antes** de a mudança tocar o alvo — um `overwrite` no meio o apaga sem deixar rastro.

Os quatro eixos são **proxies**, e escrever o contrário promete o que a ferramenta não
entrega: contagem, schema, chaves e agregados iguais **não provam** que o dado é o mesmo — duas
linhas podem trocar valores entre si e os quatro passam. Escreva "nenhum dos quatro proxies
detectou divergência", nunca "o resultado é idêntico". Sem `--key`, a chave de negócio sai em
`undeclared_axes` com a razão, e isso vai dito. `SF-FVAL-005` acesa invalida a leitura das
outras quatro.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita. E **derive o plano de validação funcional** com `funcval plan` antes de fechar a
recomendação, comparando os dois lados medidos com `funcval compare` — a regra 10, e ela
nomeia o produtor de propósito: exigência sem verbo é prosa.
