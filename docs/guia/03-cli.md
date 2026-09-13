# A CLI `sparkforge`

Este guia ensina a usar a linha de comando. Termos novos estão no
[glossário](01-conceitos.md#glossário).

## Receita rápida

O caso mais comum: analisar o código de um job e ver os achados. Rode na raiz
do repositório clonado. O exemplo usa um fixture (caso de teste sintético)
que já vem no repositório.

```bash
# 1. Uma pasta temporária para as saídas
export TMP=/tmp/sparkforge_guia && mkdir -p "$TMP"

# 2. Extrair fatos do código (troque pelo caminho do seu job)
sparkforge analyze pyspark --path fixtures/pyspark/python_udf/input --out "$TMP/facts.json"

# 3. Julgar os fatos, informando a versão do Glue
sparkforge judge --facts "$TMP/facts.json" --glue 5.0 --out "$TMP/findings.json"

# 4. Conferir que os achados seguem o formato oficial
sparkforge validate --findings "$TMP/findings.json"
```

Resultado esperado: o passo 3 mostra `"total_count": 1` com o achado
`SF-PY-001` (P1) na linha 5 de `lib/job.py`, e o passo 4 imprime
`"valid": true`. A seção [Fluxo ponta a ponta](#fluxo-ponta-a-ponta-rodado-de-verdade)
explica cada campo.

No seu projeto, troque o passo 2 por
`sparkforge analyze pyspark --path lib/ --out .sparkforge/facts.json`.

## Para que serve

A CLI é a forma mais direta de usar o SparkForge. Tudo o que as tools MCP
fazem, a CLI também faz. Ela é o caminho natural quando:

- você quer rodar a análise num terminal ou num pipeline de CI;
- você usa um assistente sem suporte a MCP;
- você quer um resultado reproduzível para anexar a um ticket ou a um PR.

Quando **não** usar a CLI: se o seu assistente já está ligado ao servidor MCP,
deixe que ele chame as tools. O resultado é o mesmo.

## Pré-requisitos

- SparkForge instalado (veja [Instalação](02-instalacao.md)). Confira com
  `sparkforge --version`.
- Um artefato para analisar. Os exemplos usam `fixtures/`, que está no
  repositório clonado. Se instalou só pelo PyPI, clone o repositório para
  ter os fixtures.
- Uma pasta temporária para gravar saídas. Nos exemplos ela se chama
  `$TMP`. Crie a sua, por exemplo:

  ```bash
  export TMP=/tmp/sparkforge_guia     # Linux/macOS
  mkdir -p "$TMP"
  ```

  ```powershell
  $env:TMP_GUIA = "$env:TEMP\sparkforge_guia"   # Windows PowerShell
  New-Item -ItemType Directory -Force $env:TMP_GUIA
  ```

  Nos comandos em PowerShell, troque `$TMP` por `$env:TMP_GUIA`.

## Anatomia de um comando

```text
sparkforge <comando> [subcomando] --opções
```

- **comando**: o comando de topo, como `analyze`, `judge`, `case`.
- **subcomando**: alguns comandos se dividem. `analyze pyspark`,
  `analyze event-log`, `case open`, `case get`. Outros não têm subcomando,
  como `judge` e `tune`.
- **opções**: começam com `--`. Algumas são obrigatórias (o `--help` mostra
  quais, sem colchetes em volta).

Todo comando e todo subcomando têm `--help`:

```bash
sparkforge --help
sparkforge analyze --help
sparkforge analyze pyspark --help
```

Se o comando `sparkforge` não estiver no PATH, use
`python -m sparkforge.adapters.cli` no lugar dele. Os argumentos são os
mesmos.

## O que sai na tela

### JSON no stdout

A resposta de quase todos os comandos é um JSON impresso na saída padrão
(stdout). Mensagens de erro vão para a saída de erro (stderr). Isso permite
encadear com outras ferramentas, por exemplo `jq`, sem misturar erro com
dado.

A exceção documentada no código é `report github`: a saída dele é o formato de
anotação do GitHub Actions, porque é isso que o GitHub lê.

### O envelope das listas

Comandos que devolvem listas (`analyze ...`, `judge`, `rules lookup`, `fuse`,
`benchmark`) usam o mesmo envelope. Exemplo real de
`analyze pyspark --path fixtures/pyspark/python_udf/input --limit 1 --detail-level summary`:

```json
{
  "total_count": 3,
  "returned_count": 1,
  "next_cursor": "1",
  "filters_applied": { "kind": null, "limit": 1, "cursor": null },
  "by_kind": {
    "pyspark.function_def": 1,
    "pyspark.module_analyzed": 1,
    "pyspark.udf": 1
  },
  "items": [
    {
      "id": "f_5fa5ca",
      "kind": "pyspark.function_def",
      "measures": { "name_reference_count": 0 },
      "at": "lib/job.py:6",
      "symbol": "trivial",
      "provenance_ref": "8a9110e6230d2c54"
    }
  ],
  "provenance": { "8a9110e6230d2c54": { "artifact": "lib/job.py", "...": "..." } },
  "schema_version": 1
}
```

| Campo | Significado |
|---|---|
| `total_count` | Quantos itens existem no total. |
| `returned_count` | Quantos vieram nesta página. |
| `next_cursor` | O valor para pedir a próxima página. `null` quer dizer que não há mais. |
| `filters_applied` | Os filtros que você usou, para conferência. |
| `by_kind` (ou `by_severity`, `by_category`) | Contagem por tipo, sobre o total, não só sobre a página. |
| `items` (ou `rules`) | Os itens da página. |

### Paginação: `--limit` e `--cursor`

A tela mostra uma página por vez. O tamanho padrão da página aparece em
`filters_applied.limit` (nos exemplos rodados, 50). Para ver a próxima página,
repita o comando com `--cursor` igual ao `next_cursor` recebido:

```bash
sparkforge analyze pyspark --path fixtures/pyspark/python_udf/input --limit 1
sparkforge analyze pyspark --path fixtures/pyspark/python_udf/input --limit 1 --cursor 1
```

Paginação só vale para a tela. Para ter tudo de uma vez, use `--out`.

### `--out`: gravar a lista completa em arquivo

`--out` grava a lista **completa**, sem paginação, num arquivo JSON. É esse
arquivo que você passa para o próximo comando. No `analyze`, o arquivo contém a
lista de facts. No `judge`, a lista de findings. A tela continua mostrando o
envelope paginado.

### `--detail-level`: quanto detalhe por item

Disponível em `analyze ...` e `fuse`. Os valores são `summary`, `normal` e
`full`; o padrão é `full`. O exemplo acima usou `summary`. Com `normal`, cada
item mantém `subject` e `attrs`, e a procedência sai uma vez no envelope,
referenciada por `provenance_ref`. Detalhes no
[glossário](01-conceitos.md#detail_level).

### `--kind`: filtrar por tipo de fact

Disponível em `analyze ...`, `fuse` e `benchmark`. É repetível. Exemplo real:

```bash
sparkforge analyze pyspark --path fixtures/pyspark/python_udf/input --kind pyspark.udf --detail-level normal
```

Saída encurtada: `total_count` passa a ser `1` e `items` traz só o fact de
`kind` `pyspark.udf`. O filtro vale para a tela; o arquivo de `--out`
continua com a lista completa.

No `judge`, o filtro equivalente é `--severity` (repetível), por exemplo
`--severity P0`.

## Códigos de saída

O código de saída é o número que o processo devolve ao terminar. Em shell ele
fica em `$?` (Bash) ou `$LASTEXITCODE` (PowerShell). Conferido em
`sparkforge/adapters/cli.py`:

| Código | Significado | Exemplos reais |
|---|---|---|
| `0` | O comando rodou. **Atenção:** um resultado vazio, uma recusa em `refused` ou um fact `*.unresolved` também saem com `0`, porque "não sei" é uma resposta válida. | `judge` com ou sem findings; `rules lookup` com id inexistente devolve `total_count: 0` e código 0. |
| `1` | Um gate ou uma verificação reprovou. | `validate` quando algum finding viola o schema; `report github` quando o limiar de `--fail-on` dispara; `pack check` quando uma regra do pack não dispara no fixture que a declara; `agents inspect` com id inválido ou inexistente. |
| `2` | Erro de uso ou de entrada: opção obrigatória ausente, arquivo não encontrado, JSON inválido, combinação recusada. | `judge` sem `--facts`; `analyze pyspark --path` para um caminho que não existe; `--emr` sobre facts de EMR on EKS. |

Exemplo real de código 2, com a mensagem que já diz o que fazer:

```bash
sparkforge analyze pyspark --path fixtures/nao_existe
```

```text
Caminho nao encontrado para analise: fixtures/nao_existe
  Aponte para o diretorio da biblioteca ou para um arquivo .py:
    sparkforge analyze pyspark --path <dir-ou-arquivo> --out .sparkforge/facts.json
```

Em CI, use o código de saída para decidir se o passo passa. Não use a
presença de texto na tela.

## Mapa dos comandos de topo

A lista abaixo foi conferida com `sparkforge --help`. Cada linha resume o que
o próprio `--help` diz. As opções exatas estão na referência gerada de cada
comando.

### Extrair (lê artefato)

| Comando | O que faz | Referência |
|---|---|---|
| `analyze` | Extrai facts determinísticos de um artefato. Cada subcomando é um tipo de artefato: `pyspark`, `event-log`, `plan`, `terraform`, `iceberg`, `sql`, `catalog-schema`, `parquet-footer` e outros. | [analyze](referencia/cli/analyze.md) |
| `collect` | Baixa artefatos reais da AWS (event log, job Glue, CloudWatch, metadata Iceberg, Athena, EMR e outros). Precisa de credenciais AWS e do extra `aws`. | [collect](referencia/cli/collect.md) |
| `fuse` | Correlaciona facts de SQL com o schema do catálogo, antes do `judge`. | [fuse](referencia/cli/fuse.md) |

### Julgar

| Comando | O que faz | Referência |
|---|---|---|
| `judge` | Aplica o catálogo de regras sobre facts já extraídos e produz findings. | [judge](referencia/cli/judge.md) |
| `rules` | Consulta o catálogo (`rules lookup --id` ou `--category`). | [rules](referencia/cli/rules.md) |
| `validate` | Valida findings contra o JSON Schema e recusa finding que promete ganho sem `benchmark_ref`. | [validate](referencia/cli/validate.md) |
| `migrate` | Avalia migração entre versões de runtime (`glue`, `emr`, `controlm`) com o catálogo. | [migrate](referencia/cli/migrate.md) |

### Compor e decidir (verbos de topo, consomem facts)

| Comando | O que faz | Referência |
|---|---|---|
| `workload` | Perfil do workload por eixos. | [workload](referencia/cli/workload.md) |
| `capacity` | A capacidade mais barata que cumpre o SLA, entre as que o job já rodou. Nunca aplica. | [capacity](referencia/cli/capacity.md) |
| `finops` | Custo, a troca entre recurso e tempo, e se a alavanca está na capacidade ou no código. | [finops](referencia/cli/finops.md) |
| `tune` | Configuração Spark derivada da medida, com a procedência de cada propriedade. Nunca aplica. | [tune](referencia/cli/tune.md) |
| `benchmark` | Compara duas execuções a partir dos facts de event log de cada uma. | [benchmark](referencia/cli/benchmark.md) |
| `funcval` | Validação funcional: `plan` deriva o que medir; `compare` compara antes e depois. | [funcval](referencia/cli/funcval.md) |
| `simulate` | O que uma mudança de configuração move estruturalmente: quais achados somem e aparecem. Nunca prevê tempo nem custo. | [simulate](referencia/cli/simulate.md) |
| `gain` | Ganho observado entre runs medidos antes e depois. Nunca projeta economia. | [gain](referencia/cli/gain.md) |
| `proof` | Obrigações de prova de cada recomendação aplicada. | [proof](referencia/cli/proof.md) |
| `root-cause` | Ordena os achados por consequência declarada e nomeia a lacuna. | [root-cause](referencia/cli/root-cause.md) |
| `arbitrate` | Arbitra findings já julgados e grava claims, evidências e contradições no blackboard do case. Grava no disco. | [arbitrate](referencia/cli/arbitrate.md) |
| `debate` | Conduz e arbitra o protocolo de debate do case. Não gera argumento. | [debate](referencia/cli/debate.md) |

### Estado da investigação

| Comando | O que faz | Referência |
|---|---|---|
| `case` | Abre, lê e atualiza `.sparkforge/case.yaml` (`open`, `get`, `update`). | [case](referencia/cli/case.md) |
| `next-step` | Próximo passo recomendado, calculado a partir de `rules/catalog/routing.yaml`. | [next-step](referencia/cli/next-step.md) |
| `resume` | Payload para retomar o case. | [resume](referencia/cli/resume.md) |
| `handoff` | Escreve `.sparkforge/handoff.md` e imprime o payload. | [handoff](referencia/cli/handoff.md) |
| `playbook` | Passos sequenciais de um coordenador, para ferramentas sem subagentes. | [playbook](referencia/cli/playbook.md) |
| `runtime` | Detecção de versões (`runtime detect`). | [runtime](referencia/cli/runtime.md) |
| `agents` | Lista e inspeciona agents. | [agents](referencia/cli/agents.md) |
| `blackboard` | Lê o blackboard do case (`.sparkforge/blackboard/`). | [blackboard](referencia/cli/blackboard.md) |
| `decisions` | Lista e explica decisões registradas. | [decisions](referencia/cli/decisions.md) |
| `budget` | Mostra o budget declarado do case. | [budget](referencia/cli/budget.md) |
| `autonomy` | Mostra os níveis de autonomia L0 a L5. | [autonomy](referencia/cli/autonomy.md) |

### Relatórios, prova e observabilidade

| Comando | O que faz | Referência |
|---|---|---|
| `report` | `sign` e `verify` provam que o relatório corresponde à evidência; `github` gera SARIF e anotações para o PR. | [report](referencia/cli/report.md) |
| `receipt` | Recibo da execução do case (`emit`, `verify`). | [receipt](referencia/cli/receipt.md) |
| `economy` | Quanto a execução pôs na janela de contexto, em bytes medidos (`economy report`). | [economy](referencia/cli/economy.md) |
| `telemetry` | Exporta os registros das tools em OTLP/JSON (`telemetry export`). | [telemetry](referencia/cli/telemetry.md) |

### Conhecimento e packs

| Comando | O que faz | Referência |
|---|---|---|
| `knowledge` | `path` localiza os arquivos de `knowledge/`; `drift` mostra o que foi afetado por fontes que mudaram. | [knowledge](referencia/cli/knowledge.md) |
| `pack` | Forge Packs de terceiros (`list`, `check`). | [pack](referencia/cli/pack.md) |
| `release` | O que uma release publica e o que muda entre duas (`describe`, `diff`). | [release](referencia/cli/release.md) |

### Plataformas específicas

| Comando | O que faz | Referência |
|---|---|---|
| `glue` | Comandos específicos do AWS Glue (`dependency-audit`). | [glue](referencia/cli/glue.md) |
| `iceberg` | Comandos específicos de Apache Iceberg (`assess-upgrade`). | [iceberg](referencia/cli/iceberg.md) |
| `lakeformation` | Eixo de versão do Lake Formation por runtime Glue (`matrix`, `access-graph`). | [lakeformation](referencia/cli/lakeformation.md) |
| `controlm` | Conhecimento versionado do Control-M Automation API (`describe`). | [controlm](referencia/cli/controlm.md) |

### Inteligência de código

| Comando | O que faz | Referência |
|---|---|---|
| `code` | Índice local de código: `init`, `sync`, `status`, `search`, `symbol`, `path`, `shape`, `context`, `read`, `export`, `doctor`, `purge`. | [code](referencia/cli/code.md) |

O índice completo, gerado a partir do código, está em
[referencia/cli/README.md](referencia/cli/README.md).

## Fluxo ponta a ponta, rodado de verdade

Vamos analisar o fixture `fixtures/pyspark/python_udf/`, que contém um job
PySpark sintético com uma UDF em Python. Rode os comandos a partir da raiz do
repositório clonado.

### 1. Declarar o runtime

```bash
sparkforge runtime detect --glue 5.0
```

```json
{
  "glue": "5.0",
  "emr": "",
  "spark": "3.5.4",
  "python": "3.11",
  "iceberg": "1.7.1",
  "athena": "",
  "detected_from": ["cli"],
  "divergences": []
}
```

Você informou só o Glue; as outras versões vieram da matriz de runtime do
Glue 5.0 que o projeto mantém.

### 2. Extrair facts

```bash
sparkforge analyze pyspark --path fixtures/pyspark/python_udf/input --out "$TMP/facts.json"
```

Saída encurtada:

```json
{
  "total_count": 3,
  "returned_count": 3,
  "next_cursor": null,
  "filters_applied": { "kind": null, "limit": 50, "cursor": null },
  "by_kind": {
    "pyspark.function_def": 1,
    "pyspark.module_analyzed": 1,
    "pyspark.udf": 1
  },
  "items": [
    { "id": "f_5fa5ca", "kind": "pyspark.function_def", "...": "..." },
    { "id": "f_9e2037", "kind": "pyspark.module_analyzed", "...": "..." },
    {
      "id": "f_726c0b",
      "kind": "pyspark.udf",
      "subject": { "file": "lib/job.py", "line": 5, "snippet": "@udf(returnType=StringType())", "...": "..." },
      "measures": {},
      "attrs": { "udf_type": "python" },
      "provenance": { "extractor": "pyspark_ast@0.1.0", "...": "..." }
    }
  ]
}
```

Três facts. Nenhum deles diz se algo está errado; eles só constatam o que há no
código. O arquivo `$TMP/facts.json` agora contém essa lista.

Um fact interessante é `pyspark.module_analyzed`: ele informa
`resolved_calls` e `unresolved_count`. Se `unresolved_count` fosse maior que
zero, haveria chamadas que o extrator não conseguiu resolver, e você saberia
que a análise daquele módulo é parcial.

### 3. Julgar

```bash
sparkforge judge --facts "$TMP/facts.json" --glue 5.0
```

Saída encurtada:

```json
{
  "total_count": 1,
  "returned_count": 1,
  "next_cursor": null,
  "filters_applied": { "severity": null, "limit": 50, "cursor": null },
  "by_severity": { "P1": 1 },
  "runtime": {
    "glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1",
    "detected_from": ["cli"], "divergences": [], "...": "..."
  },
  "plan": {
    "scope": "todos os 1 achados deste case, nao a pagina",
    "order": ["SF-PY-001"],
    "order_unresolved": {},
    "contradictions": [],
    "unresolved": [],
    "persisted": false,
    "note": "calculado, nao gravado. O registro auditavel e `sparkforge arbitrate`.",
    "...": "..."
  },
  "items": [
    {
      "rule_id": "SF-PY-001",
      "title": "Python UDF em transformação expressável nativamente",
      "severity": "P1",
      "confidence": "high",
      "status": "structural",
      "subject": { "file": "lib/job.py", "line": 5, "symbol": "trivial", "...": "..." },
      "evidence": ["f_726c0b"],
      "proposed_change": ["Reescrever com funções Spark SQL nativas.", "..."],
      "expected_effect": "",
      "validation": ["Contagem total idêntica.", "..."],
      "rollback": ["Reverter o commit; a UDF original não depende de mudança de infraestrutura."],
      "evidence_standing": {
        "value": "high",
        "source_tier": "T1_OFFICIAL_DOCS",
        "in_version_scope": true,
        "measures_present": true
      },
      "...": "..."
    }
  ]
}
```

Para gravar os findings em arquivo, acrescente `--out "$TMP/findings.json"`.

### 4. Ler o finding

Leia nesta ordem:

1. **`rule_id` e `title`**: qual regra disparou. `SF-PY-001`, "Python UDF em
   transformação expressável nativamente". Para ver a regra inteira:
   `sparkforge rules lookup --id SF-PY-001`.
2. **`subject`**: onde está. Arquivo `lib/job.py`, linha 5, função `trivial`.
3. **`evidence`**: o fact que sustenta o achado, `f_726c0b`. Procure esse id no
   `facts.json` para ver a observação crua.
4. **`severity`, `confidence` e `status`**: prioridade `P1`, confiança
   `high`, e `structural`, ou seja, a regra viu um padrão no código sem
   medida de execução.
5. **`explanation`**: por que é um problema. Aqui, a UDF em Python serializa
   cada linha para um processo Python separado e impede otimizações do Spark.
6. **`proposed_change`**: o que fazer. Reescrever com funções nativas.
7. **`risks`, `validation` e `rollback`**: o que pode mudar no resultado, como
   conferir que não mudou e como voltar atrás. Não pule esta parte: trocar uma
   UDF por função nativa pode mudar o tratamento de valores nulos.
8. **`expected_effect`**: vazio. O SparkForge não promete ganho sem medir.
   Para medir, compare dois runs com `benchmark` ou `gain`.
9. **`plan`**: quando há vários findings, a ordem sugerida de aplicação e as
   contradições entre eles. `persisted: false` avisa que esse plano não foi
   gravado; o registro auditável é o comando `arbitrate`.

### 5. Validar e perguntar o próximo passo (opcional)

Grave os findings e valide contra o schema:

```bash
sparkforge judge --facts "$TMP/facts.json" --glue 5.0 --out "$TMP/findings.json"
sparkforge validate --findings "$TMP/findings.json"
```

```json
{
  "valid": true,
  "count": 1
}
```

Para acompanhar a investigação num case, abra um no diretório do projeto
analisado (aqui, um diretório temporário de exemplo):

```bash
sparkforge case open --repo "$TMP/repo_demo" --case-id demo-udf --now 2026-09-13T10:00:00Z --glue 5.0
sparkforge next-step --repo "$TMP/repo_demo" --findings "$TMP/findings.json"
```

Saída real do `next-step`:

```json
{
  "phase": "intake",
  "recommended_skill": "analyze-library-call-graph",
  "reason": "ROUTE-002: Nenhum fact extraído. Mapear entrypoint e biblioteca antes de qualquer hipótese.",
  "evidence": ["case:facts_index.count count_eq=0"],
  "missing_artifacts": [],
  "collect_commands": [
    "sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json"
  ],
  "blocked_by": [],
  "alternatives": [],
  "recommended_agent": null,
  "recommended_agent_reason": null
}
```

O `next-step` leu o case, viu que o índice de facts do case está vazio
(`facts_index.count` igual a zero, porque o `case open` acima não recebeu
`--facts`) e recomendou mapear o código primeiro. A recomendação vem de uma
regra de roteamento (`ROUTE-002`), não de opinião. Para registrar os facts no
case, passe `--facts "$TMP/facts.json"` ao `case open` ou ao `case update`.

## Como ler as recusas

Nem todo comando termina com uma resposta completa, e isso é esperado.

- **`skipped` no `judge --show-skipped`**: regras que não foram avaliadas.
  No fluxo acima, sem `--glue`, a saída lista regras com
  `"reason": "requires_facts"` (faltou o tipo de fact, e o campo `missing`
  diz qual) e com `"reason": "runtime_scope"` (a regra depende de uma versão
  que não foi informada). Exemplo real:

  ```json
  { "rule_id": "SF-ATH-002", "reason": "requires_facts", "missing": ["catalog.table_schema", "sql.projection"] }
  ```

  Isso quer dizer: "para avaliar esta regra, rode o extrator que produz
  `catalog.table_schema` e `sql.projection`".

- **`refused` em `tune` e `capacity`**: propriedades para as quais não há
  medida que sustente um valor. Rode
  `sparkforge tune --facts fixtures/tuning/sem_shuffle_medido/input/facts.json`
  e veja `properties: []` e uma lista `refused` em que cada item nomeia a
  medida que faltou.

- **Facts `*.unresolved`**: lacunas registradas como fact. Por exemplo,
  `glue.run_cost.unresolved` quando o run não tem `dpu_seconds`.

Nos três casos o código de saída é `0`. O comando funcionou; ele só está
dizendo, com precisão, o que ainda não pode afirmar.

## Erros comuns e como resolver

| Sintoma | Causa | Correção |
|---|---|---|
| `error: the following arguments are required: --facts` (código 2) | Opção obrigatória ausente. | Veja o `--help` do comando e acrescente a opção. |
| `Arquivo de facts nao encontrado: ...` (código 2) | O caminho de `--facts` está errado ou o `analyze` não foi rodado com `--out`. | A mensagem mostra o comando `analyze` que produz o arquivo. |
| `Caminho nao encontrado para analise: ...` (código 2) | O `--path` do `analyze` não existe. | Aponte para a pasta do código ou para um `.py`. |
| `judge` devolve `total_count: 0` | Os facts não satisfazem nenhuma regra, ou faltam facts ou versão para as regras que interessam. | Rode de novo com `--show-skipped` e leia `missing` e `runtime_scope`. |
| O `runtime` do `judge` sai todo vazio | Nenhuma versão foi informada e nenhum fact trazia versão. | Passe `--glue` (ou `--emr`, `--spark` etc.), ou inclua facts que carregam a versão, como os de `analyze terraform` ou `analyze event-log`. |
| Uma regra que correlaciona duas fontes nunca dispara | Os facts das duas fontes foram julgados em chamadas separadas. | Passe os dois arquivos na mesma chamada, repetindo `--facts`. |

## Dicas

### Combine vários arquivos de facts

`--facts` é repetível em `judge`, `case open`, `case update`, `runtime detect`
e `arbitrate`. O `judge` une as listas antes de julgar. Isso é necessário para
regras que cruzam extratores diferentes (por exemplo, `SF-GLUE-004` cruza o
Terraform com a escrita no PySpark). Exemplo real, com dois fixtures:

```bash
sparkforge analyze pyspark --path fixtures/pyspark/coalesce_one/input --out "$TMP/facts_coalesce.json"
sparkforge judge --facts "$TMP/facts.json" --facts "$TMP/facts_coalesce.json" --glue 5.0
```

Resultado resumido: `total_count: 2`, `by_severity: {"P0": 1, "P1": 1}`, com
`SF-PY-005` (P0) e `SF-PY-001` (P1).

### Informe as versões

`judge`, `case open`, `runtime detect`, `arbitrate`, `root-cause`, `simulate` e
`proof` aceitam `--glue`, `--spark`, `--python`, `--iceberg`, `--athena` e
`--emr`. `--emr` aceita `emr-7.5.0` ou `7.5.0`.

A versão que você declara é **declaração**, não observação. Quando um
artefato (um event log, um `.tf`) traz outra versão, ela entra como fonte
própria, e a discordância aparece em `runtime.divergences`. Sobre facts de EMR
on EKS, `--emr` é recusado com código 2.

### Filtre por severidade

```bash
sparkforge judge --facts "$TMP/facts.json" --glue 5.0 --severity P0
```

### Veja o estado das fontes

```bash
sparkforge judge --facts "$TMP/facts.json" --glue 5.0 --source-freshness
```

Acrescenta o estado de cada fonte citada, calculado sobre
`knowledge/sources.lock.json`. O resultado depende do dia; para fixar o dia,
use `--as-of AAAA-MM-DD`.

### Grave em `.sparkforge/` no projeto real

No seu próprio projeto, a convenção é gravar em `.sparkforge/`:

```bash
sparkforge analyze pyspark --path lib/ --out .sparkforge/facts.json
sparkforge judge --facts .sparkforge/facts.json --glue 5.0 --out .sparkforge/findings.json
sparkforge next-step --repo . --findings .sparkforge/findings.json
```

### Comandos que falam com a AWS

Os comandos `collect ...` acessam a sua conta AWS e precisam de credenciais e
do extra `aws`. Por exemplo, a skill `tune-glue-job` usa:

```bash
sparkforge collect glue-job --repo . --job-name <nome> --now <ISO8601>
```

Ele baixa a definição real do job pela API do Glue, para comparar com o que o
Terraform declara. Confira as opções de cada coletor em
[referencia/cli/collect.md](referencia/cli/collect.md) antes de rodar.

## Próximos passos

- [Conceitos](01-conceitos.md): o glossário de fact, finding, recusa e os
  demais termos.
- [Instalação](02-instalacao.md): extras e problemas de instalação.
- [Índice de comandos](referencia/cli/README.md), com as opções exatas de cada
  um.
- [judge](referencia/cli/judge.md) e [analyze](referencia/cli/analyze.md) em
  detalhe.
- [Índice de tools MCP](referencia/tools/README.md), se você usa um assistente
  com MCP.
