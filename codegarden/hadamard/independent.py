"""Independent rational Gaussian determinant and strict sign-matrix validation."""
from fractions import Fraction
import hashlib,json
def validate(A,n=51):
 if type(A) is not list or len(A)!=n:raise ValueError("Wrong order")
 if any(type(r) is not list or len(r)!=n or any(type(x) is not int or x not in (-1,1) for x in r) for r in A):raise ValueError("Need an exact square sign matrix")
def determinant(A):
 n=len(A);M=[[Fraction(x) for x in r] for r in A];D=Fraction(1)
 for k in range(n):
  pivot=next((i for i in range(k,n) if M[i][k]),None)
  if pivot is None:return 0
  if pivot!=k:M[pivot],M[k]=M[k],M[pivot];D=-D
  p=M[k][k];D*=p
  for i in range(k+1,n):
   if not M[i][k]:continue
   a=M[i][k]/p
   for j in range(k+1,n):M[i][j]-=a*M[k][j]
   M[i][k]=Fraction(0)
 assert D.denominator==1
 return int(D)
def verify(data):
 A=data["matrix"];validate(A);d=abs(determinant(A))
 assert d*d<=51**51 and d%(1<<50)==0
 return {"method":"independent_fraction_gaussian","determinant":str(d),"witness_sha256":hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
