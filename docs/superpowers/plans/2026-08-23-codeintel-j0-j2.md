# SparkForge Code Intelligence — fases J0 a J2

> **Para trabalhadores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> `superpowers:subagent-driven-development` (recomendado) ou
> `superpowers:executing-plans` para implementar este plano tarefa a tarefa. Os
> passos usam caixas de seleção (`- [ ]`) para acompanhamento.

**Objetivo:** fechar a dívida de segurança de leitura que já existe hoje e
baratear o que o motor já devolve, antes de qualquer linha de índice — as três
fases entregam ganho isolado e são pré-condição medida do SFCI.

**Arquitetura:** nenhum pacote novo. J0 consolida quatro detectores de segredo
num só e aplica confinamento de caminho e denylist na varredura que já existe.
J1 tira do envelope o que é repetição (procedência por referência) e acrescenta
`detail_level` no único ponto onde a paginação já é montada. J2 decide se a
cadeia de autorização passa a ver o argumento da tool, ou aceita o limite por
escrito com compensação nomeada.

**Pilha:** Python ≥3.10, biblioteca padrão apenas (`ast`, `re`, `pathlib`,
`json`). Zero dependência nova — é requisito, não preferência.

---

## Por que estas três, nesta ordem

O mapa [`docs/harness/CODEINTEL-GAP.md`](../../harness/CODEINTEL-GAP.md) mediu a
SPEC do SFCI contra o repositório e concluiu que **a extração já existe**: os
extratores de `sparkforge/facts/` já emitem `pyspark.read`/`pyspark.write` (o
grafo de tabela da §35), `pyspark.callgraph_edge` mais os quatro kinds
`callgraph.*` (§123/§124) e `graph.unresolved`/`sql.unresolved` (§28). O que
falta é persistência, índice incremental e recuperação.

Mas o mapa também mediu que **há dívida aberta hoje**, sem SFCI nenhum:

- Quatro implementações de detector de segredo, **zero testes** no módulo
  canônico, e as quatro deixam passar PAT do GitHub, JWT e chave privada RSA
  quando o nome da chave não denuncia.
- A varredura entra em `.venv/`, `node_modules/` e `vendor/`. Só três dos doze
  sítios de `rglob` pulam sequer `__pycache__`.
- O payload devolvido é várias vezes o tamanho do código-fonte, e **27% dele é
  `provenance` repetida** — o mesmo sha256 do mesmo arquivo, copiado uma vez por
  fato.
- `detail_level` existe em **0 das 44** tools; projeção de campo em 0; paginação
  em 22.

Um índice que persista código de cliente **multiplica** cada um desses. Por isso
J0 vem primeiro, e por isso ela não é "preparação" — é conserto.

A política de git do estado local, que era a quarta pré-condição, **já foi
fechada** em `715a657`: `.sparkforge/traces.db`, `.sparkforge/cache/` e
`.sparkforge/local/` entraram no `.gitignore` com a razão escrita.

## Escopo: o que NÃO está neste plano

Fica para um segundo plano, depois que este provar a medição:

- Banco SQLite, schema, FTS5, índice completo e incremental (§19 a §29, §42).
- Recuperação, ranking e `ContextPack` (§47 a §55).
- As onze tools novas (§56 a §67).
- Worktrees, lineage de SQL, hardening, migração de SDK MCP.

A razão de recusar as tools agora está no mapa e vale repetir: **uma tool que
não tem índice responde igual a um modelo sem ferramenta nenhuma**, e cada tool
nova entra no gate de paridade e no catálogo para sempre.

## Decisão de medição: bytes, nunca tokens

Existem hoje **quatro** estimadores de token no repositório, e ao contrário dos
detectores de segredo, esses **divergem**: `agents/budget.py` e `tools/cost.py`
arredondam para cima, `context/funnel.py:81` e `providers/mock.py:18` truncam.
Todos são `len/4`, que é chute.

Um tokenizador de verdade exigiria dependência nova, o que contraria o motivo
número um do projeto (autossuficiência). Então este plano mede em **bytes**:

- Byte é observação, token é estimativa.
- Byte é determinístico e verificável pelo gate de lastro.
- Byte não precisa de dependência.

**Nenhum documento produzido por este plano pode afirmar economia em tokens.**
Onde a palavra "token" aparecer, ela vem qualificada como estimativa, e a
medição ao lado é em bytes. Unificar os quatro estimadores fica para o segundo
plano, junto com os três empacotadores de contexto — não é pré-condição de nada
aqui, e mexer neles agora arrasta superfície sem necessidade.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Fase |
|---|---|---|
| `sparkforge/facts/secrets.py` | **Único** detector de segredo. Ganha detectores por valor e passa a ser o import de todos os extratores | J0 |
| `tests/test_facts_secrets.py` | **Novo.** Corpus de segredo: positivos por valor, negativos que não podem virar falso positivo | J0 |
| `sparkforge/facts/scan.py` | **Novo.** `iter_source_files()` — a varredura única, com denylist e confinamento | J0 |
| `tests/test_facts_scan.py` | **Novo.** Denylist, traversal, symlink, arquivo especial | J0 |
| `sparkforge/facts/terraform.py`, `emr_cluster.py`, `emr_serverless.py` | Perdem a cópia privada de `_looks_like_secret` | J0 |
| `sparkforge/findings/models.py` | **Não muda.** A projeção opera sobre o dicionário já serializado, em `_core.py` — `Fact` continua com uma forma só | J1 |
| `sparkforge/adapters/_core.py` | `project_items()` novo; os 7 pontos de envelope passam a chamá-lo | J1 |
| `sparkforge/adapters/tools.py` | `detail_level` no `inputSchema` das tools que paginam | J1 |
| `sparkforge/adapters/mcp.py:83` | Separadores compactos | J1 |
| `tests/test_adapters_detail_level.py` | **Novo.** Os três níveis, e o invariante de que `id` sobrevive a todos | J1 |
| `sparkforge/agents/autonomy.py` | `authorize()` passa a receber `arguments` — ou não, e o limite fica escrito | J2 |
| `docs/harness/AUTHORIZATION-CHAIN.md` | Registra a decisão de J2 | J2 |

