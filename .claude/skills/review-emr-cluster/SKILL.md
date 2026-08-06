---
name: review-emr-cluster
description: Use quando revisar a definição de um cluster Amazon EMR on EC2 (instance fleets contra instance groups, purchasing option por papel, managed scaling com alocação dinâmica, Configurations de cluster sobrepostas por grupo, maximizeResourceAllocation, partitionOverwriteMode, LogUri, bootstrap actions, segredo em texto claro) em busca de contradição de dimensionamento, custo sem trabalho correspondente ou perda de capacidade de diagnóstico. Use também quando a pergunta for "por que esse cluster custa isso", "o cluster subiu e não desce", "esse cluster morreu no bootstrap" ou "cadê os logs do cluster que terminou", mesmo que ninguém fale em regra. Se você está prestes a ler `describe-cluster` no olho, rode `sparkforge analyze emr-cluster` e `sparkforge judge` em vez disso — o extrator normaliza grupos e frotas num kind só e o catálogo aplica as regras SF-EMR sobre o que ele achou. Cobre também EMR Serverless: se o dump é `get-application`, o verbo é `sparkforge analyze emr-serverless` e a área é SF-EMRS.
---

# Review EMR Cluster

Um `describe-cluster` tem centenas de linhas e três armadilhas de leitura: grupos e frotas
respondem a mesma pergunta com campos diferentes, `Configurations` chega por dois níveis com
precedência entre eles, e o que o grupo traz é o que foi **pedido**, não necessariamente o
que vigora. O extrator resolve as três; o catálogo aplica `SF-EMR-*` sobre o resultado.

## Procedimento

### 1. Colete os seis dumps

Um cluster EMR não cabe num comando. São **seis**, e a união deles é o artefato:

```bash
sparkforge collect emr-cluster --repo . --cluster-id j-XXXXXXXXXXXXX --now <ISO8601>
```

À mão, o equivalente é rodar os seis e juntar os objetos num JSON só, em PascalCase, sob as
chaves que o próprio CLI devolve:

| Subcomando `aws emr` | Chave no dump | O que morre sem ele |
|---|---|---|
| `describe-cluster` | `Cluster` | tudo — release, LogUri, estado, e a âncora de `SF-EMR-002`, `SF-EMR-006` e `SF-EMR-007` |
| `list-instance-groups` **ou** `list-instance-fleets` | `InstanceGroups` / `InstanceFleets` | `SF-EMR-004` (papel e purchasing option) e o lado de grupo de `emr.configuration`, que é o que alimenta `measures.overriding_group_count` |
| `list-bootstrap-actions` | `BootstrapActions` | a metade de bootstrap de `SF-EMR-002` |
| `get-managed-scaling-policy` | `ManagedScalingPolicy` | `SF-EMR-003` inteira — o fact `emr.managed_scaling` só sai daqui |
| `get-auto-termination-policy` | `AutoTerminationPolicy` | `measures.idle_timeout_seconds` do `emr.cluster` |

As duas políticas são o que costuma faltar, porque quem lista os comandos de partida quase
sempre para em `describe-cluster` e nos grupos. Elas são chamadas separadas: nenhuma das
duas aparece dentro de `describe-cluster`.

Duas armadilhas de coleta:

- **`aws emr list-configurations` é um comando que a AWS nunca teve.** As classificações
  (`spark`, `spark-defaults`, `yarn-site`) chegam por `Cluster.Configurations` e por
  `InstanceGroup.Configurations` / `InstanceTypeSpecification.Configurations` — quem coleta
  os grupos já coletou as do grupo.
- `list-instance-fleets` **falha** num cluster de instance groups, e vice-versa: os modelos
  são exclusivos. A seção correspondente deve ser **omitida** do dump, nunca gravada como
  lista vazia — vazio é lido como "coletado e não tem", que é uma afirmação diferente.

### 2. Extraia os facts

```bash
sparkforge analyze emr-cluster --path <arquivo ou diretório com os dumps> \
  --out .sparkforge/facts_emr.json
```

Leia `emr.unresolved` antes de qualquer conclusão. Ele distingue os dois motivos que
importam: `missing_instance_model` é **dump incompleto** (ninguém coletou grupos nem
frotas), e `conflicting_instance_models` descreve um cluster impossível — os dois modelos no
mesmo dump. Nenhum dos dois é "cluster sem instâncias", e tratar assim acusa quem coletou de
menos.

### 3. Junte a execução quando a recomendação for de dimensionamento

Nenhuma decisão de executor se sustenta em `describe-cluster` sozinho. Quando o achado for
`SF-EMR-001` (ou qualquer conversa sobre memória e cores por executor), traga o run:

```bash
sparkforge analyze event-log --path <event log> --out .sparkforge/facts_eventlog.json
```

`--facts` é repetível: passe os dois arquivos na mesma chamada de `judge`, que une e
deduplica as listas antes de julgar.

### 4. Julgue

```bash
sparkforge judge --facts .sparkforge/facts_emr.json --show-skipped

# com o run junto, para sustentar dimensionamento:
sparkforge judge \
  --facts .sparkforge/facts_emr.json \
  --facts .sparkforge/facts_eventlog.json \
  --show-skipped
```

**Sem flag de versão, e aqui isso é mais que conveniência.** O próprio dump carrega a
plataforma: `judge` lê `release_label` do fact `emr.cluster` e preenche `runtime.emr`, e
cada `emr.application` traz o Spark e o Iceberg que a AWS declara ter instalado **naquele
cluster** — observação com artefato, melhor que derivar da matriz de release. Confirme no
campo `runtime` da saída: `detected_from` com `describe_cluster` é a prova de que veio do
dump. Quando a versão observada discorda da matriz, nada é substituído em silêncio —
`runtime.divergences` lista as duas, e a discordância é achado próprio (`SF-ENV-001`).

O que fica de fora da detecção, e o que fazer:

- **`runtime.glue` fica vazio**, porque um cluster EMR não é um job Glue. As regras
  versionadas de outras áreas — `SF-GLUE-*` e as guardadas por versão de Glue — saem em
  `skipped` com `reason: runtime_scope`, visível em `--show-skipped`. Esse é o
  comportamento correto: o eixo fica descoberto, mas você **sabe** que ficou, em vez de a
  área sumir da saída. Declarar `--glue 5.1` num relatório de EMR seria inventar um runtime
  que não existe ali.
- **As regras `SF-EMR-*` não dependem disso.** Elas leem a release do próprio fact, então
  continuam sendo avaliadas mesmo num `judge` sem flag nenhuma. Se uma delas aparecer em
  `skipped`, o motivo é `requires_facts` — um dump que faltou, e a tabela do passo 1 diz
  qual.

### 5. Interprete por cluster, e por nível

## Cluster inteiro contra grupo: onde a afirmação mora

`Cluster.Configurations` vale para todos os nós **exceto onde um grupo redefinir**. Por isso
`SF-EMR-001`, `SF-EMR-003` e `SF-EMR-005` exigem `measures.overriding_group_count == 0`:
elas afirmam sobre o cluster inteiro, e a afirmação é falsa se metade dos nós usa outro
valor. Ao reportar, escreva o nível — "o `spark-defaults` de cluster tem X" ou "o grupo
`ig-1` redefine X" —, nunca "o cluster tem X" sem checar de qual `attrs.level` o fact veio.

O fact `emr.configuration.unapplied` é o guarda de qualidade da evidência, e a analogia é
com `tf.observability.unknown`: ele significa **reconfiguração pedida e não aplicada**. Uma
regra que afirma sobre configuração em vigor o usa em `absent:`; você faz o mesmo ao ler.
Um relatório que diz "a alocação dinâmica está desligada" sobre uma reconfiguração que
nunca entrou em vigor está errado nos dois sentidos possíveis.

`SF-EMR-002` é achado de **segurança** e tem precedência sobre qualquer achado de
performance no mesmo relatório. O valor nunca aparece no fact — o extrator grava
`<redigido>` e marca `attrs.secret_pattern_match` —, e ele não deve aparecer no seu
relatório também: a API Describe já devolve o segredo em texto claro para quem tem leitura,
e um relatório com o literal é a segunda cópia.

## Referência rápida

