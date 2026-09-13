# Lake Formation e acesso: quem pode o quê

Este manual responde a uma pergunta: **por que o job lê a tabela e não consegue
escrever?** O SparkForge junta quatro fontes (o que o job declara, o que o Lake
Formation concede, o que o IAM decide e a mensagem de erro) e diz qual delas
barrou a operação. Quando uma parte não foi medida, ele diz isso em vez de
chutar.

Todos os exemplos usam arquivos sintéticos de `fixtures/` e rodam sem acesso à
AWS.

## Receita rápida

Rode da raiz do repositório. A pasta `/tmp/sf` é só um lugar temporário para as
saídas.

```bash
# 1. O que o Lake Formation concede sobre a tabela
mkdir -p /tmp/sf
sparkforge analyze lakeformation-grants \
  --path fixtures/lakeformation/grant_de_leitura_em_local_registrado/input \
  --out /tmp/sf/facts_lf.json

# 2. O que o IAM decidiu (simulado) para o runtime role do job
sparkforge analyze iam-access \
  --path fixtures/iam_access/escrita_negada_pelo_boundary/input \
  --out /tmp/sf/facts_iam.json

# 3. Julgar os dois juntos contra o catálogo de regras
sparkforge judge --facts /tmp/sf/facts_lf.json --facts /tmp/sf/facts_iam.json --glue 5.1

# 4. Ver o caminho de acesso como um grafo: o que libera, o que barra, o que não foi medido
sparkforge lakeformation access-graph --facts /tmp/sf/facts_lf.json --facts /tmp/sf/facts_iam.json

# 5. Conferir o que a sua versão de Glue suporta
sparkforge lakeformation matrix --runtime 5.1
```

Nesse exemplo o resultado é: o Lake Formation concede `SELECT` ao role, mas o
IAM barra `s3:PutObject` pelo permissions boundary. A escrita falha no IAM, não
no Lake Formation.

Para rodar na sua conta, troque os passos 1 e 2 pelos coletores
(`collect lakeformation` e `collect iam-access`). Veja
[Coleta na AWS](coleta-na-aws.md).

## Palavras que aparecem aqui

- **IAM**: o serviço da AWS que decide o que cada identidade pode fazer.
- **Runtime role**: a identidade IAM com que o job Glue roda.
- **Policy**: o documento que dá ou nega permissões no IAM.
- **Permissions boundary**: um teto de permissões preso ao role. Ele corta o que
  a policy dá, mesmo que a policy diga "permitido".
- **SCP (service control policy)**: uma regra da organização AWS que nega acima
  do role. Nada no role a mostra.
- **Lake Formation**: o serviço da AWS que governa quem acessa as tabelas do
  catálogo de dados.
- **Grant**: uma permissão concedida no Lake Formation (por exemplo `SELECT` ou
  `ALL`) a um principal sobre uma tabela.
- **Localização registrada**: uma pasta do S3 que foi registrada no Lake
  Formation. Aí o acesso ao dado passa pela credencial do Lake Formation.
- **FGAC (fine-grained access control)**: o modelo de controle fino do Lake
  Formation, por linha e coluna.
- **FTA (Full Table Access)**: o outro modelo, por tabela inteira.
- **Resource link**: um atalho no catálogo de uma conta que aponta para uma
  tabela ou banco de outra conta (cross-account).
- **RAM (Resource Access Manager)**: o serviço que compartilha recursos entre
  contas.
- **KMS**: o serviço de chaves de criptografia. A key policy diz quem pode usar
  cada chave.

