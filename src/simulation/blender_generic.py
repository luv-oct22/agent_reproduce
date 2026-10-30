"""Render generic multi-object world-family prediction scenes."""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Vector

SIMULATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SIMULATION_DIR.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SIMULATION_DIR))
import robotics_room as room
from blender_balance import render_settings
from src.path_display import display_path

IMAGES = {'A':'choice_A.png','B':'choice_B.png','C':'choice_C.png','D':'choice_D.png'}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--manifest',required=True)
    parser.add_argument('--device',choices=['CPU','CUDA','OPTIX'],default='CUDA')
    parser.add_argument('--samples',type=int,default=96); parser.add_argument('--resolution',nargs=2,type=int,default=[1920,1280])
    parser.add_argument('--no-text',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    path=Path(args.manifest).resolve(); manifest=json.loads(path.read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene; scene.name='Generic physics laboratory'; render_settings(scene,args)
    scene.unit_settings.system='METRIC'
    board=room.material('Matte laboratory board',(.78,.82,.85),.9)
    room.box('Laboratory board',(0,.25,1.3),(5,.04,3.2),board,.004)
    world=bpy.data.worlds.new('Laboratory illumination'); world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4; scene.world=world
    room.area('Left softbox',(-2,-3,4),(0,0,1.3),250,(.95,.98,1),3)
    room.area('Right fill',(2,-2,3),(0,0,1.3),160,(1,.97,.93),2)
    camera_data=manifest['camera']; bpy.ops.object.camera_add(location=camera_data['position_m'])
    camera=bpy.context.object; camera.rotation_euler=(Vector(camera_data['target_m'])-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'; camera.data.ortho_scale=camera_data['ortho_scale_m']; scene.camera=camera
    spheres={}
    for obj in manifest['objects']:
        mat=room.material('Object '+obj['id'],obj['color_rgba'][:3],.4)
        spheres[obj['id']]=room.sphere('Object '+obj['id'],(0,0,0),(obj['radius_m'],)*3,mat)
    def pose(key):
        state=manifest['initial_state'] if key=='context' else manifest['choices'][key]['state']
        for name,sphere in spheres.items(): sphere.location=state['objects'][name]['position_m']
        bpy.context.view_layer.update()
    pose('context')
    for key,filename in IMAGES.items():
        pose(key); scene.render.filepath=str(path.parent/filename); bpy.ops.render.render(write_still=True)
    pose('context'); bpy.ops.wm.save_as_mainfile(filepath=str(path.parent/'scene.blend'),relative_remap=False)
    report={'format':'generic_visual_render','images_rendered':True,'resolution':args.resolution,'device':args.device,'samples':args.samples,
            'image_sha256':{k:hashlib.sha256((path.parent/f).read_bytes()).hexdigest() for k,f in IMAGES.items()}}
    (path.parent/'build_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'GENERIC_RENDERED {display_path(path.parent)}')
if __name__=='__main__': main()
