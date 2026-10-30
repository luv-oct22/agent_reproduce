"""Franka Panda forward kinematics and bounded inverse kinematics from MJCF.

This plans joint positions for visualization, not actuator torques or contact
dynamics. Ball flight and contact remain the physics environment's responsibility.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


DEFAULT_MODEL = Path(__file__).resolve().parents[2] / 'assets/robots/franka_panda/panda.xml'
HOME = np.array([0, -0.5, 0, -2.1, 0, 1.7, 0.7854])
TCP_OFFSET = np.array([0, 0, 0.1034])


def rotation(quaternion):
    q = np.asarray(quaternion, dtype=float)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def transform(position=(0, 0, 0), quaternion=(1, 0, 0, 0)):
    value = np.eye(4)
    value[:3, :3] = rotation(quaternion)
    value[:3, 3] = position
    return value


def axis_rotation(axis, angle):
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    result = np.eye(4)
    result[:3, :3] = np.eye(3) + np.sin(angle)*skew + (1-np.cos(angle))*(skew @ skew)
    return result


class PandaKinematics:
    def __init__(self, path=DEFAULT_MODEL, base=(-0.90, 0.20, 0.884)):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(f'Missing robot description: {self.path}. Run scripts/assets/fetch_lab_assets.py.')
        root = ET.parse(self.path).getroot()
        self.meshes = {m.get('name', Path(m.get('file')).stem): m.get('file')
                       for m in root.findall('asset/mesh')}
        self.bodies = []
        self.lower, self.upper = [], []
        self.base = transform(base)

        def visit(element, parent=None):
            pos = np.fromstring(element.get('pos', '0 0 0'), sep=' ')
            quat = np.fromstring(element.get('quat', '1 0 0 0'), sep=' ')
            joint = element.find('joint')
            info = dict(name=element.get('name'), parent=parent, origin=transform(pos, quat),
                        position=pos.tolist(), quaternion=(quat / np.linalg.norm(quat)).tolist(),
                        visuals=[dict(g.attrib) for g in element.findall('geom') if g.get('class') == 'visual'])
            if joint is not None:
                finger = joint.get('class') == 'finger'
                info['axis'] = np.fromstring(joint.get('axis', '0 1 0' if finger else '0 0 1'), sep=' ')
                info['kind'] = 'slide' if finger else 'hinge'
                if not finger:
                    info['index'] = len(self.lower)
                    lo, hi = np.fromstring(joint.get('range', '-2.8973 2.8973'), sep=' ')
                    self.lower.append(lo)
                    self.upper.append(hi)
            self.bodies.append(info)
            for child in element.findall('body'):
                visit(child, info['name'])

        visit(root.find('worldbody/body'))
        self.lower, self.upper = np.array(self.lower), np.array(self.upper)

    def forward(self, joints, opening=0.04):
        joints = np.asarray(joints)
        poses, origins, axes = {}, [], []
        for body in self.bodies:
            pose = (poses[body['parent']] if body['parent'] else self.base) @ body['origin']
            if body.get('kind') == 'hinge':
                origins.append(pose[:3, 3].copy())
                axes.append(pose[:3, :3] @ body['axis'])
                pose = pose @ axis_rotation(body['axis'], joints[body['index']])
            elif body.get('kind') == 'slide':
                pose = pose @ transform(body['axis'] * opening)
            poses[body['name']] = pose
        tcp = poses['hand'] @ transform(TCP_OFFSET)
        jacobian = np.array([np.r_[np.cross(axis, tcp[:3, 3]-origin), axis]
                             for origin, axis in zip(origins, axes)]).T
        return tcp, poses, jacobian

    def solve(self, target, seed=None, orientation=None, orientation_weight=0.35):
        q = np.clip(HOME if seed is None else np.array(seed, dtype=float), self.lower+0.002, self.upper-0.002)
        target = np.asarray(target)
        orientation = np.diag([1, -1, -1]) if orientation is None else np.asarray(orientation)
        for _ in range(300):
            tcp, _, jac = self.forward(q)
            ep = target-tcp[:3, 3]
            er = sum(np.cross(tcp[:3, i], orientation[:, i]) for i in range(3)) / 2
            if np.linalg.norm(ep) < 0.00001 and (not orientation_weight or np.linalg.norm(er) < 0.001):
                return q
            error = np.r_[ep, orientation_weight*er]
            weighted = jac.copy()
            weighted[3:] *= orientation_weight
            dq = weighted.T @ np.linalg.solve(weighted @ weighted.T + 0.0001*np.eye(6), error)
            q = np.clip(q+np.clip(dq, -0.10, 0.10), self.lower+0.002, self.upper-0.002)
        error = np.linalg.norm(self.forward(q)[0][:3, 3]-target)
        raise ValueError(f'Panda IK could not reach {target.tolist()} (position error {error:.4f} m)')


def hermite(a, b, va, vb, t, duration):
    """Cubic path with explicitly matched endpoint velocities."""
    u = np.clip(t / duration, 0, 1)
    return ((2*u**3-3*u**2+1)*a + (u**3-2*u**2+u)*duration*va
            + (-2*u**3+3*u**2)*b + (u**3-u**2)*duration*vb)


def plan_motion(data):
    settings = data.get('scene', {}).get('robot', {})
    if settings.get('asset') != 'franka_panda':
        return None
    model = PandaKinematics(base=data['scene']['robot_base'])
    ball = data['object_names'][0]
    release = np.asarray(data['history'][0][ball]['position'])
    velocity = np.asarray(data['history'][0][ball]['velocity'])
    lead = float(settings.get('lead_in', 0.65))
    settle = float(settings.get('follow_through', 0.28))
    rate = int(settings.get('motion_hz', 120))
    if lead <= 0 or settle <= 0 or rate < 30:
        raise ValueError('Positive motion durations and motion_hz >= 30 are required.')
    windup = release + np.asarray(settings.get('windup_offset', [-0.15, 0, -0.12]))
    rest = release + np.asarray(settings.get('recovery_offset', [0.12, 0.04, 0.06]))
    # Grip radius remains inside the Panda's physical 80 mm maximum aperture.
    radius = data['object_radius']
    if not 0 < radius < 0.038:
        raise ValueError('The Panda gripper needs a ball radius below 0.038 m.')
    closed = radius-0.0015
    samples, q = [], None
    times = sorted(set(np.linspace(0, lead+settle, round((lead+settle)*rate)+1).tolist() + [lead]))
    for t in times:
        if t <= lead:
            target = hermite(windup, release, np.zeros(3), velocity, t, lead)
        else:
            target = hermite(release, rest, velocity, np.zeros(3), t-lead, settle)
        q = model.solve(target, seed=q, orientation_weight=0.35 if q is None else 0)
        tcp = model.forward(q)[0][:3, 3]
        opening = closed + (0.04-closed)*np.clip((t-lead)/0.06, 0, 1)
        samples.append(dict(time=round(t, 8), joints=q.tolist(), opening=float(opening), tcp=tcp.tolist()))
    speeds = abs(np.diff([s['joints'] for s in samples], axis=0) / np.diff([s['time'] for s in samples])[:, None])
    limit = float(settings.get('max_joint_speed', 2.0))
    if speeds.max() > limit:
        raise ValueError(f'Planned joint speed {speeds.max():.3f} exceeds configured {limit} rad/s; reduce launch velocity or adjust the path.')
    return dict(lead_in=lead, duration=lead+max(settle, data['history'][-1]['time']), samples=samples,
                peak_joint_speed=float(speeds.max()),
                model='franka_panda', motion_type='kinematic IK; free ball uses environment physics')
