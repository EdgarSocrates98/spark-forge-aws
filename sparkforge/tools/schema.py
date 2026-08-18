def compare_json_schemas(before, after):
    bp=before.get("properties",{}) or {}; ap=after.get("properties",{}) or {}
    added=sorted(set(ap)-set(bp)); removed=sorted(set(bp)-set(ap))
    changed=sorted(k for k in set(bp)&set(ap) if bp[k].get("type")!=ap[k].get("type"))
    breq=set(before.get("required",[]) or []); areq=set(after.get("required",[]) or [])
    return {"added":added,"removed":removed,"type_changed":changed,"required_added":sorted(areq-breq),"required_removed":sorted(breq-areq),"compatible":not removed and not changed and not (areq-breq)}
