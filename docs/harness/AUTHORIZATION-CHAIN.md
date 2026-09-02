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

Uma segunda tabela mantida à mão seria a família de defeito que a Fase 11c achou
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
o manifesto `path` + `sha2116` que `sparkforge_collect_verify` confere — e cuja
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

### Consequência visível para clientes MCP

`readOnlyHint` não é um campo interno: os sete coletores agora anunciam
`readOnlyHint: false` **no protocolo**. Qualquer host MCP que auto-aprove tools
read-only — comportamento comum, e a razão de o campo existir — passa a **pedir
confirmação** nas sete.

Isso é o efeito pretendido, não um dano colateral: uma tool que grava artefato e
reescreve o livro-razão de integridade não deveria rodar sem alguém saber. Mas é
mudança de comportamento observável fora deste repositório, e por isso está
escrita aqui em vez de descoberta por quem usa. A direção é a segura — mais
confirmação, não menos —, e nenhuma capacidade foi removida.

## Duas classes ficam sem membro, e não são as esperadas

Distribuição depois da correção, derivada executando `tool_class()` sobre as
68 tools:

| classe | tools |
|---|---|
| `READ_ONLY` | 45 |
| `LOCAL_MUTATION` | 14 |
| `CLOUD_MUTATION` | 9 |
| `CLOUD_READ` | 0 |
| `DESTRUCTIVE` | 0 |

O plano previa `CLOUD_MUTATION` e `DESTRUCTIVE` vazias. O número de classes sem
membro continua dois, mas a identidade mudou por inteiro: **não existe hoje uma
única tool que toque a rede sem também escrever em disco**. `CLOUD_READ` é a
classe vazia, e `CLOUD_MUTATION` é onde os oito coletores vivem.

O valor da classificação hoje não é bloquear o que existe — é impedir que uma
tool futura entre sem classe. `tool_class()` levanta `KeyError` para nome
desconhecido em vez de devolver `READ_ONLY`: default permissivo para o que
ninguém declarou é exatamente como uma tool nova passa sem aprovação.

As duas classes sem membro são exercitadas com catálogo sintético, e vale dizer
**o que** cada uma tem coberto, porque "têm teste próprio" é literalmente
verdade e induz leitura falsa:

| classe vazia | classificação | teto `OFFLINE` | aprovação por classe |
|---|---|---|---|
| `CLOUD_READ` | sim | sim | sim, sob perfil sem teto |
| `DESTRUCTIVE` | sim | não se aplica (não é de rede) | sim |

A distinção não é acadêmica. O teto dispara **antes** da checagem de aprovação,
então um teste de `CLOUD_READ` que rode sob `OFFLINE` nunca chega à linha da
aprovação — o `approvals=` dele é decorativo por construção. Teste de mutação
provou o buraco: remover `CLOUD_READ` de `_EXIGEM_APROVACAO` deixava a suíte
inteira verde. O caso sob `ECO` fecha, e é a classe que mais importa cobrir,
porque foi esta fase que a esvaziou e é a mais provável de voltar a ter membro.

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

### A cadeia autorizava um NOME; agora ela vê a CHAMADA

Até a fase J2 `authorize()` não recebia os argumentos da tool: `path`, `bucket` e
`report_path` ficavam fora da decisão **por construção**. Ler
`~/.aws/credentials` é read-only, e a revisão de segurança leu um segredo de
fora do repositório sob perfil `OFFLINE` com a cadeia funcionando exatamente
como especificada.

#### O tamanho do buraco, medido

Extraindo do `inputSchema` de cada tool os parâmetros que nomeiam caminho de
sistema de arquivos, com a classe derivada por `tool_class()`:

| classe | declaram caminho | não declaram |
|---|---|---|
| `READ_ONLY` | 40 | 5 |
| `LOCAL_MUTATION` | 14 | 0 |
| `CLOUD_MUTATION` | 9 | 0 |

Medido: **40** das tools `READ_ONLY` declaram algum argumento de caminho
(`path`, `repo`, `facts_path`, `before`/`after`, `file`, `report_path`,
`findings_path`), e as duas exceções são `sparkforge_rules_lookup`, que só
aceita `category`, `id`, `limit` e `cursor`, e `sparkforge_economy_report`, que
lê o ledger pelo `run_id` e aceita `host_transcript` — nenhum dos dois nomeia
caminho de arquivo. Estendendo às outras classes, o total é
**63** de 67 — as onze `LOCAL_MUTATION` e as nove `CLOUD_MUTATION` declaram
caminho sem exceção. Receber caminho é a forma normal da chamada neste
catálogo, não um caso de borda. As onze tools que a SPEC do `SFCI` propõe
recebem todas caminho, e é o caminho que decide se a chamada é legítima.

