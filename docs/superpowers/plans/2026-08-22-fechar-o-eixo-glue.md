# Fechar o eixo Glue — Implementation Plan (fases H1–H6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar alcançável, pela CLI e pelo MCP, o motor de migração que as fases G1–G7 construíram, e fechar as lacunas restantes do mapa que têm consumidor real.

**Architecture:** Nenhum motor novo. `sparkforge/migration/assessment.py:assess()` já expande o par de versões em degraus, julga com o catálogo e agrega com gates fail-closed. O que falta é **porta de entrada** (CLI, MCP), **composição de artefato** (hoje `assess()` recebe uma lista de `Fact` pronta) e as três capacidades cujo consumidor passou a existir depois de G1–G7.

**Tech Stack:** Python 3.10/3.11 (stdlib + PyYAML), pytest, o catálogo de regras e o modelo `Fact`/`Finding` existentes.

**Mapa de origem:** [`../../harness/GLUE6-GAP.md`](../../harness/GLUE6-GAP.md). Plano anterior: [`2026-08-22-spark4-como-dado.md`](2026-08-22-spark4-como-dado.md).

---

## O achado que ordena este plano

Medido em 2026-08-22, depois de fechar G1–G7:

- `sparkforge/cli/forge.py:16` importa `GlueMigrationAnalyzer` — correspondência de substring, sem fonte, sem `runtime_scope`, com `--to` default `"5.1"` fixado no código. **`forge migrate glue` roda o analisador antigo.**
- Das 41 tools MCP, nenhuma é de migração. As próximas são `sparkforge_judge`, `sparkforge_rules_lookup` e `sparkforge_runtime_detect` — dá para compor o resultado com três chamadas à mão, não por uma entrada de migração.

Consequência: as dez regras de `SF-MIG`, `SF-SPARK4` e `SF-LF` são alcançáveis por quem chama `assess()` em Python ou lê o YAML. Pela CLI e pelo MCP, não. **H1 vem primeiro porque transforma trabalho já feito em capacidade alcançável, sem construir nada novo.**

## Ordem das fases

| fase | escopo | depende de | por que aqui |
|---|---|---|---|
| **H1** | `forge migrate glue` passa a usar `assess()`; tool MCP de migração; analisador antigo apagado | — | Fecha a dívida que o `STATUS.md` nomeia desde a fase `SF-MIG`. Sem ela, tudo o que G1–G7 entregou continua inalcançável pela superfície publicada |
| **H2** | Composição de artefato (§31) e etapas nomeadas do contrato (§32) | **H1** | `assess()` recebe `Fact` pronto. Quem chama pela CLI precisa que ele componha código, `requirements`, `.jar` e Terraform a partir de um diretório |
| **H3** | Bloqueio por consumidor incompatível (§25) | H2, e a matriz de G4 | `env.consumer` existe e a matriz de feature existe; falta cruzar. É o que impede recomendar v3 quando Athena consome |
| **H4** | `forge glue dependency-audit` (§16) e `forge iceberg assess-upgrade` (§24) | H1 | Duas entradas de CLI cujo motor já existe — `mig.python_dep` com `major`, e a matriz de feature |
| **H5** | Preço com data e região (§51) e benchmark por versão de runtime (§52) | — | Exige pesquisa de fonte oficial de pricing. Independente das demais |
| **H6** | Skills de Glue 6 com disclosure progressivo (§9, §72) e conhecimento de erro (§79) | G1, G3, G5 | O mapa dizia para não criar skill enquanto o conhecimento não existisse como dado. Ele existe agora |

**Fora deste plano, e por quê.** `RuntimeChangeGraph` (§41), `CapabilityRegistry` por capacidade (§74) e TTL por domínio (§44) continuam sem consumidor: nada os consultaria hoje, e cada um é camada nova que os gates de paridade cobram para sempre. `sparkforge_spark4_migration_scan` (§11) e `sparkforge_jar_compatibility_scan` (§13) ficam absorvidos por H1 — a tool de migração devolve o que as duas devolveriam, sem superfície nova, que é o que a §70 do prompt manda.

## Convenções deste repositório que valem para todas as fases

