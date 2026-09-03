# Gates por tipo de mudança

Este repositório guarda invariantes em listas escritas à mão e manifestos espalhados
por vários arquivos. Cada um existe porque um defeito real passou uma vez. O efeito
colateral é que **uma mudança pequena num lugar deixa vermelho um teste que ninguém
pensou em rodar**, e execução direcionada por definição não alcança.

Este documento é a lista que faltava. Ele foi escrito depois de a mesma classe de
problema aparecer quatro vezes na fase `SF-MIG` (2026-08-21), cada uma custando uma
execução da suíte completa para ser descoberta — entre 13 e 35 minutos.

A regra prática: **antes de commitar, ache a linha da sua mudança abaixo e rode os
gates dela.** Se a sua mudança não estiver na tabela, rode a suíte completa e
acrescente a linha.

---

## Acrescentar ou alterar uma REGRA no catálogo

`rules/catalog/*.yaml`

```
python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py \
  tests/test_rules_result_axis.py tests/test_rules_engine.py \
  tests/test_agent_coverage.py tests/test_router_agents.py \
  tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py \
  tests/test_refresh_knowledge.py -q
```

**A seção `runtime_scope`, abaixo, NÃO é opcional.** `runtime_scope` é campo
**obrigatório** de toda regra (ver `rules/catalog/README.md`), então *toda* regra nova cai
lá também — inclusive a que declara `{}`. Ler o "Além dos acima" daquela seção como
"quando eu decidir dar escopo" é o erro que esta linha existe para impedir; ele custou
seis testes vermelhos numa fase, e depois mais um numa área nova.

O que cada um cobra, medido na fase `SF-MIG`:

| gate | o que ele exige | como falhou de verdade |
|---|---|---|
| `test_agent_coverage` | toda área de regra tem coordenador que a declara | a área `SF-MIG` nasceu sem nenhum agente com ela em `rule_areas` |
| `test_router_agents` | a área **roteia** para um coordenador | declarar a área no agente não roteia; `rules/catalog/routing.yaml` precisa de entrada própria. Mesma lacuna já órfãou `SF-BENCH`, `SF-EMRS`, `SF-ENV`, `SF-FVAL` e `SF-UI` |
| `test_docs_coverage` | `manifest.json` declara a contagem real | `rule_count` ficou em 116 depois de três regras novas. A docstring do teste registra que esse número já apodreceu três vezes, duas delas no `README.md` |
| `test_fixtures_kind_coverage` | toda regra tem golden que a dispara, e todo ramo de severidade tem golden | regra sem fixture, e ramo de severidade descoberto |
| `test_refresh_knowledge` | toda URL de `sources:` entra na watchlist, e o lock commitado bate com ela | **medido em `SF-KMS`/`SF-NET`/`SF-XACC`, 2026-08-23:** as três fontes oficiais novas ficaram fora de `knowledge/sources.lock.json` e só a suíte completa pegou. A watchlist é derivada de **duas** origens — a seção `## Fontes` dos documentos de `knowledge/` **e** o bloco `sources:` de cada regra do catálogo —, e o gate-map só nomeava a primeira. Alinhar sem rede: `python scripts/refresh_knowledge.py --update --offline` |
| `test_rules_engine` | `blocked_on` novo é decisão consciente registrada | o teste é alarme deliberado: a docstring diz que o próximo `blocked_on` "tem que ser uma decisao consciente de quem o escreve" |

## Dar `runtime_scope` a uma regra — ou seja, **toda regra nova**

`runtime_scope` é campo obrigatório. Uma regra que declara `{}` está declarando escopo
tanto quanto uma que declara `{glue: ">=5.0"}`, e as duas passam por aqui. Além dos acima:

```
python -m pytest tests/test_rule_scope_by_nature.py \
  tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q
```

