"""Generate matched multi-object fluid-mechanics question records."""
import hashlib, json, random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'world_instances/fluid_mechanics/fluid_mechanics_g1'
RULE1={
 'variant_1':{'kind':'density_power','p':1.1}, 'variant_2':{'kind':'depth_power','p':1.2},
 'variant_3':{'kind':'pressure_log','scale':1.0}, 'variant_4':{'kind':'displacement_power','p':.8},
 'variant_5':{'kind':'density_depth_coupled','p':1.3,'q':.7}, 'variant_6':{'kind':'nested','p':1.2,'q':.6}}
FIELDS={
 'variant_1':{'field_kind':'linear_density','amplitude':.2,'reference_depth_m':1.0},
 'variant_2':{'field_kind':'linear_depth','amplitude':.25,'reference_depth_m':1.0},
 'variant_3':{'field_kind':'quadratic_depth','amplitude':.35,'reference_depth_m':1.0},
 'variant_4':{'field_kind':'log_time','amplitude':.3,'reference_time_s':2.0},
 'variant_5':{'field_kind':'density_depth','amplitude':.2,'depth_amplitude':.15,'reference_depth_m':1.0},
 'variant_6':{'field_kind':'nested','amplitude':.3,'reference_depth_m':1.0,'reference_time_s':2.0}}

def scene(rng,n):
    objs=[]; colors=['red','blue','green','yellow']
    for i in range(n):
        objs.append({'object_id':f'object_{i+1}','color':colors[i],
          'mass_kg':round(rng.uniform(.2,1.8),1),'volume_m3':round(rng.uniform(.03,.18),2),
          'position_m':[round(rng.uniform(-1.2,1.2),1),round(rng.uniform(-.8,.8),1),round(rng.uniform(-1.8,-.2),1)],
          'velocity_m_s':[round(rng.uniform(-.5,.5),1),round(rng.uniform(-.5,.5),1),round(rng.uniform(-.8,.8),1)]})
    return {'objects':objs,'start_time_s':round(rng.uniform(0,5),1),'duration_s':round(rng.uniform(.1,.3),2),'target_object_id':objs[rng.randrange(n)]['object_id']}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    baseline={'format':'world_family_group','schema_version':1,'visibility':'host_only','family':'fluid_mechanics','group_id':'fluid_mechanics_g1',
      'constants':{'fluid_density_kg_m3':1.1,'gravity_m_s2':4.2,'fluid_surface_z_m':0.0,'reference_depth_m':1.0,'minimum_separation_m':.05},
      'standard_equations':{'buoyancy':'F_b = rho_fluid * V_displaced * g','net_force':'F_net = F_b - m*g','acceleration':'a = F_net/m'}}
    (OUT/'baseline').mkdir(parents=True,exist_ok=True); (OUT/'baseline/instance.json').write_text(json.dumps(baseline,indent=2)+'\n')
    for variant,eq in RULE1.items():
      for i in range(1,16):
        rng=random.Random(int.from_bytes(hashlib.sha256(f'fluid_mechanics_g1:{variant}:{i}'.encode()).digest()[:8],'big')); state=scene(rng,2+(i-1)%3); qid=f'{variant}_q{i:02d}'
        for branch in ('rule_1','rule_2','combined_rule'):
          qd=OUT/branch/variant/f'q{i:02d}'; qd.mkdir(parents=True,exist_ok=True)
          q={'schema_version':1,'question_id':qid,'family':'fluid_mechanics','group_id':'fluid_mechanics_g1','rule':branch,'variant_id':variant,'scene_state':state,'target_object_id':state['target_object_id'],'prompt':'Using the interaction history and rendered context, choose the image showing the target object at the next frame. Answer A, B, C, or D.'}
          host={'format':'question_instance','schema_version':1,'visibility':'host_only','question':q,'equation_parameters':eq if branch in ('rule_1','combined_rule') else None,'force_function':FIELDS[variant] if branch in ('rule_2','combined_rule') else None}
          (qd/'instance.json').write_text(json.dumps(host,indent=2)+'\n'); public={k:q[k] for k in ('schema_version','question_id','family','group_id','rule','variant_id','target_object_id','prompt')}; (qd/'question.json').write_text(json.dumps(public,indent=2)+'\n')
    print('generated 270 fluid_mechanics question instances')
if __name__=='__main__': main()
