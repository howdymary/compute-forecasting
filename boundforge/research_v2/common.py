"""Separate campaign accounting; immutable initial snapshots and preserved old reservations."""
import json,pathlib,sys,os
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from providers import Ledger,Providers,Disabled
class CampaignLedger(Ledger):
    def __init__(self,out):
        super().__init__(out)
        self.campaign=json.loads((HERE/"campaign-budget.json").read_text())
        old=self.snapshot["providers"]
        for provider,p in self.campaign["providers"].items():
            old[provider].update(initial_cap=p["initial_cap"],operational_cap=p["phase3_proposed_cap"],unit=p["unit"],enabled=p["initial_cap"] is not None)
        self.db.execute("insert or ignore into reservations values(?,?,?,?,?)",("literature-43674993906","exa",0.07,0.07,"API receipt"))
        self.db.commit()
class CampaignProviders(Providers):
    def __init__(self,out,log):
        self.out=out;self.log=log;self.ledger=CampaignLedger(out)
        self.run_id=os.environ.get("GITHUB_RUN_ID","remote")
    def past_usage(self):
        r=super().past_usage()
        initial=self.ledger.campaign["providers"]["past"]
        probe=initial["read_only_probe"]
        if r["month"]["from"]!=probe["month"]["from"]:raise Disabled("past accounting period changed")
        consumed=max(0,r["balance"]["spent"]-probe["balance"]["spent"])
        r["balance"]["left"]=min(r["balance"]["left"],initial["initial_cap"]-consumed)
        return r
