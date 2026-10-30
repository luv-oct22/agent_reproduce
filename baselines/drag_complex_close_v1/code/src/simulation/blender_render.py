"""
Blender Python script — renders simulation history JSON into an MP4 video.

Usage:
    blender --background --python blender_render.py -- \
        --input sim_history.json \
        --output renders/video.mp4 \
        --fps 60 \
        --resolution 1920 1080 \
        --samples 32 \
        --frame-step 10

Requires: Blender 3.0+ (ships with its own Python, no pip needed).
Install:  sudo apt install blender   OR   download from blender.org
"""
import sys
import json
import math
import os

import bpy
import mathutils

# Blender executes scripts without adding their directory to sys.path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to sim_history.json")
    p.add_argument("--output", default="simulation.mp4", help="Output video path")
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--resolution", nargs=2, type=int, default=[1920, 1080])
    p.add_argument("--samples", type=int, default=64, help="Render samples (higher = better quality, slower)")
    p.add_argument("--frame-step", type=int, default=10, help="Use every N-th simulation step as an animation keyframe; preserve simulation time")
    p.add_argument("--trail", action="store_true", help="Show trajectory trail")
    p.add_argument("--still", action="store_true", help="Render one simulation step as PNG")
    p.add_argument("--step", type=int, default=0)
    p.add_argument("--save-blend", help="Save an editable scene before rendering")
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections:
        if c.name != "Collection":
            bpy.data.collections.remove(c)


def setup_render(args):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'

    prefs = bpy.context.preferences.addons['cycles'].preferences
    for device_type in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = device_type
            prefs.get_devices()
            if any(d.type != 'CPU' for d in prefs.devices):
                break
        except Exception:
            continue
    gpu_devices = [d for d in prefs.devices if d.type != 'CPU']
    if gpu_devices:
        for device in prefs.devices:
            device.use = True  # enable all GPUs + CPU for combined rendering
        print(f"GPU rendering enabled: {[d.name for d in gpu_devices]}")
    else:
        scene.cycles.device = 'CPU'
        for device in prefs.devices:
            device.use = True
        print("No GPU found, falling back to CPU")

    scene.cycles.samples = args.samples
    scene.render.use_persistent_data = True
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.03
    scene.cycles.adaptive_min_samples = min(16, args.samples)
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.sample_clamp_indirect = 3
    scene.cycles.seed = 7
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = min(os.cpu_count() or 8, 16)
    # Prefer modern photographic tone mapping, while supporting Blender 3.x.
    for transform in ('AgX', 'Filmic', 'Standard'):
        try:
            scene.view_settings.view_transform = transform
            break
        except TypeError:
            continue
    if scene.view_settings.view_transform == 'Filmic':
        scene.view_settings.look = 'Medium High Contrast'
    scene.render.resolution_x = args.resolution[0]
    scene.render.resolution_y = args.resolution[1]
    scene.render.fps = args.fps
    if args.still:
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.image_settings.color_depth = '8'
    else:
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.filepath = os.path.abspath(args.output)


def setup_world():
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()

    # Warm indoor ambient light (soft cream/beige tone)
    bg = tree.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.85, 0.80, 0.72, 1.0)
    bg.inputs['Strength'].default_value = 0.6

    output = tree.nodes.new('ShaderNodeOutputWorld')
    tree.links.new(bg.outputs['Background'], output.inputs['Surface'])


def setup_lighting():
    # Ceiling area light (main indoor light)
    bpy.ops.object.light_add(type='AREA', location=(3, 0, 8))
    ceiling = bpy.context.active_object
    ceiling.name = "CeilingLight"
    ceiling.data.energy = 200
    ceiling.data.size = 4
    ceiling.rotation_euler = (0, 0, 0)

    # Window-like directional light (warm sunlight through a window)
    bpy.ops.object.light_add(type='AREA', location=(-5, 5, 6))
    window = bpy.context.active_object
    window.name = "WindowLight"
    window.data.energy = 100
    window.data.size = 3
    window.data.color = (1.0, 0.95, 0.85)
    window.rotation_euler = (math.radians(60), 0, math.radians(-45))

    # Soft fill from the opposite side
    bpy.ops.object.light_add(type='AREA', location=(8, -5, 4))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 30
    fill.data.size = 3


