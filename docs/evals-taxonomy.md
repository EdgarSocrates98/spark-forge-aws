# Evals taxonomy — classificação §7.1 dos evals do SparkForge AWS

Fonte única: `sparkforge_aws/evals/taxonomy.py`. O que está aqui é a leitura
humana da mesma tabela que o manifesto `forge/context/v1` persiste em
`eval_suites[].kind` + `capabilities.evals.detail`, e que
`sparkforge-aws evals list|describe` serve. Spec: `prompt_evo_install2.0.md` §7
(lf-0038). Não reimplementa runner nenhum — classifica, expõe e protege o que
já existe.

## As quatro categorias (§7.1)

| categoria (`kind`) | o que mede |
|---|---|
| `developer` | testes internos de skills, agents, roteamento, economia e implementação |
| `runtime-decision` | decisões operacionais (rotear, abstender, re-tentar, arbitrar) |
| `output-verification` | validação do resultado da tarefa contra gabarito |
| `host-conformance` | integração host↔forge: o agente no host usa tools/protocolo certo |

O enum é fechado — `EVAL_KINDS` de `sparkforge_aws/_forgecontext.py` (vendored,
dono: the-forge). Suite nova entra pela tabela de `taxonomy.py`, nunca por
edição do manifesto gerado.

## Inventário classificado

| suite (`evals describe --suite`) | categoria | ambiente | selada | runner |
|---|---|---|---|---|
| `fase0` | output-verification | deterministic | sim | `python scripts/check_evals.py` |
| `agentic-fase0` | host-conformance | host | sim | host + `python -m sparkforge_aws.evals grade` |
| `agentic-debate` | runtime-decision | host | sim | `scripts/run_debate.py` + `evals debate` |
| `agentic-recovery` | runtime-decision | host | sim | harness de recovery do host |
| `agentic-sdd` | host-conformance | host | sim | `scripts/run_agentic_eval.py` |
| `holdout` | output-verification | deterministic | sim | nativo: extract + assess |
| `mcp-conformance` | host-conformance | deterministic | não | `pytest tests/test_mcp_conformance_matrix.py` |
| `platform-intelligence` | runtime-decision | deterministic | sim | `scripts/check_platform_eval_contract.py` |
| `skill-evals` | developer | deterministic | não | `scripts/check_skill_evals.py --strict` |
| `token-efficient` | developer | deterministic | sim | `scripts/check_token_efficient_bench.py` |
| `decision-plane` | runtime-decision | deterministic | sim | `sparkforge-aws decision benchmark` |
| `forge-lab-golden20` | output-verification | simulated | não | `sparkforge-aws lab verify` |

Contagem: developer=2, runtime-decision=4, output-verification=3,
host-conformance=3.

## Ops conceituais §7.2 → verbos reais

`discovery.ops` do manifesto é o vocabulário **fechado** do §6.2 (oito ops —
estendê-lo exigiria mudar `_forgecontext.py`, que pertence ao the-forge). Os
seis ops do §7.2 vivem em `discovery.commands` do manifesto, e em
`capabilities.evals.ops` do verbo `capabilities` — a fonte é
`discovery_ops.EVAL_OPS`, a mesma para os dois lugares.

| op conceitual | comando real | read_only |
|---|---|---|
| `evals.list` | `sparkforge-aws evals list` | sim |
| `evals.describe` | `sparkforge-aws evals describe --suite <id>` | sim |
| `evals.run` | `sparkforge-aws evals run --suite <id>` | sim |
| `evals.result` | `sparkforge-aws evals result --suite <id> --run <run>` | não (grava scorecard) |
| `verification.plan` | `sparkforge-aws funcval plan --facts <f> --out <plan>` | não (grava o plano) |
| `verification.run` | `sparkforge-aws funcval compare --plan <p> --before <b> --after <a>` | sim |

## Segurança (§7.3)

- **Gabarito selado**: suites `sealed: true` nunca emitem resposta —
  `evals describe` devolve categoria, local, `expected_answers: sealed` e
  `integrity.suite_sha256`. `tests/test_evals_surface.py` tenta extrair
  fatias de `expected/` por `describe`/`list`/manifesto e exige ausência.
  O caso estrito (`evals/holdout/`) tem a prova mais antiga:
  `tests/test_evals_holdout.py` proíbe até o *nome* do cenário em
  `skills/`, `agents/`, `knowledge/` e nos espelhos `.claude`/`.agents`.
- **Executor ≠ avaliador**: suites `environment: host` medem um agente de
  host; `evals run` nelas é recusa nomeada `EVALS-REQUIRES-HOST`, não uma
  execução sintética.
- **Baselines protegidos**: `integrity.suite_sha256` (sha256 sobre todos os
  arquivos da suite) em todo `describe`; `check_evals.py` recomputa as
  respostas de `fase0`; os scorecards de `evals/agentic/*/baselines/` são
  conferidos contra o sha256 da suite resolvida — alteração manual vira
  diff de hash, nunca edição silenciosa.
- **Simulado ≠ real**: todo resultado de `evals run` carrega `environment`
  (`deterministic`/`simulated`/`host`) e `real_environment_proof` — `false`
  exceto quando um host real executou.
- **Sem nuvem**: nenhum runner toca AWS; os gates `script:`/`pytest:` são
  recusados `EVALS-RUNNER-UNAVAILABLE` fora do checkout (scripts/ e tests/
  não entram no wheel).

## Fluxo de verificação (§7.4)

Para uma mudança relevante o caminho invocável é:

1. `analyze pyspark --out facts.json` (+ `analyze catalog-schema --out`) —
   extrai os facts do "antes";
2. `funcval plan --facts ... --key <declarada> --out plano.json` — deriva o
   plano de validação (contagem, schema, chaves, agregados);
3. execute a mudança e meça "depois" nos mesmos checks;
4. `funcval compare --plan plano.json --before b.json --after a.json` —
   veredito por check, com ausentes e falhas explícitos (`unavailable_reason`,
   nunca zero);
5. o funcval vira `funcval.*` facts para `judge`/gates — evidência
   registrada, conclusão proporcional.

`lab verify` cobre a outra metade: os contratos do ambiente simulado
(registry + Golden 20 + schemas) com `valid` explícito.

## Agentes (§7.5)

Os 14 coordinators e 5 executors de `agents/` declaram **Siga
`AGENT_PROTOCOL.md`** — referência canônica, protocolo não duplicado.
`scripts/sync_skills.py --check` prova os espelhos `.claude/`, `.agents/` e
`.github/` byte-frescos contra `skills/`+`agents/`.
