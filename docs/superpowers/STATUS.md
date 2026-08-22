# SparkForge AWS — estado por fase

**Atualizado em:** 2026-08-21
**Commit de referência:** `46b1187`, fechamento da auditoria de lastro do vNext
sobre a branch `feat/fase6b-sf-cfg` — classificou as 184 alegações que
`a5b9e96` publicou em `docs/vnext/` (48 `PROVADA`, 136 `REMOVIDA`) e removeu o
texto sem lastro dos documentos; ver a seção *Fase vNext* abaixo.
Fechamentos anteriores: expansão agêntica v2 (2026-08-18), vendorização do
ecossistema caveman (2026-08-07) e `feat/preservacao-semantica` (2026-08-05).
**Nenhuma regra executável, extrator ou fact de diagnóstico mudou na expansão
agêntica v2** — os números de detecção abaixo são os mesmos de
`feat/preservacao-semantica`; o que mudou foi o denominador do catálogo.
**Versão do pacote:** `0.5.0` — consistente em `pyproject.toml`, `manifest.json`,
`.claude-plugin/plugin.json` e `sparkforge.__version__`. A concordância entre as
quatro é verificada por
`tests/test_package_importable.py::test_every_manifest_declares_the_same_version`;
nenhum teste fixa o número, porque o que precisa ser garantido é que as quatro
fontes não divirjam, não qual é o valor.

`schema_version` e `catalog_version` continuam em `1`, de propósito: nenhum
contrato de dados mudou e nenhum limiar existente mudou. A Fase 4b acrescentou
duas chaves ao `case.yaml` (`strict_gates` e `gate_overrides`) e **não** subiu o
`schema_version` do case pela mesma razão: as duas são aditivas e todo leitor
tolera a ausência delas — `overridden_gates` devolve conjunto vazio num case
gravado antes da fase, sem migração. Subir os três juntos
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
| Testes | **5633** passando, 5 skipped, medido em `4705049` | `python -m pytest -q` |
| Regras do `AGENT_PROTOCOL.md` | **10** | `AGENT_PROTOCOL.md`, seção *Regras* |
| Regras com eixo de resultado no `validation` | **62 de 116** — as 19 restantes entre as executáveis são segredo, log, capacidade, detecção de runtime e metodologia; as 35 áreas `structural` da expansão agêntica não têm `validation` porque não julgam nada | `tests/test_rules_result_axis.py` |
| Regras com `runtime_scope` não-vazio | **12 de 120** — 11 guardadas por `glue` (3 delas `SF-MIG`), 1 por faixa de Spark (`SF-GRAPH-002`). `SF-MIG-004` NÃO entra: declara `{}` de propósito, porque afirma que o diff mudou `glue_version` e isso não depende de fronteira de versão | `load_catalog()` |
| Extratores de facts | **20** | modulo de `sparkforge/facts/` com `EMITTED_KINDS`; o diretorio tem 22 `.py`, e `runtime_matrix.py` e `secrets.py` nao emitem kind |
| Fact kinds distintos emitidos | **121** | união de `EMITTED_KINDS` |
| Regras de diagnóstico | **120**, sendo **58 `confirmed`** e **62 `structural`** (27 herdadas, 35 novas: uma por área de coordenação da expansão agêntica, sem `requires_facts`, sem `when` e sem `sources`) | `load_catalog()` |
| Regras bloqueadas (`blocked_on`) | **0** | `rules/catalog/*.yaml` |
| Regras com golden que dispara | **55 de 55 executáveis** (mais 26 `structural` herdadas que também disparam). O gate passou a filtrar `status: structural` nesta branch — ver a dívida registrada abaixo | `tests/test_fixtures_kind_coverage.py` |
| Rotas determinísticas | **91** | `rules/catalog/routing.yaml` |
| Tools MCP | **41** | `sparkforge.adapters.tools.TOOLS` |
| Tools alcançáveis a partir de algum coordenador | **41 de 41** | `tests/test_agent_coverage.py` |
| Gates do case | **4**, sendo **3** com produtor declarado | bloco `gates` de `rules/catalog/routing.yaml` |
| Coordenadores | **38** (8 herdados + 30 `sf-*` da expansão agêntica) | `agents/*.md` |
| Executores | **5** | `agents/executors/*.md` |
| Skills | **40** (20 herdadas + 20 da expansão agêntica) | `skills/*/SKILL.md` |
| Skills que declaram despacho | **12 de 20**, sendo **2** com `agent:` (3 têm declarante único; `diagnose-oom` fica fora porque o único é o orquestrador) | `grep -l "subagent: true" .agents/skills/*/SKILL.md` |
| Plataformas que despacham subagente | **3 de 5** (`claude_code`, `devin_cli`, `devin_desktop` com recorte) | mecanismo `subagent` em `parity.yaml` |
| Fixtures golden | **183** em 22 domínios | `fixtures/` |
| Ramos de severidade com golden que os produz | **89 de 89** (15 deles nas 7 regras com `severity_by`; `SF-GRAPH` não tem nenhuma, ver `V-GR-3`) | `tests/test_fixtures_kind_coverage.py::test_every_severity_branch_has_a_golden_that_produces_it` |
| Fontes oficiais vigiadas | **131** (123 móveis, 8 fixas) — 61 citadas por regra, 126 por `knowledge/`, 56 pelas duas | `knowledge/sources.lock.json` |
| Pares de eval | 10 | `evals/fase0.xml` |
| Arquivos de terceiro vendorizados | **127**, em 2 projetos MIT | `python scripts/vendor_caveman.py --check` |
| Plugins de agente ligados por padrão | **2** (`caveman`, `ck`), do marketplace local `sparkforge-caveman` | `.claude/settings.json` |

Regras por área: SF-PY 12, SF-EMR 9, SF-EMRS 6, SF-GLUE 6, SF-UI 6, SF-ATH 5,
SF-ENV 5, SF-FVAL 5, SF-ICE 5, SF-PQ 5, SF-BENCH 4, SF-DQ 4, SF-GRAPH 4,
SF-PLAN 4, SF-CG 1.

Fixtures por domínio: `graph` 25, `emr_serverless` 19, `pyspark` 17, `emr` 14, `dq` 13,
`funcval` 10, `iceberg` 9, `terraform` 8, `plan` 7, `runtime` 7, `s3` 7, `bench` 6,
`fusion` 5, `eventlog` 4, `sql` 4, `athena` 3, `callgraph` 3, `catalog` 3,
`consumers` 3, `infra_code` 2, `tfdiff` 2.

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
| `{athena: "*"}` | 5 | `athena` **nunca é detectado** — default `""`, só a flag `--athena` preenche | escopo vazio  (a premissa mudou na 5b — ver a dívida fechada de `athena.workgroup` abaixo; reabrir o guarda é decisão de catálogo, não feita aqui) |
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

### Fase 5b — EMR on EC2 — **CONCLUÍDA** em 2026-08-01

Branch `feat/fase5b-emr`. Plano:
[`plans/2026-08-01-sparkforge-fase5b-emr.md`](plans/2026-08-01-sparkforge-fase5b-emr.md).
Fecha os critérios 3, 4, 5, 6, 7, 8, 9, 12 e 14 do
[spec da Fase 5](specs/2026-08-01-sparkforge-fase5-emr-design.md).

**Plataforma virou coisa rastreada.** O critério 12 exigia sinal quando Glue e
EMR são detectados juntos **mesmo com as versões derivadas coincidindo**. Isso
não era alcançável por comparação de versão sob nenhum ajuste: `SF-ENV-001`
dispara sobre `distinct_versions > 1`, e se Glue 4.0 e um release EMR derivam o
mesmo Spark, não há divergência de versão alguma. Confirmado no código —
`glue_observations` era separado de `observations`, e `_build_facts` iterava só
o segundo, então plataforma nunca virava `env.runtime_signal`. Nasceu
`env.platform`, com `SF-ENV-005` contando identidades em vez de versões.

**`EMR_MATRIX`, e quatro coisas que a `GLUE_MATRIX` não tem.** A primeira era
uma armadilha: `3.5.6-amzn-2` não é o `3.5.6` do Apache, e a comparação de
versão quebrava em duas releases da série `-amzn-N.M` — `6.11.1`, `6.10.1`,
`6.9.1` e `6.8.1` sofriam skip silencioso de toda regra com range exato. Python
é conjunto, não valor, e a matriz guarda a lista mais o default documentado do
PySpark. Iceberg não existe antes de 6.5.0, e a chave é **omitida** em vez de
receber `"0.0.0"` — as duas grafias mentem diferente. E observação direta vence
a matriz: `Cluster.Applications[].Version` vem populado no dump.

O guard de drift é **assimétrico**, porque as duas páginas canônicas têm perfis
opostos: a série 6.x não recebe minors novos, então mudança ali é o evento que
a watchlist existe para pegar; a 7.x ganha uma coluna a cada 90 dias por
compromisso da AWS, e um guard por hash da página alarmaria quatro vezes por ano
por motivo que não é drift. Guard ruidoso é guard ignorado.

**`RuntimeContext.emr` guarda a release numérica**, não o label. `_parse` lê
`emr` de `emr-7.5.0` como zero, então `{emr: ">=7.0"}` nunca casaria — regra
pulada, cobertura apagada em silêncio, o modo de falha que as Fases 5a e 5a.2
fecharam. O curinga `"*"` não revelava, porque só checa presença. `glue` já
fazia certo: guarda `5.0`, nunca `Glue 5.0`. O label observado vive em
`env.platform.attrs`.

**O extrator, e a lista de dumps do spec estava errada.** A pesquisa de fontes
derrubou três premissas: `aws emr list-configurations` **não existe** — as
classificações vêm de `Cluster.Configurations` e dos grupos, e a distinção
importa porque grupo sobrepõe cluster; faltavam `get-managed-scaling-policy` e
`get-auto-termination-policy`, sem os quais três regras não têm gatilho; e
`Applications[].Version` vem populado.

Um kind é de **qualidade da evidência**: `emr.configuration.unapplied` compara
`Configurations` com `LastSuccessfullyAppliedConfigurations` e diz que o cluster
não está rodando o que o dump parece dizer. `SF-EMR-003` o usa como guarda — sem
ele, afirmaria sobre configuração que não vigora.

**Nove regras `SF-EMR`.** Todas com `runtime_scope: {}`, e a justificativa está
no cabeçalho do YAML: a série vem de `measures.release_major` do próprio
`emr.cluster`, e um `{emr: ...}` em cima disso é segundo guarda sobre o mesmo
dado, que falharia fechado num `judge` sem `--emr`.

Três dos quatro candidatos do spec **não sobreviveram** à leitura das fontes, e
os vetos estão registrados no cabeçalho do catálogo para ninguém reinventá-los:

- **Bootstrap action que falha em silêncio** é duplamente morto:
  `ListBootstrapActions` não devolve status nem exit code, e bootstrap que falha
  **não** falha em silêncio — o EMR termina a instância. O que se salvou é
  diferente: `SF-EMR-007`, post-mortem sobre `BOOTSTRAP_FAILURE`.
- **Ausência de EBS** — EBS nunca está ausente; o EMR aloca gp2/gp3 por default
  desde 5.22.0. A leitura ingênua daria falso positivo em quase todo cluster.
- **Spot no master como absoluto** acusaria a recomendação oficial da AWS, que
  prevê primary Spot em dois dos quatro cenários da própria tabela. Sobreviveu
  como correlação: `SF-EMR-004`, primary Spot **com core On-Demand**.
- E `SF-EMR-005` teve o argumento corrigido pela fonte: o commit protocol
  otimizado do EMRFS cobre overwrite dinâmico desde 5.30.0/6.2.0, então o
  argumento de **performance** está morto em toda release analisável. A regra
  ficou sobre a **semântica** — alcance cluster-wide mudando o que
  `mode("overwrite")` apaga.

**`SF-EMR-008` exigiu um padrão novo.** A melhor regra do conjunto — o
ApplicationMaster elegível a nó Spot, em que o AM **é** o driver e a aplicação
inteira falha — não podia ser escrita: o gatilho é a ausência de uma
**combinação** de propriedades, e `engine._absent_satisfied` só compara `kind`.
Em vez de alargar o motor, que é superfície de execução do catálogo, o extrator
decide e emite `emr.yarn.am_node_label` só quando a proteção está presente e
coerente; a regra usa `absent:` sobre ele. Proteção pela metade não emite, e o
que não dá para ler vira `unresolved` — contado, não presumido. O padrão está
escrito no cabeçalho do catálogo: se a resposta depende de mais de uma
propriedade, o extrator decide e emite.

**`SF-EMR-009` fechou a única capacidade sem consumidor que a fase deixou.**
`measures.idle_timeout_seconds` chegava ao `emr.cluster` vindo de
`get-auto-termination-policy` e nenhuma regra o lia — mecanismo sem garantia
declarada. A forma óbvia da regra, *acusar a AUSÊNCIA de política*, **não pode
existir** no motor de hoje: `_where_matches` reprova caminho ausente e
`_expr_matches` engole o `ExprError` de caminho ausente, então ausência de
measure falha fechada nas duas superfícies do `when`. O que sobrou é a metade que
lê o valor — política que existe com janela larga demais para alcançar qualquer
intervalo ocioso real. O limiar de 86400 s é `field-heuristic` declarada (a
documentação dá o default de 3600 s, o mínimo de 60 s e o máximo de 604800 s, e
não dá nenhum ponto de "larga demais"); o ramo P1 em 604800 s, esse, é o teto da
API. O gate de aplicação interativa que a pesquisa propôs **não** virou gatilho:
cluster com JupyterHub, Zeppelin ou Hue é acusado como qualquer outro, e o
trade-off vive dentro do achado em vez de virar um `skipped` que ninguém lê — o
risco documentado para notebook tem recorte 5.30.0–5.33.0 / 6.1.0–6.3.0, abaixo
do piso 6.4.0 do `EMR_MATRIX`.

**A prova do objetivo**, em `tests/test_emr_investigation_end_to_end.py`: uma
investigação real — cluster mais código PySpark, sem flag de runtime nenhuma —
produz 5 achados, 3 de infraestrutura EMR e 2 de código, e as 6 regras `SF-GLUE`
aparecem em `skipped` com `reason: runtime_scope`. Antes da fase, elas
avaliavam, nunca disparavam, e não apareciam de lado nenhum.

**Números no fechamento da branch.** 58 regras em 10 áreas, 9 delas `SF-EMR`. 14
extratores, 93 kinds, 32 tools, 7 coordenadores, 91 fixtures. 2852 testes
passando. Os commits que vieram depois do commit de documentação da fase —
`--emr` nos verbos, `PYSPARK_PYTHON`, reprodutibilidade de build, o nó por
função definida do call graph, `SF-EMR-009` e a leitura de `athena` — são desta
mesma fase e estão contados aqui.

**O que ficou de fora, por decisão registrada no spec:** EMR Serverless e EMR on
EKS. Esta fase é EMR on EC2. **Serverless entrou na Fase 5d** (2026-08-05, área
`SF-EMRS`, seção própria abaixo); EKS continua sem cobertura e sem posição na
*Ordem*.

### Fase 5c — SF-DQ, validação de dados como coisa lida — **CONCLUÍDA** em 2026-08-03

Branch `feat/fase5c-dq`. Spec:
[`specs/2026-08-03-sparkforge-fase5c-dq-design.md`](specs/2026-08-03-sparkforge-fase5c-dq-design.md) ·
Plano: [`plans/2026-08-03-sparkforge-fase5c-dq.md`](plans/2026-08-03-sparkforge-fase5c-dq.md) ·
Pesquisa de fontes: [`knowledge/dq/validation-frameworks.md`](../../knowledge/dq/validation-frameworks.md).

**O defeito de partida era folha em branco, e foi medido assim.**
`grep -ril "deequ\|great.expectations\|dbt"` sobre o repositório inteiro devolvia
**um único arquivo**: a linha deste `STATUS.md` que listava `SF-DQ` como
capacidade futura. Um job PySpark que valida dado tinha três destinos dentro do
motor, e nenhum era "foi analisado": a validação era vista como action genérica
por `SF-PY`, que nunca diz que aquela action **é** uma validação; a suíte que
roda e não tem consumidor não tinha fact que a registrasse; e a validação que
recomputa o lineage era custo real e invisível ao catálogo.

**O que entrou.** `sparkforge/facts/data_quality.py` — extrator próprio, não
crescimento de `pyspark_ast` (D-2) — com quatro kinds (`dq.check`,
`dq.enforcement`, `dq.unresolved`, `dq.module_analyzed`), reconhecendo três
formas **pela forma do código** e nunca por lista de nomes: o check artesanal
(`df.filter(...).count()` seguido de aborto), a `VerificationSuite` do PyDeequ e
a validação do Great Expectations pela chave literal `"dataframe"` de
`batch_parameters`. Quatro regras em `rules/catalog/data-quality.yaml`, todas com
`runtime_scope: {}` e a justificativa no cabeçalho. Oito fixtures em
`fixtures/dq/` com golden bidirecional. O verbo `analyze data-quality` na CLI, a
tool `sparkforge_analyze_data_quality` no MCP, e o coordenador
`data-quality-reviewer` com a skill `review-data-validation` e a rota `AGENT-008`.

**As correlações vivem no extrator, e isso não é conveniência.** Medido em
`sparkforge/rules/engine.py` antes de escrever o plano: `_condition_candidates`
avalia um fact por vez e `_absent_satisfied` compara só `kind` — o motor **não**
correlaciona dois facts. "Linha do check posterior à linha do write" não é
expressável como condição. É o mesmo limite que `SF-EMR-008` encontrou na 5b, e a
resposta é a mesma regra escrita no cabeçalho do catálogo de EMR: se a resposta
depende de mais de uma propriedade, o extrator decide e emite. Daí saem
`attrs.position_vs_write`, `attrs.target_persisted`, `attrs.action_after_check`,
`attrs.shares_scan` e `measures.checks_on_target`, e a alternativa — alargar
`_absent_satisfied` — foi recusada porque o motor é superfície de execução das 62
regras, não desta área.

**O que a pesquisa de fontes vetou.** A Task 0 rodou antes de qualquer código,
como a 5b fez, e derrubou **quatro** premissas — três que o spec já marcava como
suspeitas na §4.3, e uma que ninguém tinha marcado:

- **`attrs.single_pass` afirmava o que a fonte não sustenta** — esta é a que
  ninguém suspeitava, e estava escrita no spec como fato. O artigo original do
  Deequ (Schelter et al., PVLDB 2018, §4.1 e §5.1) descreve *scan sharing por
  agrupamento*: `isUnique`, `hasUniqueness` e entropia exigem re-particionamento e
  **pagam passada própria**. Uma suíte com N checks custa uma passada por
  agrupamento distinto, não uma — e o exemplo canônico do README do PyDeequ tem
  `isUnique("a")`. O atributo virou **`attrs.shares_scan`**, que afirma só o que a
  fonte autoriza. `SF-DQ-004` sobreviveu porque o contraste de que ela precisa
  sobrevive: N passadas contra ≤ N, nunca "uma".
- **`SparkDFDataset` está morto, e a detecção de GE mudou de forma** — o módulo
  some na 1.0.0 (2024-08-22). Detectar por métodos `expect_*` ficou **vetado**: o
  prefixo sobrevive via `Validator.__getattr__` e o AST não sabe se a variável é
  um `Validator`, então casar por prefixo produziria falso positivo sobre qualquer
  objeto. Sobrou o que é estreito e honesto: a chave literal de
  `batch_parameters`. Consequência registrada — um `dq.check` de framework
  `great_expectations` **não recebe** a chave `shares_scan`, porque quantas
  expectativas rodam vive no store do contexto, fora do `.py`. Ausência de chave é
  a forma de dizer "não sei" sem que ninguém confunda com `false`.
- **`assert` conta como consequência, com ressalva escrita dentro do achado** —
  `-O` apaga o `assert`, mas nenhuma fonte da AWS mostra Glue ou EMR rodando o
  driver assim, e no Glue o caminho documentado (`--customer-driver-env-vars`)
  rejeita chave sem o prefixo `CUSTOMER_`. O outro ramo previsto pelo plano —
  virar `dq.unresolved` — não foi tomado.
- **Recomendar suíte exige guarda de versão** — PyDeequ não alcança Glue 3.0 nem
  nenhuma release EMR 6.x (piso de Python 3.9), e o Spark 3.4 não está no mapa de
  `pydeequ/configs.py`; GX 1.x exige Python ≥ 3.10. "Use uma suíte" seria conselho
  impossível de seguir em metade das releases que o repo cobre, então a
  `proposed_change` aponta para o alcance medido em vez de recomendar às cegas.

Uma medida **não entrou** pela mesma pesquisa: `measures.declared_checks` contaria
chamadas `addCheck`, e a forma oficial encadeia seis restrições dentro de **um**
`addCheck` — medida que não sustenta o próprio nome é a família de defeito que a
5b corrigiu em `unreachable_function_count`.

**Um quinto desvio veio da revisão, não da pesquisa.** Indexar write, persist e
action por **nome nu** datava o check de uma função contra o write de outra: duas
funções com um parâmetro `vendas` cada produziam `after_write` sobre um DataFrame
que nunca foi escrito. O índice passou a ser por escopo — corpo do módulo e cada
`FunctionDef` separados — e `measures.checks_on_target` foi junto, contrariando a
letra da §4.4 do spec, que dizia "no módulo". O preço está registrado: função que
lê um DataFrame global perde a correlação e sai `no_write_in_module`. Erra para
menos, que é o lado certo.

**`SF-DQ-004` passou o gate que podia tê-la eliminado.** O spec a declarava a mais
frágil das quatro e mandava medi-la antes de escrevê-la. A taxa de alvo não
resolvido no corpus de fixtures é **1 em 9 (~11%)**, e o número ficou como
comentário acima da regra no catálogo — não só na mensagem de commit.

**A prova do objetivo**, em `tests/test_dq_investigation_end_to_end.py`: uma
investigação sem flag de runtime nenhuma sobre um job cuja linha de validação é
lida pelos dois extratores produz `SF-PY-003` e `SF-DQ-001` **sobre a mesma linha,
dizendo coisas diferentes** — o primeiro sobre o que a cadeia custa, o segundo
sobre o dado ruim já estar publicado quando o alarme toca. É a verificação de D-3,
e ela é feita pelas duas metades que podem desfazer a decisão: nenhuma regra de
uma área lê o namespace de fact da outra, e o julgamento de cada área é **idêntico
com e sem** os facts da vizinha. Supressão cruzada só se implementa olhando o fact
alheio, então as duas medidas juntas reprovam tanto quem duplicar quanto quem
calar. As seis `SF-GLUE` continuam aparecendo em `skipped` com
`reason: runtime_scope`, como a prova da 5b fixou.

**Critério 9 conferido:** `git diff --stat main -- fixtures/pyspark/` sai vazio.
Os 17 goldens de `pyspark/` são byte a byte iguais, que é a prova operacional de
que nada desta fase tocou `pyspark_ast`.

**Números no fechamento da branch.** 62 regras em 11 áreas, 4 delas `SF-DQ`. 15
extratores, 97 kinds, 33 tools, 8 coordenadores, 100 fixtures em 17 domínios, 24
rotas. 3104 testes passando, 5 skipped.

**O que ficou de fora, por decisão registrada no spec:** resultado de execução
(`VerificationResult`, validation result do GE, `run_results.json` do dbt), GE
declarativo, dbt e schema declarado. Ver as duas primeiras nas dívidas abertas.

Faixa de commits: `032b44c` … `4dd6286`, mais o commit de documentação que fecha
a fase.

### Fase 5c.2 — um passo para dentro da chamada — **CONCLUÍDA** em 2026-08-03

Branch `feat/fase5c2-helper`. Plano:
[`plans/2026-08-03-sparkforge-fase5c2-helper.md`](plans/2026-08-03-sparkforge-fase5c2-helper.md).
Sem spec próprio: a fase fecha **uma** dívida nomeada da 5c e não acrescenta área,
kind nem regra.

**O que mudou, e é uma coisa só.** Quando o alvo de um `dq.check` chega por
parâmetro e não há `cache`/`persist`/`unpersist` sobre ele dentro da própria
função, `_target_persisted` deixa de parar na omissão e dá **um passo para fora**:
se a função tem **exatamente um** call site no mesmo módulo, a chamada é por nome
e o argumento é uma variável, a evidência daquele call site é herdada. A herança
resolve nos **dois sentidos** — `true` quando o chamador persistiu, `false` quando
não. Herdar só a favor teria deixado `SF-DQ-003` morta para todo helper com os
goldens verdes, e é por isso que a fixture negativa entrou junto com a positiva.

**O preço, que continua existindo e mudou de tamanho.** A regra segue calada para
o helper cujo chamador vive **noutro arquivo** — o extrator lê um módulo por vez,
e essa fronteira não se moveu —, para o helper com **mais de um** chamador (um
pode persistir e o outro não, e escolher seria inventar), para chamada por
atributo, e para nome que o próprio chamador não liga nem persiste. Cada limite
tem controle próprio em `tests/test_facts_data_quality.py`.

**O princípio que a revisão da fase produziu, e que vale para a próxima:
herança estende evidência, nunca acusação.** Ele saiu de um caso medido (D-5c2-3):
um DataFrame cacheado no corpo do módulo e passado de dentro de uma função fazia
o índice do chamador devolver `false` por nunca ter visto o objeto, e a herança
transformaria isso numa acusação sobre código correto. Dentro do próprio escopo do
check esse `false` é comportamento aceito desde a 5c; propagá-lo por herança seria
estender a acusação junto com a evidência.

**A dívida gêmea NÃO fechou, e a decisão foi medida antes de ser tomada.** Ver a
linha própria na tabela de dívidas abertas.

**Números medidos no fechamento.** 3141 testes passando, 5 skipped (eram 3104 ao
fechar a 5c). 145 testes em `tests/test_facts_data_quality.py` (eram 135). 101
fixtures em 17 domínios, 10 delas em `fixtures/dq/`. 62 regras, **nenhuma nova** —
esta fase não acrescentou capacidade ao catálogo, ela tirou uma cegueira de uma
regra que já existia. `git diff --stat main -- fixtures/pyspark/` sai vazio.

### Fase 4a — benchmark antes/depois — **CONCLUÍDA** em 2026-08-03

Branch `feat/fase4a-benchmark`. Spec:
[`specs/2026-08-03-sparkforge-fase4a-benchmark-design.md`](specs/2026-08-03-sparkforge-fase4a-benchmark-design.md) ·
Plano: [`plans/2026-08-03-sparkforge-fase4a-benchmark.md`](plans/2026-08-03-sparkforge-fase4a-benchmark.md).

**O defeito de partida: um gate sem produtor.** Desde a Fase 0,
`validate_finding` rejeita `expected_effect` que quantifique ganho (`"40% mais
rápido"`, `"3x"`, `"2 vezes"`) sem `benchmark_ref`. O campo, porém, era **string
livre** — nada no repositório produzia a medição que ele deveria citar, então
satisfazer o gate era digitar qualquer coisa. Um gate que se contorna digitando
não é gate; é cerimônia. Esta fase deu produtor a ele.

**O que entrou.** `sparkforge/facts/benchmark.py` — função **pura** sobre `Fact`,
no padrão de `call_graph.py`: nunca lê artefato bruto, nunca executa Spark, nunca
chama AWS. Recebe os dois conjuntos de facts que `analyze event-log` já produziu,
um por execução, e emite cinco kinds: `bench.run_delta` (os totais dos dois lados
e o percentual entre eles), `bench.stage_delta` (o mesmo por stage casado),
`bench.unmatched` (cada stage sem par, com o motivo), `bench.analyzed` (a
sentinela com `matched_stage_count`/`unmatched_stage_count`) e
`bench.unresolved` (o que ele **não** conseguiu comparar, nomeando a medida e o
lado). O verbo de topo `benchmark` nas cinco superfícies, a tool MCP
`sparkforge_benchmark`, seis fixtures em `fixtures/bench/` — cada uma com **dois**
event logs —, e quatro regras em `rules/catalog/benchmark.yaml`.

**A comparação não vive no `when`, e o motivo é o mesmo de sempre.**
`rules/engine.py::_condition_candidates` avalia um fact por vez; não existe
condição que leia o fact de um run e o do outro ao mesmo tempo. Quem enxerga os
dois lados **decide e emite um fact que carrega a decisão**, e o catálogo lê
atributo de um fact só — a mesma resposta que a Fase 1 deu com `facts/fusion.py`,
a 5b com `emr.yarn.am_node_label` e a 5c com `attrs.position_vs_write`.

**A medida se chama `total_task_ms` porque é o que ela é.** Não existe fact de
duração de relógio no event log lido: `facts/event_log.py` emite duração por
stage e nada de wall-clock. O total honesto é a soma de `mean_ms * task_count`
sobre os stages — **trabalho**, não tempo decorrido. Um job pode terminar antes
no relógio somando mais tempo de task, ao paralelizar melhor. Chamá-la de
`duration_ms` teria sido o defeito que a 5b corrigiu em
`unreachable_function_count` — nome que promete mais do que entrega —, e aqui o
preço seria maior, porque é a regra que lê a medida que manda alguém desfazer
trabalho. `SF-BENCH-002` acusa "mais trabalho", nunca "mais lento", e a
`explanation` manda confirmar no relógio antes de reverter.

**Chave `*_delta_pct` ausente significa "não sei", nunca zero.** É omitida quando
o lado antes é zero, quando a medida falta ou está incompleta de um lado, e
quando um símbolo casado a perdeu num lado só. Isso mudou a forma de
`SF-BENCH-003`, que compara os **totais** e não o percentual: spill que nasce do
zero é a forma mais severa do defeito e seria a única invisível.

**A quebra de contrato do `benchmark_ref`, e ela atingiu um caso.** O campo
deixou de ser texto livre: passa a citar o `fact_id` de um `bench.run_delta`,
forma `^f_[0-9a-f]{6}$`. A validação tem **duas camadas**, porque
`validate_finding(payload)` não vê fact nenhum na assinatura padrão — a **forma**
vale sempre; a **pertinência** (o `fact_id` existe no conjunto) só quando quem
chama passa `fact_ids`, e por isso `validate` ganhou `--facts` e a tool MCP
ganhou `facts_path`. A quebra foi deliberada e o custo foi medido antes: das 83
ocorrências de `benchmark_ref` em fixtures, **todas** eram `""`, o catálogo não
declara o campo, e havia **um único** valor em texto livre — num teste, que agora
prova a rejeição em vez de a contornar.

**Sem coordenador novo (D-6 do spec).** `SF-BENCH` entrou em `rule_areas` de
`spark-performance-architect`, que já declarava a skill `benchmark-pyspark-job`:
a pergunta — *o job ficou mais rápido, e por quê* — é a que esse coordenador já
respondia. Ao contrário da 5c, onde `SF-DQ` ganhou coordenador próprio porque a
pergunta era outra. Nenhuma rota nova foi exigida: `AGENT-001` já aponta para
esse coordenador, e `tests/test_router_agents.py` seguiu verde sem tocar em
`routing.yaml`.

**Números medidos no fechamento.** 3295 testes passando, 5 skipped (eram 3141 ao
fechar a 5c.2). 66 regras em 12 áreas, 4 delas novas (`SF-BENCH`). 16 extratores
emitindo 102 kinds (eram 15 e 97). 34 tools MCP, **34 de 34** alcançáveis a partir
de algum coordenador. 107 fixtures em 18 domínios, 6 delas em `fixtures/bench/`.
24 rotas, inalteradas.

**O que esta fase NÃO fechou.** A Fase 4 do roadmap (§16) tem quatro itens; este
era um. Ficam de fora: validação funcional automatizada (contagem, schema,
chaves, agregados), gates fail-closed opcionais e assinatura de relatório. Ver a
linha própria abaixo.

Faixa de commits: `a78f3cd` … o commit de documentação que fecha a fase.

**Pontas fechadas depois do merge (`fix/pontas-4a`).** A revisão final da fase
aprovou os nove critérios do spec e mediu nove pendências; todas foram fechadas,
e três valem registro por mudarem comportamento ou contrato:

- **Bug real na forma do `benchmark_ref`.** `^f_[0-9a-f]{6}$` aceitava
  `"f_78d412\n"` — `$` casa **antes** do `\n` final. A âncora passou a `\Z`, e o
  caso importa duas vezes: um ref lido de arquivo ou colado carrega o terminador
  de linha, e a camada de pertinência compara a string **crua** contra o conjunto
  de `fact_id` — a forma que passava com `\n` era a mesma que depois não casava
  com fact nenhum, trocando rejeição clara por confusa.
- **O título da `SF-BENCH-003` passou a qualificar a medida:** "Ganho de tempo
  **de task somado** acompanhado de mais spill ou mais GC". O título é a string
  que renderiza em todo achado e viaja sozinho; "ganho de tempo" sem qualificação
  seria lido como relógio, que é o erro que o cabeçalho do catálogo e a
  `explanation` da 002 existem para impedir.
- **A justificativa da forma da 003 ganhou guarda em nível de `judge`.** Três
  documentos afirmam que spill que nasce do zero é o caso que obriga a regra a
  comparar totais em vez de `_delta_pct`; nenhuma fixture tinha essa forma e o
  arquivo do comparador nunca chamava `judge`, então uma 003 reescrita sobre o
  percentual passava verde no corpus inteiro. Fechada com facts construídos
  (`TestSFBench003SobreOSpillQueNasce`), verificada por mutação.

O spec da fase ganhou seção de desvios (§9) em vez de ser reescrito: três linhas
dele chamam a medida de *duração*, e uma lista *pico de memória* entre as medidas
do `bench.run_delta`, que `_RUN_MEASURES` não tem.

### Fase 4b — gates fail-closed e assinatura de correspondência — **CONCLUÍDA** em 2026-08-04

Branch `feat/fase4b-gates`. Spec:
[`specs/2026-08-04-sparkforge-fase4b-gates-assinatura-design.md`](specs/2026-08-04-sparkforge-fase4b-gates-assinatura-design.md) ·
Plano: [`plans/2026-08-04-sparkforge-fase4b-gates-assinatura.md`](plans/2026-08-04-sparkforge-fase4b-gates-assinatura.md).

**O defeito de partida: a razão da Fase 0 deixou de valer para metade dos gates.**
A §5.5 do spec da Fase 0 decidiu conscientemente que gate é advisory, com um
argumento que estava certo — *"gate rígido vira impasse quando o dado simplesmente
não existe"*. O que mudou desde então é que passou a existir gate **com** produtor:
a Fase 4a deu `bench.run_delta` a `baseline_captured`, e a Fase 2 do roadmap deu
`callgraph.reachable_spark_work` a `flows_mapped`. Para esses dois, "o dado não
existe" tem saída concreta — rodar um comando —, e manter o advisory era proteger
contra um impasse que não é mais possível. Daí o critério da fase, que é
verificável e não preferência: **um gate só pode ser fail-closed se tiver produtor
declarado**. Os outros dois seguem advisory pelo argumento original, intacto.

**O rigor é do case, não da invocação.** `sparkforge case open --strict-gates`
grava a escolha no `case.yaml`, e ela vale pela investigação inteira — outra
sessão, outra máquina, outra ferramenta. Uma flag por invocação desligaria o gate
em silêncio na primeira vez que alguém esquecesse de passá-la, que é exatamente a
família de defeito que a fase existe para não cometer. Sem a flag, o comportamento
é bit a bit o de antes: `set_phase` sequer lê o catálogo.

**O booleano manual não destrava, e isso é o desvio D-4b-2.** `set_phase` **não**
consulta `case["gates"]`: se consultasse, `case update --gate X --gate-value true`
seria um override sem motivo e sem registro, e o gate voltaria a se satisfazer
digitando — o defeito que a 4a mediu no `benchmark_ref` de texto livre. O que
destrava é o fact produtor estar presente nos facts passados em `case update
--facts`, ou um override declarado. Por isso `case update` ganhou `--facts`: sem
ele, rigor não teria chave (D-4b-5).

