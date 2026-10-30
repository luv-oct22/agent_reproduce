"""Blender integration check: run with the saved Panda .blend and -- history.json."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from robotics.panda import PandaKinematics, TCP_OFFSET


data = json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
motion = data['animation']
model = PandaKinematics(base=data['scene']['robot_base'])
scene = bpy.context.scene
fps = scene.render.fps / scene.render.fps_base
max_error = 0
for sample in motion['samples']:
    frame = 1+sample['time']*fps
    scene.frame_set(int(frame), subframe=frame-int(frame))
    tcp, poses, _ = model.forward(sample['joints'], sample['opening'])
    for name, pose in poses.items():
        actual = np.array(bpy.data.objects['Panda | '+name].matrix_world)
        error = float(np.max(abs(actual-pose)))
        max_error = max(max_error, error)
        assert error < 2e-5, (sample['time'], name, error)
    if sample['time'] <= motion['lead_in']:
        ball = np.array(bpy.data.objects['ball'].matrix_world.translation)
        np.testing.assert_allclose(ball, tcp[:3, 3], atol=2e-5)
textures = [image for image in bpy.data.images if image.source == 'FILE']
assert len(textures) >= 3 and all(image.packed_file for image in textures)
assert len([c for c in bpy.data.collections if c.asset_data]) >= 4
print(f'PANDA_SCENE_VERIFIED: {len(motion["samples"])} poses; max transform error {max_error:.2g}; textures packed.')
