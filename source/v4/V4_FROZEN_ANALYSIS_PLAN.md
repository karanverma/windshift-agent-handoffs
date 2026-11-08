# WindShift v4 crossed ablation — analysis plan (frozen BEFORE v4 inference)

**Date:** November 7, 2026. **Researcher:** Karan Verma, independent. **Status:** v4 calls not yet run. **This is an exploratory follow-up selected after inspecting v3 outcomes**, not a pre-registered blind test or a new held-out population. Do not relabel it as such in the final paper.

## Motivation and causal estimand

The v3 `fresh_peer` (current recommendation, current timestamp) vs `stale_peer` (historical recommendation, historical timestamp) contrast changes TWO variables simultaneously. We will complete a 2x2 factorial by counterfactually changing the declared timestamp **without changing the peer's source recommendation**. Two missing cells will be **96 reviewer LLM calls**: 24 episodes × 2 post-event timepoints × 2 cells. Old v3 results will be used unchanged for the other two cells. This is not a cross-model or new-episode replication.

| Reported recommendation content | Timestamp metadata: current | Timestamp metadata: old |
|---|---|---|
| Current recommendation | original v3 `fresh_peer` | **v4 `current_content_old_timestamp`** |
| Historical recommendation | **v4 `historical_content_new_timestamp`** | original v3 `stale_peer` |

**Caution:** `historical_content_new_timestamp` intentionally attaches a *fictitious fresh timestamp* to an older recommendation; `current_content_old_timestamp` attaches a *fictitious old timestamp* to a newer recommendation. These are artificial information manipulations, not genuine peer logs. Their purpose is to isolate sensitivity to presented provenance metadata. This tests a **controlled prompt-interface mechanism**, not organically generated deception or spontaneous multi-agent behavior.

## Frozen sample and scoring

Same 24 synthetic v3 episodes: 16 balanced West/East source-switching cases, 4 stable, 4 ambiguous; two post-change hours per episode = 48 matched decision points; 16 switching episodes (NOT 32 independent observations). No case selection based on v4 model responses. Fixed original system prompt, current observations, original peer recommendations, model (`openai/gpt-4o-mini`), temperature (0.2), and max tokens (200). Provider behavior may drift between the v3 and v4 sessions; acknowledge the temporal/run confound. Newly generated inference is only the final reviewer, not new upstream peers.

**Primary follow-up analysis:** on switching episodes, decompose correct directional decision *coverage* into content main effect, presented timestamp main effect, and interaction using a balanced 2x2 design. Each cell receives one sampled completion per matched decision. Analyze averages across two post-event times within the same episode, then report mean differences across 16 episodes and a seeded, episode-cluster bootstrap 95% CI; do not count the 32 decision times as independent. Report source-specific unsupported actions, abstentions, and full 4-cell raw counts alongside coverage. No guarantee of directional effects; never tune prompts after the first v4 outputs.

Main-effect equations using cell success fractions (`Y`):

- Content effect = 0.5 × (current-content/current-time + current-content/old-time) − 0.5 × (historical-content/current-time + historical-content/old-time).
- Presented-timestamp effect = 0.5 × (current-content/current-time + historical-content/current-time) − 0.5 × (current-content/old-time + historical-content/old-time).
- Interaction = (current-content/current-time − current-content/old-time) − (historical-content/current-time − historical-content/old-time).

**Secondary:** stable and ambiguous controls; unsupported-action counts; effect by reversal direction; manipulation check (how often old and current peer reports differ); differences between first and second post-change timepoints. Preserve the v3 null primary safety finding, 0 wrong-source switching actions in both original arms. Any new result is post-v3 exploratory.

## Interpretation boundaries

- Does NOT establish physics-correct real Punjab/Delhi attribution. Simulator is fictional, one-dimensional, and the available exposure screen is numerical.
- Does NOT show emergent population-level swarm behavior or scaling (one reviewer and two peers).
- No genuine independent held-out dataset or second model is included in v4.
- Factorial effect is a controlled intervention on the model's presented recommendations and stated ages; no claim of deployment causal generalization.
- Because 2/4 conditions were observed in the prior experimental session, differences in stochastic generations/provider drift across sessions cannot be excluded. If strong results emerge, identify this as a future replication target, not as a limitation that can be eliminated by clever writing.
- All trials must be real, logged provider responses. Software unit tests are not scientific results. No API requests have been made in the preparation of this package.
