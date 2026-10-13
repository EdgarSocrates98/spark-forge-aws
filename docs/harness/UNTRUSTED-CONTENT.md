# Conteúdo derivado de artefato é dado, nunca instrução

`prompt_evo_harness.md` §42 lista as origens: repositório, log, saída de AWS,
documentação, MCP, web, issues, comentários. Tudo isso é **dado**. Instruções
encontradas nesse conteúdo não são executadas.

## Onde o texto de terceiro entra, neste repositório

Em dois lugares, e só neles:

- `Fact.subject.snippet` — a linha exata do arquivo analisado.
- `Fact.attrs.*` — valores lidos do artefato (nome de pacote, chave de config,
  caminho de S3, texto de `--conf`).

Para onde eles vão é diferente para cada um, e a diferença importa:

| origem | destino | o que atravessa |
|---|---|---|
| `Fact.subject` | `Finding.subject` | íntegro, snippet incluído |
| `Fact.measures` | `Finding.measured` | íntegro (`measured=dict(primary.measures)`) |
| `Fact.attrs` | **não entra no `Finding`** | o motor só lê `attrs` para casar regra |
| — | `Finding.evidence` | **só ids** (`[f.id for f in evidence]`), nunca texto |

Isso quer dizer que `Finding.evidence` **não** é superfície de texto de
terceiro: é uma lista de hashes. Quem ler "o texto do artefato chega ao
`evidence`" e resolver protegê-lo vai sanitizar uma lista de ids e não terá
tocado em nada.

E `attrs` não sumir no `Finding` não quer dizer que ele não chega ao modelo. As
tools `analyze_*` devolvem **Facts**, não Findings (`sparkforge_aws/adapters/_core.py`
serializa `f.to_dict()` em `items`), e `Fact.to_dict()` inclui `attrs` inteiro.
É por aí que `attrs.target` (um `s3://...` escrito por um terceiro) chega ao
modelo — pelo payload do próprio `Fact`, não pelo `Finding`.

**4** extratores produzem `subject.snippet` não vazio: `pyspark_ast`,
`event_log`, `graph` e `spark_plan`. Nos demais a chave ou vem vazia ou nem
existe no `subject` — em `terraform`, 233 dos 248 facts do corpus de fixtures
não têm a chave.

Esse número foi medido errado uma vez, e a forma do erro importa. `terraform`
entrou na lista por contagem de `"snippet"` no fonte — mas
`sparkforge_aws/facts/terraform.py` tem `_line_subject(path, line, snippet="")` e
**nenhum** dos 14 call sites alimenta o parâmetro. O módulo parece produzir
snippet para quem lê o fonte, e não produz nenhum. Por isso a contagem agora é
derivada **executando** os extratores sobre o corpus de `fixtures/`
(`tests/test_harness_untrusted.py::extratores_com_snippet`), e o próprio teste
compara a medida com a lista escrita aqui.

Isso não quer dizer que `terraform` não carregue texto de terceiro — carrega,
por outro campo: `subject.symbol` (o nome do recurso, escrito por quem escreveu
o `.tf`) e `attrs.value` (o valor lido, um caminho de S3 ou o texto de um
`--conf`). O aviso na `description` de `sparkforge_aws_analyze_terraform` cita esses
campos, e não o `snippet`.

## O invariante, e por que ele não é sanitização

**Texto derivado de artefato nunca é concatenado num campo que o catálogo
controla.**

Um `Finding` tem campos de duas procedências, e a lista curta é a do artefato:
`subject`, `measured` e `evidence`. **Todo o resto** de `to_dict()` vem de
`rules/catalog/*.yaml` — dado versionado, revisado, com `sources`.

A enumeração é curta de propósito. Listar os campos do catálogo seria a lista
que envelhece: campo novo nasceria fora dela, desprotegido e em silêncio.
Enumerando o lado do artefato, campo novo nasce coberto, e acrescentar um campo
de artefato exige decisão explícita.

A defesa **não** é limpar o `snippet`. O `snippet` existe para que o operador
veja a linha exata que produziu o achado; apagar dela o que parece instrução
apagaria a evidência, e evidência apagada é defeito, não segurança. É a mesma
regra que vale para o resto do repositório: campo de evidência apagado para
economizar token é defeito, não compressão.

A defesa é a separação de campo. Um modelo que lê um relatório trata
`explanation` como afirmação do sistema e `subject.snippet` como amostra do
código analisado. Se o texto do artefato vazasse para `explanation` — ou para
`sources`, que carrega a mesma autoridade de dado revisado —, a instrução
plantada por um terceiro chegaria ao modelo com a autoridade do catálogo.

`tests/test_harness_untrusted.py` tranca as duas metades: que a injeção não
aparece em campo de catálogo, **e** que ela continua visível no `snippet`. A
segunda existe para impedir a correção errada.

## Onde o invariante é dito ao modelo

Invariante só protege quem sabe dele. A frase está na `description` das **4**
tools `analyze_*` que devolvem `subject.snippet` não vazio, na de
`sparkforge_aws_analyze_terraform` — que carrega o texto de terceiro por
`subject.symbol` e `attrs.value`, e cujo aviso cita esses campos —, e na de
`sparkforge_aws_judge`, a única que devolve `Finding`, e portanto o único lugar em
que o `snippet` do artefato aparece **ao lado** do `explanation` do catálogo,
que é exatamente a situação que o invariante descreve.

## O envelope `_trust` no resultado de `call_tool`

