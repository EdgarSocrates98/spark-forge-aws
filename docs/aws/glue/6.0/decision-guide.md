# Guia de decisão — migrar para o Glue 6.0?

Este guia responde oito perguntas, nesta ordem. A ordem importa: as três primeiras decidem
**se** existe migração a fazer, e as cinco últimas só valem depois de a resposta ser sim.

Duas regras valem em todas elas.

> **Não escolha uma versão porque é a mais nova.** "Ficar no 5.1" é uma resposta legítima
> deste guia, e há condições em que é a resposta certa. Elas estão na pergunta 6.

> **Redução de preço não é ganho de performance.** A AWS anunciou redução de preço no Glue
> 6.0. **Este repositório não mediu performance do Glue 6.0** — não há baseline, não há
> execução comparada, não há número. Tratar uma coisa como se implicasse a outra é o erro
> mais fácil de cometer neste assunto, e a pergunta 2 o trata separadamente.

---

## 1. Devo migrar?

A pergunta certa não é "existe uma versão mais nova". É **o que força o movimento**. Comece
pelo que empurra, não pelo que atrai:

| O que empurra | Peso |
|---|---|
| a versão atual saiu, ou está saindo, de suporte | **decisivo** — o prazo não é negociável |
| existe um defeito corrigido que morde este job hoje | forte, se o defeito for identificado por nome |
| existe uma capacidade que o job **precisa** e só o runtime novo declara | forte, se a capacidade for verificada na engine — ver a pergunta 6 |
| a fatura cairia | real, mas é fatura, não performance — ver a pergunta 2 |
| é a versão mais nova | **nenhum** |

Se nada da tabela empurra, a resposta é: **não migre agora**. Migração é risco assumido em
troca de alguma coisa; sem a alguma coisa, sobra o risco.

Checagem automatizada: nenhuma. Nada neste repositório sabe a data de fim de suporte de um
runtime nem lê a sua fatura. Esta pergunta é **manual**, e dizer isso é informação — não
lacuna a esconder.

## 2. O que eu ganho?

Três respostas diferentes, que costumam ser confundidas numa só.

**Preço.** A AWS anunciou redução de preço para o Glue 6.0, e a fonte desse anúncio está
vigiada em `knowledge/sources.lock.json`, citada pela linha do Glue 6.0 em
`knowledge/glue/runtime-matrix.yaml`. É um fato de **cobrança**: a mesma quantidade de
trabalho, faturada por um preço diferente. Ele não diz nada sobre quanto trabalho o seu job
vai gastar.

**Performance.** **Não medida aqui.** Este repositório não tem baseline de Glue 6.0, não tem
execução comparada e não tem benchmark parametrizado por versão de runtime. Se você precisa
de um número de performance, ele vem de rodar o seu job nos dois runtimes com a mesma
entrada — e o comparador de execuções existe para isso, mas a montagem é sua. Qualquer
afirmação de performance que apareça sem essa execução é hipótese, e deve ser escrita como
hipótese.

**Capacidade.** O que o Glue 6.0 declara suportar e o que já existia antes estão separados em
[`iceberg.md`](iceberg.md) e no conhecimento que ele aponta. Um ponto que muda decisão:
**deletion vectors e row lineage já vinham no runtime anterior**. Um plano que justifique o
salto por eles está pagando uma migração por algo que já tinha.

Checagem automatizada: nenhuma para preço, nenhuma para performance. A separação entre
feature da spec e suporte da engine é consultável como dado —
`knowledge/storage/iceberg-feature-support.yaml`, carregado por
`sparkforge/storage/feature_support.py`.

## 3. O que eu arrisco?

Estes são os riscos que o motor **julga sozinho**, com a regra que os acusa:

