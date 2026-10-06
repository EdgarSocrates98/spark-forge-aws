#!/usr/bin/env python3
"""Upgrade every canonical skill with the shared quality/eval contract.

This is a deterministic repository maintenance tool. It does not call a model,
AWS, or the network. `skills/` remains canonical; run `sync_skills.py` after it.
"""

# Long template literals below are intentionally preserved as generated skill
# content; line wrapping them would change the emitted artifacts.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MARKER = "## Contrato de qualidade SparkForge (v1)"

COMMON_REFS = [
    "../_shared/references/evidence-first.md",
    "../_shared/references/evaluation-contract.md",
    "../_shared/references/operational-safety.md",
]

DOMAIN_REFS: dict[str, list[str]] = {
    "aws": ["../../knowledge/cross-service-constraints.md", "../../knowledge/offline-policy.md"],
    "spark": [
        "../../knowledge/spark/execution-model.md",
        "../../knowledge/performance-principles.md",
    ],
    "iceberg": [
        "../../knowledge/storage/iceberg-performance.md",
        "../../knowledge/storage/iceberg-catalog.md",
    ],
    "lakeformation": [
        "../../knowledge/lakeformation/architecture.md",
        "../../knowledge/glue/lakeformation-fgac.md",
    ],
    "sdd": ["../../docs/sdd/README.md", "../../docs/sdd/CONTRATO.md"],
    "terraform": [
        "../../knowledge/terraform-data-platform.md",
        "../../knowledge/domain-tool-matrix.md",
    ],
    "emr": [
        "../../knowledge/emr/runtime-matrix.md",
        "../../knowledge/emr/cluster-configuration.md",
    ],
    "graph": ["../../knowledge/graph/graphframes-api.md", "../../knowledge/graph/availability.md"],
    "quality": [
        "../../knowledge/dq/validation-frameworks.md",
        "../../knowledge/data-contracts-schema-evolution.md",
    ],
    "architecture": [
        "../../knowledge/data-platform-architecture.md",
        "../../knowledge/cross-service-constraints.md",
    ],
}

FALLBACK_VERBS = {
    "analyze-functional-rules": ["sparkforge-aws analyze data-quality"],
    "aws-database": ["sparkforge-aws rules lookup"],
    "aws-iam": ["sparkforge-aws collect iam-access"],
    "aws-messaging-and-streaming": ["sparkforge-aws rules lookup"],
    "aws-security": ["sparkforge-aws collect iam-access"],
    "aws-serverless": ["sparkforge-aws rules lookup"],
    "aws-storage": ["sparkforge-aws rules lookup"],
    "design-data-architecture": ["sparkforge-aws next-step"],
    "design-s3-data-lake": ["sparkforge-aws next-step"],
    "review-terraform-data-platform": ["sparkforge-aws analyze terraform"],
    "provision-s3-tables-table": ["sparkforge-aws rules lookup"],
    "harden-s3-bucket": ["sparkforge-aws collect iam-access"],
    "tool-specialist-routing": ["sparkforge-aws next-step"],
}