Termos do próprio projeto (fact, finding, recusa nomeada) estão no
[glossário](../01-conceitos.md#glossário).

## Para que serve

- Descobrir **em qual plano** a operação parou: grant, IAM, credencial ou
  filesystem.
- Descobrir **qual permissão** o IAM negou e **quem** negou (policy, boundary,
  SCP ou deny explícito).
- Conferir se um resource link aponta para o lugar certo.
- Saber o que a sua versão de Glue suporta sob FGAC e FTA.

## Quando usar e quando não usar

Use quando:

- a leitura passa e a escrita falha com `AccessDenied` ou "Insufficient Lake
  Formation permission(s)";
- alguém propõe "trocar `writeTo` por `INSERT INTO`" para resolver erro de Lake
  Formation;
- o job migrou de versão de Glue e o acesso quebrou;
- o job lê tabela de outra conta.

Não use para:

- decidir se um grant é "suficiente" para o negócio. O SparkForge mostra o que
  a AWS respondeu; a regra de negócio é sua;
- avaliar bucket policy do S3, key policy do KMS ou Glue resource policy. Nada
  aqui coleta essas três (veja [O que fica sem resposta](#o-que-fica-sem-resposta)).

## Pré-requisitos

- SparkForge instalado ([Instalação](../02-instalacao.md)).
- Para os exemplos: nada mais.
- Para a sua conta: o extra `aws` e uma credencial de leitura
  ([Coleta na AWS](coleta-na-aws.md)).

## Os artefatos que respondem "quem pode o quê"

A seção 6.1 do [GUIA_DE_USO](../../../GUIA_DE_USO.md) define quatro artefatos, e
a ordem importa. O quinto (resource link) entra quando há outra conta no meio.

| Pergunta | Coleta (conta real) | Análise (arquivo local) |
|---|---|---|
| 1. O que o job **declara**: FGAC, FTA, catálogo, filesystem | não precisa: é o seu Terraform | `analyze terraform` e depois `fuse` |
| 2. O que a **tabela e a conta** respondem | `collect lakeformation` | `analyze lakeformation-grants` |
| 3. O que o **IAM decide**, simulado | `collect iam-access` | `analyze iam-access` |
| 4. A **mensagem exata** da falha | `collect cloudwatch-logs` | `analyze cloudwatch-logs` |
| 5. Se o **resource link** aponta certo | `collect glue-resource-link` | `analyze glue-resource-link` |

## Passo a passo

### 1. O que o job declara (Terraform)

As regras de Lake Formation (`SF-LF-*`) leem facts **derivados**. Quem os
deriva é o `fuse`. Sem ele, o `judge` não vê o modelo de acesso.

```bash
sparkforge analyze terraform \
  --path fixtures/infra_code/fgac_com_fta_no_mesmo_job/input \
  --out /tmp/sf/facts_tf.json
sparkforge fuse --facts /tmp/sf/facts_tf.json --out /tmp/sf/facts_tf_fused.json
sparkforge judge --facts /tmp/sf/facts_tf_fused.json
```

O `fuse` acrescenta os kinds de Lake Formation:

```json
  "by_kind": {
    "fusion.summary": 1,
    "lakeformation.access_model": 1,
    "lakeformation.filesystem": 1,
    "lakeformation.unresolved": 1,
    "tf.attribute": 12,
    ...
```

E o `judge` acha um P0: `SF-LF-005`, "Controle de acesso fino e Full Table
Access declarados no mesmo job". Esse Terraform liga FGAC e, no mesmo `--conf`,
o resolver de credencial do FTA. A AWS proíbe os dois juntos.

Rodar o `judge` direto sobre `facts_tf.json`, sem o `fuse`, devolve
`"total_count": 0`. Não é "está tudo certo": é o `judge` sem os facts de que a
regra precisa.

### 2. O que o Lake Formation concede

```bash
sparkforge analyze lakeformation-grants \
  --path fixtures/lakeformation/grant_de_leitura_em_local_registrado/input \
  --out /tmp/sf/facts_lf.json --detail-level summary
```

Saída (encurtada):

```json
  "by_kind": {
    "lakeformation.grant": 2,
    "lakeformation.grants.analyzed": 1,
    "lakeformation.grants.unresolved": 1,
    "lakeformation.registered_location": 1
  },
  "unresolved": 1,
  "unresolved_at": [
    { "file": "222222222222_curated_fato_venda.json", "line": 0, "reason": "sem_permissao" }
  ],
```

O `--out` grava cada fact inteiro. Dentro dele:

- um `lakeformation.grant` para o role `glue-curated`, com
  `"permissions": ["DESCRIBE", "SELECT"]`;
- um `lakeformation.grant` para `IAM_ALLOWED_PRINCIPALS` com `ALL`. Isso quer
  dizer que o Lake Formation não controla a tabela: quem decide é só o IAM;
- `lakeformation.registered_location` com `"registered": true`;
- `lakeformation.grants.unresolved` com a razão e o que destrava:

```json
{"reason": "sem_permissao", "block": "data_lake_settings",
 "unblocked_by": "conceder `lakeformation:GetDataLakeSettings` ao principal que coleta -- e ele que revela o passo de CONTA que precede qualquer grant sob Full Table Access"}
```

Ou seja: quem coletou não tinha permissão para ler as configurações da conta, e
o resultado diz isso em vez de fingir que não há nada ali.

### 3. O que o IAM decide

```bash
sparkforge analyze iam-access \
  --path fixtures/iam_access/escrita_negada_pelo_boundary/input \
  --out /tmp/sf/facts_iam.json
```

Cada `iam.access_decision` traz a ação, o recurso, a decisão da AWS e **quem**
negou (trecho do `--out`):

```json
{"action": "s3:PutObject", "resource": "arn:aws:s3:::sparkforge-demo/curated/*",
 "decision": "implicitDeny", "allowed": false, "denied_by": "permissions_boundary",
 "scoped_to_resource": true}
{"action": "s3:DeleteObject", "decision": "explicitDeny", "denied_by": "explicit_deny"}
{"action": "kms:GenerateDataKey", "decision": "explicitDeny", "denied_by": "service_control_policy"}
{"action": "glue:GetTable", "decision": "allowed", "allowed": true}
```

`scoped_to_resource: true` quer dizer que a simulação foi feita contra o recurso
real. Se fosse contra `*`, um "permitido" não valeria para o recurso.

### 4. Julgar tudo junto

```bash
sparkforge judge --facts /tmp/sf/facts_lf.json --facts /tmp/sf/facts_iam.json --glue 5.1
```

Resumo real da saída (`total_count: 5`):

| Regra | Severidade | Título |
|---|---|---|
| SF-IAM-001 | P0 | Ação negada pelo permissions boundary do role -- alargar a policy dele não resolve |
| SF-IAM-002 | P0 | Ação negada por service control policy da organização -- a decisão é acima do role |
| SF-IAM-003 | P0 | Ação negada por `Deny` explícito -- acrescentar `Allow` não vence |
| SF-LF-008 | P1 | Tabela concede permissão a `IAM_ALLOWED_PRINCIPALS` -- o controle do Lake Formation não decide nada sobre ela |
| SF-LF-010 | P2 | Tabela com localização registrada, e o job não declara modelo de acesso nenhum |

Cada finding traz explicação, mudança proposta, risco, validação e rollback.

### 5. O grafo de acesso

```bash
sparkforge lakeformation access-graph --facts /tmp/sf/facts_lf.json --facts /tmp/sf/facts_iam.json
```

Saída (encurtada):

```json
{
  "status": "ok",
  "principal_arn": "arn:aws:iam::111111111111:role/glue-curated",
  "target_table": "curated.fato_venda",
  "is_accessible": false,
  "edges": [
    { "target_node": "lakeformation:curated.fato_venda", "permission_type": "lf_grant",
      "status": "granted", "evidence": "grant medido com SELECT ou ALL" },
    { "target_node": "iam:s3:PutObject", "permission_type": "iam", "status": "blocking",
      "evidence": "negado por permissions_boundary sobre arn:aws:s3:::sparkforge-demo/curated/*" },
    { "target_node": "ram:ResourceShare", "permission_type": "ram_share", "status": "unresolved",
      "evidence": "nenhum coletor produz o estado do compartilhamento AWS RAM; destravaria: `ram:GetResourceShares` num coletor novo" },
    ...
  ],
  "counts": { "edges": 8, "granted": 2, "blocked": 3, "unresolved": 3, "not_applicable": 0 },
```

`is_accessible` tem **três** valores: `true`, `false` e `null`. `null` quer
dizer "o que eu olhei não impede", e não "funciona". As flags
`--principal-arn` e `--target-table` escolhem o role e a tabela do caminho.

### 6. Resource link (outra conta)

```bash
sparkforge analyze glue-resource-link \
  --path fixtures/resource_link/link_de_tabela_com_nome_divergente/input \
  --out /tmp/sf/facts_rl.json
sparkforge judge --facts /tmp/sf/facts_rl.json
```

O fact `glue.resource_link` mostra o link `analytics.dim_cliente_prod` na conta
`111111111111` apontando para `curated.dim_cliente` na conta `999999999999`, com
`"name_matches_source": false`. O `judge` acha `SF-XACC-002` (P2), "Resource link
com nome diferente do recurso na conta de origem". A documentação da AWS pede o
mesmo nome dos dois lados.

Quando o coletor não pôde ler o link, o resultado sai assim
(`fixtures/resource_link/link_que_o_coletor_nao_pode_ler`):

```json
  "by_kind": { "glue.resource_link.analyzed": 1, "glue.resource_link.unresolved": 2 },
  "unresolved_at": [
    { "file": "111111111111_analytics_dim_produto.json", "line": 0, "reason": "sem_permissao" },
    { "file": "111111111111_analytics_dim_produto.json", "line": 0, "reason": "sem_alvo_medido_no_link" }
  ],
```

## FGAC ou Full Table Access, e por que a versão muda tudo

Em uma frase: **FGAC e FTA são dois modelos diferentes, e o que muda entre eles
é quem entrega a credencial de acesso ao dado.**

- Sob **FGAC**, a escrita usa o IAM do runtime role.
- Sob **FTA**, a credencial do Lake Formation lê e escreve as tabelas
  registradas. Para escrever, o grant precisa de `ALL`; `SELECT` com `DESCRIBE`
  só dá para ler.
- Os dois **não podem** estar ligados no mesmo job (é o `SF-LF-005` do passo 1).

A versão do Glue muda o que vale. A matriz sai de um comando, com a frase da
documentação por trás de cada célula:

```bash
sparkforge lakeformation matrix --axis fgac_spark_native_write --detail-level summary
```

```json
  "rows": [
    { "glue_version": "4.0", "axis": "fgac_spark_native_write", "status": "not_applicable", "quoted": false },
    { "glue_version": "5.0", "axis": "fgac_spark_native_write", "status": "not_supported", "quoted": true },
    { "glue_version": "5.1", "axis": "fgac_spark_native_write", "status": "supported", "quoted": true }
  ],
```

As três fronteiras que mais enganam (regra 31 do `CLAUDE.md`):

| Mudança | O que acontece |
|---|---|
| Glue 5.0 removeu FGAC via `GlueContext`/DynamicFrame | Job do 4.0 que lia tabela protegida por DynamicFrame precisa passar para DataFrame |
| Glue 5.0 não escrevia sob FGAC; o 5.1 escreve | "FGAC não escreve" sem dizer a versão é erro |
| Glue 5.1 trocou o filesystem S3 padrão de EMRFS para S3A | FTA quebra **sem erro**: a chave `fs.s3.credentialsResolverClass` é do EMRFS e o S3A a ignora |

Sem `--detail-level summary`, cada linha traz a frase citada. Exemplo real do
5.1:

```json
{ "glue_version": "5.1", "axis": "filesystem_s3_default", "status": "supported", "value": "S3A",
  "quote": "S3A filesystem has replaced EMRFS as the default S3 connector",
  "note": "E A CELULA QUE QUEBRA CALADO. `spark.hadoop.fs.s3.credentialsResolverClass` e chave de EMRFS; sob S3A ela e ignorada sem erro e sem aviso. ..." }
```

Versão fora da matriz não vira palpite:

```bash
sparkforge lakeformation matrix --runtime 9.9
```

```json
{
  "status": "unresolved",
  "reason": "runtime_fora_da_matriz",
  "requested_runtime": "9.9",
  "known_runtimes": ["4.0", "5.0", "5.1"],
  "unblocked_by": "Ler a pagina de migracao daquele runtime para o eixo de Lake Formation e acrescentar a coluna em knowledge/glue/lakeformation-matrix.yaml",
  ...
```

### Escrita em tabela registrada sob FGAC: um conflito declarado

A documentação da AWS tem quatro frases sobre isso que não fecham entre si
(regra 32 do `CLAUDE.md`, detalhe na §6 de
[`knowledge/glue/lakeformation-fgac.md`](../../../knowledge/glue/lakeformation-fgac.md)).
O SparkForge não escolhe um lado. Ele apresenta as três saídas que a própria
documentação sustenta:

1. o alvo **não** ser registrado no Lake Formation; aí a escrita é do runtime
   role, e o que resta é `s3:PutObject`, `s3:DeleteObject` e KMS;
2. trocar o job para **FTA**, com `ALL` no grant e EMRFS restaurado no 5.1;
3. **separar** leitura e escrita em dois jobs.

E um aviso: **a API de escrita não é o caminho de autorização.** Se `writeTo`,
`insertInto` e `INSERT INTO` falham juntas, o problema está no catálogo, no
filesystem, na credencial ou na permissão. Trocar a API não muda nada.

## Como ler o resultado

- **`by_kind`**: quantos facts de cada tipo saíram.
- **`unresolved` e `unresolved_at`**: o que o extrator **não conseguiu medir**,
  com a razão (`sem_permissao`, `policy_de_recurso_nao_avaliada` e outras).
- **`*.unresolved` com `unblocked_by`**: diz exatamente o que fazer para medir.
  Isso é qualidade: o projeto separa "não há problema" de "não consegui olhar"
  (veja [Recusa nomeada](../01-conceitos.md#recusa-nomeada)).
- **`denied_by`** no IAM: `permissions_boundary`, `service_control_policy` ou
  `explicit_deny`. Cada um tem um conserto diferente, e alargar a policy do role
  não resolve nenhum dos três.
- **`refused`** no grafo: o que o verbo se recusou a concluir e por quê.

## O que fica sem resposta

Estas lacunas saem **sempre**, mesmo quando tudo respondeu `ok`:

| Lacuna | Onde aparece | Por quê |
|---|---|---|
| Bucket policy do S3, key policy do KMS, Glue resource policy | `iam.access.unresolved` com `policy_de_recurso_nao_avaliada` | A simulação do IAM avalia só as policies da identidade. Um "permitido" com bucket policy negando ainda falha |
| Compartilhamento AWS RAM | aresta `ram_share` com `status: "unresolved"` | Nenhum coletor lê `ram:GetResourceShares` hoje |
| Key policy do KMS | aresta `kms_decrypt` com `status: "unresolved"` | Nenhum coletor lê `kms:GetKeyPolicy` hoje |

Um resource link que resolve **não** prova que o convite do RAM foi aceito.

## Erros comuns

- **`judge` sobre o Terraform devolve zero findings de Lake Formation.** Faltou o
  `fuse` entre o `analyze terraform` e o `judge`.
- **Passar só um arquivo de facts ao `judge`.** Regras que cruzam grant e IAM só
  disparam com os dois na mesma chamada. `--facts` é repetível.
- **Coletar IAM sem `--resource-arn`.** A resposta vira sobre `*`, e não serve
  para o recurso real.
- **Coletar IAM com a lista inteira de ações.** Passe só as da operação que
  falhou (`--action s3:PutObject --action kms:GenerateDataKey`).
- **Esquecer `--catalog-id` em cross-account.** A mesma `db.tabela` existe nas
  duas contas, e uma coleta sobrescreve a outra no manifesto.
- **Aplicar ao Glue 5.1 uma limitação do 5.0.** Rode `lakeformation matrix`
  antes de afirmar.

## Para ir além

- Agent [`sf-lake-formation-specialist`](../referencia/agents/sf-lake-formation-specialist.md):
  conduz o diagnóstico de governança.
- Skill [`diagnose-lakeformation-access`](../referencia/skills/diagnose-lakeformation-access.md):
  a ordem dos quatro coletores, para descobrir **qual** permissão falta.
- Skill [`lakeformation-fgac-guard`](../referencia/skills/lakeformation-fgac-guard.md):
  "esta configuração é suportada sob FGAC?" (JAR extra, UDF, escolha entre FGAC e FTA).
- Skill [`aws-iam`](../referencia/skills/aws-iam.md): policies, roles e trust
  policies no próprio IAM.
- Agent [`sf-security-reviewer`](../referencia/agents/sf-security-reviewer.md):
  IAM, KMS e S3 do ponto de vista de segurança.
- Referência dos comandos: [`analyze`](../referencia/cli/analyze.md),
  [`lakeformation`](../referencia/cli/lakeformation.md),
  [`fuse`](../referencia/cli/fuse.md), [`judge`](../referencia/cli/judge.md).
- Tools MCP equivalentes:
  [`sparkforge_analyze_lakeformation_grants`](../referencia/tools/sparkforge_analyze_lakeformation_grants.md),
  [`sparkforge_analyze_iam_access`](../referencia/tools/sparkforge_analyze_iam_access.md),
  [`sparkforge_analyze_glue_resource_link`](../referencia/tools/sparkforge_analyze_glue_resource_link.md),
  [`sparkforge_lakeformation_access_graph`](../referencia/tools/sparkforge_lakeformation_access_graph.md),
  [`sparkforge_lakeformation_matrix`](../referencia/tools/sparkforge_lakeformation_matrix.md).

## Próximos passos

1. Colete os artefatos da sua conta: [Coleta na AWS](coleta-na-aws.md).
2. Migrando de versão de Glue? Veja [Migração de versão](migracao-de-versao.md).
3. Leve os findings para o pull request: [CI e GitHub](ci-e-github.md).
