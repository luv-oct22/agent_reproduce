"""Law-contrastive visual exam for central-force latent worlds.

Pipeline (each stage is a function and a CLI subcommand of ``python -m src.law_contrastive``):

    build     simulate candidate outcomes and select exam items      -> items/<g>_<rule>.json
    export    write render manifests in the attraction scene format  -> renders/.../scene.json
    validate  zero-API reference policies and leakage checks         -> items/validation.json
    render    (manual) ./scripts/render_law_contrastive.sh           -> renders/.../*.png
    status    report item, render and history coverage
    exam      ask one model under one evidence arm                   -> results/.../ledger.jsonl
    run       exam for every model x arm in the config
    analyze   tables, paired contrasts and error composition         -> results/.../analysis.json

All paths and parameters come from ``configs/law_contrastive.yaml`` (see ``config.py``).
"""
