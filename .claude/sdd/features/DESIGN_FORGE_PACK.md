# DESIGN: Forge Pack

> Technical design for implementing Forge Pack (§5 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FORGE_PACK |
| **Date** | 2026-09-12 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_FORGE_PACK.md](./DEFINE_FORGE_PACK.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  SPARKFORGE_PACKS = dirA<os.pathsep>dirB        (ausente = core so)       │
│        │                                                                  │
│        ▼                                                                  │
│  sparkforge/packs/load.py::resolve()                                      │
│     ├─ caminho inexistente ──────────────► CatalogError (exit 2, AT-015)  │
│     ├─ manifest.py: pack.yaml (id, version, prefix, core) + versao        │
│     ├─ rules/*.yaml ─► loader._validate_rule (MESMO schema do core)       │
│     └─ PackSet(active=[Pack], refused=[{dir, id, reason, detail}])        │
│              │                                  │                         │
│              ▼                                  ▼                         │
│  rules/loader.py::load_catalog()        _core.pack_list / pack_check      │
│   (directory=None) core + packs ativos   ├─ CLI `sparkforge pack list`    │
│              │                           ├─ CLI `sparkforge pack check`   │
│              ▼                           └─ tool `sparkforge_pack_list`   │
│  judge / root_cause / proof / simulate / rules_lookup (sem mudanca)      │
│              │                                                            │
│              ├─ finding `ACME-GOV-001` (schema: rule_id alargado)         │
│              └─ freshness: prefixo -> pack -> lock do pack | pack_sem_lock│
│                                                                           │
│  _core.knowledge_path(): `available` (core, 89) + `packs[]` (proprio)     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/packs/manifest.py` | Le e valida `pack.yaml`; compara a faixa `core:` com a versao instalada | PyYAML, `importlib.metadata` |
| `sparkforge/packs/load.py` | Resolve `SPARKFORGE_PACKS`, carrega as regras de cada pack pelo validador do loader, aplica as recusas, devolve `PackSet` | Python puro |
| `sparkforge/packs/check.py` | Roda os fixtures de um pack pelo `judge` e compara com o `expect.yaml` de cada um | `rules.engine.judge` |
| `sparkforge/rules/loader.py` | `_validate_rule` extraido do laco; `load_catalog()` sem `directory` acrescenta as regras dos packs ativos | Python |
| Schemas de finding e de regra | `rule_id`/`id` alargado para `^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[0-9]{3}$` | JSON Schema |
| `_core` + CLI + tool | `pack_list`, `pack_check`, `knowledge_path` com `packs`, freshness por pack | adapters existentes |

---

## Key Decisions

### Decision 1: O pack e um diretorio com `pack.yaml`, e o que ele traz tem lugar fixo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** O §5 lista doze blocos no manifesto. O brainstorm reduziu a dados (regras, knowledge, fixtures).

**Choice:**

```yaml
# <pack>/pack.yaml
pack:
  id: acme-platform          # ^[a-z][a-z0-9-]*$
  version: 1.0.0
  prefix: ACME               # ^[A-Z][A-Z0-9]*$, nunca SF
  core: ">=0.5,<1.0"         # clausulas >=, >, <=, <, == separadas por virgula
  description: Padroes de plataforma da ACME (sintetico)
```

Conteudo em lugar fixo, sem declaracao: `rules/*.yaml` (mesmo formato do catalogo, chave `rules:`), `knowledge/**` (Markdown; `knowledge/sources.lock.json` opcional), `fixtures/<caso>/{facts.json,expect.yaml}`.

**Rationale:** lugar fixo e o que o core ja faz (`rules/catalog/*.yaml`, `knowledge/`). Declarar caminhos no manifesto abriria um segundo vetor de caminho a confinar.

**Alternatives Rejected:**
1. Manifesto com lista de arquivos -- rejeitado: mais um caminho vindo de fora para confinar, sem ganho.
2. `packaging.specifiers` para `core:` -- rejeitado: `packaging` nao e dependencia declarada (`pyproject.toml` so tem PyYAML e jsonschema); um comparador de tupla de inteiros cobre as cinco clausulas.

**Consequences:**
- Versao de pre-release (`1.0.0rc1`) nao e aceita em `core:`; o manifesto invalido diz isso.
- A versao instalada vem de `importlib.metadata.version("sparkforge-aws")` (medido: `0.5.0` no install editavel). `PackageNotFoundError` vira `core_incompativel` com `instalada: desconhecida`.

---

### Decision 2: Carga em `load_catalog()` sem `directory`, pack recusado inteiro, e o core nunca cai por causa de pack

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** `load_catalog()` tem 54 chamadas em 12 arquivos e custa ~810 ms por chamada hoje (medido, sem cache). Um pack com defeito nao pode derrubar `judge` para quem nao o escreveu.

**Choice:**

- `load_catalog(directory=None, ...)`: quando `directory is None`, depois das regras do core, acrescenta `packs.resolve().rules()`. Com `directory` explicito (testes que apontam um catalogo), nenhum pack entra.
- O corpo do laco vira `_validate_rule(rule, origin) -> None` (levanta `CatalogError`), chamado pelo core como hoje e pelo pack dentro de `try`, onde `CatalogError` vira `regra_invalida`.
- Recusas, na ordem em que sao conferidas, e o pack sai INTEIRO na primeira:
  1. `manifesto_invalido`: `pack.yaml` ausente, sem `id`/`version`/`prefix`/`core`, formato fora das expressoes da Decisao 1;
  2. `prefixo_reservado`: `prefix: SF`;
  3. `pack_duplicado`: mesmo `id` OU mesmo `prefix` de um pack ja ativo. O prefixo precisa ser unico porque e ele que diz a origem do finding (Decisao 3);
  4. `core_incompativel`: a versao instalada fora da faixa;
  5. `regra_invalida`: a regra nao passa por `_validate_rule`;
  6. `id_fora_do_prefixo`: `id` que nao casa `^<PREFIX>-[A-Z][A-Z0-9]*-[0-9]{3}$`;
  7. `id_duplicado`: dois `id` iguais dentro do pack. Contra o core e impossivel (o `SF` ja foi recusado); entre packs, impossivel (prefixos unicos).
- Unica excecao que levanta: diretorio de `SPARKFORGE_PACKS` que nao existe, `CatalogError` com o caminho resolvido (AT-015), no molde de `SPARKFORGE_CATALOG`. Erro de configuracao do operador, nao defeito do pack.
- Cada regra de pack sai com `_source_file: "packs/<id>/rules/<arquivo>"`, `_pack: "<id>"` e o `catalog_version` do documento dela.

**Rationale:** carregar as regras boas de um pack meio quebrado daria um resultado que ninguem sabe explicar (regra 20: recusa tem nome). E o core nao pode depender da qualidade de um arquivo de terceiro.

**Alternatives Rejected:**
1. Parametro `packs=` explicito em `load_catalog` -- rejeitado: as 54 chamadas teriam de ser tocadas, e os verbos de topo continuariam cegos.
2. Levantar erro em pack invalido -- rejeitado: um pack quebrado derrubaria o `judge` inteiro.

**Consequences:**
- Scripts de gate (`check_status_numbers`, `regen_fixtures`, `check_evals`) contam regra de pack se a variavel estiver setada. O CI nao a seta; a doc diz para nao setar ao regenerar golden.
- Sem a variavel, `resolve()` devolve `PackSet` vazio sem tocar disco: o resultado de `load_catalog()` e o de hoje.

---

### Decision 3: A origem do finding e o prefixo, e o schema de `rule_id` e alargado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** A-002 caiu na medida: tres schemas travam `^SF-[A-Z][A-Z0-9]*-[0-9]{3}$` -- `tools.py:363` (finding), `tools.py:2287` (regra do `rules_lookup`) e `findings/schemas/finding.schema.json:20` (usado por `findings/validate.py`, o `validate_output`). Um finding `ACME-GOV-001` seria recusado na saida da MCP. O golden de paridade MCP (`fixtures/mcp_parity/`) contem o padrao **6** vezes por transporte, e `test_so_o_type_do_output_schema_difere` so aceita diferenca aditiva.

**Choice:**

- Os tres padroes passam a `^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[0-9]{3}$`. A reserva do `SF` e do loader de pack, nao do schema.
- `tests/test_fixtures_golden_mcp_parity.py` ganha `PADROES_ALARGADOS`: o par exato `(antes, agora)` com data e motivo, aceito so em caminho que termina em `.pattern`. `test_o_diff_aceito_tem_o_tamanho_medido` passa a contar 6 por transporte para esse tipo.
- Nenhum campo novo no `Finding`. `pack list` publica `prefixes: {ACME: acme-platform}`.
- `rules_lookup` tira da saida toda chave que comeca com `_` (hoje so `_source_file`); para o core, a saida e a mesma.

**Rationale:** o finding precisa validar na saida da tool, e mudar valor de schema e o que a paridade existe para pegar -- por isso a excecao e explicita, exata e contada, em vez de regravar o golden.

**Alternatives Rejected:**
1. `Finding.pack` -- rejeitado: muda o schema do finding e todos os goldens, e o prefixo ja carrega a informacao.
2. Regravar o golden MCP -- rejeitado: o golden prova a migracao de SDK e fica congelado (docstring da propria suite).

**Consequences:**
- Um `rule_id` como `FOO-X-001` passa no schema; a garantia de que so pack o produz e do loader.

---

### Decision 4: Uma tool READ_ONLY (`sparkforge_pack_list`), e o `pack check` so na CLI

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** O host precisa saber quais packs estao ativos e por que um foi recusado. Checar um pack e tarefa de quem o escreve, no terminal ou no CI dele.

**Choice:** `sparkforge_pack_list` (`_READ_ONLY`, sem parametro de caminho: le a variavel). CLI `sparkforge pack list` e `sparkforge pack check <dir>`. Tools 92 -> 93, READ_ONLY 60 -> 61; a tool nova entra no conjunto `sem_caminho` de `test_harness_authorization.py`, entao as que declaram caminho continuam 86. Dono: `agents/spark-performance-architect.md` (ja cita `sparkforge_judge` e `sparkforge_rules_lookup`).

**Rationale:** menor superficie que atende as tres personas; `pack check` pela MCP exigiria declarar caminho e confinar diretorio arbitrario para uma tarefa que o host nao faz.

**Alternatives Rejected:**
1. Duas tools (`pack_list`, `pack_check`) -- rejeitado: superficie e cadeia de autorizacao para uma tarefa de autor.
2. Nenhuma tool -- rejeitado: o host nao teria como explicar por que um `ACME-*` nao apareceu.

**Consequences:** `pack check` pela MCP fica para quando um host precisar.

---

### Decision 5: Knowledge de pack em chave propria, e freshness pelo lock do pack

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** `knowledge_path.available` tem 89 arquivos e o teste de paginacao trava em `< 100`. Freshness le um lock so (`carregar_lock(knowledge_dir())`).

**Choice:**

- `knowledge_path()` ganha `packs: [{id, root, available}]` **so quando ha pack ativo** (sem pack, a chave nao aparece e a saida e a de hoje). `file` aceita `packs/<id>/<relativo>`, resolvido por `safe_knowledge_file(<pack>/knowledge, relativo)`.
- `_freshness_de_citacoes` passa a agrupar as citacoes por origem: regra do core -> lock do core; regra de pack (pelo prefixo do `rule_id`) -> `carregar_lock(<pack>/knowledge)`, com `motivo_sem_lock="pack_sem_lock"`.

**Rationale:** o teto de 100 existe para a lista curada do core; misturar arquivo de terceiro nela quebraria a decisao documentada. `knowledge_path` ja esta em `ALTERADAS_DEPOIS_DO_GOLDEN`, e a chave nova e aditiva.

**Alternatives Rejected:**
1. Pack no `available` -- rejeitado pelo teto e pela curadoria.
2. URL de pack no lock do core -- rejeitado no brainstorm.

**Consequences:** `refresh_knowledge.py` continua so do core; o autor do pack mantem o lock dele.

---

### Decision 6: `pack check` compara o que dispara com o que cada fixture declara

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Choice:** para cada `fixtures/<caso>/`: le `facts.json`, roda `judge` com as regras do core mais as DESTE pack (carregado direto do diretorio, sem a variavel), filtra os findings com o prefixo do pack e compara o conjunto de `rule_id` com `expect.yaml: fires: [...]`. Falha (exit 1) quando algum caso diverge ou quando uma regra do pack nao aparece em `fires` de nenhum caso (regra sem prova). Pack recusado: exit 1 com a recusa. Saida JSON: `pack`, `cases[{case, expected, fired, ok}]`, `rules_without_fixture`, `ok`.

**Rationale:** e o contrato dos goldens do core (toda regra tem golden que dispara), aplicado ao pack.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/rules/loader.py` | Modify | `_validate_rule` extraido; `load_catalog()` sem `directory` acrescenta packs | (general) | None |
| 2 | `sparkforge/packs/{__init__,manifest,load,check}.py` | Create | Manifesto, versao, carga, recusas, check | (general) | 1 |
| 3 | `tests/test_packs_manifest.py`, `tests/test_packs_load.py` | Create | Unidade: cada recusa, versao, carga, ordem | (general) | 2 |
| 4 | `sparkforge/findings/schemas/finding.schema.json`, `sparkforge/adapters/tools.py` (2 padroes) | Modify | `rule_id` alargado | (general) | None |
| 5 | `sparkforge/adapters/_core.py` | Modify | `pack_list`, `pack_check`, `knowledge_path` com `packs`, freshness por pack, `rules_lookup` sem chaves `_` | (general) | 2 |
| 6 | `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py` | Modify | Grupo `pack`; tool `sparkforge_pack_list` | (general) | 5 |
| 7 | `fixtures/packs/acme-platform/` (+ packs de recusa) e `tests/test_fixtures_golden_packs.py` | Create | Golden de ponta a ponta com `SPARKFORGE_PACKS` | (general) | 5, 6 |
| 8 | Registros: `test_adapters_tools.py`, `test_harness_authorization.py` (`sem_caminho`), `test_fixtures_golden_mcp_parity.py` (`NOVAS_DEPOIS_DO_GOLDEN`, `PADROES_ALARGADOS`), `manifest.json`, `parity.yaml`, `agents/spark-performance-architect.md` + `sync_skills` | Modify | Tool nova e schema alargado | (general) | 6 |
| 9 | `docs/forge-pack.md`, STATUS, contagens de tool, surface lock, claims | Create/Modify | Spec do pack e numeros | (general) | 8 |
| 10 | `.claude/sdd/reports/BUILD_REPORT_FORGE_PACK.md` | Create | Relatorio | (general) | 9 |

**Total Files:** ~30 (contando os arquivos dos packs de fixture)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| (general) | 1-10 | Os agentes do plugin agentspec cobrem dbt, Spark, Airflow, cloud; nenhum cobre o loader de regras nem a superficie MCP deste repo. Build direto, como nos PRs #54, #56 e #58: cada passo depende de medida do anterior |

**Agent Discovery:**
- Scanned: `${CLAUDE_PLUGIN_ROOT}/agents/**/*.md` e `agents/*.md` do projeto
- O dono de produto da tool e `spark-performance-architect` (Decisao 4), que nao e agente de build

---

## Code Patterns

### Pattern 1: Comparador de faixa `core:`

```python
import re

_CLAUSULA = re.compile(r"^(>=|<=|==|>|<)(\d+(?:\.\d+)*)$")


def _versao(texto: str) -> tuple[int, ...]:
    return tuple(int(p) for p in texto.split("."))


def _comparar(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    largura = max(len(a), len(b))
    a, b = a + (0,) * (largura - len(a)), b + (0,) * (largura - len(b))
    return (a > b) - (a < b)


def dentro_da_faixa(instalada: str, faixa: str) -> bool:
    atual = _versao(instalada)
    for bruto in faixa.split(","):
        casou = _CLAUSULA.match(bruto.strip())
        if casou is None:
            raise ValueError(f"clausula invalida em core: {bruto.strip()!r}")
        op, alvo = casou.group(1), _versao(casou.group(2))
        c = _comparar(atual, alvo)
        if not {">=": c >= 0, "<=": c <= 0, "==": c == 0, ">": c > 0, "<": c < 0}[op]:
            return False
    return True
```

### Pattern 2: `load_catalog()` acrescentando os packs

```python
def load_catalog(directory=None, validate_exprs=False):
    base = directory or catalog_dir()
    rules = _load_core(base, validate_exprs)          # o laco de hoje, via _validate_rule
    if directory is None:
        from sparkforge.packs import resolve          # import tardio: packs importa o loader
        rules.extend(resolve().rules())
    return sorted(rules, key=lambda r: r["id"])
```

### Pattern 3: Pack sintetico `acme-platform`

```yaml
# fixtures/packs/acme-platform/rules/plataforma.yaml
catalog_version: 1
rules:
  - id: ACME-GOV-001
    category: acme-governanca
    title: Job Glue com worker G.4X sem aprovacao de capacidade
    requires_facts: [tf.attribute]
    when:
      same_subject: true
      all:
        - fact: tf.attribute
          where: {attrs.key: worker_type, attrs.value: G.4X}
    status: structural
    severity_default: P2
    runtime_scope: {glue: "*"}
    explanation: >
      Padrao sintetico de plataforma: G.4X exige aprovacao de capacidade.
    sources:
      - {url: "https://example.com/acme/padroes-de-plataforma", retrieved: 2026-09-12}
  - id: ACME-GOV-002
    category: acme-governanca
    title: Job Glue com timeout acima de 24 horas
    requires_facts: [tf.attribute]
    when:
      same_subject: true
      all:
        - fact: tf.attribute
          where: {attrs.key: timeout}
          expr: "measures.value > 1440"
    status: structural
    severity_default: P3
    runtime_scope: {glue: "*"}
    explanation: >
      Padrao sintetico de plataforma: timeout acima de 24 horas esconde job travado.
    sources:
      - {url: "https://example.com/acme/padroes-de-plataforma", retrieved: 2026-09-12}
```

Medido nos fixtures do core: `worker_type = G.4X` em 2 fatos; `timeout` 2880 em 2 jobs (`terraform/autoscaling_with_max_workers`, `terraform/max_capacity_conflict`), 480 em 12 e 60 em 3. Os campos exigidos por `_validate_executability` (`status` e o que a regra executavel pede) sao conferidos no build contra o loader.

---

## Data Flow

```text
1. Operador exporta SPARKFORGE_PACKS=<dir> (ou `.mcp.json` a declara)
   │
   ▼
2. load_catalog() le o core e chama packs.resolve()
   │  cada pack: manifesto -> prefixo -> unicidade -> core -> regras -> ids
   ▼
3. PackSet: regras dos ativos entram; recusados guardam motivo
   │
   ▼
4. judge/root_cause/proof/simulate julgam core + pack sem saber da diferenca
   │
   ▼
5. Finding ACME-* sai validado pelo schema alargado; freshness da fonte
   dele le o lock do pack (ou pack_sem_lock); pack list mostra ativos,
   recusados e o mapa prefixo -> pack
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Sistema de arquivos (diretorios de pack) | Leitura de YAML/Markdown/JSON, confinada por `resolve_within` | N/A |
| `importlib.metadata` | Versao instalada do pacote | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Faixa de versao, manifesto, cada recusa na ordem, `id_duplicado` dentro do pack, `_validate_rule` compartilhado | `tests/test_packs_manifest.py`, `tests/test_packs_load.py` | pytest | AT-005..AT-010, AT-015 |
| Integration | `load_catalog` com e sem a variavel; `judge`/`root_cause` vendo `ACME-*`; knowledge e freshness | `tests/test_packs_load.py` | pytest + `monkeypatch.setenv` | AT-001..AT-004, AT-013, AT-014 |
| E2E | `pack list`, `pack check` verde e vermelho pela CLI; golden de `pack list` | `tests/test_fixtures_golden_packs.py` | pytest | AT-011, AT-012 |
| Registros | Schema da tool com amostra real; paridade MCP com `PADROES_ALARGADOS` contado | registros existentes | pytest | SC7 |
| Regressao | Suite nos 9 lotes sem a variavel | `tests/test_suite_batches.py::LOTES` | pytest | SC1 |

| AT | Coberto por |
|----|-------------|
| AT-001 | `test_sem_variavel_load_catalog_igual` + suite inteira sem a variavel |
| AT-002 | `test_pack_acrescenta_regras_acme` (190 + 2) |
| AT-003 | golden: `judge` sobre os facts de `terraform/max_capacity_conflict` produz `ACME-GOV-002` e os `SF-*` iguais aos de sem pack |
| AT-004 | `test_root_cause_ve_o_finding_do_pack` |
| AT-005..AT-010 | um pack de recusa por motivo em `fixtures/packs/recusa_*` |
| AT-011, AT-012 | `pack check` sobre `acme-platform` (exit 0) e `recusa_regra_morta` (exit 1) |
| AT-013 | `test_knowledge_do_pack_confinado` e `available` com 89 |
| AT-014 | `rules lookup --id ACME-GOV-001 --source-freshness` com `pack_sem_lock` |
| AT-015 | `test_diretorio_inexistente_sai_2` |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Diretorio de `SPARKFORGE_PACKS` inexistente | `CatalogError` com o caminho resolvido; adapters traduzem para exit 2 | No |
| Pack com defeito (7 motivos) | Recusado inteiro, `refused[]` com `reason` e `detail`; core segue | No |
| Caminho de pack que escapa (`..`, symlink) | `resolve_within` devolve `None` -> `regra_invalida`/`KnowledgeError` | No |
| `importlib.metadata` sem o pacote | `core_incompativel` com `instalada: desconhecida` | No |
| `pack check` com divergencia | exit 1, casos e regras sem fixture nomeados | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `SPARKFORGE_PACKS` | string (diretorios separados por `os.pathsep`) | ausente | Packs ativos; ausente = so o core |

---

## Security Considerations

- Nenhum `import`, `exec` ou `eval` de conteudo de pack; so `yaml.safe_load`, `json.load` e leitura de texto.
- Todo caminho de pack passa por `resolve_within` (o mesmo de `safe_catalog_file`), inclusive `rules/*.yaml` achado por glob (symlink dentro do pack apontando para fora).
- `expr` de regra de pack e avaliado pelo mesmo `rules/expr.py` (seis comparadores, `ast.Call` recusado): regra de pack nao amplia o que o avaliador aceita.
- O prefixo `SF` e reservado no loader de pack; um pack nao consegue se passar por regra do core.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum log novo; a recusa aparece em `pack list` (regra 20) |
| Metrics | O span de `call_tool` da tool nova, como toda tool |
| Tracing | N/A |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | design-agent | Versao inicial. A-001 confirmada (`0.5.0`); A-002 caiu (3 schemas travam `^SF-`, 6 ocorrencias por transporte no golden MCP) e virou a Decisao 3; A-003 caiu (`absent` so confere kind, sem `where`) e trocou a regra sintetica para `worker_type`/`timeout`; A-004: `load_catalog` ja custa ~810 ms, pack soma pouco |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_FORGE_PACK.md`
