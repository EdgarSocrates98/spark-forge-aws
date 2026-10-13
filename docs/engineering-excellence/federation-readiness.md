# AWS Federation Readiness

**Data:** 2026-10-12  
**Escopo:** `spark-forge-aws` na branch `codex/evo-grill-2026-10-12`  
**Decisão:** `PARTIAL` para federação entre forjas. O repositório está pronto
para publicar capacidades determinísticas, compor artefatos AWS declarados e
verificar receipts locais; ainda não implementa descriptor canônico de peer,
negociação remota ou troca de receipts federados.

Este documento usa `supported` somente quando há código e teste que sustentam a
afirmação. Ausência de evidência permanece `unresolved`; não é convertida em
`not_supported`.

## Resumo por camada

| Camada | Estado | O que existe | Limite atual |
| --- | --- | --- | --- |
| Capabilities AWS | `SUPPORTED` | Catálogo versionado de tools/CLI para análise e coleta de artefatos AWS | Não é prova de que uma conta ou região esteja acessível |
| Descoberta local | `SUPPORTED` | Context Gateway, perfis com teto e seleção determinística | Seleciona capacidades locais; não negocia com outro peer |
| Descriptors | `PARTIAL` | `ForgeHealth`, `ForgeGraphView/v1`, `forge/PortalApi/1` e card A2A experimental | Não há um `AwsFederationDescriptor/v1` único |
| Negotiation | `NOT READY` | Estratégia por runtime e adapter A2A de tradução | Sem handshake, interseção de capabilities, auth ou acordo de versão |
| Receipts | `SUPPORTED` localmente | Receipts content-addressed e verificação por partes | Sem receipt federado que amarre peer, descriptor e contrato negociado |
| Mutação AWS | `OUT OF SCOPE` | Collectors explícitos e decisões offline; mutações locais governadas | O core não executa AWS nem promove autoridade por scorecard |

## 1. Inventário real de capabilities AWS

O inventário abaixo descreve capacidades de engenharia sobre artefatos AWS. Não
é uma promessa de cobertura total dos serviços AWS nem uma matriz de permissões.

| Família | Capabilities observadas | Evidência versionada |
| --- | --- | --- |
| Glue e catálogo | Jobs, job runs, Glue Data Catalog, Glue Streaming/Real-Time Mode, Schema Registry, Terraform `aws_glue_job`, runtime e Lake Formation | `parity.yaml` declara tools/CLI/knowledge; `sparkforge_aws/facts/`, `sparkforge_aws/collect/` e `sparkforge_aws/lakeformation/` contêm as implementações |
| EMR | EMR on EC2, EMR Serverless e EMR on EKS; análise de dumps e collectors read-only | `parity.yaml` (`analyze emr-cluster`, `emr-serverless`, `emr-eks` e correspondentes `collect`); `tests/test_runtime_emr_matrix.py` e testes dos collectors |
| Lakehouse e query | Apache Iceberg, Parquet footer, S3 listings, Athena workgroups, CloudWatch e métricas SQL | `parity.yaml` e `manifest.json`; `sparkforge_aws/facts/iceberg.py`, `parquet_footer.py`, `s3_listing.py`, `cloudwatch.py`, `sql_metrics.py` |
| Governança e acesso | Grants Lake Formation, resource links Glue, IAM policy simulation e arquitetura cross-account declarada | `sparkforge_aws/lakeformation/`, `sparkforge_aws/facts/lakeformation_grants.py`, `iam_access.py`; o caminho de acesso cross-account permanece dependente de evidência e role |
| Streaming e integração | Kafka/MSK, Kinesis, Structured Streaming, Flink/Managed Flink, CDC/Debezium/AWS DMS, OpenLineage e Schema Registry | `parity.yaml` (`analyze transport`, `flink`, `cdc`, `schema-registry`, `streaming-integrations`); collectors read-only em `sparkforge_aws/collect/` |
| Orquestração AWS | AWS Step Functions: definição de state machine e histórico de execução | `parity.yaml` (`analyze step-functions`, `analyze sfn-history`); módulos `sparkforge_aws/facts/stepfunctions.py` e `sfn_history.py` |
| Grafo live AWS | Composição limitada aos `cloud_resources` declarados no workspace manifest, com provenance, frescor, truncamento e `unresolved` | `sparkforge_aws/collect/live_graph.py`, `sparkforge_aws/workspace/federation.py`, `tests/test_collect_live_graph.py` e `tests/test_workspace_federated_graph.py` |

### Modos de acesso

- `analyze ...` lê artefatos já presentes e permanece offline.
- `collect ...` é a única lane que toca AWS; credenciais, região, role,
  catálogo e resource ARN precisam ser fornecidos pelo operador quando o verbo
  exigir.
- `collect workspace-graph` não descobre uma nuvem inteira: limita-se aos
  recursos declarados no manifest e preserva `unresolved`, limites e
  provenance.
