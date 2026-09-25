# Lake Formation e acesso: quem pode o quê

Este manual responde a uma pergunta: **por que o job lê a tabela e não consegue
escrever?** O SparkForge junta as fontes que respondem (o que o job declara, o
que o código faz com a tabela, o que o Lake Formation concede, o que o IAM
decide e a mensagem de erro) e diz qual delas barrou a operação. Quando o log
traz "Insufficient Lake Formation permission(s)", ele diz também **qual
permissão falta**. Quando uma parte não foi medida, ele diz isso em vez de
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
- Descobrir **qual permissão falta** quando o job falhou com "Insufficient Lake
  Formation permission(s)". A mensagem nomeia a tabela e não a permissão; a
  permissão sai da operação que o código faz e do modelo de acesso do job (veja
  [a seção própria](#insufficient-lake-formation-permissions-qual-permissão-falta)).
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
a ordem importa. O quinto (resource link) entra quando há outra conta no meio. O
sexto (o código do job) entra quando a pergunta é qual permissão falta, porque é
a operação que decide o que o grant precisa ter.

| Pergunta | Coleta (conta real) | Análise (arquivo local) |
|---|---|---|
| 1. O que o job **declara**: FGAC, FTA, catálogo, filesystem | não precisa: é o seu Terraform | `analyze terraform` e depois `fuse` |
| 2. O que a **tabela e a conta** respondem | `collect lakeformation` | `analyze lakeformation-grants` |
| 3. O que o **IAM decide**, simulado | `collect iam-access` | `analyze iam-access` |
| 4. A **mensagem exata** da falha | `collect cloudwatch-logs` | `analyze cloudwatch-logs` e depois `analyze error-signatures` |
| 5. Se o **resource link** aponta certo | `collect glue-resource-link` | `analyze glue-resource-link` |
| 6. A **operação** que o código faz sobre a tabela (ler, escrever, sobrescrever, criar) | não precisa: é o seu código | `analyze pyspark` (e `analyze sql` para `.sql` ou `--from-pyspark`) |

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
    "lakeformation.fta_declared": 1,
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

`SF-LF-011`, a regra que nomeia a permissão que falta, não aparece aqui. Ela
exige a falha observada no log e a operação que o código faz, e este exemplo não
tem nenhuma das duas. O caminho em que ela dispara está em
[qual permissão falta](#insufficient-lake-formation-permissions-qual-permissão-falta).

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

A perna `lf_grant` deste exemplo confere se o grant tem `SELECT` ou `ALL`, e só
isso. Quando o case traz o fact `lakeformation.missing_grant` do lado do Lake
Formation para o mesmo principal e a mesma tabela, a perna passa a usar a
operação que o código faz e diz o que faltou para ela (por exemplo, `"falta
write: ALL"`). Esse fact só existe na saída do `fuse`, então o grafo precisa
receber o arquivo fundido. O caminho completo está em
[qual permissão falta](#insufficient-lake-formation-permissions-qual-permissão-falta).

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

## Insufficient Lake Formation permission(s): qual permissão falta

A mensagem `Insufficient Lake Formation permission(s) on <tabela>` nomeia a
tabela, mas não diz qual permissão faltou. O SparkForge chega à permissão por
outro caminho: casa a mensagem com a assinatura `ERR-LF-001`, lê no código a
operação que o job faz sobre aquela tabela, lê no Terraform o modelo de acesso
(FTA ou FGAC) e compara o que a operação exige com o que foi medido. O resultado
é o fact `lakeformation.missing_grant`, que o `fuse` deriva, e a regra
`SF-LF-011`, que o `judge` dispara sobre ele.

Sem `ERR-LF-001` no case, o fact não nasce: sem falha observada, não há
permissão ausente a afirmar. As outras assinaturas de Lake Formation
(`ERR-LF-002` a `ERR-LF-005`) nomeiam ação de IAM ou validação de segurança e
têm regras próprias.

### O que cada operação exige

A tabela mora em
[`knowledge/glue/lakeformation-permissions.yaml`](../../../knowledge/glue/lakeformation-permissions.yaml),
e cada linha cita a página da AWS e a frase literal que a sustenta.

| Operação no código | Modelo | Lado cobrado | Exige |
|---|---|---|---|
| leitura | FTA ou FGAC | Lake Formation (`side: lf`) | `SELECT` no grant |
| escrita (append ou modo default) e sobrescrita | FTA | Lake Formation (`side: lf`) | `ALL` no grant, e não `INSERT`: *"AWS Glue Spark jobs that write/delete data in Amazon S3 require AWS Lake Formation ALL permission."* |
| escrita e sobrescrita | FGAC | IAM do runtime role (`side: iam`) | `s3:PutObject` e `s3:DeleteObject` no prefixo da tabela |
| `CREATE TABLE` | FTA | Lake Formation | `CREATE_TABLE` no **database**, que o coletor não lê: sai recusado |

Sob FGAC a escrita cobra o IAM porque é ele que autoriza a escrita nesse modelo
(*"Writing to a Lake Formation table uses IAM permission rather than Lake
Formation granted permissions."*). As duas ações vêm da página de permissões
mínimas de job ETL do Glue, que não separa append de overwrite; por isso as duas
escritas exigem o mesmo par. A mesma página nomeia `s3:ListBucket`, que é ação de
bucket e que a simulação no prefixo não responde, e o KMS também não é simulado.
Os dois saem no campo `unchecked` do fact, como não conferidos. Combinação de
operação e modelo sem linha na tabela sai recusada como
`operacao_sem_requisito_declarado`.

A operação sai do código. No PySpark, `spark.read` é leitura e `df.write` é
escrita; o modo `overwrite` (ou `overwritePartitions`) vira sobrescrita, e o resto
vira escrita. No SQL (`analyze sql`), `INSERT INTO`, `MERGE` e `UPDATE` são
escrita, `INSERT OVERWRITE` e `DELETE` são sobrescrita, e `CREATE TABLE` é criação.

### Como o modo de escrita é lido

O extrator de PySpark lê o modo de `.mode("...")`, de `mode=` no terminal
(`saveAsTable(t, mode="overwrite")`), de `.mode(saveMode="...")` e de
`insertInto(t, overwrite=True)`. Com mais de um `.mode()` na cadeia, vale o
último, como no Spark. Quando o modo vem de uma variável ou de argumento
desempacotado (`**opts`), o fact de escrita sai com `mode_unresolved: true`, e o
SparkForge não presume append.

Na prática, com a tabela atual isso não esconde nada: append e overwrite exigem o
mesmo conjunto nos dois modelos, então a falta é acusada assim mesmo, e o fact
leva `mode_unresolved: true` para dizer que o modo não foi lido.

O modo lido também muda `SF-GLUE-004` ("MaxRetries maior que zero em job com
escrita não idempotente"). Ela passa a disparar em `insertInto(t, overwrite=False)`
e em `mode="append"`, e deixa de disparar em `.mode("append").save(p, **opts)`,
porque ali `**opts` pode trazer outro modo.

### O caminho de ponta a ponta, com arquivos de exemplo

O exemplo usa a fixture
`fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all`: um job sob Full Table
Access que faz append em `analytics.dim_cliente`, cujo role só tem `DESCRIBE` e
`SELECT` no grant, e um log com a mensagem de permissão insuficiente.

```bash
F=fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all/input
mkdir -p /tmp/sf

# 1. A operação que o código faz sobre a tabela
sparkforge analyze pyspark --path $F/job.py --out /tmp/sf/facts_code.json

# 2. O modelo de acesso (FTA ou FGAC) e a versão do Glue, do Terraform
sparkforge analyze terraform --path $F/main.tf --out /tmp/sf/facts_tf.json

# 3. O grant do role e o registro da localização
sparkforge analyze lakeformation-grants --path $F/lf --out /tmp/sf/facts_lf.json

# 4. A mensagem do log, e a assinatura que ela casa
sparkforge analyze cloudwatch-logs --path $F/logs --out /tmp/sf/facts_logs.json
sparkforge analyze error-signatures --facts /tmp/sf/facts_logs.json --out /tmp/sf/facts_err.json

# 5. Juntar tudo: é aqui que o lakeformation.missing_grant nasce
sparkforge fuse --facts /tmp/sf/facts_code.json --facts /tmp/sf/facts_tf.json \
  --facts /tmp/sf/facts_lf.json --facts /tmp/sf/facts_logs.json \
  --facts /tmp/sf/facts_err.json --out /tmp/sf/facts_case.json

# 6. Julgar, e ver o caminho de acesso
sparkforge judge --facts /tmp/sf/facts_case.json --glue 5.0
sparkforge lakeformation access-graph --facts /tmp/sf/facts_case.json
```

Sob FGAC, acrescente o arquivo de `analyze iam-access` ao `fuse`: é dele que sai
o lado IAM da escrita.

O `fuse` grava um `lakeformation.missing_grant` com estes campos (trecho do
`--out`):

```json
{"resource": "analytics.dim_cliente", "operation": "write", "model": "fta", "side": "lf",
 "principal": "arn:aws:iam::111111111111:role/glue-fta",
 "requires": ["ALL"], "missing": ["ALL"], "granted": ["DESCRIBE", "SELECT"],
 "source": "https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html",
 "quote": "AWS Glue Spark jobs that write/delete data in Amazon S3 require AWS Lake Formation ALL permission.",
 "signature_id": "ERR-LF-001"}
```

O `judge` devolve um finding:

| Regra | Severidade | Título |
|---|---|---|
| SF-LF-011 | P1 | O job falhou por permissão do Lake Formation, e a permissão que a operação exige não está no grant medido (ou na decisão de IAM, sob FGAC) |

`SF-LF-010` (localização registrada sem modelo de acesso declarado) **não** dispara: o
job declara FTA. FTA não tem argumento de job, e por isso não produz
`lakeformation.access_model`; o pedido de FTA é o resolver de credencial, que o `fuse`
grava como `lakeformation.fta_declared`. A regra pergunta pela ausência dos dois. Um
job que só troque `spark.hadoop.fs.s3.impl`, sem o resolver, continua acusado.

No grafo, a perna `lf_grant` sai assim:

```json
{ "target_node": "lakeformation:analytics.dim_cliente", "permission_type": "lf_grant",
  "status": "missing", "evidence": "grant medido nao cobre a operacao -- falta write: ALL" }
```

A contraprova é a fixture `fixtures/cloudwatch_logs/lf_negado_fta_grant_all`: o
mesmo log e o mesmo código, com `ALL` no grant. Ali o `fuse` não produz
`lakeformation.missing_grant` nem recusa, e o `judge` não devolve finding nenhum.

### O mesmo caminho na sua conta

Os coletores gravam em `.sparkforge/artifacts/` (veja
[Coleta na AWS](coleta-na-aws.md)). Os valores entre `<` e `>` são do seu job.

```bash
# A mensagem da falha
sparkforge collect cloudwatch-logs --repo . --job-name <job> --job-run <job-run-id> \
  --log-group /aws-glue/jobs/error --start <inicio-iso> --end <fim-iso> --now <agora-iso>

# O grant e o registro. --resource-arn é a localização da PRÓPRIA tabela, não o bucket
sparkforge collect lakeformation --repo . --database <db> --table <tabela> \
  --resource-arn arn:aws:s3:::<bucket>/<prefixo-da-tabela> --now <agora-iso>

# Só sob FGAC, na escrita: a decisão de IAM no prefixo de objetos da tabela
sparkforge collect iam-access --repo . --role-arn <runtime-role-arn> \
  --action s3:PutObject --action s3:DeleteObject \
  --resource-arn 'arn:aws:s3:::<bucket>/<prefixo-da-tabela>/*' --now <agora-iso>
```

Sob FTA, a coleta de IAM é opcional. Ela ainda ajuda, porque é a decisão de IAM
que diz qual é o role do job quando a tabela tem grant para mais de um principal
(sem ela, a recusa é `principal_ambiguo`). Se você não coletar, tire
`facts_iam.json` da lista do `fuse` abaixo.

Depois, analise cada diretório, junte tudo no `fuse` e julgue:

```bash
sparkforge analyze pyspark --path <job.py> --out facts_code.json
sparkforge analyze terraform --path <diretorio-do-terraform> --out facts_tf.json
sparkforge analyze lakeformation-grants --path .sparkforge/artifacts/lakeformation/ --out facts_lf.json
sparkforge analyze iam-access --path .sparkforge/artifacts/iam_access/ --out facts_iam.json
sparkforge analyze cloudwatch-logs --path .sparkforge/artifacts/cloudwatch_logs/ --out facts_logs.json
sparkforge analyze error-signatures --facts facts_logs.json --out facts_err.json
sparkforge fuse --facts facts_code.json --facts facts_tf.json --facts facts_lf.json \
  --facts facts_iam.json --facts facts_logs.json --facts facts_err.json --out facts_case.json
sparkforge judge --facts facts_case.json
sparkforge lakeformation access-graph --facts facts_case.json
```

Por que a localização importa tanto: sob FGAC, o fact só aceita como prova sobre
a tabela a decisão de IAM simulada em `<localização>/*`, onde a localização é o
`--resource-arn` que você passou a `collect lakeformation`. Se você passar o
bucket inteiro, uma policy escopada ao prefixo da tabela também nega em
`<bucket>/*`, e a acusação pode apontar uma falta que a tabela não tem.

### O que `SF-LF-011` diz, pelo lado

**Com `side: lf`** (FTA, ou leitura sob FGAC), falta permissão no grant do Lake
Formation. `missing` lista o que falta, `granted` o que o principal tem, e o
conserto é conceder ao principal, sobre a tabela, o que está em `missing`. Sob
FTA isso é `ALL`, que também concede `DROP` e `ALTER`: o raio da concessão é
maior que o da operação, e a regra diz isso no risco. Tabela aberta a
`IAM_ALLOWED_PRINCIPALS` com `ALL` não gera o fact, porque ali quem decide é o
IAM (`SF-LF-008`).

**Com `side: iam`** (escrita sob FGAC, em localização medida como não
registrada), quem negou foi o IAM do runtime role. O fact traz a ação (`action`),
o recurso simulado (`iam_resource`), a decisão (`decision`) e a camada que negou
(`denied_by`). Só com `denied_by: implicit_deny` acrescentar uma statement
resolve; com `explicit_deny`, `permissions_boundary` ou `service_control_policy`,
é preciso achar a negação e decidir se ela sai. Uma decisão só acusa quando fala
pela tabela: `implicitDeny` exatamente em `<localização>/*`, ou `explicitDeny` num
recurso que contém a tabela. Negação implícita em `*`, no bucket ou num objeto
não acusa, porque uma policy escopada à tabela também nega ali.

O fact do lado IAM carrega mais três campos que você precisa ler antes de mexer
na policy:

- `registration_scope: exact_arn` e `caveat`: o `registered: false` veio do ARN
  exato da localização, e registro num prefixo pai não foi conferido. Se ele
  existir, o caso é o [conflito declarado](#escrita-em-tabela-registrada-sob-fgac-um-conflito-declarado),
  e não falta de IAM.
- `unchecked`: `s3:ListBucket` e KMS, que o fact não conferiu.

A regra não afirma que o job passa depois do conserto: RAM, key policy do KMS e
bucket policy não têm coletor. Para validar, recolete, rode o `fuse` de novo e
confira que o `lakeformation.missing_grant` da tabela sumiu; depois, reexecute o
job e confira que `ERR-LF-001` saiu do log.

### As recusas que você pode ver

Quando falta um pedaço, o `fuse` grava `lakeformation.missing_grant.unresolved`
com `reason` e `unblocked_by`, e `SF-LF-011` não dispara. As razões, agrupadas
pelo pedaço que falta:

| Razão | O que quer dizer | O que fazer |
|---|---|---|
| `recurso_nao_nomeado` | A mensagem não nomeia tabela, e o case não tem grant nem registro de onde inferir | `collect lakeformation` sobre a tabela da falha |
| `recurso_ambiguo` | Mais de uma tabela coletada serve para a mensagem (nome sem database, ou sem o catálogo que as separa) | Colete só a tabela da falha |
| `recurso_nao_lido` | A mensagem nomeia o recurso numa forma que o extrator não lê | Confira a mensagem no log; o fact não presume a tabela |
| `recurso_nao_e_tabela` | A mensagem nomeia uma localização S3 ou um ARN, não uma tabela | O fact só cobre grant de tabela |
| `trecho_truncado` | O matcher guarda 200 caracteres da mensagem, e o corte pode ter caído no nome da tabela | Colete a mensagem inteira do log |
| `operacao_nao_medida` | Nenhum fact de operação no case | `analyze pyspark` sobre o código do job, e junte a saída ao `fuse` |
| `operacao_nao_ligada_ao_recurso` | O código lê ou escreve outros alvos literais, e nenhum é a tabela da mensagem | Confira se o alvo vem de variável |
| `operacao_com_alvo_nao_resolvido` | Uma operação tem alvo em variável, que o extrator não resolve | Torne o alvo literal, ou confira à mão |
| `terminal_de_escrita_nao_medido` | Escrita sem modo cujo terminal não é lido: `writeTo` sem modo, ou `write` e `writeTo` na mesma cadeia | Confira a operação à mão |
| `modo_de_escrita_nao_lido` | O modo vem de expressão que o parse não lê, e só o overwrite pediria mais do que o write | Torne o modo literal e rode `analyze pyspark` de novo |
| `modelo_ausente` | Nenhum modelo de acesso declarado | `analyze terraform` sobre o job (argumento de FGAC ou as confs de FTA) |
| `modelo_both` | O job declara FGAC e FTA juntos, e a AWS não permite | Decida o modelo antes (`SF-LF-005`) |
| `grant_nao_coletado` | Nenhum grant da tabela no case | `collect lakeformation` sobre ela |
| `catalogo_ambiguo` | Grants da mesma tabela em mais de um catálogo | Colete só o catálogo da falha (`--catalog-id`) |
| `principal_nao_coletado` | Sem decisão de IAM e sem grant de principal nomeado: nada diz qual é o role do job | `collect iam-access` para o runtime role |
| `principal_ambiguo` | Mais de um role nas decisões de IAM, ou grants de vários principais sem decisão nenhuma | `collect iam-access` só para o runtime role |
| `permissao_de_database_nao_coletada` | `CREATE TABLE` exige permissão no database, e o coletor lê grant de tabela | Confira o grant do database à mão |
| `operacao_sem_requisito_declarado` | A tabela de permissões não tem linha para esta operação neste modelo | Nada é afirmado sem fonte |
| `fta_escrita_em_alvo_nao_registrado` | Sob FTA, tabela não registrada é escrita pela credencial do runtime role, e não pelo grant | `collect iam-access` com `s3:PutObject` sobre o alvo |
| `runtime_ausente` | A escrita sob FGAC depende da versão do Glue, e o case não a tem | `analyze terraform` sobre um job com `glue_version` literal |
| `runtime_divergente` | O case observa mais de uma versão de Glue | Resolva a divergência antes |
| `runtime_sem_celula_na_matriz` | A matriz de versão não declara escrita sob FGAC para esta versão | Nada é afirmado sem a página de migração lida |
| `escrita_fgac_nao_suportada_no_runtime` | A matriz diz que esta versão não escreve sob FGAC Spark-native (hoje, o Glue 5.0) | A causa é versão, não permissão |
| `fgac_spark_native_inexistente_no_runtime` | A matriz diz que o modelo FGAC Spark-native não existia nesta versão (hoje, o Glue 4.0) | A causa é versão, não permissão |
| `registro_nao_coletado` | Sob FGAC, sem saber se a tabela é registrada, o lado IAM não é cobrado | `collect lakeformation` com `--resource-arn` na localização da tabela |
| `conflito_declarado_fgac_escrita_registrada` | Escrita sob FGAC em localização registrada | É o [conflito declarado](#escrita-em-tabela-registrada-sob-fgac-um-conflito-declarado): nenhuma saída é escolhida por você |
| `recurso_iam_nao_ligado_a_tabela` | O case não dá a localização da tabela (registro sem `resource_arn`, ou dois diferentes) | `collect lakeformation --resource-arn <localização>` e `collect iam-access --resource-arn '<localização>/*'` |
| `acao_iam_nao_simulada` | A ação exigida não foi simulada para o role do job em `<localização>/*` | `collect iam-access` com a ação e `--resource-arn '<localização>/*'` |
| `decisao_iam_malformada` | A decisão de IAM não tem `allowed` booleano | Recolete com `collect iam-access` |
| `decisoes_iam_contraditorias` | Duas decisões da mesma ação no mesmo recurso, uma permitida e outra negada, de artefatos diferentes | Recolete numa coleta só |
| `decisao_iam_desconhecida` | A decisão nega com um nome fora de `implicitDeny` e `explicitDeny` | Confira o artefato de `collect iam-access` |

Duas assimetrias que parecem erro e não são. Sob FTA, leitura em tabela não
registrada continua cobrando `SELECT`, e só a escrita recusa com
`fta_escrita_em_alvo_nao_registrado`. E, sob FGAC, o fact liga uma mensagem de
permissão do Lake Formation a uma negação de IAM no S3, embora uma negação de S3
costume aparecer como `AccessDenied` do próprio S3; por isso o título de
`SF-LF-011` não afirma que foi a negação de IAM que produziu a mensagem.

## Como ler o resultado

- **`by_kind`**: quantos facts de cada tipo saíram.
- **`unresolved` e `unresolved_at`**: o que o extrator **não conseguiu medir**,
  com a razão (`sem_permissao`, `policy_de_recurso_nao_avaliada` e outras).
- **`*.unresolved` com `unblocked_by`**: diz exatamente o que fazer para medir.
  Isso é qualidade: o projeto separa "não há problema" de "não consegui olhar"
  (veja [Recusa nomeada](../01-conceitos.md#recusa-nomeada)).
- **`denied_by`** no IAM: `permissions_boundary`, `service_control_policy` ou
  `explicit_deny`. Cada um tem um conserto diferente, e alargar a policy do role
  não resolve nenhum dos três. O quarto valor, `implicit_deny`, quer dizer que
  nenhuma statement permite a ação, e aí acrescentar uma resolve.
- **`refused`** no grafo: o que o verbo se recusou a concluir e por quê.

## O que fica sem resposta

As três primeiras lacunas saem **sempre**, mesmo quando tudo respondeu `ok`. As
três últimas aparecem junto com o fact ou a recusa de permissão que falta que as
carrega:

| Lacuna | Onde aparece | Por quê |
|---|---|---|
| Bucket policy do S3, key policy do KMS, Glue resource policy | `iam.access.unresolved` com `policy_de_recurso_nao_avaliada` | A simulação do IAM avalia só as policies da identidade. Um "permitido" com bucket policy negando ainda falha |
| Compartilhamento AWS RAM | aresta `ram_share` com `status: "unresolved"` | Nenhum coletor lê `ram:GetResourceShares` hoje |
| Key policy do KMS | aresta `kms_decrypt` com `status: "unresolved"` | Nenhum coletor lê `kms:GetKeyPolicy` hoje |
| `s3:ListBucket` e KMS na escrita sob FGAC | campo `unchecked` do `lakeformation.missing_grant` com `side: iam` | `s3:ListBucket` é ação de bucket, e a simulação no prefixo da tabela não a responde; as ações `kms:*` e a key policy não são simuladas |
| Registro num prefixo pai da localização | campo `caveat` do mesmo fact, com `registration_scope: exact_arn` | O coletor confere o registro no ARN exato que você passou em `--resource-arn` |
| Permissão no database (`CREATE TABLE`) | recusa `permissao_de_database_nao_coletada` | `collect lakeformation` coleta grant de tabela |

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
- **Rodar o `access-graph` sobre os arquivos soltos, e não sobre a saída do
  `fuse`.** O `lakeformation.missing_grant` só existe no arquivo fundido; sem
  ele, a perna `lf_grant` continua conferindo só `SELECT` ou `ALL`.
- **Esquecer o `analyze error-signatures`.** O `fuse` só deriva a permissão que
  falta quando recebe a assinatura `ERR-LF-001`, e quem a produz é esse verbo,
  sobre os facts do log. Os facts do log sozinhos não bastam.
- **Esquecer o código.** Sem `analyze pyspark` (ou `analyze sql`) no `fuse`, a
  recusa é `operacao_nao_medida`: a mensagem não diz se o job lia ou escrevia.
- **Passar o bucket inteiro em `--resource-arn` do `collect lakeformation`.** Sob
  FGAC, a decisão de IAM que conta é a de `<localização>/*`, e uma localização
  mais larga que a tabela pode acusar uma falta que a tabela não tem.

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