Regras desta área e o fact que cada uma consome. Limiares e severidades **não** estão aqui
de propósito, e a lista autoritativa é `sparkforge rules lookup --category emr-infra` — o
catálogo cresce, esta tabela é uma foto.

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-EMR-001` | `emr.cluster` (`INSTANCE_FLEET`) + `emr.configuration` | `maximizeResourceAllocation` num cluster de frotas, onde o cálculo sai de um tipo de instância que a frota não garante |
| `SF-EMR-002` | `emr.configuration` **ou** `emr.bootstrap_action` com `attrs.secret_pattern_match` | Segredo em texto claro numa superfície que Describe e List devolvem a qualquer leitor |
| `SF-EMR-003` | `emr.configuration` + `emr.managed_scaling`, guardado por `emr.configuration.unapplied` | Alocação dinâmica desligada com managed scaling ligado — capacidade até o teto, sem trabalho correspondente |
| `SF-EMR-004` | `emr.instance_capacity` (papéis `MASTER` e `CORE`) | Primary em Spot num cluster que pagou On-Demand no core: as duas escolhas se contradizem |
| `SF-EMR-005` | `emr.configuration` (`spark-defaults`) | `partitionOverwriteMode` dinâmico no cluster muda a semântica de `overwrite` para todo job que rodar ali |
| `SF-EMR-006` | `emr.cluster` (`attrs.log_uri_present: false`) | Sem LogUri nenhum log sobrevive ao cluster; agrava quando `auto_terminate` é verdadeiro |
| `SF-EMR-007` | `emr.cluster` (`attrs.state_change_reason_code`) | Cluster terminado por falha de bootstrap action — post-mortem, com onde olhar |
| `SF-EMR-008` | `emr.cluster` + `emr.instance_capacity` (papel `TASK` em Spot), guardado por `emr.yarn.am_node_label` | ApplicationMaster elegível a nó Spot: em deploy-mode cluster ele é o driver, e a perda do nó derruba a aplicação inteira |

## O outro modelo de execução: EMR Serverless

Quando o dump for de `get-application` e não de `describe-cluster`, o procedimento inteiro
acima **não se aplica** — não há grupo, frota, nó nem `Configurations` em dois níveis. O que
se aplica é a mesma disciplina, sobre outra área (`SF-EMRS`) e outro namespace (`emrs.*`,
disjunto de `emr.*` de propósito). A lista autoritativa das regras é
`sparkforge rules lookup --category emr-serverless`, nunca memória.

São **uma** chamada e um artefato, contra os seis do EC2:

```bash
sparkforge collect emr-serverless --repo . --application-id 00fXXXXXXXXXXXXX --now <ISO8601>
sparkforge analyze emr-serverless --path <arquivo ou diretório> \
  --out .sparkforge/facts_emr_serverless.json
