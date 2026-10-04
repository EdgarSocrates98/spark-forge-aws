---
sdd: 1
feature: STREAMING_FLINK_TEMPORAL_METRICS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_TEMPORAL_METRICS/define.md
  sha256: "37d5a7bb653f09b13317e79d0aa7e0aeb17b3af224f3bbfcf33e62970a54ca24"
files:
  - {path: tests/test_facts_flink.py, action: modify, reason: "testes TDD para ponto válido, timestamp ausente e shape inválido"}
  - {path: tests/test_fixtures_golden_flink.py, action: modify, reason: "incluir fixture temporal no corpus obrigatório"}
  - {path: sparkforge/facts/flink.py, action: modify, reason: "extrair flink.metric upstream de metrics explícito sem tocar Managed Flink"}
  - {path: fixtures/flink/flink_temporal_metrics/input/dump.json, action: create, reason: "artifact upstream com duas observações válidas e uma lacuna temporal"}
  - {path: fixtures/flink/flink_temporal_metrics/meta.yaml, action: create, reason: "contrato do golden temporal e kinds esperados"}
  - {path: fixtures/flink/flink_temporal_metrics/expected/facts.json, action: create, reason: "golden gerado pelo extrator determinístico"}
  - {path: fixtures/flink/flink_temporal_metrics/expected/findings.json, action: create, reason: "golden gerado pelo judge sem regra nova"}
  - {path: skills/analyze-flink-job/SKILL.md, action: modify, reason: "procedimento upstream passa a listar flink.metric e seus limites"}
  - {path: knowledge/flink-streaming.md, action: modify, reason: "contrato local de métrica temporal upstream e separação Managed"}
  - {path: README.md, action: modify, reason: "documentar observações temporais Flink upstream"}
  - {path: GUIA_DE_USO.md, action: modify, reason: "documentar comando e limites do analyzer Flink"}
  - {path: PROMPT_INICIAL_MESTRE.md, action: modify, reason: "orientar uso da evidência temporal upstream"}
  - {path: docs/guia/05-agents-e-skills.md, action: modify, reason: "roteamento da skill com namespace correto"}
  - {path: docs/guia/06-extrair-julgar-compor.md, action: modify, reason: "procedimento extract/judge para flink.metric"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "marcar contrato upstream entregue e gaps live restantes"}
  - {path: docs/guia/referencia/skills/analyze-flink-job.md, action: modify, reason: "referência gerada da skill"}
  - {path: .claude/skills/analyze-flink-job/SKILL.md, action: modify, reason: "mirror Claude gerado"}
  - {path: .agents/skills/analyze-flink-job/SKILL.md, action: modify, reason: "mirror Devin gerado"}
  - {path: docs/surface.lock.json, action: modify, reason: "bytes e hash medidos após alterar skill/knowledge"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "checksum do knowledge alterado"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "números correntes e entrega do fact kind"}
  - {path: docs/EVOLUTION-CURRENT.md, action: modify, reason: "feature e cobertura corrente"}
  - {path: docs/DELIVERY-LEDGER.md, action: modify, reason: "ledger da fase e commit de fechamento"}
  - {path: docs/sdd/STREAMING_FLINK_TEMPORAL_METRICS/build_report.md, action: create, reason: "evidência TDD, revisão e gates"}
  - {path: docs/sdd/STREAMING_FLINK_TEMPORAL_METRICS/ship.md, action: create, reason: "fechamento SDD da feature"}
decisions:
  - id: D1
    choice: "Reutilizar analyze flink e emitir flink.metric somente para artifact upstream com metrics explícito."
    rejected: ["nova tool/CLI, que aumentaria surface e custo de contexto sem segundo contrato", "misturar com managed_flink.metric, que quebraria a separação de runtime"]
    rollback: "git revert dos commits da feature; artifacts sem metrics continuam no comportamento anterior."
  - id: D2
    choice: "Exigir name, value numérico e observed_at textual; normalizar aliases de nome/timestamp e preservar metadata escalar."
    rejected: ["aceitar timestamp numérico, que exigiria adivinhar unidade/epoch", "emitir fact parcial sem timestamp, que permitiria julgar ponto sem ancoragem temporal"]
    rollback: "remover o helper temporal e o kind flink.metric; manter somente flink.unresolved para o bloco metrics."
  - id: D3
    choice: "Aceitar lista de observações ou wrapper metrics.observations, com fixture que prova válido e unresolved no mesmo artifact."
    rejected: ["aceitar qualquer objeto arbitrário, que esconderia shape inválido", "criar fixture somente positiva, que não provaria fail-closed"]
    rollback: "reverter o golden e a normalização do wrapper, sem alterar o namespace Managed."
covers:
  - {part: extractor, acceptance: [AC1, AC2, AC3, AC6]}
  - {part: fixture_corpus, acceptance: [AC4]}
  - {part: docs_and_surface, acceptance: [AC5]}
---

# STREAMING_FLINK_TEMPORAL_METRICS — desenho

## Fluxo

`analyze flink --artifact flink` → `metrics` explícito no dump →
`flink.metric` para registros completos ou `flink.unresolved` para lacunas →
`judge` somente se alguma regra futura consumir esse kind. Managed Flink segue
o ramo existente e permanece em `managed_flink.*`.

## Conhecimento consultado

- `knowledge/flink-streaming.md`, `knowledge/streaming/runtime-matrix.md` e
  `rules/catalog/flink.yaml`, lidos como contrato upstream e limites atuais.
- `sparkforge/facts/transport.py`, lido para comparar o padrão existente de
  `observed_at` e métrica numérica sem copiar a semântica de Kinesis.
- `sparkforge/facts/flink.py`, `tests/test_facts_flink.py` e goldens Flink,
  lidos para preservar shape, ordenação, provenance e o namespace Managed.
