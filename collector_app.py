"""Console menu shared by source checkout and the packaged Windows EXE."""
import argparse
import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from app_paths import BASE_DIR


def main(argv=None):
    parser = argparse.ArgumentParser(description='SellerSprite Collector V2')
    parser.add_argument('command', nargs='?', choices=['run', 'inspect', 'clean', 'credentials', 'upload', 'check'])
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--task', help='只运行指定任务 ID，适合验证新增榜单')
    args = parser.parse_args(argv)
    os.chdir(BASE_DIR)
    command = args.command
    interactive = command is None
    if interactive:
        print('卖家精灵采集 V2\n1. 下载榜单\n2. 浏览器/插件初始化\n3. 清洗与合并\n4. 保存本机登录信息\n5. 打开新仓库上传页面\n6. 检查配置')
        command = dict(zip('123456', ['run', 'inspect', 'clean', 'credentials', 'upload', 'check'])).get(input('请选择：').strip())
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
        elif command in ('run', 'inspect'):
            core.ensure_directories()
            core.configure_logging()
            code = core.run_collection(config, args.force) if command == 'run' else core.inspect_mode(config)
        elif command == 'clean':
            from tools import build_dashboard_data as builder
            builder.ROOT = BASE_DIR
            code = builder.main([])
        elif command == 'credentials':
            code = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(BASE_DIR / 'save_login_credentials.ps1')]).returncode
        else:
            if config.get('repository') != 'Victor-hzh/seller-sprite-collector-v2':
                raise RuntimeError('实验版只允许上传到独立 V2 仓库。')
            date = datetime.now().strftime('%Y-%m-%d')
            folder = BASE_DIR / 'data/source' / date
            if not folder.is_dir():
                raise RuntimeError('今天的数据目录不存在，请先下载。')
            os.startfile(str(folder))
            webbrowser.open(f"https://github.com/{config['repository']}/upload/main/data/source/{date}")
            code = 0
    except Exception as exc:
        print(f'运行失败：{exc}')
        code = 1
    if interactive:
        input('按回车关闭。')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
