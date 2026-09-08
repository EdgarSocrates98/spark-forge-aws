# Executor agêntico determinístico — o que decide, e onde para

**Data:** 2026-09-08
**Estado:** desenho aprovado, implementação não iniciada
**Origem:** triagem de `prompt_evo_20.md` (68 propostas), seções 40 a 45 e 67
**Fecha:** a lacuna que a regra 29 do `CLAUDE.md` nomeia — a camada agêntica é
biblioteca, e nenhum extrator, regra, tool ou coordenador escreve
`Claim`/`Evidence`/`Decision`

---

## 1. Contexto

`sparkforge/agentic/` tem 13 módulos, 9 entidades com id content-addressed e 261
testes. As primitivas existem e são exercitadas: `should_trigger_debate`,
`arbitrate`, `assess_claim`, `make_decision`, `generate_adr`,
`design_experiment_for_unknown`, `compute_independence_score`,
`detect_false_consensus`, `validate_autonomy_boundary`, e o blackboard JSONL com
`append_*`/`read_*` por entidade.

Nenhuma delas é chamada por nada. Num repositório de trabalho
`sparkforge blackboard summary` devolve zero em todas as contagens, e a regra 29
declara que esse é o estado correto, não defeito. `decisions list` e
`decisions explain` leem um arquivo que ninguém escreve.

O pipeline de diagnóstico hoje é `facts → fuse → judge → findings → next_step →
coordenador`. `judge` decide **se a regra dispara**; `next_step` decide **para
quem despachar**. Ninguém decide **o que fazer, em que ordem, e o que foi
recusado** — e é isso que esta entrega acrescenta.

### 1.1 A triagem que definiu o escopo

Das 68 propostas de `prompt_evo_20.md`, aproximadamente 40 já existem medidas
neste repositório (`sparkforge_workload`, `analyze_plan`, `finops`, `capacity`,
`tune`, `benchmark`, `analyze_iceberg`, `migration_assess`, `economy report`, as
68 tools MCP, os 38 coordenadores) e cerca de 10 conflitam com regra declarada
do próprio projeto — simulação de capacidade não observada (regra 12), economia
estimada (regra 13), `confidence: 87%` e scores agregados publicados como
medida, previsão de volume.

O que sobra e é ancorável em artefato tem nove itens. Este spec cobre **um**: o
executor. Os outros oito (footer Parquet, Avro, JSON, read amplification
Iceberg, custo de passada em DQ, benchmark estatístico, lineage, root cause
graph, fingerprint de regressão) ficam registrados aqui como triagem e não
entram no escopo.

---

## 2. Decisão de arquitetura

**Abordagem C — híbrido com fronteira declarada.** O executor é determinístico e
completo: as quatro decisões abaixo saem sem host nenhum, sem chamada a provider,
no CI, com fixture golden. Quando a contradição **não** fecha
determinísticamente, ele emite um plano de debate e **para**, com recusa
nomeada.

Alternativas descartadas, com a razão:

- **A, determinístico puro sem plano de debate.** Deadlock sairia como achado sem
  decisão, e o operador não saberia o que destravaria. Emitir o plano custa
  pouco e é a diferença entre "não sei" e "não perguntei" (regra 20).
- **B, mediado pelo host.** Implementar `AgentRuntime` concreto e debater com
  fala de coordenador. Descartada porque não roda sem host, o teste vira fake
  runtime, e nenhum gate confere a qualidade da fala — que é exatamente o modo
  de falha que a auditoria de 2026-09-03 mediu na entrega original (206 testes
  fixando o comportamento defeituoso).

O executor **não** chama provider. `sparkforge/` não importa `anthropic`,
`openai`, `bedrock` nem `litellm`, e esta entrega não muda isso (regra 23).

---

## 3. O campo `action:`

Cada uma das 112 regras executáveis ganha um bloco `action:`. A forma:

```yaml
action:
  kind: timeout.increase_limit      # vocabulário fechado
  target: spark.network.timeout     # propriedade ou recurso que a mudança toca
  direction: increase               # increase|decrease|replace|remove|add|investigate
  requires_absent:                  # o que NÃO pode estar medido junto
    - spark.skew.severe
    - spark.stage.spill
  moves:                            # eixos que a mudança move
    - runtime.wall_clock
  depends_on: []                    # ids de ação que precisam vir antes
```

