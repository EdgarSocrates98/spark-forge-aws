# A2A spec review — bounded, documentation-only

Revisao pendente do §113 do prompt de convergencia: avaliar a spec A2A
vigente contra o vocabulario do adapter. Escopo desta revisao: a **forma**
do que `sparkforge_aws/protocols/a2a_adapter.py` produz/consome — nenhum
comportamento novo, nenhum SDK, nenhum servidor.

- Revisado em: 2026-10-06
- Spec de referencia: A2A Protocol **v1.0.x**
  (`https://a2a-protocol.org/v1.0.0/specification/`,
  `github.com/a2aproject/A2A` tag v1.0.1)
- Artefato avaliado: `sparkforge_aws/protocols/a2a_adapter.py` (stdlib-puro,
  `a2a-ready`, EXPERIMENTAL)
- Data da escrita do adapter: vocabulario da era JSON-RPC v0.2.x

## O que continua correto

- Os seis estados que o adapter produz — `submitted`, `working`,
  `completed`, `failed`, `rejected`, `unknown` — existem na spec vigente
  (TaskState), e `unresolved` mapear para `unknown` continua sendo a forma
  honesta ("o servidor nao sabe") — nunca `completed`.
- `AgentSkill` carrega `id`/`name`/`description`/`tags` — os quatro campos
  obrigatorios da spec, todos presentes.
- Mensagem com `parts` de `kind` `text`/`data` casa com o modelo `Part` da
  spec (`TextPart`/`DataPart` no binding JSON, `text`/`data` em v1.0).

## Divergencias medidas contra v1.0.x

| ponto | adapter | spec v1.0.x | impacto |
|---|---|---|---|
| metodo de submit | modela `tasks/send` (v0.2 JSON-RPC) | `message/send` | docstring renomeada; a traducao message+parts continua correta |
| AgentCard | `url` + `protocol` + `capabilities` como lista de capacidades | `supportedInterfaces` + `protocolVersion`; `capabilities` e o objeto AgentCapabilities (`streaming`, `pushNotifications`, `extensions`) | o card nao e um AgentCard v1.0 conforme — e uma forma a2a-ready ancorada no ForgeCapability |
| serializacao de enum | estados lowercase (`submitted`) | ProtoJSON serializa `TASK_STATE_SUBMITTED` (SCREAMING_SNAKE) nos bindings gRPC; o vocabulario lowercase e o do binding JSON-RPC/REST | correto para o binding JSON; documentado para nao confundir com o proto |
| estados nao produzidos | — | `input-required`, `canceled`, `auth-required` | o vocabulario Forge nao tem esses estados; o adapter so traduz o que o Forge produz — correto por construcao |
| assinatura | — | `signatures`/AgentCardSignature | fora do recorte experimental |

## Decisao

`spec_reviewed` passa a `True` com `spec_version` e as divergencias nomeadas
no proprio `A2A_EXPERIMENTAL` — a revisao aconteceu, e o resultado e que o
adapter segue sendo o que sempre declarou ser: `a2a-ready`, EXPERIMENTAL,
camada de traducao que um SDK real usaria. Nenhuma das divergencias
introduz trabalho nesta onda — sao o registro honesto do que um port para
a spec v1.0.x teria que enderecar, e ficam como BACKLOG do adapter.

Gatilho para alinhar a v1.0.x: um driver/SDK A2A real consumir o adapter
(ex.: cliente A2A externo precisando descobrir o Forge por AgentCard
conforme). Ate la, o custo de perseguir a forma v1.0 exato nao se paga —
ninguem consome o card.
