# Guia de Uso — SparkForge AWS

> Manuais passo a passo por tarefa, para quem está começando: [Guia do SparkForge](docs/guia/README.md).
> Este arquivo continua como guia de integração com Claude Code, Devin e Copilot.

## 1. Começo recomendado

Abra a ferramenta no repositório que contém:

- Terraform do Glue;
- entrypoint do job;
- biblioteca Python;
- testes;
- exemplos de logs ou planos.

Cole ou invoque o conteúdo de `PROMPT_INICIAL_MESTRE.md`.

## 1.1 Forge Lab / Digital Twin

Para construir evidência reproduzível de um caso streaming ou batch, consulte o
[guia operacional do Forge Lab](docs/guia/forge-lab.md). O caminho mínimo é:

```bash
sparkforge-aws lab doctor
sparkforge-aws lab verify --repo .
sparkforge-aws lab scenarios --json --repo .
sparkforge-aws lab plan iceberg-small-files --backend compose --seed 42 --repo .
```

O Lab é plan-only por padrão. `run`, `up`, `down`, `shell` e `gc` só podem
mutar ambiente local com `--execute --confirm`; execução AWS é tier separado e
recusada pelo core offline. O Golden 20, receipts, oracle independente e limites
de prova estão descritos no [contrato do produto](docs/knowledge/forge-lab-product.md).

## 1.2 Streaming, CDC e SLO observado

Para um caso streaming, use `streaming-realtime-architect` ou
`cdc-contract-reviewer` conforme a rota devolvida por `sparkforge-aws next-step`.
Extraia progress, transporte, checkpoint, CDC, Flink ou Glue separadamente e
componha somente depois. A avaliação SLO offline usa a mesma superfície para
progress Structured Streaming e para `kafka.lag`/`kinesis.shard`:

```bash
sparkforge-aws analyze streaming --path progress.jsonl --artifact progress --out progress.facts.json
sparkforge-aws analyze transport --path kafka.json --artifact kafka --out transport.facts.json
sparkforge-aws analyze streaming-ops --path slo-contract.json --out slo-contract.facts.json
sparkforge-aws analyze streaming-composition \
  --facts slo-contract.facts.json --facts transport.facts.json \
  --mode slo --slo-name consumer-lag --transport-key orders-group \
  --out slo-evaluation.facts.json

# saída do sink Structured Streaming
sparkforge-aws analyze streaming-composition \
  --facts slo-contract.facts.json --facts progress.facts.json \
  --mode slo --slo-name output-rows --query-name orders-query \
  --sink-name orders-sink --out sink-slo.facts.json
```

`met`/`violated` valem apenas para a série diretamente observada, com identidade,
unidade, timestamps e janela coberta. Sink usa `num_output_rows` e exige vínculo
único com batch por `batch_id`/`query_name`; `streaming.slo.unresolved` permanece
na saída quando falta evidência. `statistic: p95` usa nearest-rank sobre a
amostra e `freshness_ms` exige `timestamp` + `eventTime.max`; isso continua
offline e não prova consulta live, causalidade, custo ou latência end-to-end.

Para declarar a composição cross-engine de um pipeline, use selectors exatos e
facts já extraídos:

```bash
sparkforge-aws analyze streaming-composition \
  --facts cdc-facts.json --facts kafka-facts.json --facts flink-facts.json \
  --facts iceberg-facts.json --mode pipeline \
  --pipeline-path orders-pipeline.json --out pipeline-facts.json
```

O contrato só verifica node com um match de `kind`/atributos e edge com dois
endpoints verificados. Zero ou múltiplos matches permanecem
`streaming.pipeline.unresolved`; isso não é topologia descoberta nem prova de
latência, throughput, causalidade, exactly-once ou saúde.

Para revisar drift entre Glue Streaming efetivo e Terraform, use os facts já
extraídos e o compositor geral:

```bash
sparkforge-aws analyze glue-streaming --path effective-job.json --out glue.facts.json
sparkforge-aws analyze terraform --path infra/ --out terraform.facts.json
sparkforge-aws fuse --facts glue.facts.json --facts terraform.facts.json --out fused.facts.json
sparkforge-aws judge --facts fused.facts.json --show-skipped
```

O vínculo exige `aws_glue_job.name` literal e único. O resultado preserva
`glue.streaming.terraform_link`, `source_fact_ids`, `drifts` e
`unresolved_fields`; compare `glue_version`, RTM, linguagem e workers. Drift
vira `SF-GLUESTREAM-004`; identidade ou parâmetro ausente vira
`SF-GLUESTREAM-005`. Isso continua evidência offline, não prova que o job em
produção executa com a configuração declarada.

Se houver histórico terminal sanitizado, componha-o com a definição efetiva:

```bash
sparkforge-aws analyze glue-job-runs --path .sparkforge_aws/artifacts/glue_job_run --out runs.facts.json
sparkforge-aws fuse --facts glue.facts.json --facts runs.facts.json --out runtime.facts.json
sparkforge-aws judge --facts runtime.facts.json --show-skipped
```

Leia `glue.streaming.runtime_link`, `observed_run_ids`, `drifts` e
`source_fact_ids`. `SF-GLUESTREAM-006` é drift entre definição e run;
`SF-GLUESTREAM-007` é evidência insuficiente. Duração e DPU continuam facts de
execução, não latência de evento ou saúde do streaming.

O mesmo dump pode declarar endpoints em `stream.sources`/`source` e
`stream.sinks`/`sink`. O analyzer emite `glue.streaming.source` e
`glue.streaming.sink` com atributos escalares e medidas presentes, e emite
`glue.streaming.unresolved` quando o bloco está ausente, inválido ou não traz
métrica. Não derive endpoint de `source_type`; não trate contador ou commit como
throughput, saúde ou exactly-once sem janela e timestamp.

