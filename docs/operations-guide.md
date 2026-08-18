# Guia operacional multiplataforma — SparkForge AWS

## 1. Objetivo e escopo

Este guia descreve como instalar, configurar, executar, validar e manter a plataforma agêntica do SparkForge AWS em Linux, macOS e Windows PowerShell. O projeto combina análise determinística de workloads AWS Glue, EMR, PySpark, Parquet, Iceberg e Athena com um runtime cooperativo de agents especializados. A metáfora de sala de conversa representa um protocolo: mensagens tipadas, contexto selecionado, handoffs verificáveis, revisão cruzada e critérios de parada. Não é uma interface de chat e não autoriza retransmitir o histórico inteiro.

A fonte declarativa de agents é `config/agents.yaml`; o runtime fica em `sparkforge/agents/`; a fonte de skills e agents está em `skills/` e `agents/`; os espelhos `.claude/`, `.agents/` e `.github/` são gerados por `scripts/sync_skills.py`. O protocolo compartilhado está em `AGENT_PROTOCOL.md`. O estado durável de um caso vive em `.sparkforge/case.yaml`, com findings, handoff e manifestos derivados em `.sparkforge/`.

> **Regra operacional:** fatos, evidências, hipóteses, decisões e recomendações permanecem separados. Um finding só é conclusivo quando tem evidência suficiente, escopo de runtime e validação proporcional ao risco.

## 2. Pré-requisitos e instalação

O pacote requer Python 3.10 ou superior. O extra `mcp` instala o servidor MCP; `aws` instala dependências de coleta AWS; `dev` instala ferramentas de desenvolvimento e testes. Credenciais AWS só são necessárias para coletores que consultem a conta. A análise estática e os testes estruturais rodam sem credenciais.

| Plataforma | Pré-requisitos | Ambiente | Observação |
| --- | --- | --- | --- |
| Linux | Git, Python 3.10+, Bash | `.venv` | Criar com `python3`, usar `python` após ativação |
| macOS | Homebrew, Git, Python 3.10+, Terminal | `.venv` | O mesmo fluxo funciona em zsh e Bash |
| Windows | Git, Python 3.10+, PowerShell | `.venv` | Pode ser necessário liberar scripts para o usuário atual |

### Linux — Bash

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pipgit clone https://github.com/EdgarSocrates98/spark-forge-aws.gitcd spark-forge-awspython3 -m venv .venv. .venv/bin/activatepython -m pip install --upgrade pippython -m pip install -e ".[dev,mcp,aws]"```

### macOS — Terminal

```bash/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"brew updatebrew install git pythongit clone https://github.com/EdgarSocrates98/spark-forge-aws.gitcd spark-forge-awspython3 -m venv .venvsource .venv/bin/activatepython -m pip install --upgrade pippython -m pip install -e ".[dev,mcp,aws]"```

### Windows — PowerShell

```powershellSet-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSignedgit clone https://github.com/EdgarSocrates98/spark-forge-aws.gitSet-Location .\spark-forge-awspy -3 -m venv .venv.\.venv\Scripts\Activate.ps1python -m pip install --upgrade pippython -m pip install -e ".[dev,mcp,aws]"```

Se `py` não existir, use `python` depois de instalar o Python oficial com PATH habilitado.

### Verificação em todas as plataformas

Linux — Bash:
```bashpython -m sparkforge.adapters.cli --versionpython -c "import sparkforge; print(sparkforge.__file__)"```

macOS — Terminal:
```bashpython3 -m sparkforge.adapters.cli --versionpython3 -c "import sparkforge; print(sparkforge.__file__)"```

Windows — PowerShell:
```powershellpython -m sparkforge.adapters.cli --versionpython -c "import sparkforge; print(sparkforge.__file__)"```

## 3. Configuração declarativa

Os defaults atuais são `max_rounds: 3`, `max_messages: 120`, `max_tokens: 12000`, `max_context_messages: 24`, `max_agents: 4`, `stagnation_limit: 2`, `cheap_before_expensive: true`, `require_evidence: true` e `require_approval_for_mutation: true`. O runtime preserva os kinds `task`, `fact`, `decision` e `snapshot`.

A política de modelos declara `source: coordinator_account_inventory` e `never_hardcode_models: true`. O coordenador Devin ou Claude deve consultar o inventário vivo da conta, escolher o modelo qualificável mais barato para baixo risco ou o melhor modelo qualificável para alto risco. Se nenhum modelo atender aos requisitos, deve parar e reportar indisponibilidade, nunca inventar um identificador.