- O catálogo público é amarrado por `manifest.json`, `parity.yaml` e
  `tests/test_capability_parity.py`: tools, verbos CLI e arquivos de knowledge
  declarados precisam existir, e toda tool real precisa aparecer em alguma
  capability.

## 2. Descriptors existentes e gaps

### O que pode ser publicado hoje

1. `ForgeHealth` expõe `status`, `version`, capabilities e checks em
   `sparkforge_aws/protocols/forge.py`.
2. `ForgeGraphView/v1` expõe `GraphDescriptor` com provider, domínio, schema,
   contagens, queries, capabilities e limitations. A projeção AWS não é
   implícita: `compose_workspace_graph` exige bridges explícitas para ligar o
   grafo semântico ao artefato live.
3. O portal local expõe `forge/PortalApi/1` por `/bootstrap` e
   `/capabilities`. `SparkForgePortal.capabilities()` publica `install`,
   `hosts`, `mcp`, `skills`, `agents`, `tasks`, `docs` e `graph`, com estado
   `supported` ou `unverified` conforme a evidência local.
4. `a2a_adapter.agent_card()` traduz `ForgeCapability` para uma forma de card
   A2A experimental. O conteúdo sempre vem de `ForgeCapability`; o card não é
   uma fonte independente de capacidades.

### Gaps para `descriptors`

- Falta um descriptor canônico que reúna `forge_id`, endpoint/transport,
  identidade do peer, AWS account/region, runtime efetivo, capabilities,
  operações, schemas de input/output, limites, requisitos de permissão,
  freshness e razões `unresolved`.
- `federated: false` no portal é um estado local, não uma prova de ausência ou
  presença de peers. `GraphDescriptor` descreve o grafo que um provider expõe;
  não descreve autoridade AWS nem uma sessão de federação.
- Não existe vínculo versionado entre descriptor, capability e schema de
  receipt. Um consumidor não consegue saber, por contrato, qual descriptor
  originou uma execução ou quando ele expirou.
- O card A2A não é conforme à forma A2A v1.0.x. A revisão registrada em
  `docs/audit/A2A-SPEC-REVIEW.md` mede divergências em `supportedInterfaces`,
  `protocolVersion`, `capabilities` e assinatura.

## 3. Negotiation: capacidade local não é acordo entre peers

Há duas formas de seleção local, ambas verificadas:

- `sparkforge_aws/context/gateway_capabilities.py` descobre e limita
  capabilities pelos perfis `economy`, `balanced` e `deep` antes de materializar
  contexto.
- `sparkforge_aws/agentic/runtime.py` seleciona `parallel`, `sequential` ou
  `playbook` a partir das capacidades medidas do runtime. O teste
  `tests/test_agentic_runtime.py::TestParityBinding` amarra `spawn_agent` e
  `tool_calling` ao `parity.yaml`.

O adapter A2A cobre somente forma: `submit_task()` traduz `message.parts` em
`ForgeTask`, e `result_to_a2a_task()` devolve `evidence_bundle` e
`unresolved`. Ele não é um servidor A2A e não estabelece uma sessão com outro
agente.

### Gaps para `negotiation`

- Não há função ou endpoint que compute a interseção entre capabilities local e
  remota, considerando versão, domínio, operação, risco, budget e limites.
- Não há handshake com nonce, identidade, autenticação, autorização,
  account/region, role ou confirmação de que o peer pode executar a operação.
- Não há estados de acordo como `accepted`, `rejected` e `needs_evidence` com
  razões estruturadas; `ForgeTaskStatus` é estado de tarefa, não resultado de
  negociação.
- Não há transporte remoto, servidor A2A, cancelamento, push notification ou
  assinatura de AgentCard. A classificação correta continua `a2a-ready` e
  `EXPERIMENTAL`, conforme `A2A_EXPERIMENTAL` e
  `tests/test_runtime_convergence_a2a.py`.
- A composição federada não infere edges entre fragments. Sem bridge explícita,
  o resultado preserva os fragments separados; ausência de bridge não vira
  relação `corresponds_to`.

## 4. Receipts: integridade local presente, federação ausente

### O que existe

- O Execution Receipt em `.sparkforge_aws/receipts/` é content-addressed (`rcpt_`)
  e cobre case, evidence, judgment, decision, proof, tools e host. A verificação
  recalcula integridade e informa `match`, `diverged`, `missing`,
  `not_rechecked` ou `not_evaluable` por parte.
- `sparkforge-aws receipt emit` inclui caminhos relativos e SHA-256, IDs e
  contagens, sem copiar o conteúdo do case. `receipt verify` reconfere o disco
  e recusa path escape.
- Decision receipts ficam em `.sparkforge_aws/decision-receipts/` e receipts do
  Forge Lab/instalação têm schemas próprios (`forge/*`). São receipts locais de
  produtos diferentes; não devem ser tratados como um protocolo federado único.
- `tests/test_receipt_build.py`, `tests/test_receipt_verify.py` e
  `tests/test_fixtures_golden_receipt.py` provam determinismo, digest,
  adulteração, `unresolved` e limites do receipt.

