# SparkForge AWS — estado por fase

**Atualizado em:** 2026-07-31
**Commit de referência:** branch `feat/fase4-agentes`
**Versão do pacote:** `0.5.0` — consistente em `pyproject.toml`, `manifest.json`,
`.claude-plugin/plugin.json` e `sparkforge.__version__`. A concordância entre as
quatro é verificada por
`tests/test_package_importable.py::test_every_manifest_declares_the_same_version`;
nenhum teste fixa o número, porque o que precisa ser garantido é que as quatro
fontes não divirjam, não qual é o valor.

`schema_version` e `catalog_version` continuam em `1`, de propósito: nenhum
contrato de dados mudou e nenhum limiar existente mudou. Subir os três juntos
destruiria a reauditabilidade que a §12.2 da spec da Fase 0 quer — um Finding
gravado com `catalog_version: 2` sugeriria que o limiar que o julgou é outro.

Este arquivo é a fonte da verdade sobre **onde o projeto está**. Os specs e plans
em `specs/` e `plans/` são registro histórico de decisão: descrevem o que se
pretendia numa data, não o repositório de hoje. Quando um número divergir, este
arquivo ganha.

---

## Números correntes

| Dimensão | Valor | Onde conferir |
|---|---|---|
| Testes | **1932** passando, 5 skipped | `python -m pytest -q` |
| Extratores de facts | **13** | `sparkforge/facts/*.py` |
| Fact kinds distintos emitidos | **80** | união de `EMITTED_KINDS` |
| Regras de diagnóstico | **48** | `load_catalog()` |
| Regras bloqueadas (`blocked_on`) | **0** | `rules/catalog/*.yaml` |
| Regras com golden que dispara | **48 de 48** | `tests/test_fixtures_kind_coverage.py` |
| Rotas determinísticas | **22** (`ROUTE-001`…`ROUTE-016`, `AGENT-001`…`AGENT-006`) | `rules/catalog/routing.yaml` |
| Tools MCP | **30** | `sparkforge.adapters.tools.TOOLS` |
| Tools alcançáveis a partir de algum coordenador | **30 de 30** | `tests/test_agent_coverage.py` |
| Coordenadores | **6** | `agents/*.md` |
| Executores | **5** | `agents/executors/*.md` |
| Fixtures golden | **74** em 15 domínios | `fixtures/` |
| Fontes oficiais vigiadas | **20** (16 móveis, 4 fixas) | `knowledge/sources.lock.json` |
| Pares de eval | 10 | `evals/fase0.xml` |

Regras por área: SF-PY 12, SF-UI 6, SF-GLUE 6, SF-ATH 5, SF-ICE 5, SF-PQ 5,
SF-PLAN 4, SF-ENV 4, SF-CG 1.

Fixtures por domínio: `pyspark` 17, `iceberg` 8, `plan` 7, `terraform` 7,
`fusion` 5, `runtime` 5, `s3` 5, `sql` 4, `athena` 3, `catalog` 3, `consumers` 3,
`callgraph` 2, `infra_code` 2, `tfdiff` 2, `eventlog` 1.

---

## Fases

### Fase 0 — contratos, extração determinística e paridade — **CONCLUÍDA** (2026-07-30)

Documentos: [spec](specs/2026-07-29-sparkforge-fase0-design.md) ·
[plan](plans/2026-07-29-sparkforge-fase0.md) · errata na §18 do spec.

Entregou as seis camadas com fronteiras negativas (`facts/`, `rules/`,
`findings/`, `case/`, `collect/`, `adapters/`), o avaliador `expr` com whitelist
de nós AST, os contratos `Fact`/`Finding`/`RuntimeContext` com ordenação
determinística, o `case.yaml` com roteamento por dado, CLI + MCP, o plugin do
Claude Code, `AGENT_PROTOCOL.md`, `parity.yaml` e a suíte de eval.

Faixa de commits: `66fcb6f` … `7d51664`, fechada pelo merge `7cc739e`.

### Fase 1 — extratores restantes e coletores AWS — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-30-sparkforge-fase1-design.md) ·
[plan](plans/2026-07-30-sparkforge-fase1.md).

Doze extratores novos além de `pyspark_ast`, os coletores AWS, a etapa de fusão
de facts, e a superfície de CLI e MCP para cada um. Fecha com uma auditoria
(`bb72f9f`) que corrigiu seis defeitos, incluindo o transporte HTTP do MCP, que
era paridade afirmada e não testada.