def setup_camera(data):
    history = data["history"]
    first = history[0]
    last = history[-1]
    names = data["object_names"]

    all_positions = []
    for frame in history:
        for name in names:
            all_positions.append(frame[name]["position"])
    for m in data.get("markers", []):
        all_positions.append(m["position"])

    xs = [p[0] for p in all_positions]
    ys = [p[1] for p in all_positions]
    zs = [p[2] for p in all_positions]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 2)

    # Place camera inside the room, looking at the action
    cam_x = cx + span * 0.3
    cam_y = cy - span * 0.8
    cam_z = cz + span * 0.4 + 1.5  # eye-level offset

    # Clamp to stay inside the room walls (room: cx=2.5, 20x20x8)
    cam_x = max(-8, min(12, cam_x))
    cam_y = max(-8, min(8, cam_y))
    cam_z = max(1.0, min(7, cam_z))

    bpy.ops.object.camera_add(location=(cam_x, cam_y, cam_z))
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam

    target = mathutils.Vector((cx, cy, cz))
    direction = target - cam.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()
    cam.data.lens = 35


def _make_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return mat


def create_room():
    # Room dimensions — centered around the scene action
    room_w = 20   # x width
    room_d = 20   # y depth
    room_h = 8    # z height
    cx, cy = 2.5, 0.0  # room center offset (ball at 0, cup at 5)

    # --- Floor (wooden) ---
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.scale = (room_w / 2, room_d / 2, 1)
    floor.data.materials.append(
        _make_material("FloorMat", (0.45, 0.30, 0.18, 1), roughness=0.6)
    )

    # --- Ceiling (white plaster) ---
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, room_h))
    ceiling = bpy.context.active_object
    ceiling.name = "Ceiling"
    ceiling.scale = (room_w / 2, room_d / 2, 1)
    ceiling.rotation_euler = (math.radians(180), 0, 0)
    ceiling.data.materials.append(
        _make_material("CeilingMat", (0.90, 0.88, 0.85, 1), roughness=0.9)
    )

    # --- Walls ---
    wall_specs = [
        # (name, location, rotation, scale)
        ("WallBack",  (cx, -room_d / 2, room_h / 2), (math.radians(90), 0, 0),               (room_w / 2, room_h / 2, 1)),
        ("WallFront", (cx,  room_d / 2, room_h / 2), (math.radians(-90), 0, 0),              (room_w / 2, room_h / 2, 1)),
        ("WallLeft",  (cx - room_w / 2, cy, room_h / 2), (math.radians(90), 0, math.radians(90)),  (room_d / 2, room_h / 2, 1)),
        ("WallRight", (cx + room_w / 2, cy, room_h / 2), (math.radians(90), 0, math.radians(-90)), (room_d / 2, room_h / 2, 1)),
    ]
    wall_mat = _make_material("WallMat", (0.82, 0.78, 0.72, 1), roughness=0.85)

    for name, loc, rot, scl in wall_specs:
        bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
        wall = bpy.context.active_object
        wall.name = name
        wall.rotation_euler = rot
        wall.scale = scl
        wall.data.materials.append(wall_mat)


COLORS = [
    (0.31, 0.76, 0.97, 1),
    (0.51, 0.78, 0.52, 1),
    (1.0, 0.72, 0.30, 1),
    (0.81, 0.58, 0.83, 1),
    (0.94, 0.33, 0.31, 1),
]


def create_object_sphere(name, color_idx, radius=0.12, material=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=48, ring_count=24, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()

    if material is not None:
        obj.data.materials.append(material)
        return obj

    mat = bpy.data.materials.new(f"{name}_mat")
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = COLORS[color_idx % len(COLORS)]
    bsdf.inputs['Roughness'].default_value = 0.3
    bsdf.inputs['Metallic'].default_value = 0.4
    obj.data.materials.append(mat)
    return obj


def create_cup_marker(marker):
    pos = marker["position"]
    radius = marker.get("radius", 0.3)
    height = radius * 2

    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=height, vertices=48,
        location=(pos[0], pos[1], pos[2] - height / 2),
    )
    cup = bpy.context.active_object
    cup.name = marker.get("label", "marker")

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    cup.data.polygons[len(cup.data.polygons) - 1].select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.object.mode_set(mode='OBJECT')

    mat = bpy.data.materials.new("CupMat")
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.9, 0.2, 0.2, 1)
    bsdf.inputs['Roughness'].default_value = 0.4
    bsdf.inputs['Metallic'].default_value = 0.3
    bsdf.inputs['Alpha'].default_value = 0.6
    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'BLEND'
    cup.data.materials.append(mat)
    return cup


