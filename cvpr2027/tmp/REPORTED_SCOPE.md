# Reported scope (decided 2026-10-28)

The paper reports rule_1 (structural law change) and rule_2 (hidden coefficient field) only.

combined_rule is excluded. Until 2026-10-28, `Worlds.hidden_law()` in src/law_contrastive/worlds.py
returned only the equation for combined worlds and dropped the hidden field. So every combined_rule
item, render, episode frame and exam answer built before then is a structural world, not a combined
one. The function now merges the two, but the existing combined artifacts were not rebuilt.

Paper numbers: `PYTHONPATH=. python cvpr2027/tmp/paper_numbers.py --tex cvpr2027/author-kit-CVPR2026-v1-latex-/numbers.tex`
(filters to rule_1/rule_2; the paper reads the macros through \V{...}).
