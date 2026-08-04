# SparkForge AWS — estado por fase

**Atualizado em:** 2026-08-04
**Commit de referência:** fechamento da branch `feat/fase4b-gates`
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
| Testes | **3479** passando, 5 skipped | `python -m pytest -q` |
| Regras com `runtime_scope` não-vazio | **8 de 66**, todas sobre Glue | `load_catalog()` |
| Extratores de facts | **16** | `sparkforge/facts/*.py` |
| Fact kinds distintos emitidos | **102** | união de `EMITTED_KINDS` |
| Regras de diagnóstico | **66** | `load_catalog()` |
| Regras bloqueadas (`blocked_on`) | **0** | `rules/catalog/*.yaml` |
| Regras com golden que dispara | **66 de 66** | `tests/test_fixtures_kind_coverage.py` |
| Rotas determinísticas | **24** (`ROUTE-001`…`ROUTE-016`, `AGENT-001`…`AGENT-008`) | `rules/catalog/routing.yaml` |
| Tools MCP | **36** | `sparkforge.adapters.tools.TOOLS` |
| Tools alcançáveis a partir de algum coordenador | **36 de 36** | `tests/test_agent_coverage.py` |
| Gates do case | **4**, sendo **2** com produtor declarado | bloco `gates` de `rules/catalog/routing.yaml` |
| Coordenadores | **8** | `agents/*.md` |
| Executores | **5** | `agents/executors/*.md` |
| Skills | **20** | `skills/*/SKILL.md` |
| Fixtures golden | **107** em 18 domínios | `fixtures/` |
| Fontes oficiais vigiadas | **37** | `knowledge/sources.lock.json` |
| Pares de eval | 10 | `evals/fase0.xml` |

Regras por área: SF-PY 12, SF-EMR 9, SF-GLUE 6, SF-UI 6, SF-ATH 5, SF-ENV 5,
SF-ICE 5, SF-PQ 5, SF-BENCH 4, SF-DQ 4, SF-PLAN 4, SF-CG 1.

Fixtures por domínio: `pyspark` 17, `emr` 13, `dq` 10, `iceberg` 8, `plan` 7,
`runtime` 7, `terraform` 7, `bench` 6, `fusion` 5, `s3` 5, `sql` 4, `athena` 3,
`callgraph` 3, `catalog` 3, `consumers` 3, `eventlog` 2, `infra_code` 2,
`tfdiff` 2.

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
EKS. Esta fase é EMR on EC2.

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

### Fase 4 do roadmap (§16) — rigor — **PARCIALMENTE CONCLUÍDA**

Distinta da "Fase 4 (executada)" acima (coordenadores, executores e espelho de
orquestração), que é a Fase 4 na nova numeração da seção "Direção" mais abaixo. Esta
continua sendo a Fase 4 do roadmap original, e o escopo da §16 tem quatro itens:

| Item da §16 | Estado |
|---|---|
| Benchmark automatizado antes/depois | **Fechado pela Fase 4a.** Verbo `benchmark`, cinco kinds `bench.*`, área `SF-BENCH`, e `benchmark_ref` citando `fact_id` |
| Validação funcional automatizada (contagem, schema, chaves, agregados) | **Aberto.** A 5c leu *onde* a validação está e o que ela custa; nada ainda **executa** a validação nem compara os dois lados de uma mudança por resultado. É a Fase 4c |
| Gates fail-closed opcionais | **Fechado pela Fase 4b.** `case open --strict-gates`, `set_phase` cobrando os gates da fase, override com motivo gravado, e o contrato de produtor como dado no bloco `gates` do `routing.yaml`. Fail-closed só para gate **com** produtor: os outros dois seguem advisory, pelo argumento da §5.5 da Fase 0, que continua válido onde ele se aplica |
| Assinatura de relatório | **Fechado pela Fase 4b.** `report sign` e `report verify` nos três adaptadores, sobre `findings/signature.py`. É assinatura de **correspondência** — texto, evidência e catálogo —, nunca de autoria |

