---
name: sdd-explore
description: "Use quando uma ideia ainda sem forma vai virar mudança no SparkForge ou num job Glue/PySpark do operador — \\\"quero fazer X\\\", \\\"uso A ou B?\\\", \\\"como você atacaria isso?\\\" — e ainda não há define, design nem código. Requisito já claro vai direto para sdd-define."
metadata:
  sparkforge_aws_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - references/decision-tree.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../docs/sdd/README.md
  - ../../docs/sdd/CONTRATO.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge-aws sdd check
  - sparkforge-aws sdd status
  - sparkforge-aws code search
---

# SDD Explore

Fase 0 do SDD próprio. Transforma um pedido vago numa abordagem escolhida, com
as rejeitadas registradas ao lado. O `sparkforge-aws sdd check` confere a forma do
artefato; quem decide é o operador.

**Portão duro:** nada de código, nada de arquivo fora de `docs/sdd/<FEATURE>/`
e nenhuma skill de implementação antes de o operador aprovar uma abordagem.
"É simples demais para explorar" é exatamente onde a suposição não examinada
custa mais caro — mas o explore é opcional: se o pedido já está claro, pule para
`sdd-define`.

## Antes de começar

1. **Contexto do repositório.** `sparkforge-aws sdd status --repo .` mostra as
   features que já existem; talvez a ideia seja a continuação de uma delas.
   `sparkforge-aws code search <termo>` diz o que o código já tem. Leia os commits
   recentes.
2. **Perfil, primeira pergunta.** "A mudança é no SparkForge (`dev`) ou num job
   seu (`operator`)?" O perfil muda o resto do ciclo: no `operator`, o build
   passa sempre por `sparkforge-aws change sandbox`, e a sessão nunca escreve na
   árvore do operador.
3. **Escopo.** Pedido com vários subsistemas independentes é decomposto antes:
   cada pedaço vira uma feature com pasta própria e ciclo próprio. Explore o
   primeiro.
4. **Nome da feature.** `MAIÚSCULAS_COM_SUBLINHADO`, e fora da lista de pulos da
   varredura (`BUILD`, `DIST`, `VENDOR`, `SECRETS`...). Um nome podado vira
   lacuna `path_skipped` no check.

## O laço

A conversa roda sobre uma **árvore de decisões** gravada em
`docs/sdd/<FEATURE>/decisions.json` (contrato em
`references/decision-tree.md`). O gate só lê `explore.md`; a árvore é o
registro da entrevista — o que permite retomar, auditar e responder "por que
isto" sem depender do histórico da sessão.

1. **Monte a árvore antes de perguntar.** Liste o que o pedido deixa em
   aberto. Cada item vira `type: fact` — respondido por verbo, medida ou
   leitura (`code search`, `runtime detect`, o case), nunca por pergunta — ou
   `type: decision`, que só o operador decide. Decisão que depende de fato
   ganha `depends_on` apontando para ele: o fato é investigado antes, e a
   pergunta chega ao operador já com a resposta dele.
2. **Escolha o modo** e grave no topo da árvore:
   - `sequencial` — **uma pergunta por mensagem**, o default. Continua sempre
     disponível, em qualquer modo, quando uma decisão pede foco.
   - `rodada` — um bloco de perguntas por mensagem, agrupadas por tema; só
     entre decisões sem `depends_on` entre si.
   - `adaptativo` — a ordem muda a cada resposta ou evidência nova: a árvore
     diz quais decisões continuam `pending`, quais abriram e quais caíram.
   - `fronteiras` — agrupa por fronteira (módulo, conta, runtime) **somente
     decisões independentes** que a política da entrevista autorizar;
     decisão dependente sai do grupo e volta ao sequencial.
3. **Fato vem de verbo, não de memória** (regra em
   `docs/sdd/README.md#conhecimento-citado-nunca-memória`). Regra do catálogo
   por área: `sparkforge-aws rules lookup --category <área>`. Resposta de fato
   entra em `evidence`, não em `answer`.
