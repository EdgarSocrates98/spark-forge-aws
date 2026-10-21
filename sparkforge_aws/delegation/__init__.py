"""Peer-to-peer delegation for spark-forge-aws (lf-0029).

Optional, governed delegation to sibling forges — ``data-sentinel-forge``
(runtime diagnostics) and ``forge-doctor-data`` (static analysis) — with
the same contract shapes the-forge defines natively
(``theforge/SpecialistCapability/v1``, ``theforge/SpecialistDelegation/v1``,
``theforge/EvidenceHandoff/v1``). sparkforge_aws never imports a sibling
forge; this package re-implements the semantics locally over the real CLI
surfaces (``data-sentinel …``, ``forge-doctor-data …``).

Absent specialist → explicit discovery state + the declared
``native-analysis`` fallback — never a simulated execution.
"""

from sparkforge_aws.delegation.contracts import (  # noqa: F401
    DELEGATION_FAILURES,
    DELEGATION_RISKS,
    DISCOVERY_STATES,
    EVIDENCE_HANDOFF_SCHEMA,
    SPECIALIST_CAPABILITY_SCHEMA,
    SPECIALIST_DELEGATION_SCHEMA,
    DeclaredCapability,
    DelegationChain,
    DelegationError,
    DelegationPlan,
    DelegationPolicy,
    DelegationRefusal,
    EvidenceHandoff,
    EvidenceRef,
    ExecResult,
    HandoffError,
    HandoffFinding,
    PeerDiscovery,
    PeerDiscoveryReport,
    SpecialistCapability,
    SpecialistDelegation,
    SpecialistIdentity,
    SpecialistRef,
)
from sparkforge_aws.delegation.discovery import (  # noqa: F401
    PeerSpec,
    discover_peer,
    discover_peers,
)
from sparkforge_aws.delegation.execute import run_governed  # noqa: F401
from sparkforge_aws.delegation.governance import (  # noqa: F401
    admit_hop,
    bound_handoff,
    capability_risks,
    gate_capability,
    idempotency_key,
    may_retry,
    new_correlation_id,
    redact_handoff,
    resolve_capability_argv,
    seal_handoff,
    start_chain,
    verify_integrity,
)
from sparkforge_aws.delegation.peers import (  # noqa: F401
    DOCTOR_DATA,
    PEERS,
    SENTINEL,
    consumer_delegation,
)
from sparkforge_aws.delegation.router import plan_delegation  # noqa: F401
from sparkforge_aws.delegation.run import (  # noqa: F401
    delegate,
    discover,
    handoffs,
    plan,
)