| Risco | Regra |
|---|---|
| `cast` sem guarda sob ANSI mode ligado por padrão | `SF-MIG-003` |
| JAR compilado contra Scala anterior ao 2.13 no classpath | `SF-SPARK4-004` (**P0** — falha certa, em runtime) |
| configuração do Spark que mudou de nome, ainda escrita com o nome antigo | `SF-SPARK4-001` (silêncio: a chave não é lida) |
| API de pandas-on-Spark removida ainda chamada | `SF-SPARK4-002` |
| PyArrow pinado abaixo do piso | `SF-SPARK4-003` |
| import de SDK que o runtime não carrega mais | `SF-MIG-001` |
| configuração exclusiva de EMRFS sobrevivendo em runtime S3A | `SF-MIG-002` |
| tabela em formato v3 com Athena entre os consumidores | `SF-ENV-002` |
| JAR adicional num job com FGAC | `SF-LF-001` |
| FGAC num job de streaming | `SF-LF-002` |

Como rodar: extraia os facts do job e da infraestrutura, e chame a avaliação de migração com
o par origem → alvo. Ela expande o par em degraus derivados da matriz de runtime e julga cada
degrau com o runtime daquele degrau — ver [`testing.md`](testing.md).

E estes são os riscos que **nenhuma regra acusa**, porque não há sinal no código para
observar. São checagem **manual**, e entram no plano de regressão:

- as mudanças de comportamento do Spark 4 sem sinal no código — ver [`spark4.md`](spark4.md);
- uso de VARIANT, transform multi-argumento ou tipo novo da v3 sob DynamicFrame — os facts não
  existem, ver [`known-unknowns.md`](known-unknowns.md);
- qualquer consumidor da tabela que não seja o Athena: nada cruza feature contra consumidor.

## 4. O que é pré-requisito?

Ordenado por quanto tempo leva para descobrir que você está bloqueado:

1. **JAR customizado precisa ser recompilado contra Scala 2.13.** Se o JAR é de terceiro e não
   existe build para 2.13, **não há conserto local**: sem o fonte não dá para recompilar, e a
   migração está *bloqueada*, não atrasada. Confirmar isso com o mantenedor é pré-requisito do
   plano, não tarefa dentro dele.
2. **Pins de dependência Python precisam satisfazer os pisos da versão de Spark alvo.** O piso
   está em `knowledge/spark/spark4-migration.md`; a regra que acusa um deles é
   `SF-SPARK4-003`. Wheel binária e risco de ABI **não** são julgados — checagem manual.
3. **Se o job usa FGAC**, as incompatibilidades declaradas precisam ser resolvidas antes, não
   durante — ver [`lakeformation.md`](lakeformation.md).
4. **Se você pretende escrever no formato v3**, todo consumidor da tabela precisa ser
   verificado um a um. A matriz de compatibilidade responde onde há fonte e responde
   `UNKNOWN` onde não há; `UNKNOWN` **não** é permissão.
5. **Baseline de correção antes de qualquer comparação de performance.** Contagem, schema,
   chaves, agregados e regras de negócio. O motor tem validação funcional de saída para isso,
   e o gate de dados nasce bloqueado enquanto ela não existir.

## 5. Quando esperar?

Esperar é uma decisão, não a ausência de uma. Vale esperar quando:

- **um pré-requisito bloqueado não tem dono.** Um JAR de terceiro sem build para 2.13 não
  melhora com o tempo por si só — mas migrar sem resolvê-lo troca uma espera por uma falha em
  produção, na primeira vez que aquele caminho de código executar.
- **o único ganho é preço e o job é pequeno.** O risco de migração é aproximadamente fixo; a
  economia é proporcional ao gasto. Abaixo de certo gasto, a conta não fecha — e o número
  dessa conta é seu, não deste repositório.
- **um consumidor que você não controla lê a tabela.** Nesse caso o que espera não é a
  migração do runtime: é a decisão de formato de tabela, que é separável dela.
- **você precisa de uma capacidade que a engine declara não suportar.** Aqui esperar **não**
  resolve: transform multi-argumento está na spec v3 e a AWS declara que a engine não o
  suporta. É limitação da engine, não fila de release. Migrar não entrega e adiar não muda.

## 6. Glue 5.1 ou Glue 6.0?

**Fique no 5.1 quando:**

- o que você quer são **deletion vectors ou row lineage** — o 5.1 já os entrega, e migrar por
  eles é pagar por algo que você já tem;
