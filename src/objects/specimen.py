"""Immutable ground-truth specimens shared by experiments and future scenes.

Never pass private_dict() to an agent. Units in the private manifest are SI.
"""
from dataclasses import dataclass
import math
import random


COLORS = {'blue': (.08, .35, .8, 1), 'orange': (1, .35, .05, 1),
          'green': (.1, .65, .25, 1), 'purple': (.5, .2, .75, 1),
          'gray': (.5, .5, .5, 1), 'red': (.8, .08, .08, 1),
          'yellow': (.95, .8, .08, 1), 'white': (.9, .9, .9, 1),
          'black': (.025, .025, .025, 1)}


@dataclass(frozen=True)
class Specimen:
    specimen_id: str
    mass_kg: float
    volume_m3: float
    color: str
    shape: str = 'cube'
    color_rgba: tuple[float, float, float, float] | None = None

    def __post_init__(self):
        if not isinstance(self.specimen_id, str) or not self.specimen_id:
            raise ValueError('Specimen IDs must be nonempty strings.')
        for value in (self.mass_kg, self.volume_m3):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('Specimen mass and volume must be finite positive numbers.')
        if self.shape not in ('cube', 'sphere') or not isinstance(self.color, str) or not self.color:
            raise ValueError('Specimens need a color and a supported cube or sphere shape.')
        rgba = self.color_rgba if self.color_rgba is not None else COLORS.get(self.color.lower(), COLORS['gray'])
        if not isinstance(rgba, (tuple, list)) or len(rgba) != 4 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1
                for v in rgba):
            raise ValueError('color_rgba must contain four finite numbers in [0, 1].')
        object.__setattr__(self, 'color_rgba', tuple(rgba))
        if not math.isfinite(self.density_kg_m3) or not math.isfinite(self.mass_kg*self.side_length_m**2/6):
            raise ValueError('Derived specimen properties must be finite.')

    @property
    def density_kg_m3(self):
        return self.mass_kg/self.volume_m3

    @property
    def side_length_m(self):
        return self.volume_m3**(1/3)

    @property
    def radius_m(self):
        return (3*self.volume_m3/(4*math.pi))**(1/3)

    def public_dict(self):
        return {'id': self.specimen_id, 'color': self.color, 'shape': self.shape}

    def private_dict(self):
        size = self.side_length_m if self.shape == 'cube' else 2*self.radius_m
        inertia = self.mass_kg*size**2/6 if self.shape == 'cube' else .4*self.mass_kg*self.radius_m**2
        return dict(self.public_dict(), mass_kg=self.mass_kg, volume_m3=self.volume_m3,
                    density_kg_m3=self.density_kg_m3,
                    geometry={'dimensions_m': [size]*3, 'collision_shape': 'box' if self.shape == 'cube' else 'sphere',
                              'center_of_mass_local_m': [0, 0, 0]},
                    appearance={'color_rgba': list(self.color_rgba), 'color_space': 'linear_srgb'},
                    physics={'rigid': True, 'uniform_density': True, 'porous': False,
                             'absorbs_water': False,
                             'inertia_diagonal_kg_m2': [inertia]*3})

    @classmethod
    def from_dict(cls, data):
        """Read authored or saved SI properties; reject inconsistent derived data."""
        appearance = data.get('appearance', {})
        obj = cls(data['id'], data['mass_kg'], data['volume_m3'], data.get('color', 'gray'),
                  data.get('shape', 'cube'), data.get('color_rgba', appearance.get('color_rgba')))
        expected = obj.private_dict()
        for key in ('density_kg_m3', 'geometry', 'appearance', 'physics'):
            if key in data and data[key] != expected[key]:
                raise ValueError(f'Inconsistent saved specimen {key}.')
        return obj


def generate_specimens(seed):
    rng = random.Random(seed)
    properties = []
    for density in (500, 800, 1200, 1600):
        volume_ml = rng.choice((40, 50, 60, 80, 100, 120))
        properties.append((density*volume_ml*1e-6, volume_ml*1e-6))
    rng.shuffle(properties)
    return [Specimen(f'sample_{letter}', mass, volume, color)
            for letter, color, (mass, volume) in zip('ABCD', ('blue', 'orange', 'green', 'purple'), properties)]