**Quem produz a chave de cada gate é dado.** O bloco `gates` do `routing.yaml`
declara `satisfied_by`, `guards_phases` e o comando exato de `produced_by`, e os
**quatro** gates aparecem lá — inclusive os advisory, com `advisory_reason`, porque
gate ausente do bloco seria ambíguo entre *esqueceram* e *é advisory de propósito*.
Duas escolhas de `satisfied_by` foram medidas contra a alternativa óbvia:
`callgraph.summary` foi recusado porque é emitido incondicionalmente e destravaria
`flows_mapped` rodando `analyze call-graph` sobre um facts vazio; e
`baseline_captured` não guarda a fase `experiment`, porque `bench.run_delta` exige
o lado `--after`, que só existe depois de rodar o job mudado — guardar ali seria
gate insatisfazível no momento em que morde.

**Passar por cima custa uma frase, e a frase fica.** `case update --override-gate
<gate> --reason "<motivo>"`. Sem `--reason` é recusado, porque override anônimo não
se distingue de gate esquecido. Ele entra numa **lista**, nunca num mapa `gate →
motivo`: dois overrides do mesmo gate em momentos diferentes são dois fatos, e um
mapa apagaria o primeiro ao gravar o segundo. Aparece no `resume`. A mensagem de
bloqueio nomeia a fase pedida, cada gate que faltou, o kind ausente, o comando de
`produced_by` por extenso e a linha de override — a 4a mediu que mensagem
inacionável passa no CI.

**A assinatura prova correspondência, e o bloco diz isso em voz alta (D-6 do
spec).** `sparkforge/findings/signature.py`, mais `report sign` e `report verify`
nos três adaptadores. O hash cobre quatro coisas: os `fact_ids` citados, os
`rule_ids` que dispararam, `catalog_version`/`schema_version`, e o **corpo**
normalizado do relatório. Sem o corpo, alguém reescreveria o texto inteiro mantendo
a assinatura válida (D-7). Ela **não** prova autoria: não há chave nem segredo, e
qualquer um com os mesmos findings produz a mesma assinatura — HMAC ou GPG foi
recusado no desenho porque exigiria distribuir e guardar segredo, superfície que
o projeto hoje não tem.

Quatro decisões da assinatura foram medidas contra o esboço do plano, e as quatro
mudaram: a serialização é a canônica que já existe (`models._canonical`, base do
`Fact.id`) em vez de uma segunda inventada aqui (D-4b-9); o digest são **64 hex**
de sha256 e não 16, porque assinatura é integridade e o projeto já separa os dois
usos de digest (D-4b-10); a normalização absorve reformatação mas **não** absorve
indentação, que em Markdown muda o que o texto significa (D-4b-11); e a flag é
`--findings`, não `--facts`, porque `rule_id`, `catalog_version` e `schema_version`
não existem no arquivo de facts (D-4b-12). Dois inputs são recusados em vez de
assinados com um default silencioso: findings vazio (a assinatura cobriria só o
corpo e seria lida como prova de derivação) e `catalog_version` divergente entre
achados (escolher um faria a assinatura afirmar um catálogo que não foi o único
usado) — D-4b-16.

**`verify` diz qual das três partes divergiu, e não pode fazer isso com autoridade
total (D-4b-14).** Recomputar as três em separado a partir de um hash único é
impossível; a isolação vem de o **bloco declarar** o que foi assinado, e o bloco
mora fora do hash por construção — logo é editável. Por isso o veredito `valid`
nunca sai do bloco, sai das três checagens juntas, e a atribuição de `body` enuncia
as duas leituras possíveis ("o corpo foi editado, ou o próprio bloco foi") em vez
de escolher uma que ela não pode provar. Texto acrescentado **depois** do bloco é
recusado, não ignorado (D-4b-15): ignorá-lo deixaria aberta a porta que a
assinatura existe para fechar.

**O limite dos gates é decisão registrada, escrita em três lugares.** A checagem é
por **presença de kind**, nunca por conteúdo de fact: ela prova que a análise rodou
e produziu o artefato que destrava, e **não** que ela cobriu todo o
`scope.entrypoints` nem que o benchmark é do job certo. Passar facts inteiros
puxaria o índice de facts para dentro do `store` e faria o gate precisar saber o
que é "o job certo", que é julgamento. O recorte vai declarado no bloco do
`routing.yaml`, na docstring de `set_phase` e na própria mensagem de bloqueio — a
mesma disciplina de `dq.unresolved`.

**A revisão final aprovou 8 dos 10 critérios, e as sete pendências dela fecharam
numa Task 7.** Elas estão medidas uma a uma nos desvios D-4b-21 a D-4b-27 do
plano; o que vale registrar aqui é o padrão, porque quatro das sete são a mesma
família: **a garantia existia e o caminho lateral também.**

- **O rigor falhava ABERTO com catálogo sem o bloco `gates`** (D-4b-21). Sem o
  bloco, `load_gate_contract` devolvia `{}` e a lista de bloqueio saía vazia: um
  case com `strict_gates: true` ia de `intake` a `report` sem evidência nenhuma.
  O único guarda rodava sobre o catálogo do **repositório**, nunca sobre o que o
  runtime carrega — e `SPARKFORGE_CATALOG` move o catálogo. Contrato ausente,
  vazio ou parcial passou a ser recusa, e as três respostas são a mesma:
  a única diferença é quantos gates faltam.
- **O critério 1 pedia um grep que nenhuma suíte tinha** (D-4b-22). O invariante
  era verdadeiro e nada o defendia.
- **`case open` apagava rigor e overrides sem aviso** (D-4b-25). Uma invocação
  sem `--strict-gates` reescrevia um case estrito com `strict_gates: false`,
  `gate_overrides: []` e `phase: intake`, e a transição bloqueada passava. Abrir
  por cima virou recusa; reabrir do zero ficou, com nome (`--reopen`), e **herda**
  o rigor: ele sobe com a flag e nunca desce por omissão dela.
- **O exemplo principal do README dava rc=2** (D-4b-27) — o D-4b-3 reencenado na
  documentação, porque `report` é guardada pelos **dois** gates com produtor. O
  exemplo corrigido foi executado literalmente antes de publicado.

As outras três são de natureza diferente. A **versão da assinatura passou a ser
declarada no bloco** (D-4b-24): ela já entrava no hash — e era isso que garantia
que duas normalizações nunca produzissem a mesma assinatura —, mas sem a
declaração o `verify` não sabia dizer *por quê* não fechou, e um relatório de
versão anterior saía idêntico a um corpo adulterado. Agora sai `version_mismatch`,
com o corpo declarado **não avaliável** em vez de acusado. A **quarta cláusula do
critério 6** — override aparece no relatório — fechou pelo **corpo assinado**, e
não pelo bloco, com o custo da alternativa medido no D-4b-23. E a **dívida de
"presença de kind" foi remedida e ampliada**: ela dizia que um benchmark de outro
job destrava, e o que destrava são duas linhas de JSON escritas à mão com
`provenance` vazia.

**Números medidos no fechamento.** 3475 testes passando, 5 skipped ao fechar a
revisão final (eram 3443 ao fechar a fase, e 3295 ao fechar a 4a). 36 tools MCP, **36 de 36** alcançáveis a partir de algum coordenador
(eram 34). Nada mais mudou de tamanho: 66 regras em 12 áreas, 16 extratores, 102
kinds, 107 fixtures em 18 domínios, 24 rotas, 8 coordenadores, 5 executores, 20
skills. Esta fase não acrescentou capacidade de análise — ela cobrou rigor sobre a
que já existia.

**O que NÃO entrou, por decisão registrada na §2 do spec:** a validação funcional
automatizada (contagem, schema, chaves, agregados), que é a **Fase 4c**. Ela é de
natureza diferente das duas desta fase — precisa de um artefato que não existe, o
resultado de consultas que alguém roda —, e é por não ter esse artefato que
`functional_validation_defined` continua advisory. Também ficaram fora, com razão
escrita: assinatura de autoria e gate sobre emissão de achado.

Faixa de commits: `0b500d6` … `20591bd`, mais o commit de documentação que fecha a
fase (`c18ac3c`). O fechamento das pendências da revisão final vai de `109af64`
até o commit de documentação desta Task 7.

### Perfis de subagente do Devin — **CONCLUÍDA** em 2026-08-04

Branch `feat/devin-subagentes`. Spec:
[`specs/2026-08-04-sparkforge-devin-subagentes-design.md`](specs/2026-08-04-sparkforge-devin-subagentes-design.md) ·
Plano: [`plans/2026-08-04-sparkforge-devin-subagentes.md`](plans/2026-08-04-sparkforge-devin-subagentes.md) ·
Pesquisa de fontes:
[`../../knowledge/devin/agents-and-subagents.md`](../../knowledge/devin/agents-and-subagents.md).
**Sem número de fase**, e de propósito: nem o spec nem o plano lhe deram um, e inventar
`5d` aqui criaria numeração que nenhum outro arquivo cita (D-DV-21).

