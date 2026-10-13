# BRAINSTORM: PROMPT_EVO_NOVA_EVOLUCAO

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PROMPT_EVO_NOVA_EVOLUCAO |
| **Date** | 2026-09-30 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** `prompt_evo_nova_evolucao.md` (1,032 linhas). O arquivo avalia a evolução recente da camada de prompts/agentes e propõe elevar a prova de L0, avaliação offline determinística, para L1, replay de transcripts registrados pelo host, com caminho live externo controlado. Também aponta a necessidade de vincular a `evaluation_policy` aos receipts, remover o `minimum_labeled_tasks` duplicado, executar cada candidate uma vez, selecionar o receipt mais recente por sequência verificável e suportar policies por tipo de candidate.

**Context Gathered:**
- `sparkforge_aws/evals/evolution.py` já possui candidates content-addressed, lifecycle, replay baseline-versus-candidate, `EvaluationGatePolicy`, receipts locais e promoção com rollback.
- O gate atual ainda contém `50` diretamente em `CandidateEvaluation.gates_pass`; a policy carregada do registry é global e ainda não identifica o digest da policy no resultado.
- `EvolutionService.evaluate()` cria reports separados, mas executa o runner de cada lado duas vezes para preservar o formato antigo; `latest_evaluation()` ordena receipts pelo nome do arquivo.
- O protocolo host e os facts de transcript já existem, e o projeto mantém fixtures de replay, transcripts, comparação baseline/candidate e ground truth rotulado.
- A autoridade do repositório exige núcleo offline, provider independente, evidência nomeada, receipts verificáveis, rollback e nenhuma promoção baseada em booleanos autoafirmados.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge_aws/evals/evolution.py`, `sparkforge_aws/evals/decision_replay.py`, `sparkforge_aws/decision/host.py`, `sparkforge_aws/decision/receipts.py`, `config/evolution/prompt_agents.yaml` | Introduzir bundle/policy/adapter perto dos contratos existentes e preservar as fachadas atuais durante a migração |
| Relevant KB Domains | `genai`, `prompt-engineering`, `testing`, `python` | Usar avaliação estruturada, comparação pareada, evidência auditável, testes de integração e value objects tipados |
| IaC Patterns | N/A | A mudança é local, de avaliação e governança; não requer infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual deve ser o objetivo principal desta nova evolução? | **D:** pacote integrado com L1, receipts/policy e policies por tipo, mantendo MVP pequeno | O desenho precisa cobrir as três frentes, com fronteiras explícitas para evitar um novo runtime aberto |
| 2 | Quem será o usuário principal do fluxo? | **D:** maintainers, operadores e revisores, começando pelo maintainer | O resultado precisa ser executável em CI/local, operável para promoção e legível para auditoria |
| 3 | Qual limite de execução deve valer para o MVP? | **D:** L1 e live opcional, com execução live explicitamente autorizada | O Forge valida evidência externa, mas não chama provider por conta própria |
| 4 | Quais amostras estão disponíveis? | **A:** transcripts reais do host, fixtures atuais e ground truth rotulado | O contrato pode ser testado contra replay real, fixtures determinísticas e resultados esperados |
| 5 | Qual abordagem foi confirmada? | **A + B:** Evidence Bundle + Promotion Gate com rollout incremental compatível | A arquitetura integrada será entregue em passos pequenos, sem quebrar receipts e APIs existentes |
| 6 | A composição A+B está correta? | **A:** sim | Confirma bundle canônico, policy vinculada, execução única e compatibilidade como núcleo |
| 7 | Qual critério define que o MVP está pronto? | **C:** compatibilidade, execução única, replay L1, promoção live externa e policy por cada família registrada | O gate de aceite precisa cobrir caminho offline, transcript e host live externo, incluindo todas as families registradas |
| 8 | Como a avaliação live externa deve entrar? | **C:** bundle entregue pelo host e comando externo autorizado, sob o mesmo contrato | Dois adapters serão aceitos, com normalização única e autorização explícita para o adapter de comando |
| 9 | O fluxo proposto está alinhado? | **A:** sim | Confirma validação de schema/hashes/policy/transcript, recusa nomeada e promoção sem automatismo oculto |

**Minimum Questions:** 3 (to ensure clarity before proceeding)

---

## Sample Data Inventory

> Samples improve LLM accuracy through in-context learning and few-shot prompting.

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/host_transcript/` | 21 cenários; 18 JSONL | Inclui casos válidos, inválidos, ausência de uso, envelopes quebrados, ordem inválida e comparações baseline/candidate |
| Output examples | `fixtures/host_transcript/**/expected/` | Presente nos cenários | Contém `facts.json`, `grade.json`, `compare.json` e `scorecard.json`, conforme o cenário |
| Ground truth | `evals/token_efficient/fixtures/decision_control_plane_cases.yaml` e suites `evals/token_efficient/` | Corpus rotulado existente | Casos com status esperado, evidências, findings, rota, partição train/holdout, manifest e uso do provider quando disponível |
| Related code | `sparkforge_aws/evals/evolution.py`, `sparkforge_aws/evals/decision_replay.py`, `sparkforge_aws/decision/host.py`, `sparkforge_aws/decision/receipts.py`, `sparkforge_aws/facts/host_transcript.py`, `tests/test_decision_evolution.py` | 6 pontos principais | Contratos e testes existentes para candidate, replay, transcript, receipt, integridade e promoção |

