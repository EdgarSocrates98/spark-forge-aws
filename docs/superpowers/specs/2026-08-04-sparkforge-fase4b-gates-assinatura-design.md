# SparkForge AWS — Fase 4b: gates fail-closed e assinatura de correspondência

**Data:** 2026-08-04
**Status:** desenhado, não implementado.
**Fecha:** dois dos três itens de rigor que restam da §16 do
[spec da Fase 0](2026-07-29-sparkforge-fase0-design.md). O terceiro — validação
funcional automatizada — é a Fase 4c, por decisão registrada na §2.
**Base:** [Fase 4a](2026-08-03-sparkforge-fase4a-benchmark-design.md) — sem ela
esta fase não seria possível, pelo motivo da §1.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: a razão da Fase 0 deixou de valer para metade dos gates

A §5.5 do spec da Fase 0 registrou, como decisão consciente, que `blocked_by` é
**advisory**:

> `blocked_by` é advisory na Fase 0, não fail-closed: reporta gate não satisfeito
> e segue. **Gate rígido vira impasse quando o dado simplesmente não existe.**
> Endurecer é escopo da Fase 4.

O argumento estava certo, e continua certo — para gate sem produtor. O que mudou
é que agora existe gate **com** produtor. Medido em `rules/catalog/routing.yaml`,
o vocabulário inteiro tem dois nomes:

| Gate | Rota | Produtor |
|---|---|---|
| `baseline_captured` | `ROUTE-012` | `bench.run_delta`, entregue pela Fase 4a |
| `functional_validation_defined` | `ROUTE-015` | **nenhum** — é a Fase 4c |

Endurecer `baseline_captured` hoje tem saída concreta: o operador roda
`sparkforge benchmark`. Endurecer `functional_validation_defined` hoje é
exatamente o impasse que a Fase 0 previu.

Daí sai o critério desta fase, e ele não é preferência: **um gate só pode ser
fail-closed se tiver produtor declarado.** O critério é verificável por teste, e
faz a fase envelhecer bem — quando a 4c entregar o produtor do segundo gate, ele
passa a poder endurecer sem que nada aqui precise mudar.

## 2. Objetivo

Duas garantias que o motor não tem:

1. **O case não avança de fase com gate não satisfeito**, quando o operador pediu
   rigor — e quando ele passa por cima, isso fica registrado com nome e motivo.
2. **O relatório carrega prova de correspondência** com a evidência e o catálogo
   que o produziram.

### Não-objetivos, com razão registrada

| Fora de escopo | Razão |
|---|---|
| Validação funcional automatizada (contagem, schema, chaves, agregados) | Precisa de artefato que **não existe** — o resultado de consultas que alguém roda. Natureza diferente das duas desta fase, que não pedem artefato nenhum. Fase 4c |
| Assinatura que prove **autoria** (HMAC, GPG, sigstore) | Exige chave para distribuir e guardar, e o projeto passaria a ter um segredo — superfície que hoje não existe. E autoria só tem valor se alguém verificar; correspondência tem valor sozinha |
| Endurecer `functional_validation_defined` | Sem produtor. Endurecê-lo agora é o impasse da §5.5 |
| Gate sobre emissão de achado | `validate_finding` julga o **achado**; estado do case é outra camada. Misturar as duas foi recusado no desenho |

## 3. Decisões de desenho

### D-1 — o gate mora em `set_phase`, e só ali

`sparkforge/case/store.py:121` é o único ponto de passagem entre fases do case.
Um lugar só, nenhum caminho lateral, e o teste que prova isso é grep: nenhuma
outra função escreve `case["phase"]`.

### D-2 — produtor declarado no próprio `routing.yaml`

Cada gate ganha, ao lado do nome, o kind de fact que o satisfaz e o comando que o
produz. Sem esses dois campos o gate **permanece advisory**, mesmo com rigor
ligado — e isso é invariante de teste, não convenção.

Declarar o produtor junto do gate mantém a decisão no dado, como o roteamento de
coordenador virou dado na Fase 4. Uma lista paralela em Python seria o passo que
alguém esquece.

### D-3 — o rigor é do case, declarado na abertura

`sparkforge case open --strict-gates` grava a escolha no `case.yaml`, e ela vale
pela investigação inteira: outra sessão, outra máquina, outra ferramenta. Quem
retoma herda o rigor de quem abriu.

A alternativa recusada era flag por invocação (`case update --phase X --strict`).
Ela desliga o gate em silêncio quando alguém esquece a flag — a família de
defeito que esta sessão inteira perseguiu, e que já apareceu como `thresholds` no
plural e como `if fact_ids`.

### D-4 — override existe, exige motivo, e fica gravado

O dado às vezes genuinamente não existe: job descontinuado, ambiente que sumiu,
janela de execução que não volta. Gate sem escapatória reabre o impasse que a
§5.5 recusou.