- Comentários e docstrings em português, explicando *por quê*, nunca *o quê*.
- `python -m ruff check sparkforge scripts tests` não pode acusar nada novo nos arquivos tocados. Limite de linha 100. O repositório tem 258 achados de baseline — meça antes e depois.
- Nenhum teste afirma contagem copiada. Conte derivando, ou asserte estrutura.
- `Fact` é observação ancorada e **nunca** contém juízo nem limiar. Limiar mora na regra.
- Mensagem de commit vai em **arquivo**, com `git commit -F`. Here-string do PowerShell (`@'...'@`) e backtick corrompem a mensagem no Bash — aconteceu duas vezes nesta sessão.
- Antes de commitar, rodar os gates de [`../../gates-por-mudanca.md`](../../gates-por-mudanca.md) para o tipo de mudança.

---

## H1 — a porta de entrada

**Files:**
- Modify: `sparkforge/cli/forge.py`
- Modify: `sparkforge/adapters/tools.py`, `sparkforge/adapters/_core.py`
- Delete: `sparkforge/migration/glue/analyzer.py`, `tests/test_migration_glue.py`
- Modify: `sparkforge/migration/__init__.py`, `tests/test_migration_assessment.py`

- [x] **Step 1: medir quem consome o analisador antigo**

Run:
```bash
TOKENSAVE_DISABLE_GREP_HOOK=1 grep -rn "GlueMigrationAnalyzer\|MigrationFinding\|migration.glue" --include=*.py --include=*.yaml --include=*.json --include=*.md .
```
Expected: `sparkforge/cli/forge.py`, `sparkforge/migration/__init__.py`, `sparkforge/migration/glue/`, `tests/test_migration_glue.py`, mais as citações em `STATUS.md` e no manifesto de alegações. Anote cada uma — todas precisam ser tratadas, e as de documento viram registro histórico, não apagamento.

- [x] **Step 2: escrever o teste do comando novo, e vê-lo falhar**

O comando passa a aceitar um **diretório** de job, não só um `.py`, e um par de versões sem default fixado no código. Teste em `tests/test_cli_migrate_glue.py`:

```python
def test_o_comando_usa_o_motor_de_regras_e_nao_o_analisador_antigo(tmp_path, capsys):
    (tmp_path / "job.py").write_text(
        "import com.amazonaws.services.s3.AmazonS3\n", encoding="utf-8"
    )
    from sparkforge.cli.forge import main

    codigo = main(["migrate", "glue", str(tmp_path), "--from", "4.0", "--to", "6.0"])
    saida = json.loads(capsys.readouterr().out)

    assert codigo == 0
    assert saida["source_runtime"] == "4.0" and saida["target_runtime"] == "6.0"
    assert "SF-MIG-001" in {f["rule_id"] for f in saida["findings"]}
    assert saida["gates"]["dados"] == "BLOCKED"
    assert saida["report"], "o relatorio deduplicado precisa sair junto"
```

Run: `python -m pytest tests/test_cli_migrate_glue.py -v` — deve FALHAR.

- [x] **Step 3: religar o comando**

Em `sparkforge/cli/forge.py`, trocar o import e o corpo de `cmd_migrate_glue`:

```python
from sparkforge.facts import migration as facts_migration
from sparkforge.migration import assessment


def cmd_migrate_glue(args: argparse.Namespace) -> int:
    """Avalia a migracao com o catalogo de regras, nao com correspondencia de
    substring.

    Aceita DIRETORIO, nao arquivo: uma migracao de Glue e julgada sobre o
    conjunto de artefatos do job -- codigo, `requirements*.txt` e `.jar` --, e
    o analisador antigo, que lia um `.py` por vez, nao conseguia ver a
    dependencia pinada nem o binario que quebram a migracao.
    """
    raiz = Path(args.path)
    if not raiz.is_dir():
        _print({"error": f"Directory not found: {args.path}"})
        return 1
    facts = facts_migration.extract_migration_tree(raiz, repo_root=raiz)
    try:
        resultado = assessment.assess(facts, source=args.from_runtime, target=args.to_runtime)
    except ValueError as exc:
        # `version_path.steps` estoura com mensagem nomeada para par invalido.
        # Propagar o texto dela e melhor que traduzir para um erro generico.
        _print({"error": str(exc)})
        return 1
    _print(resultado.to_dict())
    return 0
```

