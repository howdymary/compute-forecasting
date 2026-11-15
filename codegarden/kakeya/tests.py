"""Independent exact comparisons, gradient checks and a measured full-size benchmark."""
import json,pathlib,time
import numpy as np
from search import Kernel
from verify import verify
from protected.independent import exact_area
ROOT=pathlib.Path(__file__).resolve().parent;kernel=Kernel();rng=np.random.default_rng(26001);rows=[]
for n in [3,4,8,16]:
 for case in range(4):
  x=np.round(rng.uniform(-.4,.4,n),5);data=[format(v,".5f") for v in x]
  area,g,_=kernel(x);exact=float(exact_area(data));assert abs(area-exact)<3e-14,(n,area,exact)
  assert abs(sum(g))<1e-12
  assert abs(kernel(x+.137)[0]-area)<3e-14
  assert abs(kernel(-x[::-1])[0]-area)<3e-14
  worst=0.
  for i in range(n):
   plus=x.copy();minus=x.copy();plus[i]+=1e-7;minus[i]-=1e-7
   fd=(kernel(plus)[0]-kernel(minus)[0])/2e-7;worst=max(worst,abs(fd-g[i]))
  assert worst<5e-6,(n,worst)
  rows.append({"n":n,"exact_area_error":abs(area-exact),"max_gradient_error":worst})
data=json.loads((ROOT/"baseline.json").read_text());accepted=verify(data);x=np.array(list(map(float,data["offsets"])))
started=time.monotonic()
for _ in range(10):area,g,slabs=kernel(x)
elapsed=(time.monotonic()-started)/10
assert abs(area-accepted["score"])<3e-14
report={"fixtures":rows,"baseline_verification":accepted,"baseline_native_area":area,"full_size_seconds_per_area_gradient":elapsed,"slabs":slabs,"kernel_is_not_a_verifier":True}
print(json.dumps(report,indent=2))
