---
sdd: 1
feature: LF_FTA_DECLARADO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/LF_FTA_DECLARADO/plan.md
  sha256: "26bd164b2eeced5aa8a0e01b34ccafd348392877d6ea8be7c781a9edab200ac5"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta tests/test_facts_lakeformation.py::TestFtaDeclarado::test_resolver_do_lake_formation_declara_fta tests/test_facts_lakeformation.py::TestFtaDeclarado::test_so_a_superficie_com_resolver_declara_fta -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta tests/test_facts_lakeformation.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta tests/test_lakeformation_rules.py::TestSfLf010::test_registrado_com_fta_declarado_nao_dispara tests/test_lakeformation_rules.py::TestSfLf010::test_registrado_so_com_fs_s3_impl_continua_disparando -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta tests/test_lakeformation_rules.py tests/test_rules_catalog_reachability.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta tests/test_fixtures_golden_cloudwatch_logs.py::test_fta_declarado_cala_sf_lf_010_nos_goldens tests/test_fixtures_kind_coverage.py::test_every_kind_of_every_extractor_appears_in_some_golden -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta tests/test_fixtures_golden_cloudwatch_logs.py tests/test_fixtures_golden_infra_code.py tests/test_fixtures_golden_lakeformation.py tests/test_fixtures_kind_coverage.py -q", exit: 0}
claims:
  - text: "T1 viu os dois testes de TestFtaDeclarado falharem com zero lakeformation.fta_declared, e passarem depois de _fta_declarados (commit 58473a3b)."
    evidence_ref: "tests/test_facts_lakeformation.py::TestFtaDeclarado::test_resolver_do_lake_formation_declara_fta"
  - text: "T2 viu SF-LF-010 disparar com o resolver declarado, e calar depois do segundo absent; o caso so com fs.s3.impl disparou antes e depois (commit 33ac2c31)."
    evidence_ref: "tests/test_lakeformation_rules.py::TestSfLf010::test_registrado_com_fta_declarado_nao_dispara"
  - text: "T3 viu os goldens commitados com SF-LF-010 e sem o kind (3 falhas), e passarem depois do regen (commit 759c7843); diff de findings so remove SF-LF-010 nas duas fixtures FTA e muda texto em grant_de_leitura_em_local_registrado, que continua disparando."
    evidence_ref: "tests/test_fixtures_golden_cloudwatch_logs.py::test_fta_declarado_cala_sf_lf_010_nos_goldens"
change_id: null
---

# LF_FTA_DECLARADO — relatório do build

## Desvios do plano

- `scripts/regen_fixtures.py` sem argumento não regenera `fixtures/lakeformation/`: o
  primeiro regen deixou `conta_sem_full_table_access` (resolver declarado) e
  `grant_de_leitura_em_local_registrado` (texto de `SF-LF-010`) velhos. Regenerados por nome,
  e o golden de lakeformation rodado de novo.
- Arquivos fora do manifesto do design: seis `meta.yaml` e `expected/*.json` de fixtures com o
  resolver (o design as previa como possíveis), `README.md`, `docs/guia/06-extrair-julgar-compor.md`,
  `docs/claims.lock.json`, `docs/harness/CODEINTEL-GAP.md` e o ADR-010 (números).
- O title de `SF-LF-010` não mudou (D3 previa mudar): com o segundo `absent`, "o job não
  declara modelo de acesso nenhum" ficou verdadeiro, e manter o title evitou mexer nas tabelas
  do guia e da referência. Explanation, risks e rollback mudaram.
- Controlador executou as tarefas direto, sem subagente por tarefa e sem revisão em dois
  estágios (feature de três tarefas, delegada inteira).

## Revisão

Sem revisão por subagente. Conferência do controlador: diff de findings de cada golden lido;
nenhum golden sem resolver perdeu `SF-LF-010`.

## Rodada de correção da revisão (2026-09-25)

Revisão por tarefa não foi feita; a revisão única, depois do ship, achou um crítico e cinco
menores. O que esta rodada fez:

- **C1.** `tests/test_fixtures_golden_scan.py::test_golden[misto]` falhava:
  `fixtures/scan/misto/repo/infra/main.tf:23` declara o resolver, e o `fuse` passou a
  emitir `lakeformation.fta_declared` (`after_fuse` 69 → 70). Regenerado por
  `SPARKFORGE_REGEN_SCAN=1`; a única diferença é essa contagem, e o fact novo é o único
  `lakeformation.fta_declared` do scan (`source: terraform`). Nenhum gate do ship rodava o
  golden de scan. Os 58 módulos `tests/test_fixtures_golden*.py` rodaram um por vez, e só o
  de scan falhou (commit `aa4e1450`).
- **M1.** Sem versão do Glue detectada, ou num Glue 4.0, nem `SF-LF-010` nem `SF-LF-004`
  acusam registrada + resolver + sem EMRFS; `SF-LF-004` sai em `skipped` por
  `runtime_scope`. Conferido à mão com `judge --show-skipped`; declarado em `risks` de
  `SF-LF-010` e nos *Limites declarados* do STATUS, sem mudar código.
- **M2.** O texto citava a §7 (que é sob FGAC) para não contar a chave de catálogo sozinha; a
  razão é a §5: FTA exige chave E resolver, e só o resolver faz o Lake Formation vender a
  credencial. Corrigido em `_fta_declarados` e em `risks`. A incoerência com
  `_marcadores_de_fta`, que conta a chave sozinha para `both`, ficou registrada, sem mudança.
- **M3.** `spark.conf.set` depois da sessão pode não chegar ao filesystem e ainda assim cala
  `SF-LF-010`: hipótese não verificada, declarada em `risks` e no docstring (commit
  `1a6ee077`). `grant_de_leitura_em_local_registrado` mudou só nesses `risks`.
- **M5.** O agente `sf-lake-formation-specialist` (e o `.codex`), a skill
  `lakeformation-fgac-guard` e `docs/aws/glue/6.0/lakeformation.md` ganharam o kind; espelhos
  por `sync_skills.py`, referência regenerada, superfície +157 bytes (commit `ff04d1ad`).
- **M6.** `fixtures/sarif/terraform/input/facts.json` é cópia estática de
  `infra_code/fgac_com_fta_no_mesmo_job`, feita à mão no PR #50; `regen_sarif` só grava
  `expected/`, e nada no repositório gera o `input/`. Ficou como está: difere da origem só
  pelo fact novo, e o golden de sarif passa.

Lacunas de `scripts/regen_fixtures.py`: sem argumento ele pula `fixtures/lakeformation/`,
`fixtures/iam_access/` e `fixtures/resource_link/`, e `fixtures/scan/` fica fora do script
(regenera pelo próprio teste, com `SPARKFORGE_REGEN_SCAN=1`).
