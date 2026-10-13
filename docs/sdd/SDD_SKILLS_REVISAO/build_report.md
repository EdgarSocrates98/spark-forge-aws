---
sdd: 1
feature: SDD_SKILLS_REVISAO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_SKILLS_REVISAO/plan.md
  sha256: "e8c3872b9fd3486fac7bf2d15ad3a4845e94286905ddb85e2fccd16017f472ee"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_o_detector_recusa_flag_inventada -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_descricoes_so_com_gatilho -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py tests/test_sdd_operator.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_blocos_comuns_moram_no_readme -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py tests/test_sdd_operator.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_revisao_de_build_e_ship -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py tests/test_sdd_operator.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_revisao_de_define_explore_plan_ship -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py tests/test_sdd_operator.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_templates_revisados -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py tests/test_sdd_operator.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q", exit: 0}
claims:
  - text: "O teste de comandos confere cada --flag no subparser do verbo citado, com marcador <...> trocado por valor ficticio, e recusa flag inventada ou de outro verbo; todas as skills sdd-* passam."
    evidence_ref: "tests/test_sdd_skills.py::test_o_detector_recusa_flag_inventada"
  - text: "As seis descricoes comecam com 'Use quando', sem resumo do fluxo, e cabem em 320 caracteres."
    evidence_ref: "tests/test_sdd_skills.py::test_descricoes_so_com_gatilho"
  - text: "O README guarda o laco de cada fase, o caminho da mudanca do operador e o conhecimento citado, e as skills apontam para as secoes."
    evidence_ref: "tests/test_sdd_skills.py::test_blocos_comuns_moram_no_readme"
  - text: "sdd-build e sdd-ship citam as flags de evidencia e mandam rodar cada verified_by command com exit 0; sdd-build tem revisao final, leitura critica e quem escreve red/green."
    evidence_ref: "tests/test_sdd_skills.py::test_revisao_de_build_e_ship"
  - text: "sdd-define exige a leitura do operador e previsao mensuravel; sdd-ship exige a previsao inteira, cita a regra 21, lista as quatro opcoes e pede Licoes."
    evidence_ref: "tests/test_sdd_skills.py::test_revisao_de_define_explore_plan_ship"
  - text: "Os templates estao acentuados, dizem para trocar EXEMPLO e por draft, e continuam formando uma feature valida."
    evidence_ref: "tests/test_sdd_skills.py::test_templates_formam_feature_valida"
  - text: "A superficie de skills caiu 254 bytes (532261 para 532007)."
    evidence_ref: "docs/surface.lock.json"
change_id: null
---

# SDD_SKILLS_REVISAO — relatório do build

Seis tarefas, um commit cada: `02f62cb0` (T1), `e2b20a08` (T2), `d41d4e24`
(T3), `e09e985a` (T4), `eeec948f` (T5), `b2829829` (T6). Todo vermelho foi
visto na hora. O de T1 é `NameError: _flags_recusadas`, que é a unidade sob
teste; os de T2 a T6 são asserções sobre o texto de antes.

## Sem subagente

Este build rodou num agente só, que não despacha subagente. Não houve
implementador novo por tarefa, revisão em dois estágios nem a revisão final
por revisor novo que a própria `sdd-build` agora pede. A releitura do diff
inteiro foi feita pelo mesmo agente antes do ship: nenhum critério sem
entrega, e nenhuma flag citada fora do parser.

## Desvios do plano

1. **T4, texto ajustado à asserção.** O primeiro texto quebrou a frase "O
   controlador escreve `red` e `green`" entre duas linhas, e o teste de T4
   continuou vermelho; a frase foi reescrita numa linha só no mesmo commit.
2. **T3, `sdd-explore`.** A skill não tinha seção de operador; ela aponta só
   para o laço e para o conhecimento citado, como o teste pede.
3. **Tamanho.** As skills somadas caíram 254 bytes (43664 para 43410 nos seis
   `SKILL.md`): `sdd-define` −415, `sdd-design` −882, `sdd-explore` −265,
   `sdd-plan` −213, `sdd-build` +318, `sdd-ship` +1203. O ganho da mudança
   para o README foi em boa parte gasto nos itens novos de build e ship. O
   README cresceu (as três seções).
4. **Registros fora do manifesto:** `docs/guia/referencia/skills/README.md`
   (índice das skills, regravado pelas descrições novas).

## Gates rodados no fechamento

- `python scripts/sync_skills.py` (README de `.claude/agents/` fora),
  depois `--check`: OK, exit 0.
- `python scripts/gen_reference_docs.py`: 7 páginas regravadas.
- `python scripts/check_surface_lock.py --update`: skills 532261 → 532007
  (−254).
- `python scripts/check_vnext_claims.py`: 0 divergências.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.
