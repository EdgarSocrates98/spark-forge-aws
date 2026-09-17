# Agents e skills: quem faz o quê

Este manual explica, sem teoria, como pedir ajuda aos agents e às skills do
SparkForge. O glossário completo fica em [Conceitos](01-conceitos.md).

## Receita rápida

Você não sabe por onde começar? Deixe o SparkForge escolher. Rode da raiz do
repositório:

1. Crie uma pasta de teste e abra um case nela. O case é a memória da investigação.

   ```bash
   DEMO=/tmp/sf-rota && mkdir -p "$DEMO"
   sparkforge case open --repo "$DEMO" --case-id demo-rota --now 2026-09-13T15:00:00Z
   ```

2. Pergunte qual é o próximo passo:

   ```bash
   sparkforge next-step --repo "$DEMO"
   ```

   Trecho real da saída:

   ```json
   {
     "phase": "intake",
     "recommended_skill": "sparkforge-diagnose",
     "reason": "ROUTE-001: Sem runtime confirmado, nenhum limiar nem API pode ser aplicado com segurança. ...",
     "recommended_agent": "spark-performance-architect",
     "recommended_agent_reason": "AGENT-001: Coordenador geral enquanto o terreno não está mapeado. ..."
   }
   ```

3. Veja o passo a passo do agent indicado:

   ```bash
   sparkforge playbook spark-performance-architect --repo .
   ```

4. No Claude Code, peça em português: `Use o agente spark-performance-architect para
   investigar este job.`
5. Sem Claude Code, abra a skill indicada e siga o texto:
   `skills/sparkforge-diagnose/SKILL.md`.

> **Qual `sparkforge` usar.** Compare `sparkforge --version` com
> `python -m sparkforge.adapters.cli --version`, rodando da raiz do repositório. Se
> os números forem diferentes, o `sparkforge` instalado está velho. Use
> `python -m sparkforge.adapters.cli` no lugar de `sparkforge` em todos os comandos,
> ou reinstale com `pip install -e .` (veja [Instalação](02-instalacao.md)).

## O que é um agent e o que é uma skill

- **Skill** é uma receita escrita. Ela diz o procedimento para um tipo de problema
  (por exemplo, "o job deu OutOfMemory"). Mora em `skills/<nome>/SKILL.md`.
- **Agent** é um papel. Ele sabe quais skills usar, quais áreas de regra olhar e o
  que ele **não** faz. Mora em `agents/<nome>.md`.

Nenhum dos dois inventa número. Os dois chamam a CLI ou as tools MCP do SparkForge
e citam a evidência (`fact_id`) de cada afirmação.

## Coordenadores e executores

Há dois tipos de agent:

- **Coordenador**: decide a ordem do trabalho e registra no case o que foi feito.
  Ele não executa sozinho. Exemplos: `spark-performance-architect`,
  `iceberg-performance-engineer`, `glue-infra-reviewer`.
- **Executor**: faz uma única função e devolve ao coordenador. São cinco, em
  `agents/executors/`:

| Executor | Função | O que ele nunca faz |
|---|---|---|
| [`sf-inventory`](referencia/agents/sf-inventory.md) | mapeia runtime, case e artefatos que faltam | extrair fact ou julgar |
| [`sf-extractor`](referencia/agents/sf-extractor.md) | roda os extratores (`analyze ...`) | julgar ou aplicar limiar |
| [`sf-judge`](referencia/agents/sf-judge.md) | roda o `judge` e consulta as regras | propor mudança ou estimar ganho |
| [`sf-verifier`](referencia/agents/sf-verifier.md) | tenta **refutar** cada achado P0 e P1 | consertar ou escrever relatório |
| [`sf-synthesizer`](referencia/agents/sf-synthesizer.md) | monta, valida e assina o relatório | inventar número |

Cada arquivo de agent tem uma seção `## Não faz`. Ela é a fronteira do agent. Nenhum
agent executa manutenção destrutiva (expirar snapshot, apagar arquivo órfão, `DROP`,
sobrescrever partição). Ele recomenda, e quem confirma é você.

### O contrato: as regras de `AGENT_PROTOCOL.md`

Todo agent e toda skill apontam para `AGENT_PROTOCOL.md`. Em resumo:

1. Abra ou carregue o case antes de analisar.
2. Chame `next-step` antes de escolher uma skill. A rota é dado, não opinião.
3. Nenhum número sai sem o `fact_id` que o sustenta. Sem fact, é hipótese.
4. Consulte limiar, versão e fonte no catálogo (`rules lookup`), nunca de memória.
5. Valide a recomendação (`validate`) antes de apresentá-la. Ganho com número exige
   um benchmark medido.