Para coletar contratos do Glue Schema Registry, use a operação read-only com
identidade de registry ou schema. Ela pagina resultados, captura metadata e
latest version, grava manifesto/cache local e limita a definição; não executa
create, update ou delete na AWS:

```bash
sparkforge-aws collect schema-registry --repo . --registry-name events --now 2026-10-03T00:00:00Z
sparkforge-aws analyze schema-registry --path .sparkforge_aws/artifacts/schema_registry/events.json
```

Definição ausente, inválida ou acima do limite é `unresolved`, não contrato
inventado. Veja [`knowledge/schema-registry-data-contracts.md`](knowledge/schema-registry-data-contracts.md)
e a [referência da tool MCP](referencia/tools/sparkforge_collect_schema_registry.md).

Para analisar um dump Apache Flink, preserve os endpoints explicitamente antes
de correlacionar com checkpoint, operator e transporte:

```bash
sparkforge-aws analyze flink --path flink-dump.json --artifact flink --out flink.facts.json
sparkforge-aws judge --facts flink.facts.json --show-skipped
```

O resultado pode conter `flink.source`, `flink.sink` e `flink.metric` com identidade,
connector, `delivery_semantics` e medidas observadas. Contadores não viram
throughput sem timestamp/janela; ausência dos blocos vira
`flink.unresolved` (`source_metrics_missing`/`sink_metrics_missing`). Pontos
em `metrics`/`metrics.observations` precisam de nome, valor numérico e timestamp
textual para emitir `flink.metric`; inválidos ficam unresolved. Isso não prova
exactly-once nem saúde. Para Managed Flink use `--artifact managed_flink`;
os namespaces não se completam. O upstream segue sem collector live ou série
longa; a janela temporal bounded do serviço gerenciado publica
`managed_flink.metric`.

Para coletar observabilidade temporal bounded sem misturar namespaces, use os
collectors read-only existentes com as duas pontas da janela:

```bash
sparkforge-aws collect streaming-integrations --repo . --kinesis-stream orders \
  --metrics-start 2026-10-02T00:00:00Z \
  --metrics-end 2026-10-02T00:05:00Z --metrics-period 60 \
  --now 2026-10-02T00:10:00Z

sparkforge-aws collect managed-flink --repo . --application-name orders \
  --region us-east-1 \
  --metrics-start 2026-10-03T00:00:00Z \
  --metrics-end 2026-10-03T02:00:00Z --metrics-period 60 \
  --now 2026-10-03T02:05:00Z
```

O primeiro preserva cinco métricas stream-level como `kinesis.metric`; o
segundo preserva cinco métricas application-level do namespace
`AWS/KinesisAnalytics` como `managed_flink.metric`. Observações, unidade,
estatística, timestamp, raw e lacunas permanecem no artifact. Ausência ou
resposta inválida é `unresolved`, nunca zero; enhanced/shard-level, dimensões
detalhadas Managed Flink, job plan, replay, benchmark e saúde end-to-end ficam
fora do contrato.

## 2. Claude Code

Use o agente:

```text
Use o agente glue-incremental-performance-architect e siga o PROMPT_INICIAL_MESTRE.md.
```

Ou:

```text
/glue-incremental-performance-architect
```

## 3. Devin

Use:

```text
Leia PROMPT_INICIAL_MESTRE.md e use a skill glue-incremental-performance-architect.
Não faça tuning isolado antes de mapear a biblioteca, os dois fluxos e o OOM.
```

### 3.1 Onde os perfis moram

O Devin CLI e o Devin Local agent do Devin Desktop despacham subagente, e leem os
perfis deste repositório sem nenhuma configuração adicional:

| O que | Onde | Como o Devin lê |
|---|---|---|
| Os 14 coordenadores | `.agents/agents/<nome>.md` | caminho de descoberta nativo ("Also supported" na aba *Project-specific*), no layout *flat file* documentado |
| Os mesmos 14 | `.claude/agents/<nome>.md` | importados do formato do Claude Code — *"Each `.md` file becomes a subagent profile"* |
| As 60 skills | `.agents/skills/<nome>/SKILL.md` | caminho de descoberta nativo, não convenção deste repositório |
| Os 5 executores | `.agents/agents/executors/<nome>.md` | **a fonte não documenta este layout.** Ver abaixo |

**Os cinco executores não estão num layout de descoberta documentado, e isto é medição,
não suposição.** A fonte descreve **dois** layouts de perfil customizado — *flat file*
`agents/<nome>.md` e *directory* `agents/<nome>/AGENT.md` (com `AGENTS.md`, `agent.md` e
`agents.md` também aceitos, nessa precedência) — e a importação do Claude Code casa
`.claude/agents/*.md`, que é raso. `executors/sf-judge.md` não é nenhum dos dois: pelo
layout *directory*, `executors/` só publicaria um perfil chamado `executors` se tivesse
dentro um `AGENT.md`, e não tem. Se a varredura é recursiva, a documentação não diz —
é a mesma ambiguidade do `agents/` da raiz (V-DV-7), e vale a mesma regra: **não presuma**.

**O que isso não muda.** Os executores continuam alcançáveis em toda plataforma pelo
`playbook`, que lê `agents/executors/` do repositório e devolve a decomposição do
coordenador nos cinco passos — o caminho que não depende de descoberta nenhuma:

```bash
sparkforge-aws playbook emr-infra-reviewer --repo .
```

