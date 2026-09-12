# Simulate

Antes de aplicar uma mudança de configuração, `sparkforge simulate` diz que
achados ela tira e que achados ela cria (§19 de `prompt_new_evo.md`). Não roda o
job, e nenhum número de desempenho sai daqui.

```bash
sparkforge simulate --facts terraform.json --set tf:max_concurrent_runs=1
```

A tool MCP é `sparkforge_simulate` (`READ_ONLY`). O dono é o
`spark-performance-architect`.

## O `--set`

`--set <camada>:<chave>=<valor>`, repetível. A camada é obrigatória:

| Camada | Kinds alterados |
|---|---|
| `tf` | `tf.spark_conf`, `tf.attribute` |
| `code` | `pyspark.conf_set` |
| `effective` | `spark.conf_effective` |
| `emr` | `emr.configuration`, `emrs.configuration`, `emrc.configuration` |

A regra 19 separa quem pediu de quem venceu. Mudar "a configuração" sem dizer
onde escolheria a camada pelo operador.

O valor troca em **todo** fact da camada que declara a chave, e só nesses:
`attrs.value` recebe o texto e, quando o fact guarda o valor também em
`measures.value` (medido em `tf.attribute`, onde `SF-GLUE-003` lê), a medida
recebe o número. Sem a medida, o `--set` em `max_concurrent_runs` não moveria a
regra.

## As recusas

Todas saem com código 2 e o motivo entre colchetes:

| Motivo | Quando |
|---|---|
| `camada_invalida` | Sem prefixo, ou camada fora da tabela acima |
| `set_malformado` | Sem `=`, ou chave vazia |
| `sem_set` | Nenhum `--set` |
| `chave_ausente_na_camada` | Nenhum fact da camada declara a chave. Criá-la seria inventar o default que o artefato não disse |
| `valor_nao_numerico_para_medida` | Texto para um fact que guarda o valor como medida numérica |

## Os dois lados

Antes e depois passam pelo mesmo pipeline:

1. Tiram os kinds que `fusion`, `lakeformation` e `timeout_diagnosis` derivam.
2. Rederivam com `fuse()`.
3. Detectam o runtime sobre os facts rederivados. Trocar `glue_version` muda o
   runtime do lado de depois.
4. Rodam o `judge`, com os pulados.

Assim a diferença só pode vir do `--set`. Ela nunca vem de uma rederivação que
só um lado sofreu. Repetir o valor atual dá diferença vazia, e há um golden que
confere isso.

## A saída

- **`changes`**: por `--set`, os valores antigos e quantos facts mudaram.
- **`disappeared`** / **`appeared`**: achados comparados por `(rule_id, chave
  estável do subject)`, a mesma chave do [Change Proof](change-proof.md).
- **`persisted_count`**: achados que ficaram nos dois lados.
- **`skipped_delta`**: regras que mudaram de estado entre `evaluated`,
  `requires_facts`, `runtime_scope` e `blocked_on`. É aqui que trocar
  `glue_version` aparece: nenhum achado se move, mas as regras de Lake Formation
  e de migração saem do escopo.
- **`runtime`**: `before` e `after`.
- **`refused`**: sempre as mesmas três recusas:

| Campo | Por quê |
|---|---|
| `performance_prediction` | Spill, tempo e custo não são fact de configuração |
| `dependency_incompatibility` | Use `sparkforge migration assess` |
| `execution_graph` | O grafo de execução não é previsível a partir de configuração |

## A derivação de timeout

Até esta frente, `extract_timeout_diagnosis` não tinha caller de produção. Ela
passou a rodar dentro de `fuse()`, e só quando o pool tem algum dos kinds que ela
lê (`timeout_diagnosis.SOURCE_KINDS`). Sem essa guarda, todo pool não vazio
ganharia um `spark.timeout.diagnosis` com `no_timeout_evidence`. O golden
`timeout_rederivado_aparece` mostra o efeito: `spark.network.timeout=5s` na
camada `effective` faz `SF-TIMEOUT-002` aparecer.

## Onde está provado

- `tests/test_simulate_patch.py`: o parse e as recusas do `--set`.
- `tests/test_simulate_diff.py`: a comparação pela chave estável e o
  `skipped_delta`.
- `tests/test_fusion_timeout.py`: `fuse()` produz o mesmo timeout que o extrator,
  e um pool sem kind de origem não ganha nenhum.
- `tests/test_fixtures_golden_simulate.py` e `fixtures/simulate/`: seis casos
  simulados e três recusas, de ponta a ponta pela CLI.
