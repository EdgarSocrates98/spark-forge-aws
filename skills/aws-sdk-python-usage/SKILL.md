---
name: aws-sdk-python-usage
description: Use quando for escrever código Python que usa serviços AWS via boto3 ou botocore — criar service clients ou resources, configurar sessions e credenciais, tratar erros com ClientError, usar paginators e waiters, transferências S3 e presigned URLs, operações de tabela DynamoDB, ou qualquer configuração de client boto3/botocore. Use sempre que código Python importar boto3 ou botocore, ou quando o usuário perguntar sobre operações AWS em Python.
---

> Não use emojis em nenhum código, comentário ou saída quando esta skill estiver ativa.

# AWS SDK for Python (boto3)

boto3 é o SDK Python de alto nível para AWS. Ele envolve botocore (o SDK de
baixo nível) e fornece duas interfaces distintas: **clients** (baixo nível,
mapeamento 1:1 de API) e **resources** (alto nível, orientado a objetos).
Entender qual usar e quando é essencial.

Os coletores do SparkForge usam boto3 para coletar artefatos AWS (dumps de
`describe-*`, `get-*`, `list-*`) que os extratores offline consomem — esta skill
governa esse código de coleta tanto quanto qualquer código de aplicação.

## Client vs Resource

**Clients** mapeiam diretamente para APIs de serviço AWS. Todo serviço tem um
client. Respostas são dicts plain.

**Resources** fornecem uma interface orientada a objetos com atributos e ações.
Apenas alguns serviços têm resources (S3, DynamoDB, EC2, IAM, SQS, SNS,
CloudFormation, CloudWatch, Glacier). Resources auto-marshal types (especialmente
útil para DynamoDB).

```python
import boto3

# Client - baixo nível, todos os serviços
s3_client = boto3.client("s3")
response = s3_client.list_buckets()
buckets = response["Buckets"]  # dicts plain

# Resource - alto nível, serviços selecionados
s3_resource = boto3.resource("s3")
for bucket in s3_resource.buckets.all():
    print(bucket.name)  # acesso por atributo, não dict keys
```

Use clients quando precisar de cobertura completa de API ou o serviço não tem
interface de resource. Use resources quando existem e simplificam seu código
(especialmente DynamoDB e S3).

## Criação de Session e Client

```python
import boto3

# Sessão default criada implicitamente
client = boto3.client("s3")
resource = boto3.resource("dynamodb")

# Sessão explícita quando precisar customizar como
# clients são criados, usar um profile explícito, etc.
session = boto3.Session(
    profile_name="my-profile",
    region_name="us-west-2",
)
client = session.client("s3")
```

Não crie clients dentro de loops — reutilize uma única instância de client.
Clients são thread safe e podem ser compartilhados entre threads uma vez
instanciados.

## Fazendo chamadas de API

```python
# Client - passe parâmetros como keyword arguments, receba dicts
response = client.get_object(Bucket="my-bucket", Key="my-key")
data = response["Body"].read()

# Resource - use métodos e atributos de objeto
obj = s3_resource.Object("my-bucket", "my-key")
response = obj.get()
data = response["Body"].read()
```

Nomes de parâmetro casam com o casing exato da API AWS, que é tipicamente
PascalCase, não snake_case.

## Tratamento de erros

Só capture exceções quando tiver algo actionable a fazer — retornar um valor
fallback, retryar, tomar um caminho de código diferente. Capturar uma exceção
só para imprimi-la e engoli-la é errado: esconde o erro real e impede chamadores
de reagir. Deixe exceções propagar por default.

Quando capturar, prefira exceções tipadas no client em vez de `ClientError`
genérico com matching de string de código via o atributo `client.exceptions`:

```python
lambda_client = boto3.client("lambda")

def get_function_config(name: str) -> dict | None:
    """Retorna configuração de função, ou None se não existir."""
    try:
        return lambda_client.get_function_configuration(FunctionName=name)
    except lambda_client.exceptions.ResourceNotFoundException:
        return None  # actionable: converte função ausente em None
    # Todo o resto propaga - caller ou main() trata
```

