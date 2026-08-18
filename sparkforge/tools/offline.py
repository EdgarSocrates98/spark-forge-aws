"""Indice de conhecimento local, verificavel sem rede.

A garantia offline nao e "tem arquivo no disco": e "o arquivo no disco e o que
o manifest diz que e". Por isso `verify` confere SHA-256 documento a documento
e devolve a lista do que falhou, com a causa separada entre ausencia e
divergencia de conteudo -- as duas exigem acao diferente de quem opera.

`search` e busca por frequencia de termo, deliberadamente burra e deterministica:
sem indice invertido, sem embedding, sem chamada externa. O que ela devolve e
ponto de partida para leitura, nao resposta.
"""
import hashlib
import json
import re
from pathlib import Path

_TERM_RE = re.compile(r"[A-Za-z0-9_-]{3,}")


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
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
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
