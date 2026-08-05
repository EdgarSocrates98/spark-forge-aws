# SparkForge AWS — Fase 5d: EMR Serverless

**Data:** 2026-08-04
**Status:** **implementada** e fechada em 2026-08-05, branch
`feat/fase5d-emr-serverless`. Este documento é registro do que se pretendia em
2026-08-04; o que o repositório **é** está em [`../STATUS.md`](../STATUS.md), e a
§11 abaixo lista os pontos em que a medição tornou o texto acima errado.
**Fecha:** a primeira metade da linha "EMR Serverless e EMR on EKS" da seção
*Trabalho previsto* do [`../STATUS.md`](../STATUS.md) — a única linha do roadmap
que não tinha posição na *Ordem*.
**Base:** [Fase 5b](2026-08-01-sparkforge-fase5-emr-design.md) cobriu EMR on EC2
e registrou esta como fase seguinte.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o silêncio que o motor produz hoje

Dê ao motor, hoje, um `get-application` de EMR Serverless. Isto acontece
(`sparkforge/facts/emr_cluster.py:1155-1161`):

```python
raw_cluster = payload.get("Cluster")
if raw_cluster is None:
    facts.append(_unresolved(path, "missing_cluster", provenance))
    return _finish(facts, path, provenance)
```

Saem dois facts: `emr.unresolved` com `reason: missing_cluster`, e a sentinela
`emr.analyzed` com todos os contadores em zero. Nenhuma exceção, nenhuma regra
disparada, e **nenhuma classificação errada** — o roteamento é pelo verbo
`analyze emr-cluster`, não por inspeção de conteúdo.

Esse comportamento está certo. É o invariante do projeto funcionando: o que o
motor não sabe ler vira `unresolved` **contado**, nunca omissão silenciosa.

Mas é silêncio. E a lacuna é maior do que "faltam algumas regras": **nenhuma das
nove regras `SF-EMR` sobrevive à travessia**. Cinco amarram a EC2 pelo campo que
leem — instance fleet, managed scaling, papel `MASTER`/`CORE`, `BOOTSTRAP_FAILURE`,
node label do YARN. As outras quatro têm mecanismo genérico e fact de EC2:
"destino de log ausente" e "auto-terminação longa demais" são perguntas válidas em
qualquer forma de EMR, mas leem `describe-cluster`.

## 2. Objetivo

Uma área `SF-EMRS` que julga **a definição de uma application EMR Serverless** —
capacidade pré-inicializada, auto-stop, destino de log e configuração de runtime —
a partir do JSON de `get-application`.

**Critério de sucesso central:** um `get-application` com capacidade
pré-inicializada e auto-stop desligado produz achado citando `fact_id`; um com
auto-stop habilitado e destino de log declarado não produz achado nenhum; e
nenhuma regra `SF-EMR` de EC2 dispara sobre artefato de Serverless, nem o
contrário.

### Não-objetivos, com razão registrada

| Fora de escopo | Razão |
|---|---|
| **EMR on EKS** | Traz vocabulário de Kubernetes — virtual cluster, container provider, namespace, pod template — que não existe em lugar nenhum do repositório, e `knowledge/` tem zero linha sobre ele. Fase própria, decidida junto com esta |
| **Job runs** (`get-job-run`, `list-job-runs`) | Eixo diferente: é execução, não definição. Uma application tem N runs, o que obriga a decidir amostragem, agregação e "qual run é representativo" — classe de decisão que o eixo de configuração não tem. Ver §9 |
| `billedResourceUtilization` | Consequência do item acima. É a evidência de custo mais direta que a AWS expõe, e por isso mesmo merece fase que a trate com cuidado, não um apêndice desta |
| Recomendar migração para `ARM64` | O ganho depende de compatibilidade de dependência nativa do job, que o artefato não descreve. Emitir `architecture` como `Fact` sim; julgar não |
| Executar qualquer chamada AWS durante `judge` | O motor lê artefato e julga. `collect` é o único que fala com a AWS, e é verbo separado |

## 3. Decisões de desenho

