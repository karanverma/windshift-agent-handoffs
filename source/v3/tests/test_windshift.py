import unittest
from windshift import generate, public_view, plume_contributions, truth_label, parse_decision, gate_accepts, select_votes, TIMES

class ResearchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = generate(n_switch=4, n_stable=3, n_ambiguous=2)

    def test_repeatable_dataset(self):
        self.assertEqual(self.ds, generate(n_switch=4, n_stable=3, n_ambiguous=2))

    def test_public_view_cannot_see_oracle(self):
        ep = self.ds['episodes'][0]
        text = str(public_view(ep, TIMES[1]))
        self.assertNotIn('truth', text)
        self.assertNotIn('oracle_contrib', text)

    def test_switch_cases_have_actual_label_change(self):
        for ep in self.ds['episodes']:
            if ep['kind'] == 'switch':
                labels = [ep['hours'][t]['truth'] for t in TIMES]
                self.assertIn('WEST', labels)
                self.assertIn('EAST', labels)

    def test_labels_do_not_use_observed_pm(self):
        ds = self.ds['episodes'][0]
        self.assertTrue(all(ep['truth'] in ('WEST', 'EAST', 'ABSTAIN') for ep in ds['hours']))

    def test_parse_invalid_does_not_become_abstain(self):
        with self.assertRaises(ValueError):
            parse_decision('not json')
        self.assertEqual(parse_decision('{"source":"WEST","confidence":0.4}')['source'], 'WEST')
        with self.assertRaises(ValueError):
            parse_decision('{"source":"WEST","confidence":3}')

    def test_vote_tie_abstains(self):
        self.assertEqual(select_votes([{'source':'EAST'}, {'source':'WEST'}]), 'ABSTAIN')
        self.assertEqual(select_votes([{'source':'ABSTAIN'}, {'source':'ABSTAIN'}, {'source':'WEST'}]), 'ABSTAIN')

    def test_gate_is_binary(self):
        ep = self.ds['episodes'][0]
        self.assertIsInstance(gate_accepts(ep, TIMES[0], 'WEST'), bool)

if __name__ == '__main__':
    unittest.main()

class StatsTests(unittest.TestCase):
    def test_bootstrap_requires_clusters(self):
        from analysis import boot_ci
        self.assertEqual(boot_ci([0.1, 0.2]), [None, None])
    def test_delay_without_truth_transition(self):
        from analysis import correction_delay
        self.assertIsNone(correction_delay([{'time':1,'truth':'WEST','decision':'WEST'},
                                           {'time':2,'truth':'WEST','decision':'EAST'}]))
    def test_delay_after_source_switch(self):
        from analysis import correction_delay
        rows=[{'time':1,'truth':'WEST','decision':'WEST'},
              {'time':2,'truth':'EAST','decision':'WEST'},
              {'time':3,'truth':'EAST','decision':'EAST'}]
        self.assertEqual(correction_delay(rows),(1,False))