**O defeito de partida: uma decisão registrada que a pesquisa de fontes derrubou pela
metade.** `parity.yaml`, linhas 18-29, declarava a ausência de `subagent` entre os
mecanismos como deliberada, com a justificativa de que "despacho de subagente é capacidade
de HARNESS do Claude Code […] **nenhuma outra plataforma tem um equivalente** que este
repositório possa acionar". A segunda metade é **falsa por contraexemplo medido**: o Devin
CLI lê `.agents/agents/` nativamente, importa `.claude/agents/*.md` (*"Each `.md` file
becomes a subagent profile"*) e descobre skills em `.agents/skills/<nome>/SKILL.md` —
**três diretórios que este repositório já publicava antes da fase**, sem nenhuma mudança.
O que sobrou da decisão é o recorte, e ele é mais estreito e mais defensável do que a frase
que caiu: **o perfil é nosso, o despacho é deles**. Nenhum arquivo versionado liga
subagente nem fixa modelo — `subagents_enabled` é chave de usuário, o modelo default
resolve por roteador no spawn, e um admin da organização o sobrescreve, inclusive com a
opção *None*, que desliga o despacho por completo.

**O que entrou.** `scripts/sync_skills.py` deixou de **copiar** e passou a **renderizar**
por plataforma: `.claude/` e `.github/` recebem o arquivo inalterado — passthrough byte a
byte, sem round-trip de YAML que reordenaria chaves —, e `.agents/` perde `tools:` e nunca
ganha `model:`. O gate deixou de ser `filecmp.cmp` e passou a comparar o espelho, **em
bytes**, contra o que o renderizador produz; a plataforma é derivada do próprio alvo
(`platform_for`), não de uma quarta lista paralela, e alvo fora das três raízes levanta
`ValueError` em vez de publicar o arquivo cru numa plataforma nova. Os **treze** perfis
(8 coordenadores + 5 executores) declaram em `## Não faz` que não executam manutenção
destrutiva — `ask_user_question` é **sempre negado** a subagente, o que torna a regra 10 do
`CLAUDE.md` inalcançável de dentro de um, e sem a fronteira escrita o modo de falha é
**mudo**. **Doze** das vinte skills declaram `subagent: true` no espelho do Devin, e três
declaram `agent:`. `parity.yaml` ganhou `subagent` em `mechanisms`, declarado para
`claude_code`, `devin_cli` e `devin_desktop` (com o recorte "Devin Local agent, Subagents
(Preview)" escrito em dois lugares do arquivo), e o parágrafo original foi **preservado
palavra por palavra**, com o desvio registrado ao lado.

**Os seis pontos da doc interna que não se sustentaram.** A doc trazida pelo usuário
(`guia_devin_agents_subagents.md`) foi tratada como **hipótese**, não como fonte, e cada
afirmação foi conferida contra `docs.devin.ai` com URL e `retrieved: 2026-08-04`. Seis
caíram, e nenhuma delas cairia por inspeção — todas são plausíveis lidas de longe:

1. **Identificadores de modelo com ponto** (§3.2). A doc escreve `model: glm-5.2`,
   `swe-1.7`, `kimi-k2.7`. O identificador literal usa **hífen** — `glm-5-2`, `swe-1-7`,
   `kimi-k2-7`; o ponto é o *label* de exibição, não o `model_uid`.
2. **A procedência desses literais** (§3.2). Eles vêm da tabela de **preços do Devin
   Desktop**, cujo escopo declarado é custo. Nenhuma página do CLI os documenta como valor
   aceito de `--model` ou de frontmatter; o que a doc do CLI garante são os *short names*
   `opus`, `sonnet`, `swe`, `codex`, `gemini`.
3. **O default do subagente** (§3.3). A doc diz que ele "geralmente resolve para uma
   variante do `swe-1.6` ou `swe-1.7-lightning` dependendo do plano". A fonte é mais
   estreita: resolve por **roteador no momento do spawn**, para SWE-1.6, e
   `swe-1-7-lightning` não aparece como default de subagente em lugar nenhum.
4. **`subagents_enabled` no lugar errado** (§7.2). A doc a aninha dentro de `"agent"`. A
   fonte a põe como chave **de topo** e a marca "(user only)" — ela não é aceita no
   `.devin/config.json` de projeto, e o objeto `agent` documentado tem exatamente duas
   chaves, `model` e `show_history_on_continue`. Consequência: **um repositório não
   controla se subagentes rodam.**
5. **`subagent_default_model` e `alternative_models` não existem** (§7.3). Busca literal
   nas cinco páginas de configuração: **zero ocorrências**. O equivalente funcional é a
   setting de **organização** "Default subagent model", inacessível a arquivo de
   repositório. O bloco JSON de exemplo da doc é inteiramente inventado salvo `agent.model`
   e `subagents_enabled` — e este no aninhamento errado; o formato de `permissions` também
   não corresponde ao documentado.
6. **`!ultra`, `!fast`, `!swe` não existem** (§10.2). `!` é o prefixo de **bash mode** no
   Devin CLI. `/fast` existe, com barra. Um `!fast` digitado com input vazio entraria em
   bash mode e tentaria rodar `fast` como comando de shell.

Os onze vetos `V-DV-*` da pesquisa registram esses seis mais cinco achados que não são
contradição e sim ambiguidade medida — entre eles o que decidiu o desenho do renderizador:
**o mapeamento dos valores de `tools:` não está documentado** (`Bash` → `exec`? `Write` →
`write`?). A fonte diz que o **campo** é aceito; que os **valores** sejam traduzidos é
afirmação que a documentação não faz.

**O que continua no `playbook`, e por quê.** O `playbook` deixou de ser "o que as outras
plataformas usam" e passou a ser **o piso das cinco**, declarado inclusive nas três que
despacham. Ele é o único caminho em `codex` e `copilot_ci`, que a pesquisa **não cobriu** —
e afirmar mais seria repetir o defeito do transporte HTTP da Fase 1, que este mesmo arquivo
de manifesto cita como razão de ser da regra. E ele é o caminho nas três que despacham
sempre que o despacho estiver desligado, o que **não depende deste repositório** em nenhum
dos três gatilhos: `subagents_enabled: false` é escolha do usuário, *None* em "Default
subagent model" é de um admin da organização, e a própria Cognition declara custom
subagents **experimentais**. Daí o invariante que o plano não pediu e a fase entregou:
nenhuma capacidade declara `subagent` **sem** `playbook`. Uma capacidade que declarasse só
o despacho ficaria sem caminho no dia em que o toggle virasse off, e o manifesto não
perceberia.

**Números medidos no fechamento.** 3569 testes passando, 5 skipped (eram 3479 / 5 ao abrir
a branch; +90 em cinco tasks). 13 perfis, todos com a fronteira de manutenção destrutiva
declarada. 20 skills, **12** com `subagent: true` e **3** com `agent:`. 5 mecanismos em
`parity.yaml`, 3 plataformas com `subagent`. `git diff` dos espelhos, lido linha a linha:
**13 arquivos, 13 remoções** em `.agents/agents/` (uma linha `tools:` por perfil) e **12
arquivos, 15 inserções** em `.agents/skills/`; `.claude/` e `.github/` com diff **vazio**,
que é o critério de a renderização não ter vazado para as outras duas plataformas. Nada
mais mudou de tamanho: 66 regras, 16 extratores, 102 kinds, 107 fixtures, 24 rotas, 36
tools MCP. Esta fase não acrescentou capacidade de análise — ela fez a que existe ser
despachável onde alguém mediu que dá.

**O que NÃO entrou, com razão registrada.** `model:` em perfil nenhum (o default resolve
por roteador e o admin sobrescreve; e o identificador correto é dado que envelhece — a doc
interna já errava a grafia dele). Tradução de `tools:` (mapeamento não documentado; chute
em campo de permissão erra caro nos dois sentidos). `.devin/config.json` versionado (as
chaves de projeto configuram o ambiente de quem roda, não a capacidade do repositório).
`subagent` para `codex` e `copilot_ci`. E `agent:` nas nove skills despacháveis com mais de
um coordenador: a alternativa do plano — "o primeiro em ordem determinística" — foi
recusada **com o contraexemplo na mão**, porque em ordem alfabética `review-pyspark-pr`
cairia em `data-quality-reviewer` e `analyze-spark-plan` em
`glue-incremental-performance-architect`, quando o especialista de ambas é
`pyspark-code-reviewer`.

Faixa de commits: `e0e995e` … `0f609d7`, mais o commit de documentação que fecha a fase.
Os vinte desvios `D-DV-1` a `D-DV-20` estão medidos um a um no plano, e três deles
registram teste existente que **teve que mudar** — sempre porque a afirmação antiga virou
o defeito, e sempre apertando: cópia literal da fonte no espelho do Devin passou a ser
`DIVERGENTE`, e "só `claude_code` declara `subagent`" virou "só quem a pesquisa confirma,
com a razão citando seção e `retrieved:`".

**Revisão final, 2026-08-04 — os números acima são os do fechamento e ficam como
estavam; estes são os de depois.** A revisão aprovou 9 dos 10 critérios e mediu **onze**
pendências; as onze fecharam. Testes: **3594** passando, 5 skipped (+25). As **12** skills
despacháveis passaram de **0** para **12** declarando que não executam manutenção
destrutiva e para onde a confirmação sobe — e a instrução antiga foi **corrigida**, não
duplicada, porque dentro de um subagente ela mandava obter o inalcançável. As com `agent:`
caíram de **3** para **2**: `diagnose-oom` era declarante único por **omissão** no
`skills:` de `spark-performance-architect`, e o perfil que sobrava era o orquestrador. O
gate passou a acusar órfão em qualquer profundidade e extensão — antes,
`.agents/agents/rogue/AGENT.md`, que é **layout de descoberta do Devin**, passava com
`--check` em exit 0. A regra 9 do `AGENT_PROTOCOL.md` ganhou o recorte de subagente. E
quatro textos que afirmavam que omitir `tools:` protege alguma coisa foram corrigidos: com
os dois caminhos de descoberta ligados por default e `allowed-tools` valendo *"all tools"*,
omitir é a opção **mais permissiva**. As quatro linhas fechadas estão em *Dívidas abertas*;
os cinco desvios do spec, na §8 dele. **O que a revisão diz sobre a suíte:** nenhuma das
onze quebrava teste, e quatro eram afirmação de efeito que ninguém tinha medido.

**Varredura de completude do Devin, 2026-08-04 (branch `fix/devin-varredura`) — o que
sobrou depois da revisão final.** Seis candidatos foram medidos e a superfície inteira foi
varrida por `grep`. Testes: **3605** passando, 5 skipped (+11). O resultado, em uma linha
cada:

1. **`install_skills.py` publica o espelho renderizado, e estava certo — mas sem teste
   nenhum.** Medido rodando a instalação num diretório limpo: o alvo Devin recebe
   `.agents/` (perfis sem `tools:`, doze skills com `subagent: true`, duas com `agent:`) e
   **não** recebe `agents/`, a fonte. A propriedade era verdadeira e **não guardada** — a
   suíte inteira provava a renderização dentro do repositório, e nada olhava o caminho que
   o usuário de verdade roda. Fechada com quatro testes que comparam o arquivo instalado
   contra `render_agent(fonte, "devin")`, e não contra uma cópia esperada.
2. **`.devin/agents/` é escolha, e não estava registrada.** Agora está, com o critério
   (`.agents/` é um espelho só para perfis **e** skills, é o padrão multiferramenta que a
   Cognition declara suportar, e está ligado por default) e com o gatilho que a inverteria.
3. **`mcp` era declarado para as duas plataformas Devin sem dizer como acioná-lo** — a
   família de defeito do transporte HTTP da Fase 1, que o próprio `parity.yaml` cita como
   razão de ser da regra. Pior: o texto dizia que `.mcp.json` já configurava o Devin CLI,
   e **ele não configura** — o arquivo é o do plugin do Claude Code e parametriza
   `SPARKFORGE_CATALOG` por `${CLAUDE_PLUGIN_ROOT}`, variável que nenhuma página do Devin
   documenta expandir. Medido: `CatalogError` na primeira leitura do catálogo. Fechada com
   o procedimento nativo (`.devin/mcp_config.json` e `devin mcp add`) na §3.4 do
   `GUIA_DE_USO.md`, mais a correção nos outros dois textos.
4. **Nenhum dos treze perfis colide com built-in do Devin, e nada impedia o próximo.**
   `check_profile_names()` entrou no gate que o CI já roda, conferindo as **duas** fontes
   de identidade — nome de arquivo e `name:` do frontmatter, que podem discordar.
5. **`max-nesting`: o modelo de execução da Fase 4 não se traduz, e isso não estava
   escrito.** Um coordenador despachado como subagente **não** despacha os cinco
   executores; virou limite declarado, com o `playbook` nomeado como a decomposição que
   sobra.
6. **A dívida da watchlist continua aberta, com o custo já medido na própria linha.**
   Nada mudou: fechá-la é escrever um leitor do rodapé `Fontes` de `knowledge/**.md`.

E a varredura livre achou **três** que não estavam na lista, todas da mesma espécie —
texto que a pesquisa já tinha derrubado e que ninguém foi corrigir onde ele também morava:
o `guia_devin_agents_subagents.md` na raiz seguia **sem marca nenhuma** de que é hipótese
contradita em seis pontos (agora tem cabeçalho e marcador em cada uma das seis seções); a
docstring de `sparkforge/case/playbook.py` ainda dizia *"Devin, Codex e Copilot não têm
equivalente"*, que é a frase universal que o V-DV-1 derrubou, e um docstring de teste
repetia a mesma leitura; e **quatro textos afirmavam que os treze perfis são perfis de
subagente do Devin**, quando só os oito coordenadores estão num layout de descoberta
documentado — os cinco executores moram em `executors/<nome>.md`, que não é
`agents/<nome>.md` nem `agents/<nome>/AGENT.md`, e se a varredura recorre a fonte não diz.
Nenhuma das três quebrava teste. **O que a varredura diz sobre a revisão final:** ela
mediu onze pendências e nenhuma delas era prosa fora do conjunto de arquivos que a fase
tocou — o `.py`, o guia na raiz e o docstring de teste ficaram de fora porque ninguém
buscou o texto derrubado onde ele não era esperado.

### Fase 4c — validação funcional, e o gate que enfim tem produtor — **CONCLUÍDA** em 2026-08-04

Branch `feat/fase4c-funcval`. Spec:
[`specs/2026-08-04-sparkforge-fase4c-validacao-funcional-design.md`](specs/2026-08-04-sparkforge-fase4c-validacao-funcional-design.md) ·
Plano: [`plans/2026-08-04-sparkforge-fase4c-validacao-funcional.md`](plans/2026-08-04-sparkforge-fase4c-validacao-funcional.md).

**O defeito de partida: um gate que sabia o nome do próprio produtor desde a 4b, e
esperava por ele.** `functional_validation_defined` existia no `routing.yaml` com
`advisory_reason: "sem produtor ate a Fase 4c"` — literalmente nomeando a fase que
o fecharia. A 4b tinha fixado o critério de que gate só endurece **com** produtor
declarado, e deixou este advisory por honestidade, não por omissão. A promessa
implícita era testável: quando o produtor existisse, o gate endureceria
**declarando `satisfied_by`**, sem tocar em uma linha de `store.py`. Foi
exatamente o que aconteceu.

E o nome do gate já dizia **qual** produtor: *defined*, não *executed*. O que o
satisfaz é o **plano**. `dq.check` foi medido e rejeitado como candidato ainda na
4b — ele prova validação **dentro** do job, que é verdade antes e depois da
mudança e não compara duas execuções.

**O que entrou.** `sparkforge/facts/funcval.py` — função **pura** sobre `Fact`, o
quarto módulo derivado no padrão de `call_graph.py`, `fusion.py` e
`benchmark.py`: nunca lê artefato bruto, nunca executa consulta, nunca chama AWS.
Duas metades. `build_plan` deriva **um plano por alvo distinto** de
`pyspark.write` cruzado com `catalog.table_schema`; `build_comparison` lê os dois
resultados que o operador mediu e compara. Quatro kinds — `funcval.plan`,
`funcval.check_delta`, `funcval.analyzed` e `funcval.unresolved` —, 91 testes.
Dois verbos de topo (não `analyze`, pela mesma razão de `benchmark`): `funcval
plan --facts` (repetível) `--key --out` e `funcval compare --plan --before
--after`, nas cinco superfícies, com as tools `sparkforge_funcval_plan` e
`sparkforge_funcval_compare`. Nove fixtures em `fixtures/funcval/` com golden, e
cinco regras em `rules/catalog/funcval.yaml`.

**O gate endureceu declarando dado.** `satisfied_by: funcval.plan`,
`produced_by` com o comando exato, `guards_phases: [report]`. Nenhuma linha de
Python mudou para isso — que era a propriedade que o critério da 4b prometia, e
ela cobrou aqui. `report` passou a ser guardada por **três** gates.

**As correções que a medição impôs ao desenho.** São o mais valioso da fase, e as
quatro invalidam texto que o spec afirmava:

- **`pyspark.join` não dá as chaves.** A D-1 do spec dizia que dava. O fact
  carrega `measures.on_arity` — o **número** de colunas do `on` — e nunca os
  nomes; e na forma com keyword (`df.join(dim, on=["a","b"])`) não emite medida
  alguma, porque `pyspark_ast.py:723-730` lê `node.args[1]`. Contagem, schema e
  agregados seguem deriváveis, e os agregados saem **melhores** do que a D-1
  previa: `catalog.table_schema` dá coluna **e tipo**, que é o que decide o modo
  de comparação.
- **Nenhum dos 102 kinds de então nomeia chave de negócio, então o eixo entra
  declarado.** A varredura dos 16 extratores foi exaustiva; os candidatos
  (`pyspark.dedup`, `pyspark.window`, `plan.join`, `plan.exchange`,
  `sql.predicate`, `sql.projection`) carregam booleano, contagem ou coluna de
  outra natureza. Partição como proxy foi **medida e rejeitada**: em
  `catalog/glue_table_schema`, `db.eventos` tem `distinct_values =
  partition_count = 1200` sobre `dt` para a tabela inteira, e um check de
  unicidade ali acusaria dado correto. A saída não foi calar: **todo** check
  carrega `origin` — `declared` com `derived_from: []`, ou `derived` com o
  `fact_id` —, e sem `--key` o plano escreve `undeclared_axes: ["keys"]` **com a
  razão**. Ausência declarada, que é a mesma disciplina de `dq.unresolved`.
- **`Fact` não carrega juízo nem limiar (`findings/models.py:32`), e a §5 pedia
  as duas coisas ao mesmo tempo.** O spec queria que o `check_delta` dissesse "se
  divergiu" **e** que o limiar não morasse em Python. Para ponto flutuante as duas
  se excluem: decidir exige o número, e o número é `field-heuristic` sem fonte
  oficial. Comparação **exata** continua decidindo `diverged` no fact — que dois
  valores não sejam idênticos é observação, não limiar —, e comparação
  **relativa** sai **sem** `diverged`, com `attrs.diverged_omitted_reason`
  dizendo por quê, e quem decide é a `SF-FVAL-004` contra
  `threshold.relative_tolerance`. Chave que some sem explicação é o defeito que
  este repositório persegue, e é por isso que a sentinela ganhou
  `relative_delta_check_count`: sem ele, `diverged_check_count == 0` seria lido
  como "nada divergiu" quando significa "ninguém aqui decidiu".
- **`1e-9` em YAML vira `str`, e `float > str` derruba o `judge`.** Medido com
  `yaml.safe_load`: `1e-9`, `1e+9` e `1E9` voltam **todos** como `str`; `1.0e-9`
  e `1.e-9` voltam como `float`, porque o resolver de float do PyYAML exige ponto
  decimal na mantissa. É a família do `thresholds` plural da D-4a-22 — o defeito
  não aparece na carga —, e é **pior**: o plural deixa a regra inerte, enquanto a
  string faz a comparação levantar `TypeError`, que `_expr_matches` **não**
  engole (ele só captura `ExprError`), e o `judge` inteiro cai. O limiar está
  escrito `1.0e-9` por isso, com a razão no `sources` da regra e no cabeçalho do
  arquivo.

Uma quinta, da Task 6, muda a forma de uma regra: **`SF-FVAL-004` precisa de duas
condições**, porque um `agg:sum:<coluna>` de coluna **inteira** ou **decimal** é
comparado de forma exata e sai **com** `diverged`. Uma 004 escrita só sobre
`relative_delta` deixaria essa divergência aparecer na sentinela e em achado
**nenhum**: silêncio com cara de aprovação. Medido pelo `judge`, o buraco tem duas
naturezas: por **magnitude**, uma soma que muda em uma unidade só escapa do limiar
`1.0e-9` a partir de **um bilhão** (corte em ~9,95e8 — sobre quinhentos milhões o
`relative_delta` é `2e-9`, **acima** do limiar, e a via relativa ainda pegaria); e
por **forma**, que não depende de magnitude, porque a condição relativa é filtrada
por `attrs.comparison: relative` e um agregado exato nunca casa com ela — sem a
condição exata a regra fica muda para `bigint` divergente em qualquer ordem de
grandeza.

**O limite da área inteira é declarado três vezes, de propósito.** Contagem,
schema, chaves e agregados iguais **não** provam que o dado é o mesmo — duas
linhas podem trocar valores entre si e os quatro passam. O texto está no cabeçalho
do catálogo, na `explanation` de cada uma das cinco regras, e na saída do
comparador (`funcval.analyzed.attrs.proxy_limit`). Quem lê "os quatro proxies
bateram" não pode ter que vir ao YAML descobrir o que isso não prova.

**Sem coordenador novo, e o argumento não é simetria.** `SF-FVAL` entrou em
`rule_areas` de `spark-performance-architect`, ao lado de `SF-BENCH`. Três
medições sustentam a escolha, e nenhuma delas é "a 4a fez assim". (1) **A fronteira
com `SF-DQ` já estava medida e escrita no próprio `routing.yaml`**, no comentário
do gate: `dq.check` prova validação **dentro do job**, que é verdade antes e
depois da mudança e não compara duas execuções — foi por isso que ele foi
rejeitado como `satisfied_by`. A pergunta do `data-quality-reviewer` é outra, e
pendurar `SF-FVAL` nele reabriria a fronteira que o critério 10 do spec fecha por
construção. (2) **`SF-BENCH` e `SF-FVAL` lêem o mesmo par de execuções da mesma
mudança** — um pelo tempo de task, o outro pelo resultado —, e separá-los em dois
coordenadores daria a dois agentes metade de um experimento cada. (3) **A
obrigação já estava escrita no coordenador sem produtor:** *"Preserve correção
funcional"* e *"apresente diff e plano de validação"* estão no corpo dele desde a
Fase 4, e o `reason` da `ROUTE-015` é literalmente a frase de performance —
*"ganho de performance sem validação de contagem, schema, chaves e agregados não é
resultado, é risco"*. Era o mesmo defeito do `benchmark_ref` antes da 4a: exigência
sem quem a produzisse.

**Sem skill nova, e quem decidiu foi a rota.** A `ROUTE-015` já nomeia
`recommended_skill: review-pyspark-pr`, e rota é **dado** — a skill segue a rota,
não o contrário. Os dois verbos entraram em skills que já existiam, e a divisão
saiu dos critérios de despacho que a fase do Devin tornou invariante, não de
gosto: **`funcval plan` foi para `review-pyspark-pr`** porque ele deriva de facts
que já estão em disco e não pede nada a ninguém — a skill é **despachável**, e o
plano continua produzível dentro de um subagente, porque sem `--key` ele **declara
o eixo ausente em vez de perguntar**; **`funcval compare` foi para
`benchmark-pyspark-job`**, que é **não-despachável** exatamente pela razão que o
`compare` também tem, e está escrita em `NON_DISPATCHABLE_SKILLS` desde a fase do
Devin: *"exige um run novo e o id dele, que só aparece depois de alguém publicar a
mudança"*. O lado `--before` do `compare` tem a mesma dependência, e mais: ele só
existe se alguém o mediu antes de a mudança tocar o alvo. Nenhuma entrada de
`DISPATCHABLE_SKILLS`/`NON_DISPATCHABLE_SKILLS` mudou, e nenhuma skill nova
precisou de decisão — que é o desfecho que o `ValueError` daquele gate existe para
forçar quando o contrário acontece.

A seção `## Validação de dados` de `benchmark-pyspark-job` e a red flag de
`review-pyspark-pr` sobre "plano de teste de correção" eram, as duas, **prosa sem
produtor** — mandavam conferir contagem, schema, chaves e agregados sem dizer com
o quê. As duas passaram a nomear o verbo.

**Números medidos no fechamento.** 3828 testes passando, 5 skipped (eram 3594 ao
fechar a fase de perfis do Devin). 71 regras em 13 áreas, 5 delas novas
(`SF-FVAL`). 17 extratores emitindo 106 kinds (eram 16 e 102). 38 tools MCP,
**38 de 38** alcançáveis a partir de algum coordenador. 116 fixtures em 19
domínios, 9 delas em `fixtures/funcval/`. 24 rotas, 8 coordenadores, 5
executores, 20 skills — nenhum desses quatro mudou. 4 gates, agora **3** com
produtor declarado.

**O que esta fase fecha, e é o último.** A §16 do spec da Fase 0 tem quatro itens
de rigor; este era o quarto. Ver a linha própria, logo abaixo, agora marcada
concluída.

**Revisão de documentação de 2026-08-04, depois do "pronto com ressalvas".** A
revisão final da 4c não achou defeito de código e achou **nove** incoerências de
documentação. Todas fechadas; **nenhuma** tocou código de produção. O que vale
registrar é o que a medição contrariou, porque em dois casos ela contrariou a
própria ressalva:

- **A justificativa da `D-4c-23` citava o número errado, em quatro arquivos.** O
  texto dizia que uma soma de `bigint` mudada em uma unidade sobre quinhentos
  milhões dá `relative_delta` de `2e-9`, *"abaixo de qualquer tolerância
  utilizável"*. Medido pelo `judge` contra o catálogo real: `2e-9` está **acima**
  do limiar `1.0e-9`, e nessa ordem de grandeza a via relativa pegaria o caso
  sozinha. O corte medido fica em **~9,95e8** — o `_round_relative` de três
  significativos empurra tudo entre 9,95e8 e 1e9 para `1e-9` exato, e a condição
  é `>`, estrita. **A conclusão da D-4c-23 sobrevive, e por um motivo mais forte
  do que o que estava escrito:** a condição relativa é filtrada por
  `attrs.comparison: relative`, e um agregado exato **nunca** casa com ela — sem
  a condição exata a regra fica muda para `bigint` divergente em ordem de
  grandeza nenhuma, inclusive uma soma de mil. O argumento de magnitude só vale
  num contrafactual que a regra não é. Os quatro textos foram corrigidos para
  dizer as duas naturezas.
- **A ressalva errou a ordem de grandeza, e a medição venceu.** Ela afirmava que
  a via exata só fica sozinha a partir de ~5 bilhões (`2e-10`); o medido é **um
  bilhão**. Registrado aqui porque número de revisão também envelhece.
- **O quarto lugar da correção não era `explanation`, era comentário.** A ressalva
  dizia que o texto do YAML é *"o que o motor publica ao usuário num achado"* e
  pedia atenção a golden de achado. Medido: as duas linhas erradas em
  `rules/catalog/funcval.yaml` são **comentário** dentro de `when.any`, e
  `yaml.safe_load` os descarta. A `explanation` publicada nunca citou o número.
  Nenhuma fixture podia mudar, e nenhuma mudou.
- **A `spec:202` errava um número, não dois.** Dizia "26 desvios, `D-4c-1` a
  `D-4c-26` … os outros **vinte**". Medido no plano: **27** desvios, sem lacuna
  nem duplicata. Mas a §11 detalha **seis** na lista principal mais `D-4c-26` sob
  heading próprio, então `6 + 21 = 27`: "vinte" virou "vinte e um", e "seis"
  estava certo.
- **O `GUIA_DE_USO.md` não tinha a forma que a ressalva mandava seguir.** Ela
  pedia para documentar `funcval` *"seguindo a forma que o guia já usa para
  `benchmark`"*. Medido: o guia **nunca** ensinou `benchmark` como comando —
  a palavra aparecia duas vezes, as duas como prosa solta. Os dois verbos de
  `funcval` foram documentados na §6, onde o guia ensina os outros comandos, e a
  §8 passou a nomear o verbo produtor dos **dois** itens, `benchmark` inclusive:
  cometer no próprio guia o defeito que `SF-FVAL` e `SF-BENCH` acusam no usuário
  não passa.
- **O guia não era coberto por `sync_skills.py --check`, e agora é coberto por
  teste.** Três testes novos em `tests/test_docs_coverage.py::TestGuia`. O
  principal deriva os verbos do parser **real** e exige que todo `sparkforge
  <verbo>` citado no guia exista — não o contrário, porque exigir que o guia
  documente os 16 verbos seria transformar decisão editorial em invariante. Os
  outros dois travam a §8 nomeando os verbos e a §6 ensinando os dois de
  `funcval`. Mesma disciplina de `test_agents_md_lists_every_coordinator`: lista
  derivada, nunca copiada.

Os outros quatro itens eram contagem desalinhada, e a medição confirmou a
ressalva: `AGENT_PROTOCOL.md` dizia "os outros **dois** não têm produtor" quando
são **três com produtor e um sem**; a linha de limite declarado dizia "Dois dos
quatro gates seguem advisory" e listava `functional_validation_defined` entre os
sem produtor, contradizendo a seção da própria fase; `AGENTS.md` dizia "Sixteen
extractors" e "102 distinct fact kinds" (são **17** e **106**, e o `README.md` já
dizia certo); "os quinze `analyze *`" são **catorze**, contados no parser; e "as
duas skills carregam o contorno por escrito" é **uma** — `benchmark-pyspark-job`
ensina `compare` e carrega a extração de `items`, enquanto `review-pyspark-pr`
ensina só `plan`, que **tem** `--out`, e delega a comparação.

**Uma dívida pré-existente foi medida no caminho e registrada como tal:** a área
`SF-CFG`, declarada no `README.md` do catálogo desde o primeiro commit e nunca
escrita. Não é entrega da 4c e não entra na conta dela — ver a linha própria em
*Dívidas abertas*.

### Fase 4 do roadmap (§16) — rigor — **CONCLUÍDA** em 2026-08-04

Distinta da "Fase 4 (executada)" acima (coordenadores, executores e espelho de
orquestração), que é a Fase 4 na nova numeração da seção "Direção" mais abaixo. Esta
continua sendo a Fase 4 do roadmap original, e o escopo da §16 tem quatro itens:

| Item da §16 | Estado |
|---|---|
| Benchmark automatizado antes/depois | **Fechado pela Fase 4a.** Verbo `benchmark`, cinco kinds `bench.*`, área `SF-BENCH`, e `benchmark_ref` citando `fact_id` |
| Validação funcional automatizada (contagem, schema, chaves, agregados) | **Fechado pela Fase 4c.** Verbos `funcval plan` e `funcval compare`, quatro kinds `funcval.*`, área `SF-FVAL`, e o gate `functional_validation_defined` endurecendo com `satisfied_by: funcval.plan`. Nunca **executa** a validação: deriva o que medir e compara o que o operador mediu — a fronteira é a mesma que a 4a recusou atravessar |
| Gates fail-closed opcionais | **Fechado pela Fase 4b.** `case open --strict-gates`, `set_phase` cobrando os gates da fase, override com motivo gravado, e o contrato de produtor como dado no bloco `gates` do `routing.yaml`. Fail-closed só para gate **com** produtor: os outros dois seguem advisory, pelo argumento da §5.5 da Fase 0, que continua válido onde ele se aplica |
| Assinatura de relatório | **Fechado pela Fase 4b.** `report sign` e `report verify` nos três adaptadores, sobre `findings/signature.py`. É assinatura de **correspondência** — texto, evidência e catálogo —, nunca de autoria |

**Os quatro fecharam, e vale registrar o que cada um entregou** — porque "rigor"
é palavra que não se confere:

1. **Benchmark (4a)** deu produtor ao `benchmark_ref`, que era string livre desde
   a Fase 0: o campo passou a citar o `fact_id` de um `bench.run_delta`, e
   `sparkforge validate` rejeita ganho quantificado sem ele. Satisfazer o gate
   digitando qualquer coisa deixou de ser possível.
2. **Gates fail-closed (4b)** puseram a escolha de rigor **no case** e não na
   invocação (`case open --strict-gates`), fizeram `set_phase` cobrar a
   **evidência** dos gates que guardam a fase pedida, e transformaram o contrato de
   produtor em **dado** — o bloco `gates` do `routing.yaml`, com `satisfied_by` e o
   comando de `produced_by`. Override existe e custa uma frase, que fica gravada e
   aparece no `resume`.
3. **Assinatura (4b)** deu ao relatório uma prova de **correspondência** — texto,
   evidência e catálogo —, nunca de autoria, com `report sign` e `report verify`
   nos três adaptadores sobre `findings/signature.py`.
4. **Validação funcional (4c)** deu produtor ao último gate que não tinha:
   `funcval plan` deriva o que medir e `funcval compare` compara os dois lados,
   com o limite dos quatro proxies declarado em três lugares. `report` passou a
   ser guardada por três gates, e os três têm produtor.

O que **não** fechou, e é a outra metade de uma linha do inventário:
`dominant_bottleneck_identified` segue advisory, e não por atraso — nenhum dos 112
kinds afirma dominância, que é ordenação entre candidatos. Endurecê-lo exigiria
reverter uma decisão da Fase 0. Fica como limite declarado, com o
`advisory_reason` escrito no catálogo.

---

### Fase 5d — EMR Serverless — **CONCLUÍDA** em 2026-08-05

Branch `feat/fase5d-emr-serverless`. Fecha a **primeira metade** da linha "EMR
Serverless e EMR on EKS" de *Trabalho previsto* — a única do roadmap que não
tinha posição na *Ordem*. Spec e plano em
[`specs/2026-08-04-sparkforge-fase5d-emr-serverless-design.md`](specs/2026-08-04-sparkforge-fase5d-emr-serverless-design.md)
e [`plans/2026-08-04-sparkforge-fase5d-emr-serverless.md`](plans/2026-08-04-sparkforge-fase5d-emr-serverless.md);
o spec ganhou §11 com os desvios que o tornaram errado, e não foi reescrito.

**Números medidos no fechamento** (eram, ao fechar a 4c, os da esquerda): regras
71 → **77**, áreas 13 → **14**, extratores 17 → **18**, kinds 106 → **112**,
fixtures 116 em 19 domínios → **135 em 20**, tools MCP 38 → **40** (e **40 de
40** alcançáveis a partir de algum coordenador), fontes vigiadas 37 → **51**,
testes 3831 → **4157**, 5 skipped. Rotas 24, coordenadores 8,
executores 5, skills 20 e gates 4 — nenhum dos cinco mudou. As três fixtures
acima de 132 e os testes acima de 4125 entraram na **revisão final**, descrita no
fim desta seção.

**O que entrou.** `knowledge/emr-serverless/` com dois arquivos de fonte datada;
`sparkforge/facts/emr_serverless.py` com seis kinds `emrs.*`;
`collect emr-serverless` e `analyze emr-serverless` nas cinco superfícies
declarativas **mais uma sexta que nenhum documento previa**; **19** fixtures com
golden bidirecional (16 no fechamento, 3 na revisão final); a área `SF-EMRS` com
6 regras e três vetos escritos no cabeçalho; e `tests/test_rules_emrs_boundary.py`, que mede a fronteira com
`SF-EMR` nas duas direções.

**A pergunta da matriz de runtime teve um terceiro desfecho, e ele decide o resto
da fase.** A D-5 do spec previa dois — matrizes idênticas (o produtor de
`RuntimeContext.emr` entra) ou divergentes (não entra). Medido: **a AWS não
publica a matriz do EMR Serverless.** As 24 páginas por release trazem só Spark,
Hive e Tez, sem o sufixo `-amzn-N`; Hadoop, Iceberg e Python não aparecem em
nenhuma, e há `releaseLabel` em uso (`emr-spark-8.0.0`) que não tem sequer chave
na `EMR_MATRIX`. Nas 24 releases comparáveis a versão de comunidade do Spark
coincide uma a uma — mas três das quatro colunas não têm fonte do lado do
Serverless. **O produtor não entra, e a razão escrita é "sem fonte", nunca "as
matrizes divergem"**: afirmar divergência seria afirmar o que ninguém mediu. A
consequência atravessa a fase inteira — as 19 fixtures declaram `runtime: {}`, as
6 regras têm `runtime_scope` vazio, e um `get-application` não emite
`env.platform` nenhum, porque `_PLATFORM_KEYS` conhece só `emr` e `glue`.

**O coordenador não se partiu, e o argumento é medido — não a preferência do
spec.** A D-1 dizia *"coordenador novo exige fronteira medida; aqui não há"*, e
agora **há**: 17 casos de teste medem que nenhuma regra de uma área alcança
artefato da outra, com zero invasões. Ela não muda a decisão, e a razão é que
**fronteira de catálogo e fronteira de despacho não são a mesma coisa**: a
primeira vale depois que alguém já escolheu o verbo. A de despacho foi medida e
**não existe** — nenhum fact `emrs.*` alimenta qualquer identidade de
`_PLATFORM_KEYS`, então um `describe-cluster` emite `env.platform` com
`resolved: emr` e um `get-application` não emite nada. Partir o coordenador seria
roteá-lo por prosa, que é o oposto do critério deste repositório. `SF-EMRS` fica
com `emr-infra-reviewer`, cuja `description` nomeia as duas plataformas.

**Duas medições que mudaram regra, e uma que criou fixture.** (1) Ausência de
bloco no Serverless costuma ser o default **seguro** — `autoStopConfiguration` e
`managedPersistenceMonitoringConfiguration` nascem `true` —, o inverso do EC2:
uma regra "nenhum destino de log" por ausência acusaria toda application no
default protegido, e por isso ela exige o campo explícito e o extrator é quem
aplica os defaults documentados, num fact só (`log_destination_count`). (2) O
custo de uma janela de auto-stop larga **depende de haver pré-init**, porque a
cobrança é por worker existente: `SF-EMRS-005` exige pré-init na condição, e a
linha "sem pré-init não há worker de que cobrar" está declarada como **dedução do
modelo de cobrança**, não como frase da AWS. (3) A verificação de apagabilidade
reprovou o termo de pré-init em duas regras — nenhuma das 15 fixtures o
sustentava —, e a 16ª (`sem_preinit_nada_a_cobrar`) existe por causa disso.

**O que a fase não pode afirmar, e está escrito dentro do produto.**
`get-application` descreve o **padrão** da application, e `StartJobRun` o
sobrepõe — inclusive **removendo** classificação e destino de log. Nenhum achado
de `SF-EMRS` prova o que um job run executou, e o limite viaja na `explanation`
das seis regras, no corpo do coordenador e na skill. Ver a linha própria em
*Limites declarados*.

**Cinco superfícies eram seis.** `ARTIFACT_KINDS` em
`sparkforge/collect/base.py:29` é tupla fechada validada em
`ArtifactEntry.__post_init__`: coletor com `kind` fora dela levanta `ValueError`
na escrita do manifesto, e nenhuma seção do spec ou do plano a citava. As cinco
listadas são declarativas; esta é executável e falha tarde.

**Quarenta e cinco desvios registrados** (`D-5d-1` a `D-5d-45`, sem lacuna nem
duplicata; os três últimos são da revisão final). Trinta e cinco cabeçalhos citam
uma Task do plano, onze citam o spec e quatro citam os dois — a §11 do spec
recolhe os que tornam aquele documento errado, e ela é o único lugar em que o
spec foi tocado.

**A revisão final fechou quatro ressalvas, e uma delas era uma P0 falsa.**

1. **Duas frases publicadas que o próprio HEAD tornou falsas.** `knowledge/INDEX.md`
   ainda dizia que as fontes de `emr-serverless/` não estavam no lock — estão,
   e o lock foi de 37 para **51** (13 URLs de Serverless mais
   `aws.amazon.com/emr/pricing/`, que duas regras citam). E o docstring do golden
   de Serverless ainda prometia a Task 5 no futuro, quando **6 das 16** fixturas
   de então já disparavam regra, uma por `SF-EMRS`. As duas viraram passado, na
   forma que `test_fixtures_golden_emr.py` já usava desde a 5b.
2. **A P0 que disparava sobre pré-init sem worker** (`D-5d-43`). O measure que as
   duas regras de custo liam contava **entradas do map `initialCapacity`**, não
   workers: `{"DRIVER": {"workerCount": 0}}` com auto-stop desligado disparava
   `SF-EMRS-001` em **P0**, e o mesmo payload **sem** `workerCount` disparava P0
   no mesmo julgamento em que saía `emrs.unresolved{missing_worker_count}` —
   achado confiante erguido sobre ponto cego declarado. A `explanation` da regra
   funda o achado em *"o que se cobra é worker existente"*, e nenhum dos dois
   prova worker existente. **Endurecido, não declarado como limite:** a fonte
   registra `workerCount` só como "(número)", sem `Required` e sem mínimo, então
   nada torna o estado inalcançável. O measure virou
   `initial_capacity_worker_count`, soma dos `workerCount` **lidos**; a contagem
   de entradas já existia em `emrs.analyzed`. Duas fixtures novas, dois payloads
   cada, e 14 goldens de facts regenerados.
3. **O invariante do runtime deixou de existir só em prosa.** `releaseLabel` do
   Serverless não pode alimentar `RuntimeContext.emr`, e isso estava escrito em
   **cinco** lugares e guardado por **zero** testes. Agora há um, na forma que o
   repositório já usava para PySpark: `runtime_sources_from_facts(facts) == {}`,
   com as duas iscas que no EC2 **são** produtoras — o release label e
   `spark-env`/`PYSPARK_PYTHON` — presentes nos facts e afirmadas antes, para o
   teste não passar por vacuidade.
4. **A anotação de segredo é bypass incondicional, e o produto negava.** Ver a
   linha própria em *Limites declarados*: o comportamento fica, com a razão de
   fonte; o que mudou foi a prosa que afirmava o contrário, em três lugares.

E uma quinta medição, que virou **dívida** em vez de conserto: das 7 regras do
catálogo com `severity_by`, **6 tinham ramo de severidade sem golden nenhum**.
Não é regressão da 5d — é anterior. `SF-EMRS-005` fechou o seu com dois payloads
(1440 e 1439, que fixam o ramo P2 **e** o limiar `field-heuristic`); os **cinco**
restantes estão registrados, com o teste que falta nomeado.

### Rodada de dívidas abertas — **CONCLUÍDA** em 2026-08-05

Branch `fix/dividas-abertas`, onze commits sobre `1638758`. Não é fase: nenhuma
capacidade nova, nenhum extrator novo, nenhuma área de regra nova. É o inventário
de *Dívidas abertas* atacado item a item, e o critério de escolha foi o do próprio
inventário — **dívida é o que fecha escrevendo código**. Seis das oito eram isso
mesmo e foram pagas; as outras duas **não eram dívida**, e descobrir isso exigiu
tentar pagá-las.

**Seis fecharam, duas foram reclassificadas, uma nasceu.** Saldo medido contando
as linhas das três tabelas: **8 dívidas → 1**, **5 fases → 6**, **17 limites
declarados → 18**. Abertas caem de 30 para 25; fechadas sobem de 25 para 31.

Suíte 4157 → **4266**, 5 skipped. Fixtures 135 → **145**, os mesmos 20 domínios.
Fontes vigiadas 51 → **109**. Regras 77, kinds 112, extratores 18, tools 40 —
nenhum deles mudou, e isso é o que separa esta rodada de uma fase.

**O que cada uma fechou, e o número que prova.**

1. **`funcval compare` ganhou `--out`** (`93d9c69`). `--out` na CLI e `out_path`
   na tool, com a escrita em `_core` **antes** da paginação — o arquivo traz a
   lista completa, o stdout continua sendo o envelope. Medido na cadeia inteira
   sobre `fixtures/funcval/count_diverged/`, com `--limit 2`: o arquivo traz os
   **5** facts e `judge --facts` sobre ele acha `SF-FVAL-001` em **P0**; sobre a
   página de 2 extraída do envelope (`next_cursor: 2`) o mesmo `judge` acha
   **zero**. A P0 não some por acaso: com o corpus completo o `check_delta` de
   `count` é o quarto dos cinco facts, e a primeira página nunca o alcança. Era o
   defeito que `SF-FVAL-005` acusa no dado do operador, cometido pelo fluxo do
   próprio motor. O contorno que a dívida mandava escrever — extrair `items` e
   conferir `next_cursor` à mão — virou falso ao fechar, e foi reescrito nas duas
   superfícies que o carregavam: `skills/benchmark-pyspark-job/SKILL.md` e
   `GUIA_DE_USO.md`.
2. **O ramo exato da `SF-FVAL-004` ganhou golden** (`64d7ec8`). Fixture
   `fixtures/funcval/aggregate_exact_diverged/`, com o eixo trocado em relação a
   `aggregate_outside_tolerance`: lá o agregado de ponto flutuante se move e o
   inteiro fica parado; aqui o inteiro se move e o de ponto flutuante fica
   **idêntico**. Prova por apagamento, que é o que a dívida pedia: apagar a
   condição exata da regra deixava o corpus inteiro verde, e com a fixture deixa
   golden vermelho. **A magnitude não é a que a dívida citava, e o desvio é para o
   lado que fortalece a fixture.** A dívida dizia "uma unidade sobre quinhentos
   milhões dá `relative_delta` da ordem de `2e-9`, abaixo de qualquer tolerância
   utilizável" — e `2e-9` está **acima** de `1.0e-9`, como o próprio comentário da
   regra já registrava desde a 4c (corte medido em ~9,95e8). A fixture move uma
   unidade sobre **quinhentos bilhões** (500.500.123.000 → 500.500.123.001), e o
   `relative_delta` medido é **`2,0e-12`**: três ordens de grandeza **abaixo** da
   tolerância, e não uma acima dela. **A razão principal de as duas condições
   serem necessárias nem sequer é de magnitude** — a condição relativa filtra por
   `attrs.comparison: relative`, e agregado exato não casa com ela em grandeza
   nenhuma; a magnitude desta fixture existe para fechar o contrafactual mais
   generoso possível, aquele em que a condição relativa lesse todo agregado.
3. **`plan_ref` deixou de sair `""` nos sete goldens** (`9474aa8`).
   `scripts/regen_fixtures.py` passou a injetar o `Fact.id` do plano via
   `with_plan_ref`, e `tests/test_fixtures_golden_funcval.py` **importa** essa
   função em vez de espelhá-la — o único passo do golden que não é reimplementado
   no teste, de propósito, porque um `plan_ref` reimplementado seria um segundo
   lugar onde errar. Medido, e contraria o que a dívida temia: `plan_ref` vive só
   em `attrs`, **nenhum `Fact.id` se moveu** e **nenhum `findings.json` mudou** —
   o commit `9474aa8` toca duas linhas de `facts.json` em cada uma das sete e mais nada.
4. **Os seis ramos de `severity_by` sem golden fecharam** (`0070369`, `3c45c2f`,
   `5dc3f0e`, `b89dc73`, `3b24ee6`, `080c871`). Medição refeita do zero e
   **idêntica à da revisão da 5d**: das 7 regras com `severity_by`, **15** ramos,
   **9** vistos, **6** sem — `SF-EMR-006` (P2), `SF-ICE-001` (P2), `SF-PQ-001` (P0
   **e** P1), `SF-UI-001` (P2) e `SF-UI-004` (P2). Seis fixtures, cada uma no
   **limiar exato** do próprio ramo, e o guarda que faltava:
   `test_every_severity_branch_has_a_golden_that_produces_it`, com asserção de
   vacuidade (`total >= 15`) para que a varredura não passe por ter parado de
   enxergar `severity_by`. Contado sobre o catálogo inteiro, e não só sobre as 7:
   **85 ramos de severidade, 85 com golden**. **Custo registrado, porque ele é
   real e foi medido em bytes, não estimado:** a fixture do P0 da `SF-PQ-001` tem
   **14.305.787 bytes (14,3 MB)** — o ramo é contagem de arquivo pequeno, e encolher
   a listagem seria mentir sobre a contagem que a regra lê. `fixtures/` foi de
   **1.756.621 para 17.615.531 bytes** (1,8 MB → 17,6 MB), medido em `git ls-tree -l`
   nos dois lados. Em objeto git as seis fixtures pesam **712 KB** comprimidos, e essa
   é a conta que o clone paga.
5. **`SF-DQ-002` deixou de acusar quem protegeu o pipeline** (`cd5bf49`).
   `_Callees`, a aresta simétrica de `_Callers` da 5c.2: lá "este parâmetro chegou
   persistido?", com a resposta no chamador; aqui "esta leitura leva a aborto?",
   com a resposta no callee. **Limite de um salto, e o número é a decisão:** nos
   86 `.py` de `fixtures/` e `sparkforge/` de antes da rodada havia **10** checks,
   **9** enforcements diretos e **zero** cadeia com helper — nenhum caso real
   pedia o segundo salto, e o valor que atravessa dois corpos pode ter sido
   transformado no caminho. O que passa do salto não é calado: vira
   `dq.unresolved` com reason `enforcement_beyond_one_hop`, nomeando os dois
   helpers. As três fixtures são o argumento e nenhuma prova sozinha —
   `enforcement_behind_helper` (o falso positivo que parou),
   `helper_only_logs_the_result` (mesma forma de chamada, corpo que só registra:
   ela quebra se a travessia virar "toda chamada resolvida é consequência") e
   `enforcement_two_helpers_deep` (o limite, com o ponto cego contado). Sobre o
   corpus de hoje, com as três dentro: **89** `.py`, **13** checks, **10**
   enforcements, **1** `enforcement_beyond_one_hop`. Quatro textos afirmavam que a
   análise **não** fazia isso, e os quatro foram corrigidos: a `explanation` da
   regra em `rules/catalog/data-quality.yaml`, o perfil
   `agents/data-quality-reviewer.md`, a skill `review-data-validation` e a
   descrição da tool `sparkforge_analyze_data_quality`.
6. **A pesquisa do Devin entrou no `refresh_knowledge`** (`61377ed`).
   `watchlist()` ganhou uma **segunda origem derivada** — as URLs dos blocos
   `Fontes` de `knowledge/**.md` (campo `docs` do lock) —, e continua sem lista
   mantida à mão, que era o desenho que a dívida não podia quebrar. Lock de **51
   para 109** fontes: 51 citadas por regra, 104 por `knowledge/`, 46 pelas duas,
   e **zero sem consumidor** — `test_each_entry_names_who_cites_it` exige o
   vínculo de volta, porque fonte vigiada que ninguém cita é alarme sem endereço.
   O invariante `set(lock) == set(watchlist())` **não afrouxou**: mudou de onde a
   watchlist vem, não o que o lock promete. `--update --offline` entrou junto, e
   não é conveniência — sem ele o invariante passaria a depender de rede para ser
   reparável, e num fork sem segredo isso é um teste que ninguém consegue
   consertar. As 58 fontes que entraram por `knowledge/` estão **sem hash**, e a
   primeira conferência com rede as relata como NOVA, que é a verdade.

**Uma observação de processo, sem linha no inventário porque não há nada a
escrever.** A correção da descrição da tool `sparkforge_analyze_data_quality`
está commitada em `93d9c69` (o commit do `--out` do `funcval`, 09:02) e não em
`cd5bf49` (o commit que implementou a travessia, 09:20): dois agentes editaram a
árvore ao mesmo tempo e o primeiro a commitar levou a edição do outro junto.
Consequência medida: houve uma janela de **quatro commits** — `93d9c69`,
`b89dc73`, `3b24ee6` e `080c871` — em que a descrição da tool afirmava uma
capacidade que o extrator ainda não tinha, com a suíte inteira verde. E ela fica
verde por construção: o único teste sobre descrição de tool é
`test_every_tool_has_a_description`, que confere `len(description) > 20` e mais
nada. A árvore de hoje está certa; o registro fica porque é exatamente a família
de defeito que este arquivo acusa desde a revisão da fase de perfis: **afirmação
de efeito que ninguém mediu, e que não quebra teste nenhum**.

### Fase 6a — grafo com Spark (`SF-GRAPH`) — **CONCLUÍDA** em 2026-08-05

Branch `feat/fase6a-graph`, sete tasks. **Abre o roadmap de bancos** — é a primeira
das quatro especializações e a única que não é um banco. Spec e plano em
[`specs/2026-08-05-sparkforge-fase6a-graph-design.md`](specs/2026-08-05-sparkforge-fase6a-graph-design.md)
e [`plans/2026-08-05-sparkforge-fase6a-graph.md`](plans/2026-08-05-sparkforge-fase6a-graph.md);
o spec ganhou §11 com os desvios que o tornaram errado, e **não foi reescrito**. Os
desvios medidos durante a implementação estão no plano, `D-6a-1` a `D-6a-48`.

**Números medidos no fechamento** (à esquerda, os da rodada de dívidas abertas): regras
77 → **81**, áreas 14 → **15**, extratores 18 → **19**, kinds 112 → **118**, fixtures
145 em 20 domínios → **164 em 21**, tools MCP 40 → **41** (e **41 de 41** alcançáveis a
partir de algum coordenador), fontes vigiadas 109 → **131**, ramos de severidade 85 →
**89**, testes 4266 → **4634**, 5 skipped. Rotas **24**, coordenadores **8**,
executores **5**, skills **20** e gates **4** — nenhum dos cinco mudou, e o de rotas é
decisão medida, não coincidência (ver *O coordenador*, abaixo).

**O que entrou.** `knowledge/graph/` com dois arquivos de fonte datada
(`graphframes-api.md` e `availability.md`); `sparkforge/facts/graph.py` com **seis**
kinds `graph.*`; `analyze graph` nas superfícies declarativas; **19** fixtures com golden
bidirecional; a área `SF-GRAPH` com **4** regras e **seis** vetos escritos no cabeçalho
(`V-GF-1`, `V-GF-2`, `V-GR-1`…`V-GR-4`, mais os cinco `V-AV-*` na página de
disponibilidade); e `tests/test_rules_graph_boundary.py`, que mede a fronteira nas
**três** direções entre `SF-GRAPH`, `SF-DQ` e `SF-PY` — a primeira fronteira do
repositório em que as áreas vizinhas leem o **mesmo artefato**, um `.py`, e nenhum
recorte de artefato as separa.

**A pesquisa matou uma das quatro regras candidatas, e no sentido oposto ao previsto.**
A §5 do spec previa "algoritmo iterativo sem limite de iteração". A fonte fechou — e
disse que **em nenhum dos dezesseis algoritmos com noção de iteração a ausência é
defeito**: em seis é `TypeError`/`AssertionError` (código que não roda), em três é
default documentado, em `pageRank` o modo `tol` é oficial, e em `connectedComponents` a
doc diz textualmente *"Default is `Integer.MAX_VALUE` (unlimited). It is generally not
recommended to change this value."* A fixture que existiria só para exercitá-la **saiu do
corpus**, e no lugar entrou um teste que varre as 19 fixtures e reprova se qualquer fact
passar a carregar `has_max_iter`, `max_iter_missing`, `iteration_limited`, `unbounded` ou
`has_iteration_limit` — porque bastaria um deles para alguém escrever
`where: {attrs.has_max_iter: false}` e reintroduzir a regra vetada pela porta dos fundos.
É a quinta fase seguida em que a pesquisa mata premissa que parecia óbvia no papel.

**O escopo por faixa de Spark, e a capacidade que o motor não tinha.** Nove das 34
células da matriz Glue×EMR não têm artefato de GraphFrames, e o discriminador não é "a
versão é antiga": é que **nenhum artefato foi publicado para Spark 3.3 em linhagem
nenhuma** — `0.8.2` para em 3.2, `0.8.3` começa em 3.4, `io.graphframes` compila contra
3.5. Escrever isso exigiu `version_scope._specs`: uma chave de `runtime_scope` passou a
aceitar **uma lista** de specs, conjugando como as chaves entre si, e
`{spark: [">=3.3", "<3.4"]}` é o primeiro uso. As alternativas com o que existia falham
as duas, e o número está medido: `"==3.3"` reprova `3.3.1` e `3.3.2` — os Sparks de EMR
6.10.x e 6.11.x, **quatro das nove células, que sumiriam em silêncio** —, e `">=3.3"`
sozinho estenderia a acusação a 3.4 e 3.5, onde ela é falsa. Mudança aditiva: lista vazia
levanta `ValueError` de propósito, pelo mesmo modo de falha do curinga que a Fase 5a
levou 20 regras para descobrir. `SF-GRAPH-002` é a **primeira regra do catálogo guardada
por `spark` em vez de `glue`**, e isso quebrou dois testes de escopo que presumiam o
contrário — `SPARK_VERSIONED` virou grupo próprio, porque a razão dele é "a afirmação só
é verdadeira nesta faixa" e não "esta infraestrutura não existe aqui".

**A fronteira com `SF-PY` foi medida e o resultado é 16, não zero.** O critério 6 da §10
do spec exigia que nenhuma regra de `SF-GRAPH` disparasse sobre fixture vizinha "nem o
contrário". A primeira metade está provada; **a segunda é falsa, e é a construção
funcionando**: `SF-PY` dispara **16 vezes sobre `fixtures/graph/`** — `SF-PY-008` em
catorze fixtures e `SF-PY-012` em duas. Cada um cita `pyspark.cache` ou `pyspark.conf_set`
e **nenhum** cita um fact `graph.*`; o `subject.snippet` de cada um bate com a linha real
do arquivo; e nenhuma das dezenove fixtures chama `unpersist`. `cache`/`persist`/
`unpersist` ficaram **fora** do vocabulário de `graph.algorithm` justamente porque
`pyspark.cache` já os emite sobre o mesmo artefato (`V-GR-4`). Os dezesseis estão nomeados
um a um em `ESPERADO_PY_SOBRE_GRAFO`, com o argumento ao lado — silenciar a lista era a
única saída errada, e um décimo sétimo obriga alguém a escrever o argumento antes de
acrescentar a linha.

**O coordenador ficou onde estava, e a proporção é que decidiu.** A §9 do spec deixava em
aberto: coordenador próprio ou `pyspark-code-reviewer` estendido. O critério da Fase 4c
exige fronteira de **despacho** medida, e a 5d refinou que sem discriminador **em dado**
partir cria par roteado por prosa. Medido com os três extratores sobre os três corpora:
**há** discriminador em dado — `SF-GRAPH` dispara 5 vezes em `fixtures/graph/` e **zero**
nas 13 fixtures de `dq/` e nas 17 de `pyspark/` —, então o bloqueio da 5d não se aplicava
e a decisão teve de sair do outro eixo. **Nas 19 fixtures de grafo, `SF-PY` dispara 16
vezes em 14 delas e `SF-GRAPH` 5 vezes em 5, e as cinco são subconjunto das catorze**: não
há, no corpus, um job em que a pergunta de grafo chegue sozinha. O precedente da 5c mede o
inverso — nas 13 fixtures de `dq/`, `SF-DQ` dispara 10 vezes em 8 contra `SF-PY` em 2 —, e
foi por isso que *aquele* partiu. Um coordenador de grafo seria selecionado em 5 de 19
jobs de grafo e entregaria os outros 14 a `pyspark-code-reviewer`, que precisaria declarar
`SF-GRAPH` de qualquer forma. E o teste que fundou a fronteira com o irmão responde para o
outro lado aqui: apague as linhas de validação e o job continua de pé; apague as linhas de
GraphFrames e não sobra job nenhum.

Consequência em dado, e ela fechou um buraco que a Task 5 tinha deixado provisório
(`D-6a-32`, `D-6a-45`): `AGENT-004` ganhou `findings_area: SF-GRAPH` junto com `SF-PY`,
`SF-PLAN` e `SF-CG`. **Antes disso, um case cujos achados fossem só de grafo voltava de
`next_step` com `recommended_agent: None`** — a área tinha dono no frontmatter e nenhuma
rota em dado, que é a diferença entre cobertura e despacho. Como o destino é o mesmo
agente, a pergunta de precedência que a `AGENT-008` teve de responder não existe aqui, e o
total de rotas segue **24**. A `description` do coordenador — que é o gatilho de seleção,
não decoração — passou a nomear grafo; até este commit ela não o nomeava de propósito,
para não afirmar cobertura que a decisão ainda não tinha tomado.

**Sete das dezenove fixtures existem para provar que o motor cala.** A exigência de
checkpoint de `connectedComponents` tem **cinco** saídas escritas no `.py`, não três como
o plano supunha: `algorithm="graphx"`, `checkpointInterval<=0`, `use_local_checkpoints=True`,
e mais duas por `spark.conf.set` dentro do próprio job (`spark.checkpoint.dir` e
`spark.graphframes.useLocalCheckpoints`) — ignorá-las faria a regra P0 disparar sobre
código que resolveu o problema na linha de cima. Há um **sexto** estado, em que a conf é
ilegível e `checkpoint_required` sai **ausente**: ponto cego contado, não acusação. A
decisão vem pronta do extrator porque `engine._where_matches` reprova caminho ausente e
`_expr_matches` engole o `ExprError` — nenhuma regra deste catálogo consegue exprimir "o
código não declarou saída nenhuma", que é o caso comum. É o padrão que `SF-EMR-008` fixou:
o extrator transcreve o modo de falha documentado, e severidade, limiar e recomendação
continuam no catálogo.

**O que a fase abriu.** Duas dívidas e três limites declarados, todos medidos durante a
implementação e com o número na mão — nenhum é surpresa de revisão. As duas dívidas
fecham escrevendo código nosso (um kind derivado no extrator de Terraform, e uma fixture);
os três limites fecham revertendo decisão cujo custo já está registrado, e em um deles o
gatilho de reabertura **não é nosso** — é a comunidade publicar artefato para Spark 3.3,
o que a release note da `0.8.3` afirma existir e o repositório de artefatos responde com
404.

### Preservação semântica — as superfícies que agem, e a regra que faltava — **CONCLUÍDA** em 2026-08-05

Branch `feat/preservacao-semantica`, sete commits, um por natureza. **Não é fase de
roadmap:** é o fechamento de uma exigência declarada imprescindível pelo dono do projeto —
todo agente, skill e componente preserva o funcional; tunar e reduzir custo sim, alterar
lógica, regra de negócio ou resultado não. Otimização que muda o resultado não é
otimização: é defeito com ganho embutido, e mais caro de achar depois, porque o job fica
*mais rápido* enquanto entrega dado errado.

**O achado é sobre alcance, não sobre texto.** Medido: **33 de 33** arquivos de agente e
skill apontam para `AGENT_PROTOCOL.md`, e preservar semântica não era uma das nove regras.
`CLAUDE.md:12` tem a regra 8, e o próprio `AGENT_PROTOCOL.md:3-6` declara que aquele texto
**não é injetado em lugar nenhum** — então a regra 8 alcança quem roda no Claude Code e
mais ninguém. Devin, Copilot e Codex liam nove regras, e nenhuma delas era esta.

**A assimetria mais cara estava em `agents/executors/sf-synthesizer.md`**, o arquivo onde
toda recomendação é escrita: **onze linhas** exigindo `benchmark_ref` e explicando por que
texto livre é fraude, e **zero** sobre preservar o resultado. O executor que escreve a
recomendação destrutiva sabia cobrar o relógio e não sabia cobrar o dado.

**Números medidos** — à esquerda o estado antes da branch, contado arquivo a arquivo:

| Dimensão | Antes | Depois |
|---|---|---|
| Regras do `AGENT_PROTOCOL.md` | 9 | **10** |
| Agentes que recomendam mudança com produtor nomeado | 1 de 8 | **8 de 8** |
| Skills que recomendam mudança com produtor nomeado | 2 de 14 | **14 de 14** |
| Regras do catálogo com eixo de resultado no `validation` | 59 de 81 | **62 de 81** |
| Testes | 4713, 5 skipped | **4723**, 5 skipped |

**Três medições contrariaram o levantamento que abriu a rodada, e as três estão aqui
porque medição vence texto.** (1) O levantamento dizia "4 skills acionáveis, 1 parcial, 15
mudas"; contadas uma a uma, **2** nomeavam produtor (`benchmark-pyspark-job`,
`review-pyspark-pr`), **3** tinham o princípio sem verbo, **1** mencionava semântica por
acidente e **14** calavam. (2) Dizia que `optimize-pyspark-code` tinha o princípio sem
produtor; ele não tinha menção nenhuma — quem tinha eram `diagnose-data-skew`,
`optimize-latest-per-key` e `design-incremental-processing`. (3) O eixo de resultado no
catálogo era **59**, não 54; a diferença é a redação (`resultado idêntico` conta tanto
quanto `resultado funcional`), e a contagem está no critério, não no número.

