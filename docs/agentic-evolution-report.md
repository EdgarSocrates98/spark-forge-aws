# SparkForge Agentic Evolution Report

**Entrega:** 2026-09-03
**Auditoria e correções:** 2026-09-03 (mesma data, sessão seguinte)
**Executor determinístico:** 2026-09-08, branch `feat/executor-agentico-spec`
**Executor de debate:** 2026-09-11, branch `feat/debate-executor`
**Branch:** `audit/fakes-de-coleta`
**Spec:** `docs/superpowers/specs/2026-09-03-sparkforge-agentic-evolution-design.md`
**Spec do executor:** `docs/superpowers/specs/2026-09-08-sparkforge-executor-agentico-design.md`

## Resumo executivo

O SparkForge ganhou uma **biblioteca agêntica** em `sparkforge/agentic/`: 13
módulos, 9 entidades de primeira classe, protocolo de debate formal, arbitragem
com detecção de falso consenso, desenho de experimentos, decisões auditáveis com
ADR, memória institucional cross-case, budget unificado, threat model com 12
tipos, níveis de autonomia L0-L5 e Agent Execution Graph.

**Em 2026-09-08 a camada ganhou um produtor, e ele é determinístico.**
`sparkforge/agentic/executor/` — 7 módulos, 163 testes — lê os findings que
`judge` produziu e a UNIÃO dos facts do case, e escreve `Claim`, `Evidence`,
`Contradiction`, `Unknown` e `Decision` no blackboard. Exposto por
`sparkforge arbitrate` e pela tool `sparkforge_arbitrate`.

**Em 2026-09-11 o `DebatePlan` passou a ter executor, e ele também é
determinístico.** `executor/debate_run.py` é uma máquina de estados L0 sobre
arquivos do case: `sparkforge debate start|next|submit` (tools
`sparkforge_debate_start|next|submit`) congela o plano do par, diz de quem é a
vez, recusa por nome a submissão que fere o protocolo e fecha **sempre** pelo
`referee`. A geração do argumento fica fora do pacote, no host: a skill
`run-debate` (interativa) ou `scripts/run_debate.py` (`claude -p`, headless).

**O que ela ainda não é, e a distinção é o ponto desta página:** nenhum
`AgentRuntime` concreto mora no pacote, nada aqui chama provider (regra 23), e
os dois executores são **L0** — `applied_changes` sai sempre `false`, e o ADR é
proposta com `rollback` obrigatório. **Não há benchmark** do debate contra a
arbitragem determinística, e por isso nenhuma afirmação de ganho (regra 30).
Ver **Status por componente** abaixo.

**Em 2026-09-13 o §15 do plano de evolução ganhou L1 e L2 — em OUTRA escala.**
`sparkforge change plan` (L1, *produce change*) gera o diff e o diff de rollback
de um valor de configuração pela procedência dos facts, sem aplicar;
`sparkforge change sandbox` (L2, *sandbox execute*) aplica qualquer diff numa
cópia em `.sparkforge/sandbox/<id>/` e compara os achados do `scan` antes e
depois. As duas saídas levam um campo `stage` próprio (`produce_change`,
`sandbox_execute`) e **não** usam o enum `AutonomyLevel` desta biblioteca, onde
L1 é *specialist* e L2 é *cooperative* — níveis de coordenação de agentes, com
`modify_code` proibido. Os dois executores acima continuam L0 nesta escala, e
`applied_changes` continua `false`: nada do §15 escreve na árvore do operador.

**A medida que fecha a lacuna, e como reproduzi-la.** Sobre
`fixtures/graph/import_sem_jar_no_iac` unida a
`fixtures/infra_code/fgac_com_jar_extra` — 3 findings, 60 facts, o case que a
única contradição direta do catálogo descreve:

| `blackboard summary` | claims | evidence | contradictions | unresolved |
|---|---|---|---|---|
| antes de `arbitrate` | 0 | 0 | 0 | 0 |
| depois | **3** | **11** | **1** | **1** |

E a arbitragem **não fecha**: `recommendation: experiment`, plano de debate com
`debate.unresolved`. É o desfecho correto — `SF-GRAPH-005` e `SF-LF-001` citam
documentação oficial da AWS, e o que está medido no case não separa uma da
outra.

