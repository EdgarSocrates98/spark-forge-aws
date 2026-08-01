# Configuração de cluster Amazon EMR on EC2

O que decide custo, durabilidade e capacidade de diagnóstico **antes** de qualquer linha de PySpark rodar. A matriz de versões está em [`runtime-matrix.md`](runtime-matrix.md); esta página é sobre a forma do cluster.

A forma executável deste conteúdo é [`../../rules/catalog/emr-infra.yaml`](../../rules/catalog/emr-infra.yaml).

## 1. Os dois modelos de instância, e os dois níveis de configuração

Um cluster usa **instance groups** ou **instance fleets**, nunca os dois. `Cluster.InstanceCollectionType` diz qual.

| | Instance groups | Instance fleets |
|---|---|---|
| Tipos por papel | um | vários, com capacidade ponderada |
| Purchasing option | por grupo (`Market`: `ON_DEMAND` ou `SPOT`) | por frota, com alvos separados (`TargetOnDemandCapacity`, `TargetSpotCapacity`) |
| Quantos por papel | até 48 grupos de task | uma frota de task |
| "Há Spot neste papel?" | `Market == "SPOT"` | `TargetSpotCapacity > 0` |

A mesma pergunta tem duas formas. O extrator normaliza as duas em `attrs.has_spot_capacity` / `attrs.has_on_demand_capacity` para que uma regra não precise ser escrita duas vezes — e o que é específico de um modelo (`market`, `allocation_strategy`) continua distinguível.

`Configurations` chega por **dois níveis**, e a distinção decide o alcance de qualquer afirmação:

- **cluster** — `Cluster.Configurations`. Vale para todos os nós, exceto onde um grupo redefinir.
- **grupo/frota** — `InstanceGroup.Configurations` ou `InstanceTypeSpecification.Configurations`. Sobrepõe o cluster **para aquele grupo**.

Consequência prática: "o cluster está com X" só é verdade se nenhum grupo redefiniu X. É por isso que as regras de nível cluster do catálogo exigem `measures.overriding_group_count == 0`.

**A reconfiguração pode não estar em vigor.** `InstanceGroup` traz `Configurations` (o que foi **pedido**) e `LastSuccessfullyAppliedConfigurations` (o que **vigora**). Divergência entre os dois significa que o cluster não está rodando com o que o dump aparenta dizer. Ler o primeiro como se fosse o segundo é o erro mais fácil de cometer aqui.

Configuração de cluster **não é editável em cluster em execução** no nível de cluster: mudar exige provisionar outro. Só instance group aceita reconfiguração, a partir da 5.21.0.

## 2. `maximizeResourceAllocation`

Propriedade da classificação `spark` (não de `spark-defaults`). Quando `true`, o EMR calcula o executor máximo possível para **uma** instância do core e escreve em `spark-defaults`:

| Propriedade escrita | De onde sai o valor |
|---|---|
| `spark.default.parallelism` | 2× o número de cores de CPU disponíveis para containers YARN |
| `spark.driver.memory` | menor tipo entre os grupos primary e core |
| `spark.executor.memory` | tipos de instância de core e task |
| `spark.executor.cores` | tipos de instância de core e task |
| `spark.executor.instances` | tipos de instância de core e task; não escrito se `spark.dynamicAllocation.enabled` foi posto em `true` na mesma configuração |

**Em instance groups isso é determinístico** — o grupo core tem um tipo só. **Em instance fleets não é**: a frota pode ter tipos com vCPU e memória diferentes, e o cálculo sai de um deles. Um executor calculado para o maior não cabe no menor; calculado para o menor, desperdiça o maior. A AWS é explícita: *"we don't recommend using the default settings when using maximum resource allocation. Configure custom settings for your instance fleet clusters."*

Também não usar com outras aplicações distribuídas (HBase): o EMR aplica configuração YARN própria para elas, que conflita.

## 3. Spot por papel

O que cada papel perde ao ser reclamado:

| Papel | O que roda | Efeito da terminação |
|---|---|---|
| primary | ResourceManager, NameNode, estado do cluster | **o cluster acaba** |
| core | DataNode (HDFS), NodeManager, executores | risco de perda parcial de dado |
| task | NodeManager, executores | nenhuma perda de dado |

A tabela oficial de cenários, que é o que decide se uma escolha é coerente:

| Cenário | primary | core | task |
|---|---|---|---|
| Cluster longo / data warehouse | On-Demand | On-Demand ou mix de frota | Spot ou mix |
| Custo acima de tempo | Spot | Spot | Spot |
| Dado crítico | On-Demand | On-Demand | Spot ou mix |
| Teste de aplicação | Spot | Spot | Spot |