**O que entrou.** A **regra 10** do protocolo, escrita na forma das outras nove e nomeando
os dois produtores — `sparkforge funcval plan` e `sparkforge funcval compare`, com as tools
`sparkforge_funcval_plan` e `sparkforge_funcval_compare` —, o gate
`functional_validation_defined` que o plano destrava, e os três limites que a saída carrega.
Seção nova em **8** perfis de agente e **14** skills, cada uma abrindo pelo que **move o
dado naquele domínio**, não por princípio genérico. Três regras do catálogo com eixo de
resultado: `SF-PY-009`, `SF-UI-004` e `SF-UI-005`.

**O que ficou mudo, e é decisão, não esquecimento.** Os **4** executores de leitura
(`sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier`), que dizem por escrito que não
propõem mudança, e as **4** skills de leitura (`analyze-library-call-graph`,
`analyze-spark-plan`, `analyze-spark-ui`, `sparkforge-diagnose`). Texto decorativo em
arquivo que não age é ruído que envelhece, e este arquivo já tem inventário demais de
número copiado para acrescentar prosa copiada.

**A contradição do catálogo era a medição mais forte da rodada, e não estava no
levantamento.** `SF-UI-004` e `SF-UI-005` propõem "eliminar UDF Python" — com essas
palavras — e mediam razão de GC, runtime e memória non-heap. `SF-PY-001`, `SF-PLAN-001`,
`SF-PLAN-002` e `SF-PQ-002` propõem a **mesma troca** e todas exigem comparação linha a
linha com nulls e bordas. O catálogo sabia a resposta três regras ao lado. A troca não fica
mais barata por ter chegado pela via da Spark UI em vez da via do código, e
`tests/test_rules_result_axis.py` pergunta ao catálogo quais regras propõem a troca em vez
de fixar a lista — regra nova entra sozinha na parametrização.

**Em `SF-PY-009` a metade contraintuitiva vem primeiro no `risks`, e ela é o motivo de a
regra ter passado tanto tempo medindo só tempo e heap:** o conjunto de linhas do equi-join
**não muda** entre `BroadcastHashJoin` e `SortMergeJoin`. Quem procurar a divergência na
contagem não acha. O que muda é o particionamento e a ordem, e com eles todo operador não
determinístico a jusante — `dropDuplicates`, `first`/`last`, `collect_list`,
`monotonically_increasing_id`, `row_number` com empate — que devolve outra coisa com a
**mesma** contagem. **Os quatro eixos de `SF-FVAL` passam inteiros enquanto a linha que
sobreviveu é outra**, e é exatamente o ponto cego que a `SF-FVAL` declara. O `validation`
foi escrito no padrão da `SF-EMR-005`, e a metade de campo do argumento está declarada em
`sources` com `origin: field-heuristic`, porque a página do Spark sustenta o lado do plano
e não sustenta o lado do resultado.

**Um número que envelhecia dentro do texto que o produto emite.**
`_KEYS_UNDECLARED_REASON` afirmava "nenhum dos 102 kinds dos 16 extratores nomeia chave de
negócio", e essa frase é emitida em `funcval.plan.attrs.undeclared_axes`, aparece no
`explanation` da `SF-FVAL-003`, na descrição de duas tools MCP e em três goldens. Medido: a
união de `EMITTED_KINDS` tem **118** kinds em **19** módulos, e
`spark-performance-architect.md` dizia **106** — três números diferentes para a mesma
medida, nenhum certo. A correção não foi trocar 102 por 118, que envelhece pelo mesmo
caminho: foi **tirar o número**. A afirmação que interessa continua inteira e passa a não
ter validade.

**Nenhum texto novo promete mais do que a ferramenta entrega**, e isso foi requisito de
redação, não ressalva: os quatro eixos são **proxies** — contagem, schema, chaves e
agregados iguais não provam que o dado é o mesmo, porque duas linhas podem trocar valores
entre si e os quatro passam. Todo texto escrito nesta rodada carrega esse limite, e o teste
do protocolo cobra a palavra `proxies` junto com os dois verbos e o gate.

**Nada foi escrito em `description` de skill.** O teto de 1024 (`test_frontmatter_valido`)
estava a **10** caracteres de distância em `review-emr-cluster` e a **44** em
`optimize-pyspark-code`; o corpo não tem teto, e o digest de `## Protocolo` — que resume o
contrato e existe nas 20 — ganhou a cláusula da regra 10 porque digest incompleto de um
contrato de dez regras é a mesma família de defeito que este arquivo persegue em
`AGENTS.md`.

**Correção de contagem deste próprio arquivo.** A linha de *Números correntes* declarava
**4634** testes; medidos na abertura da branch, eram **4713**. As 79 de diferença entraram
com a revisão final da Fase 6a sem que o número subisse.

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

### Revisão final da Fase 6a — **CONCLUÍDA** em 2026-08-05

Sexto par de olhos sobre a fase que acabou de fechar, e ele achou três coisas que
nenhum candidato previa. As três fecharam com teste; duas viraram limite
declarado; os números do registro da 6a acima são os do dia em que ela fechou e
**esta seção é que vale para o corpus e para as rotas**.

**A P0 acusava quem tinha configurado o checkpoint, em quatro formas correntes.**
`SF-GRAPH-001` é P0 e lê `checkpoint_configured_in_module`, e o extrator não lia
`SparkSession.builder.config("spark.checkpoint.dir", …)`, chave por constante,
chave por laço nem `set(key=…, value=…)` — e em nenhuma delas emitia
`graph.unresolved`. Afirmava `false` sobre dado que não tinha lido, que é o
oposto exato do que o cabeçalho do módulo promete. **A assimetria era o defeito**:
o caminho do *valor* já omitia a decisão e contava o ponto cego; o da *chave*, não.
Hoje as duas metades caem do mesmo lado — chave ilegível vira
`unreadable_conf_key` e a decisão é **omitida**, nunca `false`. `.config()` do
builder entrou no vocabulário por assimetria de custo e não por frequência: a
chave é literal distintivo, e o falso negativo dela era P0 sobre código correto.
Rótulo corrigido de quebra: `use_local_checkpoints=1` saía como
`non_literal_argument` sobre argumento **literal**, e agora sai como
`non_boolean_value`. **Cinco fixtures novas, uma por forma.**

**Dois `same_subject` eram apagáveis com a suíte inteira verde.** Nenhuma das 19
fixtures tinha duas construções com arestas não persistidas nem dois laços com
algoritmo — e com um sujeito só, a regra por entidade e a por conjunto dão o
mesmo número de achados. `dois_grafos_no_mesmo_arquivo` fecha os dois: quatro
achados, e apagar qualquer um dos `same_subject` derruba o golden para um,
verificado apagando cada um, rodando e restaurando. **Medido e diferente do que a
regra prometia (`D-6a-49`)**: a entidade é a **função**, não a construção — está
na tabela de *Limites declarados*.

**Cinco áreas do catálogo não alcançavam rota `AGENT-*`, e isso era
PRÉ-EXISTENTE.** `SF-BENCH` (4 regras), `SF-EMRS` (6), `SF-ENV` (5), `SF-FVAL`
(5) e `SF-UI` (6) — **26 regras** — voltavam de `next_step` com
`recommended_agent: None`. O `D-6a-45` mediu o buraco na própria área, consertou
a própria área e não olhou as outras. `SF-EMRS` era o mais caro: declarada por
`emr-infra-reviewer` em `rule_areas` desde a 5d, com a `AGENT-007` casando
`findings_area: SF-EMR` por igualdade exata. A `AGENT-007` virou `any:` com as
duas áreas de EMR; **`AGENT-009`** leva `SF-UI`/`SF-BENCH`/`SF-FVAL` ao
`spark-performance-architect` e **`AGENT-010`** leva `SF-ENV` ao
`glue-infra-reviewer`. Precedência escrita nas duas rotas, e medida: nenhum
despacho já existente muda. **O teste derivado que o `D-6a-45` dizia faltar
existe agora** — toda área do catálogo alcança uma rota, medido chamando
`next_step` e não lendo o YAML, mais a metade simétrica: o agente roteado precisa
declarar a área em `rule_areas`. Revertendo o `routing.yaml`, ele reprova com 10
falhas sobre as 5 áreas.

**Números depois desta rodada.** Corpus de grafo: **25 fixtures** (eram 19), das
quais **6** disparam regra e **19** existem para provar silêncio — **9** delas
sobre código correto. `SF-PY` dispara **23 vezes em 20** fixtures de grafo e
`SF-GRAPH` **9 vezes em 6**, e as 6 continuam subconjunto das 20: a proporção que
decidiu manter o coordenador não mudou de lado. Rotas determinísticas: **26**
(`ROUTE-001`…`ROUTE-016`, `AGENT-001`…`AGENT-010`). Kinds: **118** em **19**
extratores. Regras: **81**.

**Sete incoerências documento ↔ código**, todas medidas e corrigidas na mesma
rodada: a prosa de *Dívidas* dizia "tabela de uma linha" sobre uma tabela de
três; quatro números vencidos em tabelas **vivas** deste arquivo (112 kinds, 18
extratores, 77 regras em dois lugares); `README.md` dizia que
`emr-infra-reviewer` lê duas áreas quando são três desde a 5d — `AGENTS.md` e
`GUIA_DE_USO.md` já diziam três; `knowledge/INDEX.md` parou de contar o lock em
109 fontes quando ele está em **131**; e a docstring de `extract_graph` dava uma
razão que o próprio código contradiz — ela recebe texto porque só quem tem o
texto pode **tentar** o parse e emitir o `graph.unresolved`, e a sentinela
justamente **não** sai quando o arquivo não compila.

### `refresh_knowledge` — o que ele faz e o que recusa fazer

Não baixa o texto das docs para o repositório. Guarda, em
`knowledge/sources.lock.json`, o hash do texto normalizado de cada fonte, a data
da conferência e **quem cita aquela URL** — `rule_id` no campo `rules`, página em
`docs`. O relatório não diz "a doc mudou assim"; diz "a doc mudou, e as regras X
e Y, e a página Z, dependem dela — releia".

Três razões, na ordem em que pesam: o diff de uma página da AWS é quase todo
ruído de navegação, e relatório que grita sempre treina o operador a ignorá-lo;
copiar doc de terceiro para o repo é decisão de licenciamento que ninguém tomou;
e o objetivo nunca foi ter a doc, foi saber quando relê-la.

A watchlist tem **duas origens, as duas derivadas e nenhuma mantida à mão**: o
conjunto de `sources[].url` das regras do catálogo, e as URLs dos blocos `Fontes`
de `knowledge/**.md`. Regra nova com fonte nova entra sozinha, e página nova com
fonte nova também; lista paralela é o passo que alguém esquece. Fontes com versão
no path (`docs/3.5.6/`, `apache-iceberg-1.0.0`) não são buscadas: o conteúdo é
imutável e vigiá-las só produziria ruído.

**Até 2026-08-05 a origem era só o catálogo, e o texto acima dizia isso.** A
segunda entrou na rodada de dívidas abertas, porque conhecimento que nenhuma
regra cita nunca entrava — foi o caso de `knowledge/devin/`, que sustenta perfil
de agente e não regra. O preço da segunda origem é o **vínculo de volta**, e ele
é obrigatório: toda entrada do lock nomeia pelo menos um consumidor, porque fonte
vigiada que ninguém cita é alarme sem endereço.

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
| EMR | release label, instance fleets, `describe-cluster` | `SF-EMR` — **entregue** pela Fase 5b |
| EMR Serverless | `get-application`: pré-init, auto-stop, destinos de log, `runtimeConfiguration` | `SF-EMRS` — **entregue** pela Fase 5d. O que ficou de fora tem linha própria em *Dívidas abertas*: job runs (fase) e a matriz de runtime que a AWS não publica (**limite declarado** desde 2026-08-05 — entrou como dívida e foi reclassificada quando o caminho alternativo que ela propunha foi exercitado e não fechou o título dela) |
| EMR on EKS | virtual cluster, container provider, pod template | sem área, sem `knowledge/` e sem posição na *Ordem* |
| Testes de dados | ~~saída de Deequ, Great Expectations, dbt tests; schema declarado~~ — **o artefato previsto aqui não é o que entrou.** A Fase 5c leu o **`.py`** e vetou o resultado de execução: repetir o que a suíte já disse não acrescenta garantia. Ver a seção da 5c | `SF-DQ` — **entregue** |
| Redshift | plano de query, `STL`/`SVL`, distkey e sortkey | `SF-RS` |
| Streaming | config de Kinesis e MSK, checkpoint de Structured Streaming | `SF-STR` |
| Orquestração | DAG de Airflow/MWAA, definição de Step Functions | `SF-ORC` |
| Custo | Cost Explorer, CUR, DPU-hours | `SF-COST` |
| IaC além de Terraform | CDK, CloudFormation | estende o extrator atual |
| Configuração de Spark como coisa lida | `emr.configuration` e `emrs.configuration` (já extraídos, com `provenance` e `sha256`), `pyspark.conf_set`, `--conf` dentro de `tf.attribute`, e `SparkListenerEnvironmentUpdate` no event log — **os dois últimos ainda não são desmontados por extrator nenhum** | `SF-CFG` — declarada no primeiro commit de `rules/catalog/README.md` e **nunca escrita**; virou fase em 2026-08-05, com o buraco medido na linha própria de *Fases*. Sem posição na *Ordem* |

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
3. **Fase 5a.2** — cobrir as dívidas da 5a — **CONCLUÍDA** em 2026-08-01, mesma
   branch. Ver seção própria acima
4. **Fase 5b** — EMR on EC2 — **CONCLUÍDA** em 2026-08-01, branch
   `feat/fase5b-emr`. Ver seção própria acima
5. **Fase 5c** — SF-DQ, validação de dados — **CONCLUÍDA** em 2026-08-03, branch
   `feat/fase5c-dq`. Ver seção própria acima. É a linha "Testes de dados" da
   Metade A, e ela entrou pelo recorte estático: cobertura e posicionamento da
   validação dentro do `.py`, não resultado de execução
6. **Fase 5c.2** — um passo para dentro da chamada — **CONCLUÍDA** em 2026-08-03,
   branch `feat/fase5c2-helper`. Ver seção própria acima. Fecha uma das duas
   dívidas de travessia da 5c e deixa a outra aberta com o motivo medido
7. **Fase 4a** — benchmark antes/depois — **CONCLUÍDA** em 2026-08-03, branch
   `feat/fase4a-benchmark`. Ver seção própria acima. Fecha o primeiro dos quatro
   itens de rigor da §16 e dá produtor ao gate de `benchmark_ref`
8. **Fase 4b** — gates fail-closed e assinatura de correspondência —
   **CONCLUÍDA** em 2026-08-04, branch `feat/fase4b-gates`. Ver seção própria
   acima. Fecha dois dos três itens de rigor que restavam da §16, e o corte entre
   eles não é de esforço: gate com produtor endurece, gate sem produtor continua
   advisory
9. **Fase 4c** — validação funcional automatizada (contagem, schema, chaves,
   agregados) — **CONCLUÍDA** em 2026-08-04, branch `feat/fase4c-funcval`. Ver
   seção própria acima. Era o terceiro item de rigor, e o único que exige
   artefato novo — o resultado de consultas que alguém roda. É ela que deu
   produtor a `functional_validation_defined` sem que nada da 4b mudasse
10. **Fase 5d** — EMR Serverless — **CONCLUÍDA** em 2026-08-05, branch
    `feat/fase5d-emr-serverless`. Ver seção própria acima. Fecha a primeira
    metade da única linha de *Trabalho previsto* que não tinha posição nesta
    lista; a segunda, EMR on EKS, continua sem posição, e a decisão de enfileirá-la
    é de roadmap
11. **Especialização por banco de dados** — uma fase por ferramenta, na ordem
    `SF-GRAPH`, `SF-DDB`, `SF-NEP`, `SF-MONGO`, decomposta em
    [`specs/2026-08-03-sparkforge-roadmap-bancos.md`](specs/2026-08-03-sparkforge-roadmap-bancos.md).
    O roadmap decide a decomposição e **recusa** decidir o conteúdo: os candidatos
    de regra são hipóteses, e cada fase abre com pesquisa de fontes — em **cinco**
    fases seguidas ela matou premissa que parecia óbvia no papel.
    **`SF-GRAPH` está CONCLUÍDA** desde 2026-08-05, branch `feat/fase6a-graph` —
    Fase 6a, seção própria acima. Era a primeira das quatro e a única que não é um
    banco, e ela derrubou a premissa mais central do próprio spec: das quatro
    regras candidatas da §5, uma foi **vetada pela fonte** (limite de iteração
    ausente não é defeito em nenhum dos dezesseis algoritmos) e outra **não entrou**
    por falta de capacidade no motor. Restam `SF-DDB`, `SF-NEP` e `SF-MONGO`, nesta
    ordem, e as três leem artefato que este repositório ainda não coleta
12. **Fases seguintes** — custo, orquestração, Redshift, streaming; o eixo de
    **job runs** do EMR Serverless (`get-job-run`, `billedResourceUtilization`),
    aberto pela 5d e sem posição aqui; e **configuração de Spark como coisa lida**
    (`SF-CFG`), que virou fase em 2026-08-05 ao ser medida, e também **não tem
    posição** aqui. Dizer que não tem é a mesma disciplina que esta lista aplicou
    à linha do EMR Serverless até a semana passada: enfileirar é decisão de
    roadmap, e o inventário registra a ausência em vez de fingir uma posição
13. **Trilha paralela** — mecanismo de recomendação com garantia declarada, quando a base de restrições estiver maior. As frentes sem artefato da especialização em bancos — escolha de banco, modelagem de grafo, boas práticas genéricas — entram por aqui, e até lá viram restrição auditável em `knowledge/`

## Fase 6b — `SF-CFG`, configuração de Spark como coisa lida — **EM ANDAMENTO** (2026-08-07)

A área declarada no `README.md` do catálogo desde o primeiro commit e nunca
escrita. **Task 1 de 6 fechada**: os sinais. Área de regra, `cfg.effective`
derivado, fixtures da área, rotas e perfis seguem abertos — e esta seção diz
isso em vez de sugerir fase concluída.

**Decisão de desenho, tomada antes do código.** Quando as camadas de
configuração discordam e o event log **não** está disponível, a área **falha
fechada**: nenhum `cfg.effective` é inferido, sai um fato de conflito nomeando
as camadas, e toda regra que dependa do efetivo simplesmente não dispara. A
alternativa — aplicar a precedência documentada do Spark e marcar
`provenance: inferred` — cobriria mais casos e faria regra disparar sobre valor
que ninguém mediu. Mesmo princípio do `emr.configuration.unapplied`, que já
existia: qualidade da evidência é fato, não nota de rodapé.

| Sinal | Onde | Estado |
|---|---|---|
| `spark.conf_effective` | `facts/event_log.py` | **novo** — um fact por propriedade de `SparkListenerEnvironmentUpdate` |
| `spark.conf_excluded` | idem | **novo** — conta por seção o que o extrator não desmontou |
| `tf.spark_conf` | `facts/terraform.py` | **novo** — desmonta o `--conf` do Glue, que empacota N propriedades numa string |
| `pyspark.conf_set` | `facts/pyspark_ast.py` | **corrigido** — de 1 para 4 formas |

**O defeito que a auditoria do `pyspark.conf_set` achou, e ele estava no
corpus.** O extrator só reconhecia `<algo>.conf.set(k, v)`. Medido: das quatro
formas que aparecem em job real, **três não emitiam fact nenhum** — nem o fato,
nem `pyspark.unresolved`. `SparkConf().set()`, `SparkSession.builder.config()` e
`sc._conf.set()` sumiam, e "nenhum `conf_set` neste arquivo" era indistinguível
de "o arquivo configura por uma forma que ninguém lê". Qualquer regra com
condição `absent:` sobre uma chave seria vaziamente verdadeira.

Duas causas, e a segunda é a interessante: o gate era
`method == "set" and "conf" in methods`, e a detecção estava **depois** do guard
de raiz — `builder.config(...).getOrCreate()` fica no meio da cadeia e era
descartado inteiro. Movida para antes do guard, pelo mesmo argumento que já
isenta read/write dele, escrito no comentário daquele bloco desde a Fase 1.

A prova de que isso não era hipótese: a fixture `checkpoint_por_builder_config`,
do corpus de grafo, **existe para exercitar exatamente essa forma** — configura
`spark.checkpoint.dir` por `builder.config` — e o corpus era mudo sobre ela. Com
a correção ela passou a produzir `SF-PY-012`, e o gate de fronteira
`test_rules_graph_boundary.py` exigiu a resposta por escrito antes de aceitar a
linha nova. A resposta está lá: não é invasão, é a área SF-PY sobre um job que
também é job PySpark, com evidência ancorada na linha real.

**Recorte declarado.** De `SparkListenerEnvironmentUpdate`, só `Spark
Properties`. `System Properties` e `Classpath Entries` num `facts.json`
commitado são superfície de informação sem contrapartida para tuning. O que
ficou de fora é **contado** em `spark.conf_excluded`, por seção — exclusão
contada, nunca silenciosa, como `opaque_caller_function_count`.

**Limite herdado, registrado.** `spark.conf_effective` é o que o run **reportou**
como suas propriedades, não uma medição independente do motor. O próprio
`event_log.py` já argumentava isso para a versão de Spark, e por essa razão a
versão nunca foi lida daí. Para configuração de tuning a distinção é menos
grave — o valor reportado é o que o driver resolveu — mas ela não some, e vai na
explicação da regra quando a área for escrita.

**Dívida nova, com custo medido.** `sparkforge/facts/secrets.py` nasce como
fonte única de redação de segredo em par chave/valor. `_looks_like_secret` está
implementado em `emr_cluster.py`, `emr_serverless.py` e `terraform.py`, os dois
primeiros anotando em comentário que repetem o terceiro. Configuração de Spark é
onde credencial mais aparece — `spark.hadoop.fs.s3a.secret.key`, senha em URL de
JDBC — e virar a quarta cópia seria drift em superfície de segurança. Os três
existentes **não** foram migrados: cada um tem golden gravado, e regravar golden
sem defeito é risco de semântica sem ganho medido. Consolidá-los é dívida, não
esquecimento.

**Contagem que estava errada, corrigida no caminho.** *Números correntes* dizia
**164** fixtures golden com `graph` em 19. Medido: **171**, com `graph` em 25 —
a Fase 6a acrescentou seis e o total não acompanhou. A linha da Task 1
acrescentou a 171ª (`terraform/spark_conf_in_arguments`), criada porque o gate
`test_every_kind_of_every_extractor_appears_in_some_golden` reprovou
`tf.spark_conf` sem corpus que o produzisse.

## Compatibilidade de migração Glue por par de versões (SF-MIG) — **CONCLUÍDA** (2026-08-21)

Onze tasks (`docs/superpowers/plans/2026-08-21-glue-migration-compat.md`): a
matriz de runtime saiu de `GLUE_MATRIX` compilado para
`knowledge/glue/runtime-matrix.yaml`, com fonte e `retrieved` como qualquer
outro fato externo; `sparkforge/migration/version_path.py` expande um par
origem/alvo nos degraus intermediários; `sparkforge/facts/migration.py` emite
oito kinds `mig.*` por observação pura; `rules/catalog/glue-migration.yaml`
julga com `runtime_scope`; `sparkforge/migration/assessment.py` aplica o
catálogo uma vez por degrau e agrega, com gates fail-closed para dado que só
existe com execução real (dados, performance, custo, canary).

**Task 11 fechou a última pergunta em aberto: onde fica a fronteira do Glue
6.0.** Confirmado em 2026-08-21 contra `migrating-version-60.html` e
`release-notes.html`, as duas oficiais — runtime Spark 4.1.1, Python 3.13,
Scala 2.13.17, Java 17, Iceberg 1.11.0. `migrating-version-60.html` afirma,
textualmente: "ANSI mode is enabled by default in Spark 4.1. Operations that
previously returned NULL on overflow (for example, integer arithmetic, cast
operations) now throw exceptions." Glue 5.1 roda Spark 3.5.6, onde ANSI é
default OFF — a fronteira é Glue 6.0, não antes. Isso desbloqueou
`SF-MIG-003` (cast sem guarda sob ANSI mode), que ficava `blocked_on` desde a
Task 7 por falta exatamente dessa confirmação: trocou para
`runtime_scope: {glue: ">=6.0"}` real, e o catálogo volta a ter **zero**
regras `blocked_on` — o mesmo estado que valia antes da Task 7 introduzir
SF-MIG. O par de fixtures `cast_sem_guarda` (Glue 5.0, silêncio por versão) /
`cast_sem_guarda_ansi_default` (Glue 6.0, dispara em P1) prova as duas pontas
no nível do golden; `TestRegraBloqueadaNuncaAparece` e o teste novo
`test_sf_mig_003_dispara_no_degrau_que_cruza_glue_6_0` provam o mesmo no
nível do assessment multi-degrau.

**Dívida registrada, não dívida nova.** `sparkforge/migration/glue/analyzer.py`
(`GlueMigrationAnalyzer`) é o analisador que a área SF-MIG substitui —
correspondência de substring sem fonte, sem `runtime_scope`, sem procedência,
com `target_runtime` default `"5.1"` fixado no código. A Task 11 mediu se ele
ainda tem consumidor real antes de decidir: `TOKENSAVE_DISABLE_GREP_HOOK=1
grep -rn "GlueMigrationAnalyzer\|analyze_script\|migration.glue" --include=*.py
--include=*.yaml --include=*.json .` acha um fora do próprio teste e do
re-export — `sparkforge/cli/forge.py:16,108-109`, o comando `cmd_migrate_glue`
da CLI, que importa `GlueMigrationAnalyzer` e chama `analyzer.analyze_script(
content, source_runtime=args.from_runtime, target_runtime=args.to_runtime)`.
Mesmo padrão de `sparkforge/facts/secrets.py`: dívida **medida**, não
implícita. O módulo antigo **não foi apagado** porque apagá-lo quebraria esse
comando; `sparkforge/migration/__init__.py` reexporta `GlueMigrationAnalyzer`,
`GlueMigrationAssessment` e `MigrationFinding` por causa dele, e
`tests/test_migration_assessment.py::test_nenhum_par_de_versao_aparece_no_codigo_do_motor`
já isenta `glue/analyzer.py` do teste de par de versão embutido no motor,
citando esta mesma decisão desde a Task 10. **Fechar** é migrar
`cmd_migrate_glue` para `sparkforge.migration.assessment.assess()` — que já
expande o caminho por `version_path.steps` e julga por degrau, com o mesmo
catálogo `SF-MIG` — e só então apagar o analisador antigo, `tests/test_migration_glue.py`
e a exceção do teste de genericidade. É código nosso, sem decisão de terceiro
para reverter; fica fora do escopo desta task porque a CLI tem consumidor
externo hoje (`docs/vnext/claims.lock.json` cita `sparkforge/migration/glue/analyzer.py`
como o único artefato real por trás da dimensão "Migration" numa alegação
composta), e trocar o backend de um comando publicado não é o mesmo trabalho
que confirmar uma versão de runtime.

### Continuação — `SF-MIG-004`, o diff de Terraform ligado à migração (2026-08-22)

`docs/harness/GLUE6-GAP.md` mediu o que `prompt_glue_harness.md` pede contra o
que já existe, e apontou uma única linha em que o trabalho era **conexão, e não
construção**: `extract_terraform_diff` já anotava todo `tf.attribute` com
`changed` e `previous_value`, e `assess()` já expandia um par de versões em
degraus, mas nenhuma regra ligava os dois. Uma linha de `glue_version` alterada
num PR tinha o tamanho de um ajuste de configuração e o efeito de trocar Spark,
Python, Scala, Java e Iceberg de uma vez.

`SF-MIG-004` fecha isso. Ela casa `tf.attribute` com `key: glue_version` no bloco
raiz e exige `previous_value` **diferente** de `value` — não apenas
`changed: true`, que também é verdade para um `aws_glue_job` criado no próprio PR
já em Glue 6.0, onde não existe migração nenhuma para avaliar. O par de fixtures
`fixtures/tfdiff/glue_version_migrado` (dispara) e `fixtures/tfdiff/glue_job_novo`
(não dispara) prova as duas pontas.

**A regra é a primeira de SF-MIG com `runtime_scope: {}`, e isso teve consequência
medida.** As três anteriores são guardadas por fronteira de versão; esta afirma
que o diff mudou a versão, o que vale para qualquer par e não depende de runtime
detectado — o gate correto é `requires_facts: [tf.attribute]`. Com ela a área
deixou de sumir inteira num runtime sem Glue, e as duas exceções de ÁREA que
declaravam esse sumiço viraram letra morta: `AREA_MAY_VANISH_WHEN`
(`tests/test_rule_scope_by_nature.py`) e `AREA_FULLY_OUT_OF_SCOPE`
(`tests/test_runtime_glue_versions.py`) reprovaram juntas, em seis testes, pedindo
que a exceção fosse reexaminada. As duas saíram, com a justificativa registrada no
lugar. `docs/gates-por-mudanca.md` ganhou as duas listas, que não estavam lá.

O catálogo vai a 120 regras; `manifest.json` acompanha. `rules/catalog/README.md`
listava quinze áreas e não citava `MIG` desde que a área nasceu — corrigido aqui.

## Ferramental de agente — ecossistema caveman vendorizado (2026-08-07)

Não é fase do analisador: nenhuma regra, nenhum extrator e nenhum fact mudaram.
É **infraestrutura de sessão** — o que o repositório gasta em token para operar
os agentes que já tinha.

**Critério de entrada, fixado depois de duas rodadas:** clonar é a instalação
inteira. Não há `package.json` no repositório, nenhum caminho padrão chama `npm`
ou `npx`, e nada aqui vai à rede. Peça que não cabe nisso fica **fora**, com a
razão registrada.

| Peça | Autor | Como chega | Estado |
|---|---|---|---|
| `caveman` | Julius Brussee, MIT | `vendor/caveman/`, pinado em `ec83e5ba` | Plugin do marketplace local `sparkforge-caveman`. **Ligado, zero instalação** |
| `cavekit` (`ck`) | Julius Brussee, MIT | `vendor/cavekit/`, pinado em `c322f0bb` | Mesmo marketplace. **Ligado, zero instalação** |
| `caveman-shrink` | Julius Brussee, MIT | `vendor/caveman/src/mcp-servers/`, sem dependência | **Em disco, desligado** — medido em 0,1 % neste catálogo |
| `cavemem` | Julius Brussee, MIT | — | **Fora**: npm + módulo nativo, e não economiza token |
| `caveman-code` | Julius Brussee, MIT | — | **Fora**: npm + módulo nativo, e roda fora do Claude Code |

**Por que marketplace local e não `.claude/skills/`.** Aquele diretório é
espelho gerado de `skills/`, e `scripts/sync_skills.py --check` acusa **órfão em
qualquer profundidade** — skill de terceiro colocada ali quebraria o gate na
primeira execução, e `sync_skills.py` (modo default) a apagaria. `vendor/` como
marketplace `directory` mantém o layout do upstream intacto, não toca espelho
nenhum, e carrega skills, subagentes, comandos e hooks pela porta que o Claude
Code já tem para isso.

**As duas lacunas do "clonar e usar", e como cada uma fechou.** A primeira
rodada entregou plugin vendorizado e ativação declarada, e ainda assim o alvo —
*não instalar nada além do repositório* — não estava atingido:

1. **Node.** Os dois hooks do plugin caveman são `node ...`. Sem Node eles não
   rodam, as skills continuam carregando, e "ligado por padrão" vira "ligado
   quando alguém digitar `/caveman`" — sem nada acusar. Fechada com um hook de
   `SessionStart` em shell puro, guardado por `command -v node`: com Node é
   no-op (sem injeção dupla), sem Node imprime o ruleset de
   `vendor/caveman/src/rules/caveman-activate.md`. Perde-se só o flag de modo e
   o `/caveman-stats`, que são do hook em JS.
2. **`npm`.** Fechada por **remoção**, não por conveniência. A rodada anterior
   tentou um bootstrap opt-in que disparava `npm ci` sozinho; a decisão final
   foi tirar `cavemem` e `caveman-code` do repositório. `package.json`,
   `package-lock.json`, os cinco hooks do cavemem, o servidor MCP dele e o
   wrapper `scripts/hooks/` foram apagados. O invariante virou gate:
   `tests/test_vendor_caveman.py::TestSemNpm` falha se aparecer `package.json`
   na raiz, ou `npm`/`npx`/`node_modules` em qualquer comando de hook ou
   servidor MCP — **inclusive no `plugin.json` do projeto de terceiro**, que
   pode mudar num bump futuro.

**Por que remover em vez de manter opcional.** `cavemem` não economiza token:
o `SessionStart` dele *injeta* contexto da sessão anterior — medido em ~2 k tokens
numa sessão de teste. É memória, e memória durável neste projeto já tem dono:
`.sparkforge/case.yaml`, commitado, que é o único registro que um `Finding` pode
citar. `caveman-code` é um cliente de terminal alternativo, roda fora do Claude
Code e não participa da economia daqui. Nenhum dos dois pagava o custo de pôr
npm, registry e compilação nativa no caminho de quem clona.

