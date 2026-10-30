"""Render deterministic bounce frames in Blender; no physics resampling."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
import robotics_room as room
from blender_balance import render_settings
from bounce_scene import scene_digest, write_record
from render_record import scene_settings
from drag_candidates import validate_candidate_geometry, validate_projected_candidates


def build_scene(manifest, args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Bounce prediction laboratory'
    render_settings(scene, args)
    scene.unit_settings.system = 'METRIC'
    m = room.palette()
    room.room(m)
    settings = manifest['scene']
    floor = manifest['surface_z_m']
    extension = max(0, settings.get('grid_height_m', 1.2)-1.2)
    if extension:
        # Keep the taller measurement board and its captions below the ceiling
        # and move hanging fixtures out of the measurement area.
        for obj in list(scene.objects):
            if obj.name.startswith(('Plaster ceiling', 'Suspended LED housing', 'LED diffuser', 'Suspension wire')):
                obj.location.z += extension
            elif obj.name.startswith(('Rear plaster wall', 'Right plaster wall')):
                obj.dimensions.z += extension
                obj.location.z += extension/2
    room.workbench(m, {'table_height': floor, 'table_bounds': settings['table_bounds_m']})
    # Front-on orthographic view makes the vertical travel and scale unambiguous.
    board = room.material('Matte measurement board', (.79, .82, .84), .9)
    ink = room.material('Measurement ink', (.045, .065, .075), .8)
    fine = room.material('Grid lines', (.46, .52, .55), .9)
    y = settings['grid_back_y_m']
    height = settings.get('grid_height_m', 1.2)
    half_width = settings.get('grid_half_width_m', 1.3)
    room.box('Measurement backdrop', (0, y+.012, floor+height/2+.05),
             (2*half_width+.12, .024, height+.22), board, .003)
    for i in range(round(2*half_width/.1)+1):
        x = -half_width+i*.1
        room.box('Vertical 0.10 m grid', (x, y-.001, floor+height/2), (.001, .001, height), fine, 0)
    for i in range(round(height/.1)+1):
        z = floor+i*.1
        room.box('Horizontal 0.10 m grid', (0, y-.002, z), (2*half_width, .001, .0015), fine, 0)
        room.text('Height scale', f'{i*.1:.1f}', (-half_width-.06, y-.006, z-.012), .025, ink)
    if settings.get('minor_grid_spacing_m'):
        for i in range(1, round(height/.025)):
            if i % 4:
                z = floor+i*.025
                room.box('Minor 0.025 m height grid', (0, y-.001, z), (2*half_width, .001, .0006), fine, 0)
    room.text('Surface label', f"{manifest['surface_id']}  |  grid 0.10 m", (-1.26, -.605, floor-.06), .036, ink)
    for obj in manifest['objects']:
        x = obj['position_m'][0]
        room.text('Launch station marker', 'Station '+obj['station'], (x-.10, y-.008, floor+height+.04), .035, ink)
        room.text('Launch velocity', f"{obj['velocity_m_s'][0]:.2f} m/s  >", (x-.10, y-.008, floor+height-.01), .027, ink)
        if settings.get('show_launch_height'):
            room.text('Initial bottom clearance', f"h = {obj['release_height_m']:.3f} m",
                      (x+.40, y-.008, floor+height-.01), .033, ink)
    materials = {o['source_specimen_id']: room.material('Recorded specimen '+o['source_specimen_id'], o['color_rgba'][:3], .4)
                 for o in manifest['objects']}
    world = bpy.data.worlds.new('Laboratory lighting')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    scene.world = world
    room.area('Large left softbox', (-2, -3, 4), (0, 0, 1.4), 250, (.95, .98, 1), 3)
    room.area('Right fill', (2, -2, 3), (0, 0, 1.4), 160, (1, .97, .93), 2)
    bpy.ops.object.camera_add(location=settings['camera_position_m'])
    scene.camera = bpy.context.object
    scene.camera.rotation_euler = (Vector(settings['camera_target_m'])-scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = settings['ortho_scale_m']
    scene.camera.data.dof.use_dof = False
    bpy.context.view_layer.update()

    def center_pixels(position):
        point = world_to_camera_view(scene, scene.camera, Vector(position))
        return [point.x*args.resolution[0], point.y*args.resolution[1]]

    if 'candidate_policy' in manifest:
        # Reject unreadable clusters before any expensive image rendering.
        validate_candidate_geometry(manifest)
        validate_projected_candidates(manifest, {
            key: {'objects': [{'center_pixels': center_pixels(frame['objects'][0]['position_m'])}]}
            for key, frame in manifest['choices'].items()})
    dynamic = []

    def pose(key):
        for obj in dynamic:
            bpy.data.objects.remove(obj, do_unlink=True)
        dynamic.clear()
        positions = [o['position_m'] for o in manifest['objects']] if key == 'context' else [o['position_m'] for o in manifest['choices'][key]['objects']]
        projections = []
        for record, position in zip(manifest['objects'], positions):
            radius = record['radius_m']
            if position[2]-radius < floor-1e-9:
                raise ValueError('Sphere clips the impact surface.')
            if not settings['table_bounds_m'][0]+radius < position[0] < settings['table_bounds_m'][1]-radius:
                raise ValueError('Sphere leaves the calibrated surface.')
            sphere = room.sphere('Specimen '+record['source_specimen_id'], position, (radius,)*3, materials[record['source_specimen_id']])
            dynamic.append(sphere)
            if key == 'context':
                holder = room.box('Retracting release holder', (position[0], .10, position[2]-radius-.002),
                                  (.075, .2, .004), m['metal'], 0)
                dynamic.append(holder)
            bpy.context.view_layer.update()
            projected = [world_to_camera_view(scene, scene.camera, sphere.matrix_world @ Vector(corner)) for corner in sphere.bound_box]
            if not all(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0 for p in projected):
                raise ValueError('Sphere falls outside camera frame.')
            pixels = (max(p.x for p in projected)-min(p.x for p in projected))*args.resolution[0]
            if pixels < 16:
                raise ValueError('Sphere too small to identify; increase render resolution.')
            if manifest['format'] == 'drag_prediction_scene':
                direction = scene.camera.rotation_euler.to_quaternion() @ Vector((0, 0, -1))
                origin = Vector(position)-10*direction
                hit, _, _, _, visible, _ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, direction, distance=10)
                if not hit or visible.original != sphere:
                    raise ValueError('The specimen is occluded by laboratory geometry.')
            projections.append({'specimen_id': record['source_specimen_id'], 'center_m': position,
                                'center_pixels': center_pixels(position), 'diameter_pixels': pixels})
        for i, position in enumerate(positions):
            for j in range(i):
                if math.dist(position, positions[j]) <= manifest['objects'][i]['radius_m']+manifest['objects'][j]['radius_m']:
                    raise ValueError('Specimen meshes intersect.')
        caption = 'HELD  |  t = 0.00 s' if key == 'context' else f"t = {manifest['elapsed_s']:.2f} s"
        label = room.text('Frame time', caption, (.6, y-.009, floor+height+.11), .035, ink)
        dynamic.append(label)
        return {'objects': projections, 'elapsed_s': 0 if key == 'context' else manifest['elapsed_s']}
    return scene, pose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--device', choices=['CUDA', 'OPTIX', 'CPU'], default='CUDA')
    parser.add_argument('--samples', type=int, default=96)
    parser.add_argument('--resolution', nargs=2, type=int, default=[1536, 1024])
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.samples < 1 or min(args.resolution) < 64:
        parser.error('Invalid render quality.')
    path = Path(args.manifest).resolve()
    manifest = json.loads(path.read_text())
    if manifest.get('format') not in ('bounce_prediction_scene', 'drag_prediction_scene'):
        raise ValueError('Expected a bounce or drag prediction scene.')
    scene, pose = build_scene(manifest, args)
    report = {}
    for key, filename in manifest['images'].items():
        report[key] = pose(key)
        if not args.build_only:
            scene.render.filepath = str(path.parent/filename)
            bpy.ops.render.render(write_still=True)
            write_record(path.parent, manifest, filename, dict(scene_settings(scene), frame=key, geometry=report[key]))
    pose('context')
    bpy.ops.wm.save_as_mainfile(filepath=str(path.parent/'scene.blend'), relative_remap=False)
    actual = dict(scene_settings(scene), scene_digest=scene_digest(manifest), frames=report,
                  images_rendered=not args.build_only, blender_version=bpy.app.version_string,
                  requested_backend=args.device)
    (path.parent/'build_report.json').write_text(json.dumps(actual, indent=2)+'\n')
    write_record(path.parent, manifest, actual=actual)
    prefix = 'DRAG' if manifest['format'] == 'drag_prediction_scene' else 'BOUNCE'
    print(f"{prefix}_{'BUILT' if args.build_only else 'COMPLETE'} {path.parent}")


if __name__ == '__main__':
    main()
