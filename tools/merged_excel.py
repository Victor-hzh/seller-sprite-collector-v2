"""Preserve SellerSprite's OOXML template, fields, hyperlinks and product images.

SellerSprite uses non-standard drawing attributes. Editing ZIP/XML directly
avoids reserializing unrelated native workbook parts through another engine.
"""
from __future__ import annotations
import copy
import posixpath
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
try:
    from . import legacy_excel as excel
except ImportError:
    import legacy_excel as excel

M = excel.MAIN_NS
R = excel.REL_NS
P = excel.PACKAGE_REL_NS
X = 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
for prefix, ns in [('r', R), ('xdr', X), ('a', A), ('mc', 'http://schemas.openxmlformats.org/markup-compatibility/2006'), ('x14ac', 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac')]:
    ET.register_namespace(prefix, ns)


def resolve(part, target):
    return target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part), target))


def relpath(part):
    directory, name = posixpath.split(part)
    return f'{directory}/_rels/{name}.rels'


def xml(value):
    namespace = value.tag.split('}')[0].lstrip('{')
    if namespace in (M, P, CT):
        ET.register_namespace('', namespace)
    return ET.tostring(value, encoding='utf-8', xml_declaration=True)


def column(index):
    result = ''
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def load(path, market):
    with ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
    book = ET.fromstring(parts['xl/workbook.xml'])
    links = {r.attrib['Id']: r.attrib['Target'] for r in ET.fromstring(parts['xl/_rels/workbook.xml.rels'])}
    sheets = {s.attrib['name']: resolve('xl/workbook.xml', links[s.attrib[f'{{{R}}}id']]) for s in book.find(f'{{{M}}}sheets')}
    table = excel.read_xlsx_rows(path)
    name = market if market in sheets else next(n for n in sheets if n not in {'Brands', 'Sellers', 'Note'})
    main = sheets[name]
    tree = ET.fromstring(parts[main])
    headers = [str(v or '') for v in table[name][0]]
    row_by_asin = {}
    with ZipFile(path) as z:
        shared = excel.read_shared_strings(z)
    asin_index = headers.index('ASIN')
    for row in tree.findall(f'{{{M}}}sheetData/{{{M}}}row')[1:]:
        cells = {excel.column_index(c.attrib['r']): excel.cell_value(c, shared) for c in row}
        if cells.get(asin_index):
            row_by_asin[str(cells[asin_index]).upper()] = row
    relationships = ET.fromstring(parts.get(relpath(main), f'<Relationships xmlns="{P}"/>'))
    relationships_map = {r.attrib['Id']: r for r in relationships}
    hyperlinks_node = tree.find(f'{{{M}}}hyperlinks')
    hyperlinks = list(hyperlinks_node) if hyperlinks_node is not None else []
    images = {}
    drawing_link = next((r for r in relationships if r.attrib['Type'].endswith('/drawing')), None)
    if drawing_link is not None:
        drawing = resolve(main, drawing_link.attrib['Target'])
        image_rels = {r.attrib['Id']: resolve(drawing, r.attrib['Target']) for r in ET.fromstring(parts[relpath(drawing)])}
        for anchor in ET.fromstring(parts[drawing]):
            row = anchor.find(f'{{{X}}}from/{{{X}}}row')
            blip = anchor.find(f'.//{{{A}}}blip')
            if row is not None and blip is not None:
                image = image_rels.get(blip.attrib.get(f'{{{R}}}embed'))
                if image in parts:
                    images.setdefault(int(row.text) + 1, []).append((anchor, image, parts[image]))
    return dict(parts=parts, sheets=sheets, tree=tree, main=main, headers=headers, rows=row_by_asin,
                hyperlinks=hyperlinks, rels=relationships_map, images=images, table=table)


def write_table(tree, rows):
    data = tree.find(f'{{{M}}}sheetData')
    old_rows = list(data)
    prototypes = [copy.deepcopy(old_rows[0]), copy.deepcopy(old_rows[min(1, len(old_rows)-1)])]
    styles = [{excel.column_index(c.attrib['r']): c.attrib.get('s') for c in row} for row in prototypes]
    for row in list(data):
        data.remove(row)
    for row_number, values in enumerate(rows, 1):
        row = ET.SubElement(data, f'{{{M}}}row', {**prototypes[0 if row_number == 1 else 1].attrib, 'r': str(row_number)})
        row.attrib.pop('spans', None)
        for index, value in enumerate(values):
            attrs = {'r': f'{column(index+1)}{row_number}'}
            style = styles[0 if row_number == 1 else 1].get(index)
            if style is not None:
                attrs['s'] = style
            cell = ET.SubElement(row, f'{{{M}}}c', attrs)
            if value is None or value == '':
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                ET.SubElement(cell, f'{{{M}}}v').text = str(value)
            else:
                cell.set('t', 'inlineStr')
                text = ET.SubElement(ET.SubElement(cell, f'{{{M}}}is'), f'{{{M}}}t')
                text.text = str(value)
    end = f'{column(len(rows[0]))}{max(len(rows),1)}'
    tree.find(f'{{{M}}}dimension').set('ref', 'A1:' + end)
    auto = tree.find(f'{{{M}}}autoFilter')
    if auto is not None:
        auto.set('ref', 'A1:' + end)


