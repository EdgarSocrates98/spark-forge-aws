# Princípios de performance

## Hierarquia de otimização

1. Eliminar trabalho desnecessário.
2. Reduzir bytes lidos.
3. Reduzir cardinalidade cedo.
4. Reduzir colunas antes de joins e agregações.
5. Evitar ou reduzir shuffle.
6. Corrigir skew.
7. Melhorar layout físico.
8. Ajustar paralelismo.
9. Ajustar memória e workers.
10. Considerar mudanças arquiteturais.

## Nunca assumir

- Um número universal de partições.
- Um tamanho universal de arquivo.
- Que broadcast é sempre melhor.
- Que mais workers reduzem custo.
- Que cache acelera qualquer pipeline.
- Que AQE corrige todos os problemas.
- Que `repartition` resolve skew.
- Que compactação deve rodar após toda escrita.

## Evidências mínimas

- Plano físico.
- Métricas por stage/task.
- Distribuição das chaves.
- Tamanho real dos lados do join.
- Quantidade e tamanho dos arquivos.
- Uso de CPU, heap, GC, spill e shuffle.
- Runtime e custo da baseline.