Estes três mantêm **listas escritas à mão** de quais regras são guardadas por versão
(`GLUE_INFRA`, `GLUE_VERSIONED`, `VERSION_DEPENDENT`, `GLUE_GUARDED_RULES`,
`EXPECTED_OUT_OF_SCOPE`). Uma regra com escopo que não entre na lista certa faz o
teste falhar pedindo justificativa — e é isso que ele quer, não um bypass.

Duas dessas listas são sobre a ÁREA inteira, não sobre a regra, e por isso quebram
quando a regra nova tem natureza diferente das irmãs: `AREA_MAY_VANISH_WHEN`
(`test_rule_scope_by_nature.py`) e `AREA_FULLY_OUT_OF_SCOPE`
(`test_runtime_glue_versions.py`) declaram em que runtime uma área pode sumir por
completo. Medido em `SF-MIG-004`: acrescentar à área uma regra com
`runtime_scope: {}` faz a área deixar de sumir, e as duas exceções viram letra morta
— seis testes vermelhos de uma vez, todos pedindo que a exceção seja reexaminada e
não contornada.

O comentário no fim de `test_rule_scope_by_nature.py` explica por que o agregado é
medido: na Fase 3b, `SF-ICE-001..005` não estavam em lista nenhuma, caíram em
`_AGNOSTICAS` e cinco regras sumiram juntas de um runtime. *"O furo nao estava na
regra individual, estava no AGREGADO."*

**O mesmo agregado morde a ÁREA NOVA, e por outro caminho — medido em 2026-08-23.** As
áreas `SF-KMS`, `SF-NET` e `SF-XACC` nasceram com `runtime_scope: {glue: ">=4.0"}` em todas
as suas regras. Nenhuma lista precisou ser editada e nenhuma exceção virou letra morta: o
que quebrou foi que as **três áreas inteiras desapareciam** num runtime detectado a partir
de event log, que preenche `spark` e não `glue`. Área que some inteira lê, para um agente
autônomo, como *"nada encontrado nesse eixo"* — o falso negativo que a guarda deveria
evitar, produzido pela própria guarda.

A causa era etiqueta de serviço disfarçada de guarda de versão: não havia fronteira de
versão nenhuma, e o que gateia de verdade é `requires_facts` (sem `tf.attribute` de um
`aws_glue_job`, a regra não dispara, e `aws_glue_job` só existe onde há Glue). A correção
foi `runtime_scope: {}` nas quatro, com a razão escrita ao lado — que é literalmente o que
a mensagem de erro do teste manda fazer: *"Se o gate real e a natureza do artefato
analisado, use `runtime_scope: {}` e deixe `requires_facts` gatear."*

**A pergunta a fazer antes de escrever o escopo:** existe uma versão a partir da qual isto
passa a valer, declarada por uma fonte? Se não existe, o escopo é `{}`. `{glue: ">=X"}`
como forma de dizer "isto é sobre Glue" é o defeito — quem diz isso é `requires_facts`.

## Acrescentar uma ÁREA nova (`area:` novo num `rules/catalog/*.yaml`)

Tudo o que uma regra cobra, mais três coisas que só a área cobra:

| gate | o que ele exige | como falhou de verdade |
|---|---|---|
| `test_router_agents` | a área **roteia** — entrada própria em `rules/catalog/routing.yaml` | `findings_area` conta por prefixo exato do `rule_id` até o último hífen, então nenhuma contagem de outra área inclui a nova. Declarar a área no `rule_areas` do coordenador **não** roteia: sem entrada `AGENT-*`, os achados caem no fallback |
| `test_agent_coverage` | algum coordenador declara a área em `rule_areas` | as três áreas de 2026-08-23 exigiram um coordenador cada — e a escolha é de domínio, não de conveniência: `SF-KMS` foi para `sf-security-reviewer`, `SF-NET` para `sf-terraform-specialist`, `SF-XACC` para `sf-lake-formation-specialist` |
| `test_rule_scope_by_nature` | a área não pode sumir inteira de um runtime | ver a seção de `runtime_scope` acima: é o modo de falha específico da área nova, e não aparece em nenhuma das listas mantidas à mão |