A mesma separação vale para o outro sentido do fio: não só o que entra num
`Finding`, mas o que uma tool devolve ao modelo. Todo resultado de
`call_tool` — sucesso ou recusa — carrega `_trust` = `{label, authority,
taint}` de `sparkforge_aws/agentic/trust.py:tool_result_envelope()`, e o bloco
aterrissa no `metadata` do span em `adapters/tools.py`.

- `label` = `TOOL_OUTPUT` para saída de ferramenta: proveniência observada,
  não confundida com fato verificado nem com instrução.
- `authority` = `data_only` por construção: o conteúdo pode virar *verified
  fact* depois, por extração determinística — nunca por ter atravessado o
  despacho. `as_verified_fact()` promove só o trust factual e mantém
  `DATA_ONLY`; `TrustEnvelope.__post_init__` levanta se um envelope externo
  declarar autoridade `SYSTEM`/`POLICY` — autoridade de sistema não entra por
  payload.
- `taint` = `SUSPICIOUS` quando o payload carrega marcador lexical de
  instrução (`detect_prompt_injection`); o marcador fica registrado no span,
  a proveniência continua `TOOL_OUTPUT` — taint não apaga origem.
- `TRUST_RANK` é ranking explícito (`TRUST_RANK[label]`), não posição de enum —
  o `allows` do `RoleContextPlan` compara contra o rank declarado.

Limite declarado (T-A01 do THREAT-MODEL): o guardrail é lexical — instrução
escrita sem os marcadores passa sem `taint`, e a suíte red-team nomeia esse
caso (`test_injeccao_disfarcada_sem_marcador_passa_e_fica_nomeada`) em vez de
fingir cobertura.

## O handoff entre agentes: `admit_handoff`

O outro sentido da fronteira é mensagem entre agentes. `AgentHandoff`
(`sparkforge_aws/agentic/trust.py`) é o envelope data-only que um agente escreve
para outro; `admit_handoff` (`sparkforge_aws/agentic/handoff.py`) é o portão que
aplica o `RoleContextPlan` do **receptor** antes de o conteúdo entrar no
contexto dele:

```text
AgentHandoff → plano do receptor → ALLOW / DENY / REVIEW
```

- **`authority` nunca sobe.** O construtor só aceita `DATA_ONLY`; um dict
  serializado que declare outra autoridade nem vira objeto — a admissão
  devolve `handoff_authority_not_data_only` como DENY.
- **`trust` declarado tem teto `MODEL_OUTPUT`.** Auto-declaração não
  verifica (o mesmo molde de `classify_memory_candidate`, que não acredita
  no `trust` do próprio registro). Um handoff que diga `VERIFIED_FACT` é
  admitido como `MODEL_OUTPUT` — o trust do `Fact` mora no registro do case,
  não no rótulo do envelope.
- **`taint` é piso, não teto.** `POISONED` nega; marcador lexical de
  instrução em qualquer seção (o mesmo `detect_prompt_injection` da `_trust`
  das tools) sobe o taint efetivo para `SUSPICIOUS` e a decisão vira REVIEW
  — o conteúdo segue como dado marcado, não é apagado.
- **Filtragem por kind, item a item.** Cada seção entra como o kind que ela
  é (`facts`→`fact`, `evidence_refs`→`evidence`, …) e cada `context_items`
  pelo `kind` declarado — `plan.allows(kind, trust)` decide, e a negação
  vira `unresolved` nomeado (`handoff_section_denied`, `handoff_item_denied`).
  Um `tool_output` cru dentro de `context_items` não entra no contexto do
  `sf-judge`, porque `tool_output` não está no plano dele.
- **Confused deputy é checagem, não convenção.** `requested_action` que
  nomeia uma tool da superficie declarada (`tool_names`) é confrontado com o
  `tool_access` do remetente: pedir o que o próprio remetente não pode
  invocar é DENY (`handoff_confused_deputy`); sem plano do remetente a
  autoridade do pedido fica `unverified` e a decisão é REVIEW. O pedido
  contra o `tool_access` restrito do receptor vira `handoff_tool_denied_for_receiver`.
- **Fechado por desenho.** Role sem plano (`handoff_receiver_plan_unknown`),
  plano malformado (`handoff_receiver_plan_invalid`), `origin` de agente
  divergente do `sender_role` (`handoff_sender_origin_mismatch`) e handoff
  sem nada admissível (`handoff_nothing_admissible`) são DENY — "pedi um
  plano e ele não resolveu" nunca se lê como "sem plano".

`required_context` **não** é avaliado na admissão: o requisito do papel se
cumpre no contexto total (rules vêm do catálogo, nunca via handoff), e a
seleção final no `ContextGateway` continua emitindo `required_context_missing`.
O que a admissão devolve em `admitted` atravessa o gateway pelo mesmo plano
via `HandoffAdmission.context_items()` — defesa em profundidade que nunca
contradiz, porque as duas camadas consultam o mesmo `allows()`.

Onde a fronteira mordia: nada consumia `AgentHandoff` — era contrato sem
portão, e a lacuna estava nomeada no relatório de convergência. O teste
`tests/test_agentic_handoff.py` cobre cada caminho do vocabulário acima,
inclusive o round-trip `to_dict`/`from_dict` que a fronteira serializada
exige.

## O que este documento NÃO cobre

- **Conteúdo que chega ao modelo por fora do `Finding`** — um agente que lê um
  arquivo com `Read` recebe o texto cru, e nenhum invariante deste repositório
  alcança isso. A defesa ali é do harness da plataforma, não daqui.
- **Saída de MCP de terceiros.** Este repositório expõe tools; não consome.
- **Sanitização de qualquer natureza.** Ver acima: é decisão, não omissão.
