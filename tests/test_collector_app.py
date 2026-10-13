import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from collector_app import latest_source_folder
from collector_gui import build_change_request_prompt


class UploadFolderTests(unittest.TestCase):
    def test_prefers_today_with_excel(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / '2026-10-12'
            today = root / '2026-10-13'
            old.mkdir()
            today.mkdir()
            (old / 'old.xlsx').touch()
            (today / 'today.xlsx').touch()
            self.assertEqual(latest_source_folder(root, '2026-10-13'), today)

    def test_uses_latest_nonempty_folder_when_today_is_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for date in ('2026-10-11', '2026-10-12', '2026-10-13'):
                (root / date).mkdir()
            (root / '2026-10-11' / 'old.xlsx').touch()
            (root / '2026-10-12' / 'latest.xlsx').touch()
            self.assertEqual(latest_source_folder(root, '2026-10-13'), root / '2026-10-12')

    def test_no_excel_does_not_open_an_upload_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '2026-10-13').mkdir()
            self.assertIsNone(latest_source_folder(root, '2026-10-13'))


class ChangeRequestTests(unittest.TestCase):
    def test_template_contains_choices_links_and_requested_scope(self):
        prompt = build_change_request_prompt(
            '德国站', '洗地机',
            'https://www.amazon.de/gp/bestsellers/kitchen/218877962031\n'
            'https://www.amazon.de/gp/bestsellers/kitchen/2077530031',
            '追觅与石头分属两个榜单，需要合并并排除工业桶式吸尘器。',
        )
        self.assertIn('德国站（DE）', prompt)
        self.assertIn('品类：洗地机', prompt)
        self.assertIn('2077530031', prompt)
        self.assertIn('追觅与石头', prompt)
        self.assertIn('同一 ASIN 跨榜单出现时去重', prompt)

    def test_requires_all_four_fields(self):
        for region, category, urls, description in (
            ('', '洗地机', 'https://www.amazon.de/a', '问题'),
            ('德国站', '', 'https://www.amazon.de/a', '问题'),
            ('德国站', '洗地机', 'not-a-link', '问题'),
            ('德国站', '洗地机', 'https://www.amazon.de/a', ''),
        ):
            with self.subTest(region=region, category=category, urls=urls):
                with self.assertRaises(ValueError):
                    build_change_request_prompt(region, category, urls, description)


@unittest.skipUnless(os.name == 'nt', 'Windows DPAPI integration test')
class CredentialIntegrationTests(unittest.TestCase):
    def test_stdin_credentials_round_trip_with_unicode(self):
        project = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            shutil.copy2(project / 'save_login_credentials.ps1', folder / 'save_login_credentials.ps1')
            saved = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                 '-File', str(folder / 'save_login_credentials.ps1'), '-FromStdin'],
                input='测试用户@example.com\n临时测试密码123\n', text=True, encoding='utf-8',
                capture_output=True,
                env={key: value for key, value in os.environ.items() if key.upper() != 'PSMODULEPATH'},
            )
            self.assertEqual(saved.returncode, 0, saved.stderr)
            runtime = folder / 'runtime'
            self.assertEqual((runtime / 'seller_sprite_username.txt').read_text(encoding='utf-8-sig').strip(),
                             '测试用户@example.com')
            decrypted = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                 '-File', str(project / 'decrypt_login_password.ps1'), '-PasswordFile',
                 str(runtime / 'seller_sprite_password.dpapi')],
                text=True, encoding='utf-8', capture_output=True, check=True,
                env={key: value for key, value in os.environ.items() if key.upper() != 'PSMODULEPATH'},
            )
            self.assertEqual(decrypted.stdout, '临时测试密码123')


if __name__ == '__main__':
    unittest.main()
