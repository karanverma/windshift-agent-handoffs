"""WindShift v4: independent crossed advice-content x timestamp follow-up.

Uses immutable, independently recorded v3 provider responses. This is a
post-v3 exploratory *intervention*; it must NOT be described as preregistered
before inspecting v3 results. It makes exactly 96 NEW reviewer-model requests
for 24 episodes x 2 post-event hours x 2 missing factorial cells.

Requires Python >=3.10, standard library only. Paid calls OFF by default.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import os
import random
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL = 'openai/gpt-4o-mini'
TEMPERATURE = 0.2
ORIG_LOG = 'data/v3_calls_frozen.jsonl'
DATASET = 'data/v3_episodes.json'
OUT = 'results/v4_cross_calls.jsonl'
ARMS_NEW = ('current_content_old_timestamp', 'historical_content_new_timestamp')
ARMS_ALL = ('fresh_peer', 'current_content_old_timestamp', 'historical_content_new_timestamp', 'stale_peer')
DECISION_LABELS = {'WEST', 'EAST', 'ABSTAIN'}
SEED = 20261107


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def parse_reply(s):
    txt = s.strip()
    if txt.startswith('```'):
        txt = '\n'.join(txt.splitlines()[1:-1]).strip()
    try:
        j = json.loads(txt)
    except json.JSONDecodeError:
        i, k = txt.find('{'), txt.rfind('}')
        if i < 0 or k < i:
            raise ValueError('No JSON decision')
        j = json.loads(txt[i:k+1])
    if j.get('source') not in DECISION_LABELS:
        raise ValueError('Invalid source decision')
    try:
        confidence = float(j['confidence'])
    except Exception as e:
        raise ValueError('Invalid confidence') from e
    if not 0 <= confidence <= 1:
        raise ValueError('Invalid confidence range')
    return {'source': j['source'], 'confidence': confidence, 'reason': str(j.get('reason', ''))[:1000]}


def load_rows(filename):
    ans = []
    for n, ln in enumerate(Path(filename).read_text().splitlines(), 1):
        if ln.strip():
            try:
                ans.append(json.loads(ln))
            except Exception as e:
                raise ValueError(f'Corrupt JSON line {n} in {filename}') from e
    return ans


def load_frozen(dataset_path=DATASET, orig_log=ORIG_LOG):
    data_bytes = Path(dataset_path).read_bytes()
    log_bytes = Path(orig_log).read_bytes()
    data = json.loads(data_bytes)
    logs = load_rows(orig_log)
    assert len(data['episodes']) == 24
    assert len(logs) == 288, f'Expected 288 original v3 calls, found {len(logs)}'
    ids = [r['provider_request_id'] for r in logs]
    assert len(set(ids)) == 288 and all(ids), 'V3 log has missing or duplicate provider IDs'
    hashes = {r['dataset_sha256'] for r in logs}
    assert hashes == {sha(data_bytes)}, 'Original dataset fingerprint mismatch'
    script_hashes = {r['script_sha256'] for r in logs}
    assert len(script_hashes) == 1, 'Multiple original protocol versions'
    assert {(r['model'], r['temperature']) for r in logs} == {(MODEL, TEMPERATURE)}
    for r in logs:
        assert r['status'] == 'ok'
        assert r['prompt_sha256'] == sha(r['full_prompt'].encode()), 'Original prompt modified'
        assert r['choice'] == parse_reply(r['raw_response']), 'Original parsed decision inconsistent with raw text'
    ix = {(r['episode'],r['stage'],r['hour'],r['peer'],r['arm']):r for r in logs}
    assert len(ix) == len(logs), 'Duplicate treatment keys in original log'
    episodes = {e['episode_id']:e for e in data['episodes']}
    for ep in data['episodes']:
        eid=ep['episode_id']
        for t in ep['window']['post']:
            f=ix[(eid,'target',t,0,'fresh_peer')]
            s=ix[(eid,'target',t,0,'stale_peer')]
            a=json.loads(f['full_prompt']);b=json.loads(s['full_prompt'])
            assert a['observations']==b['observations'], 'Current evidence changed between original arms'
            assert a['observations']['now_hour']==t
            assert len(a['peer_reports'])==len(b['peer_reports'])==2
            assert all(int(p['observed_hour'])==t for p in a['peer_reports'])
            assert all(int(p['observed_hour'])==ep['window']['pre'] for p in b['peer_reports'])
            assert f['system_prompt']==s['system_prompt'], 'System prompts differ'
    return data,ix,{'v3_dataset_sha256':sha(data_bytes),'v3_log_sha256':sha(log_bytes), 'v3_script_sha256':next(iter(script_hashes))}


def crossed_prompt(index, ep, hour, arm):
    assert arm in ARMS_NEW
    eid=ep['episode_id']
    current = index[(eid,'target',hour,0,'fresh_peer')]
    historical = index[(eid,'target',hour,0,'stale_peer')]
    source = current if arm=='current_content_old_timestamp' else historical
    msg = json.loads(source['full_prompt'])
    updated_hour = ep['window']['pre'] if arm=='current_content_old_timestamp' else hour
    assert len(msg['peer_reports'])==2
    for peer in msg['peer_reports']:
        peer['observed_hour']=updated_hour
    # This changes ONLY the timestamp metadata, not the peer's recommendation.
    # False timestamp condition is a controlled COUNTERFACTUAL not a real logged report.
    check = json.loads(source['full_prompt'])
    for peer in check['peer_reports']:
        peer['observed_hour']=updated_hour
    assert msg==check
    assert msg['observations']==json.loads(current['full_prompt'])['observations']
    assert 'truth' not in canon(msg) and 'oracle_contrib' not in canon(msg)
    return canon(msg), source['system_prompt'], source['choice']['source']


def plan(data,index):
    jobs=[]
    for ep in data['episodes']:
        for t in ep['window']['post']:
            arms=list(ARMS_NEW)
            if (int(ep['episode_id'].split('_')[-1])+t) % 2:
                arms.reverse()
            for arm in arms:
                question,system,original_reviewer_choice = crossed_prompt(index,ep,t,arm)
                jobs.append({'episode':ep['episode_id'],'hour':t,'arm':arm,
                             'question':question,'system_prompt':system,'original_reviewer_choice':original_reviewer_choice})
    assert len(jobs)==96 and len({(j['episode'],j['hour'],j['arm']) for j in jobs})==96
    return jobs


def run_call(key,model,question,system,temperature,max_tokens=200):
    payload={'model':model,'temperature':temperature,'max_tokens':max_tokens,
             'messages':[{'role':'system','content':system},{'role':'user','content':question}]}
    req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
        data=json.dumps(payload).encode(),method='POST',headers={
            'Authorization':'Bearer '+key,'Content-Type':'application/json',
            'X-Title':'WindShift v4 Independent Research'})
    # No hidden retry of billable requests; stop and resume after checking the log.
    with urllib.request.urlopen(req,timeout=90) as response:
        reply=json.loads(response.read().decode())
    if 'choices' not in reply or not reply['choices']:
        raise RuntimeError('Provider did not return choices: '+str(reply)[:200])
    raw=reply['choices'][0]['message']['content']
    if not isinstance(raw,str):raw=json.dumps(raw)
    return raw,reply.get('id',''),reply.get('usage',{})


def execute(args):
    data,index,proof=load_frozen(args.dataset,args.original)
    tasks=plan(data,index)
    script_hash=sha(Path(__file__).read_bytes())
    previous=load_rows(args.out) if Path(args.out).exists() else []
    done={}
    for rec in previous:
        if rec.get('status')=='ok':
            if rec.get('protocol_script_sha256') != script_hash or rec.get('v3_log_sha256')!=proof['v3_log_sha256']:
                raise ValueError('Cannot resume with modified protocol or original results')
            k=(rec['episode'],rec['hour'],rec['arm'])
            if k in done: raise ValueError('Duplicate v4 completed task')
            done[k]=rec
    pending=[j for j in tasks if (j['episode'],j['hour'],j['arm']) not in done]
    print(f"V4 plan: 96 new calls; {len(done)} already completed, {len(pending)} pending. "
          f"Dataset={proof['v3_dataset_sha256'][:12]} log={proof['v3_log_sha256'][:12]}")
    if not args.authorize or args.max_new_calls<=0:
        print('DRY RUN: zero model calls. Authorize explicitly only after checking credits/pricing.')
        return
    key=os.environ.get('OPENROUTER_API_KEY','')
    if not key:raise RuntimeError('OPENROUTER_API_KEY unavailable. Set via Colab Secrets, never paste into notebook.')
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    successes=0
    with dest.open('a') as out:
        for item in pending:
            if successes>=args.max_new_calls:break
            rec={k:item[k] for k in ('episode','hour','arm','original_reviewer_choice')}
            rec.update({'model':args.model,'temperature':TEMPERATURE,'max_tokens':200,
                        'status':'attempt','prompt_sha256':sha(item['question'].encode()),
                        'full_prompt':item['question'],'system_prompt':item['system_prompt'],
                        'v3_dataset_sha256':proof['v3_dataset_sha256'],
                        'v3_log_sha256':proof['v3_log_sha256'],
                        'protocol_script_sha256':script_hash,'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            try:
                raw,pid,usage=run_call(key,args.model,item['question'],item['system_prompt'],TEMPERATURE)
                rec.update({'raw_response':raw,'provider_request_id':pid,'usage':usage})
                rec['choice']=parse_reply(raw)
                rec['status']='ok'
                out.write(canon(rec)+'\n');out.flush()
                successes+=1
                print(f"{rec['episode']} {rec['hour']} {rec['arm']}: {rec['choice']['source']} ({successes} new successful calls)")
            except Exception as e:
                rec['status']='error';rec['error']=str(e)[:500]
                out.write(canon(rec)+'\n');out.flush()
                print('STOPPED on error; check previous call and provider before resuming:',str(e)[:250])
                break
    print(f"New successful requests this invocation={successes}; complete={len(done)+successes}/96")


def percentile_ci(effects,seed=311,rounds=10000):
    n=len(effects)
    if n<3:return None
    rng=random.Random(seed)
    samples=sorted(statistics.mean(rng.choices(effects,k=n)) for _ in range(rounds))
    return [round(samples[int(.025*(rounds-1))],4),round(samples[int(.975*(rounds-1))],4)]


def analyze(args):
    data,original,proof=load_frozen(args.dataset,args.original)
    new=load_rows(args.out)
    expected=sha(Path(__file__).read_bytes())
    completed={}
    for r in new:
        if r.get('status')!='ok':continue
        if r.get('protocol_script_sha256')!=expected or r.get('v3_log_sha256')!=proof['v3_log_sha256']:
            raise ValueError('Crossed trial is not from the current frozen protocol/log')
        k=(r['episode'],r['hour'],r['arm'])
        if k in completed:raise ValueError('Conflicting duplicate successful crossed call')
        ep=next(e for e in data['episodes'] if e['episode_id']==r['episode'])
        q,s,_=crossed_prompt(original,ep,r['hour'],r['arm'])
        if q!=r['full_prompt'] or s!=r['system_prompt'] or sha(q.encode())!=r['prompt_sha256']:
            raise ValueError('Crossed condition prompt does not match frozen reconstruction')
        if r['choice']!=parse_reply(r['raw_response']):raise ValueError('Raw answer mismatch')
        completed[k]=r
    if len(completed)!=96:
        print(f'Incomplete study: {len(completed)}/96 new reviewer calls; refuse to report final factorial contrasts.')
        return
    eps={e['episode_id']:e for e in data['episodes']}
    records=[]
    for ep in data['episodes']:
        for t in ep['window']['post']:
            orig_f=original[(ep['episode_id'],'target',t,0,'fresh_peer')]
            orig_s=original[(ep['episode_id'],'target',t,0,'stale_peer')]
            original_map={'fresh_peer':orig_f,'stale_peer':orig_s}
            truth=ep['hours'][t]['truth']
            content_meta={
                'fresh_peer':('current','current'),
                'current_content_old_timestamp':('current','old'),
                'historical_content_new_timestamp':('historical','current'),
                'stale_peer':('historical','old')}
            for arm in ARMS_ALL:
                r= original_map[arm] if arm in original_map else completed[(ep['episode_id'],t,arm)]
                dec=r['choice']['source']
                records.append({'episode':ep['episode_id'],'kind':ep['kind'],
                                'direction':ep['window']['direction'],'hour':t,'truth':truth,
                                'arm':arm,'content':content_meta[arm][0],
                                'timestamp':content_meta[arm][1],
                                'decision':dec,'correct':int(dec==truth),
                                'coverage':int(truth in ('WEST','EAST') and dec==truth),
                                'unsupported':int(dec!='ABSTAIN' and dec!=truth),
                                'abstain':int(dec=='ABSTAIN')})
    assert len(records)==192
    summary={}
    for kind in ('switch','stable','ambiguous'):
        summary[kind]={}
        for arm in ARMS_ALL:
            xx=[r for r in records if r['kind']==kind and r['arm']==arm]
            summary[kind][arm]={'n':len(xx),'correct_n':sum(r['correct'] for r in xx),
                                 'directional_correct_n':sum(r['coverage'] for r in xx),
                                 'unsupported_n':sum(r['unsupported'] for r in xx),
                                 'abstain_n':sum(r['abstain'] for r in xx)}
    def episode_measure(ep,arm,field):
        vals=[r[field] for r in records if r['episode']==ep and r['arm']==arm]
        assert len(vals)==2
        return statistics.mean(vals)
    switch_eps=[e['episode_id'] for e in data['episodes'] if e['kind']=='switch']
    # Predeclared in v4 follow-up: signed effects on correct decisions/coverage.
    # This is exploratory conditional on *observed v3 effect*, never claim blind preregistration.
    content_effects=[];timestamp_effects=[];interaction=[]
    for ep in switch_eps:
        Y={a:episode_measure(ep,a,'coverage') for a in ARMS_ALL}
        cc=.5*(Y['fresh_peer']+Y['current_content_old_timestamp'])-.5*(Y['stale_peer']+Y['historical_content_new_timestamp'])
        tt=.5*(Y['fresh_peer']+Y['historical_content_new_timestamp'])-.5*(Y['stale_peer']+Y['current_content_old_timestamp'])
        ii=(Y['fresh_peer']-Y['current_content_old_timestamp'])-(Y['historical_content_new_timestamp']-Y['stale_peer'])
        content_effects.append(cc);timestamp_effects.append(tt);interaction.append(ii)
    def est(a): return {'mean':round(statistics.mean(a),4),'cluster_bootstrap_95pct':percentile_ci(a),'episode_effects':[round(x,4) for x in a]}
    output={'status':'complete observational v3+interventional v4 crossed exploratory analysis',
            'original_calls':288,'additional_calls':96,'matched_times':48,'n_episodes':24,
            'caution':'V4 treatment structure chosen AFTER seeing v3. Counterfactual timestamps are intentionally mismatched; not real reports. 1 response per cell per timepoint.',
            'dataset_sha256':proof['v3_dataset_sha256'],'v3_log_sha256':proof['v3_log_sha256'],
            'v4_script_sha256':expected,'by_kind_arm':summary,
            'switch_content_effect_on_correct_action':est(content_effects),
            'switch_stated_timestamp_effect_on_correct_action':est(timestamp_effects),
            'switch_content_x_timestamp_interaction_on_correct_action':est(interaction),
            'rows':records}
    target=Path(args.analysis_out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('rows',)},indent=2))


def main(argv=None):
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='cmd',required=True)
    for command in ('preflight','run','analyze'):
        q=sub.add_parser(command)
        q.add_argument('--dataset',default=DATASET)
        q.add_argument('--original',default=ORIG_LOG)
        q.add_argument('--out',default=OUT)
        q.add_argument('--model',default=MODEL)
        q.add_argument('--analysis-out',default='results/v4_cross_analysis.json')
        if command=='run':
            q.add_argument('--authorize',action='store_true')
            q.add_argument('--max-new-calls',type=int,default=0)
    args=parser.parse_args(argv)
    if args.cmd=='preflight':
        d,ix,p=load_frozen(args.dataset,args.original)
        jobs=plan(d,ix)
        print('PASS: original 288 calls validated; exactly 96 new counterfactual tasks; prompt isolation passed.')
        print('First crossed prompts:')
        for item in jobs[:2]:print(item['episode'],item['hour'],item['arm'],sha(item['question'].encode())[:12])
    elif args.cmd=='run':execute(args)
    elif args.cmd=='analyze':analyze(args)

if __name__=='__main__':main()
