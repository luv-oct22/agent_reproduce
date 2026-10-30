#!/usr/bin/env bash
# build.sh — regenerate numbers.tex from the repo root, then compile main.pdf
# Usage: ./build.sh   (from any directory)
set -e
REPO=/mnt/shared-storage-user/chenliang1/agent_reproduce
TEX=$REPO/cvpr2027/author-kit-CVPR2026-v1-latex-
cd "$REPO"
source ~/miniconda3/etc/profile.d/conda.sh && conda activate agent_reproduce
PYTHONPATH=. python cvpr2027/tmp/paper_numbers.py --tex "$TEX/numbers.tex"
cd "$TEX"
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
echo "=== done: $TEX/main.pdf ==="
