import importlib.util,pathlib,sys,time,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("cg_budget",ROOT/"budget/ledger.py")
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
class BudgetTests(unittest.TestCase):
    def test_unknown_is_unavailable(self):
        l=B.Ledger(":memory:")
        with self.assertRaises(B.BudgetUnavailable):l.reserve("modal","codegarden",1)
    def test_shared_reservations_and_verification_reserve(self):
        l=B.Ledger(":memory:")
        l.db.execute("INSERT INTO providers VALUES('modal','USD',100,60,10,?,?,1)",(time.time(),time.time()+60))
        other=l.reserve("modal","boundforge",20)
        with self.assertRaises(B.BudgetUnavailable):l.reserve("modal","codegarden",11)
        own=l.reserve("modal","codegarden",10);l.settle(own,None)
        with self.assertRaises(B.BudgetUnavailable):l.reserve("modal","codegarden",.01)
        l.settle(other,15)
        l.reserve("modal","codegarden",5)
    def test_uncoordinated_is_unavailable(self):
        l=B.Ledger(":memory:")
        l.db.execute("INSERT INTO providers VALUES('exa','USD',100,0,10,?,?,0)",(time.time(),time.time()+60))
        with self.assertRaises(B.BudgetUnavailable):l.reserve("exa","codegarden",1)
    def test_stale_is_unavailable(self):
        l=B.Ledger(":memory:")
        l.db.execute("INSERT INTO providers VALUES('tinker','USD',100,0,10,?,?,1)",(time.time()-100,time.time()-1))
        with self.assertRaises(B.BudgetUnavailable):l.reserve("tinker","codegarden",1)
if __name__=="__main__":unittest.main()
