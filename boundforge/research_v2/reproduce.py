"""Bounded replay of official FunSearch constructions, NOT reproduction of its LLM training/search."""
import ast,hashlib,itertools,json,pathlib,time,urllib.request
import numpy as np
HERE=pathlib.Path(__file__).resolve().parent
SHA="cc53f274237d7ab05c19df939edbc1f9616a7c19"
URL=f"https://raw.githubusercontent.com/google-deepmind/funsearch/{SHA}/cap_set/cap_set.ipynb"
def exact_check(vectors):
    pts=[tuple(map(int,v)) for v in vectors]
    assert len(set(pts))==len(pts)
    S=set(pts)
    assert all(len(p)==8 and all(x in (0,1,2) for x in p) for p in pts)
    for i,p in enumerate(pts):
        for q in pts[:i]:
            assert tuple((-a-b)%3 for a,b in zip(p,q)) not in S
    return True
def main():
    out=HERE/"evidence";out.mkdir(exist_ok=True)
    raw=urllib.request.urlopen(URL,timeout=45).read();nb=json.loads(raw)
    cells=["".join(c.get("source",[])) for c in nb["cells"] if c["cell_type"]=="code"]
    env={}
    exec(compile(cells[0],URL,"exec"),env)
    start=time.monotonic()
    baseline=env["solve"](8);exact_check(baseline)
    discovered=next(c for c in cells if c.startswith("def priority") and "score = n" in c)
    exec(compile(discovered,URL,"exec"),env)
    official=env["solve"](8);exact_check(official)
    assert len(official)==512
    random_sizes=[]
    for seed in range(10):
        rng=np.random.default_rng(seed)
        env["priority"]=lambda v,n:float(rng.random())
        c=env["solve"](8);exact_check(c);random_sizes.append(len(c))
    report={"scope":"one-case construction/evaluator replay; not a reproduction of LLM discovery or evidence about C3c",
            "source_url":URL,"source_commit":SHA,"source_sha256":hashlib.sha256(raw).hexdigest(),
            "license":"Official repository: Apache-2.0 software; CC-BY-4.0 other materials; code fetched transiently, not vendored",
            "dimension":8,"constant_priority_size":len(baseline),"published_priority_size":len(official),
            "random_priority_sizes":random_sizes,"all_independent_pair_checks_passed":True,
            "seconds":time.monotonic()-start,"lesson":"Search representation and an effective construction program can matter much more than random priorities; this does not establish a language-model advantage."}
    (out/"funsearch-replay.json").write_text(json.dumps(report,indent=2))
    (out/"funsearch-512-witness.json").write_text(json.dumps(official.tolist()))
    print("BF2_REPLAY "+json.dumps(report),flush=True)
if __name__=="__main__":main()
