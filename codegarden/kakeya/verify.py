"""Integrity-checked official and independent exact acceptance."""
import hashlib,importlib.util,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def verify(data):
 manifest=json.loads((ROOT/"protected/manifest.json").read_text())
 for rel,digest in manifest.items():
  if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError("Protected verifier changed: "+rel)
 O=load("kakeya_official",ROOT/"protected/official.py");I=load("kakeya_independent",ROOT/"protected/independent.py")
 score=O.evaluate(data);xs=[O._parse_offset(x) for x in data["offsets"]];x0=xs[0];exact=O.triangle_union_area([x-x0 for x in xs])
 independent=I.verify(data)
 assert exact.numerator==int(independent["numerator"]) and exact.denominator==int(independent["denominator"])
 assert score==independent["score"]
 return {"accepted":True,"score":score,"numerator":str(exact.numerator),"denominator":str(exact.denominator),"witness_sha256":independent["witness_sha256"],"reports":[{"method":"frozen_official_exact_endpoint_trapezoids","score":score},independent]}
if __name__=="__main__":
 import sys
 print(json.dumps(verify(json.load(open(sys.argv[1]))),indent=2))
