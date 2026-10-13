"""Build an EXE and editable configuration as a distributable ZIP."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--console',
                    '--name', 'SellerSpriteCollector', '--collect-all', 'playwright',
                    str(ROOT / 'collector_app.py')], cwd=ROOT, check=True)
    package = ROOT / 'dist/SellerSpriteCollector-v2'
    package.mkdir(parents=True, exist_ok=True)
    for name in ('config_v2.json', 'tasks_v2.json',
                 'save_login_credentials.ps1', 'decrypt_login_password.ps1', 'README.md'):
        shutil.copy2(ROOT / name, package / name)
    shutil.copy2(ROOT / 'dist/SellerSpriteCollector.exe', package / 'SellerSpriteCollector.exe')
    (package / 'cleaning').mkdir(exist_ok=True)
    for name in ('cleaning_rules.json', 'exchange_rates.json'):
        shutil.copy2(ROOT / 'cleaning' / name, package / 'cleaning' / name)
    subprocess.run([str(package / 'SellerSpriteCollector.exe'), 'check'], check=True)
    shutil.make_archive(str(ROOT / 'dist/SellerSpriteCollector-v2'), 'zip', ROOT / 'dist', package.name)


if __name__ == '__main__':
    main()
