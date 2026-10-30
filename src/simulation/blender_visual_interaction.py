"""Render the outcome frames of one world: the probe at its start and at every recorded moment.

One Blender process renders every experiment of a world (frames.json from src.visual_interaction.grid).
Lab, camera and lighting match the law-contrastive exam frames (blender_attraction.py), so interaction and
exam images look the same. Blender never advances physics; positions come from the manifest.
Usage: blender --background --python blender_visual_interaction.py -- --manifest frames.json [--device CUDA]
"""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import robotics_room as room
from blender_balance import render_settings
from attraction_visual import CAMERA


def build_lab(scene, args):
    render_settings(scene, args)
    board = room.material('Matte calibration panel', (.78, .82, .85), .9)
    grid = room.material('Grid ink', (.45, .50, .54), .9)
    support = room.material('Anchor clamp', (.16, .18, .20), .5)
    room.box('Calibration panel', (0., .25, 1.5), (4.8, .04, 3.25), board, .004)
    for k in range(-22, 23):
        room.box('Vertical grid', (k/10, .222, 1.5), (.001, .002, 2.6), grid, 0)
    for k in range(2, 29):
        room.box('Horizontal grid', (0., .22, k/10), (4.4, .002, .001), grid, 0)
    room.cylinder('Fixed anchor mount', (0., .16, 1.5), .035, .14, support, axis=(0, 1, 0), bevel=.002)
    world = bpy.data.worlds.new('Laboratory illumination')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    scene.world = world
    room.area('Left softbox', (-2., -3., 4.), (0., 0., 1.5), 250, (.95, .98, 1.), 3.)
    room.area('Right fill', (2., -2., 3.), (0., 0., 1.5), 160, (1., .97, .93), 2.)
    bpy.ops.object.camera_add(location=CAMERA['position_m'])
    scene.camera = bpy.context.object
    scene.camera.rotation_euler = (Vector(CAMERA['target_m'])-scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = CAMERA['ortho_scale_m']
    scene.camera.data.dof.use_dof = False


def probe_materials(rgba, n):
    """n+1 shades from faint (start) to the probe colour (last sample)."""
    out = []
    for k in range(n + 1):
        w = .25 + .75 * k / max(n, 1)
        colour = tuple(1 - w * (1 - c) for c in rgba[:3])  # blend toward white
        out.append(room.material(f'Probe shade {k}', colour, .4))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--device', choices=['CPU', 'CUDA', 'OPTIX'], default='CUDA')
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--only', nargs='*', help='experiment ids to render (default: missing ones)')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    path = Path(args.manifest).resolve()
    manifest = json.loads(path.read_text())
    args.resolution = manifest['resolution']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Visual interaction laboratory'
    build_lab(scene, args)
    catalog = {o['id']: o for o in manifest['objects']}
    anchor = catalog['anchor']
    room.sphere('Specimen anchor', manifest['anchor_m'], (anchor['radius_m'],)*3,
                room.material('Specimen anchor', anchor['color_rgba'][:3], .4))
    probe = catalog['probe']
    n = max(len(f['strobe_m']) for f in manifest['frames'])
    shades = probe_materials(probe['color_rgba'], n)
    spheres = [room.sphere(f'Probe {k}', (0, 0, -10), (probe['radius_m'],)*3, shades[k]) for k in range(n + 1)]
    rendered = 0
    for frame in manifest['frames']:
        target = path.parent / frame['image']
        if (args.only and frame['id'] not in args.only) or (not args.only and target.exists()):
            continue
        points = [frame['start_m']] + frame['strobe_m']
        # The last recorded moment gets the solid colour, earlier ones fade toward the start.
        shade_index = [round(k * n / max(len(points) - 1, 1)) for k in range(len(points))]
        for k, sphere in enumerate(spheres):
            sphere.hide_render = True
        for p, k in zip(points, shade_index):
            spheres[k].location = p
            spheres[k].hide_render = False
        bpy.context.view_layer.update()
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        rendered += 1
    print(f'VISUAL_INTERACTION_RENDERED {rendered} frames in {path.parent}')


if __name__ == '__main__':
    main()
