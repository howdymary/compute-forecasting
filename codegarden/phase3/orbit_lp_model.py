"""Exact symmetry quotient of the full fractional descendant packing relaxation."""
import collections,hashlib,json
import numpy as np
from scipy.sparse import csc_matrix
def reverse(w,n):return int(format(w,"0%db"%n)[::-1],2)
def orbits(n):
 mask=(1<<n)-1;images=[min(w,w^mask,reverse(w,n),reverse(w,n)^mask) for w in range(1<<n)];reps=sorted(set(images));lookup={w:i for i,w in enumerate(reps)};index=np.array([lookup[w] for w in images],dtype=np.int32);sizes=np.bincount(index,minlength=len(reps));return reps,index,sizes
def quotient(inc):
 n=inc.n;W,wi,ws=orbits(n);D,di,ds=orbits(n-2);rows=[];cols=[];values=[]
 for col,w in enumerate(W):
  count=collections.Counter(int(di[d]) for d in inc.desc[w])
  for row in sorted(count):rows.append(row);cols.append(col);values.append(count[row])
 A=csc_matrix((np.array(values,dtype=np.float64),(np.array(rows),np.array(cols))),shape=(len(D),len(W)))
 digest=hashlib.sha256(A.indptr.astype("<i8").tobytes()+A.indices.astype("<i8").tobytes()+A.data.astype("<f8").tobytes()+ds.astype("<i8").tobytes()).hexdigest()
 return A,ds.astype(float),W,wi,ws,D,di,digest
def lift_primal(x,wi,ws):return np.array([float(x[int(i)])/int(ws[int(i)]) for i in wi])
def dual_certificate(inc,marginals,di,denominator=1000000000):
 dual=np.maximum(0,-np.asarray(marginals));assert np.all(np.isfinite(dual))
 weights=[int(np.ceil(float(dual[int(i)])*denominator)) for i in di]
 minimum=min(sum(weights[d] for d in inc.desc[w]) for w in range(inc.N));repair=max(0,denominator-minimum)
 if repair:weights=[v+repair for v in weights]
 return {"length":inc.n,"denominator":denominator,"descendant_weights":weights,"total_weight":sum(weights),"integer_upper_bound":sum(weights)//denominator,"numerical_repair_added_per_descendant":repair,"meaning":"Global packing upper bound only after independent integer verification; never a code construction."}
