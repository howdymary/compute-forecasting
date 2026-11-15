"""Small-length, genuinely verified strategy examples. Never a length-16 record."""
import importlib.util,json,pathlib,random,sys,time
ROOT=pathlib.Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
S=module("cg_training_search",ROOT/"search.py")
D=module("cg_training_desc",ROOT/"protected/verify_descendants.py")
L=module("cg_training_lcs",ROOT/"protected/verify_lcs.py")
ACTIONS=["random8greedy","random16greedy","structural24greedy","opportunity12exact",
 "random24exact","conflict8exact","random40greedy","structural48exact","opportunity6ejection"]
def act(inc,code,index,seed):
    rng=random.Random(seed);arm=S.ARMS[index];removed=S.select_removed(inc,code,rng,arm.size,arm.mode)
    fixed=[w for w in code if w not in removed];pool=inc.compatible_pool(fixed)
    if len(pool)>120:
        other=[w for w in pool if w not in removed];rng.shuffle(other);other.sort(key=lambda w:inc.sizes[w])
        pool=sorted(removed|set(other[:120-len(removed)]))
    start=time.perf_counter();best=inc.greedy(rng,fixed,pool,"small_desc")
    # Same stated upper time budget; report actual runtime separately.
    for _ in range(2):
        trial=inc.greedy(rng,fixed,pool,"random")
        if len(trial)>len(best):best=trial
    status={"status":"NOT_RUN"}
    if arm.repair=="exact" and len(best)<=len(code):
        repair,status=S.exact_repair(inc,pool,len(removed)+1,removed,seconds=.025,node_limit=15000)
        if len(fixed)+len(repair)>len(best):best=fixed+repair
    if len(best)<len(code):best=list(code)
    words=[format(w,"0%db"%inc.n) for w in best]
    verification=D.verify(words,inc.n);independent=L.verify(words,inc.n)
    assert verification["valid"] and independent["valid"]
    return best,{"action":ACTIONS[index],"cardinality":len(best),"actual_seconds":time.perf_counter()-start,
      "verification":verification,"lcs":independent,"exact":status,"pool_sha256":S.pool_hash(pool),
      "pool_restriction":"removed plus at most 120 total candidates, smallest descendant size with seeded ties"}
def build():
    instances={n:S.Incidence(n) for n in [10,11,12]};cases=[]
    for split,count,offset in [("train",32,1000),("heldout",8,2000)]:
        for i in range(count):
            n=10+i%3;inc=instances[n];seed=offset+i;rng=random.Random(seed)
            code=inc.greedy(rng,priority="random")
            state={"length":n,"starting_cardinality":len(code),"occupied_descendants":inc.occupied(code).bit_count(),
              "weight_histogram":[sum(w.bit_count()==k for w in code) for k in range(n+1)],
              "stagnation_cycles":0}
            scores=[]
            for a in range(len(ACTIONS)):
                _,report=act(inc,code,a,seed*100+a);scores.append(report)
            chosen=max(range(len(ACTIONS)),key=lambda a:(scores[a]["cardinality"],-a))
            cases.append({"case_id":str(seed),"seed":seed,"split":split,"length":n,"state":state,
              "starting_words":[format(w,"0%db"%n) for w in code],"action":ACTIONS[chosen],
              "verified":True,"scores":scores})
    return {"scope":"small_length_policy_calibration_only","cases":cases,
      "split":"32 fresh train seeds; 8 disjoint heldout seeds; no length-16 performance implication",
      "resource_limit":"bounded candidate pool and .025-second exact limit; actual times differ and are reported"}
