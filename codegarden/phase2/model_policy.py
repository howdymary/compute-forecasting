"""Bounded native-operator policy; pricing-based conservative reservations."""
import hashlib,importlib.util,json,pathlib,re,sys,time
from common import ROOT,ACTIONS
spec=importlib.util.spec_from_file_location("cg2_legacy_policy",ROOT/"integrations/tinker_policy.py")
TP=importlib.util.module_from_spec(spec);sys.modules[spec.name]=TP;spec.loader.exec_module(TP);TP.ACTIONS=ACTIONS
def messages(state,allowed=ACTIONS):
 return [{"role":"system","content":"Choose a bounded deletion-code search operator. Return exactly one allowed identifier. Never invent a result or change validity."},
  {"role":"user","content":"Allowed operators: "+json.dumps(allowed)+"\nVerified state and scoped evidence:\n"+json.dumps(state,sort_keys=True)+"\nOperator:"}]
def encode(tok,state,allowed=ACTIONS):return tok.apply_chat_template(messages(state,allowed),tokenize=True,add_generation_prompt=True,enable_thinking=False,return_dict=False)
class Policy:
 def __init__(self,ledger,path=None):
  import tinker
  self.t=tinker;self.ledger=ledger;self.service=tinker.ServiceClient(display_name="CodeGarden phase2 policy")
  future=self.service.create_sampling_client(model_path=path) if path else self.service.create_sampling_client(base_model=TP.MODEL)
  self.sampler=future.result() if hasattr(future,"result") else future;self.tokenizer=self.sampler.get_tokenizer()
 def choose(self,state,allowed=ACTIONS):
  tokens=encode(self.tokenizer,state,allowed)
  if len(tokens)>8192:raise ValueError("Bounded proposer context exceeded")
  # Official models.json: 4B uncached prefill .33/M, sample 1.005/M.
  # 8192 input + 24 output tokens < .00273 USD; .05 retains ample uncertainty.
  ident=self.ledger.reserve("tinker","codegarden",.05);start=time.perf_counter()
  result=self.sampler.sample(prompt=self.t.ModelInput.from_ints(tokens),
   sampling_params=self.t.types.SamplingParams(max_tokens=24,temperature=0),num_samples=1).result()
  output=result.sequences[0].tokens;reply=self.tokenizer.decode(output,skip_special_tokens=True).strip()
  found={a for a in allowed if re.search(r"(?<![A-Za-z0-9_])"+re.escape(a)+r"(?![A-Za-z0-9_])",reply)}
  selected=next(iter(found)) if len(found)==1 else None
  return {"action":selected,"valid_action":selected is not None,"strict_format":reply in allowed,
    "prompt_tokens":len(tokens),"output_tokens":len(output),"latency_seconds":time.perf_counter()-start,
    "estimated_gross_usd":(len(tokens)*.33+len(output)*1.005)/1e6,"reservation_usd":.05,"reservation":ident,
    "state_sha256":hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest(),
    "raw_reply_sha256":hashlib.sha256(reply.encode()).hexdigest()}
def train(examples,ledger):
 import numpy as np,tinker
 if len(examples)!=32 or any(not x["verified"] or x["split"]!="train" for x in examples):raise ValueError("Training boundary failed")
 service=tinker.ServiceClient(display_name="CodeGarden phase2 verifier-grounded training")
 inventory=service.create_rest_client().list_user_checkpoints(limit=100).result()
 count=inventory.cursor.total_count if inventory.cursor else len(inventory.checkpoints)
 if count is None or count>=94:raise RuntimeError("Checkpoint slots reserved for other projects")
 rid=ledger.reserve("tinker","codegarden",2);trainer=service.create_lora_training_client(base_model=TP.MODEL,rank=8);tok=trainer.get_tokenizer();data=[]
 for e in examples:
  prefix=encode(tok,e["state"]);completion=tok.encode(e["action"],add_special_tokens=False);seq=prefix+completion
  data.append(tinker.Datum(model_input=tinker.ModelInput.from_ints(seq[:-1]),loss_fn_inputs={
    "target_tokens":tinker.TensorData.from_numpy(np.array(seq[1:],dtype=np.int64)),
    "weights":tinker.TensorData.from_numpy(np.array([0.]*(len(prefix)-1)+[1.]*len(completion),dtype=np.float32))}))
 metrics=[]
 for step in range(8):
  fb=trainer.forward_backward(data[step*4:step*4+4],loss_fn="cross_entropy").result()
  trainer.optim_step(tinker.types.AdamParams(learning_rate=1e-4)).result();metrics.append({"step":step+1,"metrics":fb.metrics})
 cp=trainer.save_weights_for_sampler(name="codegarden-phase2").result()
 return cp.path,{"status":"trained","checkpoint_sha256":hashlib.sha256(cp.path.encode()).hexdigest(),"updates":8,
  "examples":32,"metrics":metrics,"reservation":rid,"checkpoint_count_before":count,"new_checkpoints":1}
