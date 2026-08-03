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

Há Skills específicas para arquitetura incremental (`design-incremental-processing`), latest-per-key (`optimize-latest-per-key`), loops de batching (`analyze-batch-loop`), call graph da biblioteca (`analyze-library-call-graph`), OOM (`diagnose-oom`), Terraform (`review-glue-terraform`) e perfis de volume (`optimize-variable-volume-job`). Desde a versão 0.4.0 elas são *toolkit-first*: chamam os extratores determinísticos em vez de descrever leitura por amostragem.

## Base de conhecimento

`knowledge/` é a fonte de verdade sobre **como Spark, Glue, Athena, Parquet e Iceberg se comportam** — separada de `skills/` (procedimento) e de `.sparkforge/` (estado da investigação). Comece por [`knowledge/INDEX.md`](knowledge/INDEX.md).

Cobertura: modelo de execução do Spark, referência de configuração com defaults exatos, shuffle/join/skew, memória e as sete classes de OOM, leitura de plano físico, matriz de runtime Glue, worker types e capacidade, argumentos de job, métricas de observabilidade, performance de Athena, layout Parquet/S3 e Iceberg.

Ler [`knowledge/cross-service-constraints.md`](knowledge/cross-service-constraints.md) antes de recomendar mudança de versão, formato de tabela ou particionamento — são as armadilhas em que a mudança funciona no job e quebra no consumidor.

`rules/catalog/` é a forma **executável** desse conhecimento: 60 regras de diagnóstico em YAML com `rule_id`, limiar, guarda de versão e fonte com data, mais 22 rotas determinísticas em `routing.yaml` (16 de skill, `ROUTE-001`…`ROUTE-016`, e 6 de coordenador, `AGENT-001`…`AGENT-006`). Funciona como conhecimento consultável mesmo sem o motor Python — é o terceiro degrau da escada de portabilidade. Ver [`rules/catalog/README.md`](rules/catalog/README.md).

## Camada determinística (Fase 0)

Além da base de conhecimento e das Skills (que orientam um LLM), o pacote
inclui um analisador determinístico: extração de facts via AST estático
(nunca importa nem executa código analisado), julgamento contra um catálogo
de 60 regras versionado em YAML, e um ciclo de vida de case
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

#### `pip install sparkforge-aws`: o pacote carrega o catálogo dentro dele

```bash
pip install sparkforge-aws            # CLI sparkforge sozinho
pip install "sparkforge-aws[aws]"     # + boto3, para os extratores que leem AWS
pip install "sparkforge-aws[mcp]"     # + servidor MCP (stdio e streamable HTTP)
```

Diferente de um `pip install` comum, este wheel não traz só código: `rules/catalog/`
(o catálogo de regras em YAML) e `knowledge/` (a base de conhecimento sobre
Spark, Glue, Athena, Parquet e Iceberg) vêm embarcados dentro do pacote,
resolvidos por `loader.catalog_dir()` na mesma ordem de sempre — variável de
ambiente, raiz do repositório e, faltando as duas, o fallback dentro do
próprio pacote instalado. É esse terceiro degrau que faz `analyze`, `judge`,
`next-step`, `resume` e `rules lookup` funcionarem **sem o repositório
clonado**: um agente autônomo que sobe um sandbox efêmero, roda `pip install
sparkforge-aws` e não tem mais nada em disco ainda assim consegue extrair
facts, julgar contra o catálogo completo e citar a fonte de cada limiar —
porque o catálogo veio junto no wheel, não porque o agente clonou o
repositório antes.

Para localizar `knowledge/` a partir do pacote instalado:

```bash
sparkforge knowledge path                                  # imprime a raiz
sparkforge knowledge path --file glue/runtime-matrix.md     # imprime um arquivo específico
```

`rules lookup` também devolve os caminhos já resolvidos: cada regra retornada
inclui os arquivos de `knowledge/` que a sua `explanation` cita, com o
caminho pronto para abrir — dentro do repositório em modo desenvolvimento,
dentro de `site-packages` quando instalado por `pip`.

Essa paridade não é promessa: o CI constrói o wheel, instala em venv limpo
**fora do repositório** e reproduz as 74 fixtures byte a byte a partir do
pacote instalado, em Linux e em Windows — o mesmo golden que o repositório
usa, não um corpus à parte. Se `sparkforge` acabar sendo importado do
repositório em vez do `site-packages` nesse processo, o gate falha com
mensagem explícita em vez de comparar o repositório consigo mesmo.

#### Os dois transportes MCP

```bash
pip install -e ".[mcp]"

# stdio — Claude Code, Devin CLI, CI. É o que .mcp.json já configura.
python -m sparkforge.adapters.mcp --transport stdio

# streamable HTTP — Devin Desktop, que configura MCP por serverUrl.
python -m sparkforge.adapters.mcp --transport http --host 127.0.0.1 --port 8765
# serverUrl: http://127.0.0.1:8765/mcp
```

