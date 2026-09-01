---
name: compare-releases
description: Use quando precisar saber o que muda de COMPONENTE entre dois runtimes antes de uma migração — "vou de emr-6.15.0 para emr-7.5.0, que versão de Spark e de Iceberg eu passo a ter", "o mesmo emr-7.7.0 no EC2 e no EKS é a mesma coisa?", "que versão de Python o Glue 5.1 publica" — e também quando alguém já escreveu um número de versão num plano de migração e ninguém conferiu de onde ele veio. Rode `sparkforge release describe` e `sparkforge release diff` em vez de ler a página da AWS no olho. Esta skill NÃO responde se algo quebra: diff de versão não é avaliação de compatibilidade, e essa pergunta é do MigrationAssessment (`sparkforge migrate glue` e `sparkforge migrate emr`, que hoje cobrem as quatro plataformas). Para julgar a migração de um job Glue degrau a degrau, a skill é `migrate-glue-6`.
subagent: true
agent: sf-runtime-specialist
---

# Comparar releases de runtime

## A fronteira, antes da capacidade

**Esta skill não responde "isso quebra".** Ela lê matriz de versão e devolve números com
fonte. Um diff que diga *"Iceberg foi de 1.6.1 para 1.7.1"* não afirma nada sobre o seu job:
não sabe que API você chama, não leu o seu código, não consultou regra nenhuma. A pergunta
"o que quebra" é do `MigrationAssessment` — `sparkforge migrate glue` e
`sparkforge migrate emr`, tool `sparkforge_migration_assess` com `platform` —, que julga o
caminho degrau a degrau contra o catálogo versionado (`SF-MIG`, `SF-SPARK4`, `SF-LF`). Ele
cobre as **quatro** plataformas desde 2026-09-01, e cobre com a cobertura DECLARADA: para
EMR o catálogo tem **zero** regras guardadas por versão de plataforma, e o campo
`coverage.statement` diz isso em voz alta, porque um assessment de EMR sem achado não pode
ser lido como "nada quebra". O que ele avalia num caminho de EMR é Spark (as cinco regras
guardadas por versão de Spark, alcançáveis porque a matriz publica o Spark de cada release)
e componente. Usar o diff no lugar do assessment continua sendo trocar julgamento por
aritmética de string de versão.

A ordem correta é: **primeiro** este verbo, para saber com que números você está lidando;
**depois** o assessment, e ler `coverage.statement` antes de concluir do silêncio dele.

**Duas das sete dimensões do §8.2 têm lastro; cinco saem recusadas por nome.** As quatro
matrizes de `knowledge/` sustentam **versão de componente por release**, e nada mais. O que
sai em `unresolved`, sempre, com a razão junto:

| Dimensão | Por que não | O que a destravaria |
|---|---|---|
| `default_changes` | é a que mais parece ter. `knowledge/glue/runtime-matrix.md` **discute** mudança de default em prosa ("AQE é default desde Spark 3.2"), chaveada por versão de **Spark** e não por release de plataforma, e **só para o Glue**. As outras três não têm nem a prosa | `knowledge/<plataforma>/default-changes.yaml` **chaveado por release**, para as quatro |
| `compatibility_changes` | mesma razão, com um agravante: o que existe estruturado sobre compatibilidade é o **catálogo de regras**, e consumi-lo aqui transformaria o diff de leitor em juiz | `knowledge/<plataforma>/default-changes.yaml` na mesma forma; enquanto isso, a avaliação é do assessment, não deste verbo |
| `deprecated` | exige release notes estruturadas por release; hoje as quatro áreas têm tabela de **componentes**, não changelog | `knowledge/<plataforma>/release-notes.yaml` com `deprecated: [{api, desde, substituto, source, retrieved}]` |
| `security_changes` | nenhuma das quatro páginas cita CVE | `knowledge/<plataforma>/security-bulletins.yaml` com fonte oficial em `knowledge/sources.lock.json` |
| `performance_changes` | não é lacuna de documento: mudança de desempenho é diferença de tempo e de recurso no **mesmo** workload | dois conjuntos de facts de event log e o verbo `benchmark`, que já existe para essa pergunta |

Emitir lista vazia para qualquer uma delas seria pior que recusar: o operador leria "nenhum
default mudou".

## O achado que motiva o verbo, e ele é medido

**O mesmo rótulo publica versões diferentes em plataformas diferentes.** `emr-7.7.0` publica
Iceberg `1.7.1-amzn-0` no EMR on EC2 e `1.6.1-amzn-2` no EMR on EKS — **minor diferente**, não
patch. E Spark `3.5.3-amzn-1` contra `3.5.3-amzn-0`.

