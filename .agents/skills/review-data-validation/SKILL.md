---
name: review-data-validation
description: Use quando o job PySpark valida dado e a pergunta for onde a validação está, se ela tem consequência e quanto ela custa — check artesanal (`df.filter(...).count()`), `VerificationSuite` do PyDeequ ou Great Expectations por `batch_parameters`. Use também quando a pergunta for "esse job valida alguma coisa?", "por que o job termina verde com dado ruim?", "essa suíte protege alguém?" ou "por que validar dobrou o tempo do job?", mesmo que ninguém fale em regra. Se você está prestes a ler o `.py` no olho procurando `count()`, rode `sparkforge analyze data-quality` e `sparkforge judge` em vez disso — o extrator decide a posição relativa ao write, a persistência do alvo e quantos checks pesam sobre o mesmo DataFrame, e o catálogo aplica as regras SF-DQ sobre o que ele achou.
subagent: true
agent: data-quality-reviewer
---

# Review Data Validation

A pergunta desta skill não é "o dado está correto" — nenhum artefato estático responde isso.
É a pergunta anterior, e é a que ninguém faz: **a validação que existe no código chega a
proteger alguém?** Ela roda antes de publicar? O resultado dela leva a alguma consequência?
Quanto ela cobra em varreduras sobre o dado?

O extrator decide as correlações que o catálogo não conseguiria expressar — posição relativa
ao `write`, persistência do alvo, reuso depois do check, quantos checks pesam sobre o mesmo
DataFrame — e as entrega como atributos de um fact só. As regras `SF-DQ-*` leem esses
atributos.

## Procedimento

### 1. Defina o recorte, e escreva qual é

Toda afirmação desta área vale **dentro do corpus que você passou**. Um check cuja
consequência está noutro módulo fora do recorte aparece como validação desprotegida, e o
achado precisa ser lido como convite a verificar. Prefira o pacote inteiro do job ao arquivo
solto; quando não der, diga no relatório o que ficou de fora.

O artefato aqui é o `.py` do repositório — o checkout é a coleta.

### 2. Extraia os facts

```bash
sparkforge analyze data-quality --path <arquivo .py ou diretório> \
  --out .sparkforge/facts_dq.json
```

Quatro kinds saem daqui:

| Kind | O que ele afirma |
|---|---|
| `dq.check` | um ponto de validação, com as quatro correlações já decididas em `attrs` |
| `dq.enforcement` | há consequência (`attrs.form` em `raise`, `assert` ou `exit`), ancorada no subject do check |
| `dq.unresolved` | alvo ilegível, arquivo que não abriu, fonte que não compilou — contado, nunca presumido |
| `dq.module_analyzed` | `measures.check_count` e `measures.unresolved_count` por módulo |

O `dq.check` traz `attrs.framework` (`handmade`, `pydeequ`, `great_expectations`),
`attrs.check_type`, `attrs.target`, `attrs.position_vs_write`, `attrs.target_persisted`,
`attrs.action_after_check`, `attrs.shares_scan` e `measures.checks_on_target`.

`attrs.check_type` nomeia **a evidência que foi lida**, não o objeto que o autor escreveu:
`count_of_violations` é a cadeia `filter(...).count()`; `verification_suite` é a cadeia com
`onData` que termina em `run`; `batch_parameters_dataframe` é o DataFrame achado sob chave
literal em `batch_parameters` — e esse nome é deliberado, porque `Checkpoint.run` e
`ValidationDefinition.run` aceitam o mesmo argumento e o extrator não distingue os dois.
Nenhuma regra `SF-DQ` lê essa chave; ela é para você. Onde ela paga é no `dq.unresolved`,
que a carrega junto: sem ela o ponto cego diz *quantas* validações não foram lidas, com ela
diz **qual tipo** — e "não li uma `VerificationSuite`" pede uma investigação diferente de
"não li um `count()` artesanal".

**Duas ausências de chave são deliberadas, e as duas significam "não sei", nunca "não".**
Quando o nome do alvo é religado entre o check e o `write`, `position_vs_write` é **omitido**
em vez de receber um quarto valor. E `shares_scan` **não acompanha** o check de Great
Expectations, porque quantas expectativas a suíte roda vive no store do contexto, fora do
`.py`. Em ambos os casos a regra correspondente simplesmente passa adiante: o motor reprova
caminho ausente.

### 3. Leia a sentinela antes de concluir qualquer coisa

`dq.module_analyzed` é o que distingue **"o extrator rodou e não achou validação"** de **"o
extrator nunca rodou aqui"**. Um módulo com `check_count: 0` é um job que não valida; a
ausência do próprio `dq.module_analyzed` é análise que não aconteceu.

`measures.unresolved_count` junto de `dq.unresolved` diz quanto do arquivo ficou ilegível.
`reason: unresolved_target` é o caso comum — o alvo do check chega por parâmetro ou vem de
uma cadeia cuja raiz é a sessão —, e ele é ponto cego do extrator, não defeito do código.