**Primary em Spot não é erro por si — é erro quando contradiz o core.** Em duas das quatro linhas o primary é Spot, e nas duas o core também é. Nenhuma linha combina primary Spot com core On-Demand: essa combinação paga durabilidade num lugar e deixa o ponto único de falha exposto no outro.

Duas restrições operacionais que fecham qualquer conserto tardio:

- Purchasing option de primary e core **não muda em cluster em execução**. Trocar exige terminar e provisionar outro. Só task aceita troca, criando um grupo/frota novo e removendo o antigo.
- Com o primary em Spot, o cluster **só inicia quando a solicitação Spot é atendida** — latência inicial imprevisível.

## 4. Managed scaling e alocação dinâmica

Managed scaling ajusta a capacidade dentro de `MinimumCapacityUnits`..`MaximumCapacityUnits`, com tetos opcionais para On-Demand (`MaximumOnDemandCapacityUnits`) e para core (`MaximumCoreCapacityUnits`). Só funciona com aplicações YARN; Presto e HBase ficam de fora. A política **não** aparece em `describe-cluster`: ela vem de `get-managed-scaling-policy`.

**A combinação que a AWS documenta como problema:** desligar a alocação dinâmica do Spark (`spark.dynamicAllocation.enabled=false`) num cluster com managed scaling *"can cause Managed Scaling issues, where clusters can be scaled up more than required for your workloads (up to the maximum compute)"*. A recomendação oficial é manter a alocação dinâmica ligada, que já é o default do EMR desde a 4.4.0.

O modo de falha é caro e silencioso: nenhum job falha, nenhuma métrica de erro sobe, e a evidência é a fatura.

Outras condições que degradam o scaling, na mesma página:
- volume EBS acima de ~90% de utilização;
- métricas CloudWatch ausentes — o scaling depende delas para operar;
- endpoint de API Gateway inacessível a partir do cluster.

## 5. Escrita em S3: committer, commit protocol e semântica de overwrite

Dois mecanismos distintos, e confundi-los produz recomendação errada:

| Mecanismo | Cobre | Releases | Default |
|---|---|---|---|
| EMRFS S3-optimized **committer** | escrita comum (não dinâmica) | 5.19.0+ | ligado a partir da 5.20.0 |
| EMRFS S3-optimized **commit protocol** | overwrite **dinâmico** de partição | 5.30.0+ e 6.2.0+ | ligado |

O commit protocol existe *"to avoid rename operations in Amazon S3 during the Spark dynamic partition overwrite job commit phase"*. Ou seja: **em qualquer release da matriz deste repositório (6.4.0 em diante), `partitionOverwriteMode=dynamic` não causa mais a cauda de rename sequencial no driver.** Esse argumento de performance só vale em 5.x abaixo de 5.30.0 e 6.x abaixo de 6.2.0.

Onde a cauda de rename **ainda** aparece nas releases atuais: escrita em **partição com location customizado** (`ALTER TABLE ... ADD PARTITION ... LOCATION`). Nesse caminho o Spark renomeia arquivo por arquivo, sequencialmente, no commit.

**O que sobrevive como defeito, e é mais grave: a semântica.**

| `spark.sql.sources.partitionOverwriteMode` | O que `mode("overwrite")` apaga |
|---|---|
| `static` (default) | o caminho de destino inteiro |
| `dynamic` | apenas as partições presentes no dado escrito |

Posto no `spark-defaults` do **cluster**, o valor muda essa semântica para todo job que rodar ali — inclusive os escritos e testados supondo o default. O sintoma não é falha: é partição antiga sobrevivendo a um overwrite que deveria tê-la removido, e o erro aparece a jusante, numa conferência de números.

Daí a recomendação: **não trocar o valor no cluster — tirá-lo do cluster**, e deixar cada job declarar `.option("partitionOverwriteMode", ...)` conforme a própria semântica. Trocar de `dynamic` para `static` sem revisar o código apaga dado que deveria ficar.

E a validação correspondente: **contagem por partição, nunca só o total.** O total pode coincidir enquanto partições inteiras somem ou sobrevivam indevidamente.

Para tabela Iceberg nenhum dos dois vale: overwrite por partição ali é `MERGE INTO` ou o overwrite dinâmico do próprio Iceberg.

## 6. Logging e capacidade de diagnóstico

`LogUri` é o destino S3 dos logs do cluster. Sem ele não existe destino para nada da lista abaixo:

| Log | Caminho sob o bucket |
|---|---|
| Step | `<cluster-id>/steps/<step-id>/` |
| Container (stderr, stdout, `launch_container.sh`) | `<cluster-id>/containers/` |
| ResourceManager | `<cluster-id>/node/<instância-líder>/applications/hadoop-yarn/` |
| HDFS (NameNode, DataNode, TimelineServer) | `<cluster-id>/node/<instância>/applications/hadoop-hdfs/` |
| Estado de instância | `<cluster-id>/node/<instância>/daemons/instance-state/` |
| Provisionamento do nó | `<cluster-id>/node/<instância-líder>/provision-node/` |

