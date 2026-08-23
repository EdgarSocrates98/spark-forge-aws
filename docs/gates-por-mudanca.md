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
  tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py -q
```

O que cada um cobra, medido na fase `SF-MIG`:

| gate | o que ele exige | como falhou de verdade |
|---|---|---|
| `test_agent_coverage` | toda área de regra tem coordenador que a declara | a área `SF-MIG` nasceu sem nenhum agente com ela em `rule_areas` |
| `test_router_agents` | a área **roteia** para um coordenador | declarar a área no agente não roteia; `rules/catalog/routing.yaml` precisa de entrada própria. Mesma lacuna já órfãou `SF-BENCH`, `SF-EMRS`, `SF-ENV`, `SF-FVAL` e `SF-UI` |
| `test_docs_coverage` | `manifest.json` declara a contagem real | `rule_count` ficou em 116 depois de três regras novas. A docstring do teste registra que esse número já apodreceu três vezes, duas delas no `README.md` |
| `test_fixtures_kind_coverage` | toda regra tem golden que a dispara, e todo ramo de severidade tem golden | regra sem fixture, e ramo de severidade descoberto |
| `test_rules_engine` | `blocked_on` novo é decisão consciente registrada | o teste é alarme deliberado: a docstring diz que o próximo `blocked_on` "tem que ser uma decisao consciente de quem o escreve" |

## Dar `runtime_scope` a uma regra

Além dos acima:

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

## Acrescentar ou alterar um EXTRATOR de facts

`sparkforge/facts/*.py`

```
python -m pytest tests/test_rules_catalog_reachability.py \
  tests/test_fixtures_kind_coverage.py -q
```

Convenção da casa: kind, entrada nas listas `EXTRACTORS` dos dois arquivos de teste, e
golden entram **no mesmo commit**. `EMITTED_KINDS` declara só o que o extrator emite —
kind declarado e nunca emitido torna inalcançável qualquer regra que dependa dele.

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