### 3.1 Por que cada campo existe

`requires_absent` **codifica prosa que já está escrita e nenhuma máquina lê**. A
regra 15 do `CLAUDE.md` publica que aumentar o limite de timeout com skew,
spill, GC ou executor perdido ao lado troca uma falha rápida por uma falha cara.
`SF-TIMEOUT-001` já carrega `attrs.also_seen` no fact; falta o outro lado da
ponte — a declaração, na regra que propõe a mudança, do que a desaconselha.

`direction: investigate` é a saída honesta para regra que não propõe mudança e
sim medida. `SF-WASTE-001` manda rodar `sparkforge capacity`, não manda reduzir
worker — e forçá-la a declarar `decrease` seria inventar uma recomendação que o
`proposed_change` dela recusa por escrito.

`moves` liga com o `validation` que 112 das 147 regras já têm, e não o duplica:
`validation` diz **como conferir que o resultado não mudou**; `moves` diz **qual
eixo a mudança deveria mover**. Os dois juntos são o que torna um antes/depois
atribuível.

`depends_on` é ordem declarada. A ordem derivada está na seção 5.4.

### 3.2 O vocabulário de `kind`

O vocabulário é fechado e o gate recusa `kind` fora dele. **A lista final não é
inventada neste spec**: ela é produzida na implementação lendo os 112
`proposed_change` e agrupando por eixo, e só então travada. Inventar a lista aqui
e depois torcer as regras para caberem nela é o defeito que `EMR_MATRIX` literal
em código tinha contra a matriz em YAML.

Os eixos que a leitura vai encontrar, pelas áreas do catálogo: capacidade,
timeout, shuffle, skew, join, layout de armazenamento, código PySpark,
configuração Spark, segredo e permissão, manutenção de tabela, schema,
orquestração. O gate exige as duas direções: toda regra executável tem `kind`, e
todo `kind` do vocabulário tem ao menos uma regra que o usa — vocabulário não
incha com entrada morta.

### 3.3 Versionamento

`schema_version` do catálogo permanece em `1`. O campo é aditivo, todo leitor
antigo o ignora, e nenhum limiar ou semântica de finding muda. O precedente é a
Fase 4b, que acrescentou `strict_gates` e `gate_overrides` ao `case.yaml` sem
subir o `schema_version` pela mesma razão. `catalog_version` também permanece em
`1`: nenhum limiar existente mudou.

### 3.4 A lacuna de tier, nomeada e não resolvida por invenção

Os tiers T1-T6 graduam **fonte de conhecimento**. Não há tier para **medida do
artefato do cliente**, e não vai ser inventado um.

Uma `Evidence` produzida pelo executor carrega dois campos que nunca se fundem:

- `authority` — o tier da fonte que sustenta o limiar da regra, derivado das URLs
  em `sources:` (seção 5.2);
- `measurement_ref` — o `fact.id` que casou com o `when` da regra.

Fundir os dois num tier só produziria um número que não mede nada, na mesma
família da regra 22 (byte e token não se somam).

---

## 4. Contradição

Dois modos, e os dois produzem uma `Contradiction` no blackboard com os
`fact.id` dos dois lados:

**Direta.** Duas ações com o mesmo `target` e `direction` oposta.

**Condicional.** O `requires_absent` de uma ação está **medido** no mesmo case —
`timeout.increase_limit` sobre `spark.network.timeout` com `spark.skew.severe`
presente nos facts.

Alvos diferentes **não** são contradição. São ordem, e caem na decisão 4.

---

## 5. As quatro decisões

### 5.1 Conflito entre achados

`arbitrate(claims, evidences, target_runtime, target_version)` ordena as claims
em disputa.

**O score de `assess_claim` não sai publicado.** O `CLAUDE.md` já declara que os
pesos (evidência 40%, autoridade 30%, especificidade 20%, aplicabilidade 10%)
são convenção e que nenhum experimento os calibrou. Ele ordena internamente e
aparece no trace rotulado como convenção, nunca como confiança medida.

O `confidence` da `Decision` vem de tabela conferível:

