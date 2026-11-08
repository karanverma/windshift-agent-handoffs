import os, sys, tempfile, unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import windshift_realdata as wr

class RealDataPipelineTests(unittest.TestCase):
    def test_parse_strict(self):
        for x in ('HIGH','LOW','ABSTAIN'):
            self.assertEqual(wr.parse_label(' '+x+'\n'),x)
        for x in ('HIGH because', 'INVALID', 'West', ''):
            with self.assertRaises(ValueError): wr.parse_label(x)
    def test_station_selection_deterministic_and_disjoint(self):
        # Code fixture only: invented observations are never part of research outputs.
        frames={}
        for site in wr.STATIONS:
            dates=pd.date_range('2024-01-01',periods=100,freq='D')
            ds=pd.DataFrame({'day':dates.strftime('%Y-%m-%d'),
                             'pm25_mean':[20 if i%3 == 0 else 90 for i in range(len(dates))],
                             'hours':[24]*len(dates),
                             'quarterhour_samples':[96]*len(dates)})
            ds['label']=ds.pm25_mean.map(lambda v:'HIGH' if v>=60 else 'LOW')
            frames[site]=ds
        e,a=wr.select_episodes(frames)
        e2,a2=wr.select_episodes(frames)
        self.assertEqual(e,e2)
        seen=set()
        for row in e:
            self.assertNotIn((row['station'],row['previous_day']),seen)
            self.assertNotIn((row['station'],row['current_day']),seen)
            seen.add((row['station'],row['previous_day']))
            seen.add((row['station'],row['current_day']))
    def test_threshold_and_gated_message(self):
        ep={'station_name':'ITO','current_day':'2025-01-02','previous_day':'2025-01-01',
            'current_pm25_ugm3':61,'current_coverage_hours':24}
        old=wr.reviewer_prompt(ep,'OLD_PEER','LOW','HIGH')
        spoof=wr.reviewer_prompt(ep,'SPOOFED_OLD_PEER','LOW','HIGH')
        assert old.replace('2025-01-01','2025-01-02')==spoof
        gate=wr.reviewer_prompt(ep,'QUARANTINE','LOW','HIGH')
        self.assertNotIn('Peer recommendation: LOW',gate)
    def test_missing_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.csv'
            p.write_text('date,foo\n2024-01-01,6\n')
            with self.assertRaises(ValueError): wr.load_station_csv(p,'ITO_CPCB')
    def test_short_data_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'few.csv'
            p.write_text('Timestamp,PM2.5 (ug/m3)\n2024-01-01 00:00:00,55\n')
            with self.assertRaises(ValueError): wr.load_station_csv(p,'ITO_CPCB')
    def test_true_daily_aggregation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'two_months.csv'
            with p.open('w') as f:
                f.write('Timestamp,PM2.5 (ug/m3)\n')
                for t in pd.date_range('2024-01-01',periods=24*4*45, freq='15min'):
                    f.write(f'{t},60\n')
            day,hour,a=wr.load_station_csv(p,'ITO_CPCB')
            self.assertEqual(len(day),45)
            self.assertTrue((day.pm25_mean==60).all())
            self.assertTrue((day.label=='HIGH').all())
            self.assertEqual(a['source_rows'],24*4*45)

if __name__=='__main__': unittest.main()
