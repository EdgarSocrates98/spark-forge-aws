import hashlib, json, re
from pathlib import Path

class OfflineKnowledgeIndex:
    def __init__(self,repo="."):
        self.repo=Path(repo); self.manifest_path=self.repo/"knowledge"/"offline-manifest.json"; self.manifest=json.loads(self.manifest_path.read_text(encoding="utf-8"))
    def verify(self):
        failed=[]; checked=0
        for item in self.manifest.get("documents",[]):
            path=self.repo/item["path"]; checked+=1
            if not path.exists(): failed.append({"path":item["path"],"reason":"missing"}); continue
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            if actual!=item["sha256"]: failed.append({"path":item["path"],"reason":"checksum"})
        return {"offline":True,"checked":checked,"failed":failed,"ok":not failed}
    def search(self,query,limit=5):
        terms=[x.lower() for x in re.findall(r"[A-Za-z0-9_-]{3,}",query)]; results=[]
        for item in self.manifest.get("documents",[]):
            path=self.repo/item["path"]
            if not path.exists(): continue
            text=path.read_text(encoding="utf-8",errors="replace"); low=text.lower(); score=sum(low.count(t) for t in terms)
            if score: results.append({"path":item["path"],"title":item.get("title",path.stem),"score":score,"excerpt":" ".join(text[:300].split()),"offline":True})
        return sorted(results,key=lambda x:(-x["score"],x["path"]))[:limit]