A consequência não é estética. Toda regra `SF-ICE-*` com faixa de versão muda de
**aplicabilidade** entre os dois: uma regra cujo escopo começa em Iceberg 1.7 vale no EC2 e é
pulada no EKS, **com o mesmo `releaseLabel` escrito no job**. Quem migra de EC2 para EKS
"mantendo a release" está trocando de minor de Iceberg sem que nada no rótulo diga isso.

Por isso o diff carrega o **eixo** e o declara: `platform`, `release`, ou os dois.

## Procedimento

### 1. Descreva cada lado, e leia o `unresolved` antes dos números

```bash
sparkforge release describe --platform emr_ec2 --release 7.7.0
sparkforge release describe --platform emr_eks --release emr-7.7.0
```

Tool MCP equivalente: `sparkforge_release_describe`, com `platform` e `release`.

As quatro plataformas são `glue`, `emr_ec2`, `emr_serverless` e `emr_eks`. O rótulo entra com
ou sem o prefixo `emr-` e sai numa grafia só — a chave que indexa a matriz. Duas grafias na
saída dariam dois descritores para a mesma release, e o diff deixaria de ser determinístico.

**Componente que a fonte não publica sai em `unresolved` nomeado, nunca vazio**, e
`unresolved_detail` diz de qual das duas recusas se trata. Elas destravam com medidas
diferentes, e confundi-las faz o operador procurar no lugar errado:

| `kind` | O que é | Exemplo medido | O que destrava |
|---|---|---|---|
| `platform_source_does_not_publish` | a fonte daquela plataforma não publica o componente em release **nenhuma** | `hadoop` no EMR on EKS: 0 de 34 páginas | uma **fonte** nova |
| `release_cell_absent` | a fonte publica o eixo, e a célula **daquela** release não está lá | `iceberg` em `emr-6.4.0`; `java` em Glue 5.1, que as outras quatro releases de Glue têm | uma **leitura** daquela página |

**Nenhum valor é herdado de outra plataforma.** Não há fallback, não há "se faltar, pega do
EC2" — é exatamente o que a divergência acima proíbe.

### 2. Rode o diff, e leia o `axis` antes do `changed`

```bash
sparkforge release diff \
  --left-platform emr_ec2 --left-release 7.7.0 \
  --right-platform emr_eks --right-release 7.7.0
```

Tool MCP equivalente: `sparkforge_release_diff`, com `left_platform`, `left_release`,
`right_platform` e `right_release`.

**Quatro argumentos, dois pares `(plataforma, release)`.** Não é `--platform` mais duas
releases: com uma plataforma só, a pergunta que motiva esta skill — o mesmo rótulo em duas
plataformas — seria inexprimível. E não é `--before`/`--after` nem `--from`/`--to` como nos
verbos irmãos, porque esses nomes prometem que o eixo é o tempo. Aqui o eixo é **resultado**:
`axis` sai calculado das dimensões que efetivamente variam.

`left` é de onde o operador sai, `right` é para onde ele vai; `changed` lê "de `from` para
`to`" nessa direção.

| `axis` | O que a saída significa |
|---|---|
| `["release"]` | mesma plataforma, releases diferentes. Toda linha de `changed` é atribuível ao avanço da release |
| `["platform"]` | mesmo rótulo, plataformas diferentes. Toda linha de `changed` é atribuível à plataforma — e é o caso do achado acima |
| `["platform", "release"]` | os **dois** variam. `unresolved.attribution` acende: **nenhuma** linha de `changed` pode ser creditada a um dos dois isoladamente. Os números dos dois lados são fact e estão lá; a atribuição é que não tem base. Destrava com dois diffs de um eixo cada |
| `[]` | nada varia, e nada é atribuível a nada |

### 3. Leve o resultado para o verbo que julga

Onde ele existe — Glue —, a pergunta seguinte é do assessment:

```bash
sparkforge migrate glue ./meu-job --from 4.0 --to 6.0
```

Para EMR não existe equivalente hoje. O que existe é `sparkforge runtime detect`, que diz em
que runtime um artefato **rodou** — outra pergunta, e a fonte dela é o artefato, não a
matriz. O diff alimenta o rótulo que você declara ao julgar; ele não substitui a extração, e
esta skill não chama o motor de regras.

## Referência rápida — o que cada campo da saída afirma