```
sparkforge case update --phase remediation \
  --override-gate baseline_captured --reason "job descontinuado, sem ambiente para reexecutar"
```

Sem `--reason`, o override é recusado. O case guarda quem pulou o quê e por quê,
`resume` mostra, e o relatório carrega. É a diferença entre *o gate não existe* e
*o gate existe e alguém passou por cima com o nome dele registrado* — a mesma
distinção que `dq.unresolved` faz entre "não há problema" e "ninguém olhou".

### D-5 — a mensagem de bloqueio nomeia o comando que destrava

Não "gate não satisfeito", e sim: a fase pedida, o gate, o fact que faltou, e o
comando exato. A Fase 4a mediu que mensagem inacionável passa no CI — os testes
cobravam `code == 2` e a presença da string `"sparkforge"`, e uma mensagem
mandava rodar o verbo errado. O teste desta fase assere **conteúdo**.

### D-6 — a assinatura prova correspondência, e o bloco diz isso

Um relatório assinado afirma: *este texto foi derivado destes facts com este
catálogo*. Não afirma quem o emitiu, e qualquer um com os mesmos facts produz a
mesma assinatura.

O limite vai escrito **dentro do bloco de assinatura**, não só na documentação.
Bloco que sugira autoridade mente por omissão, e é o tipo de mentira que este
projeto existe para não cometer.

### D-7 — o corpo do relatório entra no hash

| Entra | Pega |
|---|---|
| `fact_id` citados, ordenados | achado que cita evidência trocada |
| `catalog_version`, `schema_version` | relatório julgado por catálogo diferente do declarado |
| `rule_id` que dispararam, ordenados | achado acrescentado à mão |
| corpo do relatório, normalizado | prosa editada depois da emissão |

Sem o corpo, alguém reescreve o texto inteiro mantendo a assinatura válida — e a
assinatura passaria a garantir menos do que o leitor supõe. Com o corpo, edição
legítima invalida, e reassinar é barato. O que não pode acontecer é texto editado
continuar parecendo verificado.

A normalização absorve reformatação (espaço em branco, quebra de linha), e o que
ela absorve precisa estar escrito — normalização silenciosa é superfície para
adulteração que passa.

## 4. Superfície

| Onde | O quê |
|---|---|
| `sparkforge/case/store.py` | `set_phase` consulta os gates; `case.yaml` guarda `strict_gates` e o histórico de override |
| `rules/catalog/routing.yaml` | produtor por gate: kind e comando |
| `sparkforge/adapters/{_core,cli,tools}.py` | `case open --strict-gates`; `case update --override-gate --reason`; `report sign`; `report verify` |
| `sparkforge/case/resume.py` | override aparece na retomada, com motivo |
| `templates/performance-report.md` | onde o bloco de assinatura mora |
| `parity.yaml`, `manifest.json` | as duas capacidades novas nas cinco plataformas |

**Sem extrator novo e sem kind novo.** Esta fase não produz `Fact`; ela muda o
ciclo de vida do case e acrescenta um artefato de saída. É a primeira fase desde
a 0 que não toca `sparkforge/facts/`.

## 5. Prova

- **Gate advisory continua advisory sem rigor ligado** — case aberto sem
  `--strict-gates` transita como hoje, e há teste. Nenhum case em andamento
  quebra.
- **Gate com produtor bloqueia com rigor ligado**, e a mensagem nomeia o comando.
- **Gate sem produtor declarado nunca bloqueia**, mesmo com rigor ligado — é o
  critério da §1 travado por teste, e é ele que impede alguém de endurecer
  `functional_validation_defined` antes da 4c.
- **Override sem `--reason` é recusado**; com motivo, transita e fica gravado, e
  `resume` o mostra.
- **`report verify` distingue o que divergiu** — evidência, catálogo ou corpo —
  em vez de devolver "inválido".
- **Reformatação não invalida; edição de conteúdo invalida.** Os dois com teste,
  porque é a fronteira que a normalização define.

## 6. Critérios de sucesso

1. `set_phase` é o único ponto que decide transição, provado por grep em teste
2. Gate sem produtor declarado não bloqueia, com rigor ligado, e há teste
3. `baseline_captured` bloqueia com rigor ligado e destrava com `sparkforge benchmark`
4. `functional_validation_defined` **não** bloqueia — sem produtor até a 4c
5. Case sem `--strict-gates` se comporta exatamente como antes desta fase
6. Override exige motivo, fica no case, aparece em `resume` e no relatório
7. Mensagem de bloqueio nomeia fase, gate, fact faltante e comando — asserido por conteúdo
8. `report verify` nomeia qual das três partes divergiu
9. O bloco de assinatura declara, no próprio texto, que prova correspondência e não autoria
10. Nenhum `Fact` novo, nenhum kind novo, `sparkforge/facts/` intocado

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Rigor ligado trava investigação legítima onde o dado não existe | Override com motivo, gravado. E o critério do produtor garante que todo gate que bloqueia tem comando que destrava |
| `case update --gate X --gate-value true` vira override silencioso | Ver §8, desvio D-4b-2: sob rigor o booleano manual não satisfaz |
| Assinatura lida como autoridade | O limite vai dentro do bloco, não só na doc. Critério 9 |
| Normalização absorve demais e adulteração passa | O que ela absorve está escrito e tem teste dos dois lados |
| `--strict-gates` vira padrão de fato e quebra caso antigo | Critério 5: sem a flag, comportamento idêntico ao de hoje, com teste |