E no parser: `mig_g.add_argument("path", help="Diretorio do job")`, mais `--from`/`--to` **sem default**, `required=True` — o default `"5.1"` fixado no código é parte da dívida que esta fase fecha.

- [x] **Step 4: rodar o teste e ver passar**

Run: `python -m pytest tests/test_cli_migrate_glue.py -v` — PASS.

- [x] **Step 5: a tool MCP**

Acrescentar `sparkforge_migration_assess` a `sparkforge/adapters/tools.py`, com handler em `_core.py` no molde dos vizinhos (`_h_analyze_*`). Entrada: `path` (diretório), `source`, `target`. Saída: o `to_dict()` do assessment, sob `_may_fail`.

A §70 do prompt manda **expandir** em vez de multiplicar: esta é a única tool nova da fase, e ela absorve o que `sparkforge_spark4_migration_scan` e `sparkforge_jar_compatibility_scan` devolveriam — as regras que julgam Spark 4 e binário de Scala já estão no catálogo e saem no mesmo assessment.

Gates que uma tool nova cobra: `tests/test_adapters_tools.py`, `tests/test_adapters_mcp.py`, `tests/test_agent_coverage.py` (toda tool precisa ser alcançável a partir de um coordenador) e `manifest.json`, que lista as tools.

- [x] **Step 6: apagar o analisador antigo**

Só depois dos passos acima verdes. Apagar `sparkforge/migration/glue/`, `tests/test_migration_glue.py`, os reexports de `sparkforge/migration/__init__.py`, e a exceção de `tests/test_migration_assessment.py::test_nenhum_par_de_versao_aparece_no_codigo_do_motor` que isentava `glue/analyzer.py`.

Conferir que `docs/claims.lock.json` não tem alegação `PROVADA` apontando para `sparkforge/migration/glue/analyzer.py` — o `STATUS.md` registra que existe uma. Se existir, ela vira `REMOVIDA` com nota dizendo que o artefato foi apagado e por quê.

- [x] **Step 7: gates e commit**

```bash
python -m pytest tests/test_cli_migrate_glue.py tests/test_migration_assessment.py \
  tests/test_adapters_tools.py tests/test_adapters_mcp.py tests/test_agent_coverage.py \
  tests/test_docs_coverage.py tests/test_capability_parity.py -q
python scripts/check_vnext_claims.py
python -m ruff check sparkforge tests --output-format concise
```

Commit: `feat(cli): forge migrate glue passa a usar o motor de regras`.

---

## H2 — composição de artefato e etapas do contrato

**Files:** `sparkforge/migration/assessment.py`, `tests/test_migration_assessment.py`

- [x] **Step 1: `collect()` — a composição que falta**

`assess()` recebe `list[Fact]`. Quem chama pela CLI precisa que alguém componha os extratores. Criar `sparkforge/migration/collect.py` com uma função que, dado um diretório, chama `extract_migration_tree` e, quando houver `.tf`, também `extract_terraform_tree`, e devolve a união ordenada.

Por que função separada e não dentro de `assess()`: `assess()` é puro sobre facts e é isso que torna testável julgar sem tocar disco. A composição é I/O, e I/O tem lugar próprio — mesmo motivo pelo qual `extract_migration_tree` não vive dentro de `judge`.

- [x] **Step 2: etapas nomeadas (§32)**

`MigrationAssessment.gates` hoje tem `compatibilidade`, `dados`, `performance`, `custo`, `canary`. A §32 nomeia etapas que não existem: Lake Formation, cross-account, IAM/KMS, rede, consumidor.

**Não crie gate que ninguém preenche.** Acrescente apenas os que têm produtor: `lakeformation` tem produtor (`SF-LF`), `consumidor` ganha produtor em H3. Os demais (`iam_kms`, `rede`, `cross_account`) entram como `missing_evidence` nomeado — dizendo que o eixo não foi avaliado e o que o preencheria —, que é diferente de fingir que passou.

- [x] **Step 3: gates e commit**

```bash
python -m pytest tests/test_migration_assessment.py tests/test_cli_migrate_glue.py \
  tests/test_fixtures_scenarios.py -q
```

