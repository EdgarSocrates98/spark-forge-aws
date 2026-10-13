# SparkForge AWS — índice documental vNext

Este diretório reúne arquitetura, estado corrente, catálogo, limites e decisões da
linha vNext. A leitura correta separa três coisas:

- **Implementado**: contrato local, determinístico, testável e sem mutação AWS implícita.
- **Target**: integração futura, exporter sob demanda ou capacidade que depende de
  evidência externa.
- **Unresolved**: o artefato, transcript, preço, runtime ou benchmark disponível não
  permite afirmar mais.

## Leitura recomendada

1. [`CURRENT-STATE.md`](CURRENT-STATE.md) — baseline histórico e overlay atual.
2. [`CURRENT-STATE-AUDIT.md`](CURRENT-STATE-AUDIT.md) — auditoria de componentes,
   lacunas e fechamento Agentic OS v2.
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitetura-alvo e implementação corrente,
   com fronteiras de provider e AWS.
4. [`IMPLEMENTATION-REPORT.md`](IMPLEMENTATION-REPORT.md) — fontes de código,
   contratos preservados e superfícies operacionais.
5. [`FINAL-REPORT.md`](FINAL-REPORT.md) — relatório consolidado de entrega e limites
   de evidência.
6. [`CAPABILITY-MATRIX.md`](CAPABILITY-MATRIX.md) — limites de cobertura por domínio;
   não é uma promessa geral de suporte AWS.
7. [`AGENT-CATALOG.md`](AGENT-CATALOG.md) — coordenadores, executores e skills
   canônicos.
8. [`DEMOS.md`](DEMOS.md) — demonstrações ilustrativas, sem transformar cenário em
   medição de custo, tokens ou performance.
9. [`KNOWLEDGE-MAP.md`](KNOWLEDGE-MAP.md) — vocabulário e localização dos contratos.

## Decisões e entrega

As decisões arquiteturais estão em [`adrs/`](adrs/), com destaque para
[`ADR-012-agentic-os-v2-contracts.md`](adrs/ADR-012-agentic-os-v2-contracts.md).
O ciclo SDD correspondente está em
[`../sdd/AGENTIC_ENGINEERING_OS_V2/`](../sdd/AGENTIC_ENGINEERING_OS_V2/).

O manifesto de claims auditáveis está em [`../claims.lock.json`](../claims.lock.json)
e é verificado por `python scripts/check_vnext_claims.py`. Claims removidas ficam
retidas como `REMOVIDA` para preservar a trilha de reconciliação; claims sem artefato,
transcript ou benchmark não são promovidas por prosa.

## Limite operacional

O núcleo não chama modelo, provider SDK, AWS ou Docker durante extração, julgamento,
decisão e verificação de contrato. Coleta live e ações de escrita pertencem às
fronteiras explicitamente documentadas e exigem seus artefatos, gates e confirmação.
