# Arquitetura Agentica do SparkForge

O SparkForge passa a operar como um sistema de agentes cooperativos, com caso persistente, plano de fases e sala append-only. Cada agent possui especialização, contrato de entrada e saída, limites de custo e evidências exigidas.

## Loop controlado

Cada caso executa observe -> plan -> dispatch -> debate -> verify -> synthesize -> decide, limitado por max_rounds, max_messages, max_tokens e deadline_seconds. Há decisões terminais explícitas para sucesso, bloqueio, falta de evidência e aprovação humana.

## Salas e tokens

Uma sala é um log JSONL por caso. Mensagens têm tipo, autor, fase, referências e hash. O contexto enviado a cada agent é uma janela relevante; mensagens antigas viram snapshots verificáveis. Ferramentas determinísticas rodam antes do LLM; fatos duplicados são deduplicados; saídas usam schema; o modelo escala conforme a complexidade.

## Governança

Ações destrutivas, alterações de infraestrutura, exposição de segredos e publicação externa exigem aprovação. Ferramentas são allowlisted por agent e argumentos são validados. Toda decisão registra custo estimado, resultado e rollback.

## Migração

A entrega adiciona runtime local e configuração declarativa sem substituir os agents atuais. O roteador continua produzindo recommended_agent; o supervisor consome essa decisão, abre a sala e despacha fases. MCP permanece opcional, com fallback para CLI.
