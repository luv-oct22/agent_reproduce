"""For each world: best achievable own-vs-canonical pixel separation over random launches."""
import json, math, random
import sys; sys.path.insert(0,'cvpr2027/experiments')
from build_law_contrastive_items import world, law, outcome, sample_launch, DTS
from src.worlds.attraction import DomainError
rng=random.Random(1)
for g in ['g1','g2','g3']:
  canon=world(g,None)
  for r in ['rule_1','rule_2','combined_rule']:
    row=[]
    for v in range(1,7):
      w=world(g,law(g,r,v)); seps=[]
      for _ in range(150):
        L=rng and sample_launch(rng)
        for dt in DTS:
          try: seps.append(math.dist(outcome(w,L,dt)[1],outcome(canon,L,dt)[1]))
          except DomainError: break
      seps.sort(); row.append(f'v{v}:{seps[len(seps)//2]:.0f}/{seps[-1]:.0f}' if seps else f'v{v}:-')
    print(g, r, ' '.join(row), flush=True)
