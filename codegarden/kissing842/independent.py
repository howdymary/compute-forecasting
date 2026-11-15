"""Independent outward-rounded enclosure of the true normalized overlap penalty."""
import decimal,hashlib,json,math,pathlib
from decimal import Decimal,localcontext,Inexact,ROUND_FLOOR,ROUND_CEILING
def enclosure(data,n=842,d=12):
 X=data["vectors"]
 if type(X) is not list or len(X)!=n:raise ValueError("Wrong vector count")
 V=[]
 for v in X:
  if type(v) is not list or len(v)!=d:raise ValueError("Wrong dimension")
  row=[]
  for x in v:
   if isinstance(x,bool) or not isinstance(x,(int,float,Decimal)):raise ValueError("Coordinates must be real finite JSON numbers")
   a=Decimal(str(x))
   if not a.is_finite() or (a and (a.adjusted()>6 or a.as_tuple().exponent< -60)) or len(a.as_tuple().digits)>25:raise ValueError("Unsupported coordinate magnitude or precision")
   row.append(a)
  V.append(row)
 nonzero=[a for v in V for a in v if a]
 if not nonzero:raise ValueError("Zero configuration")
 extent=max(a.adjusted() for a in nonzero)-min(a.as_tuple().exponent for a in nonzero)
 prec=max(120,4*(extent+4)+30);norms=[]
 with localcontext() as ctx:
  ctx.prec=prec;ctx.traps[Inexact]=True
  norms=[sum((a*a for a in v),Decimal(0)) for v in V]
 if min(norms)<=0:raise ValueError("Zero vector")
 lo=Decimal(0);hi=Decimal(0);uncertain=0
 with localcontext() as ctx:
  ctx.prec=90
  for i in range(n):
   for j in range(i):
    with localcontext() as exact:
     exact.prec=prec;exact.traps[Inexact]=True
     dot=sum((a*b for a,b in zip(V[i],V[j])),Decimal(0));product=norms[i]*norms[j]
    root=product.sqrt();rl=root.next_minus();rh=root.next_plus()
    ctx.rounding=ROUND_FLOOR;qlo=min(dot/rl,dot/rh)
    # The lower distance uses the upper normalized dot; reverse the endpoints.
    ctx.rounding=ROUND_CEILING;qhi=max(dot/rl,dot/rh)
    ctx.rounding=ROUND_FLOOR;distance_sq_lo=max(Decimal(0),Decimal(8)-Decimal(8)*qhi)
    ctx.rounding=ROUND_CEILING;distance_sq_hi=max(Decimal(0),Decimal(8)-Decimal(8)*qlo)
    dl=max(Decimal(0),distance_sq_lo.sqrt().next_minus());dh=distance_sq_hi.sqrt().next_plus()
    ctx.rounding=ROUND_FLOOR;loss_lo=max(Decimal(0),Decimal(2)-dh);lo+=loss_lo
    ctx.rounding=ROUND_CEILING;loss_hi=max(Decimal(0),Decimal(2)-dl);hi+=loss_hi
    uncertain+=int(loss_lo==0 and loss_hi>0)
 return {"method":"independent_decimal_outward_interval","precision":90,"exact_polynomial_precision":prec,"n":n,"d":d,"lower":str(lo),"upper":str(hi),"interval_width":str(hi-lo),"uncertain_contact_pairs":uncertain,"zero_overlap_proved":hi==0}
def tests():
 rows=[]
 for V,want in [([[1,0],[0,1]],Decimal(0)),([[1,0],[1,0]],Decimal(2)),([[1,1,0],[1,0,1]],Decimal(0))]:
  r=enclosure({"vectors":V},2,len(V[0]));assert Decimal(r["lower"])<=want<=Decimal(r["upper"]);rows.append(r)
 with localcontext() as ctx:
  ctx.prec=110;want=Decimal(2)-(Decimal(16)/5).sqrt()
 r=enclosure({"vectors":[[1,0],[3,4]]},2,2);assert Decimal(r["lower"])<=want<=Decimal(r["upper"]);rows.append(r)
 for V in [[[0,0],[1,0]],[[float("nan"),0],[1,0]],[[True,0],[1,0]]]:
  try:enclosure({"vectors":V},2,2)
  except ValueError:continue
  raise AssertionError("Invalid input accepted")
 return {"known_penalty_enclosures":rows,"invalid_cases_rejected":3}
if __name__=="__main__":
 import sys
 p=pathlib.Path(sys.argv[1]);obj=json.loads(p.read_text(),parse_float=Decimal);r=enclosure(obj);r["witness_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest();print(json.dumps(r,indent=2))
