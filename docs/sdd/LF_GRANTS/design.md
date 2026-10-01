---
sdd: 1
feature: LF_GRANTS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/LF_GRANTS/define.md
  sha256: "637fa1bfb9d62e6e5beb074a272d68362dd03d2b966258976a74d765958ed71a"
files:
  - {path: tests/test_lakeformation_missing_grant.py, action: create, reason: "testes de AC1 a AC11 e AC13, escritos antes do codigo"}
  - {path: sparkforge/facts/lakeformation_missing_grant.py, action: create, reason: "extrator derivado: EMITTED_KINDS lakeformation.missing_grant e .unresolved, SOURCE_KINDS, build_missing_grant(facts) e o carregador da tabela operacao->permissao"}
  - {path: knowledge/glue/lakeformation-permissions.yaml, action: create, reason: "tabela operacao->permissao como dado, uma linha por operacao, cada linha com source e quote literal da fonte T1"}
  - {path: sparkforge/facts/fusion.py, action: modify, reason: "fuse() chama build_missing_grant depois de build_lakeformation (o access_model precisa existir antes), guardado por SOURCE_KINDS como o timeout_diagnosis"}
  - {path: sparkforge/lakeformation/graph.py, action: modify, reason: "build_access_graph le lakeformation.missing_grant quando existe; sem ele, caminho atual intocado"}
  - {path: tests/test_lakeformation_access_graph.py, action: modify, reason: "AC14 e a guarda AC15"}
  - {path: rules/catalog/lakeformation.yaml, action: modify, reason: "regra SF-LF-011, requires_facts [lakeformation.missing_grant], runtime_scope {} com a razao escrita"}
  - {path: tests/test_lakeformation_rules.py, action: modify, reason: "AC12"}
  - {path: knowledge/errors/lakeformation/access_denied_cross_account.json, action: modify, reason: "AC13: ram.unaccepted_share declarado fora de alcance, lakeformation.missing_grant passa a ser emitido"}
  - {path: rules/catalog/errors.yaml, action: modify, reason: "comentario de SF-ERR-006/014 que afirma que lakeformation.missing_grant nao e emitido deixa de ser verdade"}
  - {path: fixtures/cloudwatch_logs, action: modify, reason: "D11: duas fixtures novas (lf_negado_fta_append_sem_all, positiva; lf_negado_fta_grant_all, negativa) e o golden regenerado das duas lf_negado_* existentes, que passam a carregar lakeformation.missing_grant.unresolved"}
  - {path: tests/test_fixtures_golden_cloudwatch_logs.py, action: modify, reason: "D11: runner extrai input/lf/ com extract_lakeformation_tree e deriva build_missing_grant depois do matcher; REQUIRED_FIXTURES ganha as duas"}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "D11: regen_cloudwatch_logs identico ao runner (par)"}
  - {path: tests/test_harness_untrusted.py, action: modify, reason: "registro snippet_measure: _derivados_de_facts ganha a chamada de build_missing_grant, senao a guarda fail-closed derruba test_a_enumeracao_do_documento_bate_com_a_medida"}
  - {path: sparkforge/simulate/diff.py, action: modify, reason: "D12: DERIVED_KINDS inclui lakeformation_missing_grant.EMITTED_KINDS, senao o simulate rederiva de um lado so"}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "registro reachability_lists: o extrator novo entra nas duas listas EXTRACTORS"}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "registro fixture_kind_coverage: o extrator novo e o golden de SF-LF-011"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "registro sources_lock: lf-permissions-reference.html entra (security-access-control-fta.html ja esta), via refresh_knowledge --update --offline"}
  - {path: manifest.json, action: modify, reason: "registro manifest_rule_count: rule_count +1"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "registro status_numbers: extratores, kinds e regras na tabela Numeros correntes"}
  - {path: docs/claims.lock.json, action: modify, reason: "registro claims_gate: arquivo .py novo move as alegacoes de corpus"}
