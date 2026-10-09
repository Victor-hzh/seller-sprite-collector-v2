from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable


from app_paths import BASE_DIR
USERNAME_PATH = BASE_DIR / "runtime" / "seller_sprite_username.txt"
PASSWORD_PATH = BASE_DIR / "runtime" / "seller_sprite_password.dpapi"
DECRYPT_SCRIPT_PATH = BASE_DIR / "decrypt_login_password.ps1"


class LoginError(RuntimeError):
    pass


def decrypt_password() -> str:
    if not DECRYPT_SCRIPT_PATH.exists():
        raise LoginError("decrypt_login_password.ps1 is missing from the patch folder.")
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(DECRYPT_SCRIPT_PATH),
            "-PasswordFile",
            str(PASSWORD_PATH.resolve()),
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # PowerShell 7's inherited module paths can break Windows PowerShell's
        # DPAPI cmdlets. Let Windows PowerShell build its own default paths.
        env={key: value for key, value in os.environ.items() if key.upper() != 'PSMODULEPATH'},
    )
    if result.returncode or not result.stdout:
        detail = result.stderr.strip().splitlines()
        suffix = f" Windows message: {detail[-1]}" if detail else ""
        raise LoginError(f"Windows could not decrypt the saved SellerSprite password.{suffix}")
    return result.stdout


def load_credentials() -> tuple[str, str]:
    if not USERNAME_PATH.exists() or not PASSWORD_PATH.exists():
        raise LoginError("Run SAVE_LOGIN_ON_THIS_PC.bat first.")
    username = USERNAME_PATH.read_text(encoding="utf-8-sig").strip()
    password = decrypt_password()
    if not username or not password:
        raise LoginError("The locally saved SellerSprite login information is empty.")
    return username, password


def first_visible(page: Any, selectors: Iterable[str]) -> Any | None:
    for frame in page.frames:
        for selector in selectors:
            try:
                locator = frame.locator(selector).first
                if locator.is_visible():
                    return locator
            except Exception:
                continue
    return None


def click_optional_in_frames(page: Any, selectors: Iterable[str]) -> bool:
    locator = first_visible(page, selectors)
    if locator is None:
        return False
    try:
        locator.click(timeout=5000)
        return True
    except Exception:
        return False


def wait_for_login_state(
    page: Any,
    signed_in_selectors: Iterable[str],
    login_tab_selectors: Iterable[str],
    timeout_seconds: int = 60,
) -> tuple[str, Any | None]:
    """Return login, signed_in, or unknown after inspecting all page frames."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        click_optional_in_frames(page, login_tab_selectors)
        locator = first_visible(page, ["input[type='password']"])
        if locator is not None:
            return "login", locator
        if first_visible(page, signed_in_selectors) is not None:
            return "signed_in", None
        page.wait_for_timeout(300)
    return "unknown", None


def login_if_needed(config_path: Path) -> int:
    try:
        from playwright.sync_api import sync_playwright
        from collector import click_optional, click_rightmost_match, load_json, load_tasks_file
    except ImportError as exc:
        raise LoginError("The working V1 collector environment is incomplete.") from exc

    username, password = load_credentials()
    config = load_json(config_path)
    load_tasks_file(config, config_path)
    if not config.get("tasks"):
        raise LoginError("No download tasks were found.")

    browser = config["browser"]
    selectors = config["selectors"]
    profile_dir = (BASE_DIR / browser.get("profile_dir", "runtime/chrome-profile")).resolve()
    timeout = int(browser.get("navigation_timeout_ms", 60000))
    first_task = config["tasks"][0]

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel=browser.get("channel", "chrome"),
            headless=False,
            viewport=None,
            slow_mo=int(browser.get("slow_mo_ms", 250)),
            ignore_default_args=[
                "--disable-extensions",
                "--disable-component-extensions-with-background-pages",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(timeout)
        try:
            print("Opening the first Amazon list to check SellerSprite login...")
            page.goto(first_task["url"], wait_until="domcontentloaded", timeout=timeout)
            click_optional(page, selectors.get("cookie_accept", []), 2500)
            click_rightmost_match(page, selectors["entry"], timeout)
            page.wait_for_timeout(1200)

            login_tab_selectors = [
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
            signed_in_selectors = [
                *selectors.get("loading", []),
                *selectors.get("loaded", []),
            ]
            login_state, password_field = wait_for_login_state(
                page,
                signed_in_selectors,
                login_tab_selectors,
            )
            if login_state == "signed_in":
                print("SellerSprite is signed in or its data panel is loading. Continuing.")
                return 0
            if login_state == "unknown" or password_field is None:
                raise LoginError(
                    "SellerSprite neither showed its data panel nor a password login form within 60 seconds."
                )

            username_field = first_visible(
                page,
                [
                    "input[placeholder*='手机号']",
                    "input[placeholder*='手机号码']",
                    "input[placeholder*='账号']",
                    "input[placeholder*='邮箱']",
                    "input[name*='username']",
                    "input[name*='account']",
                    "input[name*='phone']",
                    "input[type='tel']",
                ],
            )
            if username_field is None:
                raise LoginError("SellerSprite password field was found, but the account field was not found.")

            username_field.fill(username)
            password_field.fill(password)
            login_button = first_visible(
                page,
                [
                    "button:text-is('登录')",
                    "button:has-text('登录')",
                    "[role='button']:has-text('登录')",
                    "input[type='submit']",
                ],
            )
            if login_button is None:
                raise LoginError("SellerSprite login button was not found.")
            login_button.click(timeout=10000)

            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if first_visible(page, signed_in_selectors) is not None:
                    print("SellerSprite login completed. Continuing to the 30 downloads.")
                    page.wait_for_timeout(1500)
                    return 0
                page.wait_for_timeout(500)

            print("SellerSprite requires additional verification.")
            input("Complete the verification in Chrome, then press Enter here...")
            if first_visible(page, signed_in_selectors) is None:
                raise LoginError("SellerSprite login is still incomplete.")
            return 0
        finally:
            context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and complete SellerSprite login before V1 collection.")
    parser.add_argument("--config", default="config_all_30.json")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BASE_DIR / config_path
    try:
        return login_if_needed(config_path)
    except LoginError as exc:
        print(f"LOGIN ERROR: {exc}")
        return 1
    except KeyboardInterrupt:
        print("Login check cancelled.")
        return 130
    except Exception as exc:
        print(f"LOGIN ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
