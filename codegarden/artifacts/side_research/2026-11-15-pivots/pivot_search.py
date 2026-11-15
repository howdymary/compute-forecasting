import urllib.request,json,random,time,resource,hashlib
resource.setrlimit(resource.RLIMIT_CPU,(45,45))
rng=random.Random(2271129); start=time.monotonic()
seed_bytes=urllib.request.urlopen("https://raw.githubusercontent.com/howdymary/compute-forecasting/635d085cc08145c55fad58821678e86d02c3fe93/codegarden/artifacts/best_code.txt",timeout=20).read()
assert hashlib.sha256(seed_bytes).hexdigest()=="417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa"
base=[int(s,2) for s in seed_bytes.decode().splitlines()]; assert len(base)==226
def d2(x):
    s=set()
    for i in range(16):
        y=(x&((1<<i)-1))|((x>>(i+1))<<i)
        for j in range(i,15):s.add((y&((1<<j)-1))|((y>>(j+1))<<j))
    return tuple(sorted(s))
D=[d2(x) for x in range(65536)]; owner=[-1]*16384
for i,w in enumerate(base):
    for d in D[w]:assert owner[d]<0;owner[d]=i
B=[]
for dx in D:
    b=0
    for d in dx:
        if owner[d]>=0:b|=1<<owner[d]
    B.append(b)
universe=(1<<226)-1
class Expired(Exception):pass
def clique(adj,target,limit):
    deadline=time.monotonic()+limit; nodes=0
    def visit(P,chosen):
        nonlocal nodes
        nodes+=1
        if nodes%32==1 and time.monotonic()>deadline:raise Expired()
        if len(chosen)>=target:return chosen
        order=[];bounds=[];col=0;remaining=P
        while remaining:
            col+=1; Q=remaining
            while Q:
                bit=Q&-Q;v=bit.bit_length()-1
                order.append(v);bounds.append(col)
                remaining^=bit;Q^=bit;Q&=~adj[v]
        for k in range(len(order)-1,-1,-1):
            if len(chosen)+bounds[k]<target:return None
            v=order[k]
            ans=visit(P&adj[v],chosen+[v])
            if ans is not None:return ans
            P&=~(1<<v)
        return None
    try:return visit((1<<len(adj))-1,[]),"FOUND_OR_COMPLETE",nodes
    except Expired:return None,"TIMEOUT",nodes
for n in range(2,11):
    a=[0]*n
    for i in range(n):
        for j in range(i):
            if rng.random()<0.5:a[i]|=1<<j;a[j]|=1<<i
    opt=max(mask.bit_count() for mask in range(1<<n) if all(not(mask&(1<<v)) or (mask&~(a[v]|(1<<v)))==0 for v in range(n)))
    ans,status,nodes=clique(a,opt,2);assert ans is not None and len(ans)==opt
    ans,status,nodes=clique(a,opt+1,2);assert ans is None and status=="FOUND_OR_COMPLETE"
eligible=[w for w in range(65536) if 2<=B[w].bit_count()<=8 and w not in base]
rows=[];found=None
for trial in range(96):
    if time.monotonic()-start>30:break
    forced=rng.choice(eligible); removed=B[forced]; radius=(12,16,24,32,48,64)[trial%6]
    idx=[i for i in range(226) if not(removed>>i)&1];rng.shuffle(idx)
    for i in idx[:max(0,radius-removed.bit_count())]:removed|=1<<i
    fixedmask=universe^removed; forcedD=set(D[forced])
    pool=[w for w in range(65536) if not(B[w]&fixedmask) and not forcedD.intersection(D[w])]
    candhash=hashlib.sha256(("\n".join(format(w,"016b") for w in pool)+"\n").encode()).hexdigest()
    m=len(pool); allmask=(1<<m)-1; conflicts=[1<<i for i in range(m)];inc={}
    for i,w in enumerate(pool):
        for d in D[w]:inc[d]=inc.get(d,0)|(1<<i)
    for i,w in enumerate(pool):
        for d in D[w]:conflicts[i]|=inc[d]
    adj=[allmask^c for c in conflicts]
    target=removed.bit_count()
    sol,status,nodes=clique(adj,target,0.12)
    row={"trial":trial,"forced":format(forced,"016b"),"forced_blockers":B[forced].bit_count(),"removed_indices":[i for i in range(226) if removed>>i&1],"pool_size":m,"pool_sha256":candhash,"required_repair":target,"status":"FEASIBLE" if sol is not None else ("INFEASIBLE_ENCODED_NEIGHBORHOOD" if status=="FOUND_OR_COMPLETE" else "TIMEOUT"),"nodes":nodes}
    rows.append(row)
    if sol is not None:
        found=[w for i,w in enumerate(base) if not(removed>>i)&1]+[forced]+[pool[v] for v in sol];break
words=[format(w,"016b") for w in sorted(found or base)]
used=set()
for s in words:
    ds={s[:i]+s[i+1:j]+s[j+1:] for i in range(16) for j in range(i+1,16)}
    assert not used.intersection(ds);used.update(ds)
def lcs(a,b):
    p=[0]*17
    for c in a:
        q=[0]*17
        for j,d in enumerate(b,1):q[j]=p[j-1]+1 if c==d else max(p[j],q[j-1])
        p=q
    return p[-1]
mx=max(lcs(a,b) for i,a in enumerate(words) for b in words[i+1:]);assert mx<=13
print(json.dumps({"method":"mandatory outside pivot plus randomly enlarged exact full-universe repair pool; bitset clique with coloring bound","seed":2271129,"solver_exhaustive_fixtures":9,"queries":len(rows),"complete_negative":sum(r["status"]=="INFEASIBLE_ENCODED_NEIGHBORHOOD" for r in rows),"timeouts":sum(r["status"]=="TIMEOUT" for r in rows),"best":len(words),"max_lcs":mx,"seconds":round(time.monotonic()-start,3),"results":rows,"new_witness":words if found else None,"scope":"Only explicit fixed-outside, mandatory-pivot neighborhoods. Timeouts remain open. No global impossibility or new-record claim."}))
