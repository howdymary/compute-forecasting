"""Exact bipartite union repair with a matching/vertex-cover certificate.

The union of two independently valid codes has no within-part conflicts.
Its maximum independent set can therefore be recovered by bipartite matching.
This only optimizes this explicit union, never the entire 65536-word universe.
"""
import hashlib, random
def fuse(inc,a,b,seed=0):
    common=set(a)&set(b);left=sorted(set(a)-common);right=sorted(set(b)-common)
    rng=random.Random(seed);rng.shuffle(left);rng.shuffle(right)
    adj={x:[y for y in right if inc.masks[x]&inc.masks[y]] for x in left}
    match={}
    def augment(x,seen):
        for y in adj[x]:
            if y in seen:continue
            seen.add(y)
            if y not in match or augment(match[y],seen):
                match[y]=x;return True
        return False
    for x in left:augment(x,set())
    matched_left=set(match.values())
    zl=set(x for x in left if x not in matched_left);zr=set();todo=list(zl)
    while todo:
        x=todo.pop()
        for y in adj[x]:
            if match.get(y)==x or y in zr:continue
            zr.add(y)
            if y in match and match[y] not in zl:zl.add(match[y]);todo.append(match[y])
    cover=(set(left)-zl)|zr
    result=common|zl|(set(right)-zr)
    assert len(result)==len(set(a)|set(b))-len(match)
    assert all(x in cover or y in cover for x,ys in adj.items() for y in ys)
    inc.occupied(result)
    return sorted(result),{"method":"exact_bipartite_union","left":left,"right":right,"common":sorted(common),
        "matching":[[x,y] for y,x in match.items()],"minimum_vertex_cover":sorted(cover),
        "union_size":len(set(a)|set(b)),"optimum_in_encoded_union":len(result),
        "global_optimality_claim":False,"proof_artifact":"matching_and_vertex_cover"}
