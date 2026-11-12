# Requisitos — camada de exigência do define

Referência da skill `sdd-define`. O frontmatter do `define.md` prova
critérios; esta camada, gravada **no corpo** do artefato, declara a
exigência que cada critério serve. O gate confere o schema; quem confere a
camada é a revisão da fase e o operador. Quando o schema formalizar campos
de requisito, esta tabela migra para o frontmatter sem mudar de semântica.

## As seis coleções

| coleção | forma | regra |
|---|---|---|
| `stories` | "Como <papel>, quero <capacidade>, para <resultado>" | uma por desejo real; papel é quem pede, resultado é o porquê |
| `requirements` | `{id, statement, source, critical?, status}` | `id` = `REQ-<n>` (funcional) ou `NFR-<n>` (não funcional); estável e nunca reciclado |
| `scenarios` | dado/quando/então por `AC` | um cenário por critério; repetição do `statement` não é cenário |
| `constitution` | lista de restrições | o que a feature herda e não renegocia |
| `change_policy` | texto | como requisito muda depois do `ready` |
| `decision_refs` | `REQ-<n> -> [DEC-<n>, ...]` | a decisão do explore que cada requisito fecha |

## Regras duras

1. **Id estável.** `REQ-3` cortado fica `status: withdrawn` com o motivo —
   nunca reciclado, nunca renumerado. A trilha (`REQ -> AC -> D -> T ->
   evidência -> desfecho`) só se audita por id estável.
2. **`source` sempre.** Quem pediu (o operador, o case, a auditoria), a
   medida ou a decisão `DEC-<n>` que o origina. Requisito sem `source` é
   opinião de quem escreveu o artefato.
3. **`critical: true`** quando o requisito toca correção de dado, segurança,
   autorização ou contrato publicado. Crítico não sai do escopo por
   conveniência: sai por aprovação explícita registrada no corpo.
4. **Cenário prova observável.** "Dado um event log com skew em uma
   partição, quando roda a extração, então a regra SF-UI-001 dispara" —
   observável, repetível, ligado a um `verified_by`. "Dado que o job é
   lento, quando melhora, então fica rápido" é o mesmo critério não
   testável com roupagem nova.
5. **Constituição não negocia.** A árvore do operador não se escreve fora do
   `change sandbox`; ganho de desempenho só com medida; spec fora de
   `docs/sdd/` ou `.sparkforge_aws/sdd/` não é spec. Requisito que fere a
   constituição sobe ao operador — nunca é "reinterpretado".
6. **`change_policy` depois do `ready`:** feature nova para desejo novo, ou
   reabertura declarada — o motivo registrado e a cascata revisada
   (`upstream_stale` mostra quem ficou velho). Edição silenciosa de
   requisito em `ready` é o defeito que a política existe para nomear.
7. **Decisão não aprovada não vira requisito.** `decision_refs` aponta só
   para `DEC` `answered`; requisito cujo `DEC` está `pending`, `skipped`
   ou recusado volta ao operador.

## A lista de validação

Revise cada requisito e cada critério antes do `ready`:

| defeito | pergunta que pega |
|---|---|
| critério não testável | que observável distingue passou de falhou? qual `verified_by` o prende? |
| métrica sem fonte | de onde sai o número — comando, arquivo, fact? |
| requisito conflitante | existe estado do mundo em que os dois valem juntos? |
| requisito duplicado | mesma prova, mesmo observável, outro texto? |
| escopo inconsistente | o AC prova algo dentro do `out_of_scope`, ou fora de toda story? |
| dependência desconhecida | depende de sistema/versão/permissão sem verbo nem `U<n>`? |
| decisão não aprovada | o `decision_refs` aponta para `DEC` `answered`? |
| premissa não confirmada | afirma fato do mundo sem medida, case ou `fact_id`? |

Cada linha falha em silêncio quando a pergunta não é feita: a revisão é
ler os itens com a tabela na frente, não lembrar dela.

## Rastreabilidade ponta a ponta

```
REQ-2 "a extração não para em partição vazia"
  └─ AC2 {kind: test, ref: tests/test_x.py::test_particao_vazia}
       └─ D1 "iterador tolerante a zero linhas" (design)
            └─ T3 "escrever iterador + teste" (plan)
                 └─ red/green no build_report (build)
                      └─ hypothesis_outcome + deviations (ship)
```

Auditoria lê a trilha nos dois sentidos: para baixo ("o que entrega
REQ-2?") e para cima ("este `AC` serve a quê?"). Critério sem requisito é
escopo crescendo sozinho; requisito sem critério é promessa — os dois
voltam ao define.
