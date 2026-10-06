# Evolu‡Æo Agˆntica do SparkForge

> **Dois pacotes com nome parecido, e eles não são a mesma coisa.** Este
> documento descreve `sparkforge_aws/agents/` — `ConversationRoom`,
> `AutonomyController`, `Supervisor`, `budget`, `model_policy` —, a camada de
> orquestração que existe desde a expansão agêntica. `sparkforge_aws/agentic/`
> (2026-09-03) é OUTRO pacote: entidades de primeira classe (`Claim`,
> `Evidence`, `Decision`), protocolo de debate, arbitragem e blackboard JSONL,
> e ele é **biblioteca sem produtor** — nada no produto escreve nessas
> entidades. Ver `docs/agentic-evolution-report.md`. A sobreposição entre os
> dois (autonomia, budget e observabilidade aparecem nos dois pacotes) é dívida
> conhecida, registrada e não resolvida.


## VisÆo

O SparkForge agora combina agents especializados, mem¢ria compartilhada por caso, handoffs estruturados, roteamento por fase e autonomia limitada. A met fora de sala de conversa representa o protocolo de coopera‡Æo; nÆo ‚ necess rio criar uma interface de chat.

## Capacidades

| Capacidade | Implementa‡Æo | Benef¡cio |
|---|---|---|
| Autonomia controlada | `AutonomyController` | Escolhe a menor pr¢xima etapa e para por or‡amento, estagna‡Æo ou sucesso |
| Mem¢ria compartilhada | `ConversationRoom` | Mant‚m fatos, decisäes, referˆncias e snapshots sem reenviar o hist¢rico inteiro |
| Economia de tokens | `budget.py` | Deduplica, ranqueia por relevƒncia, preserva decisäes e limita contexto |
| Especializa‡Æo | agents de PySpark, runtime, storage, orquestra‡Æo e verifica‡Æo | Reduz escopo, fan-out e chamadas sem ganho |
| Governan‡a de ferramentas | allowlist, aprova‡Æo e rollback | Evita a‡äes mut veis e ferramentas fora do contrato |
| Conhecimento | `knowledge/agentic-engineering.md`, `token-economy.md` e matriz | Padroniza decisäes e melhora handoffs |

## Pol¡tica de qualidade por token

Uma redu‡Æo s¢ ‚ v lida quando mant‚m cobertura de evidˆncia, achados aceitos, taxa de verifica‡Æo e crit‚rios de aceita‡Æo. O sistema deve medir tokens de entrada e sa¡da, cache hits, duplicatas removidas, cobertura de evidˆncia e falhas de verifica‡Æo.

## Loop recomendado

O fluxo normal ‚ `inventory -> collect -> analyze -> judge -> verify -> synthesize`. O supervisor s¢ amplia o n£mero de agents quando existe risco, contradi‡Æo ou lacuna. A execu‡Æo deve come‡ar pelo caminho barato e determin¡stico, usando LLM apenas quando houver ambiguidade ou s¡ntese necess ria.

## Crit‚rios de parada

A execu‡Æo termina por decisÆo terminal, or‡amento de itera‡äes, or‡amento de tokens, limite de mensagens, estagna‡Æo ou regressÆo de qualidade. Nunca aumente o or‡amento automaticamente porque o loop nÆo progrediu.

## Opera‡Æo

## Prompt e agent evolution

`config/evolution/prompt_agents.yaml` registra candidatos versionados offline.
Cada candidato recebe digest SHA-256 da identidade declarada, incluindo versão,
contrato, calibração e pai. Mutação precisa apontar para o digest do pai; conteúdo
externo ao repositório é recusado.

Estados permitidos: `candidate -> evaluated -> accepted -> rolled_back` e
`evaluated -> rejected`. A transição não concede autoridade. Promoção ativa usa a
mesma `AuthorityPolicy`, exige contrato, calibração, gates, referências de
evidência e rollback, e segue desabilitada na política padrão.

`EvolutionService` faz replay local contra a suíte imutável de 50 casos, mantendo
caso, domínio, partição e perfil. Qualidade, rota, bytes, tokens de transcript e
custo com `cost_basis` ficam separados; ausência vira `unresolved`.

Recibos content-addressed em `.sparkforge/evolution/` vinculam candidato, pai,
suíte, gates, autoridade e rollback. Núcleo não chama modelo, AWS ou provedor.

