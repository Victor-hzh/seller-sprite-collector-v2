from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app_paths import BASE_DIR
RUNTIME_DIR = BASE_DIR / "runtime"
ERROR_DIR = RUNTIME_DIR / "errors"
STATE_PATH = RUNTIME_DIR / "progress.json"
LOG_PATH = RUNTIME_DIR / "collector.log"


class CollectorError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_directories() -> None:
    for path in (RUNTIME_DIR, ERROR_DIR):
        path.mkdir(parents=True, exist_ok=True)


def source_run_dir(config: dict[str, Any], run_date: str) -> Path:
    configured = Path(config.get("storage", {}).get("source_dir", "data/source"))
    source_root = configured if configured.is_absolute() else BASE_DIR / configured
    run_dir = source_root / run_date
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH, encoding="utf-8")],
    )


def atomic_write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CollectorError(f"找不到配置文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise CollectorError(f"配置文件不是有效 JSON：{exc}") from exc


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"updated_at": utc_now(), "tasks": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        shutil.copy2(STATE_PATH, STATE_PATH.with_name(f"progress-broken-{int(time.time())}.json"))
        return {"updated_at": utc_now(), "tasks": {}}


def save_task_state(state: dict[str, Any], task_id: str, status: str, **extra: Any) -> None:
    state.setdefault("tasks", {})[task_id] = {
        **state.get("tasks", {}).get(task_id, {}),
        "status": status,
        "updated_at": utc_now(),
        **extra,
    }
    state["updated_at"] = utc_now()
    atomic_write_json(STATE_PATH, state)


def upsert_task_result(results: list[dict[str, Any]], result: dict[str, Any]) -> None:
    for index, existing in enumerate(results):
        if existing.get("id") == result.get("id"):
            results[index] = result
            return
    results.append(result)


def validate_config(config: dict[str, Any], allow_placeholders: bool = False) -> None:
    tasks = config.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise CollectorError("配置中至少需要一个 tasks 任务。")
    selectors = config.get("selectors", {})
    for key in ("entry", "export"):
        values = selectors.get(key)
        if not isinstance(values, list) or not values:
            raise CollectorError(f"selectors.{key} 至少需要一个定位规则。")
        if not allow_placeholders and any("REPLACE_" in str(item) for item in values):
            raise CollectorError("卖家精灵按钮定位尚未接入。请提供操作截图后更新 config.json。")
    seen_ids = set()
    seen_outputs = set()
    for task in tasks:
        for key in ("id", "marketplace", "category", "url"):
            if not str(task.get(key, "")).strip():
                raise CollectorError(f"任务缺少字段：{key}")
        if not allow_placeholders and "PASTE_" in task["url"]:
            raise CollectorError("请先在 config.json 中粘贴一个亚马逊榜单链接。")
        if task["id"] in seen_ids:
            raise CollectorError(f"重复任务 ID：{task['id']}")
        seen_ids.add(task["id"])
        output_key = (task["marketplace"], task["category"], task.get("node_id", ""), task.get("target_rows", 50))
        if task.get("enabled", True) and output_key in seen_outputs:
            raise CollectorError(f"任务输出文件会覆盖：{task['id']}")
        if task.get("enabled", True):
            seen_outputs.add(output_key)


def load_tasks_file(config: dict[str, Any], config_path: Path) -> None:
    tasks_file = config.get("tasks_file")
    if not tasks_file:
        return
    tasks_path = Path(str(tasks_file))
    if not tasks_path.is_absolute():
        tasks_path = config_path.parent / tasks_path
    payload = load_json(tasks_path)
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise CollectorError(f"任务文件缺少 tasks 数组：{tasks_path}")
    config["tasks"] = tasks


def clean_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-") or "unknown"


def resolve_scope(page: Any, url_fragment: str) -> Any:
    if not url_fragment:
        return page
    for frame in page.frames:
        if url_fragment in frame.url:
            return frame
    raise CollectorError(f"没有找到包含 {url_fragment!r} 的插件页面或 iframe。")


def click_first(scope: Any, selectors: Iterable[str], timeout_ms: int) -> str:
    last_error: Exception | None = None
    for selector in selectors:
        try:
            locator = scope.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout_ms)
            locator.click(timeout=timeout_ms)
            return selector
        except Exception as exc:
            last_error = exc
    raise CollectorError(f"没有找到可点击按钮。最后一次错误：{last_error}")


