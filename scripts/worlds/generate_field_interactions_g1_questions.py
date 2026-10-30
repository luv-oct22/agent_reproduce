import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "world_instances" / "field_interactions" / "field_interactions_g1"

EQUATIONS = {
    f"variant_{i}": value
    for i, value in enumerate(
        (
            {"kind": "power_field", "p": 1.1},
            {"kind": "inverse_distance", "p": 1.3},
            {"kind": "log_field", "scale": 0.8},
            {"kind": "time_power", "p": 0.7},
            {"kind": "coupled_power", "p": 1.4, "q": 0.6},
            {"kind": "nested_field", "p": 1.2, "q": 0.8},
        ),
        1,
    )
}
FIELDS = {
    f"variant_{i}": value
    for i, value in enumerate(
        (
            {"field_kind": "linear_position", "amplitude": 0.2},
            {"field_kind": "linear_time", "amplitude": 0.2, "reference_time_s": 2.0},
            {"field_kind": "quadratic_position", "amplitude": 0.15},
            {"field_kind": "log_time", "amplitude": 0.25, "reference_time_s": 2.0},
            {"field_kind": "position_time", "amplitude": 0.2, "time_amplitude": 0.15},
            {"field_kind": "nested", "amplitude": 0.3, "reference_time_s": 2.0},
        ),
        1,
    )
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    constants = {
        "field_strength_N_C": 1.6,
        "field_gradient_per_m": 0.3,
        "field_direction": [0.8, -0.4, 0.2],
        "reference_position_m": 1.2,
        "reference_time_s": 2.0,
        "minimum_separation_m": 0.05,
    }
    baseline = {
        "format": "world_family_group",
        "schema_version": 1,
        "visibility": "host_only",
        "family": "field_interactions",
        "group_id": "field_interactions_g1",
        "constants": constants,
        "standard_equations": {
            "field_force": "F_i=q_i*E(x_i,t)",
            "net_force": "F_net=F_field+F_external",
            "acceleration": "a_i=F_i/m_i",
            "position_update": "x(t+dt)=x(t)+v*dt+0.5*a*dt^2",
        },
    }
    (OUT / "baseline").mkdir(parents=True, exist_ok=True)
    (OUT / "baseline" / "instance.json").write_text(json.dumps(baseline, indent=2) + "\n")
    for variant, equation in EQUATIONS.items():
        for index in range(1, 16):
            rng = random.Random(int.from_bytes(hashlib.sha256(f"field_interactions_g1:{variant}:{index}".encode()).digest()[:8], "big"))
            objects = []
            for j in range(2 + (index - 1) % 3):
                objects.append({
                    "object_id": f"object_{j + 1}",
                    "color": ["red", "blue", "green", "yellow"][j],
                    "mass_kg": round(rng.uniform(0.3, 2.0), 1),
                    "charge_c": round(rng.uniform(-1.5, 1.5), 1),
                    "position_m": [round(rng.uniform(-1.5, 1.5), 1), round(rng.uniform(-1.0, 1.0), 1), round(rng.uniform(0.4, 2.5), 1)],
                    "velocity_m_s": [round(rng.uniform(-1.2, 1.2), 1), round(rng.uniform(-1.0, 1.0), 1), round(rng.uniform(-1.2, 1.2), 1)],
                })
            state = {"objects": objects, "start_time_s": round(rng.uniform(0, 5), 1), "duration_s": round(rng.uniform(0.1, 0.3), 2), "target_object_id": objects[rng.randrange(len(objects))]["object_id"]}
            for branch in ("rule_1", "rule_2", "combined_rule"):
                question_dir = OUT / branch / variant / f"q{index:02d}"
                question_dir.mkdir(parents=True, exist_ok=True)
                question = {
                    "schema_version": 1,
                    "question_id": f"{variant}_q{index:02d}",
                    "family": "field_interactions",
                    "group_id": "field_interactions_g1",
                    "rule": branch,
                    "variant_id": variant,
                    "scene_state": state,
                    "target_object_id": state["target_object_id"],
                    "prompt": "Using the interaction history and rendered context, choose the image showing the target object at the next frame. Answer A, B, C, or D.",
                }
                host = {
                    "format": "question_instance",
                    "schema_version": 1,
                    "visibility": "host_only",
                    "question": question,
                    "equation_parameters": equation if branch in ("rule_1", "combined_rule") else None,
                    "force_function": FIELDS[variant] if branch in ("rule_2", "combined_rule") else None,
                }
                (question_dir / "instance.json").write_text(json.dumps(host, indent=2) + "\n")
                (question_dir / "question.json").write_text(json.dumps({k: question[k] for k in ("schema_version", "question_id", "family", "group_id", "rule", "variant_id", "target_object_id", "prompt")}, indent=2) + "\n")
                (question_dir / "README.md").write_text(f"# {branch}/{variant}/q{index:02d}\n\nHost-only field-interaction scene.\n")
    (OUT / "README.md").write_text("# field_interactions_g1\n\nShared constants:\n```json\n" + json.dumps(constants, indent=2) + "\n```\n")
    print("generated 270 field_interactions question instances")


if __name__ == "__main__":
    main()
