# Conhecimento e catálogo de regras

O resumo está no [README](../../README.md). Aqui fica o detalhe: onde mora o
conhecimento sobre o comportamento de cada serviço, como ele vira regra executável,
e o vocabulário de ação que torna contradição e ordem legíveis sem Python. Para
consultar regras e fontes pela CLI, veja [Packs e conhecimento](usos/packs-e-conhecimento.md).

## Base de conhecimento

`knowledge/` é a fonte de verdade sobre **como Spark, Glue, EMR, Athena, Parquet e
Iceberg se comportam** — separada de `skills/` (procedimento) e de `.sparkforge/`
(estado da investigação). Comece por [`knowledge/INDEX.md`](../../knowledge/INDEX.md).

Cobertura: modelo de execução do Spark, referência de configuração com defaults
exatos, shuffle/join/skew, memória e as sete classes de OOM, leitura de plano
físico, matriz de runtime Glue, worker types e capacidade, argumentos de job,
métricas de observabilidade, matriz de runtime EMR e configuração de cluster EMR
on EC2, configuração de application EMR Serverless, matriz Databricks Runtime →
Spark (Databricks como plataforma declarada), superfície corrente dos frameworks
de validação de dados, performance de Athena, layout Parquet/S3 e Iceberg, e Lake
Formation: os dois modelos de acesso (FGAC e Full Table Access) em
`knowledge/glue/lakeformation-fgac.md`, a matriz de capacidade por versão de Glue
em `knowledge/glue/lakeformation-matrix.yaml` e, desde 2026-09-25, a tabela que
diz qual permissão cada operação do job exige em cada modelo, com a frase da AWS
por trás de cada linha, em `knowledge/glue/lakeformation-permissions.yaml`.

Ler [`knowledge/cross-service-constraints.md`](../../knowledge/cross-service-constraints.md)
antes de recomendar mudança de versão, formato de tabela ou particionamento — são
as armadilhas em que a mudança funciona no job e quebra no consumidor.

## AWS Glue 6.0

**AWS Glue 6.0** é suportado e analisado: matriz de runtime com procedência por
fonte, áreas de regra para a fronteira do Spark 4 (`SF-SPARK4`) e para o Lake
Formation FGAC (`SF-LF`), compatibilidade de feature Iceberg por engine como dado,
e cenários de migração por par de versões. A documentação dedicada — incluindo o
guia de decisão e o que a ferramenta **não** sabe — está em
[`docs/aws/glue/6.0/`](../aws/glue/6.0/README.md). O passo a passo da migração está
em [Migração de versão](usos/migracao-de-versao.md).

## O catálogo de regras

`rules/catalog/` é a forma **executável** desse conhecimento: **169** regras de
diagnóstico em YAML com `rule_id`, limiar, guarda de versão e fonte com data —
**169 delas executáveis**, ou seja, todas; as 35 declarações de área de coordenação
(`executable: false`) saíram em 2026-09-19, porque nomeavam área sem julgar nada
(feature `docs/sdd/SF_STUBS/`) —, mais **43** rotas determinísticas em `routing.yaml`. Funciona
como conhecimento consultável mesmo sem o motor Python — é o terceiro degrau da
escada de portabilidade. Ver [`rules/catalog/README.md`](../../rules/catalog/README.md).
Os números correntes ficam na tabela *Números correntes* de
[`docs/superpowers/STATUS.md`](../superpowers/STATUS.md), e
`python scripts/check_status_numbers.py --strict` reprova linha que nenhuma medida
produz — e reprova também as frases deste manual que publicam contagem.

## As áreas

As 169 executáveis se distribuem em 31 áreas (medido em 2026-09-25 com `area_of`):
`SF-ERR` 23 (a exceção que o job lançou, e a maior área do catálogo), `SF-PY` 12
(código PySpark), `SF-EMR` 9 (cluster EMR on EC2), `SF-PQ` 9 (Parquet/S3), `SF-CTM` 6
(Control-M), `SF-EMRS` 6 (application EMR Serverless), `SF-GLUE` 6 (infraestrutura
Glue), `SF-GRAPH` 6 (grafo com GraphFrames), `SF-UI` 7 (event log), `SF-ATH` 5
(Athena), `SF-ENV` 6 (ambiente e versão, incluindo Photon não declarado sob
Databricks), `SF-FVAL` 5 (validação funcional), `SF-ICE` 8 (Iceberg, incluindo a
classe do catálogo de sessão, a operação SQL que exige as extensões e o conflito de
versão da biblioteca), `SF-BENCH` 4 (comparação entre execuções), `SF-DQ` 4
(validação de dados), `SF-EMRK` 4 (EMR on EKS), `SF-LF` 11 (Lake Formation FGAC e
FTA), `SF-MIG` 4 (migração entre versões), `SF-PLAN` 4 (plano físico), `SF-SPARK4` 4
(fronteira do Spark 4), `SF-AIRFLOW` 4 (como o DAG do Apache Airflow dispara o job Glue), `SF-SFNX` 3 (o que a execução do Step Functions registrou), `SF-SFN` 4 (como o AWS
Step Functions dispara o job Glue), `SF-KMS` 2, `SF-TIMEOUT` 2, `SF-WASTE` 2, `SF-IAM` 3 (a
camada que negou: boundary, service control policy ou `Deny` explícito), `SF-XACC` 3
(cross-account: o catálogo de outra conta, o nome do resource link e o alvo dele),
e uma cada em `SF-BRIDGE`, `SF-CG` e `SF-NET`. **Conte área com `area_of`, nunca
somando lista escrita à mão** — `SF-EMR` é prefixo de `SF-EMRS` e de `SF-EMRK`, e
comparar por `startswith` mede a fronteira ao contrário. A área não é etiqueta de
serviço: o que gateia uma regra é `requires_facts` — provar que alguém coletou o
artefato — e `runtime_scope`, que é guarda de **versão** e nada mais.

## O bloco `action:`

Cada uma das 169 carrega um bloco **`action:`** — `kind` (70 no vocabulário
fechado), `target`, `direction` (`increase`/`decrease`/`add`/`remove`/`replace`/`investigate`),
`requires_absent`, `moves` (23 eixos, cada um `nature: measure` ou `risk`) e
`depends_on`. É o que torna **contradição** e **ordem de aplicação** legíveis sem
MCP e sem Python. O vocabulário é travado **nas duas direções**: `kind`, eixo ou
direção que o catálogo não declara reprova o gate, e `kind` declarado que regra
nenhuma usa também — dez foram apagados por não serem ação dominante de regra
nenhuma. `expected_gain` é **recusado pelo schema**: afirmar quanto se economizaria
exige o custo do run que não aconteceu.

O vocabulário mora em `rules/catalog/action_kinds.yaml`; as contagens de `kind` (70)
e de eixo (23) foram relidas dele em 2026-09-18.

## Próximos passos

- [Extrair, julgar, compor](06-extrair-julgar-compor.md): o que produz os facts que as regras leem.
- [Packs e conhecimento](usos/packs-e-conhecimento.md): `rules lookup`, fontes vigiadas e Forge Packs.
- [Arbitragem e debate](usos/arbitragem-e-debate.md): o que o bloco `action:` permite decidir.