def click_optional(scope: Any, selectors: Iterable[str], timeout_ms: int = 3000) -> str | None:
    """Click the first visible optional element, or continue when it is absent."""
    for selector in selectors:
        try:
            locator = scope.locator(selector).first
            if locator.is_visible(timeout=timeout_ms):
                locator.click(timeout=timeout_ms)
                return selector
        except Exception:
            continue
    return None


def click_rightmost_match(page: Any, selectors: Iterable[str], timeout_ms: int) -> str:
    """Click the visible matching element closest to the browser's right edge.

    SellerSprite adds its floating launcher inside the Amazon page. The page can
    contain other SellerSprite text, so using the first text match is unsafe.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        best: tuple[float, Any, str] | None = None
        for frame in page.frames:
            for selector in selectors:
                try:
                    matches = frame.locator(selector)
                    for index in range(min(matches.count(), 20)):
                        locator = matches.nth(index)
                        if not locator.is_visible():
                            continue
                        box = locator.bounding_box()
                        if not box or box["width"] < 8 or box["height"] < 8:
                            continue
                        right_edge = float(box["x"] + box["width"])
                        if best is None or right_edge > best[0]:
                            best = (right_edge, locator, selector)
                except Exception as exc:
                    last_error = exc
        if best is not None:
            best[1].click(timeout=min(timeout_ms, 10000))
            return best[2]
        page.wait_for_timeout(250)
    raise CollectorError(f"没有找到页面右侧的卖家精灵悬浮入口。最后一次错误：{last_error}")


def visible_match_in_frames(page: Any, selectors: Iterable[str]) -> str | None:
    for frame in page.frames:
        for selector in selectors:
            try:
                if frame.locator(selector).first.is_visible():
                    return selector
            except Exception:
                continue
    return None


def wait_for_visible_marker(page: Any, selectors: Iterable[str], timeout_ms: int, label: str) -> str:
    selectors = list(selectors)
    if not selectors:
        raise CollectorError(f"配置中缺少{label}定位规则。")
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        selector = visible_match_in_frames(page, selectors)
        if selector:
            return selector
        page.wait_for_timeout(250)
    raise CollectorError(f"等待{label}超时，准备截图并重试。")


def click_first_in_frames(page: Any, selectors: Iterable[str], timeout_ms: int, label: str) -> str:
    deadline = time.monotonic() + timeout_ms / 1000
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        for frame in page.frames:
            for selector in selectors:
                try:
                    locator = frame.locator(selector).first
                    if locator.is_visible():
                        locator.click(timeout=min(timeout_ms, 10000))
                        return selector
                except Exception as exc:
                    last_error = exc
        page.wait_for_timeout(250)
    raise CollectorError(f"没有找到可点击的{label}。最后一次错误：{last_error}")


def wait_for_plugin_loading(page: Any, selectors: Iterable[str], timeout_ms: int) -> None:
    """Wait for SellerSprite's loading message to appear, then disappear."""
    selectors = list(selectors)
    if not selectors:
        raise CollectorError("配置中缺少卖家精灵加载状态定位规则。")

    appear_deadline = time.monotonic() + min(timeout_ms, 15000) / 1000
    visible_selector: str | None = None
    while time.monotonic() < appear_deadline:
        visible_selector = visible_match_in_frames(page, selectors)
        if visible_selector:
            break
        page.wait_for_timeout(250)
    if not visible_selector:
        raise CollectorError("点击卖家精灵后，没有检测到插件查询中的加载界面。")

    finish_deadline = time.monotonic() + timeout_ms / 1000
    hidden_checks = 0
    while time.monotonic() < finish_deadline:
        if visible_match_in_frames(page, selectors):
            hidden_checks = 0
        else:
            hidden_checks += 1
            if hidden_checks >= 2:
                return
        page.wait_for_timeout(500)
    raise CollectorError("卖家精灵数据加载超过最长等待时间，准备截图并重试。")