#### A decisão

`authorize()` passa a aceitar `arguments: dict | None` e `root: Path | str |
None`, keyword-only, ambos `None` por padrão. Quando os dois vêm, todo valor
de parâmetro que nomeia caminho — string ou lista de strings — tem de resolver
para dentro de `root`, ou a chamada é recusada.

`AuthorizationDecision` ganha `checked_arguments: bool`, e ele não é
decoração. É `True` exatamente quando o confinamento **rodou** — não quando
aprovou, nem quando argumentos foram passados. Sem esse campo, uma decisão
tomada sem `arguments` seria indistinguível de uma que examinou os caminhos e
aprovou, e a combinação que mais importa a quem audita é justamente
`authorized=true` com `checked_arguments=false`: autorizado sem que ninguém
tenha olhado para onde a chamada aponta.

Quatro decisões de projeto, com a razão:

- **A verificação é a última da ordem**, depois da aprovação. As checagens
  anteriores respondem "esta tool, para este agente, sob este perfil"; a do
  argumento responde "esta chamada". Perguntar se o caminho é legítimo antes de
  saber se a tool sequer é legítima trocaria a razão da recusa pela menos
  fundamental das duas. O preço é que uma recusa anterior sai com
  `checked_arguments=false` mesmo tendo recebido argumentos — e isso é verdade,
  não perda.
- **`arguments` sem `root` recusa**, pela mesma disciplina de `tool_class()` e
  do perfil não reconhecido: sem raiz não há confinamento, e "sem confinamento"
  não pode ser o default de quem passou o argumento e esqueceu a raiz.
- **A verificação só recusa, nunca concede.** Caminho perfeito não fura classe,
  teto nem aprovação: uma tool de rede sob `OFFLINE` continua batendo no teto
  com o argumento mais correto do mundo.
- **`~` é recusado antes do confinamento.** O confinamento não expande `~` no
  alvo, então `raiz / "~/.aws/credentials"` cairia dentro da raiz e passaria.
  Nenhum adapter deste repositório expande `~` num argumento de tool hoje
  (busca por `expanduser` em `sparkforge/`: três ocorrências, as três sobre
  raiz de configuração), então a leitura falharia de todo jeito — mas a recusa
  não depende de isso continuar verdade.

#### O algoritmo de confinamento é um só, e agora isso é medido

A verificação **não** foi reimplementada. O algoritmo — resolver o alvo debaixo
de uma raiz já resolvida e recusar o que escapar dela — estava escrito três
vezes quando esta fase começou: `rules/loader.py:safe_catalog_file`,
`knowledge_ref.py:safe_knowledge_file` e, inline, dentro de
`facts/scan.py:iter_source_files`. As duas primeiras eram cópia byte a byte uma
da outra, com só o texto do erro mudando — e o docstring de `knowledge_ref.py`
dizia "espelha o loader na contenção de caminho", o que era verdade e era o
problema: espelho é mantido à mão.

Copiar de novo para a cadeia de autorização seria a quarta cópia, e é a mesma
família de defeito que a fase J0 fechou para o detector de segredo. O algoritmo
mora em `sparkforge/paths.py:resolve_within`, e `safe_catalog_file` e
`safe_knowledge_file` só traduzem o `None` dele na exceção do domínio delas —
comportamento e testes de traversal preservados. `TestConfinamentoEhUmSoAlgoritmo`
cobra que a cadeia e o catálogo recusem e aceitem exatamente os mesmos
caminhos, então a unificação deixou de ser convenção e passou a ser coisa
medida.

A checagem inline de `iter_source_files` **não** foi absorvida, e a razão está
escrita no módulo: ela roda dentro do laço de varredura, sobre uma raiz
resolvida uma única vez fora do laço, e responde "pula este arquivo" em vez de
"recusa esta chamada". Chamar `resolve_within` ali pagaria `resolve()` da raiz
por arquivo visitado — o custo que aquele módulo mede e evita. A sobreposição é
conceitual e está declarada; a fusão seria regressão de desempenho.

