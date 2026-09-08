"""Autoridade da fonte e vigencia do escopo, para o executor agentico.

Duas perguntas separadas, e a separacao e o ponto:

- `tier_for_url` responde SO o tier -- quanto pesa a fonte por si.
- `in_scope` responde a vigencia -- se a fonte fala da versao que o case roda.

Uma T1 fora da versao alvo tem autoridade e NAO sustenta a claim. E a mesma
distincao que `sparkforge.agentic.evidence` ja faz entre
`has_sufficient_authority` (so o tier) e `has_fresh_in_scope` (tier mais
verificacao): estas duas funcoes sao os insumos dela.

O mapeamento host -> tier mora em `knowledge/source_authority.yaml`, nao aqui.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from sparkforge.agentic.models import EvidenceAuthority

# Piso usado quando o mapa nao declara `default`. T4 nunca promove um host
# desconhecido a documentacao oficial, e nunca o rebaixa a conjectura -- T5 e
# T6 sao afirmacoes sobre o CONTEUDO ("veio de LLM", "e opiniao"), e o host
# nao autoriza nenhuma das duas.
_FALLBACK_DEFAULT = EvidenceAuthority.T4_RECOGNIZED_AUTHORITY


def _authority_map_path() -> Path:
    """Caminho default de `knowledge/source_authority.yaml`.

    Mesma resolucao que `sparkforge.rules.loader` usa para o catalogo: sobe do
    modulo ate a raiz do repositorio. `parents[3]` porque este arquivo esta em
    `sparkforge/agentic/executor/`, um nivel mais fundo que os modulos irmaos.
    """
    return Path(__file__).resolve().parents[3] / "knowledge" / "source_authority.yaml"


def load_authority_map(path: Path | None = None) -> dict[str, object]:
    """Carrega o mapa de autoridade e converte os tiers em `EvidenceAuthority`.

    A conversao acontece na carga, e nao no uso, para que um tier escrito
    errado no YAML falhe uma vez ao abrir o arquivo em vez de virar um valor
    invalido circulando pelo motor.

    Arquivo ausente levanta `FileNotFoundError` em vez de devolver mapa vazio:
    o `default` existe para host DESCONHECIDO, nao para arquivo desaparecido, e
    silenciar a diferenca faria todo host virar T4 sem que nada acusasse.

    Returns:
        `{"schema_version": int, "default": EvidenceAuthority,
          "hosts": dict[str, EvidenceAuthority]}`.
    """
    target = Path(path) if path is not None else _authority_map_path()
    document = yaml.safe_load(target.read_text(encoding="utf-8-sig")) or {}

    raw_hosts = document.get("hosts") or {}
    hosts: dict[str, EvidenceAuthority] = {}
    for host, tier_name in raw_hosts.items():
        # Host normalizado ja na carga: URL traz maiuscula e ponto final, e
        # normalizar de novo no lookup convidaria as duas normalizacoes a
        # divergirem em silencio.
        hosts[str(host).strip().lower().rstrip(".")] = _to_authority(tier_name, target, host)

    default_name = document.get("default")
    default = (
        _to_authority(default_name, target, "default")
        if default_name is not None
        else _FALLBACK_DEFAULT
    )

    return {
        "schema_version": document.get("schema_version"),
        "default": default,
        "hosts": hosts,
    }


def _to_authority(name: Any, source: Path, key: str) -> EvidenceAuthority:
    """Traduz o nome do membro do enum, e nomeia o arquivo quando falha.

    Aceita o NOME do membro (`T1_OFFICIAL_DOCS`), que e como o YAML escreve, e
    tambem o valor (`T1`), que e como `EvidenceAuthority` serializa. Aceitar os
    dois evita que o mesmo tier tenha duas grafias legitimas no repositorio e
    uma delas quebre.
    """
    text = str(name).strip()
    try:
        return EvidenceAuthority[text]
    except KeyError:
        pass
    try:
        return EvidenceAuthority(text)
    except ValueError as exc:
        raise ValueError(
            f"{source}: tier desconhecido {text!r} para {key!r}; "
            f"esperado um de {[m.name for m in EvidenceAuthority]}"
        ) from exc


def tier_for_url(url: str, mapping: dict[str, object]) -> EvidenceAuthority:
    """Tier de autoridade do host de `url`, pelo mapa declarado.

    URL vazia, malformada ou sem host cai no `default` em vez de levantar. Nao
    e leniencia: uma URL ilegivel e exatamente um host DESCONHECIDO, e host
    desconhecido ja tem resposta declarada. Levantar aqui derrubaria a
    classificacao de um pacote inteiro por causa de uma fonte mal escrita, o
    que e a regra 27 ao contrario -- medicao nao derruba a chamada.

    Nao ha fallback por sufixo de dominio: `docs.aws.amazon.com.atacante.net`
    termina em nada que o mapa nomeie, mas um `endswith` sobre o host o
    promoveria a T1. A comparacao e do host inteiro, exata.
    """
    hosts: Any = mapping.get("hosts") or {}
    default: Any = mapping.get("default") or _FALLBACK_DEFAULT

    host = _hostname(url)
    if host is None:
        return default

    return hosts.get(host, default)


def _hostname(url: Any) -> str | None:
    """Host normalizado de `url`, ou `None` quando nao da para extrair um."""
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parsed = urlparse(url.strip())
        # `.hostname` ja derruba porta e caso; ele reparsa o netloc e pode
        # levantar `ValueError` (IPv6 malformado) mesmo quando `urlparse`
        # deixou passar, entao os dois ficam sob o mesmo `try`.
        host = parsed.hostname
    except ValueError:
        return None
    if not host:
        return None
    # Ponto final do FQDN absoluto (`spark.apache.org.`) e o mesmo host.
    return host.strip().lower().rstrip(".")


def in_scope(runtime_scope: dict[str, object], runtime: dict[str, object]) -> bool:
    """A regra vale no runtime do case?

    `runtime_scope` e o escopo DECLARADO pela regra (`{"glue": ["4.0","5.0"]}`);
    `runtime` e o que o case mediu (`{"glue": "5.0", "spark": "3.5.4"}`).

    Tres saidas, e a terceira e a decisao:

    1. Escopo vazio nao restringe nada -> `True`. Regra sem `runtime_scope` vale
       em qualquer versao, e essa e a leitura literal de "nao declarei escopo".
    2. Escopo nomeia a chave e o runtime tem valor fora da lista -> `False`.
    3. Escopo nomeia uma chave que o runtime NAO declara -> `False`.

    O caso 3 e escolha, nao detalhe de implementacao. A regra fala de Glue e o
    case nao diz qual Glue roda: nao da para AFIRMAR que esta dentro, e afirmar
    que esta fora seria inventar o contrario. Das duas saidas erradas possiveis,
    esta recusa em vez de aprovar -- aprovar aplicaria a regra de Glue 5.0 a um
    job que pode ser Glue 3.0, onde o significado do numero muda (regra 18 do
    `CLAUDE.md`). O custo da recusa e uma regra a menos no pacote; o custo da
    aprovacao e uma recomendacao errada com cara de medida. Quem quiser o outro
    lado declara o runtime.

    Comparacao por string normalizada, nao semantica de versao: o escopo lista
    uma a uma as versoes que a regra cobre, e ordena-las exigiria conhecer o
    esquema de versao de cada componente (`5.0`, `1.10.0`, `3.5.4-amzn-0`).
    """
    if not runtime_scope:
        return True

    for key, allowed in runtime_scope.items():
        observed = runtime.get(key) if runtime else None
        if observed is None:
            # Caso 3 -- ver docstring. Recusa em vez de aprovar.
            return False

        allowed_values = allowed if isinstance(allowed, (list, tuple, set)) else [allowed]
        normalized = {str(v).strip() for v in allowed_values}
        if str(observed).strip() not in normalized:
            return False

    return True
