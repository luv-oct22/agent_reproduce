"""Shared runtime for the generated non-central world families."""
from __future__ import annotations
import math
from typing import Any
from src.envs.base import BaseEnv
from src.envs.registry import register_env
from src.objects.base import Object


class WorldFamilyEnv(BaseEnv):
    def __init__(self, family: str, constants: dict[str, Any] | None = None,
                 equation: dict[str, Any] | None = None, force_function: dict[str, Any] | None = None):
        super().__init__(); self.family=family; self.constants=constants or {}
        self.equation=equation or {}; self.force_function=force_function or {}

    def configure(self, objects: list[dict[str, Any]], start_time: float = 0.0) -> None:
        self._objects.clear(); self._time=float(start_time)
        for s in objects:
            obj = Object(name=s['object_id'], mass=float(s.get('mass_kg',1.0)),
                position=list(s.get('position_m',s.get('initial_position_m',[0,0,0]))),
                velocity=list(s.get('velocity_m_s',s.get('initial_velocity_m_s',[0,0,0]))),
                color=s.get('color','gray'), charge=float(s.get('charge_c',0.0)))
            obj.volume_m3 = float(s.get('volume_m3', 0.0))
            self.add_object(obj)

    def _acceleration(self, obj: Object) -> list[float]:
        c=self.constants; p=obj.position; v=obj.velocity; m=max(obj.mass,1e-9)
        if self.family == 'kinematics_dynamics': a=list(c.get('acceleration_m_s2',[0,0,0]))
        elif self.family == 'fluid_mechanics':
            rho=float(c.get('fluid_density_kg_m3',1.0)); g=float(c.get('gravity_m_s2',4.0)); vol=float(getattr(obj,'volume_m3',0.0) or 0.0)
            a=[0,0,g*(rho*vol/m-1.0)]
        elif self.family == 'contact_mechanics':
            g=float(c.get('gravity_m_s2',4.0)); a=[0,0,-g]
            plane=float(c.get('plane_z_m',0.0)); depth=plane-p[2]
            if depth>0: a[2]+=float(c.get('normal_stiffness_N_m',10.0))*depth/m-float(c.get('damping_kg_s',1.0))*v[2]/m
        elif self.family == 'dissipative_dynamics':
            a=list(c.get('external_acceleration_m_s2',[0,0,0])); lin=float(c.get('linear_drag_kg_s',0.0)); quad=float(c.get('quadratic_drag_kg_m',0.0)); speed=math.sqrt(sum(x*x for x in v))
            for i in range(3): a[i]-=(lin*v[i]+quad*speed*v[i])/m
        elif self.family == 'field_interactions':
            direction=c.get('field_direction',[0,0,0]); strength=float(c.get('field_strength_N_C',1.0)); a=[obj.charge*strength*x/m for x in direction]
        else: # elastic_dynamics
            k=float(c.get('spring_stiffness_N_m',8.0)); damp=float(c.get('damping_kg_s',0.0)); rest=float(c.get('rest_length_m',1.0)); anchor=c.get('anchor_position_m',[0,0,0])
            d=[p[i]-anchor[i] for i in range(3)]; r=math.sqrt(sum(x*x for x in d)) or 1e-9; f=-k*(r-rest)/r
            a=[f*d[i]/m-damp*v[i]/m for i in range(3)]
        return a

    def step(self, dt: float = 0.01) -> dict[str, Any]:
        dt=float(dt)
        for obj in self._objects.values():
            a=self._acceleration(obj)
            obj.position=[obj.position[i]+obj.velocity[i]*dt+0.5*a[i]*dt*dt for i in range(3)]
            obj.velocity=[obj.velocity[i]+a[i]*dt for i in range(3)]
        self._time+=dt; return self.observe()

    def reset(self) -> None: self._time=0.0
    def observe(self) -> dict[str, Any]:
        return {'family':self.family,'time':self._time,'objects':{n:{'position':list(o.position),'velocity':list(o.velocity),'mass':o.mass,'color':o.color} for n,o in self._objects.items()}}


def _factory(family):
    @register_env(family)
    class _Env(WorldFamilyEnv):
        def __init__(self, constants=None, equation=None, force_function=None):
            super().__init__(family, constants, equation, force_function)
    _Env.__name__ = ''.join(x.title() for x in family.split('_'))+'Env'
    return _Env

KinematicsDynamicsEnv=_factory('kinematics_dynamics')
FluidMechanicsEnv=_factory('fluid_mechanics')
ContactMechanicsEnv=_factory('contact_mechanics')
DissipativeDynamicsEnv=_factory('dissipative_dynamics')
FieldInteractionsEnv=_factory('field_interactions')
ElasticDynamicsEnv=_factory('elastic_dynamics')
