# Coleta na AWS: trazer os artefatos da conta

Os verbos `analyze` leem arquivos locais. Os verbos `collect` são os que buscam
esses arquivos na sua conta AWS: event log, definição do job, métricas,
permissões, dumps de EMR. Cada coleta grava um arquivo em
`.sparkforge/artifacts/<tipo>/` e registra no manifesto um sha256 e o comando
exato para coletar de novo.

> **Atenção: coleta lê a sua conta AWS real.** Use uma credencial **só de
> leitura**. Os coletores só leem (nenhum grava em S3, muda job ou mexe em
> tabela), mas o artefato pode conter dado de negócio. Nunca faça commit de
> `.sparkforge/artifacts/`, exceto do `manifest.json`.

## Receita rápida

```bash
# 1. Instale o extra que traz o boto3 (o SDK da AWS para Python)
pip install -e ".[aws]"            # a partir do código-fonte
# ou: pip install "sparkforge-aws[aws]"

# 2. Aponte para uma credencial de LEITURA (qualquer forma que o boto3 aceita)
export AWS_PROFILE=leitura

# 3. Colete (exemplo: permissões do Lake Formation de uma tabela)
sparkforge collect lakeformation --repo . --database curated --table fato_venda \
  --catalog-id 222222222222 --resource-arn arn:aws:s3:::meu-bucket/curated/fato_venda \
  --now 2026-09-13T12:00:00Z

# 4. Confira que o que está no disco bate com o manifesto
sparkforge collect verify --repo .

# 5. Extraia os facts do artefato coletado
sparkforge analyze lakeformation-grants --path .sparkforge/artifacts/lakeformation/ \
  --out .sparkforge/facts_lf.json
```

Os nomes de banco, tabela, conta e bucket acima são exemplos: troque pelos
seus. Os passos 1, 2, 3 e 5 dependem da sua conta e não têm saída mostrada
aqui. O passo 4 tem exemplo real mais abaixo.

## Palavras que aparecem aqui

- **Artefato**: o arquivo bruto que veio da AWS (um JSON, um event log).
- **Manifesto**: o arquivo `.sparkforge/artifacts/manifest.json`. Ele lista cada
  artefato com o hash e o comando para recoletar.
- **sha256**: uma "impressão digital" do arquivo. Se um byte mudar, o sha256
  muda.
- **boto3**: a biblioteca oficial da AWS para Python. Os coletores a usam.
- **Cadeia padrão de credenciais**: a ordem em que o boto3 procura a credencial
  (variáveis de ambiente, perfil em `~/.aws`, role da máquina e outras).
- **Credencial de leitura**: uma identidade IAM que só tem permissões de
  consulta (`Get*`, `List*`, `Describe*`).

## Para que serve

- Trazer para a sua máquina tudo o que os `analyze` precisam, com um comando
  por artefato.
- Registrar **como** cada artefato foi obtido, para qualquer pessoa (ou outra
  ferramenta) recoletar igual.
- Detectar arquivo alterado ou faltando, pelo sha256.

## Quando usar e quando não usar

Use quando você tem acesso de leitura à conta e quer os artefatos reais do job.

Não use:

- sem credencial, ou com credencial de escrita "porque é mais fácil";
- em CI de pull request: coleta depende da conta e da hora, e o resultado não é
  um veredito sobre o commit;
- quando você já tem o artefato (por exemplo baixado pelo console ou pela AWS
  CLI). Nesse caso vá direto ao `analyze`.

## Pré-requisitos

- SparkForge instalado com o extra `aws` ([Instalação](../02-instalacao.md)).
- Uma credencial de leitura que o boto3 encontre pela cadeia padrão. O
  SparkForge não tem flag de credencial nem de região: ele usa o que o boto3
  achar.
- Permissão IAM para as chamadas do coletor que você vai usar (tabela abaixo).

## Os coletores

Lista conferida em `sparkforge collect --help`. Todos exigem `--repo` e `--now`.

