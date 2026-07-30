---
name: sf-resume
description: Rehidrata o estado de um case ao retomar a investigação em outra sessão ou ferramenta.
---

Você está retomando uma investigação SparkForge que talvez tenha sido iniciada
em outra sessão, ou por outra ferramenta (Devin, outra instância do Claude
Code). O estado sobrevive em `.sparkforge/case.yaml`, não na conversa.

Rode:

```
sparkforge resume --repo <raiz-do-repo> [--findings <arquivo-de-findings.json>] [--unresolved <n>] [--in-flight "<descrição>"]
```

Se você sabe que algo ficou pela metade quando a sessão anterior parou (um
comando rodando, uma edição incompleta), descreva em `--in-flight`.

## Como ler o payload

- `top_findings` são os achados mais severos já conhecidos — comece por eles,
  não pelo início do investigação.
- `open_hypotheses` são hipóteses ainda não confirmadas nem descartadas: não
  assuma que uma investigação "zerada" significa que nada foi tentado.
- `gates` e `unsatisfied_gates` mostram o que falta para avançar de fase
  (`baseline_captured`, `dominant_bottleneck_identified`, etc.).
- **`coverage.unresolved` é o campo mais fácil de ler errado.** Um número maior
  que zero significa que existem arquivos ou trechos que o extrator não
  conseguiu analisar (`pyspark.unresolved`) — isso é um **ponto cego**, não
  ausência de problema. Não reporte "nenhum achado nessa área" sem antes checar
  se `unresolved` é zero ali. Investigue o que está por trás desse número antes
  de concluir qualquer coisa sobre a área que ele cobre.
- `next_step` já traz a mesma rota que `/sf-next` devolveria — não precisa
  rodar os dois se só quer retomar.

Depois de ler o payload, confirme com o usuário onde a investigação parou antes
de continuar.