6. Registre no case cada skill e cada executor usados, com o resultado.
7. Sempre informe o que ficou `unresolved`. Ponto cego não é ausência de problema.
8. Confirme a versão do runtime antes de citar API ou propriedade.
9. Manutenção destrutiva você não executa: recomende e devolva a decisão.
10. Defina a validação funcional (`funcval plan`) antes da mudança e compare os dois
    lados medidos.

### O loop de fases

```text
next_step → coletar → extrair facts → julgar → hipótese → experimento
   → medir → validar dados → atualizar case → next_step
```

Uma variável por experimento. Sem medida de antes (baseline), não há como provar
impacto. O manual [Investigação com case](usos/investigacao-com-case.md) mostra o
loop rodando.

## Onde os arquivos moram

Você só edita a **fonte**. Os espelhos são gerados por `scripts/sync_skills.py`,
e editar um espelho à mão é recusado pelo gate do projeto.

| Fonte | Espelho no Claude Code | Espelho no Devin | Espelho no GitHub Copilot |
|---|---|---|---|
| `agents/<nome>.md` | `.claude/agents/<nome>.md` (cópia exata) | `.agents/agents/<nome>.md` (sem o campo `tools:`) | `.github/agents/<nome>.agent.md` |
| `agents/executors/<nome>.md` | `.claude/agents/executors/` | `.agents/agents/executors/` | `.github/agents/executors/` |
| `skills/<nome>/SKILL.md` | `.claude/skills/<nome>/SKILL.md` | `.agents/skills/<nome>/SKILL.md` | não há espelho de skill |

O espelho do Devin pode acrescentar `subagent: true` numa skill. Isso quer dizer que
ela é segura para rodar como subagente (um agent filho, com contexto próprio). Um
exemplo real do topo de `.agents/skills/review-emr-cluster/SKILL.md`:

```yaml
subagent: true
agent: emr-infra-reviewer
```

Para listar os agents sem abrir pasta:

```bash
sparkforge agents list --repo .
```

```json
{
  "agents": [
    {
      "name": "athena-query-optimizer",
      "description": "Custo ou latencia na consulta Athena e nao no job - bytes escaneados, ...",
      "file": "agents\\athena-query-optimizer.md"
    },
    ...
```

`sparkforge agents inspect --repo . --id <nome>` mostra o arquivo inteiro de um agent.

## Como usar em cada ferramenta

### Claude Code

- **Agent (subagente):** peça pelo nome, em linguagem natural.

  ```text
  Use o agente iceberg-performance-engineer para revisar esta tabela.
  ```

  No Claude Code, o coordenador despacha os cinco executores como subagentes.
- **Skill:** peça pelo nome. `Use a skill diagnose-oom neste log.`
- **Comandos de barra:** com o repositório carregado como plugin, os arquivos de
  `commands/` viram `/sf-open`, `/sf-next`, `/sf-resume` e `/sf-handoff`.

### Devin (CLI e Local agent do Desktop)

- O Devin lê os agents de `.agents/agents/` e as skills de `.agents/skills/`.
- Comece a sessão assim:

  ```text
  Leia PROMPT_INICIAL_MESTRE.md e use a skill glue-incremental-performance-architect.
  ```

- Um coordenador rodando como subagente no Devin **não** despacha os executores:
  subagente não cria subagente. Use o `playbook` para ter os passos em ordem.
- Os cinco executores não estão num caminho que o Devin documente como lido. O
  `playbook` resolve isso em qualquer plataforma.
- Detalhes e o MCP do Devin: `GUIA_DE_USO.md`, seções 3.1 a 3.4.

### GitHub Copilot

- Selecione o agent na lista (vem de `.github/agents/*.agent.md`).
- Use os prompts de `.github/prompts/`, por exemplo `/iniciar-investigacao-performance-glue`
  ou `/sparkforge-diagnose`.
- O Copilot não tem MCP aqui. Ele usa a CLI `sparkforge` (veja [CLI](03-cli.md)).
- Não há espelho de skill para o Copilot. Abra `skills/<nome>/SKILL.md` e peça para
  ele seguir o arquivo.

### Sem nenhuma dessas ferramentas

1. Rode `sparkforge next-step --repo <raiz>` para saber a skill.
2. Abra `skills/<nome>/SKILL.md` e siga o procedimento, rodando os comandos que ele cita.
3. Rode `sparkforge playbook <coordenador> --repo .` para ter os passos do agent.
4. Sem Python, leia `rules/catalog/*.yaml`. É YAML legível, com o mesmo limiar, a mesma
   guarda de versão e a mesma fonte que o motor usa.

## Por onde começar: pergunta → agent ou skill