O item que resta é o nome da **Fase 4c**. Enquanto ele existir, esta fase não é
"CONCLUÍDA" — marcar assim faria o `STATUS.md` afirmar rigor que o repositório não
tem, que é exatamente o que este arquivo existe para impedir.

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
| Testes de dados | ~~saída de Deequ, Great Expectations, dbt tests; schema declarado~~ — **o artefato previsto aqui não é o que entrou.** A Fase 5c leu o **`.py`** e vetou o resultado de execução: repetir o que a suíte já disse não acrescenta garantia. Ver a seção da 5c | `SF-DQ` — **entregue** |
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
   agregados): o terceiro item de rigor, e o único que exige artefato novo — o
   resultado de consultas que alguém roda. É ela que dá produtor a
   `functional_validation_defined` e o torna endurecível sem que nada da 4b mude
10. **Especialização por banco de dados** — uma fase por ferramenta, na ordem
    `SF-GRAPH`, `SF-DDB`, `SF-NEP`, `SF-MONGO`, decomposta em
    [`specs/2026-08-03-sparkforge-roadmap-bancos.md`](specs/2026-08-03-sparkforge-roadmap-bancos.md).
    O roadmap decide a decomposição e **recusa** decidir o conteúdo: os candidatos
    de regra são hipóteses, e cada fase abre com pesquisa de fontes — em quatro
    fases seguidas ela matou premissa que parecia óbvia no papel
11. **Fases seguintes** — custo, orquestração, Redshift, streaming
12. **Trilha paralela** — mecanismo de recomendação com garantia declarada, quando a base de restrições estiver maior. As frentes sem artefato da especialização em bancos — escolha de banco, modelagem de grafo, boas práticas genéricas — entram por aqui, e até lá viram restrição auditável em `knowledge/`

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

**Contagem: 1 dívida, 4 fases, 7 limites declarados — 12 linhas.** Eram **13
abertas** de 26 quando esta branch abriu; duas fecharam aqui (`requirements` em
`_PRECEDENCE` e a assinatura ausente das skills), e a linha dos gates virou duas
ao se partir. De treze linhas que se liam como atraso, **uma** é dívida de
verdade.

### Dívidas (1)

Fechar exige escrever código. Nada aqui espera fase nem depende de reverter
decisão.

| Dívida | Origem | Impacto |
|---|---|---|
| `SF-DQ-002` acusa validação cuja consequência está atrás de um helper | Fase 5c (`_enforcements`), **medida de novo** na Task 3 da Fase 5c.2, 2026-08-03 | **Dívida, não fase — e é o outro caso ambíguo.** Três coisas a separam de uma fase. (1) **A especificação do conserto já está escrita dentro da própria linha** — travessia de corpo de callee por parâmetro, com decisão própria sobre religação, alias e `def` aninhado; fase é trabalho que ainda precisa de spec, e esta tem o dela. (2) O escopo é **um predicado** de um extrator que já existe: `_reader`, `_read_of` e `_reads_this_check` já funcionam, e só `_abort_in` não atravessa. (3) O defeito é de **regra já entregue** que erra para o lado da acusação — `SF-DQ-002` em P1 sobre quem protegeu o pipeline —, e isso é assinatura de dívida, não de escopo não construído. Adiada com o custo medido na mão, que é a definição de dívida deste inventário. `aborta_se(ruins)` num helper que faz `if ruins > 0: raise` não produz `dq.enforcement`, e `SF-DQ-002` dispara sobre `absent: dq.enforcement` — a regra acusa exatamente quem protegeu o pipeline. **Medido, não presumido:** sobre a fonte de nove linhas do gate, o motor devolve `SF-DQ-002 (P1)` e `SF-DQ-003 (P2)`, e a instrumentação de `_enforcements` mostra onde está a lacuna — `_reader` **já aceita** `aborta_se(ruins)` como leitor, `_read_of` **já vê** o nome `ruins`, e `_reads_this_check` **já devolve** `True`. O único predicado que falha é `_abort_in`, que procura o aborto nos ramos **deste** escopo e o aborto está no corpo de outra função. **Por isso a máquina da 5c.2 não serve:** a parte que ela poderia emprestar (resolver a chamada e mapear argumento e parâmetro) é precisamente a parte que já funciona, e o que falta é ler o corpo do callee e decidir se ele aborta **condicionalmente ao valor recebido** — travessia nova, com limites próprios. Nenhum dos limites da 5c.2 transfere: "um só call site" não diz nada sobre o que a função faz, porque um helper chamado de dez lugares aborta ou não aborta independentemente disso. Implementar assim mesmo, para poder dizer que as duas fecharam, produziria uma máquina com garantia inventada num kind cujo erro cai do lado da acusação. **Fica aberta com o custo na mão**, e o que ela exige está nomeado: travessia de corpo de callee por parâmetro, com decisão própria sobre religação, alias e `def` aninhado |

