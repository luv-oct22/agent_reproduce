import math
import unittest
from pathlib import Path

import yaml

from src.envs.robotics_lab import RoboticsLabEnv
from src.objects.cup_geometry import WALL_THICKNESS, cup_body_distance


class RoboticsLabTests(unittest.TestCase):
    def make_env(self, position, velocity):
        env = RoboticsLabEnv()
        env.configure([{'name': 'ball', 'mass': 0.1, 'position': position, 'velocity': velocity}])
        return env

    def test_launch_captured_and_settled_above_cup_bottom(self):
        env = self.make_env([-0.45, -0.12, 1.35], [2.4, 0, 2.15])
        env.run()
        ball = env.get_object('ball')
        self.assertIn('ball', env._inside_cup)
        self.assertAlmostEqual(ball.position[2], 0.912)
        self.assertLessEqual(math.hypot(ball.position[0]-0.85, ball.position[1]+0.12), 0.065)
        self.assertLess(abs(ball.velocity[2]), 0.01)

    def test_ball_does_not_fall_through_table(self):
        env = self.make_env([0, 0, 1.3], [0, 0, 0])
        env.run()
        self.assertTrue(all(s['ball']['position'][2] >= 0.90 for s in env._history))
        self.assertNotIn('ball', env._inside_cup)

    def test_ball_outside_table_lands_on_floor(self):
        env = self.make_env([2, 0, 0.5], [0, 0, 0])
        env.run()
        self.assertAlmostEqual(env.get_object('ball').position[2], 0.04)

    def test_reset_reproduces_trajectory_and_clears_capture(self):
        env = self.make_env([-0.45, -0.12, 1.35], [2.4, 0, 2.15])
        env.run()
        final = env._history[-1]
        env.reset()
        self.assertEqual(env._inside_cup, set())
        self.assertEqual(env._history, [])
        env.run()
        self.assertEqual(env._history[-1], final)

    def test_free_flight_matches_semi_implicit_gravity(self):
        env = self.make_env([-0.45, -0.12, 1.35], [2.4, 0, 2.15])
        env.run()
        n, dt = 100, 0.001
        p = env._history[n]['ball']['position']
        self.assertAlmostEqual(p[0], -0.45 + 2.4*n*dt)
        self.assertAlmostEqual(p[2], 1.35 + 2.15*n*dt - 9.8*dt*dt*n*(n+1)/2)

    def test_longer_distance_throw_bounces_off_cup_exterior(self):
        path = Path(__file__).resolve().parents[1] / 'configs/robotics_lab_panda_longer_distance.yaml'
        config = yaml.safe_load(path.read_text())
        env = RoboticsLabEnv(**config['env']['params'])
        env.configure([{'name': 'ball', 'mass': .1,
                        'position': config['task']['params']['ball_position'],
                        'velocity': config['simulation']['velocity']}])
        env.run()
        self.assertTrue(any(s['ball']['velocity'][0] < 0 for s in env._history))
        self.assertNotIn('ball', env._inside_cup)
        for sample in env._history:
            distance, _ = cup_body_distance(sample['ball']['position'], env.cup_position, env._cup_profile)
            self.assertGreaterEqual(distance, env.ball_radius-1e-8)
        # Also check the exact temporal interpolation used for the 24 FPS video.
        for index in range(46):
            time = min(max(index/24-.65, 0), 1.2)
            step = min(int(time/env._dt), len(env._history)-2)
            fraction = (time-env._history[step]['time'])/env._dt
            a, b = [env._history[i]['ball']['position'] for i in (step, step+1)]
            p = [x+(y-x)*fraction for x, y in zip(a, b)]
            distance, _ = cup_body_distance(p, env.cup_position, env._cup_profile)
            self.assertGreaterEqual(distance, env.ball_radius-1e-6)

    def test_fast_exterior_impact_cannot_tunnel_through_wall(self):
        env = RoboticsLabEnv(uniform_gravity=[0, 0, 0])
        cx, cy, _ = env.cup_position
        env.configure([{'name': 'ball', 'position': [cx-.4, cy, .98], 'velocity': [10, 0, 0]}])
        env.step(dt=.05)
        ball = env.get_object('ball')
        self.assertLess(ball.velocity[0], 0)
        self.assertLessEqual(ball.position[0], cx-env.cup_radius-WALL_THICKNESS-env.ball_radius)
        self.assertEqual(env._dt, .05)
        self.assertAlmostEqual(env._time, .05)

    def test_rim_hit_bounces_up_without_entering_ceramic(self):
        env = RoboticsLabEnv(total_steps=150)
        cx, cy, rim = env.cup_position
        env.configure([{'name': 'ball', 'position': [cx+env.cup_radius+.003, cy, rim+.15],
                        'velocity': [0, 0, -2]}])
        env.run()
        self.assertTrue(any(s['ball']['velocity'][2] > 0 for s in env._history))
        for sample in env._history:
            distance, _ = cup_body_distance(sample['ball']['position'], env.cup_position, env._cup_profile)
            self.assertGreaterEqual(distance, env.ball_radius-1e-8)

    def test_ball_can_exit_open_cup(self):
        env = RoboticsLabEnv(total_steps=200, uniform_gravity=[0, 0, 0])
        cx, cy, rim = env.cup_position
        env.configure([{'name': 'ball', 'position': [cx, cy, rim-.1], 'velocity': [0, 0, 2]}])
        env.run()
        self.assertGreater(env.get_object('ball').position[2], rim+env.ball_radius)
        self.assertNotIn('ball', env._inside_cup)


if __name__ == '__main__':
    unittest.main()