**How samples will be used:**

- Fixtures `host_transcript` serão casos de integridade, normalização, comparação e recusa do adapter.
- `host_replay.yaml` e `provider_transcripts.yaml` serão exemplos mínimos de transcript presente, ausente, válido e inválido.
- Ground truth rotulado será usado para derivar status accuracy, evidence recall, false-positive rate, route accuracy e regressões.
- Fixtures de receipts e testes de tamper serão referência de compatibilidade e verificação do novo policy digest.
- Transcripts reais não serão copiados para o repositório sem sanitização; o bundle deve carregar hash, proveniência e referência segura.

---

## Approaches Explored

### Approach A: Evidence Bundle + Promotion Gate ⭐ Recommended

**Description:** Criar um bundle canônico que una candidate, parent, suite/input manifest, transcripts, modo de execução, métricas, policy digest e referências de evidência. Um `PromotionGate` deriva a decisão a partir do bundle e da policy resolvida por `candidate kind` e contract.

**Pros:**
- Usa os contratos content-addressed, replay, host e receipt que já existem.
- Permite comparar baseline e candidate com uma execução por lado e mantém qualidade/economia separadas.
- Faz integrity, CI, benchmark, revisão, rollback e policy serem verificáveis no mesmo artefato.

**Cons:**
- Exige versionar um novo envelope e definir migração dos receipts antigos.
- A policy por family aumenta o contrato de configuração e o número de casos de teste.

**Why Recommended:** O código já tem as fronteiras necessárias em `sparkforge_aws/evals/evolution.py` e o corpus já contém transcripts e ground truth. O padrão KB de `genai` recomenda métricas estruturadas, comparação pareada e quality gates; o padrão de validation prompts reforça evidência e formato verificável. Confiança: **0,95**, por haver padrão KB e correspondência direta no códigobase.

---

### Approach B: Compatibilidade em três incrementos

**Description:** Entregar a mesma arquitetura em etapas: primeiro policy digest, execução única e ordenação verificável; depois adapter de transcript L1; por fim adapter de comando live e policies por family.

**Pros:**
- Reduz risco de migração e permite manter a API de `CandidateEvaluation` durante a transição.
- Cada etapa produz evidência testável antes de habilitar promoção externa.

**Cons:**
- Contratos intermediários permanecem por algum tempo.
- Há risco de duplicar validações se a fachada de compatibilidade não apontar para o bundle canônico.

**Why not recommended alone:** É o rollout escolhido, mas não deve virar três implementações independentes. O bundle e o gate da Approach A continuam sendo a fonte única; os incrementos são apenas adapters e compatibilidade.

---

### Approach C: Workflow declarativo por adapters

**Description:** Descrever em YAML families, adapters, métricas e gates, com um executor genérico para qualquer nova classe de candidate.

**Pros:**
- Facilita adicionar novas families sem alterar o executor principal.

**Cons:**
- Amplia schema, CLI, superfície e validação antes de o primeiro fluxo L1 estar estabilizado.
- Pode esconder regras de segurança importantes em configuração declarativa.

**Why not recommended:** O repositório tem uma family registrada e contracts explícitos; descoberta automática e DSL genérica não são necessárias para validar o problema atual. Pode ser adicionada depois que o bundle provar mais de uma family real. Confiança: **0,80**, por haver apenas precedente parcial no códigobase.

---

## Data Engineering Context (if applicable)

Este recurso não é um pipeline de dados. Os arquivos de transcript e ground truth são evidências de avaliação; não há fonte operacional, transformação, tabela ou SLA de frescor a modelar.

### Source Systems

| Source | Type | Volume Estimate | Current Freshness |
|--------|------|-----------------|-------------------|
| Host transcripts | Artifact externo/local | Não declarado | Sob demanda |
| Evaluation fixtures | YAML/JSONL versionado | Corpus pequeno | Atualizado por commit |

### Data Flow Sketch

```text
[Host ou fixture] → [Adapter] → [Evidence Bundle] → [Replay/Compare] → [Promotion Gate] → [Receipt]
```