### D-1 — área nova, coordenador estendido

`SF-EMRS` ganha arquivo próprio no catálogo. Duas medições sustentam:
`rules/catalog/emr-infra.yaml` já tem **775 linhas** com 9 regras, e hoje aquelas
nove dizem *EMR on EC2* sem que o leitor precise conferir qual modelo cada uma
vale. Misturar custaria essa propriedade em todas elas, inclusive nas que já
existem.

O coordenador **não** se duplica. `emr-infra-reviewer` é estendido, porque o
gatilho dele — *"o Spark roda em EMR e o risco está na definição, não no código"* —
é idêntico nos dois modelos, e quem pergunta "revisa meu EMR" frequentemente não
sabe de antemão qual dos dois tem. Pelo critério que a Fase 4c fixou, coordenador
novo exige **fronteira medida**; aqui não há.

### D-2 — namespace `emrs.`, não `emr.serverless.`

`emr_cluster.py:1214` guarda o namespace `emr.` do extrator existente. Um segundo
extrator emitindo `emr.serverless.*` colidiria com essa guarda e com o teste de
propriedade de kind por extrator.

O plano **mede a guarda antes de escolher** — se a medição mostrar que
`emr.serverless.` passa limpo, a decisão pode mudar, e a razão fica registrada.
O que não pode é o segundo extrator invadir o namespace do primeiro sem alguém
ter olhado.

### D-3 — `runtimeConfiguration` reaproveita a forma de `emr.configuration`

`runtimeConfiguration` do Serverless tem a mesma estrutura de `Configurations` do
EMR on EC2: lista de `{classification, properties, configurations}`. Então
`emrs.configuration` nasce com o formato de `emr.configuration` — mesmo `attrs`,
mesma redação de segredo **antes** de virar `Fact`.

Não é reúso de código por conveniência: é a mesma pergunta sobre o mesmo formato
de dado, e responder diferente nos dois lugares seria o defeito.

O que **não** se reaproveita é o nível: EMR on EC2 tem `level: cluster` e
`level: instance_group`, com a regra de override entre eles. Serverless não tem
grupo de instância, logo não tem override, logo `emrs.configuration` **não
carrega `level`**. Chave ausente é como este motor diz "não se aplica".

### D-4 — a correlação mora no extrator

`initialCapacity` acima de `maximumCapacity` é contradição detectável num
artefato só, mas exige olhar dois campos ao mesmo tempo.
`engine._condition_candidates` avalia **um fact por vez**, então isso não é
expressável como condição de catálogo.

O extrator correlaciona e emite o veredito como atributo; o catálogo lê atributo
de um fact só. É o padrão que `SF-EMR-008` estabeleceu.

### D-5 — o release label não alimenta `RuntimeContext` até a matriz ser medida

`EMR_MATRIX` em `runtime_detect.py` é, pelo próprio título de
`knowledge/emr/runtime-matrix.md:1`, **"Matriz de runtime Amazon EMR on EC2"**.

Se `emr-7.5.0` no Serverless entrega o mesmo Spark, Hadoop, Iceberg e Python que
no EC2, a matriz se reaproveita e a evidência vai escrita com fonte e data. Se
divergir em **qualquer** release coberta, são duas matrizes.

Esta fase não sabe qual é, e não vai fingir que sabe. A regra de decisão:

- A pesquisa mede primeiro, e o resultado vira `knowledge/emr-serverless/runtime-matrix.md`
  com fonte datada — inclusive se o resultado for "idênticas", que é afirmação que
  também precisa de fonte.
- Até medir, `emrs.application` emite `release_label` como `attrs` e
  `release_major`/`release_minor` como `measures`, mas **não** entra como produtor
  de `RuntimeContext.emr`.
- Se as matrizes divergirem, o produtor entra na fase, e a divergência vira o
  argumento escrito de por que.

Alimentar `RuntimeContext.emr` com um label cuja matriz ninguém conferiu faria o
motor derivar versão de Spark errada e julgar com ela — o pior defeito possível
neste projeto, porque produz achado confiante e falso.

