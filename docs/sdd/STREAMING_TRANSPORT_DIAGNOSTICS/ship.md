---
sdd: 1
feature: STREAMING_TRANSPORT_DIAGNOSTICS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_TRANSPORT_DIAGNOSTICS/build_report.md
  sha256: "f5bae26de13ff2e18035ea0b701cd570165296c8fcd747d3befc6b450eca0b42"
hypothesis_outcome: confirmed
registries:
  - reachability_lists
  - fixture_kind_coverage
  - snippet_measure
  - fixture_corpus_gates
  - offline_manifest
  - sources_lock
  - surface_lock
  - generated_reference
  - status_numbers_gate
deviations:
  - "A implementação também normaliza aliases do payload Kinesis API, cobertos por teste, sem preencher valores ausentes."
  - "A onda não adiciona collector live, regra de diagnóstico, baseline temporal ou agente especializado."
---

# STREAMING_TRANSPORT_DIAGNOSTICS — entrega

## Hipótese

Confirmada no escopo declarado: um contrato comum entrega envelopes CLI/MCP
equivalentes e preserva fatos específicos de Kafka, MSK e Kinesis, inclusive
`unresolved`. A confirmação é de forma e evidência offline; não é uma afirmação
de diagnóstico causal, throughput, custo ou cobertura produtiva.

## Entrega

- Extrator determinístico para dumps JSON/JSONL Kafka, MSK e Kinesis.
- Tool MCP e comando `sparkforge-aws analyze transport` compartilhando o core.
- Goldens positivos e cegos, com aliases Kinesis API e campos ausentes nomeados.
- Knowledge, fontes, manifest, parity, surface e referências regeneradas.
- SDD da feature corrigido para o schema oficial e com RED/GREEN registrado.

## Gates

- `sparkforge-aws sdd check --repo . --feature STREAMING_TRANSPORT_DIAGNOSTICS`: exit 0,
  `ok: true`, zero recusas e zero unresolved.
- Lote direcionado: `877 passed`.
- `python scripts/check_status_numbers.py --strict`: exit 0.
- `python scripts/verify_offline_bundle.py --check`: exit 0, 59 arquivos.
- `python scripts/sync_skills.py --check`: exit 0.
- `python scripts/refresh_knowledge.py --offline --check`: exit 0, 288 fontes.
- `python scripts/check_surface_lock.py`: exit 0, 0 divergências.

## Pendências explícitas

Próximas ondas precisam coletar evidência read-only real e versionada para
Kafka/MSK/Kinesis, séries temporais de lag/iterator age, correlação com
`StreamingQueryProgress`, regras com baseline e validação de custo. Flink,
Glue streaming/RTM, CDC, Iceberg streaming, observabilidade, segurança e
especialistas dedicados continuam fora desta entrega.

## Rollback

Reverter os commits desta feature em ordem inversa. Regenerar ou remover
surface, referências, manifest, fixtures, knowledge e locks conforme os gates
derivados; não executar collector live como parte do rollback.

## Lições

O schema SDD deve ser validado antes de criar os relatórios finais: campos
semânticos úteis, mas fora do contrato, bloquearam o check. Para próximas
ondas, separar desde o plan os testes de parser, transporte e julgamento evita
confundir um envelope correto com evidência suficiente para regra causal.