---

# Fase J0 — a fronteira de leitura

## Task 1: corpus de segredo que falha contra o detector de hoje

**Arquivos:**
- Criar: `tests/test_facts_secrets.py`

- [ ] **Passo 1: escrever o teste que falha**

O corpus é o entregável, não o teste. Cada positivo tem nome de chave
**inocente** de propósito: é assim que o defeito aparece.

```python
"""Corpus de segredo, por VALOR.

O detector de hoje tem tres gatilhos, e dois deles dependem do NOME da chave.
Isso deixa passar todo segredo que chega num campo de nome inocente -- que e
exatamente como segredo chega em configuracao de verdade: `config_value`,
`data`, `payload`. Este arquivo fixa o comportamento por VALOR.

Os negativos importam tanto quanto os positivos. Um detector que redige
`s3://bucket/prefixo` ou um sha256 de commit apaga evidencia que a analise
precisa -- e apagar evidencia por medo e o defeito que a fase I2 recusou por
escrito em docs/harness/UNTRUSTED-CONTENT.md.
"""

import pytest

from sparkforge.facts.secrets import looks_like_secret

# (nome_do_caso, chave, valor)
POSITIVOS = [
    ("aws_access_key", "x", "AKIAIOSFODNN7EXAMPLE"),
    ("senha_em_url", "conn", "postgresql://admin:Hunter2@db.internal:5432/prod"),
    ("github_pat_classico", "config_value", "ghp_" + "a" * 36),
    ("github_pat_fine_grained", "data", "github_pat_" + "b" * 22 + "_" + "c" * 59),
    ("jwt", "payload", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVP"),
    ("chave_privada_rsa", "blob", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA"),
    ("chave_privada_openssh", "blob", "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaA"),
    ("slack_token", "campo", "xoxb-" + "1" * 12 + "-" + "2" * 24),
]

NEGATIVOS = [
    ("caminho_s3", "spark.sql.warehouse.dir", "s3://bucket/warehouse/prefixo/longo"),
    ("sha_de_commit", "revision", "a" * 40),
    ("booleano", "spark.hadoop.fs.s3a.secret.key", "true"),
    ("tamanho", "spark.sql.files.maxPartitionBytes", "134217728"),
    ("classe_java", "spark.serializer", "org.apache.spark.serializer.KryoSerializer"),
    ("arn", "role", "arn:aws:iam::123456789012:role/GlueETLRole"),
    ("vazio", "password", ""),
]


@pytest.mark.parametrize("nome,chave,valor", POSITIVOS, ids=[c[0] for c in POSITIVOS])
def test_segredo_e_detectado_mesmo_com_nome_de_chave_inocente(nome, chave, valor):
    assert looks_like_secret(chave, valor) is True, (
        f"{nome}: valor com forma de credencial passou batido com chave {chave!r}"
    )


@pytest.mark.parametrize("nome,chave,valor", NEGATIVOS, ids=[c[0] for c in NEGATIVOS])
def test_dado_legitimo_nao_e_redigido(nome, chave, valor):
    assert looks_like_secret(chave, valor) is False, (
        f"{nome}: dado legitimo foi tratado como segredo -- redacao apaga evidencia"
    )
```

- [ ] **Passo 2: rodar e confirmar que falha nos casos certos**

```
python -m pytest tests/test_facts_secrets.py -q
```

Esperado, **medido contra o detector de hoje antes de escrever este plano**:
**6 dos 8 positivos falham** — `github_pat_classico`, `github_pat_fine_grained`,
`jwt`, `chave_privada_rsa`, `chave_privada_openssh` e `slack_token`. Os dois que
passam são `aws_access_key` e `senha_em_url`, os únicos dois gatilhos por valor
que existem hoje. **Os 7 negativos passam, zero falso positivo.**

Se o seu resultado divergir desse, pare e diga: ou o detector mudou desde a
medição, ou o corpus está escrito diferente do que eu medi.

Se algum negativo falhar, pare: o detector de hoje já tem falso positivo, e isso
é achado a reportar antes de mexer em qualquer coisa.

- [ ] **Passo 3: NÃO commite ainda**

Um corpus vermelho na branch é um gate quebrado, e `xfail` num teste de segurança
é pior: ele documenta o furo e o mantém aberto. Siga direto para a Task 2; as
duas fecham num commit só.

## Task 2: os detectores por valor, no módulo canônico

**Arquivos:**
- Modificar: `sparkforge/facts/secrets.py`

- [ ] **Passo 1: acrescentar os padrões por valor**

Ancore após `_HIGH_ENTROPY_RE` (linha ~61). Cada padrão vem com a razão de ser
reconhecível — é isso que separa detector de chute.

```python
# Padroes que identificam credencial pelo VALOR, sem depender do nome da chave.
# Cada um tem prefixo publicado pelo emissor, o que os torna reconheciveis sem
# heuristica de entropia -- e entropia sozinha produz falso positivo em sha, em
# caminho de S3 e em nome de classe Java.
_PADROES_POR_VALOR: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    # AWS: formato publico, documentado, sem ambiguidade.
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA|AIDA|AROA)[0-9A-Z]{16}\b")),
    # GitHub, os dois formatos vivos. O classico tem 36 caracteres depois do
    # prefixo; o fine-grained e mais longo e tem underscore no meio.
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    # JWT: tres segmentos base64url separados por ponto, comecando por um header
    # que quase sempre serializa para `eyJ`.
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    # Chave privada PEM, qualquer variante. O cabecalho e literal e padronizado.
    ("private_key", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    # Slack: prefixo por tipo de token, todos com o mesmo formato segmentado.
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
)
```

- [ ] **Passo 2: usar os padrões em `looks_like_secret`**

Substitua o bloco `if _AKIA_RE.search(value): return True` por uma varredura
sobre `_PADROES_POR_VALOR`, mantendo o resto intacto:

```python
    for _, padrao in _PADROES_POR_VALOR:
        if padrao.search(value):
            return True
    if _URL_PASSWORD_RE.search(value):
        return True
```

Atualize a docstring: o gatilho 1 deixa de ser "access key da AWS" e passa a ser
"o valor casa um padrão de credencial publicado". Diga que o gatilho 3 (nome da
chave mais entropia) **continua existindo** e por quê — ele pega o segredo
proprietário, que não tem prefixo publicado.

- [ ] **Passo 3: acrescentar `detectores()` para o chamador que precisa saber qual**

A §15 da SPEC exige que o scanner diga **qual** detector disparou e **nunca** o
segredo. Isso é uma função nova, não uma mudança em `looks_like_secret`:

```python
def detectores(key: str, value: str) -> tuple[str, ...]:
    """Nomes dos detectores que dispararam, em ordem estavel.

    NUNCA devolve o valor casado -- e essa a diferenca entre relatorio de
    seguranca e vazamento. Um chamador que queira gravar "havia credencial aqui"
    grava estes nomes; um que queira o valor nao tem como obte-lo por aqui.
    """
    if not isinstance(key, str) or not isinstance(value, str):
        return ()
    achados = [nome for nome, padrao in _PADROES_POR_VALOR if padrao.search(value)]
    if _URL_PASSWORD_RE.search(value):
        achados.append("url_password")
    key_lower = key.lower()
    if any(h in key_lower for h in _SECRET_KEY_HINTS) and _HIGH_ENTROPY_RE.fullmatch(value):
        achados.append("nome_de_chave_com_entropia")
    return tuple(achados)
```

- [ ] **Passo 4: teste de que `detectores()` não vaza o valor**

Acrescente a `tests/test_facts_secrets.py`:

```python
from sparkforge.facts.secrets import detectores


def test_detectores_nomeia_sem_nunca_devolver_o_valor():
    valor = "AKIAIOSFODNN7EXAMPLE"
    nomes = detectores("x", valor)
    assert nomes == ("aws_access_key",)
    assert valor not in " ".join(nomes)


def test_detectores_vazio_para_dado_legitimo():
    assert detectores("spark.sql.warehouse.dir", "s3://bucket/prefixo") == ()
```

- [ ] **Passo 5: rodar tudo**

```
python -m pytest tests/test_facts_secrets.py -q
```
Esperado: **todos passam**.

```
python -m pytest tests/ -q -k "secret or redact or terraform or emr"
```
Esperado: nenhuma regressão. Se um teste de redação existente quebrar, leia-o
antes de mudar: pode ser que ele fixasse a permissividade antiga, e aí o teste
é que está errado. Diga qual, no commit.

- [ ] **Passo 6: commit**

```bash
git add sparkforge/facts/secrets.py tests/test_facts_secrets.py
git commit -m "fix(secrets): PAT, JWT e chave privada passavam quando o nome da chave era inocente"
```

## Task 3: uma implementação só

**Arquivos:**
- Modificar: `sparkforge/facts/terraform.py:290`, `sparkforge/facts/emr_cluster.py:299`, `sparkforge/facts/emr_serverless.py:400`
- Modificar: `tests/test_facts_secrets.py`

- [ ] **Passo 1: teste que trava a unicidade**

```python
import ast
import pathlib


def test_existe_um_unico_detector_de_segredo_no_pacote():
    """Quatro copias da mesma pergunta e como um controle de seguranca apodrece.

    As quatro NAO divergiam quando isto foi medido -- elas falhavam igual, que e
    pior de achar. O gate e estrutural: se alguem escrever a quinta, isto quebra
    antes de a quinta divergir.
    """
    raiz = pathlib.Path(__file__).resolve().parent.parent / "sparkforge"
    definidores = []
    for arquivo in sorted(raiz.rglob("*.py")):
        if "__pycache__" in arquivo.parts:
            continue
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.FunctionDef) and no.name.lstrip("_") == "looks_like_secret":
                definidores.append(str(arquivo.relative_to(raiz)))
    assert definidores == ["facts/secrets.py"], definidores
```

- [ ] **Passo 2: rodar e ver falhar**

```
python -m pytest tests/test_facts_secrets.py::test_existe_um_unico_detector_de_segredo_no_pacote -q
```
Esperado: FALHA listando os quatro caminhos.

- [ ] **Passo 3: apagar as três cópias e importar a canônica**

Em cada um dos três arquivos, apague a função `_looks_like_secret` e acrescente
ao bloco de imports:

```python
from sparkforge.facts.secrets import looks_like_secret as _looks_like_secret
```

O alias preserva os call sites, então o diff fica pequeno e auditável. **Não
renomeie os call sites nesta tarefa** — misturar remoção de duplicata com
renomeação esconde qual das duas quebrou, se quebrar.

- [ ] **Passo 4: rodar**

```
python -m pytest tests/test_facts_secrets.py -q
python -m pytest tests/ -q -k "terraform or emr_cluster or emr_serverless"
```
Esperado: tudo passa. As três cópias eram idênticas em comportamento — se algo
quebrar, você encontrou uma divergência que a medição não achou. Reporte antes
de contornar.

- [ ] **Passo 5: commit**

```bash
git add sparkforge/facts/terraform.py sparkforge/facts/emr_cluster.py sparkforge/facts/emr_serverless.py tests/test_facts_secrets.py
git commit -m "refactor(secrets): quatro copias viram uma, e um gate impede a quinta"
```

## Task 4: a varredura com denylist e confinamento

**Arquivos:**
- Criar: `sparkforge/facts/scan.py`
- Criar: `tests/test_facts_scan.py`

- [ ] **Passo 1: escrever o teste primeiro**

```python
"""A varredura e a fronteira entre o repositorio analisado e o motor.

