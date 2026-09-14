# DESIGN: Autonomia L1–L2

> Technical design for implementing Autonomy L1–L2 (§15): `change plan` e `change sandbox`

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L1_L2 |
| **Date** | 2026-09-13 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_AUTONOMY_L1_L2.md](./DEFINE_AUTONOMY_L1_L2.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
 L1  change plan (READ_ONLY, stage=produce_change)
 ------------------------------------------------
 --facts (uniao) --+--> [--from-tune] _core.tune_conf -> properties[].derived.value
                   |
                   +--> [--set k=v]   parse
                              |
                              v
        sparkforge/change/plan.py  (puro: facts + repo + {chave: valor})
          localizar(): tf.spark_conf / pyspark.conf_set da chave
             0 lugares  -> sem_procedencia_em_arquivo
             >1 lugares -> procedencia_ambigua
             redacted   -> valor_redigido
          trocar():
             .tf  -> par `chave=valor` (fronteira de token) na linha do --conf
             .py  -> ast.parse, Call na linha, span do no do valor (bytes UTF-8)
                     literal diferente -> linha_nao_confere; nao-Constant -> valor_nao_literal
          difflib.unified_diff(a/, b/, LF) -> diff ; inverso -> rollback_diff
                              |
                              v
        {stage, changes[], refused[], diff, rollback_diff}   (nada gravado; --out so CLI)

 L2  change sandbox (LOCAL_MUTATION, stage=sandbox_execute)
 -----------------------------------------------------------
 --repo, --diff <arquivo>
     |
     v
 change/apply.py  parse_unified_diff() -> [Patch]  (recusas antes de tocar disco)
     |
     v
 change/sandbox.py
   copiar(repo) via facts.scan.varrer_source_files(repo, "*") -> manifesto (rel, sha256), pulos
   id = sha256(diff + manifesto)[:16]
   .sparkforge/sandbox/<id>/before/   <- copia pristina
   .sparkforge/sandbox/<id>/after/    <- copia + aplicar_patches() (tudo ou nada, em memoria)
     |
     v
 _core.scan(before) ; _core.scan(after)      (duas raizes; cada uma grava em <raiz>/.sparkforge/scan/)
     |
     v
 simulate.diff.diff(findings_before, findings_after, [], [], proof.load_policy()["stable_keys"])
     |
     v
 {stage, sandbox, id, new[], resolved[], kept_count, proof_obligations[], next_steps[],
  copy_skipped[], main_tree_touched: false}  -> tambem em .sparkforge/sandbox/<id>/report.json
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/change/__init__.py` | API publica: `plan_change`, `parse_unified_diff`, `apply_patches`, `ChangeError`, `REFUSALS` | stdlib |
| `sparkforge/change/plan.py` | L1 puro: localizar a chave pela procedencia, conferir, trocar, gerar diff e rollback | `ast`, `re`, `difflib` |
| `sparkforge/change/apply.py` | Parser de diff unificado e aplicador estrito em memoria, com as recusas do aplicador | stdlib |
| `sparkforge/change/sandbox.py` | Copia confinada, `id`, montagem de `before/`/`after/`, limpeza; relatorio a partir dos findings | `facts.scan`, `paths.resolve_within`, `hashlib`, `shutil` |
| `sparkforge/adapters/_core.py` | `change_plan(...)` e `change_sandbox(...)`: compoem `tune_conf`, `scan`, `simulate.diff` e `proof.load_policy` | padrao dos verbos de topo |
| `sparkforge/adapters/cli.py` | `sparkforge change plan|sandbox` (`change_action` na cadeia de `getattr`) | argparse |
| `sparkforge/adapters/tools.py` | `sparkforge_change_plan` (`_READ_ONLY`) e `sparkforge_change_sandbox` (`_WRITE_IDEMPOTENT`) | schemas `_may_fail` |

`sparkforge/change/` nao importa `adapters` (a composicao mora em `_core`), nem `subprocess`, nem provider.

---

## Key Decisions

### Decision 1: O valor e localizado pelo no, nao pela linha

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** A-002. `pyspark_ast._subject` grava `line = node.lineno` do `Call` e tambem `end_line`. Num builder encadeado (`SparkSession.builder\n  .config("k", "v")`), o `lineno` do `Call` e o INICIO da expressao, nao a linha do valor. No Terraform (A-001, medido), as quatro chaves do `--conf` dividem a linha 21 de `fixtures/terraform/spark_conf_in_arguments/input/main.tf`.

**Choice:**
- `.py`: `ast.parse` do arquivo atual. Procura um `Call` com `lineno == subject.line` cujo `args[0]` e o literal da chave. Depois troca exatamente o span de `args[1]` (`lineno/col_offset` ate `end_lineno/end_col_offset`) pela representacao do novo valor, no mesmo estilo (string com a mesma aspa se o original era string; numero se era numero). Os offsets de coluna do `ast` sao em **bytes UTF-8**: a troca opera nos bytes da linha, nao nos caracteres.
- `.tf`: na linha `subject.line`, troca a ocorrencia unica de `chave=valor_atual` com fronteira de token, `(?<![\w.-])` antes e `(?=\s|"|$)` depois. Assim `spark.sql.shuffle.partitions=800` nao casa dentro de `...partitions=8000` nem de `x.spark.sql...`.
- Recusas: sem `Call`/par na linha, `linha_nao_confere`; `args[1]` que nao e `ast.Constant`, `valor_nao_literal`; par que aparece mais de uma vez na linha, `linha_nao_confere` (ambiguo dentro da linha).

**Rationale:** trocar pelo span do no preserva o resto da linha e da cadeia byte a byte (SC4), e a checagem do literal atual e a garantia contra a arvore que mudou desde a extracao.

**Alternatives Rejected:**
1. Regex na linha para `.py`: rejeitado porque falha no builder multilinha e em chamadas com a mesma chave em comentario.
2. Reextrair o arquivo com o extrator e comparar facts: rejeitado porque diz SE mudou, mas nao ONDE trocar.

**Consequences:**
- Valor escrito como expressao (`str(800)`, f-string) sai `valor_nao_literal`: e o limite declarado.
- `spark_default_explicit` (a chave escrita a mao com o valor do default) e editavel, porque existe em arquivo. A recusa `sem_procedencia_em_arquivo` fica so para `runtime_or_cluster` e `unset`. Isto corrige a redacao de SC3 do DEFINE.

---

### Decision 2: Aplicador proprio, estrito, tudo ou nada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** O L2 aplica diff escrito pelo host, que e entrada nao confiavel, e o pacote nao chama `patch` nem `git apply` (sem subprocess).

**Choice:** `parse_unified_diff(texto) -> list[Patch]`:
- aceita `--- a/x` / `+++ b/x` e tambem `--- x` / `+++ x`, e tira o prefixo `a/`/`b/`;
- cada `Hunk` guarda `@@ -l,s +l,s @@`, linhas de contexto, `-` e `+`.

As recusas saem **antes de tocar disco**:

| Condicao | Recusa |
|---|---|
| texto acima de 2 MB | `diff_grande_demais` |
| nenhum patch | `diff_vazio` |
| `/dev/null` como origem ou destino, `GIT binary patch`, `Binary files`, `rename from`, `new file mode`, `deleted file mode` | `diff_nao_suportado` |
| caminho absoluto, `..`, drive do Windows, ou nome que diverge entre `---` e `+++` | `caminho_fora_da_raiz` (ou `diff_nao_suportado` para o rename implicito) |

`apply_patches(arquivos: dict[rel, bytes], patches)` aplica cada hunk na posicao declarada. O contexto e as linhas `-` precisam bater byte a byte, sem fuzz e sem deslocamento. O primeiro hunk que nao bate levanta `diff_nao_aplica`, com arquivo, cabecalho do hunk e a primeira linha divergente. A aplicacao e toda em memoria, e so depois de todos os patches aplicados a copia `after/` e gravada. O fim de linha e preservado: arquivo com CRLF recebe as linhas `+` com CRLF.

**Rationale:** "tudo ou nada" e o que torna SC6 verificavel. Aplicar em memoria elimina o estado meio aplicado.

**Alternatives Rejected:**
1. `git apply --check` por subprocess: rejeitado pela restricao do DEFINE e porque exige git (a copia nao e repositorio).
2. Aplicacao com fuzz: rejeitada porque produz uma arvore que ninguem revisou.

**Consequences:**
- Diff de criacao ou remocao de arquivo fica fora (DEFINE, Out of Scope).
- O rollback do L1 passa pelo mesmo aplicador. A ida-e-volta (SC2) testa as duas pontas.

---

### Decision 3: Duas copias, `before/` e `after/`, e o `scan` como caixa preta

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** A-005. `_core.scan(repo)` grava em `<repo>/.sparkforge/scan/` (`_scan_gravar` apaga os `.json` antigos) e devolve o resumo; os findings ficam em `findings.json`. O catalogo carregado e so leitura.

**Choice:** O sandbox monta `.sparkforge/sandbox/<id>/before/` (copia pristina) e `after/` (copia com os patches). Roda `_core.scan(str(before))` e `_core.scan(str(after))` e le `findings.json` de cada raiz. Como sao duas raizes sem arquivo compartilhado, nao ha estado de um lado para vazar no outro. A comparacao reusa `sparkforge.simulate.diff.diff(antes, depois, [], [], load_policy()["stable_keys"])` (A-008: a chave estavel de `proof/keys.py` ignora `line`, `col` e `snippet`, que o proprio diff desloca). Os campos do resultado sao renomeados: `appeared` vira `new`, `disappeared` vira `resolved` e `persisted_count` vira `kept_count`.

**Rationale:** o `scan` tem golden e cobre o plano por manifesto, a fusao e o julgamento. Reusa-lo sem refatorar evita tocar o §22. Duas copias tambem deixam o operador comparar `before/` e `after/` com a ferramenta que quiser.

**Alternatives Rejected:**
1. Uma copia, com o scan, a aplicacao e o scan de novo: rejeitado porque a segunda passada apaga a saida da primeira e mistura a ordem.
2. Refatorar `scan` para devolver os findings em memoria: rejeitado porque mexe em verbo entregue sem necessidade.

**Consequences:**
- O custo e dobrado (duas copias, dois scans). Aceito: a copia ja pula `vendor/`, `.venv`, dados grandes e sensiveis.
- Subject sem chave estavel declarada compara inteiro. Um achado de linha deslocada por patch pode aparecer em `new` e em `resolved` ao mesmo tempo. Nesse caso o par sai marcado em `moved_candidates` quando `rule_id` e `file` batem, e a leitura fica com o operador, sem decisao silenciosa.

---

### Decision 4: `id`, relatorio e limpeza

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:**
- `id = sha256(diff_bytes + b"\0" + "".join(f"{rel}\t{sha}\n" for rel, sha in sorted(manifesto)).encode())[:16]`.
- Se `.sparkforge/sandbox/<id>/` existe, e apagado e recriado, e a apagada passa por `resolve_within(repo/.sparkforge/sandbox, alvo)`.
- O relatorio e gravado em `.sparkforge/sandbox/<id>/report.json` (`sort_keys`, LF) e devolvido.
- `--clean` remove `.sparkforge/sandbox/` inteiro, confinado, e devolve `{removed: [ids]}`.
- `.gitignore` ganha `.sparkforge/sandbox/`.

**Rationale:** mesma entrada, mesmo diretorio e mesmo relatorio (SC8). O conteudo da copia pode ter credencial pulada? Nao, porque a varredura recusa por nome antes de ler. Mesmo assim a copia nao deve ir para o git.

---

### Decision 5: Superficie — duas tools, `stage` proprio, sem `AutonomyLevel`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:**

| Tool | Classe | Entrada | Dono |
|---|---|---|---|
| `sparkforge_change_plan` | `_READ_ONLY` | `facts_path` (string ou lista), `repo`, `from_tune` (bool), `sets` (lista `chave=valor`) | `spark-performance-architect` (ja dono de `tune` e `simulate`) |
| `sparkforge_change_sandbox` | `_WRITE_IDEMPOTENT` | `repo`, `diff_path`, `clean` (bool) | `sf-verifier` (ja dono de `proof`) |

Nenhum parametro se chama `command`, `url` ou similar (INV-007/009); o diff entra por `diff_path`. As duas tools declaram caminho: `test_harness_authorization` passa de 90 para 92 e `len(TOOLS)` de 98 para 100. As saidas trazem `stage` (`produce_change` / `sandbox_execute`) e o sandbox traz `main_tree_touched: false`. `applied_changes` nao aparece nas saidas novas, e os schemas que ja o travam em `false` nao mudam. `AutonomyLevel` fica intocado.

Na CLI:
- `sparkforge change plan --facts F [--facts F2] --repo R (--from-tune | --set k=v ...) [--out arquivo.patch]`
- `sparkforge change sandbox --repo R (--diff arquivo | --clean)`

**Rationale:** as classes seguem o que as tools fazem. `_WRITE_IDEMPOTENT` segue o precedente do `sparkforge_scan`, que grava com nome fixo e recria. A policy padrao do §16 ja pre-aprova LOCAL_MUTATION.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/change/__init__.py`, `plan.py` | Create | L1 puro | @python-developer | None |
| 2 | `sparkforge/change/apply.py` | Create | Parser e aplicador estrito | @python-developer | None |
| 3 | `sparkforge/change/sandbox.py` | Create | Copia, `id`, `before/`/`after/`, limpeza, montagem do relatorio | @python-developer | 2 |
| 4 | `sparkforge/adapters/_core.py` | Modify | `change_plan`, `change_sandbox` | @python-developer | 1, 3 |
| 5 | `sparkforge/adapters/cli.py` | Modify | `change plan|sandbox`, `change_action` | @python-developer | 4 |
| 6 | `sparkforge/adapters/tools.py` | Modify | 2 tools, schemas, handlers | @python-developer | 4 |
| 7 | `fixtures/change/<caso>/{input/repo/,input/facts.json,input/request.json,expected.json}` + `.gitattributes` (`fixtures/change/** -text`) | Create | Golden sinteticos | @test-generator | 1-3 |
| 8 | `tests/test_change_plan.py`, `tests/test_change_apply.py`, `tests/test_change_sandbox.py`, `tests/test_fixtures_golden_change.py` | Create | Unidade, ida-e-volta, confinamento, golden (`FIXTURES = ROOT / "fixtures" / "change"`) | @test-generator | 1-7 |
| 9 | `.gitignore` | Modify | `.sparkforge/sandbox/` | (general) | None |
| 10 | Registros de tool nova: `tests/test_adapters_tools.py` (lista, amostra real, FAILABLE, writers), `tests/test_harness_authorization.py` (92), `tests/test_fixtures_golden_mcp_parity.py`, `parity.yaml`, `manifest.json`, `agents/spark-performance-architect.md`, `agents/executors/sf-verifier.md` + `scripts/sync_skills.py` (com backup do README), surface lock, claims | Modify | Tool nova | (general) | 6 |
| 11 | `docs/guia/usos/change.md`, `docs/guia/README.md`, referencia (`scripts/gen_reference_docs.py`), `CLAUDE.md` (tabela de verbos e contagem de tools), `STATUS`, `docs/agentic-evolution-report.md` (L1/L2 do §15 contra a escala do `AutonomyLevel`) | Create/Modify | Manual para leigo e documentacao | (general) | 5, 6 |

**Total Files:** 11 entradas

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1-6 | Python puro com dataclasses, no molde de `policy/`, `scan/` e `simulate/` |
| @test-generator | 7, 8 | Golden e unidade pytest |
| (general) | 9-11 | Registros, configuracao e docs do proprio repositorio; build direto |

---

## Code Patterns

### Pattern 1: troca pelo span do no (`.py`)

```python
import ast


def trocar_valor_py(fonte: bytes, linha: int, chave: str, atual: str, novo: str) -> bytes:
    arvore = ast.parse(fonte)
    alvos = [
        n for n in ast.walk(arvore)
        if isinstance(n, ast.Call) and n.lineno == linha and len(n.args) >= 2
        and isinstance(n.args[0], ast.Constant) and n.args[0].value == chave
    ]
    if len(alvos) != 1:
        raise ChangeError("linha_nao_confere", f"{len(alvos)} chamadas com {chave!r} na linha {linha}")
    valor = alvos[0].args[1]
    if not isinstance(valor, ast.Constant):
        raise ChangeError("valor_nao_literal", f"{chave!r} recebe expressao na linha {valor.lineno}")
    if str(valor.value) != atual:
        raise ChangeError("linha_nao_confere", f"esperava {atual!r}, o arquivo tem {valor.value!r}")
    linhas = fonte.splitlines(keepends=True)
    ini = sum(len(x) for x in linhas[: valor.lineno - 1]) + valor.col_offset  # bytes UTF-8
    fim = sum(len(x) for x in linhas[: valor.end_lineno - 1]) + valor.end_col_offset
    literal = fonte[ini:fim].decode("utf-8")
    substituto = repr_no_mesmo_estilo(literal, novo)  # "800" -> "320"; 800 -> 320
    return fonte[:ini] + substituto.encode("utf-8") + fonte[fim:]
```

### Pattern 2: diff e rollback deterministicos

```python
import difflib


def unified(rel: str, antes: str, depois: str) -> str:
    return "".join(difflib.unified_diff(
        antes.splitlines(keepends=True), depois.splitlines(keepends=True),
        fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3,
    ))

# diff = unified(rel, original, trocado); rollback_diff = unified(rel, trocado, original)
```

### Pattern 3: recusa com nome (regra 20)

```python
from dataclasses import dataclass


class ChangeError(ValueError):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{detail} [{reason}]")
        self.reason, self.detail = reason, detail


@dataclass(frozen=True)
class Recusa:
    reason: str
    key: str
    detail: str
    unlock: str  # a medida ou acao que destrava: "sparkforge analyze terraform --out ..."
```

### Pattern 4: copia confinada

```python
from sparkforge.facts.scan import varrer_source_files


def copiar(repo: Path, destino: Path) -> tuple[list[tuple[str, str]], list[dict[str, str]]]:
    varredura = varrer_source_files(repo, "*")
    manifesto = []
    for origem in varredura.arquivos:
        rel = origem.relative_to(repo).as_posix()
        dados = origem.read_bytes()
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(dados)
        manifesto.append((rel, hashlib.sha256(dados).hexdigest()))
    return manifesto, [{"path": p.relativo, "reason": p.razao} for p in varredura.pulos]
```

---

## Data Flow

```text
L1: facts (uniao) -> [tune_conf | --set] -> {chave: novo}
    -> para cada chave: facts tf.spark_conf/pyspark.conf_set da chave
       -> 0: refused sem_procedencia_em_arquivo (unlock: analyze terraform/pyspark do repo)
       -> >1 lugar: refused procedencia_ambigua (lista os lugares)
       -> 1: le repo/<file> (resolve_within), troca (Decision 1) -> diff por arquivo
    -> diff total (arquivos em ordem), rollback_diff, changes[], refused[]

L2: diff_path -> parse (recusas pre-disco) -> copia(repo) -> id
    -> before/ ; after/ = before + apply_patches (tudo ou nada; arquivo_fora_da_copia se o rel nao esta no manifesto)
    -> scan(before), scan(after) -> findings -> simulate.diff por chave estavel
    -> proof_obligations: validation + rollback dos findings em new e resolved
    -> next_steps: ["rode seus testes em after/", "sparkforge benchmark com dois runs", "sparkforge funcval plan"]
    -> report.json + retorno
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Nenhum | O pacote so le e grava disco local; sem rede, sem subprocess, sem git | Nenhuma |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Troca `.py` (string, numero, builder multilinha, UTF-8 antes do valor), troca `.tf` (4 pares na linha, fronteira de token), recusas do L1 | `tests/test_change_plan.py` | pytest | AT-001, AT-002, AT-005 a AT-007, SC4 |
| Unit | Parser e aplicador: hunk, CRLF, prefixos a/b, as 6 recusas, tudo ou nada, ida-e-volta | `tests/test_change_apply.py` | pytest | AT-010, AT-011, SC2, SC6 |
| Integracao | Sandbox: arvore principal intacta por hash, `id` estavel, `--clean` confinado, `arquivo_fora_da_copia` | `tests/test_change_sandbox.py` | pytest + `tmp_path` | AT-008, AT-012 a AT-015, SC5, SC8 |
| Golden | `fixtures/change/`: plano (`tf_linha_compartilhada`, `codigo_conf_set`, `codigo_builder_multilinha`, `do_tune`, `sem_procedencia`, `linha_nao_confere`, `procedencia_ambigua`, `valor_nao_literal`) e sandbox (`resolve_achado`, `diff_nao_aplica`, `escapa_da_raiz`, `plano_pelo_sandbox`) | `tests/test_fixtures_golden_change.py` | pytest | AT-001 a AT-004, AT-009, SC1, SC3, SC7 |
| Estrutural | Sem `subprocess`, `git` nem provider em `sparkforge/change/` (AST dos imports e chamadas) | `tests/test_change_plan.py` | pytest | SC9 |
| Registros | Tool nova, surface, claims, referencia | suites existentes | pytest + gates | SC10 |

O caso `resolve_achado` reusa o padrao de `fixtures/pyspark/conf_set_conflict`: `SF-PY-012` dispara em `spark.conf.set`, o diff do host tira a chamada e a regra sai em `resolved`, com `validation` e `rollback` dela.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Entrada invalida (sem `--facts`, `--set` malformado, `--from-tune` e `--set` juntos, repo inexistente, diff ilegivel) | `AdapterError` exit 2, mensagem com o comando `sparkforge change ...` que resolve (tool FAILABLE contem "sparkforge") | No |
| Chave sem base | `refused[]` com `reason`, `detail` e `unlock`; o verbo nao falha | No |
| Diff recusado pelo aplicador | Resultado com `refused` e `applied: false`; `after/` nao e gravado; exit 1 na CLI | No |
| `scan` com `analyze_falhou` num lado | Vai ao relatorio (`scan_failures.before/after`); a comparacao segue com o que foi julgado | No |
| Falha de disco na copia | `AdapterError` com o caminho relativo; o diretorio do `id` e removido | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `_DIFF_MAX_BYTES` | int (constante) | `2 * 1024 * 1024` | Teto do diff aceito pelo L2 |
| `_SANDBOX_DIR` | Path (constante) | `.sparkforge/sandbox` | Raiz das copias |
| `_ID_HEX` | int (constante) | `16` | Tamanho do `id` |

---

## Security Considerations

- Diff e entrada nao confiavel: caminho confinado duas vezes, no parse (sem absoluto e sem `..`) e na gravacao (`resolve_within(after, rel)`).
- A copia nunca le arquivo sensivel, porque a varredura recusa por nome antes do `stat`. O diff que o toca sai `arquivo_fora_da_copia`.
- Nada executa codigo do repositorio: os extratores do `scan` leem por AST e texto. Nenhum subprocess.
- `--clean` apaga so dentro de `.sparkforge/sandbox/`, conferido por `resolve_within`.
- Leitura do repo no L1 por `resolve_within(repo, subject.file)`: fact adulterado com `../` e recusado (`caminho_fora_da_raiz`).

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum novo; o relatorio e o registro |
| Metrics | Nenhuma nova |
| Tracing | As duas tools passam por `call_tool`, que ja grava o span |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | design-agent | Versao inicial. A-002 resolvido pelo span do no (bytes UTF-8); A-005 por duas copias; A-008 reusando `simulate.diff` com `stable_keys`. `spark_default_explicit` passa a ser editavel (correcao de SC3). Recusas acrescentadas: `diff_vazio`; `moved_candidates` para achado deslocado |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_AUTONOMY_L1_L2.md`
