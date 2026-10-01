# Mudanças com prova

Antes de mudar um job, você quer saber o que a mudança mexe. Depois, quer saber se
ela funcionou e se o resultado continua o mesmo. Este manual mostra os verbos para
isso: `simulate`, `funcval`, `benchmark`, `proof`, `gain`, `report sign` e `receipt`.

## Receita rápida

Rode da raiz do repositório. Todos os arquivos são fixtures sintéticas.

1. **Antes de mudar:** veja que achados uma mudança de configuração tira ou cria.

   ```bash
   sparkforge simulate --facts fixtures/infra_code/fgac_com_jar_extra/expected/facts.json \
     --set "tf:--enable-lakeformation-fine-grained-access=false"
   ```

2. **Antes de mudar:** defina o que medir para saber se o resultado mudou.

   ```bash
   DEMO=/tmp/sf-prova && mkdir -p "$DEMO"
   F=fixtures/funcval/count_diverged/input
   sparkforge analyze pyspark --path $F/job.py --out "$DEMO/fv_pyspark.json"
   sparkforge analyze catalog-schema --path $F/catalog/dump.json --out "$DEMO/fv_catalog.json"
   sparkforge funcval plan --facts "$DEMO/fv_pyspark.json" --facts "$DEMO/fv_catalog.json" --out "$DEMO/plano.json"
   ```

3. **Depois:** compare os dois event logs (tempo, volume, spill).

   ```bash
   B=fixtures/bench/clean_improvement/input
   sparkforge analyze event-log --path $B/before.jsonl --out "$DEMO/antes.json"
   sparkforge analyze event-log --path $B/after.jsonl --out "$DEMO/depois.json"
   sparkforge benchmark --before "$DEMO/antes.json" --after "$DEMO/depois.json" --out "$DEMO/bench.json"
   ```

4. **Depois:** compare o resultado que você mediu nos dois lados.

   ```bash
   sparkforge funcval compare --plan "$DEMO/plano.json" --before $F/before.json --after $F/after.json --out "$DEMO/fv.json"
   sparkforge judge --facts "$DEMO/fv.json"
   ```

5. **Depois:** veja o que cada obrigação de prova concluiu.

   ```bash
   sparkforge analyze pyspark --path fixtures/proof/resolucao_corrigida/input/after/lib --out "$DEMO/depois_py.json"
   sparkforge proof --findings fixtures/pyspark/collect_unbounded/expected/findings.json \
     --facts fixtures/pyspark/collect_unbounded/expected/facts.json \
     --after-facts "$DEMO/depois_py.json" --applied SF-PY-002
   ```

## Duas regras que valem para tudo aqui

- **Nunca interpolar entre capacidades (regra 12).** Se o job já rodou com 10 e com
  20 workers, o SparkForge compara esses dois. Ele não chuta como seria com 15. Mais
  máquina pode dar menos tempo e mais custo ao mesmo tempo.
- **Nunca estimar economia (regra 13).** "Você economizaria X" exige o custo de um run
  que não aconteceu. O SparkForge só mostra o que foi medido, e mostra o sintoma ao
  lado do custo sem subtrair um do outro.

Por isso você verá campos como `economia_mensal` e `gain_estimate` sempre em
`refused`. Isso é o projeto dizendo o que ele não sabe.

## Pré-requisitos

- SparkForge instalado ([Instalação](../02-instalacao.md)).
- Para `benchmark`: event logs do Spark dos dois runs (antes e depois).
- Para `funcval compare`: os resultados que **você** mediu antes e depois. O SparkForge
  não roda consulta nem Spark.
- Para `gain`: histórico de runs do Glue (`analyze glue-job-runs --out`).

## Passo a passo, com saída real

### 1. `simulate`: o que a mudança move, sem rodar o job

`--set` tem a forma `camada:chave=valor`. A camada é obrigatória: `tf` (Terraform),
`code` (código), `effective` (configuração efetiva) ou `emr`.

Saída real do passo 1 da receita:

