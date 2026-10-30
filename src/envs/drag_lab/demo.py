"""Computational reference policy; receives public observations and a submit callback only."""
from itertools import product

from src.worlds.layered_drag import LayeredDragWorld


def fit_profile(observation, readings, refinements=4):
    """Coarse-to-fine search over the declared family, never the episode's truth."""
    bounds = observation['profile_family']['parameter_bounds']
    names = ('boundary_height_m', 'lower_drag_kg_s', 'upper_drag_kg_s')
    windows = [list(bounds[name]) for name in names]
    ball = observation['specimens'][0]
    calibration = observation['calibration']
    args = (ball['mass_kg'], ball['radius_m'], calibration['restitution'])
    apparatus = observation['apparatus']
    best, best_loss = None, float('inf')
    def loss_at(values, cutoff=float('inf')):
        world = LayeredDragWorld(gravity_m_s2=calibration['gravity_m_s2'], **dict(zip(names, values)))
        loss = 0.0
        for reading in readings:
            prediction = world.drop_readings(reading['release_height_m'], *args)
            for field, resolution in [('time_to_first_impact_s', apparatus['clock_resolution_s']),
                                      ('first_rebound_height_m', apparatus['height_resolution_m'])]:
                loss += ((prediction[field]-reading[field])/resolution)**2
            if loss >= cutoff:
                break
        return loss
    for _ in range(refinements):
        steps = [(high-low)/6 for low, high in windows]
        grids = [[low+i*step for i in range(7)] for (low, _), step in zip(windows, steps)]
        for values in product(*grids):
            candidate = dict(zip(names, values))
            loss = loss_at(values, best_loss)
            if loss < best_loss:
                best, best_loss = candidate, loss
        windows = [[max(bounds[name][0], best[name]-step), min(bounds[name][1], best[name]+step)]
                   for name, step in zip(names, steps)]
    # A local simplex can follow coupled coefficient/boundary changes that a
    # shrinking rectangular grid would miss. No hidden episode data are used.
    def vertex(values):
        values = [min(bounds[n][1], max(bounds[n][0], v)) for n, v in zip(names, values)]
        return loss_at(values), values
    origin = [best[n] for n in names]
    simplex = [vertex(origin)]
    for i, name in enumerate(names):
        point = origin[:]
        step = .05*(bounds[name][1]-bounds[name][0])
        point[i] += step if point[i]+step <= bounds[name][1] else -step
        simplex.append(vertex(point))
    for _ in range(100):
        simplex.sort(key=lambda item: item[0])
        centre = [sum(p[1][i] for p in simplex[:-1])/3 for i in range(3)]
        worst = simplex[-1][1]
        reflected = vertex([2*c-w for c, w in zip(centre, worst)])
        if reflected[0] < simplex[0][0]:
            expanded = vertex([c+2*(r-c) for c, r in zip(centre, reflected[1])])
            simplex[-1] = min((reflected, expanded), key=lambda item: item[0])
        elif reflected[0] < simplex[-2][0]:
            simplex[-1] = reflected
        else:
            endpoint = reflected if reflected[0] < simplex[-1][0] else simplex[-1]
            contracted = vertex([c+.5*(p-c) for c, p in zip(centre, endpoint[1])])
            if contracted[0] < endpoint[0]:
                simplex[-1] = contracted
            else:
                anchor = simplex[0][1]
                simplex[1:] = [vertex([(a+p)/2 for a, p in zip(anchor, point[1])]) for point in simplex[1:]]
    return dict(zip(names, min(simplex, key=lambda item: item[0])[1]))


def run_demo(observation, submit):
    """Broad initial probes, then probes around the fitted boundary; <=7 measurements."""
    if observation['profile_family'].get('type') == 'unknown_smooth_height_function':
        raise ValueError('The fitted demo supports the two-layer config only. Use the model interaction or JSONL actions for a smooth profile.')
    apparatus = observation['apparatus']
    minimum, maximum = apparatus['min_release_height_m'], apparatus['max_release_height_m']
    if observation['experiments_remaining'] < 7:
        raise ValueError('The reference demo requires at least seven measurements.')
    readings = []
    def probe(height):
        result = submit({'operation': 'bounce', 'specimen_id': observation['specimens'][0]['id'],
                         'surface_id': observation['calibration']['surface_id'], 'release_height_m': height})
        if not result['success']:
            raise RuntimeError(result['error'])
        readings.append(result['observation'])
    for height in (minimum, maximum*.3, maximum*.65, maximum):
        probe(height)
    provisional = fit_profile(observation, readings, refinements=3)
    boundary_clearance = provisional['boundary_height_m']-observation['specimens'][0]['radius_m']
    for offset in (-.12, .12, .4):
        probe(round(min(maximum, max(minimum, boundary_clearance+offset)), 6))
    estimate = fit_profile(observation, readings)
    return submit(dict(operation='submit_drag_estimate', **estimate))
