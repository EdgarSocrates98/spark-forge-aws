# SparkForge AWS — EMR on EKS: a terceira plataforma

**Data:** 2026-08-31
**Status:** **proposta**. Este documento registra o que se pretende em
2026-08-31; o que o repositório **é** está em [`../STATUS.md`](../STATUS.md).
**Fecha:** a metade restante da linha que a Fase 5d encolheu. O `STATUS.md`
registra que a 5d fez "EMR Serverless e EMR on EKS" passar a nomear só EKS —
esta fase é a outra metade.
**Base:** [Fase 5b](2026-08-01-sparkforge-fase5-emr-design.md) cobriu EMR on EC2;
[Fase 5d](2026-08-04-sparkforge-fase5d-emr-serverless-design.md) cobriu EMR
Serverless e é o molde que esta fase copia por decisão, não por inércia.
**Origem:** primeiro sub-projeto da decomposição do
`PROMPT MESTRE — EVOLUÇÃO TOTAL GLUE + EMR DO SPARKFORGE AWS.md`. Os outros três
sub-projetos estão na §10.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: a única lacuna binária do inventário

O inventário de 2026-08-31 mediu, por domínio do prompt mestre, o que existe e o
que falta. Quase toda linha é "existe, incompleto". Uma é zero:

| Domínio | Medido |
|---|---|
| Glue 4.0/5.0/5.1/6.0 | `knowledge/glue/runtime-matrix.yaml` traz 3.0, 4.0, 5.0, 5.1 e 6.0; `SF-MIG` 4 regras, `SF-SPARK4` 4; `docs/aws/glue/6.0/` com 8 documentos; 4 skills da fase H6 |
| `MigrationAssessment` | `sparkforge/migration/assessment.py` com agregação por degrau, gate de compatibilidade e gate de consumidor — **só Glue** |
| EMR on EC2 | `SF-EMR` 9 regras, `facts/emr_cluster.py` com 10 kinds, `knowledge/emr/` com 2 documentos, skill `review-emr-cluster` |
| EMR Serverless | `SF-EMRS` 6 regras, `facts/emr_serverless.py` com 6 kinds, `knowledge/emr-serverless/` com 2 documentos |
| **EMR on EKS** | **zero** — nenhum fact, nenhum coletor, nenhuma regra, nenhum documento de `knowledge/`, nenhuma fixture. A string aparece em prosa de skill e de spec, e em lugar nenhum que execute |
| `ReleaseDescriptor` / `ReleaseDiff` | **zero** — a busca por `release_diff`, `ReleaseDescriptor` e `release_descriptor` em `sparkforge/`, `rules/` e `knowledge/` não retorna nada |

Dê ao motor, hoje, um `describe-job-run` de EMR on EKS. O resultado é o mesmo
silêncio que a §1 da spec da 5d descreve para o Serverless: nenhum extrator
reconhece o artefato, nenhum kind nasce, nenhuma regra tem ingrediente, e o
relatório sai vazio. Vazio é indistinguível de "está tudo certo" — que é
exatamente o defeito que a 5d existiu para fechar numa plataforma e que
sobrevive nesta.

## 2. Objetivo

Fazer o motor ler os dois artefatos da API `emr-containers`, produzir facts com
namespace fechado, julgar o que a fonte primária sustentar, e **recusar por
nome** o que fica fora da fronteira.

### Não-objetivos, com razão registrada

- **Pod template.** O YAML apontado por `spark.kubernetes.driver.podTemplateFile`
  é artefato separado, quase sempre em S3, e resolver path→conteúdo é mecanismo
  que nenhum extrator do repositório tem hoje. Fica como `emrc.pod_template.unresolved`
  carregando o path declarado: o operador vê que existe e que não foi lido.
- **EKS cluster, nodegroup, Karpenter, pod pending.** Outro serviço AWS, outro
  IAM, outra matriz de versão (Kubernetes). É onde a causa raiz de pod pendente
  mora, e é por isso que entra depois e por conta própria — enfiá-la aqui é o
  caminho mais curto para a segunda arquitetura que a §2.2 do prompt mestre
  proíbe.
- **Terraform `aws_emrcontainers_*`.** O extrator de Terraform existe e a
  extensão é barata, mas cobre o lado de quem **pediu**, não o de quem **rodou**,
  e não fecha sintoma nenhum de performance.
- **Histórico de job runs.** `list-job-runs` espelha o que `glue.job_run` fez
  para Glue e merece a mesma fase própria.
- **`ReleaseDescriptor` / `ReleaseDiff`.** Sub-projeto 2 (§10).

## 3. Decisões de desenho

### D-1 — área nova, coordenador estendido