```json
{
  "changes": [{"layer": "tf", "key": "--enable-lakeformation-fine-grained-access",
               "old_values": ["true"], "new_value": "false", "facts_changed": 2}],
  "disappeared": [{"rule_id": "SF-LF-001", "subject": {"type": "tf_resource", "file": "main.tf", "line": 15,
                   "symbol": "aws_glue_job.etl_fgac_com_jar"}}],
  "appeared": [],
  "refused": [
    {"field": "performance_prediction", "reason": "spill_e_tempo_nao_sao_fact_de_configuracao"},
    {"field": "dependency_incompatibility", "reason": "use_sparkforge_migration_assess"},
    {"field": "execution_graph", "reason": "nao_e_previsivel_a_partir_de_configuracao"}
  ],
  "fact_count": 43
}
```

- `disappeared` e `appeared`: achados que somem e que aparecem.
- `refused`: o `simulate` nunca prevê tempo, spill ou custo.

Recusa real (código 2), com texto numa medida numérica:

```bash
sparkforge simulate --facts fixtures/terraform/bookmarks_with_concurrency/expected/facts.json --set "tf:max_concurrent_runs=muitos"
```

```text
max_concurrent_runs: 'muitos' nao e numero, e o fact guarda o valor como medida numerica [valor_nao_numerico_para_medida]. Rode: sparkforge simulate --facts <facts.json> --set tf:max_concurrent_runs=1
```

Outras recusas: `camada_invalida`, `set_malformado`, `sem_set` e
`chave_ausente_na_camada` (a chave não existe no artefato, e o SparkForge não inventa
o valor padrão). Detalhes em `docs/simulate.md`.

### 2. `funcval plan`: o que medir antes de mudar

`funcval` quer dizer validação funcional: o resultado continua o mesmo? O plano sai
dos facts que você já extraiu. `--facts` se repete porque o alvo vem do código
(`analyze pyspark`) e o schema vem do catálogo (`analyze catalog-schema`). `--out` é
obrigatório.

Sem `--key`, o plano **não** inventa chave de negócio. Trecho real do plano do passo 2:

```json
{
  "target": "db.eventos",
  "checks": {
    "count": {"origin": "derived", ...},
    "schema": {"origin": "derived", ...},
    "agg:sum:cliente_id": {"origin": "derived", ...},
    "agg:sum:valor": {"origin": "derived", ...}
  },
  "undeclared_axes": ["keys"],
  "undeclared_axes_reason": {"keys": "nenhum kind que os extratores emitem nomeia chave de negocio: ... Declare com --key <col>[,<col>] para o eixo entrar ..."}
}
```

Para declarar a chave, acrescente `--key pedido_id` (vírgula faz chave composta:
`--key pedido_id,dt`). O check sai com `origin: declared`. A responsabilidade pela
chave certa é sua.

**Meça o lado de antes antes de mudar.** Um `overwrite` no meio apaga o antes sem
deixar rastro.

### 3. `benchmark`: dois event logs, lado a lado

Trecho real do passo 3, com `--detail-level summary`:

```json
{
  "by_kind": {"bench.analyzed": 1, "bench.run_delta": 1, "bench.stage_delta": 3},
  "items": [
    {"id": "f_64c631", "kind": "bench.run_delta", "measures": {
      "total_task_ms_before": 22000.0, "total_task_ms_after": 13600.0, "total_task_ms_delta_pct": -38.2,
      "total_input_bytes_before": 140000000, "total_input_bytes_after": 140000000, "total_input_bytes_delta_pct": 0.0,
      "total_spill_bytes_before": 0, "total_spill_bytes_after": 0, ...}},
    ...
  ]
}
```

- `total_task_ms` é **tempo de task somado**, ou seja, trabalho. Não é o relógio do job.
- O volume de entrada é igual nos dois lados, então a comparação vale.
- `sparkforge judge --facts "$DEMO/bench.json"` devolve `total_count: 0` aqui. É o
  esperado: melhora limpa, sem volume diferente, sem stage sem par, sem spill novo.
- O `id` do `bench.run_delta` (`f_64c631`) é o que uma recomendação cita em
  `benchmark_ref`. Sem ele, ganho com número é rejeitado.

