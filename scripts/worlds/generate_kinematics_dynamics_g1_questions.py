"""Generate matched multi-object kinematics question records."""
import hashlib, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'world_instances/kinematics_dynamics/kinematics_dynamics_g1'
VARIANTS = {
 'variant_1': {'kind':'power_velocity','p':.8},
 'variant_2': {'kind':'power_position','p':1.3},
 'variant_3': {'kind':'log_velocity','scale':1.0},
 'variant_4': {'kind':'log_position','scale':1.0},
 'variant_5': {'kind':'power_both','p':1.4,'q':.7},
 'variant_6': {'kind':'nested','p':1.2,'q':.6},
}
FIELDS = {
 'variant_1': {'field_kind':'linear_space','amplitude':.3,'time_scale':4.,'reference_time_s':2.},
 'variant_2': {'field_kind':'linear_time','amplitude':.2,'time_scale':4.,'reference_time_s':2.},
 'variant_3': {'field_kind':'quadratic_space','amplitude':.4,'time_scale':4.,'reference_time_s':2.},
 'variant_4': {'field_kind':'log_time','amplitude':.35,'time_scale':2.,'reference_time_s':2.},
 'variant_5': {'field_kind':'space_time','amplitude':.25,'time_amplitude':.2,'time_scale':4.,'reference_time_s':2.},
 'variant_6': {'field_kind':'nested','amplitude':.3,'time_scale':3.,'reference_time_s':2.},
}

def scene(rng, n):
    objects=[]
    colors=['red','blue','green','yellow']
    for i in range(n):
        objects.append({'object_id':f'object_{i+1}','color':colors[i],
            'mass_kg':round(rng.uniform(.2,2.0),1),'radius_m':round(rng.uniform(.08,.16),2),
            'initial_position_m':[round(rng.uniform(-1.2,1.2),1),round(rng.uniform(-.8,.8),1),round(rng.uniform(.8,2.8),1)],
            'initial_velocity_m_s':[round(rng.uniform(-1.0,1.0),1),round(rng.uniform(-1.0,1.0),1),round(rng.uniform(-1.2,1.2),1)]})
    return {'objects':objects,'start_time_s':round(rng.uniform(0.,5.),1),'duration_s':round(rng.uniform(.1,.3),2),
            'target_object_id':objects[rng.randrange(n)]['object_id']}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    baseline={'format':'world_family_group','schema_version':1,'visibility':'host_only','family':'kinematics_dynamics',
      'group_id':'kinematics_dynamics_g1','constants':{'acceleration_m_s2':[1.2,-.7,.4],'time_scale_s':1.0,
      'clock_range_s':[0.,30.],'minimum_separation_m':.05},'standard_equations':{
      'acceleration':'a = a0','velocity':'v = v0 + a0*t','position':'x = x0 + v0*t + 0.5*a0*t^2'}}
    (OUT/'baseline').mkdir(parents=True,exist_ok=True); (OUT/'baseline/instance.json').write_text(json.dumps(baseline,indent=2)+'\n')
    for variant, eq in VARIANTS.items():
      for i in range(1,16):
        rng=random.Random(int.from_bytes(hashlib.sha256(f'kinematics_dynamics_g1:{variant}:{i}'.encode()).digest()[:8],'big'))
        n=2+(i-1)%3; state=scene(rng,n); qid=f'{variant}_q{i:02d}'
        for branch in ('rule_1','rule_2','combined_rule'):
          qdir=OUT/branch/variant/f'q{i:02d}'; qdir.mkdir(parents=True,exist_ok=True)
          question={'schema_version':1,'question_id':qid,'family':'kinematics_dynamics','group_id':'kinematics_dynamics_g1',
            'rule':branch,'variant_id':variant,'scene_state':state,'target_object_id':state['target_object_id'],
            'prompt':'Using the interaction history and rendered context, choose the image showing the target object at the next frame. Answer A, B, C, or D.'}
          host=dict(format='question_instance',schema_version=1,visibility='host_only',question=question,
            equation_parameters=eq if branch in ('rule_1','combined_rule') else None,
            force_function=FIELDS[variant] if branch in ('rule_2','combined_rule') else None)
          (qdir/'instance.json').write_text(json.dumps(host,indent=2)+'\n')
          public={k:question[k] for k in ('schema_version','question_id','family','group_id','rule','variant_id','target_object_id','prompt')}
          (qdir/'question.json').write_text(json.dumps(public,indent=2)+'\n')
    print('generated 270 kinematics_dynamics question instances')

if __name__=='__main__': main()
