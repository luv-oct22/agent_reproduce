"""Acceptance rate of law-contrastive scene search: sample in-plane launches, keep separable ones."""
import json, math, random, itertools, sys, time
from collections import Counter
from src.worlds.definition import WorldInstance
from src.worlds.attraction import AttractionWorld, DomainError
from src.simulation.attraction_visual import projected, ANCHOR
ROOT='world_instances/central_force_dynamics'; TARGET=float(sys.argv[1]); TRIES=int(sys.argv[2])
def world(g,e): return AttractionWorld(WorldInstance(json.load(open(f'{ROOT}/central_force_dynamics_{g}/baseline/instance.json'))['payload']),equation=e)
def eq(g,r,v):
    q=json.load(open(f'{ROOT}/central_force_dynamics_{g}/{r}/variant_{v}/q01/instance.json'))['question']
    return q.get('hidden_equation_parameters') or q.get('hidden_force_function')
def end(w,launch,dt):
    s=w.make_state({'anchor':ANCHOR,'probe':launch[0]},{'anchor':[0,0,0],'probe':launch[1]},launch[2])
    p=projected(w.advance(s,dt).payload['objects']['probe']['position_m'])[:2]
    if not(40<=p[0]<=1880 and 40<=p[1]<=1240): raise DomainError('off frame')
    return p
rng=random.Random(0); acc=Counter(); tot=Counter(); t0=time.time()
for g in ['g1','g2','g3']:
  canon=world(g,None)
  for r in ['rule_1','rule_2','combined_rule']:
    W={v:world(g,eq(g,r,v)) for v in range(1,7)}
    for v in (1,4):
      for _ in range(TRIES):
        rad=rng.uniform(.6,1.6); ang=rng.uniform(0,2*math.pi); sp=rng.uniform(.1,.6); turn=rng.choice([1,-1])*rng.uniform(.6,1.2)
        pos=[ANCHOR[0]+rad*math.cos(ang),0.,ANCHOR[2]+rad*math.sin(ang)]
        vel=[sp*math.cos(ang+math.pi/2*turn),0.,sp*math.sin(ang+math.pi/2*turn)]
        launch=(pos,vel,round(rng.uniform(0,5),1)); tot[r]+=1
        for dt in (.4,.6,.8,1.0,1.2,1.5):
          try:
            own=end(W[v],launch,dt); can=end(canon,launch,dt)
            sib={s:end(W[s],launch,dt) for s in range(1,7) if s!=v}
          except DomainError: break
          if math.dist(own,can)<TARGET: continue
          if any(min(math.dist(x,y) for x,y in itertools.combinations([own,can,sib[a],sib[b]],2))>=TARGET for a,b in itertools.combinations(sib,2)):
            acc[r]+=1; break
print({r:f'{acc[r]}/{tot[r]}' for r in tot}, 'secs', round(time.time()-t0))
