# Forge Lab / Digital Twin

O Forge Lab é a fábrica de evidências reproduzíveis do SparkForge para projetos
streaming e batch. Ele transforma um cenário declarativo em um plano de ações
allowlisted, permite execução local explicitamente autorizada, captura artefatos
com hash e compara o resultado com um oracle independente.

O produto está fechado em `docs/sdd/FORGE_LAB_PRODUCT/` e o contrato detalhado
fica em [`docs/knowledge/forge-lab-product.md`](../knowledge/forge-lab-product.md).

## O que foi entregue

- Registry versionado em `lab/versions.yaml`, sem `latest` e com digest exigido
  para uma execução real.
- DSL declarativa no Golden 20 (`lab/scenarios/golden.yaml`), com dataset,
  workload, topologia, fault, observações, fatos esperados, findings proibidos,
  unresolved e plano experimental.
- Geradores determinísticos separados de workload e taxa de chegada: seed,
  schema, cardinalidade, skew, eventos atrasados e duplicidades são controláveis.
- Backends Compose e Testcontainers consumindo o mesmo cenário e o mesmo plano
  de ações.
- Perfis para core, Spark, Kafka, streaming, Flink, lakehouse, CDC, Polaris,
  observabilidade, chaos e full.
- Evidências de Spark, Kafka, Flink, Iceberg, CDC, Prometheus/OTel e runtime,
  com `run.json`, `environment.json`, `versions.json`, facts, findings e receipt
  content-addressed.
- Oracle independente: o resultado observado nunca gera o expected golden.
- Plano de equivalência Spark/Flink/Trino/DuckDB e compatibilidade explicitamente
  `declared_unmeasured` até existir receipt de execução.
- Tier AWS L3 com região, owner, TTL, budget, prefixo, tags, confirmação e
  política de cleanup obrigatórios.
- CLI completa para doctor, profiles, scenarios, verify, describe, plan, run,
  inspect, analyze, compare, promote-fixture, reproduce e lifecycle.

## Estado verificável

`lab verify` é o smoke test offline do produto. No fechamento da feature,
retornou:

| Medida | Resultado |
|---|---:|
| Componentes do registry | 11 |
| Cenários Golden | 20 |
| Ações compiladas | 240 |
| Estado | `valid: true` |
| Tokens de provider | `unresolved_without_host_transcript` |

Os sete cenários de `labs/forge-lab/lab.yaml` (`broker_kill`, `skew`,
`consumer_lag`, `checkpoint_failure`, `small_files`, `schema_evolution` e
`cdc_restart`) continuam sendo o mapa topológico de alto nível. O Golden 20 é o
corpus executável e versionado usado por `sparkforge-aws lab scenarios` e `verify`.

## Fluxo recomendado

```bash
# validar contrato sem iniciar serviços
sparkforge-aws lab doctor
sparkforge-aws lab verify --repo .
sparkforge-aws lab profiles --repo .
sparkforge-aws lab scenarios --json --repo .

# estudar e compilar cenário; ainda sem mutação
sparkforge-aws lab describe iceberg-small-files --repo .
sparkforge-aws lab plan iceberg-small-files --backend compose --seed 42 --repo .

# executar somente com autorização explícita do operador
sparkforge-aws lab run iceberg-small-files --backend compose --seed 42 \
  --execute --confirm --repo .

# inspecionar, analisar, comparar e reproduzir evidência
sparkforge-aws lab inspect .sparkforge_aws/lab/runs/<run-id> --repo .
sparkforge-aws lab analyze .sparkforge_aws/lab/runs/<run-id> --repo .
sparkforge-aws lab compare <run-a> <run-b> --repo .
sparkforge-aws lab reproduce .sparkforge_aws/lab/runs/<run-id>/receipt.json --repo .

# promover somente depois de revisão humana
sparkforge-aws lab promote-fixture <run-id> fixtures/lab/<id> \
  --reviewed --repo .
```

`plan`, `describe`, `inspect`, `analyze`, `compare`, `reproduce`, `doctor`,
`profiles`, `scenarios` e `verify` são operações de leitura ou planejamento.
`up`, `down`, `shell`, `gc` e `run` só mutam o ambiente local com
`--execute --confirm`. A promoção exige receipt válido, hashes íntegros e
revisão explícita.

## Limites e segurança

Forge Lab não é um emulador da AWS e não transforma uma execução local em claim
de produção. Ele não prova capacidade absoluta, latência absoluta, preço AWS,
semântica IAM, exactly-once ou compatibilidade entre versões sem evidência de
um run com versões e receipt.

O core offline não provisiona AWS, não baixa imagens, não chama provider e não
inicia Docker durante análise. Imagens precisam ser fornecidas pelo operador,
com tags pinadas e digest registrado. O contrato proíbe container privilegiado,
host network, mount do Docker socket, root mount e credenciais cloud implícitas.

Resultados usam cinco classes: `PASS`, `FAIL`, `UNRESOLVED`, `INFRA_FAILURE` e
`INVALID_SCENARIO`. Falha de inicialização de container é `INFRA_FAILURE`, não
um diagnóstico falso sobre o job.

## Onde continuar

- [Contrato técnico e fronteiras](../knowledge/forge-lab-product.md)
- [CLI completa gerada do código](referencia/cli/lab.md)
- [Registry de cenários](../../lab/scenarios/README.md)
- [Perfis Compose/Testcontainers](../../lab/compose/README.md)
- [README operacional do laboratório](../../labs/forge-lab/README.md)
- [Entrega SDD e gates](../sdd/FORGE_LAB_PRODUCT/ship.md)