A camada determinística existente (Fact, Finding, Rule, Case, Gates) **não foi
substituída** — foi acrescentada ao lado.

## Status por componente — medido, não declarado

Taxonomia da FASE 0 do prompt de origem: `IMPLEMENTED` (existe e é exercitado
por teste), `PARTIAL`, `DOCUMENTED ONLY`, `MISSING`.

| Módulo | Linhas | Testes | Status | Quem consome hoje |
|---|---|---|---|---|
| `models.py` | 620 | 35 | IMPLEMENTED | blackboard, debate, arbitration, decision |
| `runtime.py` | 223 | 19 | IMPLEMENTED | nada fora dos testes — protocolo sem adapter escrito |
| `evidence.py` | 273 | 23 | IMPLEMENTED | arbitration |
| `blackboard.py` | 334 | 16 | IMPLEMENTED | CLI (`blackboard`, `decisions`) |
| `debate.py` | 265 | 20 | IMPLEMENTED — protocolo e budget. Era PARTIAL até 2026-09-11 por falta de executor das rodadas, que hoje é `executor/debate_run.py` (ele lê o teto DECLARADO no `case.yaml`, nunca o default de `DebateBudget`) | `referee.py` (`Debate`, `DebateStatus`), `budget.py` |
| `arbitration.py` | 380 | 19 | IMPLEMENTED | nada fora dos testes |
| `experiment.py` | 189 | 19 (com `decision.py`) | IMPLEMENTED | nada fora dos testes |
| `decision.py` | 228 | ↑ | IMPLEMENTED | nada fora dos testes |
| `memory.py` | 183 | parte de `infra` | IMPLEMENTED | CLI (`decisions list`) |
| `budget.py` | 503 | parte de `infra` | IMPLEMENTED | CLI (`budget show`) |
| `security.py` | 340 | parte de `infra` | IMPLEMENTED | nada fora dos testes |
| `autonomy.py` | 253 | parte de `infra` | IMPLEMENTED | CLI (`autonomy show`) |
| `graph.py` | 351 | parte de `infra` | IMPLEMENTED | nada fora dos testes |

O subpacote `executor/`, medido em 2026-09-08 (`wc -l` sobre os arquivos,
`pytest --collect-only` por arquivo de teste):

| Módulo | Linhas | Testes | Status | Quem consome hoje |
|---|---|---|---|---|
| `executor/authority.py` | 186 | 27 | IMPLEMENTED | `claims.py` |
| `executor/claims.py` | 284 | 23 | IMPLEMENTED | `run.py` |
| `executor/conflict.py` | 163 | 20 | IMPLEMENTED | `run.py` |
| `executor/ordering.py` | 320 | 31 | IMPLEMENTED | `run.py` |
| `executor/unknowns.py` | 306 | 24 | IMPLEMENTED | `run.py` |
| `executor/plan.py` | 290 | 19 | IMPLEMENTED | `run.py` |
| `executor/run.py` | 1005 | 19 | IMPLEMENTED | CLI (`arbitrate`) e MCP (`sparkforge_arbitrate`) |

`executor/__init__.py` tem 19 linhas. Total do subpacote: **2573 linhas em 8
arquivos**, **105 810 bytes**, **163 testes**. Com ele, o `debate.py` continua
PARTIAL pelo mesmo motivo de sempre — o **plano** de debate passou a ter
produtor, a **execução** dele não.

**Remedido em 2026-09-11, com o executor de debate** (`wc -l`/`wc -c` e
`pytest --collect-only` por arquivo). A tabela acima é a leitura de 2026-09-08 e
fica como registro; `digest.py` (101 linhas) entrou depois dela e antes desta.

| Módulo | Linhas | Testes | Status | Quem consome hoje |
|---|---|---|---|---|
| `executor/debate_run.py` | 1100 | 24 unidade + 47 golden | IMPLEMENTED | CLI (`debate start/next/submit`) e MCP (`sparkforge_debate_start/next/submit`) |
| `executor/debate_evidence.py` | 263 | 41 | IMPLEMENTED | `debate_run.py` |

