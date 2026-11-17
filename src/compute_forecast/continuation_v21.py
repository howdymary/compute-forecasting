"""Frozen categorical continuation contracts; all model inputs reuse v19 unchanged."""
import collections,math,random,statistics
from .probability_v18 import digest,support,bin_index
from .market_state_v19 import check_asof,decision,datum
def task_key(t):return t["task_id"]
def validate_training(tasks,p):
    seen=set()
    for t in tasks:
        if t["task_id"] in seen:raise ValueError("Duplicate training task")
        seen.add(t["task_id"]);check_asof(t["context"],t["origin"])
        if t["origin"]>p["data"]["train_origins_through"] or max(t["target_dates"])>p["data"]["train_labels_through"]:raise ValueError("Training label maturity cutoff")
        if any(not math.isfinite(y) or y<=0 for y in t["outcomes"]):raise ValueError("Invalid training outcome")
        if any(x[:10]>p["data"]["train_labels_through"] for x in t.get("target_available_at",[])):raise ValueError("Label source timestamp exceeds cutoff")
    return seen
def counts(tasks,levels):
    qerrors=[];outside=0
    for t in tasks:
        z=support(t["anchor"],levels)
        for y in t["outcomes"]:
            outside+=y<z[0] or y>z[-1];qerrors.append(abs(y-z[bin_index(z,y)])/t["anchor"])
    normalized=[digest({"series":t["series_id"],"relative_history":[round(math.log(r["value"]/t["anchor"]),8) for r in t["context"]],"missing":t["context_missing_days"]}) for t in tasks]
    return {"windows":len(tasks),"horizon_examples":3*len(tasks),"groups":len({t["series_id"] for t in tasks}),"providers":len({t["metadata"]["provider"] for t in tasks}),"origins":sorted({t["origin"] for t in tasks}),"families":dict(collections.Counter(t["metadata"]["family"] for t in tasks)),"sources":dict(collections.Counter(t["metadata"]["source_id"] for t in tasks)),"instruments":dict(collections.Counter(t["metadata"]["instrument_class"] for t in tasks)),"changed_7d":sum(t["anchor"]!=t["outcomes"][2] for t in tasks),"flat_7d":sum(t["anchor"]==t["outcomes"][2] for t in tasks),"context_missing_days":sum(t["context_missing_days"] for t in tasks),"normalized_context_patterns":len(set(normalized)),"repeated_normalized_contexts":len(tasks)-len(set(normalized)),"out_of_support":outside,"out_of_support_fraction":outside/len(qerrors) if qerrors else None,"mean_relative_quantization_error":statistics.mean(qerrors) if qerrors else None,"max_relative_quantization_error":max(qerrors,default=None),"independence":"Windows, shared contracts, overlapping horizons and market shocks are dependent"}
def batches(tasks,seed,updates,batch_size,offset):
    records=[(t,h) for t in tasks for h in (1,3,7)]
    if not records:raise ValueError("Empty corpus")
    stream=[];epoch=0;needed=offset+updates*batch_size
    while len(stream)<needed:
        order=list(range(len(records)));random.Random(seed+epoch*1000003).shuffle(order)
        stream.extend(order);epoch+=1
    indices=stream[offset:needed]
    return [[records[i] for i in indices[j:j+batch_size]] for j in range(0,len(indices),batch_size)]
def batch_identity(plan):
    return digest([[(t["task_id"],h) for t,h in group] for group in plan])
def selection(checkpoints):
    return min(checkpoints,key=lambda c:(c["development"]["primary_pinball"],c["update"]))
def expansion_gate(runs,incumbent):
    eligible=[r for r in runs if r["status"]=="completed"]
    passing=[r["arm"] for r in eligible if r["selected"]["update"]>0 and r["selected"]["development"]["primary_pinball"]<=.98*incumbent and r["selected"]["development"]["failures"]==0]
    values={r["arm"]:r["selected"]["development"]["primary_pinball"] for r in eligible}
    return {"passed":bool(passing),"passing_arms":passing,"incumbent_loss":incumbent,"development_losses":values,"data_effect_screen":values.get("expanded") is not None and values.get("same") is not None and values["expanded"]<=.98*values["same"],"threshold":.98,"statistical_claim":False}
