# Guia do SparkForge AWS

Manuais simples para usar tudo o que o projeto tem. Cada manual começa com uma
**receita rápida** (poucos comandos para copiar e colar) e depois explica o resto.

## Comece aqui

1. [O que é o SparkForge, em palavras simples](01-conceitos.md), com o glossário.
2. [Instalação](02-instalacao.md).
3. [Usando a CLI (a linha de comando)](03-cli.md).
4. [Usando pelo MCP (Claude Code, Devin, Copilot e outros)](04-mcp.md).
5. [Agents e skills: quem faz o quê](05-agents-e-skills.md).

## Manuais por tarefa

| Eu quero... | Manual |
|---|---|
| Conferir o ambiente e rodar tudo o que cabe no repositório de uma vez | [Scan e doctor](usos/scan-e-doctor.md) |
| Descobrir por que um job PySpark no Glue está lento | [Job lento](usos/job-lento.md) |
| Saber quanto um job custa e qual capacidade escolher | [Custo e capacidade](usos/custo-e-capacidade.md) |
| Cuidar de tabelas Iceberg e arquivos Parquet | [Iceberg e Parquet](usos/iceberg-e-parquet.md) |
| Otimizar consultas no Athena e SQL | [Athena e SQL](usos/athena-e-sql.md) |
| Entender quem pode ler e escrever (Lake Formation, IAM) | [Lake Formation e acesso](usos/lake-formation-e-acesso.md) |
| Migrar a versão do Glue ou ir para o EMR | [Migração de versão](usos/migracao-de-versao.md) |
| Revisar jobs do Control-M | [Control-M](usos/control-m.md) |
| Coletar artefatos da conta AWS | [Coleta na AWS](usos/coleta-na-aws.md) |
| Levar o SparkForge para o CI e o pull request | [CI e GitHub](usos/ci-e-github.md) |
| Conduzir uma investigação com memória (case) | [Investigação com case](usos/investigacao-com-case.md) |
| Resolver dois achados que se contradizem | [Arbitragem e debate](usos/arbitragem-e-debate.md) |
| Provar que uma mudança funcionou | [Mudanças com prova](usos/mudancas-com-prova.md) |
| Consultar regras, fontes e packs de terceiros | [Packs e conhecimento](usos/packs-e-conhecimento.md) |
| Achar código sem ler arquivo por arquivo | [Inteligência de código](usos/code-intelligence.md) |
| Medir quanto contexto uma sessão gastou | [Economia de contexto](usos/economia-de-contexto.md) |

## Referência completa

Uma página para cada comando, tool, agent e skill, gerada direto do código (nunca
fica desatualizada):

- [Comandos da CLI](referencia/cli/README.md)
- [Tools MCP](referencia/tools/README.md)
- [Agents](referencia/agents/README.md)
- [Skills](referencia/skills/README.md)

A referência é regenerada com `python scripts/gen_reference_docs.py`, e um teste
falha se ela ficar diferente do código.
