"""Reference experimental policy using only the same public interface as an agent.

This policy is for the default calibrated, integer-gram specimen episodes.
It does not read a manifest, seed, private specimen state, or scoring output.
"""


def run_demo(observation, submit):
    weights = observation['apparatus']['balance']['reference_weights']
    available = sorted(weights, key=lambda item: item['mass_g'], reverse=True)
    maximum = int(min(sum(item['mass_g'] for item in available),
                      observation['apparatus']['balance']['capacity_per_pan_g']))

    def references(total):
        selected = []
        for item in available:
            if item['mass_g'] <= total:
                selected.append(item['id'])
                total -= item['mass_g']
        if total:
            raise RuntimeError('Reference weights cannot represent this trial mass.')
        return selected

    estimates = []
    for specimen in observation['specimens']:
        key = specimen['id']
        low, high, mass = 0, maximum, None
        while low <= high:
            trial = (low+high)//2
            result = submit({'operation': 'balance', 'left_pan': [key], 'right_pan': references(trial)})
            if not result['success']:
                raise RuntimeError(result['error'])
            reading = result['observation']['reading']
            if reading == 'level':
                mass = trial
                break
            if reading == 'left_down':
                low = trial+1
            elif reading == 'right_down':
                high = trial-1
            else:
                raise RuntimeError('Balance overloaded; the demo cannot characterize this specimen.')
        if mass is None or mass <= 0:
            raise RuntimeError('No measurable positive integer-gram mass found within the reference range.')
        result = submit({'operation': 'displace', 'specimen_id': key})
        if not result['success']:
            raise RuntimeError(result['error'])
        measurement = result['observation']
        if measurement['reading'] != 'settled':
            raise RuntimeError('Cylinder overflowed; no volume estimate is available.')
        volume = measurement['water_level_after_ml']-measurement['water_level_before_ml']
        if volume <= 0:
            raise RuntimeError('Volume is below the cylinder resolution.')
        estimates.append({'specimen_id': key, 'mass_g': mass, 'volume_ml': volume,
                          'density_kg_m3': 1000*mass/volume})
    return submit({'operation': 'submit_estimates', 'estimates': estimates})