Faixa de commits: `97b0818` … `bb72f9f`.

### Fase 2 (executada) — desbloqueio do catálogo — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-31-sparkforge-fase2-design.md) ·
[plan](plans/2026-07-31-sparkforge-fase2.md).

> **Atenção ao nome.** A "Fase 2" que o repositório executou (branch
> `feat/fase2-desbloqueios`) **não** é a Fase 2 do roadmap da §16 do spec da
> Fase 0. O roadmap chama de Fase 2 a expansão do knowledge e o
> `refresh_knowledge`. O que foi executado é o oposto: nenhuma regra nova, e sim
> a construção dos extratores que faltavam para que as regras já committadas
> parem de ser inertes.

Levou o catálogo de 5 regras com `blocked_on` e 3 sem golden positivo para
**0 bloqueadas e 43 de 43 provadas por fixture**, e travou os dois invariantes
que impedem a regressão.

Faixa de commits: `dc80efd` … `b44edd0`, merge `bc53865`.

### Fase 2 do roadmap (§16) — knowledge — **CONCLUÍDA** (2026-07-31)

Distinta da "Fase 2 executada" logo acima, que era desbloqueio de catálogo. Esta
é a que a §16 do spec da Fase 0 chama de Fase 2, e estava aberta até agora:

- **`refresh_knowledge`** — construído, com PR de revisão e sem auto-commit. Ver
  a seção de dívidas fechadas.
- **Matriz de compatibilidade** — as fontes de que ela depende entram na mesma
  watchlist; o guard de drift entre `knowledge/glue/runtime-matrix.md` e
  `GLUE_MATRIX` já existia desde `bb72f9f`.
- **Expansão do catálogo** — SF-PLAN (4 regras sobre plano físico) e SF-CG (1
  sobre grafo de chamadas) cobrem as duas capacidades da Fase 1 que nenhuma
  regra consumia. 43 → 48 regras.

### Fase 3a — distribuição pip — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-31-sparkforge-fase3a-pip-design.md) ·
[plan](plans/2026-07-31-sparkforge-fase3a-pip.md).

O defeito de partida: `pip install` entregava só código. O wheel construído
com o backend `setuptools` anterior tinha 43 arquivos e zero de
`rules/catalog/`, `knowledge/` ou `skills/` — `judge`, `next-step`, `resume` e
`rules lookup` morriam num pacote instalado fora do repositório, porque
`loader.catalog_dir()` caía no fallback `sparkforge/rules/catalog/`, que
nunca existiu em disco nem no artefato.

**Decisão central: backend `hatchling` com `force-include`, preservando a
decisão D-A da Fase 0.** `rules/catalog/` e `knowledge/` continuam morando na
raiz do repositório — são o terceiro degrau da escada de portabilidade, o
YAML que um agente sem Python lê direto — e `force-include` os copia para
dentro do pacote **no momento do build**, sem duplicar arquivo em git. Nenhum
código de `loader.catalog_dir()` foi tocado: a ordem de resolução (variável de
ambiente → raiz do repo → fallback no pacote) já estava certa desde a Fase 0;
faltava o arquivo chegar ao fallback.

Um defeito real apareceu no caminho: o sdist não pode carregar o **mesmo**
`force-include` do wheel, porque isso realoca `knowledge/` para dentro de
`sparkforge/` já dentro do tarball, e o wheel construído a partir desse sdist
(o fluxo padrão de `python -m build`, e o que `pip install` usa sem wheel
compatível) procura `knowledge` na raiz e não acha mais. O sdist usa `include`
simples, que preserva os diretórios onde o `force-include` do wheel espera
achá-los. Corrigido no commit `830923e`, exposto pelo gate de paridade desta
mesma fase — ver §4.3 do spec, corrigida nesta rodada de fechamento.

