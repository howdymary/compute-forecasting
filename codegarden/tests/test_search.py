import importlib.util,itertools,pathlib,random,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
S=load("cg_search_tests","search.py");D=load("cg_desc_tests","protected/verify_descendants.py")
F=load("cg_fusion_tests","fusion.py")
def optimum(inc,pool):
    for k in range(len(pool),-1,-1):
        for sub in itertools.combinations(pool,k):
            try:inc.occupied(sub);return k
            except ValueError:pass
class SearchTests(unittest.TestCase):
    def test_kernel_exhaustive_small_lengths(self):
        for n in range(4,9):
            inc=S.Incidence(n)
            for x in range(1<<n):
                expected={int(d,2) for d in D.descendants(format(x,"0%db"%n))}
                self.assertEqual(set(inc.desc[x]),expected)
    def test_exact_against_bruteforce(self):
        inc=S.Incidence(6);rng=random.Random(9)
        for _ in range(20):
            pool=rng.sample(range(64),10);opt=optimum(inc,pool)
            code,r=S.exact_repair(inc,pool,opt,seconds=1)
            self.assertEqual(len(code),opt);inc.occupied(code)
            code,r=S.exact_repair(inc,pool,opt+1,seconds=1)
            self.assertEqual(r["status"],"INFEASIBLE_STRICT_IMPROVEMENT")
    def test_timeout_is_not_infeasibility(self):
        inc=S.Incidence(6);code,r=S.exact_repair(inc,list(range(64)),5,seconds=0)
        self.assertEqual(r["status"],"TIMEOUT_NO_IMPROVEMENT");self.assertFalse(r["complete"])
    def test_fusion_certificate(self):
        inc=S.Incidence(6)
        for seed in range(10):
            a=inc.greedy(random.Random(seed));b=inc.greedy(random.Random(seed+100))
            result,proof=F.fuse(inc,a,b,seed)
            self.assertEqual(len(result),optimum(inc,list(set(a)|set(b))))
            cover=set(proof["minimum_vertex_cover"])
            self.assertEqual(len(cover),len(proof["matching"]))
            self.assertEqual(len({x for x,y in proof["matching"]}),len(proof["matching"]))
            self.assertEqual(len({y for x,y in proof["matching"]}),len(proof["matching"]))
            for x in proof["left"]:
                for y in proof["right"]:
                    if inc.masks[x]&inc.masks[y]:self.assertTrue(x in cover or y in cover)
if __name__=="__main__":unittest.main()
