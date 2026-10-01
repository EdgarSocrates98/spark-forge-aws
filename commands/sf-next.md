---
name: sf-next
description: Pergunta a rota determinística para o case atual — a decisão vem de routing.yaml, nunca do julgamento do agente.
---

Você vai descobrir qual é o próximo passo recomendado para o case aberto neste
repositório.

Rode:

```
sparkforge next-step --repo <raiz-do-repo> [--findings <arquivo-de-findings.json>]
```

Passe `--findings` se já existir um `findings.json` desta investigação (gerado por
`sparkforge judge --out findings.json`) — a rota pode depender de quais achados já
existem (por exemplo, `SF-PY-004` presente muda a recomendação).

## Regras de leitura do resultado

- `recommended_skill` é a decisão. Ela vem de `routing.yaml`, o mesmo tipo de
  motor determinístico do catálogo de regras, avaliado sobre o estado do case
  (fase, gates, índices) e os achados atuais. **Não substitua essa decisão pelo
  seu próprio julgamento** — se você acha que outra skill seria melhor, isso é
  sinal de que falta uma regra de roteamento, não licença para ignorar a que
  existe.
- `blocked_by` é **advisory**, não um bloqueio real: lista gates que ainda não
  foram satisfeitos (ex.: `baseline_captured`), mas não impede você de seguir a
  skill recomendada. Trate como um aviso a comunicar ao usuário, não como uma
  trava.
- `missing_artifacts` e `collect_commands` dizem o que falta coletar e como
  coletar — rode esses comandos antes de tentar a skill recomendada, se a lista
  não estiver vazia.
- `alternatives` lista outras rotas que também casaram, em ordem de rank, caso a
  principal não seja aplicável no seu contexto específico.
