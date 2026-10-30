"""Diagnose law-contrastive feasibility; siblings chosen to maximise separation."""
import json, math, sys, itertools
from collections import Counter
from src.worlds.definition import WorldInstance
from src.worlds.attraction import AttractionWorld, DomainError
from src.simulation.attraction_visual import projected
ROOT='world_instances/central_force_dynamics'; TARGET=float(sys.argv[1])
DTS=[round(.2*k,1) for k in range(1,26)]
def world(g,e): return AttractionWorld(WorldInstance(json.load(open(f'{ROOT}/central_force_dynamics_{g}/baseline/instance.json'))['payload']),equation=e)
def eq(g,r,v):
    q=json.load(open(f'{ROOT}/central_force_dynamics_{g}/{r}/variant_{v}/q01/instance.json'))['question']
    return q.get('hidden_equation_parameters') or q.get('hidden_force_function')
reason=Counter(); feas=Counter(); dts=[]
for g in ['g1','g2','g3']:
  canon=world(g,None)
  for r in ['rule_1','rule_2','combined_rule']:
    W={v:world(g,eq(g,r,v)) for v in range(1,7)}
    for v in range(1,7):
      for qi in range(1,16):
        d=json.load(open(f'renders/central_force_dynamics/central_force_dynamics_{g}/{r}/variant_{v}/q{qi:02d}/scene.json'))
        L=d['launch']; A=d['initial_state']['payload']['objects']['anchor']['position_m']
        dead=set(); best=None; why='sep'
        for dt in DTS:
          pts={}
          for k,w in [('own',W[v]),('canon',canon)]+[(s,W[s]) for s in range(1,7) if s!=v]:
            if k in dead: continue
            try:
              s0=w.make_state({'anchor':A,'probe':L['position_m']},{'anchor':[0,0,0],'probe':L['velocity_m_s']},L['start_time_s'])
              p=projected(w.advance(s0,dt).payload['objects']['probe']['position_m'])[:2]
              if 0<=p[0]<=1920 and 0<=p[1]<=1280: pts[k]=p
              else: dead.add(k)
            except DomainError: dead.add(k)
          if 'own' not in pts: why='own_invalid'; break
          if 'canon' not in pts: why='canon_invalid'; break
          sibs=[k for k in pts if isinstance(k,int)]
          for a,b in itertools.combinations(sibs,2):
            P=[pts['own'],pts['canon'],pts[a],pts[b]]
            if min(math.dist(x,y) for x,y in itertools.combinations(P,2))>=TARGET: best=dt; break
          if best: break
        feas[r]+= best is not None; reason[why if best is None else 'ok']+=1
        if best: dts.append(best)
print('feasible by rule', dict(feas), 'total', sum(feas.values()),'/810'); print('reasons', dict(reason))
dts.sort(); print('dt p10/p50/p90', [dts[int(len(dts)*x)] for x in (.1,.5,.9)])