**`caveman-shrink`: vendorizado, medido, desligado.** Proxy MCP do mesmo autor,
**sem dependência nenhuma**, que comprime o campo `description` do catálogo de
tools. Medido contra os 41 tools do `sparkforge` em 2026-08-07:
**146 438 → 146 295 bytes, 0,1 %**. As regras cortam artigo e filler **em
inglês**; as descrições deste catálogo são em português. Nomes e `inputSchema`
saem idênticos — o proxy está correto, só não tem o que cortar. Fica em disco
com a medição registrada em `vendor/CREDITS.md` e um teste que garante as duas
metades: continua disponível, e nada o põe no caminho do MCP sem medição nova.

**Dois defeitos, encontrados e depois descartados junto com o código.** Ao
exercitar o bootstrap apareceram `spawn('npm.cmd', …)` levantando **EINVAL**
desde a correção do CVE-2024-27980 (Node 18.20 / 20.12) — escondido atrás de um
lock gravado antes do spawn — e `process.stdout.write` seguido de `process.exit`
**perdendo a linha** com stdout em pipe, que é como o Claude Code chama o hook.
Ambos foram corrigidos e o código todo saiu na decisão acima. Ficam registrados
porque a lição sobrevive ao código: **caminho de hook não exercitado é caminho
não testado**, e os dois só apareceram ao rodar, nunca ao ler.

**Modo `full` fixado no repositório.** `.caveman/config.json` é o *repo-local
config* que o caveman resolve antes da configuração de usuário e depois só da
variável de ambiente. Fixa o modo para quem clonar sem alterar a configuração
global de ninguém.

**As cópias upstream ficam desligadas dentro do projeto.** `.claude/settings.json`
declara `caveman@caveman: false` e `ck@cavekit: false`. Dois caveman ligados
injetam o ruleset duas vezes por sessão — ativar em dobro custa o token que a
peça existe para cortar.

**Agente sem plugin.** Devin, Copilot e Codex não carregam plugin nem hook. Para
eles o ruleset está inline em `AGENTS.md`, com o recorte que este projeto impõe
por cima: o schema `recommendation:`/`Finding` inteiro, números, versões,
`rule_id`, `fact_id`, strings de erro e blocos de código são **verbatim**.
Compressão que apaga campo de evidência é defeito, não economia.

**O que impede o vendor de apodrecer.** `vendor/PINS.json` guarda repo, SHA,
lista de arquivos mantidos e o patch local; `vendor/MANIFEST.sha256` guarda o
sha256 de cada um dos 127 arquivos. `python scripts/vendor_caveman.py --check`
é gate **sem rede** e roda em `tests/test_vendor_caveman.py`, com 29 testes que
cobrem procedência, ativação e crédito. Um único patch declarado: o
`caveman-compress` do upstream publica o `SKILL.md` em `skills/` e os scripts
que ele executa só em `plugins/` — sem a cópia, a skill carrega e falha em uso.

**A superfície de execução virou lista fechada.** Vendorizar código de terceiro
que roda como hook criou uma superfície que o repositório não tinha: clonar e
abrir o Claude Code passa a **executar código** antes de alguém digitar nada. O
`MANIFEST.sha256` cobre os bytes de `vendor/`, mas não cobria o
`.claude/settings.json`, que é nosso e commitado — um PR que acrescentasse um
`curl | sh` ali executaria na máquina de todo contribuidor, e num diff grande
passaria como linha de JSON.

`tests/test_execution_surface.py` fecha isso com a **string exata** de cada
comando em três superfícies (`.claude/settings.json`, o `plugin.json`
vendorizado, os servidores de `.mcp.json`), mais um deny-list de construções de
execução arbitrária como segunda camada. Allowlist de padrão foi recusada de
propósito: `node .*` autorizaria `node -e "..."`.

O gate foi verificado por mutação, não por leitura: injetar
`curl -s https://… | sh` no `SessionStart` faz **3 dos 12 testes falharem** —
o da lista fechada, o do deny-list e o de permissão morta.

No mesmo passe, `.claude/settings.local.json` entrou no `.gitignore` do
repositório. Ele estava protegido apenas pelo gitignore **global** de uma
máquina; em qualquer outro clone um `git add -A` o commitaria — e o arquivo
descreve o que aquele operador autorizou a rodar sem confirmação.

**Auditoria do que foi vendorizado, 2026-08-07, no SHA pinado.** Comportamento
observável dos hooks em JS: **zero** chamadas de rede; **um** `execFileSync`, em
forma argv, sem shell — o argumento que vem do prompt (`--since`) entra como
elemento separado do argv, sem caminho de injeção; escritas confinadas a
`~/.claude/.caveman-*` e aos arquivos de agente do próprio plugin, e só quando
`CAVECREW_*_MODEL` está no ambiente. `caveman-stats.js` **lê os transcripts de
sessão** para calcular economia de token — leitura local, sem rede, mas é o
conteúdo das conversas passando por código de terceiro, e isso fica registrado.
O que **não** foi feito: leitura linha a linha dos ~226 KB de `src/`, e o Python
de `caveman-compress/scripts/` segue fora do ruff (`exclude = ["fixtures",
"vendor"]`) — ele só executa se alguém invocar `/caveman-compress`.

**Revisão de segurança da própria rodada (2026-08-07).** Três candidatos
levantados, cada um verificado por um revisor independente. Dois caíram:

- *Injeção de argumento no `git`* — **falso positivo**. A alegação era que uma
  URL `ext::<comando>` em `PINS.json` executaria no `fetch`. Errada: o git
  classifica `ext` como transporte "scary" e o default de `protocol.ext.allow`
  é **`never`** desde a série de hardening v2.11.1/v2.12. E o cenário assumia
  CI verde, o que também é falso: `pytest` roda em todo PR e
  `test_cada_projeto_declara_repo_sha_e_licenca` já rejeitava `repo` fora de
  `https://github.com/` e `sha` fora de 40 hex.
- *Gate de integridade insuficiente* — **falso positivo**. O caminho descrito
  ("PR malicioso edita um arquivo vendorizado e a linha do manifest") tem o
  mesmo privilégio de editar qualquer `.py` de `sparkforge/`. É a fronteira de
  confiança inerente a vendorizar, não defeito novo.

Um sobreviveu, e era **defeito real em código escrito nesta rodada**:

**Path traversal em `scripts/vendor_caveman.py`.** `materialize()` fazia
`dest / entry["keep"]` e `dest / patch["to"]` sem contenção, seguidos de
`shutil.rmtree`/`copytree`. `Path("vendor") / "/etc/x"` devolve `/etc/x` — o
operador `/` do pathlib **descarta** o lado esquerdo quando o direito é
absoluto, e `..` nunca é normalizado. Um `to` de `../../.claude/settings.json`
num PR de "bump de pin" escreveria fora de `vendor/`, e o CI não veria: ele só
roda `--check`, que nunca lê os campos de caminho do `PINS.json`. Pior:
`actual_manifest()` só varre `VENDOR.rglob`, então o arquivo escrito fora ficava
**invisível para o único gate que o script existe para sustentar**.

Era inconsistência, não decisão: `install_skills.py::install_dest` e
`verify_wheel.py::_artifact_dest` já aplicavam exatamente essa guarda. Corrigido
com `_confinado()` sobre `dest`, `keep`, `patches[].copy` e `patches[].to`, mais
validação de `repo`/`sha` movida para dentro de `clone_at()` — teste não protege
quem roda o script antes da suíte. Verificado por mutação de ponta a ponta: com
o `PINS.json` envenenado, o script recusa com
`` `patches[].to` = '../../.claude/settings.json' contem `..`. Recusado. `` e o
`settings.json` fica intacto.

No mesmo passe, a docstring do módulo foi corrigida: ela dizia que o manifest
"amarra cada byte a um SHA upstream declarado". Não amarra — é regravado a
partir do disco e commitado no mesmo tree. Agora diz o que o gate pega
(divergência acidental) e o que não pega (commit deliberado, cujo controle é a
revisão do diff).

**Limites declarados.** Dois, e os dois são escolha, não pendência:

- **Sem memória entre sessões.** `cavemem` está fora, pelas razões acima. O que
  atravessa sessão continua sendo `.sparkforge/case.yaml`. Reverter significa
  aceitar npm no caminho de quem clona — decisão de produto, não de código.
- **`caveman-shrink` desligado.** Reavaliar só se o catálogo passar a ter
  descrição em inglês. A medição de 2026-08-07 está registrada; reverter sem
  medir de novo é adivinhar.

Créditos e procedência completos: [`vendor/CREDITS.md`](../../vendor/CREDITS.md).

## Expansão agêntica v2 — 30 coordenadores `sf-*`, 20 skills e o runtime que os supervisiona (2026-08-18)

Branch `feat/fase6b-sf-cfg`, quatro commits sobre `3f76768`. **Nenhuma regra
executável, extrator ou fact de diagnóstico mudou.** O catálogo foi de 81 para
116 regras, e as 35 novas são todas `status: structural`: uma por área de
coordenação, sem `requires_facts`, sem `when` e sem `sources`. Elas existem para
que `routing.yaml` tenha um alvo nomeado por área; não julgam nada e não podem
disparar. As 55 executáveis são as mesmas de antes, byte a byte — só
`routing.yaml` foi tocado entre os arquivos de catálogo que já existiam.

**O que entrou de código:** `sparkforge/agents/` (sala de conversa append-only,
supervisor com orçamento, política de modelo, autonomia limitada e observabilidade
opcional) e `sparkforge/tools/` (índice offline verificável por SHA-256,
estimativa de token, avaliação de caso golden, lineage textual e comparação de
JSON Schema). Mais 43 documentos de conhecimento registrados em
`knowledge/offline-manifest.json`.

### Três defeitos achados na revisão de fechamento, e o que foi feito

**1. O default de `Budget` impedia o supervisor de terminar.** `max_rounds`
cobra uma rodada por **fase** e `Supervisor.PHASES` tem sete; o default era `3`.
Reproduzido: `Supervisor(room, [agent], {"a": handler}).run("goal")` voltava
`blocked` / `budget_exhausted` na quarta fase para **qualquer** entrada, sem
nunca chamar `verify`, `synthesize` ou `decide`. O consumidor lia falta de
evidência onde havia orçamento acabando cedo. O único teste do supervisor
forçava `max_tokens=1` e exercitava só o caminho de exaustão de token, por isso
o defeito era invisível. Fechado: o default passou a ser `len(PHASES)`, com a
razão escrita no docstring do módulo, e entrou
`test_supervisor_completes_the_whole_pipeline_with_the_default_budget`.

**2. `sparkforge-tools` era documentado e não existia depois do install.**
`sparkforge/tools/cli.py` anuncia `prog="sparkforge-tools"` e
`docs/agentic-expansion.md` documenta os três subcomandos, mas
`[project.scripts]` só declarava `sparkforge`. Só `python -m sparkforge.tools.cli`
funcionava. Fechado com a entrada no `pyproject.toml`.

**3. O gate da garantia offline existia e não rodava em lugar nenhum.**
`docs/operations-guide.md` lista `scripts/verify_offline_bundle.py` entre os
gates finais; o `ci.yml` não o invocava, e o script ignorava o `--check` que a
documentação manda passar. Manifest e disco podiam divergir sem que nada
acusasse. Fechado: passo próprio no `ci.yml`, `--check` aceito de propósito (o
script não tem outro modo, e recusar o argumento faria a linha documentada
falhar por parsing e não por integridade) e `TestOfflineBundleGate` cobrando o
passo.

**4. O gate de paridade do artefato estava vermelho desde `9474aa8`, nos dois
sistemas operacionais da matriz.** Não é defeito desta branch — chegou por
`main` — mas fechá-la sem consertar seria entregar PR que não pode ficar verde.
`tests/test_fixtures_golden_funcval.py` importa `with_plan_ref` de
`scripts/regen_fixtures.py`, e `scripts/` **não vai no wheel**: é andaime de
teste. O gate roda a suíte de golden de um `cwd` fora do repositório, com
`PYTHONSAFEPATH=1` e `-o pythonpath=`, exatamente para que `import sparkforge`
venha do artefato — e isso tira `scripts/` do `sys.path` junto. A coleta parava
com `ModuleNotFoundError: No module named 'scripts'` antes de qualquer asserção
rodar. Fechado com `tests/conftest.py`, que **acrescenta** a raiz ao fim do
`sys.path` — nunca insere no começo, para que `site-packages` continue vencendo
para `sparkforge`. O que sustenta a honestidade disso não é a ordem, que se
perde em refactor, e sim `tests/test_installed_provenance.py`, que roda no
mesmo processo e falha se o pacote tiver vindo do diretório-fonte. Copiar
`with_plan_ref` para dentro do teste foi recusado pela razão que o docstring
dele já declara: `plan_ref` derivado de dois jeitos diverge em silêncio (D-4c-22).
Medido depois do conserto: 1386 testes passando dentro do venv do gate, `twine
check` PASSED nos dois artefatos.

**5. O manifest offline só era válido no Windows.** Consequência direta de
ligar o gate do item 3: com ele no CI, `ubuntu-latest` reprovou os 43
documentos com a árvore intacta. Os 43 são markdown que o git converte na saída
(`core.autocrlf`), então o mesmo commit tem CRLF no Windows e LF no Linux, e o
hash saía dos **bytes crus** — válido só na máquina onde foi gravado. A
normalização **remove todo CR** em vez de traduzir `CRLF` para `LF`, e isso foi
medido: `knowledge/model-selection-observability.md` tem 25 sequências
`CR CR LF` (blob commitado já com CRLF, convertido de novo no checkout), onde
traduzir devolveria `LF LF` no Windows e `LF` no Linux — o hash voltaria a
depender da plataforma. Os 43 hashes foram regravados pela mesma função que os
confere. O outro lado está travado por teste: as três formas (`LF`, `CRLF`,
`CR CR LF`) verificam contra o mesmo manifest, e um byte injetado continua
reprovando, nomeando o arquivo.

### O lint que a branch introduziu

`ruff check sparkforge scripts tests` acusava **133 erros** em 21 arquivos
novos, todos da expansão — o `ci.yml` roda esse comando, então a branch não
podia fechar verde. A causa era estilo de escrita comprimido no fonte:
`import hashlib, json, re`, `self.repo=Path(repo); self.manifest_path=...` e
corpo de `if` na mesma linha. Corrigido em todos os 21, com a semântica
preservada — o que mudou foi quebra de linha, nome de constante extraída
(`_TERM_RE`, `_S3_RE`, `_TABLE_RE`) e `__all__` explícito em
`sparkforge/tools/__init__.py`, que era o que os `F401` acusavam. Os módulos
sem docstring ganharam um que diz **por que existem**, não o que fazem.

## Fase vNext — Agent Factory, o gate de lastro e a auditoria de 184 alegações — **PARCIAL** (2026-08-21)

`a5b9e96` publicou 17 documentos sob `docs/vnext/` afirmando capacidade e KPIs
que o repositório não sustentava. Este arquivo não citava o commit até agora;
esta seção fecha a lacuna e corrige os números da tabela acima que a auditoria
mediu errados.

### O que `a5b9e96` entregou de fato

Sete pacotes novos de infraestrutura têm teste comportamental real —
`sparkforge/registry` (canonical registry), `sparkforge/economy` (motor de
tiers), `sparkforge/context` (funil de contexto), `sparkforge/adapters/platforms`
(compilador de 7 plataformas), `sparkforge/workflows` (DAG em waves),
`sparkforge/evals` (runner de avaliação) e `sparkforge/observability`
(traces em SQLite) — nomeados assim em `docs/vnext/FINAL-REPORT.md` §6, com os
sete arquivos de teste (`test_canonical_registry.py`,
`test_economy_engine.py`, `test_context_funnel.py`,
`test_platform_compilers.py`, `test_workflows_dag.py`, `test_eval_runner.py`,
`test_observability.py`) presentes em `tests/`.

Oito módulos de domínio, em contraste, são esqueleto: cada um com um teste
entre 17 e 58 linhas.

| Módulo | Linhas | Teste |
|---|---|---|
| `sparkforge/migration` | 150 | `test_migration_glue.py`, 36 linhas |
| `sparkforge/lakeformation` | 218 | `test_lakeformation_engine.py`, 58 linhas |
| `sparkforge/iceberg` | 179 | `test_iceberg_doctor.py`, 36 linhas |
| `sparkforge/errors` | 77 | `test_error_matcher.py`, 26 linhas (compartilhado com `reliability`) |
| `sparkforge/databases` | 127 | `test_database_specialists.py`, 46 linhas (compartilhado com `streaming`) |
| `sparkforge/streaming` | 116 | `test_database_specialists.py`, 46 linhas (compartilhado com `databases`) |
| `sparkforge/terraform` | 144 | `test_terraform_plan_scanner.py`, 29 linhas |
| `sparkforge/reliability` | 95 | `test_error_matcher.py`, 26 linhas (compartilhado com `errors`) |

Para comparação de escala: `sparkforge/adapters` — o pacote pré-existente que
os sete novos compiladores de plataforma estendem — tem **7813** linhas e um
gate de paridade que roda (`tests/test_fixtures_golden_funcval.py` e o passo
de CI descrito na seção de expansão agêntica acima). Os oito módulos de domínio
somados (1106 linhas) não chegam a um sétimo disso, e nenhum tem gate de
paridade equivalente.

Dois pacotes adicionais, `sparkforge/cloud` (58 linhas) e
`sparkforge/providers` (22 linhas), não têm teste nenhum que os importe ou
chame — `docs/vnext/FINAL-REPORT.md` §4 registra isso por escrito e por isso
os exclui do inventário de "Novos Pacotes e Módulos".

### A auditoria: 184 alegações, 48 provadas, 136 removidas

`docs/vnext/claims.lock.json` extraiu 184 alegações numéricas e de capacidade
dos 17 documentos. **48** carregam `state: PROVADA` com prova reproduzível
(comando, artefato ou referência de código); **136** carregam
`state: REMOVIDA`, e o texto correspondente saiu dos documentos — não foi
reescrito, foi apagado, com a razão de cada uma registrada no próprio
`claims.lock.json`. Entre as removidas: a contagem de extratores de facts
(documentos diziam **21**, `sparkforge/facts/*.py` tem **20** — `VNX-042`,
`VNX-057`) e a de catálogos de regras (documentos diziam **52**,
`rules/catalog/*.yaml` tem **51** — `VNX-059`, `VNX-115`). A tabela de KPIs de
economia que `docs/vnext/FINAL-REPORT.md` publicava originalmente (taxa de
sucesso, mediana de tokens, custo por mil tarefas, cache hit rate) não tinha
artefato de medição no repositório — nenhum comando reproduzia nenhum dos dois
lados de nenhuma linha — e foi removida pela mesma razão, não reescrita com
números novos.

### Dois achados que importam além dos números

`docs/vnext/AGENT-CATALOG.md` §2 listava sete "Core Coordinators" — uma
camada permanente de supervisão e roteamento. Nenhum dos sete existe em
`agents/`, o diretório canônico espelhado em `.claude/agents/`,
`.agents/agents/` e `.github/agents/` e verificado por
`tests/test_agents_parity.py::TestMirrors`.

A mesma tabela, §3, tinha seis linhas (`sf-pyspark-specialist`,
`sf-storage-specialist`, `sf-runtime-specialist`, `sf-token-verifier`,
`sf-cost-reviewer`, `sf-security-reviewer`) marcadas "Convertido em Skill
Lazy-Loaded". Nenhum foi convertido: os seis continuam agentes ativos em
`agents/`, roteados de fato em `rules/catalog/routing.yaml` e exercitados por
`tests/test_router_agents.py`. Pior: de duas das seis skills-alvo declaradas
(`data-platform-finops` para `sf-cost-reviewer`, `security-review` para
`sf-security-reviewer`) **nenhuma existe** em `skills/*/SKILL.md` — a
alegação não só descrevia uma migração que não aconteceu, apontava para um
destino que nunca foi criado.

### O gate que impede a reintrodução

`scripts/check_vnext_claims.py` roda contra `docs/vnext/claims.lock.json` e
reprova o commit se um número ou capacidade citado num documento divergir do
que o `state`/`proof` da alegação registra — `python
scripts/check_vnext_claims.py` reporta `0 divergencia(s).` nesta revisão. O
motivo de cada uma das 184 linhas — por que foi provada ou por que foi
removida — vive em `docs/vnext/claims.lock.json`, campo por campo (`state`,
`proof`, `context`), não em prosa solta neste arquivo.

### Status: PARCIAL

Sete pacotes de infraestrutura com comportamento testado não fazem uma
"Agent Factory" — fazem sete pacotes de infraestrutura testados. Os oito
módulos de domínio que dariam à infraestrutura algo de AWS/Spark para
orquestrar são esqueleto (um teste de dezenas de linhas cada, sem gate de
paridade), dois pacotes adicionais não têm teste nenhum, e a documentação que
anunciava o conjunto como pronto tinha 136 alegações sem lastro — quase três
vezes as 48 que se sustentaram. Nada aqui está quebrado ou revertido: o gate
novo impede regressão, e o que ficou provado continua provado. Mas o volume
comparativo (`adapters` 7813 linhas com gate de paridade vs. domínio 1106
linhas sem nenhum) é o oposto do que a versão original do relatório afirmava.
**PARCIAL** é a leitura honesta; **CONCLUÍDA** exigiria que os módulos de
domínio tivessem cobertura e gate na mesma ordem de grandeza da
infraestrutura que os invoca, e isso não foi medido em lugar nenhum porque não
existe ainda.

## Dívidas abertas

A tabela era uma só e misturava **três naturezas**, e a mistura fazia o
inventário inteiro parecer atraso — o roadmap contava duas vezes e decisão
tomada aparecia como conta a pagar. Triada em 2026-08-04, branch
`fix/dividas-triagem`. **O texto de cada linha é o que já estava escrito:**
reclassificar não é reescrever, e nenhuma linha foi apagada. O que a triagem
acrescentou a cada uma é a razão da categoria, no começo da coluna de impacto.

O critério, aplicado item a item:

- **Dívida** — fechar exige **escrever código que ninguém escreveu**, por
  esquecimento ou por adiamento. É o que se deve e se pode pagar.
- **Fase** — fechar exige **executar trabalho planejado**. A linha aponta para
  onde a fase está prevista; chamar isso de dívida faz o roadmap contar duas
  vezes.
- **Limite declarado** — fechar significa **reverter uma decisão registrada**,
  cujo custo já foi medido. A linha diz qual decisão e onde ela está.

Precedente que fundou o critério: a revisão final da 4b mediu que metade de uma
dívida não era dívida — `functional_validation_defined` advisory **é o critério
do spec**, ou seja, sucesso declarado. Essa linha continua sendo a única que se
**parte em duas** aqui, e pela mesma razão: o texto dela já dizia que "as duas
metades envelhecem de formas opostas".

**Contagem de 2026-08-04, na triagem — superada duas vezes abaixo; fica pelo
histórico, e é o que ela conta que importa (o efeito da triagem), não o total:
1 dívida, 4 fases, 7 limites declarados — 12 linhas.** Eram **13
abertas** de 26 quando esta branch abriu; duas fecharam aqui (`requirements` em
`_PRECEDENCE` e a assinatura ausente das skills), e a linha dos gates virou duas
ao se partir. De treze linhas que se liam como atraso, **uma** é dívida de
verdade.

**Contagem ao fechar a fase de perfis de subagente do Devin (2026-08-04) —
também superada, pela contagem da revisão final logo abaixo: 2 dívidas,
4 fases, 10 limites declarados — 16 linhas.** A fase acrescentou quatro, e o
critério de triagem foi aplicado a cada uma na hora de escrevê-la, não depois:
três são **limite declarado** — escolha com custo medido, cujo fechamento é
reverter a decisão ou depender de terceiro —, e uma é **dívida**, porque fechá-la
é escrever código que ninguém escreveu. **O precedente que obriga a isso é a Fase
4a:** ela fechou sem acrescentar uma linha sequer a este inventário — nenhuma das
16 tem "Fase 4a" na coluna de origem —, e a revisão final dela, depois do merge,
mediu **nove** pendências, três das quais mudavam comportamento ou contrato. Fase
que fecha declarando nada a dever não prova que não deve; prova que ninguém
procurou.

**Contagem depois da revisão final da fase de perfis de subagente (2026-08-04): 2 dívidas,
4 fases, 10 limites declarados — 16 linhas abertas, e 19 fechadas.** Superada pela
varredura de completude, logo abaixo; fica como registro. **Abertas
não mudaram de número, e isso é o que a revisão diz sobre a fase:** ela mediu
onze pendências e nenhuma virou dívida nova — quatro fecharam no mesmo dia em
que foram medidas e entraram em *Fechadas* (o órfão de diretório que passava
pelo gate, a fronteira que não alcançava a skill despachada, a regra 9 do
`AGENT_PROTOCOL.md` sem recorte de subagente, e três textos que vendiam a
omissão de `tools:` como fronteira), e as demais eram texto errado em spec,
`README`, `AGENTS.md` e nas quatro superfícies do `playbook`, corrigido no lugar.
Duas linhas abertas **mudaram de tamanho**: a de `tools:` ganhou o argumento que
lhe faltava, e a de `agent:` passou de nove para dez skills sem atribuição.

O precedente vale de novo, agora contra esta revisão: quatro das onze eram
**afirmação de efeito que ninguém mediu** — a mais cara delas dizia que omitir
`tools:` protegia alguma coisa, quando omitir é a opção mais permissiva das
duas. Nenhuma quebrava teste. Fase que fecha verde não prova que está certa;
prova que a suíte olha para onde alguém já olhou.

**Contagem depois da Fase 4c (2026-08-04) — superada pela da Fase 5d, logo
abaixo; e ela contava errado, o que é registro que vale mais que o total.** O
texto dizia "5 dívidas, 3 fases, 14 limites declarados — 22 linhas abertas", e a
contagem das linhas das três tabelas na mesma data dá **6, 3 e 14 — 23 abertas**.
A divergência foi medida ao fechar a Fase 5d, contando as linhas em vez de somar
o que a fase anterior tinha escrito. É o mesmo defeito que este arquivo acusa em
`AGENTS.md`: número copiado envelhece, número medido não.

**Contagem depois da Fase 5d (2026-08-05) — superada pela da revisão final,
logo abaixo: 7 dívidas, 5 fases, 16 limites declarados — 28 linhas abertas, e 25
fechadas.**

**Contagem depois da revisão final da Fase 5d (2026-08-05) — superada pela da
rodada de dívidas abertas, logo abaixo: 8 dívidas, 5 fases, 17 limites
declarados — 30 linhas abertas, e 25 fechadas.** As três parcelas foram obtidas
**contando as linhas das três tabelas**, não somando o que a rodada anterior
escreveu — que é o defeito registrado no parágrafo acima.

**Contagem corrente, depois da rodada de preservação semântica (2026-08-05): 3
dívidas, 8 fases, 23 limites declarados — 34 linhas abertas, e 31 fechadas.**
Contadas **linha a linha** nas três tabelas, com script, e não somando o que a
rodada anterior escreveu. A rodada **não fechou nenhuma linha** e abriu **duas**,
as duas *fase* e as duas medidas antes de escritas: o invariante de eixo de
resultado no `loader`, e a rejeição no `validate`. Nenhuma delas virou dívida, e
a razão está escrita em cada linha — as duas fecham **decidindo um contrato**,
não escrevendo código que alguém esqueceu, e a segunda depende da primeira.

**A contagem da Fase 6a estava errada em duas linhas, e a correção fica aqui em
vez de apagada.** O parágrafo abaixo declarava "21 limites declarados — 30 linhas
abertas", e o cabeçalho da própria tabela já dizia `### Limites declarados (23)`.
Contadas linha a linha na mesma data, são **23**, e o total aberto era **32**, não
30. É o quarto registro deste mesmo defeito neste arquivo, e o mais irônico: a
divergência estava entre o parágrafo e o **título da tabela que ele resume**.

**Contagem anterior, depois da Fase 6a (2026-08-05), como foi escrita — superada
pela de cima, e errada em duas linhas conforme o parágrafo acima: 3 dívidas, 6
fases, 21 limites declarados — 30 linhas abertas, e 31 fechadas.** A Fase 6a **não fechou nenhuma
linha** e abriu cinco: duas dívidas (o kind derivado que faltaria ao extrator de
Terraform, e a fixture do limiar de `checkpointInterval`) e três limites
declarados (jar de outro minor, conf de checkpoint fora do artefato, e o eixo
Python de GraphFrames). As cinco foram medidas **durante** a implementação e
carregam o número na mão; nenhuma é surpresa de revisão. Fase que fecha sem abrir
linha nenhuma normalmente é fase que não olhou.

**Contagem anterior, depois da rodada de dívidas abertas (2026-08-05): 1 dívida,
6 fases, 18 limites declarados — 25 linhas abertas, e 31 fechadas.** Contadas
linha a linha nas três tabelas, pela mesma disciplina. É a maior queda que este
inventário já registrou, e **o que ela conta não é o saldo:** de 8 dívidas, **6
fecharam escrevendo código** e **2 nunca foram dívida** — a triagem de 2026-08-04
classificou as duas errado, e a correção está registrada abaixo em vez de
apagada, pela mesma convenção que a triagem original adotou. Sobra **uma** dívida
aberta, e ela nasceu nesta rodada.

**Duas reclassificações, e as duas foram medidas antes de escritas.** A triagem
que fundou estas tabelas dizia que dívida é o que fecha **escrevendo código**.
`SF-CFG` não fechava assim — fechava **decidindo**, e a decisão exigia uma
medição que ninguém tinha feito; feita agora, ela achou pergunta que nenhuma área
faz, e a linha virou **fase**. `RuntimeContext.emr` do Serverless não fechava
escrevendo código nosso: o caminho alternativo que a linha propunha — "ler a
versão de outra superfície" — **já existia** desde a Fase 5a.2 (commit `8a7d506`,
2026-08-01), quatro dias antes de a linha ser escrita, e exercitá-lo mostra que
ele **não fecha o título dela** — enche `spark` e o eixo `emr` continua vazio. O
que falta é a AWS publicar a matriz, e depender de terceiro é a assinatura de
**limite declarado**. Nenhum dos dois textos foi
reescrito: cada um ganhou a razão da nova categoria no começo da coluna de
impacto, que é o que a triagem original fez com as treze linhas dela.

**O que a rodada moveu, e a direção importa mais que o saldo.** Seis linhas
fecharam com código e teste, duas mudaram de tabela sem mudar de texto, e **uma
nasceu** — `judge --emr` gravando versão de EC2 sobre facts de Serverless. Ela é
subproduto direto de fechar as outras: foi medida enquanto se conferia o que o
caminho alternativo do Serverless realmente enche. Rodada de pagamento de dívida
que fecha sem abrir nada normalmente é rodada que só olhou para a lista.

**O que a Fase 5d moveu.** Nenhuma linha fechou, e uma **encolheu pela metade**:
"EMR Serverless e EMR on EKS" passou a nomear só EKS. Em troca a fase abriu
quatro — uma dívida (`RuntimeContext.emr` a partir de Serverless), uma fase (job
runs e `billedResourceUtilization`), uma fase dependente daquela (pré-init
subdimensionada) e dois limites declarados (julgar `architecture`, e o
`StartJobRun` que sobrepõe o que a application declara). Todas as cinco foram
medidas durante a implementação e carregam o número na mão; nenhuma é surpresa
de revisão.

**O que a Fase 4c moveu, e a direção importa mais que o saldo.** Uma linha
**fechou** — a metade `functional_validation_defined` da linha de gates advisory,
que a 4b tinha registrado como fase e que fechou exatamente como previsto,
declarando dado e sem tocar em Python. Uma linha de fase **encolheu**: os quatro
itens de rigor da §16 acabaram, e a linha de roadmap ficou só com 3b, 3c e 3d.
Em troca, a fase abriu **três dívidas e duas linhas de limite declarado**, e
nenhuma delas é surpresa — as cinco foram medidas durante a implementação e
carregam o número na mão. Fase que fecha sem abrir linha nenhuma normalmente é
fase que não olhou; o que vale conferir é se o que abriu tem custo escrito, e
tem.

**Contagem anterior, da varredura de completude do Devin (2026-08-04): 2 dívidas,
4 fases, 12 limites declarados — 18 linhas abertas, e 24 fechadas.**
**As dívidas não mudaram de número, e os limites subiram dois** — e é isso que a varredura
diz sobre a revisão que veio antes dela: dos seis candidatos medidos, **um estava certo e
sem guarda** (a instalação), **três fecharam no mesmo dia** (o gate de nome reservado, o
procedimento de MCP no Devin, e o registro da escolha de `.agents/` sobre `.devin/`), **um
virou limite declarado** (`max-nesting`) e **um já era dívida registrada** (a watchlist).
O sexto par de olhos é o que separa "a fase fechou" de "não sobrou nada": as três coisas
que a varredura livre achou não estavam em candidato nenhum, nenhuma quebrava teste, e
todas eram texto que a própria pesquisa já tinha derrubado — sobrevivendo num `.py`, num
docstring de teste e num arquivo da raiz, três lugares onde ninguém foi procurar.

### Dívidas (5)

Fechar exige escrever código. Nada aqui espera fase nem depende de reverter
decisão. **A tabela tinha oito linhas em 2026-08-05, caiu para uma no mesmo dia
e a Fase 6a a devolveu para três.** Seis fecharam na rodada de dívidas abertas,
escrevendo código e teste — ver a seção própria acima e as seis primeiras linhas
de *Fechadas*. Duas nunca foram dívida, e a triagem de 2026-08-04 as classificou
errado: `SF-CFG` desceu para *Fases* e `RuntimeContext.emr` para *Limites
declarados*, com a medição que reclassifica escrita na linha e o texto antigo
preservado embaixo. As duas que subiram são da própria Fase 6a, e as duas foram
medidas ao escrever a área — não descobertas depois.

**Nenhuma das três é herdada**, e é isso que este inventário pede de dívida: o
custo foi medido na hora, o conserto é código nosso, e nada precisa ser desfeito
para pagá-las. **Tabela curta não é motivo de comemoração e sim de suspeita** —
o precedente da Fase 4a vale aqui inteiro: fase que fecha declarando nada a dever
não prova que não deve, prova que ninguém procurou. A revisão final da 6a é a
prova disso pelo lado que dói: ela achou uma P0 que acusava código correto em
quatro formas, dois `same_subject` apagáveis com a suíte verde e cinco áreas sem
coordenador — nenhuma das três estava em candidato nenhum, e as três fecharam
com teste. O que sustenta este número é o teste que ficou para trás, não a prosa.

