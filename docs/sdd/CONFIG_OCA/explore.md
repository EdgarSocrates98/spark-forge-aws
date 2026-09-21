---
sdd: 1
feature: CONFIG_OCA
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Apagar o que nao existe e travar a volta, no molde do SF_STUBS mais o CRITERIO_DE_DOMINIO: as sete tools inexistentes saem de config/agentic-expansion.yaml, os documentos que prometem 'seis ferramentas locais deterministicas' passam a dizer o que ha, e um gate novo confere que todo nome declarado num registro de config/ aponta para algo que existe. O bloco de subagents recebe decisao explicita no define, com a medida ao lado."
    tradeoffs:
      - "e o precedente da casa, e o proprio criterio de dominio ja diz que coisa entra por artefato, nunca por nome"
      - "o gate impede a reincidencia, que e o que faltou ao SF_STUBS: ele limpou os agentes sf-* e esta camada ficou"
      - "custo: decidir o destino dos 16 subagents exige medir para que servem, e a medida pode dizer que eles sao host-side e legitimos"
  - id: B
    summary: "Implementar as sete tools que o registro declara."
    tradeoffs:
      - "entrega capacidade nova em vez de remover promessa"
      - "sete tools e uma frente inteira, nao uma limpeza, e nenhuma delas tem artefato coletavel definido nem demanda medida"
      - "contraria o criterio de dominio: construir porque o nome esta escrito e exatamente a ordem invertida"
  - id: C
    summary: "Marcar as sete como planejadas (um campo status: planned no registro) em vez de apagar."
    tradeoffs:
      - "preserva a intencao de quem escreveu"
      - "mantem no registro nome que nao resolve, e registro e lido por maquina: o campo novo precisa de leitor, senao e a mesma oca com um rotulo"
      - "sem demanda medida, 'planejado' e indistinguivel de abandonado"
chosen: A
---

# CONFIG_OCA — exploração

## Origem

A feature `SF_STUBS` (#88) apagou 19 agentes `sf-*` ocos e 35 áreas `agentic-sf-*`, e a
`CRITERIO_DE_DOMINIO` (#89) criou o gate que trava domínio novo sem artefato. As duas
deixaram **uma camada de fora**, e o `docs/sdd/CRITERIO_DE_DOMINIO/ship.md` a nomeou como
pendência herdada: os registros declarativos de `config/`.

Pedido do operador em 2026-09-20.

## Perfil

`dev`. A mudança é no próprio SparkForge.

## O que foi medido nesta árvore (2026-09-20, `main` em `e4141869`)

`config/agentic-expansion.yaml` tem quatro blocos de nomes. **Dois estão íntegros e dois
não:**

| bloco | declarado | existe |
|---|---|---|
| `agents` | 2 | **2** |
| `knowledge` | 8 | **8** |
| `subagents` | 16 | 16 contratos em `subagents/*.md` |
| `tools` | 7 | **0** |

As sete que não existem: `sparkforge_offline_knowledge_verify`,
`sparkforge_offline_knowledge_search`, `sparkforge_context_pack`,
`sparkforge_schema_compare`, `sparkforge_lineage_extract`, `sparkforge_eval_golden_case` e
`sparkforge_cost_estimate`. Nenhuma está em `sparkforge.adapters.tools.TOOLS`.

**O registro é apontado por outro registro:** `config/agents.yaml` traz
`expansion_registry: config/agentic-expansion.yaml`. E `docs/agentic-expansion.md` promete,
em prosa, *"seis ferramentas locais deterministicas"* — um número que não bate nem com as
sete declaradas nem com as zero existentes.

**Os 16 subagents são o único registro declarado sem nenhum leitor.** Medido por varredura
de `sparkforge/`, `scripts/` e `tests/`:

- `skills/` é lida por `sparkforge/registry/loader.py`, `sparkforge/economy/report.py`,
  `scripts/sync_skills.py` e outros;
- `agents/` é lida por `sparkforge/adapters/cli.py`, `tools.py`, `case/playbook.py`,
  `codeintel/` e outros;
- `config/subagents.yaml` e `subagents/*.md`: **zero** referências em Python.

Os 16 contratos existem como arquivo. O que não existe é quem os despache.

## Perguntas feitas

1. Qual abordagem? Resposta (2026-09-20): A.

## Abordagens

A é a recomendada porque é o precedente da casa e porque o critério de domínio, que esta
mesma série criou, já diz que coisa entra por artefato e não por nome. B constrói sete
tools porque os nomes estão escritos — a ordem invertida do critério. C mantém o nome no
registro com um rótulo, e rótulo sem leitor é a mesma oca.

**O que A deixa em aberto de propósito:** o destino dos 16 subagents. A medida diz que
ninguém os despacha; ela **não** diz se eles são contrato host-side legítimo (como a skill
`run-debate`, que o host executa) ou resíduo. Essa é a pergunta que o define precisa
responder com medida, não com preferência.

## Escolha

A, escolhida pelo operador.