E a decisão que vem antes dos gates: **uma área ou várias?** O eixo do contrato de migração
é derivado da área (`sparkforge/findings/models.py:area_of`), e um achado move um eixo só.
Três eixos distintos numa área só os deixaria empatados no mesmo balde — foi por isso que
`SF-KMS`, `SF-NET` e `SF-XACC` nasceram separadas em vez de uma `SF-PLAT`.

## Acrescentar ou alterar um EXTRATOR de facts

`sparkforge/facts/*.py`

```
python -m pytest tests/test_rules_catalog_reachability.py \
  tests/test_fixtures_kind_coverage.py -q
```

Convenção da casa: kind, entrada nas listas `EXTRACTORS` dos dois arquivos de teste, e
golden entram **no mesmo commit**. `EMITTED_KINDS` declara só o que o extrator emite —
kind declarado e nunca emitido torna inalcançável qualquer regra que dependa dele.

## Mexer no funil de contexto (`sparkforge/codeintel/context.py`, `ranking.py`, `budget.py`)

```
python scripts/check_recall_economy.py
python -m pytest tests/test_economy_recall.py tests/test_economy_goldset.py -q
```

O gate decide **uma** coisa e recusa outra, e a distinção é o ponto:

- **Recall nominal tem piso duro de 100%.** Perguntado pelo nome do símbolo, o pack
  entrega aquele símbolo. Se `buscar()` acha o nó e `montar()` não o entrega, o funil
  perdeu no caminho.
- **Recall conceitual é medido e não tem piso.** Perguntado pelo título da regra — como
  um operador descreve o problema —, o pack recupera? **Medido: 0 de 23.** O índice
  guarda NOME e o título descreve DEFEITO. Dar piso reprovaria capacidade que ninguém
  construiu; omitir esconderia o quanto falta.
- **A razão de economia sai `unresolved`.** O corpus do gold set tem 15 279 bytes em 23
  fixtures, e o envelope fixo do pack custa 840 bytes por chamada — 19 320 no total. Com
  o corpus menor que o envelope, qualquer razão daqui mede o piso do envelope. A §10 de
  `docs/harness/CODEINTEL-GAP.md` mediu **645× a favor** sobre 479 arquivos; as duas
  medições não se contradizem, medem corpora de ordens de grandeza diferentes.

O gold set é **derivado** das regras a cada execução (`finding.evidence[] → fact.id →
fact.subject.{file,symbol}`) e nunca versionado como arquivo. Se uma regra perder
ancoragem, o piso de 23 perguntas cai e o gate reclama; se uma regra nova ganhar fixture
ancorada, o piso sobe **no commit que o fez subir**.

## Acrescentar um CORPUS de fixture novo (`fixtures/<dominio>/`)

```
python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q
```

Diretório novo em `fixtures/` **não basta**. `test_fixtures_kind_coverage.py` cobra que
todo domínio seja reivindicado por um módulo de teste que declare
`FIXTURES = ROOT / "fixtures" / "<dominio>"`, e o módulo tem que casar o glob que
`scripts/verify_wheel.py::GOLDEN_MODULES` usa — senão o corpus existe, parece cobertura,
e o gate de wheel nunca o executa contra o pacote instalado.

Medido na fase G6: o corpus `fixtures/scenarios/` nasceu com runner
`tests/test_fixtures_scenarios.py`, fora do glob `test_fixtures_golden*.py` que as duas
pontas usavam. O conserto foi alargar o glob **nos dois lugares no mesmo commit**
(`tests/test_fixtures_kind_coverage.py::_dominios_reivindicados` e
`scripts/verify_wheel.py`), mais o teste que espelha o glob
(`tests/test_verify_wheel.py::test_discovers_every_golden_module_on_disk`). Alargar só um
deixaria a promessa do invariante — *"o gate de wheel executa este domínio"* — falsa em
silêncio.

