import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.envs.robotics_lab import RoboticsLabEnv
from src.simulation.render_record import capture_metadata, write_record


class RenderRecordTests(unittest.TestCase):
    def make_data(self):
        config = {'env': {'type': 'robotics_lab', 'params': {}},
                  'simulation': {'velocity': [.9, 0, .6]}}
        env = RoboticsLabEnv(total_steps=1)
        env.configure([{'name': 'ball', 'mass': .1, 'position': [-.4, -.12, 1.32],
                        'velocity': [1.4, 0, .8]}])
        env.run()
        return {'history': env._history, 'object_radius': .025,
                'parameter_metadata': capture_metadata(config, env, 'config.yaml')}

    def test_records_runtime_override_and_defaults(self):
        data = self.make_data()
        with tempfile.TemporaryDirectory() as directory:
            path = write_record(directory, data, {'Samples': 24}, 'scene.png')
            contents = path.read_text()
            self.assertIn('[1.4, 0, 0.8]', contents)
            self.assertNotIn('[0.9, 0, 0.6]', contents)
            self.assertIn('| restitution | 0.28 |', contents)
            self.assertIn('| ball.mass_kg | 0.1 |', contents)

    def test_encode_writes_ten_second_record_and_preserves_still_record(self):
        # Exercise the actual encode entry point with only the expensive Blender
        # encode operation replaced; no frames or videos are rendered by tests.
        module_path = Path(__file__).resolve().parents[1] / 'src/simulation/render_saved_video.py'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history = root/'sim_history.json'
            history.write_text(json.dumps(self.make_data()))
            blend = root/'scene.blend'
            blend.write_bytes(b'test scene fingerprint')
            still = write_record(root, self.make_data(), {'Samples': 64}, 'scene.png')
            previous = still.read_text()
            bpy = SimpleNamespace(data=SimpleNamespace(filepath=str(blend)),
                                  context=SimpleNamespace(scene=object()),
                                  app=SimpleNamespace(version_string='test'))
            spec = importlib.util.spec_from_file_location('record_test_video', module_path)
            module = importlib.util.module_from_spec(spec)
            with patch.dict(sys.modules, {'bpy': bpy}):
                spec.loader.exec_module(module)
            args = argparse.Namespace(output_dir=str(root), history=str(history),
                                      mode='encode', fps=24, resolution=[960, 640],
                                      samples=24, hold=1, duration=10, video_name='simulation_10s.mp4')
            with patch.object(module, 'arguments', return_value=args), \
                 patch.object(module, 'scene_settings', return_value={}), \
                 patch.object(module, 'encode') as encode:
                module.main()
            encode.assert_called_once()
            contents = (root/'simulation_10s_parameters.md').read_text()
            self.assertIn('| Video duration (s) | 10 |', contents)
            self.assertIn('| Motion playback duration (s) | 8 |', contents)
            self.assertIn('| Encoded frames | 240 |', contents)
            self.assertEqual((root/'parameters.md').read_text(), contents)
            self.assertEqual(still.read_text(), previous)


if __name__ == '__main__':
    unittest.main()
