"""University identity must survive non-Latin scripts and explicit source gaps."""
from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from erasmusgravity.cities import normalize_org_key
from erasmusgravity.dashboard.refresh import university_tables
from erasmusgravity.ka1 import PARTICIPANTS_COL

class UniversityNameTests(unittest.TestCase):
    def test_non_latin_names_remain_distinct(self):
        names=['Στρατιωτική Σχολή Ευελπίδων','ΣΧΟΛΗ ΙΚΑΡΩΝ','НАЦИОНАЛНА АКАДЕМИЯ','جامعة مصر الدولية','関西外国語大学']
        keys=[normalize_org_key(name) for name in names]
        self.assertTrue(all(keys))
        self.assertEqual(len(set(keys)),len(names))
        self.assertEqual(normalize_org_key('Università di Padova'),normalize_org_key('UNIVERSITA DI PADOVA'))
        self.assertEqual(normalize_org_key('ΣΧΟΛΗ ΙΚΑΡΩΝ'),normalize_org_key('Σχολή Ικάρων'))

    def test_normalized_placeholders(self):
        for name in [None,'','-','/','N/A','N.A.','n a','Not Applicable','not available','UNKNOWN','NULL']:
            with self.subTest(name=name):self.assertIsNone(normalize_org_key(name))
        self.assertIsNotNone(normalize_org_key('Nottingham Trent University'))

    def test_endpoint_aggregation_preserves_named_and_missing_weights(self):
        records=[]
        for name,weight in [('ΣΧΟΛΗ ΙΚΑΡΩΝ',3),('Στρατιωτική Σχολή Ευελπίδων',4),('N/A',2)]:
            records.append({'sending_code':'EL','sending_country':'Greece','Sending City':'Athens',
                            'Sending Organization':name,'receiving_code':'IT','receiving_country':'Italy',
                            'Receiving City':'Padova','Receiving Organization':'Università di Padova',PARTICIPANTS_COL:weight})
        tables=university_tables(pd.DataFrame(records))
        for rows in tables.values():self.assertEqual(sum(r['flow_count'] for r in rows),9)
        names={r['sending_org']:r['flow_count'] for r in tables['uniUni']}
        self.assertEqual(names,{'ΣΧΟΛΗ ΙΚΑΡΩΝ':3,'Στρατιωτική Σχολή Ευελπίδων':4,'(University not specified)':2})

if __name__=='__main__':unittest.main()
