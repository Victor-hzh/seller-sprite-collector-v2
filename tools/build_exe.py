"""Bundle the GUI, Python runtime, and editable configuration for Windows."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
                    '--name', 'SellerSpriteCollector', '--collect-all', 'playwright',
                    '--hidden-import', 'cleaning.build_dashboard_data',
                    '--hidden-import', 'cleaning.merged_excel',
                    str(ROOT / 'collector_gui.py')], cwd=ROOT, check=True)
    package = ROOT / 'dist/SellerSpriteCollector-v2'
    if package.exists():
        if ROOT.resolve() not in package.resolve().parents:
            raise RuntimeError(f'Unsafe package directory: {package}')
        shutil.rmtree(package)
    package.mkdir(parents=True, exist_ok=True)
    for name in ('config_v2.json', 'tasks_v2.json',
                 'save_login_credentials.ps1', 'save_github_token.ps1', 'decrypt_login_password.ps1', 'README.md', 'README_WINDOWS_GUI.txt'):
        shutil.copy2(ROOT / name, package / name)
    shutil.copy2(ROOT / 'dist/SellerSpriteCollector.exe', package / 'SellerSpriteCollector.exe')
    (package / 'cleaning').mkdir(exist_ok=True)
    for name in ('cleaning_rules.json', 'exchange_rates.json'):
        shutil.copy2(ROOT / 'cleaning' / name, package / 'cleaning' / name)
    (package / 'data/source').mkdir(parents=True)
    (package / 'runtime').mkdir()
    subprocess.run([str(package / 'SellerSpriteCollector.exe'), '--self-test'], check=True, timeout=120)
    shutil.make_archive(str(ROOT / 'dist/SellerSpriteCollector-v2'), 'zip', ROOT / 'dist', package.name)


if __name__ == '__main__':
    main()
