"""Decode explicit supported neighborhoods into native integer input."""
import json,pathlib
def load_input(out,case):
 core=json.loads((out/"support_plan.json").read_text())["core"];lines=(out/("supported_"+str(case)+".txt")).read_text().splitlines();n=int(lines[0]);assert len(lines)==n+1
 raw=[str(n)]
 for line in lines[1:]:
  assert len(line)==10
  C=[core[int(line[i:i+2],16)] for i in range(0,10,2)];assert len(set(C))==5 and C==sorted(C)
  raw.append("5 "+" ".join(map(str,C)))
 return (out/"root_core.txt").read_text()+"\n".join(raw)+"\n"