## 4. Facts

| Kind | Quando | Carrega |
|---|---|---|
| `emrs.application` | uma application lida | `application_id`, `name`, `release_label`, `type`, `state`, `architecture`, `auto_start_enabled`, `auto_stop_enabled`, decisão de capacidade da D-4; `measures`: `release_major`, `release_minor`, `idle_timeout_minutes` |
| `emrs.initial_capacity` | um worker type com capacidade pré-inicializada | `worker_type`, e `measures` com `worker_count`, `cpu`, `memory_gb`, `disk_gb` |
| `emrs.configuration` | uma propriedade de `runtimeConfiguration` | `classification`, `key`, `value`, `scope`, + `redacted`/`secret_pattern_match` quando redigido |
| `emrs.monitoring` | sempre que a application é lida | qual destino de log existe: `s3_log_uri_present`, `managed_persistence_enabled`, `cloudwatch_enabled` |
| `emrs.unresolved` | leitura impossível | vocabulário fechado de razões: payload sem `application`, campo de capacidade não numérico, `runtimeConfiguration` com forma inesperada |
| `emrs.analyzed` | sempre | sentinela: `application_count`, `initial_capacity_count`, `configuration_count`, `unresolved_count` |

A sentinela sai **mesmo quando nada foi lido**. É o que distingue "não havia
problema" de "não consegui ler", e é invariante do repositório desde a Fase 0.

## 5. Regras candidatas

Nenhuma entra sem fonte. A pesquisa da §7 confirma ou **veta** cada uma, e o veto
fica escrito no cabeçalho do catálogo — que é a convenção que
`rules/catalog/emr-infra.yaml:22-148` estabeleceu.

| Pergunta | Por que é cara | Severidade proposta |
|---|---|---|
| Capacidade pré-inicializada com auto-stop desligado | Pré-init fatura enquanto a application está `STARTED`. Auto-stop desligado significa faturar sem job rodando, indefinidamente | P0 |
| Auto-stop com `idleTimeoutMinutes` longo demais | Transposição do `SF-EMR-009`; mesma pergunta, unidade diferente (minutos, não segundos) | P1 |
| `initialCapacity` total acima de `maximumCapacity` | Contradição interna: a capacidade pré-inicializada que se paga não cabe no teto que se declarou | P0 |
| Nenhum destino de log declarado | Transposição do `SF-EMR-006`, com consequência mais dura: sem log não há event log, e sem event log **este motor não diagnostica nada** | P1 |
| Segredo em `runtimeConfiguration` | Transposição direta do `SF-EMR-002`, sobre o mesmo formato de dado | P0 |

`runtime_scope: {}` em todas, pelo mesmo argumento registrado em
`emr-infra.yaml:8-19`: a série vem de `measures.release_major` do próprio fact, e
um `{emr: ...}` seria segundo guarda sobre o mesmo dado — que apagaria a área
inteira num `judge` sem `--emr`.

**A severidade proposta não é a final.** Ela é hipótese; a fonte decide, e onde a
fonte não disser, a nota `field-heuristic` vai junto, no padrão exigido por
`rules/catalog/README.md:57`.

## 6. Superfície

| Onde | O quê |
|---|---|
| `sparkforge/facts/emr_serverless.py` | extrator; `EMITTED_KINDS` fechado |
| `sparkforge/collect/aws.py` | `collect emr-serverless`, simétrico a `collect emr-cluster` (`aws.py:654`) |
| `sparkforge/adapters/{_core,cli,tools}.py` | `analyze emr-serverless` |
| as duas listas `EXTRACTORS` | adições manuais independentes |
| as quatro listas de `tests/test_adapters_tools.py` | medidas na Fase 4b |
| `rules/catalog/emr-serverless.yaml` | área `SF-EMRS` |
| `fixtures/emr_serverless/` | domínio novo, golden bidirecional — previsto por `tests/test_fixtures_kind_coverage.py:177` |
| `knowledge/emr-serverless/` | pesquisa de fonte, com `sources.lock.json` atualizado |
| `agents/emr-infra-reviewer.md` (e os quatro espelhos) | `rule_areas` ganha `SF-EMRS` |
| `skills/review-emr-cluster/SKILL.md` (e espelhos) | hoje afirma em `:153` que "nenhum dos facts descreve os outros dois modelos". Metade disso deixa de ser verdade |
| `parity.yaml`, `manifest.json` | o verbo novo nas cinco plataformas |

