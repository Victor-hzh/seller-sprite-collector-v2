"""Console menu shared by source checkout and the packaged Windows EXE."""
import argparse
import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Callable
from app_paths import BASE_DIR


def latest_source_folder(source_root: Path, today: str) -> Path | None:
    """Prefer today's Excel files, then the newest dated folder awaiting upload."""
    if not source_root.is_dir():
        return None
    folders = sorted((path for path in source_root.iterdir() if path.is_dir()), reverse=True)
    today_folder = source_root / today
    if today_folder in folders:
        folders.remove(today_folder)
        folders.insert(0, today_folder)
    return next((path for path in folders if any(path.glob('*.xlsx'))), None)


def main(argv=None, *, wait_for_user: Callable[[], None] | None = None):
    parser = argparse.ArgumentParser(description='SellerSprite Collector V2')
    parser.add_argument('command', nargs='?', choices=['run', 'run-upload', 'inspect', 'login', 'clean', 'credentials', 'upload', 'upload-auto', 'check'])
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--task', help='只运行指定任务 ID，适合验证新增榜单')
    args = parser.parse_args(argv)
    os.chdir(BASE_DIR)
    command = args.command
    interactive = command is None
    if interactive:
        print('卖家精灵采集 V2\n1. 下载榜单\n2. 浏览器/插件初始化\n3. 一键登录\n4. 清洗与合并\n5. 保存本机登录信息\n6. 打开新仓库上传页面\n7. 检查配置')
        command = dict(zip('1234567', ['run', 'inspect', 'login', 'clean', 'credentials', 'upload', 'check'])).get(input('请选择：').strip())
        if command is None:
            return 0
    try:
        import collector_icon_export  # Applies the existing login/export compatibility layer.
        import collector as core
        config_path = BASE_DIR / 'config_v2.json'
        config = core.load_json(config_path)
        core.load_tasks_file(config, config_path)
        core.validate_config(config)
        if args.task:
            config['tasks'] = [t for t in config['tasks'] if t['id'] == args.task and t.get('enabled', True)]
            if not config['tasks']:
                raise RuntimeError('指定任务不存在或未启用。')
        if command == 'check':
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                driver_ready = playwright.chromium.name == 'chromium'
            print(json.dumps({'repository': config['repository'], 'enabledSources': sum(t.get('enabled', True) for t in config['tasks']),
                              'productGroups': len({(t['marketplace'], t['category']) for t in config['tasks'] if t.get('enabled', True)}),
                              'baseDirectory': str(BASE_DIR), 'browserDriverReady': driver_ready}, ensure_ascii=False, indent=2))
            code = 0
        elif command in ('run', 'run-upload', 'inspect'):
            core.ensure_directories()
            core.configure_logging()
            if command in ('run', 'run-upload'):
                from seller_sprite_auto_login import login_if_needed
                print('先检查卖家精灵登录状态，必要时自动登录...')
                login_code = login_if_needed(config_path, wait_for_user)
                if login_code != 0:
                    raise RuntimeError('卖家精灵登录检查未通过，下载未开始。')
                print('登录检查通过，开始下载榜单。')
                code = core.run_collection(config, args.force)
                if code == 0 and command == 'run-upload':
                    code = upload_downloaded_excel(config, task_id=args.task, today_only=True)
            else:
                code = core.inspect_mode(config, wait_for_user)
        elif command == 'login':
            from seller_sprite_auto_login import login_if_needed
            code = login_if_needed(config_path, wait_for_user)
        elif command == 'clean':
            from cleaning import build_dashboard_data as builder
            builder.ROOT = BASE_DIR
            code = builder.main([])
        elif command == 'credentials':
            code = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(BASE_DIR / 'save_login_credentials.ps1')]).returncode
        elif command == 'upload-auto':
            code = upload_downloaded_excel(config, task_id=args.task)
        else:
            if config.get('repository') != 'Victor-hzh/seller-sprite-collector-v2':
                raise RuntimeError('实验版只允许上传到独立 V2 仓库。')
            source_dir = Path(config.get('storage', {}).get('source_dir', 'data/source'))
            if not source_dir.is_absolute():
                source_dir = BASE_DIR / source_dir
            folder = latest_source_folder(source_dir, datetime.now().strftime('%Y-%m-%d'))
            if folder is None:
                raise RuntimeError('没有找到已下载的 Excel，请先点击下载榜单。')
            os.startfile(str(folder))
            webbrowser.open(f"https://github.com/{config['repository']}/upload/main/data/source/{folder.name}")
            print(f'已打开数据文件夹和 GitHub 上传页面：{folder}')
            code = 0
    except Exception as exc:
        print(f'运行失败：{exc}')
        code = 1
    if interactive:
        input('按回车关闭。')
    return code


def upload_downloaded_excel(config: dict, *, task_id: str | None = None, today_only: bool = False) -> int:
    from github_upload import GitHubClient, REPOSITORY, excel_files, read_saved_token, upload_excel_files

    if config.get('repository') != REPOSITORY:
        raise RuntimeError('自动上传仅允许独立 V2 仓库。')
    source_dir = Path(config.get('storage', {}).get('source_dir', 'data/source'))
    if not source_dir.is_absolute():
        source_dir = BASE_DIR / source_dir
    today = datetime.now().strftime('%Y-%m-%d')
    folder = source_dir / today if today_only else latest_source_folder(source_dir, today)
    if folder is None or not folder.is_dir():
        raise RuntimeError('没有找到可上传的 Excel，请先下载榜单。')
    files = excel_files(folder, task_id)
    print(f'准备自动上传 {folder.name} 的 {len(files)} 份 Excel…')
    changed, url = upload_excel_files(files, folder, GitHubClient(read_saved_token()))
    if changed:
        print(f'已提交 {changed} 份 Excel：{url}')
        print(f'清洗任务会自动运行：https://github.com/{REPOSITORY}/actions/workflows/build-dashboard-data.yml')
    else:
        print('仓库中的 Excel 与本地相同，无需重新提交；看板数据不会重复构建。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
