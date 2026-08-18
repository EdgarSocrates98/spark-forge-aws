import re

def extract_lineage_edges(text):
    edges=[]
    for m in re.finditer(r"s3://[^\s\"`,)]+",text): edges.append({"kind":"s3","name":m.group(0),"direction":"read","offset":m.start()})
    for m in re.finditer(r"(?:from|into|join|table)\s+([A-Za-z_][\w.-]*(?:\.[A-Za-z_][\w.-]*)?)",text,re.I):
        edges.append({"kind":"table","name":m.group(1),"direction":"read" if m.group(0).lower().startswith(("from","join")) else "write","offset":m.start()})
    return sorted({(e["kind"],e["name"],e["direction"]):e for e in edges}.values(),key=lambda e:(e["kind"],e["name"]))