| Verbo | O que lê na AWS (chamadas da API) | Onde grava | Próximo passo |
|---|---|---|---|
| `collect event-log` | S3: `list_objects_v2`, `get_object` | `.sparkforge/artifacts/eventlog/<job_run>.jsonl` | `analyze event-log --path <arquivo>` |
| `collect glue-job` | Glue: `get_job` | `.sparkforge/artifacts/glue_job/<job>.json` | nenhum extrator: serve para comparar a definição real com o Terraform |
| `collect glue-job-runs` | Glue: `get_job_runs` | `.sparkforge/artifacts/glue_job_run/<job>_<run>.json` | `analyze glue-job-runs --path <dir> --job-name <job>` |
| `collect cloudwatch` | CloudWatch: `get_metric_data` | `.sparkforge/artifacts/cloudwatch/<job>_<run>.json` | `analyze cloudwatch --path <arquivo>` |
| `collect cloudwatch-logs` | CloudWatch Logs: `filter_log_events` | `.sparkforge/artifacts/cloudwatch_logs/<job>_<run>_<grupo>.json` | `analyze cloudwatch-logs --path <arquivo-ou-dir>` |
| `collect iceberg-metadata` | Athena: `start_query_execution`, `get_query_execution`, `get_query_results` | `.sparkforge/artifacts/iceberg/<db>_<tabela>.json` | `analyze iceberg --path <arquivo-ou-dir>` |
| `collect athena-workgroup` | Athena: `get_work_group` | `.sparkforge/artifacts/athena/<workgroup>.json` | `analyze athena-workgroup --path <arquivo-ou-dir>` |
| `collect lakeformation` | Lake Formation: `list_permissions`, `describe_resource`, `get_data_lake_settings` | `.sparkforge/artifacts/lakeformation/<conta>_<db>_<tabela>.json` | `analyze lakeformation-grants --path <arquivo-ou-dir>` |
| `collect iam-access` | IAM: `simulate_principal_policy` | `.sparkforge/artifacts/iam_access/<conta>_<role>.json` | `analyze iam-access --path <arquivo-ou-dir>` |
| `collect glue-resource-link` | Glue: `get_table` ou `get_database` (no link e na origem) | `.sparkforge/artifacts/glue_resource_link/<conta>_<db>[_<tabela>].json` | `analyze glue-resource-link --path <arquivo-ou-dir>` |
| `collect emr-cluster` | EMR: `describe_cluster`, `list_instance_groups`, `list_instance_fleets`, `list_bootstrap_actions`, `get_managed_scaling_policy`, `get_auto_termination_policy` | `.sparkforge/artifacts/emr/<cluster_id>.json` | `analyze emr-cluster --path <arquivo-ou-dir>` |
| `collect emr-serverless` | EMR Serverless: `get_application` | `.sparkforge/artifacts/emr_serverless/<application_id>.json` | `analyze emr-serverless --path <arquivo-ou-dir>` |
| `collect emr-eks` | EMR on EKS (`emr-containers`): `describe_virtual_cluster`, `describe_job_run` | `.sparkforge/artifacts/emr_eks/<virtual_cluster>_<job_run>.json` | `analyze emr-eks --path <arquivo-ou-dir>` |
| `collect verify` | nada: só lê o disco | nada | — |

Nos caminhos de `lakeformation` e `glue-resource-link`, `<conta>` é o
`--catalog-id`; sem ele, o nome usa `local`.

Os nomes da coluna do meio são as operações do boto3 que o código chama
(`sparkforge/collect/`). A permissão IAM da credencial precisa cobrir cada uma.
O repositório **não publica uma policy pronta**; para montar a sua, use a skill
[`aws-iam`](../referencia/skills/aws-iam.md). Três avisos que vêm do próprio
código:

- `collect iceberg-metadata` roda consultas `SELECT` no Athena, e o Athena grava
  o resultado da consulta no `--output-location` que você passar.
- Tabela com filtro de linha ou de célula do Lake Formation faz as metadata
  tables do Iceberg falharem no Athena com `AccessDeniedException`. É uma
  restrição do Athena, não falta de IAM: olhe o Lake Formation.
