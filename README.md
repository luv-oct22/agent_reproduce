# Physics Simulation Benchmark

A framework for evaluating AI agents on physics reasoning tasks. Agents interact with simulation environments, then answer questions that test their understanding of physical dynamics.

The [world benchmark architecture](docs/world_benchmark_architecture.md) describes
the next extension: independently varying physical laws, object properties, and
spatial or temporal coefficient fields while sharing one recorded world across
experiments, simulation, rendering, and evaluation. The [shared record contracts
and drag adapter](docs/world_records.md) are implemented; broader runtime
composition remains planned. The drag pipeline is the working reference.

The [attraction-world runtime](docs/attraction_world.md) implements inverse-square
and inverse-cube forces with matched public interfaces and offline trajectory
previews. The [experimental bench](docs/attraction_bench.md) now provides six
agent-selected tools with budget, sensor and clock enforcement. The offline
[learnability audit](docs/attraction_audit.md) checks quantized evidence against
competing laws and held-out numerical predictions. The
[paired attraction image suite](docs/attraction_prediction.md) now prepares
16 questions, audits close candidates and provides a separate GPU render command.
The [intrinsic object-attribute baseline](docs/object_attribute_bench.md) provides
single-object measurements separately from world-law experiments.
The combined [autonomous experiment interface](docs/autonomous_experiment_tools.md)
also lets an agent select intrinsic and law tools within one shared episode.

The [frozen drag baseline](docs/drag_baseline.md) preserves the current 16-question
suite and historical model results, with an offline integrity and physics check
for future changes.

## Quick Start

