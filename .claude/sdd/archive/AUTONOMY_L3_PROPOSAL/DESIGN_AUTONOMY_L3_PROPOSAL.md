# DESIGN: Autonomia L3 — pacote de proposta de PR

> Technical design for implementing Autonomia L3 — pacote de proposta de PR

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L3_PROPOSAL |
| **Date** | 2026-09-14 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_AUTONOMY_L3_PROPOSAL.md](./DEFINE_AUTONOMY_L3_PROPOSAL.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
.sparkforge/sandbox/<id>/            (L2, ja rodado)
   ├─ before/   copia da arvore de origem
   ├─ after/    copia + diff ; after/.sparkforge/scan/{facts_*.json, findings.json}
   └─ report.json
            │
            ▼
sparkforge change propose --sandbox <id> [--benchmark f]... [--funcval f] [--now iso]
            │
   change/proposal.py (puro, sem git, sem subprocess)
   ├─ 1. ler report.json ............ sandbox_inexistente / sandbox_nao_aplicado
   ├─ 2. inventario(repo) == inventario(before/) ...... sandbox_desatualizado
   ├─ 3. severidade dos `new` pelos findings de after/ .. achado_novo_bloqueante (P0/P1)
   ├─ 4. change.patch / rollback.patch (difflib before/ <-> after/, files_changed)
   ├─ 5. pr_body.md (+ bloco do report sign sobre os findings de after/)
   ├─ 6. commit_message.txt, branch.txt, commands.md (texto; o host executa)
   ├─ 7. evidence/sandbox_report.json, evidence/receipt.json (receipt.build, raiz after/, spans None)
   └─ 8. manifest.json (sha256 de cada arquivo) -> grava em .sparkforge/proposal/<id>/ (tmp + replace)
            │
            ▼
host (skill propose-change-pr): le commands.md, git switch/apply/add/commit,
   PARA antes de `git push` e de `gh pr create` (policy ask + confirmacao da skill)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/change/proposal.py` | Montagem pura do pacote a partir do sandbox | stdlib (`difflib`, `hashlib`, `json`) |
| `sparkforge/change/refusals.py` | Quatro recusas novas com `unlock` | constantes existentes |
| `sparkforge/adapters/_core.py::change_propose` | Resolve o repo, carrega anexos, chama receipt e report sign, grava | padrão dos verbos de topo |
| `sparkforge change propose` / `sparkforge_change_propose` | CLI e tool (`_WRITE_IDEMPOTENT`) | argparse, `TOOLS` |
| `skills/propose-change-pr/SKILL.md` | Roteiro do host, com as paradas de confirmação | skill não despachável |
| `.sparkforge/policy.yaml` + `.claude/settings.json` | `git push *` e `gh pr create *` em `ask` | `policy sync-settings` |

---

## Key Decisions

### Decision 1: Árvore mudada se detecta comparando o inventário atual com `before/`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** O sandbox não guarda o diff nem o manifesto; o `id` é sha256 dos dois. Recalcular o `id` exigiria o diff original.

**Choice:** `sandbox.inventariar(repo).manifesto` (lista de `(rel, sha256)` com os mesmos pulos do L2) contra o inventário de `before/`. Qualquer diferença — arquivo mudado, novo ou removido — recusa `sandbox_desatualizado`, listando até 20 caminhos e a contagem.

**Rationale:** `before/` é por construção a árvore sobre a qual o diff foi validado; comparar com ela é a pergunta certa, sem guardar estado novo no L2.

**Alternatives Rejected:**
1. Recalcular o `id` — o diff original não existe mais.
2. Guardar o manifesto no `report.json` do L2 — muda o golden do L2 sem necessidade.

**Consequences:**
- Custo de ler a árvore duas vezes (a mesma ordem do sandbox).

---

### Decision 2: Patch regenerado de `before/` para `after/`, provado pelo próprio aplicador

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** A-002. O `change.patch` precisa aplicar na árvore de origem com `git apply`.

**Choice:** Para cada `files_changed`, `difflib.unified_diff` com cabeçalhos `a/<rel>` e `b/<rel>` e três linhas de contexto, o mesmo formato do `change plan`; `rollback.patch` é o inverso. Antes de gravar, o pacote aplica o `change.patch` com `apply_patches` sobre os bytes de `before/` e confere que o resultado é o `after/`; se não for, `AdapterError` (defeito, não recusa). O golden também roda `git apply --check` quando o git existe na máquina de teste.

**Rationale:** O aplicador estrito do L2 é a mesma régua que validou o sandbox.

**Alternatives Rejected:**
1. Pedir o diff de novo ao operador — duas fontes de verdade.

**Consequences:**
- Arquivo com CRLF: o `difflib` trabalha por linha com o fim preservado, como no `change plan`.

---

### Decision 3: Corpo do PR, assinatura e recibo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** A-004 e A-005. O bloco do `report sign` é visível (lista entre comentários HTML) e fecha o arquivo. O recibo sem `run_id` recebe `spans=None`.

**Choice:** `pr_body.md` com, nesta ordem: resumo (chaves e valores, de onde veio o valor — `basis` do `tune` quando o `report.json` o traz), achados resolvidos, achados novos P2/P3 em "Atenção", obrigações de prova (validation e rollback por regra), medidas (anexos, ou PENDENTE com o verbo que as produz), "O que esta proposta não afirma" (ganho, custo, efeito em produção), e por último `## Assinatura` seguido do bloco do `report sign` calculado sobre os findings de `after/`. O recibo sai de `receipt.build` com raiz em `after/`, facts `after/.sparkforge/scan/facts_*.json`, findings `after/.sparkforge/scan/findings.json`, `now` recebido e `run_id=None`, gravado em `evidence/receipt.json`.

**Rationale:** O revisor confere o corpo com `report verify` e a árvore com o recibo, sem acesso ao sandbox.

**Alternatives Rejected:**
1. Assinar um arquivo à parte — o que o revisor lê é o corpo.

**Consequences:**
- O rodapé de assinatura aparece no PR, com título que o explica.

---

### Decision 4: Contrato da tool e do verbo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** Mesma classe e mesmo `now` do recibo; saída no molde do sandbox.

**Choice:** `sparkforge_change_propose` (`_WRITE_IDEMPOTENT`, `required: [repo, sandbox_id, now]`, `benchmark_paths`, `funcval_path`), dono `sf-verifier` (checagem 11). Saída: `stage: propose_change`, `applied: false`, `git_run: false`, `main_tree_touched: false`, `refused`, `proposal` (caminho relativo), `id`, `files` (lista do pacote), `branch`, `blocking_findings`, `attention_findings`, `pending_measures`. CLI `sparkforge change propose --sandbox <id> [--repo .] [--benchmark f]... [--funcval f] [--now iso]`, com `now` default UTC. Recusa sai no payload e a CLI sai com código 1; erro de entrada é `AdapterError` exit 2 com o comando que resolve.

**Rationale:** Idempotência vem de `now` fixo; recusa não é erro.

**Alternatives Rejected:**
1. `LOCAL_MUTATION` — grava em pasta própria ignorada pelo git, o mesmo que o sandbox.

**Consequences:**
- Tools 102 -> 103; caminho declarado 94 -> 95 (a tool declara `repo`).

---

### Decision 5: O host executa, com duas paradas

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** "Request human approval" do §15, e a regra de que o pacote não roda git.

**Choice:** `commands.md` numerado: `git switch -c <branch>`, `git apply --check`, `git apply`, `git add <files_changed>`, `git commit -F commit_message.txt`, **PARE**, `git push -u origin <branch>`, **PARE**, `gh pr create --title <título> --body-file pr_body.md`; e a seção de rollback (`git apply -R change.patch` ou `git apply rollback.patch`). Skill `propose-change-pr` não despachável (motivo em `NON_DISPATCHABLE_SKILLS`: roda git na árvore do operador e precisa das confirmações no agente pai). Policy padrão com `git push *` e `gh pr create *` em `ask`, e `sync-settings` regrava o `permissions.ask`.

**Rationale:** Duas barreiras independentes: a skill pede, e o Claude Code pergunta.

**Alternatives Rejected:**
1. Só a skill — um host sem a skill não teria barreira nenhuma.

**Consequences:**
- Todo `git push` no repositório passa a pedir confirmação no Claude Code, não só os do L3.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/change/refusals.py` | Modify | 4 recusas | @python-developer | None |
| 2 | `sparkforge/change/proposal.py` | Create | Montagem pura | @python-developer | 1 |
| 3 | `sparkforge/change/__init__.py` | Modify | Exporta `montar` | @python-developer | 2 |
| 4 | `sparkforge/adapters/{_core,cli,tools}.py` | Modify | Verbo, tool, schema | @python-developer | 2 |
| 5 | `skills/propose-change-pr/SKILL.md` | Create | Roteiro do host | (general) | 4 |
| 6 | `.sparkforge/policy.yaml`, `.claude/settings.json`, `.gitignore` | Modify | `ask` e pasta ignorada | (general) | None |
| 7 | `fixtures/change/{proposta_completa,proposta_com_medida,proposta_desatualizada,proposta_bloqueada}/` | Create | Goldens | @test-generator | 4 |
| 8 | `tests/test_change_proposal.py`, `tests/test_fixtures_golden_change.py` | Create/Modify | Unidade, AST, golden | @test-generator | 7 |
| 9 | Registros: `tests/test_adapters_tools.py`, `test_harness_authorization.py`, `parity.yaml`, `manifest.json`, `agents/executors/sf-verifier.md`, `scripts/sync_skills.py`, `tests/test_sync_render.py`, `tests/test_fixtures_golden_mcp_parity.py` | Modify | Tool e skill novas | (general) | 4, 5 |
| 10 | `docs/guia/usos/change.md`, `docs/superpowers/STATUS.md`, `CLAUDE.md` (linha do `change`), `README.md` | Modify | Manual e números | (general) | 1-9 |

**Total Files:** 10 grupos

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1-4 | Python puro no molde do `change/` |
| @test-generator | 7, 8 | Goldens e teste por AST |
| (general) | 5, 6, 9, 10 | Registros literais do repositório |

**Agent Discovery:**
- Scanned: `agents/**/*.md` do agentspec
- Matched by: tipo de arquivo; o build constrói direto, como nas frentes anteriores

---

## Code Patterns

### Pattern 1: Inventário contra `before/`

```python
def desatualizados(repo: Path, antes: Path) -> list[str]:
    atual = dict(inventariar(repo).manifesto)
    validado = dict(inventariar(antes).manifesto)
    return sorted(
        rel for rel in atual.keys() | validado.keys() if atual.get(rel) != validado.get(rel)
    )
```

### Pattern 2: Patch provado antes de gravar

```python
patch = "".join(_diff(rel, antes, depois) for rel in files_changed)
aplicado = apply_patches({rel: (antes / rel).read_bytes() for rel in files_changed},
                         parse_unified_diff(patch))
if any(aplicado[rel] != (depois / rel).read_bytes() for rel in files_changed):
    raise ProposalDefect("change.patch nao reproduz after/")
```

### Pattern 3: Gravação atômica do pacote

```python
temporario = base.with_name(f".{base.name}.tmp")
shutil.rmtree(temporario, ignore_errors=True)
for rel, dados in arquivos.items():
    (temporario / rel).parent.mkdir(parents=True, exist_ok=True)
    (temporario / rel).write_bytes(dados)
shutil.rmtree(base, ignore_errors=True)
temporario.replace(base)
```

---

## Data Flow

```text
1. operador: change sandbox --diff d  ->  .sparkforge/sandbox/<id>/
   │
   ▼
2. change propose --sandbox <id>: recusas -> patch -> corpo -> assinatura -> recibo -> manifest
   │
   ▼
3. .sparkforge/proposal/<id>/  (ignorado pelo git)
   │
   ▼
4. host + skill: commands.md, parando antes de push e de PR
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| git / gh | Texto em `commands.md`, executado pelo host | Do operador, fora do pacote |
| `report sign` / `receipt.build` | Chamada Python local | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Recusas, inventário, patch provado, severidade dos `new`, corpo sem frase de ganho | `tests/test_change_proposal.py` | pytest | AT-003 a AT-008 |
| AST | `proposal.py` sem `subprocess`, `os.system`, `git`, `gh` | `tests/test_change_proposal.py` | `ast` | AT-013 |
| Golden | Sandbox dentro do teste + propose com `now` fixo, byte a byte e duas vezes | `tests/test_fixtures_golden_change.py` | pytest | AT-001, AT-002, AT-009 |
| Integração | `report verify` do `pr_body.md`; recibo com raiz em `after/`; `git apply --check` quando houver git | `tests/test_change_proposal.py` | pytest | AT-010 a AT-012 |
| Policy | `sync-settings` com as regras novas | teste de policy existente | pytest | AT-014 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Sandbox ausente, recusado, desatualizado ou com P0/P1 novo | `refused` no payload, nada gravado, CLI exit 1 | No |
| Anexo ilegível ou sem o kind esperado | `AdapterError` exit 2 com o comando que o produz | No |
| `change.patch` que não reproduz `after/` | `AdapterError` (defeito), nada gravado | No |
| Falha de disco | Temporário removido; `AdapterError` com o caminho relativo | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--now` | string ISO 8601 | agora (UTC) na CLI; obrigatório na tool | Entra no recibo |
| `--benchmark` | caminho (repetível) | ausente | Facts com `bench.run_delta` |
| `--funcval` | caminho | ausente | Resultado de `funcval compare` |

---

## Security Considerations

- Nenhum `subprocess`; git e gh só no host, com `ask` na policy e na skill.
- Caminhos confinados: sandbox e proposta por `resolve_within`, anexos dentro do repositório.
- O pacote não carrega segredo: o corpo cita chaves e valores já presentes no diff validado.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | N/A |
| Metrics | Span da tool pelo `call_tool` |
| Tracing | O recibo registra os artefatos; spans de tool `unresolved` de propósito |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | design-agent | Initial version |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_AUTONOMY_L3_PROPOSAL.md`
