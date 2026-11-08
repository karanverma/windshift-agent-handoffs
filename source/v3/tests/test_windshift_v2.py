import unittest, hashlib, json
from windshift import (generate, public_view, exposure_proxy, proxy_policy,
                       evidence_receipt, TIMES)

class V2ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.ds=generate(n_switch=5,n_stable=4,n_ambiguous=3)
    def test_proxy_deterministic(self):
        e=self.ds['episodes'][0]
        self.assertEqual(exposure_proxy(e,7),exposure_proxy(e,7))
    def test_oracle_not_visible(self):
        e=self.ds['episodes'][0]
        r=public_view(e,7)
        self.assertNotIn('truth',str(r))
        self.assertNotIn('oracle_contrib',str(r))
        self.assertIn('screening_model_source_exposure_index',r)
    def test_proxy_uses_no_hidden_oracle(self):
        import copy
        e=self.ds['episodes'][0]; corrupted=copy.deepcopy(e)
        for h in corrupted['hours']:
            h['truth']='EAST'
            h['oracle_contrib']={'EAST':999999,'WEST':0}
        self.assertEqual(exposure_proxy(e,7),exposure_proxy(corrupted,7))
        self.assertEqual(evidence_receipt(e,7,'WEST')['allowed'],evidence_receipt(corrupted,7,'WEST')['allowed'])
    def test_receipt_is_current(self):
        e=self.ds['episodes'][0]
        a=evidence_receipt(e,5,'WEST');b=evidence_receipt(e,7,'WEST')
        self.assertNotEqual(a['receipt_sha256'],b['receipt_sha256'])
    def test_gateway_rejects_stale_evidence(self):
        e=self.ds['episodes'][0]
        for t in TIMES[1:]:
            for s in ('WEST','EAST'):
                r=evidence_receipt(e,t,s,evidence_hour=t-2)
                self.assertFalse(r['allowed'])
                self.assertEqual(r['reason'],'stale_evidence')
    def test_receipt_reproducible(self):
        e=self.ds['episodes'][0];r=evidence_receipt(e,7,'WEST')
        self.assertEqual(r,evidence_receipt(e,7,'WEST'))
        self.assertEqual(len(r['receipt_sha256']),64)
    def test_no_unconditional_action(self):
        for e in self.ds['episodes']:
            for t in TIMES:
                accepted=[s for s in ('WEST','EAST') if evidence_receipt(e,t,s)['allowed']]
                self.assertLessEqual(len(accepted),1)
                self.assertTrue(evidence_receipt(e,t,'ABSTAIN')['allowed'])
    def test_comparator(self):
        self.assertEqual(proxy_policy({'WEST':8,'EAST':1}),'WEST')
        self.assertEqual(proxy_policy({'WEST':2,'EAST':2}),'ABSTAIN')
        self.assertEqual(proxy_policy({'WEST':1,'EAST':8}),'EAST')

if __name__=='__main__':unittest.main()
