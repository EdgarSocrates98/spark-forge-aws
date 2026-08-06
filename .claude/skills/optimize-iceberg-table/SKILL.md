---
name: optimize-iceberg-table
description: Use quando tabelas Apache Iceberg no Glue Data Catalog degradam por excesso de data files pequenos, delete files acumulados, snapshots ou manifests crescendo sem parar, partition spec inadequado ou write.distribution-mode incoerente com particionamento — e for preciso decidir entre compaction, rewrite manifests e expire snapshots com evidência, não por rotina. Use também quando a pergunta for "essa tabela Iceberg tá lenta para consultar", "o Athena demora para planejar essa tabela" ou "quantos snapshots essa tabela já acumulou", mesmo que ninguém fale em metadata table. Se você está prestes a rodar `SELECT * FROM db.tabela.files` no olho para contar arquivo pequeno, rode `sparkforge collect iceberg-metadata` e `sparkforge analyze iceberg` em vez disso — o extrator resume files, delete files, snapshots, manifests e partições deterministicamente, e o catálogo aplica os limiares versionados.
---

# Optimize Iceberg Table

Contar data file, delete file e snapshot no olho não escala e é fácil de errar por um dígito — e aqui o erro custa mais que numa contagem qualquer, porque a manutenção que a decisão dispara depois pode ser irreversível. O extrator resolve a parte de contagem: ele lê as metadata tables e calcula os resumos. O catálogo aplica os limiares versionados.

Seu trabalho não é contar. É **coletar, rodar, interpretar — e, antes de qualquer manutenção destrutiva, confirmar escopo e retenção com quem é dono do dado.**

## Procedimento

### 1. Garanta os dumps das metadata tables

```bash
sparkforge collect iceberg-metadata --repo <repo> --table <db.tabela> --workgroup <wg> --output-location <s3://...> --now <ISO8601>
```

Sem credencial AWS/Athena, rode as consultas manualmente (`SELECT * FROM db.tabela.files`, `.delete_files`, `.snapshots`, `.manifests`, `.partitions`, mais `properties`, `sort_order` e `partition_spec` da tabela) e salve o resultado no shape que o extrator espera — ver o cabeçalho de `sparkforge/facts/iceberg_metadata.py`. Registre o artefato no manifesto do case para a coleta ser retomável.

### 2. Extraia os facts

```bash
sparkforge analyze iceberg --path <dump.json ou diretório> --out .sparkforge/facts.json
```

Todas as seções do dump são opcionais: um dump com só `files` ainda produz o que dá para produzir a partir disso. Uma seção presente mas malformada (não é lista) vira `iceberg.unresolved` — leia essa contagem sempre; é ponto cego, não ausência de problema.

### 3. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --show-skipped
```

`--iceberg` saiu daqui porque, sozinha, ela não destrava nada. Nenhuma das cinco regras `SF-ICE-*` declara `runtime_scope` — todas avaliam em qualquer versão. A única regra deste eixo que guarda versão é `SF-ENV-002` (tabela em format V3 consumida por Athena), e o guarda dela é `glue >= 5.1` **e** `iceberg >= 1.10.0`, com os dois obrigatórios: a checagem falha fechada, então declarar só `--iceberg` deixa `glue` vazio e a regra continua pulada com `reason: runtime_scope`. Digitar a versão do Iceberg dava a impressão de cobrir esse eixo sem cobrir.

O caminho que de fato funciona é dar a versão do **Glue**, de onde a do Iceberg é derivada pela matriz de compatibilidade — é a versão embarcada no runtime que decide quais procedures e propriedades existem, não a que está escrita no dump. Extraia do Terraform e junte tudo na mesma chamada, já que `--facts` é repetível:

```bash
sparkforge analyze terraform --path <dir.tf> --out .sparkforge/facts_tf.json
sparkforge analyze consumers  --path <inventario.yaml> --out .sparkforge/facts_consumers.json
sparkforge judge --facts .sparkforge/facts.json --facts .sparkforge/facts_tf.json \
                 --facts .sparkforge/facts_consumers.json --show-skipped