decisions:
  - id: D1
    choice: "Extrator derivado em arquivo proprio, chamado por fuse() logo depois de build_lakeformation, guardado por SOURCE_KINDS = {error.signature_match}. Sem ERR-LF-* no pool, o fuse fica identico (AC9)."
    rejected:
      - "verbo de composicao sem fact (abordagem B do explore): judge ficaria cego"
      - "derivar dentro de sparkforge/errors/matcher.py (abordagem C): o matcher recebe log, nao a uniao dos facts"
      - "estender sparkforge/facts/lakeformation.py: ele deriva de configuracao, e este de falha mais permissao; juntar misturaria dois SOURCE_KINDS num modulo de 400 linhas"
    rollback: "git revert do commit do extrator e da chamada em fusion.py; o fuse volta a nao emitir lakeformation.missing_grant, e SF-LF-011 fica sem fact (requires_facts pula)."
  - id: D2
    choice: "Tabela operacao->permissao em knowledge/glue/lakeformation-permissions.yaml, lida via sparkforge/knowledge_ref.py (nunca Path(__file__).parents). Cada linha tem operation, model, permission, resource_level, source (URL) e quote literal. Quatro linhas: read->SELECT; write/delete sob FTA->ALL; create->CREATE_TABLE no database e DATA_LOCATION_ACCESS condicional; alter->ALTER."
    rejected:
      - "tabela em codigo Python: nenhum gate conferiria a citacao, o mesmo defeito que lakeformation_matrix.py corrigiu em 2026-09-09"
      - "linha nova dentro de lakeformation-matrix.yaml: aquela guarda capacidade por runtime, e esta permissao por operacao; perguntas diferentes"
      - "INSERT para escrita (referencia generica do LF): a pagina de FTA do Glue exige ALL para job Spark, e ela e a mais especifica"
    rollback: "git revert do commit do yaml e do sources.lock; refresh_knowledge --update --offline realinha o lock."
  - id: D3
    choice: "Operacao lida de pyspark.read (-> read), pyspark.write (mode overwrite -> overwrite; qualquer outro ou ausente -> write) e sql.write_statement (insert_into, merge_into, update -> write; insert_overwrite, delete_from -> overwrite; create_table, create_table_as -> create). Operacao com target que casa o recurso (igual, ou igual a parte depois do ultimo ponto) e a usada; sem target nenhum, todas; com targets e nenhum casando, unresolved operacao_nao_ligada_ao_recurso. Uma derivacao por operacao, nenhuma escolhida."
    rejected:
      - "operacao declarada no case.yaml: campo novo que ninguem mede (rejeitada no explore)"
      - "assumir leitura sem fact: acusa SELECT num job que falhou escrevendo"
    rollback: "git revert do commit do extrator."
  - id: D4
    choice: "Recurso: regex 'on\\s+(\\S+)' sobre attrs.matched_line (caminho de log) ou attrs.matched_class (caminho de excecao). Sem captura, o candidato unico vem de lakeformation.grant/registered_location do pool; com mais de um, unresolved recurso_ambiguo. Grants sao cruzados por principal = role do job (iam.access_decision.role_arn, ou candidato unico dos grants)."
    rejected:
      - "estender o matcher para emitir o recurso: muda um extrator que ja tem golden, e o texto e truncado em 200 caracteres ali"
    rollback: "git revert do commit do extrator."
  - id: D5
    choice: "Versao do Glue vem de env.runtime_signal com component=glue e distinct_versions == 1. Na falta dele, de tf.attribute glue_version literal unico. Nada disso presente: unresolved runtime_ausente. Mais de um valor: unresolved runtime_divergente. O eixo fgac_spark_native_write e lido por lakeformation_matrix.capability(runtime, eixo)."
    rejected:
      - "supor a versao mais recente: erro de versao (regra 31)"
      - "chamar detect_runtime de dentro do extrator: ele recebe sources, nao facts, e duplicaria a resolucao que o judge ja faz"
    rollback: "git revert do commit do extrator."
  - id: D6
    choice: "Lado IAM sob FGAC: acao exigida vem da tabela (write -> s3:PutObject; overwrite/delete -> s3:PutObject e s3:DeleteObject, pela secao 6 opcao 1 de lakeformation-fgac.md). O fact copia decision e denied_by de iam.access_decision. Acao nao simulada: unresolved acao_iam_nao_simulada, nomeando a acao para collect iam-access."
    rejected:
      - "acusar o grant do LF sob FGAC na escrita: pela secao 2 e 6, quem autoriza escrita sob FGAC e o IAM do runtime role"
    rollback: "git revert do commit do extrator."
  - id: D7
    choice: "SF-LF-011 com runtime_scope {} (a versao ja e resolvida no fact, e o gate real e requires_facts), severity P1, acao investigate, reversible true. O finding nomeia permission, side e denied_by lidos do fact, e nao propoe grant (fora de escopo)."
    rejected:
      - "runtime_scope {glue: '>=5.0'}: etiqueta de servico disfarcada de guarda de versao, o defeito que docs/gates-por-mudanca.md descreve"
      - "P0: a falha ja aconteceu e o job ja parou; o achado nomeia o conserto, nao agrava a severidade da falha que SF-ERR-006 ja da"
    rollback: "git revert do commit da regra; manifest rule_count volta com o mesmo revert."
  - id: D8
    choice: "build_access_graph: quando ha lakeformation.missing_grant com side=lf para o par (tabela, principal), a aresta lf_grant sai missing com a evidencia 'exige <permission> para <operation>'. Sem o fact, o bloco atual (SELECT ou ALL) roda sem mudanca."
    rejected:
      - "remover o SELECT fixo: quebra saidas e goldens atuais (rejeitada no explore)"
    rollback: "git revert do commit do grafo; a guarda AC15 continua passando."
  - id: D9
    choice: "Modelo de acesso: algum lakeformation.access_model com model=both -> unresolved modelo_both; com model=fgac -> FGAC; senao, lakeformation.filesystem com lf_credentials_resolver_declared=true ou lakeformation.iceberg_catalog com lakeformation_enabled=true -> FTA; nada disso -> unresolved modelo_ausente. Motivo medido: sparkforge/facts/lakeformation.py nao emite access_model para job so de FTA (docstring de _access_models), e a superficie de FTA e o filesystem e o catalogo."
    rejected:
      - "ler so lakeformation.access_model (como o explore dizia): todo job FTA sairia modelo_ausente"
      - "chamar _marcadores_de_fta: funcao privada de outro modulo; os dois fatos derivados ja carregam o mesmo sinal"
    rollback: "git revert do commit do extrator."
  - id: D10
    choice: "Gatilho so ERR-LF-001 ('Insufficient Lake Formation permission(s) on'). ERR-LF-002 a 005 nomeiam acao IAM ou validacao de seguranca, e ja tem SF-ERR-014 a 017; SOURCE_KINDS = {error.signature_match} guarda o fuse, e o extrator filtra signature_id == ERR-LF-001."
    rejected:
      - "todo ERR-LF-*: ERR-LF-003 (lakeformation:GetDataAccess negado) e falta de IAM de credential vending, nao de grant; acusaria grant ausente com o grant no lugar"
    rollback: "git revert do commit do extrator."
  - id: D11
    choice: "Golden no corpus fixtures/cloudwatch_logs, que ja extrai log, Terraform, .py, build_lakeformation e o matcher. Ganha a guarda de diretorio input/lf/ para o artefato de collect lakeformation e build_missing_grant no fim. Os cenarios de AC1 a AC9 ficam em teste unitario sobre Fact em memoria (sinteticos); o golden prende o caminho inteiro com uma positiva e uma negativa."
    rejected:
      - "corpus fixtures/lakeformation: o runner dele varre input/*.json inteiro como artefato de lakeformation, e o log e json; exigiria reestruturar tres fixtures existentes"
      - "uma fixture de golden por AC: nove diretorios para cenarios que o teste unitario ja fixa, e cada um move REQUIRED_FIXTURES e o golden"
    rollback: "git revert do commit das fixtures; python scripts/regen_fixtures.py regenera os goldens das duas lf_negado_* ao estado anterior junto com o revert do runner."
  - id: D12
    choice: "sparkforge/simulate/diff.py DERIVED_KINDS passa a incluir lakeformation_missing_grant.EMITTED_KINDS."
    rejected:
      - "deixar fora: strip_derived nao tiraria o fact, o fuse do lado simulado o derivaria de novo, e o diff mostraria duplicata que o --set nao causou"
    rollback: "git revert do commit."
