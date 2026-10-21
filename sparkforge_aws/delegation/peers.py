"""Declared specialist peers of spark-forge-aws (lf-0029).

The two optional specialists this forge may delegate to, and the real CLI
verbs each delegation binds to — inventoried from the audit
(``forge-cli/docs/integration/audit-data.md`` §2.1/§3.1), never invented:

- **data-sentinel-forge** (``data-sentinel``) — runtime diagnostics:
  ``analyze --file`` (driver/executor logs: OOM, skew, shuffle, spill),
  ``spark explain``, ``sql analyze``, ``lakehouse metadata`` (Iceberg
  runtime), ``emr analyze``, and the AWS-cloud reads ``glue inspect`` /
  ``glue runs`` / ``glue diagnose``. Cloud verbs are ``external_read`` +
  cost-undeclared → the gate requires explicit ``EXTERNAL_READ`` **and**
  ``COST_BEARING`` authorization (``--authorize``); ``--profile``/``--region``
  travel as argv flags so AWS auth resolves inside the delegatee's own
  credential chain, never through forwarded env.
- **forge-doctor-data** (``forge-doctor-data``) — static analysis:
  ``scan <path> --format agent`` covering PySpark review, antipatterns,
  config, dependency hygiene, security, environment diagnostics, structure
  and quality gates.

Everything declared is LOCAL_READ unless it reaches an AWS API. No
capability here mutates anything — sentinel and doctor are read-only by
construction (``read_only_default: true`` in both ``forge.agentic.json``),
and this forge never declares a write-capable entrypoint.
"""

from __future__ import annotations

from sparkforge_aws.delegation.contracts import (
    DeclaredCapability,
    DelegationPolicy,
    SpecialistDelegation,
    SpecialistRef,
)
from sparkforge_aws.delegation.discovery import PeerSpec

__all__ = [
    "SENTINEL",
    "DOCTOR_DATA",
    "PEERS",
    "PEER_BY_PROVIDER",
    "consumer_delegation",
    "CONSUMER_PROVIDER",
    "HANDOFFS_DIR_NAME",
]

CONSUMER_PROVIDER = "spark-forge-aws"
HANDOFFS_DIR_NAME = "delegation/handoffs"

# ---------------------------------------------------------------------------
# data-sentinel-forge — runtime diagnostics
#
# Verb inventory pinned to data-sentinel-forge cli/__init__.py:
#   analyze --file/-f --platform/-p --json --no-persist    (log or --sql)
#   spark explain --file/-f --json --no-persist
#   sql analyze --file/-f --json --no-persist
#   lakehouse metadata --file/-f --platform --json --no-persist
#   emr analyze --file/-f --platform ec2|serverless|eks --json
#   glue inspect --job --profile --region --json
#   glue runs --job --limit --profile --region --json
#   glue diagnose --job --run-id --log-group --profile --region --json --no-persist
#   capabilities --descriptors
#   import doctor-bundle --file
# ---------------------------------------------------------------------------

