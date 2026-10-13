# Receita — utilizar agents (coordenadores e executores)

**O quê:** 14 coordenadores (um por ângulo de investigação) + 5 executores
(`sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier`,
`sf-synthesizer`) — a equipe agentic que o `--profile full` instala.
**Por que:** o coordenador decide qual executor roda e quando; escolher
agente por julgamento é proibido pelo AGENT_PROTOCOL — o `next-step` diz
qual, a partir do estado do case e dos findings.
**Quando:** investigação de ponta a ponta com um host que despacha
subagentes (Claude Code, Devin) — ou via `playbook` em qualquer host.
**Quando não:** resposta de um verbo só — chamar coordenador para o que
`analyze`/`judge` resolve direto é orquestração sem necessidade.

## Problema

"Quero a equipe agentic investigando este job — quem coordena, quem
executa, como despacho?"

## Pré-requisitos

`sparkforge-aws install --profile full` (agents só aterrissam no `full`).
No Codex, o caminho é `playbook` — não há despacho de subagente.

## Passo a passo

```text
# 1) abra o case e deixe o roteador escolher
"Abra uma investigação sobre o job jobs/etl.py e me diga o próximo passo."

# 2) o host roda next-step → recommended_agent, ex.:
#    pyspark-code-reviewer (achados SF-PY dominantes)

# 3) despache o perfil
"Use the pyspark-code-reviewer profile as a subagent on this job."
```

Sem despacho de subagente (ou fora dele), o piso em todas as plataformas:

```bash
sparkforge-aws playbook pyspark-code-reviewer --repo .
```

## Saída esperada / interpretação

O coordenador lê o case, decide o próximo executor e registra quem rodou
(`case update --skill`); cada executor tem `## Não faz` e contrato
`## Pressupõe`/`## Entrega`. O `playbook` devolve a mesma decomposição
como sequência de passos.

## Verificação

```bash
sparkforge-aws playbook <coordenador> --repo .   # passos ordenados
sparkforge-aws next-step --repo .                # agente recomendado
```

## Limitações

- Coordenador despachado como subagente não despacha executores —
  decomposição roda inline.
- Codex: 14 `.toml` (executores não viram TOML — sem `description`); o
  `playbook` é o caminho, não um fallback.
- Escolher agente "porque parece" é o que o roteador existe para evitar:
  `next-step` lê fase + área dominante dos findings.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| agents não instalados | perfil `recommended` | `install --profile full` |
| `recommended_agent: null` | nenhuma rota casou | registre em `open_questions` — é estado honesto, não bug |

## Uso por agentes

Os coordenadores são perfis despacháveis (`agents/*.md` canônico, espelhos
`.claude/`/`.agents/`); executores vivem em `agents/executors/` e são
referenciados pelo coordenador, nunca despachados direto.

## Leitura seguinte

- [usar-skills](usar-skills.md)
- `AGENTS.md` §Coordinators and executors — a tabela completa
- `AGENT_PROTOCOL.md` — as regras que eles seguem