| `confidence` | Condição |
|---|---|
| `high` | fonte T1/T2 vigente e no escopo de versão do case, todas as medidas exigidas presentes, nenhuma contradição aberta |
| `medium` | fonte com autoridade mas fora do escopo de versão, ou arbitragem `disputed` resolvida |
| `low` | fonte T4 ou pior, ou medida exigida ausente |

`detect_false_consensus` entra com uso real: duas regras da mesma área citando a
**mesma** página da AWS não são duas evidências independentes, são uma. A
correção de 2026-09-03 já fez `independence_score` valer o elo fraco (`min`) e
contar a fonte por ligação `supports`.

### 5.2 Lastro suficiente para virar recomendação

O tier de cada fonte é derivado do host da URL em
`knowledge/sources.lock.json`, por mapeamento declarado em
`knowledge/source_authority.yaml`:
`docs.aws.amazon.com`, `spark.apache.org`, `iceberg.apache.org`,
`parquet.apache.org` → T1; página de release notes e código-fonte de projeto →
T2; o resto → T4. O mapeamento é dado versionado, não código, pela mesma razão
que a matriz de runtime é YAML.

`has_fresh_in_scope` cruza tier com o `runtime_scope` da regra contra o
`RuntimeContext` do case. **Uma T1 fora da versão alvo tem autoridade e não
sustenta a claim** — é essa diferença que a auditoria separou de
`has_sufficient_authority`, quando as duas eram a mesma expressão.

Claim reprovada aqui **não vira recomendação**. Vira `Unknown` nomeando a medida
ou a fonte que a destravaria. Regra 20.

### 5.3 Qual medida falta, e como obtê-la

Três origens de `Unknown`:

1. fact exigido pela regra que saiu `*.unresolved`;
2. claim reprovada em 5.2;
3. arbitragem que devolveu `recommendation: experiment`.

`design_experiment_for_unknown` já existe e produz o plano: o que rodar, o que
medir, critério de aceite.

Duas amarras que a entrega original não tinha:

- **sem previsão de ganho.** O experimento diz o que medir; nunca quanto vai
  melhorar. Regra 13.
- **custo e tempo saem `unresolved`** a menos que haja `glue.run_cost` de run
  comparável. A auditoria de 2026-09-03 pegou "custo e tempo de experimento
  fixos em texto" como um dos catorze defeitos, e a correção não pode voltar
  por aqui.

### 5.4 Ordem de aplicação

Ordenação topológica sobre `depends_on`, mais duas restrições derivadas:

- ação `investigate` sobre um `target` vem **antes** de qualquer ação que mude
  aquele `target` — medir antes de mexer;
- **duas ações que compartilham eixo em `moves` não entram no mesmo run.**
  Aplicar juntas duas mudanças que movem `runtime.wall_clock` torna o
  antes/depois inatribuível, e atribuir a melhora a uma delas exigiria o run que
  não aconteceu. Sai como restrição de sequenciamento com a razão nomeada — não
  como proibição de aplicar.

Ciclo no grafo → `order.unresolved` nomeando os ids do ciclo. Nunca ordem
arbitrária.

---

## 6. `DebatePlan` — o que sai quando não fecha

Gatilho: arbitragem `disputed` com autoridade empatada, ou
`recommendation: escalate`.

O plano nomeia:

- **participantes** — coordenadores derivados de `rules/catalog/routing.yaml`
  pela área de cada regra em disputa;
- **contexto por participante** — quais `fact.id` cada um receberia;
- **rodadas e critério de parada** — dentro do bloco `budget:` do `case.yaml`.
  Sem o bloco, `budget.unresolved` e o plano sai sem limites, nunca com os
  defaults do código travestidos de estado do case. Foi esse exato defeito que a
  auditoria corrigiu em `budget show`.

Depois de emitir, **para**, com `debate.unresolved` dizendo que este pacote não
tem executor de debate e o que destravaria — um `AgentRuntime` concreto,
implementado fora do pacote pelo host.

---

## 7. Superfície e gravação