SENTINEL = PeerSpec(
    provider="data-sentinel-forge",
    cli="data-sentinel",
    dist_names=("data-sentinel", "data-sentinel-forge", "data_sentinel"),
    capabilities_probe=("capabilities", "--descriptors"),
    capabilities=(
        DeclaredCapability(
            id="sentinel.log-analysis",
            description=(
                "Runtime log diagnostics — driver/executor logs: OOM, data "
                "skew, shuffle, spill, executor loss, timeouts"
            ),
            intents=["runtime-diagnostics", "spark-logs", "oom",
                     "data-skew", "shuffle", "spill"],
            entrypoint=["{cli}", "analyze", "--file", "{target}",
                        "--platform", "{platform}", "--json", "--no-persist"],
            execution_mode="local",
            risk="read_only",
            external_cost="none",
            timeout_s=300,
            discovery_mode="probe",
            verification_mode="handshake",
        ),
        DeclaredCapability(
            id="sentinel.spark-explain",
            description="Physical Spark plan analysis (EXPLAIN output)",
            intents=["runtime-diagnostics", "spark-explain", "physical-plan"],
            entrypoint=["{cli}", "spark", "explain", "--file", "{target}",
                        "--json", "--no-persist"],
            execution_mode="local",
            risk="read_only",
            external_cost="none",
            timeout_s=300,
            discovery_mode="probe",
            verification_mode="handshake",
        ),
        DeclaredCapability(
            id="sentinel.sql-analyze",
            description="Static analysis of heavy SQL (joins, antipatterns)",
            intents=["runtime-diagnostics", "sql-analysis", "heavy-sql"],
            entrypoint=["{cli}", "sql", "analyze", "--file", "{target}",
                        "--json", "--no-persist"],
            execution_mode="local",
            risk="read_only",
            external_cost="none",
            timeout_s=300,
            discovery_mode="probe",
            verification_mode="handshake",
        ),
        DeclaredCapability(
            id="sentinel.lakehouse-metadata",
            description=(
                "Iceberg metadata analysis (exported metadata.json — table "
                "layout, snapshots, runtime issues)"
            ),
            intents=["runtime-diagnostics", "iceberg-metadata",
                     "lakehouse", "iceberg"],
            entrypoint=["{cli}", "lakehouse", "metadata", "--file", "{target}",
                        "--platform", "{platform}", "--json", "--no-persist"],
            execution_mode="local",
            risk="read_only",
            external_cost="none",
            timeout_s=300,
            discovery_mode="probe",
            verification_mode="handshake",
        ),
        DeclaredCapability(
            id="sentinel.emr-analyze",
            description="EMR execution diagnostics (exported EMR artifacts)",
            intents=["runtime-diagnostics", "emr-diagnostics", "emr"],
            entrypoint=["{cli}", "emr", "analyze", "--file", "{target}",
                        "--platform", "{platform}", "--json"],
            execution_mode="local",
            risk="read_only",
            external_cost="none",
            timeout_s=300,
            discovery_mode="probe",
            verification_mode="handshake",
        ),
        DeclaredCapability(
            id="sentinel.glue-inspect",
            description=(
                "Read-only AWS Glue job metadata inspection (GetJob)"
            ),
            intents=["runtime-diagnostics", "glue-diagnostics", "glue"],
            entrypoint=["{cli}", "glue", "inspect", "--job", "{job}",
                        "--profile", "{profile}", "--region", "{region}",
                        "--json"],
            execution_mode="remote",
            risk="external_read",
            network=True,
            external_cost="none",  # control-plane metadata read
            timeout_s=60,
            permissions=["aws:glue:GetJob"],
            discovery_mode="probe",
            verification_mode="handshake",
        ),
        DeclaredCapability(
            id="sentinel.glue-runs",
            description=(
                "Read-only AWS Glue run history (GetJobRuns — failures, "
                "slow runs, error messages)"
            ),
            intents=["runtime-diagnostics", "glue-diagnostics", "glue",
                     "glue-failures", "slow-runs"],
            entrypoint=["{cli}", "glue", "runs", "--job", "{job}",
                        "--profile", "{profile}", "--region", "{region}",
                        "--json"],
            execution_mode="remote",
            risk="external_read",
            network=True,
            external_cost="none",
            timeout_s=60,
            permissions=["aws:glue:GetJobRuns"],
            discovery_mode="probe",
            verification_mode="handshake",
        ),
        DeclaredCapability(
            id="sentinel.glue-diagnose",
            description=(
                "Glue job run diagnosis: metadata + CloudWatch log events "
                "orchestrated into a DiagnosticReport (OOM, skew, shuffle, "
                "spill, failures, slow runs)"
            ),
            intents=["runtime-diagnostics", "glue-diagnostics", "glue",
                     "glue-failures", "oom", "data-skew", "spill",
                     "runtime-logs"],
            entrypoint=["{cli}", "glue", "diagnose", "--job", "{job}",
                        "--run-id", "{run_id}", "--profile", "{profile}",
                        "--region", "{region}", "--json", "--no-persist"],
            execution_mode="remote",
            risk="external_read",
            network=True,
            # Log retrieval volume is metered by CloudWatch — undeclared is
            # never "free", so COST_BEARING joins EXTERNAL_READ on the gate.
            external_cost="unknown",
            timeout_s=300,
            permissions=["aws:glue:GetJob", "aws:glue:GetJobRun",
                         "aws:glue:GetJobRuns", "aws:logs:GetLogEvents"],
            discovery_mode="probe",
            verification_mode="handshake",
        ),
    ),
    expected_descriptor_ids=(),
)

