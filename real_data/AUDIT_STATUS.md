# WindShift — real-world validation audit (2026-11-08)

## Verified now
- Dataset catalog metadata exists for 2024–25 ITO and Anand Vihar Delhi PM2.5 station records. Both cite CPCB/DPCC source monitoring, distributed through OpenCity.
- India 24-hour PM2.5 NAAQS benchmark is 60 ug/m3 (source: Indian Economic Service NAAQS table and CPCB report).
- The source code requires real external CSV bytes and refuses to create episodes without them.
- Offline software tests cover dataset structure, parsing, coverage, timestamp handling, disjoint episode selection, strict output decoding, provenance metadata spoofing, gateway withholding, opt-in model inference, ledger integrity and resume.
- The Colab notebook includes exact source URLs, conservative data filters, an explicit paid-call permission flag, and an export of original source CSV bytes plus SHA-256 hashes.

## Not yet verified / must not be claimed
- **Original real station CSV bytes not accessible in this sandbox** (network DNS disabled and web retrieval returned 403). No CPCB daily values have been loaded, no real episode count has been determined, and no source file hash can be asserted yet.
- **Zero live OpenRouter calls** made for this new validation; all test-response calls use explicit mock software fakes.
- No real-data classification accuracy, safety benefit, or real-data paper figure can be claimed before the Colab archive is returned and independently inspected.
- This dataset concerns measured PM2.5, not source attribution, wind transport, crop fires, or causation.

## Quality gates before integrating new evidence in submission
1. Exact CSV file sources and measured observation hashes reported.
2. Coverage report records valid days, missing data and category counts for each station.
3. Actual sampled episodes publicly released with original time and concentration; no fabricated measurements.
4. At least 12 real eligible episodes selected, ideally balanced transition directions; sample shortfalls disclosed.
5. 100% of intended peer/reviewer records have strict parsable responses, unique call keys/provider IDs, and matching prompt digests, or errors documented and explicitly excluded.
6. Same-model comparisons have matched measured current evidence and differ only in controlled peer information or timestamp metadata.
7. Original WindShift synthetic benchmark and this real-measurement retrospective screening task remain distinct in paper and counts; no pooling inconsistent outcomes.

## Sources
- https://data.opencity.in/dataset/delhi-hourly-air-quality-reports
- https://data.opencity.in/dataset/delhi-hourly-air-quality-reports/resource/890f786d-fb9f-475e-8516-191bfa1b01ea
- https://data.opencity.in/dataset/0dc7b9fe-9fd4-46ee-a37e-88f0bd6f6362/resource/5ef3f66f-2bb0-4593-91db-ba6e693a77f3
- https://ies.gov.in/arthapedia/concept/ambient-air-quality-standards-india

## Software end-to-end check
- Nine out of nine offline tests passed (2026-11-08).
- A separate throwaway fixture of 24 *fabricated SOFTWARE-TEST days* was used only in a local temporary directory to exercise full control flow: mock peer+reviewer calls 408/408, prompt logging, no-duplicate resume, model-condition tables, independent source-file hashing and final image generation. The temporary fixture and mock response ledger were erased; **they are NOT research evidence and are not in the distributable package**.
- No real CPCB measurement values or LLM outcomes are present in the deliverable; Colab must download them before a study can be said to have run.