covers:
  - {part: "extrator derivado", acceptance: [AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC13, AC17]}
  - {part: "tabela operacao->permissao", acceptance: [AC10]}
  - {part: "chamada em fuse()", acceptance: [AC11]}
  - {part: "regra SF-LF-011 e fixtures", acceptance: [AC12]}
  - {part: "grafo de acesso", acceptance: [AC14, AC15]}
  - {part: "registros manuais", acceptance: [AC16]}
---

# LF_GRANTS — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| extrator derivado | `sparkforge/facts/lakeformation_missing_grant.py`, `tests/test_lakeformation_missing_grant.py` | AC1–AC9, AC13, AC17 |
| tabela operação→permissão | `knowledge/glue/lakeformation-permissions.yaml` | AC10 |
| chamada em `fuse()` | `sparkforge/facts/fusion.py` | AC11 |
| regra e fixtures | `rules/catalog/lakeformation.yaml`, `fixtures/cloudwatch_logs/` (D11), runner e regen do golden | AC12 |
| grafo | `sparkforge/lakeformation/graph.py` | AC14, AC15 |
| registros | listas `EXTRACTORS`, `simulate/diff.py` (D12), `manifest.json`, `STATUS.md`, `sources.lock.json`, `claims.lock.json` | AC16 |

## Fluxo do extrator