### Gaps para `receipts` federados

- O receipt não amarra descriptor usado, capabilities negociadas, versão do
  contrato, peer remoto, identidade autenticada, autorização, request/response
  hash ou confirmação de entrega.
- O próprio contrato recusa autoria (`content_addressed_sem_chave`) e não faz
  hash do I/O completo de tool (`span_sem_hash_de_io`). Integridade e
  correspondência não são não-repúdio.
- Transcript fora do repo e traces ausentes podem sair como `not_rechecked`;
  isso é deliberado, mas impede alegar verificação remota completa.
- Não há endpoint ou CLI para importar, trocar e verificar um receipt de outro
  peer mantendo cadeia de confiança, replay protection ou prevenção de
  duplicação entre forjas.

## 5. Limites de especialidade

O limite operacional do projeto deve ser lido como parte da capability:

- Especialidade: diagnóstico determinístico de engenharia de dados AWS/PySpark,
  Glue, EMR, lakehouse, streaming, governança e artefatos relacionados.
- Não é: um orchestrator genérico de agentes, um servidor A2A, uma autoridade
  IAM/Lake Formation, um executor de jobs AWS ou uma prova de disponibilidade
  de qualquer conta, região ou serviço.
- `analyze` não prova estado live. `collect` exige acesso explícito e pode
  produzir truncamento ou `unresolved`; a ausência de um artefato não prova que
  o recurso não existe.
- Runtimes, Glue/EMR, Spark e Iceberg são materialmente versionados. Divergência
  entre fontes deve sair como divergência; uma capability fora da matriz não é
  promovida por analogia.
- IAM simulation não substitui bucket policy, KMS key policy ou Glue resource
  policy. Cross-account exige evidência própria, role/catálogo declarados e
  resource link quando esse for o caminho escolhido.
- O grafo preserva estado epistemológico, provenance e limites. Relações entre
  fontes só existem quando declaradas por bridge.
- Receipt válido prova correspondência dos artefatos verificados; não prova
  autoria, identidade do operador, autorização AWS ou equivalência funcional do
  resultado.

## 6. Comandos e testes de verificação

Os comandos abaixo verificam as afirmações deste documento sem tocar AWS, salvo
os comandos marcados como live.

### Catálogo e superfície

```bash
python -m pytest -q tests/test_capability_parity.py
python -m pytest -q tests/test_adapters_tools.py tests/test_adapters_mcp_compact.py tests/test_surface_lock.py
sparkforge-aws --help
```

### Descriptors, grafo e A2A-ready

```bash
python -m pytest -q \
  tests/test_runtime_convergence_a2a.py \
  tests/test_workspace_federation.py \
  tests/test_workspace_federated_graph.py \
  tests/test_offline_federated_fixtures.py \
  tests/test_portal_adapter.py

sparkforge-aws graph status --root .
sparkforge-aws graph view --root . --limit 5000
```

`graph status` pode responder `unavailable` quando o índice local ainda não
existe; o desbloqueio nomeado é executar `sparkforge-aws code index`/`code
sync`, não inferir um grafo vazio.

### AWS live, somente quando o operador autorizar e fornecer evidência

```bash
sparkforge-aws collect workspace-graph \
  --repo . \
  --manifest <workspace-manifest.yaml> \
  --now <ISO-8601>
sparkforge-aws collect verify --repo .
```

Esse caminho é bounded aos `cloud_resources` do manifest, usa as credenciais do
processo e grava artefato local. Não é executado como parte da verificação
offline.

### Receipts

```bash
python -m pytest -q \
  tests/test_receipt_build.py \
  tests/test_receipt_verify.py \
  tests/test_fixtures_golden_receipt.py \
  tests/test_decision_kernel_receipts.py \
  tests/test_decision_receipts.py

sparkforge-aws receipt verify \
  --repo . \
  --receipt .sparkforge_aws/receipts/<receipt_id>.json

sparkforge-aws decision receipt \
  --repo . \
  --path .sparkforge_aws/decision-receipts/<receipt_id>.json
```

### Gate desta mudança

```bash
git diff --check
```

## Critério para declarar `READY`

A prontidão federada só pode subir de `PARTIAL` quando houver, com testes
reexecutáveis:

1. um descriptor versionado que cubra peer, transporte, identidade, AWS scope,
   capabilities, schemas, limites e freshness;
2. handshake/negotiation que produza acordo ou recusa nomeada antes de executar;
3. receipt federado que amarre descriptor, acordo, request, resultado,
   `unresolved`, identidade/autorização e cadeia de verificação;
4. um driver ou servidor remoto real, com teste de integração; e
5. evidência separada para cada conta/região/role AWS usada no cenário.

Até lá, a classificação correta é: capabilities AWS reais e úteis para análise,
federação de grafos explícita e local, interoperabilidade A2A experimental, e
receipts verificáveis localmente — não federação AWS end-to-end.