Áreas 13 → 14. Extratores 17 → 18.

## 7. Pesquisa, antes do código

`knowledge/emr/` tem dois arquivos, ambos com **"EMR on EC2" no título**, ambos
coletados em 2026-08-01. Zero linhas sobre Serverless em `knowledge/` inteiro.

A fase começa por pesquisa, e ela produz `knowledge/emr-serverless/` no formato
que o repositório já usa: corpo em prosa e tabelas, link do espelho executável no
topo, seção `## Fontes` com `Título. URL (retrieved AAAA-MM-DD)`, e — o item que
mais importa — **os parágrafos finais que declaram o que a fonte não sustenta**,
no padrão de `knowledge/emr/cluster-configuration.md:245-246`.

Duas perguntas que a pesquisa precisa responder e que o código depende:

1. A matriz de release do Serverless coincide com a do EC2? (D-5)
2. Capacidade pré-inicializada é faturada com a application `STARTED` e sem job
   rodando? A regra P0 mais cara desta fase depende dessa afirmação, e ela
   precisa de fonte da AWS, não de leitura de campo.

Se a fonte não sustentar (2), a regra **não entra**, e o veto fica escrito.

## 8. Testes

O padrão do repositório, sem exceção nesta fase:

- Golden bidirecional por fixture: facts e findings, regenerados por
  `scripts/regen_fixtures.py`, nunca escritos à mão.
- Toda regra com golden **positivo e negativo**. A Fase 4c mostrou que "positivo
  por regra" não basta quando a regra tem duas condições — se uma condição pode
  ser apagada sem deixar golden vermelho, ela não está testada.
- Todo kind aparecendo em algum golden.
- Um teste que prove que **nenhuma regra `SF-EMR` dispara sobre artefato de
  Serverless, nem o contrário** — a fronteira entre as duas áreas medida, não
  afirmada.

## 9. O que fica escrito como dívida

| Linha | Natureza |
|---|---|
| EMR on EKS | **fase**, decidida junto com esta, sem posição na Ordem até os bancos |
| Job runs e `billedResourceUtilization` | **fase** — eixo de execução, não de definição |
| `RuntimeContext.emr` a partir de Serverless | **dívida** se a pesquisa mostrar matrizes idênticas; **fase** se divergirem |
| Julgar `architecture` | **limite declarado** — o artefato não descreve compatibilidade de dependência nativa |

## 10. Critérios de conclusão

1. `emr_serverless.py` não importa PySpark, não chama AWS, não lê nada além do
   artefato que recebe.
2. Toda regra da área tem golden positivo **e** negativo, e nenhuma condição pode
   ser apagada sem deixar golden vermelho.
3. Todo kind de `EMITTED_KINDS` aparece em algum golden.
4. `emrs.analyzed` sai mesmo quando nada foi lido.
5. Nenhuma regra `SF-EMR` dispara sobre artefato de Serverless; nenhuma `SF-EMRS`
   dispara sobre `describe-cluster`. Provado por teste, não afirmado.
6. Toda regra cita fonte com data, ou carrega `origin: field-heuristic` com nota.
7. A pergunta da D-5 está respondida por escrito, com fonte — inclusive se a
   resposta for "idênticas".
8. As cinco superfícies concordam: CLI, MCP, plugin, `parity.yaml`, `manifest.json`.
9. `sync_skills.py --check` limpo, e a frase do `SKILL.md:153` deixa de afirmar o
   que virou falso.
10. `STATUS.md` mede os números novos em vez de copiá-los, e a linha "EMR
    Serverless e EMR on EKS" da seção *Trabalho previsto* passa a nomear só EKS.

