import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import github_upload


class FakeGitHub:
    def __init__(self, existing=None, advance_once=False):
        self.files = dict(existing or {})
        self.blobs = {}
        self.calls = []
        self.head = "head-1"
        self.advance_once = advance_once

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and "/git/ref/heads/" in path:
            return {"object": {"sha": self.head}}
        if method == "GET" and "/git/commits/" in path:
            return {"tree": {"sha": "tree-" + self.head}}
        if method == "GET" and "/git/trees/" in path:
            return {"tree": [{"path": p, "sha": sha, "type": "blob"} for p, sha in self.files.items()]}
        if method == "POST" and path.endswith("/git/blobs"):
            sha = github_upload.git_blob_sha(__import__("base64").b64decode(payload["content"]))
            self.blobs[sha] = payload
            return {"sha": sha}
        if method == "POST" and path.endswith("/git/trees"):
            self.pending = {entry["path"]: entry["sha"] for entry in payload["tree"]}
            return {"sha": "new-tree"}
        if method == "POST" and path.endswith("/git/commits"):
            return {"sha": "new-commit"}
        if method == "PATCH" and "/git/refs/heads/" in path:
            if self.advance_once:
                self.advance_once = False
                self.head = "head-2"
                raise github_upload.UploadError("GitHub API 返回 HTTP 422；请检查仓库权限和网络后重试。")
            self.files.update(self.pending)
            self.head = payload["sha"]
            return {"object": {"sha": self.head}}
        raise AssertionError((method, path, payload))


class GitHubUploadTests(unittest.TestCase):
    def test_uploads_two_excel_files_in_one_commit_then_skips_identical_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "data" / "source" / "2026-10-14"
            folder.mkdir(parents=True)
            files = [folder / "one.xlsx", folder / "two.xlsx"]
            files[0].write_bytes(b"one")
            files[1].write_bytes(b"two")
            client = FakeGitHub()
            count, url = github_upload.upload_excel_files(files, folder, client)
            self.assertEqual(count, 2)
            self.assertTrue(url.endswith("/commit/new-commit"))
            self.assertEqual(len([call for call in client.calls if call[0] == "PATCH"]), 1)
            self.assertEqual(len([call for call in client.calls if call[1].endswith("/git/blobs")]), 2)
            self.assertEqual(github_upload.upload_excel_files(files, folder, client), (0, None))
            self.assertEqual(len([call for call in client.calls if call[0] == "PATCH"]), 1)

    def test_rebases_after_branch_advances_without_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "data" / "source" / "2026-10-14"
            folder.mkdir(parents=True)
            file = folder / "one.xlsx"
            file.write_bytes(b"one")
            client = FakeGitHub(advance_once=True)
            count, _ = github_upload.upload_excel_files([file], folder, client)
            self.assertEqual(count, 1)
            self.assertEqual(len([call for call in client.calls if call[1].endswith("/git/blobs")]), 1)
            commits = [call for call in client.calls if call[1].endswith("/git/commits") and call[0] == "POST"]
            self.assertEqual([call[2]["parents"] for call in commits], [["head-1"], ["head-2"]])
            self.assertTrue(all(call[2]["force"] is False for call in client.calls if call[0] == "PATCH"))

    def test_selected_task_cannot_upload_another_excel(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "data" / "source" / "2026-10-14"
            folder.mkdir(parents=True)
            correct = folder / "correct.xlsx"
            other = folder / "other.xlsx"
            correct.touch()
            other.touch()
            (folder / "run_manifest.json").write_text(json.dumps({"tasks": [
                {"id": "TASK_A", "status": "completed", "download_file": "data/source/2026-10-14/correct.xlsx"},
            ]}), encoding="utf-8")
            with patch.object(github_upload, "BASE_DIR", Path(temporary)):
                self.assertEqual(github_upload.excel_files(folder, "TASK_A"), [correct])
                with self.assertRaises(github_upload.UploadError):
                    github_upload.excel_files(folder, "TASK_B")


@unittest.skipUnless(os.name == "nt", "Windows DPAPI integration test")
class GitHubTokenTests(unittest.TestCase):
    def test_token_is_encrypted_and_can_be_read_by_same_windows_user(self):
        project = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            shutil.copy2(project / "save_github_token.ps1", folder / "save_github_token.ps1")
            token = "github_pat_test_secret_123"
            environment = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
            saved = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-File", str(folder / "save_github_token.ps1"), "-FromStdin"],
                input=token + "\n", text=True, encoding="utf-8", capture_output=True, env=environment,
            )
            self.assertEqual(saved.returncode, 0, saved.stderr)
            encrypted = folder / "runtime" / "github_token.dpapi"
            self.assertNotIn(token, encrypted.read_text(encoding="ascii"))
            with patch.object(github_upload, "TOKEN_FILE", encrypted), \
                 patch.object(github_upload, "DECRYPT_SCRIPT", project / "decrypt_login_password.ps1"):
                self.assertEqual(github_upload.read_saved_token(), token)


if __name__ == "__main__":
    unittest.main()
