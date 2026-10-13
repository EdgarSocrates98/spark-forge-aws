"""Indice de conhecimento local, verificavel sem rede.

A garantia offline nao e "tem arquivo no disco": e "o arquivo no disco e o que
o manifest diz que e". Por isso `verify` confere SHA-256 documento a documento
e devolve a lista do que falhou, com a causa separada entre ausencia e
divergencia de conteudo -- as duas exigem acao diferente de quem opera.

O hash e tirado do conteudo SEM OS BYTES CR, nunca dos
bytes crus, e isso foi medido: os 43 documentos sao markdown que o git converte
na saida (`core.autocrlf`), entao o mesmo commit tem CRLF no Windows e LF no
Linux. Hash sobre byte cru so vale na maquina onde foi gravado -- o manifest
gravado no Windows reprovava os 43 documentos no `ubuntu-latest` do CI, com a
arvore intacta. Normalizacao de fim de linha feita pelo proprio git nao e
adulteracao, e um gate que a acusa como tal nao tem como ser ligado. Qualquer
outra diferenca de byte continua reprovando.

`search` e busca por frequencia de termo, deliberadamente burra e deterministica:
sem indice invertido, sem embedding, sem chamada externa. O que ela devolve e
ponto de partida para leitura, nao resposta.
"""
import hashlib
import json
import re
from pathlib import Path

_TERM_RE = re.compile(r"[A-Za-z0-9_-]{3,}")


def _content_sha256(path: Path) -> str:
    """SHA-256 do conteudo com todo CR removido.

    Remover o CR em vez de traduzir `CRLF` para `LF` nao e preguica, e o unico
    jeito estavel: `knowledge/model-selection-observability.md` tem 25
    sequencias `CR CR LF` -- blob commitado ja com CRLF, convertido de novo no
    checkout do Windows. Traduzir `CRLF` para `LF` devolve `LF LF` ali e `LF`
    no Linux, e o hash volta a depender da plataforma. Remover CR devolve `LF`
    nos dois.

    Publica para que quem regravar o manifest use exatamente esta funcao: hash
    calculado de um jeito e conferido de outro e o defeito que o gate existe
    para pegar.
    """
    raw = path.read_bytes().replace(b"\r", b"")
    return hashlib.sha256(raw).hexdigest()


class OfflineKnowledgeIndex:
    def __init__(self, repo="."):
        self.repo = Path(repo)
        self.manifest_path = self.repo / "knowledge" / "offline-manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def verify(self):
        failed = []
        checked = 0
        for item in self.manifest.get("documents", []):
            path = self.repo / item["path"]
            checked += 1
            if not path.exists():
                failed.append({"path": item["path"], "reason": "missing"})
                continue
            actual = _content_sha256(path)
            if actual != item["sha256"]:
                failed.append({"path": item["path"], "reason": "checksum"})
        return {"offline": True, "checked": checked, "failed": failed, "ok": not failed}

    def search(self, query, limit=5):
        terms = [x.lower() for x in _TERM_RE.findall(query)]
        results = []
        for item in self.manifest.get("documents", []):
            path = self.repo / item["path"]
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            low = text.lower()
            score = sum(low.count(t) for t in terms)
            if score:
                results.append(
                    {
                        "path": item["path"],
                        "title": item.get("title", path.stem),
                        "score": score,
                        "excerpt": " ".join(text[:300].split()),
                        "offline": True,
                    }
                )
        return sorted(results, key=lambda x: (-x["score"], x["path"]))[:limit]
