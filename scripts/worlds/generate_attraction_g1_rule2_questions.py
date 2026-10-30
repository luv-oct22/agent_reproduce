"""Generate rule_2 questions matched one-to-one with rule_1 scenes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'world_instances/central_force_dynamics/central_force_dynamics_g1'
OUT = BASE/'rule_2'
FUNCTIONS = {
    'variant_1': dict(field_kind='linear_space', amplitude=.3, time_scale=4., reference_time_s=2.),
    'variant_2': dict(field_kind='linear_time', amplitude=.2, time_scale=4., reference_time_s=2.),
    'variant_3': dict(field_kind='quadratic_space', amplitude=.4, time_scale=4., reference_time_s=2.),
    'variant_4': dict(field_kind='log_time', amplitude=.35, time_scale=2., reference_time_s=2.),
    'variant_5': dict(field_kind='space_time', amplitude=.25, time_amplitude=.2, time_scale=4., reference_time_s=2.),
    'variant_6': dict(field_kind='nested', amplitude=.3, time_scale=3., reference_time_s=2.),
}


def main():
    baseline = json.loads((BASE/'baseline/instance.json').read_text())
    for variant, function in FUNCTIONS.items():
        source = BASE/'rule_1'/variant
        for qdir in sorted(source.glob('q??')):
            source_instance = json.loads((qdir/'instance.json').read_text())
            question = source_instance['question']
            question['rule'] = 'rule_2'
            question['hidden_force_function'] = function
            question.pop('hidden_equation_parameters', None)
            question_dir = OUT/variant/qdir.name
            question_dir.mkdir(parents=True, exist_ok=True)
            public = {k: question[k] for k in ('schema_version','question_id','family','group_id','rule','variant_id','pairing')}
            (question_dir/'question.json').write_text(json.dumps(public, indent=2)+'\n')
            host = dict(source_instance)
            host['question'] = question
            host['resolved_environment'] = dict(host.get('resolved_environment', {}),
                force_function=function, scene_state=question['scene_state'])
            (question_dir/'instance.json').write_text(json.dumps(host, indent=2)+'\n')
    print('generated 90 rule_2 question instances')


if __name__ == '__main__': main()
