import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collector_app
import seller_sprite_auto_login as auto_login
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


class LoginRoutingTests(unittest.TestCase):
    def test_one_click_login_uses_v2_config_and_gui_verification_callback(self):
        callback = lambda: None
        with patch('seller_sprite_auto_login.login_if_needed', return_value=0) as login:
            self.assertEqual(collector_app.main(['login'], wait_for_user=callback), 0)
        self.assertEqual(login.call_args.args[0], collector_app.BASE_DIR / 'config_v2.json')
        self.assertIs(login.call_args.args[1], callback)

    def test_download_checks_login_before_collecting(self):
        with patch('seller_sprite_auto_login.login_if_needed', return_value=0) as login, \
             patch('collector.ensure_directories'), patch('collector.configure_logging'), \
             patch('collector.run_collection', return_value=0) as collect:
            self.assertEqual(collector_app.main(['run']), 0)
        login.assert_called_once()
        collect.assert_called_once()

    def test_download_stops_when_login_check_fails(self):
        with patch('seller_sprite_auto_login.login_if_needed', return_value=1), \
             patch('collector.ensure_directories'), patch('collector.configure_logging'), \
             patch('collector.run_collection') as collect:
            self.assertEqual(collector_app.main(['run']), 1)
        collect.assert_not_called()

    def test_team_login_is_used_without_local_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary)
            with patch.object(auto_login, 'USERNAME_PATH', missing / 'username.txt'), \
                 patch.object(auto_login, 'PASSWORD_PATH', missing / 'password.dpapi'):
                username, password = auto_login.load_credentials()
        self.assertTrue(username)
        self.assertTrue(password)

    def test_local_override_takes_priority(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            username_path = folder / 'username.txt'
            password_path = folder / 'password.dpapi'
            username_path.write_text('local-user', encoding='utf-8')
            password_path.touch()
            with patch.object(auto_login, 'USERNAME_PATH', username_path), \
                 patch.object(auto_login, 'PASSWORD_PATH', password_path), \
                 patch.object(auto_login, 'decrypt_password', return_value='local-password'):
                self.assertEqual(auto_login.load_credentials(), ('local-user', 'local-password'))


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
