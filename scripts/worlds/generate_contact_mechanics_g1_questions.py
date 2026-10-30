import hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'world_instances/contact_mechanics/contact_mechanics_g1'
RULE1={f'variant_{i}':x for i,x in enumerate(({'kind':'penetration_power','p':1.2},{'kind':'damping_power','p':1.3},{'kind':'velocity_friction','q':.7},{'kind':'restitution_power','p':.8},{'kind':'normal_friction_coupled','p':1.4,'q':.6},{'kind':'nested_contact','p':1.2,'q':.5}),1)}
FIELDS={f'variant_{i}':x for i,x in enumerate(({'field_kind':'linear_position','amplitude':.2},{'field_kind':'linear_time','amplitude':.2,'reference_time_s':2.},{'field_kind':'quadratic_position','amplitude':.3},{'field_kind':'log_time','amplitude':.25,'reference_time_s':2.},{'field_kind':'position_time','amplitude':.2,'time_amplitude':.15},{'field_kind':'nested','amplitude':.3,'reference_time_s':2.}),1)}
def main():
 OUT.mkdir(parents=True,exist_ok=True); base={'format':'world_family_group','schema_version':1,'visibility':'host_only','family':'contact_mechanics','group_id':'contact_mechanics_g1','constants':{'normal_stiffness_N_m':18.,'damping_kg_s':1.6,'friction_mu':.4,'contact_threshold_m':.05,'plane_z_m':0.},'standard_equations':{'penetration':'delta=max(0,R_i+R_j-d)','normal_force':'F_n=k_n*delta+c_n*max(0,-v_rel,n)','friction':'|F_t|<=mu*F_n','acceleration':'a=F/m'}}; (OUT/'baseline').mkdir(parents=True,exist_ok=True); (OUT/'baseline/instance.json').write_text(json.dumps(base,indent=2)+'\n')
 for variant,eq in RULE1.items():
  for i in range(1,16):
   rng=random.Random(int.from_bytes(hashlib.sha256(f'contact_mechanics_g1:{variant}:{i}'.encode()).digest()[:8],'big')); objs=[]
   for j in range(2+(i-1)%3):
    radius=round(rng.uniform(.08,.16),2); objs.append({'object_id':f'object_{j+1}','color':['red','blue','green','yellow'][j],'mass_kg':round(rng.uniform(.3,2),1),'radius_m':radius,'position_m':[round(rng.uniform(-1.2,1.2),1),round(rng.uniform(-.5,.5),1),round(rng.uniform(radius-.03,1.2),2)],'velocity_m_s':[round(rng.uniform(-1,1),1),round(rng.uniform(-.5,.5),1),round(rng.uniform(-1,1),1)]})
   state={'objects':objs,'plane_z_m':0.,'start_time_s':round(rng.uniform(0,5),1),'duration_s':round(rng.uniform(.1,.3),2),'target_object_id':objs[rng.randrange(len(objs))]['object_id']}; qid=f'{variant}_q{i:02d}'
   for branch in ('rule_1','rule_2','combined_rule'):
    qd=OUT/branch/variant/f'q{i:02d}'; qd.mkdir(parents=True,exist_ok=True); q={'schema_version':1,'question_id':qid,'family':'contact_mechanics','group_id':'contact_mechanics_g1','rule':branch,'variant_id':variant,'scene_state':state,'target_object_id':state['target_object_id'],'prompt':'Using the interaction history and rendered context, choose the image showing the target object at the next frame. Answer A, B, C, or D.'}; host={'format':'question_instance','schema_version':1,'visibility':'host_only','question':q,'equation_parameters':eq if branch in ('rule_1','combined_rule') else None,'force_function':FIELDS[variant] if branch in ('rule_2','combined_rule') else None}; (qd/'instance.json').write_text(json.dumps(host,indent=2)+'\n'); (qd/'question.json').write_text(json.dumps({k:q[k] for k in ('schema_version','question_id','family','group_id','rule','variant_id','target_object_id','prompt')},indent=2)+'\n')
 print('generated 270 contact_mechanics question instances')
if __name__=='__main__': main()
