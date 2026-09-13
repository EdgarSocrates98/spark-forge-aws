# Control-M: revisar a definição dos jobs

**Control-M** é o agendador corporativo da BMC: ele decide quando cada job roda,
em que ordem e depois de qual evento. Este manual mostra como o SparkForge lê a
definição desses jobs e confere três coisas: **dependência** entre jobs,
**janela** de agendamento e **eventos**. Ele também diz se a versão do Control-M
que você usa tem as capacidades que a definição pede.

O SparkForge **não** chama o Control-M nem a BMC e não lê execução. Ele lê só o
arquivo de definição.

Todos os exemplos usam arquivos sintéticos de `fixtures/controlm/`.

## Receita rápida

```bash
# 1. O que vale na versão do Automation API do seu ambiente
sparkforge controlm describe --version 9.0.21.300 --detail-level compact

# 2. Extrair os facts da definição, declarando a versão do ambiente alvo
mkdir -p /tmp/sf
sparkforge analyze controlm-jobs \
  --path fixtures/controlm/capacidade_abaixo_da_fronteira/input \
  --version 9.0.21.300 --out /tmp/sf/facts_ctm.json

# 3. Julgar contra o catálogo de regras
sparkforge judge --facts /tmp/sf/facts_ctm.json

# 4. Vai trocar de versão? Veja o que muda em cada degrau
sparkforge migrate controlm fixtures/controlm/capacidade_acima_da_fronteira/input \
  --from 9.0.22.010 --to 9.0.21.300
```

Nesse exemplo o `judge` acusa `SF-CTM-001`: o job usa um tipo que a versão
`9.0.21.300` ainda não tem.

## Palavras que aparecem aqui

- **Jobs-as-Code**: o formato JSON em que o Control-M descreve pastas, jobs e
  agendamentos. É o artefato que o SparkForge lê.
- **Automation API**: a interface de automação do Control-M. Ela tem versão
  própria, na grafia `9.0.2x.yyy`. Essa versão **não** é a versão do produto
  Control-M, mesmo com a mesma grafia.
- **Folder**: uma pasta que agrupa jobs.
- **Evento**: um sinal nomeado. Um job publica (`AddEvents`) e outro espera
  (`WaitForEvents`).
- **Flow**: uma sequência declarada de jobs.
- **Janela (`When`)**: quando o job pode rodar: dias, datas, horário de início e
  de fim.

## Para que serve

- Ver a definição como facts: pastas, jobs, agendamentos, dependências, ações
  condicionais e variáveis.
- Achar defeitos que a documentação da BMC declara: capacidade ausente na
  versão, lista de datas acima do teto, parênteses aninhados na lógica de
  eventos e outros.
- Saber o que ganha e o que perde ao subir ou descer a versão do Automation API.

## Quando usar e quando não usar

Use ao revisar um pull request que muda definições do Control-M, antes de
promover definições para um ambiente com outra versão, e antes de uma troca de
versão do Automation API.

Não use para investigar uma execução que falhou: o SparkForge não lê log nem
histórico do Control-M. E não use para desempenho do job Spark que o Control-M
dispara: para isso veja [Job lento](job-lento.md).

## Pré-requisitos

- SparkForge instalado ([Instalação](../02-instalacao.md)).
- O JSON de **Jobs-as-Code** das suas definições (um arquivo ou um diretório de
  `*.json`). É o mesmo arquivo que o comando `ctm build` do Control-M valida;
  normalmente ele já mora no repositório da esteira.
- A versão do **Automation API** do ambiente alvo. Você precisa declará-la: o
  JSON não a traz.

A faixa de versões coberta é `9.0.21.200` a `9.0.22.100`.

## Passo a passo

### 1. O que vale na sua versão: `controlm describe`

```bash
sparkforge controlm describe --version 9.0.21.300 --detail-level compact
```

Trecho real:

