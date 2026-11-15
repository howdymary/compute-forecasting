"""Independent integer dual-cover certificate checker. Standard library only."""
import hashlib,json,pathlib,sys
def desc(s):
 return {s[:i]+s[i+1:j]+s[j+1:] for i in range(len(s)) for j in range(i+1,len(s))}
def binary(s,n):
 if not isinstance(s,str) or len(s)!=n or set(s)-{"0","1"}:raise ValueError("Invalid binary string")
def check(cert):
 if cert["n"]!=16 or cert["required_total"]!=227:raise ValueError("Wrong problem")
 fixed=cert["fixed_words"];pool=cert["pool_words"];q=cert["scale"];weights=cert["weights"]
 if not isinstance(q,int) or q<=0:raise ValueError("Invalid scale")
 if len(set(fixed))!=len(fixed) or len(set(pool))!=len(pool):raise ValueError("Duplicate words")
 occupied=set()
 for s in fixed:
  binary(s,16);ds=desc(s)
  if ds&occupied:raise ValueError("Invalid fixed code")
  occupied.update(ds)
 for s in pool:binary(s,16)
 for d,v in weights.items():
  binary(d,14)
  if not isinstance(v,int) or v<0:raise ValueError("Invalid dual weight")
 supplied=set(pool);actual=set()
 for x in range(65536):
  s=format(x,"016b")
  if not desc(s)&occupied:actual.add(s)
 if actual!=supplied:raise ValueError("Pool is not the complete fixed-code-compatible universe")
 for s in pool:
  cover=sum(weights.get(d,0) for d in desc(s))
  if cover<q:raise ValueError("Dual coverage deficit at "+s)
 numerator=sum(weights.values());repair_upper=numerator//q
 return {"valid":True,"fixed_cardinality":len(fixed),"pool_cardinality":len(pool),"scale":q,"dual_numerator":numerator,"integer_repair_upper_bound":repair_upper,
  "integer_total_upper_bound_for_codes_containing_fixed_words":len(fixed)+repair_upper,
  "excludes_227_in_this_fixed_neighborhood":len(fixed)+repair_upper<227,
  "pool_sha256":hashlib.sha256(("\n".join(sorted(pool))+"\n").encode()).hexdigest(),
  "global_optimality_claim":False,"proof":"Every pool word has dual cover at least scale. Pairwise descendant disjointness bounds any extension by total nonnegative dual mass / scale. Every compatible universe word was checked."}
if __name__=="__main__":
 try:print(json.dumps(check(json.loads(pathlib.Path(sys.argv[1]).read_text())),indent=2))
 except Exception as e:print(json.dumps({"valid":False,"error":str(e)}));sys.exit(1)
