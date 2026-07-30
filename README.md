# SparkForge AWS

Sistema especialista de diagnóstico, tuning, revisão e benchmarking para jobs **PySpark no AWS Glue**, com foco em **Amazon S3, Parquet, Apache Iceberg, Glue Data Catalog, Spark UI e CloudWatch**.

O pacote foi estruturado para funcionar em:

- Claude Code: `.claude/skills` e `.claude/agents`
- Devin: `.agents/skills`
- GitHub Copilot: `.github/copilot-instructions.md`, `.github/instructions`, `.github/prompts` e `.github/agents`
- Qualquer agente compatível com o padrão Agent Skills: `skills/`


## Investigação de fluxos full e incrementais

Para casos com latest-per-key, tabelas Iceberg bilionárias, batching, OOM e cargas muito variáveis, comece por:

1. `PROMPT_INICIAL_MESTRE.md`
2. `GUIA_DE_USO.md`
3. Skill `glue-incremental-performance-architect`

A versão 0.2.0 inclui Skills específicas para arquitetura incremental, latest-per-key, loops de batching, call graph da biblioteca, OOM, Terraform e perfis de volume.

## Base de conhecimento

`knowledge/` é a fonte de verdade sobre **como Spark, Glue, Athena, Parquet e Iceberg se comportam** — separada de `skills/` (procedimento) e de `.sparkforge/` (estado da investigação). Comece por [`knowledge/INDEX.md`](knowledge/INDEX.md).

Cobertura: modelo de execução do Spark, referência de configuração com defaults exatos, shuffle/join/skew, memória e as sete classes de OOM, leitura de plano físico, matriz de runtime Glue, worker types e capacidade, argumentos de job, métricas de observabilidade, performance de Athena, layout Parquet/S3 e Iceberg.

Ler [`knowledge/cross-service-constraints.md`](knowledge/cross-service-constraints.md) antes de recomendar mudança de versão, formato de tabela ou particionamento — são as armadilhas em que a mudança funciona no job e quebra no consumidor.

`rules/catalog/` é a forma **executável** desse conhecimento: 59 regras em YAML com `rule_id`, limiar, guarda de versão e fonte com data. Funciona como conhecimento consultável mesmo sem o motor Python — é o terceiro degrau da escada de portabilidade. Ver [`rules/catalog/README.md`](rules/catalog/README.md).

## Camada determinística (Fase 0)

Além da base de conhecimento e das Skills (que orientam um LLM), o pacote
inclui um analisador determinístico: extração de facts via AST estático
(nunca importa nem executa código analisado), julgamento contra um catálogo
de 43 regras versionado em YAML, e um ciclo de vida de case
(`.sparkforge/case.yaml`) que atravessa sessões e ferramentas.

### Sequência mínima

```bash
pip install -e .
sparkforge runtime detect --glue 5.0
sparkforge analyze pyspark --path lib/ --out .sparkforge/facts.json
sparkforge judge --facts .sparkforge/facts.json --glue 5.0 --out .sparkforge/findings.json
sparkforge next-step --repo . --findings .sparkforge/findings.json
```

### Por que extração e julgamento são verbos separados

`analyze` (extração) e `judge` (julgamento) nunca são o mesmo passo. Facts
extraídos de código-fonte são caros de recomputar — exigem re-parsear a
árvore inteira — mas o catálogo de regras evolui com frequência maior que o
código: um limiar corrigido, uma regra nova, uma fonte atualizada. Separar os
dois verbos permite **rejulgar facts antigos com um catálogo novo sem
reprocessar o código-fonte**, o que torna a evolução do conhecimento
auditável: cada revisão do catálogo pode ser aplicada retroativamente ao
mesmo conjunto de facts e o diff do resultado mostra exatamente o que mudou
no julgamento, isolado de qualquer mudança no código analisado.

### Canais de distribuição

| Canal | Como chega | Para quem |
|---|---|---|
| Plugin do Claude Code | `.claude-plugin/plugin.json`, instalado via marketplace ou path local | Claude Code |
| MCP (`sparkforge.adapters.mcp`) | `.mcp.json`, transportes `stdio` e `http` | Devin Desktop, Devin CLI, GitHub Copilot |
| `pip` | `pip install -e .` ou `pip install sparkforge-aws` | CLI `sparkforge` em qualquer shell/CI |
| Espelhos markdown | `rules/catalog/*.yaml`, `skills/`, `knowledge/` | Sem MCP e sem Python — leitura direta |

### Fluxo de handoff

`sparkforge handoff --repo <raiz>` escreve `.sparkforge/handoff.md` a partir
do mesmo payload que `sparkforge resume` produz — os dois nunca divergem
porque vêm da mesma função. Ao encerrar ou pausar uma investigação, commite:

```bash
git add .sparkforge/case.yaml .sparkforge/facts.json .sparkforge/findings.json .sparkforge/handoff.md .sparkforge/artifacts/manifest.json
```

Esses cinco arquivos são pequenos, derivados, e são o barramento de handoff
entre sessões e ferramentas (Devin, Claude Code, CI).

