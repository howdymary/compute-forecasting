"""Brute-check safe fixing and the source-scoped high-word implication on small graphs."""
import itertools,json,random
rng=random.Random(1540001);tested=0
for trial in range(120):
 m=9;C=set(range(4));outside=set(range(4,m));edges=set()
 for v in outside:
  blockers=rng.sample(sorted(C),rng.randint(1,4))
  for u in blockers:edges.add(tuple(sorted([u,v])))
 for u,v in itertools.combinations(outside,2):
  if rng.random()<.5:edges.add((u,v))
 low={v for v in outside if sum(tuple(sorted([u,v])) in edges for u in C)<=2};U=C|low;F={u for u in C if not any(tuple(sorted([u,v])) in edges for v in low)}
 independent=[]
 for mask in range(1<<m):
  Q={i for i in range(m) if mask>>i&1}
  if not any(u in Q and v in Q for u,v in edges):independent.append(Q)
 lowgoals=[Q for Q in independent if Q<=U and len(Q)>=4]
 for Q in [Q for Q in independent if Q<=U]:
  assert Q|F in independent
 if any(len(Q)>4 for Q in lowgoals):continue
 known={tuple(sorted(Q)) for Q in lowgoals}
 for Q in independent:
  if len(Q)>=4 and tuple(sorted(Q)) not in known:assert Q&(outside-low)
 tested+=1
assert tested>=20
print(json.dumps({"independent_small_graph_implication_cases":tested,"safe_isolated_fixing_and_high_word_requirement":True,"passed":True}))
