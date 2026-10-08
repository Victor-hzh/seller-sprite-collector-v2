"""Merge source lists and apply auditable cleaning before dashboard aggregation."""
from __future__ import annotations

import argparse
import copy
import json
import re
from collections import defaultdict
from pathlib import Path

try:
    from . import legacy_excel as excel
except ImportError:
    import legacy_excel as excel

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r'^BSR_(?P<marketplace>[^_]+)_(?P<category>.+?)(?:_Node(?P<node>\d+))?_Top(?P<top>\d+)_(?P<date>\d{4}-\d{2}-\d{2})\.xlsx$', re.I)


def read_source(path, tasks):
    match = PATTERN.fullmatch(path.name)
    if not match:
        raise excel.WorkbookReadError(f'Unsupported source filename: {path.name}')
    meta = match.groupdict()
    market, category = meta['marketplace'].upper(), meta['category']
    candidates = [t for t in tasks if t['marketplace'] == market and t['category'] == category]
    task = next((t for t in candidates if str(t.get('node_id')) == meta['node']), None) if meta['node'] else next(iter(candidates), None)
    if task is None:
        raise excel.WorkbookReadError(f'No matching configured source: {path.name}')
    sheets = excel.read_xlsx_rows(path)
    main = market if market in sheets else next((n for n in sheets if n not in {'Brands', 'Sellers', 'Note'}), None)
    if main is None:
        raise excel.WorkbookReadError(f'No product sheet: {path.name}')
    products = []
    for row in excel.records_from_rows(sheets[main]):
        if not excel.text(row.get('ASIN')):
            continue
        product = excel.normalize_product(row)
        product['asin'] = product['asin'].strip().upper()
        product['sourceRank'] = product.get('rank')
        products.append(product)
    return dict(marketplace=market, category=category, date=meta['date'], task=task,
                node=meta['node'] or str(task.get('node_id', '')), file=path.name,
                top=int(meta['top']), products=products, sheetNames=list(sheets))


def decision(product, rules):
    asin = product['asin']
    if asin in {str(a).upper() for a in rules.get('keep_asins', [])}:
        return True, 'explicit_keep'
    if asin in {str(a).upper() for a in rules.get('exclude_asins', [])}:
        return False, 'explicit_exclude'
    for pattern in rules.get('exclude_title_patterns', []):
        if re.search(pattern, product.get('title', ''), re.I):
            return False, 'title_pattern:' + pattern
    return True, 'no_exclusion_rule'


def summaries(products, field):
    buckets = defaultdict(list)
    for product in products:
        buckets[product.get(field) or 'Unknown'].append(product)
    total = sum(p.get('monthlyRevenue') or 0 for p in products)
    result = []
    for name, items in buckets.items():
        revenue = sum(p.get('monthlyRevenue') or 0 for p in items)
        prices = [p['price'] for p in items if p.get('price') is not None]
        result.append(dict(name=name, monthlySales=sum(p.get('monthlySales') or 0 for p in items),
                           monthlyRevenue=revenue, annualSales=None, annualRevenue=None,
                           averagePrice=sum(prices)/len(prices) if prices else None,
                           marketShare=revenue/total if total else None))
    return sorted(result, key=lambda r: (-r['monthlyRevenue'], r['name']))


def merge_group(sources, rules):
    first = sources[0]
    selected, audit = {}, []
    for source in sources:
        for incoming in source['products']:
            keep, reason = decision(incoming, rules)
            evidence = dict(file=source['file'], nodeId=source['node'], sourceUrl=source['task']['url'], rank=incoming.get('rank'))
            if not keep:
                audit.append(dict(action='excluded', asin=incoming['asin'], title=incoming.get('title'), reason=reason, source=evidence))
                continue
            asin = incoming['asin']
            if asin not in selected:
                selected[asin] = copy.deepcopy(incoming)
                selected[asin]['sources'] = [evidence]
                continue
            chosen = selected[asin]
            chosen['sources'].append(evidence)
            differences = {key: [chosen.get(key), incoming.get(key)] for key in
                           ('monthlySales', 'monthlyRevenue', 'childSales', 'childRevenue', 'price')
                           if chosen.get(key) != incoming.get(key)}
            audit.append(dict(action='duplicate', asin=asin, source=evidence,
                              resolution='configured_source_priority', differences=differences))
    products = sorted(selected.values(), key=lambda p: (p.get('monthlyRevenue') is None, -(p.get('monthlyRevenue') or 0), p['asin']))
    for rank, product in enumerate(products, 1):
        product['rank'] = rank
    return {
        'id': f"{first['marketplace']}_{first['category']}_{first['date']}",
        'marketplace': first['marketplace'], 'category': first['category'],
        'categoryLabel': first['task'].get('category_label', first['category']),
        'listName': '清洗合并后的竞品销售额榜单', 'sourceUrl': first['task']['url'],
        'date': first['date'], 'topLimit': len(products), 'sourceFile': first['file'],
        'sourceFiles': [s['file'] for s in sources], 'sourceUrls': list(dict.fromkeys(s['task']['url'] for s in sources)),
        'currency': excel.CURRENCIES[first['marketplace']], 'sheetNames': first['sheetNames'],
        'products': products, 'brands': summaries(products, 'brand'), 'sellers': summaries(products, 'buyboxSeller'),
        'rankingBasis': 'monthlyRevenue', 'aggregationScope': 'all_cleaned_unique_asins',
        'rawProductCount': sum(len(s['products']) for s in sources),
        'cleanedProductCount': len(products), 'missingRevenueCount': sum(p.get('monthlyRevenue') is None for p in products),
    }, audit


