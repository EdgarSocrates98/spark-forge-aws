# Relatório de Performance — {{job_name}}

## 1. Resumo executivo

- Gargalo dominante:
- Confiança:
- Impacto atual:
- Recomendação prioritária:
- Resultado do benchmark:

## 2. Ambiente

| Item | Valor |
|---|---|
| Glue | |
| Spark | |
| Python | |
| Iceberg | |
| Worker | |
| Workers | |
| Auto Scaling | |

## 3. Baseline

| Métrica | Valor |
|---|---:|
| Runtime | |
| DPU-hours | |
| Input bytes | |
| Shuffle read | |
| Shuffle write | |
| Disk spill | |
| Output files | |

## 4. Evidências

### Código

### Plano físico

### Spark UI

### CloudWatch

### S3/Parquet

### Iceberg

## 5. Gargalos priorizados

| Prioridade | Gargalo | Evidência | Confiança |
|---|---|---|---|

## 6. Recomendações

Use o contrato de recomendação do projeto.

## 7. Benchmark antes/depois

## 8. Validação funcional

## 9. Gates com override

Um gate passado por cima **aparece aqui**, com motivo e data. Não é formalidade:
o gate existe porque a fase depende daquela evidência, e a diferença entre *não
havia gate* e *o gate existe e alguém passou por cima* é a mesma que
`dq.unresolved` faz entre "não há problema" e "ninguém olhou". Relatório que
omite isso afirma um rigor que não foi prestado.

Copie de `sparkforge case get --repo <raiz>` (campo `gate_overrides`) ou da seção
"Overrides de gate" de `sparkforge resume`. Uma linha por override, na ordem em
que foram gravados:

| Gate | Quando | Motivo |
|---|---|---|

Sem nenhum override, escreva "nenhum" — a linha em branco não distingue *não
houve* de *ninguém preencheu*.

Esta seção fica **dentro** do corpo assinado: editá-la depois de `report sign`
invalida a assinatura, e `report verify` acusa no corpo.

## 10. Riscos e rollback

## 11. Próximos experimentos

## 12. Assinatura de correspondência

O bloco abaixo é escrito por
`sparkforge report sign --report <este arquivo> --findings <findings.json>`, e
conferido por `sparkforge report verify` com os mesmos dois arquivos. Não o
edite à mão: ele é recomputado inteiro a cada assinatura, e o corpo assinado é
tudo que vem **antes** do delimitador de abertura — inclusive esta seção. Nada
pode vir depois do delimitador de fechamento; texto ali ficaria fora da
assinatura sem que o leitor tivesse como saber.

<!-- sparkforge:signature -->
<!-- /sparkforge:signature -->
