---
name: analyze-graph-data
description: Use quando for necessario modelar, analisar ou consultar dados em grafos, caminhos, comunidades e relacionamentos.
---
# Dados em Grafos

Use a especialidade para coletar evidencias, comparar alternativas, validar custo, risco, testes e rollback.

## Quando NAO usar

Nao use quando o problema estiver fora do dominio declarado.

## Referencia rapida

Entrada: objetivo, workload, evidencias e restricoes. Saida: decisao, riscos, validacao e proxima acao.

## Red flags

Vertices sem chave, edges sem direcao, consulta sem limite e ciclo infinito.

## Protocolo

não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.

A decisao sobe ao pai coordenador antes de qualquer escrita.

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.

## Nao faz

Voce não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.

## Manutencao destrutiva

A skill não executa a operacao; a decisao sobe ao pai coordenador antes de qualquer escrita.

não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.
Manutencao destrutiva: não executa; a decisao sobe ao pai antes de qualquer escrita.
## Quando NÃO usar

Nao use fora do escopo desta especializacao ou quando faltarem fatos e evidencias verificaveis.

## Referência rápida

Comece pelo diagnostico, consulte as fontes e regras aplicaveis, produza uma saida estruturada e valide o resultado antes do handoff.