`.claude/agents/` e `.agents/agents/` — executores inclusive — são **espelhos gerados** de
`agents/`, que é a fonte; `.agents/skills/` é espelho de `skills/`. Nunca edite um
espelho: `python scripts/sync_skills.py --check` recusa. Os dois de perfil não são gerados
do mesmo jeito. `.claude/agents/` é cópia byte a byte, com `tools:` e tudo. `.agents/agents/` é
**renderizado**: sai **sem `tools:`** (o mapeamento dos valores do campo do Claude Code
para os nomes de tool do Devin não está documentado, e chute em campo de permissão
concede ou nega errado) e **nunca com `model:`** (o modelo do subagente resolve por
roteador no momento do spawn, e um admin da organização o sobrescreve — escrever um
literal seria fingir controle). O corpo do perfil, o `name` e o `description` são os
mesmos nos dois: o Devin acha o mesmo perfil pelos dois caminhos, e a documentação dele
não declara qual tem precedência quando os dois existem — o que muda entre eles é
apenas a presença de `tools:`.

**Não conte com essa omissão como fronteira.** Os dois caminhos estão ligados por
default (`read_config_from` tem `agents_standard` e `claude`, ambos `true`), a fonte não
diz qual vence, e o default de `allowed-tools` é *"all tools"* — omitir é a opção **mais
permissiva**, não a mais restrita, e o perfil pode chegar pelo `.claude/agents/`
carregando o campo. O motivo da omissão é outro, e é de honestidade: o **mapeamento de
valores** não está documentado (`Bash` → `exec`?), e chutar em campo de permissão erra
nos dois sentidos. Uma coisa que a fonte **diz**, e que é sobre nome de campo e não sobre
qual arquivo vence: `tools` (Claude Code) e `allowed-tools` (Devin) são ambos aceitos.
Quem carrega a fronteira é o `## Não faz` do corpo do perfil, igual byte a byte nos dois
espelhos — e, nas doze skills despacháveis, o parágrafo de despacho da seção
`## Protocolo`.

