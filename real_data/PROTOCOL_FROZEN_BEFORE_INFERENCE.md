# WindShift — retrospective validation with real Delhi PM2.5 observations

Status: **Prospective; no authentic CPCB rows or model inference results have been obtained in this execution environment.**
Protocol version: 1.0 — 2026-11-08, frozen before data download or API inference.

## Motivation and question
The original WindShift v1–v4 experiments used synthetic two-source observations to investigate the effect of peer recommendation content and claimed freshness on downstream reviewer decisions. These are real LLM experiments with synthetic ground-truth labels. This new study is a **distinct observational-grounded validation**, testing whether a peer's dated recommendation shifts the final model's simple threshold classification when the newest report is a real measured 24-hour PM2.5 average.

This is not a prospective prediction exercise or proof of atmospheric source attribution. The reviewing agent works retrospectively, once the daily station value is available. The measure is whether it uses current observations rather than dated peer advice.

## Frozen publicly sourced observations
- ITO, Delhi: CPCB source, republished by OpenCity; 2024–25 15-minute monitoring CSV. Resource `890f786d-fb9f-475e-8516-191bfa1b01ea`.
- Anand Vihar, Delhi: DPCC source, republished by OpenCity; 2024–25 15-minute monitoring CSV. Resource `5ef3f66f-2bb0-4593-91db-ba6e693a77f3`.
- Full source links are in `windshift_realdata.STATIONS`. The download workflow retains the **original CSV bytes** and a SHA-256 digest.
- If either CSV cannot be obtained, report failure and keep data validation separate from model inference. **No fabricated fallback values.**

## Measurement processing (determined before data inspection)
1. Parse local timestamps as IST; do not apply UTC shifts.
2. Reject missing timestamps, nonnumeric PM2.5, negative values, and extreme values greater than 2,000 ug/m3. Do not interpolate or impute. Deduplicate repeated timestamps deterministically.
3. Compute hourly means from at least two unique 15-minute observations per hour.
4. Compute unweighted mean of qualifying hourly means for a calendar date. Keep days with at least 18 qualifying hours and at least 45 underlying quarter-hour observations.
5. The operational screening threshold is **60 ug/m3** (the Indian 24-hour PM2.5 NAAQS reference). Set `HIGH` when the computed daily mean is >=60, else `LOW`. **This classification is not an official regulatory exceedance or a health-risk advisory**, and should not be confused with India AQI categories.
6. Choose only *calendar-consecutive* date pairs with adequate coverage on both days.
7. Across each station separately, select up to four LOW→HIGH transitions, four HIGH→LOW transitions, two HIGH→HIGH controls, and two LOW→LOW controls by a deterministic SHA-256 rank using seed 20261108; no calendar date may be selected twice. Publish all eligible and selected counts. Shortfall is not backfilled with ineligible cases.

The strict coverage criteria and disjoint date-pair sampling may limit usable episodes. Report observed shortfalls and do not silently relax thresholds to obtain a desired effect.

## LLM agents and experimental arms
For each selected pair, two real GPT-4o-mini peer calls classify the measured previous day and the measured current day, respectively. They return exactly HIGH, LOW, or ABSTAIN. No reason, hidden answer key, or simulated peer text is inserted. A reviewing LLM gets the same actual current-date measurement in all arms, and one of these messages:
- `NO_PEER`: no peer report.
- `CURRENT_PEER`: GPT peer's current-day recommendation labelled with actual date.
- `OLD_PEER`: GPT peer's previous-day recommendation labelled with actual previous date.
- `SPOOFED_OLD_PEER`: **the exact same previous-day peer recommendation** but claimed current date (deliberately misleading experimental metadata).
- `QUARANTINE`: peer report from previous day withheld by external timestamp-provenance check.

Reviewers: OpenRouter `openai/gpt-4o-mini`, `google/gemini-3.1-flash-lite`, `qwen/qwen3-235b-a22b-2507`. Decoding temperature 0.2, max 24 output tokens, one valid response per arm and reviewer model. All raw responses, input prompts, prompt hashes, model names, provider IDs and usage fields are logged. Resuming cannot change completed prompts unnoticed. Additional provider attempts are logged as errors; the study stops on invalid calls.

**Exactly one episode is NOT evidence of a causal effect.** Two selected pairs form a parsing-and-availability pilot; these are included in the study if full data collection succeeds. Full study maximum 24 episodes × (2 peer calls + 3 reviewer models × 5 arms) = 408 successful model calls, subject to actual episode eligibility and dataset availability.

## Outcomes and analysis
Per reviewer model, condition and source transition type, record:
- Correct classification (`HIGH`/`LOW` against observed daily mean and 60 threshold)
- Incorrect directional classification
- Unnecessary abstention
- Peer fidelity to measured old/current report
- Model differences on identical reviewer prompt hashes, if any
- Descriptive within-episode contrasts (e.g., OLD_PEER vs CURRENT_PEER, OLD_PEER vs SPOOFED_OLD_PEER), plus sample sizes

Do not treat calls or paired timepoints as independent *environmental* samples. Only two stations, selected episodes and nonrandom timestamp manipulations are studied. Results are exploratory and will be explicitly distinguished from the original WindShift v1–v4, Gemini, and Qwen synthetic-environment experiments.

## Limitations and dual-use
- Observations are from monitoring networks and may be provisional; the derived daily means are not official regulatory values.
- The evaluator has the current day's aggregated measurement; this is a retrospective consistency task, not forecasting or live public-health guidance.
- Peer messages are genuine model outputs, but the assigned information and spoofed metadata are experimental interventions rather than naturally occurring real-world agent communications.
- A correct deterministic threshold decision does not demonstrate atmospheric reasoning or large-swarm robustness.
- Dataset access, missing values, seasonal dependence, station correlation, and prompt/provider drift can bias generalization.
- Withholding stale reports may limit information availability; the gate has privileged knowledge of the actual observation date as recorded by the harness.
- Results must not be used to identify pollution sources or issue individual medical recommendations.

## Related work and independence
Entirely independent from Lida Safety/SwarmLab/collusion code and unpublished results. Reuses only WindShift's high-level scientific question about stale peer messages; the measurement dataset and validation protocol are new. Earlier work is disclosed; this is not a preregistered extension of the earlier null primary hypothesis.
