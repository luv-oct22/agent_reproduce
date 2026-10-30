import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.robotics.panda import HOME, PandaKinematics, plan_motion
from src.simulation.export_history import export_history


ROOT = Path(__file__).resolve().parents[1]


class PandaMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            path = export_history(str(ROOT / 'configs/robotics_lab_panda.yaml'), [.9, 0, .6], str(Path(directory) / 'history.json'))
            cls.data = json.loads(Path(path).read_text())
        cls.model = PandaKinematics(base=cls.data['scene']['robot_base'])

    def test_jacobian_matches_finite_difference(self):
        tcp, _, jac = self.model.forward(HOME)
        for index in range(7):
            q = HOME.copy()
            q[index] += 1e-6
            numerical = (self.model.forward(q)[0][:3, 3]-tcp[:3, 3]) / 1e-6
            np.testing.assert_allclose(numerical, jac[:3, index], atol=1e-6)

    def test_release_pose_and_velocity_are_continuous(self):
        motion = self.data['animation']
        samples = motion['samples']
        index = next(i for i, s in enumerate(samples) if s['time'] == motion['lead_in'])
        release = self.data['history'][0]['ball']
        np.testing.assert_allclose(samples[index]['tcp'], release['position'], atol=1e-5)
        before, after = samples[index-1], samples[index+1]
        velocity = (np.array(after['tcp'])-before['tcp']) / (after['time']-before['time'])
        np.testing.assert_allclose(velocity, release['velocity'], atol=.04)
        for sample in samples:
            q = np.array(sample['joints'])
            self.assertTrue(np.all(q >= self.model.lower))
            self.assertTrue(np.all(q <= self.model.upper))
            self.assertLessEqual(sample['opening'], .04)
        self.assertLessEqual(motion['peak_joint_speed'], 2.0)

    def test_ball_settles_inside_cup(self):
        p = np.array(self.data['history'][-1]['ball']['position'])
        env = self.data['env_params']
        self.assertLessEqual(np.linalg.norm(p[:2]-np.array(env['cup_position'][:2])), env['cup_radius']-env['ball_radius']+1e-7)
        self.assertAlmostEqual(p[2], env['table_height']+.012+env['ball_radius'], places=4)

    def test_oversized_ball_and_excess_speed_rejected(self):
        from copy import deepcopy
        bad = deepcopy(self.data)
        bad['object_radius'] = .04
        with self.assertRaisesRegex(ValueError, 'gripper'):
            plan_motion(bad)
        bad = deepcopy(self.data)
        bad['scene']['robot']['max_joint_speed'] = .01
        with self.assertRaisesRegex(ValueError, 'joint speed'):
            plan_motion(bad)


if __name__ == '__main__':
    unittest.main()
