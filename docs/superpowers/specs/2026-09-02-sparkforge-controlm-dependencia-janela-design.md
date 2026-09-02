# SparkForge AWS — Control-M: dependência e janela têm fonte; SLA não tem

**Data:** 2026-09-02
**Status:** **entregue** em 2026-09-02. Ver a seção 8 para os desvios medidos, e
[`../STATUS.md`](../STATUS.md) para o registro da entrega.
**Origem:** terceiro incremento da avaliação de `prompt_evo_spark_bmc.md`.
**Depende de:** [incremento 1](2026-09-01-sparkforge-controlm-conhecimento-design.md)
(matriz versionada, PR #23) e [incremento 2](2026-09-01-sparkforge-controlm-jobs-as-code-design.md)
(extrator `ctm.*` e `SF-CTM-001`, PR #24).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. A pergunta era binária

O incremento 2 registrou que a página de *What's New* não sustenta julgamento
sobre dependência, janela e SLA, e adiou os três para cá. A pergunta desta fase
não era "o que dá para construir" — era: **a fonte nomeia defeito?**

Campo documentado não sustenta regra. Sustenta extrator, e ele já existe. Regra
exige que a fonte diga que algo **está errado**: um `must`, um `cannot`, um
`is not supported`, um limite numérico.

Medido em `API_CodeRef_JobProperties.htm` (423 KB, lido 2026-09-02, `curl` com UA
de browser), varrendo por padrão de defeito em vez de por conceito:

| Eixo | Defeitos nomeados |
|---|---|
| **janela** | **3** |
| **dependência** | **2** |
| **SLA** | **0** |

`SLA`, `ServiceLevel`, `Deadline`, `MaxWait` e `CompletionTime` têm **zero
ocorrências** na página inteira.

## 2. Os cinco, citados literalmente

**J-1 — `SpecificDates` contra o resto do agendamento**

> *"The `SpecificDates` option **cannot** be used in combination with options
> `WeekDays`, `Months`, or `MonthDays`. However, since the default for these
> options is "ALL", you **must** specify these options with a value of "NONE"."*

É o mais rico dos cinco, e a segunda frase é o que o torna verificável: como o
default é `ALL`, **omitir** `WeekDays` já é combinar. Um job com `SpecificDates`
e sem `WeekDays: "NONE"` está errado **por omissão**, e é o caso que ninguém vê
lendo o JSON.

**J-2 — o teto de datas**

> *"You can list **up to 400** dates."*

Limite numérico, conferível por contagem.

**J-3 — nome de job em array**

> *"To enable job definitions in an array format, the `allowDuplicateJobNames`
> system setting **must be set to true** (the default value)."*

**D-1 — aninhamento em `WaitForEvents`**

> *"Note that nesting of parentheses within parentheses **is not supported**."*

**D-2 — `ReferencePath` e job explícito, com fronteira de versão**

> *"a sub-folder that contains the `ReferencePath` property **must not** contain
> any explicit job objects. This feature requires Control-M/Enterprise Manager
> version **9.0.21 or higher**."*

Esta é a que mais vale: carrega **defeito** e **fronteira de versão** na mesma
frase, e a fronteira cruza com a matriz do incremento 1 pelo mecanismo que a
`SF-CTM-001` já usa.

## 3. Objetivo

Cinco regras na área `SF-CTM`, cada uma com a citação que a sustenta. Nada além.

### Não-objetivos, com razão registrada

- **SLA.** Zero fonte. Vira **veto escrito** no cabeçalho do catálogo, no molde
  de `V-GR-1`/`V-GR-2` em `graph.yaml`: o que falta é a fonte nomear defeito, e
  a medida que destravaria é uma página que publique limite ou obrigação de SLA.
  Não é lacuna a preencher por inferência.
- **Julgar semântica de dependência.** "Este job espera evento que ninguém
  produz" é achado valioso e **sem fonte**: exigiria grafo do site inteiro, e a
  página não declara que evento órfão seja defeito.
- **Regra nova sobre versão.** `D-2` cruza com a matriz, mas pelo mecanismo que
  já existe. Nenhum kind derivado novo além do necessário.

## 4. Decisões de desenho

### D-1 — `J-1` julga a omissão, não só a presença

O `where` óbvio — `SpecificDates` presente **e** `WeekDays` presente — erra o
caso comum. A fonte diz que o default é `ALL`, então a condição correta é
`SpecificDates` presente **e** (`WeekDays` ausente **ou** `WeekDays != "NONE"`),
e o mesmo para `Months` e `MonthDays`.

`engine._where_matches` **rejeita caminho ausente** — é assim que o motor diz
"não sei". Então a ausência precisa virar **fact derivado** no extrator, no
molde de `tf.graphframes.jar`: o extrator decide uma vez e emite o kind já
decidido.

É a mesma dívida que a área `SF-GRAPH` pagou em 2026-08-31 (`absent` filtrado por
atributo), e a solução é a mesma.

### D-2 — a fronteira de versão de `D-2` vem da matriz

`9.0.21` é fronteira de **Enterprise Manager**, e a matriz do incremento 1 é do
**Automation API**. São produtos diferentes, e o incremento 1 mediu exatamente
essa distinção (a D-5 dele: `9.0.22.100` é número de produto, não de API).

Portanto: ou a matriz ganha o eixo de EM com fonte própria, ou a regra declara
`runtime_scope: {}` e cita a fronteira no `explanation` sem julgá-la. **Meça e
decida** — inventar eixo de EM sem fonte é o erro que a D-5 nomeou.

### D-3 — severidade por natureza

`J-1` e `D-1` produzem job que **não roda como o autor pensa**. `J-2` e `J-3` são
limite e configuração de sistema. `D-2` depende da versão. Severidade sai da
consequência que a fonte declara, não de gosto.

## 5. Testes e gates

- **`J-1` precisa de três fixtures**: `SpecificDates` com `WeekDays: "NONE"`
  (correto), `SpecificDates` com `WeekDays` ausente (**defeito por omissão** — o
  caso que a regra existe para pegar), e `SpecificDates` com `WeekDays: "ALL"`
  explícito.
- **`J-2`**: 400 datas passa, 401 dispara. A fronteira exata, não aproximada.
- **`D-2`**: fixture com `ReferencePath` e job explícito, e o par sem job.
- Golden positivo **e** negativo por regra; todo kind novo em algum golden.
- Nenhuma regra nova dispara sobre `fixtures/controlm/` existentes que o corpus
  declara corretas.
- Gates de sempre, incluindo `check_status_numbers.py --strict`.

## 6. Critérios de conclusão

- Cinco regras, cada uma com citação literal em `sources`.
- `J-1` pega a omissão, e há fixture que prova.
- SLA registrado como veto com a medida que o destravaria.
- A fronteira de EM de `D-2` ou tem fonte na matriz, ou está fora do
  `runtime_scope` com a razão escrita.

## 7. Nota de método

A pesquisa que produziu esta spec levou **4 minutos**. Uma tentativa anterior,
delegada com escopo aberto — cinco páginas candidatas, três eixos, liberdade de
trocar de mecanismo —, rodou **8 horas sem produzir nada** e foi morta.

Pergunta binária não precisa de exploração. Precisa de uma página e uma varredura
por padrão de defeito (`must`, `cannot`, `is not supported`, `up to \d+`). Fica
registrado porque o erro foi de quem escreveu o briefing, não de quem o executou.

## 8. Desvios

Cinco, medidos na execução de 2026-09-02. As cinco citações da seção 2 bateram
**literalmente** na fonte, e nenhuma regra precisou mudar de forma por causa
disso.

**D-a — o acesso foi mais fácil do que o registrado.** A seção 8.1 de
`knowledge/controlm/automation-api-matrix.md` registra que
`API_CodeRef_JobProperties` deu **403 em três tentativas** no incremento 2 e só
cedeu a um navegador de verdade. Nesta leitura, `curl` com UA de browser deu
**200 na primeira**, mesma URL, 423 239 bytes. O bloqueio é intermitente por URL,
como aquela seção já dizia; o que estava forte demais era a conclusão prática.
Quem for reler a fonte tenta `curl` antes de abrir navegador.

**D-b — `NONE` é publicado como LISTA, e isso mudou o código.** A seção 5 desta
spec pede a fixture com `WeekDays: "NONE"`, escalar. O exemplo da própria página
escreve `"WeekDays": ["NONE"], "Months": ["NONE"], "MonthDays": ["NONE"]` —
lista de um item. `_neutralized` aceita **as duas** formas, e a fixture usa a da
fonte. Um extrator que só aceitasse o escalar acusaria o artefato que a BMC
publica como correto. Pela mesma leitura, `["NONE", "MON"]` **não** anula: ele
declara segunda-feira ao lado da anulação, que é a combinação proibida.

**D-c — três fixtures de `J-1`, mas uma delas acumula dois papéis.** A seção 5
pede três (`NONE`, ausente, `ALL`) e a seção 5 também pede o par 400/401 de
`J-2`. `janela_no_teto_de_datas` é as duas coisas: as três opções anuladas com
`["NONE"]` **e** exatamente 400 datas. Acumular foi escolha, e o `proves` dela
declara os dois papéis — separá-las produziria duas fixtures cujo único
diferencial seria o comprimento de uma lista.

**D-d — o extrator não lia a forma de `WaitForEvents` em que a fonte demonstra o
defeito.** O docstring de `_dependency_facts` afirmava que a página publica as
duas formas dos blocos de evento, e o módulo só lia uma: a chave direta no job
(`"WaitForEvents": [{"Event": "e1"}]`). A forma que a página de fato usa nos
exemplos é um objeto nomeado com `"Type": "WaitForEvents"` e uma lista `Events`
dentro — e é nela que o exemplo `Wait2`, o dos parênteses, está escrito. Sem
lê-la, `D-1` não teria como ver o exemplo do próprio defeito. `_EVENT_OBJECT_TYPES`
e `_event_object_facts` fecham isso, e nenhum golden do incremento 2 mudou:
nenhuma fixture usava a forma que faltava.

**D-e — `J-3` precisou de uma chave de array que o extrator não percorria.** A
frase da fonte é sobre "job definitions in an array format", e o array de jobs é
`Jobs` — não `Folders` nem `SubFolders`, que são os dois que o incremento 2
percorria. `Jobs` entrou numa tupla **separada** (`_JOB_ARRAY_KEYS`) de
propósito: somá-la a `_ARRAY_STRUCTURE_KEYS` faria a sonda da capacidade
`folders_array_structure` disparar sobre um array de jobs, que a matriz não
data — exatamente o veto `V-CTM-4`.

### O que a spec previu e se confirmou sem ajuste

- A `D-1` da seção 4: `engine._where_matches` reprova caminho ausente, a decisão
  teve de sair do extrator, e o contrafactual está medido em teste
  (`test_sem_o_kind_derivado_a_fixture_de_omissao_fica_verde`, zero achados com
  a decisão desligada).
- A `D-2` da seção 4: a fronteira de EM ficou **fora** da matriz, com
  `runtime_scope: {}` e citação no `explanation`. A razão é mais forte do que a
  spec previa — a matriz já registrara exigência de EM **cinco** vezes, e nas
  cinco como prosa em `summary`.
- A `D-3`: severidade por natureza. `J-1` e `D-1` em P1; `J-2` e `D-2` em P2;
  `J-3` em P3, e o P3 vem do parêntese da própria fonte ("the default value"),
  que torna o achado uma dependência declarada e não um erro.
- O não-objetivo de SLA virou o veto `V-CTM-5`, com a medida que o destravaria.