Total do subpacote hoje: **4185 linhas em 11 arquivos**, **168 889 bytes**.
Fora dele, na mesma entrega: `sparkforge/evals/debate_grade.py` (333 linhas,
29 testes), `scripts/run_debate.py` (634 linhas, 13 testes) e a skill
`skills/run-debate/`. A suíte `tests/test_debate_suite.py` (26) e
`tests/test_cli_debate.py` (16) completam **196 testes novos**.

`__init__.py` tem 68 linhas. Total do pacote: **4 210 linhas em 14 arquivos**,
**148 841 bytes**. As linhas vêm de `wc -l`, não de estimativa — a tabela
publicada na primeira versão desta página estava errada em todos os módulos
(dizia 470 para `models.py`, que tinha 596 quando foi medida), porque foi escrita antes do
`ruff format` e nunca remedida.

## Entidades de primeira classe

9 dataclasses frozen com id determinístico (content-addressed sha1):

- `Claim` — afirmação de um agente (observation/inference/hypothesis/recommendation)
- `Evidence` — evidência classificada por authority tier (T1-T6)
- `Hypothesis` — explicação proposta, falsificável
- `Experiment` — teste de hipótese com variável controlada
- `Decision` — decisão auditável com rollback e falsification condition
- `Unknown` — incerteza explícita (nunca vira fact sem evidência)
- `Contradiction` — conflito entre claims
- `Objection` — contestação de uma claim, com evidência própria
- `Rebuttal` — resposta a uma objeção, com evidência própria

## AgentManifest estendido

12 campos novos, todos opcionais (backward-compatible): `responsibilities`,
`non_responsibilities`, `allowed_actions`, `forbidden_actions`, `inputs`,
`outputs`, `evidence_requirements`, `confidence_policy`, `escalation_policy`,
`time_budget`, `compatible_runtimes`, `evaluation_profile`.

## CLI — 9 verbos, oito de leitura e UM que escreve

- `sparkforge agents list` / `agents inspect <id>`
- `sparkforge blackboard summary` / `blackboard list --type <tipo>`
- `sparkforge decisions list` / `decisions explain <id>`
- `sparkforge budget show` (+ `--template`)
- `sparkforge autonomy show --level <L0-L5>`
- **`sparkforge arbitrate --findings <path> --facts <path> --repo <dir>`** — o
  único que escrevia até 2026-09-11

Desde 2026-09-11, `sparkforge debate start|next|submit` também escrevem, em
`.sparkforge/debate/<debate_id>/` e no blackboard. As tools correspondentes
são `LOCAL_MUTATION`. O `next` também é mutação, porque grava a `Decision` no
fechamento. `sparkforge debate referee` só lê.

`arbitrate` segue a forma dos verbos agênticos existentes (`--repo`, nunca
`--case <id>`), porque o blackboard mora em `<repo>/.sparkforge/blackboard/`.
`--facts` é **repetível, e a repetição é o contrato**: o executor recebe a UNIÃO
dos facts do case, o mesmo conjunto que `judge` recebeu para produzir aqueles
findings (§12.9 do spec do executor). Alimentá-lo com um subconjunto fabrica
claim desancorada que a execução real não produz. Fact sem `id` tem o id
computado por `Fact.id`. O `budget` do plano de debate sai do bloco `budget:` do
`case.yaml`, nunca do default do código: sem case, `budget.status` sai
`unresolved` nomeando a lacuna.

`budget show` lê o bloco `budget:` de `.sparkforge/case.yaml`. Sem esse bloco a
resposta é `limits.status = "unresolved"` **nomeando a lacuna**; os defaults do
código só saem sob `--template`, rotulados como template. Consumo sai
`unresolved` e aponta `sparkforge economy report --run-id <id>`, que é onde ele
é medido — `tokens` exige transcript do host (regra 24) e `cost_usd` exige
`cost_basis` (regra 25).

## O que NÃO foi implementado — declarado por nome

- **RESOLVIDO em 2026-09-08 — produtor de entidades.** Era *a lacuna que governa
  todas as outras*, e `sparkforge/agentic/executor/` a fechou:
  `sparkforge arbitrate` escreve `Claim`, `Evidence`, `Contradiction`, `Unknown`
  e `Decision`. Fica registrado por ter governado o desenho desta página por
  cinco dias, não apagado.
