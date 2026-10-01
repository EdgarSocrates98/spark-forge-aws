# DESIGN: PROMPT_EVO_NOVA_EVOLUCAO

> Technical design for implementing a canonical evaluation evidence contract and a fail-closed promotion path for prompt candidates.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PROMPT_EVO_NOVA_EVOLUCAO |
| **Date** | 2026-09-30 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_PROMPT_EVO_NOVA_EVOLUCAO.md](./DEFINE_PROMPT_EVO_NOVA_EVOLUCAO.md) |
| **Status** | ✅ Shipped |

The design confidence is **0.92** for the offline bundle and policy path because the repository already has content-addressed candidates, replay reports, host transcript validation and tamper-checked receipts. Confidence for the authorized external command adapter is **0.82** until a real host envelope is supplied; the adapter therefore accepts only the versioned JSON contract described here and refuses all other output.

KB grounding used in this design:

- `python/concepts/dataclasses.md` and `python/patterns/clean-architecture.md` support frozen/slotted value objects and one-way dependencies. Confidence: **0.95**.
- `python/patterns/error-handling.md` supports named domain errors and exception chaining. Confidence: **0.95**.
- `genai/patterns/evaluation-framework.md` supports separate samples, metrics and pairwise comparison. Confidence: **0.90**; provider calls remain excluded by the repository contract.
- `prompt-engineering/patterns/validation-prompts.md` supports strict structured-output validation and evidence/reason fields. Confidence: **0.88**.
- `testing/patterns/integration-tests.md` and `testing/patterns/fixture-factories.md` support isolated filesystem fixtures and adapter boundary tests. Confidence: **0.95**.

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                 EVALUATION EVIDENCE AND PROMOTION PATH                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Versioned fixture/file       Explicitly authorized command                 │
│          │                              │                                   │
│          ▼                              ▼                                   │
│  BundleFileAdapter       AuthorizedCommandAdapter                           │
│          └───────────────┬───────────────┘                                   │
│                          ▼                                                   │
│              EvaluationEvidenceBundle.from_mapping()                        │
│              canonicalize → validate → verify bundle digest                 │
│                          │                                                   │
│             ┌────────────┴────────────┐                                      │
│             ▼                         ▼                                      │
│   PolicyResolver                      Host/transcript validator              │
│   family/kind/contract                hash, usage, cost_basis, unresolved     │
│             │                         │                                      │
│             └────────────┬────────────┘                                      │
│                          ▼                                                   │
│       EvolutionService.evaluate()                                            │
│       one paired replay: baseline + candidate                                │
│       compare distinct reports → quality/economy gates                       │
│                          │                                                   │
│                          ▼                                                   │
│       sequence + previous receipt + policy/candidate/evidence identities      │
│                          │                                                   │
│             ┌────────────┴────────────┐                                      │
│             ▼                         ▼                                      │
│   evaluation receipt                  PromotionGate                          │
│   .sparkforge/evolution/*.json        CI + benchmark + review + rollback     │
│             │                         │                                      │
│             └──────────────► accepted candidate or named refusal             │
│                                                                            │
│  Legacy receipts enter through a read-only compatibility parser.             │
│  Missing new fields remain legacy metadata and never become new evidence.   │
│  No component imports a provider SDK, MCP SDK or network client.             │
└────────────────────────────────────────────────────────────────────────────┘
```

The package remains a local Python runtime. Dependencies flow from pure evidence and policy models to adapters and then to the evolution service. The adapters return untrusted mappings; only the canonical bundle validator can create a bundle consumed by evaluation or promotion. `EvolutionService` remains the application boundary and is the only component that writes evolution receipts. Legacy parsing is read-only and cannot call the new promotion path without a complete current bundle.

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `EvaluationEvidenceBundle` | Immutable canonical value object for candidate, parent, suite/input, execution, transcript, reports, metrics, policy, evidence and rollback identities. | Python `@dataclass(frozen=True, slots=True)`, canonical JSON and SHA-256 |
| `EvidenceRef` and `EvaluationRefusal` | Represent bounded proof references and machine-readable fail-closed reasons. | Frozen dataclasses, named `EvolutionError` subclasses/messages |
| `PolicyResolver` | Resolve exactly one policy by candidate family, kind, contract id/version; expose policy version and digest. | YAML registry + typed Python model |
| `BundleFileAdapter` | Read a local JSON/YAML bundle from a declared path and normalize it through the canonical validator. | Filesystem adapter; no execution or network |
| `AuthorizedCommandAdapter` | Invoke one explicitly allowlisted executable with argv, bounded timeout/output and a temporary input manifest; parse the returned bundle through the same validator. | `subprocess.run(..., shell=False)` and JSON |
| `EvolutionService` | Orchestrate policy resolution, paired replay, comparison, gates, receipt sequencing and promotion. | Existing `sparkforge/evals/evolution.py` facade |
| `Replay benchmark` | Run the current paired baseline/candidate benchmark once per evaluation and preserve reports as distinct sides. | Existing `run_replay_benchmark` in `decision_replay.py` |
| `Legacy receipt facade` | Read old receipts and mark missing current fields as compatibility gaps. | Existing receipt reader extended with explicit legacy state |
| `Evolution registry` | Store policy map and candidate family metadata without introducing infrastructure. | `config/evolution/prompt_agents.yaml` |

### Boundaries and dependency direction

```text
evidence.py  ←  policy.py
     ↑              ↑
adapters.py  ───────┘
     ↑
evolution.py  → decision_replay.py / decision.authority.py
     ↑
CLI and tests
```

`evidence.py` imports only the standard library and existing fingerprint helper if needed. `policy.py` imports evidence types only for identity validation. `evidence_adapters.py` imports evidence and standard-library subprocess/file APIs; it does not import `EvolutionService`. `evolution.py` imports all lower layers and remains the orchestration boundary. No lower layer imports `evolution.py`, so the compatibility facade cannot create a circular dependency.

## Canonical Evidence Contract

The new bundle is schema version `1` and its `bundle_id` is the SHA-256 digest of the canonical body with `bundle_id` omitted. Canonical JSON uses sorted keys, compact separators and UTF-8. Lists whose order has semantic meaning retain order; identity/reference lists are sorted before hashing. Raw transcript turns are not stored in the repository bundle. A transcript is represented by its hash, source reference and validated usage/cost metadata.

```yaml
schema_version: 1
bundle_id: sha256:<digest-of-canonical-body>
candidate:
  id: routing-variant
  version: "1.1.0"
  family: prompt
  kind: prompt
  candidate_digest: sha256:<candidate-digest>
  parent_digest: sha256:<accepted-parent>
  contract_id: routing.data_domain
  contract_version: "1"
  contract_sha256: sha256:<contract-digest>
suite:
  suite_id: decision-control-plane-v1
  suite_sha256: sha256:<suite-digest>
  input_manifest_sha256: sha256:<manifest-digest>
execution:
  mode: surrogate                 # surrogate | recorded_host | live_external
  adapter: fixture | bundle_file | authorized_command
  sequence: 1
transcripts:
  baseline:
    sha256: sha256:<hash-or-null>
    source_ref: fixture:baseline
  candidate:
    sha256: sha256:<hash-or-null>
    source_ref: fixture:candidate
reports:
  baseline: { ...paired replay report... }
  candidate: { ...paired replay report... }
metrics:
  comparison: { ...comparison... }
  quality: { ...quality metrics... }
  economy: { ...economy metrics... }
policy:
  policy_id: prompt.prompt.routing.data_domain.1
  policy_version: prompt-agent-evolution-policy-v2
  policy_sha256: sha256:<resolved-policy-digest>
evidence_refs:
  - kind: ci
    ref: ci:run/123
    sha256: sha256:<artifact-digest>
  - kind: benchmark
    ref: benchmark:decision-control-plane-v1
    sha256: sha256:<artifact-digest>
  - kind: review
    ref: review:PR-123
    sha256: sha256:<artifact-digest>
rollback_target: sha256:<accepted-parent>
```

Validation is ordered so failures are specific: root/version and shape, candidate/parent identity, suite and manifest identity, execution mode/adapter compatibility, transcript integrity and unresolved usage, policy identity, report/comparison identity, evidence reference shape, rollback target, then bundle digest. A valid object is the only input accepted by `EvolutionService.evaluate(bundle=...)` or the new promotion gate. Unknown required fields and unsupported versions produce a named refusal rather than being ignored.

`provider_tokens` is copied into metrics only when a transcript hash and valid usage source are present and matching. Otherwise the field is `null` and `tokens_unresolved: true` with a reason. `cost` is measured only when a value and a valid `cost_basis` are both present. Payload bytes never become provider tokens and are never used as a cost basis.

## Policy Resolution

The current single `evaluation_policy` mapping moves to an explicit policy collection. The existing thresholds remain the seed values; this feature changes ownership and binding, not the default quality decision.

```yaml
policy_version: prompt-agent-evolution-policy-v2
policies:
  - policy_id: prompt.prompt.routing.data_domain.1
    family: prompt
    kind: prompt
    contract_id: routing.data_domain
    contract_version: "1"
    minimum_labeled_tasks: 50
    quality:
      min_status_accuracy: 1.0
      min_evidence_recall: 1.0
      max_false_positive_rate: 0.0
      max_quality_regression: 0.0
      min_route_accuracy: null
      max_route_regression: 0.0
      require_route_metric: false
    economy:
      max_payload_regression: 0.05
      max_token_regression: 0.0
      max_cost_regression: 0.0
      require_tokens: false
      require_cost: false
```

Resolution key is `(family, kind, contract_id, contract_version)`. The resolver must find exactly one entry. Zero entries return `evaluation_policy_missing:<key>`; multiple entries return `evaluation_policy_ambiguous:<key>`. There is no default policy for a registered candidate. `CandidateEvaluation` stores the resolved policy identity and gate results; it no longer owns or compares a literal corpus threshold. The replay loader receives the resolved `minimum_labeled_tasks` for the new path. The legacy suite field remains readable for existing standalone replay tests, but it cannot override a resolved policy during evaluation.

## Receipt Identity and Sequence

New evaluation, promotion and rollback receipts keep the current content-addressed filename and add:

```json
{
  "receipt_id": "<sha256-of-body>",
  "receipt_schema_version": 2,
  "event_sequence": 17,
  "previous_receipt_id": "<sha256-of-sequence-16>",
  "candidate_digest": "<sha256>",
  "policy_sha256": "<sha256>",
  "bundle_id": "<sha256>",
  "rollback_target": "<sha256>"
}
```

`EvolutionService._write()` obtains the next sequence under an exclusive local lock, verifies the previous receipt, writes the content-addressed JSON atomically, and releases the lock. `latest_evaluation()` reads only verified v2 receipts, checks that sequences are unique and that `previous_receipt_id` links the chain, then selects the highest sequence for the candidate. A gap, duplicate, collision or broken predecessor returns `evolution_receipt_sequence_invalid:<reason>`. Legacy receipts without sequence are returned through a compatibility object ordered by their existing timestamp/filename only for historical inspection; they are never considered current promotion evidence.

The sequence is an ordering proof, not a wall-clock claim. No timestamp is used to choose the latest evaluation, and no provider or external service is needed to verify the chain.

## Key Decisions

### Decision 1: One canonical bundle for file and command adapters

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-30 |

**Context:** The feature must accept deterministic fixture/file evidence and a live external host result while keeping the Forge offline and provider-independent.

**Choice:** Both adapters return an untrusted mapping and immediately call `EvaluationEvidenceBundle.from_mapping()`. The command adapter contributes only provenance (`command_id`, executable digest, argv digest and bounded output digest); it does not define a second schema or run a provider itself.

**Rationale:** One validator gives AT-001 and AT-002 the same required fields, digest rules and refusal vocabulary. A host can evolve its transport without changing the promotion contract. This follows the repository’s existing `HostEnvelope` boundary and structured-output validation pattern.

**Alternatives Rejected:**
1. Separate file and command models - Rejected because equivalent inputs could pass different validation and produce non-comparable receipts.
2. Let the command print Python or YAML to be imported - Rejected because execution of returned content would violate the offline/provider-independent boundary and create code injection risk.

**Consequences:**
- Adapters must normalize into JSON-compatible mappings before validation.
- External hosts must implement the schema and carry hashes for every declared evidence source.
- The bundle validator becomes a compatibility boundary that requires careful versioning.

### Decision 2: Keep paired replay as one orchestration call

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-30 |

**Context:** `EvolutionService.evaluate()` currently builds a baseline report and a candidate report by calling `run_replay_benchmark` twice, while that function already accepts both runners in one paired pass.

**Choice:** Call `run_replay_benchmark` once with the accepted parent runner and candidate runner. Preserve the returned baseline/candidate cells as distinct reports and pass those reports to the existing comparator.

**Rationale:** This directly satisfies AT-003, avoids changing the stable report schema, and ensures same-case/input-manifest checks are applied to both sides in one pass. The instrumented test can assert one paired benchmark call and one invocation per runner/case/profile cell.

**Alternatives Rejected:**
1. Add a second independent runner API - Rejected because it would duplicate the current replay contract and create two possible report shapes.
2. Reuse one report for both sides - Rejected because it would make a comparison vacuously pass and lose candidate identity.

**Consequences:** The evaluation service must pass the resolved policy threshold to suite loading before the paired call and must persist both report identities in the evidence bundle.

### Decision 3: Policy is an identity, not a fallback configuration

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-30 |

**Context:** A global policy and the hardcoded `labeled_tasks >= 50` check can evaluate a candidate under thresholds that are not bound to its family or contract.

**Choice:** Resolve one policy by `(family, kind, contract_id, contract_version)`, canonicalize its complete mapping, store `policy_version` and `policy_sha256` in the bundle and receipt, and refuse zero or multiple matches.

**Rationale:** The reviewer can reproduce both the selection and the threshold values from one digest. It removes the hidden default from `CandidateEvaluation` while keeping the current policy values as explicit configuration.

**Alternatives Rejected:**
1. Keep one global policy - Rejected because distinct candidate families cannot be governed independently.
2. Pick the closest policy or use a default - Rejected because ambiguity would become an unreviewed promotion decision.

**Consequences:** Registry entries and fixtures need explicit family/contract identity. Old registries remain readable through the compatibility parser but do not satisfy the new promotion gate until re-evaluated.

### Decision 4: New receipts form a verifiable local chain

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-30 |

**Context:** Sorting content-addressed filenames does not express event order and permits multiple valid-looking receipts to be selected ambiguously.

**Choice:** Add an exclusive local sequence, predecessor receipt id and chain validation to v2 receipts while preserving v1 read compatibility.

**Rationale:** The chain makes latest selection deterministic without trusting timestamps or a mutable database. Tampering is caught by both receipt digest and predecessor validation. The lock only protects local writers and is not presented as distributed coordination.

**Alternatives Rejected:**
1. Sort by mtime - Rejected because filesystem metadata is mutable and not content-addressed.
2. Migrate every old receipt - Rejected because rewriting history would change identities and break historical audit links.

**Consequences:** A broken chain blocks current evaluation lookup and promotion until the operator supplies a valid new sequence. Legacy inspection remains available with an explicit compatibility status.

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/evals/evidence.py` | Create | Canonical bundle, evidence refs, transcript/economy provenance, refusal codes, canonical digest and strict parser. | (general) | None |
| 2 | `sparkforge/evals/policy.py` | Create | Typed policy key/resolver, policy collection parser, policy digest and missing/ambiguous policy errors. | (general) | 1 |
| 3 | `sparkforge/evals/evidence_adapters.py` | Create | Bundle-file and authorized-command adapters with allowlist, bounded subprocess and shared normalization. | @sf-security-reviewer | 1, 2 |
| 4 | `sparkforge/evals/evolution.py` | Modify | Consume resolved policies and bundles, remove duplicate replay execution, write v2 chained receipts, preserve legacy facade and enforce promotion evidence. | (general) | 1, 2, 3, 5 |
| 5 | `sparkforge/evals/decision_replay.py` | Modify | Accept policy-provided corpus minimum on the new path while preserving standalone legacy suite reads and paired report shape. | (general) | 2 |
| 6 | `config/evolution/prompt_agents.yaml` | Modify | Replace global-only policy with explicit family/kind/contract policy entry; add command allowlist metadata and v2 registry version. | (general) | 2, 3 |
| 7 | `tests/test_evaluation_evidence.py` | Create | Unit tests for canonicalization, required identities, tampering, transcript/usage/cost unresolved states and legacy conversion. | (general) | 1 |
| 8 | `tests/test_evaluation_adapters.py` | Create | File/command adapter equivalence, allowlist, bounded output, invalid output and no-provider tests. | @sf-security-reviewer | 1, 3, 6 |
| 9 | `tests/test_decision_evolution.py` | Modify | Policy selection, one paired replay, v2 receipt fields/sequence, legacy read and promotion completeness regressions. | (general) | 2, 4, 6 |
| 10 | `tests/test_decision_replay.py` | Modify | Verify policy-supplied corpus minimum and preservation of current report/comparator behavior. | (general) | 5 |
| 11 | `tests/test_decision_evolution_benchmark.py` | Modify | Golden equivalence between fixture and authorized command bundles and exact baseline/candidate identities. | (general) | 3, 4, 6 |
| 12 | `tests/test_host_provider.py` | Modify | Assert host transcript usage and cost provenance are imported as unresolved when source/hash is absent or invalid. | (general) | 1, 4 |
| 13 | `evals/token_efficient/fixtures/evolution_evidence_bundles.yaml` | Create | Sanitized equivalent bundle fixtures for surrogate, recorded host, tampered and incomplete promotion cases. | (general) | 1, 2 |

**Total Files:** 13

## Agent Assignment Rationale

Agents were discovered by scanning `.claude/agents/**/*.md` and `agents/**/*.md`, then matching file purpose, security boundary and selected KB domains. No prompt-evolution or evaluation-policy specialist exists in either catalog, so core Python/evaluation files use `(general)` as the explicit fallback. `pyspark-code-reviewer` is not assigned because this feature does not modify PySpark jobs, plans or Spark execution. `sf-security-reviewer` is assigned only to the command adapter and its tests because the relevant boundary is subprocess authorization and output handling.

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @sf-security-reviewer | 3, 8 | Repository agent declares security review and has the right boundary for allowlisted command execution, bounded output and refusal paths. |
| (general) | 1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 13 | No discovered specialist owns offline Python evaluation/evidence contracts; build handles these directly using the design and project tests. |

## Code Patterns

### Pattern 1: Immutable canonical value object

Use this in `evidence.py` for identities and normalized references. The parser creates tuples and mappings that are copied before the object becomes immutable; digest excludes the derived `bundle_id`.

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: str
    ref: str
    sha256: str

    def canonical(self) -> dict[str, str]:
        return {"kind": self.kind, "ref": self.ref, "sha256": self.sha256}


def canonical_digest(value: dict[str, Any]) -> str:
    import hashlib
    import json

    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

### Pattern 2: Fail-closed structured validation

Use this at every adapter boundary. Missing values are named; no `dict.get(..., default)` may turn absent promotion evidence into valid evidence.

```python
class EvidenceBundleError(ValueError):
    """Named validation/refusal error for evaluation evidence."""