def build_payload(files, tasks, cleaning):
    grouped, errors = defaultdict(list), []
    priority = {t['id']: index for index, t in enumerate(tasks)}
    for path in files:
        try:
            source = read_source(path, tasks)
            grouped[(source['marketplace'], source['category'], source['date'])].append(source)
        except (excel.WorkbookReadError, ValueError, OSError) as exc:
            errors.append(dict(file=path.name, error=str(exc)))
    datasets, audit = [], []
    for (market, category, date), sources in sorted(grouped.items()):
        # Prefer explicitly named Node files to legacy files of the same node.
        sources.sort(key=lambda s: (priority[s['task']['id']], '_Node' not in s['file'], s['file']))
        rules = dict(cleaning.get('default', {}))
        rules.update(cleaning.get('groups', {}).get(f'{market}/{category}', {}))
        dataset, events = merge_group(sources, rules)
        expected_nodes = {str(t.get('node_id')) for t in tasks if t.get('enabled', True) and t['marketplace'] == market and t['category'] == category}
        dataset['missingSourceNodes'] = sorted(expected_nodes - {s['node'] for s in sources})
        dataset['sourceCoverageComplete'] = not dataset['missingSourceNodes']
        datasets.append(dataset)
        audit.extend(dict(marketplace=market, category=category, date=date, **event) for event in events)
    expected = {}
    loaded = {(d['marketplace'], d['category']) for d in datasets}
    for task in tasks:
        key = (task['marketplace'], task['category'])
        expected.setdefault(key, dict(id=task['id'], marketplace=key[0], category=key[1], categoryLabel=task.get('category_label'),
                                     listName=task.get('list_name'), sourceUrl=task['url'], available=key in loaded))
    excel.EXCHANGE_RATES_PATH = ROOT / 'tools' / 'exchange_rates.json'
    payload = dict(schemaVersion=2, generatedAt=excel.utc_now(), exchangeRates=excel.load_exchange_rates(),
                   expectedDatasetCount=len(expected), loadedDatasetCount=len(loaded), expectedDatasets=list(expected.values()),
                   opportunityModel={'minimumMarketplaces': 2, 'weights': {'marketSize': .45, 'salesDemand': .25, 'growth': .15, 'entryFriendliness': .15},
                                     'formula': '市场规模45% + 销量需求25% + 增长15% + 进入友好度15%', 'note': '多来源清洗去重后的竞品样本，不代表全市场。'},
                   datasets=sorted(datasets, key=lambda d: (d['date'], d['marketplace'], d['category']), reverse=True), errors=errors)
    return payload, dict(generatedAt=payload['generatedAt'], duplicatePolicy='configured_source_priority', events=audit, errors=errors)


def main(argv=None):
    parser = argparse.ArgumentParser(description='合并榜单、清洗 ASIN 并生成看板数据和审计记录')
    parser.add_argument('inputs', nargs='*', default=[str(ROOT / 'data/source')])
    parser.add_argument('--tasks', default=str(ROOT / 'tasks_v2.json'))
    parser.add_argument('--rules', default=str(ROOT / 'cleaning_rules.json'))
    parser.add_argument('--output', default=str(ROOT / 'data/dashboard-data.json'))
    parser.add_argument('--audit', default=str(ROOT / 'data/cleaning-audit.json'))
    args = parser.parse_args(argv)
    files = excel.find_files(args.inputs)
    if not files:
        parser.error('没有找到 Excel 文件')
    tasks = json.loads(Path(args.tasks).read_text(encoding='utf-8'))['tasks']
    cleaning = json.loads(Path(args.rules).read_text(encoding='utf-8'))
    payload, audit = build_payload(files, tasks, cleaning)
    if payload['errors']:
        print(json.dumps(payload['errors'], ensure_ascii=False, indent=2))
        return 1  # Never replace good dashboard data with a partial parse.
    for target, value in ((args.output, payload), (args.audit, audit)):
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)
    print(f"生成 {len(payload['datasets'])} 个历史数据集；审计事件 {len(audit['events'])} 条。")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
