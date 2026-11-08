# WindShift: Old Advice, New Evidence

Karan Verma | Independent Researcher | Apart Research Swarm Alignment Hackathon, November 2026

## Research question

When a peer recommendation conflicts with newer observations, do the recommendation's content and its claimed observation time affect a receiving language model's decision?

## Study design

WindShift evaluates controlled AI-agent handoffs using 24 repeatable WEST/EAST source-decision scenarios (16 reversals, four stable, four ambiguous), two decision points, and four combinations of recommendation content and claimed time. Frozen GPT-generated peer messages are reviewed by GPT-4o-mini, Gemini 3.1 Flash Lite, and Qwen3-235B. There are 576 matched receiver decisions, clustered within 24 episodes; they are not 576 independent scenarios.

A separate retrospective evaluation uses observed daily PM2.5 measurements from two Delhi monitoring stations. That evaluation provides the current measurement and decision threshold to each reviewer. It is not a real-world source-attribution study or a deployed monitoring system.

## Main findings

- The original GPT wrong-source comparison was null: 0/32 versus 0/32 on reversal decisions.
- On the exploratory content-by-time comparison, current versus historical recommendation content increased correct source choices by 46.9 percentage points for GPT-4o-mini, 9.4 for Gemini, and 4.7 for Qwen. These are exploratory associations under the controlled prompts, not proof of a deployed safety intervention.
- Across 192 receiver decisions per model, counts for correct / unnecessary abstention / unsupported source choice were GPT 117 / 51 / 24; Gemini 131 / 10 / 51; Qwen 135 / 38 / 19.
- In the separate Delhi evaluation, 360/360 reviewer classifications were correct. Because the current measured value and threshold were explicit, this ceiling result cannot establish the benefit of a freshness safeguard.

## Repository contents

- `source/v3/` and `source/v4/`: research runners, protocols, and unit tests.
- `input/`: frozen prompts and recorded model responses.
- `results/`: decision summaries and episode-clustered statistical analyses.
- `figures/`: figures for the controlled study.
- `real_data/`: retrospective Delhi evaluation, recorded outputs, source manifest, and audit.
- `development_history/`: exploratory stages and provenance.
- `paper/`: manuscript status information.

## Reproduce the checks (offline)

Run from the repository root:

```bash
python3 audit_three_models.py
python3 real_data/audit_public_real.py
```

The audit scripts operate on recorded results without API calls. Unit tests can also be run from the respective source folders. The public package does not redistribute the original station CSV downloads; their provenance and checksums are provided for source-level verification.

## Scope, limitations, and disclosure

The controlled WEST/EAST scenarios are generated evaluation cases, not measurements of actual pollution sources. Receivers were evaluated against fixed peer reports, not as an interactive, population-scale swarm. The original main hypothesis was not supported; later contrasts are exploratory. This independent project does not include unpublished Lida Safety collaboration materials. AI tools assisted with coding, analysis, and writing.

See `PREEXISTING_WORK_AND_DISCLOSURE.md`, `LIMITATIONS_AND_ETHICS.md`, `DATA_PROVENANCE.md`, and `LICENSE_STATUS.md` before reusing material. A final approved manuscript is not included here.
