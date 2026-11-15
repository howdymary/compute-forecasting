"""Free remote preflight: fresh arena and protected acceptance, no provider calls."""
import datetime as dt,hashlib,json,os,pathlib,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
def get(url):
 with urllib.request.urlopen(url,timeout=40) as r:return r.read()
def main():
 out=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","infeasible_probe_001")/"preflight";out.mkdir(parents=True,exist_ok=True)
 p=json.loads(get("https://einsteinarena.com/api/problems/two-deletion-code-16"))
 pinned=(ROOT/"artifacts/sources/official_verifier.py").read_text()
 assert p["verifier"].strip()==pinned.strip(),"Official semantics changed; stop"
 raw=get("https://einsteinarena.com/api/solutions/best?problem_id=34&limit=5");leaders=json.loads(raw)
 best=leaders[0];words=best["data"]["words"];path=out/"baseline.txt";path.write_text("\n".join(sorted(words))+"\n")
 accepted=verify(path);assert accepted["cardinality"]>=226
 receipt={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),"arena_leader_id":best["id"],"arena_author":best["agentName"],
  "listed_score":best["score"],"verification":accepted,"target":accepted["cardinality"]+1,
  "leader_response_sha256":hashlib.sha256(raw).hexdigest(),"verifier_sha256":hashlib.sha256(p["verifier"].encode()).hexdigest(),
  "cost":"Public standard GitHub runner only; zero Exa/past/Tinker/Modal calls. Global literature audit separate."}
 (out/"arena.json").write_text(json.dumps(receipt,indent=2));print("PHASE3_PREFLIGHT "+json.dumps(receipt),flush=True)
if __name__=="__main__":main()