| Dívida | Origem | Impacto |
|---|---|---|
| `judge --emr` sobre facts de EMR Serverless grava versão de EC2 num artefato que não a declara | rodada de dívidas abertas, 2026-08-05, medida ao conferir o que o caminho alternativo do Serverless realmente enche | **Dívida, e a única aberta — fechar é escrever código, e ninguém escreveu.** Medido, reproduzível numa linha: `sparkforge judge --facts fixtures/emr_serverless/app_saudavel/expected/facts.json --emr 7.5.0` grava no contexto `{"emr": "7.5.0", "spark": "3.5.2-amzn-1", "python": "3.9", "iceberg": "1.6.1-amzn-1", "detected_from": ["cli"]}`, tudo derivado da `EMR_MATRIX` — **que é de EMR on EC2**. O conjunto de facts não tem um único fact de EC2: são cinco kinds `emrs.*`, todos de `get-application`. **Onde está o número certo:** `knowledge/emr-serverless/runtime-matrix.md:47` mede que `emr-7.5.0` no Serverless publica **`3.5.2`, sem o sufixo do fork**, e a §1 da mesma página (`knowledge/emr-serverless/runtime-matrix.md:30-31`) mede que o sufixo `-amzn-N` **não existe na fonte do Serverless** e que **três das quatro colunas da `EMR_MATRIX` não têm fonte nenhuma do lado do Serverless**. Ou seja: `spark` sai com um sufixo que a fonte não publica, e `python` e `iceberg` saem **inteiros do nada** — não é um campo com ruído, são três campos inventados sobre um artefato que não declara nenhum deles. **Nada no motor impede**, e o custo é do pior tipo: versão errada no contexto invalida toda recomendação versionada que vier depois, e o operador não tem como distinguir um eixo derivado de um eixo lido. É **dívida e não limite** porque o conserto é código nosso e há mais de uma forma de escrevê-lo: recusar `--emr` quando o conjunto tem fact `emrs.*`, avisar e marcar os eixos como derivados de matriz alheia, ou derivar da tabela do Serverless para o componente que ela publica e deixar vazio o que ela não publica. **Escolher entre as três é a decisão; nenhuma delas depende de terceiro.** Nenhum teste cobre a combinação hoje — `--emr` é exercitado com facts de EC2, e o Serverless é exercitado sem `--emr`. |
| Nenhuma regra consegue dizer "o IaC não declarou o jar de GraphFrames" — falta `absent` filtrado por atributo, e o kind derivado que o substituiria | Fase 6a, veto `V-GR-1` no cabeçalho de `rules/catalog/graph.yaml`, medido ao escrever a regra que a §5 do spec previa | **Dívida — fechar é escrever código, e ninguém escreveu.** Medido: `engine._absent_satisfied` (`rules/engine.py:68-70`) compara **só `kind`**, e o kind é `tf.attribute` dos dois lados do par de fixtures — o que muda é `attrs.key`. Não existe `absent` filtrado por atributo nem `where` negado, então `absent: tf.attribute` seria falso para todo Terraform lido, e a regra acusaria **todo** job de grafo, inclusive quem declarou o jar. **O que fecharia** é um kind derivado no extrator de Terraform, no molde exato de `tf.observability.spark_ui`: o extrator decide uma vez e emite o kind já decidido, e a regra fica com `absent:` sobre ele. É código nosso, tem precedente no próprio repositório e não depende de terceiro. **O que NÃO fecha com ele** está na linha de *Limites declarados* sobre jar de outro minor: a metade **exculpatória** — tratar um `--extra-jars` como resolução — continua vetada na faixa 3.3 mesmo com o kind escrito, e as duas metades envelhecem de formas opostas. O par de fixtures `import_sem_jar_no_iac` × `import_com_jar_declarado` já existe, compartilha o `.py` byte a byte e difere só no `--extra-jars`: o corpus para a regra está pronto, o mecanismo é que não. |
| `checkpointInterval > 2` tem fonte primária e limiar apurados, e nenhuma fixture o exercita | Fase 6a, veto `V-GR-2` no cabeçalho de `rules/catalog/graph.yaml`, medido contra as 25 fixtures | **Dívida — fechar é escrever corpus, e ninguém escreveu.** É o **único limiar numérico com fonte primária** desta área: `graphframes-api.md` §6 traz o aviso citável (o código adverte em `value <= 0 || value > 2`), e a §4.3.2 autoriza explicitamente "outra regra, com severidade menor". O que falta é golden positivo: o caso `> 2` **não tem fixture nenhuma**, e regra sem ele reprova `test_every_rule_has_a_fixture_that_fires_it`. O caso `<= 0` tem fixture, mas é `saida_intervalo_nao_positivo`, que o próprio `meta.yaml` declara "segunda forma de escrever certo" e que é uma das **cinco** saídas legítimas de `V-GF-1` — acusar o artefato que o corpus declara correto faria o relatório dizer as duas coisas ao mesmo tempo. **Fechar é uma fixture com `checkpointInterval` acima de 2 e um `<= 0` que não seja também saída legítima**, mais a regra. Nada a reverter, nada a esperar de terceiro. |
| O gate de golden deixou de cobrar as regras `status: structural`, e nada impede que uma regra de detecção real seja marcada assim | expansão agêntica v2, 2026-08-18, medida ao revisar a branch | `tests/test_fixtures_kind_coverage.py` passou a filtrar por `_executable_rules()` para acomodar as 35 áreas de coordenação, que não julgam nada e não podem disparar. A mudança está certa para o que ela acomoda e **abriu uma porta**: `status` é campo livre do YAML, e uma regra com `when` de verdade marcada `structural` sai do gate de fixture, do gate de ramo de severidade e das duas asserções de área muda dos testes ponta a ponta — quatro redes de uma vez, com a suíte verde. Fechar é escrever o invariante que falta: `structural` **exige** `when: {all: []}`, `requires_facts: []` e `sources: []`, e qualquer regra com condição real que se declare `structural` derruba o teste. Não foi escrito nesta branch porque o conjunto de arquivos dela já era o da expansão |
| `RELACAO_MEDIDA` em `tests/test_sync_render.py` é redefinido por um `update()` no meio do arquivo, e seis chaves ficam com valor morto | expansão agêntica v2, 2026-08-18, medida ao corrigir o lint do arquivo | O dicionário é declarado com as vinte skills e, ~60 linhas abaixo, um `RELACAO_MEDIDA.update({...})` sobrescreve seis entradas (`agentic-orchestration`, `token-efficient-agent`, `tool-specialist-routing`, `analyze-analytics`, `analyze-functional-rules`, `optimize-athena-queries`). O teste que consome lê só o valor final, então o primeiro valor das seis **nunca é exercitado** — quem editar a entrada de cima acha que mudou o teste e não mudou nada. Não é defeito de produto e por isso não bloqueou a branch; é armadilha de manutenção num arquivo cuja função é justamente ser a medida. Fechar é fundir o `update()` na declaração |

### Fases (8)

Trabalho planejado. A coluna de impacto abre dizendo **onde a fase está
prevista** — e **três** delas registram que a sua ainda não tem posição na fila.

**A sexta chegou por reclassificação, não por trabalho novo.** `SF-CFG` estava em
*Dívidas* desde a revisão de documentação de 2026-08-04, com o texto dizendo em voz
alta que ninguém tinha medido se ela devia morrer por escrito ou virar fase. A
medição foi feita em 2026-08-05 e deu fase: existe pergunta de configuração que
nenhuma das três áreas dispersas faz, e o motor recomenda uma propriedade `spark.*`
em cinco regras sem nunca ler se ela está ligada. **Ela é a linha mais antiga do
inventário** — declarada no primeiro commit de `rules/catalog/README.md` — e agora
também a que carrega o buraco medido de extrator, escrito na própria linha.

| Trabalho | Origem | Onde está previsto, e o impacto |
|---|---|---|
| Fases 3b, 3c e 3d não iniciadas | §16 do spec da Fase 0 | **Fase, não dívida.** Fechar as três é executar trabalho que já tem lugar na seção *Ordem*; contá-las aqui fazia o roadmap contar duas vezes. **A linha encolheu com a Fase 4c:** ela dizia também "a Fase 4 do roadmap (§16, rigor) está em **um quarto** item aberto", e esse item era a validação funcional automatizada — fechada, com os quatro de rigor completos (benchmark 4a, gates fail-closed e assinatura 4b, validação funcional 4c). A Fase 4 executada (coordenadores, executores e `playbook`) é numeração diferente — ver a nota "Atenção ao nome" na seção própria — e está **concluída** |
| Great Expectations declarativo e dbt seguem sem cobertura | Fase 5c, por decisão registrada na §2 do spec | **Fase, e a própria linha já dizia:** "as duas entram em fase própria, agora que os kinds `dq.*` existem para receber o resultado". A linha estava certa e no lugar errado. `great_expectations.yml` e as expectation suites em JSON são artefato declarativo **fora do código**, com parser próprio, e correlacionar suíte com a tabela que o job escreve exige casar por nome — heurística frágil, que produziria `SF-DQ-001` sobre um alvo adivinhado. dbt é mundo próprio e encosta no Spark só via `dbt-glue`/`dbt-spark`. As duas entram em fase própria, agora que os kinds `dq.*` existem para receber o resultado. Fora de escopo pela mesma razão: **resultado de execução** (`VerificationResult`, validation result do GE, `run_results.json` do dbt) — a ferramenta já disse que o check falhou, e repetir isso não acrescenta garantia nenhuma |
| **EMR on EKS** sem cobertura | Fase 5b, por decisão registrada no spec; **a metade Serverless da linha fechou** com a Fase 5d, em 2026-08-05 | **Fase, sem posição na *Ordem*** — e o "**única**" que esta linha dizia até 2026-08-05 estava **errado desde a própria Fase 5d**, que abriu a linha de job runs também sem posição; com `SF-CFG` são **três**, contadas nesta tabela. Corrigido no lugar, que é o que este arquivo faz com afirmação que a medição derruba. A linha dizia "EMR Serverless e EMR on EKS" e perdeu a primeira metade: `SF-EMRS` tem extrator, seis kinds, 16 fixtures, seis regras e coordenador. O que sobra é EKS, e ele não é o mesmo tamanho de trabalho: traz vocabulário de Kubernetes — virtual cluster, container provider, namespace, pod template — que não existe em lugar nenhum do repositório, e `knowledge/` continua com **zero** linha sobre ele. Enfileirá-lo é decisão de roadmap, e esta triagem não a toma por conta própria: registra que ele está fora da fila. |
| Job runs e `billedResourceUtilization` do EMR Serverless | Fase 5d, não-objetivo registrado na §2 do spec | **Fase, não dívida — é eixo novo, não código faltando.** `get-application` descreve **definição**; `get-job-run`/`list-job-runs` descrevem **execução**, e uma application tem N runs, o que obriga a decidir amostragem, agregação e "qual run é representativo" — classe de decisão que o eixo de configuração não tem. `billedResourceUtilization` é a evidência de custo mais direta que a AWS expõe em qualquer serviço deste repositório, e por isso merece fase que a trate com cuidado, não apêndice da 5d. Sem posição na *Ordem*. |
| Pré-init subdimensionada não é acusável | Fase 5d, veto registrado no cabeçalho de `rules/catalog/emr-serverless.yaml` (`D-5d-33`) | **Fase, e é a primeira consumidora concreta da linha acima — não fecha sozinha.** É o veto mais doloroso da 5d justamente porque a fonte descreve o defeito com precisão: *"the initial capacity memory configuration should be greater than the memory that the job and the overhead request"*. O que falta não é regra nem extrator: é **o outro lado da comparação**, que mora no `StartJobRun` e que esta fase não lê. Uma regra que só acusasse quando o job declara a memória na própria application produziria silêncio exatamente onde a prática comum está — pior que não ter regra, porque o silêncio se lê como aprovação. Fechar exige o eixo de job runs; escrever a regra antes dele é impossível com a informação que o artefato de definição carrega. |
| A área `SF-CFG` foi **planejada e nunca escrita** | **Pré-existente**: declarada no primeiro commit de `rules/catalog/README.md` (`ffcf150`) e nunca implementada; medida na revisão de documentação de 2026-08-04 | **Reclassificada em 2026-08-05, de dívida para fase: a medição que a própria linha exigia foi feita, e ela achou pergunta que nenhuma área faz.** A linha dizia "ninguém mediu qual dos dois é"; medido agora, é o segundo. (1) `knowledge/spark/config-reference.md` documenta **28** propriedades `spark.*` com default exato, em quatro tabelas — **35** contando as outras páginas de `knowledge/` —, e **nenhuma delas é lida por regra nenhuma**. (2) Das 81 regras, **12** tocam superfície de configuração, e o recorte delas é o argumento: **três** leem uma chave nomeada de um bloco `Configurations` do EMR (`SF-EMR-001` lê `maximizeResourceAllocation`, `SF-EMR-003` lê `spark.dynamicAllocation.enabled`, `SF-EMR-005` lê `spark.sql.sources.partitionOverwriteMode`) — e só **duas** dessas nomeiam uma propriedade `spark.*`; **três** leem qualquer chave, e só para caçar segredo (`SF-EMR-002`, `SF-EMRS-002`, `SF-GLUE-006`); **cinco** nomeiam argumento de job Glue ou atributo de recurso Terraform (`SF-ENV-003`, `SF-GLUE-001`, `SF-GLUE-003`, `SF-GLUE-004`, `SF-GLUE-005`); e **uma** ignora a chave por completo (`SF-PY-012`, cujo `when` é `{fact: pyspark.conf_set}` e mais nada). **Zero regras fora da área EMR leem uma propriedade `spark.*` nomeada.** (3) O sintoma, e ele é literal: **cinco** regras recomendam `spark.sql.adaptive.enabled` no `proposed_change` — `SF-PQ-001`, `SF-PY-005`, `SF-PY-009`, `SF-PY-010` e `SF-UI-006` — e **nenhuma regra do catálogo lê se ela está ligada**. (4) O dado já está no repositório, com procedência: os goldens de `fixtures/emr/` carregam **36** facts `emr.configuration`, os 36 com `provenance` e `artifact_sha256`, cobrindo **cinco** propriedades `spark.*` distintas — e **três delas** (`spark.sql.shuffle.partitions`, `spark.executor.memory`, `spark.executor.instances`) **têm zero consumidores**. Fact extraído, hasheado, versionado em golden, e que nenhuma regra pergunta. (5) Dois buracos de extrator, e os dois medidos. `--conf` não é desmontado: em `fixtures/terraform/unresolvable_values/input/job.tf:21` ele chega num heredoc do Terraform, vira um `tf.unresolved` com `reason: heredoc`, e as duas propriedades de dentro somem — uma delas é `spark.sql.adaptive.enabled=true`, exatamente a que cinco regras recomendam ligar. E o event log **não** emite `SparkListenerEnvironmentUpdate` (`sparkforge/facts/event_log.py:485-486` o lista entre os eventos ignorados de propósito): **a configuração efetivamente aplicada num run não é lida por superfície nenhuma**. **Portanto ela não morre por escrito.** Existe pergunta de configuração que nenhuma das três áreas faz, e responder a ela é trabalho de fase: decidir se o eixo vira área própria ou extensão das existentes, fechar os dois buracos de extrator, e resolver o problema que o próprio `config-reference.md` declara no cabeçalho — default documentado não é valor efetivo, e o Glue sobrescreve parte deles. **Ela não tem posição na *Ordem***, do mesmo jeito que a linha do EMR Serverless não teve até esta semana, e enfileirá-la é decisão de roadmap que esta rodada não toma. **A leitura anterior, da triagem de 2026-08-04, fica abaixo inteira — reclassificar não é reescrever:** **Dívida, e a mais antiga do inventário — nada a reverter, só decidir.** O `README.md` do catálogo declarava a área `CFG` (config Spark) e o arquivo `spark-config.yaml` desde o dia em que foi escrito. Medido: `git log --diff-filter=A -- rules/catalog/spark-config.yaml` não devolve **nada** — o arquivo nunca existiu em commit nenhum —, e `SF-CFG` não aparece em nenhum `.yaml`, `.py` ou teste do repositório. A tabela listava **15** arquivos para **14** reais e implicava **14** áreas contra **13** medidas; as duas linhas foram removidas, e a contagem de áreas passou a ser declarada por escrito (**treze**) para que a próxima divergência apareça. **O que fica em aberto é a decisão, não o texto:** configuração de Spark hoje é julgada de forma dispersa — `pyspark.conf_set` alimenta regras de `SF-PY`, e a configuração declarada em IaC alimenta `SF-GLUE` e `SF-EMR` (que carrega `Configurations` em dois níveis). Ou isso é reconhecido como a resposta definitiva e a `CFG` morre por escrito, ou existe uma pergunta de configuração que nenhuma das três áreas faz e aí ela vira fase. **Ninguém mediu qual dos dois é**, e é essa medição — não código — que fecha esta linha |
| O eixo de resultado é cobrado por **texto**, e o `loader` não o exige de nenhuma regra | rodada de preservação semântica, 2026-08-05, medido ao decidir o escopo | **Fase, e ela depende de uma decisão de contrato, não de código.** O que fecharia é um invariante de carga: toda regra que pode mudar o resultado carrega eixo de resultado no `validation`. **O custo medido, e é ele que tira isto de dívida:** a classificação "pode mudar o resultado" **não está no dado**. Das 81 regras, **62** já carregam o eixo e **19** não — e as 19 estão certas: são segredo (`SF-EMR-002`, `SF-EMRS-002`, `SF-GLUE-006`), destino de log (`SF-EMR-006`, `SF-EMRS-003`, `SF-EMRS-004`, `SF-GLUE-002`), capacidade (`SF-EMR-004`, `SF-EMRS-005`, `SF-GLUE-001`, `SF-GLUE-005`), detecção de runtime (as cinco `SF-ENV`) e metodologia (`SF-PLAN-004`, `SF-UI-002`). Um invariante "todas as regras" reprovaria as 19 corretas; um invariante seletivo exige um **campo declarado por regra** — os 18 campos de regra hoje (`load_catalog()`) não têm nenhum que sirva de gatilho —, e campo novo no contrato de regra é bump de `schema_version`, cujo preço este arquivo declara no cabeçalho: um Finding gravado com `catalog_version: 2` sugere que o limiar que o julgou é outro. São **81** decisões escritas à mão, e cada uma é exatamente a linha *fato versus julgamento* que este repositório traça. **O que existe hoje, e é o piso, não o teto:** `tests/test_rules_result_axis.py` pergunta ao `proposed_change` quais regras trocam a implementação que produz o valor — **7** regras — e cobra o eixo de cada uma, mais os invariantes específicos da `SF-PY-009`. Ele pega a regra que **cala**, que era o estado medido, e não a que fala pouco. Sem posição na *Ordem*. |
| `validate_output` não rejeita recomendação sem referência de validação funcional, como rejeita ganho sem `benchmark_ref` | rodada de preservação semântica, 2026-08-05, medido ao decidir o escopo | **Fase, e ela vem DEPOIS da linha acima — as duas não são paralelas, e essa ordem é o achado.** O molde existe e funciona: `benchmark_ref` cita o `fact_id` de um `bench.run_delta`, e `validate.py` (**116** linhas, **8** menções ao campo) o cobra em duas camadas, forma e pertinência. Um `funcval_ref` citando o `fact_id` de um `funcval.plan` seria a simetria. **O custo medido tem duas parcelas, e a segunda é a que manda.** (1) Campo novo em `findings/models.py` é bump de `schema_version` do contrato de findings, e **113** findings golden em **90** fixtures passariam a ser gravados sob um contrato que os anteriores não declaram. (2) **O gatilho não existe, e é por isso que a ordem importa:** `benchmark_ref` só é exigido quando `expected_effect` é quantificado — um gatilho que **está no próprio finding** e não precisa de julgamento. Não há equivalente para o eixo do dado: "esta recomendação pode mudar o resultado" é precisamente a classificação que a linha acima mede como ausente do catálogo. Sem ela, a rejeição só teria duas formas, e as duas são piores que o texto: exigir de **todas** as recomendações, o que faria o campo virar ritual preenchido para passar — o defeito que a Fase 4a mediu no `benchmark_ref` de texto livre —, ou exigir de nenhuma. **Fechar esta linha é decidir o gatilho, e o gatilho é a fase de cima.** Sem posição na *Ordem*. |

### Limites declarados (23)

Decisão tomada com o custo registrado. "Fechar" cada uma destas significa
**reverter** a decisão que a criou — e a coluna de impacto abre nomeando qual.
Sete linhas que pareciam atraso e são, em todos os casos, escolha com motivo
escrito. Três entraram com a fase de perfis de subagente do Devin, e têm uma
propriedade que as anteriores não têm: em duas delas o gatilho de reabertura
**não é nosso** — é a Cognition documentar o que hoje não documenta, ou deixar de
marcar como experimental o que hoje marca. As **duas últimas** entraram com a
Fase 4c, e são de uma espécie que nenhuma das doze anteriores tinha: elas não
limitam o que o motor **consegue** fazer, e sim o que a saída dele **pode
afirmar**. As duas já estão declaradas dentro do produto, não só aqui — que é a
diferença entre limite declarado e limite que alguém descobre no uso.

**As duas últimas entraram na revisão final da Fase 6a (2026-08-05), e as duas
são do mesmo tipo raro: o limite já existia e estava mal declarado, ou não estava
declarado em lugar nenhum.** O vocabulário por nome desta área declarava o preço
dos dois níveis no **fact** e calava sobre o achado que sai dele — meio preço
escrito é pior que preço nenhum, porque parece completo. E o `same_subject` de
`SF-GRAPH-003`/`004` prometia um achado por construção, quando a chave de
agrupamento do motor é `subject.symbol`, que aqui é a **função**. Nenhuma das duas
fecha dentro desta área: a primeira é reverter uma das duas escolhas de
vocabulário, a segunda é mexer numa chave que vale para as quinze áreas de uma vez.

**A décima oitava chegou por reclassificação em 2026-08-05, e é a única desta
tabela que começou como dívida.** `RuntimeContext.emr` a partir de artefato de EMR
Serverless estava em *Dívidas* porque a linha afirmava existir caminho alternativo.
O caminho existe e foi exercitado — e ele enche `spark`, deixando `emr` vazio, que
é exatamente o que o título da linha diz. Fechar depende da AWS publicar a matriz,
e **gatilho de reabertura que não é nosso** é o critério desta tabela. Ela entra
com um contexto que as outras dezessete não têm: **hoje o eixo que ela limita não
porteia regra nenhuma**, e isso está medido na linha em vez de presumido.

**A décima sétima entrou na revisão final da Fase 5d (2026-08-05) e é de uma
espécie que nenhuma das dezesseis anteriores tinha: o limite existia e o produto
o NEGAVA por escrito.** A anotação `EMR.secret@` é bypass incondicional da
heurística de segredo, e a docstring do extrator afirmava, sem qualificação, que
o valor casado nunca é escrito. As demais linhas desta tabela registram decisão
tomada; esta registra prosa corrigida — e é por isso que ela vale mais lida que
contada.

