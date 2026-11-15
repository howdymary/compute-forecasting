"""Independent exact midpoint integration; no imports from the official verifier."""
import hashlib,json,math,re
from fractions import Fraction
def exact_area(offsets):
 if not isinstance(offsets,list) or not 2<=len(offsets)<=128:raise ValueError("Bad offset count")
 xs=[]
 for s in offsets:
  if not isinstance(s,str) or not re.fullmatch(r"[+-]?\d{1,4}(?:\.\d{0,25})?",s):raise ValueError("Invalid exact decimal")
  xs.append(Fraction(s))
 n=len(xs);origin=xs[0];xs=[x-origin for x in xs];den=math.lcm(*(x.denominator for x in xs));base=[int(x*den)*n for x in xs]
 # Endpoint equations are integer-scaled. Integrate at slab midpoints, not endpoint trapezoids.
 lines=[(den*(j+1),base[j]) for j in range(n)]+[(den*j,base[j]+den) for j in range(n)]
 heights={Fraction(0),Fraction(1)}
 for i,(m,b) in enumerate(lines):
  for mm,bb in lines[i+1:]:
   if m!=mm:
    y=Fraction(bb-b,m-mm)
    if 0<y<1:heights.add(y)
 heights=sorted(heights);answer=Fraction(0)
 for y0,y1 in zip(heights,heights[1:]):
  y=(y0+y1)/2;p,q=y.numerator,y.denominator
  spans=sorted((base[j]*q+(j+1)*den*p,(base[j]+den)*q+j*den*p) for j in range(n))
  left,right=spans[0];length=0
  for a,b in spans[1:]:
   if a>right:length+=right-left;left,right=a,b
   else:right=max(right,b)
  length+=right-left
  answer+=Fraction(length,q*n*den)*(y1-y0)
 return answer
def verify(data):
 if not isinstance(data,dict) or len(data.get("offsets",[]))!=128:raise ValueError("Need128 offsets")
 value=exact_area(data["offsets"])
 if not 0<value<=Fraction(1,2):raise ValueError("Area range")
 return {"method":"independent_exact_midpoint_slabs","numerator":str(value.numerator),"denominator":str(value.denominator),"score":float(value),"witness_sha256":hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
if __name__=="__main__":
 import sys
 print(json.dumps(verify(json.load(open(sys.argv[1]))),indent=2))