- **ENTREGUE em 2026-09-11 — executor de debate.** Até ali o executor
  determinístico **emitia** o `DebatePlan` e parava em `debate.unresolved`, e
  nenhum laço executava as rodadas. O que existe hoje, com precisão:
  - **máquina de estados L0** em `executor/debate_run.py`. `start` congela o
    plano do par em `.sparkforge/debate/<debate_id>/`, `next` devolve o brief
    do lado da vez, e `submit` valida tudo antes de gravar qualquer coisa. O
    estado vive só em arquivo, e por isso a retomada é recálculo. Sem `budget:`
    declarado no `case.yaml`, o `start` recusa com `budget_undeclared`;
  - **geração só no host.** Quem escreve claim, objeção e réplica é a sessão,
    pela skill `run-debate`, ou `claude -p`, por `scripts/run_debate.py`. Nada
    disso mora em `sparkforge/`;
  - **fechamento sempre pelo `referee`.** Vence a regra do lado que não
    concedeu, quando exatamente um lado concedeu. `upheld: false` vira
    `Decision` `unresolved` com as violações citadas. Contagem de claim nunca
    escolhe vencedor;
  - **evidência nova só reextraída.** O lado aponta `{extractor, path}`. O
    executor confere o extrator contra uma allowlist de 22, confina o caminho
    ao case e roda o extrator. Fact escrito pelo agente não é aceito.

  **O que continua não existindo:** benchmark do debate contra a arbitragem
  determinística. A regra 30 continua bloqueando qualquer afirmação de ganho.
  E o pacote continua sem provider nenhum (regra 23): o `subprocess` do
  `claude -p` mora em `scripts/`, e `tests/test_evals_invariants.py` cobre os
  módulos novos.
- **Alcance medido do executor de debate: um par.** Sobre as 155 regras com
  `action`, `direct_conflicts` devolve **exatamente um** par no catálogo
  (`SF-GRAPH-005` × `SF-LF-001`), e nenhuma fixture sozinha o produz. O par só
  aparece na UNIÃO dos facts de dois jobs diferentes (`grafo_sem_jar`, sem
  FGAC; `etl_fgac_com_jar`, com FGAC). Um smoke real `claude -p` (Haiku,
  US$ 0,0723) argumentou que o conflito pode não existir para nenhum dos dois
  jobs sozinho. Detalhe e consequência em `evals/README.md`, seção do debate.
- **MISSING — `AgentRuntime` concreto.** Nada neste pacote faz spawn de agente,
  e nada aqui chama provider. Quem gasta token é o host.
- **MISSING — Fase 35 (checkpoint/resume).** Só existe a *flag*
  `RuntimeCapabilities.checkpointing`; não há persistência de estado de execução
  nem retomada.
- **MISSING — Fase 10 (adaptive model routing).** Não há seleção de modelo por
  complexidade/risco nesta camada.
- **MISSING — Fase 28 (agent reputation)** e **Fase 32 (solution tournament)**.
- **MISSING — Fase 14 (agentes adversariais `sf-*`).** Os campos de contrato
  existem no manifest; nenhum agente novo foi criado.
- **NOT IMPLEMENTED — semantic cache (embedding-based).** O cache existente é
  content-addressed (SHA-256), não semântico.
- **NOT IMPLEMENTED — auto-modificação L5.** O nível existe com guardrails; a
  execução de auto-modificação não.
- **NOT IMPLEMENTED — consulta automática à memória cross-case.**
  `find_similar_decisions` existe e ninguém a chama durante um case.
- **PARTIAL — `detect_waste`.** Mede duplicidade de tool call, evidência,
  sumário, contexto, doc não usado e agente sem output. **Não** mede
  `unnecessary_debates`: decidir isso exige o resultado do debate, que a função
  não recebe. O campo vazio significa "não medido", e a docstring diz isso.

## Benchmarks — ausentes, e por quê

