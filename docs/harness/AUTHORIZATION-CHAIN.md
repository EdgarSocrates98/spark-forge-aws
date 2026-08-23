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
`tests/test_harness_authorization.py` tranca a derivação — um teste troca a
anotação da mesma tool sintética nas quatro combinações e cobra que a classe
acompanhe, que é o único jeito de distinguir uma derivação de uma tabela paralela
que por acaso concorda.

`ToolClass` **não** se mapeia para `sparkforge/registry/models.py:RiskLevel`, e a
incompatibilidade é de **eixo**, não de granularidade: `RiskLevel`
(`read_only/reversible/sensitive/destructive`) grada o quanto uma mutação dói e
não tem dimensão de rede nenhuma; `ToolClass` cruza "muta?" com "sai da
máquina?" e não tem `reversible` nem `sensitive`. Nenhum dos dois é refinamento
do outro. Não há divergência viva hoje porque `CanonicalRegistry.load_from_configs()`
nunca popula `self.tools` — mas quem tentar a ponte depois vai ter de inventar o
eixo que falta, e inventá-lo sob prazo é como classificação de segurança vira
palpite. A nota está também na docstring de `ToolClass`, que é o arquivo que os
dois leitores abrem.

## Derivar a classe expôs uma anotação que mentia

O primeiro efeito da derivação não foi classificar: foi **pegar um defeito**.

Os sete coletores AWS declaravam `readOnlyHint: True`, com a razão escrita
"nunca mudam estado do lado AWS". A parte depois da vírgula é verdade — eles só
chamam `get_object`, `get_job`, `get_metric_data`, `SELECT`/`get_work_group`. Mas
`readOnlyHint` **não tem lado**: ele afirma que a tool não modifica o ambiente
dela, e os sete modificam o ambiente **local**. Todos terminam em
`sparkforge.collect.aws._write_and_register`, que grava o artefato e depois grava
o manifesto `path` + `sha256` que `sparkforge_collect_verify` confere — e cuja
entrada de mesmo `path` é substituída a cada coleta. Medido executando
`_write_and_register` num diretório vazio: **zero arquivos antes, dois depois**.

A anotação errada tinha consequência de segurança, não cosmética: com
`readOnlyHint: True` os sete caíam em `CLOUD_READ`, e **aprovar leitura de nuvem
concedia escrita local** sem nenhuma aprovação `LOCAL_MUTATION`. Dois testes
travavam a mentira em vez de pegá-la, e foram corrigidos junto
(`tests/test_adapters_tools.py`).

O defeito é anterior a esta fase. Derivar a classe da anotação foi o que o tornou
visível, e isso é o valor da derivação: uma segunda tabela mantida à mão teria
concordado com a anotação errada em silêncio.

## Duas classes ficam sem membro, e não são as esperadas

Distribuição depois da correção, derivada executando `tool_class()` sobre as
44 tools:

| classe | tools |
|---|---|
| `READ_ONLY` | 32 |
| `LOCAL_MUTATION` | 5 |
| `CLOUD_MUTATION` | 7 |
| `CLOUD_READ` | 0 |
| `DESTRUCTIVE` | 0 |

O plano previa `CLOUD_MUTATION` e `DESTRUCTIVE` vazias. O número de classes sem
membro continua dois, mas a identidade mudou por inteiro: **não existe hoje uma
única tool que toque a rede sem também escrever em disco**. `CLOUD_READ` é a
classe vazia, e `CLOUD_MUTATION` é onde os sete coletores vivem.

O valor da classificação hoje não é bloquear o que existe — é impedir que uma
tool futura entre sem classe. `tool_class()` levanta `KeyError` para nome
desconhecido em vez de devolver `READ_ONLY`: default permissivo para o que
ninguém declarou é exatamente como uma tool nova passa sem aprovação. As duas
classes sem membro têm teste próprio, com catálogo sintético — o ramo que
classifica uma tool destrutiva só roda de verdade no dia em que a primeira
entrar, e nesse dia já não há ninguém olhando.

## O que a cadeia acrescenta

`AuthorizationDecision` carrega o agente, o perfil e a aprovação que sustentou a
decisão. `authorize_tool` respondia `(bool, str)`, e o `str` dizia o motivo da
**recusa** — nada dizia o motivo da **permissão**. Um trace agora consegue
responder "quem permitiu isso, e com base em quê" sem reconstruir o estado do
momento.

