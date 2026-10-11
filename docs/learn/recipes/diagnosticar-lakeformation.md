# Receita — diagnosticar acesso Lake Formation / FGAC

**O quê:** junta o que o Lake Formation concede, o que o IAM decide, o que
o job declara e o erro observado — e diz **qual camada barrou** a operação
e qual permissão falta.
**Por que:** "Insufficient Lake Formation permission(s)" sozinho não diz
se falta `SELECT`, `INSERT`, o location registration ou o credential
vending; o diagnóstico ordenado evita conceder `*` por impotência.
**Quando:** job que lê e não escreve; FGAC ligado e conector/JAR extra
quebrando; migração Glue 4→5 que parou de escrever.
**Quando não:** "esta configuração é suportada?" isolada — isso é
`lakeformation matrix`, um passo, não o diagnóstico completo.

## Problema

"O job lê a tabela governada mas falha ao escrever — qual permissão
falta, em qual camada?"

## Pré-requisitos

Dumps locais: grants do Lake Formation (`collect lakeformation`),
decisão IAM simulada (`analyze iam-access`), e a definição do job.

## Passo a passo

```bash
# 1) o que o LF concede sobre a tabela
sparkforge-aws analyze lakeformation-grants --path <dump-lf> \
  --out /tmp/facts_lf.json

# 2) o que o IAM decidiu para a runtime role
sparkforge-aws analyze iam-access --path <dump-iam> \
  --out /tmp/facts_iam.json

# 3) julgar as fontes juntas
sparkforge-aws judge --facts /tmp/facts_lf.json --facts /tmp/facts_iam.json \
  --glue 5.1

# 4) o caminho de acesso como grafo: o que libera, o que barra, o não medido
sparkforge-aws lakeformation access-graph \
  --facts /tmp/facts_lf.json --facts /tmp/facts_iam.json

# 5) o que a sua versão de Glue suporta
sparkforge-aws lakeformation matrix --runtime 5.1
```

## Saída esperada / interpretação

A camada que barrou nomeada (grant, IAM, runtime, registro de location)
e a permissão que falta — ou `unresolved` explícito onde a medida não
chegou, nunca um chute.

## Verificação

A ordem dos quatro coletores mora na skill
`diagnose-lakeformation-access` — ela existe exatamente porque a ordem
errada diagnostica a camada errada. `lakeformation matrix` confirma o que
o runtime suporta antes de qualquer `--extra-jars`.

## Limitações

- Responde **qual** permissão falta; concedê-la é decisão de segurança,
  fora do verbo.
- Cross-account: `forge lakeformation diagnose-cross-account` — outro
  eixo, com resource link e RAM no caminho.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| diagnóstico contraditório | fontes de runs diferentes | re-colete grants e IAM do mesmo momento |
| "lê e não escreve" persiste | só olhou o grant | as 4 fontes — o access-graph mostra a camada |

## Uso por agentes

Skills: `diagnose-lakeformation-access` (o procedimento ordenado),
`lakeformation-fgac-guard` (o que FGAC quebra: JARs, conectores, UDFs),
`lakeformation-architecture` (avaliação antes de recomendar).

## Leitura seguinte

- [lake-formation-e-acesso](../../guia/usos/lake-formation-e-acesso.md)
- [lake-formation-operacional](../../guia/usos/lake-formation-operacional.md)
