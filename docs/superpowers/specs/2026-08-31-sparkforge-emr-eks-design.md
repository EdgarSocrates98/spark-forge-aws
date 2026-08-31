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

### DV-1 — a D-4 tinha duas saídas, e a medida achou uma terceira, pior

**Medido na Task 1** (commit `c724c80`, `knowledge/emr-eks/runtime-matrix.md`),
lendo o índice de releases do EMR on EKS e as 34 páginas por família, uma a uma,
em 2026-08-31.

A D-4 previa duas saídas: matriz publicada, ou matriz não publicada como no
Serverless. **A AWS publica** — na linha `Supported applications` de cada release
note, cobrindo Spark, Iceberg, Hudi e Delta. Não cobre Hadoop (0 de 34 páginas)
nem Python (2 de 34, e em prosa, não em tabela).

O que a D-4 não previa é o que a comparação achou: **onde a matriz existe, ela
diverge da de EC2 em células reais.** Em 26 releases comparáveis, Spark diverge
em 4 e Iceberg em 6:

| Release | Divergência |
|---|---|
| `emr-7.7.0` | Iceberg `1.6.1-amzn-2` no EKS contra `1.7.1-amzn-0` no EC2 — **minor diferente**, o que muda a aplicabilidade de qualquer `SF-ICE-*` com range |
| `emr-6.5.0` | o EKS **não publica Iceberg nenhum**; o EC2 publica `0.12.0` |
| `emr-7.7.0`, `emr-7.2.0` | patch do fork Spark diferente (`-amzn-0` contra `-amzn-1`, e o inverso) |
| `emr-7.9.0`, `emr-7.8.0` | o EKS omite o sufixo `-amzn-N` que as vizinhas trazem |

A proibição da D-4 fica **mais forte**, não mais fraca, e a razão muda: a
`EMR_MATRIX` de EC2 não é inaplicável ao EKS por falta de fonte, como acontece no
Serverless. Ela é **medidamente errada**.

### DV-2 — `runtime_scope` pode carregar `spark`, e não pode carregar `iceberg`

Corolário da DV-1, e corrige a §D-4 e a Task 10 do plano, que assumiam o
precedente do Serverless (`{}` em todas).