Hoje ela nao existe como unidade: sao doze sitios de `rglob` espalhados, e so
tres pulam sequer `__pycache__`. Apontar o motor para um repositorio com `.venv`
varre o ambiente virtual inteiro -- custo, ruido, e leitura de qualquer `*.json`
que houver dentro.
"""

import pathlib

import pytest

from sparkforge.facts.scan import ScanError, iter_source_files


def _criar(raiz: pathlib.Path, caminho: str, conteudo: str = "x = 1\n") -> pathlib.Path:
    alvo = raiz / caminho
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo, encoding="utf-8")
    return alvo


def test_pula_arvore_de_dependencia_e_artefato_de_build(tmp_path):
    _criar(tmp_path, "job.py")
    for ruido in (
        ".venv/lib/site-packages/requests/api.py",
        "venv/lib/x.py",
        "node_modules/pacote/index.py",
        "vendor/terceiro/mod.py",
        "build/lib/copia.py",
        "__pycache__/job.cpython-312.py",
        ".git/hooks/pre-commit.py",
        ".tox/py310/x.py",
        "site-packages/y.py",
    ):
        _criar(tmp_path, ruido)
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["job.py"]


def test_pula_caminho_sensivel_mesmo_com_extensao_pedida(tmp_path):
    _criar(tmp_path, "config.json", "{}")
    for sensivel in (
        ".aws/credentials.json",
        ".ssh/chave.json",
        "terraform.tfstate.json",
        "secrets.json",
        ".env.json",
    ):
        _criar(tmp_path, sensivel, "{}")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.json"))
    assert achados == ["config.json"]


def test_symlink_nao_e_seguido(tmp_path):
    fora = tmp_path.parent / "fora_do_alvo"
    fora.mkdir(exist_ok=True)
    (fora / "segredo.py").write_text("SENHA = 'x'\n", encoding="utf-8")
    alvo = tmp_path / "alvo"
    alvo.mkdir()
    _criar(alvo, "job.py")
    try:
        (alvo / "atalho").symlink_to(fora, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    achados = sorted(p.name for p in iter_source_files(alvo, "*.py"))
    assert achados == ["job.py"]


def test_raiz_inexistente_e_erro_nomeado_nao_lista_vazia(tmp_path):
    with pytest.raises(ScanError):
        list(iter_source_files(tmp_path / "nao_existe", "*.py"))


def test_arquivo_grande_demais_e_pulado_sem_derrubar_a_varredura(tmp_path):
    _criar(tmp_path, "pequeno.py")
    (tmp_path / "gigante.py").write_text("#" * (2 * 1024 * 1024), encoding="utf-8")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["pequeno.py"]


def test_apenas_arquivo_regular(tmp_path):
    _criar(tmp_path, "job.py")
    achados = list(iter_source_files(tmp_path, "*.py"))
    assert all(p.is_file() for p in achados)
```

- [ ] **Passo 2: rodar e ver falhar**

```
python -m pytest tests/test_facts_scan.py -q
```
Esperado: FALHA com `ModuleNotFoundError: No module named 'sparkforge.facts.scan'`.

- [ ] **Passo 3: escrever o módulo**

```python
"""A varredura unica dos extratores, com denylist e confinamento.

