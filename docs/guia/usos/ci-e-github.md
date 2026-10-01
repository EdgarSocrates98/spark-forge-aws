# CI e GitHub: o SparkForge no pull request

Este manual leva o SparkForge para o **CI**, a esteira automática que roda a
cada pull request. O resultado aparece em três lugares do GitHub: na aba
Security, no diff do PR e num resumo na página da execução. No fim, ele mostra
também como exportar a telemetria das tools e como vigiar fontes que mudaram.

Nada aqui chama rede. Quem sobe o resultado para o GitHub é uma action do
próprio GitHub.

## Receita rápida

```bash
# 1. Copie o workflow de exemplo para o repositório do seu job
mkdir -p .github/workflows
cp examples/github/sparkforge.yml .github/workflows/sparkforge.yml

# 2. Edite o arquivo: troque `jobs` e `infra` pelos seus diretórios e `--glue 5.0` pela sua versão

# 3. Não versione o que é gerado a cada execução
echo ".sparkforge/report/" >> .gitignore

# 4. Teste o passo principal na sua máquina, sobre uma fixture, numa pasta temporária
cp -r fixtures/sarif/misto/input/repo /tmp/sf_repo
sparkforge report github \
  --findings fixtures/sarif/misto/input/findings.json \
  --facts fixtures/sarif/misto/input/facts.json \
  --repo /tmp/sf_repo --source-root a --source-root b \
  --fail-on P0 --category fixture-misto
```

O passo 1 é feito no repositório do **seu job**, onde `examples/github/sparkforge.yml`
foi copiado do SparkForge. Os passos 4 e seguintes rodam na raiz do repositório
do SparkForge, porque usam as fixtures.

## Palavras que aparecem aqui

- **CI (integração contínua)**: a esteira que roda testes e verificações a cada
  push ou pull request. No GitHub, é o GitHub Actions.
- **Workflow**: o arquivo YAML em `.github/workflows/` que diz o que o CI roda.
- **SARIF**: um formato JSON padrão para resultados de análise de código. O
  GitHub o lê.
- **GitHub Code Scanning**: o recurso do GitHub que mostra alertas de análise
  na aba Security e no diff do PR.
- **Anotação**: uma linha como `::error file=...,line=...::mensagem` que o
  GitHub Actions transforma em marcação no diff.
- **OTLP**: o protocolo do OpenTelemetry, o padrão aberto de rastreamento
  (traces) e métricas.
- **Collector**: o programa do OpenTelemetry que recebe os dados e os envia
  para o seu backend (CloudWatch, Grafana, Datadog e outros).

## Para que serve

- Mostrar os findings no PR, no lugar onde a revisão acontece.
- Deixar o check vermelho quando aparece finding grave (`--fail-on`).
- Avisar quando uma regra cita uma fonte da AWS que pode ter mudado
  (`--source-freshness`).
- Exportar as chamadas de tool para o seu backend de observabilidade.
- Vigiar, num job agendado, as fontes oficiais que mudaram e o que isso arrasta.

## Quando usar e quando não usar

Use quando o repositório do job já roda `analyze` e `judge` e você quer o
resultado no PR, sem ninguém rodar nada à mão.

Não espere que o `report github` filtre "só os findings novos do PR": o próprio
Code Scanning compara com a análise da branch principal. E os findings **não**
são alertas de segurança; eles não entram na contagem de vulnerabilidades do
repositório.

## Pré-requisitos

- Um repositório no GitHub com o job (código PySpark e, se tiver, Terraform).
- Permissão para criar workflow.
- Para a aba Security: o workflow precisa de `security-events: write`. O
  exemplo já declara isso.

## Passo a passo

### 1. O que o `report github` faz

Ele pega os findings do `judge` e grava dois arquivos, com nomes fixos, em
`<repo>/.sparkforge/report/`:

- `sparkforge.sarif`: para o Code Scanning;
- `summary.md`: o resumo com **todos** os findings.

E imprime uma anotação por finding que tem linha no repositório.

Rodando o passo 4 da receita, a saída real é:

```text
sparkforge report github: 1 no SARIF, 5 sem localizacao, gate P0: disparou (.sparkforge/report/sparkforge.sarif, .sparkforge/report/summary.md)
::error file=a/main.tf,line=24,title=SF-ERR-006 P0::Permissão do Lake Formation negada em runtime, num job que lê o Data Catalog de outra conta
```

E o código de saída foi `1`, porque `--fail-on P0` encontrou P0.

O começo do `summary.md` gerado:

```markdown
# SparkForge: findings deste commit

| Severidade | Findings | No Code Scanning | Sem localizacao no repositorio |
|---|---|---|---|
| P0 | 5 | 1 | 4 |
| P1 | 1 | 0 | 1 |

**Gate:** `--fail-on P0`: disparou.
```

### 2. Por que alguns findings ficam fora do SARIF

O Code Scanning descarta resultado sem arquivo e linha. Então o finding sem
linha no repositório vai só para o resumo, **com o motivo**. Nenhum some. Trecho
real do resumo:

```markdown
## Sem localizacao no repositorio (5)

| Severidade | Regra | Motivo | Sujeito | Titulo |
|---|---|---|---|---|
| P0 | SF-BENCH-001 | `evidencia_ausente` | job_run `different_input_volume` | Comparação entre execuções com volumes de entrada diferentes ... |
| P0 | SF-PLAN-003 | `arquivo_fora_do_repo` | plan_node `(4) BroadcastNestedLoopJoin` | Join sem equi-condição — nested loop ou produto cartesiano |
| P0 | SF-PY-004 | `caminho_ambiguo` | source_location `processar` | Action ou write dentro de loop (medido: loop_depth=1) |
| P1 | SF-CTM-001 | `sem_linha` | source_location `PagamentosDiarios/ExtraiExtrato` | Job usa capacidade que a versão declarada do Control-M Automation API não tem |
```

Os motivos mais comuns:

| Motivo | Quer dizer |
|---|---|
| `runtime` | O finding veio da execução (event log, job run), e nada no código o localiza |
| `sem_linha` | Há arquivo, mas não há linha válida |
| `arquivo_fora_do_repo` | O arquivo não existe no repositório (por exemplo um `plan.txt` de execução) |
| `caminho_ambiguo` | O mesmo caminho existe em mais de uma `--source-root` |
| `evidencia_ausente` | Um fact citado pelo finding não foi passado em `--facts` |

A lista completa está em [github-code-scanning.md](../../github-code-scanning.md).

### 3. As opções que você vai usar

| Opção | Para quê |
|---|---|
| `--findings` | A saída de `judge --out` |
| `--facts` | Os facts da união do case. Repetível: passe os mesmos que foram ao `judge` |
| `--repo` | A raiz do repositório. A saída vai para `<repo>/.sparkforge/report/` |
| `--source-root` | Cada diretório que foi passado a um `analyze --path`, na mesma ordem. Repetível |
| `--fail-on P0` ou `P1` | Sai com código 1 quando há finding dessa severidade ou pior |
| `--category` | O nome da análise no Code Scanning |
| `--source-freshness` | Acrescenta ao resumo a seção "Fontes que pedem releitura" |
| `--as-of AAAA-MM-DD` | O dia de referência para o estado das fontes |

Códigos de saída: `0` sem gate disparado, `1` gate disparado, `2` erro de uso ou
de entrada.

`--source-root` é o ponto que mais confunde. `analyze pyspark --path jobs` grava
o caminho **relativo a `jobs/`** (`lib/job.py`). Por isso o `report github`
precisa receber `--source-root jobs` para achar `jobs/lib/job.py`.

### 4. Fontes que pedem releitura

```bash
sparkforge report github \
  --findings fixtures/sarif/misto/input/findings.json \
  --facts fixtures/sarif/misto/input/facts.json \
  --repo /tmp/sf_repo --source-root a --source-root b \
  --source-freshness --as-of 2026-09-13
```

Sem `--fail-on`, o gate fica desligado e a saída é `0`
(`gate off` na primeira linha). O resumo ganha esta seção (trecho real):

```markdown
## Fontes que pedem releitura (2)

| Severidade | Regra | Sujeito | Fonte | Estado | Datas |
|---|---|---|---|---|---|
| P0 | SF-PLAN-003 | plan_node `(4) BroadcastNestedLoopJoin` | https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-hints.html | `aging` | conferida 2026-07-31 (44 dias) |
...
2 finding(s) citam fonte nunca conferida por hash (`unverified`).
```

`aging` quer dizer que a fonte foi conferida há mais de 14 dias. `stale` quer
dizer que a fonte mudou depois que a regra foi validada. Detalhes em
[knowledge-freshness.md](../../knowledge-freshness.md).

### 5. O workflow

O arquivo [`examples/github/sparkforge.yml`](../../../examples/github/sparkforge.yml)
é o ponto de partida. O miolo dele:

```yaml
permissions:
  contents: read
  security-events: write

jobs:
  sparkforge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Instalar o SparkForge
        run: pip install sparkforge-aws
      - name: Extrair facts
        run: |
          mkdir -p .sparkforge
          sparkforge analyze pyspark --path jobs --out .sparkforge/facts-pyspark.json
          sparkforge analyze terraform --path infra --out .sparkforge/facts-terraform.json
      - name: Julgar
        run: |
          sparkforge judge \
            --facts .sparkforge/facts-pyspark.json \
            --facts .sparkforge/facts-terraform.json \
            --glue 5.0 \
            --out .sparkforge/findings.json
      - name: Projetar para o GitHub
        run: |
          sparkforge report github \
            --findings .sparkforge/findings.json \
            --facts .sparkforge/facts-pyspark.json \
            --facts .sparkforge/facts-terraform.json \
            --repo . --source-root jobs --source-root infra \
            --category sparkforge --fail-on P0 --source-freshness
      - name: Resumo do PR
        if: always() && hashFiles('.sparkforge/report/summary.md') != ''
        run: cat .sparkforge/report/summary.md >> "$GITHUB_STEP_SUMMARY"
      - name: Enviar ao Code Scanning
        if: always() && hashFiles('.sparkforge/report/sparkforge.sarif') != ''
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: .sparkforge/report/sparkforge.sarif
          category: sparkforge
```

Repare no `if: always()`: o SARIF sobe mesmo quando o gate deixa o check
vermelho. Assim o alerta chega à aba Security.

O próprio repositório do SparkForge usa esse passo num job real de CI
(`.github/workflows/ci.yml`, job que roda só por `workflow_dispatch`): ele roda
`report github` sobre as fixtures de `fixtures/sarif/`, sobe com
`github/codeql-action/upload-sarif@v3` e confere que o GitHub aceitou o mesmo
número de resultados que o SARIF tem.

### 6. Telemetria: `telemetry export`

Cada chamada de tool do SparkForge vira um span (um registro com início, fim e
atributos) em `.sparkforge/traces.db`. O `telemetry export` converte esses
spans para OTLP/JSON, que um Collector do OpenTelemetry lê.

```bash
# o processo que chama as tools grava com um run_id conhecido
export SPARKFORGE_RUN_ID=run_sessao_42
# ... use as tools (servidor MCP ou qualquer chamada a call_tool) ...

# depois, no mesmo diretório
sparkforge telemetry export --run-id run_sessao_42 --repo .
```

A saída tem nome fixo: `.sparkforge/telemetry/<run_id>.traces.jsonl` e
`.sparkforge/telemetry/<run_id>.metrics.jsonl`.

Se o run não tem spans, o verbo avisa e sai com código 2. Saída real num
diretório vazio:

```text
run 'run_exemplo' sem spans no ledger. Confira o SPARKFORGE_RUN_ID do processo que chamou as tools e rode, no diretorio onde ele gravou .sparkforge/traces.db: sparkforge telemetry export --run-id <run_id>
```

Duas opções mudam o que sai:

- `--host-transcript <arquivo.jsonl>`: acrescenta a sessão do agente (o
  "host"), com modelo e tokens. **Sem transcript não há token**: o projeto não
  estima token a partir de bytes.
- `--provider`: declara quem forneceu o modelo (`anthropic`, `aws.bedrock`,
  `gcp.vertex_ai`). Sem ele, o atributo fica em `unresolved` e a métrica de
  token não sai.

Configuração mínima do Collector (de [opentelemetry.md](../../opentelemetry.md)):

```yaml
receivers:
  otlp_json_file/traces:
    include: [/caminho/do/repo/.sparkforge/telemetry/*.traces.jsonl]
    start_at: beginning
  otlp_json_file/metrics:
    include: [/caminho/do/repo/.sparkforge/telemetry/*.metrics.jsonl]
    start_at: beginning
exporters:
  otlphttp:
    endpoint: https://seu-backend
service:
  pipelines:
    traces:  {receivers: [otlp_json_file/traces],  exporters: [otlphttp]}
    metrics: {receivers: [otlp_json_file/metrics], exporters: [otlphttp]}
```

### 7. Vigiar fontes que mudaram: `knowledge drift`

As regras citam páginas oficiais (AWS, Apache). O lock
`knowledge/sources.lock.json` guarda o estado de cada uma. O `knowledge drift`
diz, para cada fonte que mudou, quais regras, documentos, fixtures, evals e
agents a leram antes da mudança. Não acessa a rede.

