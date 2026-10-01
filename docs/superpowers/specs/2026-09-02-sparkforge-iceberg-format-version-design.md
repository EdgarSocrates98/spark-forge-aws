# SparkForge AWS — Iceberg: a versão que a tabela É, contra a que alguém declarou

**Data:** 2026-09-02
**Status:** **proposta**.
**Origem:** primeiro incremento de `prompt_evo_iceberg.md` (§8–10, §29–30, §72),
depois da auditoria da Fase A que o próprio prompt manda fazer.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. A auditoria da Fase A, e onde ela me corrigiu

O prompt tem 116 seções e 20 fases, e a §1 exige raciocinar sobre 27 camadas em
separado. Varri as 27 procurando **mecanismo** — fact kind ou regra —, e não menção:

| | |
|---|---|
| Com fact kind | **8 de 27** |
| Julgada por regra | **10 de 27** |
| Só menção em documentação | **15 de 27** |

**A varredura por nome de camada subestimou o repositório, e a correção importa mais
que o número.** `knowledge/storage/iceberg-feature-support.yaml` tem **858 linhas** com
**12 engines × 13 features** — `variant`, `deletion_vectors`, `row_lineage`,
`rest_catalog`, `remote_scan_planning` —, cada célula com evidência própria e `UNKNOWN`
obrigatório quando não há fonte. `sparkforge/storage/` tem `feature_support.py`
(`SPEC_VERSIONS = {2, 3}`), `readiness.py` e `upgrade.py` com
`VERDICTS = (BLOCKED, UNRESOLVED, CONDITIONAL, SAFE)`.

Camadas que marquei como ausentes — deletion vectors, Puffin, query planning — estão lá,
sob outros nomes. **O eixo spec × engine × feature existe e é rico.**

## 2. A lacuna que sobrevive à correção

`iceberg_assess_upgrade(path, source: int, target: int)` — **as duas versões são
declaradas pelo operador**, nenhuma é lida do artefato.

E o extrator não lê o `format_version` do topo do dump. Ele emite `format-version`
apenas como `iceberg.table_property` genérico — que é a **propriedade**, não a versão da
tabela.

**As duas são coisas diferentes.** O `format_version` do topo do metadata é
autoritativo; a propriedade `format-version` é um par chave/valor que pode estar ausente,
desatualizado, ou não ter sido propagado pelo coletor. Uma regra ancorada na propriedade
julgaria a declaração, não a tabela.

Medido nas 9 fixtures de `fixtures/iceberg/`: **as duas concordam em 9 de 9, e todas são
v2**. O corpus nunca exercitou nem a divergência nem outra versão — o eixo de spec está
sem lastro.

**Consequência:** o motor responde *"posso ir para v3?"* quando alguém lhe diz de onde
parte, e não responde *"esta tabela é v1, e o engine já suporta v2 há três releases"*.

## 3. Objetivo

Ligar o lado do **artefato** ao lado do **conhecimento** que já existe: um kind
`iceberg.format_version` lido do topo do dump, com a distinção entre a versão real e a
propriedade declarada, e recusa nomeada quando o coletor não a forneceu.

### Não-objetivos, com razão registrada

- **Não escrever matriz de spec × engine.** Ela existe, tem 858 linhas e uma regra de
  evidência por célula. Escrever a segunda seria a duplicação que o sub-projeto 2 do
  Glue existiu para remover.
- **Não inferir a versão da propriedade quando o topo faltar.** Se o coletor não trouxe
  `format_version`, a resposta é `unresolved` nomeada — inferir da propriedade
  transformaria "o coletor não me deu" em "a tabela é v2".
- **Não julgar v1 como defeito por si só.** Uma tabela v1 é uma tabela válida. O defeito
  só existe quando a matriz diz que o engine do consumidor suporta mais **e** há motivo
  para subir — e esse é o incremento seguinte, não este.

## 4. Decisões de desenho

### D-1 — dois campos, não um, e a divergência é FATO

O kind carrega `attrs.declared` (o topo do metadata) e `attrs.property` (o valor de
`properties["format-version"]`, se houver). Quando divergem, `attrs.diverges` é `true`.

Colapsá-los num campo escolheria por conta própria qual dos dois é a verdade, e o caso
em que eles divergem é exatamente o que vale reportar: a propriedade ficou para trás de
um upgrade, ou o coletor leu de dois lugares.

### D-2 — a ausência do topo é `unresolved` NOMEADA, com a medida que destrava

Três razões distintas, porque destravam de formas diferentes:

| Razão | O que fazer |
|---|---|
| `format_version_ausente_no_dump` | o coletor precisa incluir o campo — é uma linha do `metadata.json` |
| `format_version_nao_numerico` | o dump trouxe algo que não é inteiro |
| `format_version_fora_da_spec` | um valor fora de `{1, 2, 3}` — a spec publica três |

`SPEC_VERSIONS` em `feature_support.py` hoje é `{2, 3}` — **v1 não está lá**, e a razão é
que aquela constante governa *upgrade de spec*, não *leitura de tabela*. Este extrator
aceita `1` e o declara, sem tocar naquela constante.

### D-3 — nenhuma regra nova neste incremento

O kind entra sem consumidor de regra, e isso é deliberado: uma regra que julgasse v1
como defeito precisaria da matriz **e** de um motivo, e o motivo é do incremento
seguinte. O que este entrega é o **fato**, que hoje não existe.

Mecanismo sem consumidor é dívida quando o consumidor não está planejado. Aqui está: a
§72 (v2→v3) e o cruzamento com `readiness()` dependem exatamente deste fato.

### D-4 — o corpus ganha as versões que faltam

As 9 fixtures são todas v2. Entram três casos: uma tabela **v1**, uma **v3**, e uma em
que topo e propriedade **divergem**. Sem elas o eixo continua sem lastro, e o kind novo
sairia com um único valor em todo o corpus.

## 5. Testes e gates

- O kind sai em **todas** as fixtures, inclusive nas que não têm `format_version` no
  dump — ali como `unresolved` nomeada.
- As três razões de recusa têm caso.
- **A divergência tem fixture**, e `attrs.diverges` é `true` só nela.
- v1, v2 e v3 todos representados; nenhum é tratado como defeito.
- Todo kind novo em algum golden; extrator nas duas listas manuais de teste.
- Gates de sempre, e **`check_vnext_claims.py` antes de commitar** — ver
  [`gate-de-lastro-roda-em-todo-branch`], porque o corpus de `*.py` cresce.

## 6. Critérios de conclusão

- `iceberg.format_version` sai do topo do dump, nunca inferido da propriedade.
- A divergência entre os dois é fato, com fixture.
- As três recusas têm nome e medida que as destrava.
- v1 não é julgado como defeito, e a razão está escrita.
- Nenhuma matriz nova; a de 858 linhas é a única.

## 7. Fora do escopo

| | |
|---|---|
| Regra que cruze a versão da tabela com `readiness()` | incremento seguinte — precisa de motivo, não só de fato |
| §71/72 migração v2→v3 | depende deste fato, e vem depois |
| As outras 14 camadas sem mecanismo | cada uma precisa da mesma auditoria antes |
| Ampliar `SPEC_VERSIONS` para incluir 1 | aquela constante governa upgrade, não leitura |
