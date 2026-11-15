"""Regression checks for the actual tokenizer and bounded-action integration failures."""
import importlib.util,pathlib,types,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("cg_policy_contract",ROOT/"integrations/tinker_policy.py")
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
class Tokenizer:
    def __init__(self,reply):self.reply=reply
    def apply_chat_template(self,messages,**kwargs):
        assert kwargs["return_dict"] is False
        return [1,2,3]
    def decode(self,tokens,**kwargs):
        assert kwargs["skip_special_tokens"] is True
        return self.reply
class Ledger:
    def reserve(self,*args):return "test-reservation"
    def settle(self,*args):pass
class Future:
    def result(self):
        return types.SimpleNamespace(sequences=[types.SimpleNamespace(tokens=[1,2])])
class Sampler:
    def sample(self,**kwargs):return Future()
def choose(reply):
    p=object.__new__(P.Policy);p.tokenizer=Tokenizer(reply);p.ledger=Ledger();p.sampler=Sampler()
    p.tinker=types.SimpleNamespace(ModelInput=types.SimpleNamespace(from_ints=lambda t:list(t)),
      types=types.SimpleNamespace(SamplingParams=lambda **k:k))
    return p.choose({"length":16,"verified_best":226})
class PolicyContractTests(unittest.TestCase):
    def test_tokenizer_returns_token_sequence(self):
        self.assertEqual(P.encode_prompt(Tokenizer(""),{}),[1,2,3])
    def test_bounded_action_normalization(self):
        for text in ["random8greedy", "`random8greedy`", '"random8greedy"']:
            result=choose(text);self.assertTrue(result["valid_action"]);self.assertEqual(result["action"],"random8greedy")
    def test_ambiguous_or_unknown_action_rejected(self):
        for text in ["random8greedy random16greedy","random8greedyEVIL","invented_action",""]:
            self.assertFalse(choose(text)["valid_action"])
if __name__=="__main__":unittest.main()