Doze sitios de `rglob` faziam isto separadamente, e so tres pulavam sequer
`__pycache__`. Consolidar aqui e o que torna a fronteira auditavel: existe UM
lugar que decide o que o motor pode ler, e ele tem teste.

Fail-closed em toda decisao: caminho que escapa da raiz, symlink, arquivo
especial e arquivo grande demais sao PULADOS, nunca lidos "so para ver". A
excecao e raiz inexistente, que e erro nomeado -- devolver lista vazia ali
pareceria "nao ha nada a analisar", quando o certo e "voce apontou para o lugar
errado".
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path


class ScanError(Exception):
    """Raiz inexistente, ilegivel, ou que nao e diretorio."""


# Arvore de dependencia, artefato de build e metadados de ferramenta. Nada aqui
# e codigo do projeto analisado, e tudo aqui e volumoso.
DIRETORIOS_IGNORADOS: frozenset[str] = frozenset(
    {
        "__pycache__", ".git", ".hg", ".svn",
        ".venv", "venv", ".env", "site-packages", ".tox", ".nox",
        "node_modules", "bower_components",
        "vendor", "build", "dist", ".eggs", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", ".idea", ".vscode", ".gradle", "target",
        ".terraform", ".sparkforge",
    }
)

# Caminhos que NUNCA sao lidos, mesmo casando a extensao pedida. A allowlist de
# extensao nao pode reabilitar arquivo de credencial -- e por isso a checagem
# vem DEPOIS do casamento de padrao, nao antes.
NOMES_SENSIVEIS: frozenset[str] = frozenset(
    {"credentials", "secrets", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "kubeconfig"}
)
SUFIXOS_SENSIVEIS: tuple[str, ...] = (
    ".pem", ".key", ".p12", ".pfx", ".jks", ".tfstate", ".tfvars", ".npmrc", ".pypirc",
)
PREFIXOS_SENSIVEIS: tuple[str, ...] = (".env", "credentials", "secrets", ".netrc")

TAMANHO_MAXIMO_BYTES = 1024 * 1024