def create_trail_curve(name, positions, color_idx):
    curve_data = bpy.data.curves.new(f"{name}_trail", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.015
    curve_data.bevel_resolution = 4

    spline = curve_data.splines.new('NURBS')
    spline.points.add(len(positions) - 1)
    for i, pos in enumerate(positions):
        spline.points[i].co = (pos[0], pos[1], pos[2], 1)
    spline.use_endpoint_u = True

    trail_obj = bpy.data.objects.new(f"{name}_trail", curve_data)
    bpy.context.collection.objects.link(trail_obj)

    mat = bpy.data.materials.new(f"{name}_trail_mat")
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    c = COLORS[color_idx % len(COLORS)]
    bsdf.inputs['Base Color'].default_value = c
    bsdf.inputs['Alpha'].default_value = 0.4
    bsdf.inputs['Roughness'].default_value = 0.6
    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'BLEND'
    trail_obj.data.materials.append(mat)
    return trail_obj


def animate_objects(data, args, material=None):
    history = data["history"]
    names = data["object_names"]
    step = args.frame_step
    sampled = history[::step]
    total_video_frames = len(sampled)

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_video_frames

    objects = {}
    for i, name in enumerate(names):
        obj = create_object_sphere(name, i, data.get('object_radius', 0.12), material)
        objects[name] = obj

    # Use simulation timestamps so the video plays at physical speed for any dt/FPS.
    animation = data.get('animation', {})
    lead = animation.get('lead_in', 0)
    scene.frame_end = max(1, math.ceil(animation.get('duration', history[-1]['time']) * args.fps) + 1)
    for sample in animation.get('samples', []):
        if sample['time'] >= lead:
            break
        obj = objects[names[0]]
        obj.location = sample['tcp']
        obj.keyframe_insert(data_path='location', frame=1+sample['time']*args.fps)
    if sampled[-1] is not history[-1]:
        sampled.append(history[-1])
    for sim_frame in sampled:
        blender_frame = 1 + (lead+sim_frame['time']) * args.fps
        for name in names:
            pos = sim_frame[name]["position"]
            obj = objects[name]
            obj.location = (pos[0], pos[1], pos[2])
            obj.keyframe_insert(data_path="location", frame=blender_frame)

    for obj in objects.values():
        if obj.animation_data and hasattr(obj.animation_data.action, 'fcurves'):
            for fc in obj.animation_data.action.fcurves:
                for kf in fc.keyframe_points:
                    kf.interpolation = 'LINEAR'

    if args.trail:
        for i, name in enumerate(names):
            positions = [f[name]["position"] for f in sampled]
            create_trail_curve(name, positions, i)

    if args.still:
        if not 0 <= args.step < len(history):
            raise ValueError('Still step is outside simulation history')
        frame = 1 + (lead+history[args.step]['time']) * args.fps
        scene.frame_set(int(frame), subframe=frame-int(frame))
        for name, obj in objects.items():
            # Still images use exact simulation samples, not animation interpolation.
            obj.location = history[args.step][name]['position']
            obj.keyframe_insert(data_path='location', frame=frame)
    else:
        scene.frame_set(1)
    return scene.frame_end


def main():
    args = parse_args()

    if not bpy.app.build_options.opencolorio:
        raise RuntimeError('This Blender build has no OpenColorIO support. Use an official Blender build via --blender or BLENDER_BIN.')

    with open(args.input) as f:
        data = json.load(f)
    if 'animation' in data:
        data['animation']['fps'] = args.fps

    print(f"Loaded {data['total_frames']} simulation steps, {len(data['object_names'])} objects")

    clear_scene()
    if data.get('scene', {}).get('style') == 'robotics_lab':
        from robotics_room import build_room
        materials = build_room(data)
        total_video_frames = animate_objects(data, args, materials['ball'])
    else:
        setup_world()
        setup_lighting()
        create_room()
        total_video_frames = animate_objects(data, args)
        for marker in data.get("markers", []):
            create_cup_marker(marker)
        setup_camera(data)
    setup_render(args)

    if args.save_blend:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))

    print(f"Rendering {'still step ' + str(args.step) if args.still else str(total_video_frames) + ' frames'} -> {args.output}")
    if args.still:
        bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)
    from render_record import scene_settings, write_record
    settings = scene_settings(bpy.context.scene)
    settings.update({'Blender version': bpy.app.version_string, 'Output': os.path.abspath(args.output),
                     'Format': 'PNG' if args.still else 'MP4', 'Keyframe step': args.frame_step,
                     'Trail enabled': args.trail, 'History source': os.path.abspath(args.input)})
    if args.still:
        settings['Preview simulation step'] = args.step
        settings['Preview time after release (s)'] = data['history'][args.step]['time']
    else:
        settings['Encoded frames'] = total_video_frames
        settings['Video duration (s)'] = total_video_frames/args.fps
    write_record(os.path.dirname(os.path.abspath(args.output)), data, settings, args.output)
    print(f"Done! Render saved to {args.output}")


if __name__ == "__main__":
    main()
