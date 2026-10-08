from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = BASE_DIR / "data" / "source"
DEFAULT_OUTPUT = BASE_DIR / "output" / "dashboard-data.json"
TASKS_PATH = (
    BASE_DIR / "tasks_all_30.json"
    if (BASE_DIR / "tasks_all_30.json").exists()
    else BASE_DIR / "tasks.json"
)
EXCHANGE_RATES_PATH = BASE_DIR / "exchange_rates.json"

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS, "p": PACKAGE_REL_NS}

FILE_PATTERN = re.compile(
    r"^BSR_(?P<marketplace>[^_]+)_(?P<category>.+)_Top(?P<top>\d+)_"
    r"(?P<date>\d{4}-\d{2}-\d{2})\.xlsx$",
    re.IGNORECASE,
)

CURRENCIES = {
    "US": {"code": "USD", "symbol": "$"},
    "UK": {"code": "GBP", "symbol": "£"},
    "DE": {"code": "EUR", "symbol": "€"},
    "FR": {"code": "EUR", "symbol": "€"},
    "IT": {"code": "EUR", "symbol": "€"},
    "ES": {"code": "EUR", "symbol": "€"},
    "JP": {"code": "JPY", "symbol": "¥"},
}


class WorkbookReadError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def column_index(cell_reference: str) -> int:
    match = re.match(r"[A-Z]+", cell_reference.upper())
    if not match:
        return 0
    value = 0
    for character in match.group(0):
        value = value * 26 + ord(character) - 64
    return value - 1


def read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall("m:si", NS)
    ]


def cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    inline = cell.find("m:is", NS)
    if inline is not None:
        return "".join(node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t"))
    value_node = cell.find("m:v", NS)
    if value_node is None or value_node.text is None:
        return None
    raw_value = value_node.text
    if cell_type == "s":
        return shared_strings[int(raw_value)]
    if cell_type == "b":
        return raw_value == "1"
    if cell_type in {"str", "e"}:
        return raw_value
    try:
        return float(raw_value) if any(marker in raw_value for marker in ".eE") else int(raw_value)
    except ValueError:
        return raw_value


def read_xlsx_rows(path: Path) -> dict[str, list[list[Any]]]:
    """Read cell data without loading SellerSprite's non-standard drawing XML."""
    try:
        archive = ZipFile(path)
    except (BadZipFile, OSError) as exc:
        raise WorkbookReadError(f"无法打开 Excel：{path.name}") from exc
    with archive:
        try:
            shared_strings = read_shared_strings(archive)
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relationship_map = {
                relationship.attrib["Id"]: relationship.attrib["Target"]
                for relationship in relationships
            }
            sheets: dict[str, list[list[Any]]] = {}
            sheets_node = workbook.find("m:sheets", NS)
            if sheets_node is None:
                raise WorkbookReadError(f"Excel 中没有工作表：{path.name}")
            for sheet in sheets_node:
                title = sheet.attrib["name"]
                relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]
                target = relationship_map[relationship_id]
                sheet_path = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
                root = ET.fromstring(archive.read(sheet_path))
                rows: list[list[Any]] = []
                for row in root.findall(".//m:sheetData/m:row", NS):
                    indexed_values: dict[int, Any] = {}
                    for cell in row.findall("m:c", NS):
                        index = column_index(cell.attrib.get("r", "A1"))
                        indexed_values[index] = cell_value(cell, shared_strings)
                    if indexed_values:
                        width = max(indexed_values) + 1
                        rows.append([indexed_values.get(index) for index in range(width)])
                sheets[title] = rows
            return sheets
        except (ET.ParseError, KeyError, IndexError) as exc:
            raise WorkbookReadError(f"无法读取 Excel 单元格：{path.name}") from exc


