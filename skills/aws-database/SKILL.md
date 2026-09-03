---
name: aws-database
description: Use quando precisar escolher, comparar, recomendar, iniciar ou operar um banco de dados AWS — roteia para o servico correto entre Aurora, DSQL, RDS, DynamoDB, ElastiCache, MemoryDB, DocumentDB, Keyspaces, Timestream, Neptune. Aplica quando alguem descreve uma aplicacao que vai armazenar, recuperar ou gerenciar dados na AWS, mesmo sem mencionar "banco de dados" explicitamente. Cobre relacional (Aurora, DSQL, RDS PostgreSQL/MySQL/MariaDB/Oracle/SQL Server/Db2), key-value (DynamoDB), wide-column (Keyspaces), documento (DocumentDB), grafo (Neptune), serie temporal (Timestream) e em-memory/cache (ElastiCache, MemoryDB). NAO use para armazenamento de objeto/arquivo (S3, EFS, FSx — use aws-storage) nem para analytics query engines (Athena, Redshift).
---

# AWS Database

**PARE — Nao responda de conhecimento geral.** Antes de responder a qualquer pergunta de
banco de dados, confronte o pedido do usuario com o registro de sub-skills abaixo e siga
seu procedimento. Se o procedimento diz para entregar a uma skill de servico, voce DEVE
carregar aquela skill antes de fornecer orientacao operacional. Nunca pule o roteamento.

Bancos de dados AWS compreendem 15+ engines totalmente gerenciados, otimizados por forma
de workload ou modelo de dado — relacional (Aurora, DSQL, RDS), key-value (DynamoDB),
wide-column (Keyspaces), documento (DocumentDB), grafo (Neptune), serie temporal
(Timestream) e em-memory (ElastiCache, MemoryDB). Para workloads relacionais, a AWS
suporta PostgreSQL (Aurora, DSQL, RDS), MySQL (Aurora, RDS), MariaDB (RDS), Oracle (RDS,
ODB@AWS), SQL Server (RDS) e Db2.

Use esta skill como ponto de entrada para qualquer acao ou pergunta sobre bancos na AWS.
Ela ajuda a casar workload com o servico certo, ou entregar a uma skill de servico
especifico para questoes operacionais.

Funciona com ou sem o AWS MCP server. Quando disponivel, o AWS MCP server e recomendado
para execucao em sandbox e audit logging.

## Regras globais

1. **Revise quando nova informacao chegar.** Se o usuario discordar ou adicionar detalhes,
   re-verifique os gatilhos do registro de sub-skills antes de responder. Discordancia que
   casa com `report-issue` ("isso esta errado", "voce escolheu o servico errado") deve
   rotear para `report-issue` — nao defenda a recomendacao anterior. O objetivo e a
   resposta certa, nao consistencia com a primeira resposta.

2. **Nao confie em conhecimento de treino para fatos.** Bancos AWS mudam frequentemente.
   Antes de declarar precos, quotas ou status GA, verifique contra as referencias
   carregadas por esta skill. Se o fato nao esta em uma referencia, procure — em ordem de
   prioridade: (a) use o AWS MCP server (`aws___read_documentation`,
   `aws___search_documentation`) se disponivel; (b) direcione o usuario a documentacao
   AWS. Se o usuario menciona uma feature nao coberta, procure em vez de adivinhar.

3. **Verifique, nao chute.** Se nao puder confirmar um fato de uma referencia ou
   documentacao, diga. "Nao tenho certeza — confira a docs" e melhor que uma resposta
   confiante e errada.

## Como esta skill funciona

1. **Encontre a sub-skill** — Caso o pedido do usuario contra o registro abaixo. Case por
   significado, nao por palavras exatas. Se ambiguo, pergunte: "Voce esta escolhendo um
   banco, ou precisa de ajuda com um que ja tem?" **Este casamento se aplica a cada
   mensagem do usuario, nao apenas a primeira.**

2. **Se uma sub-skill casa** — leia `references/{sub-skill-id}.md` e siga seu procedimento.

3. **Se nenhuma sub-skill casa** — responda a partir das referencias de servico. Se a
   referencia nao cobre, use ferramentas de documentacao se disponiveis, ou direcione o
   usuario a documentacao AWS. Sempre ofereca carregar a skill de servico para orientacao
   mais profunda.

## Registro de sub-skills

| ID | Nome | Gatilhos | Quando rotear aqui | Proximos passos |
|----|------|----------|-------------------|-----------------|
| `select` | Selecao de banco | "qual banco", "ajude a escolher", "recomende", "o que devo usar", "novo projeto", "preciso de um banco", "estou construindo", "melhor forma de armazenar", "preciso suportar", "desenhar para" | Usuario nao escolheu servico, esta comparando, ou descreve workload sem nomear servico | `handoff` |
| `handoff` | Entrega de servico | "como configuro", "otimizar", "troubleshoot", "set up", "migrar para", "conectar a", "escalar", "upgrade", "monitorar", "backup", "restore", "criar", "deploy", "provisionar" + servico nomeado | Usuario nomeia servico AWS especifico e tem pergunta operacional, consultiva ou de acao | — |
| `report-issue` | Reportar problema | "isso esta errado", "incorreto", "recomendacao ruim", "voce deveria ter dito", "faltando", "skill errada", "reportar", "abrir bug" | Usuario reporta que a skill deu orientacao incorreta ou incompleta | — |