sparkforge judge --facts .sparkforge/facts_emr_serverless.json --show-skipped
```

Cinco coisas que decidem a leitura, e nenhuma delas existe no EC2:

- **`--out` não é opcional na prática.** Medido: um `get-application` com 60 propriedades em
  `runtimeConfiguration` produz 64 facts, e o envelope da tela devolve `returned_count: 50`
  com `next_cursor: "50"`. O teto de `runtimeConfiguration` é **100 propriedades**, e cada
  uma vira um `emrs.configuration` — uma application real estoura a página default com
  facilidade. Quem lê pela tela vê metade da configuração **sem saber**; o arquivo do `--out`
  traz a lista completa, e é o que `judge --facts` consome.
- **O id é obrigatório e o nome não serve.** `collect emr-serverless` exige
  `--application-id`. `name` é `Required: No` na API e a documentação não declara unicidade,
  então resolver por nome escolheria uma entre N homônimas em silêncio.
- **Ausência de bloco costuma ser o default SEGURO**, ao contrário do EC2.
  `autoStopConfiguration.enabled` nasce `true` com 15 minutos, e
  `managedPersistenceMonitoringConfiguration.enabled` nasce `true` com 30 dias de retenção.
  Um achado de auto-stop desligado exige o campo **explícito**, e é por isso que
  `emrs.application` carrega `auto_stop_declared`/`auto_start_declared`: eles separam "veio
  desligado" de "nunca veio".
- **`EMR.secret@{{Nome}}` em `runtimeConfiguration` é a correção, não o defeito.** É a
  anotação de Secrets Manager, e o valor anotado é id de segredo. Acusá-la seria acusar o
  conserto que o próprio achado recomenda.
- **`get-application` descreve o PADRÃO da application, e `StartJobRun` o sobrepõe** —
  inclusive removendo classificação e destino de log. Nenhum achado desta área prova o que um
  job run executou, e toda recomendação precisa carregar esse recorte.

E o que o motor **não** sabe aqui: `RuntimeContext.emr` fica vazio, porque a AWS não publica a
matriz de release do Serverless (as páginas trazem só Spark, Hive e Tez, sem `-amzn-N`).
`env.platform` também não sai — não há identidade de plataforma para Serverless em
`_PLATFORM_KEYS`. Nenhuma das seis regras `SF-EMRS` depende disso (todas com `runtime_scope`
vazio), mas versão que você cite entra **declarada**, nunca derivada do `releaseLabel`.

## Quando NÃO usar

- O job roda em AWS Glue, não em EMR: a área é `SF-GLUE` e a skill é `review-glue-terraform`.
- Você quer achar stage dominante, skew, spill ou GC de um run: isso é execução, e vem de
  `analyze-spark-ui` sobre o event log.
- O problema está no código ou no plano físico: comece por `sparkforge-diagnose`.
- A pergunta é sobre tabela Iceberg, small files ou layout: `optimize-iceberg-table` e
  `optimize-parquet-layout`.
- Você quer decidir capacidade de **EMR on EKS**: nenhum fact deste repositório descreve
  virtual cluster, container provider, namespace nem pod template — esse modelo de execução
  continua sem cobertura, e supor que `SF-EMR` ou `SF-EMRS` vale para ele é inventar.
  **EMR Serverless deixou de estar nesta lista**: tem extrator, área e verbo próprios, e é a
  seção acima.

## Red flags

- Escrever "o cluster está com X" sem conferir `measures.overriding_group_count` e
  `attrs.level` — metade dos nós pode estar com outro valor.
- Tratar `Configurations` de grupo como o que vigora, ignorando
  `emr.configuration.unapplied`. É o erro mais fácil de cometer aqui, porque o dump parece
  descrever o presente e descreve a intenção.
- Recomendar remover `partitionOverwriteMode` sem inventariar os jobs que rodam no cluster:
  a remoção devolve os writes ao padrão `static`, e um job que dependia de `dynamic` passa a
  apagar o destino inteiro. O risco da correção é maior que o do achado.
- Acusar primary em Spot como erro absoluto. A AWS o recomenda quando o cluster inteiro é
  Spot; o defeito de `SF-EMR-004` é a **incoerência** com um core On-Demand, e reportá-lo
  como regra geral queima a confiança no resto.
- Prometer que a correção entra hoje. Configuração de cluster EMR não é editável em cluster
  em execução — a correção é o próximo provisionamento, e o paliativo até lá é o submit do
  job.
- Reportar dump incompleto (`emr.unresolved`) como cluster mal configurado.
- Copiar limiar ou comportamento de release entre séries sem checar
  `knowledge/emr/runtime-matrix.md`; a série 6.x mudou defaults que a 5.x tinha.

## Preservar o resultado, com o verbo que produz a evidência

A skill já mede o caso mais literal do repositório: `partitionOverwriteMode` dinâmico no
cluster muda a **semântica** de `overwrite` para todo job que rodar ali. Removê-lo devolve os
jobs ao default `static`, e um job que dependia de `dynamic` passa a apagar o destino inteiro.
Nenhuma das duas direções é neutra, e o sintoma não é falha: é resultado errado a jusante. A
`SF-EMR-005` mostra a forma da validação — contagem **por partição**, não só o total.

`sparkforge funcval plan --facts <facts.json> --out <plano.json>` deriva o plano — `--facts`
é repetível, porque o alvo vem do `pyspark.write` e o schema e os agregados vêm do
`catalog.table_schema` —, e `sparkforge funcval compare --plan <plano.json> --before
<antes.json> --after <depois.json>` compara os dois lados **que o operador mediu**: nenhum dos
dois executa consulta, roda Spark ou chama AWS. Tools MCP: `sparkforge_funcval_plan` e
`sparkforge_funcval_compare`. O plano é a evidência do gate `functional_validation_defined`, e
`ROUTE-015` é a rota que manda defini-lo. O lado `--before` só existe se alguém o mediu
**antes** de a mudança tocar o alvo — um `overwrite` no meio o apaga sem deixar rastro.

Os quatro eixos são **proxies**, e escrever o contrário promete o que a ferramenta não
entrega: contagem, schema, chaves e agregados iguais **não provam** que o dado é o mesmo — duas
linhas podem trocar valores entre si e os quatro passam. Escreva "nenhum dos quatro proxies
detectou divergência", nunca "o resultado é idêntico". Sem `--key`, a chave de negócio sai em
`undeclared_axes` com a razão, e isso vai dito. `SF-FVAL-005` acesa invalida a leitura das
outras quatro.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva você **não executa** — recomende, e a confirmação de escopo e
retenção **sobe a quem pode ser perguntado**: o agente pai que despachou, ou o
operador na sessão. E **derive o plano de validação funcional** com `funcval plan` antes de fechar a
recomendação, comparando os dois lados medidos com `funcval compare` — a regra 10, e ela
nomeia o produtor de propósito: exigência sem verbo é prosa.

Esta skill é **despachável** (`subagent: true` no espelho `.agents/skills/`), e
`ask_user_question` é **sempre negado** a um subagente. Dentro do despacho, obter a
confirmação aqui não é difícil: é impossível — por isso a regra 9 de
`AGENT_PROTOCOL.md` manda não executar e devolver a decisão a quem pode ser
perguntado.
