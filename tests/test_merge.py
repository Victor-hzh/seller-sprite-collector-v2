import unittest
from tools.build_dashboard_data import PATTERN, merge_group


def source(node, products):
    return dict(marketplace='DE', category='Wet-Dry-Floor-Washer', date='2026-10-08', node=node,
                task={'url': 'https://www.amazon.de/' + node, 'category_label': '洗地机'},
                file=node + '.xlsx', top=50, products=products, sheetNames=['DE'])


def product(asin, revenue, brand='A', title='Floor washer'):
    return dict(asin=asin, monthlyRevenue=revenue, monthlySales=10, brand=brand,
                title=title, price=100, rank=5, sourceRank=5)


class MergeTests(unittest.TestCase):
    def test_union_dedup_clean_and_recompute(self):
        a = source('1', [product('B000000001', 100), product('B000000002', 50, title='Accessory')])
        b = source('2', [product('B000000001', 120), product('B000000003', 200, 'B')])
        result, audit = merge_group([a, b], {'exclude_asins': ['B000000002']})
        self.assertEqual([p['asin'] for p in result['products']], ['B000000003', 'B000000001'])
        self.assertEqual(sum(p['monthlyRevenue'] for p in result['products']), 300)
        self.assertEqual([p['rank'] for p in result['products']], [1, 2])
        self.assertEqual(result['products'][1]['sourceRank'], 5)
        self.assertEqual(len(result['products'][1]['sources']), 2)
        self.assertEqual(sum(b['monthlyRevenue'] for b in result['brands']), 300)
        self.assertAlmostEqual(sum(b['marketShare'] for b in result['brands']), 1)
        self.assertEqual({a['action'] for a in audit}, {'excluded', 'duplicate'})
        self.assertEqual(audit[-1]['differences']['monthlyRevenue'], [100, 120])

    def test_all_products_count_beyond_fifty(self):
        result, _ = merge_group([source('1', [product(str(i), i) for i in range(70)])], {})
        self.assertEqual(len(result['products']), 70)
        self.assertEqual(sum(b['monthlyRevenue'] for b in result['brands']), sum(range(70)))

    def test_keep_override_and_unknown_revenue(self):
        result, _ = merge_group([source('1', [product('A', None), product('B', 0)])],
                                {'keep_asins': ['A'], 'exclude_asins': ['A']})
        self.assertEqual([p['asin'] for p in result['products']], ['B', 'A'])
        self.assertEqual(result['missingRevenueCount'], 1)

    def test_both_filename_formats(self):
        for suffix, node in [('', None), ('_Node2077530031', '2077530031')]:
            match = PATTERN.fullmatch(f'BSR_DE_Wet-Dry-Floor-Washer{suffix}_Top50_2026-10-08.xlsx')
            self.assertEqual(match['category'], 'Wet-Dry-Floor-Washer')
            self.assertEqual(match['node'], node)


if __name__ == '__main__':
    unittest.main()
