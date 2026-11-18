"""Read-only telemetry around the pre-V8 stack for engineering attribution."""
from ..curriculum.world import World
from ..curriculum.remote import Runner
from .manipulation import ControlWorld
class LegacyWorld(ControlWorld):
 do_task=World.do_task
class LegacyRunner(Runner):
 def reset(self,seed,record=True):
  super().reset(seed,False);self.w=LegacyWorld(seed,record);return self.status()
 def result(self):
  return {'seed':self.w.s['seed'],'mode':self.mode,'failure':'fall' if self.w.fall else 'incomplete' if self.index<5 else None,'arrivals':self.arrivals,'episode':self.w.episode()}
