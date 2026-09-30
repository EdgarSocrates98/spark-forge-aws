# Evolu‡Æo Agˆntica do SparkForge

> **Dois pacotes com nome parecido, e eles não são a mesma coisa.** Este
> documento descreve `sparkforge/agents/` — `ConversationRoom`,
> `AutonomyController`, `Supervisor`, `budget`, `model_policy` —, a camada de
> orquestração que existe desde a expansão agêntica. `sparkforge/agentic/`
> (2026-09-03) é OUTRO pacote: entidades de primeira classe (`Claim`,
> `Evidence`, `Decision`), protocolo de debate, arbitragem e blackboard JSONL,
> e ele é **biblioteca sem produtor** — nada no produto escreve nessas
> entidades. Ver `docs/agentic-evolution-report.md`. A sobreposição entre os
> dois (autonomia, budget e observabilidade aparecem nos dois pacotes) é dívida
> conhecida, registrada e não resolvida.


## VisÆo

O SparkForge agora combina agents especializados, mem¢ria compartilhada por caso, handoffs estruturados, roteamento por fase e autonomia limitada. A met fora de sala de conversa representa o protocolo de coopera‡Æo; nÆo ‚ necess rio criar uma interface de chat.

## Capacidades

| Capacidade | Implementa‡Æo | Benef¡cio |
|---|---|---|
| Autonomia controlada | `AutonomyController` | Escolhe a menor pr¢xima etapa e para por or‡amento, estagna‡Æo ou sucesso |
| Mem¢ria compartilhada | `ConversationRoom` | Mant‚m fatos, decisäes, referˆncias e snapshots sem reenviar o hist¢rico inteiro |
| Economia de tokens | `budget.py` | Deduplica, ranqueia por relevƒncia, preserva decisäes e limita contexto |
| Especializa‡Æo | agents de PySpark, runtime, storage, orquestra‡Æo e verifica‡Æo | Reduz escopo, fan-out e chamadas sem ganho |
| Governan‡a de ferramentas | allowlist, aprova‡Æo e rollback | Evita a‡äes mut veis e ferramentas fora do contrato |
| Conhecimento | `knowledge/agentic-engineering.md`, `token-economy.md` e matriz | Padroniza decisäes e melhora handoffs |

## Pol¡tica de qualidade por token

Uma redu‡Æo s¢ ‚ v lida quando mant‚m cobertura de evidˆncia, achados aceitos, taxa de verifica‡Æo e crit‚rios de aceita‡Æo. O sistema deve medir tokens de entrada e sa¡da, cache hits, duplicatas removidas, cobertura de evidˆncia e falhas de verifica‡Æo.

## Loop recomendado

O fluxo normal ‚ `inventory -> collect -> analyze -> judge -> verify -> synthesize`. O supervisor s¢ amplia o n£mero de agents quando existe risco, contradi‡Æo ou lacuna. A execu‡Æo deve come‡ar pelo caminho barato e determin¡stico, usando LLM apenas quando houver ambiguidade ou s¡ntese necess ria.

## Crit‚rios de parada

A execu‡Æo termina por decisÆo terminal, or‡amento de itera‡äes, or‡amento de tokens, limite de mensagens, estagna‡Æo ou regressÆo de qualidade. Nunca aumente o or‡amento automaticamente porque o loop nÆo progrediu.

## Opera‡Æo

## Prompt e agent evolution

`config/evolution/prompt_agents.yaml` registra candidatos versionados offline.
Cada candidato recebe digest SHA-256 da identidade declarada, incluindo versão,
contrato, calibração e pai. Mutação precisa apontar para o digest do pai; conteúdo
externo ao repositório é recusado.

Estados permitidos: `candidate -> evaluated -> accepted -> rolled_back` e
`evaluated -> rejected`. A transição não concede autoridade. Promoção ativa usa a
mesma `AuthorityPolicy`, exige contrato, calibração, gates, referências de
evidência e rollback, e segue desabilitada na política padrão.

`EvolutionService` faz replay local contra a suíte imutável de 50 casos, mantendo
caso, domínio, partição e perfil. Qualidade, rota, bytes, tokens de transcript e
custo com `cost_basis` ficam separados; ausência vira `unresolved`.

Recibos content-addressed em `.sparkforge/evolution/` vinculam candidato, pai,
suíte, gates, autoridade e rollback. Núcleo não chama modelo, AWS ou provedor.

Operação local:

```bash
python -m sparkforge.evals candidate validate --repo .
python -m sparkforge.evals candidate evaluate --repo . --candidate routing-variant
python -m sparkforge.evals candidate promote --repo . --candidate routing-variant --allow-active
python -m sparkforge.evals candidate rollback --repo . --candidate routing-variant --previous routing-baseline
```

Ap¢s alterar skills ou agents, execute `python scripts/sync_skills.py`. Antes de publicar uma mudan‡a, execute os testes focados, a su¡te completa e as avalia‡äes existentes. Mudan‡as de infraestrutura, escrita ou publica‡Æo exigem aprova‡Æo humana, plano de rollback e evidˆncia do impacto.
