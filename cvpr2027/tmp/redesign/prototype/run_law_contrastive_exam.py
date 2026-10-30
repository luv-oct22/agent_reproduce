"""Law-contrastive exam: one model, one arm, all items of the selected conditions.

Arms (all reuse the existing interaction records, harness and run_evaluation loop):
  no_history   B = 0. Rendered context + candidates only.
  own          History of the world being tested (an existing interaction record).
  sibling      History of a sibling world (same regime + condition, different hidden law).
               When the sibling is also one of the item's three worlds, the sibling answer
               is a different label, so 'sibling' measures whether the history is used as
               evidence about this particular world.
  law_text     No history; the hidden law and regime constants are stated in text (ceiling).

Each (item, target world) pair is one question. The prompt states the launch velocity, start
time, and elapsed time in text because the existing renders carry no on-image captions.
Outputs one directory per question with the standard summary.json, plus a JSONL ledger.
"""
import argparse, json, os, random, sys, time
from pathlib import Path
from src.density_pipeline import RecordedHarness
from src.evaluate import run_evaluation
from src.harness import OpenAIHarness
from src.interact import InteractionRecord

ROOT = Path(__file__).resolve().parents[2]
ITEMS = ROOT / 'cvpr2027/experiments/law_contrastive_items'
RENDERS = ROOT / 'renders/law_contrastive/central_force_dynamics'
RESULTS = ROOT / 'results/law_contrastive'
WI = ROOT / 'world_instances/central_force_dynamics'
ARMS = ('no_history', 'own', 'sibling', 'law_text')


def safe(model):
    return ''.join(c if c.isalnum() or c in '_.-' else '_' for c in model)


def completed(path):
    try:
        rec = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    turns = sum(m.get('role') == 'assistant' for m in rec.get('messages', [])) + len(rec.get('skipped_turns', []))
    return bool(rec.get('finished')) or turns >= 8


def history_for(model, group, rule, variant, seed):
    """One completed interaction record of `model` in this world, chosen deterministically."""
    base = ROOT / 'results/central_force_dynamics' / group / rule / variant
    records = sorted(p for p in base.glob(f'q*/interaction/{safe(model)}_*/interaction.json') if completed(p))
    if not records:
        return None
    return records[random.Random(f'{seed}-{group}-{rule}-{variant}').randrange(len(records))]


def law_text(group, rule, variant):
    q = json.loads((WI / group / rule / variant / 'q01/instance.json').read_text())
    c, eq = q['baseline_world']['constants'], q['question'].get('hidden_equation_parameters') or q['question'].get('hidden_force_function')
    base = (f"Canonical law of this regime: F = G (m1/m_ref)(m2/m_ref)(r_ref/r)^2 with G = {c['strength_N']} N, "
            f"m_ref = {c['reference_mass_kg']} kg, r_ref = {c['reference_distance_m']} m, attraction toward the fixed anchor, "
            f"separations below {c['minimum_distance_m']} m excluded. ")
    hidden = []
    if 'q' in eq:
        hidden.append(f"This world replaces it with F = {eq['q']} G (m1/m_ref)^{eq['alpha']} (m2/m_ref)^{eq['beta']} "
                      f"(r_ref/r)^{eq['p']} [ln(e + r/r_ref)]^{eq['s']}.")
    if 'field_kind' in eq:
        hidden.append(f"The force is further multiplied by a coefficient field k(r, t) of kind '{eq['field_kind']}' with "
                      f"parameters {json.dumps({k: v for k, v in eq.items() if k not in ('q', 'alpha', 'beta', 'p', 's', 'field_kind')})}, "
                      f"where u = (r - r_ref)/r_ref and v = (t - reference_time_s)/time_scale; linear_space: 1 + a u; "
                      f"linear_time: 1 + a v; quadratic_space: 1 + a u^2; log_time: 1 + a ln(1 + |v|); "
                      f"space_time: 1 + a u + time_amplitude sin(2 pi v / 1.5); nested: 1 + 0.3 sin(pi u + 0.5 v) + 0.2 ln(1 + u^2) + 0.15 v^2.")
    return base + ' '.join(hidden)


def question_text(item, arm, group, rule, variant):
    L = item['launch']; p, v = L['position_m'], L['velocity_m_s']
    lead = {'no_history': 'You have not run any experiments in this world. Use the rendered context only.',
            'own': 'Use the evidence from your experiments in this same world.',
            'sibling': 'Use the evidence from your experiments in this same world.',
            'law_text': 'The governing law of this world is given below. ' + law_text(group, rule, variant)}[arm]
    return (f"{lead}\nThe context image shows the initial positions: the orange anchor is fixed, the blue probe moves. "
            f"Coordinates are sphere centres in metres, x right and z up, y = 0; the grid spacing is 0.10 m. "
            f"The probe starts at x = {p[0]:.3f}, z = {p[2]:.3f} m with velocity vx = {v[0]:.3f}, vz = {v[2]:.3f} m/s "
            f"at world time t = {L['start_time_s']:.1f} s. Which image shows the probe {L['duration_s']:.1f} s later? "
            f"All choices use the same camera and scale. Return exactly one character: A, B, C, or D.")


