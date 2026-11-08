"""OpenRouter inference runner for real CPCB-derived episodes.

All calls are opt-in. No API request is made unless run_study is invoked
with authorize=True and an actual OPENROUTER_API_KEY is configured.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
import requests

from windshift_realdata import peer_prompt, reviewer_prompt, parse_label, save_json

PEER_MODEL = 'openai/gpt-4o-mini'
REVIEWER_MODELS = (
    'openai/gpt-4o-mini',
    'google/gemini-3.1-flash-lite',
    'qwen/qwen3-235b-a22b-2507',
)
ARMS = ('NO_PEER', 'CURRENT_PEER', 'OLD_PEER', 'SPOOFED_OLD_PEER', 'QUARANTINE')
API_URL = 'https://openrouter.ai/api/v1/chat/completions'


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def append_jsonl(path, row):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def read_ledger(path):
    rows = []
    p = Path(path)
    if p.is_file():
        for ln, line in enumerate(p.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f'Corrupt ledger line {ln}: {exc}')
    return rows


def request_llm(model, prompt, api_key, timeout=110):
    payload={
        'model':model,
        'messages':[{'role':'user','content':prompt}],
        'temperature':0.2,
        'max_tokens':24,
    }
    headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json',
             'HTTP-Referer':'https://colab.research.google.com/',
             'X-Title':'WindShift CPCB Retrospective Validation'}
    r=requests.post(API_URL,headers=headers,json=payload,timeout=timeout)
    # Preserve even invalid server payload in exception; never fabricate success.
    if r.status_code >= 400:
        raise RuntimeError(f'OpenRouter HTTP {r.status_code}: {r.text[:800]}')
    obj=r.json()
    choices=obj.get('choices') or []
    content = choices[0].get('message',{}).get('content') if choices else None
    if isinstance(content, list):
        content=''.join(x.get('text','') for x in content if isinstance(x, dict))
    if not isinstance(content,str) or not content.strip():
        raise RuntimeError('OpenRouter response did not contain non-empty text: ' + repr(obj)[:500])
    return {'provider_id':obj.get('id'), 'raw_text':content,
            'usage':obj.get('usage',{}), 'finish_reason':choices[0].get('finish_reason') if choices else None}


def run_study(episodes, *, output_dir, authorize=False, pilot=False, models=REVIEWER_MODELS,
              transport=None, sleep_seconds=0.05):
    if not authorize:
        print('DRY PREVIEW ONLY: no paid model calls. episodes=',len(episodes),
              'potential reviewer calls=',len(episodes)*len(ARMS)*len(models),
              'potential peer calls=',len(episodes)*2)
        return {'preview_only':True}
    api_key=os.environ.get('OPENROUTER_API_KEY')
    if transport is None and not api_key:
        raise RuntimeError('OPENROUTER_API_KEY not set; paid calls cannot start.')
    Path(output_dir).mkdir(parents=True,exist_ok=True)
    ledger=Path(output_dir)/'real_llm_calls.jsonl'
    prior=read_ledger(ledger)
    index={r['call_key']:r for r in prior if r.get('valid')}
    if pilot:
        # One deterministic, already-selected real episode from each station.
        stations_in_order = list(dict.fromkeys(e['station'] for e in episodes))
        study_episodes = [next(e for e in episodes if e['station']==site) for site in stations_in_order[:2]]
    else:
        study_episodes = episodes
    added=0
    for i,e in enumerate(study_episodes,1):
        peers={}
        for which in ('previous','current'):
            key=f'peer|{e["episode_id"]}|{which}'
            prompt=peer_prompt(e,which)
            if key in index:
                rec=index[key]
                if rec['prompt_sha256']!=sha(prompt):
                    raise RuntimeError('Prompt drift detected for '+key)
                peers[which]=rec['parsed_label']
                continue
            model=PEER_MODEL
            res = None
            try:
                res = transport(model,prompt) if transport else request_llm(model,prompt,api_key)
                label=parse_label(res['raw_text'])
                rec={'phase':'peer', 'model':model, 'episode_id':e['episode_id'],
                     'arm':which, 'call_key':key, 'prompt':prompt,
                     'prompt_sha256':sha(prompt),'parsed_label':label,
                     'valid':True, **res}
            except Exception as exc:
                rec={'phase':'peer','model':model,'episode_id':e['episode_id'],
                     'arm':which,'call_key':key,'prompt':prompt,
                     'prompt_sha256':sha(prompt),'valid':False,'error':str(exc),
                     **(res or {})}  # keep full raw content and provider ID even on parse errors
            append_jsonl(ledger,rec)
            added+=1
            if not rec['valid']:
                raise RuntimeError(f'Peer call failed and was logged: {key} {rec.get("error")}')
            index[key]=rec
            peers[which]=rec['parsed_label']
            if transport is None:
                time.sleep(sleep_seconds)
        for model in models:
            for arm in ARMS:
                prompt=reviewer_prompt(e,arm,peers['previous'],peers['current'])
                key=f'reviewer|{e["episode_id"]}|{model}|{arm}'
                if key in index:
                    if index[key]['prompt_sha256']!=sha(prompt):
                        raise RuntimeError('Prompt drift detected for '+key)
                    continue
                res = None
                try:
                    res=transport(model,prompt) if transport else request_llm(model,prompt,api_key)
                    label=parse_label(res['raw_text'])
                    rec={'phase':'reviewer','model':model,'episode_id':e['episode_id'],
                         'arm':arm,'call_key':key,'prompt':prompt,
                         'prompt_sha256':sha(prompt),'parsed_label':label,
                         'valid':True,**res}
                except Exception as exc:
                    rec={'phase':'reviewer','model':model,'episode_id':e['episode_id'],
                         'arm':arm,'call_key':key,'prompt':prompt,
                         'prompt_sha256':sha(prompt),'valid':False,'error':str(exc),
                         **(res or {})}  # preserve invalid response content for audit
                append_jsonl(ledger,rec)
                added+=1
                if not rec['valid']:
                    print(f'Logged invalid response: {key}: {rec.get("error")}')
                    # Don't silently drop errors or advance to later conditions.
                    raise RuntimeError(f'Stopped on invalid call: {key}')
                index[key]=rec
                if transport is None:
                    time.sleep(sleep_seconds)
        print(f'Completed {i}/{len(study_episodes)} episodes; new requests this invocation: {added}')
    return {'preview_only':False,'added':added,'ledger':str(ledger)}


def study_audit(episodes, ledger_path):
    rows=read_ledger(ledger_path)
    eindex={e['episode_id']:e for e in episodes}
    keys=[r['call_key'] for r in rows if r.get('valid')]
    if len(keys)!=len(set(keys)):
        raise ValueError('Duplicate successful call keys present; manually inspect resume ledger.')
    ids=[r.get('provider_id') for r in rows if r.get('provider_id')]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate provider request IDs')
    for r in rows:
        if r['episode_id'] not in eindex:
            raise ValueError('Call for unknown episode')
        if r['prompt_sha256']!=sha(r['prompt']):
            raise ValueError('Logged prompt hash mismatch')
        if r.get('valid'):
            parse_label(r['parsed_label'])
    expected=len(episodes)*(2+len(REVIEWER_MODELS)*len(ARMS))
    stats={'expected_calls_full_study':expected,
           'logged_rows_including_errors':len(rows),
           'valid_logged_calls':sum(bool(r.get('valid')) for r in rows),
           'unique_provider_ids_including_invalid_attempts':len(ids),
           'successful_calls_missing_provider_id':sum(bool(r.get('valid')) and not r.get('provider_id') for r in rows),
           'invalid_logged_calls':sum(not bool(r.get('valid')) for r in rows),
           'distinct_reviewers':sorted({r['model'] for r in rows if r['phase']=='reviewer' and r.get('valid')}),
           'distinct_observed_episode_ids':len({r['episode_id'] for r in rows if r.get('valid')}),
           'complete':sum(bool(r.get('valid')) for r in rows)==expected and not any(not r.get('valid') for r in rows)
                      and all(r.get('provider_id') for r in rows if r.get('valid')),
          }
    # A strict full-study status; pilot is expected to have complete=False.
    return stats