As Fases 51-53 do prompt de origem pediam medir arquitetura nova contra antiga
(tokens, latência, custo, número de agentes, qualidade, taxa de falha), e a
Fase 63 pedia uma seção `Benchmarks` neste relatório. **Continua não havendo
benchmark, e nem o executor determinístico nem o de debate mudam isso.** O que
as Fases 51-53 comparam é a arquitetura de **debate** — vários agentes
discutindo o mesmo caso — contra a determinística. Desde 2026-09-11 os dois
lados rodam. A comparação continua não feita, por duas razões medidas:

- o debate alcança um único par de regras;
- esse par é um tópico mal posto, porque só existe na união de dois jobs.

A suíte `evals/agentic/debate/` mede mecânica e decidibilidade com submissões
gravadas. O baseline de modelo (B8) **não foi rodado de propósito**: ele
mediria um tópico mal posto.

O que **é** mensurável hoje, e foi medido:

| Medida | Valor | Como |
|---|---|---|
| Peso do pacote agêntico | 148 841 bytes, 4 210 linhas | `wc -c`/`wc -l` sobre `sparkforge/agentic/*.py` |
| Custo em contexto para comando não-agêntico | 0 byte | import é lazy: só o handler do verbo agêntico importa o módulo |
| Testes da camada | 441 | `pytest tests/test_agentic_*.py --collect-only` em 2026-09-08 — 261 antes do executor, mais 163 dele, 15 do verbo `arbitrate` e 2 em `test_agentic_models.py` |
| Peso do subpacote `executor/` | 105 810 bytes, 2573 linhas | `wc -c`/`wc -l` sobre `sparkforge/agentic/executor/*.py` |
| Crescimento da superfície de skills | 321 678 → 457 985 bytes (+42,4%) | `docs/surface.lock.json`, pelas 11 skills AWS |

Enquanto não houver produtor, "a arquitetura nova é melhor" continua sem
lastro — e por isso não está escrito em lugar nenhum deste repositório.

## Auditoria de 2026-09-03 — 14 defeitos corrigidos

Revisão da entrega encontrou defeitos que os 206 testes originais não pegavam,
porque os testes fixavam o comportamento defeituoso. Cada um tem hoje teste de
regressão:

| # | Onde | Defeito | Correção |
|---|---|---|---|
| 1 | `cli.py::_cmd_budget_show` | Imprimia `CaseBudget()` de fábrica como se fosse o estado do case | Lê o case; sem bloco `budget:` sai `unresolved`; template só sob `--template` |
| 2 | `arbitration.arbitrate` | Com UMA claim, `loser` era a própria vencedora: sempre "experiment" para diferenciar a claim dela mesma | `disputed`; claim única resolve por score, e o relatório diz que não houve disputa |
| 3 | `arbitration.assess_claim` | `evidence_weight` agregava TODAS as evidências: claim sem evidência reportava o mesmo peso da rival com T1 | Agrega só o que suporta a claim |
| 4 | `evidence.aggregate_strength` | `has_sufficient_authority` e `has_fresh_in_scope` eram a MESMA expressão | Separados: tier vs tier+verificação |
| 5 | `budget.AgentBudget` | `max_time_seconds` e `max_retries` rastreados e nunca lidos | `status` olha os quatro limites; `consume_time`/`consume_retry` |
| 6 | `budget.CaseBudget` | `max_total_tool_calls` e `max_total_time_seconds` idem | Enforçados, com `consume_tool_call`/`consume_time` |
| 7 | `budget.detect_waste` | Recebia `agent_ids` e nunca usava; 3 campos do relatório sempre vazios | `agent_outputs` + `context_chunks` medidos; o que não é medido diz que não é |
| 8 | `security.detect_prompt_injection` | "verbo imperativo + nome de serviço" bloqueava recomendação legítima do próprio produto | Heurística removida; marcadores de instrução continuam |
| 9 | `security.validate_output` | Substring: `token=`, `private_key`, `AKIA` bloqueavam prosa e nome de coluna | Regex com forma de segredo; placeholder e `${VAR}` não contam |
| 10 | `autonomy.validate_autonomy_boundary` | Checava `human_approval` no perfil ESTÁTICO do L5 — que sempre o contém: o ramo nunca disparava | `guardrails_satisfied` vem do chamador; alto risco exige o `required_validation` coberto |
| 11 | `experiment.design_experiment` | `cost_estimate`/`time_estimate` fixos ("1 Glue job run", "15-30 minutes") | Vêm do chamador; vazio quando ninguém mediu (regra 14) |
| 12 | `graph.build_graph_from_case` | Edge agente→claim usava `get_nodes_by_type(CLAIM)[-1]` e podia colar na claim errada | Referência nomeada ao nó da claim |
| 13 | `arbitration.compute_independence_score` | Média de duas diversidades: dois agentes citando a MESMA fonte davam 0,75 sobre limiar 0,3, e o falso consenso nunca disparava | `min` das duas (elo fraco), fonte contada por ligação `supports`, e sinal próprio de linhagem idêntica |
| 14 | `models.Claim.id` | Hash só de `claimant + tipo + statement`: claim revisada com evidência nova colidia com a anterior e o blackboard a recusava | `evidence_refs`, `assumptions` e `confidence` entram no hash; `supersedes` liga a revisão, conferido contra o blackboard |

