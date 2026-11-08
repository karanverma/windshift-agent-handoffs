import json, os, unittest
from pathlib import Path
import windshift_v4 as v

class CrossoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.index, cls.proof = v.load_frozen()
        cls.ep=cls.data['episodes'][0]
        cls.t=cls.ep['window']['post'][0]
    def test_frozen_calls_are_complete(self):
        self.assertEqual(len(self.index),288)
    def test_96_unique_jobs(self):
        jobs=v.plan(self.data,self.index)
        self.assertEqual(len(jobs),96)
        self.assertEqual(len({(j['episode'],j['hour'],j['arm']) for j in jobs}),96)
    def test_current_advice_timestamp_only(self):
        ep=self.ep;t=self.t
        msg,system,_=v.crossed_prompt(self.index,ep,t,'current_content_old_timestamp')
        new=json.loads(msg)
        old=json.loads(self.index[(ep['episode_id'],'target',t,0,'fresh_peer')]['full_prompt'])
        self.assertEqual([p['recommended_source'] for p in new['peer_reports']],
                         [p['recommended_source'] for p in old['peer_reports']])
        self.assertNotEqual([p['observed_hour'] for p in new['peer_reports']],
                            [p['observed_hour'] for p in old['peer_reports']])
        self.assertEqual(new['observations'],old['observations'])
        self.assertEqual(system,self.index[(ep['episode_id'],'target',t,0,'fresh_peer')]['system_prompt'])
    def test_historical_advice_timestamp_only(self):
        ep=self.ep;t=self.t
        msg,system,_=v.crossed_prompt(self.index,ep,t,'historical_content_new_timestamp')
        new=json.loads(msg)
        old=json.loads(self.index[(ep['episode_id'],'target',t,0,'stale_peer')]['full_prompt'])
        self.assertEqual([p['recommended_source'] for p in new['peer_reports']],
                         [p['recommended_source'] for p in old['peer_reports']])
        self.assertNotEqual([p['observed_hour'] for p in new['peer_reports']],
                            [p['observed_hour'] for p in old['peer_reports']])
        self.assertEqual(new['observations'],old['observations'])
        self.assertEqual(system,self.index[(ep['episode_id'],'target',t,0,'stale_peer')]['system_prompt'])
    def test_never_leak_oracle(self):
        for j in v.plan(self.data,self.index):
            self.assertNotIn('oracle_contrib',j['question'])
            self.assertNotIn('"truth"',j['question'])
    def test_original_results_not_modified(self):
        import hashlib
        self.assertEqual(v.sha(Path(v.ORIG_LOG).read_bytes()),self.proof['v3_log_sha256'])
        self.assertEqual(v.sha(Path(v.DATASET).read_bytes()),self.proof['v3_dataset_sha256'])
    def test_strict_parser(self):
        out=v.parse_reply('{"source":"ABSTAIN","confidence":0.5,"reason":"unclear"}')
        self.assertEqual(out['source'],'ABSTAIN')
        for raw in ['{ "source":"MARS","confidence":0.5}', '{"source":"EAST","confidence":4}']:
            with self.assertRaises(ValueError):v.parse_reply(raw)
    def test_dry_run_no_key(self):
        from types import SimpleNamespace
        old=os.environ.pop('OPENROUTER_API_KEY',None)
        try:
            import io, contextlib
            x=SimpleNamespace(dataset=v.DATASET,original=v.ORIG_LOG,out='results/NO_EXISTING_V4_TEST_LOG.jsonl',model=v.MODEL,authorize=False,max_new_calls=0)
            with contextlib.redirect_stdout(io.StringIO()) as buf:v.execute(x)
            self.assertIn('DRY RUN',buf.getvalue())
        finally:
            if old is not None:os.environ['OPENROUTER_API_KEY']=old

if __name__=='__main__':unittest.main()
