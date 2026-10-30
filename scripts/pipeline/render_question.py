"""Build a question manifest and invoke the appropriate Blender renderer."""
import argparse, json, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERIC_FAMILIES = {'kinematics_dynamics','fluid_mechanics','contact_mechanics','dissipative_dynamics','field_interactions','elastic_dynamics'}

def build_generic_manifest(world_path, question_path, output_dir, duration):
    raw=json.loads(Path(question_path).with_name('instance.json').read_text()); q=raw['question']; family=q['family']
    constants=json.loads(Path(world_path).read_text()).get('constants',{}); scene=q['scene_state']; dt=float(scene.get('duration_s',duration))
    if family=='kinematics_dynamics': base=list(constants.get('acceleration_m_s2',[1,-.4,.3]))
    elif family in ('fluid_mechanics','contact_mechanics'): base=[0,0,-float(constants.get('gravity_m_s2',4))]
    elif family=='dissipative_dynamics': base=list(constants.get('external_acceleration_m_s2',[1,-.4,.2]))
    elif family=='field_interactions': base=list(constants.get('field_direction',[.8,-.4,.2])); strength=float(constants.get('field_strength_N_C',1.0))
    else: base=[0,0,0]
    initial={}; truth={}; objects=[]; colors={'red':[.85,.08,.05,1],'blue':[.08,.25,.85,1],'green':[.08,.65,.22,1],'yellow':[.9,.7,.05,1]}
    for rec in scene['objects']:
        name=rec['object_id']; pos=list(rec.get('position_m',rec.get('initial_position_m'))); vel=list(rec.get('velocity_m_s',rec.get('initial_velocity_m_s',[0,0,0]))); mass=max(float(rec.get('mass_kg',1)),.1); a=list(base)
        if family=='field_interactions': a=[float(rec.get('charge_c',0))*strength*x/mass for x in base]
        elif family=='dissipative_dynamics':
            c=float(constants.get('linear_drag_kg_s',.8)); a=[a[i]-c*vel[i]/mass for i in range(3)]
        elif family=='elastic_dynamics':
            k=float(rec.get('spring_stiffness_N_m',constants.get('spring_stiffness_N_m',8))); a=[-k*pos[0]/mass,-k*pos[1]/mass,-k*(pos[2]-1)/mass]
        initial[name]={'position_m':pos,'velocity_m_s':vel}; final=[pos[i]+vel[i]*dt+.5*a[i]*dt*dt for i in range(3)]
        truth[name]={'position_m':final,'velocity_m_s':[vel[i]+a[i]*dt for i in range(3)]}
        objects.append({'id':name,'color_rgba':colors.get(rec.get('color'),[.5,.5,.5,1]),'radius_m':float(rec.get('radius_m',.08))})
    choices={}
    for label,off in (('A',(0,0,0)),('B',(.035,0,0)),('C',(-.035,0,0)),('D',(0,0,.035))):
        choices[label]={'state':{'objects':{n:{'position_m':[v['position_m'][i]+off[i] for i in range(3)],'velocity_m_s':v['velocity_m_s']} for n,v in truth.items()}}}
    manifest={'format':'generic_prediction_scene','schema_version':1,'visibility':'host_only','id':q['question_id'],'family':family,'initial_state':{'objects':initial},'choices':choices,'answer':'A','objects':objects,'camera':{'position_m':[0,-8,1.4],'target_m':[0,0,1.2],'ortho_scale_m':4.8},'duration_s':dt}
    output_dir.mkdir(parents=True,exist_ok=True); (output_dir/'scene.json').write_text(json.dumps(manifest,indent=2)+'\n'); return manifest

def main():
    p=argparse.ArgumentParser(); p.add_argument('--world-instance',required=True); p.add_argument('--question-file',required=True); p.add_argument('--output-dir',required=True); p.add_argument('--device',choices=['CPU','CUDA','OPTIX'],default='CUDA'); p.add_argument('--samples',type=int,default=96); p.add_argument('--resolution',nargs=2,type=int,default=[1920,1280]); p.add_argument('--duration',type=float,default=.2); p.add_argument('--no-text',action='store_true'); args=p.parse_args()
    question=json.loads(Path(args.question_file).with_name('instance.json').read_text())['question']; family=question.get('family'); output=Path(args.output_dir).resolve()
    if family in GENERIC_FAMILIES:
        build_generic_manifest(Path(args.world_instance),Path(args.question_file),output,args.duration); script=ROOT/'src/simulation/blender_generic.py'
    else:
        raise RuntimeError(f'No renderer registered for family: {family}')
    blender=os.environ.get('BLENDER_BIN',str(ROOT/'.tools/blender-3.6.23-linux-x64/blender'))
    cmd=[blender,'--background','--python-exit-code','1','--python',str(script),'--','--manifest',str(output/'scene.json'),'--device',args.device,'--samples',str(args.samples),'--resolution',*map(str,args.resolution),'--no-text']
    try: subprocess.run(cmd,check=True,cwd=ROOT)
    except subprocess.CalledProcessError:
        if args.device=='CPU': raise
        print(f'[render] {args.device} failed; retrying on CPU',flush=True); cmd[cmd.index('--device')+1]='CPU'; subprocess.run(cmd,check=True,cwd=ROOT)
if __name__=='__main__': main()