### 4. Traga o código quando a recomendação tocar custo

`SF-DQ-003` e `SF-DQ-004` falam de recomputo e de varredura. Quando for recomendar
persistência ou agregação única, junte a leitura estrutural do mesmo arquivo:

```bash
sparkforge analyze pyspark --path <mesmo caminho> --out .sparkforge/facts_py.json
sparkforge analyze call-graph --path <mesmo caminho> --out .sparkforge/facts_cg.json
```

`--facts` é repetível: passe os arquivos na mesma chamada de `judge`, que une e deduplica as
listas antes de julgar. As áreas são disjuntas — `SF-PY` fala do custo da chamada, `SF-DQ`
fala do papel dela na validação —, e um achado das duas sobre a mesma linha é informação
dobrada, não repetida.

### 5. Julgue

```bash
sparkforge judge --facts .sparkforge/facts_dq.json --show-skipped

# com a leitura de código junto, para sustentar custo:
sparkforge judge \
  --facts .sparkforge/facts_dq.json \
  --facts .sparkforge/facts_py.json \
  --show-skipped
```

**Como o runtime chega aqui, e o que fazer quando ele não chega.** Um `.py` não carrega
versão nenhuma: não há `glue_version` num arquivo Python, e a versão de Spark vem de event
log, de Terraform ou de declaração explícita. Rodando só com os facts de validação, o campo
`runtime` da saída volta com `detected_from` vazio e `divergences` vazio — e isso é o
esperado, não um defeito.

O que isso muda, e o que não muda:

- **As quatro regras `SF-DQ` continuam sendo avaliadas.** O gatilho delas é a posição e a
  estrutura de chamadas num AST, que não varia com versão; por isso o escopo de runtime
  delas é vazio, e elas não dependem de nenhuma flag.
- **As regras versionadas das outras áreas saem em `skipped`**, com `reason: runtime_scope`,
  visível graças ao `--show-skipped`. Sem essa flag, "nenhum achado" e "não consegui avaliar"
  ficam indistinguíveis na saída.

Quando você precisa do runtime — e nesta área você precisa dele para **recomendar
biblioteca**, nunca para disparar regra —, há duas saídas reais:

1. **Dê a fonte ao motor.** `sparkforge analyze terraform` sobre o `.tf` que define o job, ou
   `sparkforge analyze event-log` sobre o event log do run, e passe o resultado em mais um
   `--facts`. Confirme em `runtime.detected_from`, que dirá `terraform` ou `event_log`.
2. **Declare a versão que você conhece de fonte confiável**, como `--glue 5.1` ou
   `--emr 7.5.0`. Declaração perde para observação: quando a versão declarada discorda da
   observada, nada é substituído em silêncio — `runtime.divergences` lista as duas, e a
   discordância é achado próprio (`SF-ENV-001`).

### 6. Interprete os quatro atributos, e não só o achado

- **`position_vs_write`** tem três valores, e só `after_write` dispara. `no_write_in_module`
  é um módulo que valida e não escreve, o que é legítimo; `before_write` é o caso correto.
- **`target_persisted` e `action_after_check` só acusam juntos.** Alvo não persistido sem
  reuso depois não recomputa coisa alguma, e reuso sobre alvo persistido é justamente o que
  se quer. `SF-DQ-003` exige os dois.
- **`shares_scan` separa quem já compartilha varredura**, e a afirmação precisa ser lida com
  precisão: o runner do Deequ agrupa agregações que exigem o mesmo agrupamento, e métricas
  como `isUnique` pagam passada própria. O contraste é N contra ≤ N, nunca N contra um.
- **`measures.checks_on_target`** conta checks sobre o mesmo alvo no mesmo escopo. Dois ou
  mais varrem o mesmo dado duas ou mais vezes para responder ao que uma agregação
  responderia junto — e `cache` não resolve isso, porque ler duas vezes do cache continua
  sendo ler duas vezes.

## Antes de recomendar biblioteca, confira o alcance

O que a versão governa nesta área é a **recomendação**. O alcance está medido, com URL e
data, em `knowledge/dq/validation-frameworks.md`:

- PyDeequ **não instala** em Glue 3.0 nem em nenhuma release EMR 6.x — a série 6.x cai pelo
  Python, e o Spark 3.4 (EMR 6.12.0 a 6.15.0) está fora do mapa de versões do pacote.
- Great Expectations 1.x exige Python 3.10 ou maior, o que exclui os mesmos runtimes sem
  trocar o interpretador.
- `SparkDFDataset` foi removido do Great Expectations na 1.0. Ele identifica código 0.x, e
  recomendá-lo é recomendar uma API morta.