4. **Recomendação por decisão.** Cada `alternatives[]` tem a recomendada
   marcada e a `rationale`; a recomendação é sua, o `answer` é do operador —
   ele pode recusar, e a árvore registra a recusa, não a "correção" dele.
5. **Contradição e reversibilidade.** Resposta que contradiz uma decisão
   `status: answered` marca as duas e sobe ao operador na hora — contradição
   não se acumula para o define. Decisão cara de reverter ganha `impact`
   com o custo e `reopen_condition` dizendo o que permite reabri-la sem
   recomeçar a entrevista; mudança no meio usa a condição, nunca edição muda.
6. **Duas ou três abordagens**, cada uma com trade-offs, a recomendada primeiro
   e o porquê. Corte o que ninguém pediu (YAGNI).
7. **O operador escolhe.** Apresente, pergunte, espere. Se ele recusar todas,
   volte ao passo 1.
8. **Confirmação final.** Antes de fechar, releia a árvore com o operador:
   toda decisão com `answer`, toda contradição resolvida, a abordagem
   escolhida e as rejeitadas. A confirmação é um portão — sem ela, o
   `explore.md` continua `draft`.
9. **Grave** `docs/sdd/<FEATURE>/explore.md` a partir de
   `docs/sdd/templates/explore.md`, com `status: draft` enquanto a conversa não
   fecha. As perguntas e respostas vivem no corpo e na árvore; o histórico da
   entrevista não mora só na sessão.
10. **Confira** com `sparkforge-aws sdd check --repo . --feature <FEATURE>`, pelo
    laço de `docs/sdd/README.md#o-laço-de-cada-fase`. O explore é a primeira
    fase e não leva `upstream`, então não há stamp aqui.
11. **Próximo passo:** `sdd-define`. Com `explore.md` presente, o define passa a
    declarar `upstream` apontando para ele, e pode citar as decisões da
    árvore pelo `id`.

## Retomada

Sessão nova continua de `decisions.json`: decisões `answered` ficam como
estão (reabrir só por `reopen_condition`), `pending` e `blocked` voltam à
fila do modo escolhido. Árvore ausente numa feature em andamento é sinal de
entrevista que viveu só na sessão — reconstrua com o operador antes de
seguir, ou declare o risco.

## O que o artefato guarda

- `approaches`: `id`, `summary` e `tradeoffs` de cada abordagem considerada,
  inclusive as rejeitadas.
- `chosen`: o `id` que o operador aprovou — igual a um dos `approaches[].id`,
  letra por letra.
- O corpo: as perguntas feitas, as respostas, e por que a escolhida venceu.
- `decisions.json` ao lado: a árvore inteira da entrevista — decisões,
  dependências, evidências, respostas, contradições e reaberturas.

Nenhuma nota de clareza, nenhum "confiança 0,9". Número que o próprio agente
atribui é T5 na escala de autoridade e não sustenta decisão sozinho.

## Perfil operator

- O case é a fonte dos fatos do job: `sparkforge-aws case get --repo .` quando ele já
  existe. O explore não coleta artefato; se falta medida, a abordagem diz qual
  coleta a destrava.
- Glue, Spark, Python e Iceberg: a versão vem do case ou de
  `sparkforge-aws runtime detect`, nunca de suposição. A mesma configuração muda de
  significado entre versões.
- Priorize abordagens que reduzem trabalho e movimentação de dados antes das que
  aumentam workers.
- Valor de configuração não se escolhe aqui: é `sparkforge-aws tune` que o deriva da
  medida, mais adiante.

## Quando NÃO usar

- Requisito já claro e validado, ou `explore.md` já existe: vá para `sdd-define`.
- Para achar a causa de um job lento ou que falha: isso é diagnóstico
  (`sparkforge-aws-diagnose`, `sparkforge-aws next-step`). O explore decide o que mudar
  depois que a causa é conhecida.