Entregou também: metadata de publicação completa (`readme`, `license`,
`classifiers`, `urls` apontando para `EdgarSocrates98/spark-forge-aws`, não
para a organização inexistente que `plugin.json` citava); o resolvedor de
`knowledge/` a partir do pacote (`sparkforge knowledge path [--file]`, nos dois
adaptadores CLI e MCP); `rules lookup` devolvendo os caminhos de knowledge já
resolvidos; a asserção de procedência que reprova o gate se `sparkforge` for
importado do repositório em vez do `site-packages`; o gate de paridade
(`scripts/verify_wheel.py`) que constrói sdist + wheel, instala em venv limpo
fora do repositório e reproduz as 74 fixtures byte a byte; o job de CI que
roda esse gate em `ubuntu-latest` e `windows-latest`; e `release.yml`, que
constrói, prova, anexa artefatos a um GitHub Release em rascunho e **não
publica** — publicação continua ato manual do mantenedor.

Faixa de commits: `a06d7f5` … `2b6311c`.

### Fase 4 (executada) — coordenadores, executores e espelho de orquestração — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-31-sparkforge-fase4-agentes-design.md) ·
[plan](plans/2026-07-31-sparkforge-fase4-agentes.md).

> **Atenção ao nome**, mesma advertência da "Fase 2 executada" acima. Esta é a Fase 4 da
> seção "Direção: de analisador de performance a time de engenharia de dados" mais abaixo
> neste arquivo — **não** é a Fase 4 do roadmap da §16 do spec da Fase 0, que a seção "Fase
> 4 do roadmap (§16) — rigor" continua descrevendo, ainda não iniciada.

O defeito de partida não era falta de agente, era falta de alcance: medido na abertura,
**21 das 29 tools MCP não eram citadas em agente nenhum nem em skill nenhuma** — capacidade
que existe e não é alcançável não é capacidade. Entregou 6 coordenadores (os 3 existentes
mais `glue-infra-reviewer`, `athena-query-optimizer` e `pyspark-code-reviewer`) e 5
executores em `agents/executors/`, um por função do loop de fase (`sf-inventory`,
`sf-extractor`, `sf-judge`, `sf-verifier`, `sf-synthesizer`), cada um com fronteira
negativa (`## Não faz`) e contrato de handoff (`## Pressupõe`/`## Entrega`) que fecha a
cadeia sem elo solto.

As 30 tools MCP de hoje (a Fase 4 acrescentou `sparkforge_playbook` às 29 do início) são
**alcançáveis a partir de algum coordenador**, travado por
`tests/test_agent_coverage.py::TestEveryToolIsReachable`. As 9 áreas de regra têm
coordenador. Roteamento de coordenador virou dado: rotas `AGENT-001`…`AGENT-006` em
`rules/catalog/routing.yaml`, que `sparkforge_next_step` consulta como as demais. `sparkforge
playbook <coordenador>` (CLI) e a tool MCP `sparkforge_playbook` dão a mesma decomposição
sequencial, lendo `agents/` e `agents/executors/`, para quem não despacha subagente —
`parity.yaml` ganhou `codex` como plataforma e `playbook` como mecanismo, com caminho
verificado nas cinco plataformas. Isso fecha a dívida "Agente não é mecanismo de paridade
declarado" (ver seção de dívidas abaixo).

Faixa de commits: `4cf81c8` (spec) … `d366eb9`, fechada pelo commit de documentação desta
mesma fase.

### Fase 3b — marketplace de plugin — **NÃO INICIADA**

Escopo da §16: `marketplace.json` e instalação do plugin do Claude Code por
marketplace, em vez de path local. Spec próprio, ainda não escrito.

### Fase 3c — export Devin (Playbook/Knowledge) — **NÃO INICIADA**

Escopo da §16: exportar `skills/` e `knowledge/` para o formato de
Playbook/Knowledge de uma conta Devin. Spec próprio, ainda não escrito.

### Fase 3d — MCP hospedado — **NÃO INICIADA**

Escopo da §16: hospedar o transporte `streamable-http` do MCP em vez de rodar
localmente. Parcial existente: o transporte HTTP já funciona localmente
(`python -m sparkforge.adapters.mcp --transport http`) e é testado desde a
Fase 1. Falta hospedagem. Spec próprio, ainda não escrito.

### Fase 5a — correção de escopo — **CONCLUÍDA** em 2026-08-01

Branch `feat/fase5a-escopo`. Plano:
[`plans/2026-08-01-sparkforge-fase5a-escopo.md`](plans/2026-08-01-sparkforge-fase5a-escopo.md).
Spec: [`specs/2026-08-01-sparkforge-fase5-emr-design.md`](specs/2026-08-01-sparkforge-fase5-emr-design.md),
§3.1, §3.2 e critérios 10, 11 e 13.

