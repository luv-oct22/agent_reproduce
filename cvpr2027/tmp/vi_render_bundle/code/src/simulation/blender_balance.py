"""Blender entry point for the density image task. No animation or physics resampling."""
import argparse
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
import robotics_room as room
from balance_scene import write_parameters, pan_objects
from render_record import scene_settings


def render_settings(scene, args):
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x, scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.seed = 7
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = -0.4
    scene.view_settings.gamma = 1
    if args.device == 'CPU':
        scene.cycles.device = 'CPU'
    else:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = args.device
        prefs.get_devices()
        devices = [device for device in prefs.devices if device.type == args.device]
        if not devices:
            raise RuntimeError(f'No {args.device} device found. Use --device CPU for CPU rendering.')
        for device in prefs.devices:
            device.use = device.type == args.device
        scene.cycles.device = 'GPU'


def build_scene(manifest, args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Density balance laboratory'
    render_settings(scene, args)
    scene.unit_settings.system = 'METRIC'
    m = room.palette()
    room.room(m)
    room.workbench(m, {'table_height': manifest['scene']['table_height_m'],
                       'table_bounds': [-1.2, 1.2, -.65, .65]})
    # Reuse the existing robotics-lab furnishings and material vocabulary.
    room.furnishings(m)
    room.box('Balance base', (0, .025, .895), (.17, .18, .05), m['dark'], .01)
    room.cylinder('Balance column', (0, .03, 1.10), .016, .37, m['metal'], bevel=.002)
    pivot_z = manifest['balance']['pivot_z_m']
    room.box('Pivot bearing block', (0, .027, pivot_z), (.05, .032, .055), m['dark'], .004)
    room.cylinder('Horizontal pivot axle', (0, 0, pivot_z), .012, .095,
                  m['metal'], axis=(0, 1, 0), bevel=.001)
    room.box('Travel stop mounting plate', (0, .038, pivot_z-.022),
             (.15, .012, .055), m['dark'], .004)
    stop_angle = math.radians(manifest['balance']['tilt_degrees'])
    for sign in [-1, 1]:
        room.cylinder('Symmetric beam travel stop',
                      (sign*.06*math.cos(stop_angle), 0,
                       pivot_z-.06*math.sin(stop_angle)-.009/math.cos(stop_angle)-.004),
                      .004, .075, m['rubber'], axis=(0, 1, 0), bevel=0)
    for x in [-.06, .06]:
        for y in [-.035, .085]:
            room.cylinder('Base levelling foot', (x, y, .866), .014, .012, m['rubber'], bevel=.002)

    beam = room.box('Equal arm beam', (0, 0, pivot_z),
                    (2*manifest['balance']['arm_length_m']+.02, .018, .018), m['metal'], .003)
    groups = {}
    spec_objects = {}
    balance = manifest['balance']
    r, thick = balance['pan_radius_m'], balance['pan_thickness_m']
    pan_z = pivot_z-balance['pan_drop_m']
    for side, sign in [('left', -1), ('right', 1)]:
        before = set(bpy.data.objects)
        x = sign*balance['arm_length_m']
        room.cylinder(f'{side} pan', (x, 0, pan_z-thick/2), r, thick, m['metal'], bevel=.001)
        # Four suspension rods avoid the specimen; pans remain horizontal under gravity.
        for dx in [-r*.66, r*.66]:
            for dy in [-r*.66, r*.66]:
                a, b = Vector((x+dx, dy, pan_z)), Vector((x, 0, pivot_z))
                room.cylinder(f'{side} suspension', (a+b)/2, .0009, (b-a).length,
                              m['metal'], axis=b-a, bevel=0, vertices=12)
        spec_objects[side] = []
        for index, obj in enumerate(pan_objects(manifest, side)):
            specimen_mat = room.material(f"Registry {obj['source_specimen_id']} color", obj['color_rgba'][:3], .36)
            specimen_mat.diffuse_color = obj['color_rgba']
            specimen_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = obj['color_rgba']
            size = obj['side_length_m']
            dx, dy = obj.get('pan_offset_m', [0, 0])
            if math.hypot(abs(dx)+size/2, abs(dy)+size/2) >= r:
                raise ValueError('Specimen would extend beyond the pan.')
            if r*.66*(1-size/balance['pan_drop_m']) <= abs(dy)+size/2+.001:
                raise ValueError('Specimen would intersect the suspension rods; reduce sample volume.')
            cube = room.box(f"{side} #{index+1} | {obj['source_specimen_id']}",
                            (x+dx, dy, pan_z+size/2), (size, size, size), specimen_mat, 0)
            for other, other_size in spec_objects[side]:
                if (abs(cube.location.x-other.location.x) < (size+other_size)/2+1e-5
                        and abs(cube.location.y-other.location.y) < (size+other_size)/2+1e-5):
                    raise ValueError('Specimens would overlap on the pan.')
            spec_objects[side].append((cube, size))
        if manifest.get('show_specimen_labels', True):
            label = room.text(f'{side} specimen ID', pan_objects(manifest, side)[0]['source_specimen_id'],
                              (x, -r-.002, pan_z-.008), .010, m['dark'])
            label.data.align_x = 'CENTER'
            room.box(f'{side} ID plate', (x, -r, pan_z-.004), (.082, .002, .022), m['white'], .001)
        groups[side] = [(o, o.location.copy()) for o in set(bpy.data.objects)-before]
    room.area('Window daylight', (-2.6, -1.0, 2.6), (0, 0, 1.1), 200, (.85, .93, 1), 2.2)
    room.area('Bench softbox', (.4, -.7, 2.7), (0, 0, 1.1), 75, (1, .93, .83), 1.6)
    room.area('Rear fill', (1.3, 1.7, 2.5), (0, 0, 1.1), 65, (1, 1, 1), 1.5)
    world = bpy.data.worlds.new('Laboratory daylight')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .18
    scene.world = world
    settings = manifest['scene']
    bpy.ops.object.camera_add(location=settings['camera_position_m'])
    camera = bpy.context.object
    target = Vector(settings['camera_target_m'])
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.lens = settings['lens_mm']
    camera.data.dof.use_dof = True
    camera.data.dof.focus_distance = (target-camera.location).length
    camera.data.dof.aperture_fstop = settings['fstop']
    scene.camera = camera

    def pose(degrees):
        angle = math.radians(degrees)
        # Positive angle raises the right end and lowers the left end.
        beam.rotation_euler.y = -angle
        report = {}
        for side, sign in [('left', -1), ('right', 1)]:
            offset = Vector((sign*balance['arm_length_m']*(math.cos(angle)-1), 0,
                             sign*balance['arm_length_m']*math.sin(angle)))
            for obj, initial in groups[side]:
                obj.location = initial+offset
            first, first_size = spec_objects[side][0]
            report[side] = {'pan_top_z_m': pan_z+offset.z,
                            'specimen_center_m': list(first.location),
                            'specimen_bottom_z_m': first.location.z-first_size/2,
                            'objects': []}
            for cube, size in spec_objects[side]:
                bottom = cube.location.z-size/2
                assert abs(report[side]['pan_top_z_m']-bottom) < 1e-6
                report[side]['objects'].append({'name': cube.name, 'center_m': list(cube.location), 'bottom_z_m': bottom})
            assert report[side]['pan_top_z_m']-thick > settings['table_height_m']
        bpy.context.view_layer.update()
        for side, objects in spec_objects.items():
            for obj, size in objects:
                corners = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner))
                           for corner in obj.bound_box]
                if not all(0 < point.x < 1 and 0 < point.y < 1 and point.z > 0 for point in corners):
                    raise ValueError(f'{side} specimen is outside the camera frame.')
            report[side]['camera_center_normalized'] = list(world_to_camera_view(scene, camera, objects[0][0].location))
        assert report['left']['camera_center_normalized'][0] < report['right']['camera_center_normalized'][0]
        return report

    return scene, pose


