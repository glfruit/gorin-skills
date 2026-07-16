# Routing Safety

Prevent skill trigger collisions and false activations.

1. Every trigger must have explicit **negative triggers**
2. Run `detect-overlap.sh` in Step 6
3. Triggers should be specific enough to avoid false positives
4. If overlap found: narrow triggers or merge skills