- Para escolher o valor de uma configuração: `sparkforge-aws tune`.
- Para afirmar que uma abordagem é mais rápida ou mais barata sem medida.

## Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| features existentes | `sparkforge-aws sdd status --repo .` | `sparkforge_aws_sdd_status` |
| o que o código já tem | `sparkforge-aws code search <termo>` | `sparkforge_aws_code_search` |
| quem chama um símbolo | `sparkforge-aws code symbol <node_id>` | `sparkforge_aws_code_symbol` |
| regra do catálogo | `sparkforge-aws rules lookup --category <área>` | `sparkforge_aws_rules_lookup` |
| documento de conhecimento | `sparkforge-aws knowledge path --file <arquivo>` | `sparkforge_aws_knowledge_path` |
| inventário do conhecimento | `sparkforge-aws knowledge list` | `sparkforge_aws_knowledge_list` |
| busca no conhecimento | `sparkforge-aws knowledge search <termo>` | `sparkforge_aws_knowledge_search` |
| case do operador | `sparkforge-aws case get --repo .` | `sparkforge_aws_case_get` |
| conferir a fase | `sparkforge-aws sdd check --repo . --feature <F>` | `sparkforge_aws_sdd_check` |

Template: `docs/sdd/templates/explore.md`. Contrato: `sparkforge_aws/sdd/schema/explore.json`.
Visão geral do ciclo: `docs/sdd/README.md`.

## Red flags

- Pergunta sobre fato que um verbo responde — `type: fact` não vira pergunta.
- Decisões dependentes agrupadas no modo `rodada` ou `fronteiras`.
- `answer` editado em silêncio, sem `reopen_condition` e sem avisar que reabriu.
- Contradição entre respostas empurrada para o define em vez de resolvida aqui.
- Recomendação apresentada como resposta: `answer` é do operador, sempre.
- Retomada que ignora o `decisions.json` e refaz perguntas já respondidas.
- Fechamento sem a confirmação final sobre a árvore inteira.
- Duas ou mais perguntas na mesma mensagem fora do modo que as agrupa.
- Uma abordagem só, ou três que são a mesma com nomes diferentes.
- Código, arquivo fora de `docs/sdd/<FEATURE>/` ou skill de implementação antes
  da aprovação.
- A sessão escolhendo a abordagem no lugar do operador.
- Nota de clareza ou de confiança escrita no artefato.
- Versão de Glue ou Spark suposta em vez de lida.
- "Fica mais rápido" sem medida que o sustente.


## Contrato de qualidade SparkForge (v1)

Esta skill trata **exploração de alternativas e escolha explícita**. Contrato comum, sem substituir o procedimento específico acima:

- **Entrada mínima:** artefato, runtime/contexto declarado e pergunta operacional; se faltar, registre o `*.unresolved` correspondente.
- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou origem de medição; aplique regra por `rule_id` e versão, nunca por memória.
- **Verbos primários:** `sparkforge-aws sdd check`, `sparkforge-aws sdd status`, `sparkforge-aws code search`. Use-os na ordem indicada pela skill e conserve saída estruturada.
- **Saída:** fatos, findings, hipóteses e recomendações separados. Recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`, `proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e `rollback`.
- **Validação:** rode o teste/verbos listados, valide dados depois da mudança e diga o que ainda não foi medido. Ausência de finding significa apenas que nenhum proxy disparou.
- **Rollback e segurança:** não execute escrita destrutiva por inferência; peça escopo explícito e entregue rollback reversível. AWS operacional mantém `denied_by`, conta, recurso e camada de policy.
- **Referências e eval:** `../_shared/references/evidence-first.md`, `../_shared/references/evaluation-contract.md`, `../_shared/references/operational-safety.md`, `../../docs/sdd/README.md`, `../../docs/sdd/CONTRATO.md`; casos realistas em `evals/evals.json`; o script `scripts/validate_evidence.py` verifica o envelope antes do handoff.
