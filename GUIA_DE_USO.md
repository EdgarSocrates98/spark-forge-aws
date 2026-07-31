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

## 5. Ordem prática dos artefatos

Forneça nesta ordem:

1. Estrutura do repositório.
2. Terraform.
3. Entry point.
4. Biblioteca.
5. Plano `explain("formatted")`.
6. Spark UI.
7. Logs da falha.
8. CloudWatch.
9. Metadata tables Iceberg.
10. Baseline.

## 6. Quando faltarem dados

Peça ao agente para gerar:

- instrumentação;
- consultas Iceberg;
- comandos de coleta;
- logs estruturados;
- métricas por etapa;
- benchmark reprodutível.

## 7. Critério de conclusão

A investigação só está concluída quando houver:

- gargalo dominante comprovado;
- arquitetura-alvo;
- mudança implementada;
- benchmark;
- validação funcional;
- custo;
- risco;
- rollback.

## 8. Retomando entre Devin e Claude Code

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

## 9. Sem MCP e sem Python

Se as tools MCP não estiverem disponíveis, use a CLI `sparkforge` (mesmas
funções, mesma saída). Se nem Python estiver disponível, leia
`rules/catalog/*.yaml` diretamente — é YAML legível por humano, com o mesmo
`rule_id`, o mesmo limiar, a mesma guarda de versão (`runtime_scope`) e a
mesma fonte datada que o motor usaria. A automação cai; o conhecimento não.
