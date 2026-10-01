# Como contribuir

Obrigado pelo interesse. Este guia diz como montar o ambiente, o que rodar antes de
abrir um PR e as poucas regras que o projeto não negocia. As regras de domínio (Glue,
Spark, Iceberg) e os invariantes da arquitetura estão no `CLAUDE.md`; leia-o antes da
primeira mudança.

## Ambiente

Python 3.10, 3.11 ou 3.12. As dependências são travadas com hash:

```bash
python -m pip install --require-hashes -r locks/py3.11.txt
python -m pip install -e . --no-deps --no-build-isolation
```

Use `locks/py3.10.txt` no Python 3.10 e `locks/py3.12.txt` no 3.12. O projeto mira 3.10: API que só existe no 3.11+
(`datetime.UTC`, `tomllib`, `typing.Self`, `StrEnum`) passa na máquina local e cai no job
`test (3.10)` do CI.

## Antes de abrir o PR

### Lint

```bash
python -m ruff check sparkforge scripts tests
```

### Testes

A suíte inteira não cabe num processo só. Rode em lotes, **um por vez**; a receita é
executável e mora em `tests/test_suite_batches.py`, na constante `LOTES`. Não edite a
árvore com um lote rodando.

Arquivo novo de teste ou de código precisa estar no índice do git (`git add`) antes dos
lotes: `tests/test_arvore_versionada.py` reprova `.py` fora do git.

### Gates

Qual gate cada tipo de mudança toca está em `docs/gates-por-mudanca.md`. Os que o CI roda:

```bash
python scripts/sync_skills.py --check
python scripts/gen_requirements.py --check
python scripts/gen_lock.py --check
python scripts/check_evals.py
python scripts/check_vnext_claims.py
python scripts/check_status_numbers.py --strict
python scripts/check_recall_economy.py
python scripts/check_surface_lock.py
```

- **Número publicado** em `docs/vnext/` ou `docs/harness/` passa pelo gate de lastro
  (`check_vnext_claims.py`). Remedie pela lista de ids que a saída do gate imprime, nunca
  por varredura.
- **Tool, skill ou documento de `knowledge/` novo** move a superfície. Rode
  `python scripts/check_surface_lock.py --update` e declare no commit de quanto ela
  cresceu.
- **Verbo, tool, agente ou skill novo** exige regerar a referência:
  `python scripts/gen_reference_docs.py`.

## Regras que não se negociam

- **Caso real nunca entra em arquivo.** Fixture, exemplo e reporte usam dado sintético.
  O repositório é público.
- **Fato é medida, julgamento é regra.** Capacidade com artefato entra pelo motor de
  regras; valor proposto mora em `tune`, fora do catálogo (regra 11 do `CLAUDE.md`).
- **Recusa tem nome.** O que não tem base sai em `refused` ou `*.unresolved`, com a medida
  que a destravaria (regra 20).
- **O pacote não chama provider de modelo** (regra 23). Quem executa agente é o host.
- **Medição nunca derruba a chamada** (regra 27). Instrumentação que quebra o produto é
  defeito.
- **Não afirme ganho sem medida** (regras 28 e 30).

## Fluxo de trabalho

- Um branch por mudança, a partir da `main`. Um PR por frente.
- Commits no formato Conventional Commits (`feat`, `fix`, `docs`, `chore`, `test`,
  `refactor`), com o porquê no corpo quando ele não for óbvio.
- Mudança grande passa pelo SDD do próprio repositório: as skills `sdd-explore`,
  `sdd-define`, `sdd-design`, `sdd-plan`, `sdd-build` e `sdd-ship`, com os artefatos em
  `docs/sdd/<FEATURE>/` e cada fase conferida por
  `sparkforge sdd check --repo . --feature <F>`. O fluxo está em `docs/sdd/README.md`.
  `docs/superpowers/specs/` e `plans/` estão congelados, e o histórico do AgentSpec
  está em `docs/sdd/archive/agentspec/`.
- Agente se edita na fonte `agents/<nome>.md`, nunca no espelho `.claude/agents/`:
  `scripts/sync_skills.py` regrava os espelhos a partir da fonte.

## Segurança

Vulnerabilidade não vai por issue pública. Veja `SECURITY.md`.

## Licença

Ao contribuir, você concorda que sua contribuição é licenciada sob a licença MIT do
projeto (`LICENSE`).
