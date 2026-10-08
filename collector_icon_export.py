from __future__ import annotations

import re
import time
from typing import Any, Iterable

import collector as core
from seller_sprite_auto_login import click_optional_in_frames, first_visible, load_credentials


ORIGINAL_CLICK_FIRST_IN_FRAMES = core.click_first_in_frames
ORIGINAL_WAIT_FOR_PLUGIN_LOADING = core.wait_for_plugin_loading

LOGIN_TAB_SELECTORS = [
    "button:has-text('账号登录')",
    "[role='button']:has-text('账号登录')",
    "text=账号登录",
    "button:has-text('账户登录')",
    "[role='button']:has-text('账户登录')",
    "text=账户登录",
    "button:has-text('密码登录')",
    "[role='button']:has-text('密码登录')",
    "text=密码登录",
    "button:has-text('账号密码登录')",
    "text=账号密码登录",
]

USERNAME_SELECTORS = [
    "input[placeholder*='手机号']",
    "input[placeholder*='手机号码']",
    "input[placeholder*='账号']",
    "input[placeholder*='邮箱']",
    "input[name*='username']",
    "input[name*='account']",
    "input[name*='phone']",
    "input[type='tel']",
]

LOGIN_BUTTON_SELECTORS = [
    "button:text-is('登录')",
    "button:has-text('登录')",
    "[role='button']:has-text('登录')",
    "input[type='submit']",
]

LOADED_SELECTORS = [
    "text=ASIN数量",
    "th:has-text('产品信息')",
    "text=加载数据 50 条",
]

DATA_ROW_SELECTORS = [
    ".el-table__body-wrapper tbody tr",
    ".el-table__body tbody tr",
    ".el-table__row",
    ".ant-table-tbody > tr",
    ".ant-table-row",
    ".vxe-table--body-wrapper tbody tr",
    "[role='rowgroup'] [role='row']",
    "[role='row']",
    "[class*='table-row']",
    "[class*='table_row']",
    "[class*='TableRow']",
    "table tbody tr",
]

DATA_ROW_EVIDENCE = re.compile(
    r"(?:\bB[A-Z0-9]{9}\b|ASIN|BSR|月销量|销量|销售额|品牌|评分)",
    re.IGNORECASE,
)

_CREDENTIALS: tuple[str, str] | None = None


def saved_credentials() -> tuple[str, str]:
    global _CREDENTIALS
    if _CREDENTIALS is None:
        _CREDENTIALS = load_credentials()
    return _CREDENTIALS


def visible_panel_state(page: Any, loading_selectors: Iterable[str]) -> str | None:
    if first_visible(page, loading_selectors) is not None:
        return "loading"
    if first_visible(page, LOADED_SELECTORS) is not None:
        return "loaded"
    return None


def visible_product_rows_snapshot(page: Any) -> tuple[int, str]:
    """Return a stable signature for the best visible SellerSprite product table.

    The panel shell, header and ASIN counter can appear before the actual query
    result.  A real data row must contain product-level evidence such as an
    ASIN, BSR, brand or sales metric.
    """
    best_rows: list[str] = []
    for frame in page.frames:
        for selector in DATA_ROW_SELECTORS:
            try:
                rows = frame.locator(selector)
                visible_rows: list[str] = []
                for index in range(min(rows.count(), 80)):
                    row = rows.nth(index)
                    if not row.is_visible():
                        continue
                    row_text = re.sub(r"\s+", " ", row.inner_text()).strip()
                    if len(row_text) < 12 or not DATA_ROW_EVIDENCE.search(row_text):
                        continue
                    visible_rows.append(row_text[:500])
                if len(visible_rows) > len(best_rows):
                    best_rows = visible_rows
            except Exception:
                continue
    return len(best_rows), "\n".join(best_rows)


def wait_for_product_rows_to_settle(
    page: Any,
    timeout_seconds: int = 45,
    stable_checks_required: int = 4,
    final_settle_seconds: int = 12,
) -> None:
    """Wait for real rows, then require their contents to stop changing.

    SellerSprite occasionally renders the result grid with virtual/custom DOM
    nodes that cannot be matched reliably from Playwright.  In that case we
    must not block an otherwise fully loaded result forever: after the bounded
    detection window, wait once more and let the downloaded workbook validator
    be the final authority.  Empty/header-only workbooks are still rejected by
    the collector and retried, so this fallback does not accept empty exports.
    """
    deadline = time.monotonic() + timeout_seconds
    previous_snapshot = ""
    stable_checks = 0
    last_row_count = 0

    while time.monotonic() < deadline:
        row_count, snapshot = visible_product_rows_snapshot(page)
        last_row_count = row_count
        if row_count > 0 and snapshot == previous_snapshot:
            stable_checks += 1
        elif row_count > 0:
            previous_snapshot = snapshot
            stable_checks = 1
        else:
            previous_snapshot = ""
            stable_checks = 0

        if stable_checks >= stable_checks_required:
            core.logging.info(
                "已检测到 %s 条可见商品数据，内容已稳定；继续等待 %s 秒再导出。",
                row_count,
                final_settle_seconds,
            )
            page.wait_for_timeout(final_settle_seconds * 1000)
            return
        page.wait_for_timeout(1000)

    fallback_wait_seconds = 15
    core.logging.warning(
        "卖家精灵结果区已出现，但%s秒内未能通过DOM识别商品行（最后识别 %s 条）。"
        "页面可能使用了虚拟表格；继续等待 %s 秒后尝试导出，并以Excel内容校验结果为准。",
        timeout_seconds,
        last_row_count,
        fallback_wait_seconds,
    )
    page.wait_for_timeout(fallback_wait_seconds * 1000)


