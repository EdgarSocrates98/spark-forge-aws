# SparkForge Agentic Evolution Report

**Entrega:** 2026-09-03
**Auditoria e correções:** 2026-09-03 (mesma data, sessão seguinte)
**Branch:** `audit/fakes-de-coleta`
**Spec:** `docs/superpowers/specs/2026-09-03-sparkforge-agentic-evolution-design.md`

## Resumo executivo

O SparkForge ganhou uma **biblioteca agêntica** em `sparkforge/agentic/`: 13
módulos, 9 entidades de primeira classe, protocolo de debate formal, arbitragem
com detecção de falso consenso, desenho de experimentos, decisões auditáveis com
ADR, memória institucional cross-case, budget unificado, threat model com 12
tipos, níveis de autonomia L0-L5 e Agent Execution Graph.

**O que ela ainda não é, e a distinção é o ponto desta página:** a camada é uma
**biblioteca com verbos de leitura**, não um pipeline em execução. Nenhum
extrator, regra, tool MCP ou coordenador escreve `Claim`, `Evidence` ou
`Decision` hoje. Quem quiser produzir essas entidades chama a API Python. A
consequência medida: `sparkforge blackboard summary` num repositório de trabalho
devolve zero em todas as contagens, e vai continuar devolvendo até existir um
produtor. Ver **Status por componente** abaixo.

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
| `debate.py` | 265 | 20 | PARTIAL — protocolo e budget existem, executor não | nada |
| `arbitration.py` | 380 | 19 | IMPLEMENTED | nada fora dos testes |
| `experiment.py` | 189 | 19 (com `decision.py`) | IMPLEMENTED | nada fora dos testes |
| `decision.py` | 228 | ↑ | IMPLEMENTED | nada fora dos testes |
| `memory.py` | 183 | parte de `infra` | IMPLEMENTED | CLI (`decisions list`) |
| `budget.py` | 503 | parte de `infra` | IMPLEMENTED | CLI (`budget show`) |
| `security.py` | 340 | parte de `infra` | IMPLEMENTED | nada fora dos testes |
| `autonomy.py` | 253 | parte de `infra` | IMPLEMENTED | CLI (`autonomy show`) |
| `graph.py` | 351 | parte de `infra` | IMPLEMENTED | nada fora dos testes |

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

## CLI — 8 verbos, todos de leitura

- `sparkforge agents list` / `agents inspect <id>`
- `sparkforge blackboard summary` / `blackboard list --type <tipo>`
- `sparkforge decisions list` / `decisions explain <id>`
- `sparkforge budget show` (+ `--template`)
- `sparkforge autonomy show --level <L0-L5>`

`budget show` lê o bloco `budget:` de `.sparkforge/case.yaml`. Sem esse bloco a
resposta é `limits.status = "unresolved"` **nomeando a lacuna**; os defaults do
código só saem sob `--template`, rotulados como template. Consumo sai
`unresolved` e aponta `sparkforge economy report --run-id <id>`, que é onde ele
é medido — `tokens` exige transcript do host (regra 24) e `cost_usd` exige
`cost_basis` (regra 25).

## O que NÃO foi implementado — declarado por nome

- **MISSING — produtor de entidades.** Nada no produto escreve no blackboard.
  Sem isso, debate, arbitragem, experimento e decisão são API disponível, não
  comportamento do sistema. É a lacuna que governa todas as outras.
- **MISSING — executor de debate.** `should_trigger_debate()` decide *se* um
  debate cabe e `DebateBudget` limita rodadas, mas nenhum laço executa as
  rodadas. Nada consulta `budget_exhausted`.
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
Fase 63 pedia uma seção `Benchmarks` neste relatório. **Não há benchmark, e a
razão é a lacuna acima**: não existe execução agêntica para medir. Comparar
"antes" com "depois" exigiria os dois lados rodando o mesmo caso, e o lado novo
ainda não roda.

O que **é** mensurável hoje, e foi medido:

| Medida | Valor | Como |
|---|---|---|
| Peso do pacote agêntico | 148 841 bytes, 4 210 linhas | `wc -c`/`wc -l` sobre `sparkforge/agentic/*.py` |
| Custo em contexto para comando não-agêntico | 0 byte | import é lazy: só o handler do verbo agêntico importa o módulo |
| Testes da camada | 261 | `pytest tests/test_agentic_*.py` |
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
| SPECIALIST TEAM | `agentic.runtime` | protocolo, sem adapter |
| SHARED BLACKBOARD | `agentic.blackboard` | biblioteca + leitura por CLI, sem produtor |
| HYPOTHESIS ENGINE | `agentic.models.Hypothesis` | entidade, sem gerador |
| ADVERSARIAL REVIEW / ARBITRATOR | `agentic.arbitration` | biblioteca |
| DEBATE ENGINE | `agentic.debate` | protocolo e budget, sem executor |
| EXPERIMENT ENGINE | `agentic.experiment` | biblioteca |
| VALIDATION | `adapters._core.validate_output` | existente, em uso |
| DECISION ENGINE | `agentic.decision` | biblioteca |
| DECISION MEMORY | `agentic.memory` | biblioteca + leitura por CLI |
| EXECUTION | CLI/MCP adapters | existente, em uso |
| OBSERVABILITY | `sparkforge.observability` | existente, em uso (traces do blackboard: só o arquivo, sem produtor) |
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

1. Decidir se existe produtor de entidades e qual é o tier de uma `Evidence`
   derivada de `Fact`/`Finding` determinístico — é escolha de semântica, e
   escolha se registra antes de codificar.
2. Só depois: executor de debate, e então os benchmarks das Fases 51-53, que
   passam a ter os dois lados para comparar.
