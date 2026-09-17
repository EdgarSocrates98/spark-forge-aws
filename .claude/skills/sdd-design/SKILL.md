---
name: sdd-design
description: Use quando o define.md da feature está ready e é hora de decidir como construir — "desenha a solução", "quais arquivos mudam?", "fase design" — no SparkForge ou num job do operador. Grava docs/sdd/<FEATURE>/design.md com o manifesto de arquivos conferido no código, decisões com alternativas rejeitadas e rollback, e a cobertura de cada critério do define, e fecha com sparkforge sdd stamp e sparkforge sdd check.
---

# SDD Design

Fase 2 do SDD próprio. Diz **quais arquivos** mudam, **por quê**, e **como
desfazer**. O `sparkforge sdd check` confere que todo caminho alterado existe,
que toda decisão tem rollback e que todo critério do define tem uma parte que o
cobre. Se o desenho é sensato continua sendo julgamento — do operador e da
revisão.

## Antes de começar

1. `sparkforge sdd check --repo . --feature <F>` com o define em `ready`. Design
   sobre define em `draft` sai `phase_out_of_order`.
2. Leia o define inteiro: hipótese, critérios, `out_of_scope`, `unknowns` e
   `change_kinds`. Lacuna com `blocks` sobre um critério é resolvida aqui ou vira
   decisão explícita.
3. Copie `docs/sdd/templates/design.md` para `docs/sdd/<FEATURE>/design.md`, com
   `status: draft` e `upstream.path` apontando para o define da feature.

## O manifesto (`files`)

Cada item tem `path`, `action` (`create`, `modify`, `delete`) e `reason`.

- **`create`** é caminho novo. O check não o procura.
- **`modify` e `delete`** exigem o caminho existente hoje. Confira antes de
  escrever: `sparkforge code search <nome>` para achar,
  `sparkforge code symbol <node_id>` para ver quem chama e o que quebra,
  `sparkforge code path <origem> <destino>` para saber como um chega no outro.
  Caminho inventado sai `manifest_path_unknown`. Depois do build pronto, o
  `delete` de um arquivo que sumiu é o desenho cumprido e deixa de ser recusado.
- **Os registros entram no manifesto agora.** Para cada chave de `change_kinds`,
  abra a seção dela em `docs/gates-por-mudanca.md` e liste os arquivos que ela
  move: skill nova mexe na tabela de despacho de `scripts/sync_skills.py`, no
  `manifest.json` e nos testes de espelho; tool nova move `docs/surface.lock.json`
  e a referência gerada. Registro descoberto só no build é desvio que o ship vai
  ter de listar.
- Um arquivo por responsabilidade. Arquivo que já é grande e vai crescer merece
  uma linha no `reason` dizendo por que fica assim.

## As decisões (`decisions`)

Cada decisão tem `id` `D<n>`, `choice`, `rejected` e `rollback`.

- **`rejected`**: ao menos uma alternativa real, com o motivo — as rejeitadas do
  explore entram aqui.
- **`rollback`**: como desfazer, em comando (`git revert` do commit, o script que
  regenera, o `rollback.patch` do pacote de mudança). Sem ele,
  `rollback_missing`.
- **Conhecimento citado, nunca lembrado.** Decisão sobre Glue, Spark, Iceberg ou
  Lake Formation cita `sparkforge rules lookup --id <SF-...>` ou
  `sparkforge knowledge path --file <documento>`, com a versão alvo. Documentação
  oficial e changelog sustentam uma decisão; texto de modelo sozinho não.
- **Valor de configuração não é decisão de design.** Ele sai de `sparkforge tune`
  sobre a medida; o design decide *onde* o valor mora e *quem* o pede.

## A cobertura (`covers`)

Cada item liga uma `part` do desenho aos `acceptance` do define que ela
entrega. Todo `AC` aparece em pelo menos um `covers`; o que faltar sai
`acceptance_uncovered`, nomeando o critério.

## O laço

1. Rascunhe manifesto, decisões e cobertura com `status: draft`.
2. Apresente ao operador por partes, do tamanho da complexidade de cada uma, e
   pergunte se está certo antes de seguir.
3. `sparkforge sdd stamp --repo . docs/sdd/<F>/design.md`.
4. `sparkforge sdd check --repo . --feature <F>`; corrija o campo de cada recusa.
5. `status: ready` com zero recusa. Próximo passo: `sdd-plan`.

## Cascata

Se o define mudar depois, `sparkforge sdd status --repo .` mostra o design em
`upstream_stale`. Leia o que mudou no define, **revise** o design e só então
carimbe de novo. Carimbar sem revisar é o erro que a cascata existe para pegar.

## Perfil operator

- O manifesto lista os arquivos do job que a mudança toca (`.tf`, `.py`). A
  procedência de cada configuração vem dos facts `tf.spark_conf` e
  `pyspark.conf_set`, com arquivo e linha.
- Esses arquivos mudam **só** por diff gerado em `sparkforge change plan` e
  aplicado numa cópia por `sparkforge change sandbox`. A sessão nunca escreve na
  árvore do operador.
- O `rollback` da decisão é o `rollback.patch` que `sparkforge change propose`
  grava no pacote, ou `git revert` depois do merge.

## Quando NÃO usar

- Define ainda em `draft`, ou critério sem `verified_by`: volte a `sdd-define`.
- Para quebrar o trabalho em tarefas com teste e código: `sdd-plan`.
- Para aplicar a mudança: `sdd-build`.
- Para escolher o valor de configuração: `sparkforge tune`.

## Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| achar o arquivo | `sparkforge code search <nome>` | `sparkforge_code_search` |
| quem chama, o que quebra | `sparkforge code symbol <node_id>` | `sparkforge_code_symbol` |
| como X chega em Y | `sparkforge code path <origem> <destino>` | `sparkforge_code_path` |
| regra citada | `sparkforge rules lookup --id <SF-...>` | `sparkforge_rules_lookup` |
| documento citado | `sparkforge knowledge path --file <arquivo>` | `sparkforge_knowledge_path` |
| carimbar | `sparkforge sdd stamp --repo . docs/sdd/<F>/design.md` | `sparkforge_sdd_stamp` |
| conferir | `sparkforge sdd check --repo . --feature <F>` | `sparkforge_sdd_check` |
| diff do job (operator) | `sparkforge change plan --facts <f> --set k=v --out d.patch` | `sparkforge_change_plan` |

Recusas desta fase: `phase_out_of_order`, `manifest_path_unknown`,
`rollback_missing`, `acceptance_uncovered`, `upstream_stale`.
Template: `docs/sdd/templates/design.md`.

## Red flags

- `modify` num caminho que ninguém abriu nem procurou.
- Decisão sem alternativa rejeitada, ou com `rollback` "reverter se precisar".
- Limiar, default ou comportamento de Spark citado de memória, sem versão.
- Registro manual (tabela de despacho, manifest, surface lock) fora do
  manifesto de uma mudança que o exige.
- Critério do define sem parte que o cubra.
- Design carimbado de novo sem ler o que mudou no define.
- Arquivo do operador no manifesto com caminho de escrita direta, sem
  `change plan`.