Se o corpus novo também tem regeneração própria, ela entra em `scripts/regen_fixtures.py`
no mesmo commit: golden escrito à mão é golden que descreve o que alguém achou que o
código faz.

Corpus que mora **fora** de `fixtures/` (hoje só `evals/holdout/`) não entra nessa
contagem, e a razão é o propósito dele — ver a seção seguinte.

## Acrescentar ou alterar um cenário de `evals/holdout/`

```
python -m pytest tests/test_evals_holdout.py -q
```

`evals/holdout/` mede **generalização**: um cenário só vale como holdout enquanto nenhuma
skill, agente ou documento de `knowledge/` o cita pelo nome. Essa é a propriedade que
`tests/test_evals_holdout.py` **prova** — sem ele, "holdout" seria só um nome de pasta.
Citar um cenário de holdout num `SKILL.md` para ilustrar um exemplo é o jeito natural de
destruí-lo, e o teste é o que transforma esse acidente em vermelho.

Ele fica fora de `fixtures/` de propósito: os invariantes de `fixtures/` existem para
cobrar cobertura por kind e por regra, e holdout não é cobertura — é a amostra retida
justamente para não ser otimizada contra. Mantê-lo ali o transformaria em mais um alvo do
gate de cobertura, que é o oposto do que ele mede.

## Editar um documento em `knowledge/`

```
python -m pytest tests/test_offline_expansion.py -q
python scripts/verify_offline_bundle.py
```

`knowledge/offline-manifest.json` guarda o `sha256` de cada documento. Editar o `.md`
sem regravar o hash reprova o bundle inteiro.

Para regravar, use `sparkforge.tools.offline._content_sha256` — a docstring dela pede
isso explicitamente: *"hash calculado de um jeito e conferido de outro e o defeito que
o gate existe para pegar."* Ela remove todo `CR` em vez de traduzir `CRLF`, porque um
manifesto gravado no Windows já reprovou os 43 documentos no Linux.

Se a mudança acrescenta uma fonte à seção `## Fontes`, rode também:

```
python scripts/refresh_knowledge.py --update --offline
python -m pytest tests/test_refresh_knowledge.py -q
```

**A watchlist tem DUAS origens, e esta seção só cobre uma.** Ela é derivada da seção
`## Fontes` dos documentos de `knowledge/` **e** do bloco `sources:` de cada regra do
catálogo. Quem acrescenta URL numa regra passa por aqui também — a seção de regra, no topo
deste arquivo, agora nomeia o mesmo comando. Medido em 2026-08-23: três URLs oficiais
entraram em regras novas, nenhuma entrou no lock, e o desalinhamento só apareceu na suíte
completa. O gate existe para que o lock não envelheça em silêncio; o gate-map é que estava
incompleto.

## Alterar `knowledge/glue/runtime-matrix.yaml`

```
python -m pytest tests/test_runtime_matrix.py tests/test_runtime_detect.py \
  tests/test_runtime_glue_versions.py tests/test_runtime_inferred_from_facts.py \
  tests/test_version_path.py tests/test_migration_assessment.py -q
```

A matriz é **dado com consumidor em código**: `runtime_detect` monta `GLUE_MATRIX`
a partir dela no nível de módulo, `version_path` deriva os degraus da ordem das
versões, e todo `runtime_scope` é comparado contra o que ela resolve. Uma versão
acrescentada muda o conjunto de degraus de todo par que a atravessa.

**Vale para as quatro matrizes desde 2026-09-01.** `version_path.steps` e
`assessment.assess` recebem `platform` e leem `knowledge/emr/`, `knowledge/emr-eks/`
e `knowledge/emr-serverless/` pela mesma porta (`release_descriptor`), então uma
release nova em qualquer uma delas muda os degraus daquela plataforma — e só dela.
Rode o mesmo lote, mais `tests/test_release_descriptor.py` e
`tests/test_release_diff.py`. Rótulo fora do padrão de versão (`spark-8.0.0`,
`spark-8.0-preview`) **não** entra na ordem: ele é recusado pelo nome, e o teste
`test_rotulo_fora_do_padrao_e_recusado_pelo_nome` varre os quatro YAMLs procurando
por eles.

