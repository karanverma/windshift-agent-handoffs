# Historical Delhi monitoring-data boundary study

This is a **separate** retrospective analysis from the controlled WEST/EAST handoff evaluation. It uses recorded daily PM2.5 measurements from two Delhi stations, not atmospheric source-attribution labels. Three reviewer models received measured current-day values and the explicit 60 µg/m³ threshold. All **360/360** reviewer classifications were correct across five advice conditions; 48 peer-generation calls brought total successful calls to **408**. One failed provider attempt was logged and successfully retried. Consequently the original audit status is `PARTIAL` even though all successful-call slots are populated. **This finding does not establish benefit from the quarantine intervention**.

## Data provenance and redistribution

The original station CSVs are deliberately **not mirrored** here because their redistribution terms have not been independently confirmed. `source_manifest.json` provides the original OpenCity resource URLs, the full-file SHA-256 hashes and data-quality details. The limited derived observation tables (`episodes.json`, `station_daily.csv` and `measured_decisions.csv`) are included for verification of the analyzed subset; they are not an official regulatory dataset.

You may obtain original source files from the resource URLs in the manifest and place them at:

- `real_data/raw/ITO_CPCB.csv`
- `real_data/raw/ANAND_VIHAR_DPCC.csv`

Then compare hashes to `source_manifest.json` and run `python windshift_real_analysis.py` with an explicit audit wrapper if needed. The self-contained **public/offline** audit below requires no original station files and verifies the logged model output, labels and matching episode counts, but cannot re-validate original-provider CSV integrity without those source bytes.

```bash
python audit_public_real.py
```

The notebook/code can be re-run against the original files for full source-data integrity; these commands may require pandas/matplotlib and may incur API charges if the inference runner is deliberately enabled. The public audit makes no paid calls.
