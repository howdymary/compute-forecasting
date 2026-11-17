"""Paired origin-block sensitivity, never treating seeds/contracts as new dates."""
import random,statistics
from .market_state_v19 import quantile
def paired(cells,candidate,reference,block_lengths=(2,4),replicates=2000,seed=20261117):
    by={}
    for r in cells:
        if r["horizon_days"]!=7 or r["method"] not in (candidate,reference):continue
        key=(r["origin"],r["series_id"]);by.setdefault(key,{})[r["method"]]=r["loss"]
    origins={}
    for (origin,sid),methods in sorted(by.items()):
        if set(methods)!={candidate,reference}:continue
        origins.setdefault(origin,[]).append(methods[candidate]-methods[reference])
    dates=sorted(origins);n=len(dates);total=sum(map(len,origins.values()))
    if not n:return {"status":"pending_compatible_pairs","n_origins":0,"cells":0,"estimate":None}
    estimate=sum(sum(origins[d]) for d in dates)/total
    result={"status":"descriptive_final_analysis","contrast":candidate+" minus "+reference,"estimate":estimate,"n_origins":n,"cells":total,"origin_counts":{d:len(origins[d]) for d in dates},"block_sensitivity":{}}
    for length in block_lengths:
        if n<length:result["block_sensitivity"][str(length)]=None;continue
        rng=random.Random(seed+length);samples=[]
        for _ in range(replicates):
            indices=[]
            while len(indices)<n:
                start=rng.randrange(n);indices.extend((start+j)%n for j in range(length))
            chosen=[dates[i] for i in indices[:n]];samples.append(sum(sum(origins[d]) for d in chosen)/sum(len(origins[d]) for d in chosen))
        result["block_sensitivity"][str(length)]={"lower":quantile(samples,.025),"upper":quantile(samples,.975),"replicates":replicates}
    result["limitation"]="Dependent origins, common shocks and a small panel; bootstrap sensitivity is not a coverage guarantee. No automatic promotion."
    return result
