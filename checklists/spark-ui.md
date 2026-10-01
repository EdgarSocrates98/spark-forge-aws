# Checklist Spark UI

## Jobs e stages

- [ ] Stage que domina o runtime.
- [ ] Número de tasks.
- [ ] Mediana, p95 e máximo da duração.
- [ ] Stragglers.
- [ ] Retries/failures.
- [ ] Dependências e exchanges no DAG.

## Tasks

- [ ] Input size/records.
- [ ] Shuffle read/write.
- [ ] Fetch wait.
- [ ] Memory spill.
- [ ] Disk spill.
- [ ] GC time.
- [ ] Scheduler delay.
- [ ] Result serialization time.
- [ ] Peak execution memory.

## Executors

- [ ] CPU/utilização.
- [ ] Heap.
- [ ] GC.
- [ ] Executors removidos/perdidos.
- [ ] Distribuição de tasks.
- [ ] Desbalanceamento.
- [ ] Driver como gargalo.

## Plano SQL

- [ ] Tipo de scan.
- [ ] Partition/data filters.
- [ ] Exchanges.
- [ ] Estratégia de join.
- [ ] Sort global.
- [ ] Aggregate.
- [ ] AQE e plano final.
- [ ] Broadcast real.