### Fases (4)

Trabalho planejado. A coluna de impacto abre dizendo **onde a fase está
prevista** — e uma delas registra que a sua ainda não tem posição na fila.

| Trabalho | Origem | Onde está previsto, e o impacto |
|---|---|---|
| Fases 3b, 3c e 3d não iniciadas; a Fase 4 do roadmap (§16, rigor) está em **um quarto** item aberto | §16 do spec da Fase 0 | **Fase, não dívida.** Fechar as três (3b, 3c, 3d) e o item de rigor que resta é executar trabalho que já tem lugar na seção *Ordem* — a validação funcional automatizada é a **Fase 4c**, item 9. Contá-las aqui fazia o roadmap contar duas vezes. Ver as seções acima. Dos quatro itens de rigor, três fecharam — benchmark (4a), gates fail-closed e assinatura (4b) —, e resta a validação funcional automatizada, que é a **Fase 4c**. A Fase 4 executada (coordenadores, executores e `playbook`) é numeração diferente — ver a nota "Atenção ao nome" na seção própria — e está **concluída** |
| Dois dos quatro gates seguem advisory mesmo sob `strict_gates` — metade `functional_validation_defined` | Fase 4b, por decisão registrada na §1 do spec | **Fase — metade de uma linha que se parte, porque as duas metades têm natureza oposta e o texto original já dizia isso.** Advisory hoje **é o critério da fase 4b**, sucesso declarado e não atraso; o endurecimento chega com a **Fase 4c**, item 9 da *Ordem*, sem tocar em Python. `dominant_bottleneck_identified` e `functional_validation_defined` não têm `satisfied_by`, e gate sem produtor **nunca** entra na lista de bloqueio — é o critério da fase, não uma omissão. As duas metades envelhecem de formas opostas, e isso é o que vale registrar. `functional_validation_defined` **fecha na Fase 4c**: quando ela entregar o produtor, basta declarar `satisfied_by` e `guards_phases` no bloco `gates` do `routing.yaml`, sem tocar em Python. |
| Great Expectations declarativo e dbt seguem sem cobertura | Fase 5c, por decisão registrada na §2 do spec | **Fase, e a própria linha já dizia:** "as duas entram em fase própria, agora que os kinds `dq.*` existem para receber o resultado". A linha estava certa e no lugar errado. `great_expectations.yml` e as expectation suites em JSON são artefato declarativo **fora do código**, com parser próprio, e correlacionar suíte com a tabela que o job escreve exige casar por nome — heurística frágil, que produziria `SF-DQ-001` sobre um alvo adivinhado. dbt é mundo próprio e encosta no Spark só via `dbt-glue`/`dbt-spark`. As duas entram em fase própria, agora que os kinds `dq.*` existem para receber o resultado. Fora de escopo pela mesma razão: **resultado de execução** (`VerificationResult`, validation result do GE, `run_results.json` do dbt) — a ferramenta já disse que o check falhou, e repetir isso não acrescenta garantia nenhuma |
| EMR Serverless e EMR on EKS sem cobertura | Fase 5b, por decisão registrada no spec | **Fase, e a única cuja fase não tem posição na *Ordem*.** Cobrir uma plataforma nova é fase inteira — extrator, kinds, regras e coordenador, que foi o formato da 5b para EMR on EC2 —, e a decisão registrada no spec da 5b foi sobre **quando**, não sobre **se**. Enfileirá-la é decisão de roadmap, e a triagem não a toma por conta própria: registra que ela está fora da fila. O extrator lê `describe-cluster` de EMR on EC2. Serverless tem worker config e pre-init capacity; EKS tem virtual cluster e job run. Nenhum dos dois tem fact, regra ou coordenador |

