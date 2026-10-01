# O plano de aplicação chega ao operador — `judge` calcula, `arbitrate` grava

**Data:** 2026-09-08
**Estado:** desenho aprovado, implementação não iniciada
**Depende de:** `docs/superpowers/specs/2026-09-08-sparkforge-executor-agentico-design.md`
(o executor determinístico, PR #42)
**Fecha:** o executor produz ordem, lastro e lacunas, e nada disso chega a quem
lê o resultado

---

## 1. Contexto

O executor determinístico entregue no PR #42 produz, sobre um case julgado:
ordem de aplicação (17 arestas `depends_on` reais no catálogo, a maioria citada
literalmente no texto das regras), restrições de sequenciamento (10 grupos de
eixo de medida compartilhado), lastro por achado (sobre o corpus: 89 `high`, 50
`low`, 18 `medium`), contradições e lacunas nomeadas.

**Nada disso chega ao operador.** O único caminho é `sparkforge arbitrate`, que
exige montar dois arquivos JSON à mão — e a união dos facts, que é o insumo
correto, foi justamente o que a implementação do executor errou primeiro
(§12.9 do spec anterior). O pipeline que o agente percorre continua sendo
`analyze → judge → findings → next_step`, e o executor está fora dele.

É a mesma família da lacuna que o PR #42 fechou, um nível acima: antes era
**biblioteca sem produtor**; agora é **produtor sem consumidor**.

### 1.1 O que foi medido antes de desenhar

- `judge_findings` **já recebe os facts** (inline ou por `facts_path`, com
  `_merge_facts_files` montando a união) **e produz os findings** — os dois
  insumos do executor, no mesmo lugar, no verbo que o agente já chama.
- `judge_findings` **pagina**: a resposta tem `items`, `total_count`,
  `returned_count` e `next_cursor`. A ordem de aplicação é propriedade do
  **conjunto**, não da página.
- `sparkforge_judge` **não declara `detail_level`** — não há nível de resumo com
  que o bloco novo possa conflitar.
- `next_step` recebe `case` e `finding_ids`, **sem facts**. Ele resolve rota
  sobre `routing.yaml` e não tem como chamar o executor sozinho.
- **Oito arquivos de teste** leem a resposta de `judge`.

---

## 2. As três decisões que governam o desenho

**`judge` calcula e não grava.** `sparkforge_judge` é `READ_ONLY` e continua
sendo. O plano sai na resposta; nenhuma entidade é criada e nada toca o disco.
Fazer o `judge` gravar o tornaria `LOCAL_MUTATION`, mudaria a cadeia de
autorização de uma tool que muitas skills chamam, e faria um verbo de leitura
escrever no repositório do operador.

**O registro auditável continua sendo `arbitrate`.** Blackboard, ADR, decisões
e `DebatePlan` completo saem por lá. A mesma computação roda duas vezes se o
operador quiser as duas coisas, e isso é aceitável: é derivação em memória sobre
dados que ele já tem.

**O bloco sai sempre, e o custo vai medido.** Sem parâmetro opt-in: o agente não
precisa saber que o plano existe para recebê-lo. Em troca, medir os bytes antes
e depois é parte da entrega, não observação posterior (regra 28).

---

## 3. Onde o código mora

Módulo novo `sparkforge/agentic/executor/digest.py`:

```python
def plan_digest(
    findings: list[dict], facts: list[dict], runtime: dict
) -> tuple[dict, dict[str, dict]]: ...
```

Devolve o bloco `plan` e o mapa `rule_id -> evidence_standing`. Ele chama
`claims_from_findings`, `direct_conflicts`, `conditional_conflicts`,
`order_actions` e `unknowns_from`, e monta — **sem criar entidade e sem tocar o
disco**.

**`run.py` passa a usar `digest.py`** em vez de repetir a sequência. Se as duas
montassem o plano por conta própria, divergiriam com o tempo, e o `judge`
passaria a dizer uma coisa e o `arbitrate` outra sobre o mesmo case. `run.py`
continua fazendo o que só ele faz: criar as entidades, arbitrar, decidir, gerar
ADR e gravar.

`_core.judge_findings` **só chama `plan_digest` e anexa**. Nenhuma lógica nova
em `_core.py`, que já tem 243 KB.

---

## 4. A forma da resposta

```json
{
  "items": [ "... findings, cada um com evidence_standing ..." ],
  "total_count": 20,
  "returned_count": 20,
  "next_cursor": null,
  "by_severity": { },
  "runtime": { },
  "plan": {
    "scope": "todos os 20 achados deste case, nao a pagina",
    "order": ["SF-UI-002", "SF-UI-001", "SF-ICE-005", "SF-ICE-001"],
    "order_unresolved": {},
    "constraints": [
      {
        "axis": "runtime.wall_clock",
        "rules": ["SF-PY-001", "SF-UI-003"],
        "reason": "aplicar juntas torna o antes/depois inatribuivel"
      }
    ],
    "contradictions": [
      {
        "rules": ["SF-GRAPH-005", "SF-LF-001"],
        "target": "glue.default_arguments",
        "directions": ["add", "remove"]
      }
    ],
    "objections": [
      {"rule": "SF-X-001", "blocked_by_kind": "env.unresolved", "fact_id": "f_abc123"}
    ],
    "unresolved": [
      {
        "question": "glue.run_cost: a medida nao foi resolvida.",
        "evidence_needed": ["sem DPUSeconds sob Auto Scaling"]
      }
    ],
    "persisted": false,
    "note": "calculado, nao gravado. O registro auditavel e `sparkforge arbitrate`."
  }
}
```

### 4.1 `scope` e `persisted` não são decoração

`scope` diz que a ordem é do **caso** e não da página. Sem ele, um agente que
recebeu 20 de 60 achados leria a ordem como completa — e ordem parcial
apresentada como ordem é a família de afirmação que este projeto recusa.

`persisted` é a fronteira da §2 escrita na própria resposta: quem lê o JSON sabe
que nada foi registrado, sem precisar consultar este spec.

### 4.2 `objections` sai vazio no catálogo de hoje, e a chave fica

O exemplo acima mostra `objections` preenchido para documentar a **forma**. Sobre
o catálogo medido no PR #42, ela é **sempre uma lista vazia**: a contradição
condicional tem zero casos, porque as quatro guardas `requires_absent` são todas
de **recusa** (`emr.configuration.unapplied`, `emrc.pod_template.unresolved`,
`env.unresolved`) e nenhuma de sintoma — e regra não dispara sobre "não deu para
ler".

A chave fica mesmo assim, pela razão da §8: forma estável é o que permite ao
agente confiar na chave em vez de testar se ela existe. E ela deixa de ser vazia
no dia em que um extrator emitir kind que só apareça acima do limiar — que é a
entrega própria já nomeada na §12.5 do spec anterior.

### 4.3 O que fica de fora do bloco

Claims e evidences completos (duplicam o finding que está ao lado), decisions e
ADR (exigem gravação), e o `DebatePlan` inteiro. Da existência de um plano de
debate sai apenas a contradição que o motivou; quem quer o plano chama
`arbitrate`.

---

## 5. `evidence_standing` no item

```json
{
  "rule_id": "SF-WASTE-001",
  "confidence": "medium",
  "evidence_standing": {
    "value": "high",
    "source_tier": "T1_OFFICIAL_DOCS",
    "in_version_scope": true,
    "measures_present": true
  }
}
```

**O nome é próprio de propósito.** `Finding.confidence` já existe, vem da regra,
e continua onde está. O lastro é outra coisa: é computado pelo executor a partir
de tier da fonte, escopo de versão e presença da medida. Dois campos `confidence`
na mesma resposta seriam ambiguidade publicada.

**Os três insumos viajam com o valor.** Um rótulo de confiança sem os insumos é
exatamente o que a §5.1 do spec anterior proibiu ao recusar publicar o score de
`assess_claim`. Com eles, quem lê refaz a conta: `high` exige os três; `medium` é
autoridade fora do escopo de versão; `low` é tier fraco ou medida ausente.

**O campo é anexado na serialização, não no dataclass.** Acrescentá-lo ao
`Finding` moveria os 125 goldens do corpus de novo e faria o campo viajar para
artefatos que não têm como computá-lo — `run_judge` não conhece mapa de
autoridade.

---

## 6. O custo, medido e publicado

O bloco sai em toda resposta, então o crescimento é de todo consumidor.
A entrega mede e publica:

- bytes da resposta de `judge` **antes e depois**, sobre o gold set de
  recuperação, com o comando que produz o número;
- o crescimento do `outputSchema` da tool no lock de superfície.

O número entra no spec, no STATUS e no manifesto de lastro — para que não
envelheça calado, que é o defeito que `check_vnext_claims.py` existe para pegar.

**Se o crescimento for grande o bastante para mudar a conclusão, isso sai escrito
e a decisão volta ao operador.** Nenhuma afirmação de que o plano "compensa" o
custo: não há os dois lados medidos, e a regra 30 vale aqui igual.

---

## 7. Gates que a entrega move

- `tests/test_adapters_tools.py`, `test_capability_parity.py`,
  `test_adapters_detail_level.py`, `test_adapters_code_surface.py`,
  `test_harness_authorization.py`, `test_runtime_inferred_from_facts.py`,
  `test_emr_eks_area_boundary.py`, `test_emr_serverless_runtime_boundary.py` —
  os oito que leem a resposta de `judge`;
- `check_surface_lock.py --update` — o `outputSchema` cresce, e o crescimento vai
  declarado no commit (regra 26);
- `check_vnext_claims.py` — `.py` novo move o corpus, como moveu nas sete vezes
  anteriores desta pilha;
- `tests/test_suite_batches.py` — arquivo de teste novo cai em exatamente um lote.

**Os goldens de fixture não devem mudar**: eles guardam `expected/findings.json`,
produzido por `run_judge`, não a resposta do adapter. **A implementação confirma
isso antes de escrever qualquer código** — se estiver errado, o custo triplica e
o desenho volta à mesa.

---

## 8. Testes

- `plan_digest` sobre fixture real: ordem, restrições e lastro batem com o que
  `run_executor` produz para o mesmo case — **é o teste que impede as duas
  respostas de divergirem**;
- `judge_findings` com paginação: `plan.order` cobre o conjunto, não a página, e
  `scope` diz isso;
- `plan.persisted` é sempre `false`, e nenhum arquivo é criado — teste que
  verifica o disco;
- os três ramos de `evidence_standing`, cada um com os insumos que o produziram;
- resposta de `judge` não carrega `score` em lugar nenhum — varredura de texto;
- case sem contradição, sem restrição e sem lacuna produz bloco com listas
  vazias, não bloco ausente: forma estável é o que permite ao agente confiar na
  chave.

---

## 9. O que fica de fora, explícito

- `judge` gravando qualquer coisa.
- `next_step` chamando o executor — ele não tem os facts, e dá-los a ele é outra
  entrega.
- Decisões, ADR e `DebatePlan` completo na resposta de `judge`.
- Qualquer afirmação de ganho — de token, de tempo, de qualidade de decisão.

---

## 10. O custo medido — os três cases, e o comando que os produz

Medido em 2026-09-08, sobre o corpus de fixtures, runtime `{glue 5.0, spark
3.5.4}`. **Antes** é a resposta de `judge_findings` sem o bloco `plan` e sem
`evidence_standing` nos itens; **depois** é a resposta como ela sai hoje.

| Case | findings | antes | depois | delta | pct |
|---|---|---|---|---|---|
| `fixtures/timeout/heartbeat_perdido/input` | 1 | 3501 | 3921 | +420 | **+12,0%** |
| `fixtures/terraform/plataforma_kms_rede_conta/expected` | 4 | 12157 | 13002 | +845 | **+7,0%** |
| `fixtures/eventlog/skewed_stage/expected` | 6 | 14172 | 15460 | +1288 | **+9,1%** |
| união dos três maiores do corpus | 15 | 47383 | 50506 | +3123 | **+6,6%** |

**O percentual varia de 12,0% a 6,6%, e a maior porcentagem cai no menor case.**
Publicar um número só teria sido a média que esconde a distribuição — é a mesma
armadilha que a regra 28 já documenta para `detail_level`, e ela aparece aqui
com o sinal invertido: lá o envelope fixo do pacote fazia a redução parecer
nula; aqui o envelope fixo do bloco `plan` faz o crescimento parecer grande.

A decomposição diz por quê:

| Case | findings | bloco `plan` | soma dos `evidence_standing` |
|---|---|---|---|
| `heartbeat_perdido` | 1 | 283 | 104 |
| `plataforma_kms_rede_conta` | 4 | 327 | 416 |
| `skewed_stage` | 6 | 492 | 648 |
| união | 15 | 1160 | 1608 |

`evidence_standing` custa **104 a 108 bytes por achado** e cresce linear com
eles. O bloco `plan` tem piso — `scope`, `persisted` e `note` saem sempre, mesmo
com um achado só — e daí o 12,0% do case de um achado: ali o denominador é
pequeno e o piso do bloco domina. Somados, os dois campos explicam o delta
inteiro menos ~33 bytes, que são as chaves e vírgulas do JSON.

**Nenhuma afirmação de que o plano compensa esse custo.** Não há os dois lados
medidos — decisão tomada com o bloco contra decisão tomada sem ele —, e a regra
30 vale aqui igual. O que está medido é o preço; o valor não está.

**O crescimento NÃO muda a conclusão do desenho**, e a base para dizer isso é a
direção da curva, não o tamanho do número: o percentual **cai** conforme o case
cresce, e o pior caso medido é o menor payload do corpus (3921 bytes), onde 420
bytes a mais não pressionam janela de contexto nenhuma. Se a curva subisse com o
tamanho, a decisão de sair sem opt-in voltaria ao operador.

**O corpus não tem case maior que 6 achados.** Varridos os **264** arquivos
`fixtures/*/*/expected/facts.json` e os **41** `fixtures/*/*/input/facts.json`,
a distribuição por `total_count` é `{0: 147, 1: 99, 2: 13, 3: 2, 4: 2, 6: 1}` no
primeiro conjunto e `{0: 36, 1: 5}` no segundo. A quarta linha
das tabelas é uma **união** de três fixtures pelo contrato repetível de `facts`,
e está rotulada como tal: ela mede a tendência além do teto do corpus, não uma
execução que alguém observou.

### O comando

```bash
python - <<'PY'
import json

from sparkforge.adapters._core import judge_findings

CASOS = [
    ["fixtures/timeout/heartbeat_perdido/input/facts.json"],
    ["fixtures/terraform/plataforma_kms_rede_conta/expected/facts.json"],
    ["fixtures/eventlog/skewed_stage/expected/facts.json"],
    [
        "fixtures/eventlog/skewed_stage/expected/facts.json",
        "fixtures/terraform/plataforma_kms_rede_conta/expected/facts.json",
        "fixtures/graph/dois_grafos_no_mesmo_arquivo/expected/facts.json",
    ],
]

for alvo in CASOS:
    r = judge_findings(facts_path=alvo, glue="5.0", spark="3.5.4")
    depois = len(json.dumps(r, ensure_ascii=False))
    sem = {k: v for k, v in r.items() if k != "plan"}
    sem["items"] = [
        {k: v for k, v in i.items() if k != "evidence_standing"} for i in sem["items"]
    ]
    antes = len(json.dumps(sem, ensure_ascii=False))
    plano = len(json.dumps(r["plan"], ensure_ascii=False))
    lastro = sum(
        len(json.dumps(i["evidence_standing"], ensure_ascii=False))
        for i in r["items"]
        if "evidence_standing" in i
    )
    print(
        f"{'+'.join(alvo)}\n  findings={r['total_count']} antes={antes} "
        f"depois={depois} delta={depois - antes} "
        f"pct={round((depois - antes) / antes * 100, 1)} "
        f"plan={plano} standing={lastro}"
    )
PY
```

### A superfície, já medida na T5

`docs/surface.lock.json`: tools de **376 854 para 380 762 bytes**, **+3908**
(**+1,04%**), com `tool_count` parado em **69** — o `outputSchema` de
`sparkforge_judge` cresceu, nenhuma tool nova entrou. Skills (57, 457 985 bytes)
e knowledge (50, 460 219 bytes) não se moveram.

**Byte de payload e byte de superfície não se somam num total.** O primeiro é o
que cada resposta carrega; o segundo é o que a tool pesa em repouso, uma vez por
sessão. São as mesmas unidades e grandezas diferentes, e juntá-los daria um
número que não mede nada — a mesma família de erro que a regra 22 recusa entre
byte e token.
