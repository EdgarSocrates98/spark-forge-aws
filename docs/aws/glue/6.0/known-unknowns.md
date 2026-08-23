# O que o SparkForge não sabe sobre Glue 6.0

Este é o documento mais importante desta pasta. Os outros dizem o que a ferramenta faz; este
diz onde ela **cala**, e o que esse silêncio significa.

A regra que o organiza: silêncio da ferramenta **nunca** é atestado de ausência de risco.
Nenhum finding sobre um assunto listado abaixo significa que ninguém olhou — não que está
tudo bem.

Está agrupado por **consequência para quem usa**, não pela seção do prompt que originou cada
lacuna. As fontes de cada item são as linhas `NÃO EXISTE` e `EXISTE PARCIAL` de
[`../../../harness/GLUE6-GAP.md`](../../../harness/GLUE6-GAP.md), as notas "a verificar" dos
documentos de `knowledge/`, as células `UNKNOWN` da matriz de features e os pontos cegos do
extrator registrados em [`../../../gates-por-mudanca.md`](../../../gates-por-mudanca.md).

---

## 1. Perguntas que a ferramenta não responde sozinha

Você vai querer perguntar estas coisas. A resposta hoje é trabalho manual.

- **"Posso subir esta tabela de v2 para v3?"** Não existe avaliação de upgrade de formato de
  tabela. O diagnóstico devolve o `format_version` corrente; prontidão para v3 não faz parte
  do relatório.
- **"Algum consumidor desta tabela quebra se eu migrar?"** *Respondida em parte pela fase H3.*
  O inventário de consumidores emite `env.consumer`, e `sparkforge iceberg assess-upgrade`
  cruza esse inventário contra a matriz de suporte antes de recomendar um upgrade de formato;
  o eixo `consumidor` do assessment bloqueia quando um consumidor declarado não suporta o
  formato-alvo. **O que continua sem resposta** é o cruzamento para as *outras* features de
  Iceberg: a armadilha judicável segue sendo a de formato v3 contra Athena (`SF-ENV-002`).
- **"Minhas dependências Python aguentam?"** O observador de dependência declarada existe, e
  há regra sobre um piso específico. *A auditoria como comando chegou na fase H4*:
  `sparkforge glue dependency-audit --glue <versão> <path>`. **O que continua sem existir** é
  julgamento de **wheel binária, extensão nativa ou risco de ABI** — o comando audita o que
  está declarado, não o que está compilado dentro do artefato.
- **"Este JAR carrega no runtime novo?"** Existe a regra que acusa o sufixo de Scala no nome
  do artefato. Não existe varredura de compatibilidade binária que abra o JAR, e não existe
  vocabulário de veredito próprio ("recompilar", "bloqueado") — o resultado é um finding
  comum, com severidade.
- **"Quanto isto vai custar, e quanto mais rápido vai ficar?"** *Respondida em parte pelas
  fases H5 e H6.* `knowledge/glue/pricing.yaml` registra preço **com data de coleta**, e
  `bench.runtime_pair` parametriza a comparação por par de runtime. **O que continua sem
  existir** é o eixo de **região**: a fonte oficial usada não diferencia por região, e o
  arquivo grava `region: UNQUALIFIED` em vez de fingir um número regional. Custo por região
  segue não respondível. Ver a seção 6.

## 2. Coisas que a ferramenta não consegue **ver** no seu job

Não é que a regra esteja faltando; é que o **fact** que a alimentaria não existe. Regra sem
fact é regra que nunca dispara ou que dispara por chute, e criá-la seria pior do que não
tê-la.

| O que fica invisível | Observação que falta |
|---|---|
| uso de coluna VARIANT numa tabela | tipo de coluna no schema Iceberg, com `variant` distinguível |
| transform multi-argumento em partition spec ou sort order | aridade do transform; o fact de partition spec não carrega os argumentos |
| tipo novo da v3 alcançado por DynamicFrame | marcador de uso de DynamicFrame correlacionável com o schema escrito |
| pipeline montado no Visual ETL do Glue Studio | procedência do job (Studio contra script) |