#### O que esta fase NÃO fecha

Ver o argumento não **impõe** nada. Nenhum dos quatro caminhos de execução —
`sparkforge/adapters/mcp.py`, `sparkforge/adapters/tools.py`,
`sparkforge/adapters/cli.py`, `sparkforge/agents/supervisor.py` — chama
`authorize()`. A cadeia continua sendo uma função pura que ninguém consulta
antes de executar, então uma tool continua recebendo o caminho que quiserem
passar para ela, e o segredo de fora do repositório continua legível por quem
chamar a tool direto.

> **Superado em `5cc065d`.** O parágrafo acima registra o que a fase J2 não
> fechou e fica como está — é o registro dela. O que mudou depois:
> `sparkforge/adapters/tools.py:call_tool` passou a chamar a cadeia via
> `CallPolicy.decide`, e o despacho é único para as 68 tools, então fechar ali
> cobre `adapters/mcp.py` junto. Ver *A imposição no despacho* abaixo.

Isso é o gap do hook `PreToolUse` do §41, e ele **não** fecha aqui. O que
mudou é que ele deixou de ser bloqueado por uma questão de projeto: a decisão
de "a cadeia passa a receber `arguments` ou o argumento é responsabilidade
exclusiva do hook" está tomada, e é a primeira. Quem escrever o hook tem para
onde delegar.

#### Medido por mutação

Nove mutações aplicadas a uma cópia do repositório em diretório temporário —
nunca no arquivo vivo — contra
`test_harness_authorization.py`, `test_rules_loader.py` e
`test_knowledge_ref.py`: contenção removida de `authorize()`;
`checked_arguments` sempre `True`; `resolve_within` nunca recusando; o
algoritmo compartilhado divergindo de `safe_catalog_file`; lista de caminhos
não percorrida; só o parâmetro `path` verificado; `arguments` sem `root`
passando calado; `~` deixando de ser recusado; `safe_catalog_file` deixando de
usar a função compartilhada.

A primeira rodada pegou oito. A sobrevivente foi `checked_arguments` sempre
`True`, e ela apontou buraco real, não ruído: o ramo da aprovação é o único que
constrói `AuthorizationDecision` direto, sem passar por `recusa()`, e herda o
default do campo — nenhum teste cobria essa combinação, então a decisão podia
afirmar que examinou um argumento que nunca chegou a ver. Com o teste
acrescentado, as nove são pegas.

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

## A imposição no despacho

`sparkforge/adapters/tools.py:call_tool(name, arguments, *, policy=None)` chama
a cadeia antes de despachar. O ponto foi escolhido por ser **único**: as 68
tools passam por ele, e `adapters/mcp.py` o usa, então fechar ali cobre os dois
de uma vez em vez de uma checagem por porta.

A fonte da política é `sparkforge/agents/autonomy.py:CallPolicy`, e
`CallPolicy.from_manifest` tira allowlist e denylist de `AgentManifest`, que já
as declara e valida por schema — nenhuma fonte nova, um carregador para a que
existe.

O nome **não** é `ToolPolicy` porque `CURRENT-HARNESS-GAP.md` já usa esse rótulo
para a classificação do §40, que classifica a *tool*; isto autoriza a *chamada*.

Sem política declarada, o comportamento é o de antes, byte a byte — é a
não-regressão, e ela tem teste próprio. A recusa sai no envelope do repositório
(`error` + `exit_code`), com `error_code: UNAUTHORIZED` e, quando a recusa foi
por classe, `required_approval` ao lado: a frase acionável em `error`, o campo
maquinável separado, como em `CodeIndexError`.

O teste que sustenta isto é `test_politica_que_recusa_impede_o_handler_de_rodar`,
e ele não verifica que veio erro — verifica com espião no `_HANDLERS` que o
handler **não rodou**. Recusa que devolve erro depois de executar não é recusa.

## O que falta, declarado

O hook `PreToolUse` do §41 **não** existe, e a imposição acima não o substitui:
ela vale dentro do processo Python. Um agente que chame `terraform destroy` por
`Bash` continua sem passar por `authorize()`. O hook depende desta cadeia — hook
sem classe de tool seria uma lista de comandos mantida à mão, a segunda tabela
que esta fase existe para não criar.
