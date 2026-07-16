# Trigger Eval Methodology

Evaluate trigger quality using train/dev/holdout split.

## Pipeline
1. Generate test cases: `python3 scripts/generate_trigger_cases.py <dir>`
2. Split: 60% train / 20% dev / 20% holdout
3. Evaluate: `python3 scripts/trigger_eval.py <dir>`
4. Metrics: precision, recall, F1

## Success Criteria
- F1 ≥ 0.8 on holdout set
- No false positive on unrelated skill triggers
- Negative triggers must fire correctly

## Regression
Store baseline in `evals/regression-baseline.json`. New versions must not regress > 5% F1.