```json
{
  "domain": "controlm_automation_api",
  "version": "9.0.21.300",
  "covers": {"from": "9.0.21.200", "to": "9.0.22.100"},
  "capabilities": [
    "agentless_host_configuration",
    "config_em_high_availability",
    ...
  ],
  "deprecated": {
    "config_em_param_set": {
      "summary": "`config em:param::set` esta depreciado a partir desta versao.",
      "boundary": "deprecated_from",
      "declared_at": "9.0.21.300",
      "replaced_by": "config systemsettings::set"
    },
    ...
```

`--detail-level` aceita `minimal`, `compact` e `full` (o padrão). Versão fora
da faixa é recusada, com o intervalo:

```bash
sparkforge controlm describe --version 9.0.20.000
```

```text
versao '9.0.20.000' fora da faixa que esta matriz sustenta: 9.0.21.200 a 9.0.22.100. A faixa e passado FECHADO e nao se extrapola -- ...
  A matriz e do Control-M AUTOMATION API, nao do produto Control-M:
  as duas coisas usam a grafia `9.0.2x.yyy` e nao sao a mesma.
    sparkforge controlm describe --version 9.0.21.200
```

### 2. Extrair os facts: `analyze controlm-jobs`

```bash
sparkforge analyze controlm-jobs \
  --path fixtures/controlm/capacidade_abaixo_da_fronteira/input \
  --version 9.0.21.300 --out /tmp/sf/facts_ctm.json --detail-level summary
```

Contagem real por kind:

```json
  "by_kind": {
    "ctm.action": 1,
    "ctm.analyzed": 1,
    "ctm.capability_incompatible": 1,
    "ctm.dependency": 3,
    "ctm.folder": 1,
    "ctm.job": 2,
    "ctm.schedule": 2,
    "ctm.variable": 2,
    "ctm.version_declared": 1
  },
```

Dentro do `--out`, é assim que dependência, janela e variável aparecem (trechos
reais):

```json
{"kind": "ctm.dependency", "attrs": {"direction": "wait", "event": "EXTRATO-PRONTO", "container": "job"}}
{"kind": "ctm.dependency", "attrs": {"direction": "add", "event": "EXTRATO-PRONTO", "container": "job"}}
{"kind": "ctm.dependency", "attrs": {"direction": "sequence", "container": "Flow", "flow": "Sequencia",
                                     "sequence": ["ExtraiExtrato", "ConciliaExtrato"]}}
{"kind": "ctm.schedule",   "attrs": {"from_time": "0300", "to_time": "0600"}}
{"kind": "ctm.variable",   "attrs": {"name": "TOKEN_DO_PORTAL", "value": "<redigido>", "redacted": true,
                                     "secret_pattern_match": true}}
```

Repare na última linha: um valor com cara de segredo sai **redigido** no fact.
O segredo nunca entra no `facts.json`.

### 3. Julgar: `judge`

```bash
sparkforge judge --facts /tmp/sf/facts_ctm.json
```

Resumo real: um finding.

```text
SF-CTM-001 P1 Job usa capacidade que a versão declarada do Control-M Automation API não tem
           sujeito: PagamentosDiarios/ExtraiExtrato
```

A explicação do finding diz qual capacidade, qual fronteira, em qual versão ela
foi lida e qual versão foi declarada. Aqui, o job usa o tipo
`Job:DetachedEmbeddedScript`, que só existe a partir de `9.0.22.005`.

As regras de janela e de eventos rodam sobre outras fixtures. Resumo real de
`judge` sobre `janela_acima_do_teto_de_datas` e `evento_com_parenteses_aninhados`
(as duas analisadas com `--version 9.0.22.010`):

```text
SF-CTM-005 P1 Parênteses aninhados na expressão de eventos
           sujeito: ConciliacaoDiaria/Concilia/EsperaAsCargas
           medido: {"max_paren_depth": 2, "open_paren_count": 2, "close_paren_count": 2, "operator_count": 2}
SF-CTM-003 P2 Lista de SpecificDates acima do teto que a fonte publica
           sujeito: FechamentoContabil/ApuraImpostos
           medido: {"months_count": 1, "month_days_count": 1, "week_days_count": 1, "specific_dates_count": 401}
```

As regras da área, pelo título (`sparkforge rules lookup --id SF-CTM-00N`):