A observabilidade inicial mantém `trace_view: false`, `show_content: false`, `token_notice: true`, `record_usage_when_available: true` e `estimate_when_unavailable: true`. Assim, metadados e consumo podem ser registrados sem expor conversas. Habilite conteúdo somente para depuração autorizada e desative depois.

| Campo | Função | Regra |
| --- | --- | --- |
| `max_rounds` | Limita ciclos | Aumentar só com evidência de progresso |
| `max_messages` | Limita mensagens | Evita conversa improdutiva |
| `max_tokens` | Orçamento agregado | Nunca remover o limite |
| `max_context_messages` | Janela compartilhada | Encaminhar fatos e decisões, não histórico inteiro |
| `max_agents` | Paralelismo | Manter baixo quando tarefas se sobrepõem |
| `stagnation_limit` | Estagnação | Parar repetição sem novidade |
| `cheap_before_expensive` | Escalonamento | Fazer gate barato antes do modelo forte |
| `require_evidence` | Evidência | Manter verdadeiro em produção |
| `require_approval_for_mutation` | Mutação | Manter verdadeiro sempre |

Linux — Bash:
```bashsed -n '1,220p' config/agents.yaml${EDITOR:-vi} config/agents.yaml```

macOS — Terminal:
```bashsed -n '1,220p' config/agents.yaml${EDITOR:-nano} config/agents.yaml```

Windows — PowerShell:
```powershellGet-Content .\config\agents.yamlnotepad .\config\agents.yaml```

## 4. Times de especialização

O coordenador começa pelo objetivo, detecta domínios, seleciona o menor contexto suficiente, delega tarefas estruturadas e solicita revisão cruzada. O catálogo detalhado está em `docs/teams-catalog.md`; a matriz de domínios, ferramentas e handoffs está em `knowledge/domain-tool-matrix.md`.

| Time | Agents | Uso |
| --- | --- | --- |
| Arquitetura de dados | `sf-data-architect`, `sf-storage-specialist`, `sf-s3-specialist`, `sf-iceberg-specialist`, `sf-parquet-specialist` | Lakehouse, camadas, contratos, formatos e layout |
| Arquitetura de pipelines | `sf-airflow-specialist`, `sf-step-functions-specialist`, `sf-lambda-serverless-specialist`, `sf-pyspark-specialist` | DAGs, state machines, eventos e jobs Spark |
| Analytics e regras | `sf-analytics-specialist`, `sf-functional-rules-specialist`, `sf-athena-specialist`, `sf-token-verifier` | Dados, SQL, semântica funcional e verificação |
| Plataforma | `sf-terraform-specialist`, `sf-runtime-specialist`, `sf-storage-specialist`, `sf-orchestrator` | IaC, runtime, governança, custo e coordenação |
| Grafos e NoSQL | `sf-graph-specialist`, `sf-neptune-specialist`, `sf-dynamodb-specialist` | Grafos, Neptune, chaves, índices e consistência |
| Engenharia de agents | `sf-agent-builder`, `sf-orchestrator`, `sf-token-verifier` | Skills, contratos, handoffs, loops e validação |

Linux — Bash:
```bashpython -m sparkforge.adapters.cli playbook sf-data-architect --repo .python -m sparkforge.adapters.cli playbook sf-airflow-specialist --repo .python -m sparkforge.adapters.cli playbook sf-agent-builder --repo .```

macOS — Terminal:
```bashpython3 -m sparkforge.adapters.cli playbook sf-data-architect --repo .python3 -m sparkforge.adapters.cli playbook sf-airflow-specialist --repo .python3 -m sparkforge.adapters.cli playbook sf-agent-builder --repo .```

Windows — PowerShell:
```powershellpython -m sparkforge.adapters.cli playbook sf-data-architect --repo .python -m sparkforge.adapters.cli playbook sf-airflow-specialist --repo .python -m sparkforge.adapters.cli playbook sf-agent-builder --repo .```

## 5. Ciclo de vida de casos

Um caso exige `case-id` estável, timestamp ISO-8601 explícito e runtime conhecido. A CLI não lê o relógio por conta própria. O fluxo é abrir, coletar ou analisar, derivar próximo passo, executar somente mudanças aprovadas, validar, assinar relatório e concluir ou fazer handoff.

### Abrir caso

Linux — Bash:
```bashpython -m sparkforge.adapters.cli case open \  --repo . \  --case-id lakehouse-review-001 \  --now 2026-08-18T12:00:00Z \  --glue 5.0 --emr emr-7.12.0 --spark 3.5.4 --python 3.11 \  --iceberg 1.7.1 --athena 3 --strict-gates```