### Key Data Questions Explored

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual a origem da evidência? | Host externo ou fixture versionada | O adapter deve validar proveniência e hash |
| 2 | O Forge chama o provider? | Não | Tokens e custo só entram quando o host fornece transcript/usage válido |
| 3 | Como a evidência é consumida? | Comparação e promoção auditável | Bundle e receipt precisam preservar IDs, policy e rollback |

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A + B: Evidence Bundle + Promotion Gate entregue por incrementos compatíveis |
| **User Confirmation** | 2026-09-30 |
| **Reasoning** | O usuário confirmou o pacote integrado, aceitou rollout incremental, exigiu replay L1 e live externo opcional, e aprovou dois adapters sob o mesmo contrato. |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|---------------------|
| 1 | Bundle canônico será a fonte de verdade da avaliação | Evita que gates e receipts reconstruam evidência de forma diferente | Manter `CandidateEvaluation` como único contrato sem policy digest |
| 2 | Host bundle e comando externo usam o mesmo adapter contract | Permite file/stdin e execução autorizada sem duplicar o gate | Criar um fluxo especial para live |
| 3 | Cada candidate é executado uma vez por avaliação | Remove duplicação observada no formato baseline/candidate atual | Rodar o candidate duas vezes e esconder o custo no report |
| 4 | Policy resolve por candidate family/kind e contract | Evita policy global ambígua e centraliza mínimo de corpus | Aceitar `50` hard-coded em `gates_pass` |
| 5 | Live é externo e explícito | Preserva o núcleo offline e torna autorização/proveniência auditáveis | SDK/provider chamado diretamente pelo Forge |
| 6 | Receipts antigos continuam legíveis | Reduz migração e permite auditoria histórica | Invalidar todo o histórico ao mudar o envelope |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Chamada direta de provider dentro do Forge | Viola o núcleo offline/provider-independent e mistura avaliação com execução | Yes |
| Múltiplos judges ou consenso automático | Não é necessário para provar replay, policy e receipt; adicionaria variabilidade | Yes |
| Auto-merge, deploy ou ativação automática após gate | Promoção precisa continuar explícita e reversível neste MVP | Yes |
| DSL YAML genérica para descobrir adapters/families | Há uma family registrada e o bundle primeiro precisa ser provado | Yes |
| Otimização adaptativa dos thresholds | Thresholds devem vir de policy versionada e revisão humana, não de feedback automático | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Architecture concept | ✅ | Confirmou A+B: bundle/gate integrado com rollout incremental | No |
| Component breakdown | ✅ | Confirmou compatibilidade, execução única, policy por family e receipts verificáveis | No |
| Data flow | ✅ | Confirmou dois adapters: bundle do host e comando externo sob o mesmo contrato | No |
| Error handling | ✅ | Confirmou recusa nomeada para integridade, policy, transcript ou evidência incompleta | No |

**Minimum Validations:** 2 (to ensure alignment)

---

## Suggested Requirements for /define

Based on this brainstorm session, the following should be captured in the DEFINE phase:

### Problem Statement (Draft)

A camada de evolução precisa transformar avaliações offline e host externas em evidência content-addressed, policy-bound e verificável, permitindo replay L1 e promoção live autorizada sem chamadas de provider no Forge, duplicação de execução ou gates autoafirmados.

### Target Users (Draft)

| User | Pain Point |
|------|------------|
| Maintainer | Não consegue reproduzir uma avaliação real nem provar que a policy usada é a mesma da promoção |
| Operator | Precisa entregar transcript/live evidence e promover ou recusar candidate com rollback claro |
| Reviewer | Precisa auditar hashes, métricas, policy, CI, benchmark, revisão e receipt sem confiar em booleanos |

### Success Criteria (Draft)

- [ ] Um adapter de bundle e um adapter de comando externo produzem o mesmo `EvaluationEvidenceBundle` canônico.
- [ ] Baseline e candidate são executados uma vez por avaliação; a prova registra a identidade e a contagem das execuções.
- [ ] O bundle vincula candidate, parent, suite/input manifest, transcript hashes, modo de execução, métricas, policy digest e referências de evidência.
- [ ] `minimum_labeled_tasks` e demais gates vêm da policy resolvida por family/kind e contract, sem cópia hard-coded em `CandidateEvaluation`.
- [ ] O comparador deriva quality/economy gates; caller não consegue afirmar `ci_verified`, `quality_gate` ou `economy_gate` sem evidência validada.
- [ ] Alteração de bundle, transcript, candidate, suite, contract ou policy produz recusa nomeada e impede promoção.
- [ ] Receipts legados continuam legíveis; receipts novos têm versão, sequência verificável e policy digest.
- [ ] Promoção exige CI/benchmark/review refs, rollback target, contract identity e autorização explícita.
- [ ] O Forge não importa nem chama provider; tokens/custo ficam unresolved quando o host não fornece fonte válida.
- [ ] Todos os candidate kinds/families registrados têm policy explícita ou recusa nomeada por ausência de policy.

### Constraints Identified

- O núcleo deve permanecer offline e provider-independent.
- A evidência externa pode vir por bundle ou comando autorizado, com o mesmo contrato e proveniência verificável.
- Receipts, candidate digests e rollback são content-addressed ou vinculados por hash.
- Nenhum transcript real sem sanitização deve ser adicionado ao repositório.
- Promoção não pode ocorrer por flag booleana ou por evidência incompleta.
- A migração precisa preservar leitura de receipts existentes.

### Out of Scope (Confirmed)

- Chamada direta de SDK/provider pelo Forge.
- Múltiplos judges, consenso estatístico ou thresholds adaptativos.
- Auto-merge, deploy ou ativação automática.
- DSL genérica para descoberta automática de adapters e families.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 9 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 2 |
| Duration | Not measured |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_PROMPT_EVO_NOVA_EVOLUCAO.md`