def records_from_rows(rows: list[list[Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    headers = [str(value or "").strip() for value in rows[0]]
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        record = {
            header: row[index] if index < len(row) else None
            for index, header in enumerate(headers)
            if header
        }
        if any(value not in (None, "") for value in record.values()):
            records.append(record)
    return records


def first_value(record: dict[str, Any], *names: str, prefix: str | None = None) -> Any:
    for name in names:
        if name in record:
            return record[name]
    if prefix:
        for key, value in record.items():
            if key.startswith(prefix):
                return value
    return None


def number(value: Any) -> float | int | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return value
    normalized = str(value).strip().replace(",", "").replace("%", "")
    try:
        parsed = float(normalized)
        return parsed / 100 if "%" in str(value) else int(parsed) if parsed.is_integer() else parsed
    except ValueError:
        return None


def integer(value: Any) -> int | None:
    parsed = number(value)
    return int(parsed) if parsed is not None else None


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def yes(value: Any) -> bool:
    return text(value).lower() in {"y", "yes", "true", "1", "是"}


def short_product_title(brand: str, title: str) -> str:
    """Create a compact, stable label while retaining the source title in raw data."""
    clean = re.sub(r"\s+", " ", title).strip(" ,|-/")
    clean_brand = brand.strip() or "Unknown"
    remainder = re.sub(
        rf"^\s*{re.escape(clean_brand)}(?:\s+|[-–—,:|]+)",
        "",
        clean,
        count=1,
        flags=re.IGNORECASE,
    )

    model_candidates = re.findall(
        r"\b(?=[A-Z0-9-]{3,}\b)(?=[A-Z0-9-]*[A-Z])(?=[A-Z0-9-]*\d)[A-Z0-9-]+\b",
        clean.upper(),
    )
    model = next(
        (
            item
            for item in model_candidates
            if item not in {"2-IN-1", "3-IN-1", "4-IN-1", "5-IN-1", "6-IN-1"}
            and not re.fullmatch(r"\d+(?:V|W|KPA|PA|ML|L|OZ|LB|FT)", item)
        ),
        "",
    )

    configuration_patterns = [
        r"\b\d+(?:\.\d+)?\s?(?:V|W|KPA|PA|ML|L|OZ|LB|LBS|FT)\b",
        r"\b\d+[- ]IN[- ]1\b",
        r"\b(?:CORDLESS|CORDED|HANDHELD|PORTABLE|BAGLESS|WET.?DRY|PET|HEPA)\b",
    ]
    configurations: list[str] = []
    for pattern in configuration_patterns:
        for match in re.findall(pattern, clean, flags=re.IGNORECASE):
            value = match if isinstance(match, str) else match[0]
            normalized = re.sub(r"\s+", " ", value).strip()
            if normalized.upper() not in {item.upper() for item in configurations}:
                configurations.append(normalized)
    configurations = configurations[:3]

    descriptor = re.split(r"[,|;:]", remainder, maxsplit=1)[0].strip()
    descriptor_words = descriptor.split()
    if len(descriptor_words) > 7:
        descriptor = " ".join(descriptor_words[:7])

    parts = [clean_brand]
    if model and model.lower() not in clean_brand.lower():
        parts.append(model)
    if descriptor and descriptor.lower() not in " ".join(parts).lower():
        parts.append(descriptor)
    for item in configurations:
        if item.lower() not in " ".join(parts).lower():
            parts.append(item)
    result = " · ".join(parts)
    return result[:96].rstrip(" ,|-/·") or clean[:96]


def normalize_product(record: dict[str, Any]) -> dict[str, Any]:
    brand = text(record.get("品牌")) or "Unknown"
    title = text(record.get("商品标题"))
    return {
        "rank": integer(record.get("#")),
        "asin": text(record.get("ASIN")),
        "parentAsin": text(record.get("父ASIN")),
        "sku": text(record.get("SKU")),
        "brand": brand,
        "brandUrl": text(record.get("品牌链接")),
        "title": title,
        "shortTitle": short_product_title(brand, title),
        "features": text(record.get("产品卖点")),
        "detailParameters": text(record.get("详细参数")),
        "productUrl": text(record.get("商品详情页链接")),
        "imageUrl": text(record.get("商品主图")),
        "categoryPath": text(record.get("类目路径")),
        "mainCategory": text(record.get("大类目")),
        "mainBsr": integer(record.get("大类BSR")),
        "mainBsrChange": integer(record.get("大类BSR增长数")),
        "mainBsrChangeRate": number(record.get("大类BSR增长率")),
        "subCategory": text(record.get("小类目")),
        "subBsr": integer(record.get("小类BSR")),
        "monthlySales": integer(record.get("月销量")),
        "monthlySalesGrowth": number(record.get("月销量增长率")),
        "monthlyRevenue": number(first_value(record, prefix="月销售额(")),
        "childSales": number(record.get("子体销量")),
        "childRevenue": number(first_value(record, prefix="子体销售额(")),
        "variationCount": integer(record.get("变体数")),
        "price": number(first_value(record, prefix="价格(")),
        "primePrice": number(first_value(record, prefix="Prime价格(")),
        "coupon": text(record.get("Coupon")),
        "questionCount": integer(record.get("Q&A数")),
        "reviewCount": integer(record.get("评分数")),
        "newReviewCount": integer(record.get("月新增评分数")),
        "rating": number(record.get("评分")),
        "reviewRate": number(record.get("留评率")),
        "fbaFee": number(first_value(record, prefix="FBA(")),
        "grossMargin": number(record.get("毛利率")),
        "grade": text(record.get("评级")),
        "listedDate": text(record.get("上架时间")),
        "listingDays": integer(record.get("上架天数")),
        "fulfillment": text(record.get("配送方式")),
        "deliveryTime": text(record.get("配送时长")),
        "primeDeliveryTime": text(record.get("Prime配送时长")),
        "buyerShipping": number(first_value(record, prefix="买家运费(")),
        "lqs": number(record.get("LQS")),
        "sellerCount": integer(record.get("卖家数")),
        "buyboxSeller": text(record.get("Buybox卖家")),
        "buyboxType": text(record.get("BuyBox类型")),
        "sellerOrigin": text(record.get("卖家所属地")) or "Unknown",
        "sellerInfo": text(record.get("卖家信息")),
        "sellerHome": text(record.get("卖家首页")),
        "badges": {
            "bestSeller": yes(record.get("Best Seller标识")),
            "amazonChoice": yes(record.get("Amazon's Choice")),
            "cpf": yes(record.get("CPF绿标")),
            "newRelease": yes(record.get("New Release标识")),
        },
        "content": {
            "aPlus": yes(record.get("A+页面")),
            "video": yes(record.get("视频介绍")),
            "spAds": yes(record.get("SP广告")),
            "brandStory": yes(record.get("品牌故事")),
            "brandAds": yes(record.get("品牌广告")),
            "deal": yes(record.get("秒杀")),
            "acKeyword": text(record.get("AC关键词")),
        },
        "productWeight": text(record.get("商品重量")),
        "productWeightMetric": text(record.get("商品重量（单位换算）")),
        "productDimensions": text(record.get("商品尺寸")),
        "productDimensionsMetric": text(record.get("商品尺寸（单位换算）")),
        "packageWeight": text(record.get("包装重量")),
        "packageWeightMetric": text(record.get("包装重量（单位换算）")),
        "packageDimensions": text(record.get("包装尺寸")),
        "packageDimensionsMetric": text(record.get("包装尺寸（单位换算）")),
        "packageSizeTier": text(record.get("包装尺寸分段")),
        "raw": {key: value for key, value in record.items() if value not in (None, "")},
    }


def normalize_summary(record: dict[str, Any], label_field: str) -> dict[str, Any]:
    return {
        "name": text(record.get(label_field)) or "Unknown",
        "monthlySales": integer(record.get("月销量")),
        "monthlyRevenue": number(first_value(record, prefix="月销售额(")),
        "annualSales": integer(record.get("近1年销量")),
        "annualRevenue": number(first_value(record, prefix="近一年销售额(")),
        "averagePrice": number(first_value(record, prefix="平均价格(")),
        "marketShare": number(record.get("市场份额")),
    }


def load_tasks() -> list[dict[str, Any]]:
    payload = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    return payload.get("tasks", [])


def load_exchange_rates() -> dict[str, Any]:
    if not EXCHANGE_RATES_PATH.exists():
        raise WorkbookReadError("缺少汇率配置文件 exchange_rates.json")
    payload = json.loads(EXCHANGE_RATES_PATH.read_text(encoding="utf-8"))
    rates = payload.get("cnyPerUnit", {})
    for code in {currency["code"] for currency in CURRENCIES.values()}:
        if number(rates.get(code)) is None:
            raise WorkbookReadError(f"汇率配置缺少 {code} → CNY")
    return payload


def find_files(inputs: Iterable[str]) -> list[Path]:
    files: set[Path] = set()
    for raw_input in inputs:
        path = Path(raw_input).expanduser().resolve()
        if path.is_file() and path.suffix.lower() == ".xlsx":
            files.add(path)
        elif path.is_dir():
            files.update(candidate.resolve() for candidate in path.rglob("*.xlsx"))
    return sorted(files)


def task_for_dataset(tasks: list[dict[str, Any]], marketplace: str, category: str) -> dict[str, Any] | None:
    for task in tasks:
        if task.get("marketplace") == marketplace and task.get("category") == category:
            return task
    return None


def build_dataset(path: Path, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    match = FILE_PATTERN.match(path.name)
    if not match:
        raise WorkbookReadError(
            f"文件名不符合 BSR_站点_品类_Top数量_日期.xlsx：{path.name}"
        )
    metadata = match.groupdict()
    marketplace = metadata["marketplace"].upper()
    category = metadata["category"]
    sheets = read_xlsx_rows(path)
    main_sheet_name = marketplace if marketplace in sheets else next(
        (name for name in sheets if name not in {"Brands", "Sellers", "Note"}),
        None,
    )
    if main_sheet_name is None:
        raise WorkbookReadError(f"未找到主商品表：{path.name}")
    products = [
        normalize_product(record)
        for record in records_from_rows(sheets.get(main_sheet_name, []))
        if text(record.get("ASIN"))
    ]
    products.sort(key=lambda product: product.get("rank") or 999999)
    brands = [
        normalize_summary(record, "品牌")
        for record in records_from_rows(sheets.get("Brands", []))
        if text(record.get("品牌"))
    ]
    sellers = [
        normalize_summary(record, "卖家")
        for record in records_from_rows(sheets.get("Sellers", []))
        if text(record.get("卖家"))
    ]
    task = task_for_dataset(tasks, marketplace, category) or {}
    currency = CURRENCIES.get(marketplace, {"code": "", "symbol": ""})
    return {
        "id": f"{marketplace}_{category}_{metadata['date']}",
        "marketplace": marketplace,
        "category": category,
        "categoryLabel": task.get("category_label", category),
        "listName": task.get("list_name", products[0].get("subCategory", category) if products else category),
        "sourceUrl": task.get("url", ""),
        "date": metadata["date"],
        "topLimit": int(metadata["top"]),
        "sourceFile": path.name,
        "currency": currency,
        "sheetNames": list(sheets.keys()),
        "products": products,
        "brands": brands,
        "sellers": sellers,
    }


def build_payload(files: list[Path]) -> dict[str, Any]:
    tasks = load_tasks()
    exchange_rates = load_exchange_rates()
    datasets: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in files:
        try:
            datasets.append(build_dataset(path, tasks))
        except WorkbookReadError as exc:
            errors.append({"file": path.name, "error": str(exc)})
    datasets.sort(key=lambda item: (item["date"], item["marketplace"], item["category"]), reverse=True)
    loaded_keys = {(item["marketplace"], item["category"]) for item in datasets}
    expected = [
        {
            "id": task.get("id"),
            "marketplace": task.get("marketplace"),
            "category": task.get("category"),
            "categoryLabel": task.get("category_label"),
            "listName": task.get("list_name"),
            "sourceUrl": task.get("url"),
            "available": (task.get("marketplace"), task.get("category")) in loaded_keys,
        }
        for task in tasks
    ]
    return {
        "schemaVersion": 2,
        "generatedAt": utc_now(),
        "exchangeRates": exchange_rates,
        "opportunityModel": {
            "minimumMarketplaces": 2,
            "weights": {
                "marketSize": 0.45,
                "salesDemand": 0.25,
                "growth": 0.15,
                "entryFriendliness": 0.15,
            },
            "formula": "市场规模45% + 销量需求25% + 增长15% + 进入友好度15%",
            "note": "同品类至少接入2个站点后计算；所有金额先换算为人民币。",
        },
        "expectedDatasetCount": len(expected),
        "loadedDatasetCount": len(loaded_keys),
        "expectedDatasets": expected,
        "datasets": datasets,
        "errors": errors,
    }


def merge_existing_payload(payload: dict[str, Any], existing_path: Path) -> dict[str, Any]:
    if not existing_path.exists():
        return payload
    try:
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkbookReadError(f"无法读取已有看板JSON：{existing_path}") from exc
    existing_datasets = existing.get("datasets")
    if not isinstance(existing_datasets, list):
        raise WorkbookReadError(f"已有看板JSON缺少 datasets：{existing_path}")

    merged_by_id = {
        str(item.get("id")): item
        for item in existing_datasets
        if isinstance(item, dict) and item.get("id")
    }
    for item in payload["datasets"]:
        merged_by_id[item["id"]] = item
    payload["datasets"] = sorted(
        merged_by_id.values(),
        key=lambda item: (item["date"], item["marketplace"], item["category"]),
        reverse=True,
    )
    loaded_keys = {
        (item["marketplace"], item["category"])
        for item in payload["datasets"]
    }
    payload["loadedDatasetCount"] = len(loaded_keys)
    for item in payload["expectedDatasets"]:
        item["available"] = (item.get("marketplace"), item.get("category")) in loaded_keys
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将卖家精灵 Excel 转换为看板统一数据。")
    parser.add_argument(
        "inputs",
        nargs="*",
        default=[str(DEFAULT_SOURCE)],
        help="Excel 文件或包含 Excel 的文件夹，可传入多个。",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="输出 JSON 路径。")
    parser.add_argument(
        "--merge-existing",
        help="保留已有JSON中的历史日期；同一榜单同一日期以本次Excel为准。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = find_files(args.inputs)
    if not files:
        raise SystemExit("未找到可读取的 .xlsx 数据源。")
    payload = build_payload(files)
    if args.merge_existing:
        payload = merge_existing_payload(
            payload,
            Path(args.merge_existing).expanduser().resolve(),
        )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"看板数据已生成：{output} | "
        f"成功 {len(payload['datasets'])} 份 | 失败 {len(payload['errors'])} 份"
    )
    return 1 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

