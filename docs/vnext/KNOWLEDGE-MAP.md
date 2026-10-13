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
Limiar mora na regra do catálogo, nunca no extrator. `sparkforge_aws/findings/models.py`.

**Catálogo de regras.** Conhecimento em forma executável. Cada regra declara de que facts
precisa (`requires_facts`), em que faixa de versão vale (`runtime_scope`), o que propõe, o
que arrisca, como validar e como reverter — com fonte e data. `rules/catalog/`, lido por
`sparkforge_aws/rules/engine.py`.

**Fail-closed por versão.** Regra fora da faixa não some em silêncio: é reportada como
pulada, com motivo. Silêncio, para quem lê um relatório, é indistinguível de "avaliei e
não achei" — e essa confusão é o defeito que o mecanismo existe para impedir.
`sparkforge_aws/rules/version_scope.py`.

**Waves de execução.** Tarefas independentes em paralelo, dependentes em sequência,
derivadas de um grafo em vez de estágios numerados à mão.
`sparkforge_aws/workflows/dag.py:ExecutionDAG.compute_waves()`.

**Cadeia de autorização.** Toda ferramenta declara a classe de mutação que pratica, e
mutação pode exigir aprovação. `CallPolicy` decide allowlist, denylist, perfil, raiz e
aprovações; `sparkforge_aws.adapters.tools.call_tool(..., policy=...)` aplica a decisão e
devolve recusa estruturada. A política é opcional por compatibilidade: sem policy
declarada não existe bloqueio universal. `sparkforge_aws/registry/models.py`,
`sparkforge_aws/agents/autonomy.py`, `sparkforge_aws/policy/`.

**Arquitetura Lake Formation.** Contrato determinístico que separa engine/runtime,
FGAC/FTA, formato, operação, ownership dos catálogos, cross-account e credential
vending. A matriz versionada está em
`knowledge/lakeformation/capability-matrix.yaml`; o motor está em
`sparkforge_aws/lakeformation/architecture.py` e a rota de contas em
`sparkforge_aws/lakeformation/catalog_routing.py`. A saída distingue `consistent`,
`unresolved` e `blocked`, preservando `required_verification`.

O fechamento operacional está em `knowledge/lakeformation/operational-closure.md`
e no guia `docs/guia/usos/lake-formation-operacional.md`: explain-access,
autorização em camadas, root-cause, migration report e runbooks são carregados
por progressive disclosure a partir das dimensões declaradas.

## Vocabulário de contexto e custo

**Funil de contexto.** Reduzir o repositório inteiro ao mínimo que sustenta a resposta,
descartando ruído e preservando evidência. `sparkforge_aws/context/funnel.py`.

**Disclosure progressivo.** Carregar metadado primeiro, instrução depois, referência
completa só quando necessário. `sparkforge_aws/context/progressive.py`.

**Cascata de tiers.** A ideia central da economia de token deste projeto: o primeiro tier
é determinístico e custa zero token, e só o que ele não resolve sobe para modelo — mais
barato antes, mais caro depois, multi-agente por último. `sparkforge_aws/economy/`.

**Observabilidade local.** Tokens, custo estimado, latência, spans e chamadas de
ferramenta gravados localmente, sem depender de serviço pago. O que é medido e o que é
estimado ficam distinguíveis — número estimado apresentado como medido é a mesma classe de
mentira que um finding sem evidência. `sparkforge_aws/observability/`.

**Agentic OS v2.** Contratos locais que conectam memória, trust, contexto, economia,
checkpoint, Forge e AgentOps sem substituir o núcleo determinístico. As fontes principais
são `sparkforge_aws/agentic/`, `sparkforge_aws/context/quality.py`,
`sparkforge_aws/economy/ledger.py`, `sparkforge_aws/agentic/checkpoint.py`,
`sparkforge_aws/protocols/forge.py` e `sparkforge_aws/observability/agentops.py`.

**Trust, taint e autoridade.** Proveniência e confiança não autorizam instrução.
Dados externos e handoffs recebem `DATA_ONLY`; uma rota `active` exige autoridade,
evidência de promoção e rollback. `sparkforge_aws/agentic/trust.py` e
`sparkforge_aws/economy/model_router.py`.

**Unresolved.** Estado explícito para aquilo que o artefato, transcript, preço ou
benchmark não permite afirmar. Não é sinônimo de falso nem de ausência comprovada.

**Paridade entre plataformas.** Uma fonte canônica compilada para cada plataforma-alvo, e
um gate que reprova quando os espelhos divergem da fonte. `sparkforge_aws/adapters/`,
`parity.yaml`, `scripts/sync_skills.py`.

Lake Formation acceptance and observability are version-aware: the decision
graph selects only declared dimensions, while CloudTrail consumer/producer legs,
Glue/Spark logs, Lake Formation audit and RAM state remain independent evidence
sources. See `docs/sdd/LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION/`.
The final prompt-gap audit also proves EMR Serverless/resource-link, Hybrid
cross-account, LF-TBAC/RAM and newer-version routing cases without loading
Glue-only knowledge into EMR decisions.

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
As melhorias de FGAC/FTA estão em `knowledge/lakeformation/fgac-fta-improvements.md`:
enforcement por capability, decisões source/target, resolução cross-account,
Hybrid Access e comparação semântica de `glue.id`/`glue.account-id`. O runtime
corrente legado só entra em migration report quando há destino ou intent
declarado.
