# DEFINE: Forge Pack

> Um pack de dados (regras, knowledge, fixtures) de terceiro carregado junto do core por `SPARKFORGE_PACKS`, com prefixo proprio e recusa nomeada, sem fork e sem importar codigo.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FORGE_PACK |
| **Date** | 2026-09-12 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Uma equipe de plataforma que quer regras e knowledge proprios sobre os mesmos artefatos (Terraform, PySpark, event log) precisa hoje de fork do SparkForge, porque o core le regras de uma raiz so (`catalog_dir()`) e knowledge de uma raiz so (`knowledge_dir()`). O efeito colateral e que todo padrao especifico de empresa vira pedido de regra no core, e o core cresce -- o contrario do "sistema central pequeno e confiavel" do §5 de `prompt_new_evo.md`.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Equipe de plataforma de dados | Mantem padroes internos de job Glue (tags, configuracao de seguranca, convencao de worker) | Padrao interno vira fork do SparkForge ou revisao manual de PR |
| Mantenedor do SparkForge | Cura as 190 regras do core | Pedido de regra especifica de empresa entra no core e nao serve a mais ninguem |
| Agente host via MCP (Claude Code, Devin) | Chama `judge`, `root_cause`, `simulate` | Precisa ver as regras do pack sem parametro novo em cada tool |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: modulo puro `sparkforge/packs/`: `SPARKFORGE_PACKS` com diretorios separados por `os.pathsep`, cada um resolvido para caminho absoluto e exigido existente; `pack.yaml` com `id`, `version`, `prefix`, `core` (faixa de versao do SparkForge) e o conteudo (`rules/`, `knowledge/`, `fixtures/`); nenhum `import` de arquivo do pack |
| **MUST** | G2: recusas nomeadas, e pack recusado sai INTEIRO: `manifesto_invalido`, `prefixo_reservado` (`SF`), `id_fora_do_prefixo`, `id_duplicado` (contra o core ou outro pack), `core_incompativel`, `pack_duplicado`, `regra_invalida` (a regra nao passa pelo mesmo schema do core) |
| **MUST** | G3: `load_catalog()` devolve core + regras dos packs ativos; sem `SPARKFORGE_PACKS`, a lista e byte a byte a de hoje |
| **MUST** | G4: finding de regra de pack sai de `judge` e dos verbos de topo que julgam (`root_cause`, `proof`, `simulate`) sem campo novo no `Finding`; a origem sai do prefixo do `rule_id` |
| **MUST** | G5: CLI `sparkforge pack list` (ativos, recusados com motivo, mapa prefixo -> pack) e `sparkforge pack check <dir>` (valida o manifesto e roda cada fixture do pack pelo `judge`, falhando quando uma regra do pack nao dispara no fixture que a declara); superficie MCP READ_ONLY equivalente |
| **MUST** | G6: `fixtures/packs/` com o pack sintetico `acme-platform` (2 ou 3 regras sobre kinds que o core ja emite, 1 documento de knowledge, 1 fixture por regra) e um pack quebrado por recusa; golden de ponta a ponta |
| **SHOULD** | G7: `knowledge_path` lista o knowledge dos packs ativos numa chave PROPRIA (nao em `available`), confinado ao diretorio do pack por `sparkforge.paths.resolve_within` |
| **SHOULD** | G8: freshness de fonte de regra de pack le o `knowledge/sources.lock.json` do proprio pack; sem ele, a fonte sai `unresolved` com `pack_sem_lock` |
| **COULD** | G9: `docs/forge-pack.md` com a spec do `pack.yaml`, as recusas e o que o pack nao faz |

---

## Success Criteria

