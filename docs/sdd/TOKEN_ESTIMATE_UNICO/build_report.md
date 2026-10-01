---
sdd: 1
feature: TOKEN_ESTIMATE_UNICO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/TOKEN_ESTIMATE_UNICO/plan.md
  sha256: "37a11a59682fbcb5a3b9980b9ab5ee5087acb818052f49edc7ec0a0d953459ec"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_token_estimate_unico.py::test_uma_definicao_e_os_sitios_a_usam tests/test_token_estimate_unico.py::test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso tests/test_token_estimate_unico.py::test_mock_nunca_afirma_zero_token -q", exit: 1}
    green: {command: "python -m pytest tests/test_token_estimate_unico.py::test_uma_definicao_e_os_sitios_a_usam tests/test_token_estimate_unico.py::test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso tests/test_token_estimate_unico.py::test_mock_nunca_afirma_zero_token -q", exit: 0}
claims:
  - text: "tools/cost e o pacote sparkforge.tools apontam para a mesma funcao de agents/budget, conferido por identidade."
    evidence_ref: "tests/test_token_estimate_unico.py::test_uma_definicao_e_os_sitios_a_usam"
  - text: "Com o teto, o funnel escolhe sempre um prefixo do que escolhia com o piso: 0 falhas em 59.040 casos exaustivos da revisao."
    evidence_ref: "tests/test_token_estimate_unico.py::test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso"
  - text: "O mock nunca afirma zero token."
    evidence_ref: "tests/test_token_estimate_unico.py::test_mock_nunca_afirma_zero_token"
  - text: "A API publica nao levanta para valor que o JSON nao serializa: cai para str(valor), como antes."
    evidence_ref: "tests/test_token_estimate_unico.py::test_valor_que_nao_serializa_em_json_nao_levanta"
---

# TOKEN_ESTIMATE_UNICO — relatorio do build

| commit | entregou |
|---|---|
| `2b1ca5a7` | T1: dono unico, alias em cost, funnel e mock chamando, alegacao VNX-603 |
| `0839755c` | correcao da revisao: a API publica deixou de levantar; duas docstrings velhas |

## SC2 — o custo da mudanca, medido

Nenhum teste existente mudou de expectativa, e nenhum quebrou. Mudou o **valor
calculado**, que nenhum teste conferia:

| onde | antes | depois |
|---|---|---|
| `tests/test_context_funnel.py`, `total_tokens_estimate` | 11 | 13 |
| `MockModelProvider()`, `output_tokens` da resposta padrao | 8 | 9 |

**E a selecao do funnel muda de fato.** A revisao varreu 59.040 casos pequenos (1 a 4
chunks de 0 a 9 caracteres, orcamento de 0 a 7): a selecao mudou em **20.553**. Um chunk
unico que cabia justo com o piso agora sai -- `'abcde'` com orcamento 1 devolve contexto
vazio. E o custo que a abordagem A aceitou: o teto encaixa no maximo o mesmo, nunca mais,
e a propriedade de prefixo valeu nos 59.040.

## Revisao final

Nenhum critico. **Importante:** o alias fazia a API publica `sparkforge.tools.estimate_tokens`
levantar `TypeError` para set, bytes, Path, objeto e dict de chaves mistas, onde antes
devolvia numero. Nenhum chamador de hoje era afetado. Corrigido no dono, com vermelho
visto (exit 1) antes do codigo.

## Desvios

1. O dono passou a contar JSON (antes `cost` contava `str()`) para valor que serializa;
   dict com chave int conta mais (`{1:'a'}`: 2 para 3). Os dois chamadores reais passam
   texto; o numero deles nao muda.
2. `plan.md` entrou de novo no commit da T1 (ajuste de `noqa S311` no teste).
3. Plano e build foram numa rodada so, por pressao de contexto da sessao.
4. **Scan Snyk nao concluiu.** O servidor MCP nao conectou, e o CLI, autenticado, trava ate
   em 6 arquivos. Revisao manual da superficie: sem eval, subprocesso, I/O ou
   desserializacao.