def jobs(args):
    for f in sorted(ITEMS.glob('g*_*.json')):
        g, rule = f.stem.split('_', 1)
        if args.groups and g not in args.groups or args.rules and rule not in args.rules:
            continue
        for item in json.loads(f.read_text()):
            for variant in sorted(item['answers']):
                yield item, f'central_force_dynamics_{g}', rule, variant


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--arm', choices=ARMS, required=True)
    ap.add_argument('--history-model', help='model whose interaction records supply history (default: --model)')
    ap.add_argument('--groups', nargs='*', default=[]); ap.add_argument('--rules', nargs='*', default=[])
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--temperature', type=float); ap.add_argument('--max-completion-tokens', type=int)
    ap.add_argument('--limit', type=int, default=0, help='stop after N questions (pilot)')
    ap.add_argument('--dry-run', action='store_true', help='build prompts and check inputs; no API calls')
    a = ap.parse_args()
    hist_model = a.history_model or a.model
    out_root = RESULTS / safe(a.model) / a.arm
    ledger = out_root / 'ledger.jsonl'; out_root.mkdir(parents=True, exist_ok=True)
    done = set()
    if ledger.exists():
        done = {(r['item'], r['variant']) for r in map(json.loads, ledger.read_text().splitlines()) if r.get('status') == 'complete'}
    kwargs = {k: v for k, v in dict(temperature=a.temperature, max_completion_tokens=a.max_completion_tokens).items() if v is not None}
    n = skipped = failed = 0
    for item, group, rule, variant in jobs(a):
        if (item['id'], variant) in done:
            continue
        if a.limit and n >= a.limit:
            break
        render = RENDERS / group / rule / item['id']
        if not (render / 'choice_D.png').exists():
            skipped += 1; continue
        record = None
        if a.arm in ('own', 'sibling'):
            if a.arm == 'own':
                source = variant
            else:  # nearest other world in this condition that has a record, fixed per (item, variant)
                others = [f'variant_{k}' for k in range(1, 7) if f'variant_{k}' != variant]
                random.Random(f"{a.seed}-{item['id']}-{variant}").shuffle(others)
                source = next((o for o in others if history_for(hist_model, group, rule, o, a.seed)), None)
            path = source and history_for(hist_model, group, rule, source, a.seed)
            if not path:
                skipped += 1; continue
            record = InteractionRecord.load(str(path))
        out = out_root / group / rule / item['id'] / variant
        out.mkdir(parents=True, exist_ok=True)
        q = dict(id=f"{item['id']}::{variant}", type='image_multiple_choice',
                 question=question_text(item, a.arm, group, rule, variant), context_caption='Context frame',
                 context_image=os.path.relpath(render / 'context.png', out),
                 choices=[dict(label=k, image=os.path.relpath(render / f'choice_{k}.png', out)) for k in 'ABCD'],
                 answer=item['answers'][variant])
        (out / 'questions.json').write_text(json.dumps([q], indent=1) + '\n')
        meta = dict(item=item['id'], variant=variant, group=group, rule=rule, arm=a.arm, model=a.model,
                    history_model=hist_model if record else None, history_record=str(path.relative_to(ROOT)) if record else None,
                    history_world=(source if record else None), answer=q['answer'], canonical_label=item['canonical_label'],
                    sibling_answer=(item['answers'].get(source) if a.arm == 'sibling' else None), generation_kwargs=kwargs)
        if a.dry_run:
            print(json.dumps(meta)); n += 1; continue
        harness = RecordedHarness(OpenAIHarness(model=a.model), out, 'law_contrastive_exam')
        try:
            ev = run_evaluation('law_contrastive_exam', harness, str(out / 'questions.json'), record,
                                with_history=record is not None, output_dir=str(out), generation_kwargs=kwargs)
            ans = ev.answers[0]['agent_answer']
            row = dict(meta, status='complete', agent_answer=ans, correct=ans == q['answer'],
                       picked_canonical=ans == item['canonical_label'],
                       picked_sibling=(ans == meta['sibling_answer']) if meta['sibling_answer'] else None)
            n += 1
        except Exception as exc:  # keep going; rerun resumes from the ledger
            row = dict(meta, status='failed', error=f'{type(exc).__name__}: {exc}'[:300]); failed += 1
        row['time_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (out / 'summary.json').write_text(json.dumps(row, indent=1) + '\n')
        with ledger.open('a') as fh:
            fh.write(json.dumps(row) + '\n')
        print(f"[{a.arm}] {item['id']} {variant}: {row['status']} {row.get('agent_answer', '')} (answer {q['answer']})", flush=True)
    print(f'Done: {n} answered, {skipped} skipped (missing render or history), {failed} failed. Ledger: {ledger}')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