Componente pode ser escalar ou vir na **forma longa** (`status` + `claims`). Nesse
caso a fonte de cada claim precisa estar em `knowledge/sources.lock.json` — o
mesmo lock da lista `sources` da linha, e conferido por teste próprio. Fonte nova
entra pelo `## Fontes` do `.md` correspondente mais
`python scripts/refresh_knowledge.py --update --offline`, e o `.md` editado exige
regravar o `sha256` no `knowledge/offline-manifest.json` (seção acima).

Status `CONFLICTING` ou `UNRESOLVED` **retém** o valor do componente, e valor
retido apaga toda regra guardada por ele — por isso
`test_a_matriz_publicada_nao_tem_componente_em_disputa` existe: o primeiro
componente em disputa tem que ser decisão consciente de quem editou a matriz.

## Pontos cegos medidos do extrator de Terraform

Registrados aqui porque uma regra nova que leia `default_arguments` herda os dois sem
perceber, e o sintoma é silêncio.

- **`non_overridable_arguments` é ignorado inteiro.** `sparkforge/facts/terraform.py` não
  emite fact nenhum para esse bloco. Um `aws_glue_job` que forneça argumento por ali é
  invisível para toda regra que lê `default_arguments` — hoje `SF-LF-001`, `SF-GLUE-002` e
  `SF-GLUE-003`. Medido ao escrever `SF-LF-001`.
- **Valor com interpolação vira `tf.unresolved`, não `tf.attribute`.** Uma regra cuja
  condição é conjunção plana fica calada quando o atributo que ela procura foi
  interpolado — `_evaluate_when` não aninha `any` dentro de `all`. A saída conhecida é um
  kind de "desconhecido" no molde de `tf.observability.unknown`, que sinaliza a lacuna em
  vez de escondê-la.

## Ler dado do disco em código de `sparkforge/`

```
python scripts/verify_wheel.py
```

Lento — constrói wheel e sdist e cria um venv isolado —, mas é o único gate que prova
o **caso instalado**. Teste em árvore passa dos dois jeitos.

Na Task 1 da fase `SF-MIG` um módulo novo calculou `Path(__file__).resolve().parents[2]`
para achar `knowledge/`, o que aponta um nível acima de onde o pacote a empacota. Em
árvore funcionava; num wheel instalado, importar o módulo levantava `FileNotFoundError`.
Existe resolvedor pronto para isso desde a Fase 3a: `sparkforge/knowledge_ref.py`, com
teste do fallback para o diretório do pacote. **Procure antes de escrever.**

## Alterar dependência: `pyproject.toml`, `requirements.txt`, `locks/` ou os workflows

```
python scripts/gen_requirements.py --check
python scripts/gen_lock.py --check
python -m pytest tests/test_supply_chain.py tests/test_requirements_mirror.py \
  tests/test_ci_workflow.py -q
```

Três artefatos derivam de `pyproject.toml` e cada um tem seu `--check`, porque cada um
serve a uma ferramenta diferente: `requirements.txt` é o espelho de **pisos** que um SCA
consegue ler, e `locks/py<versão>.txt` é o fecho **resolvido** que o CI instala com
`pip install --require-hashes` — modo em que qualquer dependência não pinada no arquivo
vira erro em vez de virar versão escolhida na hora. Confundir os dois é o erro caro: auditar pisos não
responde nada -- `PyYAML>=6.0` não tem CVE, a versão instalada é que tem.

Dependência nova no `pyproject.toml` exige regenerar os **dois**, e o lock precisa de
rede e de `uv` (`pip install uv && python scripts/gen_lock.py`). `--check` é offline nos
dois casos, de propósito: gate que precisa do índice do PyPI para dizer "ok" fica
vermelho quando o índice cai, sem defeito nenhum no repositório.

