# SparkForge AWS — estado por fase

**Atualizado em:** 2026-08-03
**Commit de referência:** fechamento da branch `feat/fase5c-dq`
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
| Testes | **3104** passando, 5 skipped | `python -m pytest -q` |
| Regras com `runtime_scope` não-vazio | **8 de 62**, todas sobre Glue | `load_catalog()` |
| Extratores de facts | **15** | `sparkforge/facts/*.py` |
| Fact kinds distintos emitidos | **97** | união de `EMITTED_KINDS` |
| Regras de diagnóstico | **62** | `load_catalog()` |
| Regras bloqueadas (`blocked_on`) | **0** | `rules/catalog/*.yaml` |
| Regras com golden que dispara | **62 de 62** | `tests/test_fixtures_kind_coverage.py` |
| Rotas determinísticas | **24** (`ROUTE-001`…`ROUTE-016`, `AGENT-001`…`AGENT-008`) | `rules/catalog/routing.yaml` |
| Tools MCP | **33** | `sparkforge.adapters.tools.TOOLS` |
| Tools alcançáveis a partir de algum coordenador | **33 de 33** | `tests/test_agent_coverage.py` |
| Coordenadores | **8** | `agents/*.md` |
| Executores | **5** | `agents/executors/*.md` |
| Fixtures golden | **99** em 17 domínios | `fixtures/` |
| Fontes oficiais vigiadas | **37** | `knowledge/sources.lock.json` |
| Pares de eval | 10 | `evals/fase0.xml` |

Regras por área: SF-PY 12, SF-EMR 9, SF-GLUE 6, SF-UI 6, SF-ATH 5, SF-ENV 5,
SF-ICE 5, SF-PQ 5, SF-DQ 4, SF-PLAN 4, SF-CG 1.

Fixtures por domínio: `pyspark` 17, `emr` 13, `iceberg` 8, `dq` 8, `plan` 7,
`runtime` 7, `terraform` 7, `fusion` 5, `s3` 5, `sql` 4, `athena` 3,
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
extratores, 97 kinds, 33 tools, 8 coordenadores, 99 fixtures em 17 domínios, 24
rotas. 3104 testes passando, 5 skipped.

**O que ficou de fora, por decisão registrada no spec:** resultado de execução
(`VerificationResult`, validation result do GE, `run_results.json` do dbt), GE
declarativo, dbt e schema declarado. Ver as duas primeiras nas dívidas abertas.

Faixa de commits: `032b44c` … `4dd6286`, mais o commit de documentação que fecha
a fase.

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
6. **Fases seguintes** — custo, orquestração, Redshift, streaming
7. **Trilha paralela** — mecanismo de recomendação com garantia declarada, quando a base de restrições estiver maior

## Dívidas abertas

