"""Offline correctness checks: no live LLM or provider calls."""
import json, os, tempfile, unittest, pathlib
from collections import Counter
from unittest.mock import patch
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent))
import windshift_v3 as w
import windshift_v2 as base


class TestV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=w.make_dataset()
        w.check_dataset(cls.data)

    def test_exact_balance_and_identity(self):
        self.assertEqual(len(self.data['episodes']),24)
        self.assertEqual(len({x['episode_id'] for x in self.data['episodes']}),24)
        labels=Counter(x['window']['direction'] for x in self.data['episodes'])
        self.assertEqual(labels['WEST_TO_EAST'],8)
        self.assertEqual(labels['EAST_TO_WEST'],8)

    def test_temporal_sequence_and_truth_isolation(self):
        for ep in self.data['episodes']:
            pre=ep['window']['pre']
            for t in ep['window']['post']:
                self.assertLess(pre,t)
                v=base.public_view(ep,t)
                self.assertNotIn('truth',str(v))
                self.assertNotIn('oracle_contrib',str(v))
                for key in ('recent_fire_activity','recent_wind_kmh','recent_receptor_pm_index'):
                    self.assertTrue(all(r['hour']<=t for r in v[key]))
                self.assertTrue(all(r['hour']<=pre for r in base.public_view(ep,pre)['recent_fire_activity']))

    def test_target_views_are_equal(self):
        for ep in self.data['episodes']:
            t=ep['window']['post'][0]
            a=[{'source':'WEST','confidence':0.9}, {'source':'EAST','confidence':0.8}]
            for arm in w.ARMS:
                p=json.loads(w.target_prompt(ep,t,arm,a,a))
                self.assertEqual(p['observations'],base.public_view(ep,t))
                self.assertNotIn('truth',str(p))
            fresh=json.loads(w.target_prompt(ep,t,'fresh_peer',a,a))
            stale=json.loads(w.target_prompt(ep,t,'stale_peer',a,a))
            self.assertEqual(len(stale['peer_reports']),2)
            self.assertEqual(len(fresh['peer_reports']),2)
            self.assertTrue(all(x['observed_hour']<t for x in stale['peer_reports']))
            self.assertTrue(all(x['observed_hour']==t for x in fresh['peer_reports']))

    def test_call_number_and_balanced_order(self):
        tasks=list(w.planned_tasks(self.data))
        self.assertEqual(len(tasks),288)
        self.assertEqual(Counter(t[4] for t in tasks if t[1]=='target'),{
            'no_peer':48, 'fresh_peer':48,'stale_peer':48})
        first=[]
        for ep in self.data['episodes']:
            for t in ep['window']['post']:
                first.extend(a for x,s,time,idx,a in tasks if x==ep and s=='target' and time==t)
        # No single arm always goes last.
        first_arm=[next(a for x,s,time,idx,a in tasks if x==ep and s=='target' and time==t)
                   for ep in self.data['episodes'] for t in ep['window']['post']]
        self.assertEqual(Counter(first_arm),{'no_peer':16,'fresh_peer':16,'stale_peer':16})

    def test_reversal_labels(self):
        for ep in self.data['episodes']:
            if ep['kind']!='switch':continue
            pre=ep['window']['pre']
            p0=ep['hours'][pre]['truth']
            x,y=ep['window']['post']
            self.assertEqual(ep['hours'][x]['truth'],ep['hours'][y]['truth'])
            self.assertNotEqual(p0,ep['hours'][x]['truth'])

    def test_no_paid_calls_without_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/'data.json'
            path.write_text(json.dumps(self.data))
            args=type('Args',(),{'dataset':str(path),'out':str(pathlib.Path(tmp)/'calls.jsonl'),
                 'model':w.MODEL,'temperature':.2,'episodes':2,'max_new_calls':0,'authorize':False})()
            with patch.object(w,'invoke_provider',side_effect=AssertionError('No API expected')):
                w.execute(args)
            self.assertFalse(pathlib.Path(args.out).exists())

    def test_synthetic_mock_pipeline_resume_and_analysis(self):
        # Fabricated provider decisions are used ONLY to test plumbing; never reported as science.
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/'data.json';path.write_text(json.dumps(self.data))
            out=pathlib.Path(tmp)/'mock_calls.jsonl'
            args=type('Args',(),{'dataset':str(path),'out':str(out),
                   'model':w.MODEL,'temperature':.2,'episodes':2,'max_new_calls':8,'authorize':True})()
            call_count=[0]
            def mock_provider(key,model,prompt,temp,max_tokens=180,retries=2):
                call_count[0]+=1
                view=json.loads(prompt)['observations']
                label=base.proxy_policy(view['screening_model_source_exposure_index'])
                choice={'source':label,'confidence':.7,'reason':'mock offline, not LLM'}
                return choice,json.dumps(choice),{},f'mock_{call_count[0]}'
            with patch.dict(os.environ,{'OPENROUTER_API_KEY':'TEST_FAKE_KEY'}),patch.object(w,'invoke_provider',side_effect=mock_provider):
                w.execute(args)
                self.assertEqual(len(w.load_log(out)[0]),8)
                args.max_new_calls=16
                w.execute(args)
                self.assertEqual(len(w.load_log(out)[0]),24)
                w.execute(args)
                self.assertEqual(len(w.load_log(out)[0]),24)  # resumable / idempotent
            d=self.data
            rows,miss,got,errors=w.rows_from_log(d,out)
            self.assertEqual(len(rows),12)  # 2 episodes x 2 times x 3 arms
            self.assertEqual(len(miss),44)
            self.assertEqual(errors,0)
            for r in rows:self.assertIn(r['decision'],base.VALID)

    def test_episode_cluster_bootstrap(self):
        rows=[]
        for ep in ['x','y','z']:
            for t in (1,2):
                for arm in ('fresh_peer','stale_peer'):
                    rows.append({'episode':ep,'kind':'switch','arm':arm,
                                 'unsupported':int(arm=='stale_peer')})
        z=w.bootstrap_episode_diff(rows,'stale_peer','fresh_peer',samples=100)
        self.assertEqual(z['n_episodes'],3)
        self.assertEqual(z['mean_diff'],1)
        self.assertEqual(z['ci95'],[1,1])

if __name__=='__main__':unittest.main()
