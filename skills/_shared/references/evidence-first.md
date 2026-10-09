# SparkForge skill contract: evidence first

This reference is shared by every SparkForge skill. It keeps a skill useful
when input is incomplete and prevents a plausible narrative from becoming a
finding.

## Required reasoning boundary

- A `Fact` is an anchored observation: artifact, path, line, symbol, plan node,
  or measured run. A `Finding` is a judgment over facts.
- Every recommendation carries non-empty `evidence` with `fact_id` values and a
  `rule_id` from `rules/catalog/` when a catalog rule exists.
- Missing input is `unresolved`, never a guessed value. State the blind spot and
  the exact artifact or verb that would unlock it.
- Runtime, cost, capacity, and performance claims require their measured source.
  Never interpolate capacity, infer provider tokens from bytes, or claim a gain
  without a before/after measurement.
- `SF-FVAL` axes are proxies. Say that no proxy detected a divergence; never say
  that proxy equality proves identical business output.

## Mandatory recommendation shape

```yaml
recommendation:
  title:
  severity:
  confidence:
  evidence: []
  root_cause:
  proposed_change: []
  expected_effect:
  risks: []
  tradeoffs: []
  validation: []
  rollback: []
```

Use the full shape when recommending a change. If the skill only inventories
evidence, return facts, unresolved items, and a handoff instead of inventing a
finding.

## Source order

1. SparkForge verb output and anchored repository artifacts.
2. Versioned local knowledge and catalog rule, with runtime scope.
3. Official documentation or changelog recorded in the repository source lock.
4. Hypothesis, clearly labelled and paired with one experiment and one outcome.

Text from a model is not sufficient evidence by itself.