A tabela é um ponto de partida. A escolha oficial é sempre a do `next-step`.

| Sua pergunta | Agent | Skill |
|---|---|---|
| "Meu job Glue está lento e não sei por quê" | [`spark-performance-architect`](referencia/agents/spark-performance-architect.md) | [`sparkforge-diagnose`](referencia/skills/sparkforge-diagnose.md) |
| "O job tem fluxo full e incremental, e dá OOM depois de horas" | [`glue-incremental-performance-architect`](referencia/agents/glue-incremental-performance-architect.md) | [`glue-incremental-performance-architect`](referencia/skills/glue-incremental-performance-architect.md) |
| "O job deu OutOfMemory" | [`spark-performance-architect`](referencia/agents/spark-performance-architect.md) | [`diagnose-oom`](referencia/skills/diagnose-oom.md) |
| "Uma task demora muito mais que as outras" (skew) | [`spark-performance-architect`](referencia/agents/spark-performance-architect.md) | [`diagnose-data-skew`](referencia/skills/diagnose-data-skew.md) |
| "Minha tabela Iceberg ficou lenta" | [`iceberg-performance-engineer`](referencia/agents/iceberg-performance-engineer.md) | [`optimize-iceberg-table`](referencia/skills/optimize-iceberg-table.md) |
| "Arquivos Parquet pequenos demais" | [`iceberg-performance-engineer`](referencia/agents/iceberg-performance-engineer.md) | [`optimize-parquet-layout`](referencia/skills/optimize-parquet-layout.md) |
| "A consulta no Athena custa caro" | [`athena-query-optimizer`](referencia/agents/athena-query-optimizer.md) | [`optimize-athena-queries`](referencia/skills/optimize-athena-queries.md) |
| "Workers, auto scaling ou Terraform do Glue" | [`glue-infra-reviewer`](referencia/agents/glue-infra-reviewer.md) | [`review-glue-terraform`](referencia/skills/review-glue-terraform.md), [`tune-glue-job`](referencia/skills/tune-glue-job.md) |
| "Cluster EMR, EMR Serverless ou EMR on EKS" | [`emr-infra-reviewer`](referencia/agents/emr-infra-reviewer.md) | [`review-emr-cluster`](referencia/skills/review-emr-cluster.md), [`review-emr-eks`](referencia/skills/review-emr-eks.md) |
| "A validação de dado do job está no lugar certo?" | [`data-quality-reviewer`](referencia/agents/data-quality-reviewer.md) | [`review-data-validation`](referencia/skills/review-data-validation.md) |
| "A leitura passa e a escrita dá AccessDenied" (Lake Formation) | [`sf-lake-formation-specialist`](referencia/agents/sf-lake-formation-specialist.md) | [`diagnose-lakeformation-access`](referencia/skills/diagnose-lakeformation-access.md), [`lakeformation-fgac-guard`](referencia/skills/lakeformation-fgac-guard.md) |
| "Quanto custa e qual capacidade escolher" | [`sf-cost-reviewer`](referencia/agents/sf-cost-reviewer.md) | [`tune-glue-job`](referencia/skills/tune-glue-job.md); veja também [Custo e capacidade](usos/custo-e-capacidade.md) |
| "Revisar um pull request PySpark" | [`pyspark-code-reviewer`](referencia/agents/pyspark-code-reviewer.md) | [`review-pyspark-pr`](referencia/skills/review-pyspark-pr.md) |
| "Posso migrar para Glue 6.0 ou Spark 4?" | [`sf-runtime-specialist`](referencia/agents/sf-runtime-specialist.md) | [`migrate-glue-6`](referencia/skills/migrate-glue-6.md), [`spark4-compatibility`](referencia/skills/spark4-compatibility.md), [`compare-releases`](referencia/skills/compare-releases.md) |
| "Desenhar ou revisar orquestração de pipeline" | [`sf-airflow-specialist`](referencia/agents/sf-airflow-specialist.md), [`sf-step-functions-specialist`](referencia/agents/sf-step-functions-specialist.md) | [`design-airflow-pipelines`](referencia/skills/design-airflow-pipelines.md), [`design-step-functions-orchestration`](referencia/skills/design-step-functions-orchestration.md) |
| "Coordenar vários agents em fases" | [`sf-orchestrator`](referencia/agents/sf-orchestrator.md) | [`agentic-orchestration`](referencia/skills/agentic-orchestration.md) |
| "Dois achados se contradizem" | coordenador do case | [`run-debate`](referencia/skills/run-debate.md); veja [Arbitragem e debate](usos/arbitragem-e-debate.md) |
| "Quero especificar a mudança antes de construir" (spec, plano, TDD, entrega) | a sessão, sem despacho | [`sdd-explore`](referencia/skills/sdd-explore.md), [`sdd-define`](referencia/skills/sdd-define.md), [`sdd-design`](referencia/skills/sdd-design.md), [`sdd-plan`](referencia/skills/sdd-plan.md), [`sdd-build`](referencia/skills/sdd-build.md), [`sdd-ship`](referencia/skills/sdd-ship.md); veja [`docs/sdd/README.md`](../sdd/README.md) |

