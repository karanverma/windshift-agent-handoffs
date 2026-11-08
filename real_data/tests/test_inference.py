import tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import windshift_real_inference as r

EP={'episode_id':'REAL_TEST_2024-10-02','station_name':'Test station',
    'station':'ITO_CPCB','current_day':'2024-10-02','previous_day':'2024-10-01',
    'current_pm25_ugm3':71.0,'previous_pm25_ugm3':33.0,
    'current_label':'HIGH','previous_label':'LOW','current_coverage_hours':24,'episode_type':'LOW_TO_HIGH'}

class InferenceTests(unittest.TestCase):
    def test_no_paid_calls_default(self):
        with tempfile.TemporaryDirectory() as td:
            val=r.run_study([EP],output_dir=td,transport=lambda *args: 1)
            assert val['preview_only']
            assert not (Path(td)/'real_llm_calls.jsonl').exists()
    def test_complete_mock_resume_and_hashes(self):
        callcounter=[0]
        def fake(model,prompt):
            callcounter[0]+=1
            answer='HIGH' if '71.0000' in prompt else 'LOW'
            return {'raw_text':answer,'provider_id':f'mock-{callcounter[0]}','usage':{},'finish_reason':'stop'}
        with tempfile.TemporaryDirectory() as td:
            r.run_study([EP],output_dir=td,authorize=True,transport=fake,sleep_seconds=0)
            self.assertEqual(callcounter[0],17)
            s=r.study_audit([EP],Path(td)/'real_llm_calls.jsonl')
            self.assertTrue(s['complete']);self.assertEqual(s['valid_logged_calls'],17)
            r.run_study([EP],output_dir=td,authorize=True,transport=fake,sleep_seconds=0)
            self.assertEqual(callcounter[0],17)
    def test_spoof_only_changes_declared_date(self):
        from windshift_realdata import reviewer_prompt
        a=reviewer_prompt(EP,'OLD_PEER','LOW','HIGH')
        b=reviewer_prompt(EP,'SPOOFED_OLD_PEER','LOW','HIGH')
        self.assertEqual(a.replace('2024-10-01','2024-10-02'),b)

if __name__=='__main__':unittest.main()
