import copy,itertools,json,pathlib,random
from dual_verify import check
pool=[format(i,"016b") for i in range(65536)]
cert={"n":16,"required_total":227,"fixed_words":[],"pool_words":pool,"scale":1,"weights":{format(i,"014b"):1 for i in range(16384)}}
assert check(cert)["integer_total_upper_bound_for_codes_containing_fixed_words"]==16384
tests=1
for mutate in [lambda c:c["pool_words"].append(c["pool_words"][0]),lambda c:c["pool_words"].__setitem__(0,"invalid"),lambda c:c["weights"].__setitem__("00000000000000",-1),lambda c:c["pool_words"].pop(),lambda c:c.update(weights={}),lambda c:c.update(fixed_words=["0"*16,"0"*15+"1"])]:
 c=copy.deepcopy(cert);mutate(c)
 try:check(c)
 except ValueError:tests+=1
 else:raise AssertionError("invalid certificate accepted")
rng=random.Random(2271134);arithmetic=0
for _ in range(100):
 sets=[set(rng.sample(range(8),rng.randint(1,4))) for _ in range(7)]
 y=[rng.randrange(6) for _ in range(8)];Q=7
 for S in sets:
  deficit=Q-sum(y[i] for i in S)
  if deficit>0:y[min(S)]+=deficit
 delta=[sum(y[i] for i in S)-Q for S in sets];U=sum(y)
 for mask in range(1<<7):
  selected=[i for i in range(7) if mask>>i&1];occupied=set();valid=True
  for i in selected:
   if occupied&sets[i]:valid=False;break
   occupied.update(sets[i])
  if valid:
   assert len(selected)*Q<=U
   for target in range(1,len(selected)+1):
    slack=U-target*Q
    assert sum(delta[i] for i in selected)<=slack
    assert all(delta[i]<=slack for i in selected)
   arithmetic+=1
print(json.dumps({"certificate_fixtures":tests,"reduced_cost_subset_checks":arithmetic,"passed":True}))
