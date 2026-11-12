# Árvore de decisões — `decisions.json`

Referência da skill `sdd-explore`. O `decisions.json` mora ao lado do
`explore.md` em `docs/sdd/<FEATURE>/` (ou `.sparkforge_aws/sdd/<FEATURE>/` no
perfil operator) e registra a entrevista como dado: o que já foi decidido,
por quem, com que evidência, e o que ainda falta. O gate do SDD não lê este
arquivo — ele é o registro da skill, e é o que permite retomar a entrevista
noutra sessão sem depender de memória.

## O contrato

```json
{
  "feature": "EXEMPLO",
  "mode": "sequencial",
  "decisions": [
    {
      "id": "DEC-1",
      "question": "A mudança é no SparkForge ou num job do operador?",
      "type": "decision",
      "depends_on": [],
      "status": "answered",
      "alternatives": [
        {"id": "dev", "recommended": true,
         "rationale": "o pedido toca o catálogo de regras"},
        {"id": "operator", "recommended": false,
         "rationale": "nenhum artefato de job foi citado"}
      ],
      "evidence": [],
      "answer": "dev",
      "actor": "operator",
      "impact": "reversible",
      "reopen_condition": "se o case revelar um job afetado"
    }
  ]
}
```

| campo | forma | regra |
|---|---|---|
| `id` | `DEC-<n>` | estável; nunca reciclado dentro da feature |
| `question` | texto | a pergunta como foi (ou será) feita |
| `type` | `fact` \| `decision` | `fact` se resolve com verbo, medida ou leitura; `decision` se só o operador resolve |
| `depends_on` | `[DEC-<n>, ...]` | só `type: fact` ou decisões já `answered`; cadeia circular não vale |
| `status` | `pending` \| `answered` \| `blocked` \| `skipped` \| `reopened` | `reopened` registra que voltou atrás, nunca apaga a resposta anterior |
| `alternatives` | `[{id, recommended, rationale}]` | uma marcada `recommended: true` com o porquê; alternativa sem `rationale` não entra |
| `evidence` | `[{kind, ref, note}]` | verbo rodado, arquivo lido, medida tomada — nunca "eu acho" |
| `answer` | texto ou `null` | a escolha do operador, igual a um `alternatives[].id` quando há alternativas |
| `actor` | `operator` \| `agent` | quem respondeu; `agent` só para `type: fact` |
| `impact` | `reversible` \| `costly` \| `one-way` | `costly`/`one-way` exigem `reopen_condition` explícita |
| `reopen_condition` | texto | o que permite reabrir sem recomeçar a entrevista |

Campo de topo: `mode` registra o modo vigente; a troca de modo é registrada
no corpo do `explore.md` com o motivo.

## Os modos

- **`sequencial`** — uma pergunta por mensagem. Default e sempre disponível:
  qualquer decisão pode puxar a conversa de volta para ele, mesmo nos outros
  modos.
- **`rodada`** — um bloco de perguntas por mensagem, agrupadas por tema
  ("três sobre o job, duas sobre a entrega"). Só entre decisões sem
  `depends_on` entre si; a primeira resposta que criar dependência quebra a
  rodada.
- **`adaptativo`** — a ordem muda a cada resposta ou evidência: decisões que
  ficaram irrelevantes saem (`skipped` com o motivo), as que abriram entram
  `pending`, e a fila é re-apresentada quando muda.
- **`fronteiras`** — agrupa por fronteira (módulo, conta, runtime) **somente
  decisões independentes** que a política da entrevista autorizar. A
  política mínima: sem `depends_on` entre si, sem `impact: one-way`, e o
  operador ciente de que está respondendo em bloco. Decisão dependente sai
  do grupo e volta ao sequencial — agrupar dependência é a forma mais comum
  de resposta coerente-errada.

## Contradições e reabertura

- Resposta nova que contradiz uma `answered` marca as duas no corpo e sobe ao
  operador **na mesma hora**: ele confirma uma delas, ou as duas viram
  `reopened` para repensar. Contradição registrada não é defeito; escondida é.
- Reabrir usa `reopen_condition`: a decisão volta `reopened`, a resposta
  antiga permanece no histórico (o `answer` muda, o corpo registra o par
  antes/depois), e o motivo entra na evidência. Editar `answer` em silêncio
  é como a árvore deixa de ser registro.
- `impact: one-way` na prática é raro no explore (quase tudo é reversível em
  spec); quando aparecer, a decisão desce para `sequencial` custe o que
  custar.

## Retomada

Na reabertura da sessão: leia `decisions.json` primeiro — `answered` fica,
`pending`/`blocked`/`reopened` volta à fila do `mode` gravado. Depois
`sparkforge-aws sdd status --repo .` para conferir que a feature ainda está na
fase esperada. Sem árvore e sem memória da entrevista, reconstrua com o
operador antes de seguir: décisão sem registro é premissa não confirmada.

## Confirmação final

Antes de `status: ready` no `explore.md`, releia a árvore com o operador:
toda decisão com `answer` ou `skipped` justificado, toda contradição
resolvida, a abordagem escolhida entre as `approaches` e as rejeitadas com o
motivo. A confirmação é o último portão da fase — sem ela, `draft`.
