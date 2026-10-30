"""Versioned, immutable data contracts. These records do not execute physics or tools."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re

from src.objects.specimen import Specimen


def canonical(data):
    try:
        return json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError('Records must contain finite JSON values.') from exc


def keys(data, required, optional=()):
    if not isinstance(data, dict) or set(required)-data.keys() or data.keys()-set(required)-set(optional):
        raise ValueError(f'Expected keys {sorted(required)}; optional {sorted(optional)}.')


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', value):
        raise ValueError('Identifiers must contain letters, digits, underscores or hyphens.')


def number(value, minimum=None, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or (minimum is not None and value < minimum) or (positive and value <= 0)):
        raise ValueError('Expected a finite number within its physical bounds.')


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty text.')


def vector(values, length=3):
    if not isinstance(values, list) or len(values) != length:
        raise ValueError(f'Expected a vector of length {length}.')
    for v in values:
        number(v)


def unique(items):
    if len(items) != len(set(items)):
        raise ValueError('Duplicate identifiers or selectors.')


@dataclass(frozen=True, init=False)
class Record:
    """Store canonical JSON internally; callers receive independent copies."""
    _json: str
    format = 'record'

    def __init__(self, payload):
        encoded = canonical(payload)
        self.validate(json.loads(encoded))
        object.__setattr__(self, '_json', encoded)

    @property
    def payload(self):
        return json.loads(self._json)

    @property
    def record_id(self):
        return 'sha256:'+hashlib.sha256(canonical({
            'format': self.format, 'schema_version': 1, 'payload': self.payload}).encode()).hexdigest()

    def to_dict(self):
        return dict(format=self.format, schema_version=1, visibility='host_only',
                    record_id=self.record_id, payload=self.payload)

    @classmethod
    def from_dict(cls, data):
        keys(data, ('format', 'schema_version', 'visibility', 'record_id', 'payload'))
        if data['format'] != cls.format or type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported record format or schema version.')
        record = cls(data['payload'])
        if record.to_dict() != data:
            raise ValueError('Record fingerprint or visibility is inconsistent.')
        return record

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if type(self).load(path) != self:
                raise FileExistsError(f'Different record already exists: {path}')
        else:
            with path.open('x') as stream:
                json.dump(self.to_dict(), stream, indent=2, allow_nan=False)
                stream.write('\n')

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    @staticmethod
    def validate(data):
        raise NotImplementedError


class FieldSpec(Record):
    format = 'coefficient_field_spec'

    @staticmethod
    def validate(d):
        keys(d, ('id', 'kind', 'version', 'unit', 'bounds', 'parameters'))
        identifier(d['id'])
        if type(d['version']) is not int or d['version'] != 1:
            raise ValueError('Unsupported field version.')
        if d['unit'] not in ('kg/s', 'm/s^2', 'N', '1'):
            raise ValueError('Unsupported coefficient unit.')
        vector(d['bounds'], 2)
        low, high = d['bounds']
        if low > high:
            raise ValueError('Field bounds are reversed.')
        p = d['parameters']
        if d['kind'] == 'constant':
            keys(p, ('value',))
            values = [p['value']]
        elif d['kind'] in ('smoothstep_height', 'layered_height'):
            common = ('surface_id', 'extrapolation')
            identifier(p.get('surface_id'))
            if p.get('extrapolation') != 'constant_endpoints':
                raise ValueError('Height fields require explicit endpoint extrapolation.')
            if d['kind'] == 'smoothstep_height':
                keys(p, (*common, 'heights_m', 'values'))
                heights, values = p['heights_m'], p['values']
                if not isinstance(heights, list) or not isinstance(values, list) or len(heights) != len(values) or len(heights) < 2:
                    raise ValueError('Height/value samples must have matching lengths >= 2.')
                for z in heights:
                    number(z, minimum=0)
                if any(b <= a for a, b in zip(heights, heights[1:])):
                    raise ValueError('Height samples must increase strictly.')
            else:
                keys(p, (*common, 'boundary_height_m', 'lower_value', 'upper_value'))
                number(p['boundary_height_m'], positive=True)
                values = [p['lower_value'], p['upper_value']]
        elif d['kind'] == 'sinusoid_time':
            keys(p, ('offset', 'amplitude', 'period_s', 'phase_rad', 'time_origin_s'))
            for name in ('offset', 'phase_rad', 'time_origin_s'):
                number(p[name])
            number(p['amplitude'], minimum=0)
            number(p['period_s'], positive=True)
            values = [p['offset']-p['amplitude'], p['offset']+p['amplitude']]
        else:
            raise ValueError('Unknown field kind; expression strings are not executable.')
        for value in values:
            number(value)
            if not low <= value <= high:
                raise ValueError('Field values exceed declared bounds.')


LAW_UNITS = {'uniform_gravity': {'acceleration': 'm/s^2'},
             'linear_drag': {'coefficient': 'kg/s'},
             'central_attraction': {'strength': 'N'}}


class LawSpec(Record):
    format = 'physical_law_spec'

    @staticmethod
    def validate(d):
        keys(d, ('id', 'kind', 'version', 'parameters', 'fields'))
        identifier(d['id'])
        if d['kind'] not in LAW_UNITS or type(d['version']) is not int or d['version'] != 1:
            raise ValueError('Unsupported law kind/version.')
        keys(d['fields'], LAW_UNITS[d['kind']])
        for reference in d['fields'].values():
            identifier(reference)
        p = d['parameters']
        if d['kind'] == 'uniform_gravity':
            keys(p, ('direction',))
            vector(p['direction'])
            if not math.isclose(sum(v*v for v in p['direction']), 1., abs_tol=1e-12):
                raise ValueError('Gravity direction must be a unit vector.')
        elif d['kind'] == 'linear_drag':
            keys(p, ('medium_velocity_m_s',))
            vector(p['medium_velocity_m_s'])
        else:
            keys(p, ('exponent', 'reference_distance_m', 'reference_mass_kg',
                     'minimum_distance_m', 'coefficient_sample', 'mass_coupling'))
            for key in ('exponent', 'reference_distance_m', 'reference_mass_kg', 'minimum_distance_m'):
                number(p[key], positive=True)
            if p['coefficient_sample'] != 'pair_midpoint' or p['mass_coupling'] != 'inertial_mass':
                raise ValueError('Only midpoint sampling with inertial-mass coupling is specified in v1.')


class ObjectSpec(Record):
    format = 'physical_object_spec'

    @staticmethod
    def validate(d):
        keys(d, ('id', 'color', 'color_rgba', 'shape', 'mass_kg', 'volume_m3', 'motion'))
        identifier(d['id'])
        Specimen(d['id'], d['mass_kg'], d['volume_m3'], d['color'], d['shape'], d['color_rgba'])
        if d['motion'] not in ('dynamic', 'fixed'):
            raise ValueError('Object motion must be dynamic or fixed.')

    def properties(self):
        d = self.payload
        obj = Specimen(d['id'], d['mass_kg'], d['volume_m3'], d['color'], d['shape'], d['color_rgba'])
        return dict(mass_kg=obj.mass_kg, volume_m3=obj.volume_m3, density_kg_m3=obj.density_kg_m3,
                    **({'radius_m': obj.radius_m} if obj.shape == 'sphere' else {'side_length_m': obj.side_length_m}))

    def public_dict(self):
        d = self.payload
        return {k: d[k] for k in ('id', 'color', 'color_rgba', 'shape', 'motion')}


class ContactSpec(Record):
    format = 'contact_rule_spec'

    @staticmethod
    def validate(d):
        keys(d, ('id', 'kind', 'version', 'object_id', 'surface_id', 'surface_z_m',
                 'restitution', 'tangential_friction'))
        for key in ('id', 'object_id', 'surface_id'):
            identifier(d[key])
        if d['kind'] != 'normal_restitution' or type(d['version']) is not int or d['version'] != 1:
            raise ValueError('Unsupported contact kind/version.')
        number(d['surface_z_m'])
        number(d['restitution'], minimum=0)
        number(d['tangential_friction'], minimum=0)
        if d['restitution'] > 1:
            raise ValueError('Restitution must be at most one.')


class SolverSpec(Record):
    format = 'solver_spec'

    @staticmethod
    def validate(d):
        keys(d, ('kind', 'version', 'parameters'))
        identifier(d['kind'])
        if type(d['version']) is not int or d['version'] < 1:
            raise ValueError('Solver version must be a positive integer.')
        if not isinstance(d['parameters'], dict):
            raise ValueError('Solver parameters must be an object.')
        for name, value in d['parameters'].items():
            identifier(name)
            number(value, positive=True)


class ProtocolSpec(Record):
    format = 'experiment_protocol_spec'

    @staticmethod
    def validate(d):
        keys(d, ('id', 'track', 'instructions', 'tools', 'budget', 'clock', 'disclosures'))
        identifier(d['id'])
        text(d['instructions'])
        if d['track'] not in ('law_discovery', 'disclosed_law'):
            raise ValueError('Unknown experimental track.')
        keys(d['budget'], ('measurement_units', 'max_turns'))
        for value in d['budget'].values():
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError('Budgets must be positive integers or null when not recorded.')
        if d['budget']['measurement_units'] is None:
            raise ValueError('A measurement budget is required.')
        clock = d['clock']
        keys(clock, ('mode', 'start_time_s', 'time_range_s', 'reset_behavior'))
        if clock['mode'] not in ('resettable', 'continuous'):
            raise ValueError('Unknown clock mode.')
        expected = 'explicit_start_time' if clock['mode'] == 'resettable' else 'preserve_time'
        if clock['reset_behavior'] != expected:
            raise ValueError('Clock reset behavior contradicts its mode.')
        number(clock['start_time_s'])
        if clock['time_range_s'] is not None:
            vector(clock['time_range_s'], 2)
            if not clock['time_range_s'][0] <= clock['start_time_s'] <= clock['time_range_s'][1]:
                raise ValueError('Start time must lie within the clock domain.')
        if not isinstance(d['tools'], list) or not d['tools']:
            raise ValueError('A nonempty tool catalog is required.')
        for tool in d['tools']:
            keys(tool, ('name', 'description', 'parameters', 'measurements', 'sample_definition', 'cost'))
            identifier(tool['name'])
            text(tool['description'])
            text(tool['sample_definition'])
            if not isinstance(tool['parameters'], dict) or tool['parameters'].get('type') != 'object':
                raise ValueError('Tool arguments must have an object JSON schema.')
            schema = tool['parameters']
            if not isinstance(schema.get('properties'), dict) or schema.get('additionalProperties') is not False:
                raise ValueError('Tool schemas must declare properties and reject additional arguments.')
            required = schema.get('required', [])
            if not isinstance(required, list) or any(not isinstance(k, str) or k not in schema['properties'] for k in required):
                raise ValueError('Required tool arguments must reference declared properties.')
            unique(required)
            if not isinstance(tool['measurements'], list):
                raise ValueError('Tool measurements must be a list.')
            for reading in tool['measurements']:
                keys(reading, ('name', 'unit', 'resolution', 'range'))
                identifier(reading['name'])
                text(reading['unit'])
                number(reading['resolution'], positive=True)
                if reading['range'] is not None:
                    vector(reading['range'], 2)
                    if reading['range'][0] >= reading['range'][1]:
                        raise ValueError('Instrument range must increase strictly.')
            unique([r['name'] for r in tool['measurements']])
            cost = tool['cost']
            keys(cost, ('base_units', 'per_sample_units', 'per_simulated_second_units'))
            for value in cost.values():
                number(value, minimum=0)
        unique([t['name'] for t in d['tools']])
        if not isinstance(d['disclosures'], list):
            raise ValueError('Disclosures must be an explicit list.')
        for selector in d['disclosures']:
            text(selector)
            parts = selector.split('.')
            if len(parts) not in (2, 3) or parts[0] not in ('objects', 'laws', 'fields', 'contacts'):
                raise ValueError('Invalid disclosure selector.')
            for part in parts:
                identifier(part)
            if d['track'] == 'law_discovery' and parts[0] in ('laws', 'fields'):
                raise ValueError('Law-discovery protocols cannot disclose active laws or fields.')
        unique(d['disclosures'])

    def public_dict(self):
        d = self.payload
        return {k: d[k] for k in ('instructions', 'tools', 'budget', 'clock')}


class WorldSpec(Record):
    format = 'physical_world_spec'

    @staticmethod
    def validate(d):
        keys(d, ('coordinate_frame', 'motion_law', 'laws', 'fields', 'objects', 'contacts'))
        if d['coordinate_frame'] != 'cartesian_z_up_m' or d['motion_law'] != 'newton_second_law_v1':
            raise ValueError('Unsupported frame or motion law.')
        groups = {}
        for key, cls in (('laws', LawSpec), ('fields', FieldSpec), ('objects', ObjectSpec), ('contacts', ContactSpec)):
            if not isinstance(d[key], list):
                raise ValueError('World components must be lists.')
            records = [cls.from_dict(value) for value in d[key]]
            unique([r.payload['id'] for r in records])
            groups[key] = {r.payload['id']: r.payload for r in records}
        if not groups['laws'] or not groups['objects']:
            raise ValueError('A world requires laws and objects.')
        for law in groups['laws'].values():
            for parameter, ref in law['fields'].items():
                field = groups['fields'].get(ref)
                if field is None or field['unit'] != LAW_UNITS[law['kind']][parameter]:
                    raise ValueError('Missing coefficient field or inconsistent units.')
                if field['bounds'][0] < 0:
                    raise ValueError('These laws require nonnegative coefficient fields.')
        surfaces, pairs = {}, []
        for contact in groups['contacts'].values():
            if contact['object_id'] not in groups['objects']:
                raise ValueError('Contact refers to an unknown object.')
            surface = contact['surface_id']
            if surface in surfaces and surfaces[surface] != contact['surface_z_m']:
                raise ValueError('Conflicting positions for the same surface.')
            surfaces[surface] = contact['surface_z_m']
            pairs.append((contact['object_id'], surface))
        unique(pairs)
        for field in groups['fields'].values():
            if field['kind'] in ('smoothstep_height', 'layered_height') and field['parameters']['surface_id'] not in surfaces:
                raise ValueError('Height field refers to an unknown reference surface.')


class WorldInstance(Record):
    format = 'world_instance'

    @staticmethod
    def validate(d):
        keys(d, ('world', 'protocol', 'solver', 'provenance'))
        world = WorldSpec.from_dict(d['world'])
        protocol = ProtocolSpec.from_dict(d['protocol'])
        SolverSpec.from_dict(d['solver'])
        if not isinstance(d['provenance'], dict):
            raise ValueError('Provenance must be an object.')
        if any(f['payload']['kind'] == 'sinusoid_time' for f in world.payload['fields']):
            if protocol.payload['clock']['time_range_s'] is None:
                raise ValueError('Time-varying fields require an explicit clock domain.')
        for selector in protocol.payload['disclosures']:
            WorldInstance.disclosed_value(world, selector)

    @staticmethod
    def disclosed_value(world, selector):
        group, name, *attribute = selector.split('.')
        records = {r['payload']['id']: r for r in world.payload[group]}
        if name not in records:
            raise ValueError(f'Disclosure refers to an unknown component: {selector}')
        data = records[name]['payload']
        if group == 'objects':
            properties = ObjectSpec.from_dict(records[name]).properties()
            if len(attribute) != 1 or attribute[0] not in properties:
                raise ValueError('Object disclosures must select a supported physical property.')
            return properties[attribute[0]]
        if not attribute:
            return data
        if group == 'laws' and attribute == ['family']:
            return {k: data[k] for k in ('kind', 'version')}
        raise ValueError('Unsupported disclosure attribute.')

    def public_dict(self):
        """Only explicit disclosures and visible appearance; no host IDs or seeds."""
        d = self.payload
        world, protocol = WorldSpec.from_dict(d['world']), ProtocolSpec.from_dict(d['protocol'])
        return dict(protocol.public_dict(),
                    objects=[ObjectSpec.from_dict(o).public_dict() for o in world.payload['objects']],
                    known_properties={s: self.disclosed_value(world, s) for s in protocol.payload['disclosures']})

    def require_same_public_interface(self, other):
        if self.public_dict() != other.public_dict():
            raise ValueError('Worlds expose different public information or experimental interfaces.')