def unknown_scene(manifest, args, context_path):
    """Blur the exact context pixels, then composite sharp centered text in Blender."""
    overlay = bpy.data.scenes.new('Unknown image overlay')
    bpy.context.window.scene = overlay
    render_settings(overlay, args)
    overlay.cycles.samples = 1
    overlay.view_settings.look = 'None'
    overlay.view_settings.exposure = 0
    overlay.render.film_transparent = True
    bpy.ops.object.camera_add(location=(0, 0, 10))
    overlay.camera = bpy.context.object
    overlay.camera.data.type = 'ORTHO'
    overlay.camera.data.ortho_scale = 2
    ink = room.emission('Unknown white lettering', (1, 1, 1), 1)
    text = room.text('Unknown centered title', manifest['unknown']['text'], (0, 0, 0), .30, ink, rotation=(0, 0, 0))
    text.data.align_x, text.data.align_y = 'CENTER', 'CENTER'
    text.data.extrude = 0
    overlay.use_nodes = True
    nodes, links = overlay.node_tree.nodes, overlay.node_tree.links
    nodes.clear()
    bg = nodes.new('CompositorNodeImage')
    if context_path.is_file():
        bg.image = bpy.data.images.load(str(context_path), check_existing=False)
    blur = nodes.new('CompositorNodeBlur')
    blur.filter_type = 'GAUSS'
    blur.size_x = blur.size_y = round(manifest['unknown']['gaussian_blur_pixels']*args.resolution[0]/1536)
    links.new(bg.outputs['Image'], blur.inputs['Image'])
    # Dim the blurred photograph so the white title remains legible.
    dim = nodes.new('CompositorNodeMixRGB')
    dim.blend_type = 'MULTIPLY'
    dim.inputs[0].default_value = 1
    dim.inputs[2].default_value = (.40, .40, .40, 1)
    links.new(blur.outputs['Image'], dim.inputs[1])
    foreground = nodes.new('CompositorNodeRLayers')
    merge = nodes.new('CompositorNodeAlphaOver')
    links.new(dim.outputs[0], merge.inputs[1])
    links.new(foreground.outputs['Image'], merge.inputs[2])
    composite = nodes.new('CompositorNodeComposite')
    links.new(merge.outputs[0], composite.inputs[0])
    return overlay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--device', choices=['CUDA', 'OPTIX', 'CPU'], default='CUDA')
    parser.add_argument('--samples', type=int, default=96)
    parser.add_argument('--resolution', nargs=2, type=int, default=[1536, 1024])
    parser.add_argument('--build-only', action='store_true', help='Save/validate the scene without rendering pixels.')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.samples < 1 or min(args.resolution) < 64:
        parser.error('Samples must be positive and resolution dimensions at least 64.')
    path = Path(args.manifest).resolve()
    root = path.parent
    manifest = json.loads(path.read_text())
    if manifest.get('format') != 'density_balance_scene':
        raise ValueError('Expected density_balance_scene manifest.')
    scene, pose = build_scene(manifest, args)
    tilt = manifest['balance']['tilt_degrees']
    geometry = {state: pose(degrees) for state, degrees in [('level', 0), ('left_down', tilt), ('right_down', -tilt)]}
    pose(0)
    actual = scene_settings(scene)
    actual['Requested compute backend'] = args.device
    actual['Blender version'] = bpy.app.version_string
    actual['Geometry checks'] = geometry
    (root/'build_report.json').write_text(json.dumps(actual, indent=2)+'\n')
    if not args.build_only:
        for key, degrees in [('context', 0), ('A', tilt), ('B', -tilt)]:
            pose(degrees)
            scene.render.filepath = str(root/manifest['images'][key])
            bpy.ops.render.render(write_still=True)
            write_parameters(root, manifest, manifest['images'][key], dict(actual, state=key, tilt_degrees=degrees))
        shutil.copyfile(root/manifest['images']['context'], root/manifest['images']['C'])
        write_parameters(root, manifest, manifest['images']['C'], dict(actual, state='C', tilt_degrees=0))
    pose(0)
    overlay = unknown_scene(manifest, args, root/manifest['images']['context'])
    if not args.build_only:
        overlay.render.filepath = str(root/manifest['images']['D'])
        bpy.ops.render.render(write_still=True, scene=overlay.name)
        write_parameters(root, manifest, manifest['images']['D'],
                         dict(scene_settings(overlay), state='D', background_source='context.png',
                              blur_pixels=round(manifest['unknown']['gaussian_blur_pixels']*args.resolution[0]/1536),
                              background_brightness_multiplier=.4))
    bpy.context.window.scene = scene
    # Keep image dependencies portable when a question folder is moved.
    for image in bpy.data.images:
        if image.source == 'FILE' and Path(bpy.path.abspath(image.filepath)).parent == root:
            image.filepath = '//'+Path(image.filepath).name
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'scene.blend'), relative_remap=False)
    write_parameters(root, manifest, 'scene.blend', dict(actual, images_rendered=not args.build_only))
    print(f"BALANCE_{'BUILT' if args.build_only else 'COMPLETE'} {root}")


if __name__ == '__main__':
    main()