Fora da lista, no mesmo passe: `agents inspect --id` rejeita caminho
(`../`), `RuntimeCapabilities` ganhou teste que o amarra a `parity.yaml`
(`spawn_agent` ↔ mecanismo `subagent`, `tool_calling` ↔ `mcp`), a isenção do
gate `TestNoPlatformKnowledge` foi estreitada de "qualquer `references/`" para
as 11 skills AWS nomeadas, e 6 vazamentos de caractere chinês saíram do código
e dos documentos.

**As duas decisões de projeto, tomadas e registradas** (elas estavam listadas
como vistas-e-não-corrigidas na primeira versão desta página):

- **Falso consenso passou a medir linhagem, não contagem de agentes.**
  `compute_independence_score` devolve agora a MAIS FRACA das duas
  diversidades — `min(claimant, fonte)` em vez da média —, conta fonte por
  ligação `supports` (evidência solta na lista não sustenta claim nenhuma), e
  `detect_false_consensus` ganhou um segundo sinal: duas ou mais claims com
  conjunto de fontes IDÊNTICO são falso consenso independentemente do score.
  Ausência de fonte não entra nesse sinal — ausência não é fonte
  compartilhada, e quem pega esse caso é o score baixo.
- **`Claim.id` cobre o que define a claim.** `evidence_refs`, `assumptions` e
  `confidence` entraram no hash: revisar uma claim produz id novo e o append
  passa. Claims idênticas em tudo continuam deduplicadas — o que mudou é o que
  conta como "idêntica". `supersedes` (opcional) liga a revisão à versão
  anterior e é conferido contra o blackboard: linhagem quebrada não é gravada
  como se fosse boa.
## Números desta entrega — medidos em 2026-09-03

| O quê | Medido | O que estava publicado antes |
|---|---|---|
| Testes da suíte (coleta completa) | **9 952** | spec dizia 9486, relatório 9881, commit 9897 — três números para a mesma base |
| Testes da camada agêntica | **261** (206 originais + 55 de regressão da auditoria) | 206 |
| Módulos em `sparkforge/agentic/` | **13** (+ `__init__.py`) | `AGENTS.md` dizia 12 sobre uma tabela de 13 |

Gates verdes: `sync_skills.py --check`, `check_surface_lock.py` (0),
`check_status_numbers.py --strict` (0), `ruff check`, `ruff format --check`.
Gate de lastro (`check_vnext_claims.py`): ver `docs/vnext/` — as alegações que
medem o corpus Python foram remedidas nesta auditoria.

## Arquitetura — o alvo, e onde ele está

O prompt de origem descreve este caminho. A coluna de status é o que existe
hoje, e a primeira versão desta página publicava o desenho sem ela, o que fazia
o alvo parecer entregue.