O extra `mcp` fixa `mcp>=1.0,<2`: o SDK 2.x removeu os decoradores que
`build_server()` usa para registrar os tools, e sem o teto uma instalação
limpa resolveria para 2.x e o servidor quebraria no import — nos dois
transportes. `tests/test_adapters_mcp.py` constrói o servidor e o app ASGI de
verdade, para que um erro de API apareça no CI e não na máquina do operador.

### Extratores desbloqueados na varredura final

As cinco últimas regras inertes do catálogo passaram a disparar, e com elas
três extratores novos:

```bash
# small files, gzip não splitável, cardinalidade de partição
aws s3api list-objects-v2 --bucket lake --prefix analytics/pedidos/ > listing.json
sparkforge analyze s3-listing --path listing.json

# quem consome a tabela — arquivo declarado, versionado com o repositório
sparkforge analyze consumers --path .sparkforge/consumers.yaml

# o que mudou entre dois estados do mesmo módulo Terraform
sparkforge analyze terraform-diff --before ./infra-main --after ./infra-pr
```

Nenhum deles chama a AWS: o primeiro lê o dump que você coletou, o segundo lê
um arquivo que a sua organização escreve, o terceiro lê HCL de dois
diretórios. `rules/catalog/` não tem mais nenhuma regra com `blocked_on` — o
que falta para uma regra disparar é sempre coleta, nunca código.

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

## Coordenadores e executores

Além das Skills (procedimento) e da camada determinística (extração e julgamento), o
pacote tem duas camadas de agente:

- **Coordenador** — 6 agentes em `agents/*.md`, um por área de investigação
  (`spark-performance-architect`, `glue-incremental-performance-architect`,
  `glue-infra-reviewer`, `athena-query-optimizer`, `pyspark-code-reviewer`,
  `iceberg-performance-engineer`). Não executa: lê o case, decide qual executor rodar em
  seguida e registra no case qual executor rodou e com que resultado. Ver a tabela
  completa em `AGENTS.md`.
- **Executor** — 5 agentes em `agents/executors/*.md`, um por função do loop de fase
  (`sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier`, `sf-synthesizer`). Cada um
  declara `## Faz`, `## Não faz`, `## Pressupõe` e `## Entrega` — a fronteira negativa e o
  contrato de handoff que fazem a cadeia ser determinística entre modelos.

Qual coordenador usar é dado, não julgamento: as rotas `AGENT-001`…`AGENT-006` de
`rules/catalog/routing.yaml` mapeiam fase do case e área do achado dominante para o
coordenador certo, e `sparkforge_next_step`/`sparkforge next-step` as consulta.

Em Claude Code, o coordenador despacha os cinco executores como subagentes. Em qualquer
outra plataforma sem despacho de subagente — Devin, Codex, Copilot CI —
**`sparkforge playbook <coordenador>`** (CLI) ou a tool MCP `sparkforge_playbook` devolve a
mesma decomposição em passos sequenciais, lendo os mesmos arquivos de `agents/`: perde o
paralelismo do despacho, mantém o método.

## Instalação

### Instalar no próprio repositório

```bash
cd /caminho/do/repositorio && python /caminho/do/sparkforge/scripts/install_skills.py --all
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

A instalação escreve **no diretório atual** — por isso o `cd` no primeiro
exemplo. `--target` é opcional e serve como confirmação explícita do destino:
se for passado e não for o diretório atual, o script recusa e mostra o `cd`
correto, em vez de escrever num lugar que você não estava olhando.

### Manutenção das cópias (contribuidores)

A fonte da verdade das skills é `skills/`. As pastas `.claude/skills/` e `.agents/skills/` são espelhos byte-a-byte. Após editar uma skill em `skills/`, regenere os espelhos:

```bash
python scripts/sync_skills.py          # regenera os espelhos
python scripts/sync_skills.py --check   # falha se algo divergir (útil em CI)
```

O repositório tem **três** espelhos gerados, e cada um tem seu `--check` rodando no CI.
Editar a fonte e esquecer o espelho quebra a build — de propósito, porque drift em
manifesto silencioso é pior que erro barulhento:

| Espelho | Fonte | Comando | Por que existe |
|---|---|---|---|
| `.claude/`, `.agents/`, `.github/` | `skills/`, `agents/` | `python scripts/sync_skills.py --check` | Cada plataforma lê de um diretório próprio |
| `requirements.txt` | `pyproject.toml` | `python scripts/gen_requirements.py --check` | Ferramenta de SCA não lê `pyproject.toml` sem lockfile — e scan que não roda não é scan que passa |
| `sparkforge/rules/catalog/`, `sparkforge/knowledge/` (só no artefato) | `rules/catalog/`, `knowledge/` | `python scripts/verify_wheel.py` | `force-include` do hatchling embarca no build, sem duplicar arquivo em git |

O terceiro não existe em disco: nasce no build e é verificado pelo gate de paridade, que
constrói o artefato, instala num venv limpo e reproduz as 74 fixtures byte a byte.

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
