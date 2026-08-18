from sparkforge.tools import OfflineKnowledgeIndex
import json
result=OfflineKnowledgeIndex('.').verify()
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['ok'] else 1)
