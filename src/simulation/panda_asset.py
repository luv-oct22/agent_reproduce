"""Import the licensed Panda meshes and animate the MJCF joint hierarchy in Blender."""
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robotics.panda import PandaKinematics


def obj_mesh(path):
    """Read geometry and authored corner normals; materials come from MJCF."""
    vertices, normals, faces, corner_normals = [], [], [], []
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append(tuple(map(float, fields[1:4])))
        elif fields[0] == 'vn':
            normals.append(tuple(map(float, fields[1:4])))
        elif fields[0] == 'f':
            face, ns = [], []
            for field in fields[1:]:
                indices = field.split('/')
                vi = int(indices[0])
                face.append(vi-1 if vi > 0 else len(vertices)+vi)
                ni = int(indices[2]) if len(indices) > 2 and indices[2] else 0
                ns.append(normals[ni-1 if ni > 0 else len(normals)+ni] if ni else (0, 0, 0))
            faces.append(face)
            corner_normals.extend(ns)
    mesh = bpy.data.meshes.new(path.stem)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if normals:
        mesh.use_auto_smooth = True
        mesh.normals_split_custom_set(corner_normals)
    return mesh


def build_panda(materials, data):
    from robotics_room import box, cylinder
    model = PandaKinematics(base=data['scene']['robot_base'])
    base = Vector(data['scene']['robot_base'])
    box('Panda mounting plate', base-Vector((0, 0, 0.012)), (.23, .23, .024), materials['metal'], .005)
    for x in [-.085, .085]:
        for y in [-.085, .085]:
            cylinder('Mount bolt', base+Vector((x, y, .002)), .006, .005, materials['dark'], vertices=6)
    material_map = dict(white=materials['white'], off_white=materials['white'],
                        black=materials['rubber'], green=materials['led'], light_blue=materials['blue'])
    nodes, meshes = {}, {}
    for body in model.bodies:
        node = bpy.data.objects.new('Panda | '+body['name'], None)
        bpy.context.collection.objects.link(node)
        node.empty_display_size = .03
        node.parent = nodes.get(body['parent'])
        node.matrix_basis = Matrix(body['origin'].tolist())
        if node.parent is None:
            node.matrix_basis = Matrix((model.base @ body['origin']).tolist())
        node.rotation_mode = 'QUATERNION'
        nodes[body['name']] = node
        for geom in body['visuals']:
            mesh_name = geom['mesh']
            if mesh_name not in meshes:
                meshes[mesh_name] = obj_mesh(model.path.parent / 'assets' / model.meshes[mesh_name])
                meshes[mesh_name].materials.append(material_map[geom['material']])
            obj = bpy.data.objects.new('Panda | '+mesh_name, meshes[mesh_name])
            bpy.context.collection.objects.link(obj)
            obj.parent = node
    fps = data.get('animation', {}).get('fps', 60)
    for sample in data['animation']['samples']:
        frame = 1+sample['time']*fps
        for body in model.bodies:
            node = nodes[body['name']]
            if body.get('kind') == 'hinge':
                node.rotation_quaternion = Quaternion(body['quaternion']) @ Quaternion(Vector(body['axis']), sample['joints'][body['index']])
                node.keyframe_insert(data_path='rotation_quaternion', frame=frame)
            elif body.get('kind') == 'slide':
                node.location = Vector(body['position']) + Quaternion(body['quaternion']) @ (Vector(body['axis'])*sample['opening'])
                node.keyframe_insert(data_path='location', frame=frame)
    for node in nodes.values():
        if node.animation_data:
            for curve in node.animation_data.action.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
    nodes['link0']['source'] = 'MuJoCo Menagerie / Franka Panda; Apache-2.0'
    nodes['link0']['motion'] = data['animation']['motion_type']


def oak_material():
    """CC0 scanned wood, with UV-based color, roughness and OpenGL normal maps."""
    directory = Path(__file__).resolve().parents[2] / 'assets/materials/oak'
    mat = bpy.data.materials.new('Scanned wood | Poly Haven wood_table_001 | CC0')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    for filename, socket, color in [('Diffuse.jpg', 'Base Color', True), ('Rough.jpg', 'Roughness', False), ('nor_gl.jpg', 'Normal', False)]:
        texture = nodes.new('ShaderNodeTexImage')
        texture.image = bpy.data.images.load(str(directory / filename), check_existing=True)
        texture.image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
        texture.image.pack()
        if socket == 'Normal':
            normal = nodes.new('ShaderNodeNormalMap')
            normal.inputs['Strength'].default_value = .12
            links.new(texture.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], shader.inputs[socket])
        elif socket == 'Roughness':
            remap = nodes.new('ShaderNodeMapRange')
            remap.inputs['To Min'].default_value = .35
            remap.inputs['To Max'].default_value = .80
            links.new(texture.outputs['Color'], remap.inputs['Value'])
            links.new(remap.outputs['Result'], shader.inputs[socket])
        else:
            links.new(texture.outputs['Color'], shader.inputs[socket])
    mat.asset_mark()
    return mat
