---
name: regression-judge
dispatch: ephemeral
max_rounds: 1
max_messages: 8
max_tokens: 1800
requires_evidence: true
network: forbidden
---
# Subagent `regression-judge`

regression judge

## Contract
- Input: typed package from coordinator.
- Output: structured object with evidence and confidence.
- Tools: local tools only; no network.
- Escalation: return unresolved when evidence is missing.
- Stop: one execution and one handoff; no loop.
- Safety: no file mutation or publication.
