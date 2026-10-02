"""Offline Forge Lab / Digital Twin and product contracts."""

from sparkforge.lab.contract import (
    FIDELITY_NAMES,
    FIDELITY_TIERS,
    LAB_MODES,
    LAB_PROFILES,
    RESULT_CLASSIFICATIONS,
    Fidelity,
    LabContractError,
    LabResourceContract,
    VersionRegistry,
    load_resource_contract,
    load_version_registry,
)
from sparkforge.lab.scenario import (
    ACTION_KINDS,
    ScenarioAction,
    ScenarioSpec,
    ScenarioSuite,
    load_scenario_suite,
)
from sparkforge.lab.compatibility import (
    BlastRadiusComparison,
    EquivalencePlan,
    build_equivalence_plan,
    compare_blast_radius,
)
from sparkforge.lab.doctor import DoctorReport, run_doctor
from sparkforge.lab.evidence import (
    capture_artifact,
    compare_oracle,
    create_run,
    finalize_receipt,
    promote_fixture,
    verify_receipt,
)
from sparkforge.lab.oracle import ExpectedOracle, OracleResult
from sparkforge.lab.runtime import RuntimePlan, build_lifecycle_command, build_runtime_plan, guard_mutation

from sparkforge.lab.spec import (
    FORGE_LAB_COMPONENTS,
    FORGE_LAB_SCENARIOS,
    ForgeLabError,
    ForgeLabSpec,
    analyze_forge_lab,
    load_forge_lab,
)

__all__ = [
    "ACTION_KINDS",
    "BlastRadiusComparison",
    "DoctorReport",
    "EquivalencePlan",
    "ExpectedOracle",
    "FIDELITY_NAMES",
    "FIDELITY_TIERS",
    "FORGE_LAB_COMPONENTS",
    "FORGE_LAB_SCENARIOS",
    "ForgeLabError",
    "ForgeLabSpec",
    "LAB_MODES",
    "LAB_PROFILES",
    "RESULT_CLASSIFICATIONS",
    "Fidelity",
    "LabContractError",
    "LabResourceContract",
    "ScenarioAction",
    "ScenarioSpec",
    "ScenarioSuite",
    "VersionRegistry",
    "OracleResult",
    "RuntimePlan",
    "analyze_forge_lab",
    "build_equivalence_plan",
    "build_lifecycle_command",
    "build_runtime_plan",
    "capture_artifact",
    "compare_blast_radius",
    "compare_oracle",
    "create_run",
    "finalize_receipt",
    "guard_mutation",
    "load_forge_lab",
    "load_resource_contract",
    "load_scenario_suite",
    "load_version_registry",
    "promote_fixture",
    "run_doctor",
    "verify_receipt",
]