**CLI:** verbo novo `sparkforge arbitrate --findings <path> --facts <path>
--repo .`. A forma dos argumentos segue `sparkforge_judge` (findings e facts
vêm de arquivo, `--repo` diz onde fica o blackboard), e não `--case <id>`:
nenhum verbo agêntico existente recebe id de case, todos recebem `--repo`.
`decisions list` e `decisions explain`, que já existem, passam a ler o que ele
escreveu.

**MCP:** tool nova `sparkforge_arbitrate`. Contagem 68 → **69**, e o crescimento
de superfície vai medido e declarado na mensagem de commit
(`python scripts/check_surface_lock.py --update`, regra 26).

**Autonomia do executor: L0.** Ele escreve decisão e nunca aplica mudança. O ADR
é proposta com `rollback` obrigatório — `make_decision` já recusa sem ele —, não
registro de coisa feita. `validate_autonomy_boundary` recebe
`guardrails_satisfied` do chamador; o executor não passa lista nenhuma porque não
pede ação de risco.

**Gravação:** `.sparkforge/blackboard/*.jsonl` do case — `claims`, `evidence`,
`contradictions`, `unknowns`, `experiments`, `decisions`, `traces` — e um ADR por
decisão que `is_significant_decision` aprove.

`Claim.id` já cobre `evidence_refs`, `assumptions` e `confidence`, com
`supersedes` opcional. Rodar o executor duas vezes sobre o mesmo case com facts
novos **registra revisão**; antes da correção de 2026-09-03 colidia como
duplicata e o blackboard recusava.

**Medição nunca derruba a chamada** (regra 27): blackboard indisponível, disco
cheio ou span que falha ao ser montado não impedem a resposta do verbo.

---

## 8. Fixtures e gates

### 8.1 Fixtures

Domínio novo `fixtures/arbitration/`, um par positivo/negativo por caminho — o par é o que prova o
limiar, no molde de `janela_no_teto_de_datas` contra
`janela_acima_do_teto_de_datas`:

- contradição direta (mesmo `target`, direções opostas);
- contradição condicional (timeout com skew medido ao lado, contra o mesmo case
  sem skew);
- lastro insuficiente por versão fora de escopo (T1 vigente contra T1 fora do
  `runtime_scope`);
- fact `unresolved` que vira `Unknown` com a medida nomeada;
- ciclo em `depends_on` que vira `order.unresolved`;
- deadlock que vira `DebatePlan`, contra o mesmo case que fecha.

### 8.2 Gates

- `tests/test_rules_action_field.py` — toda regra executável tem `action`, todo
  `kind` está no vocabulário, e todo `kind` do vocabulário tem ao menos uma
  regra que o usa.
- `tests/test_agent_coverage.py` — `sparkforge_arbitrate` alcançável a partir de
  algum coordenador.
- `tests/test_suite_batches.py` — cada arquivo de teste novo cai em exatamente
  um lote, e a soma dos lotes fecha com a coleta.
- `python scripts/check_surface_lock.py --update` — tool nova move a superfície.
- `python scripts/check_vnext_claims.py` — todo número publicado em `docs/`
  passa pelo gate de lastro, e a remediação é por lista de ids tirada da saída
  do gate.
- `python scripts/check_status_numbers.py --strict`.
- A suíte em lotes, um por vez, nunca inteira num processo só.

---

## 9. Documentação que a entrega move

- `docs/superpowers/STATUS.md` — seção da fase e os números: regras com `action`,
  tools 69, fixtures por domínio, total de testes, lotes remedidos.
- `docs/agentic-evolution-report.md` — estado por componente, com o executor
  saindo de inexistente para determinístico.
- `README.md` e `AGENTS.md`.
- **`CLAUDE.md`, regra 29, reescrita e não apagada.** O executor determinístico
  passa a existir e o blackboard deixa de ser zero num case rodado; o que
  continua não existindo é o executor de **debate**. A regra 30 permanece
  inteira: nenhum benchmark da arquitetura nova contra a antiga, e por isso
  nenhuma afirmação de ganho.

---

## 10. O que fica de fora, explícito

- `AgentRuntime` concreto. Nada neste pacote faz spawn de agente.
- Debate com fala de agente. O plano é emitido; a execução dele não.
- Qualquer número de melhoria esperada — `-31% runtime`, `confidence 87%`,
  `economia de $X`. Regras 11, 13 e 30.
