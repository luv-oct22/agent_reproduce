"""Write render manifests for law-contrastive items in the existing attraction scene format.

The manifests are consumed unchanged by src/simulation/blender_attraction.py, so the new exam
images share the camera, lighting, grid and sphere materials of the existing renders. Labels in
the manifest are the permuted labels chosen by the item builder; the host keeps the answer map.
"""
import argparse, json
from pathlib import Path
from src.simulation.attraction_visual import CAMERA, IMAGES, LAW_CONTRASTIVE_POLICY

ITEMS = Path('cvpr2027/experiments/law_contrastive_items')
OUT = Path('renders/law_contrastive/central_force_dynamics')


def objects_from(item):
    src = item['source']
    if src['kind'] == 'existing_render':
        scene = json.loads((Path(src['context_image']).parent / 'scene.json').read_text())
        return scene['objects']
    # Sampled scenes use the catalogue of the regime's existing renders.
    g = item['group']
    scene = json.loads(next(Path(f'renders/central_force_dynamics/{g}/rule_1/variant_1/q01').glob('scene.json')).read_text())
    return scene['objects']


def manifest(item):
    any_state = next(iter(item['choices'].values()))['state']
    initial = json.loads(json.dumps(any_state))
    initial['payload']['objects']['probe'] = dict(position_m=item['launch']['position_m'], velocity_m_s=item['launch']['velocity_m_s'])
    initial['payload']['objects']['anchor'] = dict(position_m=item['anchor_m'], velocity_m_s=[0., 0., 0.])
    initial['payload']['time_s'] = item['launch']['start_time_s']
    initial['record_id'] = 'law_contrastive_initial'
    return dict(format='attraction_prediction_scene', schema_version=1, visibility='host_only', id=item['id'],
                pair_id=item['id'], instance_id=item['id'], world_index=0, launch=item['launch'],
                initial_state=initial, objects=objects_from(item),
                choices={lab: dict(state=c['state']) for lab, c in sorted(item['choices'].items())},
                answer=None, answers=item['answers'], canonical_label=item['canonical_label'],
                camera=dict(CAMERA), candidate_policy=dict(LAW_CONTRASTIVE_POLICY), images=dict(IMAGES))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--items', default=str(ITEMS))
    p.add_argument('--out', default=str(OUT))
    a = p.parse_args()
    n = 0
    for f in sorted(Path(a.items).glob('g*_*.json')):
        for item in json.loads(f.read_text()):
            d = Path(a.out) / item['group'] / item['rule'] / item['id']
            d.mkdir(parents=True, exist_ok=True)
            (d / 'scene.json').write_text(json.dumps(manifest(item), indent=1) + '\n')
            n += 1
    print(f'wrote {n} manifests under {a.out}')


if __name__ == '__main__':
    main()
