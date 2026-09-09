# Stacktrace intelligence — o erro entra no motor

**Data:** 2026-09-08
**Estado:** desenho aprovado, implementação não iniciada
**Frente:** 1 de 7 da triagem de `prompt_especialization_spark_forge.md` §7

---

## 1. O que está errado hoje

O SparkForge lê código, plano físico, event log, IaC, catálogo, S3 e métrica.
**Não lê o erro.**

Medido em 2026-09-08:

- o único fact de falha em todo o motor é `spark.stage.failure`
  (`sparkforge/facts/event_log.py:704`), cujo `attrs.reason` é o campo
  `Failure Reason` do event log — que num job Spark **é** a exceção com a pilha,
  já redigida por `secrets.redact`;
- **nada estrutura esse texto.** Busca por
  `Py4JJavaError|NoSuchMethodError|ClassNotFoundException|AnalysisException|Traceback`
  em `sparkforge/facts/` devolve **uma linha, e é comentário**. O único
  consumidor de `attrs.reason` é `timeout_diagnosis.py`, que casa quatro
  categorias e ignora o resto;
- existe `sparkforge/errors/matcher.py::DeterministicErrorMatcher`, com CLI
  própria, **fora do motor**: não emite fact kind, não é tool MCP, não alimenta
  `judge`, não entra em `missing_evidence`, e nenhuma regra o consome;
- ele publica **`confidence=0.98` como constante literal**
  (`matcher.py:74`) — o que a regra 28 do `CLAUDE.md` fecha;
- ele casa **substring de texto** (`sig["signature"].lower() in log_lower`) e
  **ignora o `evidence_required`** que a própria assinatura declara;
- `knowledge/errors/` tem **6** assinaturas; a §7 do documento de origem enumera
  24.

O artefato não falta. O coletor não falta. Falta o erro **entrar no motor**.

### 1.1 A raiz: o matcher faz duas coisas

Ele constata que o texto casa com uma assinatura (**fato**) **e** diz o que
fazer — `likely_causes`, `fixes`, `unsafe_fixes` (**julgamento**). É por isso que
virou uma segunda máquina de julgar em paralelo à do repositório, e é por isso
que precisa de um `confidence`: um número que só existe porque ele finge julgar.

---

## 2. A separação em três camadas

**Decidido pelo operador:** as assinaturas **ficam onde estão**
(`knowledge/errors/`), e o matcher passa a ler fact.

### 2.1 Extrator de exceção — o fato

`sparkforge/facts/exception.py`, derivação pura no molde de `bridge.py` (que
também não lê artefato: deriva sobre a união dos facts).

Consome `spark.stage.failure.attrs.reason` e os facts do coletor da §2.4.
Emite:

```
spark.exception             exception_class, message_head, is_chained, caused_by[]
spark.exception.frame       class, method, file, line   (top-N frames)
spark.exception.unresolved  sem_forma_de_stacktrace | reason_redigida | classe_nao_reconhecida
```

`spark.exception` sai **sempre** que há `spark.stage.failure` — inclusive quando
o texto não tem forma de stacktrace. A recusa nomeada é o que distingue *"esta
falha não trouxe exceção"* de *"ninguém perguntou"*, no molde de
`spark.stage.callsite`.

### 2.2 O matcher vira extrator — o fato, não o juízo

Ele passa a consumir `spark.exception` (não texto cru) e emite **um fato**:

```
error.signature_match   signature_id, matched_on (exception_class | message_head | frame)
error.signature.unresolved   catalogo_vazio | nenhuma_assinatura_casou
```

**Some dele:** `likely_causes`, `diagnostic_steps`, `fixes`, `unsafe_fixes` e
`confidence`. Nada disso é fato. `confidence=0.98` morre sem discussão — fato não
tem confiança, tem procedência.

### 2.3 O julgamento vai para o catálogo — a regra

Regras `SF-ERR-*` em `rules/catalog/errors.yaml`, uma por assinatura, com
`requires_facts: [error.signature_match, <o que a assinatura declara>]`.

**O `evidence_required` que a assinatura já declara e o matcher hoje ignora
passa a ser verificado.** Hoje `ERR-GLUE-002` casa a palavra `NoSuchMethodError`
em qualquer log e afirma 98%. Depois, a regra só dispara com `mig.jar_binary` e
`tf.attribute` presentes — que é o que a própria assinatura diz precisar.