Quatro regras que o booleano antigo não conseguia expressar:

- **Aprovação é por classe.** `approval=True` aprovava mutação local e escrita
  na nuvem de uma vez. Sem escopo, a aprovação dada para uma coisa vale para
  outra.
- **Perfil é teto, não preferência.** `OFFLINE` recusa tool de rede com
  aprovação ou sem. Se aprovação furasse o teto, `OFFLINE` deixaria de
  significar "zero rede" na primeira aprovação distraída.
- **Perfil não reconhecido recusa.** Mesma disciplina de `tool_class()`: sem
  perfil não há teto, e "sem teto" não pode ser o default de quem escreveu o
  nome errado.
- **Deny vence allow.** `AgentManifest` declara `denied_tools` ao lado de
  `allowed_tools` e valida as duas por schema; uma denylist que a cadeia
  ignorasse em silêncio seria pior que denylist nenhuma, porque quem a escreve
  acredita que ela morde.

### O teto falhava aberto, e o modo da falha era silencioso

A primeira versão desta fase comparava `profile == "OFFLINE"`. O tipo canônico do
repositório é `ExecutionProfile`, e o valor dele é **minúsculo**
(`OFFLINE = "offline"`). Por ser `str, Enum`, o valor canônico atravessava a
anotação `profile: str` sem erro de tipo e comparava `False` — o teto sumia, e a
decisão saía gravada como `reason="autorizado"`, **indistinguível de aprovação
legítima**. O caminho não era hipotético: `sparkforge/economy/router.py` já
compara `profile == ExecutionProfile.OFFLINE` e `RoutingDecision.profile` é
tipado `ExecutionProfile`, então o wiring óbvio desligava o teto.

O teste da época passava `"OFFLINE"` em maiúscula — a única grafia que
funcionava. Ele trancava o literal, não o conceito, e ficava verde com a
integração quebrada. Hoje `authorize()` normaliza contra `ExecutionProfile` e
recusa o que não nomeia perfil nenhum, e o teste exercita o enum, a grafia
canônica e o perfil inexistente.

### O que a cadeia autoriza é um NOME, nunca uma CHAMADA

Limite de granularidade desta fase, declarado porque tem consequência:
`authorize()` não recebe os argumentos da tool. `path`, `bucket` e `report_path`
estão fora da decisão **por construção**.

Medido: as 32 tools `READ_ONLY` aceitam `path` arbitrário, e ler
`~/.aws/credentials` é read-only. A revisão desta fase conseguiu ler um segredo
de fora do repositório sob perfil `OFFLINE`, com a cadeia funcionando exatamente
como especificada.

Isto **não** é consertável dentro da assinatura atual, e não há solução inventada
aqui. A consequência que precisa estar escrita é a direção: um hook `PreToolUse`
vê argumentos, e `authorize()` não tem onde recebê-los. Quem fechar o §41 vai ter
de decidir se a cadeia passa a receber `arguments` ou se o argumento é
responsabilidade exclusiva do hook — e essa decisão é de projeto, não refactor.

## Compatibilidade, declarada

`authorize_tool` **continua existindo com a mesma assinatura e a mesma
resposta**. A cadeia entra ao lado, não no lugar: quebrar a assinatura antiga
transformaria uma adição de segurança numa migração.
`tests/test_harness_authorization.py::TestCompatibilidade` tranca isso.

A razão de manter é ser **superfície pública** — `authorize_tool` é método de
`AutonomyController`, que `sparkforge.agents.__all__` exporta. O que a razão
**não** é: consumidor interno. Este documento afirmava "e há chamador hoje", e
isso era falso. Busca exaustiva: os únicos chamadores são
`tests/test_agent_autonomy.py` e o próprio teste de compatibilidade — **zero em
produção**. A decisão de não quebrar continua certa pelo argumento de API
pública; a afirmação de fato que a acompanhava não era verdade e foi corrigida.

## O que falta, declarado

O hook `PreToolUse` do §41 **não** existe. A cadeia decide; nada a *impõe* fora
do processo Python. Um agente que chame `terraform destroy` por `Bash` não passa
por `authorize()`. O hook é a fase seguinte, e depende desta: hook sem classe de
tool seria uma lista de comandos mantida à mão — a segunda tabela que esta fase
existe para não criar.
