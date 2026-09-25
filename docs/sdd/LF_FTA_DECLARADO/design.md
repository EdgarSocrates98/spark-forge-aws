---
sdd: 1
feature: LF_FTA_DECLARADO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/LF_FTA_DECLARADO/define.md
  sha256: "858b1e993a77e71a7671de6a59afb1960dcd1139cc89ae4ebfdbd4065ac716b5"
files:
  - {path: tests/test_facts_lakeformation.py, action: modify, reason: "TestFtaDeclarado (AC1, AC2), escrita antes do codigo; o teste de contrato do modulo passa a cobrir o kind novo"}
  - {path: sparkforge/facts/lakeformation.py, action: modify, reason: "_fta_declarados() e o kind em EMITTED_KINDS"}
  - {path: tests/test_lakeformation_rules.py, action: modify, reason: "TestSfLf010 (AC4, AC5)"}
  - {path: rules/catalog/lakeformation.yaml, action: modify, reason: "SF-LF-010 ganha absent de lakeformation.fta_declared; title, explanation, risks e rollback dizem isso"}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "comentario de ALLOWED_SET_LEVEL de SF-LF-010 passa a nomear os dois absent"}
  - {path: tests/test_fixtures_golden_cloudwatch_logs.py, action: modify, reason: "teste de AC6 sobre os goldens commitados"}
  - {path: fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all/meta.yaml, action: modify, reason: "expects_kinds ganha o kind, expects_rules perde SF-LF-010, proves perde a lacuna"}
  - {path: fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all/expected/facts.json, action: modify, reason: "regenerado"}
  - {path: fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all/expected/findings.json, action: modify, reason: "regenerado; SF-LF-010 sai"}
  - {path: fixtures/cloudwatch_logs/lf_negado_fta_grant_all/meta.yaml, action: modify, reason: "idem"}
  - {path: fixtures/cloudwatch_logs/lf_negado_fta_grant_all/expected/facts.json, action: modify, reason: "regenerado"}
  - {path: fixtures/cloudwatch_logs/lf_negado_fta_grant_all/expected/findings.json, action: modify, reason: "regenerado; SF-LF-010 sai"}
  - {path: docs/guia/usos/lake-formation-e-acesso.md, action: modify, reason: "a secao que dizia que SF-LF-010 dispara em FTA como lacuna"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "numeros que moverem (kinds 245 para 246) e a lacuna fechada"}
decisions:
  - id: D1
    choice: "Nome lakeformation.fta_declared. Os kinds do modulo sao substantivos da superficie (access_model, filesystem); este e o predicado que a regra pergunta, e o nome casa com o atributo de onde ele nasce (lf_credentials_resolver_declared) e com o verbo do texto da regra (declara)."
    rejected: ["lakeformation.access_model com model fta: o docstring de _access_models recusa por escrito dar ao FTA uma declaracao ancorada numa chave qualquer, e mudaria SF-LF-009, SF-LF-011 e o grafo", "absent: lakeformation.filesystem: sai tambem so com fs.s3.impl, e calaria a regra no job que nao pede credencial do Lake Formation"]
    rollback: "git revert do commit do extrator; SF-LF-010 volta a disparar em FTA e os goldens voltam com o revert do commit das fixtures."
  - id: D2
    choice: "Emitido dentro de build_lakeformation, derivado da lista de lakeformation.filesystem ja montada: um fta_declared por fact de filesystem com lf_credentials_resolver_declared true, copiando subject e provenance dele, com attrs marker (a chave do resolver), emrfs_restored, source e extractor. Sai por fuse() e pelos goldens sem chamada nova."
    rejected: ["modulo novo: o predicado mora ao lado do fact de onde deriva, e um modulo novo pediria entrada nas duas listas manuais e em fuse()", "um fact por case: perderia a procedencia (terraform, code, event_log) que o filesystem ja separa"]
    rollback: "git revert do commit do extrator."
  - id: D3
    choice: "SF-LF-010 ganha absent: lakeformation.fta_declared ao lado de absent: lakeformation.access_model. Title passa a 'nem controle de acesso fino nem o resolver de credencial do Full Table Access'; explanation diz que FTA entra pelo resolver; risks nomeiam que FTA declarado e ineficaz (S3A no 5.1) tambem cala a regra e que o marcador por catalogo sozinho nao conta; rollback diz que remover o modelo declarado, FGAC ou o resolver, devolve o job ao estado anterior."
    rejected: ["regra nova so para FTA: a pergunta e a mesma, e duplicaria a acusacao"]
    rollback: "git revert do commit da regra; os goldens das duas fixtures FTA voltam a ter SF-LF-010 no regen."
  - id: D4
    choice: "Goldens pelo scripts/regen_fixtures.py oficial, com o diff lido fixture a fixture. Toda fixture com o resolver do Lake Formation declarado ganha o fact; so as que tem localizacao registrada perdem SF-LF-010. Golden em que SF-LF-010 some sem resolver declarado e defeito e para o build."
    rejected: ["editar expected/*.json a mao"]
    rollback: "git revert do commit das fixtures."
covers:
  - {part: "extrator", acceptance: [AC1, AC2, AC3]}
  - {part: "regra", acceptance: [AC4, AC5]}
  - {part: "goldens e registros", acceptance: [AC6, AC7, AC8]}
---

# LF_FTA_DECLARADO — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| extrator | `tests/test_facts_lakeformation.py`, `sparkforge/facts/lakeformation.py` | AC1, AC2, AC3 |
| regra | `tests/test_lakeformation_rules.py`, `rules/catalog/lakeformation.yaml`, `tests/test_rules_catalog_reachability.py` | AC4, AC5 |
| goldens e registros | `tests/test_fixtures_golden_cloudwatch_logs.py`, as duas fixtures FTA, guia, `STATUS.md` | AC6, AC7, AC8 |

As outras fixtures com o resolver declarado (`get_data_access_negado_com_resolver`,
`infra_code/fgac_com_fta_no_mesmo_job`, `infra_code/fta_sem_emrfs_no_51`,
`lakeformation/conta_sem_full_table_access`) ganham o fact no `facts.json` e o kind no
`expects_kinds`; nenhuma delas tem `SF-LF-010` hoje, então os findings não mudam. Se o regen
mostrar outra coisa, entra como desvio no build.

## Conhecimento consultado

- `rules/catalog/lakeformation.yaml`, `SF-LF-010` (lida no arquivo; o MCP do SparkForge
  não conectou nesta sessão).
- Docstring de `_access_models` e `_marcadores_de_fta` em `sparkforge/facts/lakeformation.py`:
  as duas chaves que a documentação da AWS publica como pedido de credencial do FTA.
- `knowledge/glue/lakeformation-fgac.md` §5 (FTA e EMRFS) e §7 (chave por catálogo, a
  verificar), pelas citações do próprio módulo.
