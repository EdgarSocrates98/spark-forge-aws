---
name: delegate-specialists
description: "Use quando o caso pedir diagnóstico de runtime sobre artefato exportado (log de driver/executor, OOM, skew, shuffle, spill, diagnose de job Glue/EMR, metadata Iceberg) ou varredura estática independente do projeto (revisão PySpark, antipadrões, config, higiene de dependências, segurança, qualidade), quando precisar decidir SE delegar a data-sentinel-forge ou forge-doctor-data em vez de usar os extratores nativos, quando consumir um EvidenceHandoff persistido, verificar um finding vindo do especialista contra os fatos nativos, ou revalidar depois de uma mudança. Não use para inventar comando de especialista — a fronteira é `sparkforge-aws delegate`, e especialista ausente degrada para `native-analysis`, nunca para execução simulada."
metadata:
  sparkforge_aws_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge-aws delegate discover
  - sparkforge-aws delegate plan
  - sparkforge-aws delegate run
  - sparkforge-aws delegate handoffs
---

# Delegar a especialistas

Dois especialistas opcionais respondem o que esta forge não cobre — e só
isso. `data-sentinel-forge` faz **diagnóstico de runtime** sobre artefato
exportado (logs, planos, metadados). `forge-doctor-data` faz **análise
estática** do projeto (código, config, dependências, segurança). Os
extratores nativos (`analyze *` + `judge`) continuam sendo a primeira
linha: delegar é acrescentar evidência, não substituir o motor.

## Quem responde o quê

| Pergunta do caso | Caminho |
|---|---|
| fato sobre código/plano/event log já em disco | extratores nativos — não delegue |
| OOM/skew/shuffle/spill em log de driver/executor exportado | `sentinel.log-analysis` |
| EXPLAIN físico vindo do Databricks/EMR/Glue | `sentinel.spark-explain` |
| SQL pesado (joins, antipadrões) | `sentinel.sql-analyze` |
| metadata Iceberg exportado (layout, snapshots) | `sentinel.lakehouse-metadata` |
| artefato EMR exportado | `sentinel.emr-analyze` |
| metadados/histórico/diagnose de job Glue via API AWS | `sentinel.glue-inspect` / `glue-runs` / `glue-diagnose` — `EXTERNAL_READ` (+`COST_BEARING` no diagnose) exigem `--authorize` explícito |
| scan estático do projeto (PySpark, config, deps, segurança, estrutura) | `doctor.scan-project` |

Se a pergunta cabe nas duas colunas, rode o nativo primeiro: o handoff do
especialista complementa o finding nativo — nunca o substitui nem o
"confirma" por fiat.

## Procedimento

1. `sparkforge-aws delegate discover --repo .` — estados reais por
   especialista: `VERIFIED` executa; `DISCOVERED`/`NOT_INSTALLED`/
   `UNTRUSTED`/`INCOMPATIBLE` voltam como recusa nomeada. Não presuma
   presença; leia o estado.
2. `sparkforge-aws delegate plan "<intenção>" --repo .` — roteamento
   determinístico para a capability declarada; devolve o plano **sem
   executar**, com justificativa e recusas nomeadas. Nenhum argv é
   inventado: as capabilities saem do manifesto declarado (`delegate
   discover` e os descriptors do especialista), nunca da sua memória.
3. `sparkforge-aws delegate run <provider> <capability> --target <artefato> --repo .`
   — executa sob a fronteira governada (argv fixo declarado, env saneada,
   timeout, caps de saída, gate de risco). Capabilities `EXTERNAL_READ`/
   `COST_BEARING` não executam sem `--authorize RISCO` — e conceder essa
   autorização é decisão do operador, não sua.
4. `sparkforge-aws delegate handoffs --repo .` — lista os
   `EvidenceHandoff` persistidos em `.sparkforge_aws/delegation/handoffs/`.

## Consumir um handoff

O resultado de `delegate run` é um `sparkforge_aws/DelegationResult/v1`:
`findings` normalizados + `handoff` selado (SHA-256) + `limitations` +
`refusal` + `handoff_path`. Cada finding vem com `severity`, `confidence`
(POSSIBLE/LIKELY/CONFIRMED/UNKNOWN — o vocabulário do especialista,
nunca promovido) e `evidence_refs`. Trate como **evidência externa**:
para virar recomendação, correlacione com um fact nativo (`fact_id`) ou
declare que a corroboração ficou em aberto no `*.unresolved`.