Use `--before-runtime` e `--after-runtime` quando os dois runs estão em versões
diferentes do Glue.

### 4. `funcval compare`: o resultado mudou?

O arquivo de antes (medido por você) tem esta forma real:

```json
{"target": "db.eventos", "side": "before", "checks": {
  "count": {"value": 1000000},
  "schema": {"value": {"pedido_id": "string", "cliente_id": "bigint", "valor": "double", "dt": "string"}},
  "agg:sum:cliente_id": {"value": 500500123},
  "agg:sum:valor": {"value": 1000000.0}}}
```

Check que você não mediu fica **ausente**, nunca zero.

Resultado real do `judge` sobre a comparação (passo 4):

```text
SF-FVAL-001 P0 Contagem de linhas divergiu entre antes e depois da mudança
```

A contagem foi de 1.000.000 para 1.000.002, e os agregados não mudaram. Sem o eixo
de contagem, essa diferença passaria.

Se o plano pede `--key pedido_id` e você não mede a chave, aparece também:

```text
SF-FVAL-005 P1 Validação parcial — o resultado trouxe menos checks do que o plano pediu
```

Com `SF-FVAL-005`, a leitura dos outros eixos fica incompleta.

**Limite importante:** contagem, schema, chaves e agregados são *proxies*. Iguais nos
dois lados, eles não provam que o dado é o mesmo (duas linhas podem trocar valores).
Escreva "nenhum proxy detectou divergência", nunca "o resultado é idêntico".

### 5. `proof`: o que cada obrigação concluiu

Depois de aplicar uma recomendação, `proof` confere cada obrigação dela. `--applied`
recebe o `RULE_ID` (ou `RULE_ID:simbolo`). Os desfechos possíveis:

| Desfecho | Quer dizer |
|---|---|
| `refuted` | uma medida contrariou a obrigação |
| `not_refuted` | foi medida e nada a contrariou |
| `inconclusive` | foi medida, mas a comparação não vale ou não é atribuível |
| `unproven` | nada mede isso; `unlock` diz o que mediria |

Nunca "provado". Trecho real do passo 5 (o `collect()` foi removido no depois):

```json
{
  "obligations": [
    {"kind": "resolution", "rule_id": "SF-PY-002", "outcome": "not_refuted",
     "reason": "padrao_ausente_com_extrator_rodado", "absent_kinds": ["pyspark.driver_collect"]},
    {"kind": "axis", "axis": "correctness.write_result", "source": "funcval", "outcome": "unproven",
     "reason": "sem_funcval",
     "unlock": "sparkforge funcval plan ... --out <plano> e sparkforge funcval compare --plan <plano> --before <resultado-antes> --after <resultado-depois>"}
  ],
  "summary": {"refuted": 0, "not_refuted": 1, "inconclusive": 0, "unproven": 1},
  "refused": [
    {"field": "proven", "reason": "nenhuma_medida_do_pacote_prova_equivalencia_ou_melhoria"},
    {"field": "gain_estimate", "reason": "exige_o_run_que_nao_aconteceu_regra_13"}
  ]
}
```

Outro exemplo real, com o benchmark na união (`fixtures/proof/melhoria_nao_refutada`):

```bash
sparkforge proof --findings fixtures/pyspark/action_in_loop/expected/findings.json \
  --facts fixtures/pyspark/action_in_loop/expected/facts.json \
  --facts fixtures/bench/clean_improvement/expected/facts.json \
  --after-facts fixtures/pyspark/action_in_loop/expected/facts.json --applied SF-PY-004
```

O eixo `runtime.wall_clock` sai `not_refuted` com `delta_pct: -38.2` e
`proxy: task_ms_nao_e_wall_clock`. A resolução sai `refuted` (`regra_ainda_dispara`):
o laço continua no código do depois.

### 6. `gain`: ganho observado entre runs medidos

`gain` compara runs que **aconteceram**. Cada arquivo é o facts de um run
(`analyze glue-job-runs --out`). `--baseline` e `--candidate` se repetem, um por arquivo.

