# WindShift: Old Advice, New Evidence

**Karan Verma | Independent Researcher**

Independent research for the Apart Research Swarm Alignment Hackathon 2026.

## Research question

How do the content and claimed observation time of peer recommendations affect an AI model's decisions when newer evidence disagrees?

## Experiments

The controlled handoff evaluation contains 24 generated scenarios, four peer-message conditions, and three receiver models:

- GPT-4o-mini
- Gemini 3.1 Flash Lite
- Qwen3-235B

There are 576 matched reviewer decisions, representing repeated observations across 24 scenarios.

The original wrong-source comparison was null: 0/32 versus 0/32.

The exploratory analysis investigates content, claimed timestamps, unsupported decisions, and unnecessary abstention.

## Real monitoring-data evaluation

A separate retrospective evaluation uses recorded Delhi PM2.5 monitoring data.

- 24 historical episodes
- 360 reviewer classifications
- 360/360 correct classifications
- 408 valid model calls, including peer generation

This evaluation did not demonstrate improved safety from quarantining outdated peer information.

## Reproducibility

Run the offline evidence audits from the repository root:

    python3 audit_three_models.py
    python3 real_data/audit_public_real.py

The audit scripts check recorded model outputs. They do not require paid inference.

## Repository contents

- source/ : experiment implementations and tests
- input/ : controlled evaluation inputs
- results/ : model responses and analysis outputs
- real_data/ : historical measurement evaluation
- figures/ : research visualizations
- development_history/ : earlier research stages

See DATA_PROVENANCE.md, LIMITATIONS_AND_ETHICS.md, and PREEXISTING_WORK_AND_DISCLOSURE.md for important methodological and disclosure details.

## Research scope

The controlled evaluation uses generated scenarios and frozen peer messages. It does not simulate an independently interacting agent population or demonstrate a validated safety intervention.

The Delhi evaluation uses recorded measurements for a separate threshold-classification task.

## Author

Karan Verma
Independent Researcher
