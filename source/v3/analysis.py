"""Episode-clustered comparisons for completed WindShift runs, stdlib only.

Refuses to pool incompatible datasets, model IDs, protocols, or incomplete paired episodes.
"""
import argparse, json, random, statistics
from collections import defaultdict
from pathlib import Path


def boot_ci(pairs, samples=2000, seed=321):
    """Paired episode-cluster bootstrap for an episode-level scalar difference."""
    if len(pairs) < 3:
        return [None, None]
    rng = random.Random(seed)
    b = []
    n = len(pairs)
    for _ in range(samples):
        b.append(statistics.mean(pairs[rng.randrange(n)] for __ in range(n)))
    b.sort()
    return [round(b[int(0.025 * (samples - 1))], 4),
            round(b[int(0.975 * (samples - 1))], 4)]


def correction_delay(rs):
    """Count evaluation positions from first truth source switch to first correct decision.

    Events with intermediate ABSTAIN are permitted. Returns None when no switch;
    returns (num_positions, censored flag) when switch exists. Censor at n.
    """
    rows = sorted(rs, key=lambda r: r['time'])
    if len(rows) < 2:
        return None
    previous_source = None
    reversal_index = None
    new_source = None
    for i, r in enumerate(rows):
        if r['truth'] not in ('WEST', 'EAST'):
            continue
        if previous_source is not None and r['truth'] != previous_source:
            reversal_index, new_source = i, r['truth']
            break
        previous_source = r['truth']
    if reversal_index is None:
        return None
    # A "correction" requires an actual prior group commitment to the old
    # source. Otherwise this is initial detection, not revision of consensus.
    prior_committed = next((r['decision'] for r in reversed(rows[:reversal_index])
                            if r['decision'] != 'ABSTAIN'), None)
    if prior_committed != previous_source:
        return None
    for j in range(reversal_index, len(rows)):
        if rows[j]['decision'] == new_source:
            return (j - reversal_index, False)
    return (len(rows) - reversal_index, True)


def analyze(rows, bootstrap=2000):
    configs = {(r['dataset_sha256'], r['protocol_sha256'], r['model'], r['temperature']) for r in rows}
    if len(configs) != 1:
        raise ValueError('Results from different models/protocols/datasets must be analyzed separately')
    by_episode = defaultdict(list)
    for r in rows:
        by_episode[(r['episode'], r['mode'], r['n'])].append(r)
    comparisons = []
    ns = sorted({r["n"] for r in rows if r["mode"] in ("independent", "social")})
    for n in ns:
        diffs = []
        delays = []
        control = []
        for episode in sorted({k[0] for k in by_episode}):
            ind = by_episode.get((episode, 'independent', n), [])
            soc = by_episode.get((episode, 'social', n), [])
            # 6 sampled timepoints make one cluster. Ignore partial episode data.
            if len(ind) != 6 or len(soc) != 6:
                continue
            ind_map = {r['time']: r for r in ind}
            soc_map = {r['time']: r for r in soc}
            if ind_map.keys() != soc_map.keys():
                continue
            error_i = statistics.mean(r['unsupported_action'] for r in ind)
            error_s = statistics.mean(r['unsupported_action'] for r in soc)
            diffs.append(error_s - error_i)
            di, ds = correction_delay(ind), correction_delay(soc)
            if di is not None and ds is not None:
                # Correction delay only exists for prior committed source choices;
                # censored delays are lower bounds, NOT completed corrections.
                delays.append({'episode': episode, 'independent': di, 'social': ds})
            control.append({'episode':episode, 'kind':ind[0]['kind'],
                            'independent_unsupported':round(error_i,4),
                            'social_unsupported':round(error_s,4)})
        comparisons.append({
            'n':n, 'n_complete_paired_episodes':len(diffs),
            'social_minus_independent_unsupported':round(statistics.mean(diffs),4) if diffs else None,
            'episode_cluster_bootstrap_95pct':boot_ci(diffs,bootstrap),
            'correction_times_with_censoring':delays,
            'per_episode':control,
        })
    return {'statistical_note':'Exploratory estimates only; CI is a cluster bootstrap of episode-level differences. '
                                'Correction times are censored when not corrected and are NOT averaged.',
            'comparisons':comparisons}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--summary',default='results/summary.json')
    p.add_argument('--output',default='results/paired_analysis.json')
    args=p.parse_args()
    rows=json.loads(Path(args.summary).read_text(encoding='utf-8'))['rows']
    if not rows:
        raise SystemExit('No completed model rounds. Do not invent results.')
    report=analyze(rows)
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['comparisons'],indent=2))
    print('Saved',dest)

if __name__ == '__main__': main()
