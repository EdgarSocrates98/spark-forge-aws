# Evoluá∆o Agàntica do SparkForge

## Vis∆o

O SparkForge agora combina agents especializados, mem¢ria compartilhada por caso, handoffs estruturados, roteamento por fase e autonomia limitada. A met†fora de sala de conversa representa o protocolo de cooperaá∆o; n∆o Ç necess†rio criar uma interface de chat.

## Capacidades

| Capacidade | Implementaá∆o | Benef°cio |
|---|---|---|
| Autonomia controlada | `AutonomyController` | Escolhe a menor pr¢xima etapa e para por oráamento, estagnaá∆o ou sucesso |
| Mem¢ria compartilhada | `ConversationRoom` | MantÇm fatos, decis‰es, referàncias e snapshots sem reenviar o hist¢rico inteiro |
| Economia de tokens | `budget.py` e `token-efficient-agent` | Deduplica, ranqueia por relevÉncia, preserva decis‰es e limita contexto |
| Especializaá∆o | agents de PySpark, runtime, storage, orquestraá∆o e verificaá∆o | Reduz escopo, fan-out e chamadas sem ganho |
| Governanáa de ferramentas | allowlist, aprovaá∆o e rollback | Evita aá‰es mut†veis e ferramentas fora do contrato |
| Conhecimento | `knowledge/agentic-engineering.md`, `token-economy.md` e matriz | Padroniza decis‰es e melhora handoffs |

## Pol°tica de qualidade por token

Uma reduá∆o s¢ Ç v†lida quando mantÇm cobertura de evidància, achados aceitos, taxa de verificaá∆o e critÇrios de aceitaá∆o. O sistema deve medir tokens de entrada e sa°da, cache hits, duplicatas removidas, cobertura de evidància e falhas de verificaá∆o.

## Loop recomendado

O fluxo normal Ç `inventory -> collect -> analyze -> judge -> verify -> synthesize`. O supervisor s¢ amplia o n£mero de agents quando existe risco, contradiá∆o ou lacuna. A execuá∆o deve comeáar pelo caminho barato e determin°stico, usando LLM apenas quando houver ambiguidade ou s°ntese necess†ria.

## CritÇrios de parada

A execuá∆o termina por decis∆o terminal, oráamento de iteraá‰es, oráamento de tokens, limite de mensagens, estagnaá∆o ou regress∆o de qualidade. Nunca aumente o oráamento automaticamente porque o loop n∆o progrediu.

## Operaá∆o

Ap¢s alterar skills ou agents, execute `python scripts/sync_skills.py`. Antes de publicar uma mudanáa, execute os testes focados, a su°te completa e as avaliaá‰es existentes. Mudanáas de infraestrutura, escrita ou publicaá∆o exigem aprovaá∆o humana, plano de rollback e evidància do impacto.
