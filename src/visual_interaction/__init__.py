"""Visual interaction: agents learn a hidden-law world by running experiments whose outcomes they see.

Pipeline (each stage is a CLI subcommand of ``python -m src.visual_interaction``):

    prepare   simulate the experiment menu in every world; write outcome and render manifests (no API)
    render    (manual, GPU) ./scripts/render_visual_interaction.sh -> renders/visual_interaction/**.png
    status    frames, episodes and exam answers per model and mode
    episodes  run one interaction episode per world (with checkpoints) for a model and mode
    exam      frozen exam on the law-contrastive exam pool under each evidence arm
    analyze   checkpoint learning curves, exam tables and paired contrasts

All paths and parameters come from ``configs/visual_interaction.yaml`` (see ``config.py``).
Checkpoint and exam questions reuse the rendered law-contrastive items (``src.law_contrastive``).
"""
