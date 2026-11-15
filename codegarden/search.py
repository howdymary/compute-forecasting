"""Set-packing search. Integer kernels are independent of protected string verification."""
from __future__ import annotations
import argparse, array, hashlib, json, math, random, time
from dataclasses import dataclass

def canonical(words,n=16):
    return "".join(format(w,"0%db"%n)+"\n" for w in sorted(words))
def digest_words(words,n=16):
    return hashlib.sha256(canonical(words,n).encode()).hexdigest()
def pool_hash(pool):
    return hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in sorted(pool))).hexdigest()
def delete_bit(x,p):
    return ((x>>(p+1))<<p)|(x&((1<<p)-1))

class Incidence:
    def __init__(self,n=16):
        self.n=n;self.N=1<<n;self.M=1<<(n-2)
        start=time.perf_counter()
        singles=[tuple(set(delete_bit(x,p) for p in range(n-1))) for x in range(1<<(n-1))]
        self.desc=[];self.masks=[];self.children=[array.array("I") for _ in range(self.M)]
        for x in range(self.N):
            ds=tuple(sorted({z for p in range(n) for z in singles[delete_bit(x,p)]}))
            self.desc.append(ds);self.masks.append(sum(1<<d for d in ds))
            for d in ds:self.children[d].append(x)
        self.precompute_seconds=time.perf_counter()-start
        self.sizes=[len(d) for d in self.desc]
    def occupied(self,code):
        mask=0
        for x in code:
            if mask & self.masks[x]:raise ValueError("invalid search state")
            mask |= self.masks[x]
        return mask
    def compatible_pool(self,fixed):
        mask=self.occupied(fixed)
        return [x for x,m in enumerate(self.masks) if not m&mask]
    def blockers(self,code):
        out=[0]*self.N
        for i,x in enumerate(code):
            bit=1<<i
            for d in self.desc[x]:
                for w in self.children[d]:out[w]|=bit
        return out
    def greedy(self,rng,fixed=(),pool=None,priority="random"):
        code=list(fixed);mask=self.occupied(code)
        order=list(range(self.N)) if pool is None else list(pool)
        rng.shuffle(order)
        if priority=="small_desc":order.sort(key=lambda x:self.sizes[x]+rng.random()*6)
        elif priority=="large_desc":order.sort(key=lambda x:-self.sizes[x]+rng.random()*6)
        elif priority=="weight":order.sort(key=lambda x:abs(x.bit_count()-self.n/2)+rng.random()*3)
        for x in order:
            if not self.masks[x]&mask:code.append(x);mask|=self.masks[x]
        return code

def exact_repair(inc,pool,target,seed_code=(),seconds=.25,node_limit=100000):
    """Decision B&B for a target clique in the compatibility graph of this pool ONLY."""
    start=time.perf_counter();deadline=start+seconds
    pool=sorted(pool);k=len(pool);position={w:i for i,w in enumerate(pool)}
    adjacency=[0]*k
    for i,x in enumerate(pool):
        mx=inc.masks[x]
        for j in range(i):
            if not mx&inc.masks[pool[j]]:
                adjacency[i]|=1<<j;adjacency[j]|=1<<i
    best=[position[w] for w in seed_code if w in position]
    if len(best)>=target:
        return list(seed_code),{"status":"FEASIBLE","nodes":0,"complete":False,"seconds":time.perf_counter()-start}
    nodes=0;interrupted=False;found=False
    def colors(P):
        order=[];bounds=[];color=0
        while P:
            color+=1;Q=P
            while Q:
                bit=Q&-Q;v=bit.bit_length()-1
                P^=bit;Q^=bit;Q&=~adjacency[v]
                order.append(v);bounds.append(color)
        return order,bounds
    def expand(P,chosen):
        nonlocal nodes,best,interrupted,found
        nodes+=1
        if nodes>=node_limit or time.perf_counter()>=deadline:interrupted=True;return
        if len(chosen)>len(best):best=chosen[:]
        if len(best)>=target:found=True;return
        order,bounds=colors(P)
        for i in range(len(order)-1,-1,-1):
            if len(chosen)+bounds[i]<target:return
            v=order[i];expand(P&adjacency[v],chosen+[v])
            if found or interrupted:return
            P&=~(1<<v)
    expand((1<<k)-1,[])
    status="FEASIBLE" if found else "TIMEOUT_NO_IMPROVEMENT" if interrupted else "INFEASIBLE_STRICT_IMPROVEMENT"
    return [pool[i] for i in best],{"status":status,"nodes":nodes,"complete":not interrupted and not found,
        "proof_artifact":None,"proof_kind":"deterministic_branch_and_bound_execution_log" if not interrupted and not found else None,
        "seconds":time.perf_counter()-start}

