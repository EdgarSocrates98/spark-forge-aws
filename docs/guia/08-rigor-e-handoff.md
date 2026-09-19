# Rigor, assinatura e handoff

O resumo está no [README](../../README.md). Aqui fica o detalhe de três coisas que
acompanham uma investigação até o fim: gates que trancam a fase, relatório que
carrega prova de correspondência, e o handoff entre sessões e ferramentas. O case
em si está em [Investigação com case](usos/investigacao-com-case.md); o CI, em
[CI e GitHub](usos/ci-e-github.md).

## Rigor: gates que trancam e relatório que carrega prova

Duas garantias que o motor não tinha, e as duas são **opcionais por construção**.

### Gates fail-closed

O `case.yaml` tem quatro gates. Abrir o case com
`--strict-gates` grava a escolha de rigor **no case** — não na invocação —, e a
partir daí `set_phase` recusa a transição enquanto faltar a evidência dos gates
que guardam a fase pedida:

```bash
sparkforge case open --repo . --case-id perf-2026-08 \
  --now 2026-08-04T09:00:00Z --strict-gates

# `report` é guardada pelos TRÊS gates com produtor, então a transição precisa
# das três evidências: o benchmark destrava `baseline_captured`, o call graph
# destrava `flows_mapped` e o plano de validação destrava
# `functional_validation_defined`. Faltando uma, bloqueia — com a mensagem
# nomeando qual fact falta e o comando que o produz.
sparkforge analyze call-graph --facts .sparkforge/facts.json \
                              --out .sparkforge/facts_callgraph.json
sparkforge funcval plan --facts .sparkforge/facts.json \
                        --facts .sparkforge/facts-catalog.json \
                        --out .sparkforge/facts_funcval_plan.json
sparkforge case update --repo . --phase report \
  --facts .sparkforge/bench.json \
  --facts .sparkforge/facts_callgraph.json \
  --facts .sparkforge/facts_funcval_plan.json
```

O que destrava é **evidência**, nunca a flag: `case update --gate X --gate-value
true` continua gravando o booleano e não libera nada. Quem produz a chave de cada
gate é dado, no bloco `gates` de `rules/catalog/routing.yaml`, com o comando exato
em `produced_by`. Só gate **com** produtor endurece — hoje `baseline_captured`
(`bench.run_delta`, da Fase 4a), `flows_mapped`
(`callgraph.reachable_spark_work`) e `functional_validation_defined`
(`funcval.plan`, da Fase 4c). `dominant_bottleneck_identified` continua advisory,
porque endurecer gate sem produtor é o impasse que a Fase 0 recusou
conscientemente: gate rígido vira beco sem saída quando o dado simplesmente não
existe — e dominância é ordenação entre candidatos, que nenhum fact do
vocabulário afirma.

Quando o dado genuinamente não existe — job descontinuado, ambiente que sumiu —,
passar por cima custa uma frase, e a frase fica gravada no case e aparece no
`resume`:

```bash
sparkforge case update --repo . --override-gate baseline_captured \
  --reason "job descontinuado; nao ha ambiente para rodar o depois" \
  --now 2026-08-04T11:30:00Z
```

Abrir um case por cima de outro é **recusado**: sobrescrever apagaria a fase, o
rigor e os overrides gravados, e uma invocação sem `--strict-gates` desligaria em
silêncio o rigor que alguém ligou. Recomeçar do zero continua possível, com nome:
`sparkforge case open --reopen`. Ele herda o `strict_gates` do case atual — o
rigor sobe com `--strict-gates` e nunca desce por omissão de flag.

O gate confere a **presença do kind**, não o conteúdo do fact: ele prova que a
análise rodou e produziu o artefato que destrava, e **não** que ela cobriu todo o
`scope.entrypoints` nem que o benchmark é do job certo. O limite é decisão
registrada, e vai escrito na própria mensagem de bloqueio.

### Assinatura de correspondência