def _e_sensivel(caminho: Path) -> bool:
    nome = caminho.name.lower()
    talo = caminho.stem.lower()
    if talo in NOMES_SENSIVEIS:
        return True
    if any(nome.endswith(s) for s in SUFIXOS_SENSIVEIS):
        return True
    return any(nome.startswith(p) for p in PREFIXOS_SENSIVEIS)


def iter_source_files(root: Path | str, pattern: str) -> Iterator[Path]:
    """Arquivos regulares sob `root` que casam `pattern`, em ordem estavel.

    Ordem estavel importa: o motor e deterministico, e ordem de varredura muda
    ordem de fact. `sorted` em cada nivel garante isso em qualquer sistema de
    arquivos.
    """
    raiz = Path(root).expanduser()
    if not raiz.exists():
        raise ScanError(f"raiz inexistente: {raiz}")
    if not raiz.is_dir():
        raise ScanError(f"raiz nao e diretorio: {raiz}")
    raiz_real = raiz.resolve()

    for pasta_atual, subpastas, arquivos in os.walk(raiz_real, followlinks=False):
        # Poda no lugar: os.walk respeita a mutacao e nem desce nas removidas.
        subpastas[:] = sorted(d for d in subpastas if d not in DIRETORIOS_IGNORADOS)
        base = Path(pasta_atual)
        for nome in sorted(arquivos):
            caminho = base / nome
            if not caminho.match(pattern):
                continue
            if caminho.is_symlink() or not caminho.is_file():
                continue
            if _e_sensivel(caminho):
                continue
            try:
                if caminho.stat().st_size > TAMANHO_MAXIMO_BYTES:
                    continue
                # Confinamento: mesmo com followlinks=False, um componente
                # intermediario pode ter sido substituido durante a varredura.
                real = caminho.resolve()
                if raiz_real != real and raiz_real not in real.parents:
                    continue
            except OSError:
                continue
            yield caminho
```

- [ ] **Passo 4: rodar**

```
python -m pytest tests/test_facts_scan.py -q
```
Esperado: **todos passam** (o de symlink pode dar `skip` no Windows sem
privilégio, e isso é aceitável).

- [ ] **Passo 5: commit**

```bash
git add sparkforge/facts/scan.py tests/test_facts_scan.py
git commit -m "feat(scan): a varredura vira unidade, com denylist e confinamento"
```

## Task 5: os doze sítios passam a usar a varredura

**Arquivos:**
- Modificar: `sparkforge/facts/pyspark_ast.py:1127`, `graph.py:1437`, `migration.py:542,547,553`, `data_quality.py:1742`, `catalog_schema.py:359`, `athena_workgroup.py:265`, `emr_cluster.py:1257`, `emr_serverless.py:1007`, `iceberg_metadata.py:680`, `consumers.py:216`
- Modificar: `tests/test_facts_scan.py`

- [ ] **Passo 1: teste que trava a ausência de `rglob` cru**

```python
def test_nenhum_extrator_varre_com_rglob_cru():
    """`rglob` direto e a porta de entrada sem denylist.

    O gate e estrutural e por AST: quem precisar varrer chama
    `iter_source_files`, que tem teste. Este arquivo (`scan.py`) e a unica
    excecao, porque e ele que implementa a varredura.
    """
    raiz = pathlib.Path(__file__).resolve().parent.parent / "sparkforge" / "facts"
    infratores = []
    for arquivo in sorted(raiz.glob("*.py")):
        if arquivo.name == "scan.py":
            continue
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Attribute) and no.attr == "rglob":
                infratores.append(f"{arquivo.name}:{no.lineno}")
    assert infratores == [], infratores
```

- [ ] **Passo 2: rodar e ver falhar**

```
python -m pytest tests/test_facts_scan.py::test_nenhum_extrator_varre_com_rglob_cru -q
```
Esperado: FALHA listando os doze sítios. **Anote a lista** — ela é o roteiro do
passo 3 e o número vai para o commit.

- [ ] **Passo 3: trocar sítio a sítio**

Padrão da troca, aplicado em cada um:

```python
# antes
for py in sorted(root.rglob("*.py")):
    if "__pycache__" in py.parts:
        continue

# depois
from sparkforge.facts.scan import iter_source_files
...
for py in iter_source_files(root, "*.py"):
```

Cuidado com `consumers.py:216`, que varre por `pattern` variável — passe a
variável, não um literal.

Faça **um sítio por vez** e rode o teste do extrator correspondente antes de ir
ao próximo. Se algum golden mudar, pare: significa que aquela varredura estava
lendo arquivo de dentro de `build/` ou `vendor/` e o golden fixava esse ruído.
Isso é achado, não obstáculo — reporte qual fixture e qual arquivo.

- [ ] **Passo 4: rodar a suíte inteira**

```
python -m pytest tests/ -q
```
Esperado: **6362 passed, 5 skipped** ou mais. Zero falhas.

```
ruff check sparkforge tests scripts
```
Esperado: `Found 241 errors` — a linha de base. Não pode subir.

- [ ] **Passo 5: commit**

```bash
git add sparkforge/facts/ tests/test_facts_scan.py
git commit -m "refactor(facts): os doze rglob passam pela varredura com denylist"
```

---

# Fase J1 — o envelope barato

## Task 6: procedência declarada uma vez

**Arquivos:**
- Criar: `tests/test_adapters_detail_level.py`
- Criar: `tests/test_adapters_detail_level.py`

- [ ] **Passo 1: medir o custo atual, e guardar o número**

```
python -c "import subprocess,sys,json; j=json.loads(subprocess.run([sys.executable,'-m','sparkforge.adapters.cli','analyze','pyspark','--path','fixtures/pyspark/clean_job/input/lib/job.py'],capture_output=True,text=True).stdout); e=json.dumps(j,ensure_ascii=False); p=sum(len(json.dumps(f.get('provenance',{}),ensure_ascii=False)) for f in j['items']); print('envelope',len(e),'provenance',p,'pct',round(p/len(e)*100,1))"
```

Anote os três números. Eles são o "antes" e entram no commit.

- [ ] **Passo 2: escrever o teste do modo compacto**

```python
"""O envelope devolvido pelo motor, e o que dele e repeticao.

Medido antes desta fase: a procedencia responde por mais de um quarto do
payload, e o sha256 do MESMO arquivo aparece uma vez por fato. Declarar uma vez
por artefato e referenciar por chave preserva a rastreabilidade inteira e para
de pagar por ela N vezes.
"""

