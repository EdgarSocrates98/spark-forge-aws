# Mapa de conceitos — o vocabulário do SparkForge e onde ele vive no código

Este documento existe para responder uma pergunta de quem chega: **quando alguém diz
"funil de contexto", "cascata de tiers" ou "cadeia de autorização" neste repositório, que
código é esse?**

Ele nasceu, na primeira fase do projeto, como uma tabela de intenções — conceitos que a arquitetura *iria*
adotar. Isso envelheceu mal: metade das linhas descrevia coisa que nunca foi construída, e
a outra metade descrevia com nome diferente coisa que existe. A auditoria de lastro cortou
o que não tinha artefato por trás, e o documento passou a ser o que devia ter sido desde o
começo: um índice de vocabulário, não uma promessa.

**Onde está a medição.** Este documento nomeia; ele não mede. Quem responde "isto existe,
está testado, e onde" são os mapas de lacuna, componente a componente:
[`../harness/CURRENT-HARNESS-GAP.md`](../harness/CURRENT-HARNESS-GAP.md) e
[`../harness/GLUE6-GAP.md`](../harness/GLUE6-GAP.md). Divergência entre este índice e
aqueles mapas resolve-se a favor deles.

---

## Vocabulário de execução

**Fact e Finding.** A separação de que todo o resto depende. Um `Fact` é observação
ancorada num artefato, com procedência, e **nunca** carrega juízo nem limiar. Um `Finding`
é juízo, e nunca existe sem evidência: `evidence` cita os `fact_id` que o sustentam.
Limiar mora na regra do catálogo, nunca no extrator. `sparkforge/findings/models.py`.

**Catálogo de regras.** Conhecimento em forma executável. Cada regra declara de que facts
precisa (`requires_facts`), em que faixa de versão vale (`runtime_scope`), o que propõe, o
que arrisca, como validar e como reverter — com fonte e data. `rules/catalog/`, lido por
`sparkforge/rules/engine.py`.

**Fail-closed por versão.** Regra fora da faixa não some em silêncio: é reportada como
pulada, com motivo. Silêncio, para quem lê um relatório, é indistinguível de "avaliei e
não achei" — e essa confusão é o defeito que o mecanismo existe para impedir.
`sparkforge/rules/version_scope.py`.

**Waves de execução.** Tarefas independentes em paralelo, dependentes em sequência,
derivadas de um grafo em vez de estágios numerados à mão.
`sparkforge/workflows/dag.py:ExecutionDAG.compute_waves()`.

**Cadeia de autorização.** Toda ferramenta declara a classe de mutação que pratica, e
mutação exige aprovação. Hoje isso é política declarada mais função pura de verificação; o
gate que de fato barra a execução ainda não existe, e o mapa de lacuna diz isso com
todas as letras. `sparkforge/registry/models.py`, `sparkforge/agents/autonomy.py`.

## Vocabulário de contexto e custo

**Funil de contexto.** Reduzir o repositório inteiro ao mínimo que sustenta a resposta,
descartando ruído e preservando evidência. `sparkforge/context/funnel.py`.

**Disclosure progressivo.** Carregar metadado primeiro, instrução depois, referência
completa só quando necessário. `sparkforge/context/progressive.py`.

**Cascata de tiers.** A ideia central da economia de token deste projeto: o primeiro tier
é determinístico e custa zero token, e só o que ele não resolve sobe para modelo — mais
barato antes, mais caro depois, multi-agente por último. `sparkforge/economy/`.

**Observabilidade local.** Tokens, custo estimado, latência, spans e chamadas de
ferramenta gravados localmente, sem depender de serviço pago. O que é medido e o que é
estimado ficam distinguíveis — número estimado apresentado como medido é a mesma classe de
mentira que um finding sem evidência. `sparkforge/observability/`.

**Paridade entre plataformas.** Uma fonte canônica compilada para cada plataforma-alvo, e
um gate que reprova quando os espelhos divergem da fonte. `sparkforge/adapters/`,
`parity.yaml`, `scripts/sync_skills.py`.

## Vocabulário de prova

**Golden case.** Entrada fixa, saída esperada versionada, comparação byte a byte.
`fixtures/`, um diretório por domínio, com o runner correspondente em `tests/`.

**Gate de lastro.** Toda alegação publicada em documento auditado precisa de prova
registrada — comando reexecutável, artefato com teste, fonte externa, ou medição passada
ancorada num commit. Alegação sem entrada reprova; entrada órfã também.
`scripts/check_vnext_claims.py`, manifesto em [`../claims.lock.json`](../claims.lock.json).

**Gates por tipo de mudança.** A lista de quais testes uma mudança toca, escrita porque
este repositório guarda invariantes em listas feitas à mão que nada mais cobra.
[`../gates-por-mudanca.md`](../gates-por-mudanca.md).