Consequência prática: as três armadilhas que a AWS declara para a v3 — VARIANT sob FGAC,
transform multi-argumento, tipo novo sob DynamicFrame — **são conhecimento, não motor**. Elas
estão escritas em `knowledge/storage/iceberg-v3.md` para quem lê; nenhuma delas gera finding.

## 3. Compatibilidade que ninguém publicou

A matriz de feature contra engine é honesta ao custo de ser majoritariamente vazia: a maioria
das células é `UNKNOWN`, e apenas uma engine tem documentação oficial enumerando feature de
v3 por nome.

O que isso significa quando você consulta a matriz:

- **`UNKNOWN` não é "não suporta".** É "não há fonte". Tratar um `UNKNOWN` como bloqueio
  inventa um impedimento; tratá-lo como suporte inventa uma garantia. As duas leituras estão
  erradas, e a matriz recusa fazer qualquer uma delas por você.
- **Não há inferência entre engines.** Saber que a biblioteca Iceberg suporta uma feature não
  preenche a célula de nenhuma engine, e há teste que falha quando alguém tenta.
- **Uma afirmação sobre o *formato* da tabela não se estende às features individuais.** O que
  se sabe e não sustenta célula mora no campo de nota da engine, dentro do YAML.

## 4. O que só aparece em execução

Nenhuma destas produz finding, e nenhuma delas é detectável por análise estática. Elas são
entrada para o **plano de regressão**.

- **Mudanças de comportamento do Spark 4 sem sinal no código** — política de parsing de tempo
  e precedência de CTE, codec padrão do ORC, teto de bytes de partição única, cast de
  timestamp com overflow fora do ANSI, Storage-Partitioned Join ligado por padrão. Ver a
  seção 5 de `knowledge/spark/spark4-migration.md`.
- **Falha de JAR de Scala incompatível** — aparece em runtime, na primeira vez que aquele
  caminho de código executa, possivelmente depois de minutos de processamento, e passa em
  qualquer smoke test que não exercite exatamente aquela chamada.
- **Custo de leitura, pruning e efeito de shredding sobre o plano em colunas VARIANT** — não
  foram lidos na coleta que produziu o conhecimento de Iceberg. Marcado como a verificar na
  própria fonte.
- **Alcance exato do suporte inicial a `MERGE INTO` com evolução de schema no Spark 4.1** —
  "inicial" é a palavra da fonte; o alcance não foi lido. A verificar.

## 5. Onde os extratores são cegos

Cegueira medida, com o sintoma sempre igual: **silêncio**.

- **`non_overridable_arguments` no Terraform é ignorado inteiro.** Um `aws_glue_job` que
  forneça argumento por esse bloco é invisível para toda regra que lê `default_arguments` —
  o que inclui a regra de JAR sob FGAC e as de infraestrutura de Glue.
- **Valor com interpolação vira `tf.unresolved`.** Uma regra cuja condição é conjunção plana
  fica calada quando o atributo que ela procura foi interpolado.
- **O fact de JAR observa todo `.jar` da árvore**, inclusive um que seja recurso de teste
  fora do classpath do job. Separar exigiria um fact sobre `--extra-jars`, que não existe.
- **JAR cujo nome não codifica a versão de Scala não é acusado.** Pode ser Java puro — mas
  também pode ser um artefato de Scala renomeado, e nada distingue os dois casos.
- **A regra que acusa mudança de `glue_version` exige um diff.** Um `.tf` sozinho não tem
  estado anterior: o arquivo diz qual é a versão e nada nele diz que antes era outra. Uma
  migração real fica invisível para a regra que existe justamente para acusá-la, quando a
  entrada é um único estado.
- **A avaliação recebe uma lista de facts já extraída** e não sabe compor as fontes.
  Terraform, JAR, topologia de Lake Formation e inventário de consumidores existem como
  extratores isolados; ligá-los numa entrada única é trabalho de quem chama.

## 6. Custo, performance e correção

- **Não existe conhecimento de preço com data e região.** Qualquer afirmação sobre economia
  precisa vir da calculadora da AWS e da sua fatura, não desta ferramenta.
