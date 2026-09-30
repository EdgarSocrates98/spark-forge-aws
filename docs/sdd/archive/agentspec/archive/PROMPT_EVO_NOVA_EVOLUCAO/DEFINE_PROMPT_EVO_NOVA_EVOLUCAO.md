# DEFINE: PROMPT_EVO_NOVA_EVOLUCAO

> Transformar avaliações de candidates em evidência verificável e promover somente sob policy, transcript e rollback comprovados.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PROMPT_EVO_NOVA_EVOLUCAO |
| **Date** | 2026-09-30 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

---

## Problem Statement

Maintainers, operators e reviewers não têm um único contrato verificável que ligue candidate, parent, transcript, métricas, `evaluation_policy`, CI, benchmark, revisão e rollback à decisão de promoção. Isso deixa duplicação de execução, policy não vinculada ao receipt e avaliação live externa sem um caminho comum de validação, mesmo que o Forge já possua replay offline, facts de host e receipts content-addressed.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Maintainer | Mantém o registry, fixtures e CI | Precisa reproduzir uma avaliação e provar que a policy usada é a mesma que autorizou a promoção |
| Operator | Executa replay ou host externo e solicita promoção | Precisa entregar evidência válida, receber recusas nomeadas e conservar rollback claro |
| Reviewer | Audita candidate, evidence bundle e receipt | Precisa conferir hashes, métricas, proveniência, policy, CI e autorização sem confiar em booleanos autoafirmados |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | Definir um `EvaluationEvidenceBundle` canônico que vincule candidate, parent, suite/input manifest, modo de execução, transcripts, métricas, policy digest e referências de evidência. |
| **MUST** | Validar bundle produzido por fixture/arquivo e bundle retornado por comando externo autorizado usando o mesmo contrato. |
| **MUST** | Executar baseline e candidate uma vez por avaliação, compará-los como reports distintos e derivar quality/economy gates a partir de policy. |
| **MUST** | Resolver policy por candidate family/kind e contract, incluindo `minimum_labeled_tasks`, sem duplicar threshold em `CandidateEvaluation`. |
| **MUST** | Vincular receipts novos à versão/hash da policy, sequência verificável, identidade do candidate, evidências de CI/benchmark/revisão e rollback target. |
| **MUST** | Manter o núcleo do Forge offline e provider-independent; tokens e custos sem transcript/`cost_basis` válido devem permanecer unresolved. |
| **SHOULD** | Manter leitura de receipts legados por uma fachada de compatibilidade sem permitir que campos ausentes sejam tratados como evidência nova válida. |
| **SHOULD** | Permitir que o adapter de comando seja explicitamente autorizado e produza a mesma forma normalizada do adapter de bundle. |
| **COULD** | Adicionar futuramente múltiplos judges, thresholds adaptativos, auto-merge/deploy ou uma DSL genérica para novas families. |