- [ ] SC1: sem `SPARKFORGE_PACKS`, nenhum golden muda, `check_status_numbers --strict` continua com as 190 regras e a suite por lotes fecha com 0 falhas.
- [ ] SC2: com `acme-platform` ativo, `judge` sobre os facts de cada fixture do pack produz exatamente os findings `ACME-*` que o fixture declara (2 ou 3 regras, cada uma disparando em >= 1 fixture), e os findings `SF-*` sobre os mesmos facts ficam iguais aos de sem pack.
- [ ] SC3: cada uma das 7 recusas de G2 tem um pack de fixture e sai em `pack list` com o motivo; 0 regras do pack recusado entram em `load_catalog()`.
- [ ] SC4: `pack check` sai 0 sobre `acme-platform` e 1 sobre um pack com regra que nao dispara no fixture dela, nomeando a regra.
- [ ] SC5: `knowledge_path` continua listando os 89 arquivos do core em `available`; o knowledge do pack aparece so na chave propria; pedido com `..` para fora do pack e recusado.
- [ ] SC6: fonte de regra de pack com lock no pack recebe estado de freshness; sem lock, `unresolved` com `pack_sem_lock`.
- [ ] SC7: tool nova com schema validado por amostra real; registros de tool nova e de dominio novo; surface lock com o crescimento declarado; claims remedidas por lista de ids.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Sem pack | `SPARKFORGE_PACKS` ausente | `load_catalog()`, `judge` em qualquer golden | Resultado byte a byte o de hoje |
| AT-002 | Pack carrega | `SPARKFORGE_PACKS=fixtures/packs/acme-platform` | `load_catalog()` | 190 regras do core + as do pack, cada uma com `id` `ACME-*` |
| AT-003 | Regra de pack dispara | pack ativo; facts de job Terraform sem `security_configuration` (48 de 50 jobs dos fixtures do core) | `judge` | finding `ACME-*` com o subject do job; findings `SF-*` inalterados |
| AT-004 | Verbo de topo ve o pack | pack ativo | `root_cause` sobre os mesmos facts | o finding `ACME-*` aparece entre os candidatos |
| AT-005 | Prefixo reservado | pack com `prefix: SF` | `pack list` | recusado `prefixo_reservado`; nenhuma regra carregada |
| AT-006 | Id fora do prefixo | pack `ACME` com regra `BETA-X-001` | `pack list` | recusado `id_fora_do_prefixo` |
| AT-007 | Id duplicado | dois packs com a mesma regra, ou regra com `id` do core | `pack list` | o segundo recusado `id_duplicado`, nomeando o outro dono |
| AT-008 | Core incompativel | `core: ">=9.0"` | `pack list` | recusado `core_incompativel` com a versao instalada |
| AT-009 | Manifesto invalido | `pack.yaml` sem `prefix` | `pack list` | recusado `manifesto_invalido` com o campo |
| AT-010 | Regra invalida | regra de pack sem `sources` | `pack list` | recusado `regra_invalida` com a mensagem do loader |
| AT-011 | Pack check verde | `acme-platform` | `sparkforge pack check fixtures/packs/acme-platform` | exit 0, cada regra com o fixture que a disparou |
| AT-012 | Pack check vermelho | pack com regra morta | `pack check` | exit 1, a regra nomeada |
| AT-013 | Knowledge confinado | pack ativo | `knowledge_path` pedindo `../../fora.md` do pack | recusado; `available` do core com os mesmos 89 arquivos |
| AT-014 | Freshness sem lock | pack sem `sources.lock.json` | `rules lookup --id ACME-... --source-freshness` | fonte `unresolved` com `pack_sem_lock` |
| AT-015 | Diretorio inexistente | `SPARKFORGE_PACKS` com caminho que nao existe | qualquer verbo | erro com codigo 2 nomeando o caminho, como `SPARKFORGE_CATALOG` |

---

## Out of Scope

