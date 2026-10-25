"""Data-refresh contracts: source filters, complete counts, vintages, preserved research."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from erasmusgravity.dashboard.refresh import RESEARCH_KEYS, read_mobility, refresh_snapshot, university_tables
from erasmusgravity.ka1 import KA1_COLUMNS, PARTICIPANTS_COL, filter_he_studies


def row(origin='IT - Italy', destination='FR - France', weight=2, **changes):
    result = dict.fromkeys(KA1_COLUMNS, '')
    result.update({'Academic Year': '2023-24', 'Mobility Start Month': '2024-09', 'Mobility Duration': 100,
                   'Activity (mob)': 'HE-SMS - Student mobility for studies', 'Field': 'Higher Education',
                   'Participant Profile': 'LEARNERS', 'Participant Age': 22, 'Sending Country': origin,
                   'Sending City': 'Rome', 'Sending Organization': 'University A', 'Receiving Country': destination,
                   'Receiving City': 'Paris', 'Receiving Organization': 'University B', PARTICIPANTS_COL: weight})
    result.update(changes)
    return result


class RefreshTests(unittest.TestCase):
    def test_stream_filters_weights_missing_endpoint_and_na_country(self):
        records = [row(weight=3), row(destination='NA - Namibia', weight=4, **{'Receiving City': None}),
                   row(**{'Participant Profile': 'STAFF'}), row(**{'Participant Age': 17}),
                   row(**{'Activity (mob)': 'HE-SMT - Student mobility for traineeships'}),
                   row(destination='IT - Italy')]
        class Sheet:
            def iter_rows(self, **kwargs):
                return iter([KA1_COLUMNS, *[[r[k] for k in KA1_COLUMNS] for r in records]])
        class Book:
            def __getitem__(self, key):
                self_key = key
                assert self_key == 'KA1 mobilities 2024'
                return Sheet()
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as directory, patch('erasmusgravity.dashboard.refresh.load_workbook', return_value=Book()):
            source = Path(directory) / 'source.xlsx'
            source.write_bytes(b'fixture')
            cache = Path(directory) / 'cache'
            frame, diagnostics = read_mobility(source, 2024, cache)
            self.assertEqual(frame[PARTICIPANTS_COL].sum(), 7)
            self.assertIn('NA', set(frame.receiving_code))
            self.assertEqual(diagnostics[-1]['participants'], 7)
            cached, _ = read_mobility(source, 2024, cache)
            self.assertIn('NA', set(cached.receiving_code))
            self.assertEqual(cached[PARTICIPANTS_COL].sum(), 7)
            records[0]['Mobility Start Month'] = '2023-09'
            with self.assertRaisesRegex(ValueError, 'start year'):
                read_mobility(source, 2024, Path(directory) / 'other')

    def test_all_university_aggregations_retain_missing_endpoints_and_weights(self):
        records = [row(weight=3), row(weight=5), row(destination='NA - Namibia', weight=4,
                   **{'Receiving City': '', 'Sending City': None, 'Receiving Organization': '-'})]
        frame, _ = filter_he_studies(pd.DataFrame(records))
        tables = university_tables(frame)
        for table in tables.values():
            self.assertEqual(sum(r['flow_count'] for r in table), 12)
            self.assertTrue(any(r['receiving_code'] == 'NA' for r in table))
        self.assertEqual(max(r['flow_count'] for r in tables['uniUni']), 8)

    def test_refresh_keeps_missing_economic_observations_and_frozen_research(self):
        frame, _ = filter_he_studies(pd.DataFrame([row(weight=3), row(destination='NA - Namibia', weight=4)]))
        indicators = pd.DataFrame([{'country_code': code, 'country_name': code, 'gdp_pc_eur': 100,
                     'gdp_pc_current_usd_wb': 200, 'price_level_aic_eu27_2020_100': 90,
                     'net_earnings_eur': 50} for code in ['IT', 'FR']])
        grants = pd.DataFrame([{'country_code': 'IT', 'he_grants_eur': 1000,
                  'he_estimated_participants': 10, 'he_actual_participants': 8,
                  'he_grant_per_estimated_participant_eur': 100,
                  'he_grant_per_actual_participant_eur': 125}])
        source = {key: [{'original': key}] for key in RESEARCH_KEYS}
        source.update(countries=[{'code': 'IT', 'country': 'Italy'}, {'code': 'FR', 'country': 'France'}],
                      panelYears=[{'year': 2023, 'year_fe': .2}],
                      timeSeries=[{'s': 'IT', 'd': 'FR', 'dn': 'France', 'y': 2023, 'f': 10}],
                      orgFlowLevels={})
        before = deepcopy(source)
        with patch('erasmusgravity.dashboard.refresh.map_coordinates', return_value=[]):
            result = refresh_snapshot(source, frame, indicators, grants, 2024)
            repeated = refresh_snapshot(result, frame, indicators, grants, 2024)
        self.assertEqual(source, before)
        for key in RESEARCH_KEYS:
            self.assertEqual(result[key], source[key])
        self.assertEqual(sum(r['flow_count'] for r in result['flows']), 7)
        namibia = next(r for r in result['flows'] if r['receiving_code'] == 'NA')
        self.assertIsNone(namibia['receiver_gdp_pc_current_usd_wb'])
        self.assertEqual(sum(r['f'] for r in result['timeSeries'] if r['y'] == 2024), 3)
        self.assertEqual(result['timeSeries'], repeated['timeSeries'])
        self.assertEqual(result['timeSeries'][0], source['timeSeries'][0])
        self.assertEqual(result['explorationMeta']['indicatorYear'], 2024)


if __name__ == '__main__':
    unittest.main()