- você tem **JAR de Scala 2.12 que não pode ser recompilado** — o 6.0 está bloqueado para
  esse job, e o 5.1 é onde ele continua rodando;
- o job usa **DynamicFrame** e você contava com os tipos novos da v3 — eles funcionam apenas
  com Spark DataFrames, então o salto não entrega o que você foi buscar;
- **nada da pergunta 1 empurra.** Estabilidade tem valor, e não é preciso justificá-la.

**Vá para o 6.0 quando:**

- você precisa de algo que **só ele declara** — VARIANT com shredding, timestamp de precisão
  nanossegundo, tipos geoespaciais — e você verificou a limitação declarada que acompanha cada
  um (por exemplo: FGAC não é suportado com colunas VARIANT);
- o 5.1 saiu, ou está saindo, de suporte;
- os pré-requisitos da pergunta 4 estão todos resolvidos e o ganho da pergunta 2 é um dos que
  se sustentam.

**Em nenhum caso escolha pela recência.** As duas versões atravessam fronteiras diferentes:
consultar `knowledge/glue/runtime-matrix.yaml` diz quais componentes mudam em cada degrau, e a
expansão do caminho de migração diz em qual degrau cada risco nasce. É essa informação que
responde se um salto intermediário resolveria parte do problema — não a data de lançamento.

Nota sobre formato de tabela: escrever v3 é uma decisão **separada** de qual runtime você
roda. Para compatibilidade entre engines, v2 — e essa escolha continua sua depois de migrar.

## 7. Como testar?

Nesta ordem, e a ordem é a parte que costuma ser pulada:

1. **Correção antes de performance.** Valide contagem, schema, chaves, agregados e regras de
   negócio da saída. Os gates de dados, performance e custo nascem `BLOCKED` com o motivo
   escrito e **nunca** `PASS` por omissão — nenhuma recomendação favorável sai de evidência
   ausente.
2. **Análise estática do par.** A avaliação de migração julga cada degrau com o runtime
   daquele degrau, e o relatório traz três visões com cardinalidades diferentes: os findings,
   os findings por degrau, e o relatório deduplicado. As três respondem perguntas diferentes.
3. **Plano de regressão para o que a análise não vê.** As mudanças de comportamento sem sinal
   no código, listadas em [`spark4.md`](spark4.md), só aparecem executando. Um smoke test que
   não exercite o caminho de código que usa o JAR customizado **passa** com um JAR
   incompatível no classpath.
4. **Comparação de execuções, por último.** Mesma entrada, dois runtimes. É montagem manual —
   ver [`known-unknowns.md`](known-unknowns.md).

As camadas de prova do próprio repositório, e qual gate rodar para cada tipo de mudança, estão
em [`testing.md`](testing.md) e em
[`../../../gates-por-mudanca.md`](../../../gates-por-mudanca.md).

## 8. Como reverter?

Separe o que volta do que não volta. Essa separação é a resposta.

**Volta com um redeploy:** a versão do runtime. É atributo do job — no Terraform, o atributo
que a regra `SF-MIG-004` vigia. Voltar é aplicar o valor anterior. Guarde o estado anterior do
Terraform: sem ele, a regra que acusa migração de runtime não tem o que comparar, e você
também não.

**Não volta:**

- **tabela escrita em formato v3.** Baixar a versão do runtime não rebaixa o formato da
  tabela, e uma engine que não lê v3 continua sem ler depois do rollback. Esta é a decisão
  irreversível do conjunto — trate-a como decisão separada, tomada depois, e não como efeito
  colateral da migração.
- **dado escrito sob o runtime novo.** Comportamento que mudou sem sinal no código já produziu
  o que produziu; o rollback muda o que vem depois, não o que já está gravado.
- **estado de bookmark e de checkpoint** avançado durante as execuções no runtime novo.

Consequência prática para o plano: faça a migração de **runtime** primeiro, isolada, e só
depois considere mudar formato de tabela. Juntar as duas numa janela só troca uma reversão
barata por uma irreversível.
