# Data provenance and reproducibility

**Controlled handoff study.** `input/` archives 192 frozen reviewer prompts and logged responses from each of three receiving models, including raw response text, prompt digests and request identifiers. `python audit_three_models.py` checks and reconstructs all 576 outcomes. Generated WEST/EAST scenarios do not correspond to source-attributed real pollution events.

**Historical measurement study.** `real_data/source_manifest.json` records the source URLs and SHA-256 hashes for two Delhi monitoring-station datasets via OpenCity. `real_data/episodes.json` and derived tables identify the 24 paired-day examples. Logged provider outputs are included. Full original third-party CSV bytes are excluded pending a separate license check; the original-data hash verification requires fetching those source files independently. `real_data/REAL_EVIDENCE_AUDIT.json` retains the original software status `PARTIAL` due to one logged failed provider attempt despite 408 complete successful calls.

**Privacy.** Raw model logs include provider request IDs and exact prompts. These are provenance identifiers, not API keys. Review them before publishing if the research provider or author has any restrictions on sharing them. Credentials and environment variables are not needed to rerun the offline audits.