- `collect iam-access` simula; ele não executa a ação. Bucket policy, key policy
  do KMS e Glue resource policy ficam de fora (veja
  [Lake Formation e acesso](lake-formation-e-acesso.md#o-que-fica-sem-resposta)).

## Passo a passo

### 1. Instalar e apontar a credencial

```bash
pip install -e ".[aws]"
export AWS_PROFILE=leitura
```

Sem o boto3, qualquer `collect` falha com código 2 e diz onde pôr o arquivo se
você baixá-lo à mão. A mensagem começa assim:

```text
boto3 nao disponivel. Instale com `pip install 'sparkforge-aws[aws]'` para usar coletores AWS, ou colete o artefato manualmente (AWS CLI ou console) e registre-o com `sparkforge.collect.register_artifact`.
  Alternativa manual: baixe o artefato (AWS CLI ou console), salve em <repo>/.sparkforge/artifacts/..., e registre com `sparkforge.collect.register_artifact` (kind, sha256, source e o collect_command acima).
```

### 2. Coletar

Cada verbo tem as suas flags. Confira sempre com `--help`. Exemplos com as
flags reais:

```bash
# Event log de um run (o coletor LISTA o prefixo e pega o que existe)
sparkforge collect event-log --repo . --job-run jr_EXEMPLO \
  --bucket meu-bucket-de-logs --prefix sparkui/ --now 2026-09-13T12:00:00Z

# Histórico de runs de um job
sparkforge collect glue-job-runs --repo . --job-name meu-job --max-runs 20 \
  --now 2026-09-13T12:00:00Z

# Log de erro de um run (o log group é obrigatório: cada um tem conteúdo diferente)
sparkforge collect cloudwatch-logs --repo . --job-name meu-job --job-run jr_EXEMPLO \
  --log-group /aws-glue/jobs/error --start 2026-09-13T10:00:00Z --end 2026-09-13T11:00:00Z \
  --now 2026-09-13T12:00:00Z

# Decisão do IAM para a escrita que falhou, contra o recurso real
sparkforge collect iam-access --repo . --role-arn arn:aws:iam::111111111111:role/meu-runtime-role \
  --resource-arn arn:aws:s3:::meu-bucket/curated/* \
  --action s3:PutObject --action kms:GenerateDataKey --now 2026-09-13T12:00:00Z

# Cluster EMR on EC2 (pelo id, nunca pelo nome)
sparkforge collect emr-cluster --repo . --cluster-id j-XXXXXXXXXXXXX --now 2026-09-13T12:00:00Z
```

`--now` é o horário da coleta, em ISO 8601. O SparkForge nunca lê o relógio
sozinho: você declara o horário, e ele fica registrado no manifesto.

A saída de cada `collect` é a entrada do manifesto (com `kind`, `path`,
`sha256`, `source`, `collect_command` e `collected_at`) mais o campo
`cache_hit`.

### 3. Cache: coletar de novo não gasta rede

Se o artefato já está no disco **e** o sha256 bate com o manifesto, o coletor
não chama a AWS. Ele devolve a entrada já registrada, e a saída vem com
`"cache_hit": true` (o `collected_at` é o da coleta original, diferente do
`--now` que você passou). Nesse caso nem o boto3 nem a credencial são usados.

Duas exceções que o código documenta:

- `collect glue-job-runs` sempre pergunta à AWS quais runs existem. O cache
  evita baixar de novo cada run já gravado, e cada run traz o seu `cache_hit`.
  Só runs terminados (`SUCCEEDED`, `FAILED`, `TIMEOUT`, `STOPPED`, `ERROR`) viram
  artefato.
- Se o arquivo mudou no disco, o sha256 não bate e o coletor busca de novo.

### 4. Conferir: `collect verify`

`collect verify` só lê o disco. Numa pasta sem manifesto, a saída real é:

```bash
sparkforge collect verify --repo /tmp/pasta_vazia
```

```json
{
  "total_count": 0,
  "ok_count": 0,
  "missing_count": 0,
  "mismatched_count": 0,
  "artifacts": []
}
```

Com um manifesto de exemplo (um artefato presente e um que ficou faltando),
montado numa pasta temporária a partir de uma fixture:

```json
{
  "total_count": 2,
  "ok_count": 1,
  "missing_count": 1,
  "mismatched_count": 0,
  "artifacts": [
    {
      "kind": "lakeformation",
      "path": ".sparkforge/artifacts/lakeformation/222222222222_curated_fato_venda.json",
      "present": true,
      "hash_matches": true,
      "collect_command": "sparkforge collect lakeformation --repo . --database curated --table fato_venda --catalog-id 222222222222 --now 2026-09-13T12:00:00Z",
      "source": "lakeformation:ListPermissions"
    },
    {
      "kind": "iam_access",
      "path": ".sparkforge/artifacts/iam_access/111111111111_glue-curated.json",
      "present": false,
      "hash_matches": false,
      "collect_command": "sparkforge collect iam-access --repo . --role-arn arn:aws:iam::111111111111:role/glue-curated --now 2026-09-13T12:00:00Z",
      "source": "iam:SimulatePrincipalPolicy"
    }
  ]
}
```

Depois de editar um byte do primeiro arquivo, a mesma verificação passa a
mostrar `"ok_count": 0` e `"mismatched_count": 1`, com `"hash_matches": false`.

Para recuperar um artefato faltando ou alterado, rode **exatamente** o
`collect_command` registrado. Não improvise outro comando.

### 5. Extrair os facts

Com os artefatos no disco, rode o `analyze` da tabela acima e depois o `judge`.
Os manuais por assunto mostram cada um com exemplo:
[Lake Formation e acesso](lake-formation-e-acesso.md),
[Migração de versão](migracao-de-versao.md) (EMR),
[Iceberg e Parquet](iceberg-e-parquet.md), [Job lento](job-lento.md).

## O manifesto

`.sparkforge/artifacts/manifest.json` é uma lista. Cada entrada tem seis campos:

| Campo | O que é |
|---|---|
| `kind` | O tipo do artefato (`event_log`, `lakeformation`, `iam_access`, `emr_cluster`...) |
| `path` | Onde o arquivo está, relativo ao `--repo` |
| `sha256` | A impressão digital do arquivo |
| `source` | De onde veio (por exemplo `iam:SimulatePrincipalPolicy`) |
| `collect_command` | O comando exato para coletar de novo. Nunca fica vazio |
| `collected_at` | O `--now` da coleta |

**Faça commit do `manifest.json` e de mais nada em `.sparkforge/artifacts/`.**
O manifesto é pequeno e diz o que falta e como obter. O artefato bruto pode ter
dado de negócio e centenas de MB. O CI do próprio SparkForge falha se algum
artefato bruto for versionado.

## Como ler o resultado

- **`cache_hit: true`**: nada foi buscado. O artefato local já era o certo.
- **`present: false`**: o arquivo não está no disco. Recolete com o
  `collect_command`.
- **`hash_matches: false` com `present: true`**: o arquivo mudou depois da
  coleta. Não confie nele; recolete.
- **Status dentro do artefato** (`sem_permissao`, `nao_encontrado`,
  `sem_credencial`, `nao_coletado`): alguns coletores (Lake Formation, IAM,
  resource link, CloudWatch Logs) gravam a recusa em vez de falhar. O `analyze`
  depois a transforma em `*.unresolved` com o que destravaria. Isso é
  qualidade: "não consegui ler" nunca vira "não há nada" (veja
  [Recusa nomeada](../01-conceitos.md#recusa-nomeada)).

## Erros comuns

- **`boto3 nao disponivel`.** Faltou o extra: `pip install -e ".[aws]"`.
- **Credencial errada ou expirada.** O coletor falha. Confira com a própria AWS
  CLI qual identidade está ativa antes de coletar.
- **`--catalog-id` esquecido em cross-account** (`lakeformation`,
  `glue-resource-link`). A mesma `db.tabela` existe nas duas contas, e uma coleta
  sobrescreve a outra.
- **`collect emr-serverless` ou `emr-eks` pelo nome.** Os dois exigem o **id**.
- **`cloudwatch-logs` sem `--max-events` num run barulhento.** Quando o teto
  morde, o artefato sai com `truncated: true`. Use `--filter-pattern` para
  declarar o que é relevante.
- **Commit de artefato bruto.** Só o `manifest.json` vai para o git.

## Para ir além

- Skill [`aws-iam`](../referencia/skills/aws-iam.md): montar a policy de leitura
  da credencial de coleta.
- Skill [`aws-sdk-python-usage`](../referencia/skills/aws-sdk-python-usage.md):
  como o boto3 resolve credenciais, sessões e paginação.
- Skill [`diagnose-lakeformation-access`](../referencia/skills/diagnose-lakeformation-access.md):
  a ordem certa dos coletores de governança.
- Referência dos comandos: [`collect`](../referencia/cli/collect.md),
  [`analyze`](../referencia/cli/analyze.md).
- Tools MCP equivalentes, por exemplo
  [`sparkforge_collect_lakeformation`](../referencia/tools/sparkforge_collect_lakeformation.md)
  e [`sparkforge_collect_verify`](../referencia/tools/sparkforge_collect_verify.md).
  A lista completa está em [tools](../referencia/tools/README.md).

## Próximos passos

1. Coletou permissões? Siga em [Lake Formation e acesso](lake-formation-e-acesso.md).
2. Coletou o cluster ou a application EMR? Siga em [Migração de versão](migracao-de-versao.md).
3. Vai retomar a investigação em outra sessão? Veja [Investigação com case](investigacao-com-case.md).
