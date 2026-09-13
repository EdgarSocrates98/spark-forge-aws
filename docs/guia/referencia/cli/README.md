<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Referência da CLI

Um comando de topo por página, com todos os subcomandos e opções. Todo comando imprime JSON na saída padrão; `--help` mostra o mesmo texto no terminal.

| Comando | O que faz |
|---|---|
| [`sparkforge agents`](agents.md) | Lista e inspeciona agentes do runtime agêntico. |
| [`sparkforge analyze`](analyze.md) | Extrai facts deterministicos de codigo-fonte. |
| [`sparkforge arbitrate`](arbitrate.md) | Executor agentico deterministico: arbitra findings ja julgados e grava claim, evidencia, contradicao, lacuna e decisao no blackboard do case. |
| [`sparkforge autonomy`](autonomy.md) | Mostra níveis de autonomia L0-L5. |
| [`sparkforge benchmark`](benchmark.md) | Compara duas execucoes a partir dos facts de event log de cada uma. |
| [`sparkforge blackboard`](blackboard.md) | Lê o shared blackboard (.sparkforge/blackboard/). |
| [`sparkforge budget`](budget.md) | Mostra estado do budget do case. |
| [`sparkforge capacity`](capacity.md) | Escolhe a capacidade mais barata que cumpre o SLA, entre as capacidades que o job JA rodou. |
| [`sparkforge case`](case.md) | Gerencia o estado do case em .sparkforge/case.yaml. |
| [`sparkforge code`](code.md) | Indice local de codigo: prepara, sincroniza, busca simbolo, monta contexto e diagnostica. |
| [`sparkforge collect`](collect.md) | Coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg). |
| [`sparkforge controlm`](controlm.md) | Conhecimento versionado do Control-M Automation API. |
| [`sparkforge debate`](debate.md) | Conduz e arbitra o protocolo de debate do case. |
| [`sparkforge decisions`](decisions.md) | Lista e explica decisões registradas. |
| [`sparkforge economy`](economy.md) | O que a execucao poe na janela de contexto: byte medido, nunca token estimado. |
| [`sparkforge finops`](finops.md) | O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta -- capacidade ou codigo. |
| [`sparkforge funcval`](funcval.md) | Validacao funcional: deriva o que medir nos dois lados de uma mudanca e compara antes contra depois. |
| [`sparkforge fuse`](fuse.md) | Correlaciona facts de SQL com schema do catalogo (sparkforge.facts.fusion), antes de judge. |
| [`sparkforge gain`](gain.md) | Ganho OBSERVADO entre runs medidos antes e depois de uma mudanca: por lado, N, mediana, minimo e maximo de tempo, DPU-segundos e custo, e o delta das medianas. |
| [`sparkforge glue`](glue.md) | Comandos especificos do runtime AWS Glue. |
| [`sparkforge handoff`](handoff.md) | Escreve .sparkforge/handoff.md e imprime o payload. |
| [`sparkforge iceberg`](iceberg.md) | Comandos especificos de Apache Iceberg. |
| [`sparkforge judge`](judge.md) | Aplica o catalogo de regras versionado sobre facts ja extraidos. |
| [`sparkforge knowledge`](knowledge.md) | Localiza os arquivos de conhecimento versionado. |
| [`sparkforge lakeformation`](lakeformation.md) | Eixo de VERSAO de Lake Formation por runtime Glue -- capacidade, nao versao de componente. |
| [`sparkforge migrate`](migrate.md) | Avalia migracao entre versoes de runtime com o catalogo. |
| [`sparkforge next-step`](next-step.md) | Rota deterministica a partir de routing.yaml (nunca julgamento do agente). |
| [`sparkforge pack`](pack.md) | Forge Packs: regras, knowledge e fixtures de terceiro (SPARKFORGE_PACKS). |
| [`sparkforge playbook`](playbook.md) | Decomposicao de um coordenador em passos sequenciais -- o PISO de orquestracao das cinco plataformas: unico caminho em Codex e Copilot CI, e o caminho em Claude Code, Devin CLI... |
| [`sparkforge proof`](proof.md) | Obrigacoes de prova de cada recomendacao APLICADA: resolucao (a regra deixou de disparar no depois?) e um eixo por item de action.moves (funcval, benchmark ou sem comparador). |
| [`sparkforge receipt`](receipt.md) | Recibo content-addressed da execucao do case: prova CORRESPONDENCIA entre o recibo e os artefatos, nunca autoria. |
| [`sparkforge release`](release.md) | O que uma release publica, e o que muda entre duas. |
| [`sparkforge report`](report.md) | Assinatura de CORRESPONDENCIA do relatorio: prova que o texto foi derivado daquela evidencia com aquele catalogo. |
| [`sparkforge resume`](resume.md) | Payload de rehidratacao do case. |
| [`sparkforge root-cause`](root-cause.md) | Ordena os achados por consequencia declarada e nomeia a lacuna. |
| [`sparkforge rules`](rules.md) | Consulta o catalogo de regras versionado. |
| [`sparkforge runtime`](runtime.md) | Deteccao de runtime Glue/EMR/Spark/Python/Iceberg/Athena. |
| [`sparkforge simulate`](simulate.md) | O que uma mudanca de configuracao move, estruturalmente: altera o valor de facts que ja existem, rederiva e julga os dois lados, e diz que achados somem e aparecem. |
| [`sparkforge telemetry`](telemetry.md) | Os spans de tool e o transcript do host em OTLP/JSON, para um OTLP Collector. |
| [`sparkforge tune`](tune.md) | Configuracao Spark derivada da medida, com a procedencia de cada propriedade. |
| [`sparkforge validate`](validate.md) | Valida findings contra o JSON Schema e a regra de ganho sem benchmark_ref. |
| [`sparkforge workload`](workload.md) | Perfil de workload por eixos, a partir de facts ja extraidos. |
