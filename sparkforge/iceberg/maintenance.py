"""Traduz ACHADO do catalogo em comando de manutencao Iceberg. Nao julga.

## O defeito que este modulo tinha, e por que ele importava

Ate 2026-09-02 `IcebergMaintenancePlanner.generate_plan` recebia CONTAGENS
cruas e decidia com limiares escritos aqui:

    small_files_count > 20
    delete_files_count > 5
    snapshots_count > 50
    retention_days = 7

Os quatro numeros nao tinham fonte, e os tres primeiros **duplicavam julgamento
que o catalogo ja faz**: `SF-ICE-001` (small files), `SF-ICE-002` (divida de
delete) e `SF-ICE-003` (churn de snapshot), cada um com `severity_by` medido e
`sources` citadas.

Duas verdades sobre a mesma pergunta, e a segunda sem fonte -- o mesmo defeito
que `EMR_MATRIX` literal em codigo tinha contra a matriz em YAML.

Havia um quarto, pior: `rewrite_manifests` era acrescentado INCONDICIONALMENTE.
Uma acao proposta sem evidencia nenhuma, num plano que o operador executaria.

## O que este modulo faz agora

Recebe os `Finding` que o motor produziu e traduz cada um na acao que o corrige.
O limiar mora na REGRA, com fonte; aqui mora a traducao para SQL.

Nao ha `if` sobre contagem. Se `SF-ICE-001` nao disparou, nao ha `rewrite_data_files`
no plano -- e a razao e a mesma pela qual o motor inteiro existe: quem decide se
ha defeito e o catalogo.

## `retention_days` nao tem default, e isso e decisao

Reter sete dias e escolha de negocio, nao medida. Um default aqui produziria um
comando `expire_snapshots` com uma janela que ninguem declarou, e ele apagaria
snapshots de verdade. A regra 10 do `CLAUDE.md` proibe manutencao destrutiva sem
escopo e retencao explicitos -- e sem `retention_days` a acao sai em
`refused`, com a medida que a destrava.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Qual regra do catalogo autoriza qual acao. A chave e o `rule_id`, e nao um
# limiar: o limiar mora na regra.
#
# UMA regra pode autorizar DUAS acoes -- `SF-ICE-002` (divida de delete) pede
# `rewrite_data_files` para materializar os deletes E `expire_snapshots` para
# que os arquivos antigos possam sair. Duas acoes, uma evidencia.
ACOES_POR_REGRA: dict[str, tuple[str, ...]] = {
    "SF-ICE-001": ("rewrite_data_files",),
    "SF-ICE-002": ("rewrite_data_files", "expire_snapshots"),
    "SF-ICE-003": ("expire_snapshots",),
}

# `rewrite_manifests` NAO esta no mapa, e a ausencia e o ponto.
#
# Nenhuma regra do catalogo julga o estado dos manifests hoje -- nao ha
# `SF-ICE-*` sobre `iceberg.manifests_summary`. Antes desta reescrita a acao
# saia INCONDICIONALMENTE, o que a tornava a unica do plano proposta sem
# evidencia nenhuma.
#
# Ela sai em `refused`, com a medida que a destravaria: uma regra que julgue
# manifests, sobre o kind que o extrator ja emite.
_SEM_REGRA = {
    "rewrite_manifests": (
        "veto V-ICE-1 em `rules/catalog/iceberg.yaml`: nenhuma regra julga o "
        "estado dos manifests porque NAO HA FONTE COM LIMIAR. O extrator ja "
        "emite `iceberg.manifests_summary` e a knowledge diz que manifests "
        "causam planejamento lento -- mas nao publica numero, e "
        "`avg_data_files_per_manifest < N` seria N inventado"
    ),
}

# Acao que APAGA. `expire_snapshots` remove snapshots e, com eles, a
# possibilidade de time travel para antes da janela. `remove_orphan_files`
# apagaria arquivos que o metadata nao referencia -- e um metadata corrompido
# faz todo arquivo parecer orfao.
DESTRUTIVAS = frozenset({"expire_snapshots", "remove_orphan_files"})


@dataclass
class MaintenanceAction:
    action_type: str
    sql_command: str
    target_table: str
    estimated_impact: str
    # Qual regra autorizou. Acao sem `authorized_by` nao deveria existir, e o
    # campo e obrigatorio para que a ausencia seja visivel em vez de suposta.
    authorized_by: str = ""
    risk_level: str = "reversible"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RefusedAction:
    """Acao que o plano NAO propoe, com a razao e o que a destravaria.

    Recusa que vira ausencia se le como "nada a fazer aqui". Listada, ela e a
    diferenca entre "nao ha o que compactar" e "ninguem sabe dizer".
    """

    action_type: str
    reason: str
    unblocked_by: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IcebergMaintenancePlan:
    table_name: str
    actions: list[MaintenanceAction]
    refused: list[RefusedAction] = field(default_factory=list)
    is_dry_run: bool = True
    approval_required: bool = True

    @property
    def has_destructive(self) -> bool:
        return any(a.action_type in DESTRUTIVAS for a in self.actions)

    def to_dict(self) -> dict[str, Any]:
        corpo = asdict(self)
        corpo["has_destructive"] = self.has_destructive
        return corpo


def _sql(acao: str, tabela: str, retention_days: int | None) -> str:
    if acao == "rewrite_data_files":
        return (
            f"CALL glue_catalog.system.rewrite_data_files(table => '{tabela}', "
            f"strategy => 'binpack', options => "
            f"map('target-file-size-bytes','536870912'))"
        )
    if acao == "expire_snapshots":
        return (
            f"CALL glue_catalog.system.expire_snapshots(table => '{tabela}', "
            f"older_than => TIMESTAMP 'current_timestamp - "
            f"INTERVAL {retention_days} DAYS')"
        )
    if acao == "rewrite_manifests":
        return f"CALL glue_catalog.system.rewrite_manifests(table => '{tabela}')"
    raise ValueError(f"acao sem SQL: {acao!r}")


def _impacto(acao: str, regras: tuple[str, ...], retention_days: int | None) -> str:
    """O impacto NOMEIA a regra que autorizou, e nao estima ganho.

    "Compacta 60 arquivos" seria numero do artefato repetido; "reduz o tempo de
    planejamento em X" seria estimativa sem medida. O que se pode afirmar e o
    que a regra afirmou, e por isso o texto a cita.
    """
    origem = ", ".join(regras)
    if acao == "rewrite_data_files":
        return f"Compacta data files. Autorizado por {origem}."
    if acao == "expire_snapshots":
        return (
            f"Expira snapshots com mais de {retention_days} dias. "
            f"Autorizado por {origem}. DESTRUTIVO: remove a possibilidade de "
            f"time travel para antes da janela."
        )
    return f"Autorizado por {origem}."


class IcebergMaintenancePlanner:
    """Traduz achados em plano de manutencao. NAO julga -- o catalogo julga."""

    def plan_from_findings(
        self,
        findings: list[Any],
        table_name: str,
        retention_days: int | None = None,
    ) -> IcebergMaintenancePlan:
        """O plano que os `findings` autorizam, e nada alem.

        `findings` sao os `Finding` que `judge` produziu. Se `SF-ICE-001` nao
        disparou, nao ha `rewrite_data_files` no plano.

        `retention_days` sem valor NAO vira default: `expire_snapshots` sai em
        `refused` com a medida que a destrava. Reter sete dias e escolha de
        negocio, e um default aqui apagaria snapshots por uma janela que ninguem
        declarou.
        """
        disparadas = {
            getattr(f, "rule_id", "") for f in findings
        } & set(ACOES_POR_REGRA)

        # Qual regra autoriza cada acao, para que o `authorized_by` cite todas.
        por_acao: dict[str, list[str]] = {}
        for regra in sorted(disparadas):
            for acao in ACOES_POR_REGRA[regra]:
                por_acao.setdefault(acao, []).append(regra)

        acoes: list[MaintenanceAction] = []
        recusadas: list[RefusedAction] = []

        for acao in sorted(por_acao):
            regras = tuple(por_acao[acao])
            if acao in DESTRUTIVAS and retention_days is None:
                recusadas.append(
                    RefusedAction(
                        action_type=acao,
                        reason=(
                            f"autorizada por {', '.join(regras)}, mas e DESTRUTIVA e "
                            f"nenhuma janela de retencao foi declarada"
                        ),
                        unblocked_by=(
                            "declare `retention_days`. Reter N dias e escolha de "
                            "negocio, nao medida -- um default aqui apagaria "
                            "snapshots por uma janela que ninguem escolheu"
                        ),
                    )
                )
                continue
            acoes.append(
                MaintenanceAction(
                    action_type=acao,
                    sql_command=_sql(acao, table_name, retention_days),
                    target_table=table_name,
                    estimated_impact=_impacto(acao, regras, retention_days),
                    authorized_by=", ".join(regras),
                    risk_level="destructive" if acao in DESTRUTIVAS else "reversible",
                )
            )

        for acao, razao in sorted(_SEM_REGRA.items()):
            recusadas.append(
                RefusedAction(
                    action_type=acao,
                    reason=razao,
                    unblocked_by=(
                        "escreva a regra que julgue essa condicao; o plano passa "
                        "a propor a acao quando ela disparar"
                    ),
                )
            )

        return IcebergMaintenancePlan(
            table_name=table_name,
            actions=acoes,
            refused=recusadas,
            is_dry_run=True,
            approval_required=True,
        )


__all__ = [
    "ACOES_POR_REGRA",
    "DESTRUTIVAS",
    "IcebergMaintenancePlan",
    "IcebergMaintenancePlanner",
    "MaintenanceAction",
    "RefusedAction",
]