```
error.signature_match ERR-LF-001 (D10)?  -- nao --> nada (AC9)
  | sim
recurso (D4) -- ambiguo --> unresolved recurso_ambiguo
operacoes (D3) -- nenhuma --> unresolved operacao_nao_medida (AC8)
modelo (D9: access_model, filesystem, iceberg_catalog) -- both/ausente --> unresolved (AC6)
  FTA escrita com registered=false medido --> unresolved fta_escrita_em_alvo_nao_registrado (AC17)
  FTA  -> permissao da tabela (D2) vs grant do par -> missing_grant side=lf | nada (AC1, AC2, AC3)
  FGAC leitura -> SELECT vs grant -> idem
  FGAC escrita:
     runtime (D5) -- ausente/divergente --> unresolved (AC6)
     eixo fgac_spark_native_write not_supported --> unresolved escrita_fgac_nao_suportada_no_runtime (AC7)
     registered_location registered=true --> unresolved conflito_declarado_fgac_escrita_registrada (AC5)
     iam.access_decision da acao (D6) -- nao simulada --> unresolved acao_iam_nao_simulada
                                     -- != allowed --> missing_grant side=iam, denied_by (AC4)
```

A regra de cobertura é a da referência. `ALL` (`Super`) cobre qualquer permissão de
tabela. `SELECT` e `ALL` são checados em `lakeformation.grant.attrs.permissions` e nas
flags `has_select`/`has_all`, que o extrator de grants já emite.

## Conhecimento consultado

Tudo lido em 2026-09-21:
- `https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html`
  (lido por WebFetch). Dali vêm `CREATE_TABLE` no database, `DATA_LOCATION_ACCESS`
  ("not needed to query or update underlying data"), `ALTER` na tabela e `INSERT`
  genérico.
- §5 de `knowledge/glue/lakeformation-fgac.md`, que cita
  `security-access-control-fta.html`: "AWS Glue Spark jobs that write/delete data in
  Amazon S3 require AWS Lake Formation ALL permission."
- §6 de `knowledge/glue/lakeformation-fgac.md`, opção 1: a escrita do runtime role usa
  `s3:PutObject`, `s3:DeleteObject` e KMS. O conflito das frases C e D fica declarado.
- Eixo `fgac_spark_native_write` em `knowledge/glue/lakeformation-matrix.yaml`.
- `sparkforge/errors/matcher.py`: `matched_line` com no máximo 200 caracteres no caminho de
  log.
- `sparkforge/facts/runtime_detect.py`: `env.runtime_signal`, com `component` e
  `resolved`.

## Revisão de 2026-09-21, antes do plan

A leitura para escrever o plan mediu quatro coisas que o desenho aprovado não tinha, e
elas entram como D9 a D12, com o manifesto ajustado:

- **D9.** Job só de FTA não gera `lakeformation.access_model`. O modelo sai também de
  `filesystem` e `iceberg_catalog`.
- **D10.** Só `ERR-LF-001` é mensagem de grant ausente. `ERR-LF-002` a `005` falam de
  ação IAM e já têm regra própria.
- **D11.** O golden vai para `fixtures/cloudwatch_logs`, porque o runner de
  `fixtures/lakeformation` lê todo `*.json` como artefato de permissão.
- **D12.** `sparkforge/simulate/diff.py` guarda uma terceira lista de kinds derivados, e o
  kind novo precisa entrar nela.

Saíram do manifesto, por medida:
- `docs/surface.lock.json`: `sparkforge/observability/surface.py` mede só `*.md` de
  `knowledge/`, e o YAML novo não move a superfície.
- `tests/test_rule_scope_by_nature.py`: a área `SF-LF` já tem regra com
  `runtime_scope: {}` (`SF-LF-008`), então acrescentar mais uma não muda o agregado.

O registro `snippet_measure` é `_derivados_de_facts` em `tests/test_harness_untrusted.py`. O
extrator novo, derivado de facts, precisa de uma chamada ali, e ela entrou no manifesto.
