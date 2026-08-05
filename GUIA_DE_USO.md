# Guia de Uso — SparkForge AWS

## 1. Começo recomendado

Abra a ferramenta no repositório que contém:

- Terraform do Glue;
- entrypoint do job;
- biblioteca Python;
- testes;
- exemplos de logs ou planos.

Cole ou invoque o conteúdo de `PROMPT_INICIAL_MESTRE.md`.

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
| Os 8 coordenadores | `.agents/agents/<nome>.md` | caminho de descoberta nativo ("Also supported" na aba *Project-specific*), no layout *flat file* documentado |
| Os mesmos 8 | `.claude/agents/<nome>.md` | importados do formato do Claude Code — *"Each `.md` file becomes a subagent profile"* |
| As 20 skills | `.agents/skills/<nome>/SKILL.md` | caminho de descoberta nativo, não convenção deste repositório |
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
sparkforge playbook emr-infra-reviewer --repo .
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
— que é exatamente o que `sparkforge playbook <coordenador>` devolve, em ordem. Em Claude
Code o coordenador despacha os executores; no Devin, não conte com isso.

No Devin Desktop o recorte é mais estreito: subagente é capacidade do **Devin Local
agent**, sob o toggle *Subagents (Preview)*. As páginas do motor Cascade não mencionam
subagente. Fora do Devin Local agent com o toggle ligado, a coordenação no Desktop é
`playbook`.

### 3.2 Quais skills despacham, e a que não despacha de propósito

**Doze das vinte** skills declaram `subagent: true` no espelho `.agents/skills/`: as
quatro `review-*` (`review-emr-cluster`, `review-data-validation`,
`review-glue-terraform`, `review-pyspark-pr`), as quatro `analyze-*`
(`analyze-spark-plan`, `analyze-spark-ui`, `analyze-batch-loop`,
`analyze-library-call-graph`), `diagnose-oom`, `diagnose-data-skew`,
`optimize-pyspark-code` e `optimize-parquet-layout`. São as investigações fechadas: o
subagente coleta, julga sobre artefato, e o pai lê e resume o resultado.

**Duas** delas declaram também `agent:` — `review-emr-cluster` → `emr-infra-reviewer` e
`review-data-validation` → `data-quality-reviewer`. Nas outras **dez**, `agent:` não tem
resposta única e o Devin escolhe o perfil, que é a forma documentada (o campo tem default
*none*).

Nove são ambíguas por serem declaradas por dois a quatro coordenadores. A décima é
`diagnose-oom`, e a razão dela é diferente: ela **era** declarante único, mas só porque
`spark-performance-architect` não a lista no `skills:` dele — embora liste
`diagnose-data-skew`, `analyze-spark-ui` e `tune-glue-job`, toda a vizinhança do mesmo
diagnóstico. Omissão numa lista pré-existente não é juízo de competência, e o perfil que
sobrava era o `glue-incremental-performance-architect`, cuja skill homônima este
repositório declara **não-despachável** justamente por orquestrar as outras via
`next-step`. Publicar aquele `agent:` seria roteamento mecânico com cara de decisão — o
mesmo defeito que a ordem alfabética produziria.