Há um lock por entrada da matriz do CI, e eles **não** são cópias: `rpds-py` resolve para
versões diferentes nas duas linhas, e `tomli`, `importlib-metadata` e `zipp` só existem
na mais antiga. Acrescentar uma versão de Python à matriz sem gerar o lock dela quebra
`tests/test_supply_chain.py`, que lê a matriz do workflow em vez de uma lista à mão.

A política da auditoria de vulnerabilidade mora inteira na docstring de
`scripts/audit_policy.py`, e ela é função pura sobre JSON justamente para ter gate
offline. Os dois casos que mais importam não regredir: **base não consultada derruba**,
porque "não consegui perguntar" nunca pode ser lido como "não há nada"; e **relatório que
não cobre o lock derruba**, porque um JSON bem formado sobre outra coisa passa por todas as
outras checagens sem ter respondido nada. Mudar a versão de Python auditada no workflow
exige mudar o `--lock` junto — o teste que cobra isso lê a linha do `run`.

## Alterar agent, skill ou seus espelhos

`agents/`, `skills/`

```
python scripts/sync_skills.py --check
python -m pytest tests/test_agents_parity.py tests/test_sync_render.py \
  tests/test_agent_coverage.py tests/test_docs_coverage.py -q
```

Fonte da verdade é `agents/` e `skills/`; `.claude/`, `.agents/` e `.github/` são
espelhos gerados. Editar espelho direto é perda de trabalho na próxima sincronização.

Cuidado com YAML no frontmatter: `: ` dentro de valor escalar sem aspas quebra o parse.
Isso derrubou 81 testes numa única sessão, e nenhum dos quatro arquivos de teste que
rodei na hora tocava esse caminho.

## Alterar `rules/catalog/routing.yaml`

```
python -m pytest tests/test_router_agents.py tests/test_case_router.py \
  tests/test_case_store.py tests/test_artifact_contents.py -q
```

## Alterar a tabela *Números correntes* do `STATUS.md`

```bash
python scripts/check_status_numbers.py --strict
```

**Gate diferente do de lastro, e a fronteira é medida.** `check_vnext_claims.py`
audita `docs/vnext/` e `docs/harness/`; ele **não** audita o `STATUS.md`, que é a
fonte da verdade sobre onde o projeto está. A auditoria de 2026-09-01 mediu a
consequência: **oito** números da tabela errados, com aquele gate em `exit 0`.

Estender o gate de lastro ao `STATUS.md` foi medido antes de ser recusado:
o arquivo inteiro produz **1797** alegações (2,5× o manifesto de hoje), a seção
*Números correntes* sozinha produz **189** — porque o extrator pega todo número,
inclusive os que são explicação de defeito passado —, e a alegação de verdade são
as **24** da coluna `Valor`, uma por dimensão. Os 1214 números das seções de fase
são de época, e auditá-los contra o hoje seria errado por construção.

`scripts/check_status_numbers.py` tem o recorte que o outro não tem — seção,
tabela e coluna — e não tem manifesto: a **medição é código** e o valor publicado
está no `STATUS.md`. O par é o contrato, e não há terceiro arquivo de verdade.

Linha nova na tabela precisa de medida em `MEDIDAS` **ou** de recusa com razão em
`SEM_MEDIDA`; `--strict` reprova o que não tem nem uma nem outra. O gate falha
também no sentido inverso: medida sem linha na tabela é dimensão que sumiu do
documento com a medida esquecida.

O teste que prova que ele reprova é `tests/test_status_numbers_gate.py`.

## Alterar `scripts/check_vnext_claims.py`, `docs/claims.lock.json`, ou alegação em
## `docs/vnext/` ou `docs/harness/`

```
python scripts/check_vnext_claims.py
python -m pytest tests/test_vnext_claims.py -q
python -m pytest tests/test_docs_coverage.py tests/test_installed_provenance.py -q
```

