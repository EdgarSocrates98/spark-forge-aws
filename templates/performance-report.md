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

## 9. Riscos e rollback

## 10. Próximos experimentos

## 11. Assinatura de correspondência

O bloco abaixo é escrito por
`sparkforge report sign --report <este arquivo> --findings <findings.json>`, e
conferido por `sparkforge report verify` com os mesmos dois arquivos. Não o
edite à mão: ele é recomputado inteiro a cada assinatura, e o corpo assinado é
tudo que vem **antes** do delimitador de abertura — inclusive esta seção. Nada
pode vir depois do delimitador de fechamento; texto ali ficaria fora da
assinatura sem que o leitor tivesse como saber.

<!-- sparkforge:signature -->
<!-- /sparkforge:signature -->