Não presuma que o `agents/` da **raiz** seja varrido: a documentação lista
`.devin/agents/` e `.agents/agents/`, e a frase do changelog ("your project's `agents/`
directory") é ambígua.

**Por que `.agents/` e não `.devin/`, já que a fonte lista `.devin/agents/` primeiro.**
Escolha, não lacuna, e o critério é o número de espelhos. `.agents/` é o padrão
multiferramenta que a própria Cognition declara suportar (*"We support the `.agents`
skills standards, so third-party skill installation tools work with Devin CLI"*), está
ligado por default (`read_config_from.agents_standard`), e **um só** diretório serve
perfis **e** skills — `.devin/agents/` só serviria perfis, e as skills continuariam em
`.agents/skills/` de qualquer forma. Publicar nos dois seria um quarto espelho a manter
em sincronia, que só o Devin leria, para chegar ao mesmo lugar. Se um dia a fonte
declarar precedência de `.devin/` sobre `.agents/`, a decisão se inverte com o mesmo
argumento — e aí é acrescentar uma raiz em `AGENT_MIRRORS`, com `platform_for` já
derivando a plataforma do próprio alvo.

**Um coordenador despachado como subagente não despacha os cinco executores.** Por
default *"subagents cannot spawn their own subagents — only the root agent can"*, e as
tools `run_subagent`/`read_subagent` são **removidas** de dentro de um subagente; o
`max-nesting` que reverteria isso este repositório **não declara** em perfil nenhum. Na
prática: pedir o perfil como subagente entrega o **método** do coordenador (o corpo, o
`## Não faz`, as áreas de regra), e a decomposição em executores tem de rodar **inline**
— que é exatamente o que `sparkforge-aws playbook <coordenador>` devolve, em ordem. Em Claude
Code o coordenador despacha os executores; no Devin, não conte com isso.

No Devin Desktop o recorte é mais estreito: subagente é capacidade do **Devin Local
agent**, sob o toggle *Subagents (Preview)*. As páginas do motor Cascade não mencionam
subagente. Fora do Devin Local agent com o toggle ligado, a coordenação no Desktop é
`playbook`.

### 3.2 Quais skills despacham, e a que não despacha de propósito

**A lista autoritativa é `DISPATCHABLE_SKILLS` em `scripts/sync_skills.py`**, e não este
parágrafo: o conjunto cresceu a cada fase que acrescentou skill, e um número copiado aqui
envelhece em silêncio. O que não muda é o critério, e é ele que decide os casos duvidosos.

O recorte medido quando esta seção foi escrita — **doze das vinte** skills de então — era: as
cinco `review-*` (`review-emr-cluster`, `review-emr-eks`, `review-data-validation`,
`review-glue-terraform`, `review-pyspark-pr`), as quatro `analyze-*`
(`analyze-spark-plan`, `analyze-spark-ui`, `analyze-batch-loop`,
`analyze-library-call-graph`), `diagnose-oom`, `diagnose-data-skew`,
`optimize-pyspark-code` e `optimize-parquet-layout`. São as investigações fechadas: o
subagente coleta, julga sobre artefato, e o pai lê e resume o resultado.

Uma parte delas declara também `agent:`, e a regra é mecânica — `agent:` sai quando **um só**
coordenador declara a skill no `skills:` dele, e cala quando há mais de um. `review-emr-cluster`
e `review-emr-eks` são as duas de EMR, e as duas apontam para `emr-infra-reviewer`, que é o
dono das três plataformas; `review-data-validation` → `data-quality-reviewer`. Onde `agent:`
não tem resposta única, o Devin escolhe o perfil, que é a forma documentada (o campo tem
default *none*).

As ambíguas o são por serem declaradas por dois a quatro coordenadores. Uma delas não é, e a
razão dela é diferente — `diagnose-oom`, e a razão dela é diferente: ela **era** declarante único, mas só porque
`spark-performance-architect` não a lista no `skills:` dele — embora liste
`diagnose-data-skew`, `analyze-spark-ui` e `tune-glue-job`, toda a vizinhança do mesmo
diagnóstico. Omissão numa lista pré-existente não é juízo de competência, e o perfil que
sobrava era o `glue-incremental-performance-architect`, cuja skill homônima este
repositório declara **não-despachável** justamente por orquestrar as outras via
`next-step`. Publicar aquele `agent:` seria roteamento mecânico com cara de decisão — o
mesmo defeito que a ordem alfabética produziria.

**`sparkforge-aws-diagnose` não despacha, de propósito.** Ela abre o case e roteia, e o
ciclo de vida do case é o que faz a investigação atravessar sessões e ferramentas.
Despachá-la jogaria esse ciclo de vida para um contexto que **não volta**: um subagente
Devin não herda o histórico do pai, devolve texto livre sem contrato de saída, e some
quando termina. Pela mesma razão ficam de fora `glue-incremental-performance-architect`
(orquestra as outras skills, e subagente não gera subagente por default) e as skills
cujo método depende de perguntar — `optimize-iceberg-table`, `optimize-latest-per-key`,
`design-incremental-processing`: `ask_user_question` é **sempre negado** a um subagente.

### 3.3 Quando o despacho estiver desligado

Nenhum arquivo deste repositório liga ou desliga subagentes. `subagents_enabled` é
chave de usuário (não de projeto), e um admin da organização pode escolher *None* em
"Default subagent model", que desliga o despacho por completo. A própria Cognition
declara custom subagents **experimentais**. Nos três casos o caminho é o mesmo da
seção 5: `sparkforge-aws playbook <coordenador>`, que é o piso e não depende de despacho.

### 3.4 Ligar o servidor MCP no Devin

`parity.yaml` declara `mcp` para `devin_cli` e `devin_desktop`. Isto é **como** acioná-lo
— sem esta seção, a declaração seria capacidade afirmada sem caminho, que é o defeito do
transporte HTTP da Fase 1 que este repositório cita como razão de ser da regra.

**Devin CLI — stdio.** O arquivo de MCP do Devin é dedicado, e a chave é a mesma do resto
do ecossistema:

| Escopo | Caminho |
|---|---|
| Projeto | `.devin/mcp_config.json` |
| Projeto, fora do git | `.devin/mcp_config.local.json` |
| Global | `~/.config/devin/mcp_config.json` (`%APPDATA%\devin\mcp_config.json` no Windows) |

```jsonc
// .devin/mcp_config.json
{
  "mcpServers": {
    "sparkforge-aws": {
      "command": "python",
      "args": ["-m", "sparkforge_aws.adapters.mcp", "--transport", "stdio"]
    }
  }
}
```

Ou pela própria CLI, sem editar arquivo:

```bash
pip install "sparkforge-aws[mcp]"
devin mcp add -s project sparkforge-aws -- python -m sparkforge_aws.adapters.mcp --transport stdio
devin mcp list
```

**Não conte com o `.mcp.json` da raiz para isto, e a razão é medida.** O Devin importa
configuração de MCP do Claude Code (`read_config_from.claude`, default `true`, e a tabela
de importação lista `.mcp.json`). Mas o `.mcp.json` deste repositório é o do **plugin do
Claude Code**: ele parametriza `PYTHONPATH` e `SPARKFORGE_CATALOG` por
`${CLAUDE_PLUGIN_ROOT}`, que é variável do carregador de plugin do Claude Code e que
nenhuma página do Devin documenta expandir. Sem expansão, o servidor sobe e morre na
primeira leitura do catálogo, com a mensagem certa e o motivo errado:

```text
CatalogError: SPARKFORGE_CATALOG aponta para .../${CLAUDE_PLUGIN_ROOT}/rules/catalog,
que nao e um diretorio existente
```

Por isso a configuração acima **não** declara `env`: com o pacote instalado por `pip`, o
`PYTHONPATH` é desnecessário e o catálogo resolve de dentro do próprio pacote. Só declare
`SPARKFORGE_CATALOG` se quiser apontar para um catálogo fora dele — e aí com caminho de
verdade, nunca com uma variável de outra ferramenta.

**Devin Desktop — HTTP.** O Desktop configura MCP por `serverUrl`, e o servidor tem o
transporte:

```bash
python -m sparkforge_aws.adapters.mcp --transport http --host 127.0.0.1 --port 8765
# serverUrl: http://127.0.0.1:8765/mcp
```

No Desktop va em **Devin Settings > MCP**, adicione um servidor com a URL acima e
confirme. O processo do servidor precisa ficar rodando enquanto a sessao estiver ativa.

**Superfície compacta — opt-in.** O modo padrão continua `full` e publica o catálogo
completo. Para hosts que preferem descobrir capacidades sob demanda, passe `--mode
compact`; o servidor publica exatamente estas seis tools: `context_start`,
`context_expand`, `execute`, `search`, `get` e `next`.

```bash
# Devin CLI, Claude Code ou outro cliente stdio
python -m sparkforge_aws.adapters.mcp --transport stdio --mode compact

# Devin Desktop ou outro cliente HTTP
python -m sparkforge_aws.adapters.mcp --transport http --mode compact --host 127.0.0.1 --port 8765
# serverUrl: http://127.0.0.1:8765/mcp
```

`execute` mantém o dispatch e os schemas das tools existentes; `search`, `get` e
`next` fazem descoberta, leitura e paginação determinísticas. Uma tool full não
listada é recusada no modo compacto. O catálogo full continua acessível sem `--mode`
ou com `--mode full`, preservando o contrato anterior.

Para instalar essa escolha no host, use o profile de integração. `economy` e
`balanced` gravam `--mode compact`; `deep` mantém o catálogo full:

```bash
sparkforge-aws integrate claude --scope user --profile economy
```

### 3.4 Economia de contexto e execução determinística

O Gateway usa três profiles, sempre com bytes serializados separados de tokens do
provider:

| Profile | Limite de capabilities | Skills | Knowledge | Escalada |
|---|---:|---:|---:|---|
| `economy` | 8 | 3 | 8 | não |
| `balanced` | 16 | 6 | 16 | não |
| `deep` | 32 | 12 | 32 | sim |

Exemplo local:

```bash
sparkforge-aws context start --intent "Glue FGAC Iceberg" --profile economy
python scripts/check_token_efficient_bench.py
```

`payload_bytes` mede o envelope JSON em UTF-8. `provider_tokens` só aparece quando o
host fornece transcript; sem transcript, `tokens_unresolved` permanece verdadeiro. O
Gateway expõe `context_tree`, refs `ctx://v1` e `execution_plan`. O planner tenta a
resposta determinística primeiro; reviewer, specialist ou debate surgem por triggers
explícitos ou derivados de evidência estruturada (`risk`, `confidence`, conflitos e
unresolved). O core não chama modelo.

Para repositórios relacionados, declare `.sparkforge_aws/workspace.yaml` e use a API de
workspace. Paths fora da raiz, repositórios não declarados e relações ausentes não são
descobertos silenciosamente: entram como erro ou `unresolved`.

Para Codex e Copilot CI, a matriz atual registra consumo por CLI/arquivos, não uma
sessão MCP interativa com transcript de host. Portanto, a paridade compacta é
verificada pelo contrato MCP em processo e pelos fixtures; não se afirma uma sessão
ao vivo que não foi observada.

**E quando não houver MCP nenhum:** a CLI `sparkforge-aws` faz tudo o que as 143 tools fazem (catálogo atual)
(seção 11), e é o que Codex e Copilot CI usam por não manterem sessão MCP interativa.
Subagente não perde o MCP: *"Subagents can now call MCP tools directly"* (2026-04-30).

As superfícies Agentic OS v2 são locais e compartilham `_core` entre CLI e MCP:

```bash
sparkforge-aws context inspect --input context.json
sparkforge-aws agentops inspect <run_id> --repo .
sparkforge-aws agentops compare <run_a> <run_b> --repo .
sparkforge-aws agentops baseline save <run_id> --path .sparkforge_aws/baselines/base.json --repo .
sparkforge-aws agentops baseline compare <run_b> --path .sparkforge_aws/baselines/base.json --repo .
sparkforge-aws doctor agentic --repo .
```

O payload de `context inspect` deve declarar `items`; cada item pode trazer `relevant`,
`evidence_refs`, `stale`, `duplicate_of`, `reused` e `cache_hit`. O comando mede bytes
serializados. `--observed-provider-tokens` é opcional e só deve receber valor vindo do
transcript do host; bytes não viram tokens por aproximação. `agentops` lê SQLite local,
expõe `unresolved` quando run, transcript, qualidade ou preço não existem, e classifica
desperdício observado separadamente de hipótese. `baseline save` grava arquivo local;
nenhum desses comandos chama AWS ou provider.

### 3.5 Verificar que o MCP funciona

Apos conectar:

```text
Liste as tools MCP do sparkforge-aws e confirme que consegue chamar sparkforge_runtime_detect.
```

Ou, sem depender do agente, teste o stdio diretamente:

```bash
devin mcp list
```

Para o transporte HTTP, abra em outro terminal:

```bash
curl -i http://127.0.0.1:8765/mcp
```

Deve responder `405 Method Not Allowed` ou similar — isso confirma que o endpoint esta
ativo. Um `connection refused` indica que o servidor nao subiu ou a porta esta errada.

### 3.6 Troubleshooting comum

| Sintoma | Causa provavel | Correcao |
|---|---|---|
| `CatalogError: .../${CLAUDE_PLUGIN_ROOT}/...` | `.mcp.json` sendo usado no Devin | Use `.devin/mcp_config.json` ou `devin mcp add` |
| `ModuleNotFoundError: mcp` | extra `[mcp]` nao instalado | `pip install "sparkforge-aws[mcp]"` |
| `devin mcp list` nao mostra `sparkforge-aws` | arquivo no escopo global em vez de projeto | confira se `.devin/mcp_config.json` existe na raiz do repo |
| Desktop nao conecta ao `serverUrl` | servidor HTTP nao rodando ou porta errada | suba com `python -m sparkforge_aws.adapters.mcp --transport http ...` e verifique o endereco |
| Tools aparecem, mas chamadas falham com `CatalogError` | `SPARKFORGE_CATALOG` aponta para caminho inexistente | remova a variavel ou aponte para um diretorio real |

Para reinstalar do zero:

```bash
pip uninstall sparkforge-aws -y
pip install "sparkforge-aws[mcp]"
devin mcp remove -s project sparkforge-aws || true
devin mcp add -s project sparkforge-aws -- python -m sparkforge_aws.adapters.mcp --transport stdio
```

## 4. GitHub Copilot

No Copilot Chat:

```text
/iniciar-investigacao-performance-glue
```

Ou selecione o agente **Glue Incremental Performance Architect**.

## 5. Coordenador e playbook: como entrar sem escolher à mão

Qual coordenador usar não é escolha manual. `sparkforge-aws next-step` (CLI) ou
`sparkforge_next_step` (MCP) consulta as rotas `AGENT-*` de
`rules/catalog/routing.yaml` e devolve `recommended_agent` a partir do estado do case —
fase da investigação e área do achado dominante. Há 14 coordenadores, cada um com
executores declarados: ver a tabela em `AGENTS.md`.

Dois deles não são sobre performance de código, e é por isso que quem procura só
"tuning" nunca os encontra sozinho. `emr-infra-reviewer` (áreas `SF-EMR`, `SF-EMRS` e `SF-ENV`)
responde quando o Spark roda em Amazon EMR on EC2 e o risco está na definição do cluster
— instance fleets contra instance groups, opção de compra por papel, managed scaling,
`Configurations` em dois níveis, bootstrap actions, `LogUri`, cluster que terminou antes
de processar qualquer coisa. `data-quality-reviewer` (área `SF-DQ`) responde quando o job
valida dado e a pergunta é onde a validação está, se ela tem consequência e quanto ela
custa em passadas sobre o dado — nunca se o dado está correto, que é pergunta sem
artefato para extrair.

Em Claude Code, no Devin CLI e no Devin Local agent do Desktop, o coordenador indicado
despacha os cinco executores (`sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier`,
`sf-synthesizer`) como subagentes, na ordem do loop de fase — ver a seção 3 para onde os
perfis moram no Devin.

`sparkforge-aws playbook <coordenador>` (CLI) ou a tool MCP `sparkforge_playbook` devolve a
mesma decomposição em passos sequenciais: o que cada executor faz, não faz, pressupõe e
entrega, na ordem certa. Ele é o **piso das cinco plataformas**, não um substituto de
segunda classe: é o único caminho em Codex e Copilot CI, onde despacho de subagente não
foi medido, e é o caminho nas três que despacham sempre que o despacho estiver desligado
(seção 3.3). Perde o paralelismo; mantém o método.

Uma coisa não atravessa a fronteira do subagente em plataforma nenhuma: a confirmação de
escopo e retenção antes de manutenção destrutiva. Os treze perfis declaram em `## Não faz`
que **não executam** expiração de snapshot, remoção de arquivo órfão, `DROP` ou
sobrescrita de partição — eles recomendam, e a confirmação acontece com quem tem a
pergunta disponível, que nunca é o subagente.

## 6. Ordem prática dos artefatos

Forneça nesta ordem:

1. Estrutura do repositório.
2. Terraform — ou, se o Spark roda em EMR on EC2, o dump de `aws emr describe-cluster`;
   se roda em EMR Serverless, o dump de `aws emr-serverless get-application`.
3. Entry point.
4. Biblioteca.
5. Plano `explain("formatted")`.
6. Spark UI.
7. Logs da falha.
8. CloudWatch.
9. Metadata tables Iceberg.
10. Baseline.

O item 2 troca de artefato porque só ele é específico da plataforma. O resto da ordem não
muda: `analyze emr-cluster --path cluster.json` produz os facts de infraestrutura que
`analyze terraform` produziria no Glue, e a release do EMR sai do próprio dump, sem
ninguém precisar declará-la.

Em EMR Serverless o artefato é um só, e os dois verbos são estes:

```bash
sparkforge-aws collect emr-serverless --repo . --application-id 00fXXXXXXXXXXXXX --now <ISO8601>
sparkforge-aws analyze emr-serverless --path .sparkforge_aws/artifacts/<dir-ou-arquivo>   --out .sparkforge_aws/facts_emr_serverless.json
```

`collect` exige o **id** da application e nunca o nome — `name` é opcional na API e a
documentação não declara unicidade, então resolver por nome escolheria uma entre N
homônimas em silêncio. **Use o `--out` do `analyze`, não a saída de tela:** o envelope
pagina em 50 e `runtimeConfiguration` tem teto de 100 propriedades, cada uma virando um
fact — medido, um dump com 60 propriedades produz 64 facts e a tela mostra 50, com
`next_cursor` que ninguém precisa ler quando o arquivo tem tudo. Aqui a release **não**
sai do dump para o `RuntimeContext`: a AWS não publica a matriz do Serverless, e a área
`SF-EMRS` foi escrita sem guarda de versão justamente por isso.

Se a biblioteca valida dado — `df.filter(...).count()` seguido de aborto,
`VerificationSuite` do PyDeequ, ou Great Expectations —, rode também
`analyze data-quality --path lib/` sobre os mesmos arquivos do item 4. É o mesmo `.py`
lido por outra ótica, e nenhum dos dois extratores cala o outro: a mesma linha pode
produzir um achado sobre o que a cadeia custa e outro sobre o dado ruim já estar publicado
quando o alarme toca.

Se a biblioteca importa `graphframes` ou `io.graphframes`, rode também
`analyze graph --path lib/` sobre os mesmos arquivos do item 4 — é a **terceira** leitura
do mesmo `.py`, e sem ela a área `SF-GRAPH` some do relatório em silêncio. Ao contrário
do `analyze emr-serverless` acima, aqui a saída de tela **não** estoura: medido num
arquivo de grafo realista de 71 linhas, `total_count` 11 contra o teto de 50 e
`next_cursor: null`, porque este extrator emite um fact por **evento de grafo** e não um
por propriedade de configuração. Use `--out` quando o alvo for um diretório, que é o que
multiplica. Duas ressalvas que mudam a leitura do resultado: o vocabulário de GraphFrames
só é lido em módulo que **importa** a biblioteca (`find`, `degrees` e `validate` são nomes
que qualquer objeto de usuário pode ter), e `SF-GRAPH-002` é guardada por **faixa de
Spark** — sobre `.py` solto, sem fonte de versão, ela sai em `skipped` com
`reason: runtime_scope`, e é a resposta certa.

Se a investigação vai **mudar** o job, `funcval plan` deriva, **antes** da mudança, o que
precisa ser medido nos dois lados — contagem, schema, chaves e agregados do alvo:

```bash
sparkforge-aws funcval plan \
  --facts .sparkforge_aws/facts.json \
  --facts .sparkforge_aws/facts_catalog.json \
  --key pedido_id,dt \
  --out .sparkforge_aws/facts_funcval_plan.json
```

`--facts` é repetível e **precisa** ser: o alvo vem do `pyspark.write` de
`analyze pyspark`, e o schema e os agregados vêm do `catalog.table_schema` de
`analyze catalog-schema` — nenhum verbo produz os dois no mesmo arquivo. `--out` é
**obrigatório** aqui, ao contrário do `--out` dos verbos de `analyze`: o plano é a entrada
do `compare` e é a evidência do gate `functional_validation_defined`. Sem `--key` o plano
não inventa chave — nenhum fact do repositório nomeia chave de negócio —, e escreve o eixo
como ausente em `undeclared_axes` em vez de calar. Derivar o plano **antes** é o ponto:
definir depois de medir é escolher o check que passa.

Medidos os dois lados — quem mede é você, o motor não executa consulta nenhuma —,
`funcval compare` julga antes contra depois, **nunca** observado contra catálogo:

```bash
sparkforge-aws funcval compare \
  --plan .sparkforge_aws/facts_funcval_plan.json \
  --before .sparkforge_aws/funcval_before.json \
  --after .sparkforge_aws/funcval_after.json \
  --out .sparkforge_aws/facts_funcval.json
```

`--out` grava a lista **completa** de facts, no formato que `judge --facts` lê — o stdout
continua sendo o envelope paginado, e `--limit` corta ele e não o arquivo. É opcional, ao
contrário do `--out` do `plan`: aquele é a entrada do próximo verbo, este é saída
terminal. Sem ele, julgar exige extrair `items` do envelope à mão e conferir `next_cursor`
antes — `--limit` vale 50 por default, e julgar a primeira página chamando-a de comparação
é o mesmo defeito que `SF-FVAL-005` acusa. Os quatro eixos são **proxies**: iguais nos dois lados eles não
provam que o dado é o mesmo, porque duas linhas podem trocar valores entre si e os quatro
passam. Relate a ausência de achado `SF-FVAL` como "nenhum proxy detectou divergência",
nunca como "o resultado é idêntico".

## 6.1 Governança de acesso: os quatro artefatos que respondem "quem pode o quê"

Nenhum dos artefatos da seção 6 responde por que uma leitura passa e a escrita não.
Essa pergunta tem quatro coletores próprios, e a ordem entre eles importa porque
cada um responde uma metade que o anterior deixou aberta.

```bash
# 1. o que o JOB declara -- FGAC, Full Table Access, catálogo, filesystem
sparkforge-aws analyze terraform --path infra/ --out .sparkforge_aws/facts_tf.json

# 2. o que a TABELA e a CONTA respondem
sparkforge-aws collect lakeformation --repo . --database <db> --table <t>     --catalog-id <conta-dona-do-catalogo>     --resource-arn <localizacao-s3-da-tabela> --now <ISO8601>
sparkforge-aws analyze lakeformation-grants --path .sparkforge_aws/artifacts/lakeformation/     --out .sparkforge_aws/facts_lf.json

# 3. o que o IAM decide, SIMULADO -- não o documento da policy
sparkforge-aws collect iam-access --repo . --role-arn <runtime-role>     --resource-arn <arn-do-alvo> --action s3:PutObject --action kms:GenerateDataKey     --now <ISO8601>
sparkforge-aws analyze iam-access --path .sparkforge_aws/artifacts/iam_access/     --out .sparkforge_aws/facts_iam.json

# 4. a mensagem exata da falha
sparkforge-aws collect cloudwatch-logs --repo . --job-name <job> --job-run <run>     --log-group /aws-glue/jobs/error --start <ISO8601> --end <ISO8601> --now <ISO8601>
sparkforge-aws analyze cloudwatch-logs --path .sparkforge_aws/artifacts/cloudwatch_logs/     --out .sparkforge_aws/facts_log.json
```

**Três coisas que decidem a qualidade da resposta, e todas são escolha de quem coleta:**

- **`--catalog-id` é obrigatório em cross-account.** A mesma `db.tabela` existe em
  contas diferentes, e sem ele as duas coletas se sobrescrevem no manifesto.
- **`--resource-arn` no `iam-access` muda a pergunta.** Sem ele a AWS responde sobre
  `*`, e `allowed` sobre `*` **não** é `allowed` naquele recurso. O fact carrega
  `scoped_to_resource` para que as duas não se confundam.
- **`--action` deve ser o da operação que falhou.** A lista default tem 14 ações; passar
  todas quando a pergunta é sobre uma escrita produz 10 decisões que não dizem nada
  sobre o caso.

**O que estes quatro NÃO cobrem, e sai declarado em todo artefato:** bucket policy do
S3, key policy do KMS e Glue resource policy são avaliação **separada** — um `allowed`
no `iam-access` com bucket policy negando ainda falha. `iam.access.unresolved` publica
esse limite sempre, inclusive quando tudo respondeu `ok`.

## 7. Quando faltarem dados

Peça ao agente para gerar:

- instrumentação;
- consultas Iceberg;
- comandos de coleta;
- logs estruturados;
- métricas por etapa;
- benchmark reprodutível.

## 8. Critério de conclusão

A investigação só está concluída quando houver:

- gargalo dominante comprovado;
- arquitetura-alvo;
- mudança implementada;
- benchmark — `sparkforge-aws benchmark --before … --after …`;
- validação funcional — `sparkforge-aws funcval plan` **antes** da mudança e
  `sparkforge-aws funcval compare` depois, com os dois lados medidos por você;
- custo;
- risco;
- rollback.

Os dois itens com verbo são os que produzem **artefato verificável**, e é por isso que
eles nomeiam o comando: item de conclusão sem verbo produtor é exatamente a prosa que
`SF-FVAL` e `SF-BENCH` existem para acusar no job do usuário — não cabe cometê-la aqui.

## 9. Retomando entre Devin e Claude Code

O que atravessa a fronteira entre uma sessão Devin e uma sessão Claude Code é
um commit, não contexto de conversa. Cinco arquivos pequenos e derivados sob
`.sparkforge_aws/` são committados — `case.yaml`, `facts.json`, `findings.json`,
`handoff.md` e `artifacts/manifest.json` — porque são o barramento de handoff.
Tudo em `.sparkforge_aws/artifacts/**` além do `manifest.json` **não** é
committado: são artefatos brutos (event logs, planos físicos, saída de
Terraform) que podem carregar dado de negócio e chegar a centenas de MB. O
manifesto é o que substitui o artefato ausente no commit: ele registra
`sha256`, `source` e o `collect_command` exato de cada um.

Checklist de retomada, em ordem:

1. Rode `sparkforge-aws resume --repo <raiz>` (ou `/sf-resume`) para reidratar o
   payload — onde parou, runtime, achados principais, hipóteses abertas.
2. Leia `coverage.unresolved`. Um nó não resolvido é **ponto cego**, não
   ausência de problema — nunca trate contagem zero de achados como "está
   tudo limpo" sem antes conferir `unresolved`.
3. Leia `runtime.divergences`. Divergência entre fontes significa que
   **nenhum limiar é confiável ainda** — corrija a detecção de runtime antes
   de aplicar qualquer recomendação que dependa de versão.
4. Para cada artefato em `missing_artifacts`, recolete usando o
   `collect_command` exato registrado no manifesto — não improvise outro
   comando nem assuma que o artefato antigo ainda é válido.
5. Deixe `sparkforge-aws next-step` decidir a rota (via `routing.yaml`). Não
   escolha a próxima skill por julgamento próprio — é isso que divergiria
   entre modelos e entre ferramentas.

## 10. Economia de token: o que já vem ligado

O **caveman**, de [Julius Brussee](https://github.com/JuliusBrussee) (MIT —
créditos em [`vendor/CREDITS.md`](vendor/CREDITS.md)), está embutido no
repositório. **Clonar é a instalação inteira**: não há `npm install`, não há
`npx`, não há `package.json`, e nada aqui vai à rede.

| Você quer | Comando |
|---|---|
| Compressão de output (já ativa, modo `full`) | nada — abra o Claude Code na raiz do repositório |
| Trocar o nível só nesta sessão | `/caveman lite`, `/caveman full`, `/caveman ultra` |
| Ver quanto a sessão economizou | `/caveman-stats` |
| Mensagem de commit comprimida | `/caveman-commit` |
| Revisão de diff comprimida | `/caveman-review` |
| Comprimir um arquivo de memória (`CLAUDE.md`, notas) | `/caveman-compress <arquivo>` |
| Loop de spec-driven development sobre um `SPEC.md` | `/spec`, `/build`, `/check`, `/grill`, `/deepen` (para mudança no próprio SparkForge, o fluxo é o SDD do repositório: skills `sdd-*` e `sparkforge-aws sdd check`, em [`docs/sdd/README.md`](docs/sdd/README.md)) |
| Delegar a subagente comprimido | skill `cavecrew` → `cavecrew-investigator`, `cavecrew-builder`, `cavecrew-reviewer` |
| Voltar ao português normal | `stop caveman` ou `normal mode` |

Sem Node na máquina a compressão continua ativa, por um fallback em shell no
`.claude/settings.json`; o que se perde é só o flag de modo e o
`/caveman-stats`, que dependem do hook em JS.

**O que a compressão nunca corta neste projeto:** o schema
`recommendation:`/`Finding` inteiro — `evidence`, `risks`, `validation`,
`rollback` incluídos —, números, versões, `rule_id`, `fact_id`, strings de erro,
SQL, HCL, YAML, JSON e blocos de código. Campo de evidência apagado para
economizar token é defeito, não compressão. O recorte completo está em
`AGENTS.md`, seção *Output compression — caveman mode*, que é também o que Devin
e Copilot leem, já que eles não carregam plugin nem hook.

**O que ficou de fora.** `cavemem` (memória entre sessões) e `caveman-code`
(agente de terminal), do mesmo autor, exigem `npm` e módulo nativo — não cabem
em "clonar é a instalação inteira", e o primeiro nem economiza token: o
`SessionStart` dele *injeta* contexto da sessão anterior. Quem quiser instala
globalmente, fora deste repositório. A razão completa está em
[`vendor/CREDITS.md`](vendor/CREDITS.md).

## 11. Sem MCP e sem Python

Se as tools MCP não estiverem disponíveis, use a CLI `sparkforge-aws` (mesmas
funções, mesma saída). Se nem Python estiver disponível, leia
`rules/catalog/*.yaml` diretamente — é YAML legível por humano, com o mesmo
`rule_id`, o mesmo limiar, a mesma guarda de versão (`runtime_scope`) e a
mesma fonte datada que o motor usaria. A automação cai; o conhecimento não.
# Context Gateway profiles and Compact rollout

`context_start` aceita `profile: economy|balanced|deep`. `max_bytes` é opcional e usa
default determinístico do perfil: 6.000, 16.000 ou 30.000 bytes. O Gateway aplica
limites por kind antes do limite global, preserva evidência crítica e recusa quando a
materialização completa não cabe.

MCP continua `full` por padrão. `--mode compact` é opt-in e publica sete operações;
`docs/surface.lock.json` trava nomes, quantidade, bytes e digest das duas superfícies.
Use `python scripts/check_token_efficient_bench.py` para validar matriz de benchmark.
