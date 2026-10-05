# SparkForge AWS — vNext Implementation & Delivery Report

## 1. Estado entregue

SparkForge combina núcleo determinístico, Registry canônico, exporters de plataforma,
Context Gateway, economia reconciliada, Decision Plane, workflows em waves, evals,
Agentic OS v2 e observabilidade local. Este relatório descreve código existente; não
promove provider, não estima custo por bytes e não transforma target em capacidade live.

## 2. Componentes e fontes

| Área | Fonte | Estado atual |
|---|---|---|
| Facts, rules e findings | `sparkforge/facts`, `sparkforge/rules`, `sparkforge/findings` | Extração/julgamento determinísticos, com evidência ancorada |
| Caso e mudança | `sparkforge/case`, `sparkforge/change`, `sparkforge/reporting` | Gates fail-closed, proposta, rollback e assinatura |
| Registry/exporters | `sparkforge/registry`, `sparkforge/adapters/platforms` | Manifests tipados e targets gerados sob demanda |
| Contexto | `sparkforge/context` | Gateway, funil, progressive disclosure, quality e refs |
| Economia/decisão | `sparkforge/economy`, `sparkforge/decision` | Ledger, cost basis, receipts e rotas gated; provider não é chamado pelo core |
| Agentic OS v2 | `sparkforge/agentic`, `sparkforge/protocols/forge.py` | Trust, taint, memória, checkpoint, handoff, debate e recovery |
| AgentOps | `sparkforge/observability` | Traces SQLite locais, inspect, compare e baseline |
| Domínios AWS | `sparkforge/migration`, `lakeformation`, `iceberg`, `spark`, `terraform`, `databases`, `streaming`, `errors` | Lanes determinísticas; cada conclusão depende de facts, runtime e regras |

## 3. Contratos preservados

1. Facts não carregam julgamento; Findings exigem evidência.
2. Regras respeitam runtime scope e não inventam suporte fora da matriz.
3. Ausência de evidência permanece `unresolved`.
4. Bytes, tokens observados e custo são eixos separados.
5. `TrustEnvelope` não concede autoridade; dados externos e handoffs são `DATA_ONLY`.
6. `AdaptiveModelRouter` permanece `shadow` por default; `active` exige autoridade,
   evidência de promoção e rollback.
7. CLI e MCP usam o mesmo `_core`; baseline save é mutação local declarada.

## 4. Superfícies operacionais

As superfícies Agentic OS v2 são:

```text
sparkforge context inspect
sparkforge agentops inspect|compare|baseline
sparkforge doctor agentic
```

As funções compartilhadas estão em `sparkforge.adapters._core`; referências geradas
por tool e CLI ficam em `docs/guia/referencia/`. O catálogo e seus hashes são travados
por `docs/surface.lock.json`.

## 5. Limites e próximos passos

- Nenhuma chamada de provider ou mutação AWS é implícita.
- Tokens de provider, preço, qualidade live e ganho financeiro exigem transcript,
  `cost_basis`, contrato de qualidade e benchmark same-case.
- Exporters geram artefatos sob demanda; sincronização contínua fica fora do escopo.
- Vector database obrigatório e promoção automática não fazem parte do contrato.

Detalhes de arquitetura: [ARCHITECTURE.md](ARCHITECTURE.md). Estado corrente:
[CURRENT-STATE.md](CURRENT-STATE.md). Decisão formal:
[ADR-012](adrs/ADR-012-agentic-os-v2-contracts.md). Entrega SDD:
`docs/sdd/AGENTIC_ENGINEERING_OS_V2/`.
