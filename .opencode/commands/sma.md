---
description: Run the sports-data-model-architect skill for data model auditing and design
---

Use the sports-data-model-architect skill to $ARGUMENTS

First, load the skill by calling the skill tool with name "sports-data-model-architect", then execute the audit-first workflow:
1. Run the audit scripts: audit_temporal_integrity.py, audit_feature_coverage.py, audit_entity_resolution.py
2. Return findings in severity order: critical -> high -> medium
3. Provide minimal change plan if implementation is requested
4. End with validation checklist and residual risks