| Etapa | Módulo | Estado |
|---|---|---|
| CASE MANAGER | `sparkforge.case.store` | existente, em uso |
| CONTEXT ENGINE | `sparkforge.context.funnel/progressive` | existente, em uso |
| DOMAIN ROUTER | `sparkforge.case.router` + `routing.yaml` | existente, em uso |
| SPECIALIST TEAM | `agentic.runtime` | protocolo, sem adapter — nenhum `AgentRuntime` concreto no pacote |
| SHARED BLACKBOARD | `agentic.blackboard` | biblioteca, leitura por CLI e **produtor** (`agentic.executor.run`) |
| HYPOTHESIS ENGINE | `agentic.models.Hypothesis` | entidade, sem gerador — o executor produz `Unknown` e `Experiment`, não `Hypothesis` |
| ADVERSARIAL REVIEW / ARBITRATOR | `agentic.arbitration` | biblioteca, consumida por `agentic.executor.conflict` |
| DEBATE ENGINE | `agentic.debate` + `agentic.executor.debate_run` | protocolo, budget, **plano** (`agentic.executor.plan`) e, desde 2026-09-11, executor L0 das rodadas; a geração do argumento é do host (skill `run-debate`, `scripts/run_debate.py`) |
| EXPERIMENT ENGINE | `agentic.experiment` | biblioteca, consumida por `agentic.executor.unknowns` |
| VALIDATION | `adapters._core.validate_output` | existente, em uso |
| DECISION ENGINE | `agentic.decision` | biblioteca, consumida por `agentic.executor.run` (L0: propõe, nunca aplica) |
| DECISION MEMORY | `agentic.memory` | biblioteca + leitura por CLI |
| EXECUTION | CLI/MCP adapters | existente, em uso |
| OBSERVABILITY | `sparkforge.observability` | existente, em uso; o `trace` da arbitragem passou a ter produtor |
| LEARNING/EVALUATION | `agentic.memory` + waste detection | biblioteca |

## Princípios preservados

- Nenhum agente é confiável apenas por ser especialista.
- Uma conclusão só é confiável quando sobrevive à evidência, revisão cruzada,
  contestação adversarial e validação.
- Unknown nunca vira fact por conveniência — retorna `UNRESOLVED`.
- Toda decisão é auditável e reversível (ou declara-se irreversível).
- Budget é finito e enforçado — nos quatro limites, não só em tokens.
- Custo e tempo não são inventados: sem medida, o campo fica vazio.
- Runtime-independente: o protocolo é o contrato; `parity.yaml` é a fonte de
  quem despacha subagente, e um teste amarra as duas fontes.
- Correctness, safety, evidence, auditability > token savings.

## Compatibilidade

- `case.yaml` continua válido; o bloco `budget:` é **opcional** e a ausência
  dele é `unresolved`, não erro.
- APIs existentes não quebram; os 12 campos novos do `AgentManifest` são
  opcionais.
- Gates existentes continuam passando.

## Próximo passo, na ordem que a lacuna impõe

1. ~~Decidir se existe produtor de entidades e qual é o tier de uma `Evidence`
   derivada de `Fact`/`Finding` determinístico.~~ **Feito em 2026-09-08.** O
   produtor é `sparkforge arbitrate`, e o tier sai de
   `knowledge/source_authority.yaml` por host da fonte citada pela regra —
   nunca inventado. Medido sobre as 253 fixtures do corpus: T1 170, T4 20,
   T2 16; T3, T5 e T6 não aparecem, porque host não prova reprodutibilidade nem
   afirma nada sobre o conteúdo (§12.8 do spec do executor).
2. ~~Executor de debate.~~ **Feito em 2026-09-11** (máquina de estados L0,
   geração no host, fechamento pelo `referee`). Os benchmarks das Fases 51-53
   **continuam por fazer**. Os dois lados existem, mas o único par que o
   catálogo produz é um tópico mal posto, e medir modelo sobre ele não
   diria nada. O que destrava é um segundo par de conflito direto que caiba num
   job só. Até lá, **nenhuma afirmação de ganho**, pela regra 30 do `CLAUDE.md`.
3. Destravar a contradição **condicional**: ela não tem caso no catálogo de
   hoje, e a medida que a destrava é um fact kind emitido só acima do limiar
   (`glue.utilization.skew_high` ou equivalente por stage), ou um
   `requires_absent` que saiba cruzar por `attrs` além do kind. Entrega própria,
   no extrator.