| Regra | O que confere |
|---|---|
| SF-CTM-001 | Job usa capacidade que a versão declarada do Control-M Automation API não tem |
| SF-CTM-002 | SpecificDates sem anular WeekDays, Months ou MonthDays |
| SF-CTM-003 | Lista de SpecificDates acima do teto que a fonte publica |
| SF-CTM-004 | Job definido em array depende do system setting allowDuplicateJobNames |
| SF-CTM-005 | Parênteses aninhados na expressão de eventos |

### 4. Trocar de versão: `migrate controlm`

```bash
sparkforge migrate controlm fixtures/controlm/capacidade_acima_da_fronteira/input \
  --from 9.0.22.010 --to 9.0.21.300
```

O verbo percorre cada versão do caminho. Descer de versão é um caso legítimo.
Trecho real do degrau que quebra:

```json
{"from": "9.0.22.005", "to": "9.0.22.000", "gate": "incompatible",
 "changes": [{"capability": "job_detached_embedded_script", "boundary": "introduced_in",
              "severity": "break", "declared_at": "9.0.22.005",
              "summary": "O job type `Job:DetachedEmbeddedScript` roda um script embutido como processo em background.",
              "replaced_by": null}]}
```

No sentido contrário (`--from 9.0.21.300 --to 9.0.22.010`), o mesmo degrau
aparece como `"severity": "gain"` e todos os degraus saem `compatible`.

## Como ler o resultado

- **Sem `--version`, o cruzamento não acontece, e isso é dito.** A capacidade
  sai como `ctm.capability_unresolved`:

  ```json
  {"capability": "job_detached_embedded_script", "reason": "version_not_declared",
   "unblocked_by": "declare a versao do Control-M Automation API com `--version <v>` -- o JSON de Jobs-as-Code nao a carrega, e deduzi-la do conteudo seria adivinhar"}
  ```

  E o `judge --show-skipped` mostra a regra pulada e o motivo:

  ```json
  {"rule_id": "SF-CTM-001", "reason": "requires_facts", "missing": ["ctm.version_declared"]}
  ```

  Isso é qualidade: o projeto separa "não há problema" de "não perguntei" (veja
  [Recusa nomeada](../01-conceitos.md#recusa-nomeada)).
- **`skipped` com `requires_facts`**: a regra precisa de um fact que esta
  definição não produz. Ela não foi reprovada nem aprovada.
- **`gate: incompatible`** num degrau de `migrate controlm`: aquele passo de
  versão remove algo que a definição usa.

## Erros comuns

- **Rodar sem `--version`.** A regra de capacidade fica pulada. Declare a versão
  do ambiente **alvo**.
- **Usar a versão do produto Control-M.** O que vale é a versão do Automation
  API.
- **Versão fora da faixa coberta.** O comando recusa. Use uma versão dentro de
  `9.0.21.200` a `9.0.22.100`.
- **Achar que o SparkForge validou a execução.** Ele lê a definição. Falha de
  execução está no Control-M.

## Para ir além

- Agent [`sf-runtime-specialist`](../referencia/agents/sf-runtime-specialist.md):
  cobre a área `SF-CTM` dentro de uma migração.
- Referência dos comandos: [`analyze`](../referencia/cli/analyze.md),
  [`controlm`](../referencia/cli/controlm.md), [`migrate`](../referencia/cli/migrate.md),
  [`judge`](../referencia/cli/judge.md), [`rules`](../referencia/cli/rules.md).
- Tools MCP equivalentes:
  [`sparkforge_analyze_controlm_jobs`](../referencia/tools/sparkforge_analyze_controlm_jobs.md),
  [`sparkforge_controlm_describe`](../referencia/tools/sparkforge_controlm_describe.md),
  [`sparkforge_migration_assess`](../referencia/tools/sparkforge_migration_assess.md).

## Próximos passos

1. Leve os findings para o pull request da esteira: [CI e GitHub](ci-e-github.md).
2. Migrando também o runtime do job Spark? Veja [Migração de versão](migracao-de-versao.md).
