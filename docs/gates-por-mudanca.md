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

---

## Quando nada acima serve

Rode a suíte completa e acrescente a linha que faltava:

```
python -m pytest -q -p no:randomly
```

Entre 13 e 35 minutos. Uma chamada de ferramenta tem teto de dez minutos, então rode em
background e leia o resultado depois — não tente segurar em primeiro plano.
