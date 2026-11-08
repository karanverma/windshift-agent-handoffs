#!/usr/bin/env python3
"""Offline audit of recorded Delhi study (original station CSV files required for *source-level* audit)."""
import collections, csv, hashlib, json
from pathlib import Path
P=Path(__file__).resolve().parent
eps=json.loads((P/'episodes.json').read_text())
assert len(eps)==24 and len({x['episode_id'] for x in eps})==24
assert len({(x['station'],x['previous_day']) for x in eps}|{(x['station'],x['current_day']) for x in eps})==48
E={x['episode_id']:x for x in eps}
for e in eps:
 for which in ('previous','current'):
  expected='HIGH' if float(e[f'{which}_pm25_ugm3'])>=60 else 'LOW'
  assert e[f'{which}_label']==expected,(e['episode_id'],which)

rows=[json.loads(x) for x in (P/'real_llm_calls.jsonl').read_text().splitlines() if x.strip()]
valid=[r for r in rows if r.get('valid') is True]
invalid=[r for r in rows if not r.get('valid')]
assert len(rows)==409 and len(valid)==408 and len(invalid)==1,(len(rows),len(valid),len(invalid))
assert len(set(r['call_key'] for r in valid))==408
ids=[r['provider_id'] for r in valid]
assert all(ids) and len(set(ids))==408
models={'openai/gpt-4o-mini','google/gemini-3.1-flash-lite','qwen/qwen3-235b-a22b-2507'}
arms={'NO_PEER','CURRENT_PEER','OLD_PEER','SPOOFED_OLD_PEER','QUARANTINE'}
peers={}
for r in valid:
 assert r['episode_id'] in E
 assert hashlib.sha256(r['prompt'].encode('utf-8')).hexdigest()==r['prompt_sha256']
 assert r['raw_text'].strip()==r['parsed_label'] and r['parsed_label'] in ('HIGH','LOW','ABSTAIN')
 if r['phase']=='peer':
  assert r['model']=='openai/gpt-4o-mini' and r['arm'] in ('previous','current')
  peers[(r['episode_id'],r['arm'])]=r['parsed_label']
 else:
  assert r['phase']=='reviewer' and r['model'] in models and r['arm'] in arms
assert len(peers)==48
assert all(peers[(e['episode_id'],which)]==e[f'{which}_label'] for e in eps for which in ('previous','current'))
reviewers=[r for r in valid if r['phase']=='reviewer']
assert len(reviewers)==360
assert all(r['parsed_label']==E[r['episode_id']]['current_label'] for r in reviewers)
assert len(set((r['episode_id'],r['arm'],r['model']) for r in reviewers))==360
assert collections.Counter(r['model'] for r in reviewers)=={m:120 for m in models}
assert collections.Counter(r['arm'] for r in reviewers)=={a:72 for a in arms}
with (P/'measured_decisions.csv').open(newline='') as f: d=list(csv.DictReader(f))
assert len(d)==360 and sum(int(r['correct']) for r in d)==360
print('PASS: 24 measured-day episodes; 48 peer reports + 360 correct model reviews; 408 valid calls; one failed attempt retained.')
print('SOURCE-LEVEL LIMIT: original station CSVs not included; their URLs and SHA-256 are in source_manifest.json.')
