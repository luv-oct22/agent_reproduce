# Attraction world instances

Instances are organized as:

```text
attraction/
  <group>/
    group_manifest.json
    baseline/instance.json
    rule_1/instance.json
    rule_2/instance.json
    combined_rule/instance.json
```

Each branch is a complete executable world record. A group is comparison
metadata; it is not a runtime parent of the branch worlds.
