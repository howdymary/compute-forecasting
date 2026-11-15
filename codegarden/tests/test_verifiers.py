import importlib.util, itertools, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"protected"/(name+".py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
D=load("verify_descendants");L=load("verify_lcs")
class VerificationTests(unittest.TestCase):
    def invalid(self, words, kind):
        with self.assertRaises(D.InvalidCode) as e:D.verify(words)
        self.assertEqual(e.exception.report["error"],kind)
        self.assertFalse(L.verify(words)["valid"])
    def test_duplicate(self):self.invalid(["0"*16]*2,"duplicate_word")
    def test_lengths(self):self.invalid(["0"*15],"invalid_word")
    def test_symbols(self):self.invalid(["0"*15+"x"],"invalid_word")
    def test_nonstring(self):self.invalid([0],"invalid_word")
    def test_empty(self):self.invalid([],"invalid_cardinality")
    def test_internal_repetition(self):
        self.assertEqual(len(D.descendants("0"*16)),1)
        self.assertTrue(D.verify(["0"*16])["valid"])
    def test_collision_positions(self):
        words=["0"*16,"0"*15+"1"]
        with self.assertRaises(D.InvalidCode) as e:D.verify(words)
        r=e.exception.report
        for word,positions in zip(r["words"],r["deletion_positions_zero_based"]):
            self.assertEqual("".join(c for i,c in enumerate(word) if i not in positions),r["descendant"])
        self.assertFalse(L.verify(words)["valid"])
    def test_small_valid(self):
        for n in [4,8,16]:
            words=["0"*n,"1"*n]
            self.assertTrue(D.verify(words,n)["valid"]);self.assertTrue(L.verify(words,n)["valid"])
    def test_all_small_pairs(self):
        for n in [4,5]:
            words=[format(x,"0%db"%n) for x in range(1<<n)]
            for a,b in itertools.combinations(words,2):
                collision=not set(D.descendants(a)).isdisjoint(D.descendants(b))
                self.assertEqual(collision,L.lcs(a,b)[0]>=n-2)
    def test_input_list_or_official_object(self):
        words=["0"*16,"1"*16]
        self.assertEqual(D.verify(words),D.verify({"words":words}))
        self.assertEqual(L.verify(words),L.verify({"words":words}))
if __name__=="__main__":unittest.main()
