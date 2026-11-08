# WindShift v4 — controlled crossover follow-up

This package completes a 2x2 factorial of the **content** of agent advice and its **claimed age**. It does not depend on the Lida Safety collusion project. Existing v3 data and logs are embedded as immutable input evidence. Only **96 new model calls** are needed because two arms were already observed in v3.

## Read this first

- `V4_FROZEN_ANALYSIS_PLAN.md`: scientific reasoning, explicit after-v3 exploratory status, tests, and limitations.
- `windshift_v4.py`: data audit, prompt builder, budget-capped API runner, and factorial analysis.
- `data/v3_episodes.json` and `data/v3_calls_frozen.jsonl`: original unmodified v3 data/results; new runs do not overwrite them.
- `results/v4_cross_calls.jsonl`: new results appended only after explicit authorization in Colab.

## Run locally (no calls)

```bash
python windshift_v4.py preflight
python -m unittest discover -s tests -v
python windshift_v4.py run
```

## Call budget

The notebook leaves authorizations disabled by default. First authorize a capped pilot (`--max-new-calls 8`). If output IDs are valid and you have provider credits, authorize the rest (`--max-new-calls 96`); it resumes successful calls. It never silently retries paid requests after errors. A provider timeout may still have incurred a charge. You remain responsible for checking actual pricing and invoices.

## Analysis

```bash
python windshift_v4.py analyze
```

The analysis refuses to produce factorial conclusions without all 96 new valid calls. Do not create an artificial or fake output file to get around this. New results are scientifically exploratory. Current study uses a single LLM and 24 preexisting synthetic v3 episodes, so we explicitly **do not** claim external replication.
