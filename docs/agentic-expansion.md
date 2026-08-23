# Agentic Expansion e Offline First

## O que foi criado

A expansao adiciona dez agents permanentes, dezesseis subagents efemeros, seis ferramentas locais deterministicas, seis knowledge bases novas, cinco times cooperativos e um manifesto SHA-256 para todos os documentos locais. Os registries sao `config/agentic-expansion.yaml`, `config/subagents.yaml` e `config/teams-expansion.yaml`.

## Garantia sem internet

O computador executor pode estar sem DNS, HTTP, SDK cloud ou acesso ao provedor de documentacao. Os agents consultam primeiro `knowledge/offline-manifest.json`, verificam checksums e fazem busca local. Nenhuma ferramenta offline usa requests, socket, DNS ou fallback silencioso. Se um fato depender de fonte ausente, o resultado deve ser `unresolved`.

## Verificacao

Linux e macOS:
```bash
python -m sparkforge.tools.cli offline verify --repo .
python -m sparkforge.tools.cli offline search "schema streaming governance" --repo .
```

Windows PowerShell:
```powershell
python -m sparkforge.tools.cli offline verify --repo .
python -m sparkforge.tools.cli offline search "schema streaming governance" --repo .
```

O comando `offline verify` valida o SHA-256 de cada arquivo listado no manifesto. O comando `offline search` retorna somente caminhos locais, score, excerpt e a marca `offline: true`.

## Ferramentas novas

- `sparkforge/tools/context.py`: deduplicacao e selecao de contexto por kind.
- `sparkforge/tools/cost.py`: estimativa local de tokens, sempre marcada como estimativa.
- `sparkforge/tools/schema.py`: comparacao de campos, tipos, required e compatibilidade.
- `sparkforge/tools/lineage.py`: extracao deterministica de edges em texto e SQL.
- `sparkforge/tools/evaluation.py`: comparacao de golden cases e findings.
- `sparkforge/tools/offline.py`: busca local e verificacao de manifesto.
- `sparkforge/tools/cli.py`: interface `sparkforge-tools offline`, `cost` e `lineage`.

## Ordem de cooperacao

1. O coordenador empacota objetivo e artefatos com `intake-packager`.
2. `evidence-extractor` produz fatos locais.
3. O especialista permanente formula hipoteses e pede `cross-reviewer`.
4. `schema-compatibility-checker`, `lineage-impact-analyzer`, `security-gate` ou `cost-estimator` executam gates focados.
5. `regression-judge`, `rollback-planner` e `release-gate` fecham a validacao.
6. O supervisor escreve handoff com unresolved e next_step quando faltar evidencia.

## Times novos

| Time | Coordenador | Missao |
| --- | --- | --- |
| Evidence Quality | `sf-evidence-verifier` | Evidencia, avaliacao, contexto e memoria |
| Governance Security | `sf-security-reviewer` | Lake governance, lineage, schema e mutacao |
| Streaming Reliability | `sf-kinesis-specialist` | Lag, replay, checkpoint e resiliencia |
| FinOps Data | `sf-cost-reviewer` | Custo de dados, infraestrutura e tokens |
| Agent Quality | `sf-agent-evaluation-specialist` | Golden cases, regressao e seguranca |

## Limites

A ausencia de internet permite usar conhecimento local, mas nao atualiza fontes externas. Para atualizar, execute uma sincronizacao em computador conectado, regenere o manifesto, revise o diff e distribua o pacote novamente. Nao transforme uma pagina web antiga ou um checksum ausente em recomendacao afirmativa.
