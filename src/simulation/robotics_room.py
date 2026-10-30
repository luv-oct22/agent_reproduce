"""Configurable robotics laboratory for Blender (metres, z-up).

Run through render_scene, not the system Python: this module requires bpy.
All visible fixtures are editable meshes; simulation positions are not rescaled.
"""
import math
import random
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from objects.cup_geometry import WALL_THICKNESS, cup_profile


def material(name, color, roughness=0.45, metal=0, texture=0, wood=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metal
    if texture or wood:
        texcoord = nodes.new('ShaderNodeTexCoord')
        mapping = nodes.new('ShaderNodeVectorMath')
        mapping.operation = 'MULTIPLY'
        mapping.inputs[1].default_value = (1.5, 45, 4) if wood else (texture,) * 3
        links.new(texcoord.outputs['Generated'], mapping.inputs[0])
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 3
        noise.inputs['Detail'].default_value = 3
        links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = 0.15
        ramp.color_ramp.elements[0].color = (*[c * (0.50 if wood else 0.85) for c in color], 1)
        ramp.color_ramp.elements[1].position = 0.85
        ramp.color_ramp.elements[1].color = (*[min(c * 1.22, 1) for c in color], 1)
        links.new(noise.outputs['Fac'], ramp.inputs[0])
        links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.16 if wood else 0.12
        bump.inputs['Distance'].default_value = 0.001 if wood else 0.0004
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return mat


def emission(name, color, strength):
    mat = material(name, color)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Emission' if 'Emission' in shader.inputs else 'Emission Color'].default_value = (*color, 1)
    shader.inputs['Emission Strength'].default_value = strength
    return mat


def finish(obj, name, mat, bevel=0):
    obj.name = name
    obj.data.materials.append(mat)
    if bevel:
        if hasattr(obj.data, 'use_auto_smooth'):
            obj.data.use_auto_smooth = True
        modifier = obj.modifiers.new('Manufactured edge radius', 'BEVEL')
        modifier.width, modifier.segments = bevel, 3
        modifier = obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, position, size, mat, bevel=0.008):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, bevel)


def cylinder(name, position, radius, depth, mat, axis=(0, 0, 1), bevel=0.003, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=position)
    obj = bpy.context.object
    obj.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler()
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return finish(obj, name, mat, bevel)


def link(name, a, b, radius, mat, radius_end=None):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=radius,
                                   radius2=radius if radius_end is None else radius_end,
                                   depth=(b-a).length, location=(a+b)/2)
    obj = bpy.context.object
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return finish(obj, name, mat, 0.012)


def sphere(name, position, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=position)
    obj = bpy.context.object
    obj.scale = scale
    for face in obj.data.polygons:
        face.use_smooth = True
    return finish(obj, name, mat)


def tube(name, points, radius, mat):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 16
    curve.bevel_depth, curve.bevel_resolution = radius, 3
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for point, xyz in zip(spline.bezier_points, points):
        point.co = xyz
        point.handle_left_type = point.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def text(name, body, position, size, mat, rotation=(math.pi/2, 0, 0)):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body, curve.size, curve.extrude = body, size, 0.0003
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location, obj.rotation_euler = position, rotation
    obj.data.materials.append(mat)
    return obj


def area(name, position, target, energy, color, size, size_y=None):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.color = energy, color
    light.shape = 'RECTANGLE'
    light.size, light.size_y = size, size_y or size
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target)-Vector(position)).to_track_quat('-Z', 'Y').to_euler()
    return obj


