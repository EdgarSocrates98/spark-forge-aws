---
name: optimize-variable-volume-job
description: Use quando o mesmo job Glue recebe de dezenas de registros a centenas de milhões e um único perfil configurado para o pior caso fica caro para microcargas e inadequado para full, e você precisa de perfis por volume, curto-circuito e separação de workloads.
---

# Optimize Variable Volume Job

## Perfis

Classifique execuções:
- empty;
- micro;
- small;
- medium;
- large;
- full/bootstrap.

Os limites devem ser derivados do workload, não fixos universalmente.

## Avaliar

- custo fixo de inicialização;
- custo de planejamento Iceberg;
- bytes lidos;
- files planned/opened;
- estratégia de join;
- workers;
- Auto Scaling;
- escrita;
- commits;
- compactação;
- SLA;
- frequência;
- concorrência.

## Padrões possíveis

- full/bootstrap separado;
- incremental recorrente separado;
- manutenção Iceberg separada;
- curto-circuito sem mudanças;
- escolha de estratégia por volume;
- materialização current-state;
- perfis de workers;
- argumentos por classe de carga;
- filas/concorrência separadas.

## Anti-pattern

Um job único configurado para o pior caso pode ser caro e lento para microcargas, e ainda inadequado para full.

## Saída

Matriz:

| Perfil | Estratégia | Workers | Leituras | Joins | Escrita | SLA | Observabilidade |
|---|---|---|---|---|---|---|---|

## Quando NÃO usar

- O volume é estável: use `tune-glue-job` para um único perfil bem dimensionado.
- O foco é provar que o incremental reduz trabalho: use `design-incremental-processing`.
- Só precisa dimensionar workers: use `tune-glue-job`.

## Referência rápida

| Perfil de execução | Risco dominante | Estratégia coerente |
|---|---|---|
| empty / micro | cold start e planning dominam o custo | curto-circuito; sair cedo se não há mudança |
| small / medium | join/estratégia inadequada para o volume | escolher estratégia por volume |
| large / full | OOM e custo | perfil de workers dedicado; separar do incremental |
| manutenção Iceberg | conflito com carga | job de manutenção separado |

## Red flags

- Configurar um job único para o pior caso e pagar isso em toda microcarga.
- Não ter curto-circuito para execuções sem mudanças (empty/micro).
- Misturar full, incremental e manutenção Iceberg no mesmo job/fila.