# ---------------------------------------------------------------------------
# forge-doctor-data — static analysis
#
# Verb surface pinned to forge-doctor-data cli/scan.py + cli/common.py:
#   scan [PATH] --format text|json|html|sarif|agent --check CATEGORY
#       --quiet --fail-on error|warning --no-plugins --files --output
#   --version (callback), capabilities list|explain|graph
# The `agent` format emits scan-json@3.0: {tool, version, schema_version,
# project, summary, findings: [{id, sev, loc, fp}]}.
# ---------------------------------------------------------------------------

DOCTOR_DATA = PeerSpec(
    provider="forge-doctor-data",
    cli="forge-doctor-data",
    dist_names=("forge-doctor-data", "forge_doctor_data"),
    capabilities_probe=None,  # no descriptor verb; version probe is the handshake
    capabilities=(
        DeclaredCapability(
            id="doctor.scan-project",
            description=(
                "Static project scan — PySpark review, antipatterns, config, "
                "dependency hygiene, security, environment diagnostics, "
                "structure and quality gates (scan-json@3.0 agent output)"
            ),
            intents=["static-analysis", "pyspark-review", "antipatterns",
                     "config", "deps-hygiene", "security",
                     "env-diagnostics", "structure", "quality-gates"],
            entrypoint=["{cli}", "scan", "{target}", "--format", "agent",
                        "--check", "{check}"],
            execution_mode="local",
            risk="read_only",
            external_cost="none",
            timeout_s=300,
            discovery_mode="probe",
            verification_mode="handshake",
        ),
    ),
)

PEERS: tuple[PeerSpec, ...] = (SENTINEL, DOCTOR_DATA)
PEER_BY_PROVIDER: dict[str, PeerSpec] = {p.provider: p for p in PEERS}

# Intents the consumer declares it may need. They are the routing surface of
# ``router.plan_delegation`` — a task names them; the router matches tokens.
_SENTINEL_INTENTS = [
    "runtime-diagnostics",
    "spark-logs",
    "oom",
    "data-skew",
    "shuffle",
    "spill",
    "glue-diagnostics",
    "glue",
    "glue-failures",
    "slow-runs",
    "runtime-logs",
    "emr-diagnostics",
    "emr",
    "iceberg-metadata",
    "lakehouse",
    "iceberg",
    "sql-analysis",
    "heavy-sql",
    "spark-explain",
    "physical-plan",
]

_DOCTOR_INTENTS = [
    "static-analysis",
    "pyspark-review",
    "antipatterns",
    "config",
    "deps-hygiene",
    "security",
    "env-diagnostics",
    "structure",
    "quality-gates",
]


def consumer_delegation() -> SpecialistDelegation:
    """The ``theforge/SpecialistDelegation/v1`` declaration of spark-forge-aws.

    Both specialists are ``optional`` — absent peers degrade to the named
    fallback (``native-analysis``: this forge's own extractors/judges),
    never to a simulated execution.
    """
    return SpecialistDelegation(
        consumer=CONSUMER_PROVIDER,
        specialists=[
            SpecialistRef(
                provider=SENTINEL.provider,
                optional=True,
                intents=list(_SENTINEL_INTENTS),
            ),
            SpecialistRef(
                provider=DOCTOR_DATA.provider,
                optional=True,
                intents=list(_DOCTOR_INTENTS),
            ),
        ],
        policy=DelegationPolicy(
            discovery="runtime",
            execution="governed",
            preserve_evidence=True,
            fallback="native-analysis",
        ),
    )