```

Leia o campo `runtime` da saída: ele traz o contexto efetivamente usado, `detected_from` diz de onde veio (`["terraform"]`), e `divergences` denuncia fontes que discordam. `--glue 5.1` continua válido quando você sabe a versão de fonte confiável e não tem o `.tf` — mas prefira a fonte ao palpite, porque aqui a versão errada não gera só um finding errado: ela sustenta uma recomendação de manutenção destrutiva.

`--show-skipped` mostra por que cada regra não avaliou, e aqui isso importa mais que em outras áreas por causa de `SF-ICE-004`. Ela **dispara** a partir de um dump único — a evidência é por arquivo, não temporal: `iceberg.files_summary` conta os data files cujo `sort_order_id` é um id registrado diferente do `default-sort-order-id` da tabela, e um id não-zero só é gravado quando um writer chamou `withSortOrder` deliberadamente. Duas condições para ela chegar até lá:

- O dump precisa trazer a coluna `sort_order_id` da metadata table `.files` (campo 140). Se a sua coleta projetou só um subconjunto de colunas, a regra sai em `skipped` com `reason: requires_facts` — recolha com a coluna.
- O número é um **piso confirmado, não um total**. Arquivos com `sort_order_id` 0 ficam de fora e viram `iceberg.unresolved`, porque até o Iceberg 1.10.0 o writer do Spark não gravava esse campo e 0 não distingue "não ordenado" de "não registrado". Reporte "pelo menos N arquivos", nunca "N arquivos".

### 4. Interprete

As regras dizem o que ultrapassou o limiar. Decidir qual manutenção corrige a causa — e se vale o custo de DPU e o risco de rodar sobre uma tabela ativa — é o seu trabalho.

## O que cada fact significa

| Fact | O que mede | Por que importa |
|---|---|---|
| `iceberg.files_summary` | contagem, total de bytes, avg/p50/p95/min/max por data file | Tamanho médio baixo com contagem alta é small files; alimenta `SF-ICE-001` |
| `iceberg.delete_files_summary` | contagem de delete files, e a razão contra `data_file_count` quando `files` também foi lido no mesmo dump | Merge-on-read reconcilia delete files a cada leitura — a degradação é lenta e silenciosa, sem que nada tenha mudado no código |
| `iceberg.snapshots_summary` | contagem de snapshots, operações distintas, span de tempo entre o mais antigo e o mais novo | Cada commit é um snapshot. Loop de append por lote cria um snapshot por lote — correlaciona com `SF-PY-004` quando a causa é escrita em loop |
| `iceberg.manifests_summary` | contagem de manifests, bytes totais, média de data files por manifest | Manifests crescendo sem parar é planejamento de leitura mais lento, inclusive para Athena |
| `iceberg.partitions_summary` | contagem de partições, arquivos e registros médios por partição | Desigualdade grande entre partições aponta partition spec ruim antes de apontar para escrita |
| `iceberg.table_property` | chave/valor de `properties`, mais `sort-order` e `partition-spec` sintetizados como propriedade estrutural | `write.distribution-mode`, presença de sort order e de partition spec vêm daqui |
| `iceberg.table_analyzed` | sentinela: prova que a extração rodou sobre este dump, com contagem de seções lidas e de unresolved | Sem isso, uma condição `absent` do catálogo seria verdadeira tanto por "não achou" quanto por "nunca rodou" — o sentinela distingue os dois |

## Manutenção destrutiva — leia isto antes de propor qualquer procedure

`expire_snapshots` e `remove_orphan_files` não têm desfazer. Depois que um snapshot expira, o time travel para ele desaparece — não existe comando que o traga de volta, porque o próprio ponteiro de metadata que apontava para os arquivos daquele estado foi removido junto. Se alguém perguntar "e se precisarmos voltar depois", a resposta depois de expirar é não.

Por isso, nunca proponha `expire_snapshots` ou `remove_orphan_files` com um número de retenção escolhido por você. Quantos dias de histórico manter, e se existe requisito de auditoria ou regulatório que exige mais do que o técnico pediria, é uma decisão de negócio — quem a toma é o dono dos dados, não quem está otimizando a tabela. `AGENT_PROTOCOL.md` regra 9 exige confirmação explícita de escopo e retenção antes de qualquer manutenção destrutiva; `SF-ICE-003` registra a mesma exigência no catálogo, com a mesma frase: não há rollback, a mitigação é escolher a retenção antes de executar.

`remove_orphan_files` carrega um segundo risco, independente do primeiro: se a idade mínima configurada for curta demais, ele pode apagar um arquivo que uma escrita concorrente ainda não commitou — o arquivo já existe no S3 mas ainda não está em nenhum manifest. Confirme a idade mínima contra a duração máxima de escrita observada nessa tabela antes de propor um valor.

Sempre que uma dessas duas procedures aparecer numa recomendação: ofereça dry run se a versão embarcada do Iceberg suportar, e escreva explicitamente "não há rollback" — não deixe implícito, e não deixe para o leitor descobrir isso ao ler a doc da procedure depois.

## Referência rápida

Regras desta área, e o fact que cada uma consome. Os limiares **não** estão aqui de propósito — consulte com `sparkforge rules lookup --id <ID>`, que devolve limiar, guarda de versão, risco, validação, rollback e fonte com data.

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-ICE-001` | `iceberg.files_summary` | Tamanho médio de data file muito abaixo do alvo — small files |
| `SF-ICE-002` | `iceberg.delete_files_summary` + `iceberg.files_summary` | Razão delete files / data files alta — dívida de merge-on-read |
| `SF-ICE-003` | `iceberg.snapshots_summary` | Contagem de snapshots alta — metadata growth por commits frequentes |
| `SF-ICE-004` | `iceberg.table_property` + `iceberg.files_summary` | Sort order definido sem rewrite do passivo — conta os data files sob uma ordem registrada anterior. Piso, não total |
| `SF-ICE-005` | `iceberg.table_property` (`write.distribution-mode` + `partition-spec`) | `distribution-mode: none` com particionamento — causa estrutural de small files |