def count_rows(scope: Any, selectors: Iterable[str]) -> int | None:
    for selector in selectors:
        try:
            count = scope.locator(selector).count()
            if count:
                return count
        except Exception:
            continue
    return None


def validate_download(path: Path, expected_suffix: str | None = None) -> None:
    if not path.exists():
        raise CollectorError("浏览器提示下载完成，但目标文件不存在。")
    if path.stat().st_size < 1024:
        raise CollectorError(f"下载文件过小，可能不完整：{path.name}")
    suffix = (expected_suffix or path.suffix).lower()
    if suffix == ".xlsx" and not zipfile.is_zipfile(path):
        raise CollectorError(f"Excel 文件结构损坏：{path.name}")
    if suffix not in {".xlsx", ".csv"}:
        raise CollectorError(f"暂不支持的下载格式：{suffix}")


COLUMN_ALIASES = {
    "asin": {"asin", "asin码"},
    "rank": {"排名", "rank", "bsr", "bsr排名", "自然排名"},
    "title": {"标题", "产品标题", "商品标题", "title", "product title"},
    "brand": {"品牌", "brand"},
    "price": {"价格", "price", "售价"},
    "rating": {"评分", "rating", "星级"},
    "reviews": {"评论数", "评价数", "reviews", "review count"},
    "monthly_sales": {"月销量", "monthly sales", "月销售量"},
    "monthly_revenue": {"月销售额", "monthly revenue", "销售额"},
    "image_url": {"图片", "图片链接", "主图", "image", "image url"},
    "product_url": {"商品链接", "产品链接", "listing url", "product url", "url"},
}