def palette():
    return {
        'wall': material('Warm mineral plaster', (0.76, 0.745, 0.70), 0.85, texture=100),
        'floor': material('Terrazzo porcelain', (0.34, 0.37, 0.36), 0.65, texture=180),
        'white': material('Robot ceramic white powder coat', (0.80, 0.82, 0.80), 0.27, metal=0.12),
        'dark': material('Graphite anodised aluminium', (0.035, 0.047, 0.055), 0.33, metal=0.65),
        'rubber': material('Soft black rubber', (0.014, 0.019, 0.023), 0.8, texture=90),
        'metal': material('Brushed stainless steel', (0.50, 0.55, 0.58), 0.29, metal=0.92, texture=100),
        'wood': material('Natural oiled oak', (0.53, 0.32, 0.155), 0.4, wood=True),
        'blue': material('Muted blue enamel', (0.065, 0.22, 0.30), 0.31, metal=0.25),
        'cup': material('Glazed teal ceramic', (0.025, 0.25, 0.28), 0.19),
        'ball': material('Orange training ball', (0.92, 0.19, 0.022), 0.53, texture=100),
        'green': material('Leaf green', (0.09, 0.23, 0.08), 0.5),
        'terracotta': material('Terracotta', (0.35, 0.16, 0.09), 0.83, texture=80),
        'light': emission('Warm luminaire diffuser', (1.0, 0.88, 0.70), 3),
        'led': emission('Robot status light', (0.10, 0.80, 0.65), 2),
    }


def room(m):
    # Individual tiles, joints and skirting supply real scale and contact detail.
    box('Floor slab', (0, 0, -0.085), (7, 8, 0.12), m['dark'])
    for ix in range(9):
        for iy in range(10):
            box('Floor porcelain tile', (-3.2+ix*0.8, -3.6+iy*0.8, -0.018),
                (0.796, 0.796, 0.034), m['floor'], 0.001)
    box('Rear plaster wall', (0, 2.85, 1.65), (7, 0.18, 3.3), m['wall'])
    box('Right plaster wall', (3.45, 0, 1.65), (0.18, 5.8, 3.3), m['wall'])
    box('Plaster ceiling', (0, 0, 3.38), (7, 8, 0.15), m['wall'])
    box('Rear skirting', (0, 2.74, 0.065), (6.85, 0.035, 0.13), m['white'], 0.003)
    box('Right skirting', (3.34, 0, 0.065), (0.035, 5.5, 0.13), m['white'], 0.003)
    # Left wall has a genuine window opening rather than an image background.
    for pos, size in [((-3.45, 0, 0.47), (0.18, 5.8, 0.94)),
                      ((-3.45, 0, 3.04), (0.18, 5.8, 0.52)),
                      ((-3.45, -2.48, 1.86), (0.18, 0.85, 1.84)),
                      ((-3.45, 2.2, 1.86), (0.18, 1.4, 1.84))]:
        box('Window wall', pos, size, m['wall'])
    for y in [-2.04, -0.85, 0.34, 1.5]:
        box('Window mullion', (-3.40, y, 1.88), (0.13, 0.045, 1.8), m['white'], 0.002)
    for z in [0.98, 1.88, 2.78]:
        box('Window transom', (-3.40, -0.27, z), (0.14, 3.6, 0.05), m['white'], 0.002)
    box('Deep window sill', (-3.30, -0.27, 0.97), (0.43, 3.7, 0.065), m['wood'])
    sky = emission('Bright overcast exterior', (0.71, 0.84, 1.0), 0.7)
    box('Exterior light court', (-4.2, 0, 1.9), (0.05, 7, 4), sky)
    # Visible ceiling fixture and fine suspension cables.
    for x in [-0.9, 1.3]:
        box('Suspended LED housing', (x, 0.3, 2.95), (0.095, 1.9, 0.055), m['dark'])
        box('LED diffuser', (x, 0.3, 2.919), (0.072, 1.83, 0.008), m['light'], 0.002)
        for y in [-0.45, 1.05]:
            cylinder('Suspension wire', (x, y, 3.14), 0.002, 0.33, m['metal'], bevel=0)