`SF-EMRK`, em `rules/catalog/emr-eks.yaml`. O coordenador **não** é novo:
`agents/emr-infra-reviewer.md` declara hoje `rule_areas: [SF-EMR, SF-EMRS,
SF-ENV]` e passa a declarar `SF-EMRK`. É exatamente o que a D-1 da 5d decidiu, e
a razão é a mesma: fato e regra se separam por plataforma porque o artefato é
outro; despacho não se separa, porque a pergunta que o operador traz ("meu Spark
na AWS está mal configurado") é uma só.

A skill, essa sim, é nova — `review-emr-eks`. Não estende `review-emr-cluster`
porque a §8.1 do prompt mestre é explícita em não esconder diferença de ciclo de
vida, isolamento e scaling dentro de regra de EC2, e a skill é o lugar onde o
operador lê a fronteira antes de trazer o artefato.

### D-2 — namespace `emrc.`, não `emr.eks.` nem `emrk.`

`emrc` vem de `emr-containers`, que é o nome do serviço na API e no CLI. A 5d
escolheu `emrs.` sobre `emr.serverless.` pela mesma razão que vale aqui: prefixo
de kind é fronteira de namespace verificada por `EMITTED_KINDS`, e um prefixo
que é sub-caminho de outro (`emr.` de `emr.eks.`) transforma toda checagem de
pertencimento em comparação de string com armadilha.

O par área/namespace fica assimétrico de propósito — área `SF-EMRK`, namespace
`emrc.` — pela mesma assimetria que já existe: `SF-EMRS` sobre `emrs.` casa, mas
`SF-EMR` sobre `emr.` também, e um terceiro membro precisa se distinguir dos
dois lados. `SF-EMRC` colidiria visualmente com `SF-EMR` numa lista de findings.

### D-3 — `sparkSubmitParameters` e `applicationConfiguration` são kinds separados

São duas superfícies de configuração com precedência diferente, e o operador tem
as duas ao mesmo tempo. Fundi-las num kind só apagaria a única pergunta que
importa quando as duas dizem coisas diferentes: **qual venceu**. A §19 do
`CLAUDE.md` já cobra procedência ("responde quem PEDIU, não quem venceu"), e o
extrator não pode destruir a informação antes de a regra chegar.

`emrc.spark_submit_parameters` sai com os `--conf` separados par a par, e com
`entryPointArguments` **fora** — argumento de aplicação não é configuração de
Spark, e confundir os dois faria o detector de segredo varrer a superfície
errada.

### D-4 — o release label não alimenta `RuntimeContext` até a matriz ser medida

Esta é a decisão mais cara da fase, e ela tem precedente doloroso no próprio
repositório.

A 5d mediu (D-5) que a AWS **não publica** matriz de release do EMR Serverless.
A consequência foi `runtime: {}` em toda fixture e `runtime_scope: {}` em toda
regra `SF-EMRS`, com a razão escrita no `meta.yaml` de cada uma — porque
restrição de versão sobre corpus sem versão deixa o golden verde por SKIP, que é
pior que vermelho.

O `STATUS.md` registra a dívida aberta que nasceu de contornar isso pelo lado
errado: `sparkforge judge --facts <facts de Serverless> --emr 7.5.0` grava no
contexto `spark`, `python` e `iceberg` derivados da `EMR_MATRIX`, **que é de EMR
on EC2**, sobre um conjunto de facts que não tem um único fact de EC2. Três
campos inventados sobre artefato que não declara nenhum deles.

Repetir esse erro numa **terceira** plataforma é o defeito mais previsível desta
fase. Por isso a regra é escrita antes do código: **a `EMR_MATRIX` de EC2 não é
reusada para EMR on EKS em hipótese nenhuma.** A Task 1 (§7) pesquisa se a AWS
publica matriz de release para EMR on EKS, e o resultado bifurca:

- **matriz publicada** → `knowledge/emr-eks/runtime-matrix.md` com fonte, data e
  confiança; eixo próprio no `RuntimeContext`; regras podem carregar
  `runtime_scope`; fixtures carregam `runtime:`.
- **matriz não publicada** → a 5d à risca: `runtime: {}`, `runtime_scope: {}` em
  todas as regras, e a razão medida escrita no `meta.yaml` de cada fixture, como
  a 5d escreveu.

Nenhum dos dois caminhos é o caminho de derivar de EC2.

### D-5 — candidata sem fonte primária não vira regra

A §5 lista candidatas, não regras. Cada uma carrega o estado de evidência, e a
que não tiver fonte primária ao fim da Task 1 sai como lacuna registrada com a
medida que a destravaria — que é o que a §20 do `CLAUDE.md` cobra de toda
recusa. O número final de regras é resultado da pesquisa, não promessa desta
spec.

### D-6 — overlap medido, não evitado por reescrita

Três das candidatas fazem o **mesmo julgamento** que uma regra já entregue em
`SF-EMR` ou `SF-EMRS`, sobre artefato diferente. A alternativa de generalizar as
três áreas numa só com discriminador de plataforma foi avaliada e recusada com o
custo na mão: reescreveria duas áreas entregues, mudaria ids de regra e
invalidaria os goldens de 33 fixtures (`emr` 14, `emr_serverless` 19) que hoje
passam.

O que fica no lugar: cada regra desta área declara, no comentário, se o
julgamento é **novo** ou é o **terceiro exemplar** do mesmo julgamento. A
triplicação vira limite declarado com o número na mão, em vez de ser negada ou
paga com reescrita de área verde.

## 4. Facts

Namespace `emrc.`, fechado por `EMITTED_KINDS` como nos 27 extratores
existentes, com a mesma asserção de que nenhum kind fora da lista escapa.

| Kind | Conteúdo |
|---|---|
| `emrc.virtual_cluster` | id, `state`, nome do cluster EKS, namespace, tipo do container provider |
| `emrc.job_run` | `releaseLabel`, `executionRoleArn`, `state`, `virtualClusterId` |
| `emrc.spark_submit_parameters` | cada `--conf` como par chave/valor; `entryPointArguments` fora (D-3) |
| `emrc.configuration` | `applicationConfiguration` achatada em `classification` + `properties`, na forma que `emr.configuration` já usa |
| `emrc.monitoring` | `s3MonitoringConfiguration`, `cloudWatchMonitoringConfiguration`, `persistentAppUI` |
| `emrc.pod_template.unresolved` | path declarado em `spark.kubernetes.*.podTemplateFile`, não lido (§2) |
| `emrc.unresolved` | `read_error` \| `malformed_json`, na convenção de `athena_workgroup.extract_athena_workgroup_path`: falha ao abrir vira fact, nunca exceção que derruba quem chamou |
| `emrc.analyzed` | marca de passagem, para que regra possa silenciar por ausência de fact e não por ausência de análise |

## 5. Regras candidatas

| Candidata | Julgamento | Overlap | Evidência necessária |
|---|---|---|---|
| segredo em claro em `applicationConfiguration` ou em `--conf` de `sparkSubmitParameters` | terceiro exemplar de `SF-EMRS-002` / `SF-EMR-002` | **triplicação real** — D-6 | nenhuma nova: o detector unificado da fase J0 pega por valor |
| nenhum destino de log em `monitoringConfiguration` | segundo exemplar de `SF-EMRS-003` | duplicação real — D-6 | shape da API |
| `persistentAppUI` desligado com log em S3 | análogo parcial de `SF-EMRS-004` | parcial | shape da API |
| `dynamicAllocation` ligado sem `shuffleTracking.enabled` | **novo** — no Kubernetes não há external shuffle service | nenhum | ⚠️ fonte primária de Spark on Kubernetes |
| imagem de container em tag mutável | **novo** | nenhum | ⚠️ fonte primária; sem ela, não entra (D-5) |

## 6. Superfície

Aditiva, nos nomes que `sparkforge/adapters/tools.py` já usa para as duas
plataformas irmãs:

```
sparkforge_analyze_emr_eks     espelha sparkforge_analyze_emr_serverless
sparkforge_collect_emr_eks     espelha sparkforge_collect_emr_serverless
CLI: sparkforge analyze emr-eks / sparkforge collect emr-eks
```

O coletor faz `DescribeVirtualCluster` e `DescribeJobRun` e grava os dois JSONs
no mesmo formato de artefato que `collect_emr_serverless` grava, com o mesmo
registro de sha256 — o operador que já tem os JSONs pula o coletor, e o extrator
lê os mesmos arquivos. É a paridade que a 5d estabeleceu e que o teste de
paridade cobra.

`agents/emr-infra-reviewer.md` ganha `SF-EMRK` em `rule_areas` e o vocabulário
de EKS na `description`. Skill nova `review-emr-eks`, declarando na abertura o
que **não** julga: capacidade de nó, pod pendente e pod template.

## 7. Pesquisa, antes do código

`knowledge/` inteiro tem zero linhas sobre EMR on EKS. A fase começa por
pesquisa, produzindo `knowledge/emr-eks/` no formato que o repositório usa:
prosa e tabelas, seção `## Fontes` com `Título. URL (retrieved AAAA-MM-DD)`, e
os parágrafos finais que declaram **o que a fonte não sustenta**, no padrão de
`knowledge/emr/cluster-configuration.md`.

Três perguntas que a pesquisa precisa responder e das quais o código depende:

1. A AWS publica matriz de release para EMR on EKS? (D-4 — bifurca a fase
   inteira)
2. `dynamicAllocation` sem `shuffleTracking.enabled` no Kubernetes é defeito que
   a fonte nomeia, ou é leitura nossa? Sem fonte, a candidata não entra.
3. Qual a precedência declarada entre `sparkSubmitParameters` e
   `applicationConfiguration` quando as duas tocam a mesma propriedade? (D-3
   preserva as duas; a regra precisa saber qual vence para não acusar a errada)

As fontes entram em `knowledge/sources.lock.json` por
`python scripts/refresh_knowledge.py --offline --update`.

## 8. Testes

O padrão do repositório, sem exceção:

- Golden bidirecional por fixture — facts e findings, regenerados por
  `scripts/regen_fixtures.py`, nunca escritos à mão.
- Toda regra com golden **positivo e negativo**. Regra com duas condições
  precisa que apagar qualquer uma delas deixe um golden vermelho.
- Todo kind de `EMITTED_KINDS` em algum golden — inclusive
  `emrc.pod_template.unresolved`, que não alimenta regra nenhuma nesta fase e
  ainda assim precisa de fixture.
- Extrator novo entra nas **duas** listas manuais: `EXTRACTORS` em
  `tests/test_fixtures_kind_coverage.py` **e** em
  `tests/test_rules_catalog_reachability.py`. Esquecer uma não quebra nada — é o
  modo de falha silencioso que o comentário da 5d documenta na primeira lista, e
  a razão de as duas entrarem no mesmo commit, **antes** de a área existir.
- Teste de fronteira em três direções, não duas: nenhuma regra `SF-EMR` dispara
  sobre artefato de EKS, nenhuma `SF-EMRS` dispara sobre artefato de EKS, e
  nenhuma `SF-EMRK` dispara sobre artefato de EC2 ou de Serverless.
- Teste que prove que `judge` não deriva eixo de runtime de EKS a partir da
  `EMR_MATRIX` de EC2 (D-4) — o contrafactual da dívida aberta.

Gates aplicáveis, por `docs/gates-por-mudanca.md`: área nova exige rota em
`rules/catalog/routing.yaml` e coordenador que a declare; extrator novo entra
nas duas listas e na medida de snippet; fonte nova entra em
`knowledge/sources.lock.json`; skill, duas tools e knowledge novo movem a
superfície e exigem `python scripts/check_surface_lock.py --update` com o
crescimento declarado no commit.

A suíte roda em seis lotes alfabéticos, um por vez; o lote dos
`test_fixtures_golden_*` se quebra outra vez. A árvore não se edita com a suíte
rodando.

## 9. Critérios de conclusão

- `describe-virtual-cluster` e `describe-job-run` de EMR on EKS produzem facts
  `emrc.*` com namespace fechado, e artefato malformado produz
  `emrc.unresolved` sem exceção.
- Toda regra de `SF-EMRK` que entrou tem fonte primária citada e golden positivo
  e negativo; toda candidata que não entrou está registrada como lacuna com a
  medida que a destravaria.
- O eixo de runtime de EKS ou vem de matriz publicada com fonte, ou fica vazio
  com a razão escrita — nunca derivado da `EMR_MATRIX` de EC2, e há teste que
  prova isso.
- `emr-infra-reviewer` alcança a área; a skill `review-emr-eks` declara a
  fronteira; CLI e MCP têm paridade.
- Os gates da §8 passam, e o crescimento da superfície está declarado no commit.
- O que ficou fora (§2) está escrito com causa, evidência ausente e artefato
  necessário.

## 10. Os outros três sub-projetos

Esta spec é o primeiro de quatro. Os demais, na ordem em que a dependência
sugere e sem posição de fila comprometida:

1. **EMR on EKS** — este documento.
2. **`ReleaseDescriptor` + `ReleaseDiff`** — abstração que hoje não existe em
   lugar nenhum; habilita `compare-emr-releases`. É transversal a Glue e EMR, e
   é onde o risco de segunda arquitetura é maior.
3. **`MigrationAssessment` para EMR** — estender `sparkforge/migration/` para
   releases EMR. Depende de (2) para ser determinístico.
4. **Iceberg v3 × consumidores × Lake Formation** — expandir
   `knowledge/storage/iceberg-feature-support.yaml` com as features do §7 do
   prompt mestre e cruzar com `ConsumerGraph` e FGAC. Independente dos outros
   três.

## 11. Desvios

Vazio. Preenchido quando a implementação medir algo que torne o texto acima
errado; a correção mora aqui, não na reescrita do que está acima.