O manifesto separa duas provas: `candidate_digest` identifica a especificacao
completa (id, versao, conteudo, contrato, calibracao, tipo e pai), enquanto
`content_sha256` e o SHA-256 real dos bytes UTF-8 do conteudo. Candidatos `root`
nao tem pai; candidatos `mutation` exigem `parent_digest`. Cada candidato tambem
fixa `contract_sha256`, que precisa coincidir com o contrato carregado do
repositorio.

`EvolutionService.evaluate` executa o baseline aceito e o candidato em
replay same-case separado. O runner offline e deterministico e o conteudo da
mutacao altera a observacao; ele nao simula tokens de provider. Os campos
`quality_gate` e `economy_gate` sao derivados dos `metrics` contra
`evaluation_policy` do manifesto. `ci_verified` e referencias de evidencia
continuam sendo evidencia externa explicita.

Na leitura, todo receipt verifica nome, `receipt_id` e o digest do corpo antes
de ser usado. Campos booleanos, inteiros, textos e referencias sao lidos sem
coercao. `require_evaluation_receipt` e `require_rollback_target` controlam
efetivamente promocao e avaliacao conforme a politica declarada.

Operação local:

```bash
python -m sparkforge_aws.evals candidate validate --repo .
python -m sparkforge_aws.evals candidate evaluate --repo . --candidate routing-variant
python -m sparkforge_aws.evals candidate promote --repo . --candidate routing-variant --allow-active
python -m sparkforge_aws.evals candidate rollback --repo . --candidate routing-variant --previous routing-baseline
```

### Hardening de evidence e lifecycle

Bundles sao estruturalmente validos antes de serem evidence verificadas. O
`EvidenceResolver` usa roots exclusivos por kind (`ci`, `benchmark` e `review`),
resolve symlinks dentro do repositorio e compara o SHA real do arquivo. A forma
legada `evidence.roots` continua disponivel somente quando `evidence.kinds` nao
existe; nao ha root implicito do repositorio.

`recorded_host` exige transcripts baseline e candidate com `source_ref` e SHA
verificaveis. `live_external` exige comando presente no registry e uma
`ExternalCommandIdentity` derivada de command id, hashes do executavel e artefato,
args fixos, timeout e limite de saida. O adapter usa `shell=False`, arquivo de
saida bounded e anexa a identidade ao bundle.

Para bundles recorded/live, metrics declaradas sao claims. O compiler local
recalcula comparison, quality e economy a partir de rows primitivas e recusa
mismatch. `unresolved` entra em `CandidateEvaluation`; somente valores permitidos
pela policy permanecem nao bloqueantes. `gates_pass` inclui evidence verificada,
kinds requeridos e reasons de gate antes de chamar `AuthorityPolicy`.

O estado efetivo do candidate vem da cadeia de receipts v2 verificada. Receipts
v1 permanecem legiveis para auditoria, mas nao autorizam lifecycle ou promotion.
O lock local grava PID, host, timestamp e fingerprint de processo; recovery so
ocorre apos threshold e prova de PID ausente. Lock ocupado ou nao verificavel
falha fechado. Promotion receipts guardam provenance compacta: evaluation receipt,
bundle, producer identity, refs/kinds verificadas, metrics, mode e rollback.

O caminho surrogate continua offline e nao executa comandos externos. Os modos
bundle e external sao opt-in pela CLI:

```bash
python -m sparkforge_aws.evals candidate evaluate --repo . --candidate routing-variant --bundle path/to/bundle.json
python -m sparkforge_aws.evals candidate evaluate --repo . --candidate routing-variant --external-command command-id
```

### Active promotion provenance

Surrogate replay remains valid for evaluation, shadow, assisted and regression
flows, but it is never eligible for active promotion. When active authority is
enabled, promotion requires resolver-verified evidence, at least one verified
reference and verified evidence kinds covering every kind required by the
candidate policy. `bundle_id` identifies a bundle; it does not prove that its
evidence was verified.

The promotion order is evaluation, evidence resolution, active provenance gate,
rollback validation and authority policy. Missing or unverified provenance is a
named refusal and never falls back to raw `evidence_refs`.

Authorized external commands must pin every repo-confined regular file passed by
fixed arguments through the existing `artifact`/`script` declaration and its
`artifact_sha256`/`script_sha256`. A missing declaration, path escape, digest
mismatch or argument/artifact mismatch fails closed. Self-contained executables
with no file argument remain valid without an artifact declaration.

Ap¢s alterar skills ou agents, execute `python scripts/sync_skills.py`. Antes de publicar uma mudan‡a, execute os testes focados, a su¡te completa e as avalia‡äes existentes. Mudan‡as de infraestrutura, escrita ou publica‡Æo exigem aprova‡Æo humana, plano de rollback e evidˆncia do impacto.