**Priority Guide:**
- **MUST** = MVP fails without this (non-negotiable)
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] Os dois adapters do MVP produzem o mesmo schema canônico para 100% dos fixtures equivalentes cobertos pelo conjunto de replay.
- [ ] Cada avaliação registra exatamente uma execução do baseline e uma do candidate; testes verificam as duas contagens e identidades.
- [ ] 100% dos receipts novos contêm `policy_version`/`policy_sha256`, candidate digest, suite/input identity, execution mode e rollback target.
- [ ] 100% dos casos de bundle adulterado, policy incompatível, transcript inválido ou evidência ausente terminam em recusa nomeada e não promovem candidate.
- [ ] 100% dos candidate kinds/families registrados resolvem uma policy explícita ou retornam recusa nomeada por ausência de policy.
- [ ] 100% dos receipts legados cobertos pelos fixtures atuais continuam legíveis; nenhum campo ausente é promovido silenciosamente a evidência válida.
- [ ] O comando de promoção exige referências verificáveis de CI, benchmark e revisão, além de contract identity, corpus mínimo e rollback.
- [ ] Static/import tests confirmam que o Forge não importa nem chama SDK/provider; sem transcript/`cost_basis`, tokens/custo permanecem unresolved.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Avaliação por bundle | Um registry válido, suite rotulada e bundle host válido com baseline/candidate | O maintainer executa avaliação | O Forge normaliza o bundle, deriva métricas/gates e grava receipt com candidate e policy identities |
| AT-002 | Avaliação por comando autorizado | Um comando externo permitido retorna o mesmo bundle válido | O operador executa o adapter de comando | O resultado normalizado é equivalente ao adapter de arquivo e a execução fica vinculada à proveniência do comando |
| AT-003 | Execução única | Um runner instrumentado registra chamadas para baseline e candidate | A avaliação é executada | Cada lado é chamado exatamente uma vez e os reports permanecem distintos |
| AT-004 | Policy por family | Existem policies distintas para os candidate kinds/contracts registrados | O candidate é avaliado | A policy correta é escolhida por identidade e seu digest aparece no bundle e no receipt |
| AT-005 | Policy ausente | Um candidate kind não possui policy registrada | O operador tenta avaliar ou promover | O Forge retorna recusa nomeada e não usa default implícito |
| AT-006 | Bundle adulterado | Um bundle válido teve candidate, transcript, suite ou policy alterado após a geração | O reviewer verifica o bundle | A verificação falha com motivo específico e a promoção é bloqueada |
| AT-007 | Transcript inválido ou ausente | O bundle declara transcript com hash incorreto ou uso sem fonte válida | O Forge deriva economia | A métrica correspondente fica unresolved e o gate que exige sua presença falha de forma explícita |
| AT-008 | Receipts legados | Há receipts existentes sem o novo policy digest | O maintainer chama leitura/importação histórica | Os receipts continuam legíveis, mas não satisfazem silenciosamente os requisitos de um novo promotion gate |
| AT-009 | Seleção determinística | Existem vários receipts de avaliação do mesmo candidate | O operador solicita a avaliação mais recente | O Forge usa sequência/ordenação verificável do evento, rejeitando colisão ou ambiguidade |
| AT-010 | Promoção comprovada | Bundle, policy, CI, benchmark, revisão, contract, corpus e rollback são válidos | O operador solicita promoção explicitamente | A promoção é autorizada e o receipt registra todas as referências |
| AT-011 | Promoção incompleta | Falta CI, benchmark, revisão, rollback, contract digest ou autorização | O operador solicita promoção | O Forge recusa com a lista de evidências ausentes e não altera o candidate aceito |
| AT-012 | Núcleo sem provider | O pacote é importado em ambiente offline | A suíte de testes é executada | Nenhum SDK/provider é chamado; tokens e custo sem fonte permanecem unresolved |

---

## Out of Scope

Explicitly NOT included in this feature:

- Chamada direta de SDK/provider pelo Forge.
- Múltiplos judges, consenso estatístico ou thresholds adaptativos.
- Auto-merge, deploy, ativação automática ou alteração silenciosa do route em produção.
- DSL YAML genérica para descoberta automática de adapters e candidate families.
- Inclusão de transcripts reais sem sanitização no repositório.
- Interpretação de payload bytes como provider tokens ou cálculo de custo sem `cost_basis`.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | O núcleo permanece offline e provider-independent | Host/live execution é externo; Forge valida evidência recebida |
| Technical | Candidates, contracts, policies e receipts são identificados por hash/digest | Alterações precisam produzir recusa nomeada ou novo identity |
| Technical | O comparador deve separar qualidade, payload, tokens e custo | Não haverá score agregado nem economia inferida de bytes |
| Compatibility | Receipts legados continuam legíveis | A leitura histórica precisa de uma fachada, mas promoção nova exige campos atuais |
| Governance | Promoção exige autorização explícita, CI, benchmark, revisão e rollback | Nenhum booleano do caller pode substituir evidência |
| Data handling | Transcripts podem conter contexto do operador | Fixtures devem ser sanitizadas; referências externas carregam hash e proveniência |
| Resource | Não criar infraestrutura nova | A mudança usa filesystem, fixtures, registry e adapters locais/externalizados |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/evals/`, `sparkforge/decision/`, `config/evolution/`, `tests/`, `evals/fixtures/` | A feature estende contracts existentes de evolution, host, replay e receipts; não cria serviço novo |
| **KB Domains** | `genai`, `prompt-engineering`, `testing`, `python` | Consultar avaliação estruturada/pareada, validação com evidência, integração e value objects tipados |
| **IaC Impact** | None | Não há recursos AWS, Terraform ou mudança de deployment |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from the selected knowledge bases
- **IaC Impact** → Confirms that infrastructure planning is not required

---

## Data Contract (if applicable)

Este recurso não é um pipeline ETL ou analítico. O `EvaluationEvidenceBundle` é um contrato de evidência de avaliação, não um contrato de dados operacionais. Seu conteúdo mínimo deve ser definido na fase Design e precisa incluir candidate/parent identity, suite/input identity, execution mode, transcript provenance, metric groups, policy identity, evidence refs, authorization context e rollback target.

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| Host transcript/bundle | Artifact externo ou local | Não declarado; sob demanda | Por execução | Host/Operator |
| Evaluation fixtures | YAML/JSONL versionado | Corpus pequeno existente | Por commit | Maintainer |

### Schema Contract

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| `candidate_digest` | string | Obrigatório; content-addressed | No |
| `parent_digest` | string/null | Obrigatório para mutation | No |
| `suite_sha256` | string | Obrigatório; deve corresponder à suite | No |
| `policy_sha256` | string | Obrigatório em bundle/receipt novo | No |
| `execution_mode` | enum | `surrogate`, `recorded_host`, `live_external` | No |
| `transcript_hash` | string/null | Hash obrigatório quando transcript é declarado | No |
| `provider_tokens` | object/null | Só com transcript/usage válido | No |
| `evidence_refs` | list[string] | Deve ser não vazia para promoção | No |
| `rollback_target` | string | Obrigatório para promoção | No |

### Freshness SLAs

Não aplicável como SLA de dados. A validade do bundle é determinada por hash, identity e sequência verificável, não por idade do artefato.

### Completeness Metrics

- 100% dos campos obrigatórios do schema presentes antes de promoção.
- 100% das referências declaradas resolvíveis ou recusadas com motivo nomeado.
- Zero conversões de bytes para tokens e zero custos sem `cost_basis`.

### Lineage Requirements

- Candidate → parent → suite/input manifest → transcript/bundle → comparison → policy → promotion receipt.
- Cada etapa deve preservar digest e referências suficientes para replay ou recusa.

---

## Assumptions

Assumptions that if wrong could invalidate the design:

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Fixtures atuais representam os formatos de bundle/transcript que o adapter precisa aceitar | Será necessário criar novo corpus antes de definir o schema | [x] Parcialmente: fixtures de host, replay e provider existem |
| A-002 | Um host externo consegue retornar baseline/candidate, usage e transcript hash em envelope verificável | O adapter de comando precisará de uma fase adicional de captura/normalização | [ ] |
| A-003 | Receipts atuais podem ser lidos como histórico sem policy digest | Migração precisará de conversor ou recusa explícita para receipts antigos | [x] Parcialmente: leitura/tamper já tem cobertura |
| A-004 | A lista de candidate kinds/families do registry é a fonte de verdade para resolver policy | Families fora do registry continuarão sem promoção | [x] Registry atual é explícito e content-addressed |
| A-005 | Transcripts reais usados no fluxo externo podem permanecer fora do repositório e ser referenciados por hash | Será necessário processo de sanitização/armazenamento antes do L1 | [x] Compatível com a regra offline e de artefatos não rastreados |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Dor, impacto e camada afetada estão explícitos |
| Users | 3 | Maintainer, operator e reviewer têm papéis e dores definidos |
| Goals | 3 | Goals têm prioridade MoSCoW e fronteira de MVP |
| Success | 3 | Há critérios numéricos para adapters, execução, receipts, refusals e policies |
| Scope | 3 | Includes, out of scope, constraints e assumptions estão registrados |
| **Total** | **15/15** | Clarity gate atingido |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

Nenhuma questão de requisito bloqueia o Design. A fase Design deve escolher o formato final do bundle, transporte/allowlist do comando externo, estratégia de sequência dos receipts e o mapeamento detalhado das policies por family.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-30 | define-agent | Requisitos extraídos do brainstorm validado; clarity score 15/15 |
| 1.1 | 2026-09-30 | ship-agent | Shipped and archived |

---

## Next Step

**Status:** ✅ Shipped and archived