Use `ClientError` genérico apenas como catch-all em um handler de erro de
topo, não em funções de lógica de negócio. Ele vive em botocore, não boto3:

```python
from botocore.exceptions import ClientError

def main() -> int:
    try:
        result = do_the_work()
        print(result)
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

Para a hierarquia completa de erros e exceções botocore, veja
`references/error-handling.md`.

## Estrutura de script

Quando pedir para escrever um script que usa `boto3` ou `botocore`, mantenha `if
__name__ == "__main__"` a uma única chamada de função. Parsing de argumentos,
apresentação de erro e exit codes pertencem a `main()`, não espalhados por
funções de lógica de negócio:

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bucket")
    args = parser.parse_args()

    try:
        do_the_work(args.bucket)
        return 0
    except ClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

Nunca chame `sys.exit()` de uma função de lógica de negócio — isso torna a
função untestable e inutilizável como biblioteca. Levante uma exceção ou
retorne um valor de erro em vez disso, e deixe `main()` decidir como
apresentá-lo.

## Paginação

Nunca faça loop manual com `NextToken` — use paginators. Quando precisar só de
campos específicos, use `.search()` com uma expressão JMESPath para extrair e
achatar através de páginas:

```python
paginator = iam.get_paginator("list_users")
for name in paginator.paginate().search("Users[].UserName"):
    print(name)

# Filtrar e projetar
for arn in paginator.paginate().search("Users[?Path == '/admin/'][].Arn"):
    print(arn)
```

Quando precisar do objeto de resposta completo por item, ou controle por-página
(ex. contar páginas, batchar por página), itere páginas diretamente:

```python
for page in paginator.paginate():
    for user in page.get("Users", []):
        process(user)
```

Para mais detalhes sobre paginação, veja `references/pagination.md`.

## Waiters

Espere um recurso alcançar um estado desejado:

```python
waiter = client.get_waiter("bucket_exists")
waiter.wait(
    Bucket="my-bucket",
    WaiterConfig={"Delay": 5, "MaxAttempts": 20},
)
```

Para mais detalhes sobre waiters, veja `references/waiters.md`.

## Configuração de client

Use `botocore.config.Config` para retries, timeouts e configurações de pool de
conexão, etc.:

```python
from botocore.config import Config

config = Config(
    retries={"total_max_attempts": 2, "mode": "adaptive"},
    connect_timeout=5,
    read_timeout=10,
    max_pool_connections=50,
)
client = boto3.client("s3", config=config)
```

Ao criar configuração custom para um client, veja
`references/configuration.md`.

## Logging

Tanto boto3 quanto botocore usam o módulo `logging` da biblioteca padrão. Você
pode configurar logging através das APIs padrão de `logging`, ou usar helpers
fornecidos por boto3 e botocore por conveniência:

```python
# Rápido: logar todos os detalhes wire-level do botocore para stderr
boto3.set_stream_logger("")  # root logger -- tudo
boto3.set_stream_logger("botocore")  # só botocore

# Botocore, logar todos os detalhes do botocore
import logging

from botocore.session import Session

session = Session()