def workbench(m, params):
    xmin, xmax, ymin, ymax = params.get('table_bounds', [-1.4, 1.6, -0.7, 0.7])
    height = params.get('table_height', 0.86)
    center = ((xmin+xmax)/2, (ymin+ymax)/2)
    box('Solid oak worktop', (*center, height-0.035), (xmax-xmin, ymax-ymin, 0.07), m['wood'], 0.012)
    for x in [xmin+0.16, xmax-0.16]:
        for y in [ymin+0.12, ymax-0.12]:
            box('Bench steel leg', (x, y, height/2-0.03), (0.065, 0.065, height-0.08), m['dark'], 0.005)
            cylinder('Adjustable bench foot', (x, y, 0.035), 0.048, 0.035, m['rubber'])
            cylinder('Foot threaded stem', (x, y, 0.067), 0.017, 0.045, m['metal'])
        box('Bench cross rail', (x, center[1], 0.20), (0.05, ymax-ymin-0.24, 0.055), m['dark'])
    for y in [ymin+0.12, ymax-0.12]:
        box('Bench apron', (center[0], y, height-0.13), (xmax-xmin-0.24, 0.045, 0.12), m['dark'])
    box('Bench lower brace', (center[0], ymax-0.12, 0.22), (xmax-xmin-0.24, 0.045, 0.06), m['dark'])
    box('Bench identification plate', (xmax-0.36, ymin-0.001, height-0.037), (0.27, 0.004, 0.032), m['metal'], 0.002)
    text('Bench serial', 'LAB / 01', (xmax-0.475, ymin-0.004, height-0.047), 0.019, m['dark'])


def robot(m, base, release):
    bx, by, bz = base
    box('Robot mounting plate', (bx, by, bz+0.012), (0.46, 0.42, 0.024), m['metal'])
    for x in [-0.18, 0.18]:
        for y in [-0.16, 0.16]:
            cylinder('Mount socket bolt', (bx+x, by+y, bz+0.03), 0.012, 0.012, m['dark'], vertices=6)
    cylinder('Robot base flange', (bx, by, bz+0.055), 0.145, 0.065, m['dark'])
    cylinder('Base motor shroud', (bx, by, bz+0.15), 0.115, 0.16, m['white'])
    cylinder('Base status ring', (bx, by, bz+0.225), 0.116, 0.012, m['led'])
    p = [(bx, by, bz+0.28), (bx-0.25, by, bz+0.78),
         (bx+0.13, by, bz+1.09), (release[0]+0.035, release[1], release[2]+0.24)]
    for i, (a, b) in enumerate(zip(p, p[1:])):
        link('Robot cast link %d' % (i+1), a, b, 0.092-i*0.017, m['white'], 0.075-i*0.015)
    for i, pos in enumerate(p):
        radius = [0.108, 0.103, 0.089, 0.062][i]
        cylinder('Revolute joint %d' % i, pos, radius, radius*1.75, m['rubber'], axis=(0, 1, 0))
        for side in [-1, 1]:
            cap = (pos[0], pos[1]+side*radius*0.9, pos[2])
            cylinder('Joint machined rim', cap, radius*0.88, 0.013, m['metal'], axis=(0, 1, 0))
            cylinder('Joint enamel end cap', (cap[0], cap[1]+side*0.009, cap[2]),
                     radius*0.72, 0.012, m['white'], axis=(0, 1, 0))
            cylinder('Joint encoder cover', (cap[0], cap[1]+side*0.017, cap[2]),
                     radius*0.42, 0.005, m['dark'], axis=(0, 1, 0), bevel=0.001)
            cylinder('Joint centre insert', (cap[0], cap[1]+side*0.021, cap[2]),
                     radius*0.17, 0.004, m['metal'], axis=(0, 1, 0), bevel=0.001)
            for j in range(4):
                theta = j*math.pi/2+math.pi/4
                cylinder('Joint cap screw', (cap[0]+radius*0.76*math.cos(theta), cap[1]+side*0.015,
                                             cap[2]+radius*0.76*math.sin(theta)),
                         0.004, 0.004, m['dark'], axis=(0, 1, 0), bevel=0, vertices=6)
    # Wrist and parallel gripper are positioned around the initial ball.
    rx, ry, rz = release
    link('Wrist tool adapter', p[-1], (rx, ry, rz+0.135), 0.044, m['metal'])
    box('Parallel gripper actuator', (rx, ry, rz+0.107), (0.075, 0.16, 0.065), m['dark'])
    for sign in [-1, 1]:
        box('Gripper carriage', (rx, ry+sign*0.058, rz+0.072), (0.057, 0.033, 0.018), m['metal'], 0.003)
        box('Gripper finger', (rx, ry+sign*0.064, rz+0.018), (0.032, 0.021, 0.105), m['metal'], 0.003)
        box('Soft finger pad', (rx, ry+sign*0.050, rz+0.005), (0.034, 0.008, 0.045), m['rubber'], 0.002)
    tube('Arm braided service cable', [(bx, by+0.125, bz+0.18),
         (bx-0.36, by+0.12, bz+0.66), (bx-0.14, by+0.12, bz+1.16),
         (bx+0.24, by+0.12, bz+1.09), (rx+0.05, ry+0.065, rz+0.2),
         (rx, ry+0.042, rz+0.105)], 0.012, m['rubber'])
    tube('Bench service cable', [(bx, by+0.10, bz+0.12), (bx-0.25, by+0.19, bz+0.08),
         (bx-0.42, by+0.22, bz), (bx-0.52, by+0.22, bz-0.30), (bx-0.48, by+0.22, 0.18)], 0.013, m['rubber'])
    box('Robot service plate', (bx, by-0.116, bz+0.14), (0.085, 0.004, 0.054), m['dark'], 0.003)
    text('Robot base marking', 'R / 07', (bx-0.033, by-0.120, bz+0.135), 0.018, m['white'])