- **Não existe benchmark parametrizado por versão de runtime.** O comparador de execuções
  existe e usa métricas reais, mas nada o parametriza por versão — comparar dois runtimes é
  montagem manual.
- **Este repositório não mediu performance do Glue 6.0.** Não há baseline, não há execução
  comparada, não há número. Ver a seção *O que eu ganho?* do
  [`decision-guide.md`](decision-guide.md), que trata isso explicitamente.
- **Os gates de dados, performance e custo nascem `BLOCKED`**, com o motivo escrito, e nunca
  `PASS` por omissão. Nenhuma recomendação favorável sai de evidência ausente. Isso é o
  comportamento correto, e também significa que a ferramenta vai bloquear até você trazer a
  medição.

## 7. Conhecimento sobre o próprio conhecimento

- **TTL por domínio não existe.** Há cálculo de staleness de pacote de conhecimento e
  reconciliação de lock, mas não um prazo de validade configurável por domínio. Por isso os
  status `STALE` e `UNVERIFIED` são recusados pelo carregador da matriz: os dois afirmam
  frescor, e frescor é o que não se sabe medir aqui.
- **A matriz publicada não tem componente em disputa.** O mecanismo de conflito entre fontes
  existe e é testado; a divergência que motivou construí-lo foi procurada e **não se
  reproduziu**. O mecanismo está lá para o dia em que houver uma de verdade.
- **Não existe conhecimento de erro para este domínio.** `knowledge/errors/` tem
  subdiretórios por domínio, mas nenhum para migração de runtime: a mensagem de erro que você
  vai receber em execução não está catalogada aqui.

## 8. Estrutura que o prompt de origem pedia e que não existe

Registrada para que ninguém a procure achando que é uma pasta perdida:

- **Grafo de mudança de runtime por componente** — o caminho de migração é uma cadeia linear
  de versões de Glue. Não há nó por componente (Spark, Python, Java, Scala, Iceberg,
  conector) com aresta de origem, destino, severidade e ruptura, consultável sem LLM.
- **Área `SF-ICE-V3`** — não existe, e depende dos facts da seção 2.
- **Matriz de Lake Formation por operação** (`SELECT`/`INSERT`/`MERGE`/`ALTER`) cruzada com
  conta — a fonte enumera limitação, não operação.
- **Separação nominal entre control plane e data plane** — o grafo de permissão modela aresta
  com origem e destino; a distinção entre permissão de catálogo, Lake Formation, IAM, S3 e
  KMS não está declarada como tipo.
- **Registro de capacidade indexado por capacidade** — o registro existente indexa por tipo.
- **Skills de Glue 6 com disclosure progressivo** — a infraestrutura de disclosure existe;
  nenhuma skill atual é de Glue 6. A decisão de não criá-las, e o motivo, estão no ADR
  [`../../../vnext/adrs/ADR-009-glue-6-spark-4-iceberg-v3.md`](../../../vnext/adrs/ADR-009-glue-6-spark-4-iceberg-v3.md).
- **Tools MCP dedicadas** a varredura de Spark 4 e a compatibilidade de JAR — a composição de
  ferramentas existentes entrega o mesmo resultado, e uma superfície nova sem capacidade nova
  é etiqueta.
- **Agente especialista em migração de Glue** — o especialista de runtime existente declara
  compatibilidade entre versões; não há um agente dedicado, e a orientação do mapa é evoluir
  o existente antes de criar outro.
- **Escalonamento para agente quando o fato determinístico não basta** — a avaliação é
  determinística de ponta a ponta e não chama agente nenhum. O caminho inverso não existe.

## 9. O que não vigia esta pasta

`docs/aws/` **não está em `audited_roots()`** do gate de lastro. Diferente de `docs/vnext/` e
`docs/harness/`, nada aqui é auditado alegação por alegação, e nenhum teste cobra a
existência ou o conteúdo destes documentos.

É uma lacuna real, e está escrita aqui em vez de escondida. A mitigação escolhida foi
estrutural: **estes documentos apontam para a fonte em vez de copiá-la**. Um ponteiro
envelhece junto com o que ele aponta; um número copiado apodrece sozinho.