A primeira `proposed_change` de `SF-DQ-004` é deliberadamente a que não depende de biblioteca
nenhuma — uma agregação única, com uma expressão por regra. Ela vale em qualquer release.

## Referência rápida

Regras desta área e o fact que cada uma consome. Limiares e severidades **não** estão aqui de
propósito, e a lista autoritativa é `sparkforge rules lookup --category data-quality` — o
catálogo cresce, esta tabela é uma foto.

| Regra | O que consome | O que acusa |
|---|---|---|
| `SF-DQ-001` | `dq.check` com `attrs.position_vs_write: after_write` | A validação roda depois da escrita: quando ela acusa, o dado ruim já está publicado |
| `SF-DQ-002` | `dq.check` com `dq.enforcement` ausente no mesmo subject, sentinelado por `dq.module_analyzed` | Validação sem consequência — o job termina verde com dado inválido, e a suíte cria a crença de que há garantia |
| `SF-DQ-003` | `dq.check` com `attrs.target_persisted: false` **e** `attrs.action_after_check: true` | A action do check materializa o DataFrame e a próxima action recomeça o lineage: o custo é proporcional ao lineage, não ao check |
| `SF-DQ-004` | `dq.check` com `attrs.shares_scan: false` e `measures.checks_on_target >= 2` | Vários checks independentes sobre o mesmo alvo varrem o mesmo dado várias vezes |

## Quando NÃO usar

- A pergunta é sobre **o dado**, e não sobre a validação — quantas linhas violam, qual valor
  está errado, qual coluna deveria ter `not null`. Isso é a ferramenta de DQ rodando sobre o
  dado; esta análise lê apenas o `.py`.
- O gargalo é o código ou o plano físico, e a validação é irrelevante para a pergunta:
  comece por `sparkforge-diagnose`, e siga com `optimize-pyspark-code` ou
  `analyze-spark-plan`.
- O risco está na definição do job ou do cluster: `review-glue-terraform` para Glue,
  `review-emr-cluster` para EMR on EC2.
- A validação é declarativa e vive fora do `.py` — `great_expectations.yml`, suites em JSON,
  testes de dbt. O recorte desta área é o código Python do job, e essa cobertura está
  registrada como dívida aberta.
- A pergunta é sobre tabela Iceberg, small files ou layout: `optimize-iceberg-table` e
  `optimize-parquet-layout`.

## Red flags

- Ler `SF-DQ-002` como "este job não protege nada" quando o recorte foi um arquivo só. O
  achado diz **sem consequência neste corpus**; consequência atrás de um helper
  (`aborta_se(ruins)`) ou noutro módulo não é vista, porque isso exigiria seguir o valor para
  dentro da função.
- Tratar `dq.unresolved` como job sem validação. É alvo ilegível, e `unresolved_count` diz
  quanto ficou de fora — acusar ali é acusar quem escreveu o código de um defeito que ele não
  tem.
- Concluir que a validação está adequada porque nada disparou. As quatro regras falam de
  posição, consequência e custo; um job pode passar limpo nas quatro validando a coluna
  errada.
- Recomendar PyDeequ ou Great Expectations sem saber a release em que o job roda. É o
  conselho que destrói a confiança no resto do relatório, e o alcance está medido em
  `knowledge/dq/validation-frameworks.md`.
- Prometer que uma `VerificationSuite` com N checks é uma passada só. O compartilhamento é
  por agrupamento, e `isUnique` e entropia pagam passada própria.
- Contar chamadas `addCheck` como número de restrições: a forma oficial encadeia várias
  restrições dentro de um `addCheck` só.
- Responder a `SF-DQ-003` com `cache()` reflexo, sem olhar o tamanho do DataFrame. Persistir
  troca CPU e I/O de recomputo por memória de executor, e o remédio de um gargalo vira spill
  ou OOM.
- Tratar `assert` como consequência definitiva. Ele conta — nenhuma fonte oficial mostra Glue
  ou EMR rodando o driver com `-O` —, mas sob `PYTHONOPTIMIZE` o interpretador não gera
  código nenhum para ele. Proteção que precisa sobreviver a isso usa `raise`.
- Recomendar mover a validação para antes do `write` sem dizer o que acontece com o destino
  quando ela reprovar. Abortar antes deixa o destino com o ciclo anterior; abortar depois
  deixa o destino com dado reprovado. As duas exigem decisão de operação.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva você **não executa** — recomende, e a confirmação de escopo e
retenção **sobe a quem pode ser perguntado**: o agente pai que despachou, ou o
operador na sessão.

Esta skill é **despachável** (`subagent: true` no espelho `.agents/skills/`), e
`ask_user_question` é **sempre negado** a um subagente. Dentro do despacho, obter a
confirmação aqui não é difícil: é impossível — por isso a regra 9 de
`AGENT_PROTOCOL.md` manda não executar e devolver a decisão a quem pode ser
perguntado.