**`.sparkforge/artifacts/**` nunca é commitado**, exceto o `manifest.json`
acima — o `.gitignore` já bloqueia isso. É onde ficam os artefatos brutos
coletados (event logs, planos físicos, saída de Terraform): podem carregar
dados de negócio e chegar a centenas de MB. O que substitui o artefato bruto
no commit é o manifesto: ele registra `sha256`, `source` (origem) e
`collect_command` (comando exato de recoleta) para cada artefato, de modo
que uma sessão que retome em outra ferramenta saiba exatamente o que falta e
como coletar de novo.

## Objetivos

1. Encontrar o gargalo dominante antes de sugerir alterações.
2. Correlacionar código, plano físico, Spark UI, CloudWatch, configuração do Glue e layout de dados.
3. Produzir recomendações baseadas em evidências, com riscos, trade-offs, validação e rollback.
4. Melhorar runtime, DPU-hours, custo, escalabilidade e confiabilidade sem alterar o resultado funcional.
5. Tratar Parquet e Iceberg como camadas diferentes de otimização.
6. Ser consciente da versão do AWS Glue, Spark e Iceberg.

## Skills incluídas

Cada skill segue um formato padronizado: `description` orientada ao gatilho ("Use quando…"), procedimento, **Quando NÃO usar**, **Referência rápida** (sintoma → sinal/limiar → ação) e **Red flags**.

| Skill | Use quando… |
|---|---|
| `sparkforge-diagnose` | precisar do diagnóstico ponta a ponta e não souber o gargalo dominante |
| `glue-incremental-performance-architect` | orquestrar investigação de fluxos full + incremental (biblioteca, OOM, batching) |
| `optimize-pyspark-code` | revisar/refatorar código PySpark ou Spark SQL |
| `analyze-spark-plan` | interpretar `explain()`/`EXPLAIN` e o plano físico |
| `analyze-spark-ui` | ler Spark UI/event logs (stage lento, skew, spill, GC) |
| `analyze-library-call-graph` | mapear actions/reads/writes escondidos numa biblioteca Python |
| `analyze-batch-loop` | houver actions/writes dentro de loop e recomputação de DAG |
| `design-incremental-processing` | um "incremental" fizer scan global ou recomputar histórico |
| `optimize-latest-per-key` | calcular registro mais recente por chave em tabela grande |
| `optimize-variable-volume-job` | o mesmo job receber de dezenas a centenas de milhões de registros |
| `diagnose-data-skew` | poucas tasks dominarem o tempo por hot keys/nulls |
| `diagnose-oom` | houver OOM (driver, executor, broadcast, metadata, lineage) |
| `tune-glue-job` | ajustar workers, Auto Scaling, argumentos e custo (com baseline) |
| `optimize-parquet-layout` | small files, listing lento e pruning ausente em Parquet/S3 |
| `optimize-iceberg-table` | dívida de data/delete files, snapshots, manifests e manutenção Iceberg |
| `benchmark-pyspark-job` | comprovar (não estimar) o impacto de uma mudança antes/depois |
| `review-pyspark-pr` | revisar um PR buscando regressões de performance e custo |
| `review-glue-terraform` | revisar o IaC do job (workers, Auto Scaling, args, observabilidade) |

## Instalação

### Instalar no próprio repositório

```bash
python scripts/install_skills.py --target /caminho/do/repositorio --all
```

### Apenas Claude Code

```bash
python scripts/install_skills.py --target . --claude
```

### Apenas Devin

```bash
python scripts/install_skills.py --target . --devin
```

### Apenas GitHub Copilot

```bash
python scripts/install_skills.py --target . --copilot
```

Use `--force` para substituir arquivos existentes.

### Manutenção das cópias (contribuidores)

A fonte da verdade das skills é `skills/`. As pastas `.claude/skills/` e `.agents/skills/` são espelhos byte-a-byte. Após editar uma skill em `skills/`, regenere os espelhos:

```bash
python scripts/sync_skills.py          # regenera os espelhos
python scripts/sync_skills.py --check   # falha se algo divergir (útil em CI)
```

Os testes (`pytest`) validam frontmatter, seções padronizadas, referências e paridade das três cópias.

## Uso rápido

### Claude Code

```text
/sparkforge-diagnose
/optimize-pyspark-code
/analyze-spark-plan
/optimize-iceberg-table
```

### GitHub Copilot

No Copilot Chat:

```text
/sparkforge-diagnose
/analyze-spark-plan
/review-pyspark-performance
```

### Devin

Peça explicitamente:

```text
Use a skill sparkforge-diagnose para analisar este job Glue.
```

## Dados mínimos recomendados

Forneça, sempre que possível:

- Código do job.
- Versão do AWS Glue.
- Tipo e quantidade de workers.
- Argumentos e Spark configs.
- Runtime e DPU-hours.
- Volume de entrada e saída.
- `df.explain("formatted")`.
- Screenshots ou event logs do Spark UI.
- Métricas do CloudWatch.
- Quantidade e tamanho dos arquivos.
- Metadados da tabela Iceberg.
- SLA e frequência do job.

## Regra central

> Não ajustar por intuição. Medir, formular hipótese, testar isoladamente e validar o resultado funcional.

## Segurança

As Skills não executam automaticamente alterações destrutivas. Operações como expiração de snapshots, remoção de arquivos órfãos, mudanças de particionamento e overwrite devem ser propostas com escopo, retenção, dry run quando disponível e plano de rollback.