Regra desta área **pode** restringir por versão de Spark. **Não pode** restringir
por Iceberg: `emr-7.7.0-java8-latest` não tem Iceberg (*"Iceberg is excluded from
the following Java 8 images"*), a linha `Supported applications` é publicada **por
família e não por variante**, e não existe tabela por variante. Derivar `iceberg`
do release label erraria exatamente nas imagens Java 8.

### DV-3 — a candidata (e) é vetada por fonte que recomenda o contrário

A §5 listava "imagem de container em tag mutável" como candidata sem análogo. A
Task 1 mediu que o exemplo oficial de URI de imagem base é
`.../spark/emr-7.13.0:latest`, e que o release label `-latest` é **recomendado**
*"to ensure that your Amazon EMR version always includes the latest security
updates"*. As *Considerations for customizing images* têm seis itens e nenhum
sobre imutabilidade de tag.

A regra acusaria a configuração que a AWS ensina. **Vetada**, e o veto é do tipo
mais caro de descobrir depois: não é falta de fonte, é fonte que diz o oposto.

### DV-4 — a candidata (b) volta à forma que o Serverless obrigou a abandonar

A §5 registrava "nenhum destino de log" como **segundo exemplar** de
`SF-EMRS-003`, com a leitura enfraquecida pelo armazenamento gerenciado.

A Task 1 mediu que **não existe** equivalente no EMR on EKS:
`managedLogs.allowAWSToRetainLogs` cobre só *"system namespace logs when running
a job using Native FGAC"*, sem default declarado e sem retenção publicada. E há
um `must` literal, repetido em duas páginas: *"you must configure your jobs to
send log information to Amazon S3, Amazon CloudWatch Logs, or both."*

A regra fica **mais forte** aqui do que no Serverless, não mais fraca. A decisão
do extrator de emitir `emrc.monitoring` mesmo com o bloco ausente (Task 5) estava
certa pela razão certa.

### DV-5 — as outras três candidatas, com a ressalva de cada uma

- **(a) segredo em claro** — sobrevive com fonte **mais fraca** que a das áreas
  irmãs. O *Warning* de texto claro é da ReleaseGuide e é de EC2; a página que
  enumera integrações com Secrets Manager tem seção para EC2 e para Serverless e
  **não tem para o EKS**. O apoio real é o *Response Syntax* de `DescribeJobRun`,
  que devolve `properties` sem redação. **Não recomendar `EMR.secret@` como
  remédio** — não há fonte que o declare disponível aqui.
- **(c) `persistentAppUI` desligado** — só com `DISABLED` **explícito**. O default
  não é publicado em lugar nenhum (API, CLI, guia), e presumi-lo seria
  materializar default sem fonte.
- **(d) `dynamicAllocation` sem `shuffleTracking`** — o requisito é nomeado, mas
  por **composição de duas páginas**, e nenhuma o chama de defeito.
  `configuration.html` declara uma disjunção (`shuffle.service.enabled` **ou**
  `shuffleTracking.enabled`); `running-on-kubernetes.html` fecha a disjunção
  (*"since Kubernetes doesn't support an external shuffle service at this
  time"*), mas essa frase vive dentro de *Stage Level Scheduling Overview*, num
  parágrafo sobre `ResourceProfile`. Entra como **relação entre propriedades**
  (§16 do `CLAUDE.md`), nunca como julgamento de valor isolado, e a composição
  fica escrita na regra.

### DV-6 — `-latest` quebra comparação entre execuções

Fora do escopo desta fase, e registrado aqui porque ninguém vai procurar depois:
duas execuções com o mesmo `emr-7.13.0-latest` podem ter rodado imagens
diferentes — a fonte diz que o ponteiro se move de propósito. Qualquer
`benchmark` que assuma runtime idêntico por `releaseLabel` idêntico está errado
por construção quando o sufixo é `-latest`.

### DV-7 — a forma do release label, e a regex que o plano errou

O plano (Task 2) trazia `^emr-(\d+)\.(\d+)(?:\.\d+)?(?:-[a-z0-9]+)?$`, que não
casa `emr-7.7.0-java8-latest` (dois segmentos de sufixo) nem
`emr-7.7.0-spark-rapids-java8-latest` (três), e casaria formas que não deve. As
seis formas medidas que a regex precisa tratar estão em
`knowledge/emr-eks/runtime-matrix.md`; `emr-spark-8.0.0-latest` e
`notebook-spark/emr-7.13.0-latest` são as duas que ela deve **rejeitar**.

### DV-8 — o `check_vnext_claims.py` não rodou na Task 1

Passou de 120 s e foi interrompido. Ele cobre números publicados em `docs/vnext/`
e `docs/harness/`, e a Task 1 não tocou nenhum dos dois. Fica registrado como
gate não exercitado, não como gate verde.

### DV-9 — o plano esqueceu um arquivo que um gate exige

Medido na Task 7 (commit `6ec0028`). A tabela de arquivos do plano nomeava as
duas listas manuais, o regenerador e as fixtures, e **não** nomeava
`tests/test_fixtures_golden_emr_eks.py`.

O gate `test_every_fixture_domain_has_a_golden_module` cruza diretório de fixture
contra módulo que declare `FIXTURES = ROOT / "fixtures" / "<dominio>"`. Criar
`fixtures/emr_eks/` sem esse módulo o reprova com `dominios de fixture sem modulo
golden: ['emr_eks']` — e o comentário do próprio teste nomeia EMR on EKS como o
risco para o qual ele foi escrito. O módulo entrou no mesmo commit.

Duas coisas menores medidas junto, e a segunda é armadilha real:

- `regen_fixtures.py` trata `sem_destino_de_log` como nome ambíguo — a fixture
  existe em `emr_serverless` **e** em `emr_eks` — e regenera as duas. A de
  Serverless voltou byte a byte idêntica.
- A varredura de corpus completo precisou de guarda `is_dir()` em
  `FIXTURES_EMR_EKS`: sem ela, uma regeneração total a partir de um checkout
  anterior a este commit morre com `FileNotFoundError` **depois** de já ter
  reescrito todos os corpora acima dele.

### DV-10 — dois testes da Task 6 passavam antes da implementação

Reportado pelo próprio implementador. Dos 6 testes novos de
`emrc.pod_template.unresolved`, `test_sem_pod_template_nao_ha_recusa` e
`test_a_recusa_nao_conta_como_unresolved_de_leitura` passavam **antes** de o kind
existir, porque asseguram dicionário vazio e contagem zero. Só 4 ficaram
vermelhos no passo de TDD.

Não é defeito de produto e não invalida nenhum dos seis; é registro de que o
vermelho prévio cobriu 4 e não 6. Vale para quem for reusar o par
positivo/negativo desta área: teste que passa vazio não prova o mecanismo.

O mesmo padrão apareceu na Task 7 por outra via, e ali é mais interessante: o
contrafactual da lista manual (`tirar a linha reprova nomeando os oito kinds`) é
**inmensurável antes de os goldens existirem** — sem golden carregando `emrc.*`,
remover a linha faz tudo passar. Ele foi medido depois do Step 5, e aí sim
reprova nomeando exatamente os oito.

### DV-11 — `--conf` com valor entre aspas fragmenta

Medido pelo implementador da Task 4. `sparkSubmitParameters` é uma string única e
o extrator a separa por espaço, sem consciência de aspas de shell. Um par como
`--conf "spark.foo=a b"` vira `spark.foo=a` mais um token solto `b`, que é
descartado em silêncio em vez de virar `malformed_conf`.

Os exemplos da AWS nunca mostram valor com espaço em `--conf`, e um
`spark-submit` de verdade recebe argv já separado em vez de uma string — então o
caso é plausível de nunca aparecer. Fica registrado como **limite declarado**, não
como dívida: fechá-lo é decidir adotar um tokenizador com aspas, e essa decisão
tem custo (divergir do que a API entrega) que ninguém mediu ainda.

### DV-12 — a DV-5(d) foi medida contra a versão FIXADA, e as duas leituras estão erradas

Medido pelo implementador da Task 10, relendo as duas páginas do Spark na
versão que este repositório fixa para fonte que sustenta regra. A Task 1 citou
`spark.apache.org/docs/latest/`; a versão fixada correspondente ao Spark de EMR
on EKS 7.5.0 (`3.5.2-amzn-1`) é `docs/3.5.6/`. Duas divergências, e a segunda
inverte a regra:

| Registrado na DV-5(d) | `docs/3.5.6/` | `docs/latest/` **hoje** |
|---|---|---|
| disjunção de **dois** ramos | **quatro** ramos (os dois, mais decommission de blocos de shuffle, mais `ShuffleDataIO` customizado — experimental) | quatro, texto idêntico |
| `shuffleTracking.enabled` com default **`false`** | default **`true`**, `Since Version: 3.0.0` | default **`true`** |
| a frase de Kubernetes vive em *Stage Level Scheduling Overview* | confere | confere |

A primeira divergência não é entre versões: o texto de dois ramos não é o que
`latest` publica hoje, é redação de uma série anterior do Spark. A segunda é a
que decide a forma da regra — **com default `true`, alocação dinâmica ligada
sem `shuffleTracking` declarado está no default SEGURO**, e uma regra que
disparasse por ausência acusaria configuração correta.

`SF-EMRK-004` exige, por isso, os **dois valores explícitos** —
`enabled=true` **e** `shuffleTracking.enabled=false` escritos — e a fixture
`alocacao_dinamica_no_default` é o golden negativo que trava a volta do erro. Os
ramos 3 e 4 da disjunção **não são observados** pela regra (o motor não sabe
exigir ausência de chave): estão declarados no `explanation`, e é por isso que
ela é `confidence: medium`. As duas URLs fixadas entraram em
`knowledge/sources.lock.json`, e `knowledge/emr-eks/job-run-configuration.md`
ganhou a §12 com a medida.

### DV-13 — a DV-5(a) não era implementável: o extrator não tinha detector de segredo

Medido pelo implementador da Task 10, ao escrever `SF-EMRK-001`.
`sparkforge/facts/emr_eks.py` não importava `facts/secrets.py` e não emitia
`attrs.secret_pattern_match` em nenhum dos dois kinds de configuração — regra
que citasse esse campo nunca dispararia, em silêncio. Pior: os dois valores
saíam **em claro** para o `facts.json`, que é o artefato commitado do handoff.

A Task 10 acrescentou `_mark_secret` ao extrator, aplicado às **duas**
superfícies (`emrc.configuration` e `emrc.spark_submit_parameters`), porque a
§7 do knowledge mede que as duas voltam sem redação no *Response Syntax*. O
`EXTRACTOR_ID` foi para `emr_eks@0.1.1`, e os quatro goldens existentes
mudaram só na proveniência.

**O que NÃO foi transportado do `emr_serverless.py`:** a precedência de
`EMR.secret@{{Nome}}` sobre a heurística. Lá ela existe para não acusar a
própria correção; aqui a anotação **não está documentada** para
`emr-containers`, e criar a isenção seria construir um ponto cego a partir de
uma suposição.

### DV-14 — a DV-2 permite `runtime_scope: {spark: ...}`, e as quatro regras declaram `{}`

Medido pelo implementador da Task 10. A DV-2 está certa e continua valendo: a
AWS publica matriz de release para EMR on EKS, então regra desta área **pode**
restringir por `spark`. A medida que faltava é a outra ponta: **nenhuma fonte
alimenta `RuntimeContext.spark` a partir de um artefato `emrc.*`**.
`sparkforge/facts/runtime_detect.py` deriva Spark de `GLUE_MATRIX` (por
`glue_version`), de `EMR_MATRIX` (por release de EMR on EC2 — proibida aqui pela
DV-2) e da leitura direta de `spark.runtime_version` do event log; o
`releaseLabel` do EKS não entra em nenhuma das três.

Uma regra desta área com `{spark: ">=3.0"}` passaria no golden — as fixtures
declaram `runtime` no `meta.yaml` — e seria **pulada em toda execução real**,
porque `in_scope` falha fechada. Golden verde por SKIP é pior que vermelho:
ninguém investiga o que passou. A afirmação de versão que `SF-EMRK-004` precisa
fazer mora no `explanation` dela, com a URL da versão fixada. A decisão se
reabre quando alguém ligar o `releaseLabel` do EKS ao `RuntimeContext`.

### DV-15 — `SF-EMRK-004` lê uma superfície só, e o ponto cego está declarado

Medido pelo implementador da Task 10 contra `sparkforge/rules/engine.py`. A
propriedade pode chegar por `applicationConfiguration` ou por
`sparkSubmitParameters`, e `when` tem um grupo `all` **ou** `any`, sem
aninhamento: "(A na superfície 1 ou A na 2) e (B na 1 ou B na 2)" não é
escrevível.

Das duas saídas, a regra escolhe a que erra para o lado do **silêncio**: ler
`applicationConfiguration` acusaria valor que pode ter **perdido** (a AWS
declara que *"the Spark submit parameters take precedence"*), e acusar
configuração correta é o pior defeito de regra. Ler `sparkSubmitParameters`
nunca acusa valor derrotado — ele só perde para `spark.conf.set` no código, que
é invisível para a área inteira.

**O ponto cego:** um job run que configure alocação dinâmica apenas por
`applicationConfiguration` não é julgado — não aparece em `findings` nem em
`skipped`. A fixture `shuffle_tracking_desligado` prova o outro lado: o
override diz `true`, a linha de submit diz `false`, e o achado sai. Fechar o
ponto cego exige o motor saber aninhar grupos, ou o extrator resolver a
precedência e emitir a configuração efetiva num fact só — a segunda é a saída
que `SF-EMR-008` e `graph.checkpoint_required` já usaram, e é decisão de desenho
de extrator, não de regra.