## 11. Desvios

O spec **não é reescrito** — é registro do que se pretendia em 2026-08-04. Esta
seção lista só os desvios que tornam o texto acima **errado**, com o número do
plano ([`../plans/2026-08-04-sparkforge-fase5d-emr-serverless.md`](../plans/2026-08-04-sparkforge-fase5d-emr-serverless.md),
seção *Desvios*), onde os 42 estão registrados por inteiro. Os demais são
detalhe de execução que o spec nunca afirmou.

**§3, D-2 — a colisão de namespace que o spec citou não existe** (`D-5d-1`). A
guarda de `emr_cluster.py:1214` é **local ao módulo**: compara os kinds emitidos
contra o `EMITTED_KINDS` daquele arquivo, e um segundo extrator emitindo
`emr.serverless.*` passaria por ela sem tocá-la. A escolha `emrs.` sobrevive por
outro argumento — o precedente de fronteira do repositório mede invasão com
`startswith` sobre o namespace vizinho, e com `emr.serverless.` **todo** kind do
Serverless começaria com `emr.`, tornando a fronteira mensurável só com exceção
escrita à mão.

**§3, D-5 e §9 — a pergunta da matriz tinha um terceiro desfecho** (`D-5d-5`). O
spec previu dois: idênticas (o produtor entra) ou divergentes (não entra). A
medição achou o terceiro: **a AWS não publica a matriz do EMR Serverless.** As 24
páginas por release trazem só Spark, Hive e Tez, sem o sufixo `-amzn-N`; Hadoop,
Iceberg e Python não aparecem em nenhuma. O produtor não entra, e a razão escrita
é **"sem fonte"**, nunca "as matrizes divergem" — afirmar divergência seria
afirmar o que ninguém mediu. A linha correspondente da §9 é **dívida**.

**§4 — a tabela de facts está desatualizada em quatro pontos**
(`D-5d-14`, `D-5d-15`, `D-5d-16`, `D-5d-17`). `emrs.configuration` não carrega
`level` **nem** `scope` (Serverless não tem grupo de instância, e `scope` só
poderia ser string vazia). `emrs.monitoring` não são três booleanos crus: é o
**único** fact do módulo que aplica default documentado, porque os defaults são
assimétricos — managed persistence nasce `true` e CloudWatch nasce `false` —, e
ganhou `monitoring_declared`, `managed_persistence_declared`,
`cloudwatch_declared` e `measures.log_destination_count`. `emrs.application`
ganhou `auto_stop_declared`/`auto_start_declared`, que o spec não previu e sem os
quais nenhuma regra distingue "desligado de propósito" de "nunca declarado". E
ganhou `measures.initial_capacity_worker_type_count`, porque a correlação que a
D-4 previu (`initialCapacity` × `maximumCapacity`) não era a única necessária.

**§4 — `release_major`/`release_minor` nem sempre saem** (`D-5d-6`). A lista
oficial de releases traz `emr-spark-8.0.0` e `emr-spark-8.0-preview`, que não
casam `emr-<major>.<minor>.<patch>`. Forma não reconhecida **omite** os dois em
vez de forçar número.

**§5 — cinco candidatas viraram seis regras, e três vetos que a §5 não previu**
(`D-5d-29`, `D-5d-33`). Nenhuma candidata foi vetada por falta de fonte; duas
mudaram de forma; e entrou uma sexta (`SF-EMRS-004`, armazenamento gerenciado
desligado com S3 presente). Os três vetos escritos no cabeçalho do catálogo são
`autoStartConfiguration` (sem custo e sem risco), **pré-init subdimensionada** (a
fonte descreve o defeito com precisão, e o outro lado da comparação mora no
`StartJobRun`, que esta fase não lê) e `schedulerConfiguration` (nenhuma página
declara o default de `queueTimeoutMinutes` nem o efeito da expiração).

