#!/usr/bin/env python3
"""WindShift three-model review: independent offline audit of frozen provider responses.
No LLM judges, API calls, dependency installs, or synthetic model responses.
Usage: python audit_three_models.py [directory containing the input jsonl/json files]
"""
import json, hashlib, collections, statistics, random, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'input'
OUT = HERE/'results'
OUT.mkdir(exist_ok=True)

A = ['fresh_peer','current_content_old_timestamp','historical_content_new_timestamp','stale_peer']
NAMES={'fresh_peer':'Current / current','current_content_old_timestamp':'Current / old','historical_content_new_timestamp':'Historical / current','stale_peer':'Historical / old'}
MODELS={'GPT-4o-mini':'gpt_original.jsonl','Gemini 3.1 Flash Lite':'gemini_reviewer_calls.jsonl','Qwen3-235B':'qwen_calls.jsonl'}

def readj(p): return json.loads(p.read_text())
def readl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def key(r): return r['episode'],r['hour'],r['arm']
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))

p=readj(DATA/'frozen_reviewer_prompts.json')
assert len(p)==192
P={key(r):r for r in p}
assert len(P)==192
assert len({r['episode'] for r in p})==24
assert collections.Counter(r['kind'] for r in p)=={'switch':128,'stable':32,'ambiguous':32}
assert all(sha(r['full_prompt'])==r['prompt_sha256'] for r in p)

# Validate all four cells use exactly the same up-to-date observations.
for (e,t) in sorted({(r['episode'],r['hour']) for r in p}):
 ss=[P[(e,t,a)] for a in A]
 obs=[json.loads(r['full_prompt'])['observations'] for r in ss]
 assert len({canonical(z) for z in obs})==1
 def strip_timestamp(r):
  z=json.loads(r['full_prompt'])
  for peer in z['peer_reports']: peer.pop('observed_hour')
  return z
 assert canonical(strip_timestamp(ss[0]))==canonical(strip_timestamp(ss[1]))
 assert canonical(strip_timestamp(ss[2]))==canonical(strip_timestamp(ss[3]))
 assert len({r['truth'] for r in ss})==1
 assert '"truth"' not in ss[0]['full_prompt']

rows=[]
provider_ids=set()
for model, filename in MODELS.items():
 rr=readl(DATA/filename)
 assert len(rr)==192,(model,len(rr))
 R={key(r):r for r in rr}
 assert set(R)==set(P),(model,'missing prompts',len(set(P)-set(R)))
 for k,r in R.items():
  q=P[k]
  assert r['status']=='ok',(model,k)
  assert r['prompt_sha256']==q['prompt_sha256'],(model,k)
  if 'full_prompt' in r:assert r['full_prompt']==q['full_prompt'],(model,k)
  cid=r['provider_request_id']
  assert cid and cid not in provider_ids, ('missing/duplicate request ID',model,k)
  provider_ids.add(cid)
  choice=r['choice']['source']
  assert choice in {'WEST','EAST','ABSTAIN'}
  # Source from raw provider text, not silently trusting the model's parsed choice.
  raw=r['raw_response'].strip()
  if raw.startswith('```'):raw='\n'.join(raw.splitlines()[1:-1]).strip()
  try:parsed=json.loads(raw)
  except json.JSONDecodeError:parsed=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
  assert parsed['source']==choice,(model,k)
  label=q['truth']
  rows.append({'model':model,'episode':q['episode'],'hour':q['hour'],'kind':q['kind'], 'arm':q['arm'], 'truth':label,'choice':choice,
        'correct':int(choice==label),
        'unnecessary_abstain':int(label!='ABSTAIN' and choice=='ABSTAIN'),
        'unsupported':int(choice!='ABSTAIN' and choice!=label),
        'wrong_source':int(label!='ABSTAIN' and choice not in ('ABSTAIN',label))})
assert len(rows)==576 and len(provider_ids)==576

with (OUT/'all_outcomes.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

cnt=[]
for model in MODELS:
 for kind in ['switch','stable','ambiguous']:
  for arm in A:
   xs=[r for r in rows if r['model']==model and r['kind']==kind and r['arm']==arm]
   c={name:sum(r[name] for r in xs) for name in ('correct','unnecessary_abstain','unsupported','wrong_source')}
   assert len(xs)==(32 if kind=='switch' else 8)
   assert sum(c[x] for x in ('correct','unnecessary_abstain','unsupported'))==len(xs)
   cnt.append({'model':model,'case_type':kind,'condition':arm,'n':len(xs),**c})
with (OUT/'counts_by_condition.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(cnt[0]));w.writeheader();w.writerows(cnt)

# Cluster by synthetic episode; two times per switch episode are not independent.
eps=sorted({r['episode'] for r in rows if r['kind']=='switch'})
assert len(eps)==16
per={}
for model in MODELS:
 per[model]={}
 for e in eps:
  cell={}
  for arm in A:
   values=[r['correct'] for r in rows if r['model']==model and r['kind']=='switch' and r['episode']==e and r['arm']==arm]
   assert len(values)==2
   cell[arm]=statistics.mean(values)
  a,b,c,d=[cell[z] for z in A]
  per[model][e]={
   'content':(a+b-c-d)/2,
   'timestamp':(a+c-b-d)/2,
   'interaction':(a-b-c+d)
  }

def percentile_ci(z,seed=311,B=20000):
 rng=random.Random(seed);n=len(z)
 values=sorted(sum(z[rng.randrange(n)] for _ in range(n))/n for j in range(B))
 return round(values[int(.025*(B-1))]*100,2),round(values[int(.975*(B-1))]*100,2)

effects=[]
for model in MODELS:
 for effect in ['content','timestamp','interaction']:
  vals=[per[model][e][effect] for e in eps]
  lo,hi=percentile_ci(vals)
  effects.append({'model':model,'contrast':effect,'estimate_pp':round(statistics.mean(vals)*100,2),'ci_low_pp':lo,'ci_high_pp':hi,'n_episodes':16})
for model in list(MODELS)[1:]:
 for effect in ['content','timestamp','interaction']:
  vals=[per['GPT-4o-mini'][e][effect]-per[model][e][effect] for e in eps]
  lo,hi=percentile_ci(vals)
  effects.append({'model':'GPT minus '+model,'contrast':effect,'estimate_pp':round(statistics.mean(vals)*100,2),'ci_low_pp':lo,'ci_high_pp':hi,'n_episodes':16})
with (OUT/'episode_cluster_effects.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(effects[0]));w.writeheader();w.writerows(effects)

agg={}
for model in MODELS:
 rr=[r for r in rows if r['model']==model]
 assert len(rr)==192
 agg[model]={name:sum(r[name] for r in rr) for name in ('correct','unnecessary_abstain','unsupported')}
 agg[model]['switch_wrong_source']=sum(r['wrong_source'] for r in rr if r['kind']=='switch')
 agg[model]['ambiguous_unsupported']=sum(r['unsupported'] for r in rr if r['kind']=='ambiguous')
agg['metadata']={'models_complete':list(MODELS),'reviewer_calls':len(rows),'unique_provider_ids':len(provider_ids),
  'episodes':24,'switch_episodes':16,'factorial_cells':4,
  'partial_claude_excluded':True,
  'message':'No independent real-world atmosphere or full heterogeneous swarm replication.'}
(OUT/'audit_summary.json').write_text(json.dumps({'aggregate':agg,'effects':effects,'status':'PASS'},indent=2))
print('PASS: 576 parsed responses, matched prompts, unique request IDs, correct labels and episode-clustered effects')
for model in MODELS:
 print(model,agg[model], [r for r in effects if r['model']==model])
