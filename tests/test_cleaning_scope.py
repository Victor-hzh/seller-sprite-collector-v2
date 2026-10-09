import json
import unittest
from pathlib import Path
from tools.build_dashboard_data import decision


class FloorWasherScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads((Path(__file__).resolve().parents[1] / 'cleaning_rules.json').read_text(encoding='utf-8'))['groups']['DE/Wet-Dry-Floor-Washer']

    def test_important_floor_washers_in_both_sources(self):
        for title in ['Dreame H12 Pro Ultra Nass- und Trockensauger', 'Tineco Floor ONE Stretch S6', 'roborock F25 LT Wet Dry Vacuum Cleaner', 'Rowenta X-Clean 4', 'KÄRCHER FC 7 Bodenreiniger', 'MOVA X4 Pro Heißwasserwischen', 'dreame T16 Pro Heat-A', 'PHILIPS AquaTrio Nass-Trockensauger', 'Midea X10 Smart Nass-Trocken-Sauger']:
            self.assertTrue(decision({'asin': 'test', 'title': title}, self.rules)[0], title)

    def test_tank_vacuums_do_not_enter_market(self):
        for title in ['KÄRCHER WD 2 Plus V-12/4/18/C', 'Bosch GAS18V-6LS', 'Bosch Allzwecksauger PAS15-200', 'Akku Nass-Trockensauger Werkstattsaugersmit 10L Staubbehälter', 'KWD 3 S V-17/4/20/F']:
            keep, reason = decision({'asin': 'test', 'title': title}, self.rules)
            self.assertFalse(keep, title)
            self.assertTrue(reason.startswith('title_pattern:'), reason)

    def test_ambiguous_model_needs_review(self):
        self.assertEqual(decision({'asin': 'test', 'title': 'Unknown Nass-Trockensauger'}, self.rules),
                         (False, 'needs_review:household_floor_washer_not_confirmed'))


if __name__ == '__main__':
    unittest.main()