```bash
sparkforge knowledge drift --as-of 2026-09-13
```

Saída real hoje (nenhuma fonte com mudança registrada no lock):

```json
{
  "as_of": "2026-09-13",
  "lock": {"sources": 247, "checked": 21, "pinned": 15, "changed": 0},
  "changed_sources": [],
  "totals": {"rules": 0, "docs": 0, "goldens": 0, "evals": 0, "agents": 0},
  "unresolved": [],
  "refused": [
    {"field": "conteudo_da_mudanca", "reason": "exige_leitura_humana_da_fonte"}
  ]
}
```

O `refused` é honesto: o lock guarda o hash da página inteira, então o radar
não sabe se a mudança tocou o trecho que a regra cita. Isso exige leitura
humana. Os números do bloco `lock` mudam com o tempo; o que importa é o formato.

Um job agendado de exemplo (monte a partir dele; ele usa só comandos
conferidos acima):

```yaml
name: sparkforge-drift
on:
  workflow_dispatch:
  schedule:
    - cron: "0 6 * * 1"   # segunda-feira, 06:00 UTC
permissions:
  contents: read
jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e .
      - name: Knowledge drift
        run: sparkforge knowledge drift > drift.json
      - uses: actions/upload-artifact@v4
        with:
          name: knowledge-drift
          path: drift.json
```

Rode-o num clone do SparkForge. Instalado só pelo pip, o pacote não traz
`fixtures/`, `evals/` nem `agents/`, e esses saltos saem `unresolved` com
`sem_repositorio`, nunca como lista vazia.

O repositório do SparkForge tem o seu próprio job semanal,
`.github/workflows/refresh-knowledge.yml`. Ele é o único que acessa a rede:
confere as fontes, atualiza o lock e abre um PR para uma pessoa revisar.

## Como ler o resultado

- **"Sem localizacao no repositorio"** não é erro: é o finding que o Code
  Scanning não aceitaria, listado com o motivo. SARIF mais essa lista dá sempre
  o total.
- **`gate ... disparou`** e código 1: há finding da severidade pedida. O check
  fica vermelho de propósito.
- **`unresolved`** na telemetria: um atributo que ninguém declarou (provider,
  modelo). O projeto não preenche por palpite.
- **`refused`** no drift: o que o verbo não pode concluir sem uma pessoa ler.

## Erros comuns

- **Esquecer `--source-root`.** Os findings de código caem em
  `arquivo_fora_do_repo`. Passe as mesmas raízes dos `analyze --path`, na mesma
  ordem.
- **`--source-root` absoluta ou fora do `--repo`.** É erro de uso (código 2).
- **Passar ao `report github` só parte dos facts.** Findings viram
  `evidencia_ausente`. Passe todos os que foram ao `judge`.
- **Faltar `security-events: write`.** O upload do SARIF falha.
- **Versionar `.sparkforge/report/`.** São arquivos gerados; ponha no
  `.gitignore`.
- **Rodar `telemetry export` em outro diretório.** Rode onde o processo gravou
  `.sparkforge/traces.db`, com o mesmo `SPARKFORGE_RUN_ID`.

## Para ir além

- Guia completo do Code Scanning: [github-code-scanning.md](../../github-code-scanning.md).
- Telemetria em detalhe: [opentelemetry.md](../../opentelemetry.md).
- Estados das fontes e o radar de drift: [knowledge-freshness.md](../../knowledge-freshness.md).
- Referência dos comandos: [`report`](../referencia/cli/report.md),
  [`telemetry`](../referencia/cli/telemetry.md), [`knowledge`](../referencia/cli/knowledge.md).
- Tools MCP equivalentes (elas devolvem o conteúdo, mas **não gravam**; gravar é
  da CLI):
  [`sparkforge_report_github`](../referencia/tools/sparkforge_report_github.md),
  [`sparkforge_telemetry_export`](../referencia/tools/sparkforge_telemetry_export.md),
  [`sparkforge_knowledge_drift`](../referencia/tools/sparkforge_knowledge_drift.md).
- Skill [`aws-observability`](../referencia/skills/aws-observability.md): se o
  seu backend de telemetria é o CloudWatch ou o X-Ray.

## Próximos passos

1. Ainda não gera os findings? Comece por [Job lento](job-lento.md).
2. Quer saber quanto contexto uma sessão gastou? Veja [Economia de contexto](economia-de-contexto.md).
3. Quer provar que uma mudança do PR funcionou? Veja [Mudanças com prova](mudancas-com-prova.md).
