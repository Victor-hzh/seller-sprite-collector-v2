"""Compile a per-user Windows installer from the validated GUI bundle."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'installer' / 'SellerSpriteCollector.nsi'
OUTPUT = ROOT / 'dist' / 'SellerSpriteCollector-v2-Setup.exe'


def compiler() -> Path:
    found = shutil.which('makensis')
    candidates = [Path(found)] if found else []
    candidates += [Path(r'C:\Program Files (x86)\NSIS\makensis.exe'),
                   Path(r'C:\Program Files\NSIS\makensis.exe')]
    result = next((path for path in candidates if path.is_file()), None)
    if result is None:
        raise RuntimeError('NSIS is required on the build machine; end users do not need it.')
    return result


def main() -> None:
    payload = ROOT / 'dist' / 'SellerSpriteCollector-v2' / 'SellerSpriteCollector.exe'
    if not payload.is_file():
        raise RuntimeError('Build the GUI bundle first: python tools/build_exe.py')
    subprocess.run([str(compiler()), f'/DPROJECT_ROOT={ROOT}', str(SCRIPT)], cwd=ROOT, check=True)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
        raise RuntimeError(f'Installer was not created: {OUTPUT}')
    print(f'Windows installer: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
