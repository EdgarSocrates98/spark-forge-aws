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

Em Claude Code, o coordenador indicado despacha os cinco executores (`sf-inventory`,
`sf-extractor`, `sf-judge`, `sf-verifier`, `sf-synthesizer`) como subagentes, na ordem do
loop de fase. Em Devin, Codex ou Copilot CI — que não despacham subagente —
`sparkforge playbook <coordenador>` (CLI) ou a tool MCP `sparkforge_playbook` devolve a
mesma decomposição em passos sequenciais: o que cada executor faz, não faz, pressupõe e
entrega, na ordem certa.

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
