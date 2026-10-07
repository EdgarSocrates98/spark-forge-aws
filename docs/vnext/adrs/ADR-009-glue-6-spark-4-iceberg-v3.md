# ADR-009: Suporte a AWS Glue 6.0, Spark 4.1 e Iceberg v3

## Status
Accepted

## Context
O runtime mais novo do AWS Glue troca, de uma vez, a versão do Apache Spark, do Python, do
Scala e da biblioteca Iceberg, e passa a declarar suporte à spec v3 de tabela. Suportar isso
aqui não é uma tarefa de conteúdo: é uma sequência de escolhas sobre **onde cada afirmação
mora** e **o que a ferramenta tem direito de afirmar**.

Antes desta sequência, versão de runtime vivia em dois lugares sem nada que forçasse os dois
a concordarem, a única fronteira do Spark novo codificada era o ANSI mode, e não havia
representação para "duas fontes oficiais discordam". O prompt de origem pedia muito mais do
que isso — e pedia também dezenas de skills e várias tools novas, cuja utilidade dependia de
conhecimento que ainda não existia como dado.

O mapa componente a componente do que já existia contra o que o prompt pediria está em
`docs/harness/GLUE6-GAP.md`, e é a base factual das decisões abaixo.

## Decision

### Conhecimento externo entra como dado versionado com fonte, nunca como prosa
Versão de serviço, feature de spec e suporte de engine são fatos de terceiros: mudam por
decisão de quem os publica, não deste repositório. Entram em YAML com `source`, `source_type`
e `retrieved`, carregados por módulo próprio, e toda URL citada precisa estar no lock de
fontes. Prosa continua existindo em `knowledge/*.md` para leitura humana, mas prosa não é
consultável nem gateada — o que julga é o dado.

### Guarda por Spark quando a fronteira é do Apache, por Glue quando é do empacotamento
Uma afirmação sobre o que o Apache mudou vale igual em qualquer distribuição que empacote
aquela versão, e amarrá-la a um runtime de Glue prenderia a afirmação a um empacotamento que
não a produziu. A recíproca também vale: a fronteira que só existe porque a AWS empacotou
daquele jeito é guardada por Glue. Isso é cobrado por teste, não deixado a critério de quem
escreve a próxima regra.

### Célula de compatibilidade sem evidência é `UNKNOWN`, e o carregador recusa afirmação sem fonte
A matriz de feature contra engine tem uma célula por par, e cada célula afirmativa carrega a
própria evidência. Célula que afirma suporte sem fonte derruba a matriz inteira na carga —
regra em código, não advertência em prosa. `UNKNOWN` é o único status que dispensa fonte, e
precisa existir como célula escrita: célula ausente diz "ninguém perguntou", célula `UNKNOWN`
diz "perguntamos e não há fonte". A consequência aceita é que a maioria das células é
`UNKNOWN`, porque só uma engine publica documentação enumerando as features novas por nome.
Isso é o resultado, não a pendência: preencher por inferência apagaria a distinção entre "não
há fonte" e "não suporta", que é justamente a distinção que decide se uma migração está
bloqueada.

### As skills dedicadas que o prompt de origem enumera não foram criadas
Skill é apresentação sobre conhecimento. Enquanto o conhecimento não existisse como dado, uma
skill sobre ele seria prosa sobre prosa, e o consumidor não existia. A infraestrutura de
disclosure progressivo já existe e continua disponível para o dia em que houver o que
apresentar.

### Extrator novo só entra com consumidor
Fact sem regra que o consuma é observação que ninguém lê; regra sem fact é regra que nunca
dispara ou que dispara por chute. A ordem é fact primeiro **quando houver julgamento que o
consuma**. Foi essa decisão que impediu regras sobre VARIANT, sobre transform multi-argumento
e sobre DynamicFrame: as três armadilhas estão declaradas pela AWS e registradas como
conhecimento, e nenhuma delas tem observação que a sustente hoje. Elas ficam escritas como
lacuna nomeada, com o fact que faltaria, em vez de virarem regra que finge cobertura.

## Consequences

- **Positivas.** Versão de runtime tem uma única origem, com procedência e data. Discordância
  entre fontes retém o valor em vez de eleger um, e regra guardada por componente retido é
  reportada como pulada, com motivo, em vez de julgada com um número que as fontes não
  confirmam juntas. Afirmação de compatibilidade sem fonte não passa da carga. O que a
  ferramenta não sabe está escrito em `docs/aws/glue/6.0/known-unknowns.md`, agrupado por
  consequência para quem usa.
- **Trade-offs.** A matriz de compatibilidade é majoritariamente `UNKNOWN`, e quem a consulta
  precisa entender que isso não é "não suporta". Parte do risco de migração continua sendo
  checagem manual — as mudanças de comportamento sem sinal no código, preço e performance —, e
  o guia de decisão nomeia cada uma dessas checagens como manual em vez de omiti-las.
- **Limite declarado.** `docs/aws/` não está sob o gate de lastro: nada ali é auditado
  alegação por alegação. A mitigação é estrutural — os documentos apontam para o arquivo que
  sustenta cada afirmação em vez de copiá-la. Trazer esse diretório para `audited_roots()` é
  decisão de outra fase.