def ensure_login_for_current_list(
    page: Any,
    loading_selectors: Iterable[str],
    timeout_seconds: int = 60,
) -> str:
    """Check SellerSprite login after opening every list and sign in when required."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = visible_panel_state(page, loading_selectors)
        if state:
            return state

        click_optional_in_frames(page, LOGIN_TAB_SELECTORS)
        password_field = first_visible(page, ["input[type='password']"])
        if password_field is None:
            page.wait_for_timeout(300)
            continue

        username_field = first_visible(page, USERNAME_SELECTORS)
        if username_field is None:
            raise core.CollectorError("检测到卖家精灵登录页，但没有找到账号输入框。")

        username, password = saved_credentials()
        core.logging.info("当前榜单需要重新登录卖家精灵，正在切换账号登录。")
        username_field.fill(username)
        password_field.fill(password)
        login_button = first_visible(page, LOGIN_BUTTON_SELECTORS)
        if login_button is None:
            raise core.CollectorError("检测到卖家精灵登录页，但没有找到登录按钮。")
        login_button.click(timeout=10000)

        login_deadline = time.monotonic() + 60
        while time.monotonic() < login_deadline:
            state = visible_panel_state(page, loading_selectors)
            if state:
                core.logging.info("当前榜单的卖家精灵重新登录完成，继续加载数据。")
                return state
            page.wait_for_timeout(500)
        raise core.CollectorError("卖家精灵已提交账号密码，但60秒内没有进入数据界面。")

    raise core.CollectorError("60秒内没有检测到卖家精灵数据界面或账号登录界面。")


def wait_for_plugin_loading_with_login(
    page: Any,
    loading_selectors: Iterable[str],
    timeout_ms: int,
) -> None:
    state = ensure_login_for_current_list(page, loading_selectors)
    if state != "loaded":
        ORIGINAL_WAIT_FOR_PLUGIN_LOADING(page, loading_selectors, timeout_ms)
    wait_for_product_rows_to_settle(page)


def bottom_left_buttons(page: Any) -> list[tuple[float, float, Any]]:
    """Find compact visible buttons in the plugin's bottom-left toolbar."""
    viewport = page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
    viewport_width = float(viewport["width"])
    viewport_height = float(viewport["height"])
    matches: list[tuple[float, float, Any]] = []

    for frame in page.frames:
        try:
            buttons = frame.locator("button")
            count = min(buttons.count(), 250)
        except Exception:
            continue
        for index in range(count):
            button = buttons.nth(index)
            try:
                if not button.is_visible():
                    continue
                box = button.bounding_box()
                if not box:
                    continue
                width = float(box["width"])
                height = float(box["height"])
                center_x = float(box["x"] + width / 2)
                center_y = float(box["y"] + height / 2)
                if not (18 <= width <= 80 and 18 <= height <= 65):
                    continue
                if center_x > min(500, viewport_width * 0.45):
                    continue
                if center_y < viewport_height - 90:
                    continue
                matches.append((center_x, center_y, button))
            except Exception:
                continue

    if not matches:
        return []

    bottom_y = max(item[1] for item in matches)
    same_row = [item for item in matches if abs(item[1] - bottom_y) <= 12]
    same_row.sort(key=lambda item: item[0])

    deduplicated: list[tuple[float, float, Any]] = []
    for item in same_row:
        if deduplicated and abs(item[0] - deduplicated[-1][0]) < 8:
            continue
        deduplicated.append(item)
    return deduplicated


def click_bottom_left_second_button(page: Any, timeout_ms: int) -> str:
    deadline = time.monotonic() + min(timeout_ms, 30000) / 1000
    last_count = 0
    while time.monotonic() < deadline:
        buttons = bottom_left_buttons(page)
        last_count = len(buttons)
        if len(buttons) >= 2:
            buttons[1][2].click(timeout=10000)
            return "bottom-left-toolbar button #2"
        page.wait_for_timeout(300)
    raise core.CollectorError(
        f"没有找到卖家精灵底部左侧第二个导出图标；最后检测到同排按钮 {last_count} 个。"
    )


def click_first_in_frames_with_icon_fallback(
    page: Any,
    selectors: Iterable[str],
    timeout_ms: int,
    label: str,
) -> str:
    if label != "左下角导出按钮":
        return ORIGINAL_CLICK_FIRST_IN_FRAMES(page, selectors, timeout_ms, label)

    try:
        return ORIGINAL_CLICK_FIRST_IN_FRAMES(page, selectors, min(timeout_ms, 2500), label)
    except core.CollectorError:
        return click_bottom_left_second_button(page, timeout_ms)


core.click_first_in_frames = click_first_in_frames_with_icon_fallback
core.wait_for_plugin_loading = wait_for_plugin_loading_with_login


if __name__ == "__main__":
    raise SystemExit(core.main())