## 8. Desvios medidos antes da implementação

Duas medições feitas ao escrever o plano corrigem este documento. Ele **não é
reescrito** — a convenção do repositório (`STATUS.md`, "Como manter este arquivo
honesto") manda registrar o desvio e preservar o que se pretendia.

**D-4b-1 — o vocabulário de gate tem quatro nomes, não dois.** A §1 lê o
vocabulário a partir de `rules/catalog/routing.yaml`, que declara `blocked_by`
em duas rotas. Mas `sparkforge/case/store.py:34` define `GATES` com **quatro**:
`baseline_captured`, `dominant_bottleneck_identified`, `functional_validation_defined`
e `flows_mapped`. O case rastreia os quatro desde a Fase 0; o roteamento usa
dois.

Isso **amplia** o critério do produtor em vez de contrariá-lo: cada um dos
quatro precisa ser classificado, e só os que tiverem produtor declarado podem
endurecer. `dominant_bottleneck_identified` e `flows_mapped` entram na mesma
pergunta que a §1 fez para os outros dois, e a resposta é trabalho da Task 1 do
plano — não deste spec.

**D-4b-2 — o booleano manual já existe, e sob rigor ele não pode satisfazer.**
`case update --gate <nome> --gate-value true` (`cli.py:386-387`,
`_core.py:1641`) permite virar qualquer gate à mão. Se isso satisfizesse o gate
no modo estrito, virar a flag seria um override **sem motivo e sem registro** —
e o `--reason` do D-4 perderia sentido, porque existiria um caminho mais curto
que não o exige.

Decisão: no modo estrito o booleano manual é **ignorado**. O gate é satisfeito
por evidência (o fact produtor presente) ou por override registrado. No modo
advisory — o de hoje — nada muda, e nenhum case em andamento quebra.

O critério 5 da §6 já cobria a metade compatível disso; a metade nova é: **com
rigor ligado, `--gate-value true` não destrava**, e há teste.

**D-4b-3 — nenhuma fase é guardada por um gate só, e isso muda dois testes, não
um.** A Task 1 avisou que a fase do teste do gate *sem* produtor precisa levar o
kind do gate que a guarda. Medido ao implementar: o mesmo vale para o teste que
prova que **o fact produtor satisfaz** — `validation` e `report` são guardadas
pelos **dois** gates com produtor (`baseline_captured` e `flows_mapped`), então
`set_phase(case, "validation", fact_kinds={"bench.run_delta"})` continua
bloqueando, por `flows_mapped`. O esboço do plano passaria só um kind e falharia
por um motivo que não é o que ele afirma testar.

Consequência escrita no teste: `TODOS_OS_KINDS` para as fases do fechamento, e
`hypothesis` — a única fase guardada por exatamente um gate — para asserir a
mensagem de bloqueio de `flows_mapped` isolada. Mais um teste novo,
`test_satisfazer_so_um_dos_dois_gates_ainda_bloqueia`, que trava a sobreposição
em vez de deixá-la implícita.

**D-4b-4 — o contrato é lido e validado em `router.py`, não em `store.py`.** A
lista de arquivos da Task 2 previa só `store.py`, `routing.yaml` e o teste. Mas
`routing.yaml` já tem dono — `sparkforge/case/router.py`, que é quem sabe
resolver o diretório do catálogo com contenção de path (`safe_catalog_file`).
Duplicar essa leitura no store seria uma segunda porta para o mesmo arquivo.

`load_gate_contract()` fica ao lado de `load_routing()`, e a validação de forma
do bloco (`satisfied_by` sem `produced_by`, `guards_phases` vazio,
`advisory_reason` ausente) roda **dentro de `load_routing`** — isto é, em todo
uso do routing, e não só quando o gate é cobrado. Mesma razão de
`loader._validate_conditions`: bloco malformado morre na carga, porque gate
inerte em silêncio é falso negativo mudo. Ao store cabe só o que depende de
`GATES`: recusar nome de gate que o case não conhece. O import de `router` é
tardio, para que sem `strict_gates` o catálogo não seja lido — e há teste
disso.
