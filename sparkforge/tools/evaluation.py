def _ids(value):
    if isinstance(value,dict): value=value.get("findings",value.get("rules",[]))
    if not isinstance(value,list): return set()
    return {str(x if isinstance(x,str) else x.get("id",x.get("rule_id",""))) for x in value}

def evaluate_golden_case(expected,actual):
    exp,got=_ids(expected),_ids(actual)
    return {"passed":exp==got,"expected":sorted(exp),"actual":sorted(got),"missing":sorted(exp-got),"unexpected":sorted(got-exp),"match_rate":1.0 if exp==got else len(exp&got)/max(1,len(exp|got))}