Corte por release:

- **≤ 6.8.0** — *"log files are not saved to Amazon S3 during cluster termination, so you can't access the log files once the nodes terminate"*. O arquivamento periódico (a cada 5 minutos) precisa ser habilitado **no lançamento**.
- **≥ 6.9.0** — o arquivamento durante scale-down é automático, e os logs de um nó removido persistem.
- **≥ 7.13.0** — `S3LoggingConfiguration` permite política por tipo de log (`emr-managed`, `on-customer-s3only`, `disabled`), e *"can only be set at cluster creation time and cannot be modified for running clusters"*.

Em todas elas, `LogUri` é propriedade de criação: **não há conserto retroativo**. Quando a investigação for necessária, já será tarde. É o mesmo tipo de achado que `SF-GLUE-002` no Glue — não é performance, é a possibilidade de diagnosticar qualquer coisa depois do fato.

Criptografia dos logs com chave gerenciada pelo cliente existe a partir da 5.30.0 (exceto 6.0.0), e exige `kms:GenerateDataKey` no perfil de instância EC2 e `kms:DescribeKey` no papel de serviço do EMR.

## 7. Node labels e onde o ApplicationMaster roda

Em `deploy-mode cluster` o ApplicationMaster **é** o driver do Spark. Onde ele roda decide se a perda de um nó mata uma task ou a aplicação inteira.

| Série | Node labels | Onde o AM pode rodar |
|---|---|---|
| 5.19.0 – 5.x | ligadas por default | só em nós com label `CORE` |
| 6.x | **desligadas por default** | core **e task** |
| 7.x | desligadas por default; labels atribuídas também por market type | core e task |

Para prender o AM, as duas propriedades de `yarn-site` precisam estar presentes:

```
yarn.node-labels.enabled: true
yarn.node-labels.am.default-node-label-expression: 'CORE'      # 6.x, e 7.0+
yarn.node-labels.am.default-node-label-expression: 'ON_DEMAND' # 7.x, por market type
```

Com task em Spot e sem essas propriedades, a reclamação de um Spot pelo EC2 pode derrubar o AM — e com ele a aplicação, não uma task.

Restrições que a página de managed scaling acrescenta:
- o EMR **não** rotula nós de task, então não há como restringir o AM apenas a task;
- *"We don't recommend using Spot nodes for application primary processes"*;
- as labels são criadas no provisionamento; o EMR **não** aceita adicionar node labels ao reconfigurar o cluster;
- com labels e managed scaling, `yarn.scheduler.capacity.maximum-am-resource-percent: 1` quando houver aplicações em paralelo, e `yarn.resourcemanager.decommissioning.timeout` maior que a aplicação mais longa.

**A regra é `SF-EMR-008`**, e ela precisou de um fact derivado para existir. O gatilho exige provar a **ausência** de um par de propriedades com valores específicos, num nível específico, e o motor de regras só sabe `absent: <kind>` — não existe `where` negado nem `absent` filtrado por atributo (`sparkforge/rules/engine.py::_absent_satisfied`). Essa limitação **continua existindo**; ela foi contornada, não removida: `sparkforge/facts/emr_cluster.py::_am_node_label_facts` decide a combinação e emite `emr.yarn.am_node_label` quando o AM **não está provadamente solto**, e a regra usa `absent:` sobre esse kind. É padrão reaproveitável — quando o gatilho for a ausência de uma combinação, o extrator emite o kind que representa a combinação satisfeita, em vez de o catálogo ganhar negação.

O que o extrator decide, e por quê:

| Configuração observada | Decisão | Efeito em SF-EMR-008 |
|---|---|---|
| nenhuma das duas propriedades | fact ausente | **acusa** |
| `enabled=true` sozinho, em qualquer nível | fact ausente | **acusa** — o AM cai na partição `DEFAULT`, e o EMR não rotula nós de task, então `DEFAULT` é onde o Spot está |
| expressão sozinha, sem `enabled=true` | fact ausente | **acusa** — a série 6.x em diante vem com a feature desligada |
| par no nível **cluster**, expressão `CORE` ou `ON_DEMAND` | `pinned` | cala |
| par no nível cluster, expressão fora desse vocabulário | `undetermined` + `emr.unresolved` | cala, e conta o ponto cego |
| propriedade em nível de **grupo** divergindo do cluster | `undetermined` + `emr.unresolved` | cala, e conta o ponto cego |