- Score agregado publicado como confiança medida.
- As outras oito propostas ancoráveis da triagem da seção 1.1.

---

## 11. Riscos

**O maior é o tamanho de 3.** Declarar `action:` em 112 regras é a parte que
domina a entrega, e é trabalho de leitura — cada `proposed_change` em prosa
precisa virar `kind`/`target`/`direction` sem que a regra passe a propor coisa
que ela não propunha. O modo de falha é declarar `decrease` onde o
`proposed_change` diz "investigue", e o `direction: investigate` existe para
impedir isso.

**O segundo é o vocabulário fechado cedo demais.** Travar a lista antes de ler
as 112 forçaria regras a caberem em `kind` errado. A ordem obrigatória é ler,
agrupar, e só então travar o gate.

**O terceiro é o teste escrito a partir do código.** Foi o que produziu os 206
testes verdes sobre catorze defeitos na entrega original. As fixtures desta
entrega são escritas como par positivo/negativo **antes** da implementação de
cada caminho, e o par é o que prova que o limiar é o que se diz que é.


---

## 12. Desvios medidos durante a implementação

Esta seção é acréscimo, não reescrita. O corpo acima fica como foi aprovado, e
o que a execução mediu contra o catálogo real entra aqui.

### 12.1 O exemplo canônico da §3.1 e da §4 está invertido

O spec usa, nas duas seções, `timeout.increase_limit` sobre
`spark.network.timeout` com `requires_absent: [spark.stage.skew,
spark.stage.spill]` como o caso que `requires_absent` existe para pegar.

**Medido em 2026-09-08, contra `rules/catalog/timeout.yaml`:** `SF-TIMEOUT-001`
não propõe aumentar limite nenhum. O título dela é *"Timeout com sintoma medido
ao lado — aumentar o limite mascara a causa"*, o `when` dispara **apenas** com
skew, spill, GC ou executor perdido acima do limiar, e o `proposed_change` manda
ler `attrs.category`, investigar o sintoma, e só depois avaliar o limite. Ela é
`direction: investigate`.

A guarda que a §3.1 queria mover para `requires_absent` **já está no `when` da
regra**. Não existe, no catálogo de hoje, regra que proponha
`timeout.increase_limit` — logo o par que a §4 chama de contradição condicional
não tem produtor.

### 12.2 `requires_absent` cruza por kind, e o sintoma costuma ser measure

O lote A mediu a razão estrutural: `requires_absent` compara **fact kinds**, e
o sintoma que desaconselha uma ação costuma ser uma **measure dentro de um
kind** que sai sempre. `glue.utilization.summary` carrega
`measures.skew_p95_over_p50` em toda coleta; `spark.stage.spill` e
`spark.stage.gc` são emitidos para todo stage analisado, inclusive com zero
byte — o comentário de `event_log.py:826` registra isso. Presença de kind não é
sintoma, e a guarda por kind não vale.

Consequência: 24 das 27 regras do lote A saíram com `requires_absent: []`, e as
três que receberam guarda usam kinds de recusa (`emr.configuration.unapplied`,
`emrc.pod_template.unresolved`), não de sintoma.

### 12.3 O que fica decidido

`requires_absent` **permanece** no schema. Ele custa uma chave opcional e é o
que o executor vai usar no dia em que uma regra propuser mudança que outra
desaconselhe por medida própria.

O que muda é a **afirmação**: ao fim da Fase 2, a entrega mede quantas das 112
declaram `requires_absent` não vazio e publica o número. Se a contradição
condicional não tiver caso no catálogo de hoje, isso sai escrito — mecanismo sem
caso é `unresolved` nomeado, não funcionalidade entregue. A contradição
**direta** (mesmo `target`, direções opostas) é medida no mesmo passo, e pela
mesma régua.

Destravar a guarda por sintoma exige um kind emitido só acima do limiar
(`glue.utilization.skew_high` ou equivalente por stage). Isso é entrega própria,
no extrator, e não entra aqui.


### 12.4 A Fase 2 fechou, e as medidas mudam o motor

Catálogo completo em `d8cd9c2`: **112 de 112** com bloco `action`, vocabulário de
**66 `kind`** (dez apagados por não serem ação dominante de regra nenhuma) e
**22 eixos**.

