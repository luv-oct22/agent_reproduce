"""Blender renderer for registry-backed liquid equilibrium multiple-choice images."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
import robotics_room as room
from blender_balance import render_settings
from render_record import scene_settings
from liquid_scene import frame_geometry, write_liquid_record, liquid_visual_settings


def transparent_material(name, color, surface_mix, roughness=.18):
    """A controlled optical display: no refracted duplicate objects or opaque glare."""
    material = room.material(name, color, roughness)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Specular'].default_value = .2
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    transparent.inputs['Color'].default_value = (*color, 1)
    mix = nodes.new('ShaderNodeMixShader')
    mix.inputs[0].default_value = surface_mix
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(shader.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes.get('Material Output').inputs['Surface'])
    return material


def marked_material(record):
    material = room.material('Recorded material '+record['source_specimen_id'], record['color_rgba'][:3], .38)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    tex = nodes.new('ShaderNodeTexCoord')
    split = nodes.new('ShaderNodeSeparateXYZ')
    links.new(tex.outputs['Generated'], split.inputs[0])
    scale = nodes.new('ShaderNodeMath')
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = 10
    links.new(split.outputs['Z'], scale.inputs[0])
    fraction = nodes.new('ShaderNodeMath')
    fraction.operation = 'FRACT'
    links.new(scale.outputs[0], fraction.inputs[0])
    line = nodes.new('ShaderNodeMath')
    line.operation = 'LESS_THAN'
    line.inputs[1].default_value = .025
    links.new(fraction.outputs[0], line.inputs[0])
    mix = nodes.new('ShaderNodeMixRGB')
    mix.inputs[1].default_value = record['color_rgba']
    mix.inputs[2].default_value = (.015, .015, .015, 1)
    links.new(line.outputs[0], mix.inputs[0])
    links.new(mix.outputs[0], shader.inputs['Base Color'])
    return material


def build_scene(manifest, args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Liquid equilibrium laboratory'
    render_settings(scene, args)
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = -.5
    visual = liquid_visual_settings(manifest)
    scene.cycles.max_bounces = 16
    scene.cycles.transmission_bounces = 12
    scene.cycles.transparent_max_bounces = 16
    scene.unit_settings.system = 'METRIC'
    materials = room.palette()
    room.room(materials)
    room.workbench(materials, {'table_height': .86, 'table_bounds': [-1.2, 1.2, -.65, .65]})
    room.furnishings(materials)
    tank = manifest['tank']
    length, wall, floor = tank['inner_side_m'], tank['wall_thickness_m'], tank['floor_z_m']
    glass = transparent_material('Low reflection display glass', (.995, .998, 1), visual['glass_surface_mix'])
    if visual['neutral_backdrop']:
        backdrop = room.material('Neutral measurement backdrop', (.65, .68, .69), .95)
        room.box('Tank measurement backdrop', (0, length/2+.04, floor+length/2),
                 (length+.075, .006, length+.025), backdrop, .003)
    room.box('Tank glass bottom', (0, 0, floor-wall/2), (length+2*wall, length+2*wall, wall), glass, 0)
    for sign in (-1, 1):
        room.box('Tank side wall', (sign*(length+wall)/2, 0, floor+length/2),
                 (wall, length+2*wall, length), glass, 0)
        room.box('Tank front or rear wall', (0, sign*(length+wall)/2, floor+length/2),
                 (length, wall, length), glass, 0)
    room.box('Tank protective base', (0, 0, floor-wall-.004),
             (length+.022, length+.022, .008), materials['dark'], .003)
    # Four permanent low-profile guide channels, present in every frame.
    for record in manifest['objects']:
        x, y = record['xy_m']
        size = record['side_length_m']
        for dx in (-size/2-.0015, size/2+.0015):
            for dy in (-size/2-.0015, size/2+.0015):
                room.cylinder('Upright frictionless guide', (x+dx, y+dy, floor+length/2),
                              .00045, length-.006, materials['metal'], bevel=0, vertices=12)
    tint = visual['liquid_tint_rgba'][:3]
    water = transparent_material('Pale blue transparent liquid', tint, visual['liquid_body_surface_mix'])
    surface = transparent_material('Visible liquid surface', tint, visual['liquid_top_surface_mix'], .24)
    waterline = room.material('Liquid level outline', visual['waterline_color_rgb'], .45)
    specimen_materials = {obj['source_specimen_id']: marked_material(obj) for obj in manifest['objects']}
    world = bpy.data.worlds.new('Soft lab daylight')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .3
    scene.world = world
    room.area('Window softbox', (-1.5, -.8, 2.4), (0, 0, 1), 160, (.9, .95, 1), 2)
    room.area('Upper softbox', (.5, .5, 2.3), (0, 0, 1), 90, (1, .95, .9), 1.5)
    room.area('Front fill', (.6, -1.5, 1.6), (0, 0, 1), 45, (1, 1, 1), 1.1)
    camera_settings = manifest['scene']
    bpy.ops.object.camera_add(location=camera_settings['camera_position_m'])
    scene.camera = bpy.context.object
    target = Vector(camera_settings['camera_target_m'])
    scene.camera.rotation_euler = (target-scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = camera_settings['ortho_scale_m']
    scene.camera.data.dof.use_dof = False
    dynamic = []

    def pose(key):
        for obj in dynamic:
            bpy.data.objects.remove(obj, do_unlink=True)
        dynamic.clear()
        records = manifest['context_objects'] if key == 'context' else manifest['objects']
        states = manifest['context_states'] if key == 'context' else manifest['choice_states'][key]
        frame = frame_geometry(manifest, records, states)
        cubes = []
        for record in frame['objects']:
            size = record['side_length_m']
            cube = room.box('Specimen '+record['source_specimen_id'], record['center_m'], (size,)*3,
                            specimen_materials[record['source_specimen_id']], 0)
            cubes.append(cube)
            dynamic.append(cube)
        liquid = room.box('Liquid volume', (0, 0, floor+frame['liquid_depth_m']/2),
                          (length, length, frame['liquid_depth_m']), water, 0)
        dynamic.append(liquid)
        # Remove object volumes from the liquid, rather than intersecting two optical solids.
        for cube in cubes:
            modifier = liquid.modifiers.new('Displaced liquid', 'BOOLEAN')
            modifier.operation = 'DIFFERENCE'
            modifier.solver = 'EXACT'
            modifier.object = cube
            bpy.context.view_layer.objects.active = liquid
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        # Tint the existing top faces; no extra plane changes or intersects the liquid volume.
        liquid.data.materials.append(surface)
        top_faces = 0
        for polygon in liquid.data.polygons:
            polygon.material_index = 0
            if polygon.normal.z > .95 and abs(polygon.center.z-frame['liquid_depth_m']/2) < 1e-5:
                polygon.material_index = len(liquid.data.materials)-1
                top_faces += 1
        if not top_faces:
            raise ValueError('No liquid surface faces found for the visibility treatment.')
        mesh = bmesh.new()
        mesh.from_mesh(liquid.data)
        actual_volume = abs(mesh.calc_volume(signed=True))
        mesh.free()
        expected_volume = length**2*tank['initial_liquid_depth_m']
        if abs(actual_volume-expected_volume) > expected_volume*1e-4:
            raise ValueError('Rendered liquid volume does not match the conserved physical volume.')
        # Geometric reading aids sit exactly at the physical liquid level in every option.
        def outline(points, radius, name):
            for start, end in zip(points, points[1:]+points[:1]):
                a, b = Vector(start), Vector(end)
                edge = room.cylinder(name, (a+b)/2, radius, (b-a).length, waterline,
                                     axis=b-a, bevel=0, vertices=12)
                dynamic.append(edge)
        z = frame['surface_z_m']
        half = length/2-.0008
        outline([(-half, -half, z), (half, -half, z), (half, half, z), (-half, half, z)],
                visual['wall_waterline_radius_m'], 'Waterline at tank wall')
        for record in frame['objects']:
            if record['mode'] != 'floating':
                continue
            x, y, _ = record['center_m']
            half_size = record['side_length_m']/2+.0002
            outline([(x-half_size, y-half_size, z), (x+half_size, y-half_size, z),
                     (x+half_size, y+half_size, z), (x-half_size, y+half_size, z)],
                    visual['object_waterline_radius_m'], 'Waterline at floating object')
        bpy.context.view_layer.update()
        for cube in cubes:
            projected = [world_to_camera_view(scene, scene.camera, cube.matrix_world @ Vector(corner))
                         for corner in cube.bound_box]
            if not all(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0 for p in projected):
                raise ValueError('Object outside camera frame.')
        return dict(frame, rendered_liquid_volume_m3=actual_volume,
                    wall_waterline_z_m=z, floating_object_waterline_count=sum(o['mode'] == 'floating' for o in frame['objects']))

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
        parser.error('Invalid render quality settings.')
    path = Path(args.manifest).resolve()
    manifest = json.loads(path.read_text())
    if manifest.get('format') != 'liquid_equilibrium_scene':
        raise ValueError('Expected liquid equilibrium scene.')
    root = path.parent
    manifest['visual'] = liquid_visual_settings(manifest)
    scene, pose = build_scene(manifest, args)
    report = {}
    for key in manifest['images']:
        report[key] = pose(key)
        if not args.build_only:
            scene.render.filepath = str(root/manifest['images'][key])
            bpy.ops.render.render(write_still=True)
            write_liquid_record(root, manifest, manifest['images'][key],
                                dict(scene_settings(scene), frame=key, geometry=report[key], visual_settings=manifest['visual']))
    pose('context')
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'scene.blend'), relative_remap=False)
    actual = dict(scene_settings(scene), blender_version=bpy.app.version_string,
                  requested_backend=args.device, frames=report, images_rendered=not args.build_only,
                  visual_settings=manifest['visual'])
    (root/'build_report.json').write_text(json.dumps(actual, indent=2)+'\n')
    write_liquid_record(root, manifest, 'scene.blend', actual)
    print(f"LIQUID_{'BUILT' if args.build_only else 'COMPLETE'} {root}")


if __name__ == '__main__':
    main()