FOCUS: dict[str, str] = {
    "analyze-batch-loop": "laços de processamento, actions, writes e recomputação de DAG",
    "analyze-functional-rules": "regras funcionais, contratos, estados e critérios de aceite",
    "analyze-library-call-graph": "grafo de chamadas e trabalho Spark alcançável",
    "analyze-spark-plan": "plano físico Spark, scans, joins, exchanges e AQE",
    "analyze-spark-ui": "event log Spark, stages, skew, spill, GC e subparalelismo",
    "benchmark-pyspark-job": "comparação medida entre runs PySpark antes/depois",
    "compare-releases": "compatibilidade e diferenças entre releases e runtimes",
    "design-data-architecture": "arquitetura de dados, contratos, ownership e operação",
    "design-incremental-processing": "processamento incremental, latest-per-key e Iceberg",
    "design-s3-data-lake": "layout de data lake S3, camadas e governança",
    "diagnose-data-skew": "skew de dados, distribuição de tasks e custo de shuffle",
    "diagnose-oom": "OOM, heap, GC, spill e limites do event log",
    "glue-incremental-performance-architect": "arquitetura de performance para Glue full/incremental",
    "optimize-iceberg-table": "metadados, manifests, data files e manutenção Iceberg",
    "optimize-latest-per-key": "seleção latest-per-key e custo de window/join",
    "optimize-parquet-layout": "layout Parquet, arquivos, partições e pruning",
    "optimize-pyspark-code": "reescrita de código PySpark e plano de execução",
    "optimize-variable-volume-job": "capacidade e comportamento de jobs com volume variável",
    "review-data-validation": "validação de dados, consequência e custo da checagem",
    "review-pyspark-pr": "revisão de PR PySpark com fatos, plano e call graph",
    "sparkforge-aws-diagnose": "triagem inicial e roteamento determinístico de casos SparkForge",
    "tune-glue-job": "capacidade e configuração de jobs Glue após gargalo comprovado",
    "spark4-compatibility": "compatibilidade Spark 4, Glue e dependências",
    "lakeformation-architecture": "arquitetura Lake Formation, FGAC, FTA e autorização",
    "lakeformation-fgac-guard": "guarda de migração FGAC/FTA e evidência de acesso",
    "diagnose-lakeformation-access": "diagnóstico de autorização Lake Formation/IAM",
    "iceberg-v3-readiness": "prontidão Iceberg v3 por runtime, engine e consumidores",
    "aws-billing-and-cost-management": "custo AWS, DPUSeconds, provenance e limites da medição",
    "aws-database": "seleção e operação segura de serviços AWS de banco",
    "aws-iam": "IAM, simulação de política e camadas de negação",
    "aws-messaging-and-streaming": "mensageria, streaming, retries e entrega",
    "aws-observability": "observabilidade AWS, métricas, logs e sinais de execução",
    "aws-sdk-python-usage": "uso seguro e paginado de SDK AWS para Python",
    "aws-security": "segurança AWS, threat model e controles verificáveis",
    "aws-serverless": "arquitetura serverless AWS e restrições operacionais",
    "aws-storage": "armazenamento AWS, durabilidade, custo e governança",
    "harden-s3-bucket": "hardening de bucket S3 e policy segura",
    "provision-s3-tables-table": "provisionamento de S3 Tables com escopo e rollback",
    "review-emr-cluster": "revisão de cluster EMR e EMR Serverless",
    "review-emr-eks": "revisão de workloads EMR on EKS",
    "review-glue-terraform": "revisão de Terraform para jobs Glue",
    "review-terraform-data-platform": "revisão de Terraform da plataforma de dados",
    "migrate-glue-6": "migração Glue 6, dependências e compatibilidade",
    "sdd-build": "execução rastreável das tarefas de build SDD",
    "sdd-define": "critérios de aceite, hipótese e métricas do SDD",
    "sdd-design": "manifesto, decisões e rollback do design SDD",
    "sdd-explore": "exploração de alternativas e escolha explícita",
    "sdd-plan": "plano executável com testes e cobertura SDD",
    "sdd-ship": "fechamento, gates, evidência e rollback do SDD",
    "run-debate": "debate determinístico, reextração e fechamento por evidência",
    "propose-change-pr": "pacote de mudança, validação e PR",
    "tool-specialist-routing": "roteamento por evidência para especialista e verbo",
}


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("skill sem frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("frontmatter sem fechamento")
    return text[: end + 4], text[end + 4 :]


def normalize_frontmatter(front: str) -> str:
    """Quote description as YAML-safe UTF-8 and remove forbidden placeholders."""
    lines = front.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line.partition(":")[2].strip()
        try:
            parsed = yaml.safe_load(value)
            if isinstance(parsed, str):
                value = parsed
        except yaml.YAMLError:
            pass
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        # Agent skill frontmatter rejects angle-bracket placeholders. Keep the
        # command meaning while making descriptions portable across validators.
        value = re.sub(r"<([^<>]+)>", r"\1", value)
        if len(value) > 1024:
            value = value[:1021].rstrip() + "..."
        newline = "\n" if line.endswith("\n") else ""
        lines[index] = f"description: {json.dumps(value, ensure_ascii=False)}{newline}"
        break
    return "".join(lines)


def primary_verbs(name: str, body: str) -> list[str]:
    found: list[str] = []
    for verb in re.findall(r"sparkforge-aws [a-z][a-z0-9-]*(?: [a-z][a-z0-9-]*)?", body):
        if verb not in found:
            found.append(verb)
    return found[:3] or FALLBACK_VERBS.get(name, ["sparkforge-aws next-step"])


def domain_refs(name: str) -> list[str]:
    keys = []
    if name.startswith("aws-") or name in {"harden-s3-bucket", "provision-s3-tables-table"}:
        keys.append("aws")
    if any(
        token in name for token in ("spark", "pyspark", "batch", "oom", "skew", "variable-volume")
    ):
        keys.append("spark")
    if "iceberg" in name or "parquet" in name:
        keys.append("iceberg")
    if "lakeformation" in name:
        keys.append("lakeformation")
    if name.startswith("sdd-"):
        keys.append("sdd")
    if "terraform" in name:
        keys.append("terraform")
    if "emr" in name:
        keys.append("emr")
    if "graph" in name or "call-graph" in name:
        keys.append("graph")
    if "data-validation" in name or "functional-rules" in name:
        keys.append("quality")
    if "architecture" in name or name.startswith("design-"):
        keys.append("architecture")
    result: list[str] = []
    for key in keys:
        for path in DOMAIN_REFS[key]:
            if path not in result:
                result.append(path)
    return result[:3]


def metadata_block(name: str, verbs: list[str], refs: list[str]) -> str:
    data = {
        "sparkforge_contract": "v1",
        "evals": "evals/evals.json",
        "references": ["references/README.md", *refs],
        "scripts": ["scripts/validate_evidence.py"],
        "primary_verbs": verbs,
    }
    return yaml.safe_dump({"metadata": data}, allow_unicode=True, sort_keys=False)


def contract_section(name: str, verbs: list[str], refs: list[str]) -> str:
    focus = FOCUS.get(name, name.replace("-", " "))
    verb_text = ", ".join(f"`{v}`" for v in verbs)
    ref_text = ", ".join(f"`{r}`" for r in refs)
    return f"""\n\n{MARKER}\n\nEsta skill trata **{focus}**. Contrato comum, sem substituir o procedimento específico acima:\n\n- **Entrada mínima:** artefato, runtime/contexto declarado e pergunta operacional; se faltar, registre o `*.unresolved` correspondente.\n- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou origem de medição; aplique regra por `rule_id` e versão, nunca por memória.\n- **Verbos primários:** {verb_text}. Use-os na ordem indicada pela skill e conserve saída estruturada.\n- **Saída:** fatos, findings, hipóteses e recomendações separados. Recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`, `proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e `rollback`.\n- **Validação:** rode o teste/verbos listados, valide dados depois da mudança e diga o que ainda não foi medido. Ausência de finding significa apenas que nenhum proxy disparou.\n- **Rollback e segurança:** não execute escrita destrutiva por inferência; peça escopo explícito e entregue rollback reversível. AWS operacional mantém `denied_by`, conta, recurso e camada de policy.\n- **Referências e eval:** {ref_text}; casos realistas em `evals/evals.json`; o script `scripts/validate_evidence.py` verifica o envelope antes do handoff.\n"""


def references_readme(name: str, refs: list[str]) -> str:
    focus = FOCUS.get(name, name.replace("-", " "))
    links = [
        "../../_shared/references/evidence-first.md",
        "../../_shared/references/evaluation-contract.md",
        "../../_shared/references/operational-safety.md",
    ]
    links.extend(path.replace("../../", "../../../") for path in refs if path not in COMMON_REFS)
    lines = [
        f"# Referências — {name}",
        "",
        f"Escopo: {focus}.",
        "",
        "Referências verificáveis no repositório:",
        "",
    ]
    lines.extend(f"- `{path}`" for path in links)
    lines += [
        "",
        "A auditoria `python scripts/audit_skills.py --strict` confere todos os caminhos.",
        "",
    ]
    return "\n".join(lines)


def evals(name: str, verbs: list[str], refs: list[str]) -> dict:
    focus = FOCUS.get(name, name.replace("-", " "))
    primary = verbs[0]
    common = [
        f"The response uses the primary evidence path `{primary}` or explains why the available artifact cannot support it.",
        "The response separates anchored facts from findings and cites a fact_id or source path.",
        "The response reports unresolved evidence instead of guessing missing runtime, cost, capacity, or authorization facts.",
        "The response includes validation and rollback steps; any proposed change uses the mandatory recommendation fields.",
        "The response cites at least one local reference and preserves version or provenance constraints.",
    ]
    return {
        "skill_name": name,
        "version": "1.0",
        "evals": [
            {
                "id": 1,
                "prompt": f"Use the {name} skill to review a case about {focus}. The supplied artifact is partial; produce an evidence-first handoff and do not invent measurements.",
                "expected_output": f"A structured handoff for {focus} using {primary}, with anchored facts, unresolved gaps, recommendation schema when applicable, validation, and rollback.",
                "files": [],
                "expectations": common,
            },
            {
                "id": 2,
                "prompt": f"Apply {name} to a before/after change involving {focus}. Decide what can be concluded, what must be measured, and how an operator can safely revert.",
                "expected_output": "A bounded decision that distinguishes observed result from hypothesis, records provenance, and names the next deterministic validation command.",
                "files": [],
                "expectations": common
                + [
                    "The response does not claim a performance or cost gain without a same-case measurement."
                ],
            },
        ],
    }


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def generated_files(skill_dir: Path) -> dict[Path, str]:
    name = skill_dir.name
    skill_path = skill_dir / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    front, body = split_frontmatter(text)
    front = normalize_frontmatter(front)
    verbs = primary_verbs(name, text)
    refs = [*COMMON_REFS, *domain_refs(name)]
    if "metadata:" not in front:
        metadata = metadata_block(name, verbs, refs)
        front = front[:-4] + "\n" + metadata + "---"
    if MARKER not in body:
        body += contract_section(name, verbs, refs)
    generated: dict[Path, str] = {skill_path: front + body}

    eval_path = skill_dir / "evals" / "evals.json"
    generated[eval_path] = json.dumps(evals(name, verbs, refs), ensure_ascii=False, indent=2) + "\n"
    ref_path = skill_dir / "references" / "README.md"
    generated[ref_path] = references_readme(name, refs)
    script_path = skill_dir / "scripts" / "validate_evidence.py"
    wrapper = f'''#!/usr/bin/env python3\n"""Validate {name} recommendation envelope offline."""\nfrom pathlib import Path\nimport sys\n\n_SHARED = Path(__file__).resolve().parents[2] / "_shared" / "scripts"\nsys.path.insert(0, str(_SHARED))\nfrom validate_skill_context import main  # noqa: E402\n\nif __name__ == "__main__":\n    raise SystemExit(main(default_skill="{name}"))\n'''
    generated[script_path] = wrapper
    return generated


def upgrade_skill(skill_dir: Path, *, write: bool) -> int:
    changed = 0
    for path, content in generated_files(skill_dir).items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        changed += 1
        if write:
            write_if_changed(path, content)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()
    total = 0
    for skill_dir in sorted(
        p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
    ):
        if args.check:
            changed = upgrade_skill(skill_dir, write=False)
            if changed:
                raise SystemExit(f"drift detected for {skill_dir.name}; run without --check")
        else:
            total += upgrade_skill(skill_dir, write=True)
    print(
        f"{len([p for p in SKILLS.iterdir() if (p / 'SKILL.md').exists()])} skills processadas; {total} arquivos atualizados"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