- Extractor, collector, tool MCP, agente e skill vindos de pack (importar Python de terceiro esta fora).
- `forge pack install`, registry, publicacao, assinatura de pack.
- Dependencia entre packs e resolvedor de versoes.
- Sobrescrever limiar, severidade ou texto de regra do core.
- Rota de pack para coordenador: a area do pack cai no `fallback` do `routing.yaml`.
- Vigiar URL de pack no `knowledge/sources.lock.json` do core, ou rodar `refresh_knowledge.py` sobre pack.
- Script `forge` em `[project.scripts]`.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Nenhum `import` de arquivo do pack: so leitura de YAML, Markdown e JSON | O pack nao pode trazer extrator; as regras dele so consomem kinds do core |
| Technical | Contencao por `sparkforge.paths.resolve_within`, como `safe_catalog_file` e `safe_knowledge_file` | Todo caminho vindo do pack e confinado ao diretorio dele |
| Technical | `load_catalog()` tem 54 chamadas em 12 arquivos (30 em `regen_fixtures`, 6 em `check_evals`) | O comportamento sem a variavel nao pode mudar; gates e CI rodam sem ela |
| Technical | Regra de pack passa pelo MESMO schema do core (`_REQUIRED` inclui `sources`; `status` exigido de regra executavel) | Regra de pack precisa citar fonte |
| Technical | `knowledge_path.available` tem 89 arquivos e o teste de paginacao trava em `< 100` | Knowledge de pack nao entra em `available` |
| Technical | Nao ha `__version__` no pacote; a versao mora no `pyproject.toml` (0.5.0) | A compatibilidade le `importlib.metadata.version("sparkforge-aws")` |
| Technical | Tool nova move os registros manuais (memoria `tool-nova-move-registros-manuais`) | Contagens de tool, de tool com caminho e de READ_ONLY sobem |
| Technical | Regra 23: nada chama provider | Nenhuma parte do pack e executada por modelo |
| Resource | Repo publico | Pack sintetico; nenhuma regra real de empresa |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/packs/` (novo), `sparkforge/rules/loader.py`, `sparkforge/knowledge_ref.py`, `sparkforge/knowledge_freshness.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `fixtures/packs/`, `docs/forge-pack.md` | Carga em varias raizes nos loaders que ja existem; verbo de topo novo |
| **KB Domains** | Nenhum dominio do KB do agentspec cobre empacotamento (o indice tem dbt, spark, airflow...) | Padroes vem do codigo: `catalog_dir()`, `safe_catalog_file`, `resolve_within`, `carregar_lock`, `citacoes_de` |
| **IaC Impact** | None | Nada de infraestrutura |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `importlib.metadata.version("sparkforge-aws")` responde no install editavel local e no CI | A checagem de `core:` precisaria de outra fonte da versao | [ ] |
| A-002 | Nenhum consumidor de `load_catalog()` assume que todo `rule_id` comeca com `SF-` (area por prefixo, gold set, autoridade do executor agentico, `root_cause`) | Finding `ACME-*` quebraria um verbo de topo; o design precisa varrer os literais `SF-` | [ ] |
| A-003 | As regras sinteticas cabem em kinds que o core ja emite (medido: `security_configuration` aparece em 2 de 50 jobs `tf.attribute` dos fixtures) | O pack precisaria de fact novo, que exige extrator, que esta fora | [x] |
| A-004 | Carregar o pack a cada `load_catalog()` e barato (poucos YAML) | Precisaria de cache por processo, com cuidado para nao esconder mudanca de variavel | [ ] |
| A-005 | O `fallback` do `routing.yaml` aceita finding de area desconhecida sem erro (medido em `case/router.py::next_step`) | Pack precisaria declarar rota, que esta fora | [x] |

**Note:** A-001, A-002 e A-004 sao conferidas no inicio do design.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Raiz unica medida em `catalog_dir()`/`knowledge_dir()`; efeito no crescimento do core |
| Users | 3 | Tres personas com dor concreta |
| Goals | 3 | MoSCoW, com as recusas nomeadas |
| Success | 2 | Numeros medidos (190, 89, 7 recusas), mas quais regras sinteticas e quantas tools dependem do design |
| Scope | 3 | Fora de escopo explicito, com as decisoes do brainstorm |
| **Total** | **14/15** | |

---

## Open Questions

Nenhuma que bloqueie o design. Ficam para ele: uma tool (`pack` com acao) ou duas (`pack_list`, `pack_check`); as 2 ou 3 regras sinteticas e os fixtures delas; se `load_catalog()` ganha parametro explicito para os scripts de gate.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | define-agent | Versao inicial, a partir de `BRAINSTORM_FORGE_PACK.md`; medido: 89 arquivos de knowledge (docstring diz 19), `security_configuration` em 2 de 50 jobs, `_REQUIRED` exige `sources` |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_FORGE_PACK.md`