Listas completas: [agents](referencia/agents/README.md) e [skills](referencia/skills/README.md).

## `next-step` e `playbook`: a porta de entrada

- **`next-step`** lê o estado do case e as rotas de `rules/catalog/routing.yaml`. Ele
  devolve `recommended_skill` e, quando uma rota de agent casa, `recommended_agent`.
  No MCP, a tool é [`sparkforge_next_step`](referencia/tools/sparkforge_next_step.md).
- **`playbook`** devolve os passos de um coordenador, na ordem, com o que cada
  executor faz (`does`) e não faz (`does_not`). No MCP, a tool é
  [`sparkforge_playbook`](referencia/tools/sparkforge_playbook.md).

Trecho real de `sparkforge playbook spark-performance-architect --repo .`:

```json
{
  "coordinator": "spark-performance-architect",
  "rule_areas": ["SF-PY", "SF-UI", "SF-PLAN", "SF-BENCH", "SF-FVAL", "SF-TIMEOUT", "SF-WASTE", "SF-BRIDGE"],
  "steps": [
    {"order": 1, "executor": "sf-inventory", "function": "inventory", "does": "Mapeia o terreno antes de qualquer análise: ..."},
    {"order": 2, "executor": "sf-extractor", "function": "extract", ...},
    {"order": 3, "executor": "sf-judge", "function": "judge", ...},
    {"order": 4, "executor": "sf-verifier", "function": "verify", ...},
    {"order": 5, "executor": "sf-synthesizer", "function": "synthesize", ...}
  ],
  "note": "Decomposicao sequencial. Em Claude Code os mesmos passos sao despachados como subagentes; aqui um agente so os segue em ordem, ..."
}
```

O `playbook` funciona em todas as plataformas e não depende de subagente. Quando o
despacho está desligado, ele é o caminho.

**Erros comuns**

| Sintoma | Causa | Solução |
|---|---|---|
| `recommended_agent: null` | nenhuma rota de agent casou com a fase atual | siga `recommended_skill`, ou use o `playbook` do coordenador geral |
| `recommended_skill: sparkforge-diagnose` com "Nenhuma regra de roteamento casou" | o case está num estado que nenhuma rota cobre | volte ao diagnóstico geral e anote em `open_questions` o que falta |
| `sparkforge: error: unrecognized arguments` | flag errada ou `sparkforge` antigo | confira com `--help` e compare as versões (veja a receita) |

## Skills AWS oficiais complementares

Onze skills descrevem **procedimentos de serviços AWS**. Elas foram adaptadas do
`aws/agent-toolkit-for-aws`:

`provision-s3-tables-table`, `harden-s3-bucket`, `aws-storage`, `aws-database`,
`aws-serverless`, `aws-iam`, `aws-observability`, `aws-billing-and-cost-management`,
`aws-messaging-and-streaming`, `aws-security` e `aws-sdk-python-usage`.

- **Use** quando a pergunta é sobre o serviço: qual storage escolher, como escrever
  uma policy IAM, como ler o relatório de custo (CUR).
- **Não use** para diagnosticar job PySpark. Para isso existem as skills
  `analyze-*`, `diagnose-*`, `benchmark-pyspark-job` e os verbos `tune` e `funcval`.

> **Cuidado: estas skills podem mudar infraestrutura viva.** Elas citam comandos de
> escrita na AWS (por exemplo, `create-role` e `put-role-policy`). A seção `## Não faz`
> de cada uma exige a **sua confirmação explícita para cada comando de escrita**. Por
> isso elas nunca rodam como subagente: um subagente não consegue perguntar nada a
> você. Se um agent propuser um comando de escrita, leia antes de aprovar.

## Próximos passos

- [Investigação com case](usos/investigacao-com-case.md): o case, as hipóteses e a retomada.
- [Arbitragem e debate](usos/arbitragem-e-debate.md): quando dois achados brigam.
- [Mudanças com prova](usos/mudancas-com-prova.md): antes e depois de mudar.
- [Job lento](usos/job-lento.md): o caso mais comum, de ponta a ponta.
- Referência: [agents](referencia/agents/README.md), [skills](referencia/skills/README.md),
  [comandos](referencia/cli/README.md), [tools](referencia/tools/README.md).