def select_removed(inc,code,rng,size,mode):
    size=min(size,len(code))
    if mode=="random":return set(rng.sample(code,size))
    if mode=="structural":
        w=rng.choice(code).bit_count()
        return set(sorted(code,key=lambda x:abs(x.bit_count()-w)+rng.random()*.3)[:size])
    if mode=="opportunity":
        blockers=inc.blockers(code)
        options=[x for x,b in enumerate(blockers) if 1<=b.bit_count()<=size and x not in code]
        if options:
            pivot=rng.choice(options);bits=blockers[pivot]
            removed={code[i] for i in range(len(code)) if bits>>i&1}
            remaining=[x for x in code if x not in removed]
            removed.update(rng.sample(remaining,min(size-len(removed),len(remaining))))
            return removed
    if mode=="conflict":
        blockers=inc.blockers(code);pressure=[0]*len(code)
        for b in blockers:
            if 1<=b.bit_count()<=4:
                while b:
                    bit=b&-b;pressure[bit.bit_length()-1]+=1;b^=bit
        return set(code[i] for i in sorted(range(len(code)),key=lambda i:pressure[i]+rng.random()*10,reverse=True)[:size])
    return set(rng.sample(code,size))

@dataclass
class Arm:
    mode:str
    size:int
    repair:str

ARMS=[Arm("random",8,"greedy"),Arm("random",16,"greedy"),Arm("structural",24,"greedy"),
      Arm("opportunity",12,"exact"),Arm("random",24,"exact"),Arm("conflict",8,"exact"),
      Arm("random",40,"greedy"),Arm("structural",48,"exact"),Arm("opportunity",6,"ejection")]