Commit: `feat(migration): assessment compoe os artefatos do job e nomeia os eixos nao avaliados`.

---

## H3 — bloqueio por consumidor incompatível (§25)

**Files:** `sparkforge/migration/assessment.py` ou regra nova, `sparkforge/storage/feature_support.py`, `rules/catalog/`

- [x] **Step 1: decidir a forma, e registrar a decisão**

Duas formas possíveis, e a escolha precisa estar escrita:
1. **Regra do catálogo** que correlaciona `env.consumer` com `iceberg.table_property` (`format-version`) — segue o padrão de `SF-ENV-002`, que já faz exatamente isso para Athena.
2. **Gate do assessment** que consulta `feature_support.support(feature, engine, versao)`.

A forma 1 é a do repositório e não cria camada. Prefira-a, a menos que meça razão para a outra — e então escreva a razão.

- [x] **Step 2: generalizar sem duplicar `SF-ENV-002`**

`SF-ENV-002` já cobre Athena × format v3. A regra nova precisa cobrir o que ela **não** cobre, sem acusar duas vezes o mesmo caso. Meça: com um `env.consumer` de Athena e uma tabela v3, quantos achados saem? Se saírem dois, a regra nova está errada.

- [x] **Step 3: golden e gates**

Fixture com inventário de consumidores mais tabela em v3. Gates de regra nova, os mesmos de `docs/gates-por-mudanca.md`.

Commit: `feat(rules): consumidor incompativel bloqueia a recomendacao`.

---

## H4 — as duas CLIs que faltam

- [x] **`forge glue dependency-audit` (§16).** Entrada: diretório. Lê `mig.python_dep` (que já carrega `major`) e `mig.jar_binary` (que já carrega `scala_minor`), julga com o catálogo e devolve pins, conflitos e risco de ABI. O motor existe; é composição de CLI.
- [x] **`forge iceberg assess-upgrade --from 2 --to 3` (§24).** Consulta `sparkforge/storage/feature_support.py` para as engines do inventário de consumidores e devolve `SAFE`/`CONDITIONAL`/`BLOCKED`/`UNRESOLVED`. **Nunca executa o upgrade** — a §94 do prompt é explícita.

Cada uma com teste de CLI no molde de H1. Commits separados.

---

## H5 — preço e benchmark

- [x] **Preço (§51).** Pesquisar a página oficial de pricing do AWS Glue e registrar como conhecimento com `retrieved`, região e tipo de worker. **Não codificar "-30%"**: o prompt proíbe explicitamente, e preço muda. Se a fonte não separar preço por versão de runtime, diga isso em vez de inferir.
- [x] **Benchmark por runtime (§52).** `sparkforge/facts/benchmark.py` já compara execuções. Falta parametrizar por versão de runtime e recusar comparação sem as duas execuções — sem baseline não há prova de melhoria, e o repositório já tem gate com essa forma (`missing_evidence`).

**Escreva no relatório o que a fonte não sustentar.** Preço 30% menor não é performance 30% maior, e a §52 manda medir as duas coisas separadamente.

---

## H6 — skills e conhecimento de erro

- [x] **Skills (§9, §72).** O mapa mandava não criar skill enquanto o conhecimento não existisse como dado. Ele existe agora (`spark4-migration.md`, `iceberg-v3.md`, `lakeformation-fgac.md`, `runtime-matrix.yaml`, `iceberg-feature-support.yaml`).

**Não faça as quarenta.** Faça as que têm conhecimento por trás e superfície de uso: migração para Glue 6, compatibilidade de Spark 4, Iceberg v3, FGAC. Cada uma com `SKILL.md` curto e referências sob demanda, que é o disclosure progressivo da §72. Cada skill nova cobra `scripts/sync_skills.py`, `tests/test_agents_parity.py`, `tests/test_sync_render.py`, `tests/test_skill_content.py` e `manifest.json`.

- [x] **Conhecimento de erro (§79).** `knowledge/errors/` já existe com subdiretórios por domínio. Acrescentar só erro **observado em fonte oficial** — a §79 proíbe inventar erro hipotético como conhecido. Os que esta sessão já mediu, com texto exato: `Cannot read unsupported version 3` (Athena sobre tabela v3), `NoSuchMethodError`/`ClassNotFoundException` (JAR Scala 2.12 sob Spark 4), `NoSuchFieldError` (SDK v2 antigo com `--user-jars-first`).

