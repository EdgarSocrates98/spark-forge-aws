"""O bloco de plano que o `judge` publica.

Ele e CALCULADO e nao gravado: nenhuma entidade e criada, nenhum arquivo e
escrito. O registro auditavel continua sendo `sparkforge arbitrate`.
"""

from __future__ import annotations

import json
import pathlib

from sparkforge.agentic.executor.digest import plan_digest
from sparkforge.findings.models import Fact

_RUNTIME = {"glue": "5.0", "spark": "3.5.4"}


def _uniao(nome: str) -> tuple[list[dict], list[dict]]:
    """Facts do case = entrada (com id computado) + derivados. Ver §12.9 do
    spec do executor: alimentar com o subconjunto fabrica claim desancorada."""
    base = pathlib.Path("fixtures") / nome
    entrada = json.loads((base / "input" / "facts.json").read_text(encoding="utf-8"))
    entrada = entrada if isinstance(entrada, list) else entrada.get("facts", [])
    facts = []
    vistos = set()
    for f in entrada:
        obj = Fact(
            kind=f["kind"],
            subject=f.get("subject", {}),
            measures=f.get("measures", {}),
            attrs=f.get("attrs", {}),
        )
        if obj.id not in vistos:
            vistos.add(obj.id)
            facts.append(dict(f, id=obj.id))
    derivados = json.loads((base / "expected" / "facts.json").read_text(encoding="utf-8"))
    derivados = derivados if isinstance(derivados, list) else derivados.get("facts", [])
    for f in derivados:
        if f.get("id") not in vistos:
            vistos.add(f.get("id"))
            facts.append(f)
    findings = json.loads((base / "expected" / "findings.json").read_text(encoding="utf-8"))
    findings = findings if isinstance(findings, list) else findings.get("findings", [])
    return findings, facts


class TestFormaDoBloco:
    def test_bloco_tem_as_chaves_declaradas(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, standing = plan_digest(findings, facts, _RUNTIME)
        assert set(bloco) == {
            "scope", "order", "order_unresolved", "constraints",
            "contradictions", "objections", "unresolved", "persisted", "note",
        }

    def test_persisted_e_sempre_falso(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, _ = plan_digest(findings, facts, _RUNTIME)
        assert bloco["persisted"] is False
        assert "arbitrate" in bloco["note"]

    def test_caso_sem_nada_produz_listas_vazias_e_nao_bloco_ausente(self):
        bloco, standing = plan_digest([], [], _RUNTIME)
        assert bloco["order"] == []
        assert bloco["constraints"] == []
        assert bloco["contradictions"] == []
        assert bloco["objections"] == []
        assert bloco["unresolved"] == []
        assert standing == {}

    def test_scope_nomeia_o_conjunto_e_a_contagem(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, _ = plan_digest(findings, facts, _RUNTIME)
        assert str(len(findings)) in bloco["scope"]


class TestLastro:
    def test_standing_tem_uma_entrada_por_finding_com_rule_id(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        _, standing = plan_digest(findings, facts, _RUNTIME)
        assert set(standing) == {f["rule_id"] for f in findings}
        for valor in standing.values():
            assert set(valor) == {
                "value", "source_tier", "in_version_scope", "measures_present",
            }


class TestNaoGrava:
    def test_nenhum_arquivo_e_criado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        antes = set(tmp_path.rglob("*"))
        plan_digest(
            [{"rule_id": "SF-X-001", "evidence": [], "sources": [], "runtime_scope": {}}],
            [],
            _RUNTIME,
        )
        assert set(tmp_path.rglob("*")) == antes


class TestNaoPublicaScore:
    def test_bloco_nao_carrega_score(self):
        findings, facts = _uniao("timeout/timeout_com_spill_e_skew")
        bloco, standing = plan_digest(findings, facts, _RUNTIME)
        texto = json.dumps([bloco, standing])
        assert "score" not in texto