def cup(m, position, radius, height):
    # Lathed closed cross-section gives a real ceramic wall, lip and interior bottom.
    outer = radius + WALL_THICKNESS
    profile = cup_profile(radius, height)
    vertices, faces, n = [], [], 96
    for r, z in profile:
        vertices.extend([(position[0]+r*math.cos(i*2*math.pi/n),
                          position[1]+r*math.sin(i*2*math.pi/n), position[2]+z) for i in range(n)])
    for j in range(len(profile)-1):
        for i in range(n):
            a, b = j*n+i, j*n+(i+1)%n
            faces.append((a, b, b+n, a+n))
    mesh = bpy.data.meshes.new('Ceramic cup lathe')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new('Target cup | solid ceramic', mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(m['cup'])
    for face in mesh.polygons:
        face.use_smooth = True
    # Handle lies in the XZ plane, to the right of the target.
    points = [(position[0]+outer*0.97+0.065*math.sin(t), position[1],
               position[2]-height/2+0.066*math.cos(t)) for t in [i*math.pi/12 for i in range(13)]]
    tube('Ceramic cup handle', points, 0.012, m['cup'])
    return obj


def plant(m, position, scale=1):
    x, y, z = position
    link('Clay planter', (x, y, z), (x, y, z+0.21*scale), 0.10*scale, m['terracotta'], 0.135*scale)
    cylinder('Planter soil', (x, y, z+0.20*scale), 0.122*scale, 0.012, m['rubber'])
    for i in range(9):
        angle = i*2.4
        tip = (x+math.cos(angle)*0.20*scale, y+math.sin(angle)*0.20*scale, z+(0.40+0.10*(i%3))*scale)
        tube('Plant stem', [(x, y, z+0.17*scale), (x, y, z+0.33*scale), tip], 0.003*scale, m['green'])
        leaf = sphere('Plant leaf', tip, (0.052*scale, 0.13*scale, 0.008*scale), m['green'])
        leaf.rotation_euler = (0.4, 0.5, angle)


def furnishings(m):
    # Rear cabinetry with recessed reveals, brushed pulls and an oak countertop.
    box('Rear cabinet carcass', (0, 2.34, 0.44), (4.75, 0.70, 0.83), m['dark'])
    box('Rear cabinet countertop', (0, 2.31, 0.885), (4.86, 0.78, 0.055), m['wood'])
    for i in range(8):
        x = -2.08+i*0.595
        box('Cabinet door', (x, 1.972, 0.475), (0.575, 0.032, 0.73), m['white'], 0.005)
        box('Cabinet pull', (x+0.18, 1.942, 0.70), (0.014, 0.022, 0.15), m['metal'], 0.003)
    # Research station monitor: physical display, bezel, stand, and plotted traces.
    box('Monitor base', (1.40, 2.28, 0.93), (0.38, 0.25, 0.025), m['dark'])
    link('Monitor stand', (1.40, 2.32, 0.93), (1.40, 2.32, 1.24), 0.035, m['metal'])
    box('Monitor housing', (1.40, 2.29, 1.40), (0.77, 0.045, 0.45), m['dark'])
    screen = emission('Monitor pixels', (0.028, 0.070, 0.10), 0.55)
    box('Monitor screen', (1.40, 2.264, 1.40), (0.72, 0.002, 0.40), screen, 0.001)
    ink = emission('Monitor trace ink', (0.12, 0.64, 0.57), 1)
    text('Monitor title', 'TRAJECTORY / 001', (1.08, 2.259, 1.53), 0.035, m['white'])
    for j in range(3):
        tube('Display trajectory', [(1.09+i*0.014, 2.259, 1.27+j*0.03+0.08*math.sin(i*0.07+j)) for i in range(43)], 0.0018, ink)
    box('Keyboard', (1.40, 2.04, 0.926), (0.43, 0.13, 0.022), m['dark'], 0.007)
    for row in range(4):
        for col in range(13):
            box('Keyboard key', (1.21+col*0.029, 2.0+row*0.027, 0.94), (0.023, 0.021, 0.006), m['rubber'], 0.001)
    # Wall-mounted perforated equipment board.
    box('Equipment pegboard', (-1.10, 2.71, 1.69), (1.8, 0.032, 1.16), m['blue'])
    for ix in range(23):
        for iz in range(14):
            cylinder('Pegboard perforation', (-1.94+ix*0.075, 2.69, 1.20+iz*0.075),
                     0.007, 0.002, m['dark'], axis=(0, 1, 0), bevel=0, vertices=8)
    for i in range(5):
        x = -1.76+i*0.24
        link('Hanging tool shaft', (x, 2.655, 1.62), (x, 2.655, 1.99), 0.01, m['metal'])
        cylinder('Tool grip', (x, 2.655, 1.64), 0.027, 0.18, m['rubber'])
    box('Parts shelf', (-1.12, 2.55, 1.28), (1.52, 0.29, 0.035), m['metal'])
    for i in range(4):
        box('Parts bin', (-1.67+i*0.36, 2.54, 1.37), (0.29, 0.22, 0.14), m['dark'])
        box('Parts label', (-1.67+i*0.36, 2.425, 1.37), (0.13, 0.004, 0.045), m['white'], 0.001)
    text('Wall lab title', 'MOTION LAB', (0.17, 2.744, 2.43), 0.205, m['dark'])
    text('Wall lab subtitle', 'ROBOTICS  /  PHYSICAL INTELLIGENCE', (0.18, 2.742, 2.28), 0.041, m['blue'])
    plant(m, (2.73, 1.86, 0), 2.3)
    plant(m, (-2.04, 2.29, 0.915), 0.70)
    # Emergency stop box sits within reach on the workbench.
    box('Safety switch enclosure', (1.23, 0.40, 0.90), (0.18, 0.15, 0.08), m['dark'])
    yellow = material('Safety yellow', (0.90, 0.60, 0.025), 0.4)
    red = material('Emergency stop red', (0.65, 0.018, 0.014), 0.3)
    cylinder('E-stop collar', (1.23, 0.40, 0.945), 0.045, 0.01, yellow)
    cylinder('E-stop mushroom', (1.23, 0.40, 0.965), 0.033, 0.03, red)
    # Bench-mounted stereo observation camera and its USB cable.
    cylinder('Vision mount foot', (0.58, 0.53, 0.874), 0.072, 0.026, m['dark'])
    cylinder('Vision mount post', (0.58, 0.53, 1.09), 0.018, 0.41, m['metal'])
    box('Stereo vision camera', (0.58, 0.53, 1.32), (0.19, 0.065, 0.065), m['dark'], 0.01)
    for x in [0.51, 0.65]:
        cylinder('Camera lens barrel', (x, 0.493, 1.32), 0.019, 0.02, m['metal'], axis=(0, 1, 0))
        cylinder('Camera lens glass', (x, 0.481, 1.32), 0.014, 0.005, m['rubber'], axis=(0, 1, 0), bevel=0)
    tube('Vision sensor cable', [(0.67, 0.56, 1.32), (0.70, 0.59, 1.15),
         (0.63, 0.61, 0.87), (0.90, 0.64, 0.87), (1.1, 0.72, 0.68)], 0.004, m['rubber'])


def build_room(data):
    random.seed(data.get('scene', {}).get('seed', 7))
    m = palette()
    if data.get('scene', {}).get('pbr_materials'):
        from panda_asset import oak_material
        m['wood'] = oak_material()
    params = data.get('env_params', {})
    scene = bpy.context.scene
    if data.get('scene', {}).get('pbr_materials'):
        scene.view_settings.exposure = -0.3
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'METERS'

    def section(name, function, *args):
        before = set(bpy.data.objects)
        function(*args)
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
        for obj in set(bpy.data.objects) - before:
            for parent in list(obj.users_collection):
                parent.objects.unlink(obj)
            collection.objects.link(obj)
        collection.asset_mark()

    section('01 | Architecture', room, m)
    section('02 | Workbench', workbench, m, params)
    release = data['history'][0][data['object_names'][0]]['position']
    if data.get('animation', {}).get('model') == 'franka_panda':
        from panda_asset import build_panda
        section('03 | Articulated Franka Panda', build_panda, m, data)
    else:
        section('03 | Robot at release', robot, m,
                data.get('scene', {}).get('robot_base', [-0.90, 0.20, 0.86]), release)
    section('04 | Lab furnishings', furnishings, m)
    for marker in data.get('markers', []):
        cup(m, marker['position'], marker.get('radius', 0.105), params.get('cup_height', 0.22))
    world = bpy.data.worlds.new('Daylight environment')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.66, 0.77, 1.0, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.22
    bpy.context.scene.world = world
    area('Large window daylight', (-3.18, -0.6, 2.1), (0, 0.1, 1.0), 480, (0.80, 0.89, 1.0), 3.1, 1.6)
    area('Ceiling softbox', (0.4, 0.4, 3.08), (0, 0, 0.8), 170, (1.0, 0.88, 0.73), 2.5, 1.3)
    area('Front bounce', (1, -3.5, 2.5), (-0.4, 0.2, 1.0), 85, (1.0, 0.95, 0.88), 3.0)
    area('Rear rim', (1.5, 2.55, 2.8), (-0.6, 0, 1.5), 90, (1.0, 0.88, 0.70), 1.7)
    settings = data.get('scene', {}).get('camera', {})
    bpy.ops.object.camera_add(location=settings.get('position', [3.6, -5.6, 3.1]))
    camera = bpy.context.object
    camera.name = 'Camera | robotics experiment'
    target = Vector(settings.get('target', [0, 0.25, 1.10]))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.lens = settings.get('lens', 48)
    camera.data.dof.use_dof = True
    camera.data.dof.focus_distance = (target-camera.location).length
    camera.data.dof.aperture_fstop = settings.get('fstop', 7.1)
    bpy.context.scene.camera = camera
    return m