**O defeito.** `runtime_scope` é guarda de **versão**. Vinha sendo usado como
etiqueta de **serviço** — e o ramo do curinga em
`sparkforge/rules/version_scope.py` pulava a checagem de presença da chave,
então `{glue: "*"}` casava com qualquer runtime. Ele nunca filtrou nada.

A execução encontrou quatro famílias do mesmo erro de camada, três delas não
previstas pelo plano:

| Família | Regras | O que era | O que virou |
|---|---|---|---|
| `{glue: "*"}` em regra agnóstica | 20 | AST, plano, armazenamento, execução | escopo vazio, gate por `requires_facts` |
| `{athena: "*"}` | 5 | `athena` **nunca é detectado** — default `""`, só a flag `--athena` preenche | escopo vazio |
| `{iceberg: ">=1.0.0"}` | 5 | gate de Glue disfarçado: `iceberg` só é resolvido por flag ou inferido de `GLUE_MATRIX` | escopo vazio |
| `{spark: ">=3.0"}` | 28 | falhava fechado num `judge` sem flags — **6 das 9 áreas do catálogo sumiam** | escopo vazio |

A quarta foi criada pela própria fase: mover 19 regras de `{glue: "*"}` para
`{spark: ">=3.0"}` trocou um rótulo permissivo e errado por um guarda estrito e
errado. Medido e corrigido antes de sair da branch.

**O critério que ficou.** `runtime_scope` só pode ser não-vazio quando o
**gatilho** da regra genuinamente varia com a versão **e** essa versão vem do
runtime, não de um fact que a própria regra já lê. Restaram 8 de 48, todas
sobre Glue: `SF-ENV-002`, `SF-ENV-003`, `SF-GLUE-001` e as 5 `SF-GLUE-002..006`.

**`SF-GLUE-002` reancorada.** Seu `requires_facts` era `tf.module_analyzed`,
sentinela de "algum `.tf` foi lido". Num repositório sem `aws_glue_job` ela
passava a barreira, avaliava, dava falso, e sumia de findings **e** de skipped —
mesmo num runtime que era Glue. Passou a exigir `tf.resource`, que
`sparkforge/facts/terraform.py:678` só emite depois do filtro
`resource_type == "aws_glue_job"`. Prova as duas coisas de uma vez: o extrator
rodou **e** há job Glue. Nenhum golden mudou.

**Números correntes.** 48 regras, 40 com escopo vazio, 8 com guarda de versão.
Num `judge` sem flags, 40 avaliadas e só `SF-GLUE` pulada — que é o correto.
2124 testes passando, ruff limpo, espelhos conferindo.

**Invariantes novos**, em `tests/test_rule_scope_by_nature.py` e
`tests/test_skill_content.py`:

- regra agnóstica não some num runtime sem `glue`
- regra dependente de Glue aparece como **pulada**, não avalia em silêncio
- nenhum `runtime_scope` com valor `"*"` fora de uma allowlist por chave — foi a
  literalidade do teste antigo, que procurava a string `{'glue': '*'}`, que
  deixou `{athena: "*"}` passar
- **nenhuma área do catálogo some inteira** por versão não detectada, com
  exceção declarada e justificada para `SF-GLUE`. Runtimes derivados de
  `GLUE_MATRIX` mais o contexto vazio da CLI, então versão nova entra sozinha
- toda invocação de `sparkforge judge` nas skills passa runtime

### Fase 5b — EMR — **NÃO INICIADA**

Spec escrito e revisado; plano ainda não. O eixo de infraestrutura que só existe
hoje para Glue: `emr` no `RuntimeContext`, `EMR_MATRIX`, extrator de cluster
(EMR on EC2 primeiro), release label, instance fleets vs. instance groups, EMR
Serverless, EMR on EKS, área `SF-EMR` no catálogo, coordenador próprio, e a
divergência de plataforma da §3.3 do spec.

Herda três decisões que a 5a mediu e deixou registradas:

1. **Inferir runtime dos facts.** `build_runtime_context`
   (`sparkforge/adapters/_core.py:104-121`) monta o contexto só de flags da CLI,
   nunca do que os extratores observaram. É a causa raiz de todo guarda falhar
   fechado, e é trabalho necessário para detectar EMR de qualquer forma.
