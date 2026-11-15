"""Bounded strategy proposals and verifier-grounded SFT; no model access to verifiers."""
import hashlib,json,os
MODEL="Qwen/Qwen3.5-4B"
ACTIONS=["random8greedy","random16greedy","structural24greedy","opportunity12exact",
         "random24exact","conflict8exact","random40greedy","structural48exact","opportunity6ejection"]
def prompt(state):
    return ("Choose exactly one CodeGarden search action. Reply with its identifier only.\n"
      "Actions: "+json.dumps(ACTIONS)+"\nObserved verified state: "+json.dumps(state,sort_keys=True)+"\nAction:")
def encode_prompt(tokenizer,state):
    messages=[{"role":"system","content":"Select bounded search experiments. Return only an allowed action identifier; never invent scores."},
              {"role":"user","content":prompt(state)}]
    return tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,return_dict=False)
class Policy:
    def __init__(self,ledger,sampler_path=None):
        import tinker
        self.tinker=tinker;self.ledger=ledger
        self.service=tinker.ServiceClient(display_name="CodeGarden strategy policy")
        self.sampler=self.service.create_sampling_client(model_path=sampler_path) if sampler_path else self.service.create_sampling_client(base_model=MODEL)
        if hasattr(self.sampler,"result"):self.sampler=self.sampler.result()
        self.tokenizer=self.sampler.get_tokenizer()
    def choose(self,state):
        text=prompt(state);tokens=encode_prompt(self.tokenizer,state)
        if len(tokens)>2048:raise ValueError("bounded strategy context exceeded")
        rid=self.ledger.reserve("tinker","codegarden",1.0)
        result=self.sampler.sample(prompt=self.tinker.ModelInput.from_ints(tokens),
          sampling_params=self.tinker.types.SamplingParams(max_tokens=64,temperature=0),
          num_samples=1).result()
        reply=self.tokenizer.decode(result.sequences[0].tokens).strip()
        selected=next((a for a in ACTIONS if reply==a),None)
        self.ledger.settle(rid,None)
        return {"action":selected,"valid_action":selected is not None,"raw_reply_sha256":hashlib.sha256(reply.encode()).hexdigest(),
          "state_sha256":hashlib.sha256(text.encode()).hexdigest(),"reservation":rid,"model":MODEL}
def train(examples,ledger,updates=8):
    import numpy as np,tinker
    if len(examples)<32:raise ValueError("Not enough verified training cases")
    if updates>20 or updates<1:raise ValueError("training batch must be bounded")
    case_ids={e["case_id"] for e in examples}
    if len(case_ids)<16:raise ValueError("Too few distinct verified starting cases")
    for e in examples:
        if not e["verified"] or e["action"] not in ACTIONS or e["split"]!="train":
            raise ValueError("Invalid, unverified, or held-out training label")
    rid=ledger.reserve("tinker","codegarden",2.0)
    service=tinker.ServiceClient(display_name="CodeGarden verifier-grounded SFT")
    trainer=service.create_lora_training_client(base_model=MODEL,rank=8)
    tokenizer=trainer.get_tokenizer();data=[]
    for e in examples:
        prefix=encode_prompt(tokenizer,e["state"])
        completion=tokenizer.encode(e["action"],add_special_tokens=False)
        all_tokens=prefix+completion
        data.append(tinker.Datum(model_input=tinker.ModelInput.from_ints(all_tokens[:-1]),
          loss_fn_inputs={"target_tokens":tinker.TensorData.from_numpy(np.array(all_tokens[1:],dtype=np.int64)),
          "weights":tinker.TensorData.from_numpy(np.array([0.]*(len(prefix)-1)+[1.]*len(completion),dtype=np.float32))}))
    metrics=[]
    for step in range(updates):
        batch=[data[(step*4+j)%len(data)] for j in range(4)]
        fb=trainer.forward_backward(batch,loss_fn="cross_entropy").result()
        op=trainer.optim_step(tinker.types.AdamParams(learning_rate=1e-4)).result()
        metrics.append({"step":step+1,"forward_backward":fb.metrics,"optimizer":op.metrics})
    checkpoint=trainer.save_weights_for_sampler(name="codegarden-final").result()
    ledger.settle(rid,None)
    return {"checkpoint":checkpoint.path,"updates":updates,"metrics":metrics,"case_ids":sorted(case_ids),
      "reservation":rid,"heldout_results":None,"status":"trained_not_yet_evaluated"}
