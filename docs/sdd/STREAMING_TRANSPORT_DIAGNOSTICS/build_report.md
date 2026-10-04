---
sdd: 1
feature: STREAMING_TRANSPORT_DIAGNOSTICS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_TRANSPORT_DIAGNOSTICS/plan.md
  sha256: "f305c218a4bbd95a22a30482eb81dd450a5bbd82ce9c44a3c25c3a11a097faf0"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_transport.py::test_kafka_dump_emits_topic_partition_group_and_lag_facts tests/test_facts_transport.py::test_msk_and_kinesis_dump_emit_observed_facts tests/test_facts_transport.py::test_transport_blind_spots_are_unresolved -q -p no:cacheprovider --basetemp=C:/sf-test/transport-facts-red", exit: 1}
    green: {command: "python -m pytest tests/test_facts_transport.py::test_kafka_dump_emits_topic_partition_group_and_lag_facts tests/test_facts_transport.py::test_msk_and_kinesis_dump_emit_observed_facts tests/test_facts_transport.py::test_transport_blind_spots_are_unresolved -q -p no:cacheprovider --basetemp=C:/sf-test/transport-t1-green", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_transport.py::test_transport_fixture_corpus_is_complete -q -p no:cacheprovider --basetemp=C:/sf-test/transport-golden-red", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_transport.py::test_transport_fixture_corpus_is_complete -q -p no:cacheprovider --basetemp=C:/sf-test/transport-t2-green", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_analyze_transport.py::test_cli_and_mcp_transport_envelopes_match -q -p no:cacheprovider --basetemp=C:/sf-test/transport-t3-red2", exit: 2}
    green: {command: "python -m pytest tests/test_analyze_transport.py::test_cli_and_mcp_transport_envelopes_match -q -p no:cacheprovider --basetemp=C:/sf-test/transport-t3-green", exit: 0}
  - id: T4
    status: done
    red: {command: "python scripts/verify_offline_bundle.py --check", exit: 1}
    green: {command: "python scripts/verify_offline_bundle.py --check", exit: 0}
  - id: T5
    status: done
    red: {command: "python scripts/check_surface_lock.py", exit: 1}
    green: {command: "python scripts/check_surface_lock.py", exit: 0}
claims:
  - text: "Kafka, MSK e Kinesis agora têm facts offline específicos, com unresolved nomeado para JSON inválido, shape ausente e campos não observados."
    evidence_ref: "sparkforge/facts/transport.py; tests/test_facts_transport.py"
  - text: "CLI e MCP usam o mesmo analyzer e retornam o envelope de transporte sem collector implícito."
    evidence_ref: "tests/test_analyze_transport.py::test_cli_and_mcp_transport_envelopes_match"
  - text: "O corpus golden, knowledge offline, manifest, parity e referências públicas foram sincronizados."
    evidence_ref: "tests/test_fixtures_golden_transport.py; python scripts/check_surface_lock.py"
change_id: null
---

# STREAMING_TRANSPORT_DIAGNOSTICS — relatório do build

## Resultado

T1–T5 concluídas. A onda entrega ingestão determinística de dumps Kafka, MSK e
Kinesis, sem chamada de rede, sem regra de causa e sem valor padrão para campo
ausente. O contrato de evidência preserva domínio, âncora do artefato, campos
observados e `unresolved`.

## Desvios do plano

- A primeira implementação precisou normalizar aliases da API Kinesis
  (`StreamName`, `Shards`, `IteratorAgeMilliseconds`) além do formato compacto
  das fixtures. O comportamento foi coberto por teste e não inventa valores.
- As contagens publicadas em `STATUS.md`, README, guias e superfícies geradas
  foram recontadas depois da nova tool: 46 extratores, 289 kinds, 117 tools,
  580 fixtures e 288 fontes vigiadas.
- Nenhuma regra, rota de finding, coleta live ou agente dedicado entrou nesta
  onda; o diagnóstico causal continua pendente de série temporal e baseline.

## Revisão

Revisão de especificação: parser offline comum com especialização por domínio,
sem colapsar ausência em zero. Revisão de qualidade: fixtures positivas,
unresolved, aliases Kinesis, parity, surface lock e bundle offline.

Gates executados:

- `877 passed` no lote direcionado de facts, goldens, analyzer, reachability,
  parity, surface e contratos host.
- `python scripts/check_status_numbers.py --strict`: exit 0.
- `python scripts/verify_offline_bundle.py --check`: exit 0, `checked: 59`.
- `python scripts/sync_skills.py --check`: exit 0.
- `python scripts/refresh_knowledge.py --offline --check`: exit 0, 288 fontes.
- `python scripts/gen_reference_docs.py`: 244 páginas, 0 regravadas, 0 removidas.
- `python scripts/check_surface_lock.py`: exit 0, 0 divergências.

## Limites e rollback

Não há evidência para lag ao longo do tempo, hot partition, throughput,
capacidade, custo, compatibilidade completa de versões MSK ou autorização
produtiva. Para desfazer, reverter os commits desta feature em ordem inversa e
regenerar referências/surface; remover junto o extrator, tool, fixtures,
knowledge e manifest derivados.

## O laço

O RED de T1–T3 foi registrado antes do comportamento verde; T4 e T5 registram
as recusas observadas durante sincronização e seus estados verdes finais. O
próximo passo é `sdd-ship`, com hipótese fechada pela cobertura dos goldens e
pelos envelopes equivalentes.