2. **`proposed_change` ramificado por versão.** Cinco regras têm gatilho
   agnóstico mas recomendação que cita AQE ou o hint `REBALANCE`, de Spark 3.2:
   `SF-PY-005`, `SF-PY-009`, `SF-PY-010`, `SF-PQ-001` e `SF-UI-006`. Com escopo
   vazio elas disparam onde o conselho pode não se aplicar. Foi pesado e aceito —
   apagar um P0 real por causa de um bullet de remediação é o erro maior — mas a
   remediação merece ramo.
3. **`SF-ENV-002` é o guarda não-vazio mais fraco.** Seu `when` já lê
   `format-version == 3` de `iceberg.table_property`, então
   `{glue: ">=5.1", iceberg: ">=1.10.0"}` é redundante do mesmo jeito que o de
   `SF-ENV-004` era. Hoje sem efeito medível — a regra é inerte, `env.consumer`
   não tem extrator — e `test_the_iceberg_v3_rule_is_scoped_to_51_and_only_51`
   a fixa deliberadamente.

### Fase 4 do roadmap (§16) — rigor — **NÃO INICIADA**

Distinta da "Fase 4 (executada)" acima (coordenadores, executores e espelho de
orquestração), que é a Fase 4 na nova numeração da seção "Direção" mais abaixo. Esta
continua sendo a Fase 4 do roadmap original: escopo da §16 — gates fail-closed opcionais,
benchmark automatizado antes/depois, validação funcional automatizada (contagem, schema,
chaves, agregados), assinatura de relatório. `blocked_by` segue advisory, como a §5.5 da
Fase 0 decidiu conscientemente.

---

## Dívidas — fechadas em 2026-07-31

As cinco dívidas listadas na versão anterior deste arquivo foram tratadas. Duas
delas **estavam mal enunciadas por mim**, e a correção está registrada aqui em
vez de apagada: um inventário de dívidas que só cresce e nunca se corrige vale
tão pouco quanto um que nunca se atualiza.

| Dívida (como estava escrita) | Desfecho |
|---|---|
| `refresh_knowledge` não existe | **Construído.** `scripts/refresh_knowledge.py` + workflow manual/semanal que abre PR e nunca commita em main |
| Matriz de compatibilidade não é automatizada | **Coberta pelo mesmo mecanismo.** As URLs de que a matriz depende estão na watchlist; mudança nelas vira PR de releitura |
| Três eixos de versionamento parados em 1/1/0.4.0 | **Resolvida com uma decisão, não com três bumps.** Pacote em `0.5.0`; `schema_version` e `catalog_version` ficam em 1 porque nada que eles versionam mudou |
| Catálogo cobre 7 áreas, não as 18 skills | **Enunciado errado.** 15 das 18 skills já citavam regra. O gap real era *capacidade sem regra*, não *skill sem regra*: `plan.*` e `callgraph.*`. Fechado com SF-PLAN (4 regras) e SF-CG (1) |
| Glue 3.0 na `GLUE_MATRIX` sem cobertura de fixture própria | **Falso.** `fixtures/runtime/pre_aqe_runtime/` é a fixture de Glue 3.0, e nela o 3.0 é o lado **positivo** de SF-ENV-004 — quem é o lado negativo é o Glue 4.0. A exclusão do 3.0 de `CURRENT` é deliberada e já documentada em `tests/test_runtime_glue_versions.py:31-33` |

### `refresh_knowledge` — o que ele faz e o que recusa fazer

Não baixa o texto das docs para o repositório. Guarda, em
`knowledge/sources.lock.json`, o hash do texto normalizado de cada fonte, a data
da conferência e **quais `rule_id` citam aquela URL**. O relatório não diz "a doc
mudou assim"; diz "a doc mudou, e as regras X e Y dependem dela — releia".

Três razões, na ordem em que pesam: o diff de uma página da AWS é quase todo
ruído de navegação, e relatório que grita sempre treina o operador a ignorá-lo;
copiar doc de terceiro para o repo é decisão de licenciamento que ninguém tomou;
e o objetivo nunca foi ter a doc, foi saber quando relê-la.

