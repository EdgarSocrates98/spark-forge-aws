<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_playbook`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Decomposicao de um coordenador (agents/*.md) em passos sequenciais -- o PISO de orquestracao das cinco plataformas. Tres despacham subagente (Claude Code, Devin CLI e o Devin Local agent do Devin Desktop, sob o toggle Subagents (Preview)); esta tool e o unico caminho em Codex e Copilot CI, onde nenhuma pesquisa mediu despacho, e continua sendo o caminho nas tres quando o despacho esta desligado -- por escolha do usuario (subagents_enabled) ou do admin da organizacao (Default subagent model: None). No Devin ela e o caminho tambem com o despacho LIGADO: um coordenador despachado como subagente nao gera subagente proprio por default, e este repositorio nao declara max-nesting em perfil nenhum. Le os arquivos de agents/ e agents/executors/ em vez de repetir a lista: uma copia divergiria do coordenador na primeira mudanca. `does_not` de cada passo vem da secao `## Não faz` do executor, nunca reescrito aqui. Case ausente nao e erro -- os passos saem com `phase: null`. Traz tambem o `next_step` do case (mesmo calculo de sparkforge_next_step), incluindo `recommended_agent` -- ver secao 4.5 da spec de Fase 4.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `coordinator` | string | sim | Nome do arquivo em agents/ (sem .md), ex.: glue-infra-reviewer. |
| `findings` | array de object | não | Findings atuais, usados para resolver o `next_step` embutido (so `rule_id` importa). |
| `repo` | string | não | Raiz do repositorio analisado. |

## Na CLI

[`sparkforge playbook`](../cli/playbook.md)

## Capacidade

coordenar investigacao por agente especializado

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
