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
| Os 8 coordenadores e os 5 executores | `.agents/agents/` e `.agents/agents/executors/` | caminho de descoberta nativo ("Also supported" na aba *Project-specific*) |
| Os mesmos 13 perfis | `.claude/agents/` | importados do formato do Claude Code — *"Each `.md` file becomes a subagent profile"* |
| As 20 skills | `.agents/skills/<nome>/SKILL.md` | caminho de descoberta nativo, não convenção deste repositório |

Os dois primeiros são **espelhos gerados** de `agents/`, que é a fonte — nunca edite um
espelho: `python scripts/sync_skills.py --check` recusa. Eles não são gerados do mesmo
jeito. `.claude/agents/` é cópia byte a byte, com `tools:` e tudo. `.agents/agents/` é
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
2. Terraform — ou, se o Spark roda em EMR on EC2, o dump de `aws emr describe-cluster`.
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

Se a biblioteca valida dado — `df.filter(...).count()` seguido de aborto,
`VerificationSuite` do PyDeequ, ou Great Expectations —, rode também
`analyze data-quality --path lib/` sobre os mesmos arquivos do item 4. É o mesmo `.py`
lido por outra ótica, e nenhum dos dois extratores cala o outro: a mesma linha pode
produzir um achado sobre o que a cadeia custa e outro sobre o dado ruim já estar publicado
quando o alarme toca.

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
- benchmark;
- validação funcional;
- custo;
- risco;
- rollback.

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
