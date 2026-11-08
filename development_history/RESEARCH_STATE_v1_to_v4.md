# WindShift research continuity — frozen status as of 7 November 2026

**Independent researcher / proposed sole author:** Karan Verma. **Sprint:** Apart Research Swarm Alignment Hackathon, 6–8 November 2026. **Primary track:** 4 — Multi-Agent Oversight and Control. No code or results from the Lida Safety collusion work have been included.

## History

- **v1 feasibility pilot:** 24 provider responses, all ABSTAIN. Uninformative; preserved as failed design attempt, not pooled.
- **v2 development/evaluation:** revised synthetic two-source environment and numerical evidence. 504 live provider calls across 12 episodes, including solo, independent N=3, and sequential social N=3. The small difference between social and independent arms was not robust. The toy gateway shared assumptions with the simulator. These results are not pooled with the v3/v4 paper's model-count headline.
- **v3 original frozen experiment:** 24 new episodes (16 source-switching; 4 stable; 4 ambiguous); two decision points per episode; no-peer vs current/current vs historical/old peer arms; 288 successful provider calls. Original pre-specified unsupported-action comparison on switching episodes returned 0/32 vs 0/32. Fresh/current reported 32 correct, stale/old 12 correct and 20 abstentions.
- **v4 exploratory crossed follow-up:** Designed *after seeing v3* to fill the current/old and historical/current cells. Added 96 successful reviewer calls, keeping original v3 calls unchanged. Full evidence base = 384 calls (288 v3 + 96 v4). Factorial analysis uses 192 reviewer decisions across four peer arms and 48 matched decision times. Another 48 no-peer reviewer decisions exist in v3, but are excluded from the four-arm factorial calculations.

## Crossed switch-case cells (each 32 decisions, 16 episodes)

| Advice content | Claimed current | Claimed old |
|---|---|---|
| Current | 32 correct / 0 abstain / 0 unsupported | 21 correct / 10 abstain / 1 unsupported |
| Historical | 11 correct / 21 abstain / 0 unsupported | 12 correct / 20 abstain / 0 unsupported |

Episode-clustered exploratory effects: current vs historical content +46.9 pp (95% bootstrap interval +32.8 to +60.9); current vs old claimed timestamp +15.6 pp (+7.8 to +25.0); interaction +37.5 pp (+15.6 to +59.4).

## Ambiguous controls (eight decision points, four episodes)

Unsupported decisions: current/current 6; current/old 2; historical/current 8; historical/old 4. These are small descriptive counts, not a general prevalence estimate.

## Boundaries

One LLM (openai/gpt-4o-mini), three agent roles, synthetic fictional environmental simulator with imperfect numerical screen, one temperature and response per cell, no real-world pollution data, and two original treatment cells generated in a different session. False claimed timestamps are controlled counterfactuals, not real deceptive-agent interactions. No large-swarm scaling or external replication established.

## Submission artifacts

`WindShift_FINAL_Research_Paper.pdf` (6 pages, main paper 5 pages, references and required appendices on page 6); Word editable counterpart; `reanalyse_verified.py` and raw logs; `REVIEWER_AUDIT.md`. Public GitHub link still needs to be created and verified by the author. Final submission to Apart not yet claimed or performed.
