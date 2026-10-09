# Holdout — cenários retidos

Dois cenários de migração, no mesmo formato de `fixtures/scenarios/`
(`meta.yaml` + `input/` + `expected/assessment.json`), com uma regra a mais:

> **Nenhum arquivo de `skills/`, `agents/` ou `knowledge/` cita o nome de um
> diretório deste corpus.**

`tests/test_evals_holdout.py` **prova** essa regra a cada execução da suíte. Sem
esse teste, "holdout" seria só um nome de pasta — e o jeito natural de destruir
um holdout é exatamente o inocente: citar o cenário num `SKILL.md` para
ilustrar um exemplo, e a partir daí o agente que resolve o caso pode estar
lembrando em vez de generalizando.

## Por que a distinção importa aqui

O resto do corpus deste repositório é determinístico: extrator estático e motor
de regras sobre YAML versionado, sem LLM em lugar nenhum da extração ou do
julgamento. Para aquele nível, um golden citado numa skill não corrompe nada —
o código não lê skills.

O nível de agente é outro. Um agente é instruído por `skills/`, `agents/` e
`knowledge/`, e um exemplo resolvido dentro dessas instruções é resposta
disponível, não capacidade demonstrada. Um cenário citado ali mede memorização
com a mesma cara com que mediria generalização, e a diferença não aparece em
nenhum número.

## O que cada cenário retém

| cenário | par | o que ele exercita que os visíveis não exercitam |
|---|---|---|
| `lote_misto_iceberg_parquet` | 4.0 → 5.1 | job em **pacote**, com cada sinal num módulo diferente; lê Parquet e grava Iceberg; caminho que **não alcança** o Glue 6.0, então `mig.ansi_risk` presente e SF-MIG-003 calada em todos os degraus |
| `config_por_caminho_indireto` | 5.1 → 6.0 | configuração declarada num mapa e aplicada por laço em outro módulo — nenhuma chave aparece numa chamada literal; único cenário do repositório cujo desfecho é `PASS_WITH_RISK` / `CONDITIONAL_GO`, e único que dispara `SF-SPARK4-001` |

Os dois usam apenas regras que já existem no catálogo. Um holdout que exigisse
regra nova mediria a regra, não o sistema.

## Como mexer sem estragar

- **Regenerar o golden**: `python scripts/regen_fixtures.py <nome>` — o mesmo
  `regen_scenario` de `fixtures/scenarios/`. Golden escrito à mão descreve o que
  alguém achou que o código faz.
- **Renomear um cenário**: o teste passa a cobrar o nome novo automaticamente
  (ele lê o disco, não uma lista escrita à mão).
- **Citar um cenário numa skill**: não faça. Se o exemplo for necessário para
  ensinar alguma coisa, escreva um cenário novo em `fixtures/scenarios/` e cite
  aquele — é o corpus que existe justamente para ser visível.
- **Acrescentar um cenário**: escolha uma forma que os visíveis não tenham. Um
  holdout que repete a forma de um cenário exposto mede o mesmo que ele, e
  gasta a única propriedade que o torna um holdout.

Ver também `docs/gates-por-mudanca.md`, seção *Acrescentar ou alterar um cenário
de `evals/holdout/`*.
