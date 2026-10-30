"""Reference policy using only public observations and tool responses."""
import math


def run_demo(observation, submit):
    apparatus = observation['apparatus']['bounce_tower']
    maximum = apparatus['max_release_height_m']
    heights = [max(apparatus['min_release_height_m'], maximum/2), maximum]
    gravities, estimates = [], []
    for specimen in observation['specimens']:
        coefficients = []
        for height in heights:
            result = submit({'operation': 'bounce', 'specimen_id': specimen['id'],
                             'surface_id': apparatus['surface_id'], 'release_height_m': height})
            if not result['success']:
                raise RuntimeError(result['error'])
            reading = result['observation']
            time = reading['time_to_first_impact_s']
            if time <= 0:
                raise RuntimeError('Impact time is below instrument resolution.')
            gravities.append(2*reading['release_height_m']/time**2)
            coefficients.append(math.sqrt(reading['first_rebound_height_m']/reading['release_height_m']))
        estimates.append({'specimen_id': specimen['id'], 'surface_id': apparatus['surface_id'],
                          'restitution': min(1, sum(coefficients)/len(coefficients))})
    submit({'operation': 'submit_world_estimate', 'gravity_m_s2': sum(gravities)/len(gravities)})
    return submit({'operation': 'submit_contact_estimates', 'estimates': estimates})
