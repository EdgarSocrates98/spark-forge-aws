<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Referência da CLI

Um comando de topo por página, com todos os subcomandos e opções. Todo comando imprime JSON na saída padrão; `--help` mostra o mesmo texto no terminal.

| Comando | O que faz |
|---|---|
| [`sparkforge-aws agentops`](agentops.md) | Inspeciona runs locais, compara baseline e atribui desperdicio observado. |
| [`sparkforge-aws agents`](agents.md) | Lista e inspeciona agentes do runtime agêntico. |
| [`sparkforge-aws analyze`](analyze.md) | Extrai facts deterministicos de codigo-fonte. |
| [`sparkforge-aws arbitrate`](arbitrate.md) | Executor agentico deterministico: arbitra findings ja julgados e grava claim, evidencia, contradicao, lacuna e decisao no blackboard do case. |
| [`sparkforge-aws architecture`](architecture.md) | Avalia arquitetura declarada sem escolher por preferência ou custo inventado. |
| [`sparkforge-aws autonomy`](autonomy.md) | Mostra níveis de autonomia L0-L5. |
| [`sparkforge-aws benchmark`](benchmark.md) | Compara duas execucoes a partir dos facts de event log de cada uma. |
| [`sparkforge-aws blackboard`](blackboard.md) | Lê o shared blackboard (.sparkforge_aws/blackboard/). |
| [`sparkforge-aws budget`](budget.md) | Mostra estado do budget do case. |
| [`sparkforge-aws capacity`](capacity.md) | Escolhe a capacidade mais barata que cumpre o SLA, entre as capacidades que o job JA rodou. |
| [`sparkforge-aws case`](case.md) | Gerencia o estado do case em .sparkforge_aws/case.yaml. |
| [`sparkforge-aws change`](change.md) | Autonomia L1-L2: gera o diff de um valor de configuracao (plan) e aplica um diff numa copia isolada para ver o que ele move nos achados (sandbox). |
| [`sparkforge-aws code`](code.md) | Indice local de codigo: prepara, sincroniza, busca simbolo, monta contexto e diagnostica. |
| [`sparkforge-aws collect`](collect.md) | Coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg). |
| [`sparkforge-aws context`](context.md) | Descobre capabilities e empacota contexto deterministico sob limite explicito. |
| [`sparkforge-aws controlm`](controlm.md) | Conhecimento versionado do Control-M Automation API. |
| [`sparkforge-aws debate`](debate.md) | Conduz e arbitra o protocolo de debate do case. |
| [`sparkforge-aws decision`](decision.md) | Valida e observa decisões declarativas sem alterar o dispatch atual. |
| [`sparkforge-aws decisions`](decisions.md) | Lista e explica decisões registradas. |
| [`sparkforge-aws detach`](detach.md) | Remove a integracao de usuario do host: so o que o manifesto ~/.sparkforge_aws/integrations.json registrou e ainda tem o sha256 gravado. |
| [`sparkforge-aws distribution`](distribution.md) | Inspeção e inicialização portátil offline. |
| [`sparkforge-aws doctor`](doctor.md) | Confere se o ambiente esta pronto: pacote, extras, MCP, catalogo, packs, knowledge, indice de codigo, artefatos, credencial AWS e a integracao de usuario de cada host. |
| [`sparkforge-aws dq-ai`](dq-ai.md) | Avalia governanca Glue DQ ADVANCED sobre facts e artefatos observados. |
| [`sparkforge-aws economy`](economy.md) | O que a execucao poe na janela de contexto: byte medido, nunca token estimado. |
| [`sparkforge-aws finops`](finops.md) | O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta -- capacidade ou codigo. |
| [`sparkforge-aws funcval`](funcval.md) | Validacao funcional: deriva o que medir nos dois lados de uma mudanca e compara antes contra depois. |
| [`sparkforge-aws fuse`](fuse.md) | Correlaciona facts de SQL com schema do catalogo (sparkforge_aws.facts.fusion), antes de judge. |
| [`sparkforge-aws gain`](gain.md) | Ganho OBSERVADO entre runs medidos antes e depois de uma mudanca: por lado, N, mediana, minimo e maximo de tempo, DPU-segundos e custo, e o delta das medianas. |
| [`sparkforge-aws glue`](glue.md) | Comandos especificos do runtime AWS Glue. |
| [`sparkforge-aws handoff`](handoff.md) | Escreve .sparkforge_aws/handoff.md e imprime o payload. |
| [`sparkforge-aws iceberg`](iceberg.md) | Comandos especificos de Apache Iceberg. |
| [`sparkforge-aws integrate`](integrate.md) | Instala skills, agents e o MCP do SparkForge nos diretorios de USUARIO do host (Claude Code por marketplace local; Devin, Codex e Copilot CLI), a partir do pacote instalado. |
| [`sparkforge-aws journal`](journal.md) | Journal de eventos do case (.sparkforge_aws/journal.jsonl): um started e um finished por verbo que muda estado, encadeados por hash. |
| [`sparkforge-aws judge`](judge.md) | Aplica o catalogo de regras versionado sobre facts ja extraidos. |
| [`sparkforge-aws knowledge`](knowledge.md) | Localiza os arquivos de conhecimento versionado. |
| [`sparkforge-aws lab`](lab.md) | Planeja e inspeciona experimentos Forge Lab; execução mutável exige confirmação explícita. |
| [`sparkforge-aws lakeformation`](lakeformation.md) | Eixo de VERSAO de Lake Formation por runtime Glue -- capacidade, nao versao de componente. |
| [`sparkforge-aws migrate`](migrate.md) | Avalia migracao entre versoes de runtime com o catalogo. |
| [`sparkforge-aws next-step`](next-step.md) | Rota deterministica a partir de routing.yaml (nunca julgamento do agente). |
| [`sparkforge-aws pack`](pack.md) | Forge Packs: regras, knowledge e fixtures de terceiro (SPARKFORGE_AWS_PACKS). |
| [`sparkforge-aws playbook`](playbook.md) | Decomposicao de um coordenador em passos sequenciais -- o PISO de orquestracao das cinco plataformas: unico caminho em Codex e Copilot CI, e o caminho em Claude Code, Devin CLI... |
| [`sparkforge-aws policy`](policy.md) | Politica de seguranca do repositorio (.sparkforge_aws/policy.yaml): validar, explicar uma decisao e gerar as regras ask do .claude/settings.json. |
| [`sparkforge-aws proof`](proof.md) | Obrigacoes de prova de cada recomendacao APLICADA: resolucao (a regra deixou de disparar no depois?) e um eixo por item de action.moves (funcval, benchmark ou sem comparador). |
| [`sparkforge-aws receipt`](receipt.md) | Recibo content-addressed da execucao do case: prova CORRESPONDENCIA entre o recibo e os artefatos, nunca autoria. |
| [`sparkforge-aws release`](release.md) | O que uma release publica, e o que muda entre duas. |
| [`sparkforge-aws report`](report.md) | Assinatura de CORRESPONDENCIA do relatorio: prova que o texto foi derivado daquela evidencia com aquele catalogo. |
| [`sparkforge-aws resume`](resume.md) | Payload de rehidratacao do case. |
| [`sparkforge-aws root-cause`](root-cause.md) | Ordena os achados por consequencia declarada e nomeia a lacuna. |
| [`sparkforge-aws rules`](rules.md) | Consulta o catalogo de regras versionado. |
| [`sparkforge-aws runtime`](runtime.md) | Deteccao de runtime Glue/EMR/Databricks/Spark/Python/Iceberg/Athena. |
| [`sparkforge-aws scan`](scan.md) | Roda sozinho os analyzes que cabem num repositorio: artefato coletado pelo manifesto, codigo pela extensao; depois fuse, judge e um resumo em .sparkforge_aws/scan/. |
| [`sparkforge-aws sdd`](sdd.md) | Confere os artefatos de spec em docs/sdd/<FEATURE>/<fase>.md: recusa por nome o que nao fecha, sem julgar a prosa. |
| [`sparkforge-aws simulate`](simulate.md) | O que uma mudanca de configuracao move, estruturalmente: altera o valor de facts que ja existem, rederiva e julga os dois lados, e diz que achados somem e aparecem. |
| [`sparkforge-aws telemetry`](telemetry.md) | Os spans de tool e o transcript do host em OTLP/JSON, para um OTLP Collector. |
| [`sparkforge-aws tune`](tune.md) | Configuracao Spark derivada da medida, com a procedencia de cada propriedade. |
| [`sparkforge-aws validate`](validate.md) | Valida findings contra o JSON Schema e a regra de ganho sem benchmark_ref. |
| [`sparkforge-aws workload`](workload.md) | Perfil de workload por eixos, a partir de facts ja extraidos. |
| [`sparkforge-aws workspace`](workspace.md) | Workspace virtual declarado e descoberta limitada. |
