---
sdd: 1
feature: SDD_OPERATOR_DURAVEL
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Com os artefatos do operador em .sparkforge/sdd, as referencias volateis (case, sandbox) tratadas como historicas depois do ship, o fact citado por kind e a prova de tarefa por funcval, fact ou achado movido, uma feature operator continua passando no sdd check fora da sessao que a escreveu."
  prediction: "O fluxo operator ponta a ponta com case_open, change_sandbox e change_propose reais, raiz .sparkforge/sdd, uma tarefa provada por finding e um moved conferido contra o report.json real passa no sdd check; continua passando depois de change sandbox clean (pelo pacote de proposal) e depois de trocar o case com o ship done; e o mesmo fluxo com os artefatos em docs/sdd faz change propose recusar a copia como desatualizada. Se qualquer uma dessas quatro observacoes falhar no teste, a afirmacao esta errada."
  experiment: "Estender tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta com as tools reais e cobrir cada gate novo em tests/test_sdd.py, rodando os dois arquivos."
acceptance:
  - id: AC1
    statement: "Artefatos do operador em .sparkforge/sdd sao descobertos por sdd check e carimbados por sdd stamp com --root .sparkforge/sdd, e escreve-los ali nao deixa o sandbox desatualizado para change propose, ao contrario de docs/sdd."
    verified_by: {kind: test, ref: "tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta"}
  - id: AC2
    statement: "change_id e aceito quando existe .sparkforge/sandbox/<id>/ ou .sparkforge/proposal/<id>/, as duas bases com um segmento so e confinadas."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_change_id_aceita_proposal"}
  - id: AC3
    statement: "case_missing e change_missing so valem enquanto o ship da feature nao carregou com status done; com o ship done, case trocado e sandbox apagado nao recusam."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_case_e_change_historicos_depois_do_ship"}
  - id: AC4
    statement: "verified_by kind fact aceita o seletor path#kind:<kind>, que passa quando o arquivo tem ao menos um fact daquele kind; path#<id> continua valendo."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_fact_por_kind"}
  - id: AC5
    statement: "No perfil operator, tarefa do plan pode declarar proof {kind funcval, fact ou finding, ref} no lugar de test; finding e <change_id>#<rule_id>; no dev, proof sem test continua task_without_test."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_proof_de_tarefa_operator"}
  - id: AC6
    statement: "No perfil operator, tarefa do build_report pode declarar moved {change_id, resolved} no lugar de red e green; o gate exige cada rule_id em resolved e fora de new no relatorio do sandbox ou do pacote de proposal, e recusa com moved_not_observed."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_moved_confere_o_relatorio"}
  - id: AC7
    statement: "Os schemas de plan e build_report continuam recusando campo desconhecido, inclusive dentro de proof e moved."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_proof_e_moved_fecham_propriedades"}
  - id: AC8
    statement: "As skills sdd-define, sdd-plan, sdd-build e sdd-ship e docs/sdd/README.md ensinam a raiz .sparkforge/sdd, o seletor por kind, proof e moved, e os comandos com as flags de evidencia."
    verified_by: {kind: test, ref: "tests/test_sdd_operator.py::test_skills_ensinam_o_operador_duravel"}
  - id: AC9
    statement: "Os espelhos das skills conferem com a renderizacao."
    verified_by: {kind: command, ref: "python scripts/sync_skills.py --check"}
success:
  - id: SC1
    metric: "Codigos novos de recusa e lacuna exercitados pelos testes do nucleo e do fluxo operator"
    source: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q"
  - id: SC2
    metric: "Bytes de skills antes e depois, lidos do surface lock"
    source: "python scripts/check_surface_lock.py --update (docs/surface.lock.json)"
out_of_scope:
  - "Julgar se o achado resolvido e o certo: o veredito continua com judge e com as SF-* (regra 11)."
  - "Conferir o achado em after/.sparkforge/scan/findings.json: o pacote de proposal nao o carrega, e o gate le so o relatorio."
  - "Mudar o perfil dev: test continua obrigatorio e red continua exigido."
  - "A revisao de texto das skills que nao toca o perfil operator (feature SDD_SKILLS_REVISAO)."
unknowns: []
change_kinds: [agent_or_skill]
---

# SDD_OPERATOR_DURAVEL — o perfil operator fora da sessão viva

## Problema

Uma revisão do perfil operator (feature `SDD_OPERATOR`) achou que ele quebra
assim que a sessão que o escreveu termina:

1. **Onde os artefatos moram.** As skills mandam gravar em `docs/sdd/` do
   repositório do operador. Isso muda a árvore que `change sandbox` copiou, e
   `change propose` recusa a cópia como desatualizada.
2. **`change_missing` só olha o sandbox.** `.sparkforge/sandbox/` é recriado e
   limpo (`change sandbox --clean`); o pacote que sobra é
   `.sparkforge/proposal/<id>/`, com o mesmo id.
3. **Referência volátil depois do ship.** O `case.yaml` atual pode ser de outro
   case, e o sandbox pode ter sido limpo. Uma feature entregue não deveria
   voltar a ser recusada por isso.
4. **Fact por id.** O id de fact é hash de conteúdo, desconhecido na hora do
   define. Só o `kind` é conhecido antes da coleta.
5. **Prova de tarefa.** O operador raramente tem pytest; o gate exigia `test`
   em toda tarefa e `red`/`green` em todo build.

## O que muda

- Raiz do operador: `.sparkforge/sdd` (`--root .sparkforge/sdd`).
- `change_id` aceito pelo sandbox ou pelo pacote de proposal.
- `case_missing` e `change_missing` param de valer com o ship `done`.
- Seletor `path#kind:<kind>` no `verified_by` de fact.
- `proof` na tarefa do plan e `moved` na tarefa do build, só no operator, com
  os códigos novos `finding_not_observed` (lacuna) e `moved_not_observed`
  (recusa).
- Skills e README contam tudo isso.

As decisões 1 a 6 vieram prontas da revisão; o design registra cada uma com a
alternativa rejeitada e o rollback.
