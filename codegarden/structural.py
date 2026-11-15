"""Small structural baselines; never an assumption that a family preserves D2."""
import hashlib,json,pathlib,random,sys,time
def run(S,D,L):
    start=time.perf_counter();inc=S.Incidence(16);rows=[];witnesses={}
    def checked(name,code):
        words=sorted(format(w,"016b") for w in code)
        verification={"descendant":D.verify(words,16),"lcs":L.verify(words,16)}
        assert all(v["valid"] for v in verification.values())
        witnesses[name]=words;return {"cardinality":len(words),"verification":verification}
    classes=[[] for _ in range(17)]
    for w in range(65536):
        syndrome=sum((i+1)*((w>>i)&1) for i in range(16))%17;classes[syndrome].append(w)
    vt_best=[];vt_parameters=None
    for syndrome,pool in enumerate(classes):
        for seed in [4101,4102,4103]:
            code=inc.greedy(random.Random(seed),pool=pool,priority="small_desc")
            rows.append({"family":"VT-syndrome restriction","syndrome":syndrome,"seed":seed,
              "candidate_pool_sha256":S.pool_hash(pool),"size_unverified":len(code)})
            if len(code)>len(vt_best):vt_best=code;vt_parameters={"syndrome":syndrome,"seed":seed}
    vt=checked("worker_structural_vt",vt_best);vt["parameters"]=vt_parameters
    families={}
    reverse8=lambda x:int(format(x,"08b")[::-1],2)
    for name,pool in {
      "repeated_half":[(x<<8)|x for x in range(256)],
      "mirror_half":[(x<<8)|reverse8(x) for x in range(256)],
      "complement_mirror_half":[(x<<8)|(reverse8(x)^255) for x in range(256)]
    }.items():
        candidates=[inc.greedy(random.Random(seed),pool=pool,priority="small_desc") for seed in [4201,4202,4203]]
        families[name]=checked("worker_structural_"+name,max(candidates,key=len))
        families[name]["candidate_pool_sha256"]=S.pool_hash(pool)
    short=S.Incidence(8)
    component=max((short.greedy(random.Random(seed),priority="small_desc") for seed in range(4300,4320)),key=len)
    component_words=[format(w,"08b") for w in component]
    component_verification={"descendant":D.verify(component_words,8),"lcs":L.verify(component_words,8)}
    product=checked("worker_structural_product",[(a<<8)|b for a in component for b in component])
    result={"scope":"Exploratory structural baselines, not record candidates or universal family optima",
      "VT":{"definition":"sum((i+1)*bit_i for i=0..15) modulo 17; LSB indexing; greedy D2 packing inside each class",
        "inspiration":"VT-family single-deletion discussion in Weindel-Heckel; no claim that the whole class corrects two deletions",
        "runs":rows,"best":vt},
      "structured_families":families,
      "recursive_product":{"component_length":8,"component_size":len(component),"component_words":component_words,
        "component_verification":component_verification,"length16_result":product,
        "why_valid":"The first six received bits belong to D2 of the prefix component, and the last six to D2 of the suffix component; both component words are uniquely determined."},
      "actual_wall_seconds":time.perf_counter()-start,"global_optimality_claim":False}
    return result,witnesses
def main():
    ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
    import search as S
    from training_cases import D,L
    result,witnesses=run(S,D,L);result["source_sha256"]=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    out=ROOT/"artifacts/structural";out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").write_text(json.dumps(result,indent=2))
    for name,words in witnesses.items():(out/(name+".txt")).write_text("\n".join(words)+"\n")
    print(json.dumps({name:len(words) for name,words in witnesses.items()}))
if __name__=="__main__":main()