`report sign` escreve um bloco no fim do
relatório; `report verify` confere e diz **qual** das quatro partes divergiu —
versão da assinatura, evidência, catálogo ou corpo — em vez de devolver só
"inválido". Os dois existem na CLI e como tool MCP (`sparkforge_report_sign`,
`sparkforge_report_verify`):

```bash
sparkforge report sign   --report relatorio.md --findings .sparkforge/findings.json
sparkforge report verify --report relatorio.md --findings .sparkforge/findings.json
```

O arquivo é o de **findings**, e não o de facts: `rule_id`, `catalog_version` e
`schema_version` só existem lá. O hash cobre os `fact_id` citados, os `rule_id`
que dispararam, as duas versões e o **corpo** do relatório — sem o corpo, alguém
reescreveria o texto inteiro mantendo a assinatura válida. Editar a prosa depois
de assinar invalida, e é para isso que serve: reassinar é barato.

O bloco declara também o `signature_version` sob o qual foi assinado. Ele já
entrava dentro do hash — é o que garante que duas regras de normalização nunca
produzam a mesma assinatura —, mas sem a declaração o `verify` não tinha como
dizer **por que** não fechou: um relatório assinado sob a regra anterior saía
igual a um corpo adulterado. Com ela, versão diferente vira `version_mismatch`,
e o corpo sai como **não avaliável** em vez de acusado.

Ela prova **correspondência**, nunca **autoria**: não há chave nem segredo, e
qualquer pessoa com os mesmos findings produz exatamente a mesma assinatura.
Assinatura de autoria (HMAC, GPG) foi recusada no desenho — exigiria distribuir e
guardar um segredo, superfície que o projeto hoje não tem —, e o limite vai
escrito dentro do bloco que o relatório carrega, porque bloco que sugira
autoridade mente por omissão.

## No GitHub: Code Scanning e resumo de PR

`sparkforge report github` projeta os findings de `judge` em SARIF 2.1.0 para o
Code Scanning (aba Security e diff do PR), num resumo Markdown para o
`$GITHUB_STEP_SUMMARY` e em anotações `::error` no diff. Só entra no SARIF o
finding com linha num arquivo do repositório; o de execução (event log, job run)
sai no resumo com o motivo, e nenhum some. `--fail-on P0` deixa o check
vermelho. Não chama rede: quem sobe o SARIF é a action `upload-sarif`. Guia e
workflow de exemplo em [`docs/github-code-scanning.md`](../github-code-scanning.md)
e [`examples/github/sparkforge.yml`](../../examples/github/sparkforge.yml).

## Fluxo de handoff

`sparkforge handoff --repo <raiz>` escreve `.sparkforge/handoff.md` a partir
do mesmo payload que `sparkforge resume` produz — os dois nunca divergem
porque vêm da mesma função. Ao encerrar ou pausar uma investigação, commite:

```bash
git add .sparkforge/case.yaml .sparkforge/facts.json .sparkforge/findings.json .sparkforge/handoff.md .sparkforge/artifacts/manifest.json
```

Esses cinco arquivos são pequenos, derivados, e são o barramento de handoff
entre sessões e ferramentas (Devin, Claude Code, CI).

**`.sparkforge/artifacts/**` nunca é commitado**, exceto o `manifest.json`
acima — o `.gitignore` já bloqueia isso. É onde ficam os artefatos brutos
coletados (event logs, planos físicos, saída de Terraform): podem carregar
dados de negócio e chegar a centenas de MB. O que substitui o artefato bruto
no commit é o manifesto: ele registra `sha256`, `source` (origem) e
`collect_command` (comando exato de recoleta) para cada artefato, de modo
que uma sessão que retome em outra ferramenta saiba exatamente o que falta e
como coletar de novo.

## Próximos passos

- [Investigação com case](usos/investigacao-com-case.md): o case, as hipóteses e a retomada.
- [CI e GitHub](usos/ci-e-github.md): o SparkForge no pull request.
- [Mudanças com prova](usos/mudancas-com-prova.md): o `benchmark` que destrava `baseline_captured`.