macOS — Terminal:
```bashpython3 -m sparkforge.adapters.cli case open \  --repo . \  --case-id lakehouse-review-001 \  --now 2026-08-18T12:00:00Z \  --glue 5.0 --emr emr-7.12.0 --spark 3.5.4 --python 3.11 \  --iceberg 1.7.1 --athena 3 --strict-gates```

Windows — PowerShell:
```powershellpython -m sparkforge.adapters.cli case open `  --repo . `  --case-id lakehouse-review-001 `  --now 2026-08-18T12:00:00Z `  --glue 5.0 --emr emr-7.12.0 --spark 3.5.4 --python 3.11 `  --iceberg 1.7.1 --athena 3 --strict-gates```

### Analisar e coletar

A análise não executa jobs. Ela extrai facts de código, planos, logs e metadados. Se um artefato não puder ser resolvido, registre `*.unresolved`; ausência de evidência não é evidência de ausência.

Linux — Bash:
```bashpython -m sparkforge.adapters.cli analyze --helppython -m sparkforge.adapters.cli collect --helppython -m sparkforge.adapters.cli knowledge pathpython -m sparkforge.adapters.cli rules --help```

macOS — Terminal:
```bashpython3 -m sparkforge.adapters.cli analyze --helppython3 -m sparkforge.adapters.cli collect --helppython3 -m sparkforge.adapters.cli knowledge pathpython3 -m sparkforge.adapters.cli rules --help```

Windows — PowerShell:
```powershellpython -m sparkforge.adapters.cli analyze --helppython -m sparkforge.adapters.cli collect --helppython -m sparkforge.adapters.cli knowledge pathpython -m sparkforge.adapters.cli rules --help```

### Handoff e retomada

Use `.sparkforge/handoff.md`, `.sparkforge/findings.json` e `.sparkforge/artifacts/manifest.json` como barramento pequeno e verificável entre sessões. Não apague findings anteriores para esconder falhas.

Linux — Bash:
```bashpython -m sparkforge.adapters.cli next-step --repo . --findings .sparkforge/findings.jsonpython -m sparkforge.adapters.cli resume --repo . --findings .sparkforge/findings.jsonpython -m sparkforge.adapters.cli handoff --repo . --findings .sparkforge/findings.json --in-flight "validar benchmark" --unresolved 0```

macOS — Terminal:
```bashpython3 -m sparkforge.adapters.cli next-step --repo . --findings .sparkforge/findings.jsonpython3 -m sparkforge.adapters.cli resume --repo . --findings .sparkforge/findings.jsonpython3 -m sparkforge.adapters.cli handoff --repo . --findings .sparkforge/findings.json --in-flight "validar benchmark" --unresolved 0```

Windows — PowerShell:
```powershellpython -m sparkforge.adapters.cli next-step --repo . --findings .sparkforge/findings.jsonpython -m sparkforge.adapters.cli resume --repo . --findings .sparkforge/findings.jsonpython -m sparkforge.adapters.cli handoff --repo . --findings .sparkforge/findings.json --in-flight "validar benchmark" --unresolved 0```

### Validação e relatório

Benchmark compara facts e não executa jobs nem mede relógio. Validação funcional define o que comparar antes e depois. O relatório só deve ser entregue depois de assinado e verificado.

Linux — Bash:
```bashpython -m sparkforge.adapters.cli benchmark --helppython -m sparkforge.adapters.cli funcval --helppython -m sparkforge.adapters.cli report sign --helppython -m sparkforge.adapters.cli report verify --helppython -m sparkforge.adapters.cli validate --help```

macOS — Terminal:
```bashpython3 -m sparkforge.adapters.cli benchmark --helppython3 -m sparkforge.adapters.cli funcval --helppython3 -m sparkforge.adapters.cli report sign --helppython3 -m sparkforge.adapters.cli report verify --helppython3 -m sparkforge.adapters.cli validate --help```

Windows — PowerShell:
```powershellpython -m sparkforge.adapters.cli benchmark --helppython -m sparkforge.adapters.cli funcval --helppython -m sparkforge.adapters.cli report sign --helppython -m sparkforge.adapters.cli report verify --helppython -m sparkforge.adapters.cli validate --help```

## 6. Loops e critérios de parada

Cada rodada seleciona contexto mínimo, executa especialistas, registra mensagens tipadas, aplica gate de evidência, pede revisão e decide continuar, fazer handoff, solicitar dado ou parar. O loop deve parar quando o objetivo e os gates foram atendidos; o limite de rodadas, mensagens, tokens ou agents foi atingido; `stagnation_limit` foi atingido; uma dependência ficou `unresolved`; ou uma mutação exige aprovação humana.

O resultado não precisa fingir completude. Quando faltarem dados, entregue estado parcial explícito com lacuna, risco e próximo passo. Uma conversa infinita é falha de controle, não autonomia.

## 7. Economia de tokens sem impacto na qualidade

A economia reduz duplicação de contexto, não evidência. Encaminhe fatos, decisões, lacunas e snapshots necessários; referencie artefatos por caminho e checksum; use saídas estruturadas; deduplicate mensagens; limite paralelismo; e mantenha revisão cruzada focalizada.

O fluxo barato-primeiro faz triagem com o modelo qualificável mais barato, valida schema e completude programaticamente e escala apenas falhas, alto risco ou revisão difícil. Não remova fonte, risco, validação ou evidência para economizar tokens.

| Técnica | Configuração ou prática | Garantia |
| --- | --- | --- |
| Contexto seletivo | `max_context_messages: 24` | Preserva evidência relevante |
| Rodadas limitadas | `max_rounds: 3` | Evita deliberação infinita |
| Estagnação | `stagnation_limit: 2` | Para repetição sem novidade |
| Paralelismo | `max_agents: 4` | Evita duplicidade e custo oculto |
| Gate barato | `cheap_before_expensive: true` | Escala somente o necessário |
| Mensagens tipadas | `task`, `fact`, `decision`, `snapshot` | Facilita handoff e validação |
| Observação de custo | `token_notice: true` | Exibe aviso quando houver métrica |

Nunca hardcode a lista de modelos. O coordenador consulta o inventário da conta e registra a decisão quando houver trace. Nenhum modelo disponível deve ser tratado como se estivesse garantido no futuro.

## 8. Observabilidade opcional

O padrão é trace desligado e conteúdo oculto. `record_usage_when_available` grava uso real quando fornecido; `estimate_when_unavailable` marca estimativas; `token_notice` avisa sobre custo. Para depuração autorizada, faça backup, habilite temporariamente, execute e restaure.

Linux — Bash:
```bashcp config/agents.yaml config/agents.yaml.baksed -i 's/trace_view: false/trace_view: true/' config/agents.yamlsed -i 's/show_content: false/show_content: true/' config/agents.yamlpython -m sparkforge.adapters.cli playbook sf-orchestrator --repo .mv config/agents.yaml.bak config/agents.yaml```

macOS — Terminal:
```bashcp config/agents.yaml config/agents.yaml.baksed -i '' 's/trace_view: false/trace_view: true/' config/agents.yamlsed -i '' 's/show_content: false/show_content: true/' config/agents.yamlpython3 -m sparkforge.adapters.cli playbook sf-orchestrator --repo .mv config/agents.yaml.bak config/agents.yaml```

Windows — PowerShell:
```powershellCopy-Item .\config\agents.yaml .\config\agents.yaml.bak(Get-Content .\config\agents.yaml) -replace 'trace_view: false','trace_view: true' | Set-Content .\config\agents.yaml -Encoding utf8(Get-Content .\config\agents.yaml) -replace 'show_content: false','show_content: true' | Set-Content .\config\agents.yaml -Encoding utf8python -m sparkforge.adapters.cli playbook sf-orchestrator --repo .Move-Item -Force .\config\agents.yaml.bak .\config\agents.yaml```

## 9. Sincronização de skills e agents

A fonte de verdade fica em `skills/` e `agents/`; nunca edite `.claude/`, `.agents/` ou `.github/` manualmente. O sincronizador valida frontmatter, seções contratuais, paridade e espelhos.

Linux — Bash:
```bashpython scripts/sync_skills.pypython scripts/sync_skills.py --check```

macOS — Terminal:
```bashpython3 scripts/sync_skills.pypython3 scripts/sync_skills.py --check```

Windows — PowerShell:
```powershellpython .\scripts\sync_skills.pypython .\scripts\sync_skills.py --check```

## 10. Claude Code, Devin e MCP

`commands/sf-open.md`, `sf-next.md`, `sf-resume.md` e `sf-handoff.md` são comandos do host agêntico. `/sf-open`, `/sf-next`, `/sf-resume` e `/sf-handoff` são invocados no Claude Code ou host que carregou os comandos; não são binários independentes. No terminal, use `case`, `next-step`, `resume` e `handoff` da CLI.

O MCP é opcional e usa stdio. Não coloque tokens ou chaves AWS em `.mcp.json`.

Linux — Bash:
```bashpython -m pip install -e ".[mcp]"python -m sparkforge.adapters.mcp --transport stdio --repo .```

macOS — Terminal:
```bashpython3 -m pip install -e ".[mcp]"python3 -m sparkforge.adapters.mcp --transport stdio --repo .```

Windows — PowerShell:
```powershellpython -m pip install -e ".[mcp]"python -m sparkforge.adapters.mcp --transport stdio --repo .```

## 11. Domínios e saídas mínimas

O roteamento deve se basear no artefato e na evidência. PySpark/Glue/EMR exigem runtime, gargalo, mudança isolada e benchmark. Iceberg/Parquet/S3 exigem layout, metadados, impacto e risco de migração. Athena exige SQL, filtros, partições, engine e bytes lidos. Airflow/Step Functions exigem dependências, retry, timeout e idempotência. Lambda exige evento, contrato, limite e duplicação. DynamoDB exige padrões de acesso, PK/SK, índices e consistência. Neptune exige modelo, linguagem, cardinalidade e traversal. Terraform exige plano, estado, permissões e detecção de destruição.

Se faltar código, plano, log, schema, metadado, listagem S3, DAG, state machine, Terraform ou contrato funcional, peça o artefato ou registre `unresolved`. Nunca invente uma configuração.

## 12. Testes e gates

Antes de alterar runtime, skill, agent, regra ou espelho, capture status, leia `AGENTS.md`, rode teste focalizado e depois a suíte completa. Regras `status: structural` são declarativas e não devem ser tratadas como investigação executável.

Linux — Bash:
```bashgit status --shortpython -m pytest tests/test_dq_investigation_end_to_end.py -qpython -m pytest -qpython scripts/sync_skills.py --checkgit diff --check```

macOS — Terminal:
```bashgit status --shortpython3 -m pytest tests/test_dq_investigation_end_to_end.py -qpython3 -m pytest -qpython3 scripts/sync_skills.py --checkgit diff --check```

Windows — PowerShell:
```powershellgit status --shortpython -m pytest tests/test_dq_investigation_end_to_end.py -qpython -m pytest -qpython .\scripts\sync_skills.py --checkgit diff --check```

A suíte final desta entrega registrou `5354 passed, 5 skipped` em `698.92s`, sem falhas. Reexecute após qualquer mudança.

## 13. Troubleshooting

Módulo ausente: confirme ambiente e reinstale editável. MCP sem inicializar: execute foreground, valide stdio e não misture diagnóstico no stdout. Sincronização falha: corrija a fonte e rode `--check`, nunca o espelho. Finding ausente: procure facts faltantes, runtime fora de escopo ou regra estrutural.

Linux — Bash:
```bashwhich pythonpython -m pip show sparkforge-awspython -m sparkforge.adapters.cli --helppython -m sparkforge.adapters.mcp --help```

macOS — Terminal:
```bashwhich python3python3 -m pip show sparkforge-awspython3 -m sparkforge.adapters.cli --helppython3 -m sparkforge.adapters.mcp --help```

Windows — PowerShell:
```powershellGet-Command pythonpython -m pip show sparkforge-awspython -m sparkforge.adapters.cli --helppython -m sparkforge.adapters.mcp --help```

## 14. Segurança e manutenção

Nenhum agent pode apagar dados, sobrescrever estado ou publicar mudança irreversível sem confirmação e registro. O caminho padrão é somente leitura: coletar, analisar, propor, revisar, validar e relatar. Mutações precisam de plano, impacto, rollback, aprovação e evidência posterior. Não versione credenciais, dumps sensíveis ou conversas completas sem necessidade. Use IAM de menor privilégio, região explícita e perfis isolados.

## Referências oficiais

[1]: https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html "What is AWS Glue?"
[2]: https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html "What is Amazon EMR?"
[3]: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html "Amazon S3 User Guide"
[4]: https://docs.aws.amazon.com/athena/latest/ug/what-is.html "What is Amazon Athena?"
[5]: https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html "What is AWS Step Functions?"
[6]: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html "What is AWS Lambda?"
[7]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html "What is Amazon DynamoDB?"
[8]: https://docs.aws.amazon.com/neptune/latest/userguide/intro.html "What is Amazon Neptune?"
[9]: https://iceberg.apache.org/docs/latest/aws/ "Apache Iceberg on AWS"
[10]: https://parquet.apache.org/docs/ "Apache Parquet Documentation"
[11]: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html "Apache Airflow Core Concepts"
[12]: https://developer.hashicorp.com/terraform/docs "Terraform Documentation"

*Autor: Manus AI. Documento operacional mantido junto com o contrato do repositório.*
