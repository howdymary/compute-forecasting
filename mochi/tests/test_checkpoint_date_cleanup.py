"""Scope and no-delete guards for an irreversible date-scoped operation."""
import asyncio,json
from datetime import date
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import pytest,tinker
from mochi.maintenance import checkpoints_by_date as cleanup

class Checkpoint:
 def __init__(self,key,stamp):self.tinker_path='tinker://fake:train:0/weights/'+key;self.time=stamp;self.checkpoint_id='weights/'+key;self.checkpoint_type='training';self.size_bytes=10
 def model_dump(self,mode):return {'time':self.time}

@pytest.mark.parametrize('stamp,selected',[
 ('2026-11-16T07:59:59Z',False),('2026-11-16T08:00:00Z',True),
 ('2026-11-17T07:59:59Z',True),('2026-11-17T08:00:00Z',False),
 ('2026-11-15T12:00:00Z',False),(None,False)])
def test_exact_los_angeles_creation_date(stamp,selected):
 assert cleanup.eligible(Checkpoint('test',stamp),date(2026,11,16),ZoneInfo('America/Los_Angeles')) is selected

def test_target_mismatch_causes_zero_deletions(monkeypatch,tmp_path):
 class Rest:
  def __init__(self):self.deleted=[]
  async def list_user_checkpoints(self,**kwargs):return SimpleNamespace(checkpoints=[Checkpoint('one','2026-11-16T20:00:00Z')],cursor=SimpleNamespace(total_count=1))
  async def delete_checkpoint_from_tinker_path(self,path):self.deleted.append(path)
 rest=Rest();monkeypatch.setattr(tinker,'RestClient',lambda:rest);monkeypatch.setattr(cleanup,'ROOT',tmp_path);(tmp_path/'configs').mkdir();(tmp_path/'configs/checkpoint-cleanup.json').write_text(json.dumps({'mode':'delete','creation_date':'2026-11-16','timezone':'America/Los_Angeles','expected_target_digest':'wrong','expected_count':1}))
 with pytest.raises(RuntimeError,match='target set changed'):asyncio.run(cleanup.main())
 assert rest.deleted==[]
