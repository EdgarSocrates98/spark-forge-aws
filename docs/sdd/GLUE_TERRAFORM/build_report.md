---
sdd: 1
feature: GLUE_TERRAFORM
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/GLUE_TERRAFORM/plan.md
  sha256: "313109dde453b3dc5c3c0a2752f83da560ec2e3c89c0b11833432351d68a55ea"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_glue_terraform.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_glue_terraform.py -q", exit: 0}
claims:
  - text: "As duas funcoes tem uma definicao so, em sparkforge/facts/glue_terraform.py, e os dois extratores usam ELA: a conferencia e por identidade, nao por nome."
    evidence_ref: "tests/test_glue_terraform.py::test_a_definicao_e_unica_e_os_dois_extratores_importam"
  - text: "As tres origens de max_retries respondem o mesmo de antes, inclusive o not_literal conservador quando ha tf.unresolved de max_retries no MESMO arquivo."
    evidence_ref: "tests/test_glue_terraform.py::test_as_tres_origens_de_max_retries_e_o_indice_por_nome"
  - text: "O modulo nao tem EMITTED_KINDS nem EXTRACTOR_ID, e nao e citado pelas listas manuais nem pela medida de snippet: e essa ausencia que o mantem fora das varreduras."
    evidence_ref: "tests/test_glue_terraform.py::test_o_modulo_auxiliar_nao_conta_como_extrator"
  - text: "As duas derivacoes que consomem as funcoes continuam produzindo os mesmos facts: os goldens dos dois dominios passam sem regeneracao."
    evidence_ref: "tests/test_fixtures_golden_airflow.py::test_golden"
  - text: "Nenhum golden do repositorio mudou: a suite inteira deu 3299 passed e 4 skipped, o mesmo numero de antes da refatoracao, sem regeneracao."
    evidence_ref: "tests/test_fixtures_golden_stepfunctions.py::test_golden"
  - text: "A contagem publicada de extratores de facts nao se moveu, e o STATUS.md nao precisou ser editado."
    evidence_ref: "docs/superpowers/STATUS.md"
---

# GLUE_TERRAFORM — relatório do build

## A tarefa

| tarefa | commit | o que entregou |
|---|---|---|
| T1 | `d7890433` | o módulo auxiliar, os três testes, e os dois extratores importando |

Uma tarefa só, de propósito: criar o módulo sem trocar os chamadores, ou o contrário,
deixaria a árvore vermelha entre dois commits.

## O vermelho, e como ele foi obtido

`red` é **exit 2**, erro de coleta, com a linha decisiva
`ModuleNotFoundError: No module named 'sparkforge.facts.glue_terraform'`. O módulo ausente
era a unidade sob teste.

**Esse exit é meu, e vale dizer como.** O subagente da T1 travou esperando o próprio gate
de lastro e nunca entregou relato — o mesmo padrão que, na SFN_HISTORY, deixou a T4 em
`skipped` para sempre. Desta vez, em vez de herdar o buraco, **reproduzi o vermelho**: tirei
`sparkforge/facts/glue_terraform.py` do lugar, rodei o teste, li o `ModuleNotFoundError` e
capturei o exit, e devolvi o arquivo. O verde veio logo depois, 3 passed.

## O que a revisão final achou

Um revisor novo leu o diff inteiro contra o define e o design, medindo em memória. Achou
**um crítico, três importantes e dois menores**, corrigidos em dois commits (`9d1d86f1` e
`faf1b59c`).

### O crítico: a branch reprovava o CI, e eu tinha aceitado o contrário

O gate de lastro estava defasado. O relatório do implementador dizia exit 0 — ele o rodou
**antes** de criar os dois `.py` novos, e leu o resultado de um estado que já não existia.
Eu aceitei o relato sem reconferir.

Medido depois: `iter_source_files(raiz, "*.py")` devolve **776** arquivos, e
`docs/harness/CODEINTEL-GAP.md` publicava **774**. O gate listou **seis** ids — um a mais
do que a revisão previra —, e **duas das alegações caíram em vez de subir**:
`stepfunctions.py` e `airflow_dag.py` encolheram cerca de 56 linhas cada, e os dois estão
dentro do corpus medido. Refatoração que remove código move alegação para baixo.

### Os três importantes, todos prosa afirmando mais do que o artefato sustenta

- **"As TRÊS varreduras do repositório"** era artigo definido e exaustivo. A revisão achou
  seis lugares que discriminam por `EMITTED_KINDS`; a correção contou de novo e achou
  **sete**, incluindo uma em **produção** (`sparkforge/diagnosis/root_cause.py`, que monta
  o mapa `emitted_by`) e uma que a própria revisão perdera
  (`tests/test_rules_errors.py`). As sete já ignoravam o módulo corretamente: o defeito era
  o numeral. A frase nova não tem numeral fechado — ela diz que é a lista **do que foi
  conferido**, com a data.
- **A duplicação foi datada no incremento errado.** A docstring dizia "do incremento do
  Step Functions"; em `b324aa3b` havia **uma** definição de cada função, e a cópia nasceu em
  `f155fddf`, o incremento do Airflow. A mensagem do commit que introduziu a docstring
  acertava, e a docstring errava.
- **"Três revisões finais seguidas conferiram à mão"** não tinha lastro. Varridos os 17
  `ship.md`, existe **um** registro de conferência.

### O que a correção mediu e decidiu preservar

Três peculiaridades que as cópias antigas já tinham e o módulo novo manteve, todas fora do
escopo declarado no define e agora nomeadas na docstring para não serem redescobertas como
novidade: o truncamento silencioso de `value` float (`int(2.9) == 2`); o `name` literal sem
`value` indexando sob a chave `"None"`; e o `subject.file` ausente virando `""`.

A terceira rende mais do que se supunha, e a correção mediu isso: esse `""` **não casa nem
com o fact de onde veio**, então `max_retries` devolve `("absent", 0, None)` — um zero que
ninguém leu, que é exatamente o que a conservadoria do `not_literal` existe para evitar.
Está escrito na docstring como fato preservado, não como conserto.

## Desvios do plano e do design

1. **O manifesto do design estava incompleto para o AC5.**
   `docs/vnext/adrs/ADR-010-code-intelligence-indice-local.md` carrega uma das alegações
   remediadas e não estava no `files:`. A linha foi acrescentada e a cascata recarimbada.
2. **O gate de lastro listou seis ids, e o plano não previa nenhum em particular** — como
   nas quatro tarefas da feature anterior. A lista veio da saída, um id por vez.
3. **Vários campos `context` do `docs/claims.lock.json` estavam defasados** de remediações
   antigas: o de `VNX-640` dizia `**501**`. O gate não confere esse campo.
4. **O plano escrevia `git commit -F <arquivo com a mensagem>`**, e o marcador foi
   executado literalmente: sobraram três arquivos vazios na raiz (`[(arquivo`, `nome`,
   `modulo`). Removidos. Planos futuros precisam de um caminho real ou de aviso explícito.
5. **A revisão em dois estágios por tarefa não rodou**; a revisão final do diff inteiro
   rodou, e é dela que vieram os seis achados.

## Medidas

| | antes (`e4141869`) | depois |
|---|---|---|
| definições de cada leitor de Terraform | 2 | 1 |
| arquivos `.py` no corpus medido | 774 | 776 |
| extratores de facts publicados | 41 | 41 |
| goldens passando | 3299 | 3299 |