import json
import subprocess
import sys

FIXTURE = "fixtures/pyspark/clean_job/input/lib/job.py"


def _analisar(*extra: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "sparkforge.adapters.cli", "analyze", "pyspark",
         "--path", FIXTURE, *extra],
        capture_output=True, text=True, check=True,
    )
    return json.loads(proc.stdout)


def test_provenance_e_declarada_uma_vez_e_referenciada_por_chave():
    saida = _analisar("--detail-level", "normal")
    assert "provenance" in saida, "o envelope precisa declarar as procedencias"
    for item in saida["items"]:
        assert "provenance" not in item, "procedencia inline volta a custar por fato"
        assert item["provenance_ref"] in saida["provenance"]


def test_nada_de_rastreabilidade_se_perde():
    completo = _analisar("--detail-level", "full")
    compacto = _analisar("--detail-level", "normal")
    for inline, referenciado in zip(completo["items"], compacto["items"], strict=True):
        assert compacto["provenance"][referenciado["provenance_ref"]] == inline["provenance"]
```

- [ ] **Passo 3: rodar e ver falhar**

```
python -m pytest tests/test_adapters_detail_level.py -q
```
Esperado: FALHA — `--detail-level` não existe ainda.

- [ ] **Passo 4: implementar em `_core.py` (ver Task 7)**

Esta tarefa e a próxima são um par: o teste acima só passa depois que
`project_items()` existir. Siga direto para a Task 7 e commite as duas juntas.

## Task 7: `detail_level` no ponto único

**Arquivos:**
- Modificar: `sparkforge/adapters/_core.py` (os 7 pontos de envelope)
- Modificar: `sparkforge/adapters/tools.py` (inputSchema das 22 que paginam)
- Modificar: `sparkforge/adapters/cli.py` (a flag)
- Modificar: `sparkforge/adapters/mcp.py:83`

- [ ] **Passo 1: escrever `project_items()` em `_core.py`**

Ancore imediatamente após `paginate_items` (linha ~118), que é onde a
paginação já mora — o `detail_level` é o mesmo tipo de decisão.

```python
NIVEIS_DE_DETALHE: tuple[str, ...] = ("summary", "normal", "full")

# Campos que sobrevivem a `summary`. `id` esta aqui porque e ele que torna o
# funil possivel: quem quiser o fato inteiro pede por id, e sem id o `summary`
# seria um beco sem saida em vez de um primeiro passo.
_CAMPOS_DE_SUMARIO: tuple[str, ...] = ("id", "kind", "measures")