**`sparkforge-diagnose` não despacha, de propósito.** Ela abre o case e roteia, e o
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
seção 5: `sparkforge playbook <coordenador>`, que é o piso e não depende de despacho.

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
    "sparkforge": {
      "command": "python",
      "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"]
    }
  }
}
```

Ou pela própria CLI, sem editar arquivo:

```bash
pip install "sparkforge-aws[mcp]"
devin mcp add -s project sparkforge -- python -m sparkforge.adapters.mcp --transport stdio
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
python -m sparkforge.adapters.mcp --transport http --host 127.0.0.1 --port 8765
# serverUrl: http://127.0.0.1:8765/mcp
```

**E quando não houver MCP nenhum:** a CLI `sparkforge` faz tudo o que as 40 tools fazem
(seção 10), e é o que Codex e Copilot CI usam por não manterem sessão MCP interativa.
Subagente não perde o MCP: *"Subagents can now call MCP tools directly"* (2026-04-30).

## 4. GitHub Copilot

No Copilot Chat:

```text
/iniciar-investigacao-performance-glue
```

Ou selecione o agente **Glue Incremental Performance Architect**.

## 5. Coordenador e playbook: como entrar sem escolher à mão

Qual coordenador usar não é escolha manual. `sparkforge next-step` (CLI) ou
`sparkforge_next_step` (MCP) consulta as rotas `AGENT-001`…`AGENT-008` de
`rules/catalog/routing.yaml` e devolve `recommended_agent` a partir do estado do case —
fase da investigação e área do achado dominante. Há oito coordenadores, cada um com
executores declarados: ver a tabela em `AGENTS.md`.

Dois deles não são sobre performance de código, e é por isso que quem procura só
"tuning" nunca os encontra sozinho. `emr-infra-reviewer` (áreas `SF-EMR` e `SF-ENV`)
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

`sparkforge playbook <coordenador>` (CLI) ou a tool MCP `sparkforge_playbook` devolve a
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
sparkforge collect emr-serverless --repo . --application-id 00fXXXXXXXXXXXXX --now <ISO8601>
sparkforge analyze emr-serverless --path .sparkforge/artifacts/<dir-ou-arquivo>   --out .sparkforge/facts_emr_serverless.json
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

Se a investigação vai **mudar** o job, `funcval plan` deriva, **antes** da mudança, o que
precisa ser medido nos dois lados — contagem, schema, chaves e agregados do alvo:

```bash
sparkforge funcval plan \
  --facts .sparkforge/facts.json \
  --facts .sparkforge/facts_catalog.json \
  --key pedido_id,dt \
  --out .sparkforge/facts_funcval_plan.json
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
sparkforge funcval compare \
  --plan .sparkforge/facts_funcval_plan.json \
  --before .sparkforge/funcval_before.json \
  --after .sparkforge/funcval_after.json \
  --out .sparkforge/facts_funcval.json
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
- benchmark — `sparkforge benchmark --before … --after …`;
- validação funcional — `sparkforge funcval plan` **antes** da mudança e
  `sparkforge funcval compare` depois, com os dois lados medidos por você;
- custo;
- risco;
- rollback.

Os dois itens com verbo são os que produzem **artefato verificável**, e é por isso que
eles nomeiam o comando: item de conclusão sem verbo produtor é exatamente a prosa que
`SF-FVAL` e `SF-BENCH` existem para acusar no job do usuário — não cabe cometê-la aqui.

## 9. Retomando entre Devin e Claude Code

O que atravessa a fronteira entre uma sessão Devin e uma sessão Claude Code é
um commit, não contexto de conversa. Cinco arquivos pequenos e derivados sob
`.sparkforge/` são committados — `case.yaml`, `facts.json`, `findings.json`,
`handoff.md` e `artifacts/manifest.json` — porque são o barramento de handoff.
Tudo em `.sparkforge/artifacts/**` além do `manifest.json` **não** é
committado: são artefatos brutos (event logs, planos físicos, saída de
Terraform) que podem carregar dado de negócio e chegar a centenas de MB. O
manifesto é o que substitui o artefato ausente no commit: ele registra
`sha256`, `source` e o `collect_command` exato de cada um.

Checklist de retomada, em ordem:

1. Rode `sparkforge resume --repo <raiz>` (ou `/sf-resume`) para reidratar o
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
5. Deixe `sparkforge next-step` decidir a rota (via `routing.yaml`). Não
   escolha a próxima skill por julgamento próprio — é isso que divergiria
   entre modelos e entre ferramentas.

## 10. Sem MCP e sem Python

Se as tools MCP não estiverem disponíveis, use a CLI `sparkforge` (mesmas
funções, mesma saída). Se nem Python estiver disponível, leia
`rules/catalog/*.yaml` diretamente — é YAML legível por humano, com o mesmo
`rule_id`, o mesmo limiar, a mesma guarda de versão (`runtime_scope`) e a
mesma fonte datada que o motor usaria. A automação cai; o conhecimento não.