### Limites declarados (7)

Decisão tomada com o custo registrado. "Fechar" cada uma destas significa
**reverter** a decisão que a criou — e a coluna de impacto abre nomeando qual.
Sete linhas que pareciam atraso e são, em todos os casos, escolha com motivo
escrito.

| Limite | Origem | Qual decisão o fecha, e o impacto |
|---|---|---|
| Dois dos quatro gates seguem advisory mesmo sob `strict_gates` — metade `dominant_bottleneck_identified` | Fase 4b, por decisão registrada na §1 do spec | **Limite declarado — a outra metade da mesma linha.** Fechar exige **reverter uma decisão da Fase 0**: ou um kind que declare dominância, e aí a evidência passa a carregar julgamento contra o contrato, ou fazer `set_phase` ler findings, que é outra camada. `dominant_bottleneck_identified` e `functional_validation_defined` não têm `satisfied_by`, e gate sem produtor **nunca** entra na lista de bloqueio — é o critério da fase, não uma omissão. As duas metades envelhecem de formas opostas, e isso é o que vale registrar. `dominant_bottleneck_identified` **não tem caminho previsto**: dominância é ordenação entre candidatos, nenhum dos 102 kinds a afirma, e o que mais se aproxima é um Finding — que não é Fact, mora em `findings_index` e não chega a `set_phase`. Endurecê-lo exigiria ou um kind que declare dominância (e aí a evidência passaria a carregar julgamento, contra o contrato da Fase 0) ou fazer `set_phase` ler findings (outra camada). Fica advisory com `advisory_reason` escrito no catálogo, e é a linha honesta a manter |
| O gate confere presença de kind, nunca conteúdo de fact — e **nenhum benchmark destrava** | Fase 4b, limite declarado em três lugares; **remedida** na revisão final e ampliada | **Limite declarado.** A alternativa que fecharia — passar facts inteiros ao gate — **segue recusada pelos dois motivos originais**, e o que foi feito no lugar foi declarar o recorte em três pontos do produto. Fechar é reverter essa recusa e construir duas capacidades que hoje não existem em verbo nenhum. `_gates_blocking` pergunta se o kind está no conjunto de kinds; ele **não** pergunta se o `bench.run_delta` é do job certo, se os dois lados do benchmark são o mesmo job, nem se o `callgraph.reachable_spark_work` cobre todo o `scope.entrypoints`. **A versão anterior desta linha dizia "um benchmark de outro job destrava", e subdimensionava o custo por uma ordem de grandeza.** Medido: **duas linhas de JSON escritas à mão** — `{"kind": "bench.run_delta", "subject": {}, "measures": {}, "attrs": {}, "provenance": {}}` e a irmã com `callgraph.reachable_spark_work` — levam um case com `strict_gates: true` de `intake` a `report` com rc=0. Não é preciso benchmark nenhum, nem job nenhum, nem execução nenhuma: `provenance` vazia passa, porque **nada a valida** — `_fact_kinds_for_gates` projeta `{fact.kind for fact in ...}` e descarta o resto. O custo de contornar o rigor saiu de uma flag (`--gate-value true`, que o D-4b-2 fechou) para um arquivo, e um arquivo é mais barato do que a redação sugeria. A alternativa — passar facts inteiros — segue recusada pelos dois motivos originais: puxaria o índice de facts para dentro do `store`, e faria o gate precisar saber o que é "o job certo", que é julgamento. **O que foi feito em vez de fechar:** declarar o recorte onde ele opera — bloco `gates` do `routing.yaml`, docstring de `set_phase`, mensagem de bloqueio. Fechar de verdade exige duas capacidades novas e independentes: validar `provenance` (que hoje nenhum verbo faz, em nenhum kind) e correlacionar `scope` com o conteúdo dos facts |
| `report verify` não isola o corpo com autoridade | Fase 4b, desvio D-4b-14, medido ao implementar | **Limite declarado.** Fechar exige assinar o bloco junto (recursivo) ou mover a declaração para um arquivo lateral assinado — e o segundo é exatamente o modo de falha de handoff que o **D-4b-14 recusou**, três arquivos no lugar de um. A assinatura é um hash único das três partes **de então**; não há como recomputá-las em separado a partir dele. A isolação que o critério 8 do spec pede vem de o **bloco declarar** o que foi assinado — e o bloco mora fora do hash por construção, logo é editável por quem editar o relatório. Consequência: `checks.body` não distingue "o corpo foi editado" de "o próprio bloco foi", e a saída enuncia as duas leituras em vez de escolher a que não pode provar. O veredito `valid` é preservado porque **nunca** sai do bloco: sai das três checagens juntas, e um bloco adulterado para fechar com o corpo passa a divergir dos findings reais. Fechar exigiria assinar o bloco junto (recursivo) ou mover a declaração para um arquivo lateral assinado — nenhum dos dois foi feito, e o segundo trocaria um arquivo por dois, que é o modo de falha de handoff que este projeto evita. **Uma das três atribuições saiu desta ambiguidade na revisão final** (desvio D-4b-24): a versão da assinatura agora é declarada no bloco, e relatório de versão anterior sai como `version_mismatch` em vez de "corpo editado" |
| `verify` não sabe verificar o corpo de um relatório assinado sob outra `SIGNATURE_VERSION` | Fase 4b, desvio D-4b-24, medido ao fechar a revisão final | **Limite declarado, e esta linha é a declaração que o D-4b-24 disse faltar.** O suporte é de **uma** normalização, por decisão: preservar `normalize_body_v1`, `v2`, … é código que só envelhece. Relatório de outra versão se **reassina**, nunca se reverifica. O desvio mediu que a alternativa barata era declarar isso por escrito e não a fez; está declarado aqui, e nada no código mudou. A build guarda **uma** normalização — a dela. Quando o `signature_version` declarado no bloco não é o corrente, `checks.body` sai como **não avaliável** e fica fora de `diverged`, porque recomputar responderia sobre a regra de agora e nunca sobre o corpo de então. É a resposta honesta, e é menos do que o leitor gostaria: um relatório antigo não pode ser reverificado, só reassinado — e reassinar prova correspondência com a evidência de **hoje**, não com a de quando ele foi emitido. Fechar exigiria preservar as normalizações antigas (`normalize_body_v1`, `v2`, …) e despachar por versão, que é código que só envelhece; a alternativa mais barata, e não feita, é declarar por escrito que o suporte é de uma versão só. Hoje há uma versão e nenhum relatório afetado: a dívida é do primeiro dia em que a normalização mudar |
| A tabela de overrides do relatório não é correlacionada com o case | Fase 4b, desvio D-4b-23, medido ao fechar a revisão final | **Limite declarado.** Fechar exige `report sign --repo` e `report verify --repo`, e o **D-4b-23 mediu as duas saídas**: opcional, a checagem some em silêncio; obrigatório, o pacote de handoff vira três arquivos — o mesmo que o D-4b-14 recusou. A seção 9 de `templates/performance-report.md` manda declarar gate, data e motivo de cada override, e por estar **dentro** do corpo assinado ela ganha uma garantia real: apagá-la depois de `report sign` invalida a assinatura, e `verify` acusa em `body` (com teste). O que **não** existe é qualquer código que compare a tabela com o `gate_overrides` do `case.yaml`: um relatório que omite um override, ou que declara um que nunca houve, assina e verifica normalmente. Fechar exigiria `report sign --repo` e `report verify --repo`, e o custo foi medido no D-4b-23 — com `--repo` opcional a checagem some em silêncio, e obrigatório o pacote de handoff vira três arquivos, que é o modo de falha que o D-4b-14 já recusou |
| Igualdade bit-a-bit não vale entre plataformas nem entre versões do backend | medido em 2026-08-01, ao fechar a dívida acima | **Limite declarado.** Fechar não é escrever código que falta: é **reverter a decisão** de não pinar `hatchling==` e não nomear um interpretador de referência — as duas recusadas, com o motivo na própria linha (o artefato publicado já declara o `Generator:` que o produziu). Dois eixos sobrevivem à `reproducible = true`, e nenhum é do hatchling. (1) A versão do backend vaza para `WHEEL` como `Generator: hatchling X.Y.Z`, e `requires = ["hatchling>=1.25"]` não é pin — dois builds separados por um release do hatchling divergem. (2) O fluxo de deflate depende da implementação de zlib do interpretador: o CPython 3.14 do Windows usado na medição roda `zlib-ng` (`ZLIB_RUNTIME_VERSION = 1.3.1.zlib-ng`), o `ubuntu-latest`/3.11 do CI roda zlib padrão, e as duas comprimem os mesmos bytes de formas diferentes. Consequência: `verify_wheel.py` prova reprodutibilidade **dentro de uma plataforma**, que é o que o job `wheel` mede nos dois SOs separadamente — não entre elas. Fechar exigiria pinar `hatchling==` e nomear um interpretador de referência; nenhum dos dois foi feito, porque o artefato publicado já declara o `Generator:` que o produziu |
| Normalização de HTML do `refresh_knowledge` não foi calibrada contra meses de execução real | 2026-07-31 | **Limite declarado, e de espécie diferente das cinco acima — é o caso ambíguo desta triagem.** Fechar não é reverter decisão nem escrever código: `normalize()` existe e funciona, e o que falta é **medição que ainda não aconteceu**. Chamar de dívida lançaria como atraso o que ninguém pode pagar hoje, que é o erro de contagem que esta triagem existe para corrigir. O que está **decidido e registrado** é a resposta ao dado quando ele chegar, e é isso que a torna limite e não incógnita: o primeiro PR ruidoso ajusta `normalize()`, nunca silencia a fonte. Esse PR é o gatilho que a converte em dívida com conserto conhecido. Se alguma página oficial mudar hash a cada leitura, ela vira alarme permanente. O primeiro PR ruidoso deve ajustar `normalize()`, não silenciar a fonte |

