# Revisão de desenho — os blocos além do manifesto

Referência da skill `sdd-design`. O schema do `design.md` cobre `files`,
`decisions` e `covers`; estes blocos moram **no corpo** e entram quando o
risco da mudança os justifica — não é burocracia por feature, é profundidade
proporcional. Nenhum bloco substitui os campos do schema: o `D<n>` continua
obrigatório com `rejected` e `rollback`.

## Quando cada bloco é obrigatório

| bloco | dispara quando |
|---|---|
| ADR | a decisão é cara de reverter, cruza fronteira de sistema, ou muda contrato público/formato persistido |
| threat model | toca entrada não confiada, segredo, IAM, cross-account, Lake Formation ou caminho de exfiltração |
| contrato de integração | outro sistema/job lê o que a mudança publica (tabela, arquivo, tópico, API) |
| data model | a mudança cria ou altera entidade persistida |
| research | o desenho depende de comportamento que precisou ser verificado (spike, doc, fact) |
| quickstart | sempre — como o revisor confere o desenho em minutos |
| impact/compatibility | sempre que `modify`/`delete` aparece no manifesto; reforçado quando runtimes divergem |
| durabilidade de escrita | qualquer persistência ou atualização de dado |

## ADR — a forma curta

```
### ADR D<n> — título
Contexto: o que força decidir agora.
Decisão: o choice do schema.
Alternativas: as rejected[], com o motivo real de cada queda.
Consequências: o que fica fácil, o que fica caro, o que fecha porta.
Rollback: o do schema — e o que ele não cobre.
```

Decisão que não justifica ADR fica no `D<n>` do schema. ADR sem alternativa
rejeitada real é prosa, não decisão.

## Threat model — as cinco perguntas

1. O que entra sem confiança (arquivo, partição, payload, SQL)?
2. O que vale proteger (segredo, dado, permissão, metadado de governança)?
3. Que caminho tira valor do cofre (exfiltração por log, por saída, por
   grant excessivo)?
4. Que identidade executa (role do job, quem chama Step Functions,
   cross-account)?
5. O que a negação mostra — `denied_by`, conta, recurso, camada de policy?

Resposta sem evidência (o `.tf`, o `iam-access` simulado, a policy lida)
é threat model de corredor.

## Contrato de integração e data model

Para cada consumidor: formato de entrada/saída, campos com tipo,
comportamento de erro, e versão do contrato. Mudança de contrato sem
versão é incompatibilidade adiada. Data model declara entidade, chave de
negócio (a do `funcval plan` quando houver), dono e retenção.

## Compatibilidade entre runtimes

Afirmação de comportamento só com a versão em que foi verificada — **um
runtime não vale pelo outro**:

- Glue 4.x/5.x (e versões futuras verificadas) ≠ EMR ≠ Databricks: o mesmo
  `spark.sql` muda de significado.
- Athena engine e Athena UNLOAD: sintaxe e limite por versão de engine.
- Iceberg/Delta/Parquet: atomicidade, schema evolution e concorrência são
  do formato **e** do runtime que o escreve — Iceberg no Glue não é
  Iceberg no EMR por decreto.
- Streaming: checkpoint, trigger e estado por engine — o que vale em
  Structured Streaming não decorre para Glue Streaming sem verificação.

Fonte: `sparkforge-aws rules lookup --id <SF-...>`, `knowledge path --file <doc>`
com a versão alvo, `runtime detect` quando o caso permite. Sem fonte, a
afirmação é `unresolved` do desenho.

## Durabilidade de escrita

Para persistência/atualização de dado, responda por escrito:

| pergunta | o que o desenho mostra |
|---|---|
| atomicidade | uma operação falha no meio — o que fica visível? |
| isolamento | leitor concorrente vê o quê, de qual snapshot? |
| consistência | o invariante de negócio preservado entre etapas? |
| idempotência | reexecutar a escrita duplica ou repara? |
| concorrência | dois writers, commit conflicts, quem perde? |
| versionamento | schema evolution aditiva vs. destrutiva, e quem lê versão velha |
| chave de negócio | o que identifica a linha — e o que acontece em reprocessamento |
| recovery | retry, reprocessamento, dados parcialmente atualizados |
| limites de transação | onde começa e onde termina o commit; o que fica fora |

Snapshot isolado não resolve falha de múltiplas operações: o desenho diz
como o invariante sobrevive quando a operação 2 de 3 falha, e qual teste
negativo prova.

## Foco AWS — o checklist por serviço

Glue e Glue jobs (worker, bookmark, retry), Glue Catalog (tabela, partição,
schema evolution), Athena e UNLOAD (engine, formato, consistência da
escrita), Lake Formation (grant, FGAC), cross-account (role, recurso,
policy), IAM (menor privilégio, camada de negação), S3 (layout, lifecycle),
EMR (runtime, fleet), Step Functions (retry, estado), Iceberg/Delta/Parquet
(commit, vacuum/expiration, concurrency control), Spark SQL e Spark jobs
(semântica por versão), Terraform (drift, estado) e Streaming (checkpoint,
backpressure). Para cada um em jogo: o que muda, a versão, e a fonte.