| Dívida | Origem | Impacto |
|---|---|---|
| Fases 3b, 3c, 3d e a Fase 4 do roadmap (§16, rigor) não iniciadas | §16 do spec da Fase 0 | Ver as seções acima. A Fase 4 executada (coordenadores, executores e `playbook`) é numeração diferente — ver a nota "Atenção ao nome" na seção própria — e está **concluída** |
| Cobertura de EMR não existe | identificada ao fechar a Fase 3a | `RuntimeContext` não tem eixo de infraestrutura para EMR (release label, instance fleets, EMR Serverless, EMR on EKS); área `SF-EMR` inexistente. Spec escrito e revisado; plano da 5a escrito, 5b sem plano — ver seção acima |
| ~~O curinga `"*"` de `runtime_scope` não filtra nada~~ — **fechada** na Fase 5a, commit `fcb8402` | revisão adversarial do spec da Fase 5, 2026-08-01 | `version_scope.py` pula a checagem de presença da chave, então `{glue: "*"}` casa com qualquer runtime. 20 regras agnósticas ficaram etiquetadas como de Glue, e as 5 de infra Glue avaliam em silêncio fora do Glue. Fase 5a corrige |
| ~~`SF-GLUE-002` some de findings e de skipped ao mesmo tempo~~ — **fechada** na Fase 5a, commit `8815f53` | revisão adversarial do spec da Fase 5, 2026-08-01 | `requires_facts: tf.module_analyzed` é sentinela de "algum `.tf` foi lido", não de "há job Glue aqui": sem `aws_glue_job`, ela passa a barreira, avalia, dá falso, e desaparece dos dois lados. Fase 5a corrige |
| ~~`sparkforge judge` não tem flag `--emr`~~ — **fechada** em 2026-08-01, commit `b9c2c87` | Fase 5b, 2026-08-01 | Há `--glue`, `--spark`, `--python`, `--iceberg` e `--athena`; a release do EMR só entra no `RuntimeContext` pelo fact `emr.cluster`. Hoje inócuo — toda regra `SF-EMR` lê a release do próprio fact — mas quem sabe a release e não tem dump não consegue declará-la, e é assimetria com as outras cinco plataformas. **Entrou nos três verbos que aceitam runtime** (`judge`, `case open`, `runtime detect`) e nas três tools MCP que os espelham — deixar o MCP para trás recriaria a assimetria um nível acima. A flag perde para o dump (`cli` está abaixo de `describe_cluster` em `_PRECEDENCE`) e discordar dele vira divergência, nunca resolução silenciosa; concordar na **outra grafia** (`7.5.0` contra `emr-7.5.0`) deixou de virar divergência falsa, porque a comparação de identidade passou a normalizar por `_emr_key`. O conjunto esperado de flags agora é derivado de `RuntimeContext`, não de lista literal: eixo novo cobra flag **e** propriedade de tool no mesmo commit |
| ~~`PYSPARK_PYTHON` sai como `emr.configuration` e não alimenta a detecção de Python~~ — **fechada** em 2026-08-01, commit `9dea76b` | Fase 5b, Task 3 | A `EMR_MATRIX` omite `python` na série 6.x de propósito (a AWS lista `"2.7, 3.7"` como *instalados*), e o desenho previa `python` resolver quando `spark-env`/`PYSPARK_PYTHON` estivesse no dump. O extrator já emitia o valor cru e nada lia. **Ligado, com fronteira estreita:** só o nome de executável `pythonX.Y`, que carrega o minor por construção. `/usr/bin/python3` (só o major), `/usr/bin/python`, wrapper de nome arbitrário e `env python3.11` **não emitem** — a leitura entra como `describe_cluster`, acima da matriz e da flag, e versão errada com precedência alta alimenta `runtime_scope`. Só nível cluster: configuração de instance group é a **pedida**, e é para isso que `emr.configuration.unapplied` existe. Nenhum golden mudou — a fixture existente usa `/usr/bin/python3`, que é justamente o caso que não emite |
| ~~`athena.workgroup` carrega `engine_version` e não alimenta a detecção de Athena~~ — **fechada** em 2026-08-01 | Fase 5b, ao fechar a dívida acima | A mesma dívida virada do avesso: o número era observado, com artefato e sha256, e `RuntimeContext.athena` só era preenchível pela flag `--athena` — foi por isso que a Fase 5a esvaziou o `runtime_scope` das cinco `SF-ATH` (linha `{athena: "*"}` da tabela acima). **Ligado, e só quando é inequívoco:** o valor vai como geração inteira (`"3"`, nunca `"3.0"` — a AWS não publica nada entre as duas), sob a fonte nova `get_work_group`, colada em `describe_cluster` em `_PRECEDENCE` (mesma classe de evidência: API da AWS reportando o que está **em vigor**; a ordem relativa entre as duas nunca decide nada porque elas jamais disputam o mesmo componente). **Multiplicidade de workgroup não é divergência:** `legacy-etl` na 2 e `primary` na 3 é configuração normal de conta, e chamar isso de SF-ENV-001 seria P0 falso; unanimidade ou nada, e o número de cada workgroup continua no seu próprio fact, onde `SF-ATH-004` o lê. `athena.unresolved` **anula** a leitura em vez de ser ignorado por ela. Com isso `runtime_scope: {athena: ">=3"}` volta a ser possível — medido nas três fixtures de `fixtures/athena/`, `True`/`False`/`False`. Invariante novo em `tests/test_capability_parity.py`: eixo com flag e **sem produtor** falha, derivado do AST de `_runtime_reading` |
| `requirements` está em `_PRECEDENCE` e nenhum extrator a alimenta | Fase 5b, ao ligar `athena` | Produtor **previsto e não escrito**, não vestígio: `knowledge/glue/runtime-matrix.md` seção 5 lista `requirements.txt`/`pyproject.toml` como a fonte de menor confiabilidade ("indica intenção, não runtime"), e a precedência foi desenhada com ela no fim por isso. Nenhum módulo de `sparkforge/facts/` lê manifesto de dependência, então a fonte nunca recebe nada. Fica declarada **com nota no código**, no padrão que `describe_cluster` usou até ter extrator — fonte sem produtor e sem nota é superfície que parece existir |
| EMR Serverless e EMR on EKS sem cobertura | Fase 5b, por decisão registrada no spec | O extrator lê `describe-cluster` de EMR on EC2. Serverless tem worker config e pre-init capacity; EKS tem virtual cluster e job run. Nenhum dos dois tem fact, regra ou coordenador |
| ~~Runtime não é inferido dos facts coletados~~ — **fechada** na Fase 5a.2, commits `0513dc2` e `8a7d506` | Fase 5a, medido em 2026-08-01 | `build_runtime_context` monta o contexto só de flags da CLI. Todo `runtime_scope` falha fechado quando a versão não foi declarada, e nenhum extrator alimenta a detecção. A 5a contornou esvaziando os guardas que não guardavam versão nenhuma; os 8 que restaram seguem expostos. Trabalho da 5b, onde é necessário de qualquer forma para detectar EMR |
| ~~`proposed_change` cita AQE e `REBALANCE` sem ramo por versão~~ — **fechada** na Fase 5a.2, commit `3641f46`; `SF-UI-002` entrou, somando seis | Fase 5a, medido em 2026-08-01 | `SF-PY-005`, `SF-PY-009`, `SF-PY-010`, `SF-PQ-001` e `SF-UI-006` têm gatilho agnóstico mas recomendação de Spark 3.2. Com escopo vazio disparam onde o conselho pode não se aplicar — aceito, porque apagar um P0 real por causa de um bullet de remediação é pior |
| ~~`sdist`/`wheel` não são reproduzíveis bit-a-bit entre duas construções da mesma árvore~~ — **medida e fechada** em 2026-08-01, ver `[tool.hatch.build]` em `pyproject.toml` e `compare_builds` em `scripts/verify_wheel.py` | Fase 3a, commit `2b6311c` | **A dívida não se confirmou como escrita.** Foi registrada por inspeção, nunca medida: duas chamadas de `python -m build` sobre a mesma árvore produzem artefatos com **sha256 idêntico**, inclusive depois de `touch` em 1012 arquivos. `reproducible = true` já era o *default* do hatchling e fecha os quatro eixos (timestamp via `SOURCE_DATE_EPOCH` com fallback na constante 1580601600; permissão normalizada para 644/755; uid/gid 0 no tar; caminhada do FS ordenada). O que era real e foi fechado: a garantia era um **default implícito, sem contrato e sem teste**. Agora está declarada no `pyproject.toml`, medida a cada execução do gate (segunda build + comparação por sha256, com o relatório nomeando o campo do zip que divergiu) e travada por invariantes baratos em `tests/test_artifact_contents.py`. `--outdir` em `release.yml` **fica** — por "o byte publicado é o byte testado", que é propriedade separada da reprodutibilidade |
| Igualdade bit-a-bit não vale entre plataformas nem entre versões do backend | medido em 2026-08-01, ao fechar a dívida acima | Dois eixos sobrevivem à `reproducible = true`, e nenhum é do hatchling. (1) A versão do backend vaza para `WHEEL` como `Generator: hatchling X.Y.Z`, e `requires = ["hatchling>=1.25"]` não é pin — dois builds separados por um release do hatchling divergem. (2) O fluxo de deflate depende da implementação de zlib do interpretador: o CPython 3.14 do Windows usado na medição roda `zlib-ng` (`ZLIB_RUNTIME_VERSION = 1.3.1.zlib-ng`), o `ubuntu-latest`/3.11 do CI roda zlib padrão, e as duas comprimem os mesmos bytes de formas diferentes. Consequência: `verify_wheel.py` prova reprodutibilidade **dentro de uma plataforma**, que é o que o job `wheel` mede nos dois SOs separadamente — não entre elas. Fechar exigiria pinar `hatchling==` e nomear um interpretador de referência; nenhum dos dois foi feito, porque o artefato publicado já declara o `Generator:` que o produziu |
| ~~`unreachable_function_count` não detecta código morto~~ — **fechada** na Fase 5b | Fase 1 | `pyspark_ast` passou a emitir `pyspark.function_def` (um fact por função **definida**, com ou sem aresta) e `call_graph` semeia os nós com ele. A medida antiga virou `unreachable_from_entrypoint_count` (mesma conta, nome honesto: componente cíclico sem entrada) e entrou `unreferenced_function_count` + `attrs.unreferenced_functions`, que afirma "sem referência **neste corpus**" e nada além. Método, decorada e exportada em `__all__` ficam fora da população e são contadas em `opaque_caller_function_count`. Continua **sem regra**, agora por decisão registrada e travada por teste, não por defeito: ver `rules/catalog/callgraph.yaml` e a fixture `fixtures/callgraph/library_surface` |
| Great Expectations declarativo e dbt seguem sem cobertura | Fase 5c, por decisão registrada na §2 do spec | `great_expectations.yml` e as expectation suites em JSON são artefato declarativo **fora do código**, com parser próprio, e correlacionar suíte com a tabela que o job escreve exige casar por nome — heurística frágil, que produziria `SF-DQ-001` sobre um alvo adivinhado. dbt é mundo próprio e encosta no Spark só via `dbt-glue`/`dbt-spark`. As duas entram em fase própria, agora que os kinds `dq.*` existem para receber o resultado. Fora de escopo pela mesma razão: **resultado de execução** (`VerificationResult`, validation result do GE, `run_results.json` do dbt) — a ferramenta já disse que o check falhou, e repetir isso não acrescenta garantia nenhuma |
| `SF-DQ-003` não avalia check cujo alvo chega por parâmetro | revisão final da Fase 5c, medida em 2026-08-03 (desvio D-5c-11) | O índice de correlação é por escopo (D-5c-10), e persistência de um **parâmetro** vive no chamador: o extrator não pode vê-la. Emitir `target_persisted: false` ali acusava a forma canônica de biblioteca Glue — validar num helper, `cache()` no chamador — sobre um DataFrame que **está** persistido, e `SF-DQ-003` dispara justamente sobre `false`. A chave passou a ser **omitida** nesse recorte, e `engine._where_matches` reprova caminho ausente. **O preço é o inverso:** a regra fica cega para todo helper de validação, inclusive os genuinamente não persistidos — subnotificação, que é o lado aceito. Exceção: `cache`/`persist`/`unpersist` sobre o parâmetro **dentro** da própria função é evidência local e a chave volta. Fechar exige seguir o argumento para dentro da chamada (o mesmo trabalho que `SF-DQ-002` já declara não fazer para consequência atrás de helper), e as duas dívidas se fecham juntas ou não se fecham. Nenhuma fixture exercita o recorte novo — a garantia é de teste unitário |
| `manifest.json` declara 18 skills e o disco tem 20 | nomeada pela Task 9 da Fase 5c, 2026-08-03 | A lista `"skills"` do manifesto não recebeu `review-emr-cluster` (desde a Fase 5b) nem `review-data-validation` (desta fase). A causa é a mesma nos dois casos: **nenhum invariante compara a lista com `skills/`** — `grep -rn "review-emr-cluster"` sobre `.py`, `.json` e `.yaml` não devolve nada, então o esquecimento não tem quem o acuse. A assimetria com `"tools"` é o que a torna visível: as 33 tools batem, porque `tests/test_capability_parity.py` deriva o conjunto esperado do código em vez de confiar na lista. Fechar é escrever esse mesmo teste para skills, e só então acrescentar as duas — acrescentá-las sem o teste deixa a próxima skill cair no mesmo buraco |
| Normalização de HTML do `refresh_knowledge` não foi calibrada contra meses de execução real | 2026-07-31 | Se alguma página oficial mudar hash a cada leitura, ela vira alarme permanente. O primeiro PR ruidoso deve ajustar `normalize()`, não silenciar a fonte |

## Como manter este arquivo honesto

Ao fechar uma fase:

1. Atualize a tabela **Números correntes** rodando os comandos da coluna direita.
2. Marque a fase e cole a faixa de commits.
3. Escreva o par spec + plan em `specs/` e `plans/` com a data do merge.
4. Se um número de um spec antigo ficou obsoleto, **não edite o spec** — acrescente
   a linha na seção de desvios dele (§18 no caso da Fase 0) e aponte para cá.