def project_items(
    items: list[dict[str, Any]], detail_level: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """`(itens_projetados, procedencias)` para o nivel pedido.

    `full` devolve o que sempre devolveu -- e o modo de reauditoria, e mudar a
    forma dele quebraria golden por toda parte. `normal` tira a procedencia de
    dentro de cada item e a declara uma vez, referenciada por chave. `summary`
    mantem so o que responde "onde e o que", com o `id` para pedir o resto.

    A procedencia NUNCA some: em `summary` ela continua no envelope. Economia
    que apaga rastreabilidade seria o defeito que o gate de lastro recusa.
    """
    if detail_level not in NIVEIS_DE_DETALHE:
        raise AdapterError(
            f"detail_level invalido: {detail_level!r}; use um de {NIVEIS_DE_DETALHE}",
            exit_code=2,
        )
    if detail_level == "full":
        return items, {}

    procedencias: dict[str, Any] = {}
    projetados: list[dict[str, Any]] = []
    for item in items:
        prov = item.get("provenance")
        chave = ""
        if prov:
            chave = str(prov.get("artifact_sha256") or prov.get("artifact") or "")[:12]
            # Truncar o sha cria risco de colisao. Ele e desprezivel entre os
            # artefatos de um mesmo job, mas colisao aqui seria SILENCIOSA: dois
            # artefatos passariam a compartilhar procedencia, e a rastreabilidade
            # apontaria para o arquivo errado. Fail-closed: se a chave ja existe
            # com procedencia diferente, use o sha inteiro para os dois.
            existente = procedencias.get(chave)
            if existente is not None and existente != prov:
                chave = str(prov.get("artifact_sha256") or prov.get("artifact") or "")
            procedencias.setdefault(chave, prov)

        if detail_level == "normal":
            novo = {k: v for k, v in item.items() if k not in ("provenance", "schema_version")}
        else:
            sujeito = item.get("subject", {})
            local = f"{sujeito.get('file', '')}:{sujeito.get('line', '')}".strip(":")
            novo = {c: item[c] for c in _CAMPOS_DE_SUMARIO if item.get(c)}
            if local:
                novo["at"] = local
        if chave:
            novo["provenance_ref"] = chave
        projetados.append(novo)
    return projetados, procedencias
```

- [ ] **Passo 2: ligar nos 7 pontos de envelope**

Os pontos estão nas linhas `482, 542, 587, 1599, 1789, 2016, 3067` de
`_core.py` (confirme por `grep -n '"total_count":'` antes de editar — as linhas
mudam a cada edição anterior). Em cada um, o padrão:

```python
    page, next_cursor = paginate_items(items, limit, cursor)
    page, procedencias = project_items(page, detail_level)
    ...
    resultado = {
        "total_count": len(filtered),
        "returned_count": len(page),
        ...
    }
    if procedencias:
        resultado["provenance"] = procedencias
```

`detail_level` chega como parâmetro da função que monta o envelope, com default
`"full"`. **O default é `full` de propósito**, ao contrário do que o §12 do
prompt de evolução sugeria: mudar o default muda a saída de todo chamador
existente, incluindo os goldens, e isso é decisão separada desta fase. Registre
essa escolha na docstring.

- [ ] **Passo 3: expor na CLI e no MCP**

Na CLI, no parser de `analyze` (importe `NIVEIS_DE_DETALHE` de
`sparkforge.adapters._core` — a lista de níveis mora onde a projeção mora, e
duplicá-la no parser criaria duas fontes para a mesma verdade):

```python
    parser.add_argument(
        "--detail-level",
        choices=NIVEIS_DE_DETALHE,
        default="full",
        help="Verbosidade da saida. `summary` mantem id, kind, local e medidas.",
    )
```

Em `tools.py`, no `inputSchema` de cada tool que já tem `limit`/`cursor`:

```python
    "detail_level": {
        "type": "string",
        "enum": ["summary", "normal", "full"],
        "description": (
            "Verbosidade. `summary` devolve id, kind, arquivo:linha e medidas; "
            "peca o fato inteiro por id quando precisar. Default `full`."
        ),
    },
```

Em `mcp.py:83`, troque para separadores compactos:

```python
                text=json.dumps(result, ensure_ascii=False, separators=(",", ":")),
```

- [ ] **Passo 4: teste dos três níveis**

Acrescente a `tests/test_adapters_detail_level.py`:

```python
import pytest


@pytest.mark.parametrize("nivel", ["summary", "normal", "full"])
def test_id_sobrevive_a_todos_os_niveis(nivel):
    """Sem `id`, `summary` seria beco sem saida em vez de primeiro passo."""
    saida = _analisar("--detail-level", nivel)
    assert saida["items"], "a fixture precisa produzir ao menos um fato"
    for item in saida["items"]:
        assert item["id"]


def test_summary_e_menor_que_normal_que_e_menor_que_full():
    tamanhos = {
        n: len(json.dumps(_analisar("--detail-level", n), ensure_ascii=False, separators=(",", ":")))
        for n in ("summary", "normal", "full")
    }
    assert tamanhos["summary"] < tamanhos["normal"] < tamanhos["full"], tamanhos


def test_full_nao_mudou_de_forma():
    """`full` e o modo de reauditoria. Mudar a forma dele quebraria golden."""
    saida = _analisar("--detail-level", "full")
    for item in saida["items"]:
        assert "provenance" in item
        assert "provenance_ref" not in item
    assert "provenance" not in saida


def test_detail_level_invalido_e_recusado():
    proc = subprocess.run(
        [sys.executable, "-m", "sparkforge.adapters.cli", "analyze", "pyspark",
         "--path", FIXTURE, "--detail-level", "nao_existe"],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
```

- [ ] **Passo 5: rodar tudo e medir o depois**

```
python -m pytest tests/test_adapters_detail_level.py -q
python -m pytest tests/ -q
ruff check sparkforge tests scripts
```
Esperado: todos passam; suíte sem regressão; ruff em 241.

Meça o "depois" com o mesmo comando do Passo 1 da Task 6, agora com
`--detail-level summary` e `normal`. **Os três números (antes, normal, summary),
em bytes, vão para o commit e para o claim.**

- [ ] **Passo 6: registrar a medição no gate de lastro**

Escreva a medição em `docs/harness/CODEINTEL-GAP.md`, na seção 14, e registre o
claim em `docs/claims.lock.json` com prova `kind: command` que **execute** o
`analyze` nos dois níveis e compare os tamanhos. Reler o número do documento não
prova nada.

**Não escreva o número em tokens.** Bytes, com a palavra "bytes" ao lado.

- [ ] **Passo 7: commit**

```bash
git add sparkforge/adapters/ tests/test_adapters_detail_level.py docs/harness/CODEINTEL-GAP.md docs/claims.lock.json
git commit -m "feat(adapters): detail_level e procedencia por referencia"
```

---

# Fase J2 — a cadeia vê o argumento, ou o limite fica escrito

## Task 8: decidir, com medição

**Arquivos:**
- Modificar: `sparkforge/agents/autonomy.py`
- Modificar: `docs/harness/AUTHORIZATION-CHAIN.md`
- Modificar: `tests/test_harness_authorization.py`

- [ ] **Passo 1: medir o tamanho do buraco**

Escreva um script em `scratchpad/` (não commite) que, para cada uma das 44
tools, extraia do `inputSchema` os parâmetros cujo nome ou descrição indique
caminho de filesystem. Rode e anote quantas são, por classe de `tool_class()`.

O número conhecido é **31 das 32 `READ_ONLY`** — `sparkforge_rules_lookup` é a
única sem entrada de caminho. Confirme e estenda às outras classes.

- [ ] **Passo 2: escrever o teste da decisão**

`authorize()` passa a aceitar `arguments` opcional, e a decisão recusa quando o
caminho escapa da raiz do case:

```python
def test_autorizacao_recusa_caminho_fora_da_raiz(tmp_path):
    """A cadeia autorizava um NOME; agora ela ve a CHAMADA.

    O limite estava declarado em AUTHORIZATION-CHAIN.md com medicao: uma tool
    READ_ONLY com `path` arbitrario leu segredo de fora do repositorio sob perfil
    OFFLINE. A classe da tool nao muda -- ler continua sendo READ_ONLY. O que
    muda e que o argumento entra na decisao.
    """
    decisao = authorize(
        agent="a",
        tool="sparkforge_analyze_pyspark",
        allowed_tools=["sparkforge_analyze_pyspark"],
        profile=ExecutionProfile.ECO,
        arguments={"path": "../../../etc/passwd"},
        root=tmp_path,
    )
    assert decisao.authorized is False
    assert "fora da raiz" in decisao.reason


def test_autorizacao_aceita_caminho_dentro_da_raiz(tmp_path):
    (tmp_path / "job.py").write_text("x = 1\n", encoding="utf-8")
    decisao = authorize(
        agent="a",
        tool="sparkforge_analyze_pyspark",
        allowed_tools=["sparkforge_analyze_pyspark"],
        profile=ExecutionProfile.ECO,
        arguments={"path": str(tmp_path / "job.py")},
        root=tmp_path,
    )
    assert decisao.authorized is True


def test_sem_arguments_a_decisao_continua_como_antes(tmp_path):
    """Compatibilidade: quem nao passa `arguments` nao muda de comportamento."""
    decisao = authorize(
        agent="a",
        tool="sparkforge_analyze_pyspark",
        allowed_tools=["sparkforge_analyze_pyspark"],
        profile=ExecutionProfile.ECO,
    )
    assert decisao.authorized is True
    assert decisao.checked_arguments is False
```

- [ ] **Passo 3: rodar e ver falhar**

```
python -m pytest tests/test_harness_authorization.py -q -k caminho
```
Esperado: FALHA — `authorize()` não aceita `arguments`.

- [ ] **Passo 4: implementar**

`authorize()` ganha `arguments: dict[str, Any] | None = None` e
`root: Path | None = None`, keyword-only, ambos default `None`.
`AuthorizationDecision` ganha `checked_arguments: bool`, que declara se a
verificação **aconteceu** — sem esse campo, uma decisão sem `arguments` seria
indistinguível de uma decisão que verificou e aprovou.

A verificação reusa o algoritmo que já existe em
`sparkforge/rules/loader.py:safe_catalog_file`. **Não reimplemente** — extraia o
algoritmo para uma função compartilhada e faça `safe_catalog_file` chamá-la, ou
importe-a. Duas implementações de confinamento de caminho seriam o mesmo defeito
que a Task 3 acabou de fechar para segredo.

- [ ] **Passo 5: rodar e medir a mutação**

```
python -m pytest tests/test_harness_authorization.py -q
python -m pytest tests/ -q
```

Depois, teste de mutação: apague a verificação de contenção e confirme que os
testes **pegam**. Se sobreviverem, o teste não prova o que diz.

- [ ] **Passo 6: registrar a decisão**

Em `docs/harness/AUTHORIZATION-CHAIN.md`, substitua a seção do limite declarado
pela decisão tomada, com a medição do Passo 1. Diga explicitamente o que
**continua** fora: `authorize()` ver o caminho não impede a tool de receber um
caminho por outro meio, porque **nada chama `authorize()`** nos quatro caminhos
de execução (`adapters/mcp.py`, `adapters/tools.py`, `adapters/cli.py`,
`agents/supervisor.py`). Isso continua sendo o gap do hook `PreToolUse`, e ele
não fecha nesta fase.

Atualize a linha correspondente em `docs/harness/CURRENT-HARNESS-GAP.md`.

- [ ] **Passo 7: commit**

```bash
git add sparkforge/agents/autonomy.py sparkforge/rules/loader.py tests/test_harness_authorization.py docs/harness/
git commit -m "feat(harness): a cadeia de autorizacao passa a ver o argumento"
```

---

## Recusas declaradas

Registradas aqui para que ninguém as reabra sem revogar a decisão por escrito.

**Não escrevemos um quinto empacotador de contexto.** Já existem três
(`ContextFunnel.build_minimal_context`, `tools/context.py:pack_context`,
`agents/budget.py:select_context`) e quatro estimadores de token. Somar um
quarto empacotador na superfície mais cara do sistema repetiria o defeito que a
Task 3 acabou de fechar para detector de segredo.

**Não mudamos o default de `detail_level` para `summary`.** O §12 do prompt de
evolução pedia isso. Mudar o default muda a saída de todo chamador existente e
de todo golden; é decisão de contrato, separada da de capacidade. A capacidade
entra agora; o default muda quando houver medição de que nenhum consumidor
depende de `full`.

**Não afirmamos economia em tokens.** Só em bytes, medidos. Os quatro
estimadores do repositório são `len/4` e divergem entre si no arredondamento.

**Não tratamos a viabilidade do Tier 0 como resolvida.** `FTS5` e `blake2b`
foram medidos em Python 3.14.6 nesta workstation; o `pyproject.toml` declara
`>=3.10` e o CI roda 3.10/3.11. Nada no repositório mede FTS5 nas versões
suportadas, e o módulo `ast` mudou no intervalo (`ast.Str` e `ast.Num` saíram em
3.12). Antes de o índice depender disso, ou o piso sobe deliberadamente, ou a
matriz de CI passa a medir.

---

## O que vem no segundo plano

Depois que J0–J2 fecharem e a medição de J1 estiver provada:

| Fase | Conteúdo | Pré-condição |
|---|---|---|
| J3 | Banco, schema, índice completo e incremental, FTS | J0 inteira |
| J4 | Recuperação, ranking, `ContextPack` consolidando os três empacotadores | J3 + a medição de J1 |
| J5 | Superfície nova de tool, o mínimo possível | J4 |

A extração **não** ganha fase própria, ao contrário do que a SPEC propõe: ela já
existe com golden por fixture, e o que falta (classe, import, qualified name) é
incremento sobre varredura pronta.