def export_dataset(dataset, source_paths, output):
    sources = {name: load(path, dataset['marketplace']) for name, path in source_paths.items()}
    primary = sources[dataset['sourceFiles'][0]]
    if any(s['headers'] != primary['headers'] for s in sources.values()):
        raise excel.WorkbookReadError('来源Excel列结构不同，需要明确字段映射后再合并，未生成可能丢列的文件。')
    parts = dict(primary['parts'])
    tree = copy.deepcopy(primary['tree'])
    headers = primary['headers']
    products = dataset['products']
    rows = [headers] + [[p['rank'] if h == '#' else p['raw'].get(h) for h in headers] for p in products]
    write_table(tree, rows)
    for name in ('hyperlinks', 'drawing', 'extLst'):
        old = tree.find(f'{{{M}}}{name}')
        if old is not None:
            tree.remove(old)
    hyperlinks = ET.Element(f'{{{M}}}hyperlinks')
    relationships = ET.Element(f'{{{P}}}Relationships')
    drawing = ET.Element(f'{{{X}}}wsDr')
    drawing_rels = ET.Element(f'{{{P}}}Relationships')
    counter, image_counter = 0, 0
    types = ET.fromstring(parts['[Content_Types].xml'])
    for out_row, product in enumerate(products, 2):
        src = sources[product['selectedSourceFile']]
        original = src['rows'][product['asin']]
        old_row = int(original.attrib['r'])
        for link in src['hyperlinks']:
            ref = link.attrib['ref']
            if ref.endswith(str(old_row)) and re_cell_row(ref) == old_row:
                rel = src['rels'].get(link.attrib.get(f'{{{R}}}id'))
                if rel is None:
                    continue
                counter += 1
                rid = f'rId{counter}'
                relationships.append(ET.Element(f'{{{P}}}Relationship', {**rel.attrib, 'Id': rid}))
                hyperlinks.append(ET.Element(f'{{{M}}}hyperlink', {**link.attrib, 'ref': ref.rstrip('0123456789') + str(out_row), f'{{{R}}}id': rid}))
        for anchor, image_path, payload in src['images'].get(old_row, []):
            image_counter += 1
            new_anchor = copy.deepcopy(anchor)
            # Fix SellerSprite's invalid editAs value while retaining offsets.
            if new_anchor.attrib.get('editAs') == 'undefined':
                new_anchor.set('editAs', 'oneCell')
            for position in ('from', 'to'):
                row = new_anchor.find(f'{{{X}}}{position}/{{{X}}}row')
                if row is not None:
                    row.text = str(int(row.text) + out_row - old_row)
            pic = new_anchor.find(f'.//{{{X}}}cNvPr')
            if pic is not None:
                pic.set('id', str(image_counter))
                pic.set('name', f'Product {image_counter}')
            extension = Path(image_path).suffix.lower()
            media = f'xl/media/merged-product-{image_counter}{extension}'
            parts[media] = payload
            rid = f'rId{image_counter}'
            new_anchor.find(f'.//{{{A}}}blip').set(f'{{{R}}}embed', rid)
            drawing.append(new_anchor)
            drawing_rels.append(ET.Element(f'{{{P}}}Relationship', {'Id': rid, 'Type': R+'/image', 'Target': '../media/'+Path(media).name}))
            if not any(t.attrib.get('Extension') == extension[1:] for t in types):
                ET.SubElement(types, f'{{{CT}}}Default', Extension=extension[1:], ContentType='image/jpeg' if extension in ('.jpg','.jpeg') else 'image/'+extension[1:])
    if len(hyperlinks):
        tree.append(hyperlinks)
    if len(drawing):
        counter += 1
        rid = f'rId{counter}'
        relationships.append(ET.Element(f'{{{P}}}Relationship', {'Id':rid, 'Type':R+'/drawing','Target':'../drawings/merged-products.xml'}))
        ET.SubElement(tree, f'{{{M}}}drawing', {f'{{{R}}}id':rid})
        parts['xl/drawings/merged-products.xml'] = xml(drawing)
        parts['xl/drawings/_rels/merged-products.xml.rels'] = xml(drawing_rels)
        ET.SubElement(types, f'{{{CT}}}Override', PartName='/xl/drawings/merged-products.xml', ContentType='application/vnd.openxmlformats-officedocument.drawing+xml')
    parts[primary['main']] = xml(tree)
    parts[relpath(primary['main'])] = xml(relationships)
    for name, records in [('Brands', dataset['brands']), ('Sellers', dataset['sellers'])]:
        part = primary['sheets'][name]
        summary_tree = ET.fromstring(parts[part])
        old_links = summary_tree.find(f'{{{M}}}hyperlinks')
        if old_links is not None:
            summary_tree.remove(old_links)
        summary_headers = primary['table'][name][0]
        rows = [summary_headers] + [[r['name'], r['monthlySales'], r['monthlyRevenue'], None, None, r['averagePrice'], r['marketShare']] for r in records]
        write_table(summary_tree, rows)
        parts[part] = xml(summary_tree)
    parts['[Content_Types].xml'] = xml(types)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.xlsx.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as z:
        for name, value in parts.items():
            z.writestr(name, value)
    temporary.replace(output)
    return output


def re_cell_row(reference):
    return int(''.join(c for c in reference if c.isdigit()))
