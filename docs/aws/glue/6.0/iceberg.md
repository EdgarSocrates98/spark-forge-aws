# Iceberg e a spec v3 no Glue 6.0

## A separação que organiza tudo aqui

[`../../../../knowledge/storage/iceberg-v3.md`](../../../../knowledge/storage/iceberg-v3.md)
tem duas metades, e a separação entre elas é a razão de o documento existir:

1. **Feature da spec** — o que o formato v3 define, e o que a biblioteca passou a
   implementar.
2. **Suporte da engine** — o que o AWS Glue 6.0 declara suportar, por escrito.

**As duas não se deduzem uma da outra.** "A spec v3 define transforms multi-argumento" não
implica "o Glue 6.0 executa transforms multi-argumento" — neste caso específico implica o
contrário, porque a AWS declara essa limitação. Toda recomendação que atravesse da metade 1
para a metade 2 sem uma linha da metade 2 que a sustente é inferência, não fato.

A versão de Iceberg empacotada por cada runtime está na matriz — ver
[`runtime.md`](runtime.md). Não é repetida aqui, e a versão do **formato de tabela** não é a
versão da **biblioteca**: `mig.table_format` existe justamente para separar as duas.

## A mesma separação como dado

Prosa não é consultável e não tem gate. A mesma separação vive como dado em
[`../../../../knowledge/storage/iceberg-feature-support.yaml`](../../../../knowledge/storage/iceberg-feature-support.yaml),
carregado por `sparkforge/storage/feature_support.py`: uma matriz de **feature contra
engine**, uma célula por par, e cada célula carrega a própria evidência.

A regra está em código, não em prosa: **toda célula afirmativa precisa de `source`,
`source_type` e `retrieved` próprios**, e o carregador **recusa a matriz inteira** quando uma
célula afirma suporte sem eles. `source_type` reusa o vocabulário fechado da matriz de
runtime, importado de lá e nunca redeclarado.

Chave de versão `"*"` significa que a fonte não qualifica a afirmação por versão da engine.
Onde a AWS distingue runtimes por escrito, a linha tem uma chave por runtime; inventar um
recorte de versão que a fonte não faz seria precisão fabricada.

## Por que célula sem evidência é `UNKNOWN` — e por que isso é o resultado

`UNKNOWN` é o único status que dispensa fonte: desconhecimento não precisa de prova. Mas ele
precisa **existir** como célula escrita, e não ser omitido — célula ausente e célula
`UNKNOWN` dizem coisas diferentes. A ausente diz "ninguém perguntou". A `UNKNOWN` diz
"perguntamos e não há fonte".

A maioria das células é `UNKNOWN`, e a contagem exata mora no cabeçalho do próprio YAML, não
aqui. Isso **não é lacuna do dado**. É o resultado honesto de existir documentação oficial
enumerando feature de v3 **por nome** para apenas uma engine. A alternativa — preencher a
linha de outra engine a partir do que a biblioteca Iceberg suporta — é exatamente a
inferência que a separação acima proíbe, e há teste que falha quando ela acontece.

A distinção que `UNKNOWN` preserva é a que uma matriz preenchida por raciocínio apagaria:
**"não há fonte" não é "não suporta"**. Uma recomendação construída sobre a segunda leitura
bloqueia uma migração por um fato que ninguém verificou.

O caso que vale ler junto com a limitação declarada pela AWS: `multi_argument_transforms` é
`UNSUPPORTED` no Glue 6.0 **apesar** de estar na spec v3. É a linha em que a spec implica o
contrário da engine.

## O que a AWS declara, e o que já existia antes

O detalhe está na metade 2 do documento de conhecimento. Dois pontos que mudam decisão e
costumam ser lidos errado:

- **Deletion vectors e row lineage não são novidade do Glue 6.0** — o runtime anterior já os
  entregava. Um plano que justifique o salto por eles está pagando uma migração por algo que
  já tinha.
- **Tabela criada com `'format-version'='3'` não é lida pelo Athena SQL.** Para
  compatibilidade entre engines, v2. Esta é a única armadilha da página que já é **judicável**
  neste repositório: é `SF-ENV-002`, cruzando `iceberg.table_property` com `env.consumer`.
  Não existe regra nova para ela, e duplicá-la seria dívida, não cobertura.

## Por que não existe área `SF-ICE-V3`

Regra sem fact é regra que nunca dispara ou que dispara por chute. As armadilhas novas da v3
— VARIANT sob FGAC, transform multi-argumento, tipo novo sob DynamicFrame, pipeline montado
no Visual ETL — **não têm fact que as sustente** neste repositório. A seção 6 de
[`../../../../knowledge/storage/iceberg-v3.md`](../../../../knowledge/storage/iceberg-v3.md)
nomeia, uma a uma, qual observação faltaria para cada julgamento.

Criar extrator antes de haver consumidor é o erro que `docs/harness/GLUE6-GAP.md` existe para
impedir. A ordem é: fact primeiro **quando houver julgamento que o consuma**, nunca o
inverso. Ver [`known-unknowns.md`](known-unknowns.md) para o que isso deixa fora de alcance.

## O que o diagnóstico de tabela entrega hoje

`sparkforge/iceberg/doctor.py:IcebergTableDoctor` devolve o `format_version` no relatório de
saúde, e `sparkforge/facts/iceberg_metadata.py` extrai metadados de dump. Prontidão para v3,
uso de VARIANT e suporte por consumidor **não** fazem parte do relatório — ver
[`known-unknowns.md`](known-unknowns.md).