**§5 — três das cinco candidatas mudaram de forma ou de severidade**
(`D-5d-4`, `D-5d-7` com `D-5d-32`, `D-5d-8`, `D-5d-9`). "Nenhum destino de log"
**não** dispara por ausência: `managedPersistenceMonitoringConfiguration.enabled`
*defaults to true*, então `monitoringConfiguration` ausente significa
**protegido**, e uma regra por ausência acusaria toda application no default
seguro. `initialCapacity` acima de `maximumCapacity` entrou como **P1
`field-heuristic`**, não a P0 que o spec pediu: a aritmética se sustenta, mas
nenhuma fonte declara se a API aceita ou rejeita o estado. O auto-stop **não** é
"a mesma pergunta do `SF-EMR-009` com outra unidade": ausência do bloco significa
protegido (o inverso do EC2) e o custo da janela **depende de haver pré-init**,
porque a cobrança é por worker existente — a regra exige pré-init na condição, e
a linha "sem pré-init não há worker de que cobrar" fica declarada como **dedução
do modelo de cobrança**, não como frase da AWS. E o segredo em
`runtimeConfiguration` **não** é transposição direta do `SF-EMR-002`: o bloco
*Warning* que sustenta aquela regra não existe na documentação do Serverless, e a
área tem mecanismo próprio que o EC2 não tem — a anotação `EMR.secret@{{Nome}}`,
que é **id de segredo, não segredo**, e acusá-la seria acusar a correção que o
achado recomenda.

**§6 — as superfícies são seis, não cinco** (`D-5d-20`). A sexta é
`ARTIFACT_KINDS` em `sparkforge/collect/base.py:29`, tupla fechada validada em
`ArtifactEntry.__post_init__`: coletor com `kind` fora dela levanta `ValueError`
na escrita do manifesto. As cinco do spec são declarativas; esta é executável e
falha tarde.

**§6 — `collect emr-serverless` não é simétrico a `collect emr-cluster`**
(`D-5d-22`). São **uma** chamada e um artefato, contra seis. E ele aceita só
`--application-id`: `name` é `Required: No` na API e a documentação não declara
unicidade, então resolver por nome escolheria uma entre N homônimas em silêncio.

**§6 — `sources.lock.json` não podia ser atualizado com a pesquisa** (`D-5d-2`).
`test_the_committed_lock_matches_the_catalog` afirma
`set(lock["sources"]) == set(watchlist())`, e a watchlist é derivada
**exclusivamente** dos `sources[].url` das regras do catálogo: URL sem regra que a
cite quebra a suíte. As URLs entraram junto com as regras.

**§3, D-1 — a decisão sobrevive, e o argumento que a sustenta é outro**
(`D-5d-21`, `D-5d-34`, e a decisão da Task 7). A D-1 dizia *"pelo critério que a
Fase 4c fixou, coordenador novo exige fronteira medida; aqui não há"* — e agora
**há**: `tests/test_rules_emrs_boundary.py` mede a fronteira nas duas direções,
com zero invasões. Ela não muda a decisão porque é fronteira de **catálogo**, e
vale depois que alguém já escolheu o verbo. A fronteira de **despacho** foi
medida e não existe: `_PLATFORM_KEYS` (`sparkforge/facts/runtime_detect.py:403`)
conhece duas identidades de plataforma, `emr` e `glue`, e nenhum fact `emrs.*`
alimenta qualquer uma — um `describe-cluster` emite `env.platform` com
`resolved: emr`, um `get-application` **não emite `env.platform` nenhum**. Partir
o coordenador seria roteá-lo por prosa. `emr-infra-reviewer` fica com
`SF-EMR`, `SF-EMRS` e `SF-ENV`, e a `description` nomeia as duas plataformas.

**§9 — a tabela de dívidas ganha uma quarta linha que o spec não previu**
(`D-5d-11`). `get-application` descreve **o padrão da application**, e
`StartJobRun` o sobrepõe — com merge por classificação, e inclusive **removendo**
classificação e destino de log. Nenhum achado desta área prova o que um job run
executou. É **limite declarado**, escrito na `explanation` de todas as seis
regras, no corpo do coordenador e na skill.
