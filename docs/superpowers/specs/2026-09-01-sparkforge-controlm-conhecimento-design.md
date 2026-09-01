# SparkForge AWS — Control-M como domínio de conhecimento: dois eixos, porque a fonte tem dois

**Data:** 2026-09-01
**Status:** **proposta**.
**Origem:** primeiro incremento da avaliação de `prompt_evo_spark_bmc.md`.
O prompt pede 95 seções; esta spec entrega **uma** — a que responde a pergunta
que o operador trouxe.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. A pergunta, e o recorte

O operador declarou: **não tem Control-M instalado**, não tem artefato, e quer
*"conhecimento para atuar em todas as versões entre `9.0.21.200` e
`9.0.22.100`"*.

Isso mata metade do prompt de origem antes de começar. Sem artefato não há
extrator validado, e sem extrator não há regra que julgue definição de job. O
que **sobra** é o que a pergunta de fato pede: conhecimento versionado.

## 2. A fonte, e como ela foi achada

A primeira leitura deu **HTTP 403** e a conclusão apressada foi "não há fonte
acessível". **Estava errada por duas razões independentes**, e as duas ficam
registradas porque a segunda vai morder de novo:

1. **O 403 é de user-agent, não de produto.** `curl` sem UA devolve 403; com UA
   de browser devolve 200. Medido nas duas direções. **`WebFetch` é inutilizável
   contra `docs.bmc.com` e `documents.bmc.com`** — toda coleta desta fonte exige
   UA de browser, e isso é mecanismo do coletor, não detalhe de operação.
2. **O caminho estava errado.** O espaço de nomes é `Control-M-Orchestration`,
   não `IT-Operations-Management`.

A fonte que sustenta a matriz:

```
https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_What_s_New.htm
```

