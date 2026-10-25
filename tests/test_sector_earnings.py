"""Contracts for latest-wave sector earnings, units and missing observations."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from erasmusgravity.indicators import fetch_sector_earnings


def observation(code='IT', sector='C', value=2500):
    return {'geo': code, 'geo_label': {'IT': 'Italy', 'EL': 'Greece', 'EU27_2020': 'EU'}.get(code, code),
            'nace_r2': sector, 'nace_r2_label': sector, 'value': value}


class SectorEarningsTests(unittest.TestCase):
    @patch('erasmusgravity.indicators.fetch_eurostat')
    def test_latest_wave_uses_detailed_sectors_and_keeps_missing_currency(self, fetch):
        fetch.side_effect = [pd.DataFrame({'time': ['2018', '2022']}),
                             pd.DataFrame([observation(), observation('EU27_2020')]),
                             pd.DataFrame([observation(value=2700), observation('EL', value=1800)])]
        result = fetch_sector_earnings()
        self.assertEqual(set(result.year), {2022})
        self.assertEqual(set(result.country_code), {'IT', 'EL'})
        self.assertEqual(result.loc[result.country_code.eq('IT'), 'earnings_eur'].iloc[0], 2500)
        self.assertEqual(result.loc[result.country_code.eq('IT'), 'earnings_pps'].iloc[0], 2700)
        greek = result.loc[result.country_code.eq('EL')].iloc[0]
        self.assertTrue(pd.isna(greek.earnings_eur))
        self.assertEqual(greek.country_name, 'Greece')
        for call in fetch.call_args_list[1:]:
            self.assertEqual(call.args, ('earn_ses22_24',))
            self.assertEqual(call.kwargs['sizeclas'], 'GE10')
            self.assertEqual(call.kwargs['time'], '2022')
        self.assertEqual([c.kwargs['unit'] for c in fetch.call_args_list[1:]], ['EUR', 'PPS'])

    @patch('erasmusgravity.indicators.fetch_eurostat')
    def test_aggregate_only_response_does_not_replace_sector_reference(self, fetch):
        fetch.return_value = pd.DataFrame([observation(sector='B-S_X_O')])
        with self.assertRaisesRegex(ValueError, 'no detailed NACE sectors'):
            fetch_sector_earnings(year=2022)

    @patch('erasmusgravity.indicators.fetch_eurostat')
    def test_missing_release_fails_explicitly(self, fetch):
        fetch.return_value = pd.DataFrame()
        with self.assertRaisesRegex(ValueError, 'No published'):
            fetch_sector_earnings()


if __name__ == '__main__':
    unittest.main()
