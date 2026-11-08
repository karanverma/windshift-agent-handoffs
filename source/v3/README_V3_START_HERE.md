# WindShift v3 — independent first-author research experiment

**Sole proposed author:** Karan Verma, Independent Researcher  
**Sprint:** Apart Research Swarm Alignment Hackathon, November 6–8, 2026  
**Status:** v3 code + dataset ready and locally tested. **No v3 LLM findings are bundled**.

## What is new and what already existed?

- **New during the sprint, v3:** prespecified peer-time intervention; 24-episode synthetic test set seed `20261117`; equal-current-evidence paired conditions; two actual peer model calls at historical timestamp and two current peers per evaluation time; deterministic rotating treatment order; new checkpointed call logs, integrity checks, and cluster-level analysis; eight local v3 tests.
- **Prior within this sprint (v2):** `windshift_v2.py` (copied from our standalone WindShift v2 experiment) contains the pre-existing *relative to v3* toy transport simulator, observations, proxy, gateway and decision parser. Earlier v2 evidence: 504 GPT-4o-mini calls across 12 episodes (72 matched rounds per condition), small and uncertain communication effect. Prior v1 24-call all-abstention pilot. Older v2 results are stored in `prior_v2/` and **must not be pooled with v3**.
- **Never sourced from:** Lida Safety's collusion work, MARL market benchmark, coauthor/team project, or unpublished collaborator results.
- **LLM assistance:** AI tools assisted with experiment design, coding, testing, and drafting; the researcher remains responsible for verifying every result and citation.

## What problem does it address?

When data changes, prior reviewers' advice can become obsolete. V3 asks whether showing an LLM reviewer old timestamped peer advice increases unsupported source-specific follow-up decisions, compared with showing the *same kind* of advice generated from current evidence. It is a narrowly defined multi-agent information-propagation failure, not a real-world Delhi air-quality model.

## Run in Google Colab

Use the included **single-file** `WindShift_v3_ONE_FILE_COLAB.ipynb`; it unpacks this code itself, runs unit tests and a dry-run, and does not call OpenRouter unless you explicitly set an authorization flag after checking credits and pricing. The notebook can export its actual `v3_calls.jsonl` and `v3_analysis.json` together with the code and dataset.

## Run locally without paid calls

```bash
python windshift_v3.py preflight
python -m unittest discover -s tests -p test_windshift_v3.py -v
python windshift_v3.py run --episodes 2  # dry-run; 0 provider requests
```

## Safe live execution after checking model pricing

Set `OPENROUTER_API_KEY` through a secrets manager and **do not place secrets in code or ZIPs**.

```bash
python windshift_v3.py run --episodes 2 --authorize --max-new-calls 24
python windshift_v3.py analyze
# If pilot valid, resume to complete the same frozen 24-episode dataset:
python windshift_v3.py run --episodes 24 --authorize --max-new-calls 288
python windshift_v3.py analyze
```

Each run resumes from existing `results/v3_calls.jsonl`, and stops on invalid or failed API responses. Failed requests and retries may still incur charges. The successful-call cap is not a hard currency cap. Do not paste your key into ChatGPT.

## Reading the results

Primary contrast: for the 16 switch episodes, the paired difference between stale-peer and fresh-peer unsupported-action rates, averaging the **two post-switch timepoints per episode**. Also inspect legitimate decision coverage and manipulation success. 4 stable and 4 ambiguous controls are separately reported. The defense is an **external toy proxy-based action gate**, not proof of corrected model reasoning. The paper's claims must be limited to verified real-model outcomes.

## Submission

The official Apart template has been provided separately. 4–8 pages recommended, **8-page main-text hard maximum** excluding references/appendices; 150–250-word abstract; required *Limitations and Dual-Use / Ethical Considerations* appendix; LLM usage statement. Do not insert placeholder quantitative findings into the report. Deadline: Monday, Nov 9 2026, 5:29 PM India time.