## Verificar um finding do especialista

- Finding do sentinel sobre log = diagnóstico do especialista, não
  medição sua. O nativo que aproxima é `analyze event-log` sobre o mesmo
  artefato, quando houver extrator.
- Finding do doctor = revisão estática independente; o nativo que
  aproxima é `analyze pyspark`. Dois `finding_id`s sobre a mesma linha
  são corroboração; divergência vira `unresolved`, não média.
- `status` do handoff (`completed|partial|failed|refused`) e
  `limitations` fazem parte da evidência — reporte-os.

## Revalidar depois de uma mudança

Mudança aplicada pede novo `delegate run` sobre o artefato novo — nunca
relê o handoff antigo como se fosse atual. O par antes/depois se compara
por `correlation_id` e pelos `finding_id`s persistidos; ausência do
finding na segunda leitura é sinal, não prova de correção (sem o custo do
run que não aconteceu, não há ganho declarável — o schema recusa afirmar
quanto se economizaria).

## Quando NÃO usar

- O artefato já responde via extrator nativo (`analyze pyspark`,
  `analyze event-log`, `analyze plan`, `judge`) — delegar duplica
  evidência e custa contexto.
- O artefato não existe ainda: especialista nenhum coleta por você —
  `collect *` é nativo, e sentinel/doctor leem artefato já exportado.
- Especialista `DISCOVERED` mas não `VERIFIED` — não force com
  `--allow-unverified` nem contorne; o nome do estado é a resposta.
- Capabilities de nuvem sem autorização do operador para
  `EXTERNAL_READ`/`COST_BEARING`.
- Qualquer execução fora da fronteira `delegate` — você nunca monta argv
  de especialista à mão nem executa `data-sentinel`/`forge-doctor-data`
  direto; ops governadas registradas apenas.

## Referência rápida

Entrada: artefato exportado ou diretório de projeto + intenção + (para
nuvem) autorização de risco concedida. Saída: `DelegationResult` com
findings, handoff selado em `.sparkforge_aws/delegation/handoffs/`,
refusals nomeadas (`provider-absent`, `version-incompatible`,
`capability-absent`, `policy-refusal`, `cycle-detected`,
`budget-exhausted`, `timeout`, `runtime-error`, `invalid-output`,
`insufficient-evidence`) e fallback `native-analysis` quando o
especialista está ausente.

## Red flags

Delegar antes de rodar o nativo; tratar finding do especialista como
CONFIRMED quando veio POSSIBLE/UNKNOWN; executar capability de nuvem sem
`--authorize`; inventar argv ou flag que não está no manifesto;
reinterpretar recusa nomeada como "serviço quebrado" em vez de estado;
ler handoff velho como evidência de estado novo; somar custo de
especialista no custo do run sem `dpu_seconds`.

## Contrato de qualidade SparkForge (v1)

Esta skill trata **delegação governada a especialistas opcionais**.
Contrato comum, sem substituir o procedimento específico acima:

- **Entrada mínima:** artefato/alvo real e intenção; se faltar, registre o
  `*.unresolved` correspondente.
- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou
  origem de medição; aplique regra por `rule_id` e versão, nunca por
  memória. Findings do especialista citam `handoff_path` e `run_id`.
- **Verbos primários:** `sparkforge-aws delegate discover`, `delegate plan`,
  `delegate run`, `delegate handoffs`. Use-os na ordem indicada e conserve
  saída estruturada.
- **Saída:** fatos, findings, hipóteses e recomendações separados.
  Recomendação usa `title`, `severity`, `confidence`, `evidence`,
  `root_cause`, `proposed_change`, `expected_effect`, `risks`,
  `tradeoffs`, `validation` e `rollback`.
- **Validação:** reexecute o especialista sobre o artefato novo após a
  mudança e valide dados; ausência de finding é ausência de proxy, não
  prova.
- **Rollback e segurança:** a fronteira é read-only por construção;
  capabilities de nuvem exigem grant explícito por nível de risco e são
  revertíveis por não-mutação — o rollback é "não executar", e o registro
  fica no handoff persistido.
- **Referências e eval:** `../_shared/references/evidence-first.md`,
  `../_shared/references/evaluation-contract.md`,
  `../_shared/references/operational-safety.md`; casos em
  `evals/evals.json`; `scripts/validate_evidence.py` verifica o envelope
  antes do handoff.