### Fechadas — registro histórico (15)

Fechar não é apagar: a linha fechada é o que impede a dívida de voltar sem que
alguém perceba, e o modo de falha da linha de EMR — sobreviveu fechada por três
fases — é o motivo de o registro ficar aqui, e não sumir.

| Dívida | Origem | Impacto |
|---|---|---|
| ~~Cobertura de EMR não existe~~ — **fechada** pela Fase 5b em 2026-08-01, merge `59c27e2` | identificada ao fechar a Fase 3a | `RuntimeContext.emr` existe e guarda a release numérica, `EMR_MATRIX` tem guard de drift assimétrico contra o knowledge, `emr_cluster.py` lê o dump de `describe-cluster` e os cinco que o completam, e a área `SF-EMR` tem 9 regras com coordenador próprio. **A linha sobreviveu fechada por três fases** — a 5b marcou a fase como concluída na seção própria e não voltou aqui, e as varreduras seguintes conferiram números, não vereditos. Fica como lembrete do modo de falha: inventário de dívida só é confiável se fechar dívida for parte de fechar fase. O que **continua aberto** do escopo original está na linha própria — EMR Serverless e EMR on EKS |
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

## Como manter este arquivo honesto

Ao fechar uma fase:

1. Atualize a tabela **Números correntes** rodando os comandos da coluna direita.
2. Marque a fase e cole a faixa de commits.
3. Escreva o par spec + plan em `specs/` e `plans/` com a data do merge.
4. Se um número de um spec antigo ficou obsoleto, **não edite o spec** — acrescente
   a linha na seção de desvios dele (§18 no caso da Fase 0) e aponte para cá.