O gate audita todo diretório declarado em `audited_roots()` (hoje `docs/vnext/` e
`docs/harness/`), não só `docs/vnext/`. `docs/claims.lock.json` é o manifesto único
para os dois -- moveu de `docs/vnext/claims.lock.json` quando `docs/harness/` entrou
sob o gate, porque um manifesto cobrindo dois diretórios morando dentro de só um deles
é a mesma mentira estrutural que o gate existe para impedir em texto, só que no próprio
caminho do arquivo.

Editar prosa em `docs/vnext/*.md` ou `docs/harness/*.md` sem rodar `--seed` primeiro
reprova o gate com "alegacao sem entrada no manifesto" ou "entrada orfa" -- rode
`python scripts/check_vnext_claims.py --seed` (NUNCA `--seed --force`, que descarta
toda classificação) para fundir a alegação nova, depois classifique manualmente
(`state: PROVADA` com `proof`, ou `REMOVIDA` com `note`). `SEM_LASTRO` não é um estado
terminal aceitável para commit.

Um **mapa de lacuna** -- documento de tabela `Componente | Classificação | Módulo(s) |
Teste`, como `docs/harness/CURRENT-HARNESS-GAP.md` e `docs/harness/GLUE6-GAP.md` -- é
descoberto por padrão de nome (`*-GAP.md`, em `gap_documents()`), não por lista escrita à
mão. Um mapa novo entra na auditoria só por se chamar assim; renomeá-lo para fora do padrão
não passa calado, porque as entradas dele viram órfãs no manifesto. Só linha cuja
classificação começa em `EXISTE` vira alegação: a linha que diz `NÃO EXISTE` descreve uma
ausência, e ausência não é capacidade a provar.

**Artefato removido da árvore também vira `historical`, e o caso é medido.** Em
2026-09-03, catorze alegações de `docs/harness/CURRENT-HARNESS-GAP.md` e
`docs/harness/GLUE6-GAP.md` liam `prompt_evo_harness.md` e
`prompt_glue_harness.md`, apagados no commit `083a038`. Reexecutar no HEAD
reprovava pelo único motivo de o arquivo não existir mais — e o gap que aquelas
linhas medem contra o prompt continua verdadeiro. Convertidas para `historical`
com `commit: 386d402` (o último que continha os arquivos), o `cmd` virando
receita: reproduza com `git checkout` daquele commit primeiro.

**Medida de corpus não honra `.gitignore`, e por isso diverge entre workstation
e CI.** `iter_source_files` percorre o que está EM DISCO. Em 2026-09-03 um
diretório ignorado com 57 arquivos `.py` (`tmp_skills/`, sobra do import das
skills AWS) fazia a mesma prova devolver **581** na workstation e **524** no CI,
sem que nada versionado tivesse mudado. Antes de remediar alegação de corpus,
confira que a árvore está limpa — `git status --ignored` mostra o que a medição
enxerga e o `git` não.

Um número que descreve um estado ATUAL (re-executável, e portanto obrigado a
continuar batendo) usa `proof.kind: "command"`. Um número que descreve uma MEDIÇÃO
PASSADA ancorada a um commit (um baseline, que por definição envelhece) usa
`proof.kind: "historical"` -- carrega `cmd` (a receita, nunca reexecutada) e `commit`
(verificado contra o git real via `git cat-file -t`). Confundir os dois é o defeito
que motivou o `proof.kind` novo: um baseline validado como `command` reprova sozinho
assim que o tempo passa, pelo único motivo de ter envelhecido -- não porque o número
parou de ser verdade no dia em que foi medido.

---

## Quando nada acima serve

Rode a suíte completa e acrescente a linha que faltava:

```
python -m pytest -q -p no:randomly
```

Entre 13 e 35 minutos. Uma chamada de ferramenta tem teto de dez minutos, então rode em
background e leia o resultado depois — não tente segurar em primeiro plano.
