# Convergência semântica — a passada antes dos gates

Referência da skill `sdd-ship`. O `sdd check` confere a **estrutura** da
cadeia SDD (schemas, stamps, upstream). A convergência confere o
**sentido**: o que o define prometeu é o que a árvore entrega. É uma
passada somente de leitura — diagnóstico classificado no corpo do
`ship.md`; a correção volta à fase dona.

## A cadeia conferida

```
requisito (REQ/NFR) ↔ design (D<n>, manifesto) ↔ plano (T<n>, covers)
   ↔ tarefa executada (build_report) ↔ código (diff) ↔ teste (recibo)
   ↔ evidência (evidence_ref, medida) ↔ desfecho (hypothesis_outcome)
```

Para cada elo, a pergunta é "os dois lados dizem a mesma coisa?". Não é
"o elo existe?" — o gate já responde isso.

## As seis classes de divergência

| classe | o que é | exemplo | fase dona |
|---|---|---|---|
| `missing` | o elo não existe | AC sem tarefa, requisito sem design | define/plan |
| `partial` | o elo cobre parte | teste prova 2 dos 4 cenários do AC | plan/build |
| `contradicts` | os lados se contradizem | define pede retry, código faz fail-fast | define ou design |
| `unrequested` | entregue sem ser pedido | código, registro ou config que nenhum requisito cita | build (deviation) ou operador |
| `unverified` | o elo existe, a prova não rodou | `verified_by` declarado nunca executado | build |
| `stale` | a prova é de outra árvore | recibo de sha anterior, `report_sha256` divergente | build |

## As seis checagens

1. **Verificação de fonte** — cada claim do relatório aponta para
   `evidence_ref` que existe, confere e diz o que a claim diz. Claim sem
   ref é `unverified`; ref que mudou é `stale`.
2. **Cobertura de aceitação** — todo AC tem o `verified_by` **executado**
   nesta entrega (exit no build_report), não só declarado. Executado em
   parte é `partial`.
3. **Regressão** — a suíte e os gates rodam **agora** (a skill já manda
   rodar antes de oferecer integração); "rodaram quando o build fechou" é
   `stale` se a árvore andou.
4. **Drift** — requisito↔design, design↔plano, plano↔build: cada um pode
   divergir sem o outro. `deviations` do relatório é a lista oficial;
   drift não listado é divergência de registro.
5. **Frescor** — sha do recibo, `report_sha256`, versão citada: contra a
   árvore e a versão de hoje.
6. **Confirmação de decisões** — toda decisão que o design deixou aberta
   tem resposta do operador ou `reopen_condition` registrada. Confirmada
   por omissão é `unverified`.

## Regras duras

- **Read-only**: a passada escreve só o diagnóstico no `ship.md`.
- **Volta à fase dona**: missing de requisito é define; de teste, plan;
  stale de recibo, build. O ship não conserta a montante.
- **Nunca reescreve**: requisito, hipótese e design não são editados para
  fechar a cadeia. Mudança neles exige aprovação do operador e derruba as
  fases de baixo para `upstream_stale` — caminho mais longo que consertar
  a jusante.
- **`unrequested` não é elogio**: código que nenhum requisito pediu sai
  classificado mesmo funcionando — ele é superfície sem dono na próxima
  manutenção.
- **Rollback verificável**: a entrega fecha com o rollback que
  realmente reverte o diff (não só o do design). Rollback que não se
  consegue executar ou nomear é divergência de ship, não nota de rodapé.
