# Cadeia de autorização

`prompt_evo_harness.md` §76 pede que cada ação tenha nível de autorização
verificado **antes** de executar, e §40 pede cinco classes de tool. O que
existia antes desta fase era `AutonomyController.authorize_tool(agent, tool,
allowed_tools, mutating, approval)` — uma checagem de um nível, com um booleano
`approval` sem escopo.

## A classe é derivada, não mantida

`sparkforge/adapters/tools.py` já declara três dimensões por tool:
`readOnlyHint`, `openWorldHint`, `destructiveHint`. Elas definem a classe:

| classe | derivação |
|---|---|
| `DESTRUCTIVE` | `destructiveHint` |
| `CLOUD_READ` | `readOnlyHint` ∧ `openWorldHint` |
| `READ_ONLY` | `readOnlyHint` ∧ ¬`openWorldHint` |
| `CLOUD_MUTATION` | ¬`readOnlyHint` ∧ `openWorldHint` |
| `LOCAL_MUTATION` | ¬`readOnlyHint` ∧ ¬`openWorldHint` |

Uma segunda tabela mantida à mão seria a família de defeito que a Fase 5c achou
nos dois `EXTRACTORS` paralelos: uma cresce, a outra não, e o desacordo é mudo.
`tests/test_harness_authorization.py` tranca a derivação — trocar a anotação de
uma tool muda a classe dela junto.

## Duas classes nascem vazias, e isso é o resultado

Medido em 2026-08-23, sobre 44 tools: nenhuma é `destructive`, e nenhuma é
mutante **e** de nuvem. `CLOUD_MUTATION` e `DESTRUCTIVE` existem sem membro.

O valor da classificação hoje não é bloquear o que existe — é impedir que uma
tool futura entre sem classe. `tool_class()` levanta `KeyError` para nome
desconhecido em vez de devolver `READ_ONLY`: default permissivo para o que
ninguém declarou é exatamente como uma tool nova passa sem aprovação.

## O que a cadeia acrescenta

`AuthorizationDecision` carrega o agente, o perfil e a aprovação que sustentou a
decisão. `authorize_tool` respondia `(bool, str)`, e o `str` dizia o motivo da
**recusa** — nada dizia o motivo da **permissão**. Um trace agora consegue
responder "quem permitiu isso, e com base em quê" sem reconstruir o estado do
momento.

Duas regras que o booleano antigo não conseguia expressar:

- **Aprovação é por classe.** `approval=True` aprovava mutação local e escrita
  na nuvem de uma vez. Sem escopo, a aprovação dada para uma coisa vale para
  outra.
- **Perfil é teto, não preferência.** `OFFLINE` recusa tool de rede com
  aprovação ou sem. Se aprovação furasse o teto, `OFFLINE` deixaria de
  significar "zero rede" na primeira aprovação distraída.

## Compatibilidade, declarada

`authorize_tool` **continua existindo com a mesma assinatura e a mesma
resposta**. A cadeia entra ao lado, não no lugar: quebrar a assinatura antiga
transformaria uma adição de segurança numa migração, e há chamador hoje.
`tests/test_harness_authorization.py::TestCompatibilidade` tranca isso.

## O que falta, declarado

O hook `PreToolUse` do §41 **não** existe. A cadeia decide; nada a *impõe* fora
do processo Python. Um agente que chame `terraform destroy` por `Bash` não passa
por `authorize()`. O hook é a fase seguinte, e depende desta: hook sem classe de
tool seria uma lista de comandos mantida à mão — a segunda tabela que esta fase
existe para não criar.
