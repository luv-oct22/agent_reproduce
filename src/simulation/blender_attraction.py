"""Render recorded attraction poses. Blender never advances the world's physics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import robotics_room as room
from blender_balance import render_settings
from render_record import scene_settings
from attraction_visual import IMAGES, digest, geometry, validate_projections
from src.path_display import display_path


def build_scene(manifest, args):
    geometry(manifest, args.resolution)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Calibrated motion laboratory'
    render_settings(scene, args)
    show_text = not args.no_text
    scene.unit_settings.system = 'METRIC'
    board = room.material('Matte calibration panel', (.78, .82, .85), .9)
    grid = room.material('Grid ink', (.45, .50, .54), .9)
    ink = room.material('Caption ink', (.035, .05, .065), .9)
    support = room.material('Anchor clamp', (.16, .18, .20), .5)
    room.box('Calibration panel', (0., .25, 1.5), (4.8, .04, 3.25), board, .004)
    for k in range(-22, 23):
        x = k/10
        room.box('Vertical grid', (x, .222, 1.5), (.001, .002, 2.6), grid, 0)
        if k % 5 == 0 and show_text:
            room.text('X scale', f'{x:.1f}', (x-.035, .215, .16), .03, ink)
    for k in range(2, 29):
        z = k/10
        room.box('Horizontal grid', (0., .22, z), (4.4, .002, .001), grid, 0)
        if k % 5 == 0 and show_text:
            room.text('Z scale', f'{z:.1f}', (-2.34, .215, z-.015), .03, ink)
    if show_text:
        room.text('Axes', '+x right  |  +z up  |  y = 0  |  grid = 0.10 m', (-2.2, .21, 3.03), .045, ink)
    launch = manifest['launch']
    p, v = launch['position_m'], launch['velocity_m_s']
    if show_text:
        room.text('Initial condition caption',
                  f'Initial centre: x={p[0]:.6f}, z={p[2]:.6f} m  |  v0: x={v[0]:.6f}, z={v[2]:.6f} m/s',
                  (-2.2, .21, .055), .038, ink)
    catalog = {o['id']: o for o in manifest['objects']}
    if show_text:
        room.text('Calibration caption',
                  f'Orange: fixed, {catalog["anchor"]["mass_kg"]:g} kg, r={catalog["anchor"]["radius_m"]:g} m  |  '
                  f'Blue: {catalog["probe"]["mass_kg"]:g} kg, r={catalog["probe"]["radius_m"]:g} m',
                  (-2.2, .21, -.025), .039, ink)
    room.cylinder('Fixed anchor mount', (0., .16, 1.5), .035, .14, support, axis=(0, 1, 0), bevel=.002)
    world = bpy.data.worlds.new('Laboratory illumination')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    scene.world = world
    room.area('Left softbox', (-2., -3., 4.), (0., 0., 1.5), 250, (.95, .98, 1.), 3.)
    room.area('Right fill', (2., -2., 3.), (0., 0., 1.5), 160, (1., .97, .93), 2.)
    settings = manifest['camera']
    bpy.ops.object.camera_add(location=settings['position_m'])
    scene.camera = bpy.context.object
    scene.camera.rotation_euler = (Vector(settings['target_m'])-scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = settings['ortho_scale_m']
    scene.camera.data.dof.use_dof = False
    spheres = {}
    for obj in manifest['objects']:
        material = room.material('Specimen '+obj['id'], obj['color_rgba'][:3], .4)
        spheres[obj['id']] = room.sphere('Specimen '+obj['id'], (0, 0, 0), (obj['radius_m'],)*3, material)
    caption = room.text('Frame timing', '', (-2.2, .21, 2.93), .044, ink) if show_text else None

    def pose(key):
        state = manifest['initial_state'] if key == 'context' else manifest['choices'][key]['state']
        elapsed = 0. if key == 'context' else launch['duration_s']
        if caption is not None:
            caption.data.body = f'World start = {launch["start_time_s"]:.1f} s  |  elapsed = {elapsed:.4f} s'
        for name, sphere in spheres.items():
            sphere.location = state['payload']['objects'][name]['position_m']
        bpy.context.view_layer.update()
        for label in (obj for obj in scene.objects if obj.type == 'FONT'):
            corners = [world_to_camera_view(scene, scene.camera, label.matrix_world @ Vector(c)) for c in label.bound_box]
            if not all(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0 for p in corners):
                raise ValueError('Calibration text falls outside the camera frame: '+label.name)
        objects = {}
        for name, sphere in spheres.items():
            center = world_to_camera_view(scene, scene.camera, sphere.location)
            corners = [world_to_camera_view(scene, scene.camera, sphere.matrix_world @ Vector(c)) for c in sphere.bound_box]
            if not all(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0 for p in corners):
                raise ValueError('Specimen falls outside the actual camera frame.')
            direction = Vector((0., 1., 0.))
            hit, _, _, _, visible, _ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(),
                sphere.location-10*direction, direction, distance=10)
            objects[name] = dict(center_pixels=[center.x*args.resolution[0], center.y*args.resolution[1]],
                                 diameter_pixels=(max(p.x for p in corners)-min(p.x for p in corners))*args.resolution[0],
                                 visible=bool(hit and visible.original == sphere), center_m=list(sphere.location))
        return dict(elapsed_s=elapsed, objects=objects)
    return scene, pose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--device', choices=['CPU', 'CUDA', 'OPTIX'], default='CUDA')
    parser.add_argument('--samples', type=int, default=96)
    parser.add_argument('--resolution', nargs=2, type=int, default=[1920, 1280])
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--no-text', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.samples < 1 or min(args.resolution) < 64:
        parser.error('Invalid image quality settings.')
    path = Path(args.manifest).resolve()
    manifest = json.loads(path.read_text())
    existing = path.parent/'build_report.json'
    if args.build_only and existing.exists() and json.loads(existing.read_text()).get('images_rendered'):
        raise ValueError('Build-only must not replace a completed render record.')
    scene, pose = build_scene(manifest, args)
    # Validate all actual projections and visibility before rendering any pixels.
    frames = {key: pose(key) for key in IMAGES}
    validate_projections(manifest, frames, args.resolution)
    image_hashes = {}
    for key, filename in IMAGES.items():
        pose(key)
        if not args.build_only:
            scene.render.filepath = str(path.parent/filename)
            bpy.ops.render.render(write_still=True)
            image_hashes[key] = hashlib.sha256((path.parent/filename).read_bytes()).hexdigest()
            (path.parent/(Path(filename).stem+'_parameters.md')).write_text(
                '# Attraction frame parameters (host-only)\n\n```json\n'+json.dumps(dict(
                    scene_digest=digest(manifest), frame=key, geometry=frames[key],
                    settings=scene_settings(scene)), indent=2)+'\n```\n')
    pose('context')
    bpy.ops.wm.save_as_mainfile(filepath=str(path.parent/'scene.blend'), relative_remap=False)
    report = dict(scene_digest=digest(manifest), frames=frames, resolution=args.resolution,
                  images_rendered=not args.build_only, image_sha256=image_hashes,
                  blender_version=bpy.app.version_string, device=args.device, samples=args.samples,
                  settings=scene_settings(scene))
    (path.parent/'build_report.json').write_text(json.dumps(report, indent=2)+'\n')
    (path.parent/'scene_parameters.md').write_text('# Attraction scene parameters (host-only)\n\n```json\n'
        +json.dumps(report, indent=2)+'\n```\n')
    print(f'ATTRACTION_{"BUILT" if args.build_only else "RENDERED"} {display_path(path.parent)}')


if __name__ == '__main__':
    main()