| Campo | O que ele mede | O que ele **não** mede |
|---|---|---|
| `components` | a célula da matriz daquela release, com `sources` e `retrieved` | o que roda de fato no cluster: imagem de container, `spark.conf.set` no código e o nível de otimização que o EMR escolhe pela release não estão em tabela nenhuma |
| `unresolved` / `unresolved_detail` | os componentes **nomeados** que aquela release não resolve, e a medida que destrava cada um | não é "o componente não existe" — é "a fonte não publica" |
| `axis` | as dimensões que **efetivamente** variam entre os dois lados | não é entrada, e não é escolha do operador |
| `changed` | os componentes que os dois lados resolvem com valores **diferentes** | não diz se a diferença quebra algo |
| `added` / `removed` | a **presença da célula** por release | não é "a plataforma passou a embarcar". `python` aparecer em `emr-7.0.0` e não em `emr-6.15.0` mede que a AWS passou a reafirmar o default do PySpark por release na série 7.x, não que a 6.15.0 não tivesse Python |
| `unresolved["component.<nome>"]` | componente que **uma das duas** plataformas não publica como eixo | nunca vira `added` nem `removed`: dizer "o EKS removeu o Hadoop" inverteria a causa |
| `unresolved["attribution"]` | os dois eixos variam ao mesmo tempo, e a atribuição por nome está recusada | — |
| as cinco dimensões sem lastro | a recusa, com a medida que a destravaria | — |

`sparkforge rules lookup` continua sendo a lista autoritativa de limiar e escopo de versão.
Esta skill não consulta o catálogo, e nenhum `Finding` nasce dela.

## Quando NÃO usar

- A pergunta é **"o que quebra se eu migrar"**: isso é `migrate-glue-6` e
  `sparkforge migrate glue` (Glue), `sparkforge migrate emr --platform ...` (as três de EMR),
  ou `spark4-compatibility` para a fronteira do Spark 4.
  Diff de versão não é avaliação de compatibilidade.
- A pergunta é **em que runtime este job rodou**: `sparkforge runtime detect` sobre facts já
  extraídos. O diff não lê artefato nenhum do operador.
- A pergunta é **ficou mais rápido depois de mudar**: isso é medida, não documento —
  `benchmark-pyspark-job` sobre dois conjuntos de facts de event log.
- A pergunta é sobre **subir o `format-version` de uma tabela Iceberg**: `iceberg-v3-readiness`
  e `sparkforge iceberg assess-upgrade`, que cruzam o inventário de consumidores com a matriz
  de suporte de feature. Versão de biblioteca Iceberg não é versão de spec da tabela.
- A pergunta é sobre a **configuração** do job — worker, escala, log, segredo: as skills são
  `review-glue-terraform`, `review-emr-cluster` e `review-emr-eks`.
- Você quer saber quais **defaults** mudaram entre duas versões: hoje isso sai recusado, e a
  recusa é a resposta correta. Ver a tabela da fronteira.

## Red flags

- Escrever que uma migração é segura porque o diff saiu pequeno. O diff não olhou o seu
  código, e um único minor de Iceberg pode mover a aplicabilidade de uma regra inteira.
- Ler `unresolved` vazio como "não mudou nada". As cinco dimensões sem lastro saem **sempre**;
  `unresolved` vazio seria o defeito, não o bom resultado.
- Atribuir uma linha de `changed` à release quando `axis` traz `["platform", "release"]`. É
  exatamente a inversão de causa que `unresolved.attribution` existe para impedir.
- Ler `removed` como "a plataforma deixou de embarcar o componente". Ele mede ausência de
  **célula**, e componente que uma das duas plataformas não publica como eixo nem chega lá.
- Assumir que o mesmo `releaseLabel` significa o mesmo runtime em plataformas diferentes.
  `emr-7.7.0` publica Iceberg `1.7.1-amzn-0` no EC2 e `1.6.1-amzn-2` no EKS.
- Copiar o valor de uma plataforma para preencher a lacuna de outra. É a herança que o
  descritor recusa por construção, e a divergência acima é a razão medida.
- Citar um número de versão sem `sources` e `retrieved`. Os dois vêm no `components` de cada
  lado; um número de memória num plano de migração é o defeito que este verbo existe para
  fechar.
- Tratar a versão publicada como a versão que rodou. A matriz descreve o que a AWS publica
  para a release; imagem de container em tag móvel e `spark.conf.set` no código ficam fora.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id` ou sem a fonte que o descritor traz;
`rules_lookup` em vez de memória para limiar e versão; `validate_output` antes de apresentar;
reporte `unresolved` — aqui ele é metade da resposta, e inclui as cinco dimensões que este
verbo recusa por nome. Feche assinando com `sparkforge report sign` e conferindo com
`sparkforge report verify`.

Manutenção destrutiva você **não executa**, e nesta área ela não nasce do verbo: `describe` e
`diff` só leem `knowledge/` e não tocam dado, tabela nem infraestrutura. Ela nasce do que vem
**depois** — trocar a release de um job, mudar de plataforma, subir o `format-version` de uma
tabela. Nada disso você executa, e a confirmação de escopo e retenção **sobe** a quem pode ser
perguntado: o agente pai que despachou, ou o operador na sessão.

Esta skill é **despachável** (`subagent: true` no espelho `.agents/skills/`), e
`ask_user_question` é **sempre negado** a um subagente. Devolva os números com a fonte, o eixo
declarado e a lista de recusas; a decisão de migrar é de quem pode ser perguntado.
