until [ "$(grep -c '^g' cvpr2027/experiments/build_law_contrastive_items.log)" -ge 9 ] && [ -f cvpr2027/experiments/law_contrastive_items/build_report.json ]; do sleep 20; done
sleep 30; echo builder-done