def require_text(raw: object, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise EvidenceBundleError(f"evidence_bundle_invalid:{field}")
    return raw.strip()


def require_hash(raw: object, field: str) -> str:
    value = require_text(raw, field)
    if len(value.removeprefix("sha256:")) != 64:
        raise EvidenceBundleError(f"evidence_bundle_invalid:{field}_sha256")
    return value
```

### Pattern 3: Authorized command adapter

The allowlist is resolved from repository configuration before subprocess creation. The command is an argv tuple; shell interpolation, executable search outside the allowlist and arbitrary environment inheritance are prohibited.

```python
import json
import subprocess
from pathlib import Path
from collections.abc import Mapping


def run_authorized_bundle(
    argv: tuple[str, ...],
    *,
    allowed_executable: str,
    input_path: Path,
    cwd: Path,
    timeout_seconds: float = 30.0,
) -> Mapping[str, object]:
    if not argv or Path(argv[0]).resolve() != Path(allowed_executable).resolve():
        raise EvidenceBundleError("external_command_not_authorized")
    completed = subprocess.run(
        (*argv, "--input", str(input_path)),
        cwd=cwd,
        env={"PATH": str(Path(argv[0]).resolve().parent)},
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise EvidenceBundleError(
            f"external_command_failed:exit_{completed.returncode}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise EvidenceBundleError("external_command_invalid_output:json") from exc
    if not isinstance(value, Mapping):
        raise EvidenceBundleError("external_command_invalid_output:object")
    return value
```

The final implementation must additionally bound stdout/stderr before parsing, reject path traversal in the input manifest and record command/executable digests in provenance. The snippet shows the dependency direction and `shell=False` requirement; it is not permission to execute an unconfigured command.

### Pattern 4: Separate metrics and unresolved denominators

```python
def normalize_usage(
    usage: Mapping[str, object] | None,
    *,
    transcript_sha256: str | None,
) -> tuple[dict[str, int] | None, bool, str | None]:
    if not isinstance(usage, Mapping) or not transcript_sha256:
        return None, True, "provider_transcript_absent"
    if usage.get("transcript_sha256") != transcript_sha256:
        return None, True, "usage_transcript_hash_mismatch"
    try:
        input_tokens = int(usage["input_tokens"])
        output_tokens = int(usage["output_tokens"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceBundleError("provider_tokens_invalid") from exc
    if input_tokens < 0 or output_tokens < 0:
        raise EvidenceBundleError("provider_tokens_invalid")
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }, False, None
```

## Data Flow

```text
1. Registry loads candidate and resolves exactly one policy by family/kind/contract.
   │
   ▼
2. File or authorized-command adapter reads an untrusted mapping and validates the
   EvaluationEvidenceBundle, including policy/candidate/suite/transcript hashes.
   │
   ▼
3. Offline evaluation either accepts the supplied reports or runs one paired replay
   with the accepted parent runner and candidate runner.
   │
   ▼
4. Existing comparator checks same suite, cells, labels, manifests and volume; the
   resolved policy derives quality/economy gates with unresolved denominators preserved.
   │
   ▼
5. EvolutionService writes a v2 content-addressed receipt with sequence, predecessor,
   bundle/policy identity and rollback target.
   │
   ▼
6. PromotionGate verifies current receipt, CI/benchmark/review refs, contract identity,
   corpus minimum, authorization and rollback; it either records promotion or returns
   a named refusal without changing the accepted candidate.
```

### Evaluation path distinction

There are two valid sources for reports:

1. **Surrogate/recorded host:** the Forge performs the deterministic local replay, using the canonical bundle to bind inputs and any host transcript metadata.
2. **Live external:** an authorized command returns already-produced baseline/candidate reports and provenance. The Forge verifies the returned bundle and derives/validates gates; it never calls a provider or assumes that command output is truthful without hashes.

Both paths end at the same `EvaluationEvidenceBundle` and `CandidateEvaluation` representation. The command path cannot bypass `compare_replay_benchmark` checks when reports are supplied; a missing or refused comparison keeps both gates false.

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Local fixture/bundle file | Filesystem read | Repository path confinement; no credentials |
| Authorized host command | Local subprocess with JSON stdout | Explicit registry allowlist and executable digest; no provider credentials inherited |
| Host transcript | Hash/reference in bundle; optional existing `HostEnvelope` validation | No network access; source hash required for usage |
| CI/benchmark/review artifacts | Evidence references with kind, URI/ref and SHA-256 | Caller supplies references; Forge verifies shape/digest and does not fetch network data |
| `.sparkforge/evolution/` | Content-addressed filesystem receipts | Local exclusive sequence lock |

No AWS, provider SDK, MCP SDK, HTTP client or new service is added. If a future integration needs network retrieval, it is outside this feature and requires a new explicit contract.

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Bundle canonicalization, strict fields, policy selection, transcript/cost states | `tests/test_evaluation_evidence.py`, `tests/test_decision_replay.py` | `pytest`, temporary paths | All required fields, all named refusal families, digest tampering |
| Adapter integration | File and authorized-command normalization, equivalent schemas, command allowlist and output bounds | `tests/test_evaluation_adapters.py`, `tests/test_decision_evolution_benchmark.py` | `pytest`, `tmp_path`, stub executable | AT-001, AT-002, AT-006, AT-012 |
| Evolution integration | One paired replay, policy binding, chained receipts, legacy reads and promotion gate | `tests/test_decision_evolution.py` | `pytest`, copied config/evals fixtures | AT-003–AT-011 |
| Host provenance regression | Invalid/missing transcript, tokens and cost basis remain unresolved | `tests/test_host_provider.py` | `pytest`, existing host fixtures | AT-007 and AT-012 |
| Static/import | Provider SDK and network imports absent from new/changed Forge modules | `tests/test_evaluation_adapters.py`, existing import guard | `ast`, `importlib`, repository import scan | AT-012; zero provider/network imports |
| Golden fixture | Equivalent bundle normalization and receipt schema | `evals/token_efficient/fixtures/evolution_evidence_bundles.yaml` | `pytest` | 100% equivalent fixture pairs and deterministic digests |

Acceptance mapping:

| Acceptance | Verification |
|------------|--------------|
| AT-001 | Valid fixture bundle normalizes, derives metrics/gates and writes a receipt containing candidate/policy ids. |
| AT-002 | Authorized command returns the golden bundle; normalized canonical mapping and digest equal the file adapter result. |
| AT-003 | Instrumented paired replay asserts one service benchmark call, one baseline runner cell and one candidate runner cell for every case/profile, with distinct identities. |
| AT-004 | Two policy entries resolve by family/kind/contract; receipt digest equals the selected entry digest. |
| AT-005 | Unknown key raises `evaluation_policy_missing:<key>` and writes no evaluation/promotion receipt. |
| AT-006 | Mutating candidate, suite, transcript or policy causes the precise digest mismatch refusal. |
| AT-007 | Missing/mismatched transcript yields `tokens_unresolved`; missing `cost_basis` yields unresolved cost and a required economy gate failure. |
| AT-008 | Existing v1 receipts parse as `legacy`; missing policy/bundle/sequence fields are reported and cannot satisfy v2 promotion. |
| AT-009 | Multiple v2 receipts select highest verified sequence; duplicate/gap/predecessor mismatch refuses lookup. |
| AT-010 | Complete bundle and typed CI/benchmark/review/contract/corpus/rollback evidence allow explicit promotion and record all identities. |
| AT-011 | Each missing promotion reference is named; accepted candidate and registry remain unchanged. |
| AT-012 | Import scan and command adapter tests prove provider-independent operation and unresolved token/cost semantics. |

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `evidence_bundle_invalid:<field>` | Fail fast at adapter boundary; return structured refusal and do not write receipt. | No |
| `evidence_bundle_digest_mismatch` | Reject bundle and preserve the supplied reason for audit; caller must regenerate it. | No |
| `evaluation_policy_missing:<key>` / `evaluation_policy_ambiguous:<key>` | Refuse evaluation and promotion; never use a global or default policy. | No |
| `transcript_hash_mismatch` / `provider_tokens_invalid` | Keep tokens unresolved, fail any gate that requires tokens, and record reason. | No |
| `cost_basis_absent` / `cost_value_absent` | Keep cost unresolved; exclude it from measured denominator and fail a required-cost gate. | No |
| `external_command_not_authorized` | Refuse before subprocess execution. | No |
| `external_command_failed:*` | Return named command failure; do not retry an external command automatically. | No |
| `external_command_invalid_output:*` | Refuse output after bounded capture; do not execute or coerce it. | No |
| `evolution_receipt_sequence_invalid:*` | Block current lookup/promotion until a valid chain is supplied. | No |
| `promotion_evidence_missing:<kind>` | Refuse promotion and list all missing kinds in stable order. | No |
| Existing legacy receipt without v2 fields | Read through compatibility facade with `legacy` status; never silently upgrade. | No |

Exceptions use the existing `EvolutionError` family at the service boundary and chain underlying `OSError`, `JSONDecodeError` or `TimeoutExpired` causes. Refusal messages are stable machine-readable prefixes followed by bounded field/reason values; transcript bodies and command output are not logged.

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `policy_version` | string | required for v2 | Version namespace for policy resolution and receipt binding. |
| `policies` | list[mapping] | required for v2 | Explicit family/kind/contract policies; exactly one must match. |
| `minimum_labeled_tasks` | int | required per policy | Corpus minimum consumed by new evaluation; no `CandidateEvaluation` literal fallback. |
| `external_commands` | list[mapping] | empty | Allowlisted command id, executable path/digest, timeout and output limit. Empty means command adapter refuses. |
| `receipt_schema_version` | int | `2` for new writes | Selects chained receipt fields; v1 remains read-only compatibility. |
| `require_promotion_evidence` | bool | `true` | Requires typed CI, benchmark and review refs in new promotion bundles. |

Path handling is repository-relative and confined to the declared repository/artifact root. Config parsing rejects unknown policy fields and duplicate resolution keys.

## Security Considerations

- Treat bundle mappings, transcript metadata, labels, report rows and command stdout as untrusted data. Validate structure and hashes; never import, evaluate or execute returned content.
- Invoke only configured commands with an exact executable identity, `shell=False`, fixed working directory, scrubbed environment, bounded argv/stdout/stderr and timeout. Do not inherit provider credentials.
- Keep raw transcripts and secrets out of receipts and fixtures. Persist hashes, source refs and bounded reason codes only.
- Constrain fixture, input-manifest and receipt paths to the repository or declared artifact root; reject traversal and symlink escapes where path resolution can detect them.
- Require independent typed evidence refs for CI, benchmark and review. `ci_verified: true` by itself cannot satisfy the new gate.
- Keep provider/network imports out of `sparkforge/evals`; enforce with an AST/import test. The core is offline even when a bundle declares `live_external`.
- Preserve unresolved states. A missing transcript, invalid usage hash or absent cost basis must never become zero, an empty success or a promotion proof.

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Structured bounded events: adapter, candidate digest, suite digest, policy digest, execution mode, refusal code and sequence; never transcript or command output. |
| Metrics | Existing quality/economy axes remain separate: status, evidence recall, false positives, route, payload bytes, provider tokens and cost status. No aggregate score is introduced. |
| Tracing | Bundle id → policy digest → comparison → receipt id → promotion receipt id; predecessor chain makes order inspectable. |
| Provenance | Candidate/parent, contract, suite/input manifest, adapter/command digest, transcript hashes, typed evidence refs and rollback target. |
| Refusals | Stable reason codes with `unresolved` fields for evidence not available to the core. |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-30 | design-agent | Initial design from validated DEFINE; selected canonical bundle, explicit policy resolution, single paired replay, authorized command boundary and chained receipt compatibility. |
| 1.1 | 2026-09-30 | ship-agent | Shipped and archived |

## Next Step

**Status:** ✅ Shipped and archived
