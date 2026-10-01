---
sdd: 1
feature: SDD_MIGRATION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_MIGRATION/plan.md
  sha256: "da0d4e6e503e6c2435a3f9b758340352516dfb57d91324f3ab294207ac5b93f2"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd_migration.py::test_agentspec_desligado_no_projeto -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_migration.py tests/test_vendor_caveman.py tests/test_execution_surface.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sdd_migration.py::test_historico_agentspec_arquivado -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_migration.py tests/test_arvore_versionada.py tests/test_agents_parity.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_facts_secrets.py tests/test_harness_untrusted.py tests/test_codeintel_security.py tests/test_knowledge_drift.py tests/test_bootstrap_budget.py tests/test_sdd.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sdd_migration.py::test_superpowers_congelado -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_migration.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_arvore_versionada.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_sdd_migration.py::test_documentos_de_entrada_apontam_o_sdd -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_migration.py tests/test_bootstrap_budget.py tests/test_docs_coverage.py tests/test_vendor_caveman.py tests/test_skill_content.py tests/test_agents_parity.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_sdd_migration.py::test_readme_e_journal -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_migration.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_execution_surface.py tests/test_adapters_code_surface.py tests/test_capability_parity.py tests/test_codeintel_search.py -q", exit: 0}
claims:
  - text: "O projeto desliga agentspec@agentspec em .claude/settings.json, sem mexer nos plugins caveman."
    evidence_ref: "tests/test_sdd_migration.py::test_agentspec_desligado_no_projeto"
  - text: "Nenhum arquivo rastreado sob .claude/sdd/; os 103 documentos do AgentSpec estao em docs/sdd/archive/agentspec/ por renomeacao com conteudo identico (R100), e .claude/sdd/ esta no .gitignore."
    evidence_ref: "tests/test_sdd_migration.py::test_historico_agentspec_arquivado"
  - text: "O arquivo nao vira feature: sdd check descobre as mesmas seis features de antes."
    evidence_ref: "sparkforge/sdd/checks.py"
  - text: "docs/superpowers/README.md declara specs/ e plans/ congelados e aponta docs/sdd/; STATUS.md continua ali."
    evidence_ref: "tests/test_sdd_migration.py::test_superpowers_congelado"
  - text: "CLAUDE.md, AGENTS.md e CONTRIBUTING.md citam sdd-define e sparkforge sdd check, e nenhum manda o fluxo para .claude/sdd/."
    evidence_ref: "tests/test_sdd_migration.py::test_documentos_de_entrada_apontam_o_sdd"
  - text: "CLAUDE.md foi de 22868 para 23533 bytes e AGENTS.md de 21582 para 22145, abaixo do teto de 26000."
    evidence_ref: "tests/test_bootstrap_budget.py::test_arquivos_de_instrucao_cabem_no_teto"
  - text: "README.md apresenta as seis skills, os tres verbos e os dois perfis; .sparkforge/journal.jsonl esta ignorado."
    evidence_ref: "tests/test_sdd_migration.py::test_readme_e_journal"
  - text: "O corpus de *.py foi de 738 para 739, relido pela propria prova de VNX-640."
    evidence_ref: "docs/claims.lock.json"
change_id: null
---

# SDD_MIGRATION — relatório do build

Cinco tarefas, um commit cada: `3bc603b5` (T1), `b9e2d365` (T2), `901c981a`
(T3), `417ce5b4` (T4), `993c9202` (T5); mais `4e7fde07` com a lista de
alegações. Todo vermelho foi visto na hora, e cada um pelo comportamento
ausente: T1 `KeyError` (a chave não existia), T2 a lista de `.claude/sdd` não
vazia, T3 `FileNotFoundError` do próprio `docs/superpowers/README.md` (o
arquivo é a unidade sob teste), T4 e T5 a asserção sobre o texto de antes.

## Sem subagente

Este build rodou num agente só, que não despacha subagente. Não houve
implementador novo por tarefa, revisão em dois estágios nem revisão final por
revisor novo. A releitura do diff inteiro (de `e56cc9d4` até o último commit)
foi feita pelo mesmo agente: os cinco critérios têm entrega, e as 103
renomeações são `R100` (`git diff -M --name-status`).

## Desvios do plano

1. **Arquivos fora do manifesto:** `docs/superpowers/STATUS.md` (nota de que
   os ponteiros `.claude/sdd/...` das entradas antigas resolvem sob
   `docs/sdd/archive/agentspec/`, sem reescrever as entradas),
   `GUIA_DE_USO.md` (a linha do laço `/spec` do caveman aponta o SDD para
   mudança no próprio repositório), `docs/claims.lock.json` e
   `docs/harness/CODEINTEL-GAP.md` (VNX-640, 738 → 739).
2. **Recusa transitória esperada.** Entre T2 e este relatório, `sdd check`
   recusou `manifest_path_unknown` em `design.md` (`.claude/sdd` com `action:
   delete` já sumido). O gate só aceita o `delete` sumido com o build pronto;
   com este relatório em `ready` a recusa some.
3. **T2, gates.** O plano não listava os testes que varrem a árvore; rodei os
   que leem `docs/` ou `.claude/` (`test_agents_parity`, `test_facts_secrets`,
   `test_harness_untrusted`, `test_codeintel_security`,
   `test_knowledge_drift`). Nenhum lê `docs/sdd/archive/`, então nenhum gate
   precisou de exclusão.
4. **Documentos revistos sem mudança:** `.github/copilot-instructions.md` e
   `.devin/README.md` não descrevem o fluxo de desenvolvimento;
   `docs/guia/05-agents-e-skills.md` já apontava as skills `sdd-*`; `GEMINI.md`
   não existe no repositório.

## Decisões tomadas sozinho

- A seção nova do README fica antes de *Instalação*, com tabela de fases e os
  três verbos; a alternativa (só um parágrafo em *Skills incluídas*) não dizia
  os perfis.
- STATUS ganhou uma nota no cabeçalho em vez de ter os nove ponteiros
  trocados: trocar reescreveria entradas datadas.

## Gates rodados no fechamento

- `python scripts/sync_skills.py --check`: OK, exit 0 (README de
  `.claude/agents/` fora da árvore durante os gates).
- `python scripts/gen_reference_docs.py`: 268 páginas, 0 regravadas.
- `python scripts/check_surface_lock.py --update`: sem mudança.
- `python scripts/check_vnext_claims.py`: 1 divergência (VNX-640), remediada
  por id; depois 0.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.
- Bateria de 13 arquivos (`test_sdd`, `test_sdd_operator`, `test_sdd_skills`,
  `test_sdd_migration`, `test_skill_content`, `test_sync_render`,
  `test_agents_parity`, `test_agent_coverage`, `test_docs_coverage`,
  `test_reference_docs`, `test_arvore_versionada`, `test_bootstrap_budget`,
  `test_vnext_claims`): 1316 verdes.