The [hidden-layer drag lab](docs/drag_lab.md) adds two invisible height-dependent
air-drag layers. The model chooses release heights and receives only impact times
and rebound heights; mass, gravity and restitution are calibrated. Run
`python -m src.envs.drag_lab --demo` offline or
`bash scripts/interact/interact_drag_lab.sh --model 'YOUR_MODEL'` for interaction.
Its [drag image evaluation](docs/drag_lab.md#image-context-question-evaluation) uses
the recorded world and public interaction history: eight context-plus-four-choice
questions in `renders/lab_5/drag_prediction`. The older bounce batch uses no-drag physics.

For a more complex invisible drag function, add `--config configs/drag_lab_complex.yaml`
to the interaction command. This uses a fixed seeded random smooth curve instead of
two constant layers; its private record is shared with image simulation. See
[complex drag](docs/drag_lab.md#complex-random-height-function) for the complete commands.

The [world lab](docs/world_lab.md) adds a configurable hidden-gravity world (initially 3.0 m/s²), a timed-drop experiment and separate grading of the model's inferred gravity. Use `configs/world_lab_low_gravity.yaml` with task `identify_world`.

The [stage-2 bounce lab](docs/bounce_lab.md) adds spherical specimens and measured rebound experiments to infer gravity and specimen–surface restitution. Use `configs/bounce_lab.yaml` with task `identify_bounce`; `python -m src.envs.bounce_lab --demo` runs an offline reference policy. Every run records the world, objects and contact rules for subsequent visual scenes.

The [bounce visual evaluation](docs/bounce_prediction.md) now has 16 harder image-choice questions across two paired worlds. Both objects must be checked, launch heights are read from images, and multiple impacts must be tracked. Render with `bash scripts/render/render_bounce_prediction.sh --device CUDA`, then use `scripts/eval/eval_bounce_prediction.sh`; it reuses the first-world interaction and acquires a separate interaction for the second world.

```bash
git clone https://github.com/<your-username>/agent_reproduce.git
cd agent_reproduce
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
```

### Run a full benchmark (interaction + evaluation)

```bash
python eval.py \
    --tasks shoot_ball \
    --model gpt-4o \
    --max-turns 10 \
    --mode both \
    --questions questions.json \
    --config configs/shoot_ball.yaml
```

### Run interaction only

```bash
python eval.py \
    --tasks shoot_ball \
    --model gpt-4o \
    --mode interact
```

### Run evaluation only (from a saved interaction record)

```bash
python eval.py \
    --tasks shoot_ball \
    --model gpt-4o \
    --mode evaluate \
    --questions questions.json \
    --record results/shoot_ball_20240101_120000/interaction.json
```

## Requirements

- Python 3.10+
- An OpenAI API key (set `OPENAI_API_KEY` env var)
- Blender 3.0+ (optional, for video rendering only — see [Blender Installation](#blender-installation))

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Project Structure

```
.
├── eval.py                          # Main CLI entry point
├── configs/
│   ├── shoot_ball.yaml              # Env/task/renderer parameters
│   └── spring_system.yaml
├── src/
│   ├── envs/                        # Physics simulation environments
│   │   ├── base.py                  # BaseEnv abstract class
│   │   ├── registry.py              # @register_env decorator & lookup
│   │   ├── gravity_field/scene.py   # 3D gravity + projectile sim
│   │   └── spring_system/scene.py   # Spring-connected particles
│   ├── tasks/                       # Benchmark tasks
│   │   ├── base.py                  # BaseTask abstract class
│   │   ├── registry.py              # @register_task decorator & lookup
│   │   └── shoot_ball/task.py       # Shoot a ball into a cup
│   ├── harness/                     # LLM interface
│   │   ├── base.py                  # ModelHarness abstract class
│   │   ├── openai.py               # OpenAI GPT harness (tool calling)
│   │   └── types.py                # Message, ToolCall, ToolDef, etc.
│   ├── objects/                     # Physics object definitions
│   │   └── base.py                  # Object dataclass
│   ├── simulation/                  # Rendering & visualization
│   │   ├── config.py                # YAML config loader
│   │   ├── renderer.py              # Matplotlib 2D/3D renderer
│   │   ├── threejs_renderer.py      # Three.js interactive HTML renderer
│   │   ├── blender_render.py        # Blender Python script (MP4 video)
│   │   ├── export_history.py        # Export sim history to JSON
│   │   ├── render_scene.py          # Unified render CLI
│   │   └── snapshot.py              # Snapshot dataclass
│   ├── interact.py                  # Agent interaction loop
│   └── evaluate.py                  # Question-based evaluation
├── scripts/
│   ├── render/
│   │   ├── render.sh                # Matplotlib PNG rendering
│   │   ├── render_threejs.sh        # Three.js HTML rendering
│   │   └── render_video.sh          # Blender MP4 rendering
│   ├── interact/interact.sh
│   ├── eval/evaluate.sh
│   └── full/
│       ├── run_both.sh
│       └── full_pipeline.sh
└── results/                         # Output directory (auto-created)
```

## How It Works

The pipeline has two phases:

### 1. Interaction Phase

The agent explores a physics environment through multi-turn conversation. It receives a text description of the scene and can take actions (e.g., set a ball's velocity) using tool calls. The agent signals readiness by calling a `finish` tool. The full conversation is saved as `interaction.json`.

### 2. Evaluation Phase

The agent answers questions from a `questions.json` file. Two question types are supported:

- **`multiple_choice`** — Choose A/B/C/D about the physics scenario.
- **`predict_next_frame`** — Given the state at step N, predict an object's position at step N+1. Scored by Euclidean distance within a tolerance.

Evaluation can run **with** the interaction history (the agent recalls what it learned) or **without** it (cold, no prior context).

## Environments

### `material_lab`: discover hidden object properties through experiments

The agent compares unknown specimens with an equal-arm beam balance and measures
water displacement in a graduated cylinder. It infers mass, volume, and density
from instrument readings; the tool interface does not expose the hidden values.
An experiment budget and notebook persist across actions. Submitted estimates
receive an acknowledgement only, with private scoring performed after interaction.

Run the environment without a model API or rendering:

```bash
python -m src.envs.material_lab --demo
```

Or use the existing model harness:

```bash
python eval.py --tasks identify_material --config configs/material_lab.yaml \
    --mode interact --model YOUR_MODEL --max-turns 64
```

See [the experimental-lab blueprint and action API](docs/material_lab.md) for manual
experiments, configuration, private scoring, and the specimen manifest that will
connect this environment to a separate future video-prediction scene. This stage
is a headless experimental environment; it does not render a buoyancy scene.

Each experimental run automatically writes a shared, host-only
`object_registry.json` and `object_registry.md` before the first model request.
Both the environment and the subsequent scene builder use this registry to retain
the exact same object properties, geometry, appearance, and identity. See the
[shared registry contract](docs/object_registry.md).

### `gravity_field`

3D gravitational field simulation. Objects move under uniform gravity and/or point-mass gravity. Configurable parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `g_constant` | 0 | Gravitational constant for point-mass gravity |
| `dt` | 0.001 | Time step |
| `total_steps` | 5000 | Number of simulation steps |
| `uniform_gravity` | `[0, 0, -9.8]` | Uniform gravity vector |

### `spring_system`

Spring-connected particle system. Step-by-step simulation with spring forces.

## Tasks

### `shoot_ball`

Shoot a ball to land in a cup. The agent sets the initial velocity `[vx, vy, vz]`; the simulation runs under gravity and checks if the ball passes through the cup opening.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cup_position` | `[5, 0, 0]` | Target cup location |
| `cup_radius` | 0.3 | Cup opening radius |
| `ball_position` | `[0, 0, 0]` | Ball starting position |

## Configuration

All env/task/renderer parameters are set via YAML config files:

```yaml
# configs/shoot_ball.yaml
env:
  type: gravity_field
  params:
    g_constant: 0
    dt: 0.001
    total_steps: 5000
    uniform_gravity: [0.0, 0.0, -9.8]

task:
  type: shoot_ball
  params:
    cup_position: [5.0, 0.0, 0.0]
    cup_radius: 0.3
    ball_position: [0.0, 0.0, 0.0]

renderer:
  projection: "2d"
  axes: [0, 2]       # x-axis vs z-axis
  xlim: [-1, 7]
  ylim: [-3, 5]
  figsize: [8, 6]
```

## Visualization

Successful render commands automatically write `parameters.md` in their output
directory, plus an output-specific record such as `scene_parameters.md` or
`simulation_10s_parameters.md`. Records include the actual release state (including
CLI overrides), resolved physics parameters, camera settings, and render/playback
timing. Saved-video frame batches also receive individual Markdown records.
`parameters.md` always describes the most recently completed output in that folder.

### Detailed Panda lab: reusable assets and articulated animation

`configs/robotics_lab_panda.yaml` assembles licensed Franka Panda meshes,
scanned wood materials and the procedural room into an editable Blender scene.
The seven robot joints and two fingers animate through a windup, release and
follow-through. A 50 mm ball fits inside the Panda gripper; its release position
and velocity match the subsequent simulated flight. The default clip has
0.65 seconds of arm preparation and 1.2 seconds of ball simulation, plus video
holds. Joint positions respect MJCF limits and sampled speeds are capped at
2 rad/s in this preset.

```bash
bash scripts/render/render_panda_lab.sh
bash scripts/render/render_panda_video.sh
# renders/lab_1/original_distance/scene.png       (1920×1280)
# renders/lab_1/original_distance/scene.blend     (packed, editable asset collections)
# renders/lab_1/original_distance/simulation.mp4  (960×640, 24 FPS)
```

For a quick still, append `--samples 24 --res-x 960 --res-y 640` to the first
command. Set `VIDEO_SAMPLES=16` for faster video rendering. Blender automatically
uses a supported GPU if exposed to the process and otherwise uses CPU; activating
a CUDA Python environment is not required. This workflow is tested with the
official Blender 3.6.23 build.

Edit [configs/robotics_lab_panda.yaml](configs/robotics_lab_panda.yaml) to
change the object parameters, camera and motion timing:

| Property | Configuration field | Current value |
|---|---|---|
| Ball release position | `task.params.ball_position` | `[-0.4, -0.12, 1.32]` |
| Ball release velocity | `simulation.velocity` | `[0.9, 0.0, 0.6]` |
| Ball radius | `task.params.ball_radius` and `env.params.ball_radius` | `0.025` |
| Cup position | `task.params.cup_position` and `env.params.cup_position` | `[-0.139, -0.12, 1.08]` |
| Cup radius | `task.params.cup_radius` and `env.params.cup_radius` | `0.085` |
| Robot base position | `scene.robot_base` | `[-0.90, 0.20, 0.884]` |
| Camera position | `scene.camera.position` | `[2.5, -4.8, 2.7]` |
| Preparation duration | `scene.robot.lead_in` | `0.65` seconds |

Positions use `[x, y, z]` in metres, with Z pointing upward. Velocities use
metres/second. The cup's Z coordinate specifies its opening height. Keep
parameters appearing under both `task` and `env` consistent. Changing the launch
automatically replans the arm animation; unreachable positions or excessive
joint speeds produce an error.

Regenerate the scene after edits and use a new video output directory:

```bash
bash scripts/render/render_panda_lab.sh
VIDEO_OUTPUT=renders/panda_video_v2 bash scripts/render/render_panda_video.sh
```

Cached frame settings include scene/history hashes to prevent mixing different
animations. `--step` still refers to time after release. The ball is currently
the moving physics object. Furniture placement and materials are editable in
the Blender scene or scene-building code; furniture dynamics and arbitrary
object velocities are not implemented.

The robot is animated with joint-limited inverse kinematics, with a free wrist
orientation during the swing. This is a visualization workflow, not a validated
robot controller: actuator torques, accelerations, grasp forces, self-collision
and robot/environment contacts are not simulated. Ball/table/cup physics retains
the benchmark's approximate contact model. Do not treat the animation as proof
that the throw can execute on hardware.

Asset sources, licenses, verification and Blender library reuse are described in
[assets/README.md](assets/README.md). Tests cover the kinematic Jacobian, release
continuity, limits and the ball settling inside the cup:

```bash
python scripts/assets/fetch_lab_assets.py --verify
python -m unittest discover -s tests -v
```

To check that the saved Blender hierarchy matches the kinematics at every
sample and that textures are packed:

```bash
.tools/blender-3.6.23-linux-x64/blender --background \
    renders/lab_1/original_distance/scene.blend --python-exit-code 1 \
    --python scripts/render/verify_panda_scene.py -- \
    renders/lab_1/original_distance/sim_history.json
```

### Realistic robotics laboratory

`configs/robotics_lab.yaml` provides a tabletop ball-and-cup experiment in a
procedurally modelled room. The Blender scene includes a robot arm and parallel
gripper, an oak and steel workbench, a solid ceramic cup, tiled flooring, window
daylight, ceiling lights, equipment storage, a monitor and plants. Materials use
procedural surface detail; no external models or textures are needed.

Render a high-quality PNG and save an editable, animated `.blend` scene:

```bash
bash scripts/render/render_robotics_lab.sh
# renders/robotics_lab/scene.png
# renders/robotics_lab/scene.blend
# renders/robotics_lab/sim_history.json
```

Render the ball in flight, or make a quick preview:

```bash
bash scripts/render/render_robotics_lab.sh --step 260 --output-dir renders/robotics_lab_flight
bash scripts/render/render_robotics_lab.sh --samples 24 --res-x 960 --res-y 640
```

Render a video with physical playback timing (1.6 seconds for this config):

```bash
python -m src.simulation.render_scene \
    --config configs/robotics_lab.yaml --format blender \
    --output-dir renders/robotics_lab_video \
    --fps 24 --frame-step 10 --samples 32 --res-x 960 --res-y 640
```

For an existing saved lab scene, use the resumable video renderer:

```bash
bash scripts/render/render_robotics_video.sh
# renders/robotics_lab_video/simulation.mp4
```

This renders 960×640 frames at 24 FPS in batches of eight, reuses completed PNG
frames after an interruption, and encodes H.264 using Blender's built-in video
sequencer. The clip includes a one-second pause at each end. The robot retains
its release pose while the ball follows the simulated trajectory. Set
`VIDEO_SCENE`, `VIDEO_HISTORY`, `VIDEO_OUTPUT`, `VIDEO_FPS`, or `VIDEO_SAMPLES` to
override defaults. Use a fresh output directory if the scene or render settings
change. No separate FFmpeg installation is needed.

The renderer uses Cycles, denoising, photographic color management and GPU
rendering when available, with a CPU fallback. An official Blender 3.6 build is
recommended; a build without OpenColorIO fails with an actionable error. Set
`BLENDER_BIN=/path/to/blender` or pass `--blender /path/to/blender` to select an
installation. The CLI also detects `.tools/blender-3.6.23-linux-x64/blender`.

Edit `scene.camera` in the YAML for viewpoint, lens and depth of field.
`simulation.velocity` sets the default launch. `--step` selects a simulation
sample for a still. Trajectory overlays are off for Blender by default; pass
`--trail 1` to include one. Room construction is in
`src/simulation/robotics_room.py`.

The `robotics_lab` physics environment uses metres and z-up coordinates. It adds
approximate sphere contact with the table/floor, descending capture through the
cup opening, interior wall response, and settling on the cup bottom. The robot
is a static visual fixture posed at release, not an actuated robot or a robot
collision model. The scene and physics share table bounds, cup dimensions, ball
radius and unscaled simulation coordinates. The outer cup shell and other room
furniture are visual geometry, not general rigid-body colliders.

The existing agent task works with this environment:

```bash
python eval.py --tasks shoot_ball --mode interact --config configs/robotics_lab.yaml
python -m unittest discover -s tests -v
```

Three rendering backends are available:

### Matplotlib (PNG images)

```bash
python -m src.simulation.render_scene \
    --config configs/shoot_ball.yaml \
    --output-dir renders \
    --format matplotlib \
    --velocity 5.0 0.0 5.0 \
    --every 500 \
    --trail 50
```

### Three.js (interactive HTML)

Generates a self-contained HTML file with 3D orbit controls and playback.

```bash
python -m src.simulation.render_scene \
    --config configs/shoot_ball.yaml \
    --output-dir renders \
    --format threejs \
    --velocity 5.0 0.0 5.0
# Open renders/simulation.html in a browser
```

### Blender (MP4 video)

Renders a photorealistic video using Blender's Cycles engine. Requires Blender to be installed (see [Blender Installation](#blender-installation) below).

```bash
python -m src.simulation.render_scene \
    --config configs/shoot_ball.yaml \
    --output-dir renders \
    --format blender \
    --velocity 5.0 0.0 5.0 \
    --fps 60 \
    --samples 64 \
    --frame-step 10

# Quick preview (lower quality, faster)
python -m src.simulation.render_scene \
    --config configs/shoot_ball.yaml \
    --output-dir renders \
    --format blender \
    --velocity 5.0 0.0 5.0 \
    --samples 16 \
    --res-x 960 --res-y 540
```

| Flag | Default | Description |
|------|---------|-------------|
| `--fps` | 60 | Video framerate |
| `--frame-step` | 10 | Simulation steps between animation keyframes; playback time is preserved |
| `--samples` | 64 | Ray-tracing quality (lower = faster) |
| `--res-x` | 1920 | Video width |
| `--res-y` | 1080 | Video height |

### Blender Installation

Blender is only needed for `--format blender` (MP4 video rendering). The other render formats (matplotlib, threejs) do not require it.

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install blender
```

**Snap (any Linux distro):**

```bash
sudo snap install blender --classic
```

**Download from blender.org (recommended for latest version):**

```bash
# 1. Download the tarball for your platform
wget https://download.blender.org/release/Blender4.1/blender-4.1.0-linux-x64.tar.xz

# 2. Extract
tar -xf blender-4.1.0-linux-x64.tar.xz

# 3. Add to PATH (append to ~/.bashrc for persistence)
export PATH="$PWD/blender-4.1.0-linux-x64:$PATH"

# 4. Verify
blender --version
```

**macOS:**

```bash
brew install --cask blender
```

**Windows:**

Download the installer from https://www.blender.org/download/ and add `blender.exe` to your system PATH.

**Verify installation:**

```bash
blender --version
# Expected: Blender 3.x or 4.x
```

**GPU acceleration (optional but recommended):**

Blender's Cycles engine uses GPU rendering when available. For NVIDIA GPUs, ensure CUDA drivers are installed. The render script automatically requests GPU mode — if no GPU is available, it falls back to CPU (slower).

For a fast test render, use low quality settings:

```bash
python -m src.simulation.render_scene \
    --config configs/shoot_ball.yaml \
    --output-dir renders \
    --format blender \
    --velocity 5.0 0.0 5.0 \
    --samples 16 \
    --res-x 640 --res-y 360 \
    --frame-step 50
```

## Adding a New Environment

1. Create `src/envs/<name>/scene.py`:

```python
from src.envs.base import BaseEnv
from src.envs.registry import register_env

@register_env("my_env")
class MyEnv(BaseEnv):
    def reset(self): ...
    def step(self): ...
    def observe(self) -> str: ...
```

2. Add `src/envs/<name>/__init__.py`:
```python
from .scene import *
```

3. Import it in `src/envs/__init__.py`.

## Adding a New Task

1. Create `src/tasks/<name>/task.py`:

```python
from src.tasks.base import BaseTask
from src.tasks.registry import register_task

@register_task("my_task")
class MyTask(BaseTask):
    def setup(self): ...
    def get_prompt(self) -> str: ...
    def get_action_space(self) -> list: ...
    def apply_action(self, action: dict): ...
    def evaluate(self) -> dict: ...
```

2. Add `src/tasks/<name>/__init__.py` and import in `src/tasks/__init__.py`.

3. Create a config file `configs/<name>.yaml`.

## Results

Each run creates a timestamped folder under `results/`:

```
results/shoot_ball_20240101_120000/
├── interaction.json    # Full conversation history
└── evaluation.json     # Question scores and answers
```

## Density balance image evaluation

The [liquid equilibrium task](docs/liquid_equilibrium.md) adds eight questions: infer a liquid's density from a floating object, then choose the image where all objects float or sink correctly. Use `--batch-dir renders/lab_3/liquid_equilibrium` in the same pipeline.

The [hard suite](docs/density_balance_hard.md) adds 32 balanced questions with one to three objects per pan, unseen colors and Unknown/cancellation reasoning. Select it with `--batch-dir renders/lab_2/density_balance_hard`.

Run new material experiments and all density-image questions in one pipeline:

```bash
bash scripts/eval/run_density_pipeline.sh --model 'YOUR_MODEL'
```

Both stages' responses, parameters, images and scores are saved in `results/density_pipeline/<timestamp>/`. See the [combined pipeline guide](docs/density_pipeline.md) for separate experiment/vision models and optional CUDA rendering.

After material-lab experiments, prepare a tabletop beam-balance question using the saved object registry. The scene uses equal-volume samples with the recorded colors, shapes and densities, and provides a level context image plus four choices: left down, right down, level and Unknown over a blurred context. See [the density balance guide](docs/density_balance.md) for CUDA rendering and evaluation commands.

## License

MIT
