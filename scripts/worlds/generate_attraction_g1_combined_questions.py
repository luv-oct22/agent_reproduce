"""Generate combined questions matched to the single-rule suites."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'world_instances/central_force_dynamics/central_force_dynamics_g1'
OUT = BASE/'combined_rule'


def main():
    baseline = json.loads((BASE/'baseline/instance.json').read_text())
    for variant_dir in sorted((BASE/'rule_1').glob('variant_*')):
        variant = variant_dir.name
        for qdir in sorted(variant_dir.glob('q??')):
            rule1 = json.loads((qdir/'instance.json').read_text())['question']
            rule2 = json.loads((BASE/'rule_2'/variant/qdir.name/'instance.json').read_text())['question']
            question = dict(rule1)
            question['rule'] = 'combined_rule'
            question['hidden_force_function'] = rule2['hidden_force_function']
            target = OUT/variant/qdir.name
            target.mkdir(parents=True, exist_ok=True)
            public = {k: question[k] for k in ('schema_version','question_id','family','group_id','rule','variant_id','pairing')}
            (target/'question.json').write_text(json.dumps(public, indent=2)+'\n')
            host = {
                'format': 'question_instance', 'schema_version': 1, 'visibility': 'host_only',
                'question': question,
                'baseline_world': {'path': 'baseline/instance.json', 'record_id': baseline['record_id']},
                'resolved_environment': {'equation': question['hidden_equation_parameters'],
                                         'force_function': question['hidden_force_function'],
                                         'scene_state': question['scene_state']},
            }
            (target/'instance.json').write_text(json.dumps(host, indent=2)+'\n')
    print('generated 90 combined_rule question instances')


if __name__ == '__main__': main()