Medido no corpo real, não no relatório de terceiro: **45 versões citadas**, das
quais **31 dentro da faixa pedida**, com fronteiras literais —
*"no longer supports Java 11 as of version 9.0.21.325"*, *"`config
em:param::set` is deprecated from version 9.0.21.300"*, *"new
`Job:DetachedEmbeddedScript`... 9.0.22.010"*.

O schema de `Jobs-as-Code` também abre (`API_CodeRef_JobProperties.htm`,
`API_CodeRef_JobTypes.htm`) — é o insumo do **incremento 2**, fora desta spec.

## 3. Decisões de desenho

### D-1 — dois eixos, porque a fonte tem dois tipos de afirmação

As quatro plataformas de runtime deste repositório têm forma **componente →
versão** (`spark: 3.5.3-amzn-0`). A fonte da BMC tem **duas** formas:

| Forma | Exemplo medido | Molde no repositório |
|---|---|---|
| **capacidade com fronteira** | `Job:DetachedEmbeddedScript` existe a partir de `9.0.22.010` | matriz de feature do Iceberg (`min_library_version`) |
| **componente com exigência** | Java 11 deixa de ser suportado em `9.0.21.325`; Python `3.8.4+` | matriz de runtime |

Forçar tudo num eixo só foi avaliado e **recusado**: `Java 11` não é componente
com versão, é fronteira de exigência. A D-1 do sub-projeto 4 já registrou o custo
desse erro — *célula que responde por coisas de naturezas diferentes é pior que
célula ausente, porque ausência é recusa e a célula é afirmação*.

Cada afirmação vai para o eixo que a descreve. As que não couberem em nenhum
saem `unresolved` **nomeadas**.

### D-2 — a faixa congela; a página fica vigiada

A fonte é a página **`Monthly`**, e ela **rola**: hoje declara `9.0.22.125`, e
ganha linha a cada mês. O `sources.lock.json` vigia hash de conteúdo, então ela
vai disparar drift ~12×/ano.

Isso **não** é motivo para tirá-la da watchlist. Há precedente medido e mais
brando: `knowledge/emr/runtime-matrix.md` registra que a série 7.x da AWS
*"prepende uma coluna a cada minor"* e que o *"hash muda ~4×/ano sem que nada que
a matriz conhece tenha mudado — alarme esperado"*.

O procedimento fica escrito no cabeçalho do documento:

> A faixa `9.0.21.200`–`9.0.22.100` é **passado fechado**: nada que role muda o
> que aconteceu no `9.0.21.300`. Ao drift, confira se alguma célula **da faixa**
> mudou — não deveria, e se mudou é errata da BMC e vale leitura. Linha nova de
> versão **futura** não entra sem alguém ler.

Isso torna o alarme mensal barato: quase sempre fecha sem ação, e o texto diz
por quê.

### D-3 — o verbo é `describe`, e ele responde a pergunta que foi feita

O operador atua em clientes com versões diferentes. A pergunta dele é *"estou na
`9.0.21.300` — o que posso usar?"*, não *"o que quebra de X para Y"*.

Entrega: um `describe` por versão, no molde de `sparkforge release describe` que
já existe. O `diff` sai de graça depois, porque o dado é o mesmo — mas **não é
objetivo desta spec**, e prometê-lo aqui seria escopo que ninguém pediu.

### D-4 — sem extrator, sem regra, sem área

Não há artefato para extrair e não há fonte que sustente julgamento. Este
incremento entrega **dado e consulta**. Regra que julgue definição de job depende
do incremento 2, e escrevê-la agora produziria regra sem corpus.

### D-5 — o lastro é do Automation API, não do produto inteiro

Medido: do lado do **produto** Control-M, só `9.0.21.300` e `9.0.22` abrem;
`9.0.22.100` está atrás de login de entitlement e `9.0.21.200` não tem raiz de
doc própria.

Então a matriz é do **Automation API**, e o documento precisa dizer isso no
título e no cabeçalho. Célula sobre o produto fora do Automation API sai
`unresolved` com a razão — nunca preenchida por analogia.

## 4. O que entregar

```
knowledge/controlm/automation-api-matrix.md    prosa, fontes, e o que a fonte NAO sustenta
knowledge/controlm/automation-api-matrix.yaml  espelho executavel, dois eixos
```

O par `.md` + `.yaml` com guard de drift é o molde que as quatro matrizes já
usam (`tests/test_runtime_matrix_drift.py`), e o guard existente é parametrizado
por célula — estender é acrescentar entrada, não escrever quinto mecanismo.

Superfície: `sparkforge controlm describe --version 9.0.21.300` e a tool MCP
equivalente, em paridade.

## 5. Testes e gates

- Guard de drift: YAML × tabela do `.md`, como as quatro irmãs.
- Toda célula: fronteira de versão com fonte, ou `unresolved` com razão. Nenhuma
  vazia.
- **O contrafactual da faixa:** `describe 9.0.21.300` e `describe 9.0.22.010`
  respondem **diferente** para `Job:DetachedEmbeddedScript`. É o teste que prova
  que a fronteira de versão não é decorativa.
- Versão fora da faixa coberta: recusa nomeada com o intervalo que a matriz
  sustenta — não `UNKNOWN` mudo, e não extrapolação.
- Fonte no `sources.lock.json` com o perfil de drift declarado (D-2).
- Gates de sempre: `check_surface_lock.py --update`, `check_status_numbers.py
  --strict` se a tabela de *Números correntes* ganhar linha, suíte em lotes.

## 6. Critérios de conclusão

- As 31 versões da faixa estão na matriz, cada afirmação no eixo que a descreve.
- `describe` responde por versão, e recusa por nome fora da faixa.
- O perfil de drift da fonte está escrito, com o procedimento do alarme mensal.
- O limite do Automation API contra o produto inteiro está declarado.
- Nenhuma regra nova, nenhum extrator — e a razão dos dois está escrita.

## 7. Fora do escopo, e onde cada um mora

| | |
|---|---|
| Extrator de `Jobs-as-Code` | incremento 2 — o schema abre, e é o insumo |
| Regras sobre dependência, janela, SLA | incremento 3, depois do extrator |
| Cruzamento com Glue/EMR (job que dispara Spark) | incremento 3 |
| `diff` entre versões de Control-M | sai de graça do dado, mas não é objetivo aqui |
| As outras ~90 seções do prompt de origem | debate, review matrix, repair loop, MCP taxonomy — avaliadas e não pedidas por esta pergunta |

## 8. Desvios

Vazio.