As duas linhas de `undetermined` são a mesma decisão: a expressão é lida pelo ResourceManager, que roda no nó primário, e um valor ilegível ou de escopo incerto não permite afirmar nem proteção nem exposição. Acusar ali seria acusar configuração possivelmente correta, que `rules/catalog/README.md` trata como o pior tipo de defeito de regra — então a regra se cala e o `emr.unresolved` registra que houve um ponto cego, em vez de a ausência de achado ser lida como "revisei e está tudo bem".

**Limite declarado da regra:** ela acusa a *ausência de restrição*, não a presença do AM em Spot. Num cluster inteiramente Spot que fixou o AM em `CORE`, o AM continua num nó reclamável e SF-EMR-008 não dispara; a coerência entre as opções de compra dos papéis é assunto de `SF-EMR-004`.

## 8. Bootstrap actions

Rodam antes da instalação das aplicações, e também em cada nó adicionado depois. Até 16 por cluster.

`ListBootstrapActions` devolve **apenas** `{Name, ScriptBootstrapAction{Path, Args}}` — sem status, sem exit code, sem timestamp. Não há como julgar o resultado de uma bootstrap action a partir dela.

O que a API responde está do outro lado: *"If the bootstrap action returns a nonzero error code, Amazon EMR treats it as a failure and terminates the instance. If too many instances fail their bootstrap actions, then Amazon EMR terminates the cluster. (...) Use the cluster `lastStateChangeReason` error code to identify failures caused by a bootstrap action."*

Ou seja, bootstrap que falha **não** falha em silêncio: aparece como `Status.StateChangeReason.Code = BOOTSTRAP_FAILURE`. O caso genuinamente mudo é o script que sai com zero sem ter feito o trabalho, e esse é invisível a qualquer API por construção — a defesa é o próprio script verificar o efeito.

Causas mais comuns, na ordem: objeto S3 do script ausente ou sem `s3:GetObject` para o perfil de instância EC2; dependência externa inalcançável a partir da subnet; tempo de execução além do tolerado.

Shutdown actions (`/mnt/var/lib/instance-controller/public/shutdown-actions/`) rodam em paralelo no término, com 60 segundos cada, e **não** têm execução garantida quando o nó termina com erro. Não usar para nada que precise acontecer.

## 9. Segredo em configuração

Bloco Warning da própria documentação: *"Amazon EMR Describe and List API operations emit custom and configurable settings, which are used as a part of Amazon EMR job flows, in plaintext."*

A superfície não é log nem histórico de IaC: é a **resposta da API**, devolvida a qualquer principal com permissão de leitura sobre o cluster — que é a permissão amplamente concedida para observabilidade, inventário e FinOps. Um segredo em `Configurations` está exposto desde a criação do cluster, e não há como saber quem chamou `DescribeCluster` nesse intervalo.

O mecanismo oficial é referenciar o Secrets Manager em vez do literal. E como configuração de cluster não é editável em cluster em execução, a correção é sempre um cluster novo — mais a rotação do segredo, que é a parte que não pode ser adiada.

## Fontes

- Understand node types: primary, core, and task nodes. https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-master-core-task-nodes.html (retrieved 2026-08-01)
- Configuring Amazon EMR cluster instance types and best practices for Spot instances. https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-instances-guidelines.html (retrieved 2026-08-01)
- Using managed scaling in Amazon EMR. https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-managed-scaling.html (retrieved 2026-08-01)
- Configure Amazon EMR cluster logging and debugging. https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-debugging.html (retrieved 2026-08-01)
- Create bootstrap actions to install additional software with an Amazon EMR cluster. https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html (retrieved 2026-08-01)
- Configure Spark (inclui `maximizeResourceAllocation`). https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-configure.html (retrieved 2026-08-01)
- Configure applications (Warning sobre texto claro em Describe/List). https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-configure-apps.html (retrieved 2026-08-01)
- Store sensitive configuration data in AWS Secrets Manager. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/storing-sensitive-data.html (retrieved 2026-08-01)
- Requirements for the EMRFS S3-optimized committer. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-committer-reqs.html (retrieved 2026-08-01)
- Use the EMRFS S3-optimized commit protocol. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-s3-optimized-commit-protocol.html (retrieved 2026-08-01)
- Requirements for the EMRFS S3-optimized commit protocol. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-commit-protocol-reqs.html (retrieved 2026-08-01)
- A semântica de `static` — overwrite apagando o caminho de destino inteiro — é comportamento do Apache Spark e **não** foi encontrada declarada em nenhuma das páginas da AWS acima. Está aqui como leitura de campo, e é ela que sustenta o risco de perda de dado ao remover a propriedade do cluster. Confirmar contra a versão de Spark do cluster antes de agir.
- O número máximo de tipos de instância por frota não foi conferido nesta coleta. Não citar número; a afirmação que importa é "vários tipos com vCPU e memória diferentes", que a página de `maximizeResourceAllocation` sustenta.