---

## Auto-revisão deste plano

**Cobertura.** H1–H6 cobrem os 26 itens abertos do mapa, menos três declarados fora com razão escrita (`RuntimeChangeGraph`, `CapabilityRegistry` por capacidade, TTL por domínio) e dois absorvidos por H1 (as duas tools de scan).

**Ordem.** H1 primeiro porque é o único item que não constrói nada e mesmo assim muda o que o usuário alcança. H2 depende de H1 porque a composição só tem consumidor quando a CLI existe. H3 depende de H2 porque o gate de consumidor precisa dos facts compostos.

**Risco declarado.** H6 é a fase com maior superfície nova por unidade de valor: cada skill entra em quatro gates de paridade e lá fica. Se o orçamento acabar, ela é a primeira a cortar — e o corte não deixa nada quebrado, só menos apresentado.

---

## Desvios do plano, medidos na execução (2026-08-23)

O plano foi executado inteiro, H1 a H6. Cinco pontos saíram diferente do escrito, e cada um
tem razão medida — nenhum foi escolha de conveniência.

**1. O eixo `consumidor` entrou em H2, não em H3.** O plano dizia "acrescente apenas os que têm
produtor: `lakeformation` tem produtor, `consumidor` ganha produtor em H3". Medido: `SF-ENV-002`
já existia em `rules/catalog/env.yaml` e `collect()` passou a compor o inventário na própria
H2 — o produtor existia naquele momento. H3 então generalizou o bloqueio em vez de criar o eixo.

**2. H3 usou a forma 2 (gate), não a forma 1 (regra do catálogo).** O plano preferia a regra e
mandava escrever a razão caso a outra fosse escolhida. A razão: o avaliador de `expr` tem
whitelist de nós AST sem `Call` e sem `In`, e `where` compara igualdade — não há como escrever
"serviço que a matriz não declara suportado" numa condição. A alternativa seria uma regra por
engine, cada uma copiando em YAML o que a matriz já diz com `source` e `retrieved`.

**3. As duas CLIs de H4 foram num commit só.** O plano pedia "commits separados". As duas
entram no mesmo `manifest.json` e no mesmo `parity.yaml`, e `tests/test_capability_parity.py`
cobra tool MCP para todo verbo de CLI: separar deixaria o gate vermelho no commit do meio.

**4. H5 e H6 também.** Mesma família de razão, agora no gate de lastro: `docs/claims.lock.json`
é atômico, a reclassificação do mapa cobre §16, §24, §25, §51 e §52 na mesma passada, e a
contagem de skills de `CURRENT-STATE.md` só fica verdadeira quando as skills existem na árvore.

**5. Duas tools MCP a mais do que o plano previa.** H1 declarou "esta é a única tool nova da
fase", e isso valeu para H1. H4 precisou de duas — `sparkforge_glue_dependency_audit` e
`sparkforge_iceberg_assess_upgrade` — porque o gate de paridade recusa verbo de CLI sem tool
correspondente, e nenhuma das duas exceções declaradas em `ALLOWED_CLI_ONLY` se aplicava.
Total: 41 → 44 tools.

## O que ficou fora, e continua fora

`RuntimeChangeGraph` (§41), `CapabilityRegistry` por capacidade (§74) e TTL por domínio (§44).
As três linhas do mapa passaram a dizer **"fora de escopo declarado"** em vez de só
`NÃO EXISTE`, apontando para cá — `NÃO EXISTE` sozinho lê como pendência, e essas três são
decisão.

Duas tools do prompt foram **absorvidas** em vez de construídas, e o mapa registra isso:
`sparkforge_spark4_migration_scan` (§11) e `sparkforge_jar_compatibility_scan` (§13). O
assessment de migração e o `dependency-audit` devolvem o que elas devolveriam.

A §12 pedia uma família `spark-4-*`; existe **uma** skill, `spark4-compatibility`, e a linha do
mapa diz `EXISTE PARCIAL` por isso. O critério que sobreviveu foi "conhecimento por trás **e**
consumidor", não "uma skill por seção do prompt".
