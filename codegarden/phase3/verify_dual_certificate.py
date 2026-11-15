"""Standalone exact dual check: no LP/search incidence, solver, model, API or history."""
import argparse,hashlib,importlib.util,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument("certificate");args=ap.parse_args();path=pathlib.Path(args.certificate);raw=path.read_bytes();c=json.loads(raw);n=c["length"];Q=c["denominator"];weights=c["descendant_weights"]
assert isinstance(n,int) and 3<=n<=16 and isinstance(Q,int) and Q>0 and len(weights)==1<<(n-2) and all(isinstance(w,int) and not isinstance(w,bool) and w>=0 for w in weights)
checker=ROOT/"protected/verify_descendants.py";assert hashlib.sha256(checker.read_bytes()).hexdigest()=="3c844b9c56e05a7f7e309bdf7d7ab094e098b4a70fd50189f6db92b1181b63fb"
spec=importlib.util.spec_from_file_location("frozen_literal_descendants",checker);D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
minimum=None;argmin=None
for w in range(1<<n):
 word=format(w,"0%db"%n);distinct=set(D.descendants(word));assert distinct and all(len(s)==n-2 and set(s)<={"0","1"} for s in distinct);value=sum(weights[int(d,2)] for d in distinct)
 if value<Q:raise ValueError("Uncovered word "+word+" has exact coverage "+str(value)+" below "+str(Q))
 if minimum is None or value<minimum:minimum=value;argmin=word
total=sum(weights);bound=total//Q;assert total==c["total_weight"] and bound==c["integer_upper_bound"]
if n==16:assert bound>=226,"Contradiction with the separately verified226baseline"
print(json.dumps({"valid_dual_certificate":True,"length":n,"all_words_checked":1<<n,"denominator":Q,"minimum_word_cover":minimum,"argmin_word":argmin,"total_weight":total,"integer_upper_bound":bound,"certificate_sha256":hashlib.sha256(raw).hexdigest(),"protected_descendants_sha256":hashlib.sha256(checker.read_bytes()).hexdigest(),"proof":"Every word has distinct-descendant weight at least Q; pairwise disjoint descendant sets of a valid code imply cardinality*Q<=sum(weights).","construction_claim":False,"global_record_claim":False}))
