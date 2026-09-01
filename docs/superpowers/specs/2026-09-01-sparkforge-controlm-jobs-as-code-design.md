# SparkForge AWS — Jobs-as-Code: o extrator, e a regra que usa a matriz

**Data:** 2026-09-01
**Status:** **proposta**.
**Origem:** segundo incremento da avaliação de `prompt_evo_spark_bmc.md`.
**Depende de:** [incremento 1](2026-09-01-sparkforge-controlm-conhecimento-design.md),
que entregou a matriz versionada do Automation API (PR #23).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. O que o incremento 1 destravou

A matriz do Automation API sabe, por versão, **qual capacidade existe**:
`Job:DetachedEmbeddedScript` a partir de `9.0.22.005`, `config em:param::set`
depreciado em `9.0.21.300`.

Isso abre um julgamento que não existia antes:

> *"este job usa `Job:DetachedEmbeddedScript`, e o Control-M do cliente é
> `9.0.21.300` — não vai rodar."*

**É o único julgamento que a fonte sustenta hoje**, e ele é o motivo de o
extrator e a regra virem juntos, contra o que o incremento 1 previu. Separá-los
produziria facts que ninguém julga — o defeito de *mecanismo sem consumidor* que
a auditoria de 2026-09-01 pegou duas vezes.

Precedente: EMR on EKS entregou extrator e regras na mesma fase, doc-sourced.

## 2. O artefato existe, mesmo sem Control-M instalado

O incremento 1 partiu de *"o operador não tem Control-M e não tem artefato"*.
Para `Jobs-as-Code` isso **muda**, e a diferença é de natureza:

`describe-job-run` é saída de runtime — precisa da instância. **Jobs-as-Code é
código-fonte**: definição de job em JSON, versionada no repositório do cliente,
que o `ctm build` valida e o `ctm deploy` publica.

Ou seja: o operador plausivelmente **tem** o artefato mesmo sem ter o Control-M.
É a mesma natureza de `main.tf` ou de um `.py` de PySpark, que este motor já lê.

## 3. Objetivo

Ler definição de `Jobs-as-Code`, emitir facts com namespace fechado, e julgar
**compatibilidade de capacidade contra versão declarada**.

### Não-objetivos, com razão registrada

- **Julgar dependência, janela e SLA.** A página de *What's New* não sustenta o
  que é defeito nesses eixos. Exigiria pesquisa nova no `API_CodeRef`, e é o
  incremento 3.
- **Validar o JSON contra o schema completo.** `ctm build` faz isso e é da BMC.
  Reimplementar validação de schema seria concorrer com a ferramenta oficial sem
  fonte que sustente divergência.
- **Regra de segredo em texto claro.** Seria o **quarto** exemplar do mesmo
  julgamento (`SF-EMR-002`, `SF-EMRS-002`, `SF-EMRK-001`). Entra **se e somente
  se** a leitura do `API_CodeRef` mostrar campo que carregue credencial por
  desenho; caso contrário é triplicação sem ganho.

## 4. Decisões de desenho

### D-1 — a versão do Control-M é **declarada**, nunca inferida do artefato

O JSON de Jobs-as-Code **não** carrega a versão do Control-M que vai executá-lo.
Inferir do conteúdo seria adivinhar.

Então a versão entra **declarada pelo operador** — `--version 9.0.21.300` — e o
fact registra que ela é **declaração**, não leitura. Sem versão declarada, a
regra de compatibilidade **não dispara**: ela sai em `refused` com a medida que a
destravaria.

É a mesma disciplina de `RuntimeContext` das quatro plataformas de EMR, e o
inverso do erro que a dívida do `judge --emr` cometeu por três fases.

### D-2 — namespace `ctm.`

`ctm` é o prefixo da CLI oficial (`ctm build`, `ctm deploy`, `ctm run`) e do
cliente Python (`ctm-python-client`). Não colide com nenhum kind existente.

### D-3 — a regra lê a matriz, e não repete a fronteira

A fronteira de versão mora em `knowledge/controlm/automation-api-matrix.yaml`. A
regra **não** repete `9.0.22.005` no `when` — ela pergunta à matriz.

Repetir criaria a segunda cópia do mesmo fato, que é o defeito que o
sub-projeto 2 existiu para remover, e que a D-1 do sub-projeto 4 proibiu
explicitamente.

Consequência de mecanismo: como o motor de regras avalia expressão sobre facts, o
**cruzamento precisa acontecer no extrator ou num fact derivado** — no molde de
`tf.observability.spark_ui` e `tf.graphframes.jar`, que decidem uma vez e emitem
o kind já decidido. A regra fica com a condição simples sobre ele.

### D-4 — capacidade que a matriz não conhece é recusa, não aprovação

Job que use capacidade fora da matriz (porque a fonte não a nomeia, ou porque é
de versão futura) sai `unresolved` **nomeado** — nunca "compatível por omissão".

O incremento 1 mediu que **9 das 31 versões da faixa não têm afirmação própria**
e que **175 linhas de *Corrected Problems*** não couberam em eixo nenhum. O
silêncio da matriz é grande, e tratá-lo como aprovação seria o pior defeito
possível.

### D-5 — coleta da BMC precisa de UA **e** de espaçamento

Medido em 2026-09-01, depois do incremento 1: as páginas do `API_CodeRef`
devolveram **403 mesmo com UA de browser**, e voltaram **200** após pausa de ~45
segundos. **Era rate limit, não gate.**

Isso precisa estar escrito onde quem for reler a fonte vá olhar: uma coleta de
várias páginas em sequência **vai** dar 403 no meio, e quem não souber disso
conclui que a fonte fechou. O incremento 1 já registrou que `WebFetch` não serve;
esta é a segunda metade da mesma armadilha.

## 5. Testes e gates

- **O contrafactual da regra:** o mesmo job julgado contra `9.0.21.300` e contra
  `9.0.22.010` produz achado **diferente**. Se não conseguir ficar vermelho antes
  da mudança, não há cruzamento com a matriz — há regra com número embutido.
- **Sem versão declarada, a regra não dispara**, e a recusa é nomeada. Fixture
  própria.
- Capacidade fora da matriz → `unresolved` nomeado, nunca aprovação.
- Todo kind de `EMITTED_KINDS` em algum golden; toda regra com golden positivo e
  negativo; extrator novo nas **duas** listas manuais, no mesmo commit.
- Fronteira: nenhuma regra `SF-CTM` dispara sobre artefato das outras áreas, e o
  inverso.
- Gates de sempre, incluindo `check_status_numbers.py --strict`, que agora
  audita a tabela de *Números correntes*.

## 6. Critérios de conclusão

- Definição de `Jobs-as-Code` produz facts `ctm.*` com namespace fechado; JSON
  malformado vira `ctm.unresolved` sem exceção.
- A regra de compatibilidade cruza com a matriz e **não** repete a fronteira.
- Versão não declarada → recusa nomeada, não silêncio.
- Capacidade desconhecida → `unresolved`, não aprovação.
- CLI e MCP em paridade; gates verdes.

## 7. Desvios

Vazio.