A watchlist é derivada do próprio catálogo — é o conjunto de `sources[].url`.
Regra nova com fonte nova entra sozinha; lista paralela é o passo que alguém
esquece. Fontes com versão no path (`docs/3.5.6/`, `apache-iceberg-1.0.0`) não
são buscadas: o conteúdo é imutável e vigiá-las só produziria ruído.

Na primeira execução real ele já encontrou uma citação quebrada — a URL do doc
de Arrow que SF-PLAN-001 citava era 404 (`user_guide/` em vez de `tutorial/`).

## Direção: de analisador de performance a time de engenharia de dados

Decidido em 2026-08-01. O projeto passa a mirar cobertura de engenharia de dados
no ecossistema AWS — arquitetura, ferramentas, resolução de problema, tuning,
análise e testes de dados — e não só performance de Glue PySpark.

A expansão tem duas metades que se comportam de forma **oposta** dentro da
arquitetura atual, e confundi-las destruiria a propriedade central do projeto
(§1 da spec da Fase 0: "qualidade acoplada ao modelo" é o inimigo).

### Metade A — cabe no motor existente

Tem artefato para extrair. É repetir o padrão da Fase 1, que já funcionou 12 vezes:
extrator novo → área de regra nova → fixtures com golden bidirecional.

| Capacidade | Artefato | Área |
|---|---|---|
| EMR | release label, instance fleets, EMR Serverless, EMR on EKS | `SF-EMR` |
| Testes de dados | saída de Deequ, Great Expectations, dbt tests; schema declarado | `SF-DQ` |
| Redshift | plano de query, `STL`/`SVL`, distkey e sortkey | `SF-RS` |
| Streaming | config de Kinesis e MSK, checkpoint de Structured Streaming | `SF-STR` |
| Orquestração | DAG de Airflow/MWAA, definição de Step Functions | `SF-ORC` |
| Custo | Cost Explorer, CUR, DPU-hours | `SF-COST` |
| IaC além de Terraform | CDK, CloudFormation | estende o extrator atual |

**Medição que favorece isso:** num runtime sem chave `glue`, 44 das 48 regras já
avaliam. A análise de código e execução é agnóstica por construção — AST, plano
físico, event log, Parquet, Iceberg. O que é Glue-específico é só o eixo de
infraestrutura. O motor já generaliza; falta plugar extrator.

**Primeira da fila: EMR.** Já estava listada, o gap está medido, e ela é a que
prova a generalização de runtime — o que destrava todas as outras.

### Metade B — exige mecanismo próprio

"Melhor arquitetura para X", "qual ferramenta usar", "desenhe a solução": **não
têm artefato**. Não há fato para extrair, regra para disparar, nem `fact_id` para
citar.

Entrar como área de regra normal quebraria o projeto em silêncio: o `judge`
emitiria achado que nenhum `Fact` sustenta, e `validate_output` — que hoje
rejeita ganho sem `benchmark_ref` — viraria obstáculo a contornar em vez de
guarda. Ninguém veria o momento da quebra.

**Decisão: mecanismo próprio, com garantia declarada.** Três níveis, explícitos
em vez de misturados:

| Camada | Garantia | Mecanismo |
|---|---|---|
| **Finding** | determinístico — mesmo input, mesma saída | catálogo + `fact_id` |
| **Restrição** | auditável — cita fonte e data | `knowledge/` + `rules_lookup` |
| **Recomendação de desenho** | rastreável — declara sobre quais restrições se apoia e **rotula o que é julgamento** | verbo próprio, nunca misturado com finding |

O caminho do meio já existe no repositório e é o que torna a Metade B viável:
"Athena não lê Iceberg V3" não é opinião, é fato com URL e data em
`knowledge/cross-service-constraints.md`. Recomendação construída **só sobre
restrições com fonte** não é determinística como um finding, mas é auditável.

O erro caro seria apresentar as três camadas com a mesma cara.

### Ordem

1. **Fase 4** — coordenadores, executores e `playbook` — **CONCLUÍDA** em 2026-07-31,
   branch `feat/fase4-agentes`. Ver seção própria acima.
2. **Fase 5a** — correção de escopo — **CONCLUÍDA** em 2026-08-01, branch
   `feat/fase5a-escopo`. Ver seção própria acima
3. **Fase 5b** — EMR, provando a generalização de runtime. Spec escrito, plano não
4. **Fases seguintes** — testes de dados, custo, orquestração, Redshift, streaming
5. **Trilha paralela** — mecanismo de recomendação com garantia declarada, quando a base de restrições estiver maior

