# Camada agêntica: executores determinísticos, e o que ela ainda não é

O resumo está no [README](../../README.md). Aqui fica o detalhe das entidades, dos
dois executores e do que a camada **não** afirma. O passo a passo com saída real está
em [Arbitragem e debate](usos/arbitragem-e-debate.md).

## As entidades

`sparkforge/agentic/` (14 módulos fora o `__init__.py`, contados em 2026-09-18) traz
entidades de primeira classe e engines para trabalho agêntico auditável: `Claim`,
`Evidence` (com tiers de autoridade T1-T6), `Hypothesis`, `Experiment`, `Decision`,
`Unknown`, `Contradiction`, `Objection`, `Rebuttal`; mais blackboard JSONL, protocolo
de debate, arbitragem com detecção de falso consenso, ADR automático, memória
institucional, budget e níveis de autonomia L0-L5.

## O executor determinístico

`sparkforge/agentic/executor/` (11 módulos fora o `__init__.py`, contados em
2026-09-18) é o **produtor** dessas entidades, e ele é determinístico.
`sparkforge arbitrate` roda depois de `judge` e escreve no blackboard do case — num
case rodado, `blackboard summary` deixa de devolver zero.

## O executor de debate (2026-09-11)

Quando a arbitragem não fecha, o `arbitrate` emite um `DebatePlan` e para, com
`debate.unresolved`. Desde 2026-09-11 esse plano tem executor:
`sparkforge debate start|next|submit` (tools `sparkforge_debate_start|next|submit`).
É uma máquina de estados L0 que diz de quem é a vez, recusa por nome a submissão fora
do protocolo e só aceita evidência nova **reextraída** por extrator da allowlist. O
fechamento é sempre do `referee`. O argumento é escrito pelo host, pela skill
`run-debate` ou por `scripts/run_debate.py` (`claude -p`), nunca dentro do pacote. O
placar da suíte `evals/agentic/debate/` sai de
`python -m sparkforge.evals debate --run <nome>`.

## O que ela NÃO é, e isso governa o resto

Nenhum `AgentRuntime` concreto mora no pacote, e nada aqui chama provider — quem gasta
token é o host que executa os agents. Os executores são **L0**: `applied_changes` sai
sempre `false`, e o ADR é proposta com `rollback` obrigatório, nunca registro de coisa
feita.

Por isso **não há afirmação de ganho** publicada em lugar nenhum. Os dois lados
rodam, mas o debate alcança um único par de regras (`SF-GRAPH-005` × `SF-LF-001`, de
157 com `action`). Esse par só existe na união dos facts de dois jobs, e o baseline de
modelo foi deliberadamente não rodado. Detalhe em [`evals/README.md`](../../evals/README.md).

## Os comandos

```bash
sparkforge arbitrate --findings f.json --facts a.json --facts b.json --repo .
sparkforge debate start --rules A,B --findings f.json --facts a.json --facts b.json --repo .
sparkforge debate next --debate <id> --repo .                 # brief da vez, ou done
sparkforge debate submit --debate <id> --file s.json --repo . # submissao do lado
sparkforge blackboard summary --repo .        # contagem do blackboard do case
sparkforge decisions list --repo .            # decisões do case e da memória
sparkforge decisions explain <id> --repo .    # rollback e falsification_condition
sparkforge budget show --repo .               # budget DECLARADO no case.yaml
sparkforge budget show --template             # defaults do código, rotulados
sparkforge autonomy show --level L3           # perfil de autonomia
```

`--facts` é **repetível, e a repetição é o contrato**: o executor recebe a UNIÃO dos
facts do case, o mesmo conjunto que `judge` recebeu para produzir aqueles findings.
Alimentá-lo com um subconjunto fabrica claim desancorada que a execução real não
produz. A tool MCP equivalente é `sparkforge_arbitrate`, e ela é `LOCAL_MUTATION`,
como as três `sparkforge_debate_start|next|submit`.

Status por componente, defeitos corrigidos na auditoria de 2026-09-03 e o que falta:
[`docs/agentic-evolution-report.md`](../agentic-evolution-report.md).

## Próximos passos

- [Arbitragem e debate](usos/arbitragem-e-debate.md): o fluxo rodado, com saída real.
- [Economia de contexto](usos/economia-de-contexto.md): o que medir antes de afirmar que economizou.
- [Agents e skills](05-agents-e-skills.md): coordenadores, executores e o `playbook`.