session.set_stream_logger('botocore', logging.DEBUG)
# OU: Configurar logging para um arquivo.
session.set_file_logger(logging.DEBUG, '/tmp/botocore.log')
```

`set_stream_logger(name, level=logging.DEBUG)` adiciona um `StreamHandler` ao
logger nomeado. Esta é a forma idiomática de obter saída de debug
request/response do SDK.

## Issues comuns

### Issue: localização do import de ClientError

**Errado:** `from boto3.exceptions import ClientError`
**Certo:** `from botocore.exceptions import ClientError`

## Customizações específicas de serviço

Ao escrever qualquer código Python que use os serviços a seguir, você DEVE
carregar estes arquivos de referência adicionais para boas práticas e APIs de
alto nível custom:

* S3 - você DEVE carregar `references/s3.md`.
* Dynamodb - você DEVE carregar `references/dynamodb.md`.

## Referências

* Configuração de client (retries, timeouts, endpoints): `references/configuration.md`
* Credenciais e sessions: `references/credentials.md`
* Padrões de tratamento de erro: `references/error-handling.md`
* Paginação: `references/pagination.md`
* Waiters: `references/waiters.md`
* Transferências S3 e presigned URLs: `references/s3.md`
* Operações DynamoDB: `references/dynamodb.md`

## Referência rápida

| Tarefa | Padrão | Referência |
|---|---|---|
| Criar client | `boto3.client("s3")` ou `session.client(...)` | — |
| Criar resource | `boto3.resource("dynamodb")` (só alguns serviços) | — |
| Erro tipado | `client.exceptions.ResourceNotFoundException` | `references/error-handling.md` |
| Erro genérico topo | `from botocore.exceptions import ClientError` | `references/error-handling.md` |
| Paginar | `client.get_paginator("list_users").paginate()` | `references/pagination.md` |
| Esperar estado | `client.get_waiter("bucket_exists").wait(...)` | `references/waiters.md` |
| Config (retries/timeouts) | `botocore.config.Config(...)` | `references/configuration.md` |
| S3 transfer/presigned | — | `references/s3.md` |
| DynamoDB ops | — | `references/dynamodb.md` |
| Credenciais/sessions | — | `references/credentials.md` |

Cross-referência SparkForge: os coletores que alimentam os extratores offline
(`analyze catalog-schema`, `analyze athena-workgroup`, `analyze emr-cluster`,
etc.) usam boto3 para chamar `GetTables`/`GetTable`, `get_work_group`,
`describe-cluster` e demais APIs de leitura. Esta skill governa esse código de
coleta — sessão explícita com profile/região, `ClientError` de botocore,
paginators em vez de `NextToken` manual.

## Quando NÃO usar

- **SDKs de outras linguagens:** JavaScript (aws-sdk-js-v3), Swift, etc. têm
  skills próprias.
- **AWS CLI direta (shell):** use a sintaxe `aws <service> <command>` das skills
  de serviço; esta skill é código Python.
- **Operações de escrita sem confirmação:** boto3 pode mutar infraestrutura ao
  vivo; esta skill não autoriza escrita sem confirmação explícita do operador.
- **SparkForge `judge`/extratores:** o motor é offline e determinístico; boto3
  é apenas a camada de coleta de artefatos que o alimenta.

## Red flags

- `from boto3.exceptions import ClientError` — errado; é `from
  botocore.exceptions import ClientError`.
- Capturar exceção só para imprimir e engolir — esconde o erro real.
- Loop manual com `NextToken` em vez de paginators.
- Criar clients dentro de loops em vez de reutilizar uma instância.
- Chamar `sys.exit()` de função de lógica de negócio — torna a função untestable.
- Nomes de parâmetro em snake_case em vez de PascalCase da API AWS.
- Escrever código S3 ou DynamoDB sem carregar `references/s3.md` ou
  `references/dynamodb.md`.
- Hardcode de credenciais em vez de profiles/SO env/SSO.

## Não faz

Esta skill é procedimento operacional que pode mutar infraestrutura AWS ao
vivo. Não executa comandos de escrita sem confirmação explícita do operador. Não
despacha como subagente.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-sdk-python-usage`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a fonte
autoritativa dos padrões boto3/botocore e dos `references/` (configuration,
credentials, error-handling, pagination, waiters, s3, dynamodb). Esta é uma
adaptação ao contrato SparkForge (PT-BR, fronteira de manutenção,
não-despachável) e **pode desatualizar** quando a AWS atualizar o SDK. Antes de
reproduzir comando de escrita, confira o upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme a
região e o profile; nenhum número sem `fact_id` (aqui, fact vem do artefato
coletado via boto3, não de inspeção); `validate_output` antes de apresentar;
manutenção destrutiva você **não executa** — recomende, e a confirmação de
escopo **sobe a quem pode ser perguntado**: o operador na sessão, ou o agente
pai que despachou.