## Dívidas abertas

| Dívida | Origem | Impacto |
|---|---|---|
| Fases 3b, 3c, 3d e a Fase 4 do roadmap (§16, rigor) não iniciadas | §16 do spec da Fase 0 | Ver as seções acima. A Fase 4 executada (coordenadores, executores e `playbook`) é numeração diferente — ver a nota "Atenção ao nome" na seção própria — e está **concluída** |
| Cobertura de EMR não existe | identificada ao fechar a Fase 3a | `RuntimeContext` não tem eixo de infraestrutura para EMR (release label, instance fleets, EMR Serverless, EMR on EKS); área `SF-EMR` inexistente. Spec escrito e revisado; plano da 5a escrito, 5b sem plano — ver seção acima |
| ~~O curinga `"*"` de `runtime_scope` não filtra nada~~ — **fechada** na Fase 5a, commit `fcb8402` | revisão adversarial do spec da Fase 5, 2026-08-01 | `version_scope.py` pula a checagem de presença da chave, então `{glue: "*"}` casa com qualquer runtime. 20 regras agnósticas ficaram etiquetadas como de Glue, e as 5 de infra Glue avaliam em silêncio fora do Glue. Fase 5a corrige |
| ~~`SF-GLUE-002` some de findings e de skipped ao mesmo tempo~~ — **fechada** na Fase 5a, commit `8815f53` | revisão adversarial do spec da Fase 5, 2026-08-01 | `requires_facts: tf.module_analyzed` é sentinela de "algum `.tf` foi lido", não de "há job Glue aqui": sem `aws_glue_job`, ela passa a barreira, avalia, dá falso, e desaparece dos dois lados. Fase 5a corrige |
| Runtime não é inferido dos facts coletados | Fase 5a, medido em 2026-08-01 | `build_runtime_context` monta o contexto só de flags da CLI. Todo `runtime_scope` falha fechado quando a versão não foi declarada, e nenhum extrator alimenta a detecção. A 5a contornou esvaziando os guardas que não guardavam versão nenhuma; os 8 que restaram seguem expostos. Trabalho da 5b, onde é necessário de qualquer forma para detectar EMR |
| `proposed_change` cita AQE e `REBALANCE` sem ramo por versão | Fase 5a, medido em 2026-08-01 | `SF-PY-005`, `SF-PY-009`, `SF-PY-010`, `SF-PQ-001` e `SF-UI-006` têm gatilho agnóstico mas recomendação de Spark 3.2. Com escopo vazio disparam onde o conselho pode não se aplicar — aceito, porque apagar um P0 real por causa de um bullet de remediação é pior |
| `sdist`/`wheel` não são reproduzíveis bit-a-bit entre duas construções da mesma árvore | Fase 3a, commit `2b6311c` | Nenhum `SOURCE_DATE_EPOCH` é fixado, e o zip carrega timestamp interno; duas chamadas de `python -m build` sobre o mesmo commit produzem artefatos com bytes diferentes. `release.yml` contorna isso copiando (`--outdir`) o artefato que o gate já provou, em vez de reconstruir — mas a build em si segue não-determinística, o que importa para quem quiser verificar um wheel publicado por hash contra uma reconstrução própria |
| `unreachable_function_count` não detecta código morto | Fase 1 | A medida só pega componente cíclico isolado. Detectar código morto de verdade exige emitir um nó por função **definida**, com ou sem aresta — mudança no extrator. Documentado em `rules/catalog/callgraph.yaml` |
| Normalização de HTML do `refresh_knowledge` não foi calibrada contra meses de execução real | 2026-07-31 | Se alguma página oficial mudar hash a cada leitura, ela vira alarme permanente. O primeiro PR ruidoso deve ajustar `normalize()`, não silenciar a fonte |

## Como manter este arquivo honesto

Ao fechar uma fase:

1. Atualize a tabela **Números correntes** rodando os comandos da coluna direita.
2. Marque a fase e cole a faixa de commits.
3. Escreva o par spec + plan em `specs/` e `plans/` com a data do merge.
4. Se um número de um spec antigo ficou obsoleto, **não edite o spec** — acrescente
   a linha na seção de desvios dele (§18 no caso da Fase 0) e aponte para cá.