| Limite | Origem | Qual decisão o fecha, e o impacto |
|---|---|---|
| Os quatro eixos de `SF-FVAL` são **proxies**, e não provam que o dado é o mesmo | Fase 4c, §3 do spec e critério 8 da §9 | **Limite declarado, e é o limite da área inteira.** Contagem, schema, chaves e agregados iguais **não** provam que o dado é o mesmo: duas linhas podem trocar valores entre si e os quatro passam. A área afirma "nenhum dos quatro proxies detectou divergência", **nunca** "o resultado é idêntico", e a distinção não é retórica — é a diferença entre uma aprovação e a ausência de uma reprovação. **Fechar é reverter a decisão de não comparar linha a linha**, que é a afirmação forte e é inviável sobre volume real: é justamente por isso que os quatro existem. O que foi feito em vez de fechar é declarar o limite **três vezes, de propósito** — no cabeçalho de `rules/catalog/funcval.yaml`, na `explanation` de cada uma das cinco regras, e na saída do comparador (`funcval.analyzed.attrs.proxy_limit`) —, para que quem lê "os quatro proxies bateram" nunca precise vir ao YAML descobrir o que isso não prova. É a mesma disciplina de `dq.unresolved` e `bench.unresolved`: o que o motor não sabe fica **dito**, e não vira silêncio que o leitor interpreta como aprovação |
| Chave declarada errada produz **P0 sobre dado correto** | Fase 4c, consequência da D-4c-2, medida ao desenhar o eixo | **Limite declarado, e não é dívida — não há código que o conserte.** Nenhum dos 118 kinds nomeia chave de negócio (varredura dos 19 extratores), então o eixo de chaves só existe se alguém o **declarar** em `funcval plan --key`. Quem declara, responde: `--key cliente_id` numa tabela de itens de pedido faz `SF-FVAL-003` acusar duplicata sobre dado perfeitamente correto, em **P0**. O motor não tem como saber — e a alternativa que pareceria segura foi **medida e rejeitada**: usar partição como proxy de chave, que na fixture `catalog/glue_table_schema` daria `distinct_values = partition_count = 1200` sobre `dt` para `db.eventos`, ou seja, um check de unicidade acusando dado correto **sem** ninguém ter declarado nada. Trocar erro do operador por erro do motor não é melhoria. **Fechar exige dado que não existe**: uma declaração de chave primária de negócio por tabela, que nem o Glue Data Catalog nem o Iceberg carregam de forma confiável. O que foi feito é tornar a procedência **legível**: todo check sai com `origin` (`declared` com `derived_from: []`, ou `derived` com o `fact_id`), e sem `--key` o plano escreve `undeclared_axes: ["keys"]` **com a razão**, em vez de calar. Quem lê um `SF-FVAL-003` consegue saber, do próprio plano, se a chave que o produziu foi derivada ou afirmada |
| **Um** dos quatro gates segue advisory mesmo sob `strict_gates` — `dominant_bottleneck_identified` | Fase 4b, por decisão registrada na §1 do spec; a outra metade **fechou** com a Fase 4c e está no registro de fechadas | **Limite declarado, e agora ele é de um gate só.** Medido no bloco `gates` de `rules/catalog/routing.yaml`: dos quatro gates, **três** têm `satisfied_by` — `baseline_captured` ← `bench.run_delta`, `flows_mapped` ← `callgraph.reachable_spark_work` e `functional_validation_defined` ← `funcval.plan`, este último desde a Fase 4c. Sobra **um** sem produtor, e gate sem produtor **nunca** entra na lista de bloqueio — é o critério da fase, não uma omissão. `dominant_bottleneck_identified` **não tem caminho previsto**: dominância é ordenação entre candidatos, nenhum dos 118 kinds a afirma, e o que mais se aproxima é um Finding — que não é Fact, mora em `findings_index` e não chega a `set_phase`. Endurecê-lo exigiria **reverter uma decisão da Fase 0**: ou um kind que declare dominância (e aí a evidência passaria a carregar julgamento, contra o contrato) ou fazer `set_phase` ler findings (outra camada). Fica advisory com `advisory_reason` escrito no catálogo, e é a linha honesta a manter |
| O gate confere presença de kind, nunca conteúdo de fact — e **nenhum benchmark destrava** | Fase 4b, limite declarado em três lugares; **remedida** na revisão final e ampliada | **Limite declarado.** A alternativa que fecharia — passar facts inteiros ao gate — **segue recusada pelos dois motivos originais**, e o que foi feito no lugar foi declarar o recorte em três pontos do produto. Fechar é reverter essa recusa e construir duas capacidades que hoje não existem em verbo nenhum. `_gates_blocking` pergunta se o kind está no conjunto de kinds; ele **não** pergunta se o `bench.run_delta` é do job certo, se os dois lados do benchmark são o mesmo job, nem se o `callgraph.reachable_spark_work` cobre todo o `scope.entrypoints`. **A versão anterior desta linha dizia "um benchmark de outro job destrava", e subdimensionava o custo por uma ordem de grandeza.** Medido: **duas linhas de JSON escritas à mão** — `{"kind": "bench.run_delta", "subject": {}, "measures": {}, "attrs": {}, "provenance": {}}` e a irmã com `callgraph.reachable_spark_work` — levam um case com `strict_gates: true` de `intake` a `report` com rc=0. Não é preciso benchmark nenhum, nem job nenhum, nem execução nenhuma: `provenance` vazia passa, porque **nada a valida** — `_fact_kinds_for_gates` projeta `{fact.kind for fact in ...}` e descarta o resto. O custo de contornar o rigor saiu de uma flag (`--gate-value true`, que o D-4b-2 fechou) para um arquivo, e um arquivo é mais barato do que a redação sugeria. A alternativa — passar facts inteiros — segue recusada pelos dois motivos originais: puxaria o índice de facts para dentro do `store`, e faria o gate precisar saber o que é "o job certo", que é julgamento. **O que foi feito em vez de fechar:** declarar o recorte onde ele opera — bloco `gates` do `routing.yaml`, docstring de `set_phase`, mensagem de bloqueio. Fechar de verdade exige duas capacidades novas e independentes: validar `provenance` (que hoje nenhum verbo faz, em nenhum kind) e correlacionar `scope` com o conteúdo dos facts |
| `report verify` não isola o corpo com autoridade | Fase 4b, desvio D-4b-14, medido ao implementar | **Limite declarado.** Fechar exige assinar o bloco junto (recursivo) ou mover a declaração para um arquivo lateral assinado — e o segundo é exatamente o modo de falha de handoff que o **D-4b-14 recusou**, três arquivos no lugar de um. A assinatura é um hash único das três partes **de então**; não há como recomputá-las em separado a partir dele. A isolação que o critério 8 do spec pede vem de o **bloco declarar** o que foi assinado — e o bloco mora fora do hash por construção, logo é editável por quem editar o relatório. Consequência: `checks.body` não distingue "o corpo foi editado" de "o próprio bloco foi", e a saída enuncia as duas leituras em vez de escolher a que não pode provar. O veredito `valid` é preservado porque **nunca** sai do bloco: sai das três checagens juntas, e um bloco adulterado para fechar com o corpo passa a divergir dos findings reais. Fechar exigiria assinar o bloco junto (recursivo) ou mover a declaração para um arquivo lateral assinado — nenhum dos dois foi feito, e o segundo trocaria um arquivo por dois, que é o modo de falha de handoff que este projeto evita. **Uma das três atribuições saiu desta ambiguidade na revisão final** (desvio D-4b-24): a versão da assinatura agora é declarada no bloco, e relatório de versão anterior sai como `version_mismatch` em vez de "corpo editado" |
| `verify` não sabe verificar o corpo de um relatório assinado sob outra `SIGNATURE_VERSION` | Fase 4b, desvio D-4b-24, medido ao fechar a revisão final | **Limite declarado, e esta linha é a declaração que o D-4b-24 disse faltar.** O suporte é de **uma** normalização, por decisão: preservar `normalize_body_v1`, `v2`, … é código que só envelhece. Relatório de outra versão se **reassina**, nunca se reverifica. O desvio mediu que a alternativa barata era declarar isso por escrito e não a fez; está declarado aqui, e nada no código mudou. A build guarda **uma** normalização — a dela. Quando o `signature_version` declarado no bloco não é o corrente, `checks.body` sai como **não avaliável** e fica fora de `diverged`, porque recomputar responderia sobre a regra de agora e nunca sobre o corpo de então. É a resposta honesta, e é menos do que o leitor gostaria: um relatório antigo não pode ser reverificado, só reassinado — e reassinar prova correspondência com a evidência de **hoje**, não com a de quando ele foi emitido. Fechar exigiria preservar as normalizações antigas (`normalize_body_v1`, `v2`, …) e despachar por versão, que é código que só envelhece; a alternativa mais barata, e não feita, é declarar por escrito que o suporte é de uma versão só. Hoje há uma versão e nenhum relatório afetado: a dívida é do primeiro dia em que a normalização mudar |
| A tabela de overrides do relatório não é correlacionada com o case | Fase 4b, desvio D-4b-23, medido ao fechar a revisão final | **Limite declarado.** Fechar exige `report sign --repo` e `report verify --repo`, e o **D-4b-23 mediu as duas saídas**: opcional, a checagem some em silêncio; obrigatório, o pacote de handoff vira três arquivos — o mesmo que o D-4b-14 recusou. A seção 9 de `templates/performance-report.md` manda declarar gate, data e motivo de cada override, e por estar **dentro** do corpo assinado ela ganha uma garantia real: apagá-la depois de `report sign` invalida a assinatura, e `verify` acusa em `body` (com teste). O que **não** existe é qualquer código que compare a tabela com o `gate_overrides` do `case.yaml`: um relatório que omite um override, ou que declara um que nunca houve, assina e verifica normalmente. Fechar exigiria `report sign --repo` e `report verify --repo`, e o custo foi medido no D-4b-23 — com `--repo` opcional a checagem some em silêncio, e obrigatório o pacote de handoff vira três arquivos, que é o modo de falha que o D-4b-14 já recusou |
| Igualdade bit-a-bit não vale entre plataformas nem entre versões do backend | medido em 2026-08-01, ao fechar a dívida acima | **Limite declarado.** Fechar não é escrever código que falta: é **reverter a decisão** de não pinar `hatchling==` e não nomear um interpretador de referência — as duas recusadas, com o motivo na própria linha (o artefato publicado já declara o `Generator:` que o produziu). Dois eixos sobrevivem à `reproducible = true`, e nenhum é do hatchling. (1) A versão do backend vaza para `WHEEL` como `Generator: hatchling X.Y.Z`, e `requires = ["hatchling>=1.25"]` não é pin — dois builds separados por um release do hatchling divergem. (2) O fluxo de deflate depende da implementação de zlib do interpretador: o CPython 3.14 do Windows usado na medição roda `zlib-ng` (`ZLIB_RUNTIME_VERSION = 1.3.1.zlib-ng`), o `ubuntu-latest`/3.11 do CI roda zlib padrão, e as duas comprimem os mesmos bytes de formas diferentes. Consequência: `verify_wheel.py` prova reprodutibilidade **dentro de uma plataforma**, que é o que o job `wheel` mede nos dois SOs separadamente — não entre elas. Fechar exigiria pinar `hatchling==` e nomear um interpretador de referência; nenhum dos dois foi feito, porque o artefato publicado já declara o `Generator:` que o produziu |
| O espelho do Devin sai **sem `tools:`**, e o subagente herda o que o harness der | fase de perfis de subagente do Devin, decisão registrada na §2 do spec e travada por teste | **Limite declarado, e o gatilho de reabertura não é nosso: a Cognition documentar o mapeamento.** A fonte diz que o **campo** `tools` do Claude Code é aceito pelo Devin ("Both formats are supported automatically") e a página de permissões enumera os nomes de tool dele (`read`, `edit`, `grep`, `glob`, `exec`) — mas **nenhuma página documenta o mapeamento de valores**: `Bash` → `exec` e `Write` → `write` não estão escritos em lugar nenhum (V-DV-8). Fechar significa reverter a decisão de não chutar, e o custo do chute foi medido nos dois sentidos: traduzir errado para menos **nega** uma tool que o perfil precisa, e o subagente para sem dizer por quê; traduzir errado para mais **concede** o que ninguém revisou, num campo cuja função é justamente restringir. Omitido, o perfil herda o que o harness dá, que é o comportamento default documentado — menos preciso do que gostaríamos, e o único que não afirma o que a fonte não diz. `render_agent(..., "devin")` remove a linha e as continuações dela, para a remoção nunca engolir a chave seguinte, e `tools:` **no corpo** do perfil não é tocado. **Reabre no dia em que a doc do Devin publicar a tabela de correspondência**: aí a tradução vira derivação de dado publicado, e a decisão se inverte com o mesmo argumento que a criou. **O que esta linha não afirmava, e a revisão final de 2026-08-04 obrigou a escrever:** a omissão **não é fronteira**, e o argumento acima nunca disse que era — ele é só sobre mapeamento de valores, e nunca mencionava que **o outro caminho carrega o campo**. Os dois diretórios de descoberta estão ligados por default (`read_config_from` tem `agents_standard` e `claude`, ambos `true`), a fonte é **silenciosa** sobre precedência entre eles, e `allowed-tools` tem default *"all tools"* — logo omitir é a opção **mais permissiva**, não a mais restrita, e o mesmo perfil pode chegar pelo `.claude/agents/` **com** `tools:`. A segurança não depende disso em grau nenhum: ela é a prosa de `## Não faz` no corpo, byte-idêntica nos dois espelhos, e a declaração de despacho das doze skills. Três textos afirmavam efeito onde não há (`README.md`, `AGENTS.md` e esta linha) e foram corrigidos na mesma varredura |
| Custom subagents são **experimentais** pela própria Cognition | fase de perfis de subagente do Devin, risco registrado na §7 do spec | **Limite declarado — e é o único do inventário cujo fechamento não depende deste repositório em nenhum grau.** A fonte declara literalmente: *"Custom subagents are **experimental**. The format, behavior, and configuration options may change in future releases"* (V-DV-6), e o mesmo se aplica a `subagent:`/`agent:` em skills. Some junto o formato de descoberta: nada garante que `.agents/agents/` continue sendo varrido, nem que a importação de `.claude/agents/*.md` sobreviva. **A mitigação é estrutural e já está no manifesto:** nenhuma capacidade declara `subagent` sem `playbook`, travado por teste — se o despacho sumir, o piso permanece e a única perda é o paralelismo. **O que não existe é vigilância:** ver a dívida da watchlist, logo acima; hoje a página que declara a experimentalidade é a mesma que ninguém confere quando muda. O que **deve** acontecer em toda fase futura que toque neste mecanismo está escrito no V-DV-6 e vale repetir aqui: **re-verificar a doc na data da entrega**, nunca construir garantia dura sobre ele |
| Dez das doze skills despacháveis saem **sem `agent:`**, e o Devin escolhe o perfil | fase de perfis de subagente do Devin, desvio D-DV-11, medido na Task 4; a décima entrou na revisão final de 2026-08-04 | **Limite declarado, e a alternativa foi recusada com o contraexemplo na mão — não por gosto.** Medido na relação derivada de `skills:` dos oito coordenadores: **14 das 20** skills são declaradas por dois a cinco coordenadores, e entre as **12** despacháveis apenas **3** têm resposta única (`review-emr-cluster` → `emr-infra-reviewer`, `review-data-validation` → `data-quality-reviewer`, `diagnose-oom` → `glue-incremental-performance-architect`). O caso ambíguo é a **maioria**, não a exceção. As outras nove declaram `subagent: true` sem `agent:`, que é forma documentada — o campo tem default *none* na tabela de frontmatter da fonte —, e o roteamento passa a ser do harness. Fechar significa reverter essa decisão e escolher um perfil por skill; a saída óbvia do plano ("o primeiro em ordem determinística") foi recusada porque a medição mostrou que ela **erra**: em ordem alfabética `review-pyspark-pr` cairia em `data-quality-reviewer` e `analyze-spark-plan` em `glue-incremental-performance-architect`, quando o especialista de ambas é `pyspark-code-reviewer`. Ordem alfabética não é critério de competência, e publicá-la como se fosse seria roteamento errado com cara de decisão. O contraexemplo está fixado em `test_a_ordem_alfabetica_seria_o_perfil_errado`. **O que fecharia de verdade é dado que não existe:** uma declaração de especialidade por skill, hoje inferível só do julgamento de quem escreveu os coordenadores. Enquanto ela não existir, o invariante bidirecional é a garantia que sobra — `agent:` presente sempre nomeia perfil que existe **e** que declara aquela skill. **A revisão final de 2026-08-04 mediu que "declarante único" não bastava, e a terceira atribuição caiu:** `diagnose-oom` → `glue-incremental-performance-architect` era única só porque `spark-performance-architect` **não lista** `diagnose-oom` no `skills:` dele — embora liste `diagnose-data-skew`, `analyze-spark-ui` e `tune-glue-job`, toda a vizinhança do mesmo diagnóstico. Isso é **omissão numa lista pré-existente**, não juízo de competência, e o perfil que sobrava era o orquestrador, cuja skill homônima este arquivo declara não-despachável por orquestrar via `next-step` — despachar investigação fechada para dentro dele publica o método que a mesma fase recusou. A regra nova é **derivada, não mantida à mão**: `orchestrator_profiles()` é o conjunto dos perfis cuja skill homônima está em `NON_DISPATCHABLE_SKILLS`, hoje com **um** elemento; se aquela skill virar despachável, a exclusão some sozinha. Sobram **duas** atribuições, e o limite ficou maior — dez de doze, não nove |
| Os cinco executores não estão num layout de descoberta documentado do Devin | varredura de completude do Devin, 2026-08-04, medida contra a §1.1 da pesquisa | **Limite declarado, e o gatilho de reabertura é dos dois lados: a Cognition documentar a recursão, ou este repositório decidir achatar o espelho.** Medido: a fonte descreve **dois** layouts de perfil customizado — *flat file* `agents/<nome>.md` e *directory* `agents/<nome>/AGENT.md`, com `AGENTS.md`, `agent.md` e `agents.md` também aceitos nessa precedência — e a importação do Claude Code casa `.claude/agents/*.md`, que é **raso**. `.agents/agents/executors/sf-judge.md` não é nenhum dos dois: pelo layout *directory*, `executors/` só publicaria um perfil chamado `executors`, e só se tivesse dentro um `AGENT.md`. Se a varredura recorre, **a documentação não diz** — é a mesma ambiguidade do `agents/` da raiz (V-DV-7), e vale a mesma regra. **Quatro textos afirmavam o contrário** (`README.md`, `AGENTS.md`, a tabela da §3.1 do `GUIA_DE_USO.md` e o desvio D-DV-R4 do spec, que escreve *"os executores também são perfis de subagente válidos"*), e a afirmação nunca teve fonte: ela foi lida da contagem de arquivos do espelho, não de uma página. Corrigidos os quatro. **Nada se perde na prática**, e é por isso que isto é limite e não dívida: `sparkforge playbook <coordenador>` lê `agents/executors/` do próprio repositório e devolve os mesmos cinco passos em qualquer plataforma, sem depender de descoberta nenhuma. **Fechar é decisão de desenho com custo, não código faltando:** achatar os executores para `.agents/agents/sf-judge.md` os tornaria treze perfis de topo, e aí `run_subagent` poderia escolher `sf-judge` para conduzir uma investigação inteira — o executor sozinho não é coordenador, e publicar os dois no mesmo espaço de nomes é exatamente o que o subdiretório existe para impedir. Fazer isso **só no espelho do Devin** é possível (`platform_for` já deriva a plataforma do alvo), e é fase própria: muda o que a plataforma enxerga, não como o arquivo é traduzido |
| Um coordenador despachado como subagente no Devin **não** despacha os cinco executores | varredura de completude do Devin, 2026-08-04, medida contra a §5.2 da pesquisa | **Limite declarado, e fechá-lo é reverter uma decisão que ninguém tomou por escrito até agora: declarar `max-nesting`.** A fonte é literal — *"By default, subagents cannot spawn their own subagents — only the root agent can. Subagent tools (`run_subagent` and `read_subagent`) are **disabled** inside a subagent"* —, e o campo que reverte isso (`max-nesting`, introduzido em 2026-05-26) **não** é declarado em perfil nenhum deste repositório. Consequência: o modelo de execução da Fase 4 — coordenador despacha os cinco executores — **não se traduz** quando o próprio coordenador é o subagente. O que se traduz é o **método**: o corpo do perfil, o `## Não faz`, as áreas de regra. A decomposição roda inline, e ela tem nome e verbo: `sparkforge playbook <coordenador>`, que é o piso das cinco plataformas justamente por não depender de despacho. **A decisão de não declarar `max-nesting` tem os mesmos três argumentos que a de não declarar `model:`**, e um quarto: (1) o campo é de um mecanismo que a própria Cognition declara **experimental**; (2) *"cost scales with the number of subagents [...] tasks that fan out into many subagents (or nest them) cost more"*, e aninhar é o caso caro; (3) nenhum arquivo versionado pode garantir que o despacho esteja sequer ligado; e (4) o `playbook` já entrega a decomposição, então o que se ganharia é paralelismo, não método. **Reabre no dia em que alguém medir que o paralelismo aninhado paga o custo** — e aí é uma linha por coordenador, no renderizador do Devin, com o número na mão |
| Normalização de HTML do `refresh_knowledge` não foi calibrada contra meses de execução real | 2026-07-31 | **Limite declarado, e de espécie diferente das cinco acima — é o caso ambíguo desta triagem.** Fechar não é reverter decisão nem escrever código: `normalize()` existe e funciona, e o que falta é **medição que ainda não aconteceu**. Chamar de dívida lançaria como atraso o que ninguém pode pagar hoje, que é o erro de contagem que esta triagem existe para corrigir. O que está **decidido e registrado** é a resposta ao dado quando ele chegar, e é isso que a torna limite e não incógnita: o primeiro PR ruidoso ajusta `normalize()`, nunca silencia a fonte. Esse PR é o gatilho que a converte em dívida com conserto conhecido. Se alguma página oficial mudar hash a cada leitura, ela vira alarme permanente. O primeiro PR ruidoso deve ajustar `normalize()`, não silenciar a fonte |
| `get-application` descreve o padrão da application, e `StartJobRun` o sobrepõe | Fase 5d, medido na Task 1 e registrado no `D-5d-11`, que nem o spec nem o plano previam | **Limite declarado, e é o limite da área `SF-EMRS` inteira.** A fonte é literal: *"The priority of configurations that you provide at `StartJobRun` supersede the configurations that you provide at the application level"*, com merge por classificação em `applicationConfiguration` e por tipo em `monitoringConfiguration` — **inclusive remoção** (`properties: {}`, `s3MonitoringConfiguration: {}`). Logo: **nenhum achado desta área prova o que um job run executou.** Fechar é reverter a decisão de não ler job run, que é a linha de fase logo acima — e é assimetria real com o EMR on EC2, onde o override de instance group mora **no mesmo dump** e por isso vira `emr.configuration.unapplied`; aqui ele mora noutro artefato. O que foi feito em vez de fechar é declarar o recorte em quatro lugares do produto: a §0 de `knowledge/emr-serverless/application-configuration.md`, a `explanation` das seis regras, o corpo de `agents/emr-infra-reviewer.md` e a seção de Serverless de `skills/review-emr-cluster/SKILL.md`. |
| A anotação `EMR.secret@` é **bypass incondicional** da heurística de segredo | Fase 5d, revisão final de 2026-08-05, medido ao reproduzir os dois valores | **Limite declarado, e é o único do inventário em que o limite era negado por escrito pelo próprio produto.** `_is_secret_reference` é `startswith` puro e roda **antes** da heurística. Logo `"EMR.secret@AKIAIOSFODNN7EXAMPL"` e `"EMR.secret@jdbc://user:senha@host"` saem com `secret_reference: True` e o valor **inteiro em `attrs.value`, sem redação** — e, num golden, commitado. A docstring do módulo afirmava sem qualificação que *"quando casa, o valor NUNCA é escrito em attrs"*; isso vale para a heurística e **não** vale quando a anotação vence antes. Corrigida a prosa em três lugares (docstring do módulo, `_is_secret_reference`, e o filtro `startswith("EMR.secret@")` de `test_no_secret_value_survives_into_a_committed_golden`, que é onde a concessão mora no teste). **O comportamento fica, e não é omissão:** a fonte declara **só o prefixo** — *"add the `EMR.secret@` annotation to the configuration value"* —, e o `{{SecretName}}` aparece no exemplo, não como gramática exigida. Validar a forma `EMR.secret@{{nome}}` inventaria gramática que a fonte não declara, e toda anotação legítima fora dela seria redigida **e** marcada `secret_pattern_match`, fazendo `SF-EMRS-002` acusar exatamente a correção que recomenda. **Fechar sem custo de falso positivo é possível e tem preço:** manter `secret_reference: True` (achado nenhum) e ainda assim redigir `attrs.value` quando o valor anotado casa a heurística — a evidência deixa de dizer QUAL segredo é referenciado, que é a parte útil dela. Não foi feito; está escrito aqui para ser decidido, não descoberto no uso |
| `architecture` é emitido como `Fact` e nunca julgado | Fase 5d, não-objetivo registrado na §2 do spec | **Limite declarado, e fechar é reverter uma decisão cujo custo já está medido.** Recomendar migração para `ARM64` depende de compatibilidade de dependência **nativa** do job — wheel compilada, JNI, binário empacotado —, e o `get-application` não descreve nada disso. Uma regra sobre `architecture` acusaria `X86_64` sem saber se o job sequer roda em ARM, que é achado confiante e possivelmente falso — a família de defeito que este projeto trata como a pior. O valor **sai** no fact, para quem tem a informação de fora poder decidir; o que não sai é julgamento. Fechar exigiria um artefato que declare as dependências nativas do job, que não existe em verbo nenhum deste repositório. |
| `RuntimeContext.emr` não é alimentado por artefato de EMR Serverless | Fase 5d, medida na Task 1 e registrada no `D-5d-5` | **Reclassificada em 2026-08-05, de dívida para limite declarado: o caminho alternativo que a linha propunha existe, foi exercitado, e não fecha o título dela.** A linha dizia que era dívida "porque existe caminho, e ele é ler a versão de outra superfície" — e esse caminho **já existia** desde a Fase 5a.2 (commit `8a7d506`, 2026-08-01), quatro dias antes de a linha ser escrita; o que faltava era exercitá-lo. Medido: `_PRECEDENCE` é `("event_log", "describe_cluster", "get_work_group", "cli", "terraform")` (`sparkforge/facts/runtime_detect.py:389`), e **`event_log` alimenta só `spark_version`** — `SparkListenerLogStart` carrega `Spark Version` e nada que se pareça com release label. Fora `describe_cluster`, que lê `emr.cluster` e não existe no Serverless, e a flag `cli`, que é declaração do operador, **nenhuma superfície preenche o eixo `emr`**. A prova é de uma linha: sobre os facts `emrs.*` de `fixtures/emr_serverless/app_saudavel/` o contexto sai com **todos** os eixos vazios e `detected_from: []`; acrescentando um `spark.runtime_version` sintético de event log, ele sai `{'emr': '', 'spark': '3.5.2', 'detected_from': ['event_log']}`. **O caminho alternativo enche `spark` e deixa `emr` vazio**, que é literalmente o que o título desta linha afirma. Fechar de verdade depende de terceiro — a AWS publicar a matriz de release do Serverless com os quatro componentes —, e gatilho de reabertura que não é nosso é a assinatura de limite declarado, a mesma das duas linhas de Cognition nesta tabela. **Contexto que reduz o peso da linha, e vale escrito porque ninguém tinha medido:** **zero** das 81 regras têm `emr` em `runtime_scope` — os únicos eixos usados no catálogo inteiro são `glue` (8 regras), `iceberg` (1) e `spark` (1, a `SF-GRAPH-002` da Fase 6a) —, e as **9** regras `SF-EMR-*` e as **6** `SF-EMRS-*` declaram `runtime_scope: {}`. Hoje `RuntimeContext.emr` **não porteia regra nenhuma**, no EC2 nem no Serverless. **A leitura anterior, da triagem de 2026-08-04, fica abaixo inteira — reclassificar não é reescrever:** **Dívida, e a redação importa: a AWS não publica a matriz — não que as matrizes divirjam.** A D-5 do spec previa dois desfechos, idênticas ou divergentes; a medição achou um terceiro. As 24 páginas de release do EMR Serverless trazem **só** Spark, Hive e Tez, sem o sufixo `-amzn-N`; Hadoop, Iceberg e Python não aparecem em nenhuma — **três das quatro colunas de `EMR_MATRIX` não têm fonte do lado do Serverless** —, e há `releaseLabel` em uso (`emr-spark-8.0.0`) que não tem sequer chave na matriz, ou seja, derivar por ela falharia calada justamente na release mais nova. Nas 24 releases comparáveis a versão de comunidade do Spark **coincide, uma a uma**, e é por isso que isto é dívida e não limite: existe caminho, e ele é ler a versão de outra superfície (um event log de job run, ou uma declaração do operador) em vez de derivar do label. Consequência hoje: `emrs.application` não é produtor, um `get-application` não emite `env.platform` nenhum (`_PLATFORM_KEYS` só conhece `emr` e `glue`), e as seis regras `SF-EMRS` foram escritas com `runtime_scope` vazio para que a área não dependesse disso. **Afirmar divergência para fechar a linha seria afirmar o que ninguém mediu**, que é o defeito que este projeto existe para não cometer. |
| Jar de GraphFrames de **outro minor** de Spark não é tratado como resolução, e por isso `SF-GRAPH-002` acusa os dois lados do par de fixtures | Fase 6a, veto `V-GR-1` (motivo b) e §7 de `knowledge/graph/availability.md` | **Limite declarado — fechar é reverter a recusa de afirmar o que a fonte nega.** Para Spark 3.3 **não há artefato publicado em linhagem nenhuma** (`0.8.2` para em 3.2, `0.8.3` começa em 3.4, `io.graphframes` compila contra 3.5), então qualquer `--extra-jars` de GraphFrames naquela faixa aponta necessariamente para **outro** minor. Tratar isso como "resolvido" inventaria a garantia que a fonte recusa dar. Consequência medida e aceita: `import_com_jar_declarado` — escrita como metade **negativa** do par — dispara `SF-GRAPH-002` igual à positiva, e o `--extra-jars` aparece **no texto do achado** como tentativa de contorno em vez de sumir. O `proves` da fixture foi reescrito para o que ela de fato prova: que a acusação é sobre o **artefato**, não sobre o IaC. **O gatilho de reabertura não é nosso:** é a comunidade publicar `-spark3.3` — a release note da `0.8.3` afirma o suporte e o artefato responde **404** (`V-AV-5`), e para a pergunta "há o que instalar?" o repositório vence a nota. |
| A conf de checkpoint que vem **de fora do `.py`** não é lida, e a ressalva vai escrita dentro do achado P0 | Fase 6a, veto `V-GF-1` e desvio `D-6a-12` | **Limite declarado — fechar é reverter o recorte de artefato da fase.** `spark.checkpoint.dir` (0.9.3+) satisfaz a exigência de `connectedComponents` **sem aparecer no código**, quando vem do `--conf` do IaC ou do `spark-submit`. A fase leu o que **está** no arquivo — as duas grafias por `spark.conf.set` dentro do próprio job entraram como `graph.checkpoint_dir` com `form`, porque ignorá-las faria a P0 disparar sobre código que resolveu o problema na linha de cima —, e o que sobra fora do alcance vai declarado **dentro do achado**, no padrão de `V-AS-2`. Não é omissão silenciosa: é a diferença entre "o motor não viu" e "não há". **Fechar depende de superfície que outra linha já registra:** o `--conf` do Terraform vira `tf.unresolved` com `reason: heredoc` e o event log não emite `SparkListenerEnvironmentUpdate` — as duas medições estão na linha de `SF-CFG`, em *Fases*, e é lá que a configuração efetivamente aplicada passa a ser lida por alguma superfície. |
| O eixo **Python** de GraphFrames não vira regra, embora a matriz esteja medida | Fase 6a, veto `V-AV-3` no cabeçalho de `knowledge/graph/availability.md` | **Limite declarado — fechar é reverter a recusa de acusar sem saber a linhagem.** Medido abrindo os dois jars: `graphframes-0.8.2-spark3.2-s_2.12.jar` carrega **13** arquivos `.py` dentro dele e `graphframes-spark3_2.12-0.12.1.jar` carrega **0** — a fratura da `0.9.0` mudou de onde vem o wrapper. O pacote PyPI `graphframes-py` (`0.12.1`, 2026-06-17) exige `requires_python >=3.10`, e cruzando com as matrizes isso corta **toda a série EMR 6.x e Glue 3.0**; o homônimo `graphframes` no PyPI parou em `0.6`, em 2018, e é pacote abandonado com o nome certo. **Por que não é regra:** o `.py` não diz qual linhagem o job usa, e carregar o Python de dentro do jar legado por `--py-files` é caminho válido — acusar seria afirmar sobre uma escolha que o artefato não registra. Fica como **contexto do achado** de disponibilidade, não como condição. Fechar exige uma superfície que diga qual jar está no classpath, que esta fase não lê. |
| O vocabulário por nome cobra o preço **também em achado**, e não só em fact — `str.find()` em laço e `GraphFrame` sem import | Fase 6a, revisão final de 2026-08-05, medido reproduzindo as duas formas contra o extrator | **Limite declarado, e o que a revisão mudou foi o lugar onde ele está escrito.** O cabeçalho de `sparkforge/facts/graph.py` declarava o preço dos dois níveis **no fact** e calava sobre a consequência: medido, um `"...".find(x)` dentro de laço, num módulo que importa GraphFrames, sai como **`SF-GRAPH-004` (P2)**; e um `GraphFrame(v, e)` **sem import nenhum** sai como `graph.construction` e pode virar **`SF-GRAPH-003` (P2)**, porque `constructors` nasce semeado com `"GraphFrame"`. **As duas metades foram medidas e nenhuma fecha barato.** Exigir import para semear `constructors` é uma linha, e está **errado**: `GraphFrame` é nome publicado e específico da biblioteca — mesmo critério de `connectedComponents`, que é lido sem import —, e a exigência perderia `from minha_lib.grafo import GraphFrame`, que reexporta o símbolo e não deixa `graphframes` nenhum no arquivo. Fechar o `find` exigiria correlacionar o receptor com um nome que **este** arquivo viu ser construído como grafo, o que troca um falso positivo estreito (import presente **E** `str.find` dentro de laço) por um falso negativo largo, porque grafo que chega por parâmetro é forma corrente e o módulo já declara não saltar para o chamador. **Fechar é reverter uma das duas escolhas**, e o preço de cada reversão está medido acima. As duas severidades são P2; nenhuma é a acusação P0 que esta área existe para não cometer. O cabeçalho passa a declarar as duas, com número de regra. |
| `same_subject` desta área agrupa por **função**, e não por construção nem por laço | Fase 6a, revisão final de 2026-08-05, `D-6a-49` — medido ao escrever a fixture que torna `same_subject` inapagável | **Limite declarado — fechar é mexer na chave de agrupamento do motor, que vale para as quinze áreas de uma vez.** Medido: `engine._subject_group_key` prefere `subject.symbol` quando ele existe, e o `symbol` de todo fact de `facts/graph.py` é a **função** que contém o nó (`_subject`). Consequência: duas construções com arestas não persistidas **dentro da mesma função** caem no mesmo grupo e viram **um** achado, com a evidência das duas — e o remédio de `SF-GRAPH-003` é um `cache()` **por construção**. O mesmo vale para dois laços na mesma função em `SF-GRAPH-004`. **É subnotificação, não acusação falsa**: quem lê o achado vê os dois facts na evidência, e o número de correções está lá. **O que o corpus prova hoje**: `dois_grafos_no_mesmo_arquivo` põe os dois grafos em funções diferentes, sai com quatro achados, e apagar qualquer um dos dois `same_subject` derruba o golden para um — verificado apagando cada um, rodando e restaurando. **Fechar não é código desta área**: a alternativa seria `_subject_group_key` desempatar por linha mesmo quando há `symbol`, e isso mudaria a contagem de achados de toda regra `same_subject` do catálogo — `SF-DQ-001`, `SF-DQ-003`, `SF-ATH-002`, `SF-ATH-003`, `SF-GLUE-002` e as quatro de `SF-BENCH` —, sem medição que sustente a mudança. A decisão não cabe numa regra de grafo. |

### Fechadas — registro histórico (31)

Fechar não é apagar: a linha fechada é o que impede a dívida de voltar sem que
alguém perceba, e o modo de falha da linha de EMR — sobreviveu fechada por três
fases — é o motivo de o registro ficar aqui, e não sumir.

As **seis primeiras** fecharam juntas, na rodada de dívidas abertas de 2026-08-05,
e são a maior baixa que este inventário já teve num dia. Elas têm uma propriedade
em comum que vale mais que o número: **as seis deixaram teste para trás** — uma
varredura por ramo de severidade, um golden por ramo, três fixtures de travessia de
helper, o invariante do lock com a segunda origem, a paridade das quatro listas de
tools, e o golden que importa `with_plan_ref` em vez de espelhá-lo. Dívida que fecha
sem guarda volta; estas têm guarda, e o guarda é nomeado em cada linha.

A **sétima** é a única do inventário que estava classificada como **fase** e fechou
como fase — sem virar dívida no caminho.

As **nove últimas** entraram e fecharam no mesmo dia: quatro na revisão final da fase de
perfis de subagente, e **cinco na varredura de completude** que veio depois dela.
Registrar dívida que nasceu fechada não é formalidade: três das primeiras eram **buraco de
gate ou de fronteira** que a suíte inteira dava por coberto, e três das segundas são
**texto derrubado que sobreviveu fora do conjunto de arquivos que a fase tocou** — e é
exatamente o tipo que volta sem alarme se ninguém escrever onde estava.