**A ação é de mudança em 89 das 112; `investigate` são 23.** A leitura dos dois
primeiros lotes sugeria o contrário, e estava errada — os lotes A e B são as
áreas onde o catálogo mais manda medir antes de mexer. No conjunto, ele
prescreve.

**A contradição direta tem exatamente UM caso, e ele é melhor que o exemplo que
este spec inventou.** `SF-GRAPH-005` manda declarar o jar de GraphFrames em
`--extra-jars` do `default_arguments`; `SF-LF-001` manda removê-lo, porque
**a AWS não oferece modo de FGAC que aceite JAR adicional** e o texto da regra
diz que não existe meio-termo. Um job que usa GraphFrames e tem controle de
acesso fino do Lake Formation dispara as duas, e elas são incompatíveis por
limitação de plataforma **documentada** — não por heurística. É o caso canônico
que a §4 procurava e a §12.1 mostrou não existir no timeout.

**`correctness.write_result` não é eixo de medida, e tratá-lo como um quebra as
duas coisas que dependem de `moves`.** Ele aparece em 33 das 112 — é o eixo que
diz *o resultado pode se mover*, ou seja, **risco semântico**, não grandeza
comparável. Duas consequências medidas:

- **Contradição:** com ele no teste, `SF-PLAN-003` (acrescentar a equi-condição
  que falta) e `SF-PY-009` (remover hint de broadcast) saem como par contraditório
  — mesmo `target: pyspark.join`, direções opostas, `correctness` em comum. São
  coisas diferentes no mesmo construto, e o par é falso positivo. Excluindo-o,
  sobra só o caso real.
- **Sequenciamento:** a restrição da §5.4 (duas ações no mesmo eixo não entram no
  mesmo run, porque o antes/depois fica inatribuível) produziria um grupo de
  **33 regras**. Isso é ruído. Sem ele, são 15 eixos e o maior grupo tem 10.

A razão é principiada, não conveniência: a restrição existe por causa da regra 13
— aplicar duas mudanças que movem a mesma **medida** torna a atribuição
impossível. Duas mudanças que ambas *podem alterar o resultado* não têm esse
problema; o que elas exigem é validação funcional de cada uma, que é outro
mecanismo (`funcval`).

**Decidido:** `axes:` ganha `nature: measure | risk`. `conflict.py` e
`ordering.py` consideram **só** os de `nature: measure`.

### 12.5 `requires_absent`: 4 em 112, nenhuma de sintoma

Confirmado sobre o catálogo inteiro. As quatro guardas são
`emr.configuration.unapplied` (duas), `emrc.pod_template.unresolved` e
`env.unresolved` — todas **kinds de recusa**, que dizem *não deu para ler*, não
*o problema está presente*.

Onze candidatas foram medidas e recusadas ao longo dos sete lotes, sempre por um
de dois motivos: o kind **sai sempre** (`spark.stage.spill` e `spark.stage.gc`
saem para todo stage, inclusive com zero byte —
`sparkforge/facts/event_log.py:826`), ou **sai por motivos sem relação**
(`iceberg.unresolved` cobre `read_error`, `malformed_json` e três de
`format_version` no mesmo kind).

**A contradição condicional não tem caso no catálogo de hoje.** Isso sai
publicado assim, com a medida que a destravaria nomeada — um kind emitido só
acima do limiar, ou um `requires_absent` que saiba cruzar por `attrs` além do
kind. Mecanismo sem caso é `unresolved` nomeado, nunca funcionalidade entregue.

### 12.6 `depends_on` é o que tem mais lastro

**17 arestas em 15 regras**, a maioria citada literalmente no texto das regras
(`SF-ATH-001/-002/-005 → SF-ATH-004`, "antes de *qualquer* reescrita de SQL";
`SF-UI-001 → SF-UI-002`, classificar o skew antes de tratá-lo;
`SF-ICE-001 → SF-ICE-005`, corrigir na origem primeiro).

A decisão 4 do spec — ordem de aplicação — é a que chega à Fase 3 com mais caso
real. A decisão 1 (conflito) chega com um. As duas continuam no escopo, e o
relatório publica os dois números lado a lado.