## Referencia de servicos

Carregue referencias sob demanda — apenas quando o turno corrente requer verificar ou
declarar fatos sobre um servico. As knowledge cards do upstream (`assets/*.md`) nao sao
copiadas localmente; quando precisar de fato especifico de servico, consulte a
documentacao AWS ou o AWS MCP server.

| Servico | Skill SparkForge relacionada |
|---------|-------------------------------|
| Aurora DSQL | — |
| Aurora MySQL | — |
| Aurora PostgreSQL | — |
| DocumentDB | — |
| DynamoDB | `design-dynamodb-model` |
| ElastiCache | — |
| Keyspaces | — |
| MemoryDB | — |
| Neptune | `design-neptune-graph` |
| ODB @ AWS | — |
| RDS for Db2 | — |
| RDS for MariaDB | — |
| RDS for MySQL | — |
| RDS for Oracle | — |
| RDS for PostgreSQL | — |
| RDS for SQL Server | — |
| Timestream | — |

## Referência rápida

| Topico | Referencia |
| --- | --- |
| Selecao de banco de dados | `references/select.md` |
| Entrega para skill de servico | `references/handoff.md` |
| Reportar problema com a skill | `references/report-issue.md` |

### Skills SparkForge relacionadas

| Topico | Skill |
| --- | --- |
| Modelar dados no DynamoDB | `design-dynamodb-model` |
| Desenhar grafo no Neptune | `design-neptune-graph` |

## Quando NÃO usar

- **Armazenamento de objeto/arquivo/bloco** (S3, EFS, FSx, EBS): roteie para `aws-storage`.
- **Analytics query engines** (Athena, Redshift, EMR): nao sao bancos transacionais —
  use `optimize-athena-queries` ou as skills de performance Spark/Glue.
- **Streaming** (Kafka, MSK, Kinesis): roteie para `aws-messaging-and-streaming`.
- **Modelagem de DynamoDB**: a selecao de servico roteia aqui, mas o desenho de modelo
  pertence a `design-dynamodb-model`.
- **Modelagem de grafo Neptune**: a selecao roteia aqui, mas o desenho de grafo pertence
  a `design-neptune-graph`.
- **Migracao de banco para AWS**: use o procedimento de `handoff` para o servico alvo, nao
  tente aconselhar migracao sem carregar a skill de servico.

## Red flags

- Recomendar um banco de dados sem ter carregado `references/select.md` — o procedimento
  de selecao tem fatores de decisao e armadilhas que nao estao na memoria.
- Declarar preco, quota ou status GA de memoria — bancos AWS mudam frequentemente;
  verifique contra documentacao ou MCP server.
- Defender uma recomendacao anterior quando o usuario discorda — re-rodeie para
  `report-issue` em vez de insistir.
- Responder pergunta operacional de servico sem carregar a sub-skill `handoff` — pular o
  roteamento e o defeito que esta skill existe para evitar.
- Tratar Aurora DSQL como "mais um Aurora" — e um produto distinto com modelo de
  concorrencia e limites proprios; verifique a referencia antes de aconselhar.
- Nao mencionar ElastiCache/MemoryDB quando o usuario pede baixa latencia em memoria —
  sao a resposta para cache e sessao em memoria.

## Não faz

Esta skill e procedimento operacional que pode mutar infraestrutura AWS ao vivo. Nao
executa comandos de escrita sem confirmacao explicita do operador. Nao despacha como
subagente.

Comandos de escrita — `create-db-instance`, `create-table`, `modify-db-cluster`,
`create-global-table`, `create-cache-cluster` — voce **nao executa**. Recomende o comando,
exiba o que ele faz, e **suba a decisao** a quem pode ser perguntado — o operador na
sessao, ou o agente pai que despachou. Dentro de um subagente, obter essa confirmacao e
**impossivel** (`ask_user_question` e sempre negado a subagente), e por isso esta skill
**nao despacha**.

Manutencao destrutiva — `delete-db-instance`, `delete-table`, `delete-cluster`, remocao
de snapshot — voce **nao executa**. Recomende, e a confirmacao de escopo e retencao sobe
a quem tem a pergunta disponivel.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-database`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream e a fonte autoritativa
dos arquivos de referencia (`references/select.md`, `references/handoff.md`,
`references/report-issue.md`) e das knowledge cards de servico (`assets/*.md`, nao
copiadas localmente). Esta e uma adaptacao ao contrato SparkForge (PT-BR, fronteira de
manutencao, nao-despachavel) e **pode desatualizar** quando a AWS atualizar servicos ou
procedimentos. Antes de reproduzir comando de escrita, confira o upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme o servico e a
regiao; nenhum numero sem verificacao contra documentacao corrente ou referencia;
manutencao destrutiva voce **nao executa** — recomende, e a confirmacao de escopo e
retencao **sobe a quem pode ser perguntado**: o operador na sessao, ou o agente pai que
despachou.