```bash
G=fixtures/gain/ganho_por_capacidade
sparkforge gain $(for f in $G/baseline/*.json; do printf -- '--baseline %s ' "$f"; done) \
                $(for f in $G/candidate/*.json; do printf -- '--candidate %s ' "$f"; done)
```

Trecho real (G.1X ×10 contra G.2X ×10, 10 runs de cada lado):

```json
"metrics": {
  "execution_time_s": {"baseline": {"n": 10, "median": 900.0}, "candidate": {"n": 10, "median": 500.0},
                       "delta": -400.0, "delta_pct": -44.4, "marks": []},
  "dpu_seconds":      {"baseline": {"n": 10, "median": 900.0}, "candidate": {"n": 10, "median": 1000.0},
                       "delta": 100.0, "delta_pct": 11.1, "marks": []},
  "cost": {"delta": null, "delta_pct": null, "marks": ["custo_indisponivel"]}
},
"refused": [
  {"field": "economia_mensal", "reason": "projecao_sobre_runs_que_nao_aconteceram"},
  {"field": "atribuicao_causal", "reason": "sem_run_de_controle"},
  {"field": "intervalo_de_confianca", "reason": "amostra_pequena_use_mediana_e_faixa"}
]
```

O tempo caiu 44,4% e os DPU-segundos subiram 11,1%. O `gain` mostra os dois e não
escolhe qual é "o ganho". Isso é a regra 12 na prática.

As **marcas** dizem quando o delta não sustenta a palavra "ganho":
`amostra_insuficiente` (menos de 3 runs num lado), `volume_desconhecido`,
`volume_diverge` e `custo_indisponivel`. Com `fixtures/gain/amostra_insuficiente`
(2 runs no candidato), o tempo sai `delta_pct: -77.8` com a marca
`amostra_insuficiente`. Número com marca não é ganho.

### 7. `report sign` e `report verify`: o relatório corresponde à evidência?

A assinatura prova que o texto do relatório foi escrito a partir daqueles findings e
daquele catálogo. Ela **não** prova quem escreveu: não há chave nem segredo.

```bash
cp fixtures/receipt/uniao_debate/input/report.md "$DEMO/relatorio.md"
sparkforge judge --facts fixtures/graph/import_sem_jar_no_iac/expected/facts.json \
  --facts fixtures/infra_code/fgac_com_jar_extra/expected/facts.json --out "$DEMO/findings.json"
sparkforge report sign --report "$DEMO/relatorio.md" --findings "$DEMO/findings.json"
sparkforge report verify --report "$DEMO/relatorio.md" --findings "$DEMO/findings.json"
```

O `sign` reescreve o arquivo e acrescenta um bloco no fim:

```text
- assinatura: sig_90ae9511f5e974fa2f976a36a3b7b65980f33d2bb848df8833967157e4c21b48
- signature_version: 1
- evidência: 7 facts, 2 regras
- rule_ids: SF-GRAPH-005, SF-LF-001
...
```

O `verify` responde `"valid": true, "status": "signed"`. Com o título do relatório
editado depois da assinatura, a resposta real é (código 1):

```json
{"valid": false, "status": "diverged", "diverged": ["body"],
 "reason": "divergiu em: corpo. ... Reassine com: sparkforge report sign --report ... --findings <findings.json>"}
```

As quatro partes conferidas são `version`, `evidence`, `catalog` e `body`.
`version_mismatch` quer dizer regra mudada, não adulteração: reassine.

### 8. `receipt emit` e `receipt verify`: o recibo da execução

O recibo amarra, por caminho e sha256 (uma impressão digital do arquivo), o case, os
facts, os findings, o relatório, o blackboard e os debates. Ele é gravado em
`.sparkforge/receipts/` e por isso deve rodar numa pasta de case, nunca no repositório.

```bash
sparkforge case open --repo "$DEMO" --case-id demo-recibo --now 2026-09-13T14:00:00Z --glue 5.0
cp fixtures/graph/import_sem_jar_no_iac/expected/facts.json "$DEMO/facts_grafo.json"
cp fixtures/infra_code/fgac_com_jar_extra/expected/facts.json "$DEMO/facts_lf.json"
sparkforge receipt emit --repo "$DEMO" --facts facts_grafo.json --facts facts_lf.json \
  --findings findings.json --report relatorio.md --now 2026-09-13T14:30:00Z
```

