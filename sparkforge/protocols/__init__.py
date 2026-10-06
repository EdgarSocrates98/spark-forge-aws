"""Public, provider-neutral interoperability protocols."""

from sparkforge.protocols.forge import (
    ForgeCapability,
    ForgeEvidenceBundle,
    ForgeHandoff,
    ForgeHealth,
    ForgeResult,
    ForgeTask,
    ForgeTaskStatus,
)

__all__ = [
    "ForgeCapability",
    "ForgeEvidenceBundle",
    "ForgeHandoff",
    "ForgeHealth",
    "ForgeResult",
    "ForgeTask",
    "ForgeTaskStatus",
]

# O adapter A2A fica FORA do import ansioso: `a2a_adapter` e experimental
# (§111-112) e quem o usa declara a intencao com `import
# sparkforge.protocols.a2a_adapter`, nunca `from protocols import ...`.