| Dívida | Origem | Impacto |
|---|---|---|
| ~~`funcval compare` não tem `--out`, e a saída dele não chega ao `judge` por arquivo~~ — **fechada** na rodada de dívidas abertas, commit `93d9c69` | Fase 4c, desvio D-4c-26, medido ao fechar a fase | `--out` na CLI e `out_path` na tool, com a escrita em `_core` **antes** da paginação. Fechou exatamente como a linha previa — duas linhas de argumento e duas de handler —, e a segunda consequência, a que a linha dizia que morde, foi **medida na cadeia inteira**: sobre `count_diverged` com `--limit 2`, o arquivo do `--out` traz os 5 facts e `judge` acha `SF-FVAL-001` em P0; sobre a página de 2 extraída do envelope, `judge` acha zero. O contorno que a linha mandava manter escrito na skill virou falso ao fechar, e foi reescrito em `skills/benchmark-pyspark-job/SKILL.md` e no `GUIA_DE_USO.md`. **O texto de quando ela estava aberta fica inteiro abaixo, e é o que permite conferir se ela fechou pelo motivo que dizia:** **Dívida, e das baratas — não há decisão a reverter, só código a escrever.** `funcval plan` grava o artefato (`--out` **obrigatório**, porque o plano é a entrada do `compare` e a evidência do gate `functional_validation_defined`); `compare` **imprime** o envelope paginado e não escreve arquivo nenhum. Todos os outros produtores de fact do repositório gravam: os **catorze** `analyze *`, o `benchmark`, o `fuse` e o próprio `funcval plan`. **Medido na CLI, ponta a ponta** sobre `fixtures/funcval/count_diverged/`: `funcval compare > arquivo.json` seguido de extrair `items` do envelope e passar a `judge --facts` devolve `SF-FVAL-001`, então o caminho existe — o que não existe é o caminho de um passo. Duas consequências, e a segunda é a que morde. (1) O operador precisa de um passo de `python -c` ou `jq` entre os dois verbos, num fluxo cujo passo seguinte (`judge`) é obrigatório para a área servir para alguma coisa. (2) `--limit` vale **50** por default e o envelope pagina: quem extrair `items` sem conferir `next_cursor` julga a primeira página e chama o resultado de comparação — que é literalmente o defeito que `SF-FVAL-005` acusa no dado do operador, cometido pelo fluxo do próprio motor. **Fechar são duas linhas de argumento e duas de handler**, `--out` na CLI e `out_path` na tool, mais a paridade que a Fase 4b tornou invariante (as quatro listas de `tests/test_adapters_tools.py`). Fica aberta com o contorno **escrito** na skill que ensina o verbo, e não só aqui: `benchmark-pyspark-job` é a única que ensina `compare`, e carrega a extração de `items` e a conferência de `next_cursor`; `review-pyspark-pr` ensina só `funcval plan` — que **tem** `--out` — e delega a comparação, então não há contorno a carregar lá. Skill que ensina o caminho feliz e cala o passo que falta é como a dívida vira erro do usuário |
| ~~O corpus não exercita o ramo **exato** da `SF-FVAL-004`~~ — **fechada** na rodada de dívidas abertas, commit `64d7ec8` | Fase 4c, desvio D-4c-23, medido ao escrever a regra | Fixture `fixtures/funcval/aggregate_exact_diverged/`, com golden bidirecional. Prova por apagamento, que é o que a linha pedia: apagar a condição exata da regra deixava o corpus inteiro verde, e com a fixture deixa golden vermelho. **A magnitude não é a que a linha citava, e o desvio fortalece a fixture:** a linha dizia "uma unidade sobre quinhentos milhões dá `relative_delta` da ordem de `2e-9`, abaixo de qualquer tolerância utilizável", e `2e-9` está **acima** de `1.0e-9`. A fixture move uma unidade sobre quinhentos **bilhões** e o `relative_delta` medido é `2,0e-12` — três ordens **abaixo** da tolerância. E a razão principal de as duas condições existirem nem é de magnitude: a relativa filtra por `attrs.comparison: relative`, e agregado exato não casa com ela em grandeza nenhuma. **O texto de quando ela estava aberta fica inteiro abaixo, e é o que permite conferir se ela fechou pelo motivo que dizia:** **Dívida de fixture, e a própria D-4c-23 já a nomeia assim.** A 004 tem `when.any` com **duas** condições, porque agregado de coluna inteira ou decimal é comparado de forma exata e sai **com** `diverged`, enquanto o de ponto flutuante sai sem. Nas **sete** fixtures de comparação, `agg:sum:cliente_id` (o `bigint`) é **idêntico** nos dois lados: o ramo que dispara é sempre o relativo. Consequência precisa, e é ela que dimensiona a linha: apagar a condição exata da regra **não** deixaria golden nenhum vermelho, e é justamente o ramo cuja ausência produziria o defeito que a fase existe para acusar — uma soma de `bigint` que mudou em uma unidade sobre quinhentos milhões dá `relative_delta` da ordem de `2e-9`, abaixo de qualquer tolerância utilizável, e sumiria de achado nenhum aparecendo só em `diverged_check_count`. **O que existe hoje** é a classificação de `bigint` como exato, medida em `tests/test_facts_funcval.py`, e a regra escrita sobre ela; **o que falta** é uma fixture com o agregado inteiro divergindo, que é a única prova que sobrevive a alguém reescrever a regra. Fechar é uma décima fixture com golden bidirecional, no molde de `aggregate_outside_tolerance` com o eixo trocado — nada a reverter, e o custo é o de sempre para fixture nova |
| ~~`plan_ref` sai `""` nos sete goldens de comparação~~ — **fechada** na rodada de dívidas abertas, commit `9474aa8` | Fase 4c, desvio D-4c-22, medido na Task 5 | `scripts/regen_fixtures.py` passou a injetar o `Fact.id` do plano via `with_plan_ref`, que `tests/test_fixtures_golden_funcval.py` **importa** em vez de espelhar — o único passo do golden que não é reimplementado no teste, de propósito. Fechou pelo caminho que a linha nomeava (derivar na regeneração, nunca escrever à mão), e **o resultado contraria o que a linha temia**: `plan_ref` vive só em `attrs`, nenhum `Fact.id` se moveu e nenhum `findings.json` mudou — duas linhas por `facts.json`, nos sete. **O texto de quando ela estava aberta fica inteiro abaixo, e é o que permite conferir se ela fechou pelo motivo que dizia:** **Dívida, e o desvio registra por que ela não foi paga na hora.** `plan_ref` é o `Fact.id` do `funcval.plan`, sha1 de (kind, subject, measures) — depende do corpus. Escrevê-lo **à mão** nos `before.json`/`after.json` faria o golden depender de um id que muda quando o `input/` muda, e a fixture passaria a quebrar por uma razão que não é a dela; pior, um `plan_ref` desatualizado é exatamente o defeito que `_reject_foreign_plan_ref` (D-4c-16) existe para pegar, e ele mora no **adaptador**, que este corpus não exercita. Então os resultados trazem `target` e `checks`, e `funcval.analyzed.attrs.plan_ref` sai vazio nos sete. **Não é campo morto: é campo que este corpus não alimenta**, e a distinção importa porque quem ler o golden não tem como saber qual dos dois é. O caso de `plan_ref` conflitante entre os lados **está** coberto, por teste unitário em `tests/test_facts_funcval.py` — o que não está coberto é o caminho pelo adaptador. **Fechar não é escrever o id à mão**, que é o que a D-4c-22 recusou: é `regen_funcval` derivar o plano e injetar o `fact_id` dele nos dois resultados **na regeneração**, que é o mesmo mecanismo que faz os goldens sobreviverem a mudança de `input/`. Código que ninguém escreveu, e uma decisão de escopo do regenerador |
| ~~Cinco regras com `severity_by` têm ramo de severidade **sem golden nenhum**~~ — **fechada** na rodada de dívidas abertas, commits `0070369`, `3c45c2f`, `5dc3f0e`, `b89dc73`, `3b24ee6` e `080c871` | Revisão final da Fase 5d, 2026-08-05, medida sobre os 132 `findings.json` do repositório; **pré-existente**, não regressão da 5d | Medição refeita do zero e **idêntica à da revisão da 5d**: 15 ramos, 9 vistos, 6 sem. Seis fixtures, cada uma no **limiar exato** do próprio ramo. **O que fecha a linha não é a sétima fixture e sim o guarda que ela pedia por escrito:** `test_every_severity_branch_has_a_golden_that_produces_it`, com asserção de vacuidade (`total >= 15`) para que a varredura não passe por ter deixado de enxergar `severity_by`. Contado sobre o catálogo inteiro: **85 ramos de severidade, 85 com golden**. **Custo registrado, e ele é real:** a fixture do P0 da `SF-PQ-001` tem 14.305.787 bytes (14,3 MB), porque o ramo é contagem de arquivo pequeno e encolher a listagem seria mentir sobre a contagem que a regra lê; `fixtures/` foi de 1.756.621 para 17.615.531 bytes na árvore (1,8 MB → 17,6 MB, medido em `git ls-tree -l` nos dois lados), e as seis fixtures pesam 712 KB em objeto git. **O texto de quando ela estava aberta fica inteiro abaixo, e é o que permite conferir se ela fechou pelo motivo que dizia:** **Dívida de fixture, e a mais barata do inventário — uma fixture por ramo, nenhuma decisão a reverter.** Medido: das **7** regras do catálogo com `severity_by`, **15** ramos existem (contando o `severity_default` quando ele é alcançável) e **9** aparecem em algum golden. Faltam **6**, em **5** regras: `SF-EMR-006` (P2), `SF-ICE-001` (P2), `SF-PQ-001` (P0 **e** P1), `SF-UI-001` (P2) e `SF-UI-004` (P2). O que isso significa concretamente: **o ramo sem golden pode virar qualquer severidade com a suíte inteira verde** — nada compara severidade de regra contra fixture fora do golden de `findings`, e onde não há golden não há comparação. `SF-PQ-001` é a pior, com dois ramos abertos de três. **Duas fecharam antes desta linha existir**, e as duas são o modelo: `SF-EMR-009` desde a Fase 5b (86400 e 604800), e `SF-EMRS-005` nesta revisão (1440 e 10080, com o par 1439 fixando o limiar junto). A área que abriu a linha fechou a sua; as cinco restantes são de áreas que esta rodada não tocou, e fechá-las à mão sem o corpus daquelas áreas seria inventar payload em vez de medir. **Fechar é escrever cinco fixtures**, cada uma com o número do ramo que ela prova — e o teste que faltaria depois é o que torna a lacuna visível em vez de silenciosa: uma varredura que exija golden por ramo, no espírito de `test_fixtures_kind_coverage.py` |
| ~~`SF-DQ-002` acusa validação cuja consequência está atrás de um helper~~ — **fechada** na rodada de dívidas abertas, commit `cd5bf49` | Fase 5c (`_enforcements`), **medida de novo** na Task 3 da Fase 5c.2, 2026-08-03 | `_Callees`, a aresta simétrica de `_Callers` — e a linha estava certa ao dizer que a máquina da 5c.2 não servia: o que faltava era ler o corpo do callee, não resolver a chamada. **O limite é de um salto, e ele foi medido antes de decidido:** nos 86 `.py` de `fixtures/` e `sparkforge/` de antes da rodada havia 10 checks, 9 enforcements diretos e **zero** cadeia com helper — nenhum caso real pedia o segundo salto. O que passa do salto não é calado: vira `dq.unresolved` com reason `enforcement_beyond_one_hop`, nomeando os dois helpers. Três fixtures, e o triô é o argumento — a do falso positivo que parou, a do helper que **só registra** (que quebra se a travessia virar "toda chamada resolvida é consequência") e a do limite com o ponto cego contado. **Quatro textos afirmavam que a análise não fazia isso e os quatro foram corrigidos:** a `explanation` da regra, o perfil `data-quality-reviewer`, a skill `review-data-validation` e a descrição da tool `sparkforge_analyze_data_quality`. **O texto de quando ela estava aberta fica inteiro abaixo, e é o que permite conferir se ela fechou pelo motivo que dizia:** **Dívida, não fase — e é o outro caso ambíguo.** Três coisas a separam de uma fase. (1) **A especificação do conserto já está escrita dentro da própria linha** — travessia de corpo de callee por parâmetro, com decisão própria sobre religação, alias e `def` aninhado; fase é trabalho que ainda precisa de spec, e esta tem o dela. (2) O escopo é **um predicado** de um extrator que já existe: `_reader`, `_read_of` e `_reads_this_check` já funcionam, e só `_abort_in` não atravessa. (3) O defeito é de **regra já entregue** que erra para o lado da acusação — `SF-DQ-002` em P1 sobre quem protegeu o pipeline —, e isso é assinatura de dívida, não de escopo não construído. Adiada com o custo medido na mão, que é a definição de dívida deste inventário. `aborta_se(ruins)` num helper que faz `if ruins > 0: raise` não produz `dq.enforcement`, e `SF-DQ-002` dispara sobre `absent: dq.enforcement` — a regra acusa exatamente quem protegeu o pipeline. **Medido, não presumido:** sobre a fonte de nove linhas do gate, o motor devolve `SF-DQ-002 (P1)` e `SF-DQ-003 (P2)`, e a instrumentação de `_enforcements` mostra onde está a lacuna — `_reader` **já aceita** `aborta_se(ruins)` como leitor, `_read_of` **já vê** o nome `ruins`, e `_reads_this_check` **já devolve** `True`. O único predicado que falha é `_abort_in`, que procura o aborto nos ramos **deste** escopo e o aborto está no corpo de outra função. **Por isso a máquina da 5c.2 não serve:** a parte que ela poderia emprestar (resolver a chamada e mapear argumento e parâmetro) é precisamente a parte que já funciona, e o que falta é ler o corpo do callee e decidir se ele aborta **condicionalmente ao valor recebido** — travessia nova, com limites próprios. Nenhum dos limites da 5c.2 transfere: "um só call site" não diz nada sobre o que a função faz, porque um helper chamado de dez lugares aborta ou não aborta independentemente disso. Implementar assim mesmo, para poder dizer que as duas fecharam, produziria uma máquina com garantia inventada num kind cujo erro cai do lado da acusação. **Fica aberta com o custo na mão**, e o que ela exige está nomeado: travessia de corpo de callee por parâmetro, com decisão própria sobre religação, alias e `def` aninhado |
| ~~A pesquisa de fontes do Devin não é vigiada por `refresh_knowledge`, e o spec afirmava que era~~ — **fechada** na rodada de dívidas abertas, commit `61377ed` | fase de perfis de subagente do Devin, medido ao fechar a Task 6 em 2026-08-04 | `watchlist()` ganhou a **segunda origem derivada** que a linha nomeava — as URLs dos blocos `Fontes` de `knowledge/**.md` — e recusou a saída barata que a própria linha já tinha condenado. Lock de **51 para 109**: 51 por regra, 104 por `knowledge/`, 46 pelas duas, **zero sem consumidor**. O invariante `set(lock) == set(watchlist())` **não afrouxou**, e `test_each_entry_names_the_rules_that_cite_it` virou `test_each_entry_names_who_cites_it`, mais forte no que importa: toda entrada nomeia pelo menos um consumidor. `--update --offline` entrou junto e não é conveniência — sem ele o invariante passaria a depender de rede para ser reparável. **O texto de quando ela estava aberta fica inteiro abaixo, e é o que permite conferir se ela fechou pelo motivo que dizia:** **Dívida, não limite — e a linha existe porque uma mitigação declarada no spec não existe.** A §7 do spec lista, contra o risco "o Devin muda formato de perfil e o tradutor quebra em silêncio", que "a pesquisa fica em `knowledge/` com data, **na watchlist do `refresh_knowledge`**". A primeira metade é verdadeira; a segunda é **falsa por construção**, e a medição é de uma linha: `watchlist()` em `scripts/refresh_knowledge.py` deriva a lista de URLs de `sources[].url` **das regras do catálogo**, e `knowledge/sources.lock.json` tem **37 fontes, zero com `devin`**. Conhecimento sem regra que o cite nunca entra — a docstring da função diz isso em voz alta ("ela É o conjunto de `sources[].url` das regras"), e o desenho é bom: watchlist mantida à mão apodrece. O efeito aqui é que as **24 URLs distintas** de `docs.devin.ai` citadas na pesquisa e coletadas em 2026-08-04 envelhecem sem alarme, sobre uma superfície que a própria fonte declara **experimental** ("format, behavior, and configuration options may change"). É a combinação mais cara possível: a página que mais provavelmente muda é a única que ninguém vigia. **Duas saídas, e a barata é errada.** Escrever uma regra de catálogo que cite as URLs só para entrar na watchlist seria fabricar diagnóstico sobre Spark que não existe, e o catálogo é dado julgado por `runtime_scope` — poluí-lo para obter frescor inverte a relação. A saída certa é ampliar `watchlist()` para varrer também os blocos `Fontes` de `knowledge/**.md`, que **é código que ninguém escreveu**: exige um leitor do formato de rodapé (hoje prosa com URL e `retrieved:`, sem schema), decidir o que fazer quando a mesma URL é citada por regra e por knowledge com datas diferentes, e aceitar que páginas de doc de produto mudam de hash com frequência maior que a de fonte AWS — o risco de alarme permanente que a linha de `normalize()` já registra. Fica aberta com o custo na mão e o número medido: 37 fontes vigiadas, 24 não vigiadas |
| ~~Dois dos quatro gates seguem advisory mesmo sob `strict_gates`~~ — a metade `functional_validation_defined` **fechou** com a Fase 4c, em 2026-08-04 | Fase 4b, por decisão registrada na §1 do spec; era a única linha do inventário classificada como **fase**, e fechou como fase | **Fechou exatamente como a linha previa, e isso é o que vale registrar.** O texto de 4b dizia: *"quando ela entregar o produtor, basta declarar `satisfied_by` e `guards_phases` no bloco `gates` do `routing.yaml`, **sem tocar em Python**"*. Foi o que aconteceu — `satisfied_by: funcval.plan`, `produced_by` com o comando exato, `guards_phases: [report]`, e zero linhas de `store.py` alteradas. Previsão que se confirma ao ser paga é a única forma de saber que a arquitetura do gate estava certa: se tivesse sido preciso mexer no motor, o "contrato de produtor como dado" da 4b teria sido só uma tabela bonita. **A outra metade da linha continua aberta e mudou de mesa**, como o texto original mandava: `dominant_bottleneck_identified` não tem produtor previsto — dominância é ordenação entre candidatos, nenhum kind a afirma — e está nos limites declarados, não aqui. A fase que a fechou escolheu `funcval.plan` e **não** `funcval.check_delta`: o gate diz *defined*, não *executed*, e o que satisfaz é o plano |
| ~~Cobertura de EMR não existe~~ — **fechada** pela Fase 5b em 2026-08-01, merge `59c27e2` | identificada ao fechar a Fase 3a | `RuntimeContext.emr` existe e guarda a release numérica, `EMR_MATRIX` tem guard de drift assimétrico contra o knowledge, `emr_cluster.py` lê o dump de `describe-cluster` e os cinco que o completam, e a área `SF-EMR` tem 9 regras com coordenador próprio. **A linha sobreviveu fechada por três fases** — a 5b marcou a fase como concluída na seção própria e não voltou aqui, e as varreduras seguintes conferiram números, não vereditos. Fica como lembrete do modo de falha: inventário de dívida só é confiável se fechar dívida for parte de fechar fase. O que **continua aberto** do escopo original está na linha própria — que a Fase 5d encolheu para **EMR on EKS** só |
| ~~O curinga `"*"` de `runtime_scope` não filtra nada~~ — **fechada** na Fase 5a, commit `fcb8402` | revisão adversarial do spec da Fase 5, 2026-08-01 | `version_scope.py` pula a checagem de presença da chave, então `{glue: "*"}` casa com qualquer runtime. 20 regras agnósticas ficaram etiquetadas como de Glue, e as 5 de infra Glue avaliam em silêncio fora do Glue. Fase 5a corrige |
| ~~`SF-GLUE-002` some de findings e de skipped ao mesmo tempo~~ — **fechada** na Fase 5a, commit `8815f53` | revisão adversarial do spec da Fase 5, 2026-08-01 | `requires_facts: tf.module_analyzed` é sentinela de "algum `.tf` foi lido", não de "há job Glue aqui": sem `aws_glue_job`, ela passa a barreira, avalia, dá falso, e desaparece dos dois lados. Fase 5a corrige |
| ~~`sparkforge judge` não tem flag `--emr`~~ — **fechada** em 2026-08-01, commit `b9c2c87` | Fase 5b, 2026-08-01 | Há `--glue`, `--spark`, `--python`, `--iceberg` e `--athena`; a release do EMR só entra no `RuntimeContext` pelo fact `emr.cluster`. Hoje inócuo — toda regra `SF-EMR` lê a release do próprio fact — mas quem sabe a release e não tem dump não consegue declará-la, e é assimetria com as outras cinco plataformas. **Entrou nos três verbos que aceitam runtime** (`judge`, `case open`, `runtime detect`) e nas três tools MCP que os espelham — deixar o MCP para trás recriaria a assimetria um nível acima. A flag perde para o dump (`cli` está abaixo de `describe_cluster` em `_PRECEDENCE`) e discordar dele vira divergência, nunca resolução silenciosa; concordar na **outra grafia** (`7.5.0` contra `emr-7.5.0`) deixou de virar divergência falsa, porque a comparação de identidade passou a normalizar por `_emr_key`. O conjunto esperado de flags agora é derivado de `RuntimeContext`, não de lista literal: eixo novo cobra flag **e** propriedade de tool no mesmo commit |
| ~~`PYSPARK_PYTHON` sai como `emr.configuration` e não alimenta a detecção de Python~~ — **fechada** em 2026-08-01, commit `9dea76b` | Fase 5b, Task 3 | A `EMR_MATRIX` omite `python` na série 6.x de propósito (a AWS lista `"2.7, 3.7"` como *instalados*), e o desenho previa `python` resolver quando `spark-env`/`PYSPARK_PYTHON` estivesse no dump. O extrator já emitia o valor cru e nada lia. **Ligado, com fronteira estreita:** só o nome de executável `pythonX.Y`, que carrega o minor por construção. `/usr/bin/python3` (só o major), `/usr/bin/python`, wrapper de nome arbitrário e `env python3.11` **não emitem** — a leitura entra como `describe_cluster`, acima da matriz e da flag, e versão errada com precedência alta alimenta `runtime_scope`. Só nível cluster: configuração de instance group é a **pedida**, e é para isso que `emr.configuration.unapplied` existe. Nenhum golden mudou — a fixture existente usa `/usr/bin/python3`, que é justamente o caso que não emite |
| ~~`athena.workgroup` carrega `engine_version` e não alimenta a detecção de Athena~~ — **fechada** em 2026-08-01 | Fase 5b, ao fechar a dívida acima | A mesma dívida virada do avesso: o número era observado, com artefato e sha256, e `RuntimeContext.athena` só era preenchível pela flag `--athena` — foi por isso que a Fase 5a esvaziou o `runtime_scope` das cinco `SF-ATH` (linha `{athena: "*"}` da tabela acima). **Ligado, e só quando é inequívoco:** o valor vai como geração inteira (`"3"`, nunca `"3.0"` — a AWS não publica nada entre as duas), sob a fonte nova `get_work_group`, colada em `describe_cluster` em `_PRECEDENCE` (mesma classe de evidência: API da AWS reportando o que está **em vigor**; a ordem relativa entre as duas nunca decide nada porque elas jamais disputam o mesmo componente). **Multiplicidade de workgroup não é divergência:** `legacy-etl` na 2 e `primary` na 3 é configuração normal de conta, e chamar isso de SF-ENV-001 seria P0 falso; unanimidade ou nada, e o número de cada workgroup continua no seu próprio fact, onde `SF-ATH-004` o lê. `athena.unresolved` **anula** a leitura em vez de ser ignorado por ela. Com isso `runtime_scope: {athena: ">=3"}` volta a ser possível — medido nas três fixtures de `fixtures/athena/`, `True`/`False`/`False`. Invariante novo em `tests/test_capability_parity.py`: eixo com flag e **sem produtor** falha, derivado do AST de `_runtime_reading` |
| ~~`requirements` está em `_PRECEDENCE` e nenhum extrator a alimenta~~ — **fechada** em 2026-08-04 **tirando a fonte**, não escrevendo o produtor | Fase 5b, ao ligar `athena`; medida e fechada na triagem de 2026-08-04 | Produtor **previsto e não escrito**, não vestígio: `knowledge/glue/runtime-matrix.md` seção 5 lista `requirements.txt`/`pyproject.toml` como a fonte de menor confiabilidade ("indica intenção, não runtime"), e a precedência foi desenhada com ela no fim por isso. Nenhum módulo de `sparkforge/facts/` lê manifesto de dependência, então a fonte nunca recebe nada. Fica declarada **com nota no código**, no padrão que `describe_cluster` usou até ter extrator — fonte sem produtor e sem nota é superfície que parece existir **A medição decidiu, e reprovou o produtor por duas razões que extrator nenhum conserta.** Com `{"terraform": {"glue_version": "4.0"}, "requirements": {"spark_version": "3.5.1"}}` o motor devolve `RuntimeContext.spark == "3.5.1"` e uma divergência. (1) **A posição no fim da tupla não protege nada:** `_resolve` prefere observação **direta** à derivação `:matrix` e só depois desempata por `_source_rank`, e leitura de manifesto é direta por construção — a fonte de menor confiabilidade do projeto vence a derivação da matriz oficial a partir de um `glue_version` observado no Terraform, e alimenta o `runtime_scope` de toda regra versionada. É o oposto exato da disciplina que a 5b declarou ("observação direta vence a matriz"). (2) `distinct_versions` sai **2**, e isso é `SF-ENV-001` em **P0** sobre `pyspark==3.5.1` fixado para teste local num job que roda em Glue 4.0 — configuração normal, não contradição, e o mesmo P0 falso que `_UNANIMOUS_SOURCES` recusou para múltiplos workgroups do Athena. E o que sobraria de honesto para ler é quase nada: `pyspark` no manifesto é a versão de teste local (o runtime embarca a sua), `requires-python` é **faixa** e não versão, e `pyiceberg` é outro artefato que não o jar do cluster. **O custo dos dois caminhos:** escrever o produtor são três capacidades independentes — o extrator, uma classe de rank nova em `_resolve` ("declaração de intenção nunca vence derivação de observação", que mexe na resolução de **todas** as fontes) e supressão de divergência no molde de `_UNANIMOUS_SOURCES` —, sobre a superfície de paridade que um extrator novo cobra, medida em `athena.workgroup`: **40 arquivos** fora de `build/` e `docs/` citam aquele extrator — 9 de teste, 9 de `sparkforge/`, 6 de fixture golden, 12 de agente entre canônico e os três espelhos, mais `parity.yaml`, `manifest.json`, `rules/catalog/athena.yaml` e `scripts/regen_fixtures.py`. Tirar a fonte custou **4 arquivos** e nenhuma mudança de comportamento (sem produtor, `RuntimeContext` nunca recebeu nada por ela). A seção 5 do knowledge **fica**: lá o manifesto é orientação para um **humano**, que sabe pesar "indica intenção"; o motor não tem classe de rank para intenção. Travada por `TestNoPrecedenceSourceIsAnUndeclaredProducerGap` — nome em `_PRECEDENCE` passa a exigir alguém que o emita, derivado do AST de `_runtime_reading` e `build_runtime` —, e o invariante acusou exatamente uma fonte. |
| ~~Runtime não é inferido dos facts coletados~~ — **fechada** na Fase 5a.2, commits `0513dc2` e `8a7d506` | Fase 5a, medido em 2026-08-01 | `build_runtime_context` monta o contexto só de flags da CLI. Todo `runtime_scope` falha fechado quando a versão não foi declarada, e nenhum extrator alimenta a detecção. A 5a contornou esvaziando os guardas que não guardavam versão nenhuma; os 8 que restaram seguem expostos. Trabalho da 5b, onde é necessário de qualquer forma para detectar EMR |
| ~~`proposed_change` cita AQE e `REBALANCE` sem ramo por versão~~ — **fechada** na Fase 5a.2, commit `3641f46`; `SF-UI-002` entrou, somando seis | Fase 5a, medido em 2026-08-01 | `SF-PY-005`, `SF-PY-009`, `SF-PY-010`, `SF-PQ-001` e `SF-UI-006` têm gatilho agnóstico mas recomendação de Spark 3.2. Com escopo vazio disparam onde o conselho pode não se aplicar — aceito, porque apagar um P0 real por causa de um bullet de remediação é pior |
| ~~`sdist`/`wheel` não são reproduzíveis bit-a-bit entre duas construções da mesma árvore~~ — **medida e fechada** em 2026-08-01, ver `[tool.hatch.build]` em `pyproject.toml` e `compare_builds` em `scripts/verify_wheel.py` | Fase 3a, commit `2b6311c` | **A dívida não se confirmou como escrita.** Foi registrada por inspeção, nunca medida: duas chamadas de `python -m build` sobre a mesma árvore produzem artefatos com **sha256 idêntico**, inclusive depois de `touch` em 1012 arquivos. `reproducible = true` já era o *default* do hatchling e fecha os quatro eixos (timestamp via `SOURCE_DATE_EPOCH` com fallback na constante 1580601600; permissão normalizada para 644/755; uid/gid 0 no tar; caminhada do FS ordenada). O que era real e foi fechado: a garantia era um **default implícito, sem contrato e sem teste**. Agora está declarada no `pyproject.toml`, medida a cada execução do gate (segunda build + comparação por sha256, com o relatório nomeando o campo do zip que divergiu) e travada por invariantes baratos em `tests/test_artifact_contents.py`. `--outdir` em `release.yml` **fica** — por "o byte publicado é o byte testado", que é propriedade separada da reprodutibilidade |
| ~~`unreachable_function_count` não detecta código morto~~ — **fechada** na Fase 5b | Fase 1 | `pyspark_ast` passou a emitir `pyspark.function_def` (um fact por função **definida**, com ou sem aresta) e `call_graph` semeia os nós com ele. A medida antiga virou `unreachable_from_entrypoint_count` (mesma conta, nome honesto: componente cíclico sem entrada) e entrou `unreferenced_function_count` + `attrs.unreferenced_functions`, que afirma "sem referência **neste corpus**" e nada além. Método, decorada e exportada em `__all__` ficam fora da população e são contadas em `opaque_caller_function_count`. Continua **sem regra**, agora por decisão registrada e travada por teste, não por defeito: ver `rules/catalog/callgraph.yaml` e a fixture `fixtures/callgraph/library_surface` |
| ~~`SF-DQ-003` não avalia check cujo alvo chega por parâmetro~~ — **fechada** na Fase 5c.2, commits `e046853` e `a7ebc1c` | revisão final da Fase 5c, medida em 2026-08-03 (desvio D-5c-11) | O índice de correlação é por escopo (D-5c-10), e persistência de um **parâmetro** vive no chamador. A 5c **omitia** a chave, porque `target_persisted: false` acusava a forma canônica de biblioteca Glue — validar num helper, `cache()` no chamador — sobre um DataFrame que **está** persistido. A omissão era a resposta certa **com a informação que o extrator tinha**; a 5c.2 ampliou a informação, não a política. **O mecanismo:** quando o alvo é parâmetro sem evidência local, `_target_persisted` consulta o **único** call site da função no mesmo módulo (`_persisted_in_caller`) e herda a evidência do argumento — `true` se o chamador persistiu antes de chamar, `false` se não. Herança que só resolvesse a favor teria deixado a regra morta com os goldens verdes, e é por isso que a fixture negativa `helper_validates_uncached_param` entrou junto: ela é a única do corpus em que `SF-DQ-003` dispara sobre parâmetro. **O preço, menor mas real:** a regra segue calada para chamador noutro arquivo (o extrator lê um módulo por vez, e essa fronteira não se moveu), para mais de um chamador, para chamada por atributo, para argumento que não é variável, para parâmetro religado dentro do helper, e para nome que o próprio chamador não liga nem persiste (D-5c2-3 — o `false` ali acusaria um DataFrame cacheado um escopo acima). **A previsão de que "as duas dívidas se fecham juntas ou não se fecham" não sobreviveu à medição** — ver a linha de `SF-DQ-002` logo abaixo |
| ~~`manifest.json` declara 18 skills e o disco tem 20~~ — **fechada** em 2026-08-03, commit `a06bd44` | nomeada pela Task 9 da Fase 5c | A lista `"skills"` não recebeu `review-emr-cluster` (desde a Fase 5b) nem `review-data-validation` (da 5c), e a segunda omissão aconteceu com a primeira ainda aberta — assinatura de invariante ausente, não de descuido. Fechada na ordem que a própria dívida prescrevia: **o teste primeiro**, `TestManifest::test_skills_list_equals_the_skills_on_disk`, derivado de `skills/` como o irmão de `"tools"` sempre foi derivado de `TOOLS` — que é por isso que aquele nunca divergiu —, e só então as duas entradas. Acrescentá-las sem o teste deixaria a terceira omissão para a próxima fase |
| ~~`attrs.check_type` é emitido e ninguém foi ensinado a lê-lo~~ — **fechada** em 2026-08-03, commit `10a4a32` | revisão final da Fase 5c | Nenhuma regra, agente ou skill citava a chave. Ela sai de graça do extrator (constante literal por detector), então não é mecanismo sem consumidor no sentido caro de `SF-EMR-009` — mas é chave emitida sem leitor, e a resposta foi ensinar o leitor em vez de declará-la descritiva. Onde ela paga é no `dq.unresolved`, que a carrega junto: sem ela o ponto cego diz **quantas** validações não foram lidas; com ela diz **qual tipo**, e "não li uma `VerificationSuite`" pede investigação diferente de "não li um `count()` artesanal" |
| ~~Nenhuma skill cita `report sign`; a assinatura chegou ao protocolo e ao executor, não ao procedimento~~ — **fechada** em 2026-08-04 | Fase 4b, medido ao fechar a fase | `grep -rl "report sign\|report_sign" skills/` sai vazio: quem segue uma skill de ponta a ponta — `sparkforge-diagnose`, `benchmark-pyspark-job`, `review-pyspark-pr` — chega ao relatório sem nunca ser mandado assiná-lo. A capacidade **é** alcançável (o passo 3 de `agents/executors/sf-synthesizer.md` a invoca, e é o que `tests/test_agent_coverage.py::test_no_tool_is_orphan` cobra), e `AGENT_PROTOCOL.md` a descreve — mas o caminho por skill, que é o terceiro degrau da escada de portabilidade, não a menciona. Nada obriga assinar: `strict_gates` guarda a **transição de fase**, não a emissão do relatório. Fica aberta porque fechá-la é editar `skills/` e regerar os três espelhos, fora do conjunto de arquivos desta task **Fechada em `skills/sparkforge-diagnose/SKILL.md`**, a skill que fecha a investigação: passo 9, entre `validate` e `handoff`, com `report sign` e `report verify`, o arquivo de **findings** (nunca o de facts), o que a assinatura **não** prova (autoria) e as duas coisas que continuam com o agente — preencher a seção de overrides, que nenhum código confere contra o case, e saber que nada obriga a assinar. **Dois espelhos, não três:** `scripts/sync_skills.py` leva `skills/` para `.claude/skills/` e `.agents/skills/`; `.github/` espelha agents e não skills — a redação anterior superestimava o custo. Travada por `TestOTerceiroDegrauAlcancaAAssinatura`, que lê o corpus de `skills/` **sozinho**: `TestEveryToolIsReachable` não pegava a lacuna porque lê o coordenador mais os executores que ele declara, e `sf-synthesizer` já citava a tool. |
| ~~O gate não vê órfão de diretório, e esse é o caminho do Devin~~ — **fechada** na revisão final da fase de perfis de subagente, 2026-08-04 | fase de perfis de subagente do Devin, medida ao revisar o gate da Task 2 | `check_agents`/`sync_agents` varriam `mirror_dir.glob("*.md")` — **raso, e só `.md`**. Reproduzido antes do conserto: `.agents/agents/rogue/AGENT.md` com `tools: Read, Bash` e `.agents/agents/nota.txt` passavam com `--check` em **exit 0**. O que fazia disso buraco e não sujeira é a seção 1.1 da pesquisa: `agents/<nome>/AGENT.md` é **layout de descoberta documentado do Devin**, com precedência `AGENT.md > AGENTS.md > agent.md > agents.md`. Dava para publicar perfil não revisado, com `tools:` arbitrário e **sem `## Não faz`**, invisível ao gate **e** ao teste de fronteira — que deriva de `PERFIS`, ou seja, das pastas-fonte, e nunca olha o espelho. A varredura passou a ser recursiva e de qualquer extensão, com `executors/` excluído por ter dono próprio (`check_executors`), e o `sync` apaga também o diretório que ficou vazio. Os dois casos viraram teste, mais a regressão que a recursão poderia introduzir: os cinco executores **não** viram órfãos dos agentes |
| ~~A fronteira de manutenção destrutiva não alcança a unidade que o Devin despacha~~ — **fechada** na revisão final da fase, 2026-08-04 | fase de perfis de subagente do Devin, medida ao revisar o D-4 contra o D-6 | O D-4 pôs a fronteira no **perfil**, e o spec chamou isso de "segunda rede" do D-6. Medido: o que `subagent: true` despacha é a **skill**, e o perfil só entra quando `agent:` o nomeia — em **duas** das doze. Nas outras **dez** o Devin escolhe, e a escolha inclui o built-in `subagent_general`, que tem acesso total e nenhum `## Não faz`: nessas dez a segunda rede podia não estar em escopo. Medido também o estado das doze: `## Não faz` em skill, **0 de 20**; skills dizendo que não executam ou para onde a confirmação vai, **0 de 12**; terminando em *"manutenção destrutiva só com confirmação explícita"*, **12 de 12** — sem dizer com quem, e dentro de um subagente mandando obter o **inalcançável** (`ask_user_question` é sempre negado, V-DV-10). A instrução foi **corrigida** nas doze, não duplicada, e o teste ancora na seção `## Protocolo` começando por uma **ausência**: a frase antiga não pode ter sobrado ao lado da correção. **As oito não-despacháveis ficaram com o texto antigo, de propósito** — elas rodam inline, onde a confirmação é alcançável |
| ~~A regra 9 do `AGENT_PROTOCOL.md` manda obter o inalcançável~~ — **fechada** na revisão final da fase, 2026-08-04 | fase de perfis de subagente do Devin, medida junto com a fronteira acima | *"Manutenção destrutiva exige confirmação explícita de escopo e retenção"* — sem sujeito, sem "não execute", sem dizer para onde a confirmação vai. Os **treze** perfis abrem declarando este documento contrato **superior** à prosa deles, então dentro de um subagente o contrato mandava buscar o que a plataforma nega. Agora a regra diz as duas metades: não executa, e a confirmação **sobe a quem pode ser perguntado** — com o recorte de subagente escrito, porque o modo de falha é mudo nos dois sentidos (segue sem confirmar, ou para sem dizer por quê) |
| ~~Três textos afirmavam que a omissão de `tools:` é fronteira de segurança~~ — **fechada** na revisão final da fase, 2026-08-04 | fase de perfis de subagente do Devin, medida contra a própria pesquisa de fontes | Não é *load-bearing*, e não teria como ser: os dois caminhos de descoberta estão ligados por default (`read_config_from` tem `agents_standard` e `claude`, **ambos `true`**), a fonte é **silenciosa** sobre precedência entre eles, e `allowed-tools` tem default *"all tools"* — omitir é a opção **mais permissiva**, e o mesmo perfil pode chegar pelo `.claude/agents/` **com** o campo. `README.md`, `AGENTS.md` e o limite declarado deste arquivo diziam ou sugeriam efeito; o `GUIA_DE_USO.md` tinha o não-sequitur ao lado (*"os dois formatos são aceitos"* é sobre `tools` contra `allowed-tools` como **nome de campo**, não sobre qual arquivo vence). **A decisão de não traduzir continua de pé pelo motivo que sempre teve** — honestidade sobre o que a fonte não diz —, e o limite declarado correspondente ganhou o argumento que lhe faltava. Quem carrega a fronteira está nomeado nos quatro textos: o `## Não faz` do corpo, byte-idêntico nos dois espelhos, e a declaração de despacho das doze skills |
| ~~O caminho de instalação não tinha teste nenhum, e é o único que publica~~ — **fechada** na varredura de completude, 2026-08-04 | varredura de completude do Devin, medida rodando a instalação num diretório limpo | **A propriedade estava certa e não estava guardada, que é a pior combinação para durar.** `scripts/install_skills.py --devin` copia `.agents/` — o espelho **renderizado** —, nunca `agents/`, a fonte. Medido no destino: os oito coordenadores e os cinco executores chegam sem `tools:`, doze skills chegam com `subagent: true` e duas com `agent:`, e `agents/` **não existe** no alvo. Mas `grep -rl install_skills tests/` só encontrava uma citação em `test_verify_wheel.py`, sobre a recusa de symlink: **nada testava o que ele instala.** Se um dia ele passasse a copiar a fonte, a decisão inteira da fase viraria nula pelo único caminho que o usuário de verdade roda, e a suíte continuaria verde — ela prova a renderização **dentro** do repositório. Fechada com quatro testes em `TestInstalacaoPublicaOEspelhoRenderizado`, e o invariante é o mesmo de `mirror_is_current`, agora medido no destino: o arquivo instalado é **exatamente** o que `render_agent(fonte, "devin")` produz — não uma cópia esperada, que envelheceria junto com a fonte |
| ~~Nome de perfil podia colidir com built-in do Devin, e nada acusava~~ — **fechada** na varredura de completude, 2026-08-04 | varredura de completude do Devin, medida contra a tabela de frontmatter da §1 da pesquisa | A tabela da fonte diz, sobre `name`: *"Identifier for the profile (**must not conflict with built-in profiles**)"*, e os built-ins são `subagent_explore` e `subagent_general`. **Medido: nenhum dos treze colide hoje.** O gate existe para o perfil que ainda não foi escrito, e o custo de errar é assimétrico — a fonte **proíbe** a colisão e **não diz o que acontece** nela; pular com aviso, sobrescrever o built-in ou recusar a sessão são todos plausíveis e nenhum está escrito, e o pior deles (ignorar em silêncio) faz o método sumir sem alarme, com `subagent_general` — acesso total, nenhum `## Não faz` — atendendo no lugar. Supor qual vale seria a mesma família de chute que o V-DV-8 recusou em `tools:`, agora num campo de **identidade**. `check_profile_names()` entrou em `check()`, que é o que o CI roda, e confere as **duas** fontes de identidade: o nome do arquivo (default do campo) e o `name:` do frontmatter (que vence quando existe) — um gate que só olhasse o caminho deixaria passar `revisor.md` com `name: subagent_general` |
| ~~`mcp` era declarado para Devin sem dizer como acioná-lo, e o texto dizia que `.mcp.json` já bastava~~ — **fechada** na varredura de completude, 2026-08-04 | varredura de completude do Devin, medida executando o carregador de catálogo | **A família de defeito que o próprio `parity.yaml` cita como razão de ser da regra — o transporte HTTP da Fase 1 — estava de volta, e com um agravante.** Três textos (`README.md`, as `notes` do `parity.yaml` e o docstring do adaptador) diziam que o Devin CLI usa stdio *"que é o que `.mcp.json` já configura"*. O Devin **importa** MCP do Claude Code (`read_config_from.claude`, e a tabela de importação lista `.mcp.json`), mas o `.mcp.json` deste repositório é o do **plugin**: ele parametriza `PYTHONPATH` e `SPARKFORGE_CATALOG` por `${CLAUDE_PLUGIN_ROOT}`, variável do carregador de plugin do Claude Code que **nenhuma página do Devin documenta expandir**. Medido, não inferido: com o valor literal no ambiente, `catalog_dir()` levanta `CatalogError: SPARKFORGE_CATALOG aponta para .../${CLAUDE_PLUGIN_ROOT}/rules/catalog, que nao e um diretorio existente`. Falha alto, que é o único consolo. Fechada com o procedimento **nativo** na §3.4 do `GUIA_DE_USO.md` — `.devin/mcp_config.json` com a chave `mcpServers`, os três escopos, `devin mcp add -s project`, o `serverUrl` do Desktop, e a razão de a configuração **não** declarar `env` —, mais a correção dos outros textos. A pesquisa já tinha tudo isso medido na §9 desde o primeiro dia; o que faltava era alguém escrever o procedimento |
| ~~`guia_devin_agents_subagents.md` estava na raiz sem marca de que é hipótese contradita~~ — **fechada** na varredura de completude, 2026-08-04 | varredura de completude do Devin, medida contra os onze vetos | Este arquivo é a doc trazida pelo usuário que **motivou** a pesquisa, e seis afirmações dele caíram — as seis estão nomeadas na seção da fase, logo acima. O `STATUS.md` registrava isso; **o arquivo não**. Quem chegasse nele por `grep max-nesting` ou `grep subagent_default_model` leria `swe-1.7` com ponto, um bloco JSON inteiramente inventado, `subagents_enabled` no aninhamento errado, *"crie perfis na pasta `agents/`"* e três atalhos que não existem — tudo com cara de referência. Fechada pela convenção do repositório, que é a mesma do parágrafo preservado do `parity.yaml`: **o corpo fica palavra por palavra**, e o desvio entra ao lado. Cabeçalho com a tabela dos seis pontos e o ponteiro para a fonte, **mais um marcador `> CONTRADITO` dentro de cada uma das seis seções** — porque quem chega por `grep` não passa pelo cabeçalho, e um aviso que só existe no topo protege só quem lê de cima |
| ~~A frase universal que o V-DV-1 derrubou sobrevivia em `playbook.py` e num docstring de teste~~ — **fechada** na varredura de completude, 2026-08-04 | varredura de completude do Devin, achada por `grep` fora dos arquivos que a fase tocou | *"Existe porque despacho de subagente é capacidade de HARNESS, não conteúdo deste repositório: **Devin, Codex e Copilot não têm equivalente**"* — a segunda metade é exatamente o contraexemplo do V-DV-1, e estava no docstring de módulo de `sparkforge/case/playbook.py`, o arquivo cuja razão de existir a frase explica. Mais duas leituras da mesma coisa (*"quem só tem `playbook` (Devin, Codex, Copilot CI)"*) em `playbook.py` e em `tests/test_router_agents.py`. A fase corrigiu `parity.yaml`, `README.md`, `AGENTS.md` e `GUIA_DE_USO.md`, e **não olhou o `.py` nem os testes**. Corrigidas as três no lugar, com o recorte que sobrou: `codex` e `copilot_ci` sempre; as três que despacham, quando o despacho estiver desligado — e o `playbook` é o **piso das cinco**, não o degrau de quem não tem despacho |

## Como manter este arquivo honesto

Ao fechar uma fase:

1. Atualize a tabela **Números correntes** rodando os comandos da coluna direita.
2. Marque a fase e cole a faixa de commits.
3. Escreva o par spec + plan em `specs/` e `plans/` com a data do merge.
4. Se um número de um spec antigo ficou obsoleto, **não edite o spec** — acrescente
   a linha na seção de desvios dele (§18 no caso da Fase 0) e aponte para cá.
