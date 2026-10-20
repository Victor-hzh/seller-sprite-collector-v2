import json
import unittest
from pathlib import Path
from cleaning.build_dashboard_data import decision, rules_for


class FloorWasherScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cleaning = json.loads((Path(__file__).resolve().parents[1] / 'cleaning' / 'cleaning_rules.json').read_text(encoding='utf-8'))
        cls.rules = rules_for(cls.cleaning, 'DE', 'Wet-Dry-Floor-Washer')

    def test_important_floor_washers_in_both_sources(self):
        for title in ['Dreame H12 Pro Ultra Nass- und Trockensauger', 'Tineco Floor ONE Stretch S6', 'roborock F25 LT Wet Dry Vacuum Cleaner', 'Rowenta X-Clean 4', 'KÄRCHER FC 7 Bodenreiniger', 'MOVA X4 Pro Heißwasserwischen', 'dreame T16 Pro Heat-A', 'PHILIPS AquaTrio Nass-Trockensauger', 'Midea X10 Smart Nass-Trocken-Sauger']:
            self.assertTrue(decision({'asin': 'test', 'title': title}, self.rules)[0], title)

    def test_french_floor_washer_scope(self):
        rules = rules_for(self.cleaning, 'FR', 'Wet-Dry-Floor-Washer')
        included = [
            'Tineco Floor ONE S7 Stretch aspirateur laveur',
            'roborock F25 GT Aspirateur Balai Laveur',
            'MOVA M10 Aspirateur Laveur',
            'Rowenta X-Clean 4 Aspirateur laveur',
            'Bissell CrossWave aspirateur laveur',
            'EUREKA NEW400 aspirateur balai laveur',
            'JONR H2 aspirateur laveur eau chaude auto-nettoyante',
            'Dyson Pencilwash nettoyeur de sols',
        ]
        for title in included:
            with self.subTest(title=title):
                self.assertTrue(decision({'asin': 'test', 'title': title}, rules)[0])

        excluded = [
            'Kärcher WD 3 aspirateur eau et poussière 17 L',
            'Kärcher NT 22 aspirateur professionnel',
            'Einhell TC-VC 1812 aspirateur eau et poussière',
            'Scheppach DC500 aspirateur industriel',
            'Aspirateur à cendres chaudes 20 L',
            'Shampouineuse nettoyeur de tapis et canapés',
            'Ecovacs DEEBOT robot aspirateur laveur',
            'Dyson Cyclone V10 Submarine aspirateur sans fil',
        ]
        for title in excluded:
            with self.subTest(title=title):
                keep, reason = decision({'asin': 'test', 'title': title}, rules)
                self.assertFalse(keep)
                self.assertTrue(reason.startswith('title_pattern:'), reason)

        self.assertEqual(
            decision({'asin': 'test', 'title': 'Aspirateur balai sans fil 500 W'}, rules),
            (False, 'needs_review:household_floor_washer_not_confirmed'),
        )

    def test_tank_vacuums_do_not_enter_market(self):
        for title in ['KÄRCHER WD 2 Plus V-12/4/18/C', 'Bosch GAS18V-6LS', 'Bosch Allzwecksauger PAS15-200', 'Akku Nass-Trockensauger Werkstattsaugersmit 10L Staubbehälter', 'KWD 3 S V-17/4/20/F']:
            keep, reason = decision({'asin': 'test', 'title': title}, self.rules)
            self.assertFalse(keep, title)
            self.assertTrue(reason.startswith('title_pattern:'), reason)

    def test_ambiguous_model_needs_review(self):
        self.assertEqual(decision({'asin': 'test', 'title': 'Unknown Nass-Trockensauger'}, self.rules),
                         (False, 'needs_review:household_floor_washer_not_confirmed'))

    def test_shared_exclusions_and_category_scope(self):
        cases = [
            ('US', 'Robot-Vacuum', 'eufy RoboVac Hard Floor Cleaning Solution (2 Bottles)'),
            ('UK', 'Spot-Cleaner', 'Shark StainForce Dual-Formula Refill Cartridge, 2 x 500ml'),
            ('FR', 'Spot-Cleaner', 'Bissell Brosse pour Taches Tenaces, Noir, 15 cm'),
            ('IT', 'Robot-Vacuum', 'DREAME 4x Panni mocio di ricambio compatibili con X40'),
            ('IT', 'Spot-Cleaner', 'STANHOMEsDetergente Smacchiante Tappeti Carpet Cleaner, 500 ML'),
            ('JP', 'Spot-Cleaner', 'KEEPOW 8枚組 ケルヒャー用 消耗品 スチームクリーナー ハンドブラシ用'),
            ('UK', 'Wet-Dry-Floor-Washer', 'KÄRCHER WD 2 Plus Wet and Dry Vacuum Cleaner, 12 L'),
            ('US', 'Wet-Dry-Floor-Washer', 'Bissell Garage Pro Wall-Mounted Wet Dry Vacuum/Blower, 18P03'),
            ('US', 'Wet-Dry-Floor-Washer', 'BISSELL MultiClean Wet/Dry Garage and Auto Vacuum, 2035M'),
            ('US', 'Wet-Dry-Floor-Washer', 'Shark EveryMess 3-in-1 Wet/Dry Vac & Stain Eliminator'),
            ('US', 'Wet-Dry-Floor-Washer', 'Dyson V16 Piston Animal Submarine Cordless Wet and Dry Vacuum'),
            ('JP', 'Wet-Dry-Floor-Washer', '日動 業務用バキュームクリーナー２０Ｌ'),
            ('US', 'Spot-Cleaner', 'McCulloch MC1275 Heavy-Duty Steam Cleaner'),
        ]
        for market, category, title in cases:
            with self.subTest(market=market, category=category, title=title):
                keep, reason = decision({'asin': 'test', 'title': title}, rules_for(self.cleaning, market, category))
                self.assertFalse(keep)
                self.assertTrue(reason.startswith('title_pattern:'), reason)

    def test_scope_reviews_generic_handheld_but_keeps_mattress_vacuum(self):
        rules = rules_for(self.cleaning, 'US', 'Mite-Vacuum')
        self.assertEqual(decision({'asin': 'test', 'title': 'Cordless Car Handheld Vacuum'}, rules),
                         (False, 'needs_review:mite_vacuum_not_confirmed'))
        self.assertTrue(decision({'asin': 'test', 'title': 'FEPPO Mattress Vacuum Cleaner with UV-C'}, rules)[0])
        self.assertTrue(decision({'asin': 'test', 'title': 'JIGOO Aspiratore acaro per materassi'}, rules)[0])

    def test_consumables_included_with_machine_do_not_remove_machine(self):
        samples = [
            ('UK', 'Spot-Cleaner', 'Akitas X5 Spot Cleaner, Dual Water Tanks, Fabric Cleaning Solution Trial Size'),
            ('FR', 'Spot-Cleaner', 'BISSELL Revolution HydroSteam Nettoyeur Vapeur, Shampouineuse pour canapé'),
            ('ES', 'Stick-Vacuum', 'Aspiradora sin Cable con Cepillo para Mascotas'),
            ('US', 'Wet-Dry-Floor-Washer', 'Shark HydroVac Reveal Cordless Vacuum, Mop and Self-Clean'),
            ('US', 'Wet-Dry-Floor-Washer', 'Bissell CrossWave HydroSteam 3-in-1 Steam Mop'),
        ]
        for market, category, title in samples:
            with self.subTest(title=title):
                self.assertTrue(decision({'asin': 'test', 'title': title}, rules_for(self.cleaning, market, category))[0])

    def test_site_specific_scope_keeps_shared_exclusions(self):
        rules = rules_for(self.cleaning, 'DE', 'Wet-Dry-Floor-Washer')
        self.assertTrue(decision({'asin': 'test', 'title': 'KÄRCHER FC 7 Bodenreiniger'}, rules)[0])
        self.assertGreater(len(rules['exclude_title_patterns']), len(self.cleaning['groups']['DE/Wet-Dry-Floor-Washer']['exclude_title_patterns']))

    def test_site_requirement_can_replace_category_requirement(self):
        layers = {
            'default': {'exclude_title_patterns': ['global-part']},
            'categories': {'Example': {'require_title_patterns': ['category-machine']}},
            'groups': {'DE/Example': {'require_title_patterns': ['local-machine']}},
        }
        rules = rules_for(layers, 'DE', 'Example')
        self.assertEqual(rules['require_title_patterns'], ['local-machine'])
        self.assertEqual(rules['exclude_title_patterns'], ['global-part'])

    def test_explicit_keep_and_missing_title(self):
        rules = rules_for(self.cleaning, 'DE', 'Wet-Dry-Floor-Washer')
        self.assertTrue(decision({'asin': 'B0GJT26L7Z', 'title': ''}, rules)[0])
        self.assertEqual(decision({'asin': 'other', 'title': ''}, rules), (False, 'needs_review:missing_title'))


if __name__ == '__main__':
    unittest.main()
