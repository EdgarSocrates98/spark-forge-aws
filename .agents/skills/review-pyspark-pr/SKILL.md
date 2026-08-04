---
name: review-pyspark-pr
description: Use quando revisar um Pull Request PySpark/AWS Glue e precisar classificar risco de regressão de performance, custo e escala antes de aprovar — novas actions, shuffles, joins com cardinalidade, UDFs, collect, loops de DataFrame, mudança de write mode, particionamento ou operações Iceberg/Parquet introduzidas pelo diff. Use também quando pedirem "dá uma olhada nesse PR", "isso é seguro de mergear", "o que mudou de performance aqui" ou "aprova esse diff", mesmo sem falar em code review formal. Se você está prestes a ler o diff e apontar problema de cabeça, rode `sparkforge analyze pyspark` nos arquivos alterados e compare contra a versão base em vez de confiar em leitura visual — e valide sua própria recomendação com `sparkforge validate` antes de postar, porque um ganho quantificado sem `benchmark_ref` é rejeitado pelo schema.
subagent: true
---

# Review PySpark PR

Revisão de diff por leitura visual erra de dois jeitos: comenta em padrão que já existia antes do PR (fora de escopo, ruído para o autor), ou promete um ganho ("isso deve reduzir 40%") que ninguém mediu. O extrator resolve o primeiro comparando facts da versão nova contra a base. O `validate` resolve o segundo: o schema de finding rejeita `expected_effect` quantificado sem `benchmark_ref`.

## Escopo

Analise impactos introduzidos ou alterados pelo PR. Considere contexto suficiente para entender a execução, mas não repita como "achado do PR" um padrão que já estava lá antes.

## Procedimento

### 1. Extraia os facts da versão nova (HEAD)

Para cada arquivo `.py` alterado pelo PR:

```bash
sparkforge analyze pyspark --path <arquivo_alterado.py> --out .sparkforge/facts_head_<n>.json
```

`--path` recebe um arquivo ou diretório por chamada — não uma lista de caminhos. Se as mudanças estão concentradas num diretório, aponte para ele; senão, uma chamada por arquivo alterado.

### 2. Extraia os facts da versão base

```bash
git show <base-ref>:<caminho_do_arquivo> > .sparkforge/base/<arquivo>.py
sparkforge analyze pyspark --path .sparkforge/base/<arquivo>.py --out .sparkforge/facts_base_<n>.json
```

### 3. Julgue as duas versões

```bash
sparkforge judge --facts .sparkforge/facts_head_<n>.json --show-skipped
sparkforge judge --facts .sparkforge/facts_base_<n>.json --show-skipped
```

As duas chamadas precisam do **mesmo** contexto de runtime, ou a comparação HEAD-contra-base compara duas coisas diferentes e você reporta como regressão do PR uma regra que só passou a ser avaliada. Omitir a flag nas duas é a forma mais segura de garantir isso: os facts vêm de `analyze pyspark`, que não observa runtime, então as duas saídas trazem o mesmo `runtime` vazio com `detected_from: []`, e nenhuma regra `SF-PY-*` guarda versão. Se você passar a versão, passe idêntica nas duas — e confira o campo `runtime` de cada saída antes de comparar, em vez de confiar que digitou igual.

O que `--show-skipped` listar com `reason: runtime_scope` é infraestrutura Glue, que um diff de `.py` não alimenta. Se o PR mexe no `.tf` junto, isso deixa de ser ruído: extraia o Terraform das duas versões também e junte na mesma chamada (`--facts` é repetível), e o runtime passa a sair do próprio diff — inclusive uma mudança de `glue_version` no PR, que aparece como `runtime.divergences` se as duas leituras forem julgadas juntas.

Compare os dois conjuntos de findings por `rule_id` + `subject`:

- **Novo no HEAD, ausente na base** → regressão introduzida pelo PR. É o achado principal da revisão.
- **Presente na base, ausente no HEAD** → o PR corrigiu algo; vale mencionar como ponto positivo.
- **Presente nos dois** → pré-existente, fora do escopo do diff — cite apenas se for `P0`/`P1`, não repita como se fosse do PR.

### 4. Escreva os comentários

Um finding por comentário, citando `rule_id` e o `fact_id` da evidência (nunca um número solto). Cada comentário precisa de: problema, evidência no diff, impacto, correção concreta, como testar.

### 5. Valide antes de postar

```bash
sparkforge validate --findings .sparkforge/review_findings.json
```

Isso pega exatamente o erro mais comum de review sob pressão: afirmar "isso deve reduzir o runtime em ~30%" para soar convincente, sem ter medido nada. O schema rejeita qualquer `expected_effect` com número (`%`, `x`, "vezes") que não venha acompanhado de `benchmark_ref`. Se `validate` falhar, ou você mede antes (`benchmark-pyspark-job`) ou reformula a frase como hipótese, sem número.

## Verificações fora do alcance do extrator

O extrator de AST não substitui julgamento sobre: estratégia de merge/delete Iceberg (snapshots, commits — precisa de `analyze iceberg` ou plano), mudança de particionamento físico, testes de correção ausentes, e logging que dispara job (`count()`/`show()` em `logger` aparece como `pyspark.action`, mas decidir se é aceitável é seu).

## Quando NÃO usar

- Não é um diff/PR e sim refatoração exploratória: use `optimize-pyspark-code`.
- A mudança é de infraestrutura/IaC do job (workers, timeout, argumentos): use `review-glue-terraform`.
- Precisa comprovar o impacto com números reais antes de reivindicar ganho: encadeie `benchmark-pyspark-job`.
- O PR mexe numa biblioteca com múltiplos módulos e o entrypoint não conta a história: passe por `analyze-library-call-graph` antes.

## Referência rápida

| Severidade | Critério |
|---|---|
| P0 | corrupção, perda de dados, explosão de custo ou indisponibilidade provável |
| P1 | regressão crítica comprovável pelos facts |
| P2 | problema relevante de escala/performance |
| P3 | melhoria incremental |
| P4 | sugestão experimental |

A severidade default de cada regra vem do catálogo (`sparkforge rules lookup --id <rule_id>`); ajuste apenas com justificativa registrada no comentário, nunca em silêncio.

## Red flags

- Aprovar mudança de write mode ou operação Iceberg (merge/delete) sem plano de teste de correção (contagem, schema, chaves).
- Comentário genérico ("otimize isso") sem correção concreta e sem como validar.
- Repetir como "achado do PR" um finding que já existia na versão base — sempre compare HEAD contra base antes de comentar.
- Postar `expected_effect` quantificado sem rodar `sparkforge validate` primeiro.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