def normalized_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def header_mapping(row: list[Any]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for index, value in enumerate(row):
        normalized = normalized_cell(value)
        for standard, aliases in COLUMN_ALIASES.items():
            if normalized in aliases:
                mapping[index] = standard
                break
    return mapping


def detect_header(rows: list[list[Any]]) -> tuple[int, dict[int, str]]:
    best_index, best_mapping = -1, {}
    for index, row in enumerate(rows[:15]):
        mapping = header_mapping(row)
        if len(mapping) > len(best_mapping):
            best_index, best_mapping = index, mapping
    if len(best_mapping) < 2:
        raise CollectorError("无法识别导出文件表头。请提供原始样例文件以补充字段映射。")
    return best_index, best_mapping


def read_csv_rows(path: Path) -> list[list[Any]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.reader(handle))
        except UnicodeError as exc:
            last_error = exc
    raise CollectorError(f"无法识别 CSV 编码：{last_error}")


def read_xlsx_rows(path: Path) -> list[list[Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise CollectorError("缺少 openpyxl，请先运行“首次安装.bat”。") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        return [list(row) for row in workbook.active.iter_rows(values_only=True)]
    finally:
        workbook.close()


def normalize_export(path: Path, task: dict[str, Any]) -> list[dict[str, Any]]:
    rows = read_xlsx_rows(path) if path.suffix.lower() == ".xlsx" else read_csv_rows(path)
    header_index, mapping = detect_header(rows)
    products: list[dict[str, Any]] = []
    for raw_row in rows[header_index + 1 :]:
        record = {standard: raw_row[index] if index < len(raw_row) else None for index, standard in mapping.items()}
        if not any(value not in (None, "") for value in record.values()):
            continue
        record.update({"marketplace": task["marketplace"], "category": task["category"], "source_url": task["url"]})
        products.append(record)
    if not products:
        raise CollectorError("表头已识别，但没有读取到产品数据。")
    return products


def launch_browser_session(playwright: Any, config: dict[str, Any], run_date: str) -> tuple[Any, Any]:
    """Launch one persistent Chrome session for the whole batch run."""
    browser = config["browser"]
    profile_dir = (BASE_DIR / browser.get("profile_dir", "runtime/chrome-profile")).resolve()
    timeout = int(browser.get("navigation_timeout_ms", 60000))
    run_dir = source_run_dir(config, run_date)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        channel=browser.get("channel", "chrome"),
        headless=False,
        accept_downloads=True,
        downloads_path=str(run_dir),
        slow_mo=int(browser.get("slow_mo_ms", 250)),
        viewport=None,
        ignore_default_args=[
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
        ],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(timeout)
    attach_runtime_diagnostics(context, page)
    logging.info("批量采集浏览器已启动；后续榜单将复用同一个 Chrome 会话。")
    return context, page


def attach_runtime_diagnostics(context: Any, page: Any) -> None:
    """Write explicit lifecycle events to the log so TargetClosed errors are diagnosable."""
    try:
        context.on("close", lambda: logging.warning("[BROWSER] Persistent context 已关闭。"))
    except Exception:
        pass
    try:
        page.on("close", lambda: logging.warning("[PAGE] 当前采集页面已关闭。"))
        page.on("crash", lambda: logging.error("[PAGE] 当前采集页面发生 crash。"))
    except Exception:
        pass


def ensure_working_page(context: Any, page: Any, timeout: int) -> Any:
    """Return a live page, creating one when only the tab was closed."""
    try:
        if page is not None and not page.is_closed():
            page.set_default_timeout(timeout)
            return page
    except Exception:
        pass
    page = context.new_page()
    page.set_default_timeout(timeout)
    try:
        page.on("close", lambda: logging.warning("[PAGE] 当前采集页面已关闭。"))
        page.on("crash", lambda: logging.error("[PAGE] 当前采集页面发生 crash。"))
    except Exception:
        pass
    logging.warning("检测到原页面已关闭，已在现有 Chrome 会话中新建采集页面。")
    return page


def is_target_closed_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(
        marker in text
        for marker in (
            "targetclosed",
            "target page, context or browser has been closed",
            "browser has been closed",
            "context has been closed",
        )
    )


def save_error_diagnostics(page: Any, error_stem: str) -> None:
    try:
        if page is None or page.is_closed():
            return
        page.screenshot(path=str(ERROR_DIR / f"{error_stem}.png"), full_page=True)
        (ERROR_DIR / f"{error_stem}-frames.json").write_text(
            json.dumps([frame.url for frame in page.frames], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def collect_once(
    config: dict[str, Any], task: dict[str, Any], attempt: int, run_date: str, page: Any
) -> Path:
    """Collect one list using an already-running persistent Chrome session."""
    browser, selectors = config["browser"], config["selectors"]
    timeout = int(browser.get("navigation_timeout_ms", 60000))
    plugin_load_timeout = int(browser.get("plugin_load_timeout_ms", 180000))
    download_timeout = int(browser.get("download_timeout_ms", 180000))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    error_stem = f"{clean_name(task['id'])}-attempt-{attempt}-{timestamp}"
    run_dir = source_run_dir(config, run_date)
    page.set_default_timeout(timeout)

    try:
        logging.info("[%s] 打开榜单：%s", task["id"], task["url"])
        page.goto(task["url"], wait_until="domcontentloaded", timeout=timeout)
        cookie_selector = click_optional(page, selectors.get("cookie_accept", []), 2500)
        if cookie_selector:
            logging.info("[%s] 已处理 Cookie 同意弹窗：%s", task["id"], cookie_selector)
        else:
            logging.info("[%s] 未出现 Cookie 弹窗，继续执行。", task["id"])

        entry_selector = click_rightmost_match(page, selectors["entry"], timeout)
        logging.info("[%s] 已点击页面右侧的卖家精灵入口：%s", task["id"], entry_selector)
        wait_for_plugin_loading(page, selectors.get("loading", []), plugin_load_timeout)
        loaded_selector = wait_for_visible_marker(
            page, selectors.get("loaded", []), 30000, "卖家精灵数据表"
        )
        logging.info("[%s] 卖家精灵查询完成，数据表已出现：%s", task["id"], loaded_selector)

        scope = resolve_scope(page, selectors.get("frame_url_contains", ""))
        target_rows = int(task.get("target_rows", 100))
        for _ in range(int(task.get("max_load_more_clicks", 0))):
            current = count_rows(scope, selectors.get("row", []))
            if current is not None and current >= target_rows:
                break
            if not selectors.get("load_more"):
                break
            try:
                click_first(scope, selectors["load_more"], 5000)
                page.wait_for_timeout(1500)
            except CollectorError:
                break

        with page.expect_download(timeout=download_timeout) as download_info:
            export_selector = click_first_in_frames(
                page, selectors["export"], timeout, "左下角导出按钮"
            )
            logging.info("[%s] 已点击导出：%s", task["id"], export_selector)
        download = download_info.value

        suffix = Path(download.suggested_filename).suffix.lower() or ".xlsx"
        data_type = clean_name(str(task.get("data_type", "BSR")))
        target_rows = int(task.get("target_rows", 50))
        filename = (
            f"{data_type}_{clean_name(task['marketplace'])}_"
            f"{clean_name(task['category'])}"
            f"{('_Node' + clean_name(str(task['node_id']))) if task.get('node_id') else ''}"
            f"_Top{target_rows}_{run_date}{suffix}"
        )
        destination = run_dir / filename
        temporary = run_dir / f".{filename}.partial"
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass

        download.save_as(temporary)
        validate_download(temporary, suffix)
        temporary.replace(destination)
        logging.info("[%s] 下载并校验完成：%s", task["id"], destination.name)
        return destination
    except Exception:
        save_error_diagnostics(page, error_stem)
        raise


def run_collection(config: dict[str, Any], force: bool) -> int:
    validate_config(config)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CollectorError("缺少 Playwright，请先运行“首次安装.bat”。") from exc

    state = load_state()
    failures = 0
    run_date = datetime.now().strftime("%Y-%m-%d")
    run_dir = source_run_dir(config, run_date)
    manifest_path = run_dir / "run_manifest.json"
    if manifest_path.exists():
        try:
            task_results = load_json(manifest_path).get("tasks", [])
        except CollectorError:
            task_results = []
    else:
        task_results = []

    max_attempts = int(config.get("run", {}).get("max_attempts_per_task", 3))
    retry_wait = int(config.get("run", {}).get("retry_wait_seconds", 8))
    timeout = int(config.get("browser", {}).get("navigation_timeout_ms", 60000))

    with sync_playwright() as playwright:
        context = None
        page = None
        try:
            context, page = launch_browser_session(playwright, config, run_date)

            for task in config["tasks"]:
                task_id = task["id"]
                if not task.get("enabled", True):
                    logging.info("[%s] 当前未启用，跳过。", task_id)
                    continue

                previous = state.get("tasks", {}).get(task_id, {})
                if (
                    previous.get("status") == "completed"
                    and previous.get("run_date") == run_date
                    and previous.get("source_url") == task["url"]
                    and previous.get("download_file")
                    and (BASE_DIR / previous["download_file"]).is_file()
                    and not force
                ):
                    logging.info("[%s] 已完成，跳过。使用 --force 可重新运行。", task_id)
                    continue

                save_task_state(state, task_id, "running", attempt=0, run_date=run_date)
                task_error = ""

                for attempt in range(1, max_attempts + 1):
                    save_task_state(state, task_id, "running", attempt=attempt, run_date=run_date)
                    try:
                        page = ensure_working_page(context, page, timeout)
                        download = collect_once(config, task, attempt, run_date, page)
                        result = {
                            "id": task_id,
                            "status": "completed",
                            "data_type": task.get("data_type", "BSR"),
                            "marketplace": task["marketplace"],
                            "category": task["category"],
                            "node_id": task.get("node_id", ""),
                            "expected_rows": int(task.get("target_rows", 50)),
                            "source_url": task["url"],
                            "download_file": str(download.relative_to(BASE_DIR)),
                            "file_size_bytes": download.stat().st_size,
                            "completed_at": utc_now(),
                        }
                        upsert_task_result(task_results, result)
                        state_result = {
                            key: value for key, value in result.items() if key not in {"id", "status"}
                        }
                        save_task_state(
                            state,
                            task_id,
                            "completed",
                            run_date=run_date,
                            **state_result,
                        )
                        atomic_write_json(
                            manifest_path,
                            {"run_date": run_date, "updated_at": utc_now(), "tasks": task_results},
                        )
                        break

                    except Exception as exc:
                        task_error = str(exc)
                        logging.exception("[%s] 第 %s 次尝试失败：%s", task_id, attempt, exc)
                        save_task_state(
                            state,
                            task_id,
                            "retrying",
                            attempt=attempt,
                            error=task_error,
                            run_date=run_date,
                        )

                        if attempt < max_attempts:
                            if is_target_closed_error(exc):
                                logging.warning(
                                    "[%s] 检测到浏览器/Context 已失联；仅此时重启 Chrome 后重试当前榜单。",
                                    task_id,
                                )
                                try:
                                    if context is not None:
                                        context.close()
                                except Exception:
                                    pass
                                context, page = launch_browser_session(playwright, config, run_date)
                            else:
                                try:
                                    page = ensure_working_page(context, page, timeout)
                                    page.goto("about:blank", wait_until="domcontentloaded", timeout=15000)
                                except Exception:
                                    logging.warning(
                                        "[%s] 当前页面无法恢复，重启 Chrome 后重试当前榜单。", task_id
                                    )
                                    try:
                                        if context is not None:
                                            context.close()
                                    except Exception:
                                        pass
                                    context, page = launch_browser_session(playwright, config, run_date)
                            time.sleep(retry_wait)
                else:
                    failures += 1
                    result = {
                        "id": task_id,
                        "status": "failed",
                        "data_type": task.get("data_type", "BSR"),
                        "marketplace": task["marketplace"],
                        "category": task["category"],
                        "source_url": task["url"],
                        "error": task_error,
                        "failed_at": utc_now(),
                    }
                    upsert_task_result(task_results, result)
                    state_result = {
                        key: value for key, value in result.items() if key not in {"id", "status"}
                    }
                    save_task_state(
                        state,
                        task_id,
                        "failed",
                        run_date=run_date,
                        **state_result,
                    )
                    atomic_write_json(
                        manifest_path,
                        {"run_date": run_date, "updated_at": utc_now(), "tasks": task_results},
                    )
        finally:
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass

    logging.info("本周原始数据下载完成，清单：%s", manifest_path)
    return 2 if failures else 0

def inspect_mode(config: dict[str, Any]) -> int:
    validate_config(config, allow_placeholders=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CollectorError("缺少 Playwright，请先运行“首次安装.bat”。") from exc
    task, browser = config["tasks"][0], config["browser"]
    if "PASTE_" in task["url"]:
        raise CollectorError("inspect 模式也需要先粘贴一个亚马逊榜单链接。")
    profile_dir = (BASE_DIR / browser.get("profile_dir", "runtime/chrome-profile")).resolve()
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel=browser.get("channel", "chrome"),
            headless=False,
            viewport=None,
            ignore_default_args=[
                "--disable-extensions",
                "--disable-component-extensions-with-background-pages",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(task["url"], wait_until="domcontentloaded", timeout=60000)
        print("\n浏览器已打开。请确认卖家精灵已登录并打开悬浮面板。")
        input("完成后按回车，程序会保存诊断截图……")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        page.screenshot(path=str(ERROR_DIR / f"inspect-{timestamp}.png"), full_page=True)
        (ERROR_DIR / f"inspect-{timestamp}-frames.json").write_text(
            json.dumps([frame.url for frame in page.frames], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        context.close()
    print(f"诊断文件已保存到：{ERROR_DIR}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="卖家精灵单榜单测试采集器")
    parser.add_argument("command", nargs="?", choices=("run", "inspect"), default="run")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--force", action="store_true", help="重新运行已完成任务")
    return parser.parse_args()


def main() -> int:
    ensure_directories()
    configure_logging()
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BASE_DIR / config_path
    try:
        config = load_json(config_path)
        load_tasks_file(config, config_path)
        return inspect_mode(config) if args.command == "inspect" else run_collection(config, args.force)
    except CollectorError as exc:
        logging.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        logging.warning("用户已中止运行。进度已经保留。")
        return 130
    except Exception as exc:
        logging.exception("程序遇到未预期错误：%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