O mapeamento assinatura → regra é quase 1:1 e já existe no dado:

| assinatura | regra |
|---|---|
| `evidence_required` | `requires_facts` |
| `signature` | `when` sobre `error.signature_match` |
| `likely_causes` | `explanation` |
| `fixes` | `proposed_change` |
| `unsafe_fixes` | `risks` |
| `verification` | `validation` |
| `rollback` | `rollback` |
| `sources`, `last_verified` | `sources`, `retrieved` |
| `versions` | `runtime_scope` |

As regras novas ganham bloco `action:` como todas as outras (112 hoje).

### 2.4 Coletor de CloudWatch Logs

`sparkforge/collect/cloudwatch_logs.py` e tool
`sparkforge_collect_cloudwatch_logs`. Medido: `sparkforge/facts/cloudwatch.py`
lê **só métricas** (`CLOUDWATCH_METRICS`), nunca log group.

Traz o que o event log **não** carrega: falha de driver antes do primeiro stage,
`Py4JJavaError` de código Python, e OOM de container.

---

## 3. Redação e recusa

**Todo texto de log passa por `secrets.redact` antes de virar fact**, no mesmo
caminho de `spark.conf_effective` e do próprio `spark.stage.failure`. Log de
driver carrega credencial com a mesma facilidade que configuração, e
`facts.json` é commitado como barramento de handoff.

Três recusas, nomeadas e nunca silenciosas:

| Situação | Kind e razão |
|---|---|
| log group inexistente, sem permissão, ou vazio | `cloudwatch.logs.unresolved` com a razão |
| `reason` já redigida, sem forma de stacktrace | `spark.exception.unresolved: reason_redigida` |
| classe fora do vocabulário conhecido | `spark.exception.unresolved: classe_nao_reconhecida`, com o topo preservado |

A redação vem **antes** do parse, e o parse não a desfaz. Um texto redigido não
vira exceção estruturada — vira recusa nomeada.

---

## 4. O que fica de fora

- **Não migrar as assinaturas para o catálogo como dado.** Elas ficam em
  `knowledge/errors/`; o catálogo ganha as regras que as consomem.
- **Nenhuma inferência de causa sem assinatura.** Exceção que não casa com
  assinatura nenhuma produz `spark.exception` e `error.signature.unresolved` —
  nunca um palpite.
- **Nenhum score.** Nem `confidence`, nem severidade derivada de frequência.
- **Não ampliar de 6 para 24 assinaturas nesta frente.** Escrever assinatura é
  pesquisa de fonte, com `sources` e `last_verified` cobrados por teste. A frente
  entrega o **mecanismo**; as assinaturas novas são entrega própria, e o número
  de hoje sai publicado como o que é.

---

## 5. Gates que a entrega move

- extrator novo entra nas **duas listas manuais** de teste e na medida de snippet;
- kinds novos em `EMITTED_KINDS`, e o total de fact kinds sobe (187 hoje);
- tool nova move `docs/surface.lock.json`: **69 → 70**, com o crescimento
  declarado no commit (regra 26);
- área de regra nova exige **rota em `rules/catalog/routing.yaml`** e coordenador
  que a declare;
- fonte citada por regra nova entra em `knowledge/sources.lock.json` via
  `python scripts/refresh_knowledge.py --offline --update`;
- `check_vnext_claims.py` cai a cada `.py` novo — remediar **relendo pela própria
  prova**.

---

## 6. Testes

- `spark.exception` sobre fixture com `Failure Reason` real: classe, cabeça da
  mensagem e frames;
- exceção **encadeada** (`Caused by:`) produz `caused_by[]` na ordem certa;
- texto sem forma de stacktrace → `unresolved` com a razão, e **não** exceção
  inventada;
- texto redigido → `reason_redigida`, e o parse não tenta desfazer;
- o matcher emite **fato** e não carrega `confidence`, `fixes` nem
  `likely_causes` — varredura de campo;
- regra `SF-ERR-*` **não dispara** sem os facts que a assinatura declara em
  `evidence_required` — é o teste que prova que a integração vale;
- par positivo/negativo por assinatura migrada, no molde do corpus.