def run(inc,starting,seed=0,seconds=30,policy="adaptive",max_pool=600,emit=None,max_cycles=120):
    rng=random.Random(seed);start=time.perf_counter();deadline=start+seconds
    current=list(starting);best=list(starting);archive={digest_words(best,inc.n):best[:]}
    history=[];counts=[0]*len(ARMS);rewards=[0.]*len(ARMS);seen=set();stale=0;cycle=0
    while time.perf_counter()<deadline and cycle<max_cycles:
        if policy=="fixed":a=1
        else:
            unused=[i for i,c in enumerate(counts) if not c]
            a=unused[0] if unused else max(range(len(ARMS)),key=lambda i:rewards[i]/counts[i]+math.sqrt(2*math.log(cycle+1)/counts[i]))
        arm=ARMS[a];cycle+=1;counts[a]+=1
        # A deteriorated path is restarted from a retained, structurally distinct incumbent.
        if stale and stale%25==0:
            current=list(rng.choice(list(archive.values())));stale=0
        old=current[:];removed=select_removed(inc,old,rng,min(96,arm.size+(stale//40)*8) if policy=="adaptive" else arm.size,arm.mode)
        fixed=[x for x in old if x not in removed];pool=inc.compatible_pool(fixed)
        full_count=len(pool);restriction=None
        if len(pool)>max_pool:
            other=[x for x in pool if x not in removed]
            rng.shuffle(other);other.sort(key=lambda x:inc.sizes[x])
            pool=sorted(removed|set(other[:max(0,max_pool-len(removed))]))
            restriction="removed words plus smallest-descendant candidates after seeded random tie-break; capped"
        ident=(digest_words(old,inc.n),pool_hash(pool),arm.repair)
        if ident in seen:
            history.append({"cycle":cycle,"status":"DUPLICATE_SKIPPED","arm":a});stale+=1;continue
        seen.add(ident);beg=time.perf_counter()
        options=[inc.greedy(rng,fixed,pool,"small_desc") for _ in range(3)]
        options.append(inc.greedy(rng,fixed,pool,"random"))
        forced_pivots=[]
        if arm.repair=="ejection":
            pivots=[x for x in pool if x not in removed]
            rng.shuffle(pivots)
            for pivot in pivots[:8]:
                forced_pivots.append(pivot)
                options.append(inc.greedy(rng,fixed+[pivot],pool,"small_desc"))
        candidate=max(options,key=len)
        exact={"status":"NOT_RUN","complete":False}
        if arm.repair=="exact" and len(candidate)<=len(old) and time.perf_counter()<deadline:
            repaired,exact=exact_repair(inc,pool,len(removed)+1,removed,
                                      seconds=min(.4,max(.001,deadline-time.perf_counter())),node_limit=60000)
            if len(fixed)+len(repaired)>len(candidate):candidate=fixed+repaired
        elapsed=time.perf_counter()-beg
        # Plateau moves preserve cardinality; limited downhill exploration is explicit.
        accepted=len(candidate)>=len(old) or (len(candidate)>=len(best)-2 and rng.random()<.03)
        if accepted:current=candidate
        gain=max(0,len(candidate)-len(best));rewards[a]+=gain/max(elapsed,.001)
        h=digest_words(candidate,inc.n)
        if len(candidate)>=len(best)-1:archive[h]=candidate[:]
        if len(archive)>24:
            keep=sorted(archive,key=lambda h:len(archive[h]),reverse=True)[:12]
            archive={h:archive[h] for h in keep}
        improved=len(candidate)>len(best)
        if improved:best=candidate[:];stale=0
        else:stale+=1
        event={"cycle":cycle,"seed":seed,"policy":policy,"arm":a,"removal_mode":arm.mode,
               "destruction_size":len(removed),"repair":arm.repair,"incumbent_sha256":digest_words(old,inc.n),
               "fixed_outside_sha256":digest_words(fixed,inc.n),"candidate_pool_sha256":pool_hash(pool),
               "candidate_pool_size":len(pool),"full_compatible_pool_size":full_count,"restriction":restriction,
               "fixed_outside":sorted(fixed),"candidate_pool":sorted(pool),"removed":sorted(removed),"forced_ejection_pivots":forced_pivots,
               "before":len(old),"candidate":len(candidate),"best":len(best),"accepted":accepted,
               "exact":exact,"seconds":elapsed,"best_changed":improved}
        history.append(event)
        if emit and (improved or cycle%50==0):emit({k:v for k,v in event.items() if k not in {"fixed_outside","candidate_pool","removed"}})
    return {"best":best,"archive":list(archive.values()),"history":history,"seed":seed,"policy":policy,
            "wall_seconds":time.perf_counter()-start,"arms":[a.__dict__ for a in ARMS],
            "arm_counts":counts,"arm_reward_rates":rewards,"cycles":cycle,
            "llm_strategy_decisions":False,"adaptive_kind":"empirical_UCB_operator_selection",
            "limitation":"Best and per-experiment scores require independent verifier acceptance; local results are not global proofs."}

def main():
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument("--start",required=True);p.add_argument("--seconds",type=float,default=30)
    p.add_argument("--seed",type=int,default=0);p.add_argument("--policy",choices=["fixed","adaptive"],default="adaptive")
    p.add_argument("--output",default="codegarden/artifacts/run.json");p.add_argument("--cycles",type=int,default=120);a=p.parse_args()
    words=Path(a.start).read_text().splitlines();inc=Incidence(len(words[0]))
    result=run(inc,[int(w,2) for w in words],a.seed,a.seconds,a.policy,max_cycles=a.cycles)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result))
    witness=Path(a.output).with_suffix(".txt");witness.write_text(canonical(result["best"],inc.n))
    print(json.dumps({"best_size_unverified":len(result["best"]),"witness":str(witness),"cycles":result["cycles"]}))
if __name__=="__main__":main()
