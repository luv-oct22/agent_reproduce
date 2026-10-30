# World-independent interaction and evaluation pipeline

The world instance should contain only executable world data: equations,
constants, objects, tools, solver settings, scene state, and answer keys. It
must not contain a model name, agent prompt, harness choice, interaction
script, evaluation script, or output directory.

The current `eval.py` combines those concerns. The target pipeline separates
them into five inputs:

```text
world instance + scene/question
        |
        +--> world runtime adapter ------> tool calls and measurements
        |
agent profile + harness profile ----------> interaction runner
        |
interaction record ----------------------> evaluation runner
        |
renderer profile + question --------------> render artifacts
```

## Canonical layout

```text
world_instances/<family>/<group>/<branch>/instance.json   # physics only
world_instances/<family>/<group>/<branch>/q01/question.json
world_instances/<family>/<group>/<branch>/q01/instance.json  # host-only resolved episode
configs/agents/<agent_id>.yaml                             # prompt/tool policy
configs/harnesses/<harness_id>.yaml                        # provider/model/retry
configs/renderers/<renderer_id>.yaml                       # camera/output policy
src/world_runtime/                                          # load/execute world
src/agents/                                                 # agent profiles
src/harness/                                                 # model adapters
src/pipeline/                                                # runners/contracts
scripts/pipeline/interact_question.sh
scripts/pipeline/evaluate_question.sh
results/<agent_id>/<world_id>/<question_id>/interaction/
results/<agent_id>/<world_id>/<question_id>/evaluation/
```

The `world_id` is read from the immutable instance record. The runner never
selects a world from a model answer, and the agent profile never changes world
constants.

## Interaction runner

The interaction command should accept explicit paths and IDs:

```text
interact_question \
  --world-instance <instance.json> \
  --question <q01/question.json> \
  --agent-config configs/agents/<agent_id>.yaml \
  --harness-config configs/harnesses/<harness_id>.yaml \
  --output-dir results/<agent>/<world>/<question>/interaction
```

It loads the world runtime, exposes only that world's declared tools, creates
the agent from its profile, and writes an interaction record containing
`world_id`, `scene_id`, `question_id`, `agent_id`, `harness_id`, tool calls,
observations, token usage, and completion status. No score or answer key is
written into the model-visible conversation.

## Evaluation runner

Evaluation is a separate command:

```text
evaluate_question \
  --world-instance <instance.json> \
  --question <q01/question.json> \
  --interaction-record <interaction.json> \
  --agent-config configs/agents/<agent_id>.yaml \
  --harness-config configs/harnesses/<harness_id>.yaml \
  --renderer-config configs/renderers/<renderer_id>.yaml \
  --output-dir results/<agent>/<world>/<question>/evaluation
```

It verifies that the interaction record's `world_id` and `question_id` match
the supplied inputs, reconstructs the held-out scene from the world runtime,
renders images if required, asks the evaluation agent for an answer, and writes
the score and private ground truth only to the evaluation artifact. It must not
rerun or mutate the interaction.

## Agent and harness separation

An agent profile defines system instructions, allowed response format, tool
selection policy, and evaluation prompt. A harness profile defines the model
provider, model name, timeout, retry budget, and multimodal support. Multiple
agents can use one harness, and one agent can be evaluated with multiple
harnesses. Neither profile is stored in a world instance.

## Migration from the current scripts

1. Keep `src/harness` as the provider adapter and move model selection into a
   harness config.
2. Extract task/world loading from `eval.py` into `src/world_runtime`.
3. Use `Rule1AttractionBenchEnv` for Rule 1 questions: it loads fixed group
   constants from the world instance and hidden equation parameters from the
   question record, then exposes the same Python tool interface.
4. Move the interaction loop from `src/interact.py` into an interaction runner
   that receives a world adapter and agent profile.
5. Keep scoring and image generation in an evaluation runner that consumes an
   interaction record.
6. Make each per-question launcher a thin path wrapper;
   they should not contain physics, model, or scoring settings.

This permits the same world question to be evaluated with different agents and
harnesses, and permits the same agent to be compared across world families
without copying or modifying world records.
