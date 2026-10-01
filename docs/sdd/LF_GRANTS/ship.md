---
sdd: 1
feature: LF_GRANTS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/LF_GRANTS/build_report.md
  sha256: "80a440606ffac8ea06f831a50f43ec26dbb14ef06f6422c8ef101e87d7458188"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, rules_catalog_gates, manifest_rule_count, runtime_scope_gates, offline_manifest, sources_lock, verify_wheel, status_numbers_gate, claims_gate, sync_skills, agents_parity]
deviations:
  - "Seis commits na T2 onde o plano previa um: quatro passes de revisão de qualidade, quase todos sobre o texto do gatilho, que é um trecho de 200 caracteres da mensagem (design D5 tratou a leitura do recurso como um regex só)."
  - "Tarefa extra fora do manifesto, por decisão do operador: sparkforge/facts/pyspark_ast.py passou a gravar o modo de escrita (mode=, insertInto(overwrite=), saveMode=, último .mode()) e a marcar mode_unresolved (21966c09, 2c05ac47)."
  - "Decisão do operador: sob FGAC, sem registro coletado, o fact recusa registro_nao_coletado em vez de presumir tabela não registrada."
  - "Lado IAM mais estreito que o design: implicitDeny só acusa em <localização>/*, explicitDeny em recurso que contém a tabela; decisões contraditórias recusam; a acusação declara registration_scope, caveat e unchecked."
  - "Tabela de permissões: sob FGAC, write e overwrite exigem s3:PutObject e s3:DeleteObject, pela fonte getting-started-min-privs-job, que não separa os dois (o design separava sem fonte); ListBucket e KMS ficam em unchecked."
  - "Agent sf-lake-formation-specialist e skill diagnose-lakeformation-access passaram a listar SF-LF-011 (fora do manifesto; espelhos sincronizados, referência regenerada)."
  - "Registros descobertos só na verificação final: lakeformation_missing_grant na lista SO_AWS de tests/test_databricks_rule_audit.py, contagem de governança SF-LF 10 para 11, SF-GLUE-004 fora da dívida de mutação, STATUS e claims relidos à mão."
  - "O D2 do design prometia alter e DATA_LOCATION_ACCESS condicional no create; a tabela não tem as duas linhas (inerte: _SQL não produz alter, e o create sai recusado)."
  - "A hipótese pedia fixtures em fixtures/lakeformation/; a medida saiu de cenários em memória no teste da regra (judge sobre cada um) e de um par de goldens em fixtures/cloudwatch_logs/."
  - "Por pedido do operador, a partir da T5 cada tarefa rodou só o próprio teste e ruff; goldens e gates de número rodaram uma vez, na verificação final."
  - "O manifesto offline de knowledge/ ficou com o hash antigo de lakeformation-fgac.md e lakeformation-index.md até o ship; regravado em a6945973 com _content_sha256."
  - "Docs: só as pt-br que a feature toca; o espelho en-us vai para a feature DOCS_EN."
---

# LF_GRANTS — entrega

## Hipótese

Confirmada, com a medida inteira da previsão:

- FTA com escrita, FTA com leitura e FGAC com escrita: `judge` emite `SF-LF-011`
  nomeando a permissão e o lado (`tests/test_lakeformation_rules.py::test_sf_lf_011_dispara_so_com_permissao_nomeada`,
  sobre os cenários `cenario_fta_append_sem_all`, `cenario_fta_leitura_sem_select` e
  `cenario_fgac_escrita_negada`; e o golden `fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all`
  pelo caminho inteiro do log ao finding).
- Negativa: com o grant que cobre, `SF-LF-011` não dispara (mesmo teste,
  `cenario_grant_que_cobre`, e o golden `lf_negado_fta_grant_all`).
- Conflito da §6, modelo `both` e operação sem fact saem
  `lakeformation.missing_grant.unresolved` com a razão nomeada
  (`test_fgac_escrita_registrada_e_conflito_declarado`,
  `test_modelo_ou_runtime_desconhecido_recusa_por_nome`, `test_sem_operacao_recusa_por_nome`).

Nenhuma fixture de acusação saiu `unresolved`, e a negativa não disparou.

## Gates rodados

Rodados na seção de `docs/gates-por-mudanca.md` de cada `change_kind` do define, mais a
de agent e skill (tocados fora do manifesto), sobre `121ef24a` e, para o manifesto
offline, de novo sobre `a6945973`:

| Registro | Comando | Exit |
|---|---|---|
| reachability_lists, fixture_kind_coverage, snippet_measure | `pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py` | 0 (731 passed) |
| rules_catalog_gates, manifest_rule_count | `pytest` loader, reachability, result_axis, engine, agent_coverage, router_agents, docs_coverage, kind_coverage, refresh_knowledge, threshold_mutation | 0 (992 passed) |
| runtime_scope_gates | `pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py` | 0 (646 passed) |
| offline_manifest, sources_lock | `pytest tests/test_offline_expansion.py` e `python scripts/verify_offline_bundle.py` | 1 sobre `121ef24a` (hash velho de dois documentos); 0 sobre `a6945973` (4 passed, 56 conferidos) |
| verify_wheel | `python scripts/verify_wheel.py` | 0 |
| status_numbers_gate | `python scripts/check_status_numbers.py --strict` | 0 |
| claims_gate | `python scripts/check_vnext_claims.py`, `pytest tests/test_vnext_claims.py`, `pytest tests/test_docs_coverage.py tests/test_installed_provenance.py` | 0 (147; 27 passed e 5 skipped) |
| sync_skills, agents_parity | `python scripts/sync_skills.py --check`, `pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py` | 0 (202 passed) |

A suíte inteira rodou em lotes na verificação final do build (registrada no
`build_report.md`): verde, fora os três arquivos que o SDK `mcp` 1.30 do ambiente derruba.
Crescimento de superfície declarado nos commits `7594ace0` (skills +1608, knowledge +85)
e `bad38e3d` (skills +619, knowledge +726).

## Comandos `kind: command` do define

- AC16: `python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py`, exit 0.

## Pendências

- `SF-LF-010` dispara em job que declara Full Table Access: a regra pede
  `absent: lakeformation.access_model`, e um job só de FTA não produz esse kind. Anterior a
  esta feature; exige predicado derivado (regra 33).
- O SDK `mcp` 1.30 do ambiente local derruba `tests/test_adapters_mcp.py`,
  `tests/test_doctor.py` e `tests/test_run_debate.py`. Nenhum arquivo por trás deles mudou.
- Espelho en-us das docs e revisão de todos os guias: feature `DOCS_EN`.
- O `verified_by` de AC10 não confere o lock de fontes; quem confere é
  `test_fontes_da_tabela_estao_no_lock`, que o define não cita.
- Grafo: o casamento do grant ainda usa `startswith(target_table + "#")` com caixa, e o do
  fact usa `casa_tabela`.

## Lições

- O texto que o gatilho carrega é um trecho de 200 caracteres de uma mensagem que o
  extrator não controla; tratá-lo como "um regex só" custou quatro passes de revisão na T2.
  Feature que lê texto de log deve listar, no design, o corte, as formas de pontuação e o
  que acontece quando a cláusula some.
- Fixture com `*` escondeu a semântica do `SimulatePrincipalPolicy`: `implicitDeny` em `*`
  não fala por uma tabela. Fixture de IAM deve usar o recurso escopado da tabela.
- Linha de tabela de dado citado precisa ter o `requires` escrito na própria `quote`; o
  teste que conferia só "tem quote" deixou passar uma divisão write/overwrite sem fonte até
  a revisão final.