## Quando NÃO usar

- A tabela é Parquet "puro" no S3, sem metadados Iceberg: use `optimize-parquet-layout`.
- O foco é o cálculo latest-per-key sobre a tabela: use `optimize-latest-per-key`.
- Muitos commits vêm de um loop de batches na aplicação: comece por `analyze-batch-loop` — a causa provável é `SF-PY-004`, não a tabela.
- Ainda não sabe se o gargalo é mesmo Iceberg: comece por `sparkforge-diagnose`.

## Red flags

- Propor `expire_snapshots` ou `remove_orphan_files` com retenção decidida por você, sem confirmação explícita de escopo.
- Apresentar `measures.files_written_before_sort_order` de `SF-ICE-004` como o total do passivo. É um piso: os arquivos com `sort_order_id` 0 estão em `iceberg.unresolved`, fora da conta, e dimensionar o `rewrite_data_files` por esse número subestima o custo.
- Compactar data files quando o sintoma real é manifests ou snapshots crescendo (`ROUTE-010` em `routing.yaml`): planejamento lento aponta para metadado, não para data file, e compactar dado custa horas de DPU sem tocar a causa.
- Rodar procedure ou propriedade da doc `latest` do Iceberg sem confirmar suporte na versão embarcada pelo Glue.

## Preservar o resultado, com o verbo que produz a evidência

As três recomendações desta skill têm relações opostas com o dado. Compactação e reescrita de
manifest não mudam linha. Mudar partition spec ou sort order muda qual linha cai em qual
arquivo. E `expire_snapshots` e `remove_orphan_files` **destroem a capacidade de provar
qualquer uma das duas depois**, porque apagam o time travel de onde sairia o lado `--before`.
Por isso o plano se define **antes** do procedimento, e não depois.

`sparkforge funcval plan --facts <facts.json> --out <plano.json>` deriva o plano — `--facts`
é repetível, porque o alvo vem do `pyspark.write` e o schema e os agregados vêm do
`catalog.table_schema` —, e `sparkforge funcval compare --plan <plano.json> --before
<antes.json> --after <depois.json>` compara os dois lados **que o operador mediu**: nenhum dos
dois executa consulta, roda Spark ou chama AWS. Tools MCP: `sparkforge_funcval_plan` e
`sparkforge_funcval_compare`. O plano é a evidência do gate `functional_validation_defined`, e
`ROUTE-015` é a rota que manda defini-lo. O lado `--before` só existe se alguém o mediu
**antes** de a mudança tocar o alvo — um `overwrite` no meio o apaga sem deixar rastro.

Os quatro eixos são **proxies**, e escrever o contrário promete o que a ferramenta não
entrega: contagem, schema, chaves e agregados iguais **não provam** que o dado é o mesmo — duas
linhas podem trocar valores entre si e os quatro passam. Escreva "nenhum dos quatro proxies
detectou divergência", nunca "o resultado é idêntico". Sem `--key`, a chave de negócio sai em
`undeclared_axes` com a razão, e isso vai dito. `SF-FVAL-005` acesa invalida a leitura das
outras quatro.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita. E **derive o plano de validação funcional** com `funcval plan` antes de fechar a
recomendação, comparando os dois lados medidos com `funcval compare` — a regra 10, e ela
nomeia o produtor de propósito: exigência sem verbo é prosa.