Trecho real (no exemplo, o `arbitrate` já tinha rodado nesta pasta):

```json
{"receipt_id": "rcpt_676c274e...",
 "refused": [{"field": "authorship", "reason": "content_addressed_sem_chave"},
             {"field": "tool_io", "reason": "span_sem_hash_de_io"}],
 "unresolved": [{"field": "proof.tests", "reason": "sem_prova_funcional"},
                {"field": "proof.before_after", "reason": "sem_benchmark"},
                {"field": "tools", "reason": "run_id_nao_declarado"},
                {"field": "host.provider", "reason": "provider_nao_declarado"}, ...]}
```

Caminhos relativos resolvem contra `--repo`. Cada lacuna sai com nome em `unresolved`.

```bash
sparkforge receipt verify --repo "$DEMO" --receipt .sparkforge/receipts/<receipt_id>.json
```

Sem mudanças: `"valid": true, "status": "valid"`. Depois de alterar `facts_lf.json`,
a resposta real é `"status": "diverged", "diverged": ["evidence"]`, com código 1.
Estados possíveis de cada parte: `match`, `diverged`, `missing`, `not_rechecked`,
`not_evaluable` e `not_declared`. Detalhes em `docs/execution-receipt.md`.

## Como ler o resultado

- **`refused`** aparece sempre nos verbos deste manual. É a lista do que o SparkForge
  se recusa a afirmar (previsão de tempo, economia, prova, autoria), com o motivo.
- **`*.unresolved`** e `unresolved`: lacuna com nome. O campo diz o que faltou e,
  muitas vezes, o comando que a fecharia (`unlock`).
- **`marks`** no `gain`: o número saiu, mas não sustenta a palavra "ganho".
- **Código 1** em `verify`: não corresponde. **Código 2**: erro de uso ou recusa.

## Erros comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `[chave_ausente_na_camada]` no `simulate` | a chave não existe naquela camada | confira a camada (`tf`, `code`, `effective`, `emr`) e o nome da chave |
| `funcval plan` sem eixo de chave | faltou `--key` | declare a chave de negócio, se você a conhece |
| `SF-FVAL-005` aceso | você mediu menos checks do que o plano pede | meça os checks faltantes nos dois lados |
| `benchmark` com `SF-BENCH-001` | volume de entrada diferente entre os lados | rode os dois lados sobre a mesma entrada |
| `report verify` com `diverged: ["body"]` | o texto mudou depois de assinar | reassine com `report sign` |
| `receipt verify` com `missing` | um arquivo do recibo foi apagado ou movido | restaure o arquivo ou emita um recibo novo |

## Próximos passos

- [Investigação com case](investigacao-com-case.md): feche a hipótese com o `fact_id` do benchmark.
- [Custo e capacidade](custo-e-capacidade.md): `capacity` e `finops` sobre os mesmos runs.
- [CI e GitHub](ci-e-github.md): levar o relatório assinado ao pull request.
- Referência: [`simulate`](../referencia/cli/simulate.md), [`funcval`](../referencia/cli/funcval.md),
  [`benchmark`](../referencia/cli/benchmark.md), [`proof`](../referencia/cli/proof.md),
  [`gain`](../referencia/cli/gain.md), [`report`](../referencia/cli/report.md),
  [`receipt`](../referencia/cli/receipt.md); tools
  [`sparkforge_simulate`](../referencia/tools/sparkforge_simulate.md),
  [`sparkforge_funcval_plan`](../referencia/tools/sparkforge_funcval_plan.md),
  [`sparkforge_benchmark`](../referencia/tools/sparkforge_benchmark.md),
  [`sparkforge_proof`](../referencia/tools/sparkforge_proof.md),
  [`sparkforge_gain`](../referencia/tools/sparkforge_gain.md),
  [`sparkforge_report_sign`](../referencia/tools/sparkforge_report_sign.md),
  [`sparkforge_receipt_emit`](../referencia/tools/sparkforge_receipt_emit.md).
