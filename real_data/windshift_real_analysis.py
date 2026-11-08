"""Offline-independent audit and analysis. No API key or network needed."""
from __future__ import annotations
from collections import defaultdict, Counter
from pathlib import Path
import csv
import hashlib
import json
import pandas as pd
import matplotlib.pyplot as plt
from windshift_realdata import STATIONS, THRESHOLD, file_sha256, parse_label, reviewer_prompt, peer_prompt, save_json
from windshift_real_inference import read_ledger, ARMS, REVIEWER_MODELS, PEER_MODEL, study_audit, sha


def independent_audit(base_dir, figure=True):
    root = Path(base_dir)
    eps = json.loads((root/'episodes.json').read_text())
    manifest = json.loads((root/'source_manifest.json').read_text())
    for site in STATIONS:
        raw_file=root/'raw'/f'{site}.csv'
        if not raw_file.exists():
            raise ValueError('Original real measured CSV missing: '+str(raw_file))
        if manifest['stations'][site]['sha256']!=file_sha256(raw_file):
            raise ValueError('Original source CSV hash mismatch for '+site)
    days = pd.read_csv(root/'station_daily.csv')
    keymap={(str(r.station),str(r.day)):r for r in days.itertuples(index=False)}
    used=set()
    for e in eps:
        site=e['station']
        for date, meas_key, label_key in (('previous_day','previous_pm25_ugm3','previous_label'),
                                          ('current_day','current_pm25_ugm3','current_label')):
            date_s=e[date]
            k=(site,date_s)
            if k not in keymap:raise ValueError('Episode source measurement missing '+str(k))
            if abs(float(keymap[k].pm25_mean)-float(e[meas_key]))>0.0002:
                raise ValueError('Episode measured value does not match daily archive')
            if ('HIGH' if float(e[meas_key])>=THRESHOLD else 'LOW')!=e[label_key]:
                raise ValueError('Label not consistent with measured PM2.5 threshold')
            if (site,date_s) in used:
                raise ValueError('A calendar day was reused across selected paired episodes')
            used.add((site,date_s))
    ledger=root/'real_llm_calls.jsonl'
    if not ledger.exists():
        return {'status':'MEASUREMENTS_ONLY', 'real_episodes':len(eps),
                'source_validation':'PASS', 'inference_results':'NOT_YET_RUN'}
    rows = read_ledger(ledger)
    basic = study_audit(eps, ledger)
    successful={r['call_key']:r for r in rows if r.get('valid')}
    errors=[r for r in rows if not r.get('valid')]
    counts=defaultdict(Counter)
    peer_ok=defaultdict(Counter)
    detail=[]
    for e in eps:
        p={}
        for which in ('previous','current'):
            key=f'peer|{e["episode_id"]}|{which}'
            if key not in successful:continue
            r=successful[key]
            exp=peer_prompt(e,which)
            if r['prompt_sha256']!=sha(exp):raise ValueError('Peer prompt replay mismatch '+key)
            p[which]=r['parsed_label']
            peer_ok[which]['n']+=1
            peer_ok[which]['correct']+=int(r['parsed_label']==e[f'{which}_label'])
        if set(p)!={'previous','current'}:continue
        for arm in ARMS:
            exp=reviewer_prompt(e,arm,p['previous'],p['current'])
            cross_model_hashes=[]
            for model in REVIEWER_MODELS:
                key=f'reviewer|{e["episode_id"]}|{model}|{arm}'
                if key not in successful:continue
                r=successful[key]
                if r['prompt_sha256']!=sha(exp):raise ValueError('Reviewer prompt drift '+key)
                cross_model_hashes.append(r['prompt_sha256'])
                label=r['parsed_label']
                k=(model,arm,e['episode_type'])
                counts[k]['n']+=1
                counts[k]['correct']+=int(label==e['current_label'])
                counts[k]['wrong']+=int(label not in (e['current_label'],'ABSTAIN'))
                counts[k]['abstain']+=int(label=='ABSTAIN')
                detail.append({'episode_id':e['episode_id'],'station':e['station'],
                               'day':e['current_day'],'episode_type':e['episode_type'],
                               'real_current_pm25_ugm3':e['current_pm25_ugm3'],
                               'observed_label':e['current_label'],'previous_label':e['previous_label'],
                               'peer_old':p['previous'],'peer_current':p['current'],
                               'model':model,'arm':arm,'model_label':label,
                               'correct':int(label==e['current_label']),
                               'wrong':int(label not in (e['current_label'],'ABSTAIN')),
                               'abstain':int(label=='ABSTAIN'),
                               'provider_id':r.get('provider_id'),'prompt_sha256':r['prompt_sha256']})
            if len(set(cross_model_hashes))>1:
                raise ValueError('Prompt mismatch across reviewer models')
    df=pd.DataFrame(detail)
    if len(df):df.to_csv(root/'measured_decisions.csv',index=False)
    summary=[{'model':a,'arm':b,'episode_type':c,**dict(d)} for (a,b,c),d in sorted(counts.items())]
    aggregate=[]
    for model in REVIEWER_MODELS:
        for arm in ARMS:
            subset=df[(df.model==model)&(df.arm==arm)] if len(df) else pd.DataFrame()
            n=int(len(subset))
            aggregate.append({'model':model,'arm':arm,'n':n,
                              'correct':int(subset.correct.sum()) if n else 0,
                              'wrong':int(subset.wrong.sum()) if n else 0,
                              'abstain':int(subset.abstain.sum()) if n else 0})
    report={'source_validation':'PASS','status':'COMPLETE' if basic['complete'] else 'PARTIAL',
            'source_files':{k:manifest['stations'][k]['sha256'] for k in STATIONS},
            'real_episodes':len(eps),'inference_audit':basic,
            'peer_fidelity':{k:dict(v) for k,v in peer_ok.items()},
            'all_outcomes':summary,'aggregate':aggregate,
            'invalid_attempts_logged':len(errors),
            'warning':'Descriptive observational-grounded screening, not forecasting or atmospheric source attribution. Reviewers see current measured daily mean. Only two stations; no causal transport inference.'}
    save_json(report,root/'REAL_EVIDENCE_AUDIT.json')
    pd.DataFrame(aggregate).to_csv(root/'summary_by_model_arm.csv',index=False)
    if figure and len(df) and basic['complete']:
        fig, axes=plt.subplots(1,3,figsize=(15,5),sharey=True)
        for ax,model in zip(axes,REVIEWER_MODELS):
            sub=[x for x in aggregate if x['model']==model]
            xs=range(len(sub))
            cor=[x['correct']/x['n']*100 if x['n'] else 0 for x in sub]
            absn=[x['abstain']/x['n']*100 if x['n'] else 0 for x in sub]
            wrong=[x['wrong']/x['n']*100 if x['n'] else 0 for x in sub]
            ax.bar(xs,cor,label='Correct')
            ax.bar(xs,absn,bottom=cor,label='Abstain')
            ax.bar(xs,wrong,bottom=[a+b for a,b in zip(cor,absn)],label='Wrong')
            ax.set_title(model.split('/')[-1],fontsize=10)
            ax.set_xticks(list(xs),[x['arm'].replace('_','\n') for x in sub],rotation=0,fontsize=7)
            ax.set_ylim(0,102)
            if ax is axes[0]:ax.set_ylabel('Percent of eligible paired day episodes')
        axes[-1].legend(loc='lower right',fontsize=8)
        fig.suptitle('Real station measurements: retrospective reviewer outcomes (NOT live air-quality decisions)')
        fig.tight_layout()
        fig.savefig(root/'real_monitoring_outcomes.png',dpi=180)
        plt.close(fig)
    return report
